from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

LOCALES_DIR = Path(__file__).resolve().parent / "locales"

_translations: dict[str, dict[str, str]] = {}
_current_language = "ko"


def _load_locales() -> None:
    global _translations
    if _translations:
        return

    if not LOCALES_DIR.exists():
        logger.error(f"Locales directory does not exist: {LOCALES_DIR}")
        return

    for path in LOCALES_DIR.glob("*.json"):
        lang = path.stem
        try:
            with open(path, "r", encoding="utf-8") as f:
                _translations[lang] = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load locale file {path}: {e}")


def set_language(language: str) -> None:
    global _current_language
    _load_locales()
    if language in _translations:
        _current_language = language
    else:
        # fallback to Korean ("ko") when language is unsupported
        _current_language = "ko"


def current_language() -> str:
    return _current_language


def tr(key: str, **kwargs: object) -> str:
    _load_locales()

    lang = _current_language if _current_language in _translations else "ko"
    lang_translations = _translations.get(lang, {})
    ko_translations = _translations.get("ko", {})

    # Retrieve translation text:
    # 1. Active language key
    # 2. Korean fallback key
    # 3. Fallback to key itself
    text = lang_translations.get(key, ko_translations.get(key, key))

    if not kwargs:
        return text

    try:
        return text.format(**kwargs)
    except (KeyError, ValueError, IndexError, TypeError) as e:
        # Safe fallback behavior: log warning and return unformatted text
        logger.warning(
            f"Formatting translation failed for key '{key}' with text '{text}' and args {kwargs}: {e}"
        )
        return text
