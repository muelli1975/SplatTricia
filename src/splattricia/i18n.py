from __future__ import annotations

import json
from importlib import resources
from typing import Any


SUPPORTED_LOCALES = ("de", "en")


class Translator:
    def __init__(self, locale: str = "de") -> None:
        self._cache: dict[str, dict[str, str]] = {}
        self.locale = locale if locale in SUPPORTED_LOCALES else "de"

    def _load(self, locale: str) -> dict[str, str]:
        if locale in self._cache:
            return self._cache[locale]
        try:
            resource = resources.files("splattricia").joinpath(
                "locales", f"{locale}.json"
            )
            data = json.loads(resource.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        self._cache[locale] = data
        return data

    def tr(self, key: str, **values: Any) -> str:
        active = self._load(self.locale)
        fallback = self._load("de")
        template = active.get(key, fallback.get(key, key))
        try:
            return template.format(**values)
        except (KeyError, ValueError):
            return template
