from rhythm_cut.analysis.selection import ObservedCandidate, select_edit_plan
from rhythm_cut.domain.candidates import CandidateClip
from rhythm_cut.domain.models import BeatPoint, ClipObservation


def observed(candidate_id: str, color: str, action: str, quality: float, asset: str = "a1"):
    candidate = CandidateClip(
        candidate_id=candidate_id,
        asset_id=asset,
        start_s=0.0,
        end_s=1.0,
        source_in_frame=0,
        source_out_frame=30,
    )
    return ObservedCandidate(
        candidate=candidate,
        observation=ClipObservation(
            asset_id=asset,
            start_s=0.0,
            end_s=1.0,
            color_id=color,
            action_id=action,
            garment_visibility=1.0,
            motion_energy=0.5,
            quality_score=quality,
            confidence=1.0,
        ),
    )


def test_selector_prefers_quota_and_action_coverage_deterministically():
    plan = select_edit_plan(
        [
            observed("c1", "red", "A", 0.95),
            observed("c2", "blue", "B", 0.80, asset="a2"),
            observed("c3", "red", "B", 0.70, asset="a3"),
        ],
        [BeatPoint(beat_id=0, time_s=0.0, strength=1.0), BeatPoint(beat_id=1, time_s=1.0, strength=1.0)],
        plan_id="p1",
        fps=30,
        duration_s=2.0,
        audio_asset_id="music",
        color_quota={"red": 1, "blue": 1},
        required_actions={"A", "B"},
    )
    assert [shot.color_id for shot in plan.shots] == ["red", "blue"]
    assert plan.relaxations == []


def test_selector_reports_unmet_constraints_and_skips_empty_slots():
    plan = select_edit_plan(
        [observed("c1", "red", "A", 0.9)],
        [
            BeatPoint(beat_id=0, time_s=0.0, strength=1.0),
            BeatPoint(beat_id=1, time_s=1.5, strength=1.0),
        ],
        plan_id="p2",
        fps=30,
        duration_s=2.0,
        audio_asset_id="music",
        color_quota={"blue": 1},
        required_actions={"B"},
    )
    assert len(plan.shots) == 1
    assert {item.constraint for item in plan.relaxations} == {
        "beat_slot_coverage",
        "color_quota",
        "action_coverage",
    }
