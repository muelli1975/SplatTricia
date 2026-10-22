"""Play packaged WebP/AVIF exports in a real Chromium browser (development only)."""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import hashlib
import io
import time

from PIL import Image
import os
from pathlib import Path
import threading


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.directory.resolve()
    paths = sorted(p for p in root.rglob('*') if p.suffix in ('.webp', '.avif'))
    assert {p.suffix for p in paths} == {'.webp', '.avif'}, 'Both export formats are required'
    from playwright.sync_api import sync_playwright
    candidates = [Path(os.environ.get(key, 'C:/Program Files')) / suffix
                  for key in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA')
                  for suffix in ('Microsoft/Edge/Application/msedge.exe',
                                 'Google/Chrome/Application/chrome.exe')]
    browser_path = next((p for p in candidates if p.is_file()), None)
    assert browser_path, 'No installed Edge/Chrome browser found'
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass
    handler = functools.partial(Handler, directory=str(root))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=str(browser_path), headless=True)
            try:
                page = browser.new_page()
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                for path in paths:
                    from urllib.parse import quote
                    url = '/' + quote(path.relative_to(root).as_posix())
                    result = page.evaluate('''async (url) => {
                        const image = new Image();
                        image.src = url;
                        await image.decode();
                        document.body.replaceChildren(image);
                        return {width:image.naturalWidth,height:image.naturalHeight};
                    }''', url)
                    # drawImage(animatedImage) is specified to use its poster
                    # frame. Inspect the actual compositor output instead.
                    early, late = set(), set()
                    started = time.monotonic()
                    while time.monotonic() - started < 2.4:
                        screenshot = page.locator('img').screenshot(animations='allow')
                        with Image.open(io.BytesIO(screenshot)) as image:
                            frame_hash = hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()
                        (early if time.monotonic() - started < 1.1 else late).add(frame_hash)
                        time.sleep(0.05)
                    result.update(early_frames=len(early), late_frames=len(late))
                    assert result['early_frames'] > 1 and result['late_frames'] > 1, (path, result)
                    results.append(dict(file=path.relative_to(root).as_posix(), status='passed', **result))
                version = browser.version
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dict(status='passed', browser_version=version,
                                          animations=results), indent=2), encoding='utf-8')
    print(args.output.read_text(encoding='utf-8'))


if __name__ == '__main__':
    main()
