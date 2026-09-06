from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


CACHE_VERSION = 1
SOURCE_HASH_BLOCK_SIZE = 4 * 1024 * 1024


@dataclass(frozen=True)
class CacheIdentity:
    source_fingerprint: str
    cache_fingerprint: str
    checkpoint_signature: dict[str, int | str]
    target_height: int
    fixed_focal_length_mm: float


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def fingerprint_file(path: Path) -> str:
    digest = hashlib.blake2b(digest_size=16)
    with path.open("rb") as handle:
        while block := handle.read(SOURCE_HASH_BLOCK_SIZE):
            digest.update(block)
    return digest.hexdigest()


def checkpoint_signature(path: Path) -> dict[str, int | str]:
    """
    Stabile Modellkennung ohne Pfad oder Änderungszeit.

    Für den großen Checkpoint werden nur drei 1-MiB-Bereiche gelesen
    (Anfang, Mitte, Ende). So bleibt die Kennung beim Verschieben der
    portablen Programmmappe stabil, ohne bei jedem Start 2,8 GB zu hashen.
    """
    stat = path.stat()
    sample_size = 1024 * 1024
    offsets = sorted(
        {
            0,
            max(0, stat.st_size // 2 - sample_size // 2),
            max(0, stat.st_size - sample_size),
        }
    )
    digest = hashlib.blake2b(digest_size=16)
    digest.update(str(stat.st_size).encode("ascii"))
    with path.open("rb") as handle:
        for offset in offsets:
            handle.seek(offset)
            digest.update(handle.read(sample_size))
    return {
        "name": path.name,
        "size": stat.st_size,
        "sample_fingerprint": digest.hexdigest(),
    }


def build_cache_identity(
    source_path: Path,
    checkpoint: dict[str, int | str],
    target_height: int,
    fixed_focal_length_mm: float,
) -> CacheIdentity:
    source_fingerprint = fingerprint_file(source_path)
    payload = {
        "cache_version": CACHE_VERSION,
        "source_fingerprint": source_fingerprint,
        "checkpoint": checkpoint,
        "target_height": int(target_height),
        "fixed_focal_length_mm": float(fixed_focal_length_mm),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    cache_fingerprint = hashlib.blake2b(encoded, digest_size=16).hexdigest()
    return CacheIdentity(
        source_fingerprint=source_fingerprint,
        cache_fingerprint=cache_fingerprint,
        checkpoint_signature=checkpoint,
        target_height=int(target_height),
        fixed_focal_length_mm=float(fixed_focal_length_mm),
    )


def cache_paths(ply_dir: Path, item_key: str, identity: CacheIdentity) -> tuple[Path, Path]:
    stem = f"{item_key}__{identity.cache_fingerprint[:12]}"
    return ply_dir / f"{stem}.ply", ply_dir / f"{stem}.json"


def write_cache_record(
    metadata_path: Path,
    ply_path: Path,
    source_path: Path,
    identity: CacheIdentity,
) -> None:
    stat = ply_path.stat()
    _atomic_write_json(
        metadata_path,
        {
            "cache_version": CACHE_VERSION,
            "source_name": source_path.name,
            "source_path": str(source_path.resolve()),
            "source_fingerprint": identity.source_fingerprint,
            "cache_fingerprint": identity.cache_fingerprint,
            "checkpoint": identity.checkpoint_signature,
            "target_height": identity.target_height,
            "fixed_focal_length_mm": identity.fixed_focal_length_mm,
            "ply_name": ply_path.name,
            "ply_size": stat.st_size,
            "created_utc": datetime.now(timezone.utc).isoformat(),
        },
    )


def is_valid_cache(
    ply_path: Path,
    metadata_path: Path,
    identity: CacheIdentity,
) -> bool:
    if not ply_path.is_file() or not metadata_path.is_file():
        return False
    try:
        with metadata_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return (
            payload.get("cache_version") == CACHE_VERSION
            and payload.get("source_fingerprint") == identity.source_fingerprint
            and payload.get("cache_fingerprint") == identity.cache_fingerprint
            and payload.get("checkpoint") == identity.checkpoint_signature
            and payload.get("target_height") == identity.target_height
            and float(payload.get("fixed_focal_length_mm"))
            == identity.fixed_focal_length_mm
            and payload.get("ply_name") == ply_path.name
            and int(payload.get("ply_size", -1)) == ply_path.stat().st_size
            and ply_path.stat().st_size > 0
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def clear_temporary_files(temp_dir: Path) -> None:
    """
    Löscht den vollständigen internen Arbeitsordner.

    Der Ordner enthält den PLY-Cache und die zugehörigen JSON-Begleitdaten.
    Er wird erst beim nächsten Verarbeitungslauf wieder angelegt. Fertige
    SBS- und Anaglyphenbilder liegen außerhalb und bleiben erhalten.
    """
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
