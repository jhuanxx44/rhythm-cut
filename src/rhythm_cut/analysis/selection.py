"""Deterministic candidate selection for beat slots."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from rhythm_cut.domain.candidates import CandidateClip
from rhythm_cut.domain.models import BeatPoint, ClipObservation, EditPlan, Relaxation, Shot


@dataclass(frozen=True)
class ObservedCandidate:
    """A candidate window paired with its normalized visual observation."""

    candidate: CandidateClip
    observation: ClipObservation

    @property
    def candidate_id(self) -> str:
        return self.candidate.candidate_id


def _base_score(item: ObservedCandidate) -> float:
    observation = item.observation
    return (
        0.40 * observation.quality_score
        + 0.25 * observation.confidence
        + 0.20 * observation.garment_visibility
        + 0.15 * observation.motion_energy
    )


def _slot_ranges(beats: Sequence[BeatPoint], duration_s: float) -> list[tuple[BeatPoint, float, float]]:
    ordered = sorted(beats, key=lambda beat: (beat.time_s, beat.beat_id))
    ranges: list[tuple[BeatPoint, float, float]] = []
    for index, beat in enumerate(ordered):
        start = beat.time_s
        end = ordered[index + 1].time_s if index + 1 < len(ordered) else duration_s
        if start < duration_s and end > start:
            ranges.append((beat, start, min(end, duration_s)))
    return ranges


def _to_shot(item: ObservedCandidate, beat: BeatPoint, start_s: float, end_s: float) -> Shot:
    return Shot(
        shot_id=f"shot-{beat.beat_id:04d}",
        timeline_start_s=start_s,
        timeline_end_s=end_s,
        source_asset_id=item.candidate.asset_id,
        source_in_frame=item.candidate.source_in_frame,
        source_out_frame=item.candidate.source_out_frame,
        beat_id=beat.beat_id,
        color_id=item.observation.color_id,
        action_id=item.observation.action_id,
        evidence_refs=item.observation.evidence_refs,
    )


def select_edit_plan(
    candidates: Sequence[ObservedCandidate],
    beats: Sequence[BeatPoint],
    *,
    plan_id: str,
    fps: int,
    duration_s: float,
    audio_asset_id: str,
    color_quota: Mapping[str, int] | None = None,
    required_actions: set[str] | frozenset[str] = frozenset(),
    max_search_nodes: int = 256,
) -> EditPlan:
    """Select one candidate per feasible beat using bounded deterministic search.

    Hard constraints are legal windows, one candidate per beat, and no candidate reuse.
    Color quotas and action coverage are optimization goals; unmet goals are returned in
    ``EditPlan.relaxations`` instead of being silently ignored.
    """

    if not candidates:
        raise ValueError("at least one observed candidate is required")
    if max_search_nodes <= 0:
        raise ValueError("max_search_nodes must be positive")
    if duration_s <= 0 or fps <= 0:
        raise ValueError("duration_s and fps must be positive")
    quota = Counter(color_quota or {})
    if any(value < 0 for value in quota.values()):
        raise ValueError("color quota values must be non-negative")

    slots = _slot_ranges(beats, duration_s)
    by_slot: list[tuple[BeatPoint, float, float, tuple[ObservedCandidate, ...]]] = []
    for beat, start_s, end_s in slots:
        legal = tuple(
            sorted(
                (
                    item
                    for item in candidates
                    if item.candidate_id
                    and item.candidate.end_s - item.candidate.start_s >= end_s - start_s
                ),
                key=lambda item: (-_base_score(item), item.candidate_id),
            )
        )
        by_slot.append((beat, start_s, end_s, legal))

    # Candidate windows are source ranges; only their duration matters for fitting a slot.
    # The explicit source bounds are checked by CandidateClip itself.
    best: tuple[float, tuple[tuple[int, ObservedCandidate], ...]] = (-float("inf"), ())
    nodes = 0

    def objective(selected: list[tuple[int, ObservedCandidate]]) -> float:
        colors = Counter(item.observation.color_id for _, item in selected if item.observation.color_id)
        actions = {item.observation.action_id for _, item in selected if item.observation.action_id}
        score = sum(_base_score(item) for _, item in selected)
        score += sum(min(colors[color], count) * 0.50 for color, count in quota.items())
        score -= sum(max(0, colors[color] - count) * 0.35 for color, count in quota.items())
        score += len(actions & set(required_actions)) * 0.75
        score -= len({item.candidate.asset_id for _, item in selected}) * 0.02
        return score

    def search(index: int, used: set[str], selected: list[tuple[int, ObservedCandidate]]) -> None:
        nonlocal best, nodes
        if nodes >= max_search_nodes:
            return
        nodes += 1
        if index == len(by_slot):
            value = objective(selected)
            tie = tuple((slot_index, item) for slot_index, item in selected)
            if value > best[0] or (value == best[0] and tuple(x[1].candidate_id for x in tie) < tuple(x[1].candidate_id for x in best[1])):
                best = (value, tie)
            return
        _, _, _, legal = by_slot[index]
        for item in legal:
            if item.candidate_id in used:
                continue
            used.add(item.candidate_id)
            selected.append((index, item))
            search(index + 1, used, selected)
            selected.pop()
            used.remove(item.candidate_id)
        search(index + 1, used, selected)

    search(0, set(), [])
    chosen_by_slot = dict(best[1])
    shots = [
        _to_shot(item, beat, start_s, end_s)
        for index, (beat, start_s, end_s, _) in enumerate(by_slot)
        if (item := chosen_by_slot.get(index)) is not None
    ]
    selected_items = [item for _, item in best[1]]
    selected_colors = Counter(item.observation.color_id for item in selected_items if item.observation.color_id)
    selected_actions = {item.observation.action_id for item in selected_items if item.observation.action_id}
    relaxations: list[Relaxation] = []
    for beat, _, _, legal in by_slot:
        if not legal:
            relaxations.append(
                Relaxation(
                    constraint="beat_slot_coverage",
                    requested=f"beat_id={beat.beat_id}",
                    applied="skipped",
                    reason="no candidate window is long enough for the slot",
                )
            )
    for color, count in sorted(quota.items()):
        if selected_colors[color] < count:
            relaxations.append(
                Relaxation(
                    constraint="color_quota",
                    requested=f"{color}={count}",
                    applied=f"{color}={selected_colors[color]}",
                    reason="candidate supply or slot capacity was insufficient",
                )
            )
    for action in sorted(set(required_actions) - selected_actions):
        relaxations.append(
            Relaxation(
                constraint="action_coverage",
                requested=action,
                applied="missing",
                reason="no legal candidate with this action was selected",
            )
        )
    if not shots:
        raise ValueError("no feasible candidate can fill any beat slot")
    return EditPlan(
        plan_id=plan_id,
        fps=fps,
        duration_s=duration_s,
        audio_asset_id=audio_asset_id,
        shots=shots,
        relaxations=relaxations,
    )
