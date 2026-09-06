from __future__ import annotations

import os
from pathlib import Path


def main() -> int:
    # The installed gsplat package compiles its CUDA extension lazily.  Importing
    # and invoking the extension loader here forces that compilation into the
    # build environment before PyInstaller packages the result.
    os.environ.setdefault("TORCH_CUDA_ARCH_LIST", "7.5;8.0;8.6;8.9;9.0+PTX")

    import torch
    import gsplat.cuda._wrapper as wrapper

    ext = wrapper._C
    # Accessing one exported symbol forces extension initialisation on gsplat
    # versions where _C is a lazy wrapper object.
    _ = getattr(ext, "rasterize_to_pixels_fwd", None)

    import gsplat.cuda as cuda_pkg

    cuda_dir = Path(cuda_pkg.__file__).resolve().parent
    pyds = sorted(cuda_dir.glob("*.pyd"))
    if not pyds:
        raise RuntimeError(f"Keine gsplat CUDA-PYD unter {cuda_dir} gefunden.")

    print("gsplat native extension bereit:")
    for path in pyds:
        print(f"  {path}")
    print(f"CUDA verfuegbar: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
