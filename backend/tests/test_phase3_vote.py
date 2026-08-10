from __future__ import annotations

import random

import pytest
from dataqual.analysis.core import Annotation, Gold
from dataqual.consensus.models import ConsensusStatus, GoldPartition
from dataqual.consensus.vote import (
    development_worker_weights,
    majority_vote,
    reliability_weighted_vote,
)


def test_majority_vote_counts_distribution_tie_and_single_source() -> None:
    rows = [
        Annotation("a1", "i1", "w1", "a"),
        Annotation("a2", "i1", "w2", "a"),
        Annotation("a3", "i1", "w3", "b"),
        Annotation("a4", "i2", "w1", "a"),
        Annotation("a5", "i2", "w2", "b"),
        Annotation("a6", "i3", "w1", "b"),
    ]
    result = {row.item_id: row for row in majority_vote(rows, ["a", "b"])}
    assert result["i1"].label == "a"
    assert result["i1"].probabilities == {"a": 2 / 3, "b": 1 / 3}
    assert result["i2"].status == ConsensusStatus.UNRESOLVED
    assert result["i2"].label is None
    assert result["i3"].support == 1
    assert result["i3"].label == "b"


def weighted_fixture() -> tuple[list[Annotation], list[Gold], GoldPartition]:
    annotations = []
    gold = []
    development = []
    for index in range(20):
        item = f"dev-{index}"
        truth = "a" if index % 2 == 0 else "b"
        development.append(item)
        gold.append(Gold(f"g-{item}", item, truth, "resolved_hard", "simulation_truth"))
        annotations.extend(
            [
                Annotation(f"p-{index}", item, "perfect", truth),
                Annotation(f"w-{index}", item, "weak", "b" if truth == "a" else "a"),
                Annotation(
                    f"m-{index}",
                    item,
                    "medium",
                    truth if index % 4 else ("b" if truth == "a" else "a"),
                ),
            ]
        )
    annotations.extend(
        [
            Annotation("e1", "eval-1", "perfect", "a"),
            Annotation("e2", "eval-1", "medium", "a"),
            Annotation("e3", "eval-1", "weak", "b"),
        ]
    )
    gold.append(Gold("g-eval", "eval-1", "b", "resolved_hard", "simulation_truth"))
    return (
        annotations,
        gold,
        GoldPartition(
            partition_id="split-1",
            development_item_ids=development,
            evaluation_item_ids=["eval-1"],
        ),
    )


def test_weighted_vote_uses_contract_weights_and_excludes_nonpositive_worker() -> None:
    annotations, gold, partition = weighted_fixture()
    weights, support, excluded = development_worker_weights(
        annotations, gold, partition, class_count=2
    )
    assert support == {"perfect": 20, "weak": 20, "medium": 20}
    assert weights["perfect"] > weights["medium"] > 0
    assert excluded["weak"] == "nonpositive_chance_adjusted_weight"
    outcomes, coverage = reliability_weighted_vote(annotations, gold, ["a", "b"], partition)
    assert outcomes[0].label == "a"
    assert outcomes[0].support == 2
    assert coverage.minimum_gold_threshold == 20
    assert coverage.coverage_fraction == 1.0


def test_evaluation_gold_cannot_affect_worker_weights_or_weighted_output() -> None:
    annotations, gold, partition = weighted_fixture()
    first_weights = development_worker_weights(annotations, gold, partition, 2)[0]
    first = reliability_weighted_vote(annotations, gold, ["a", "b"], partition)[0]
    changed = [
        Gold(
            row.gold_label_id,
            row.item_id,
            "a" if row.label == "b" else "b",
            row.resolution_status,
            row.gold_source,
        )
        if row.item_id in partition.evaluation_item_ids
        else row
        for row in gold
    ]
    assert development_worker_weights(annotations, changed, partition, 2)[0] == first_weights
    assert reliability_weighted_vote(annotations, changed, ["a", "b"], partition)[0] == first


def test_weighted_vote_rejects_partition_overlap_and_low_support() -> None:
    with pytest.raises(ValueError, match="disjoint"):
        GoldPartition(
            partition_id="bad", development_item_ids=["same"], evaluation_item_ids=["same"]
        )
    annotations, gold, partition = weighted_fixture()
    small_partition = partition.model_copy(
        update={"development_item_ids": partition.development_item_ids[:19]}
    )
    outcomes, coverage = reliability_weighted_vote(annotations, gold, ["a", "b"], small_partition)
    assert outcomes[0].status == ConsensusStatus.INSUFFICIENT_EVIDENCE
    assert coverage.eligible_workers == []


def test_majority_vote_is_row_order_invariant() -> None:
    rows, _gold, _partition = weighted_fixture()
    before = majority_vote(rows, ["a", "b"])
    random.Random(11).shuffle(rows)  # noqa: S311 -- deterministic test permutation
    assert majority_vote(rows, ["a", "b"]) == before
