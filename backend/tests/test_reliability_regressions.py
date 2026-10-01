from __future__ import annotations

import json

import pytest
from dataqual.api import create_app
from dataqual.config import Settings
from dataqual.consensus.dawid_skene import fit_dawid_skene
from dataqual.prioritization.evidence import REVIEW_DS_CONFIG
from dataqual.prioritization.runs import ReviewRunStore
from dataqual.prioritization.service import ReviewPrioritizationService
from dataqual.provenance import sha256_file
from dataqual.schemas.simulation import SimulatorConfig
from dataqual.simulation import SyntheticDatasetGenerator
from dataqual.storage.repository import StorageError
from fastapi.testclient import TestClient


def test_ranking_consumes_actual_ds_posteriors_and_reuses_fit():
    cfg = SimulatorConfig(simulation_world_seed=42, item_count=30, worker_count=5)
    annotations, golds, _ = SyntheticDatasetGenerator(cfg).generate()
    service = ReviewPrioritizationService(annotations, golds, cfg.label_classes)
    candidates = service.get_candidates("lowest_consensus_confidence", "item")
    expected = {}
    for fit in fit_dawid_skene(annotations, cfg.label_classes, REVIEW_DS_CONFIG):
        if fit.status == "success":
            expected.update(
                {item: 1 - max(fit.posteriors[i]) for i, item in enumerate(fit.component.item_ids)}
            )
    assert expected, "fixture must exercise successful model evidence, not empty outputs"
    for candidate in candidates:
        assert candidate.eligible_coverage == (candidate.item_id in expected)
        if candidate.eligible_coverage:
            assert candidate.score == pytest.approx(expected[candidate.item_id], abs=1e-12)
            assert candidate.contextual_evidence["ds_probabilities"]
    assert any(c.score > 0 for c in candidates)
    assert service.features is service.features
    with pytest.raises(ValueError, match="unsupported"):
        service.get_candidates("invented_method")


def test_demo_checksum_and_review_runs_survive_restart(tmp_path):
    settings = Settings(tmp_path / "data")
    app = create_app(settings)
    client = TestClient(app)
    dataset = client.post("/api/v1/demo/bootstrap").json()["dataset_id"]
    directory = app.state.repository.dataset_path(dataset)
    checksums = json.loads((directory / "artifact_checksums.json").read_text())
    for name, checksum in checksums.items():
        filename = "dataset_manifest.json" if name == "dataset_manifest" else f"{name}.parquet"
        assert sha256_file(directory / filename) == checksum
    run = client.post(f"/api/v1/datasets/{dataset}/review-runs").json()
    assert run["canonical_snapshot_checksum"]
    restarted = TestClient(create_app(settings))
    assert restarted.get(f"/api/v1/review-runs/{run['run_id']}").json() == run
    page = restarted.get(f"/api/v1/review-runs/{run['run_id']}/page?limit=3").json()
    assert len(page["items"]) == 3
    assert page["total"] > 3
    item = page["items"][0]["item_id"]
    filtered = restarted.get(f"/api/v1/review-runs/{run['run_id']}/page", params={"q": item}).json()
    assert all(item in candidate["item_id"] for candidate in filtered["items"])
    for suffix in ("?method=typo", "?review_unit=worker", "?random_ranking_seed=-1"):
        assert client.post(f"/api/v1/datasets/{dataset}/review-runs{suffix}").status_code == 422
    assert (
        client.get(f"/api/v1/review-runs/{run['run_id']}/candidates?offset=-1").status_code == 422
    )
    assert client.get("/api/v1/benchmark/results?seeds=0").status_code == 422
    assert client.get("/api/v1/benchmark/results?scenario_id=S99").status_code == 422


def test_review_run_store_rejects_traversal_and_detects_corruption(tmp_path):
    store = ReviewRunStore(tmp_path)
    assert store.load("../../secret") is None
    with pytest.raises(ValueError):
        store.save({"run_id": "../escape"})
    run_id = "run-" + "a" * 32
    store.save({"run_id": run_id, "score": 0.5})
    with pytest.raises(StorageError, match="already exists"):
        store.save({"run_id": run_id})
    path = store.root / f"{run_id}.json"
    body = json.loads(path.read_text())
    body["run"]["score"] = 0.9
    path.write_text(json.dumps(body))
    with pytest.raises(StorageError, match="checksum"):
        store.load(run_id)


def test_api_preserves_observed_confidence_and_only_current_events(tmp_path, config, valid_csv):
    client = TestClient(create_app(Settings(tmp_path / "data")))
    imported = client.post(
        "/api/v1/imports",
        files={"file": ("events.csv", valid_csv, "text/csv")},
        data={"config_json": config.model_dump_json()},
    )
    assert imported.json()["status"] == "accepted"
    dataset = client.get("/api/v1/datasets").json()[0]["dataset_id"]
    response = client.get(f"/api/v1/datasets/{dataset}/annotators/worker_01/profile")
    assert response.status_code == 200
    calibration = response.json()["calibration"]
    assert calibration["status"] == "available"
    assert calibration["observations"] == 1  # superseded 0.90 confidence is excluded
    assert calibration["brier_score"] == pytest.approx(0.95**2)


def test_benchmark_holds_out_development_gold_and_uses_sample_variance():
    from math import sqrt

    import scipy.stats as stats
    from dataqual.benchmarking.runner import BenchmarkRunner
    from dataqual.simulation.scenarios import get_pre_registered_scenario_config

    manifest, payloads = BenchmarkRunner("S1", seed_count=2).run_benchmark()
    for seed in manifest.world_seeds:
        cfg = get_pre_registered_scenario_config("S1", world_seed=seed)
        _, development_gold, _ = SyntheticDatasetGenerator(cfg).generate()
        known = {g.item_id for g in development_gold}
        assert not known.intersection(p["item_id"] for p in payloads if p["world_seed"] == seed)
    for comparison in manifest.summary.paired_comparisons:
        half_width = stats.t.ppf(0.975, 1) * comparison.std_difference / sqrt(2)
        assert comparison.ci_lower_95 == pytest.approx(comparison.mean_difference - half_width)
        assert comparison.ci_upper_95 == pytest.approx(comparison.mean_difference + half_width)
    single, _ = BenchmarkRunner("S1", seed_count=1).run_benchmark()
    assert all(
        c.ci_lower_95 is None and c.ci_upper_95 is None for c in single.summary.paired_comparisons
    )
