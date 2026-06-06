from __future__ import annotations

from dataclasses import dataclass

from eml_viewer.models.email_data import ParsedEmail


@dataclass(frozen=True)
class AIAnalysisResult:
    summary: str
    keywords: list[str]
    suggested_tags: list[str]


class AIAnalysisService:
    """향후 AI 요약, 키워드 추출, 자동 태그 추천을 붙일 자리입니다."""

    def analyze(self, email: ParsedEmail) -> AIAnalysisResult:
        raise NotImplementedError("AI 분석 기능은 MVP 이후에 구현합니다.")
