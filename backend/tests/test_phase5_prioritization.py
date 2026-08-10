from __future__ import annotations

import pytest
from dataqual.prioritization.config import DEFAULT_ERV_CONFIG
from dataqual.prioritization.service import ReviewPrioritizationService
from dataqual.schemas.prioritization import ErvScoreComponents
from dataqual.schemas.simulation import SimulatorConfig
from dataqual.simulation import SyntheticDatasetGenerator


def test_erv_formula_exact_reconciliation():
    cfg = SimulatorConfig(simulation_world_seed=42, item_count=30, worker_count=5)
    annos, golds, _ = SyntheticDatasetGenerator(cfg).generate()

    labels = ["positive", "neutral", "negative"]
    svc = ReviewPrioritizationService(annos, golds, labels)

    cands = svc.get_candidates(method="erv")
    assert len(cands) > 0

    for c in cands:
        comp = c.score_components
        assert isinstance(comp, ErvScoreComponents)
        u_i = comp.u_i
        h_i = comp.h_i
        e_i = comp.e_i
        raw_score = comp.raw_score

        expected_raw = (
            DEFAULT_ERV_CONFIG.weight_uncert * u_i
            + DEFAULT_ERV_CONFIG.weight_entropy * h_i
            + DEFAULT_ERV_CONFIG.weight_worker_error * e_i
        )
        assert raw_score == pytest.approx(expected_raw, abs=1e-6)
        assert c.score == pytest.approx(expected_raw, abs=1e-6)


def test_prioritization_methods_generate_unique_ranks():
    cfg = SimulatorConfig(simulation_world_seed=99, item_count=40, worker_count=5)
    annos, golds, _ = SyntheticDatasetGenerator(cfg).generate()
    labels = ["positive", "neutral", "negative"]

    svc = ReviewPrioritizationService(annos, golds, labels)

    methods = [
        "random",
        "highest_entropy",
        "lowest_consensus_confidence",
        "lowest_worker_reliability",
        "erv",
    ]

    for m in methods:
        cands = svc.get_candidates(method=m)
        ranks = [c.rank for c in cands]
        assert ranks == list(range(1, len(cands) + 1))
