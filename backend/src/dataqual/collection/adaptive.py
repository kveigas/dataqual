"""Adaptive label collection: stop paying for labels once an item is confidently resolved.

Fixed redundancy (for example "five labels per item") spends the same budget on obvious and
contested items. Adaptive schemes request another label only while an item's posterior is
below a target confidence (Welinder & Perona 2010; Khetan & Oh, NeurIPS 2016), and route items
that stay contested after many labels to expert review instead of buying more votes, because
persistent disagreement is often genuine human label variation rather than error.

The worker model is a Dawid-Skene fit (reference-compatible profile). Posteriors combine
each observed label through that worker's confusion row; unseen workers use the
label-weighted average confusion. No gold or hidden truth is used for planning.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from dataqual.analysis.core import Annotation
from dataqual.consensus.dawid_skene import fit_dawid_skene
from dataqual.consensus.models import ConsensusStatus, DawidSkeneConfig

PLAN_VERSION = "adaptive-collection-1.0.0"
FALLBACK_ACCURACY = 0.7
MIN_LABELS = 2
# Smoothed profile (Dirichlet pseudo-counts): the unsmoothed reference fit becomes overconfident on
# small pilots (near-perfect confusion rows), which made one label look like proof.
COLLECTION_DS_CONFIG = DawidSkeneConfig(profile="dawid_skene_smoothed_v1")


@dataclass(frozen=True)
class WorkerModel:
    labels: list[str]
    confusion: dict[str, np.ndarray]
    default_confusion: np.ndarray
    class_prior: np.ndarray
    basis: str

    @property
    def average_accuracy(self) -> float:
        return float(np.trace(self.default_confusion) / len(self.labels))


def _diagonal(k: int, accuracy: float) -> np.ndarray:
    off = (1.0 - accuracy) / (k - 1) if k > 1 else 0.0
    matrix = np.full((k, k), off)
    np.fill_diagonal(matrix, accuracy)
    return matrix


def fit_worker_model(annotations: Sequence[Annotation], labels: Sequence[str]) -> WorkerModel:
    labels = list(labels)
    k = len(labels)
    confusion: dict[str, np.ndarray] = {}
    weights: dict[str, int] = defaultdict(int)
    for row in annotations:
        weights[row.annotator_id] += 1
    prior_sum = np.zeros(k)
    for fit in fit_dawid_skene(annotations, labels, COLLECTION_DS_CONFIG):
        if fit.status != ConsensusStatus.SUCCESS:
            continue
        for index, worker in enumerate(fit.component.worker_ids):
            confusion[worker] = np.asarray(fit.worker_confusion[index], dtype=float)
        prior_sum += np.asarray(fit.class_prior, dtype=float) * len(fit.component.item_ids)
    if not confusion:
        uniform = np.full(k, 1.0 / k)
        fallback = _diagonal(k, FALLBACK_ACCURACY)
        return WorkerModel(labels, {}, fallback, uniform, "fallback_assumed_accuracy")
    workers = sorted(confusion)
    default = np.average(
        np.stack([confusion[w] for w in workers]), axis=0, weights=[weights[w] for w in workers]
    )
    prior = prior_sum / prior_sum.sum() if prior_sum.sum() > 0 else np.full(k, 1.0 / k)
    return WorkerModel(labels, confusion, default, prior, "dawid_skene_worker_model")


def posterior(model: WorkerModel, observed: Sequence[tuple[str, str]]) -> np.ndarray:
    """Item posterior over true classes given (annotator_id, label) observations."""
    index = {label: i for i, label in enumerate(model.labels)}
    log_p = np.log(np.maximum(model.class_prior, 1e-12))
    for worker, label in observed:
        if label not in index:
            continue
        row = model.confusion.get(worker, model.default_confusion)[:, index[label]]
        log_p = log_p + np.log(np.maximum(row, 1e-9))
    log_p -= log_p.max()
    p = np.exp(log_p)
    return p / p.sum()


def labels_needed(confidence: float, target: float, likelihood_ratio: float) -> int | None:
    """Optimistic count of further agreeing labels from an average annotator to reach target."""
    if confidence >= target:
        return 0
    if likelihood_ratio <= 1.0:
        return None  # An average annotator carries no evidence; more votes cannot help.
    confidence = min(max(confidence, 1e-9), 1 - 1e-9)
    gap = math.log(target / (1 - target)) - math.log(confidence / (1 - confidence))
    return max(1, math.ceil(gap / math.log(likelihood_ratio)))


def plan_label_collection(
    annotations: Sequence[Annotation],
    labels: Sequence[str],
    target_confidence: float = 0.95,
    max_labels: int = 7,
    min_labels: int = MIN_LABELS,
) -> dict:
    model = fit_worker_model(annotations, labels)
    k = len(model.labels)
    accuracy = model.average_accuracy
    error_share = (1.0 - accuracy) / (k - 1) if k > 1 else 1.0
    likelihood_ratio = accuracy / error_share if error_share > 0 else float("inf")

    by_item: dict[str, list[Annotation]] = defaultdict(list)
    for row in annotations:
        by_item[row.item_id].append(row)

    items = []
    for item_id in sorted(by_item):
        rows = by_item[item_id]
        p = posterior(model, [(r.annotator_id, r.label) for r in rows])
        top = int(np.argmax(p))
        confidence = float(p[top])
        count = len(rows)
        if confidence >= target_confidence and count >= min_labels:
            status, more = "confident", 0
        elif count >= max_labels:
            status, more = "expert_review", 0
        else:
            needed = labels_needed(confidence, target_confidence, likelihood_ratio)
            if needed is None:
                status, more = "expert_review", 0
            else:
                needed = max(needed, min_labels - count)  # never settle on a single label
                status, more = "collect_more", min(needed, max_labels - count)
        items.append(
            {
                "item_id": item_id,
                "labels_collected": count,
                "posterior": {label: float(p[i]) for i, label in enumerate(model.labels)},
                "most_likely_label": model.labels[top],
                "confidence": confidence,
                "status": status,
                "additional_labels": more,
            }
        )

    order = {"expert_review": 0, "collect_more": 1, "confident": 2}
    items.sort(key=lambda row: (order[row["status"]], row["confidence"], row["item_id"]))
    counts = {status: sum(1 for row in items if row["status"] == status) for status in order}
    return {
        "plan_version": PLAN_VERSION,
        "basis": model.basis,
        "target_confidence": target_confidence,
        "max_labels": max_labels,
        "average_annotator_accuracy": accuracy,
        "items_total": len(items),
        "status_counts": counts,
        "labels_collected": sum(row["labels_collected"] for row in items),
        "additional_labels_requested": sum(row["additional_labels"] for row in items),
        "items": items,
        "method": [
            "Smoothed Dawid-Skene worker confusion matrices; no gold used.",
            (
                f"Stop at {min_labels}+ labels once the posterior reaches "
                f"{target_confidence:.0%}; otherwise request the optimistic number of further "
                "agreeing labels."
            ),
            (
                f"Items still contested after {max_labels} labels go to expert review "
                "(possible genuine ambiguity)."
            ),
        ],
    }


def replay_adaptive_collection(
    annotations: Sequence[Annotation],
    labels: Sequence[str],
    acceptable: Mapping[str, set[str]],
    target_confidence: float,
    seed: int,
    pilot_fraction: float = 0.3,
    min_labels: int = MIN_LABELS,
) -> dict:
    """Sequential replay for evaluation (uses hidden truth only to score, never to decide).

    A pilot share of items is fully labelled and used to fit the worker model; the remaining
    items reveal their existing labels one at a time in random order until the posterior
    reaches the target. Baselines use the same model on the same items.
    """
    rng = random.Random(seed)  # noqa: S311 - reproducible simulation order, not security
    by_item: dict[str, list[Annotation]] = defaultdict(list)
    for row in annotations:
        by_item[row.item_id].append(row)
    items = sorted(by_item)
    rng.shuffle(items)
    pilot_count = max(1, round(len(items) * pilot_fraction))
    pilot, evaluation = items[:pilot_count], items[pilot_count:]
    model = fit_worker_model([r for item in pilot for r in by_item[item]], labels)

    totals = defaultdict(float)
    max_k = max(len(by_item[item]) for item in evaluation)
    fixed_correct = [0] * (max_k + 1)
    fixed_labels = [0] * (max_k + 1)
    for item in evaluation:
        rows = list(by_item[item])
        rng.shuffle(rows)
        observed = [(r.annotator_id, r.label) for r in rows]
        ok = acceptable[item]

        used, p = 0, posterior(model, [])
        for used in range(1, len(observed) + 1):
            p = posterior(model, observed[:used])
            if used >= min_labels and p.max() >= target_confidence:
                break
        totals["adaptive_labels"] += used
        totals["adaptive_correct"] += model.labels[int(np.argmax(p))] in ok

        full = posterior(model, observed)
        totals["full_labels"] += len(observed)
        totals["full_model_correct"] += model.labels[int(np.argmax(full))] in ok
        votes: dict[str, int] = defaultdict(int)
        for _, label in observed:
            votes[label] += 1
        best = max(votes.values())
        winners = [label for label, n in votes.items() if n == best]
        totals["full_majority_correct"] += len(winners) == 1 and winners[0] in ok

        for k in range(1, max_k + 1):
            take = observed[:k]
            fixed_labels[k] += len(take)
            fixed_correct[k] += model.labels[int(np.argmax(posterior(model, take)))] in ok

    n = len(evaluation)

    def summary(labels_key: str, correct_key: str) -> dict[str, float]:
        return {"labels_per_item": totals[labels_key] / n, "accuracy": totals[correct_key] / n}

    return {
        "evaluated_items": n,
        "pilot_items": len(pilot),
        "model_basis": model.basis,
        "adaptive": summary("adaptive_labels", "adaptive_correct"),
        "full_model": summary("full_labels", "full_model_correct"),
        "full_majority_vote": summary("full_labels", "full_majority_correct"),
        "fixed_k": [
            {"k": k, "labels_per_item": fixed_labels[k] / n, "accuracy": fixed_correct[k] / n}
            for k in range(1, max_k + 1)
        ],
    }
