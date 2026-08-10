from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from dataqual.schemas.core import SCHEMA_VERSION


class ResultStatus(StrEnum):
    SUCCESS = "success"
    UNRESOLVED = "unresolved"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    ASSUMPTION_VIOLATION = "assumption_violation"
    NON_CONVERGED = "non_converged"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class EvidenceLevel(StrEnum):
    MINIMAL = "minimal"
    LIMITED = "limited"
    ADEQUATE = "adequate"
    STRONG = "strong"


class AnalysisProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    analysis_run_id: str
    dataset_id: str
    dataset_snapshot_id: str
    canonical_artifact_checksum: str
    method_identifier: str
    method_version: str
    configuration_hash: str
    computed_at: str
    software_version: str
    git_commit: str | None
    git_dirty: bool | None


class ConfidenceInterval(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    estimate: float
    lower: float
    upper: float
    confidence_level: float
    replicates: int
    valid_replicates: int
    failed_replicates: int
    seed: int
    method: Literal["percentile"] = "percentile"
    resampling_unit: Literal["item"] = "item"
    population: str


class StatisticalResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["4.0.0"] = SCHEMA_VERSION
    metric_name: str
    value: Any = None
    status: ResultStatus
    evidence_level: EvidenceLevel
    support: dict[str, int | float | str]
    uncertainty: ConfidenceInterval | None = None
    method_identifier: str
    method_version: str
    configuration: dict[str, Any]
    configuration_hash: str
    provenance: AnalysisProvenance
    warnings: list[str] = Field(default_factory=list)
    failure_reason: str | None = None


class EvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["4.0.0"] = SCHEMA_VERSION
    dataset_id: str
    analysis_run_id: str
    annotation_event_count: int
    all_annotation_event_count: int
    superseded_annotation_event_count: int
    unique_item_count: int
    unique_annotator_count: int
    class_count: int
    gold_item_count: int
    gold_coverage_fraction: float
    mean_annotations_per_item: float
    median_annotations_per_item: float
    min_annotations_per_item: int
    max_annotations_per_item: int
    mean_annotations_per_annotator: float
    median_annotations_per_annotator: float
    coannotated_item_count: int
    coannotated_item_fraction: float
    items_with_1_annotation: int
    items_with_2_annotations: int
    items_with_3plus_annotations: int
    class_counts: dict[str, int]
    class_proportions: dict[str, float]
    labels_per_item_distribution: dict[str, int]
    labels_per_annotator_distribution: dict[str, int]
    evidence_level: EvidenceLevel
    provenance: AnalysisProvenance


class PairwiseAgreement(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    annotator_a: str
    annotator_b: str
    shared_item_count: int
    agreements: int
    disagreements: int
    raw_percent_agreement: float | None
    status: ResultStatus
    evidence_level: EvidenceLevel
    uncertainty: ConfidenceInterval | None = None
    warnings: list[str] = Field(default_factory=list)


class OverlapSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    worker_item_overlap_counts: dict[str, dict[str, int]]
    graph_node_count: int
    graph_edge_count: int
    connected_component_count: int
    largest_component_size: int
    isolated_workers: list[str]
    isolated_items: list[str]
    worker_degrees: dict[str, int]
    worker_shared_item_totals: dict[str, int]
    pairwise: list[PairwiseAgreement]


class AgreementResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["4.0.0"] = SCHEMA_VERSION
    dataset_id: str
    analysis_run_id: str
    dataset_agreement: StatisticalResult
    alpha: StatisticalResult
    overlap: OverlapSummary


class ClassMetric(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    label: str
    precision: float | None
    recall: float | None
    f1: float | None
    gold_support: int
    predicted_support: int
    true_positive: int
    false_positive: int
    false_negative: int
    warnings: list[str] = Field(default_factory=list)


class ConfusionMatrix(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    labels: list[str]
    row_axis: Literal["authoritative_gold"] = "authoritative_gold"
    column_axis: Literal["submitted_annotation"] = "submitted_annotation"
    raw_counts: list[list[int]]
    row_normalized: list[list[float | None]]
    support: int


class GoldMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["4.0.0"] = SCHEMA_VERSION
    dataset_id: str
    analysis_run_id: str
    annotator_id: str | None = None
    gold_sources: list[str]
    gold_label_record_ids: list[str]
    evaluated_annotation_event_ids: list[str]
    excluded_distributional_gold_items: int
    excluded_unresolved_gold_items: int
    accuracy: StatisticalResult
    macro_precision: StatisticalResult
    macro_recall: StatisticalResult
    macro_f1: StatisticalResult
    micro_precision: StatisticalResult
    micro_recall: StatisticalResult
    micro_f1: StatisticalResult
    per_class: list[ClassMetric]
    confusion: ConfusionMatrix


class AnnotatorEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    annotator_id: str
    annotation_count: int
    items_covered: int
    gold_items: int
    classes_used: int
    overlapping_annotators: int
    gold_accuracy: float | None
    macro_f1: float | None
    gold_support: int
    evidence_level: EvidenceLevel


class AnalysisBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["4.0.0"] = SCHEMA_VERSION
    dataset_id: str
    analysis_run_id: str
    evidence: EvidenceSummary
    agreement: AgreementResponse
    gold_metrics: GoldMetricsResponse
    annotators: list[AnnotatorEvidence]
