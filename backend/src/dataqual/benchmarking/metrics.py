from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from pydantic import BaseModel, Field

from dataqual.schemas.prioritization import ReviewCandidate
from dataqual.schemas.simulation import HiddenGroundTruth


class BudgetMetrics(BaseModel):
    budget_fraction: float
    k_count: int
    errors_recovered: int
    total_eligible_errors: int
    precision_at_k: float
    error_recall: float


class BenchmarkResult(BaseModel):
    prioritization_method: str
    review_unit: str
    total_candidates: int
    total_eligible_errors: int
    budget_metrics: dict[str, BudgetMetrics]
    cumulative_recovery_curve: list[dict[str, float]]
    aurec_20: float = Field(
        ..., description="Trapezoidal area under review-efficiency curve for budget 0-20%"
    )
    normalized_aurec_20: float = Field(..., description="AUREC divided by max budget 0.20")


def evaluate_review_candidates(
    candidates: Sequence[ReviewCandidate],
    hidden_truth: HiddenGroundTruth,
    budgets: Sequence[float] = (0.01, 0.05, 0.10, 0.20),
) -> BenchmarkResult:
    if not candidates:
        raise ValueError("Cannot evaluate empty candidate list.")

    review_unit = candidates[0].review_unit
    method = candidates[0].prioritization_method
    total_n = len(candidates)

    # Sort candidates by rank
    sorted_cands = sorted(candidates, key=lambda c: c.rank)

    # Determine ground truth defect status for each candidate in order
    is_true_error_list: list[bool] = []
    for c in sorted_cands:
        if review_unit == "annotation":
            assert c.annotation_id is not None
            at = hidden_truth.annotations_truth.get(c.annotation_id)
            is_err = at.is_actually_wrong if at else False
        else:
            # Item level review - true error if item is ambiguous or has defect
            it = hidden_truth.items_truth.get(c.item_id)
            is_err = (it.item_truth_type == "ambiguous") if it else False
        is_true_error_list.append(is_err)

    total_eligible_errors = sum(1 for is_err in is_true_error_list if is_err)

    # 1. Fixed Budget Metrics
    budget_map: dict[str, BudgetMetrics] = {}
    for b in budgets:
        k = max(1, int(np.round(b * total_n)))
        top_k_defects = sum(1 for is_err in is_true_error_list[:k] if is_err)
        prec = float(top_k_defects / k) if k > 0 else 0.0
        rec = float(top_k_defects / total_eligible_errors) if total_eligible_errors > 0 else 0.0

        b_key = f"{int(b * 100)}%"
        budget_map[b_key] = BudgetMetrics(
            budget_fraction=float(b),
            k_count=k,
            errors_recovered=top_k_defects,
            total_eligible_errors=total_eligible_errors,
            precision_at_k=prec,
            error_recall=rec,
        )

    # 2. Cumulative Recovery Curve & AUREC@20%
    # Step points from 0 to 20% budget in 1% increments
    curve: list[dict[str, float]] = []
    grid_budgets = np.linspace(0.0, 0.20, 21)

    x_vals: list[float] = []
    y_vals: list[float] = []

    for b in grid_budgets:
        if b == 0.0:
            rec = 0.0
        else:
            k = max(1, int(np.round(b * total_n)))
            top_k_defects = sum(1 for is_err in is_true_error_list[:k] if is_err)
            rec = float(top_k_defects / total_eligible_errors) if total_eligible_errors > 0 else 0.0

        x_vals.append(float(b))
        y_vals.append(rec)
        curve.append({"budget_fraction": float(b), "error_recall": rec})

    # Trapezoidal Integration for AUREC@20%
    aurec_20 = float(np.trapezoid(y_vals, x_vals))
    norm_aurec_20 = float(aurec_20 / 0.20)

    return BenchmarkResult(
        prioritization_method=method,
        review_unit=review_unit,
        total_candidates=total_n,
        total_eligible_errors=total_eligible_errors,
        budget_metrics=budget_map,
        cumulative_recovery_curve=curve,
        aurec_20=aurec_20,
        normalized_aurec_20=norm_aurec_20,
    )
