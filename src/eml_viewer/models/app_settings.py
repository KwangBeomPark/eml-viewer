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
    smtp_host: str = ""
    smtp_sender: str = ""
    smtp_port: int = 25

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
            smtp_host=str(data.get("smtp_host", cls.smtp_host)).strip(),
            smtp_sender=str(data.get("smtp_sender", cls.smtp_sender)).strip(),
            smtp_port=cls._safe_port(data.get("smtp_port", cls.smtp_port)),
        )

    def to_dict(self) -> dict[str, int | str]:
        return {
            "window_x": self.window_x,
            "window_y": self.window_y,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "language": self.language,
            "theme": self.theme,
            "smtp_host": self.smtp_host,
            "smtp_sender": self.smtp_sender,
            "smtp_port": self.smtp_port,
        }

    @staticmethod
    def _safe_port(value: object) -> int:
        try:
            port = int(value)
        except (TypeError, ValueError):
            return AppSettings.smtp_port
        return port if 1 <= port <= 65535 else AppSettings.smtp_port
