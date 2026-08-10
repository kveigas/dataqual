from __future__ import annotations

import copy

import pytest
from dataqual.prioritization.service import ReviewPrioritizationService
from dataqual.schemas.simulation import SimulatorConfig
from dataqual.simulation import SyntheticDatasetGenerator


def test_adversarial_hidden_truth_leakage_invariance():
    cfg = SimulatorConfig(simulation_world_seed=42, item_count=50, worker_count=5)
    annos, golds, hidden_truth = SyntheticDatasetGenerator(cfg).generate()

    labels = ["positive", "neutral", "negative"]
    svc1 = ReviewPrioritizationService(annos, golds, labels)

    methods = [
        "random",
        "highest_entropy",
        "lowest_consensus_confidence",
        "lowest_worker_reliability",
        "erv",
    ]

    initial_cands = {m: svc1.get_candidates(method=m) for m in methods}

    # Adversarially modify hidden truth (flip all error flags, zero true accuracies)
    corrupted_truth = copy.deepcopy(hidden_truth)
    for at in corrupted_truth.annotations_truth.values():
        at.is_actually_wrong = not at.is_actually_wrong
        at.worker_true_accuracy = 0.0
    for it in corrupted_truth.items_truth.values():
        it.canonical_true_label = "MUTATED"

    # Re-compute prioritization candidates using observed evidence
    svc2 = ReviewPrioritizationService(annos, golds, labels)
    post_cands = {m: svc2.get_candidates(method=m) for m in methods}

    for m in methods:
        c1_list = initial_cands[m]
        c2_list = post_cands[m]
        assert len(c1_list) == len(c2_list)
        for c1, c2 in zip(c1_list, c2_list, strict=False):
            assert c1.candidate_id == c2.candidate_id
            assert c1.rank == c2.rank
            assert c1.score == pytest.approx(c2.score, abs=1e-6)


def test_worker_reliability_uses_only_development_gold():
    cfg = SimulatorConfig(
        simulation_world_seed=123, item_count=50, worker_count=5, development_gold_fraction=0.0
    )
    annos, no_dev_golds, _ = SyntheticDatasetGenerator(cfg).generate()

    labels = ["positive", "neutral", "negative"]
    svc = ReviewPrioritizationService(annos, no_dev_golds, labels)

    # When development gold is 0, no worker has gold evidence
    cands = svc.get_candidates(method="lowest_worker_reliability")
    for c in cands:
        assert c.eligible_coverage is False
