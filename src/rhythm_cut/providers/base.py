"""Provider interfaces. Concrete SDKs must stay behind this boundary."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from rhythm_cut.domain.models import ClipObservation


@dataclass(frozen=True)
class VideoWindow:
    asset_id: str
    path: str
    start_s: float
    end_s: float
    sample_fps: float


class VisionProvider(Protocol):
    """Analyze one short video window and return normalized observations."""

    name: str
    model: str

    def analyze(self, window: VideoWindow, *, prompt_version: str) -> Sequence[ClipObservation]:
        ...
