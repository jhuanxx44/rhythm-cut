"""Deterministic local media ingestion and ffprobe normalization."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from rhythm_cut.domain.models import AssetManifest


class IngestError(RuntimeError):
    """Raised when a media asset cannot be hashed or probed."""


@dataclass(frozen=True)
class MediaProbe:
    """Normalized media metadata; time values are seconds and fps is frames/second."""

    asset_id: str
    path: Path
    sha256: str
    duration_s: float
    fps: float | None
    frame_count: int | None
    streams: tuple[str, ...]

    def video_manifest(self) -> AssetManifest:
        """Return an AssetManifest for assets containing a video stream."""

        if self.fps is None or self.frame_count is None:
            raise IngestError("asset has no video stream; a video manifest is unavailable")
        return AssetManifest(
            asset_id=self.asset_id,
            sha256=self.sha256,
            duration_s=self.duration_s,
            fps=self.fps,
            frame_count=self.frame_count,
        )


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(chunk_size), b""):
                digest.update(chunk)
    except OSError as exc:
        raise IngestError(f"cannot read media asset {path}: {exc}") from exc
    return digest.hexdigest()


def _parse_ratio(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        numerator, denominator = value.split("/", 1)
        result = float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        return None
    return result if result > 0 else None


def probe_asset(
    path: Path,
    *,
    asset_id: str | None = None,
    ffprobe: str = "ffprobe",
    timeout_s: int = 30,
    runner: Runner = subprocess.run,
) -> MediaProbe:
    """Hash and probe one local media file using a fixed ffprobe invocation."""

    path = path.expanduser().resolve()
    if not path.is_file():
        raise IngestError(f"media asset does not exist: {path}")
    command: Sequence[str] = (
        ffprobe,
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-print_format",
        "json",
        str(path),
    )
    try:
        result = runner(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise IngestError(f"ffprobe failed for {path}: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or "").strip()[:500]
        raise IngestError(f"ffprobe returned {result.returncode} for {path}: {detail}")
    try:
        payload = json.loads(result.stdout)
        streams = payload["streams"]
        duration_s = float(payload["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise IngestError(f"ffprobe returned invalid metadata for {path}") from exc
    if duration_s <= 0 or not isinstance(streams, list):
        raise IngestError(f"ffprobe returned non-positive duration or invalid streams for {path}")

    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    fps = _parse_ratio(video.get("avg_frame_rate") or video.get("r_frame_rate")) if video else None
    frame_count = None
    if video:
        raw_frames = video.get("nb_frames")
        if raw_frames not in (None, "N/A"):
            try:
                frame_count = int(raw_frames)
            except ValueError:
                frame_count = None
        if frame_count is None and fps is not None:
            frame_count = round(duration_s * fps)
    return MediaProbe(
        asset_id=asset_id or path.stem,
        path=path,
        sha256=_sha256(path),
        duration_s=duration_s,
        fps=fps,
        frame_count=frame_count,
        streams=tuple(sorted({str(item.get("codec_type")) for item in streams})),
    )
