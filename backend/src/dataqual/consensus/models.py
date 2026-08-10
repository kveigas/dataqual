from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dataqual.analysis.models import AnalysisProvenance
from dataqual.schemas.core import SCHEMA_VERSION


class ConsensusMethod(StrEnum):
    MAJORITY_VOTE = "majority_vote"
    RELIABILITY_WEIGHTED_VOTE = "reliability_weighted_vote"
    DAWID_SKENE = "dawid_skene"


class ConsensusStatus(StrEnum):
    SUCCESS = "success"
    UNRESOLVED = "unresolved"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NON_CONVERGED = "non_converged"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class GoldPartition(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=False)
    partition_id: str
    development_item_ids: list[str]
    evaluation_item_ids: list[str]

    @model_validator(mode="after")
    def disjoint_roles(self) -> GoldPartition:
        overlap = set(self.development_item_ids) & set(self.evaluation_item_ids)
        if overlap:
            raise ValueError("development and evaluation gold partitions must be disjoint")
        if len(set(self.development_item_ids)) != len(self.development_item_ids):
            raise ValueError("development gold item IDs must be unique")
        if len(set(self.evaluation_item_ids)) != len(self.evaluation_item_ids):
            raise ValueError("evaluation gold item IDs must be unique")
        return self


class DawidSkeneConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=False)
    profile: Literal["dawid_skene_smoothed_v1", "dawid_skene_reference_compatible"] = (
        "dawid_skene_smoothed_v1"
    )
    initialization: Literal["smoothed_vote", "raw_majority_vote"] = "smoothed_vote"
    gamma: float = Field(default=1.0, ge=0.0, le=1.0)
    smoothing_lambda: float = Field(default=1.0, ge=0.0, le=1.0)
    probability_floor: float = Field(default=1e-12, ge=1e-12, le=1e-10)
    max_iterations: int = Field(default=200, ge=1, le=1000)
    absolute_tolerance: float = Field(default=1e-8, gt=0)
    relative_tolerance: float = Field(default=1e-6, gt=0)
    consecutive_small_improvements: int = Field(default=3, ge=1, le=3)
    stopping_rule: Literal["observed_likelihood_sustained", "crowdkit_elbo_signed_delta"] = (
        "observed_likelihood_sustained"
    )
    component_policy: Literal["separate", "global"] = "separate"

    @model_validator(mode="before")
    @classmethod
    def profile_defaults(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        profile = value.get("profile", "dawid_skene_smoothed_v1")
        expected = (
            {
                "initialization": "raw_majority_vote",
                "gamma": 0.0,
                "smoothing_lambda": 0.0,
                "probability_floor": 1e-10,
                "max_iterations": 200,
                "absolute_tolerance": 1e-6,
                "relative_tolerance": 1e-6,
                "consecutive_small_improvements": 1,
                "stopping_rule": "crowdkit_elbo_signed_delta",
                "component_policy": "global",
            }
            if profile == "dawid_skene_reference_compatible"
            else {
                "initialization": "smoothed_vote",
                "gamma": 1.0,
                "smoothing_lambda": 1.0,
                "probability_floor": 1e-12,
                "max_iterations": 200,
                "absolute_tolerance": 1e-8,
                "relative_tolerance": 1e-6,
                "consecutive_small_improvements": 3,
                "stopping_rule": "observed_likelihood_sustained",
                "component_policy": "separate",
            }
        )
        result = dict(value)
        for key, setting in expected.items():
            result.setdefault(key, setting)
        return result

    @model_validator(mode="after")
    def locked_profile(self) -> DawidSkeneConfig:
        expected = (
            ("raw_majority_vote", 0.0, 0.0, 1e-10, 1, "crowdkit_elbo_signed_delta", "global")
            if self.profile == "dawid_skene_reference_compatible"
            else (
                "smoothed_vote",
                1.0,
                1.0,
                1e-12,
                3,
                "observed_likelihood_sustained",
                "separate",
            )
        )
        actual = (
            self.initialization,
            self.gamma,
            self.smoothing_lambda,
            self.probability_floor,
            self.consecutive_small_improvements,
            self.stopping_rule,
            self.component_policy,
        )
        if actual != expected:
            raise ValueError("Dawid-Skene profile settings are immutable; choose a named profile")
        return self


class ConsensusRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=False)
    methods: list[ConsensusMethod] = Field(min_length=1)
    ds: DawidSkeneConfig = Field(default_factory=DawidSkeneConfig)
    gold_partition: GoldPartition | None = None
    minimum_development_gold: Literal[20] = 20

    @model_validator(mode="after")
    def unique_methods_and_partition(self) -> ConsensusRunRequest:
        if len(set(self.methods)) != len(self.methods):
            raise ValueError("consensus methods must be unique")
        if (
            ConsensusMethod.RELIABILITY_WEIGHTED_VOTE in self.methods
            and self.gold_partition is None
        ):
            raise ValueError("weighted vote requires an explicit gold partition")
        return self


class ConsensusResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["4.0.0"] = SCHEMA_VERSION
    result_id: str
    analysis_run_id: str
    dataset_id: str
    project_id: str
    item_id: str
    method: ConsensusMethod
    method_version: str
    status: ConsensusStatus
    label: str | None
    probabilities: dict[str, float]
    vote_counts: dict[str, int] | None = None
    scores: dict[str, float] | None = None
    confidence: float | None = None
    uncertainty: float | None = None
    posterior_entropy: float | None = None
    support: int
    workers_used: list[str]
    excluded_workers: dict[str, str]
    configuration: dict[str, Any]
    configuration_hash: str
    provenance: AnalysisProvenance
    component_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    created_at: str


class WorkerConfusionEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    annotator_id: str
    analysis_run_id: str
    method: Literal["dawid_skene_confusion"] = "dawid_skene_confusion"
    labels: list[str]
    row_axis: Literal["latent_true_class"] = "latent_true_class"
    column_axis: Literal["worker_emitted_class"] = "worker_emitted_class"
    probabilities: list[list[float]]
    support: int
    classes_observed: list[str]
    component_id: str
    warnings: list[str] = Field(default_factory=list)


class ConvergenceDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    converged: bool
    iterations: int
    stopping_reason: str
    tolerance_absolute: float
    tolerance_relative: float
    max_iterations: int
    initialization_method: str
    seed: int | None = None
    initial_class_prior: dict[str, float]
    final_class_prior: dict[str, float]
    final_log_likelihood: float | None
    final_delta: float | None
    log_likelihood_history: list[float]
    monotonicity_tolerance: float
    component_id: str
    items: int
    workers: int
    annotations: int
    observed_classes: int


class WeightedVoteCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    eligible_workers: list[str]
    ineligible_workers: dict[str, str]
    worker_weights: dict[str, float]
    development_gold_support: dict[str, int]
    evaluation_items: int
    items_with_weighted_consensus: int
    coverage_fraction: float
    minimum_gold_threshold: Literal[20] = 20
    weighting_method: Literal["beta_binomial_chance_adjusted_clipped"] = (
        "beta_binomial_chance_adjusted_clipped"
    )
    partition_id: str


class ConsensusComparisonItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    item_id: str
    classification: list[str]
    labels: dict[str, str | None]
    probabilities: dict[str, dict[str, float]]
    raw_votes: list[dict[str, str]]
    analysis_run_id: str


class ConsensusComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    analysis_run_id: str
    compared_items: int
    same_label_all_methods: int
    mv_vs_ds_disagreement: int
    weighted_vs_mv_disagreement: int
    weighted_vs_ds_disagreement: int
    tie_or_unresolved: int
    method_dependent_fraction: float
    items: list[ConsensusComparisonItem]


class ConsensusRun(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["4.0.0"] = SCHEMA_VERSION
    analysis_run_id: str
    dataset_id: str
    project_id: str
    canonical_artifact_checksum: str
    status: ConsensusStatus
    methods: list[ConsensusMethod]
    configuration: dict[str, Any]
    configuration_hash: str
    created_at: str
    software_version: str
    git_commit: str | None
    git_dirty: bool | None
    items: list[ConsensusResult]
    workers: list[WorkerConfusionEstimate]
    convergence: list[ConvergenceDiagnostics]
    weighted_vote_coverage: WeightedVoteCoverage | None
    comparison: ConsensusComparison
    warnings: list[str] = Field(default_factory=list)


class PaginatedConsensusItems(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    analysis_run_id: str
    total: int
    offset: int
    limit: int
    items: list[ConsensusResult]
