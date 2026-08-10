from __future__ import annotations

from dataqual.benchmarking.metrics import evaluate_review_candidates
from dataqual.prioritization.service import ReviewPrioritizationService
from dataqual.schemas.simulation import SimulatorConfig
from dataqual.simulation import SyntheticDatasetGenerator


def test_budget_metrics_bounds_and_monotonicty():
    cfg = SimulatorConfig(simulation_world_seed=42, item_count=40, worker_count=5)
    annos, golds, hidden_truth = SyntheticDatasetGenerator(cfg).generate()
    labels = list(cfg.label_classes)

    svc = ReviewPrioritizationService(annos, golds, labels)
    cands = svc.get_candidates(method="erv")

    res = evaluate_review_candidates(cands, hidden_truth)

    assert 0.0 <= res.normalized_aurec_20 <= 1.0

    prev_recall = 0.0
    for b_key in ["1%", "5%", "10%", "20%"]:
        bm = res.budget_metrics[b_key]
        assert 0.0 <= bm.precision_at_k <= 1.0
        assert 0.0 <= bm.error_recall <= 1.0
        assert bm.error_recall >= prev_recall - 1e-6
        prev_recall = bm.error_recall
