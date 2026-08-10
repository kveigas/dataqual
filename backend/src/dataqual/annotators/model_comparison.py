from __future__ import annotations

import numpy as np

from dataqual.schemas.intelligence import (
    CellDifference,
    DirichletConfusionEstimate,
    GoldVsDSComparison,
)


def compare_gold_vs_ds_confusion(
    gold_confusion: DirichletConfusionEstimate,
    ds_matrix: np.ndarray,
    ds_labels: list[str],
    ds_support: int,
) -> GoldVsDSComparison:
    annotator_id = gold_confusion.annotator_id
    labels = gold_confusion.labels
    K = len(labels)

    matched_cells: list[CellDifference] = []
    diffs: list[float] = []

    # Map DS matrix rows/cols to labels
    ds_indices = {label: index for index, label in enumerate(ds_labels)}

    for c_idx, c_label in enumerate(labels):
        gold_row_support = gold_confusion.row_support.get(c_label, 0)

        for k_idx, k_label in enumerate(labels):
            if c_label in ds_indices and k_label in ds_indices:
                ds_prob = float(ds_matrix[ds_indices[c_label], ds_indices[k_label]])
            else:
                ds_prob = 1.0 / K if K > 0 else 0.0

            if gold_row_support > 0:
                gold_prob = gold_confusion.smoothed_probabilities[c_idx][k_idx]
                diff = abs(gold_prob - ds_prob)
                diffs.append(diff)
                matched_cells.append(
                    CellDifference(
                        true_class=c_label,
                        emitted_label=k_label,
                        gold_observed_probability=gold_prob,
                        ds_estimated_probability=ds_prob,
                        absolute_difference=diff,
                    )
                )
            else:
                matched_cells.append(
                    CellDifference(
                        true_class=c_label,
                        emitted_label=k_label,
                        gold_observed_probability=None,
                        ds_estimated_probability=ds_prob,
                        absolute_difference=0.0,
                    )
                )

    mae = float(np.mean(diffs)) if diffs else None
    total_gold_support = sum(gold_confusion.row_support.values())

    return GoldVsDSComparison(
        annotator_id=annotator_id,
        matched_cells=matched_cells,
        mae=mae,
        gold_support=total_gold_support,
        ds_support=ds_support,
    )
