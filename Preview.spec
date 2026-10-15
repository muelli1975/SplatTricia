# Rebuild the application EXE while retaining the verified dependency code archive.
# Native DLLs/PYDs and all third-party Python code come from the existing 1.0.
from pathlib import Path
import importlib.util
import json
import marshal

from PyInstaller.archive.readers import CArchiveReader
from PyInstaller.config import CONF

ROOT = Path(SPECPATH).resolve()
base = ROOT / 'portable/SplatTricia/SplatTricia.exe'
archive = CArchiveReader(str(base))
old = archive.open_embedded_archive('PYZ.pyz')
entries = []
code = {}
for name, item in old.toc.items():
    if name == 'splattricia' or name.startswith('splattricia.'):
        continue
    kind = item[0]
    source = '-' if kind == 3 else ('__init__.py' if kind == 1 else 'module.py')
    entries.append((name, source, 'PYMODULE'))
    if kind != 3:
        code[name] = old.extract(name)
for path in sorted((ROOT/'src/splattricia').rglob('*.py')):
    relative = path.relative_to(ROOT/'src').with_suffix('')
    parts = relative.parts[:-1] if relative.name == '__init__' else relative.parts
    name = '.'.join(parts)
    entries.append((name,str(path),'PYMODULE'))
    code[name] = compile(path.read_bytes(),str(relative)+'.py','exec',optimize=0)
CONF.setdefault('code_cache', {})[id(entries)] = code
pyz = PYZ(entries)

# Preserve the published application's runtime hook code, including Tcl/Tk,
# multiprocessing and dependency resource setup.
hook_dir = ROOT / 'build/preview-hooks'
hook_dir.mkdir(parents=True,exist_ok=True)
hooks = []
for name,item in archive.toc.items():
    if item[-1] == 's' and name not in {'pyiboot01_bootstrap','launcher'}:
        path = hook_dir / (name+'.pyc')
        path.write_bytes(importlib.util.MAGIC_NUMBER + b'\0'*12 + archive.extract(name))
        hooks.append((name,str(path),'PYSOURCE'))

exe = EXE(pyz, hooks, [('launcher',str(ROOT/'launcher.py'),'PYSOURCE')], [],
          exclude_binaries=True, name='SplatTricia', console=False, debug=False,
          strip=False, upx=False, bootloader_ignore_signals=False,
          icon=str(ROOT/'assets/splattricia.ico'), contents_directory='_internal')
print('Rebuilt application EXE with', len(entries), 'Python modules and unchanged dependency code.')
coll = COLLECT(exe, [], name='SplatTricia', strip=False, upx=False)
