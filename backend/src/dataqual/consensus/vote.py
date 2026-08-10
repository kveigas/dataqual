from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from dataqual.analysis.core import Annotation, Gold
from dataqual.consensus.models import ConsensusStatus, GoldPartition, WeightedVoteCoverage


@dataclass(frozen=True, slots=True)
class VoteOutcome:
    item_id: str
    status: ConsensusStatus
    label: str | None
    probabilities: dict[str, float]
    counts: dict[str, int]
    scores: dict[str, float] | None
    support: int
    workers_used: list[str]
    excluded_workers: dict[str, str]
    confidence: float | None
    uncertainty: float | None
    entropy: float | None


def _winner(values: dict[str, float], *, tolerance: float = 0.0) -> tuple[str | None, bool]:
    maximum = max(values.values(), default=0.0)
    winners = [label for label, value in values.items() if abs(value - maximum) <= tolerance]
    return (winners[0], False) if len(winners) == 1 else (None, True)


def _entropy(probabilities: dict[str, float]) -> float:
    return -math.fsum(value * math.log(value) for value in probabilities.values() if value > 0)


def majority_vote(annotations: Sequence[Annotation], labels: Sequence[str]) -> list[VoteOutcome]:
    grouped: dict[str, list[Annotation]] = defaultdict(list)
    for annotation in annotations:
        grouped[annotation.item_id].append(annotation)
    outcomes = []
    for item_id in sorted(grouped):
        rows = grouped[item_id]
        counts = Counter(row.label for row in rows)
        complete_counts = {label: counts[label] for label in labels}
        proportions = {label: complete_counts[label] / len(rows) for label in labels}
        label, tied = _winner({key: float(value) for key, value in complete_counts.items()})
        maximum = max(proportions.values())
        outcomes.append(
            VoteOutcome(
                item_id=item_id,
                status=ConsensusStatus.UNRESOLVED if tied else ConsensusStatus.SUCCESS,
                label=label,
                probabilities=proportions,
                counts=complete_counts,
                scores=None,
                support=len(rows),
                workers_used=sorted(row.annotator_id for row in rows),
                excluded_workers={},
                confidence=maximum,
                uncertainty=1.0 - maximum,
                entropy=_entropy(proportions),
            )
        )
    return outcomes


def development_worker_weights(
    annotations: Sequence[Annotation],
    gold: Sequence[Gold],
    partition: GoldPartition,
    class_count: int,
    minimum_support: int = 20,
) -> tuple[dict[str, float], dict[str, int], dict[str, str]]:
    if set(partition.development_item_ids) & set(partition.evaluation_item_ids):
        raise ValueError("evaluation gold cannot enter development worker weights")
    development_ids = set(partition.development_item_ids)
    gold_by_item = {
        record.item_id: record.label
        for record in gold
        if record.item_id in development_ids and record.resolution_status == "resolved_hard"
    }
    successes: Counter[str] = Counter()
    totals: Counter[str] = Counter()
    workers = {row.annotator_id for row in annotations}
    for row in annotations:
        truth = gold_by_item.get(row.item_id)
        if truth is None:
            continue
        totals[row.annotator_id] += 1
        successes[row.annotator_id] += row.label == truth
    total_success = sum(successes.values())
    total_n = sum(totals.values())
    weights: dict[str, float] = {}
    excluded: dict[str, str] = {}
    chance = 1.0 / class_count
    for worker in sorted(workers):
        n = totals[worker]
        if n < minimum_support:
            excluded[worker] = f"development_gold_support_below_{minimum_support}"
            continue
        other_n = total_n - n
        other_success = total_success - successes[worker]
        prior_mean = (other_success + 0.5) / (other_n + 1) if other_n >= 20 else 0.5
        posterior_mean = (2.0 * prior_mean + successes[worker]) / (2.0 + n)
        weight = min(1.0, max(0.0, (posterior_mean - chance) / (1.0 - chance)))
        if weight <= 0:
            excluded[worker] = "nonpositive_chance_adjusted_weight"
            continue
        weights[worker] = weight
    return weights, dict(totals), excluded


def reliability_weighted_vote(
    annotations: Sequence[Annotation],
    gold: Sequence[Gold],
    labels: Sequence[str],
    partition: GoldPartition,
    minimum_support: int = 20,
) -> tuple[list[VoteOutcome], WeightedVoteCoverage]:
    weights, support, globally_excluded = development_worker_weights(
        annotations, gold, partition, len(labels), minimum_support
    )
    evaluation_ids = set(partition.evaluation_item_ids)
    grouped: dict[str, list[Annotation]] = defaultdict(list)
    for annotation in annotations:
        if annotation.item_id in evaluation_ids:
            grouped[annotation.item_id].append(annotation)
    outcomes = []
    resolved = 0
    for item_id in sorted(evaluation_ids):
        rows = grouped.get(item_id, [])
        eligible = [row for row in rows if row.annotator_id in weights]
        excluded = {
            row.annotator_id: globally_excluded.get(row.annotator_id, "worker_not_eligible")
            for row in rows
            if row.annotator_id not in weights
        }
        scores = dict.fromkeys(labels, 0.0)
        counts = dict.fromkeys(labels, 0)
        for row in rows:
            counts[row.label] += 1
        for row in eligible:
            scores[row.label] += weights[row.annotator_id]
        total_weight = math.fsum(scores.values())
        if len(eligible) < 2 or total_weight <= 0:
            outcomes.append(
                VoteOutcome(
                    item_id=item_id,
                    status=ConsensusStatus.INSUFFICIENT_EVIDENCE,
                    label=None,
                    probabilities=dict.fromkeys(labels, 0.0),
                    counts=counts,
                    scores=scores,
                    support=len(eligible),
                    workers_used=sorted(row.annotator_id for row in eligible),
                    excluded_workers=excluded,
                    confidence=None,
                    uncertainty=None,
                    entropy=None,
                )
            )
            continue
        probabilities = {label: score / total_weight for label, score in scores.items()}
        label, tied = _winner(scores, tolerance=1e-15)
        maximum = max(probabilities.values())
        if not tied:
            resolved += 1
        outcomes.append(
            VoteOutcome(
                item_id=item_id,
                status=ConsensusStatus.UNRESOLVED if tied else ConsensusStatus.SUCCESS,
                label=label,
                probabilities=probabilities,
                counts=counts,
                scores=scores,
                support=len(eligible),
                workers_used=sorted(row.annotator_id for row in eligible),
                excluded_workers=excluded,
                confidence=maximum,
                uncertainty=1.0 - maximum,
                entropy=_entropy(probabilities),
            )
        )
    coverage = WeightedVoteCoverage(
        eligible_workers=sorted(weights),
        ineligible_workers=globally_excluded,
        worker_weights=weights,
        development_gold_support=support,
        evaluation_items=len(evaluation_ids),
        items_with_weighted_consensus=resolved,
        coverage_fraction=resolved / len(evaluation_ids) if evaluation_ids else 0.0,
        partition_id=partition.partition_id,
    )
    return outcomes, coverage
