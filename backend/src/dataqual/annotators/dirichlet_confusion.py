from __future__ import annotations

from collections.abc import Sequence

import scipy.stats as stats

from dataqual.analysis.core import Annotation
from dataqual.schemas.core import GoldLabel
from dataqual.schemas.intelligence import DirichletCellInterval, DirichletConfusionEstimate


def compute_dirichlet_confusion(
    annotations: Sequence[Annotation],
    gold_labels: Sequence[GoldLabel],
    labels: Sequence[str],
    target_annotator_id: str,
) -> DirichletConfusionEstimate:
    label_list = list(labels)
    label_indices = {label: index for index, label in enumerate(label_list)}
    K = len(label_list)

    hard_gold = {
        g.item_id: g.label
        for g in gold_labels
        if str(g.resolution_status) == "resolved_hard" and g.label is not None
    }

    raw_counts = [[0] * K for _ in range(K)]
    for row in annotations:
        if row.annotator_id == target_annotator_id and row.item_id in hard_gold:
            gold_c = hard_gold[row.item_id]
            emitted_k = row.label
            if gold_c in label_indices and emitted_k in label_indices:
                raw_counts[label_indices[gold_c]][label_indices[emitted_k]] += 1

    smoothed_probs = [[0.0] * K for _ in range(K)]
    cell_intervals: list[DirichletCellInterval] = []
    row_support: dict[str, int] = {}
    dominant_targets: dict[str, str | None] = {}

    total_gold_evals = 0
    for c_idx, c_label in enumerate(label_list):
        n_c = sum(raw_counts[c_idx])
        row_support[c_label] = n_c
        total_gold_evals += n_c

        if n_c == 0:
            dominant_targets[c_label] = None
            for k_idx, k_label in enumerate(label_list):
                smoothed_probs[c_idx][k_idx] = 1.0 / K if K > 0 else 0.0
                cell_intervals.append(
                    DirichletCellInterval(
                        true_class=c_label,
                        emitted_label=k_label,
                        raw_count=0,
                        smoothed_probability=smoothed_probs[c_idx][k_idx],
                        marginal_lower_bound=0.0,
                        marginal_upper_bound=1.0,
                    )
                )
        else:
            best_k_idx = max(range(K), key=lambda k: raw_counts[c_idx][k])
            dominant_targets[c_label] = label_list[best_k_idx]

            for k_idx, k_label in enumerate(label_list):
                count_k = raw_counts[c_idx][k_idx]
                prob = float((count_k + 0.5) / (n_c + 0.5 * K))
                smoothed_probs[c_idx][k_idx] = prob

                # Marginal Beta interval derived from Dirichlet posterior
                a = count_k + 0.5
                b = (n_c - count_k) + 0.5 * (K - 1)
                lower = float(stats.beta.ppf(0.025, a, b))
                upper = float(stats.beta.ppf(0.975, a, b))

                cell_intervals.append(
                    DirichletCellInterval(
                        true_class=c_label,
                        emitted_label=k_label,
                        raw_count=count_k,
                        smoothed_probability=prob,
                        marginal_lower_bound=lower,
                        marginal_upper_bound=upper,
                    )
                )

    if total_gold_evals >= 20:
        status = "success"
    elif total_gold_evals >= 1:
        status = "limited"
    else:
        status = "no_gold"

    return DirichletConfusionEstimate(
        annotator_id=target_annotator_id,
        labels=label_list,
        raw_counts=raw_counts,
        smoothed_probabilities=smoothed_probs,
        cell_intervals=cell_intervals,
        row_support=row_support,
        dominant_targets=dominant_targets,
        status=status,
    )
