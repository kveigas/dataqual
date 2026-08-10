"""Non-production pre-registration spike for weighted-vote evidence sensitivity.

This script resolves benchmark design feasibility only. It is intentionally isolated
from future production simulator/aggregation modules and must not set release defaults.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from crowdkit.aggregation import DawidSkene
from scipy.stats import spearmanr
from sklearn.metrics import accuracy_score, f1_score


SCENARIOS = (
    "homogeneous_workers",
    "heterogeneous_workers",
    "one_weak_worker",
    "adversarial_workers",
    "class_specific_errors",
    "sparse_overlap",
)
THRESHOLDS = (5, 10, 20, 50, 100)
CLASS_PRIOR = np.array([0.50, 0.30, 0.20])


def confusion_matrices(scenario: str, rng: np.random.Generator, workers: int) -> np.ndarray:
    matrices = np.zeros((workers, 3, 3), dtype=float)
    if scenario == "heterogeneous_workers":
        abilities = rng.uniform(0.55, 0.95, workers)
    else:
        abilities = np.full(workers, 0.78)
    if scenario == "homogeneous_workers":
        abilities[:] = 0.75
    if scenario == "one_weak_worker":
        abilities[:] = 0.82
        abilities[0] = 0.36
    for worker, ability in enumerate(abilities):
        matrices[worker] = np.full((3, 3), (1.0 - ability) / 2.0)
        np.fill_diagonal(matrices[worker], ability)
    if scenario == "adversarial_workers":
        for worker in range(6):
            matrices[worker] = np.array(
                [[0.10, 0.80, 0.10], [0.10, 0.10, 0.80], [0.80, 0.10, 0.10]]
            )
    if scenario == "class_specific_errors":
        for worker in range(workers):
            weak_class = worker % 3
            matrices[worker, weak_class] = np.array([0.10, 0.10, 0.10])
            matrices[worker, weak_class, weak_class] = 0.35
            matrices[worker, weak_class, (weak_class + 1) % 3] = 0.55
    return matrices


def sample_label(rng: np.random.Generator, probabilities: np.ndarray) -> int:
    return int(rng.choice(3, p=probabilities))


def generate(scenario: str, seed: int) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    workers, items = 40, 1500
    matrices = confusion_matrices(scenario, rng, workers)
    true_reliability = np.einsum("c,wcc->w", CLASS_PRIOR, matrices)

    # Evidence availability is generated independently of worker ability and labels.
    median = 15.0 if scenario == "sparse_overlap" else 40.0
    development_counts = np.clip(
        np.rint(rng.lognormal(np.log(median), 0.9, workers)), 2, 150
    ).astype(int)
    successes = np.zeros(workers, dtype=int)
    for worker in range(workers):
        for _ in range(development_counts[worker]):
            truth = int(rng.choice(3, p=CLASS_PRIOR))
            observed = sample_label(rng, matrices[worker, truth])
            successes[worker] += observed == truth

    truth = rng.choice(3, size=items, p=CLASS_PRIOR)
    annotations_per_item = 2 if scenario == "sparse_overlap" else 5
    rows = []
    for item in range(items):
        assigned = rng.choice(workers, size=annotations_per_item, replace=False)
        for worker in assigned:
            rows.append(
                {
                    "task": f"eval-{item}",
                    "worker": f"w-{worker}",
                    "label": str(sample_label(rng, matrices[worker, truth[item]])),
                    "worker_index": int(worker),
                }
            )
    return pd.DataFrame(rows), truth, development_counts, successes, true_reliability


def probability_metrics(
    probabilities: pd.DataFrame, truth: np.ndarray
) -> tuple[float, float, float, float]:
    probabilities = probabilities.reindex(columns=["0", "1", "2"], fill_value=0.0)
    item_index = probabilities.index.str.replace("eval-", "", regex=False).astype(int)
    ordered = probabilities.assign(_item=item_index).sort_values("_item").drop(columns="_item")
    row_sum = ordered.sum(axis=1).to_numpy()
    nonzero = row_sum > 0
    normalized = ordered.to_numpy()[nonzero] / row_sum[nonzero, None]
    ordered_indices = np.sort(item_index.to_numpy())[nonzero]
    eligible_truth = truth[ordered_indices]
    prediction = normalized.argmax(axis=1)
    one_hot = np.eye(3)[eligible_truth]
    return (
        float(len(eligible_truth) / len(truth)),
        float(accuracy_score(eligible_truth, prediction)),
        float(f1_score(eligible_truth, prediction, average="macro")),
        float(np.mean(np.sum((normalized - one_hot) ** 2, axis=1))),
    )


def majority_probabilities(events: pd.DataFrame) -> pd.DataFrame:
    votes = pd.crosstab(events["task"], events["label"]).astype(float)
    return votes.div(votes.sum(axis=1), axis=0)


def beta_reliability(counts: np.ndarray, successes: np.ndarray) -> np.ndarray:
    total_success = successes.sum()
    total_count = counts.sum()
    estimates = np.zeros(len(counts), dtype=float)
    for worker in range(len(counts)):
        other_n = total_count - counts[worker]
        other_s = total_success - successes[worker]
        prior_mean = (other_s + 0.5) / (other_n + 1) if other_n >= 20 else 0.5
        estimates[worker] = (2 * prior_mean + successes[worker]) / (2 + counts[worker])
    return estimates


def weighted_probabilities(
    events: pd.DataFrame, weights: np.ndarray, eligible: np.ndarray
) -> pd.DataFrame:
    frame = events.copy()
    frame["eligible"] = frame["worker_index"].map(lambda index: bool(eligible[index]))
    frame["weight"] = frame["worker_index"].map(lambda index: float(weights[index]))
    frame = frame[frame["eligible"] & (frame["weight"] > 0)]
    counts = frame.groupby("task")["worker"].nunique()
    scores = frame.pivot_table(
        index="task", columns="label", values="weight", aggfunc="sum", fill_value=0.0
    )
    scores = scores.loc[scores.index.intersection(counts[counts >= 2].index)]
    return scores.div(scores.sum(axis=1), axis=0)


def bootstrap_interval(values: list[float], seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    array = np.asarray(values, dtype=float)
    samples = rng.choice(array, size=(2000, len(array)), replace=True).mean(axis=1)
    return [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replicates", type=int, default=10)
    args = parser.parse_args()
    records = []

    for scenario_index, scenario in enumerate(SCENARIOS):
        for replicate in range(args.replicates):
            seed = 1009 + scenario_index * 100_000 + replicate * 997
            events, truth, counts, successes, true_reliability = generate(scenario, seed)
            mv = probability_metrics(majority_probabilities(events), truth)
            ds_model = DawidSkene(n_iter=100, tol=1e-5)
            ds = probability_metrics(ds_model.fit_predict_proba(events[["task", "worker", "label"]]), truth)
            estimated = beta_reliability(counts, successes)

            for threshold in THRESHOLDS:
                eligible = counts >= threshold
                weights = np.clip((estimated - 1 / 3) / (1 - 1 / 3), 0, 1)
                wv_frame = weighted_probabilities(events, weights, eligible)
                if len(wv_frame):
                    wv = probability_metrics(wv_frame, truth)
                else:
                    wv = (0.0, None, None, None)
                if eligible.sum() >= 2:
                    mae = float(np.mean(np.abs(estimated[eligible] - true_reliability[eligible])))
                    rank = float(spearmanr(estimated[eligible], true_reliability[eligible]).statistic)
                    if not np.isfinite(rank):
                        rank = None
                else:
                    mae = rank = None
                for method, metrics in (("majority_vote", mv), ("weighted_vote", wv), ("dawid_skene", ds)):
                    records.append(
                        {
                            "scenario": scenario,
                            "replicate": replicate,
                            "seed": seed,
                            "evidence_threshold": threshold,
                            "method": method,
                            "eligible_worker_fraction": float(eligible.mean()) if method == "weighted_vote" else 1.0,
                            "evaluation_item_coverage": metrics[0],
                            "accuracy": metrics[1],
                            "macro_f1": metrics[2],
                            "brier_score": metrics[3],
                            "worker_reliability_mae": mae if method == "weighted_vote" else None,
                            "worker_reliability_spearman": rank if method == "weighted_vote" else None,
                        }
                    )

    frame = pd.DataFrame(records)
    summaries = []
    metric_columns = [
        "eligible_worker_fraction",
        "evaluation_item_coverage",
        "accuracy",
        "macro_f1",
        "brier_score",
        "worker_reliability_mae",
        "worker_reliability_spearman",
    ]
    for summary_index, (keys, group) in enumerate(
        frame.groupby(["scenario", "evidence_threshold", "method"])
    ):
        row = dict(zip(("scenario", "evidence_threshold", "method"), keys))
        for metric in metric_columns:
            values = group[metric].dropna().tolist()
            row[metric] = None if not values else float(np.mean(values))
            row[f"{metric}_bootstrap_95"] = (
                None
                if not values
                else bootstrap_interval(values, 900_001 + summary_index * 101 + metric_columns.index(metric))
            )
        summaries.append(row)

    result = {
        "status": "exploratory_non_production",
        "production_default": 20,
        "production_default_changed": False,
        "replicates": args.replicates,
        "thresholds": list(THRESHOLDS),
        "scenarios": list(SCENARIOS),
        "summary": summaries,
        "replicate_metrics": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} metric rows and {len(summaries)} summaries to {args.output}")


if __name__ == "__main__":
    main()
