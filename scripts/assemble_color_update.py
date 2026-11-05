"""Reuse the exact published 1.1 runtime; update only application and source files."""
import argparse
from pathlib import Path
import assemble_preview


assemble_preview.BASE_PACKAGES = {
    "SplatTricia_1.1.zip": "766b63c5d29d8ab3f1fa5e755203e673dbdaf1f5268fad3eb70fcacffa601e75",
    "SplatTricia_1.1_Runtime_1.zip": "99369b6502061bcf03829c0ad17b5ca8a3c74913ecae94d237765c1cdb95d8e8",
    "SplatTricia_1.1_Runtime_2.zip": "7cfa03d01433706345b95d9c04b819ea29381c2a0123a0b61f0b005cbfacb9be"
}



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['assemble', 'package'])
    args = parser.parse_args()
    if args.stage == 'assemble':
        assemble_preview.assemble(Path('base'), Path('portable'), stable=True)
    else:
        assemble_preview.package(Path('base'), Path('portable/SplatTricia'),
                                 Path('publish'), base_version='1.1')
        for index in (1, 2):
            name = f'SplatTricia_1.1_Runtime_{index}.zip'
            assert assemble_preview.digest(Path('publish') / name) == assemble_preview.BASE_PACKAGES[name]
