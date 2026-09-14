"""Beat grid generation with a deterministic fallback for offline planning."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rhythm_cut.domain.models import BeatPoint


class BeatAnalysisError(RuntimeError):
    """Raised when an audio beat analysis backend is unavailable or fails."""


@dataclass(frozen=True)
class BeatGrid:
    """Beat points and the estimated tempo used to produce them."""

    beats: tuple[BeatPoint, ...]
    tempo_bpm: float
    backend: str


def fixed_beat_grid(
    duration_s: float,
    *,
    tempo_bpm: float,
    start_s: float = 0.0,
    strength: float = 1.0,
) -> BeatGrid:
    """Create a stable beat grid without reading media; useful for fixtures."""

    if duration_s <= 0 or tempo_bpm <= 0:
        raise ValueError("duration_s and tempo_bpm must be positive")
    if not 0 <= strength <= 1:
        raise ValueError("strength must be between 0 and 1")
    interval_s = 60.0 / tempo_bpm
    points: list[BeatPoint] = []
    time_s = start_s
    beat_id = 0
    while time_s < duration_s:
        points.append(BeatPoint(beat_id=beat_id, time_s=round(time_s, 9), strength=strength))
        beat_id += 1
        time_s += interval_s
    return BeatGrid(beats=tuple(points), tempo_bpm=tempo_bpm, backend="fixed")


def analyze_audio(path: Path, *, sr: int | None = None, hop_length: int = 512) -> BeatGrid:
    """Estimate tempo and beats with librosa, imported only when this feature is used."""

    try:
        import librosa
    except ImportError as exc:
        raise BeatAnalysisError("librosa is required for analyze_audio; install rhythm-cut[analysis]") from exc
    try:
        signal, sample_rate = librosa.load(path, sr=sr, mono=True)
        tempo, beat_frames = librosa.beat.beat_track(y=signal, sr=sample_rate, hop_length=hop_length)
        onset = librosa.onset.onset_strength(y=signal, sr=sample_rate, hop_length=hop_length)
        times = librosa.frames_to_time(beat_frames, sr=sample_rate, hop_length=hop_length)
    except Exception as exc:
        raise BeatAnalysisError(f"librosa failed for {path}: {exc}") from exc
    tempo_value = float(tempo[0] if hasattr(tempo, "__len__") else tempo)
    peak = float(onset.max()) if len(onset) else 0.0
    points = tuple(
        BeatPoint(
            beat_id=index,
            time_s=float(time_s),
            strength=min(1.0, float(onset[frame]) / peak) if peak and frame < len(onset) else 0.0,
        )
        for index, (time_s, frame) in enumerate(zip(times, beat_frames, strict=False))
    )
    return BeatGrid(beats=points, tempo_bpm=tempo_value, backend="librosa")
