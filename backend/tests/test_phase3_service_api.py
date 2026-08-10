from __future__ import annotations

from pathlib import Path

from dataqual.api import create_app
from dataqual.config import Settings
from dataqual.consensus.models import ConsensusRunRequest
from dataqual.consensus.service import ConsensusService
from dataqual.ingestion import ImportService
from dataqual.schemas.imports import ImportConfig
from dataqual.storage import DatasetRepository
from fastapi.testclient import TestClient


def imported(repository: DatasetRepository, config: ImportConfig, valid_csv: bytes) -> str:
    record = ImportService(repository, 1024 * 1024).import_bytes("events.csv", valid_csv, config)
    assert record.dataset_id is not None
    return record.dataset_id


def test_consensus_service_persists_provenance_comparison_and_current_events(
    repository: DatasetRepository, config: ImportConfig, valid_csv: bytes
) -> None:
    dataset_id = imported(repository, config, valid_csv)
    request = ConsensusRunRequest(methods=["majority_vote", "dawid_skene"])
    service = ConsensusService(repository)
    run = service.create_run(dataset_id, request)
    assert run.dataset_id == dataset_id
    assert run.canonical_artifact_checksum
    assert run.configuration_hash
    assert {row.method.value for row in run.items} == {"majority_vote", "dawid_skene"}
    current_worker_one = next(
        row for row in run.comparison.items if row.item_id == "item_001"
    ).raw_votes
    assert {tuple(row.values()) for row in current_worker_one} == {
        ("worker_01", "neutral"),
        ("worker_02", "positive"),
    }
    stored = service.get_run(run.analysis_run_id)
    assert stored == run
    assert (repository.consensus_root / run.analysis_run_id / "run.json").is_file()
    page = service.items(run.analysis_run_id, offset=0, limit=2)
    assert page.total == len(run.items) and len(page.items) == 2


def test_consensus_same_configuration_is_deterministic_except_identity_and_time(
    repository: DatasetRepository, config: ImportConfig, valid_csv: bytes
) -> None:
    dataset_id = imported(repository, config, valid_csv)
    service = ConsensusService(repository)
    request = ConsensusRunRequest(methods=["majority_vote", "dawid_skene"])
    first = service.create_run(dataset_id, request)
    second = service.create_run(dataset_id, request)
    assert first.configuration_hash == second.configuration_hash
    comparable_first = [
        (row.item_id, row.method, row.status, row.label, row.probabilities) for row in first.items
    ]
    comparable_second = [
        (row.item_id, row.method, row.status, row.label, row.probabilities) for row in second.items
    ]
    assert comparable_first == comparable_second


def test_consensus_api_routes_and_pagination(
    tmp_path: Path, config: ImportConfig, valid_csv: bytes
) -> None:
    client = TestClient(create_app(Settings(tmp_path / "data", 1024 * 1024)))
    imported_response = client.post(
        "/api/v1/imports",
        files={"file": ("events.csv", valid_csv, "text/csv")},
        data={"config_json": config.model_dump_json()},
    )
    dataset_id = imported_response.json()["dataset_id"]
    created = client.post(
        f"/api/v1/datasets/{dataset_id}/consensus/runs",
        json={"methods": ["majority_vote", "dawid_skene"]},
    )
    assert created.status_code == 200
    run_id = created.json()["analysis_run_id"]
    assert client.get(f"/api/v1/consensus/runs/{run_id}").status_code == 200
    page = client.get(f"/api/v1/consensus/runs/{run_id}/items?limit=2").json()
    assert page["limit"] == 2 and len(page["items"]) == 2
    item_id = page["items"][0]["item_id"]
    assert client.get(f"/api/v1/consensus/runs/{run_id}/items/{item_id}").status_code == 200
    assert client.get(f"/api/v1/consensus/runs/{run_id}/workers").status_code == 200
    assert client.get(f"/api/v1/consensus/runs/{run_id}/comparison").status_code == 200
    assert client.get("/api/v1/consensus/runs/missing").status_code == 404


def test_api_rejects_weighted_vote_without_partition(
    tmp_path: Path, config: ImportConfig, valid_csv: bytes
) -> None:
    client = TestClient(create_app(Settings(tmp_path / "data", 1024 * 1024)))
    response = client.post(
        "/api/v1/imports",
        files={"file": ("events.csv", valid_csv, "text/csv")},
        data={"config_json": config.model_dump_json()},
    )
    dataset_id = response.json()["dataset_id"]
    rejected = client.post(
        f"/api/v1/datasets/{dataset_id}/consensus/runs",
        json={"methods": ["reliability_weighted_vote"]},
    )
    assert rejected.status_code == 422
