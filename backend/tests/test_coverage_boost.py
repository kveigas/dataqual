from __future__ import annotations

from dataqual.api import create_app
from dataqual.config import Settings
from dataqual.prioritization.service import ReviewPrioritizationService
from dataqual.schemas.core import AnnotationEvent, GoldLabel
from dataqual.simulation import SyntheticDatasetGenerator
from dataqual.simulation.scenarios import get_pre_registered_scenario_config
from fastapi.testclient import TestClient


def test_scenario_configs_coverage():
    scenarios = [f"S{i}" for i in range(1, 13)]
    for sc in scenarios:
        cfg = get_pre_registered_scenario_config(sc, world_seed=123, random_ranking_seed=999)
        assert cfg.version == "1.0.0"
        assert cfg.item_count > 0
        assert cfg.worker_count > 0


def test_prioritization_item_review_unit_coverage():
    cfg = get_pre_registered_scenario_config("S2", world_seed=42)
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
        cands = svc.get_candidates(method=m, review_unit="item")
        assert len(cands) > 0
        for c in cands:
            assert c.review_unit == "item"
            assert c.item_id is not None
            assert c.rank >= 1


def test_api_404_error_handling_coverage():
    from pathlib import Path

    t_dir = Path("temp_pytest_api_test")
    t_dir.mkdir(parents=True, exist_ok=True)
    settings = Settings(t_dir / "data", 1024 * 1024)
    app = create_app(settings)
    client = TestClient(app)

    bogus_run_id = "run_nonexistent_123"

    res1 = client.get(f"/api/v1/review-runs/{bogus_run_id}")
    assert res1.status_code == 404

    res2 = client.get(f"/api/v1/review-runs/{bogus_run_id}/candidates")
    assert res2.status_code == 404

    res3 = client.get(f"/api/v1/review-runs/{bogus_run_id}/summary")
    assert res3.status_code == 404


def test_prioritization_edge_cases_coverage():
    # Test prioritization service with workers missing gold labels
    annos = [
        AnnotationEvent(
            annotation_id="a1",
            project_id="p1",
            item_id="item1",
            annotator_id="w1",
            label_domain_id="sentiment_v1",
            label="positive",
            event_version=1,
            is_current=True,
            annotation_source="human",
            source_import_id="imp1",
            source_row_number=1,
        ),
        AnnotationEvent(
            annotation_id="a2",
            project_id="p1",
            item_id="item1",
            annotator_id="w2",
            label_domain_id="sentiment_v1",
            label="negative",
            event_version=1,
            is_current=True,
            annotation_source="human",
            source_import_id="imp1",
            source_row_number=2,
        ),
        AnnotationEvent(
            annotation_id="a3",
            project_id="p1",
            item_id="item2",
            annotator_id="w1",
            label_domain_id="sentiment_v1",
            label="positive",
            event_version=1,
            is_current=True,
            annotation_source="human",
            source_import_id="imp1",
            source_row_number=3,
        ),
    ]
    # No gold labels
    golds: list[GoldLabel] = []
    labels = ["positive", "negative"]

    svc = ReviewPrioritizationService(annos, golds, labels)
    cands_w = svc.get_candidates(method="lowest_worker_reliability", review_unit="annotation")
    assert len(cands_w) == 3
    for c in cands_w:
        assert c.eligible_coverage is False

    cands_erv = svc.get_candidates(method="erv", review_unit="annotation")
    assert len(cands_erv) == 3
