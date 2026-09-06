from __future__ import annotations

import argparse
from importlib import metadata
from pathlib import Path


ROOT = Path(__file__).resolve().parent

PACKAGE_HINTS = [
    "customtkinter",
    "numpy",
    "Pillow",
    "plyfile",
    "torch",
    "torchvision",
    "gsplat",
    "pyinstaller",
]


SHARP_NOTICE = """Apple SHARP
===========

SplatTricia interfaces with Apple SHARP, but the SHARP checkpoint is not part of
SplatTricia and is not distributed by this project.

The user must provide the checkpoint separately under:

    models\\sharp_2572gikvuh.pt

Apple's SHARP software and model remain subject to Apple's own license terms.
SplatTricia's MIT License does not apply to SHARP or its checkpoint.

The applicable SHARP license text should be obtained from the official SHARP
source/model distribution used by the user.
"""


def package_license_text(distribution_name: str) -> tuple[str, str] | None:
    try:
        dist = metadata.distribution(distribution_name)
    except metadata.PackageNotFoundError:
        return None

    label = f"{dist.metadata.get('Name', distribution_name)} {dist.version}"
    files = dist.files or []
    candidates = []
    for item in files:
        name = Path(str(item)).name.lower()
        if name.startswith(("license", "copying", "notice")):
            candidates.append(item)

    blocks: list[str] = []
    for item in candidates:
        full = Path(dist.locate_file(item))
        try:
            text = full.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if text:
            blocks.append(f"[{item}]\n{text}")

    if blocks:
        return label, "\n\n".join(blocks)

    license_field = (dist.metadata.get("License") or "").strip()
    if license_field:
        return label, f"Package metadata license field:\n{license_field}"

    return label, "No bundled license file found automatically. Consult the package distribution."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    sections = [SHARP_NOTICE.strip()]
    for package in PACKAGE_HINTS:
        result = package_license_text(package)
        if result is None:
            sections.append(
                f"{package}\n{'=' * len(package)}\nPackage not installed in the build environment."
            )
            continue
        label, text = result
        sections.append(f"{label}\n{'=' * len(label)}\n{text}")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n\n\n".join(sections) + "\n", encoding="utf-8")
    print(f"Lizenzdatei geschrieben: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
