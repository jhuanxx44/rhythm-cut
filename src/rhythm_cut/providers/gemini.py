"""Gemini adapter placeholder; live calls are intentionally not part of the skeleton."""

from __future__ import annotations

from collections.abc import Sequence

from rhythm_cut.domain.models import ClipObservation
from rhythm_cut.providers.base import VideoWindow


class GeminiVisionProvider:
    """Future Gemini implementation with a strict normalized return contract."""

    name = "gemini"

    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self.model = model

    def analyze(self, window: VideoWindow, *, prompt_version: str) -> Sequence[ClipObservation]:
        raise NotImplementedError(
            "Live Gemini calls are not wired yet; add a recorded-response fixture first."
        )
