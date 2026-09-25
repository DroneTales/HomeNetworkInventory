import json
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
DEFAULT_LANG = "en"
SUPPORTED_LANGS = ["en", "ru"]

_translations: dict[str, dict[str, str]] = {}

def load_translations() -> None:
    _translations.clear()
    for lang in SUPPORTED_LANGS:
        path = LOCALES_DIR / f"{lang}.json"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as f:
            _translations[lang] = json.load(f)

def detect_language(accept_language: str | None) -> str:
    if not accept_language:
        return DEFAULT_LANG

    for chunk in accept_language.split(","):
        code = chunk.split(";")[0].strip().lower()
        short = code.split("-")[0]
        if short in SUPPORTED_LANGS:
            return short
    return DEFAULT_LANG

def translate(key: str, lang: str) -> str:
    lang = lang if lang in _translations else DEFAULT_LANG
    return _translations.get(lang, {}).get(key, key)
