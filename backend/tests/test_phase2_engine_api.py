from __future__ import annotations

from pathlib import Path

from dataqual.analysis import AnalysisEngine
from dataqual.api import create_app
from dataqual.config import Settings
from dataqual.ingestion import ImportService
from dataqual.schemas.imports import ImportConfig
from dataqual.storage import DatasetRepository
from fastapi.testclient import TestClient


def imported(repository: DatasetRepository, config: ImportConfig, valid_csv: bytes) -> str:
    record = ImportService(repository, 1024 * 1024).import_bytes("events.csv", valid_csv, config)
    assert record.dataset_id is not None
    return record.dataset_id


def test_engine_reconciles_current_events_overlap_gold_and_provenance(
    repository: DatasetRepository, config: ImportConfig, valid_csv: bytes
) -> None:
    dataset_id = imported(repository, config, valid_csv)
    bundle = AnalysisEngine(repository).analyze(dataset_id, seed=7, replicates=50)
    assert bundle.evidence.annotation_event_count == 8
    assert bundle.evidence.all_annotation_event_count == 9
    assert bundle.evidence.superseded_annotation_event_count == 1
    assert bundle.evidence.unique_item_count == 4
    assert bundle.evidence.class_counts == {"positive": 1, "neutral": 4, "negative": 3}
    assert bundle.evidence.gold_item_count == 2
    assert bundle.agreement.dataset_agreement.value == 0.4
    assert bundle.agreement.dataset_agreement.support["compared_unordered_pairs"] == 5
    assert bundle.agreement.alpha.value is not None
    assert bundle.gold_metrics.confusion.support == 4
    assert len(bundle.gold_metrics.evaluated_annotation_event_ids) == 4
    assert bundle.analysis_run_id == bundle.evidence.provenance.analysis_run_id
    assert bundle.agreement.alpha.provenance.canonical_artifact_checksum
    assert (repository.analysis_root / bundle.analysis_run_id / "analysis.json").is_file()
    worker = next(row for row in bundle.annotators if row.annotator_id == "worker_01")
    assert worker.annotation_count == 3  # old ann_001 is not counted


def test_analysis_cache_is_stable_per_snapshot_and_config(
    repository: DatasetRepository, config: ImportConfig, valid_csv: bytes
) -> None:
    dataset_id = imported(repository, config, valid_csv)
    engine = AnalysisEngine(repository)
    first = engine.analyze(dataset_id, seed=1, replicates=10)
    second = engine.analyze(dataset_id, seed=1, replicates=10)
    third = engine.analyze(dataset_id, seed=2, replicates=10)
    assert first.analysis_run_id == second.analysis_run_id
    assert first.analysis_run_id != third.analysis_run_id


def test_phase2_api_routes_are_typed_and_honest(
    tmp_path: Path, config: ImportConfig, valid_csv: bytes
) -> None:
    client = TestClient(create_app(Settings(tmp_path / "data", 1024 * 1024)))
    response = client.post(
        "/api/v1/imports",
        files={"file": ("events.csv", valid_csv, "text/csv")},
        data={"config_json": config.model_dump_json()},
    )
    dataset_id = response.json()["dataset_id"]
    query = "?seed=5&replicates=20"
    evidence = client.get(f"/api/v1/datasets/{dataset_id}/evidence{query}")
    assert evidence.status_code == 200
    assert evidence.json()["annotation_event_count"] == 8
    agreement = client.get(f"/api/v1/datasets/{dataset_id}/agreement{query}").json()
    assert agreement["dataset_agreement"]["status"] == "success"
    pairs = client.get(f"/api/v1/datasets/{dataset_id}/agreement/pairs{query}").json()
    assert pairs and all("shared_item_count" in pair for pair in pairs)
    assert client.get(f"/api/v1/datasets/{dataset_id}/agreement/alpha{query}").status_code == 200
    gold = client.get(f"/api/v1/datasets/{dataset_id}/gold-metrics{query}").json()
    assert gold["confusion"]["support"] == 4
    assert client.get(f"/api/v1/datasets/{dataset_id}/confusion{query}").status_code == 200
    assert client.get(f"/api/v1/datasets/{dataset_id}/annotators{query}").status_code == 200
    worker = client.get(f"/api/v1/datasets/{dataset_id}/annotators/worker_01/gold-metrics{query}")
    assert worker.status_code == 200 and worker.json()["annotator_id"] == "worker_01"
    assert client.get(f"/api/v1/datasets/missing/evidence{query}").status_code == 404
    assert client.get(f"/api/v1/datasets/{dataset_id}/evidence?replicates=10001").status_code == 422
