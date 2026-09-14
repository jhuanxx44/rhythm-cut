"""Gemini provider boundary and normalized vision adapter."""

from __future__ import annotations

from collections.abc import Sequence

from rhythm_cut.domain.models import ClipObservation
from rhythm_cut.providers.base import VideoWindow
from rhythm_cut.providers.gemini_client import GeminiClient, GeminiError, GeminiResponse

__all__ = ["GeminiClient", "GeminiError", "GeminiResponse", "GeminiVisionProvider"]


class GeminiVisionProvider:
    """Future Gemini implementation with a strict normalized return contract."""

    name = "gemini"

    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self.model = model

    def analyze(self, window: VideoWindow, *, prompt_version: str) -> Sequence[ClipObservation]:
        raise NotImplementedError(
            "Live Gemini calls are not wired yet; add a recorded-response fixture first."
        )
