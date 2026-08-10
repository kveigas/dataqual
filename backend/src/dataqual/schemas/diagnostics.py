from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

QualityFlagType = Literal[
    "probable_quality_defect",
    "probable_ambiguity_policy_issue",
    "mixed_evidence",
    "insufficient_evidence",
    "no_flag",
]

QualityFlagSeverity = Literal["info", "low", "medium", "high"]

RecommendedAction = Literal[
    "review_annotation",
    "review_label",
    "clarify_policy",
    "collect_more_labels",
    "inspect_overlap",
    "no_action",
]


class ItemDisagreementFeatures(BaseModel):
    item_id: str
    annotation_count: int
    vote_counts: dict[str, int]
    vote_proportions: dict[str, float]
    vote_entropy: float
    normalized_entropy: float | None
    vote_margin: float
    mv_status: str
    mv_label: str | None
    ds_status: str
    ds_probabilities: dict[str, float] | None = None
    ds_max_posterior: float | None = None
    ds_entropy: float | None = None
    method_disagreement: bool
    distinct_labels_count: int
    gold_status: str | None = None
    dissenting_worker_ids: list[str] = Field(default_factory=list)
    dissenting_worker_gold_reliabilities: dict[str, float | None] = Field(default_factory=dict)
    dissenting_worker_reliability_states: dict[str, str] = Field(default_factory=dict)


class QualityFlag(BaseModel):
    schema_version: str = "4.0.0"
    quality_flag_id: str
    dataset_snapshot_id: str
    project_id: str
    entity_type: Literal["item", "annotation", "dataset"]
    entity_id: str
    flag_type: QualityFlagType
    severity: QualityFlagSeverity
    evidence: dict[str, Any]
    support_n: int
    method: str = "dataqual_disagreement_diagnostic_v1"
    threshold_config_version: str = "1.0.0"
    threshold_config_hash: str
    thresholds_used: dict[str, Any]
    uncertainty: dict[str, Any] | None = None
    recommended_action: RecommendedAction
    status: Literal["active", "resolved", "superseded"] = "active"
    created_at: str
    explanation: str


class DiagnosticSummary(BaseModel):
    total_items: int
    items_with_flags: int
    flag_counts: dict[QualityFlagType, int]
    severity_counts: dict[QualityFlagSeverity, int]
    entity_type_counts: dict[str, int]
