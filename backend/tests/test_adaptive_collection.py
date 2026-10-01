from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from dataqual.analysis.core import Annotation
from dataqual.api import create_app
from dataqual.collection import plan_label_collection, replay_adaptive_collection
from dataqual.collection.adaptive import WorkerModel, labels_needed, posterior
from dataqual.config import Settings
from dataqual.prioritization.runs import ReviewRunQuotaError, ReviewRunStore
from dataqual.simulation import SyntheticDatasetGenerator
from dataqual.simulation.scenarios import get_pre_registered_scenario_config
from dataqual.storage.repository import StorageError
from fastapi.testclient import TestClient

LABELS = ["positive", "neutral", "negative"]


def _world(scenario: str = "S2", version: str = "1.1.0", seed: int = 100):
    cfg = get_pre_registered_scenario_config(scenario, world_seed=seed).model_copy(
        update={"version": version}
    )
    return SyntheticDatasetGenerator(cfg).generate()


def test_simulator_honours_base_accuracy_only_from_version_1_1() -> None:
    _, _, legacy = _world("S1", "1.0.0")
    _, _, current = _world("S1", "1.1.0")
    assert legacy.worker_parameters["w01"]["base_accuracy"] == pytest.approx(0.95)
    assert current.worker_parameters["w01"]["base_accuracy"] == pytest.approx(0.92)
    # Registered scenarios still declare 1.0.0, so frozen RC1 evidence is reproducible.
    assert get_pre_registered_scenario_config("S1").version == "1.0.0"


def test_posterior_and_labels_needed_follow_the_worker_model() -> None:
    expert = np.full((3, 3), 0.05)
    np.fill_diagonal(expert, 0.9)
    model = WorkerModel(LABELS, {}, expert, np.full(3, 1 / 3), "test")
    one = posterior(model, [("w1", "positive")])
    two = posterior(model, [("w1", "positive"), ("w2", "positive")])
    split = posterior(model, [("w1", "positive"), ("w2", "negative")])
    assert one[0] == pytest.approx(0.9)
    assert two[0] > one[0] > split[0]
    assert labels_needed(0.99, 0.95, 18.0) == 0
    assert labels_needed(0.9, 0.95, 18.0) == 1
    assert labels_needed(0.5, 0.95, 1.0) is None


def test_plan_classifies_every_item_and_respects_the_target() -> None:
    annotations, _, _ = _world()
    plan = plan_label_collection(annotations, LABELS, target_confidence=0.95, max_labels=5)
    counts = plan["status_counts"]
    assert sum(counts.values()) == plan["items_total"] == 100
    assert plan["basis"] == "dawid_skene_worker_model"
    for row in plan["items"]:
        if row["status"] == "confident":
            assert row["confidence"] >= 0.95 and row["additional_labels"] == 0
        elif row["status"] == "collect_more":
            assert row["additional_labels"] >= 1
            assert row["labels_collected"] + row["additional_labels"] <= 5
        else:
            assert row["confidence"] < 0.95
    assert plan["additional_labels_requested"] == sum(r["additional_labels"] for r in plan["items"])


def test_plan_falls_back_when_no_worker_model_can_be_fitted(monkeypatch) -> None:
    import dataqual.collection.adaptive as adaptive

    monkeypatch.setattr(adaptive, "fit_dawid_skene", lambda *_args, **_kwargs: [])
    plan = plan_label_collection([Annotation("a1", "i1", "w1", "positive")], LABELS)
    assert plan["basis"] == "fallback_assumed_accuracy"
    assert plan["items"][0]["status"] in {"collect_more", "confident"}


def test_replay_uses_fewer_labels_than_full_redundancy() -> None:
    annotations, _, truth = _world("S1")
    acceptable = {item: set(t.acceptable_labels) for item, t in truth.items_truth.items()}
    result = replay_adaptive_collection(annotations, LABELS, acceptable, 0.95, seed=7)
    assert result["adaptive"]["labels_per_item"] < result["full_model"]["labels_per_item"]
    assert result["adaptive"]["accuracy"] >= result["fixed_k"][0]["accuracy"]
    assert result["evaluated_items"] + result["pilot_items"] == 100


def test_review_run_store_quota_and_corruption(tmp_path: Path) -> None:
    store = ReviewRunStore(tmp_path, max_runs=1)
    store.save({"run_id": "run-" + "b" * 32})
    with pytest.raises(ReviewRunQuotaError):
        store.save({"run_id": "run-" + "c" * 32})
    (store.root / f"run-{'d' * 32}.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(StorageError, match="corrupted"):
        store.load("run-" + "d" * 32)


def test_api_reuses_runs_plans_collection_and_reports_ds_in_diagnostics(tmp_path: Path) -> None:
    client = TestClient(create_app(Settings(tmp_path / "data", 10 * 1024 * 1024)))
    dataset = client.post("/api/v1/demo/bootstrap").json()["dataset_id"]

    first = client.post(f"/api/v1/datasets/{dataset}/review-runs?method=erv")
    again = client.post(f"/api/v1/datasets/{dataset}/review-runs?method=erv&random_ranking_seed=9")
    assert first.status_code == again.status_code == 200
    assert first.headers["X-Review-Run-Reused"] == "false"
    assert again.headers["X-Review-Run-Reused"] == "true"
    assert again.json() == first.json()
    runs_url = f"/api/v1/datasets/{dataset}/review-runs?method=random"
    random_a = client.post(f"{runs_url}&random_ranking_seed=1")
    random_b = client.post(f"{runs_url}&random_ranking_seed=2")
    assert random_a.json()["run_id"] != random_b.json()["run_id"]

    plan = client.get(
        f"/api/v1/datasets/{dataset}/label-collection-plan?target_confidence=0.9&limit=5"
    ).json()
    assert plan["items_returned"] == 5 and plan["target_confidence"] == 0.9
    plan_url = f"/api/v1/datasets/{dataset}/label-collection-plan"
    assert client.get(f"{plan_url}?max_labels=99").status_code == 422

    item = client.get(f"/api/v1/datasets/{dataset}/diagnostics/items").json()[0]
    assert item["ds_status"] == "success" and item["ds_probabilities"]

    run_path = tmp_path / "data" / "review-runs" / f"{first.json()['run_id']}.json"
    run_path.write_text("{broken", encoding="utf-8")
    broken = client.get(f"/api/v1/review-runs/{first.json()['run_id']}")
    assert broken.status_code == 500 and broken.json()["error"]["code"] == "storage_error"
