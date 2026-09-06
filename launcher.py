from __future__ import annotations

import sys
from pathlib import Path


def _add_source_path() -> None:
    root = Path(__file__).resolve().parent
    source = root / "src"
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))


def main() -> int:
    _add_source_path()
    from splattricia.gui import run_gui

    run_gui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
