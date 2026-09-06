from __future__ import annotations

import argparse
import time
from pathlib import Path

from .config import ProcessingConfig
from .controller import ProcessingCancelled, ProcessingController
from .models import ProgressEvent


def _print_event(event: ProgressEvent) -> None:
    prefix = ""
    if event.total > 0 and event.current > 0:
        prefix = f"[{event.current}/{event.total}] "
    print(prefix + event.fallback_message)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Modularer SplatTricia-Kern")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=Path("output"))
    parser.add_argument("-c", "--checkpoint", type=Path, default=Path("models/sharp_2572gikvuh.pt"))
    parser.add_argument("--exiftool", type=Path, default=Path("tools/exiftool.exe"))
    parser.add_argument("--target-height", type=int, default=2160)
    parser.add_argument("--deviation", type=float, default=20.0)
    parser.add_argument("--window-position", type=float, default=100.0)
    parser.add_argument("--window-back", type=float, default=0.0)
    parser.add_argument("--gray-anaglyph", action="store_true")
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--rebuild-ply", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    start = time.perf_counter()
    config = ProcessingConfig(
        checkpoint_path=args.checkpoint,
        exiftool_path=args.exiftool if args.exiftool.is_file() else None,
        target_height=args.target_height,
        deviation_permille=args.deviation,
        window_position_percent=args.window_position,
        window_back_permille=args.window_back,
        gray_anaglyph=args.gray_anaglyph,
    )
    controller = ProcessingController(config, event_callback=_print_event)
    try:
        items = controller.run(
            args.input, args.output, args.recursive, args.rebuild_ply, args.limit
        )
    except ProcessingCancelled:
        print("Verarbeitung abgebrochen.")
        return 3
    ok = sum(1 for item in items if item.status == "ok")
    print(f"Gesamtzeit: {time.perf_counter() - start:.2f} s")
    print(f"Erfolgreich: {ok}/{len(items)}")
    return 0 if ok == len(items) else 2


if __name__ == "__main__":
    raise SystemExit(main())
