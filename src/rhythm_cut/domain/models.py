"""Stable, provider-neutral domain contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class EvidenceRef(BaseModel):
    """A pointer to the media evidence behind an observation."""

    asset_id: str
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    frame_start: int | None = Field(default=None, ge=0)
    frame_end: int | None = Field(default=None, ge=0)

    @field_validator("end_s")
    @classmethod
    def end_after_start(cls, value: float, info):
        start = info.data.get("start_s")
        if start is not None and value <= start:
            raise ValueError("end_s must be greater than start_s")
        return value


class AssetManifest(BaseModel):
    """Stable metadata for one local media asset."""

    asset_id: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    duration_s: float = Field(gt=0)
    fps: float = Field(gt=0)
    frame_count: int = Field(gt=0)

    @model_validator(mode="after")
    def frame_count_covers_duration(self) -> AssetManifest:
        expected_frames = self.duration_s * self.fps
        if self.frame_count < expected_frames:
            raise ValueError("frame_count must cover the asset duration at the declared fps")
        return self


class ClipObservation(BaseModel):
    """Normalized output from Gemini or another VLM provider."""

    schema_version: Literal["clip-observation-v1"] = "clip-observation-v1"
    asset_id: str
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    product_id: str | None = None
    color_id: str | None = None
    action_id: str | None = None
    garment_visibility: float = Field(ge=0, le=1)
    motion_energy: float = Field(ge=0, le=1)
    quality_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)

    @field_validator("end_s")
    @classmethod
    def end_after_start(cls, value: float, info):
        start = info.data.get("start_s")
        if start is not None and value <= start:
            raise ValueError("end_s must be greater than start_s")
        return value


class BeatPoint(BaseModel):
    """A candidate timeline cut anchor in seconds."""

    beat_id: int = Field(ge=0)
    time_s: float = Field(ge=0)
    strength: float = Field(ge=0, le=1)
    subdivision: Literal["bar", "beat", "half", "quarter"] = "beat"


class Shot(BaseModel):
    """One selected source range placed on the output timeline."""

    shot_id: str
    timeline_start_s: float = Field(ge=0)
    timeline_end_s: float = Field(gt=0)
    source_asset_id: str
    source_in_frame: int = Field(ge=0)
    source_out_frame: int = Field(gt=0)
    beat_id: int = Field(ge=0)
    color_id: str | None = None
    action_id: str | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)

    @field_validator("timeline_end_s")
    @classmethod
    def timeline_end_after_start(cls, value: float, info):
        start = info.data.get("timeline_start_s")
        if start is not None and value <= start:
            raise ValueError("timeline_end_s must be greater than timeline_start_s")
        return value

    @field_validator("source_out_frame")
    @classmethod
    def source_end_after_start(cls, value: int, info):
        start = info.data.get("source_in_frame")
        if start is not None and value <= start:
            raise ValueError("source_out_frame must be greater than source_in_frame")
        return value


class Relaxation(BaseModel):
    """An explicit record of a softened constraint."""

    constraint: str
    requested: str
    applied: str
    reason: str


class EditPlan(BaseModel):
    """Reproducible plan consumed by the renderer."""

    schema_version: Literal["edit-plan-v1"] = "edit-plan-v1"
    plan_id: str
    fps: int = Field(gt=0)
    duration_s: float = Field(gt=0)
    audio_asset_id: str
    shots: list[Shot] = Field(min_length=1)
    relaxations: list[Relaxation] = Field(default_factory=list)
    model: str | None = None
    prompt_version: str | None = None

    @model_validator(mode="after")
    def validate_global_shot_constraints(self) -> EditPlan:
        """Enforce timeline invariants that cannot be checked per shot."""

        seen_beats: set[int] = set()
        previous_end = 0.0
        for index, shot in enumerate(self.shots):
            if shot.timeline_end_s > self.duration_s:
                raise ValueError(f"shots[{index}] must end within duration_s")
            if shot.timeline_start_s < previous_end:
                raise ValueError("shots must be sorted and must not overlap")
            if shot.beat_id in seen_beats:
                raise ValueError(f"beat_id {shot.beat_id} may appear at most once")
            seen_beats.add(shot.beat_id)
            previous_end = shot.timeline_end_s
        return self
