from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from statistics import median

import numpy as np

from dataqual.analysis.models import ConfidenceInterval, EvidenceLevel, ResultStatus


@dataclass(frozen=True, slots=True)
class Annotation:
    annotation_id: str
    item_id: str
    annotator_id: str
    label: str
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class Gold:
    gold_label_id: str
    item_id: str
    label: str | None
    resolution_status: str
    gold_source: str


@dataclass(frozen=True, slots=True)
class AlphaComponents:
    value: float | None
    observed_disagreement: float | None
    expected_disagreement: float | None
    pairable_items: int
    annotations: int
    categories: int
    status: ResultStatus
    reason: str | None


def evidence_level(
    relevant_items: int,
    *,
    smallest_display_support: int | None = None,
    material_warning: bool = False,
) -> EvidenceLevel:
    if relevant_items >= 100 and not material_warning:
        return EvidenceLevel.STRONG
    if relevant_items >= 20 and (smallest_display_support is None or smallest_display_support >= 5):
        return EvidenceLevel.ADEQUATE
    if relevant_items < 20 or (
        smallest_display_support is not None and smallest_display_support < 5
    ):
        return EvidenceLevel.LIMITED
    return EvidenceLevel.MINIMAL


def group_annotations(annotations: Iterable[Annotation]) -> dict[str, list[Annotation]]:
    grouped: dict[str, list[Annotation]] = defaultdict(list)
    for annotation in annotations:
        grouped[annotation.item_id].append(annotation)
    return dict(grouped)


def pooled_percent_agreement(
    groups: Sequence[Sequence[Annotation]],
) -> tuple[float | None, int, int, int]:
    agreeing_pairs = 0
    compared_pairs = 0
    pairable_items = 0
    for group in groups:
        count = len(group)
        if count < 2:
            continue
        pairable_items += 1
        labels = Counter(row.label for row in group)
        agreeing_pairs += sum(n * (n - 1) // 2 for n in labels.values())
        compared_pairs += count * (count - 1) // 2
    value = agreeing_pairs / compared_pairs if compared_pairs else None
    return value, pairable_items, compared_pairs, agreeing_pairs


def nominal_alpha(groups: Sequence[Sequence[Annotation]]) -> AlphaComponents:
    coincidence: dict[tuple[str, str], float] = defaultdict(float)
    pairable_items = 0
    annotations = 0
    for group in groups:
        m_i = len(group)
        if m_i < 2:
            continue
        pairable_items += 1
        annotations += m_i
        counts = Counter(row.label for row in group)
        for left, left_count in counts.items():
            for right, right_count in counts.items():
                numerator = left_count * (right_count - (1 if left == right else 0))
                coincidence[(left, right)] += numerator / (m_i - 1)
    if pairable_items < 2:
        return AlphaComponents(
            None,
            None,
            None,
            pairable_items,
            annotations,
            0,
            ResultStatus.INSUFFICIENT_EVIDENCE,
            "at_least_two_pairable_items_required",
        )
    categories = sorted({label for pair in coincidence for label in pair})
    total = math.fsum(coincidence.values())
    if total <= 1 or len(categories) < 2:
        return AlphaComponents(
            None,
            None,
            0.0 if len(categories) == 1 else None,
            pairable_items,
            annotations,
            len(categories),
            ResultStatus.UNAVAILABLE,
            "zero_expected_disagreement",
        )
    observed = (
        math.fsum(value for (left, right), value in coincidence.items() if left != right) / total
    )
    marginals = {
        label: math.fsum(coincidence.get((label, other), 0.0) for other in categories)
        for label in categories
    }
    expected_numerator = math.fsum(
        marginals[left] * marginals[right]
        for left in categories
        for right in categories
        if left != right
    )
    expected = expected_numerator / (total * (total - 1))
    if expected <= 0 or not math.isfinite(expected):
        return AlphaComponents(
            None,
            observed,
            expected,
            pairable_items,
            annotations,
            len(categories),
            ResultStatus.UNAVAILABLE,
            "zero_expected_disagreement",
        )
    value = 1.0 - observed / expected
    if not math.isfinite(value):
        return AlphaComponents(
            None,
            observed,
            expected,
            pairable_items,
            annotations,
            len(categories),
            ResultStatus.FAILED,
            "non_finite_alpha",
        )
    return AlphaComponents(
        value,
        observed,
        expected,
        pairable_items,
        annotations,
        len(categories),
        ResultStatus.SUCCESS,
        None,
    )


def bootstrap_item_statistic(
    groups: Sequence[Sequence[Annotation]],
    statistic: Callable[[Sequence[Sequence[Annotation]]], float | None],
    *,
    estimate: float,
    seed: int,
    replicates: int = 2000,
    confidence_level: float = 0.95,
    population: str,
) -> tuple[ConfidenceInterval | None, str | None]:
    if len(groups) < 10:
        return None, "fewer_than_10_eligible_items"
    if replicates < 1 or not 0 < confidence_level < 1:
        return None, "invalid_bootstrap_configuration"
    rng = np.random.Generator(np.random.PCG64(seed))
    values: list[float] = []
    for indices in rng.integers(0, len(groups), size=(replicates, len(groups))):
        value = statistic([groups[int(index)] for index in indices])
        if value is not None and math.isfinite(value):
            values.append(value)
    failed = replicates - len(values)
    if failed / replicates > 0.05:
        return None, "more_than_5_percent_undefined_replicates"
    tail = (1.0 - confidence_level) / 2.0
    lower, upper = np.quantile(np.asarray(values), [tail, 1.0 - tail]).tolist()
    return ConfidenceInterval(
        estimate=estimate,
        lower=float(lower),
        upper=float(upper),
        confidence_level=confidence_level,
        replicates=replicates,
        valid_replicates=len(values),
        failed_replicates=failed,
        seed=seed,
        population=population,
    ), None


def distribution(values: Iterable[int]) -> dict[str, int]:
    return {str(key): value for key, value in sorted(Counter(values).items())}


def mean(values: Sequence[int]) -> float:
    return math.fsum(values) / len(values) if values else 0.0


def median_float(values: Sequence[int]) -> float:
    return float(median(values)) if values else 0.0
