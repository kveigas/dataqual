from __future__ import annotations

import math
import random

import pytest
from dataqual.analysis.core import (
    Annotation,
    bootstrap_item_statistic,
    nominal_alpha,
    pooled_percent_agreement,
)
from dataqual.analysis.engine import AnalysisEngine
from dataqual.analysis.models import ResultStatus
from hypothesis import given
from hypothesis import strategies as st
from nltk.metrics.agreement import AnnotationTask


def rows(matrix: list[list[str | None]]) -> list[list[Annotation]]:
    groups = []
    for item_index, ratings in enumerate(matrix):
        group = [
            Annotation(f"a-{item_index}-{worker}", f"i-{item_index}", f"w-{worker}", label)
            for worker, label in enumerate(ratings)
            if label is not None
        ]
        groups.append(group)
    return groups


def nltk_alpha(matrix: list[list[str | None]]) -> float:
    data = [
        (f"w-{worker}", f"i-{item}", label)
        for item, ratings in enumerate(matrix)
        for worker, label in enumerate(ratings)
        if label is not None
    ]
    return float(AnnotationTask(data=data).alpha())


@pytest.mark.parametrize(
    "matrix",
    [
        [["a", "a"], ["b", "b"], ["a", "a"]],
        [["a", "a"], ["a", "b"], ["b", "b"]],
        [["a", None, "a"], ["b", "b", None], ["a", "b", "b"]],
        [["a", "b", "c"], ["a", "a", "c"], ["c", "b", "c"]],
        [["a", None, "b", None], [None, "b", None, "b"], ["a", "a", None, None]],
    ],
)
def test_nominal_alpha_matches_nltk_golden_fixtures(matrix: list[list[str | None]]) -> None:
    actual = nominal_alpha(rows(matrix))
    assert actual.status == ResultStatus.SUCCESS
    assert actual.value == pytest.approx(nltk_alpha(matrix), abs=1e-10)


def test_nominal_alpha_matches_nltk_randomized_finite_fixtures() -> None:
    rng = random.Random(20260809)  # noqa: S311 -- deterministic statistical fixture only
    checked = 0
    for _ in range(100):
        matrix = [[rng.choice(["a", "b", "c", None]) for _ in range(4)] for _ in range(12)]
        actual = nominal_alpha(rows(matrix))
        if actual.status == ResultStatus.SUCCESS:
            assert actual.value == pytest.approx(nltk_alpha(matrix), abs=1e-8)
            checked += 1
    assert checked >= 90


def test_pooled_agreement_uses_comparable_unordered_pairs() -> None:
    # Item 1 contributes 1 agreeing pair; item 2 contributes 3 pairs, only one agrees.
    value, items, pairs, agreements = pooled_percent_agreement(rows([["a", "a"], ["a", "a", "b"]]))
    assert (items, pairs, agreements) == (2, 4, 2)
    assert value == 0.5


def test_alpha_reports_degenerate_and_sparse_states() -> None:
    single_class = nominal_alpha(rows([["a", "a"], ["a", "a"]]))
    assert single_class.value is None
    assert single_class.status == ResultStatus.UNAVAILABLE
    assert single_class.reason == "zero_expected_disagreement"
    too_sparse = nominal_alpha(rows([["a", None], [None, "b"], ["a", "b"]]))
    assert too_sparse.status == ResultStatus.INSUFFICIENT_EVIDENCE
    assert too_sparse.value is None


def test_item_bootstrap_is_reproducible_and_preserves_constant_statistic() -> None:
    groups = rows([["a", "a"], ["b", "b"]] * 5)
    kwargs = {
        "estimate": 1.0,
        "seed": 42,
        "replicates": 200,
        "confidence_level": 0.95,
        "population": "ten pairable items",
    }
    first, reason = bootstrap_item_statistic(
        groups, lambda sampled: pooled_percent_agreement(sampled)[0], **kwargs
    )
    second, _ = bootstrap_item_statistic(
        groups, lambda sampled: pooled_percent_agreement(sampled)[0], **kwargs
    )
    assert reason is None
    assert first == second
    assert first is not None
    assert (first.lower, first.upper, first.failed_replicates) == (1.0, 1.0, 0)


def test_bootstrap_refuses_tiny_population_and_excess_undefined() -> None:
    tiny, reason = bootstrap_item_statistic(
        rows([["a", "a"]] * 9),
        lambda _sampled: 1.0,
        estimate=1.0,
        seed=1,
        replicates=10,
        population="tiny",
    )
    assert tiny is None and reason == "fewer_than_10_eligible_items"
    failed, reason = bootstrap_item_statistic(
        rows([["a", "b"]] * 10),
        lambda _sampled: None,
        estimate=0.0,
        seed=1,
        replicates=10,
        population="undefined",
    )
    assert failed is None and reason == "more_than_5_percent_undefined_replicates"


def test_overlap_reports_disconnected_groups_isolates_and_zero_shared_pairs() -> None:
    annotations = [
        Annotation("a1", "i1", "w1", "a"),
        Annotation("a2", "i1", "w2", "a"),
        Annotation("a3", "i2", "w3", "b"),
        Annotation("a4", "i2", "w4", "a"),
        Annotation("a5", "i3", "w5", "a"),
    ]
    overlap, _ = AnalysisEngine._overlap(annotations, ["i1", "i2", "i3", "i4"])
    assert overlap.connected_component_count == 3
    assert overlap.largest_component_size == 2
    assert overlap.isolated_workers == ["w5"]
    assert overlap.isolated_items == ["i3", "i4"]
    no_shared = next(
        pair for pair in overlap.pairwise if pair.annotator_a == "w1" and pair.annotator_b == "w3"
    )
    assert no_shared.raw_percent_agreement is None
    assert no_shared.status == ResultStatus.UNAVAILABLE


@given(
    st.lists(
        st.lists(st.sampled_from(["a", "b", "c"]), min_size=2, max_size=4), min_size=2, max_size=20
    )
)
def test_nominal_alpha_is_invariant_to_item_worker_and_label_names(
    matrix: list[list[str]],
) -> None:
    original = nominal_alpha(rows(matrix))
    relabeled = [
        [{"a": "x", "b": "z", "c": "y"}[label] for label in reversed(item)]
        for item in reversed(matrix)
    ]
    changed = nominal_alpha(rows(relabeled))
    assert changed.status == original.status
    if original.value is not None:
        assert changed.value is not None
        assert math.isclose(changed.value, original.value, abs_tol=1e-12)
