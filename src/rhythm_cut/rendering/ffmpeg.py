"""Controlled FFmpeg rendering for validated edit plans."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from rhythm_cut.domain.models import EditPlan


class RenderError(RuntimeError):
    """Raised when a render cannot be prepared or completed."""


@dataclass(frozen=True)
class RenderResult:
    """Auditable result of one FFmpeg invocation."""

    output_path: Path
    manifest_path: Path
    argv: tuple[str, ...]
    duration_s: float
    shot_count: int


Runner = Callable[..., subprocess.CompletedProcess[str]]


def build_ffmpeg_argv(
    plan: EditPlan,
    *,
    assets: Mapping[str, Path],
    audio_path: Path,
    output_path: Path,
    asset_fps: Mapping[str, float] | None = None,
    ffmpeg: str = "ffmpeg",
    video_codec: str = "libx264",
    audio_codec: str = "aac",
) -> list[str]:
    """Build a fixed-structure FFmpeg argument list from an EditPlan."""

    if not plan.shots:
        raise RenderError("cannot render an EditPlan without shots")
    if not audio_path.is_file():
        raise RenderError(f"audio asset does not exist: {audio_path}")
    for shot in plan.shots:
        source = assets.get(shot.source_asset_id)
        if source is None:
            raise RenderError(f"missing source asset mapping: {shot.source_asset_id}")
        if not source.is_file():
            raise RenderError(f"source asset does not exist: {source}")

    fps_by_asset = asset_fps or {}
    argv = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for shot in plan.shots:
        argv.extend(["-i", str(assets[shot.source_asset_id])])
    audio_index = len(plan.shots)
    argv.extend(["-i", str(audio_path)])

    filters: list[str] = []
    labels: list[str] = []
    for index, shot in enumerate(plan.shots):
        source_fps = fps_by_asset.get(shot.source_asset_id, float(plan.fps))
        if source_fps <= 0:
            raise RenderError(f"asset fps must be positive: {shot.source_asset_id}")
        slot_duration = shot.timeline_end_s - shot.timeline_start_s
        requested_frames = max(1, round(slot_duration * source_fps))
        end_frame = min(shot.source_out_frame, shot.source_in_frame + requested_frames)
        if end_frame <= shot.source_in_frame:
            raise RenderError(f"shot has no renderable source frames: {shot.shot_id}")
        label = f"v{index}"
        filters.append(
            f"[{index}:v]trim=start_frame={shot.source_in_frame}:end_frame={end_frame},"
            f"setpts=PTS-STARTPTS[{label}]"
        )
        labels.append(f"[{label}]")
    filters.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[vout]")

    argv.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[vout]",
            "-map",
            f"{audio_index}:a:0?",
            "-t",
            f"{plan.duration_s:.9f}",
            "-r",
            str(plan.fps),
            "-c:v",
            video_codec,
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            audio_codec,
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    return argv


def render_edit_plan(
    plan: EditPlan,
    *,
    assets: Mapping[str, Path],
    audio_path: Path,
    output_path: Path,
    asset_fps: Mapping[str, float] | None = None,
    ffmpeg: str = "ffmpeg",
    video_codec: str = "libx264",
    audio_codec: str = "aac",
    runner: Runner = subprocess.run,
) -> RenderResult:
    """Render an EditPlan and write a JSON manifest next to the output."""

    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    argv = build_ffmpeg_argv(
        plan,
        assets=assets,
        audio_path=audio_path,
        output_path=output_path,
        asset_fps=asset_fps,
        ffmpeg=ffmpeg,
        video_codec=video_codec,
        audio_codec=audio_codec,
    )
    try:
        result = runner(argv, check=False, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RenderError(f"FFmpeg failed to start or timed out: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or "").strip()[-1000:]
        raise RenderError(f"FFmpeg returned {result.returncode}: {detail}")
    if not output_path.is_file():
        raise RenderError(f"FFmpeg reported success but output is missing: {output_path}")

    manifest_path = output_path.with_suffix(".render.json")
    manifest_path.write_text(
        json.dumps(
            {
                "plan_id": plan.plan_id,
                "schema_version": plan.schema_version,
                "output_path": str(output_path),
                "duration_s": plan.duration_s,
                "fps": plan.fps,
                "shot_count": len(plan.shots),
                "argv": argv,
                "relaxations": [item.model_dump() for item in plan.relaxations],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    return RenderResult(
        output_path=output_path,
        manifest_path=manifest_path,
        argv=tuple(argv),
        duration_s=plan.duration_s,
        shot_count=len(plan.shots),
    )
