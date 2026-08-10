from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field

ReviewUnit = Literal["annotation", "item"]

PrioritizationMethod = Literal[
    "random",
    "highest_entropy",
    "lowest_consensus_confidence",
    "lowest_worker_reliability",
    "ds_worker_error",
    "erv",
]


class ErvScoreComponents(BaseModel):
    u_i: float = Field(..., description="Dawid-Skene uncertainty: 1 - max(q_i)")
    h_i: float = Field(..., description="Normalized vote entropy: H / ln(K)")
    e_i: float = Field(..., description="Mean worker error exposure from gold Beta posteriors")
    raw_score: float = Field(..., description="0.60*u_i + 0.20*h_i + 0.20*e_i")


class ReviewCandidate(BaseModel):
    candidate_id: str
    review_unit: ReviewUnit
    item_id: str
    annotation_id: str | None = None
    annotator_id: str | None = None
    submitted_label: str | None = None
    prioritization_method: PrioritizationMethod
    score: float
    score_components: ErvScoreComponents | dict[str, float]
    rank: int
    eligible_coverage: bool = True
    contextual_evidence: dict[str, Any] = Field(default_factory=dict)
    provenance_reference: str = "dataqual_review_prioritization_v1"


class ErvConfig(BaseModel):
    version: str = "1.0.0"
    weight_uncert: float = 0.60
    weight_entropy: float = 0.20
    weight_worker_error: float = 0.20
    default_cost: float = 1.0

    def config_hash(self) -> str:
        serialized = json.dumps(self.model_dump(), sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
