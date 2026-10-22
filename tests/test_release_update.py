"""Exercise release replacement and rollback without making network requests."""
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs


class ReleaseUpdateTests(unittest.TestCase):
    def run_update(self, fail_promotion=False):
        path = Path(__file__).resolve().parents[1] / 'scripts/publish_export_update.py'
        spec = importlib.util.spec_from_file_location('release_update_under_test', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        old_sha, new_sha = 'a' * 40, 'b' * 40
        data = {'app.zip': b'old application', 'sums.txt': b'old sums', 'runtime.zip': b'unchanged runtime'}
        def digest(value):
            return 'sha256:' + hashlib.sha256(value).hexdigest()
        assets = {i: dict(id=i, name=name, digest=digest(value), size=len(value),
                          browser_download_url='https://downloads.test/' + str(i))
                  for i, (name, value) in enumerate(data.items(), 1)}
        old_assets = copy.deepcopy(assets)
        release = dict(id=123, draft=False, immutable=False, body='old release notes',
                       target_commitish=old_sha, upload_url='https://uploads.github.com/assets{?name}',
                       html_url='https://github.com/example/test/releases/tag/v1.1')
        old_release = copy.deepcopy(release)
        tag = old_sha
        uploaded_data = {}
        failed = False
        def response(value):
            return io.BytesIO(json.dumps(value).encode() if value is not None else b'')
        def urlopen(req, **kwargs):
            nonlocal tag, failed
            if isinstance(req, str):
                return io.BytesIO(uploaded_data[int(req.rsplit('/', 1)[1])])
            url = urlparse(req.full_url)
            method = req.get_method()
            payload = json.loads(req.data) if req.data and url.netloc != 'uploads.github.com' else None
            route = url.path.removeprefix('/repos/example/test')
            if url.netloc == 'uploads.github.com':
                identifier = max(assets) + 1
                name = parse_qs(url.query)['name'][0]
                assets[identifier] = dict(id=identifier, name=name, digest=digest(req.data),
                                         size=len(req.data), browser_download_url='https://downloads.test/' + str(identifier))
                uploaded_data[identifier] = req.data
                return response(assets[identifier])
            if route == '/git/ref/heads/main':
                return response({'object': {'sha': new_sha}})
            if route == '/git/ref/tags/v1.1':
                return response({'object': {'sha': tag}})
            if route == '/git/refs/tags/v1.1':
                tag = payload['sha']; return response({})
            if route == '/releases/tags/v1.1':
                return response(dict(release, assets=list(assets.values())))
            if route == '/releases/123':
                release.update(payload); return response(release)
            if route.startswith('/releases/assets/'):
                identifier = int(route.rsplit('/', 1)[1])
                if method == 'DELETE':
                    del assets[identifier]; return response(None)
                if fail_promotion and not failed and payload['name'] == 'sums.txt' and identifier not in old_assets:
                    failed = True
                    raise OSError('Simulated failed second promotion')
                assets[identifier].update(payload)
                return response(assets[identifier])
            raise AssertionError((method, route))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in data.items():
                (root / name).write_bytes(b'new ' + value if name != 'runtime.zip' else value)
            (root / 'notes.md').write_text('new release notes')
            config = dict(repository='example/test', release_id=123, previous_tag=old_sha,
                          assets={name: digest(value) for name, value in data.items()},
                          replace=['app.zip', 'sums.txt'])
            (root / 'config.json').write_text(json.dumps(config))
            args = ['publish', '--root', str(root), '--config', str(root / 'config.json'),
                    '--notes', str(root / 'notes.md')]
            with (patch.object(sys, 'argv', args), patch.dict(os.environ, dict(
                    GITHUB_REPOSITORY='example/test', GITHUB_SHA=new_sha, GH_TOKEN='test-token')),
                    patch.object(module.urllib.request, 'urlopen', urlopen), patch('sys.stdout', new_callable=io.StringIO)):
                if fail_promotion:
                    with self.assertRaisesRegex(OSError, 'Simulated'):
                        module.main()
                else:
                    module.main()
        self.assertEqual(assets[3], old_assets[3], 'Runtime asset must retain its exact ID and digest')
        self.assertEqual({a['name'] for a in assets.values()}, set(data))
        if fail_promotion:
            self.assertEqual(assets, old_assets)
            self.assertEqual(tag, old_sha)
            self.assertEqual(release, old_release)
        else:
            self.assertEqual(tag, new_sha)
            self.assertEqual(release['id'], 123)
            self.assertIn('new release notes', release['body'])
            self.assertNotIn(1, assets)

    def test_replace_only_selected_assets_and_keep_release_identity(self):
        self.run_update()

    def test_failed_promotion_restores_previous_assets_tag_and_notes(self):
        self.run_update(fail_promotion=True)
