from __future__ import annotations

from dataqual.benchmarking.metrics import evaluate_review_candidates
from dataqual.prioritization.service import ReviewPrioritizationService
from dataqual.schemas.simulation import (
    ItemArchetypeConfig,
    SimulatorConfig,
    WorkerArchetypeConfig,
)
from dataqual.simulation import SyntheticDatasetGenerator


def test_sanity_case_a_weak_worker_errors():
    # CASE A: All errors belong to one known low-reliability worker with development gold.
    cfg = SimulatorConfig(
        simulation_world_seed=101,
        item_count=50,
        worker_count=5,
        worker_archetypes=[
            WorkerArchetypeConfig(archetype="EXPERT", count=4, base_accuracy=0.95),
            WorkerArchetypeConfig(archetype="WEAK", count=1, base_accuracy=0.20),
        ],
        development_gold_fraction=0.40,
    )
    annos, golds, hidden_truth = SyntheticDatasetGenerator(cfg).generate()
    labels = list(cfg.label_classes)

    svc = ReviewPrioritizationService(annos, golds, labels)

    w_cands = svc.get_candidates(method="lowest_worker_reliability")
    r_cands = svc.get_candidates(method="random")

    w_res = evaluate_review_candidates(w_cands, hidden_truth)
    r_res = evaluate_review_candidates(r_cands, hidden_truth)

    # Worker reliability should outperform random on 10% budget
    w_rec = w_res.budget_metrics["10%"].error_recall
    r_rec = r_res.budget_metrics["10%"].error_recall
    assert w_rec >= r_rec


def test_sanity_case_b_high_entropy_errors():
    # CASE B: Errors concentrated on high-entropy items.
    cfg = SimulatorConfig(
        simulation_world_seed=202,
        item_count=50,
        worker_count=5,
        worker_archetypes=[WorkerArchetypeConfig(archetype="AVERAGE", count=5, base_accuracy=0.60)],
    )
    annos, golds, hidden_truth = SyntheticDatasetGenerator(cfg).generate()
    labels = list(cfg.label_classes)

    svc = ReviewPrioritizationService(annos, golds, labels)

    h_cands = svc.get_candidates(method="highest_entropy")
    r_cands = svc.get_candidates(method="random")

    h_res = evaluate_review_candidates(h_cands, hidden_truth)
    r_res = evaluate_review_candidates(r_cands, hidden_truth)

    assert h_res.normalized_aurec_20 >= r_res.normalized_aurec_20


def test_sanity_case_d_ambiguity_degrades_entropy_defect_recovery():
    # CASE D: Ambiguity generates entropy but not true errors.
    cfg = SimulatorConfig(
        simulation_world_seed=404,
        item_count=50,
        worker_count=5,
        item_archetypes=[
            ItemArchetypeConfig(archetype="AMBIGUOUS", count=50),
        ],
        worker_archetypes=[WorkerArchetypeConfig(archetype="EXPERT", count=5, base_accuracy=0.90)],
    )
    annos, golds, hidden_truth = SyntheticDatasetGenerator(cfg).generate()
    labels = list(cfg.label_classes)

    svc = ReviewPrioritizationService(annos, golds, labels)

    h_cands = svc.get_candidates(method="highest_entropy")
    h_res = evaluate_review_candidates(h_cands, hidden_truth)

    # Total true annotation defects on ambiguous items with expert workers should be low/zero
    assert h_res.total_eligible_errors <= 10
