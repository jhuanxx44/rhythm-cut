from rhythm_cut.domain.models import ClipObservation, EditPlan, EvidenceRef, Shot


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
