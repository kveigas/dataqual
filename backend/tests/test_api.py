from __future__ import annotations

from pathlib import Path

from dataqual.api import create_app
from dataqual.config import Settings
from dataqual.schemas.imports import ImportConfig
from fastapi.testclient import TestClient


def test_api_import_browse_summary_and_provenance(
    tmp_path: Path, config: ImportConfig, valid_csv: bytes
) -> None:
    client = TestClient(create_app(Settings(tmp_path / "data", 1024 * 1024)))
    assert client.get("/api/v1/health").json()["status"] == "ok"
    response = client.post(
        "/api/v1/imports",
        files={"file": ("events.csv", valid_csv, "text/csv")},
        data={"config_json": config.model_dump_json()},
    )
    assert response.status_code == 200
    record = response.json()
    assert record["status"] == "accepted"
    assert client.get(f"/api/v1/imports/{record['import_id']}").status_code == 200
    datasets = client.get("/api/v1/datasets").json()
    assert len(datasets) == 1
    dataset_id = datasets[0]["dataset_id"]
    assert client.get(f"/api/v1/datasets/{dataset_id}").status_code == 200
    assert client.get(f"/api/v1/datasets/{dataset_id}/summary").json()["unique_items"] == 4
    assert len(client.get(f"/api/v1/datasets/{dataset_id}/provenance").json()["raw_sha256"]) == 64


def test_api_structured_errors(tmp_path: Path, config: ImportConfig) -> None:
    client = TestClient(create_app(Settings(tmp_path / "data", 5)))
    invalid_config = client.post(
        "/api/v1/imports", files={"file": ("x.csv", b"a", "text/csv")}, data={"config_json": "{}"}
    )
    assert invalid_config.status_code == 422
    assert invalid_config.json()["error"]["code"] == "invalid_import_config"
    too_large = client.post(
        "/api/v1/imports",
        files={"file": ("x.csv", b"abcdef", "text/csv")},
        data={"config_json": config.model_dump_json()},
    )
    assert too_large.status_code == 413
    assert too_large.json()["error"]["code"] == "import_rejected"
    for path in (
        "/api/v1/imports/nope",
        "/api/v1/datasets/nope",
        "/api/v1/datasets/nope/summary",
        "/api/v1/datasets/nope/provenance",
    ):
        response = client.get(path)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
