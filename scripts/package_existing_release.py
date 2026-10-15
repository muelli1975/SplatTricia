"""Split the existing Windows 1.0 distribution without rebuilding any binaries."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import urllib.request
import zipfile

SOURCE_URL = 'https://traumnarben.de/download/SplatTricia_1.0.zip'
SOURCE_SIZE = 3151440792
SOURCE_SHA256 = 'a04843bd7d38582c4bed23a23033de65a83b471f9fa8a34aefb3f333152c0229'
# Leave ample room below GitHub's 2 GiB per-asset limit.
RUNTIME_LIMIT = 1700 * 1024 * 1024

INSTALLATION = '''SplatTricia 1.0 - Installation / Setup
======================================

Deutsch
-------
1. SplatTricia_1.0.zip und ALLE SplatTricia_1.0_Runtime_*.zip aus demselben
   GitHub-Release herunterladen.
2. Jedes ZIP in DENSELBEN Zielordner entpacken. Alle Archive enthalten Teile
   des gemeinsamen Unterordners SplatTricia. Die Inhalte zusammenfuehren;
   die ZIPs nicht in getrennte Ordner mit den Archivnamen entpacken.
3. Den SHARP-Checkpoint selbst von Apples offizieller Projektseite beziehen.
   Vor dem Download Apples Modellbedingungen lesen und akzeptieren:
   https://github.com/apple-aiml-research/ml-sharp
4. sharp_2572gikvuh.pt im Unterordner SplatTricia\\models ablegen.
5. SplatTricia\\SplatTricia.exe starten.

Saemtliche Laufzeitbibliotheken sind in den ZIPs enthalten. Python, CUDA-
Toolkit und Build-Werkzeuge muessen nicht separat installiert werden.
Windows 10/11 und eine geeignete NVIDIA-Grafikkarte mit aktuellem Treiber
werden weiterhin benoetigt. Nach der Einrichtung funktioniert alles offline.
Der SHARP-Checkpoint ist in keinem dieser Pakete enthalten.

English
-------
1. Download SplatTricia_1.0.zip and ALL SplatTricia_1.0_Runtime_*.zip files
   from the same GitHub release.
2. Extract EVERY ZIP into the SAME destination directory. All archives
   contain parts of the shared SplatTricia subfolder. Merge their contents;
   do not extract each ZIP into a separate folder named after the archive.
3. Obtain the SHARP checkpoint yourself from Apple's official project page.
   Read and accept Apple's model terms before downloading:
   https://github.com/apple-aiml-research/ml-sharp
4. Place sharp_2572gikvuh.pt in SplatTricia\\models.
5. Start SplatTricia\\SplatTricia.exe.

All runtime libraries are included in the ZIPs. No separate Python, CUDA
Toolkit or build tools are required. Windows 10/11 and a compatible NVIDIA
GPU with a current driver are still required. Processing works offline after
setup. The SHARP checkpoint is not included in any of these packages.
'''


def sha256_file(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download_original(path: Path) -> None:
    if path.exists() and path.stat().st_size == SOURCE_SIZE:
        if sha256_file(path) == SOURCE_SHA256:
            return
        raise RuntimeError('Existing original archive has an unexpected checksum')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Bounded range requests also work with servers that close long transfers.
    while (offset := path.stat().st_size if path.exists() else 0) < SOURCE_SIZE:
        end = min(offset + 128 * 1024 * 1024, SOURCE_SIZE) - 1
        request = urllib.request.Request(SOURCE_URL, headers={'Range': f'bytes={offset}-{end}'})
        with urllib.request.urlopen(request, timeout=120) as response:
            if response.status != 206 or not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                raise RuntimeError('The original server did not honor the requested byte range')
            data = response.read()
        if not data or len(data) != end - offset + 1:
            raise RuntimeError('Incomplete download range; the command can be retried')
        with path.open('ab') as stream:
            stream.write(data)
        print(f'Original downloaded: {path.stat().st_size}/{SOURCE_SIZE}', flush=True)
    if sha256_file(path) != SOURCE_SHA256:
        raise RuntimeError('Original archive differs from the independently audited release')


def canonical(name: str) -> str:
    name = name.replace('\\', '/')
    parts = PurePosixPath(name).parts
    if not parts or parts[0] != 'SplatTricia' or '..' in parts or ':' in name or '\n' in name or '\r' in name:
        raise RuntimeError(f'Unexpected archive path: {name}')
    return name


def repackage(source: Path, destination: Path) -> dict:
    if sha256_file(source) != SOURCE_SHA256:
        raise RuntimeError('Original archive checksum does not match')
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(source) as original:
        entries = original.infolist()
        names = [canonical(item.filename) for item in entries]
        if len(names) != len(set(names)):
            raise RuntimeError('Duplicate original archive entries')
        if any('sharp_2572gikvuh.pt' in name.lower() for name in names):
            raise RuntimeError('Checkpoint found in distribution')
        if any(name.startswith('SplatTricia/models/') and not item.is_dir()
               and Path(name).suffix.lower() in {'.pt', '.pth', '.safetensors'}
               for item, name in zip(entries, names)):
            raise RuntimeError('Model weights found in distribution')
        files = {canonical(item.filename): item for item in entries if not item.filename.endswith(('\\', '/'))}
        if not {'SplatTricia/SplatTricia.exe','SplatTricia/LICENSE.txt','SplatTricia/LICENSES.txt'} <= files.keys():
            raise RuntimeError('Expected release files missing')
        groups: list[list[zipfile.ZipInfo]] = [[]]
        runtime: list[list[zipfile.ZipInfo]] = [[]]
        runtime_size = 0
        for item in entries:
            name = canonical(item.filename)
            if name.startswith('SplatTricia/_internal/') and not item.filename.endswith(('\\','/')):
                # Info-ZIP copies compressed records; the estimate needs no recompression margin.
                cost = item.compress_size + len(item.filename.encode('utf-8')) * 2 + 1024
                if cost > RUNTIME_LIMIT:
                    raise RuntimeError(f'Runtime file exceeds package limit: {name}')
                if runtime_size + cost > RUNTIME_LIMIT and runtime[-1]:
                    runtime.append([])
                    runtime_size = 0
                runtime[-1].append(item)
                runtime_size += cost
            else:
                groups[0].append(item)
        groups.extend(group for group in runtime if group)
        packages = []
        for index, group in enumerate(groups):
            name = 'SplatTricia_1.0.zip' if index == 0 else f'SplatTricia_1.0_Runtime_{index}.zip'
            target = destination / name
            subprocess.run(['zip', '-q', '-U', '-nw', str(source.resolve()), '--out', str(target.resolve()), '-@'],
                           input=''.join(item.filename + '\n' for item in group), text=True, check=True)
            if index == 0:
                with zipfile.ZipFile(target, 'a', compression=zipfile.ZIP_DEFLATED) as package:
                    note = zipfile.ZipInfo('SplatTricia/INSTALLATION.txt', date_time=(2026, 9, 28, 0, 0, 0))
                    note.compress_type = zipfile.ZIP_DEFLATED
                    package.writestr(note, INSTALLATION)
                    # Ensure the empty, user-supplied-checkpoint directory exists.
                    if not any(canonical(item.filename).rstrip('/') == 'SplatTricia/models' for item in group):
                        package.writestr(zipfile.ZipInfo('SplatTricia/models/', date_time=(2026, 9, 28, 0, 0, 0)), b'')
            if target.stat().st_size >= 2 * 1024**3:
                raise RuntimeError(f'GitHub asset limit exceeded: {name}')
            packages.append({'name': name, 'size': target.stat().st_size, 'sha256': sha256_file(target)})
            print(f'Created {name}: {target.stat().st_size} bytes', flush=True)

        # Read every file in both the original and the new packages. This verifies
        # CRCs as well as byte identity, and detects missing/duplicate/new files.
        inventory = {}
        for package in packages:
            with zipfile.ZipFile(destination / package['name']) as archive:
                for info in archive.infolist():
                    name = canonical(info.filename)
                    if info.filename.endswith(('\\','/')):
                        continue
                    if name in inventory:
                        raise RuntimeError(f'Duplicate packaged file: {name}')
                    with archive.open(info) as stream:
                        inventory[name] = hashlib.file_digest(stream, 'sha256').hexdigest()
        if set(inventory) != set(files) | {'SplatTricia/INSTALLATION.txt'}:
            raise RuntimeError('Packaged inventory differs from original plus installation note')
        for name, info in files.items():
            with original.open(info) as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if inventory[name] != digest:
                raise RuntimeError(f'File content changed: {name}')
        report = {'original_sha256': SOURCE_SHA256, 'original_size': SOURCE_SIZE,
                  'original_entries': len(entries), 'unchanged_files': len(files),
                  'added_files': ['SplatTricia/INSTALLATION.txt'], 'checkpoint_included': False,
                  'files': inventory, 'packages': packages}
    (destination / 'SplatTricia_1.0_manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    checksums = [(p['name'], p['sha256']) for p in packages]
    manifest = destination / 'SplatTricia_1.0_manifest.json'
    checksums.append((manifest.name, sha256_file(manifest)))
    (destination / 'SplatTricia_1.0_SHA256SUMS.txt').write_text(''.join(f'{digest}  {name}\n' for name,digest in checksums),encoding='ascii')
    print(f"Verified {len(files)} unchanged original files; no checkpoint included.", flush=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, default=Path('original.zip'))
    parser.add_argument('--output', type=Path, default=Path('publish'))
    args = parser.parse_args()
    download_original(args.original)
    repackage(args.original, args.output)


if __name__ == '__main__':
    main()
