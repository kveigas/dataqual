from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from dataqual.analysis.core import Annotation, Gold
from dataqual.analysis.models import ClassMetric, ConfusionMatrix


@dataclass(frozen=True, slots=True)
class GoldCalculation:
    accuracy: float | None
    macro_precision: float | None
    macro_recall: float | None
    macro_f1: float | None
    micro_precision: float | None
    micro_recall: float | None
    micro_f1: float | None
    per_class: list[ClassMetric]
    confusion: ConfusionMatrix
    evaluated: list[Annotation]
    gold_records: list[Gold]


def calculate_gold_metrics(
    annotations: Sequence[Annotation], gold: Sequence[Gold], labels: Sequence[str]
) -> GoldCalculation:
    hard = {
        record.item_id: record for record in gold if record.resolution_status == "resolved_hard"
    }
    evaluated = [annotation for annotation in annotations if annotation.item_id in hard]
    gold_records = [hard[item_id] for item_id in sorted({row.item_id for row in evaluated})]
    index = {label: position for position, label in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]
    for annotation in evaluated:
        truth = hard[annotation.item_id].label
        if truth is None or truth not in index or annotation.label not in index:
            continue
        matrix[index[truth]][index[annotation.label]] += 1
    per_class: list[ClassMetric] = []
    for position, label in enumerate(labels):
        tp = matrix[position][position]
        fp = sum(matrix[row][position] for row in range(len(labels)) if row != position)
        fn = sum(matrix[position][column] for column in range(len(labels)) if column != position)
        gold_support = sum(matrix[position])
        predicted_support = sum(row[position] for row in matrix)
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall
            else None
        )
        warnings = []
        if gold_support == 0:
            warnings.append("class_has_no_gold_support")
        elif gold_support < 5:
            warnings.append("class_support_below_5")
        if predicted_support == 0:
            warnings.append("class_never_predicted")
        per_class.append(
            ClassMetric(
                label=label,
                precision=precision,
                recall=recall,
                f1=f1,
                gold_support=gold_support,
                predicted_support=predicted_support,
                true_positive=tp,
                false_positive=fp,
                false_negative=fn,
                warnings=warnings,
            )
        )
    supported = [metric for metric in per_class if metric.gold_support > 0]
    macro_precision = (
        sum(metric.precision if metric.precision is not None else 0.0 for metric in supported)
        / len(supported)
        if supported
        else None
    )
    recall_values = [metric.recall for metric in supported if metric.recall is not None]
    f1_values = [metric.f1 if metric.f1 is not None else 0.0 for metric in supported]
    macro_recall = sum(recall_values) / len(recall_values) if recall_values else None
    macro_f1 = sum(f1_values) / len(f1_values) if f1_values else None
    total = sum(sum(row) for row in matrix)
    correct = sum(matrix[i][i] for i in range(len(labels)))
    micro = correct / total if total else None
    normalized: list[list[float | None]] = [
        [value / sum(row) for value in row] if sum(row) else [None for _ in row] for row in matrix
    ]
    return GoldCalculation(
        accuracy=micro,
        macro_precision=macro_precision,
        macro_recall=macro_recall,
        macro_f1=macro_f1,
        micro_precision=micro,
        micro_recall=micro,
        micro_f1=micro,
        per_class=per_class,
        confusion=ConfusionMatrix(
            labels=list(labels), raw_counts=matrix, row_normalized=normalized, support=total
        ),
        evaluated=evaluated,
        gold_records=gold_records,
    )


def annotations_by_item(rows: Sequence[Annotation]) -> list[list[Annotation]]:
    grouped: dict[str, list[Annotation]] = {}
    for row in rows:
        grouped.setdefault(row.item_id, []).append(row)
    return list(grouped.values())


def gold_metric_from_groups(
    groups: Sequence[Sequence[Annotation]], gold: Sequence[Gold], labels: Sequence[str], name: str
) -> float | None:
    rows = [row for group in groups for row in group]
    calculation = calculate_gold_metrics(rows, gold, labels)
    return getattr(calculation, name)


def gold_status_counts(gold: Sequence[Gold]) -> Counter[str]:
    return Counter(record.resolution_status for record in gold)
