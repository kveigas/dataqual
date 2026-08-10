from __future__ import annotations

import pytest
from dataqual.analysis.core import Annotation, Gold
from dataqual.analysis.gold import calculate_gold_metrics
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score


def fixture() -> tuple[list[Annotation], list[Gold], list[str]]:
    labels = ["a", "b", "c"]
    truth = ["a", "a", "b", "b", "c", "c"]
    predicted = ["a", "b", "b", "b", "a", "c"]
    annotations = [
        Annotation(f"ann-{i}", f"item-{i}", "worker", label) for i, label in enumerate(predicted)
    ]
    gold = [
        Gold(f"gold-{i}", f"item-{i}", label, "resolved_hard", "trusted_reference")
        for i, label in enumerate(truth)
    ]
    return annotations, gold, labels


def test_gold_metrics_match_sklearn_and_confusion_axes() -> None:
    annotations, gold, labels = fixture()
    result = calculate_gold_metrics(annotations, gold, labels)
    truth = [record.label for record in gold]
    predicted = [row.label for row in annotations]
    assert result.accuracy == pytest.approx(accuracy_score(truth, predicted))
    assert result.macro_precision == pytest.approx(
        precision_score(truth, predicted, labels=labels, average="macro", zero_division=0)
    )
    assert result.macro_recall == pytest.approx(
        recall_score(truth, predicted, labels=labels, average="macro", zero_division=0)
    )
    assert result.macro_f1 == pytest.approx(
        f1_score(truth, predicted, labels=labels, average="macro", zero_division=0)
    )
    assert result.confusion.row_axis == "authoritative_gold"
    assert result.confusion.column_axis == "submitted_annotation"
    assert result.confusion.raw_counts == [[1, 1, 0], [0, 2, 0], [1, 0, 1]]
    assert sum(map(sum, result.confusion.raw_counts)) == result.confusion.support == 6


def test_gold_excludes_non_hard_records_and_preserves_nulls() -> None:
    annotations = [Annotation("a1", "i1", "w", "a"), Annotation("a2", "i2", "w", "a")]
    gold = [
        Gold("g1", "i1", None, "unresolved", "expert_adjudication"),
        Gold("g2", "i2", None, "resolved_distributional", "trusted_reference"),
    ]
    result = calculate_gold_metrics(annotations, gold, ["a", "b"])
    assert result.accuracy is None
    assert result.confusion.support == 0
    assert result.confusion.row_normalized == [[None, None], [None, None]]
    assert all(metric.recall is None for metric in result.per_class)


def test_supported_but_unpredicted_class_is_zero_only_in_macro_precision() -> None:
    annotations = [Annotation("a1", "i1", "w", "a"), Annotation("a2", "i2", "w", "a")]
    gold = [
        Gold("g1", "i1", "a", "resolved_hard", "simulation_truth"),
        Gold("g2", "i2", "b", "resolved_hard", "simulation_truth"),
    ]
    result = calculate_gold_metrics(annotations, gold, ["a", "b"])
    assert result.per_class[1].precision is None
    assert "class_never_predicted" in result.per_class[1].warnings
    assert result.macro_precision == pytest.approx(0.25)
    assert result.macro_f1 == pytest.approx(1 / 3)
