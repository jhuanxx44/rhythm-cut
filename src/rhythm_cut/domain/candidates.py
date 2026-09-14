"""Provider-neutral candidate clip contract."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class CandidateClip(BaseModel):
    """A legal source window available to the selector."""

    candidate_id: str
    asset_id: str
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    source_in_frame: int = Field(ge=0)
    source_out_frame: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_range(self) -> CandidateClip:
        if self.end_s <= self.start_s:
            raise ValueError("end_s must be greater than start_s")
        if self.source_out_frame <= self.source_in_frame:
            raise ValueError("source_out_frame must be greater than source_in_frame")
        return self
