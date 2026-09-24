import json
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
DEFAULT_LANG = "en"
SUPPORTED_LANGS = ["en", "ru"]

_translations: dict[str, dict[str, str]] = {}


def load_translations() -> None:
    """Загружает все JSON-файлы переводов в память при старте."""
    _translations.clear()
    for lang in SUPPORTED_LANGS:
        path = LOCALES_DIR / f"{lang}.json"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as f:
            _translations[lang] = json.load(f)


def detect_language(accept_language: str | None) -> str:
    """Определяет язык по заголовку Accept-Language браузера.

    Возвращает первый поддерживаемый язык из списка предпочтений,
    либо DEFAULT_LANG, если ничего не подошло.
    """
    if not accept_language:
        return DEFAULT_LANG

    # Пример: "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    for chunk in accept_language.split(","):
        code = chunk.split(";")[0].strip().lower()
        # ru-RU -> ru
        short = code.split("-")[0]
        if short in SUPPORTED_LANGS:
            return short
    return DEFAULT_LANG


def translate(key: str, lang: str) -> str:
    """Возвращает перевод ключа для языка. Если ключа нет — возвращает сам ключ."""
    lang = lang if lang in _translations else DEFAULT_LANG
    return _translations.get(lang, {}).get(key, key)

