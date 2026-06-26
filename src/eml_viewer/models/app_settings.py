from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    """프로그램 창 위치와 크기를 저장하는 데이터입니다."""

    window_x: int = 100
    window_y: int = 100
    window_width: int = 1100
    window_height: int = 760
    language: str = "ko"
    theme: str = "system"

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        language = str(data.get("language", cls.language))
        if language not in {"ko", "en"}:
            language = cls.language

        theme = str(data.get("theme", cls.theme))
        if theme not in {"system", "light", "dark"}:
            theme = cls.theme

        return cls(
            window_x=int(data.get("window_x", cls.window_x)),
            window_y=int(data.get("window_y", cls.window_y)),
            window_width=int(data.get("window_width", cls.window_width)),
            window_height=int(data.get("window_height", cls.window_height)),
            language=language,
            theme=theme,
        )

    def to_dict(self) -> dict[str, int | str]:
        return {
            "window_x": self.window_x,
            "window_y": self.window_y,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "language": self.language,
            "theme": self.theme,
        }
