import json
import subprocess
import wave
from pathlib import Path

import pytest

from rhythm_cut.analysis.beats import BeatAnalysisError, analyze_audio, fixed_beat_grid
from rhythm_cut.analysis.ingest import IngestError, probe_asset


def _completed(payload: dict, returncode: int = 0, stderr: str = ""):
    return subprocess.CompletedProcess(args=["ffprobe"], returncode=returncode,
                                       stdout=json.dumps(payload), stderr=stderr)


def test_probe_asset_hashes_and_normalizes_video_metadata(tmp_path: Path):
    media = tmp_path / "look.mp4"
    media.write_bytes(b"fixture-media")
    payload = {
        "format": {"duration": "2.0"},
        "streams": [
            {"codec_type": "video", "avg_frame_rate": "30/1", "nb_frames": "60"},
            {"codec_type": "audio"},
        ],
    }
    probe = probe_asset(media, asset_id="look-001", runner=lambda *args, **kwargs: _completed(payload))
    assert probe.asset_id == "look-001"
    assert probe.sha256 == "dac1fed13aa242918137de32273ba0b85544a6cf762c16d8fea8d5a3085b8f19"
    assert probe.streams == ("audio", "video")
    assert probe.video_manifest().frame_count == 60


def test_probe_asset_reports_ffprobe_failure(tmp_path: Path):
    media = tmp_path / "broken.mp4"
    media.write_bytes(b"broken")
    with pytest.raises(IngestError, match="ffprobe returned 1"):
        probe_asset(media, runner=lambda *args, **kwargs: _completed({}, 1, "invalid data"))


def test_fixed_beat_grid_is_stable_and_frame_independent():
    grid = fixed_beat_grid(2.1, tempo_bpm=120)
    assert [point.time_s for point in grid.beats] == [0.0, 0.5, 1.0, 1.5, 2.0]
    assert grid.backend == "fixed"


def test_probe_asset_uses_real_ffprobe_for_audio(tmp_path: Path):
    media = tmp_path / "tone.wav"
    with wave.open(str(media), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\0\0" * 800)
    probe = probe_asset(media)
    assert probe.duration_s == pytest.approx(0.1, abs=0.01)
    assert probe.streams == ("audio",)
    with pytest.raises(IngestError, match="no video stream"):
        probe.video_manifest()


def test_analyze_audio_reports_optional_dependency_boundary(tmp_path: Path):
    with pytest.raises(BeatAnalysisError, match="librosa is required"):
        analyze_audio(tmp_path / "missing.wav")
