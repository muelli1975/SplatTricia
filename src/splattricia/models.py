from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .cache import CacheIdentity


@dataclass
class ProcessingItem:
    source_path: Path
    key: str
    ply_path: Path
    cache_metadata_path: Path
    sbs_path: Path
    anaglyph_path: Path
    cache_identity: CacheIdentity
    cache_valid: bool
    status: str = "offen"


@dataclass(frozen=True)
class ProgressEvent:
    stage: str
    message_key: str
    fallback_message: str
    current: int = 0
    total: int = 0
    item_key: str = ""
    details: dict[str, Any] = field(default_factory=dict)
