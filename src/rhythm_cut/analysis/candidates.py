"""Deterministic fixed-window candidate extraction."""

from __future__ import annotations

from rhythm_cut.domain.candidates import CandidateClip


def fixed_windows(
    asset_id: str,
    *,
    duration_s: float,
    fps: float,
    window_s: float,
    step_s: float | None = None,
    min_duration_s: float = 0.18,
) -> tuple[CandidateClip, ...]:
    """Generate stable, frame-aligned windows that stay inside an asset."""

    if duration_s <= 0 or fps <= 0 or window_s <= 0 or min_duration_s <= 0:
        raise ValueError("duration_s, fps, window_s and min_duration_s must be positive")
    step_s = window_s if step_s is None else step_s
    if step_s <= 0:
        raise ValueError("step_s must be positive")
    total_frames = max(1, round(duration_s * fps))
    window_frames = max(1, round(window_s * fps))
    step_frames = max(1, round(step_s * fps))
    min_frames = max(1, round(min_duration_s * fps))

    candidates: list[CandidateClip] = []
    start_frame = 0
    index = 0
    while start_frame < total_frames:
        end_frame = min(total_frames, start_frame + window_frames)
        if end_frame - start_frame >= min_frames:
            candidates.append(
                CandidateClip(
                    candidate_id=f"{asset_id}-w{index:04d}",
                    asset_id=asset_id,
                    start_s=round(start_frame / fps, 9),
                    end_s=round(end_frame / fps, 9),
                    source_in_frame=start_frame,
                    source_out_frame=end_frame,
                )
            )
        index += 1
        start_frame += step_frames
    return tuple(candidates)
