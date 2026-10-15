"""Assemble a 1.1 test build and rebuild its EXE from the verified 1.0 dependencies.

Third-party Python code, native libraries and frozen runtime hooks are retained.
Preview.spec replaces only application modules and rebuilds a normal frozen EXE.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE_PACKAGES = {
    'SplatTricia_1.0.zip':'e1bc1fb89ca3e36890de38bf754790fc754a0f442b7fe780cc87e4cec75c820b',
    'SplatTricia_1.0_Runtime_1.zip':'5a6e78810af48108d4cc70328b3b22958a1d259329b8c4b190e341139bc3b7d3',
    'SplatTricia_1.0_Runtime_2.zip':'7cfa03d01433706345b95d9c04b819ea29381c2a0123a0b61f0b005cbfacb9be',
}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def assemble(base: Path, output: Path, stable: bool = False):
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for name, expected in BASE_PACKAGES.items():
        path = base/name
        if digest(path) != expected:
            raise RuntimeError(f'Base package checksum mismatch: {name}')
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                name = info.filename.replace('\\','/')
                p = PurePosixPath(name)
                if p.is_absolute() or '..' in p.parts or ':' in name or p.parts[0] != 'SplatTricia':
                    raise RuntimeError(f'Unsafe ZIP entry: {name}')
                target = output.joinpath(*p.parts)
                if name.endswith('/'):
                    target.mkdir(parents=True,exist_ok=True)
                    continue
                if name in hashes:
                    raise RuntimeError(f'Duplicate base file: {name}')
                target.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(info) as source, target.open('wb') as destination:
                    shutil.copyfileobj(source,destination)
                hashes[name] = digest(target)
        print('Extracted and verified:',path.name,flush=True)
    app = output/'SplatTricia'
    if (app/'models/sharp_2572gikvuh.pt').exists():
        raise RuntimeError('Checkpoint must not be distributed')
    locales = app/'_internal/splattricia/locales'
    locales.mkdir(parents=True,exist_ok=True)
    for path in (ROOT/'src/splattricia/locales').glob('*.json'):
        shutil.copy2(path,locales/path.name)
    source = app/'source'
    shutil.rmtree(source)
    source.mkdir()
    for name in ['src','scripts','tests']:
        shutil.copytree(ROOT/name,source/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for path in ROOT.iterdir():
        if path.is_file() and path.suffix in ('.md','.txt','.py','.bat','.spec'):
            shutil.copy2(path,source/path.name)
    shutil.copytree(ROOT/'assets',source/'assets')
    for name in ['README_DE.txt','README_EN.txt','LICENSE.txt']:
        shutil.copy2(ROOT/name,app/name)
    note = (('SplatTricia 1.1\n\n' if stable else 'SplatTricia 1.1 - Testversion / Test build\n\n') +
            'Alle drei ZIP-Dateien in denselben Zielordner entpacken.\n'
            'Extract all three ZIP files into the same destination directory.\n\n'
            'SHARP-Checkpoint separat von Apple beziehen; vor dem Download die\n'
            'Modellbedingungen lesen und akzeptieren. Nicht in diesen ZIPs enthalten.\n'
            'Obtain the SHARP checkpoint separately from Apple and read and accept\n'
            'the model terms before downloading. It is not included in these ZIPs.\n'
            'https://github.com/apple-aiml-research/ml-sharp\n'
            'Datei / file: SplatTricia/models/sharp_2572gikvuh.pt\n\n'
            'Danach SplatTricia.exe starten. / Then start SplatTricia.exe.\n'
            'NVIDIA-Grafikkarte weiterhin erforderlich. / NVIDIA GPU still required.\n')
    (app/'INSTALLATION.txt').write_text(note,encoding='utf-8')
    (app/'models').mkdir(exist_ok=True)
    # Locale resources belong to the updated application. All other frozen
    # runtime files must remain identical before the EXE is rebuilt.
    updated_locales = {f'SplatTricia/_internal/splattricia/locales/{path.name}'
                       for path in (ROOT/'src/splattricia/locales').glob('*.json')}
    preserved = {name:sha for name,sha in hashes.items()
                 if (name.startswith('SplatTricia/_internal/') or name=='SplatTricia/SplatTricia.exe')
                 and name not in updated_locales}
    for name,expected in preserved.items():
        if digest(output.joinpath(*PurePosixPath(name).parts)) != expected:
            raise RuntimeError(f'Runtime changed: {name}')
    report = {'preserved_runtime_files':len(preserved),'launcher_sha256':digest(app/'SplatTricia.exe'),
              'application_source':'frozen application modules','version':'1.1','checkpoint_included':False}
    (output/'assembly-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return app


def package(base: Path, app: Path, destination: Path):
    destination.mkdir(parents=True,exist_ok=False)
    runtime = set()
    application_resources = {f'SplatTricia/_internal/splattricia/locales/{path.name}'
                             for path in (ROOT/'src/splattricia/locales').glob('*.json')}
    for index in (1,2):
        old = base/f'SplatTricia_1.0_Runtime_{index}.zip'
        new = destination/f'SplatTricia_1.1_Runtime_{index}.zip'
        shutil.copyfile(old,new)
        with zipfile.ZipFile(new) as archive:
            outdated = [info.filename for info in archive.infolist()
                        if info.filename.replace('\\','/') in application_resources]
        if outdated:
            # Move application translations out of the dependency ZIPs so the
            # extraction order cannot restore old labels. 7-Zip copies all
            # retained compressed entries without recompressing native files.
            seven_zip = shutil.which('7z') or str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'7-Zip/7z.exe')
            subprocess.run([seven_zip,'d','-y',str(new),*outdated],check=True)
        with zipfile.ZipFile(new) as archive:
            runtime.update(info.filename.replace('\\','/').rstrip('/') for info in archive.infolist())
    if runtime & application_resources:
        raise RuntimeError('Old application translations remain in runtime ZIPs')
    main = destination/'SplatTricia_1.1.zip'
    with zipfile.ZipFile(main,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(app.rglob('*')):
            relative = path.relative_to(app.parent).as_posix()
            if path.is_file() and relative not in runtime and '__pycache__' not in path.parts:
                if path.suffix in ('.pt','.pth','.safetensors') and 'models' in path.parts:
                    raise RuntimeError('Checkpoint in output')
                archive.write(path,relative)
        archive.writestr('SplatTricia/models/',b'')
    files = [main,*(destination/f'SplatTricia_1.1_Runtime_{i}.zip' for i in (1,2))]
    if any(path.stat().st_size >= 2*1024**3 for path in files):
        raise RuntimeError('Release asset exceeds GitHub size limit')
    # Verify the combined extracted result, not just the pre-package app.
    # This catches omitted updates and overlapping paths across the three ZIPs.
    expected = {path.relative_to(app.parent).as_posix():digest(path)
                for path in app.rglob('*') if path.is_file() and '__pycache__' not in path.parts}
    actual = {}
    for path in files:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                name = info.filename.replace('\\','/')
                if name.endswith('/'):
                    continue
                if name in actual:
                    raise RuntimeError(f'Duplicate packaged file: {name}')
                with archive.open(info) as stream:
                    actual[name] = hashlib.file_digest(stream,'sha256').hexdigest()
    if actual != expected:
        raise RuntimeError('Combined ZIP contents differ from the tested application')
    print(f'Verified {len(actual)} packaged files against the tested application.',flush=True)
    (destination/'SplatTricia_1.1_SHA256SUMS.txt').write_text(''.join(f'{digest(path)}  {path.name}\n' for path in files),encoding='ascii')
    print('Three test ZIPs created; EXE rebuilt, native dependencies preserved.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['assemble','package'])
    parser.add_argument('--base',type=Path,default=Path('base'))
    parser.add_argument('--output',type=Path,default=Path('portable'))
    parser.add_argument('--publish',type=Path,default=Path('publish'))
    parser.add_argument('--stable',action='store_true',help='Write the final-release installation note')
    args=parser.parse_args()
    if args.stage=='assemble':assemble(args.base,args.output,args.stable)
    else:package(args.base,args.output/'SplatTricia',args.publish)
