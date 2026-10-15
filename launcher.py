from __future__ import annotations

import importlib
import os
import sys
import traceback
from pathlib import Path


STARTUP_LOG_NAME = "splattricia_startup_error.log"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def add_portable_runtime_paths(base_dir: Path) -> None:
    candidates = [Path(sys.executable).resolve().parent, base_dir, base_dir / "tools"]
    if sys.platform.startswith("win"):
        candidates.append(base_dir / "venv" / "Scripts")
    else:
        candidates.append(base_dir / "venv" / "bin")

    existing = os.environ.get("PATH", "")
    keys = {
        part.lower() if sys.platform.startswith("win") else part
        for part in existing.split(os.pathsep)
        if part
    }
    prepend: list[str] = []
    for candidate in candidates:
        if not candidate.exists():
            continue
        value = str(candidate)
        key = value.lower() if sys.platform.startswith("win") else value
        if key not in keys:
            prepend.append(value)
            keys.add(key)
    if prepend:
        os.environ["PATH"] = os.pathsep.join(prepend + ([existing] if existing else []))


def install_portable_gsplat_backend() -> None:
    """Use the bundled native gsplat extension instead of runtime JIT builds."""
    if not getattr(sys, "frozen", False):
        return

    # Import torch first so its native DLL search paths are active before the
    # compiled gsplat extension is loaded.
    import torch  # noqa: F401

    try:
        native_backend = importlib.import_module("gsplat_cuda")
    except Exception as exc:
        raise RuntimeError(
            "Die mitgelieferte gsplat-CUDA-Erweiterung konnte nicht geladen werden. "
            "Der portable Build ist unvollstaendig oder inkompatibel."
        ) from exc

    # gsplat 1.5.3 first looks for gsplat.csrc. Register the bundled module
    # under that name before importing gsplat, so its JIT fallback is never used.
    sys.modules["gsplat.csrc"] = native_backend
    import gsplat

    setattr(gsplat, "csrc", native_backend)


def write_startup_error(base_dir: Path) -> None:
    try:
        (base_dir / STARTUP_LOG_NAME).write_text(
            traceback.format_exc(),
            encoding="utf-8",
        )
    except OSError:
        pass


def run() -> int:
    base_dir = app_dir()
    add_portable_runtime_paths(base_dir)

    if not getattr(sys, "frozen", False):
        src_dir = base_dir / "src"
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

    try:
        install_portable_gsplat_backend()

        # Vor dem Smoke-Test importieren: Der Test bestaetigt damit sowohl das
        # GUI-Paket als auch die native gsplat-Erweiterung im portablen Build.
        from splattricia.gui import run_gui

        if "--smoke-test" in sys.argv:
            return 0

        return int(run_gui())
    except Exception:
        write_startup_error(base_dir)
        raise


if __name__ == "__main__":
    raise SystemExit(run())
