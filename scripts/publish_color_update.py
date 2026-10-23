"""Refresh explicitly authorized existing assets after staging and download verification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request


def digest(path):
    with path.open('rb') as stream:
        return 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    tag = config['tag']
    branch = config['branch']
    repo, sha = os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_SHA']
    assert repo == config['repository']
    token = os.environ['GH_TOKEN']
    api_root = 'https://api.github.com/repos/' + repo

    def request(url, method='GET', payload=None, binary=False):
        data = payload if binary else (json.dumps(payload).encode() if payload is not None else None)
        headers = {'Authorization': 'Bearer ' + token,
                   'Accept': 'application/vnd.github+json',
                   'X-GitHub-Api-Version': '2022-11-28',
                   'Content-Type': 'application/octet-stream' if binary else 'application/json'}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=300) as response:
            body = response.read()
        return json.loads(body) if body else None

    def api(path, method='GET', payload=None):
        return request(api_root + path, method, payload)

    def current_tag():
        return api('/git/ref/tags/' + tag)['object']['sha']

    def check_heads():
        assert api('/git/ref/heads/' + branch)['object']['sha'] == sha, 'A newer source commit superseded this build'
        assert current_tag() in (config['previous_tag'], sha), 'Release tag changed concurrently'

    check_heads()
    release = api('/releases/tags/' + tag)
    assert release['id'] == config['release_id'] and not release['draft'] and not release['immutable']
    old_body = release['body']
    old_tag = current_tag()
    assets = {a['name']: a for a in release['assets']}
    files = {}
    for name, expected in config['assets'].items():
        matches = list(args.root.rglob(name))
        assert len(matches) == 1, (name, 'Missing or ambiguous package')
        path = matches[0]
        files[name] = dict(path=path, digest=digest(path), size=path.stat().st_size)
        assert name in assets
        if assets[name]['digest'] != files[name]['digest']:
            assert assets[name]['digest'] == expected, ('Published asset changed concurrently', name)
        if name not in config['replace']:
            assert files[name]['digest'] == expected, ('Unrelated runtime archive changed', name)
    staged, previous, promoted = {}, {}, []
    tag_moved = False
    notes_updated = False
    try:
        # Old public download names remain available until ALL new uploads pass.
        for name in config['replace']:
            item = files[name]
            if assets[name]['digest'] == item['digest'] and assets[name]['size'] == item['size']:
                continue
            staged_name = name + '.pending-' + sha[:12]
            url = release['upload_url'].split('{')[0] + '?name=' + urllib.parse.quote(staged_name)
            uploaded = request(url, 'POST', item['path'].read_bytes(), binary=True)
            staged[name] = uploaded
            assert uploaded['digest'] == item['digest'] and uploaded['size'] == item['size']
            # Public download URLs need no Authorization header on redirects.
            with urllib.request.urlopen(uploaded['browser_download_url'], timeout=300) as stream:
                downloaded = 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()
            assert downloaded == item['digest'], ('Downloaded upload differs', name)
            print('Staged and download-verified:', name, flush=True)
        check_heads()
        assert api('/releases/tags/' + tag)['body'] == old_body, 'Release notes changed concurrently'
        for name, uploaded in staged.items():
            old = assets[name]
            api('/releases/assets/' + str(old['id']), 'PATCH', {'name': name + '.previous-' + sha[:12]})
            previous[name] = old
            api('/releases/assets/' + str(uploaded['id']), 'PATCH', {'name': name})
            promoted.append(name)
        if old_tag != sha:
            api('/git/refs/tags/' + tag, 'PATCH', {'sha': sha, 'force': True})
            tag_moved = True
        # Keep the existing release prose. Only refresh existing hash/source references.
        body = old_body
        for name, item in files.items():
            body = body.replace(assets[name]['digest'].split(':')[-1], item['digest'].split(':')[-1])
        body = body.replace(old_tag, sha)
        body = body.replace(old_tag[:7], sha[:7])
        api('/releases/' + str(release['id']), 'PATCH', {'body': body, 'target_commitish': sha})
        notes_updated = True
        final = api('/releases/tags/' + tag)
        final_assets = {a['name']: a for a in final['assets']}
        assert final['body'] == body and not final['draft'] and current_tag() == sha
        for name, item in files.items():
            assert final_assets[name]['digest'] == item['digest'] and final_assets[name]['size'] == item['size']
            if name in config['replace']:
                with urllib.request.urlopen(final_assets[name]['browser_download_url'], timeout=300) as stream:
                    downloaded = 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()
                assert downloaded == item['digest'], ('Final public download differs', name)
    except BaseException:
        # Restore the previous names and source link if promotion failed.
        for name in reversed(promoted):
            api('/releases/assets/' + str(staged[name]['id']), 'PATCH', {'name': name + '.pending-' + sha[:12]})
        for name, old in previous.items():
            api('/releases/assets/' + str(old['id']), 'PATCH', {'name': name})
        if tag_moved and current_tag() == sha:
            api('/git/refs/tags/' + tag, 'PATCH', {'sha': old_tag, 'force': True})
        if notes_updated:
            api('/releases/' + str(release['id']), 'PATCH', {'body': old_body, 'target_commitish': release['target_commitish']})
        for uploaded in staged.values():
            api('/releases/assets/' + str(uploaded['id']), 'DELETE')
        raise
    # The new assets, release notes and tag have all been checked successfully.
    for old in previous.values():
        api('/releases/assets/' + str(old['id']), 'DELETE')
    print(json.dumps({'status': 'passed', 'release': final['html_url'], 'commit': sha,
                      'assets': {name: {'size': item['size'], 'digest': item['digest']}
                                 for name, item in files.items()}}, indent=2))


if __name__ == '__main__':
    main()
