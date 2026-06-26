from __future__ import annotations

_current_language = "ko"

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "ko": {
        "settings.title": "설정",
        "settings.language": "언어",
        "settings.theme": "테마",
        "settings.restart_required": "언어 변경은 프로그램을 다시 시작한 뒤 적용됩니다.",
        "settings.saved": "설정을 저장했습니다.",
        "settings.ok": "확인",
        "settings.cancel": "취소",
        "language.ko": "한국어",
        "language.en": "English",
        "theme.system": "시스템",
        "theme.light": "라이트",
        "theme.dark": "다크",
    },
    "en": {
        "settings.title": "Settings",
        "settings.language": "Language",
        "settings.theme": "Theme",
        "settings.restart_required": "Language changes are applied after restarting the app.",
        "settings.saved": "Settings saved.",
        "settings.ok": "OK",
        "settings.cancel": "Cancel",
        "language.ko": "Korean",
        "language.en": "English",
        "theme.system": "System",
        "theme.light": "Light",
        "theme.dark": "Dark",
    },
}


def set_language(language: str) -> None:
    global _current_language
    _current_language = language if language in _TRANSLATIONS else "ko"


def tr(key: str) -> str:
    return _TRANSLATIONS.get(_current_language, _TRANSLATIONS["ko"]).get(
        key,
        _TRANSLATIONS["ko"].get(key, key),
    )
