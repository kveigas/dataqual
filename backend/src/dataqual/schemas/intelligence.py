from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BetaBinomialEstimate(BaseModel):
    annotator_id: str
    successes: int
    failures: int
    evaluated_gold_items: int
    posterior_mean: float
    posterior_median: float
    lower_bound: float
    upper_bound: float
    confidence_level: float = 0.95
    prior_alpha: float
    prior_beta: float
    prior_source: Literal["leave_one_out_project", "fallback_symmetric"]
    prior_population_n: int
    prior_mean: float
    prior_strength: float = 2.0
    evidence_status: Literal["strong", "adequate", "limited", "minimal", "no_gold"]
    reliability_evidence_state: Literal["CREDIBLY_LOW", "UNCERTAIN", "NOT_LOW", "NO_GOLD"] = (
        "NO_GOLD"
    )


class DirichletCellInterval(BaseModel):
    true_class: str
    emitted_label: str
    raw_count: int
    smoothed_probability: float
    marginal_lower_bound: float
    marginal_upper_bound: float
    interval_type: Literal["marginal_beta_credible_interval"] = "marginal_beta_credible_interval"


class DirichletConfusionEstimate(BaseModel):
    annotator_id: str
    labels: list[str]
    raw_counts: list[list[int]]
    smoothed_probabilities: list[list[float]]
    cell_intervals: list[DirichletCellInterval]
    row_support: dict[str, int]
    dominant_targets: dict[str, str | None]
    status: Literal["success", "limited", "no_gold"]


class CellDifference(BaseModel):
    true_class: str
    emitted_label: str
    gold_observed_probability: float | None
    ds_estimated_probability: float
    absolute_difference: float


class GoldVsDSComparison(BaseModel):
    annotator_id: str
    matched_cells: list[CellDifference]
    mae: float | None
    gold_support: int
    ds_support: int
    warning: str = (
        "Gold-observed confusion reflects evaluated ground truth; "
        "Dawid-Skene matrix is a latent-model estimate from agreement patterns."
    )


class ECEBin(BaseModel):
    bin_index: int
    lower_bound: float
    upper_bound: float
    count: int
    mean_confidence: float | None
    accuracy: float | None


class AnnotatorCalibration(BaseModel):
    annotator_id: str
    status: Literal["available", "not_available"]
    observations: int
    brier_score: float | None = None
    ece: float | None = None
    bins: list[ECEBin] = Field(default_factory=list)
    reason: str | None = None


class AnnotatorProfile(BaseModel):
    annotator_id: str
    total_annotations: int
    evaluated_gold_items: int
    evidence_level: Literal["strong", "adequate", "limited", "minimal"]
    beta_binomial: BetaBinomialEstimate | None = None
    dirichlet_confusion: DirichletConfusionEstimate | None = None
    gold_vs_ds: GoldVsDSComparison | None = None
    calibration: AnnotatorCalibration | None = None
