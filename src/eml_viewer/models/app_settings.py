from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    """프로그램 창 위치와 크기를 저장하는 데이터입니다."""

    window_x: int = 100
    window_y: int = 100
    window_width: int = 1100
    window_height: int = 760

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        return cls(
            window_x=int(data.get("window_x", cls.window_x)),
            window_y=int(data.get("window_y", cls.window_y)),
            window_width=int(data.get("window_width", cls.window_width)),
            window_height=int(data.get("window_height", cls.window_height)),
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "window_x": self.window_x,
            "window_y": self.window_y,
            "window_width": self.window_width,
            "window_height": self.window_height,
        }
