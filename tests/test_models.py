from pathlib import Path

import pytest

from rhythm_cut.domain.models import AssetManifest, ClipObservation, EditPlan, EvidenceRef, Shot

FIXTURES = Path(__file__).parent / "fixtures"


def test_clip_observation_keeps_evidence_and_bounds():
    item = ClipObservation(
        asset_id="a1",
        start_s=1.0,
        end_s=2.0,
        color_id="red",
        action_id="C",
        garment_visibility=0.9,
        motion_energy=0.7,
        quality_score=0.8,
        confidence=0.85,
        evidence_refs=[EvidenceRef(asset_id="a1", start_s=1.0, end_s=2.0)],
    )
    assert item.evidence_refs[0].asset_id == "a1"


def test_edit_plan_round_trip():
    plan = EditPlan(
        plan_id="p1",
        fps=30,
        duration_s=1.0,
        audio_asset_id="music",
        shots=[
            Shot(
                shot_id="s1",
                timeline_start_s=0.0,
                timeline_end_s=1.0,
                source_asset_id="a1",
                source_in_frame=30,
                source_out_frame=60,
                beat_id=0,
                color_id="red",
                action_id="A",
            )
        ],
    )
    assert EditPlan.model_validate_json(plan.model_dump_json()).plan_id == "p1"


def test_edit_plan_rejects_out_of_bounds_shot():
    with pytest.raises(ValueError, match="within duration_s"):
        EditPlan(
            plan_id="p1",
            fps=30,
            duration_s=1.0,
            audio_asset_id="music",
            shots=[
                Shot(
                    shot_id="s1",
                    timeline_start_s=0.0,
                    timeline_end_s=1.1,
                    source_asset_id="a1",
                    source_in_frame=0,
                    source_out_frame=1,
                    beat_id=0,
                )
            ],
        )


def test_edit_plan_rejects_overlap_and_duplicate_beat():
    base = {
        "plan_id": "p1",
        "fps": 30,
        "duration_s": 2.0,
        "audio_asset_id": "music",
    }
    shot = {
        "source_asset_id": "a1",
        "source_in_frame": 0,
        "source_out_frame": 1,
    }
    with pytest.raises(ValueError, match="must not overlap"):
        EditPlan(
            **base,
            shots=[
                Shot(shot_id="s1", timeline_start_s=0.0, timeline_end_s=1.0, beat_id=0, **shot),
                Shot(shot_id="s2", timeline_start_s=0.5, timeline_end_s=1.5, beat_id=1, **shot),
            ],
        )
    with pytest.raises(ValueError, match="at most once"):
        EditPlan(
            **base,
            shots=[
                Shot(shot_id="s1", timeline_start_s=0.0, timeline_end_s=1.0, beat_id=0, **shot),
                Shot(shot_id="s2", timeline_start_s=1.0, timeline_end_s=2.0, beat_id=0, **shot),
            ],
        )


def test_asset_manifest_uses_explicit_frame_semantics():
    asset = AssetManifest(
        asset_id="a1",
        sha256="0" * 64,
        duration_s=2.0,
        fps=30.0,
        frame_count=60,
    )
    assert asset.frame_count == 60
    with pytest.raises(ValueError, match="frame_count must cover"):
        AssetManifest(
            asset_id="a1",
            sha256="0" * 64,
            duration_s=2.01,
            fps=30.0,
            frame_count=60,
        )


def test_json_fixtures_cover_valid_and_invalid_plans():
    valid = EditPlan.model_validate_json((FIXTURES / "edit_plan_valid.json").read_text())
    assert valid.plan_id == "fixture-valid-001"
    with pytest.raises(ValueError, match="within duration_s"):
        EditPlan.model_validate_json(
            (FIXTURES / "edit_plan_invalid_out_of_bounds.json").read_text()
        )
