import json
import subprocess
from pathlib import Path

import pytest

from rhythm_cut.domain.models import EditPlan, Shot
from rhythm_cut.rendering.ffmpeg import RenderError, build_ffmpeg_argv, render_edit_plan


def plan() -> EditPlan:
    return EditPlan(
        plan_id="render-p1",
        fps=30,
        duration_s=1.0,
        audio_asset_id="music",
        shots=[
            Shot(
                shot_id="s1",
                timeline_start_s=0.0,
                timeline_end_s=1.0,
                source_asset_id="asset-1",
                source_in_frame=3,
                source_out_frame=33,
                beat_id=0,
            )
        ],
    )


def test_build_ffmpeg_argv_contains_only_controlled_render_arguments(tmp_path: Path):
    source = tmp_path / "source.mp4"
    audio = tmp_path / "music.wav"
    source.touch()
    audio.touch()
    argv = build_ffmpeg_argv(
        plan(),
        assets={"asset-1": source},
        audio_path=audio,
        output_path=tmp_path / "out.mp4",
    )
    assert argv[0] == "ffmpeg"
    assert "-filter_complex" in argv
    assert "start_frame=3:end_frame=33" in argv[argv.index("-filter_complex") + 1]
    assert "out.mp4" in argv[-1]


def test_render_edit_plan_writes_manifest(tmp_path: Path):
    source = tmp_path / "source.mp4"
    audio = tmp_path / "music.wav"
    output = tmp_path / "out.mp4"
    source.touch()
    audio.touch()

    def fake_runner(argv, **kwargs):
        Path(argv[-1]).write_bytes(b"rendered")
        return subprocess.CompletedProcess(argv, 0, "", "")

    result = render_edit_plan(
        plan(),
        assets={"asset-1": source},
        audio_path=audio,
        output_path=output,
        runner=fake_runner,
    )
    manifest = json.loads(result.manifest_path.read_text())
    assert manifest["plan_id"] == "render-p1"
    assert manifest["shot_count"] == 1
    assert output.read_bytes() == b"rendered"


def test_render_edit_plan_reports_missing_asset(tmp_path: Path):
    audio = tmp_path / "music.wav"
    audio.touch()
    with pytest.raises(RenderError, match="missing source asset mapping"):
        render_edit_plan(
            plan(),
            assets={},
            audio_path=audio,
            output_path=tmp_path / "out.mp4",
        )
