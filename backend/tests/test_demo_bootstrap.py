from __future__ import annotations

from pathlib import Path

from dataqual.api import create_app
from dataqual.config import Settings
from fastapi.testclient import TestClient


def test_demo_bootstrap_endpoint_success_and_idempotency(tmp_path: Path) -> None:
    settings = Settings(tmp_path / "data", 10 * 1024 * 1024)
    app = create_app(settings)
    client = TestClient(app)

    # Initial bootstrap call
    res1 = client.post("/api/v1/demo/bootstrap")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "ready"
    assert data1["dataset_name"] == "Synthetic Demo Dataset"
    assert data1["is_existing"] is False
    assert data1["imported_events"] > 0
    assert data1["imported_golds"] > 0
    assert "hidden_truth" not in data1

    dataset_id = data1["dataset_id"]

    # Second bootstrap call (must be idempotent and return same dataset_id)
    res2 = client.post("/api/v1/demo/bootstrap")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "ready"
    assert data2["dataset_id"] == dataset_id
    assert data2["is_existing"] is True

    # Datasets endpoint should list exactly 1 dataset
    datasets = client.get("/api/v1/datasets").json()
    assert len(datasets) == 1
    assert datasets[0]["dataset_id"] == dataset_id
