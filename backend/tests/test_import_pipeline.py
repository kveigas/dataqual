from __future__ import annotations

import pytest
from conftest import FIXTURES
from dataqual.descriptive import DescriptiveQueries
from dataqual.ingestion import ImportLimitError, ImportService
from dataqual.schemas.imports import ImportConfig, ImportStatus
from dataqual.storage import DatasetRepository


def test_valid_csv_is_preserved_deduplicated_and_queryable(
    service: ImportService, repository: DatasetRepository, config: ImportConfig, valid_csv: bytes
) -> None:
    record = service.import_bytes("..\\unsafe name.csv", valid_csv, config)
    assert record.status == ImportStatus.ACCEPTED
    assert (record.input_rows, record.accepted_rows, record.rejected_rows) == (10, 10, 0)
    assert record.duplicate_identical_occurrences == 1
    raw = repository.raw_root / record.import_id / record.stored_filename
    assert raw.read_bytes() == valid_csv
    assert raw.stat().st_mode & 0o222 == 0
    assert record.input_rows == record.accepted_rows + record.rejected_rows
    assert "unsafe_name.csv" in record.stored_filename
    assert repository.get_import(record.import_id) == record
    assert record.dataset_id is not None
    summary = DescriptiveQueries(repository).summary(record.dataset_id)
    assert summary is not None
    assert (summary.annotation_events, summary.current_annotation_events) == (9, 8)
    assert (summary.unique_items, summary.unique_annotators, summary.label_classes) == (4, 3, 3)
    assert summary.class_counts == {"negative": 3, "neutral": 4, "positive": 1}
    assert summary.gold_items == 2 and summary.gold_coverage == 0.5
    assert summary.coannotated_items == 3
    history = DescriptiveQueries(repository).annotation_history(
        record.dataset_id, "item_001", "worker_01"
    )
    assert [event["event_version"] for event in history] == [1, 2]
    assert [event["is_current"] for event in history] == [False, True]
    provenance = repository.provenance(record.dataset_id, "test")
    assert provenance is not None and provenance.raw_sha256 == record.raw_sha256
    assert len(provenance.artifact_files) == 7


def test_valid_json_and_empty_gold_table(
    service: ImportService, repository: DatasetRepository, config: ImportConfig
) -> None:
    no_gold = (
        b'[{"annotation_id":"j1","item_id":"i1","annotator_id":"w1",'
        b'"label":"positive","event_version":1,"annotation_source":"human"}]'
    )
    record = service.import_bytes("events.json", no_gold, config)
    assert record.dataset_id
    summary = DescriptiveQueries(repository).summary(record.dataset_id)
    assert summary is not None and summary.gold_items == 0


@pytest.mark.parametrize(
    "fixture,code",
    [
        ("invalid_unknown_label.csv", "unknown_label"),
        ("invalid_duplicate_conflict.csv", "duplicate_annotation_id_conflict"),
        ("invalid_reannotation_branch.csv", "duplicate_identity_conflict"),
        ("invalid_timestamp.csv", "schema_validation"),
        ("invalid_missing_item.csv", "schema_validation"),
        ("invalid_confidence.csv", "schema_validation"),
        ("invalid_reannotation_cycle.csv", "reannotation_cycle"),
    ],
)
def test_invalid_batch_is_atomic_and_raw_is_retained(
    service: ImportService,
    repository: DatasetRepository,
    config: ImportConfig,
    fixture: str,
    code: str,
) -> None:
    content = (FIXTURES / fixture).read_bytes()
    record = service.import_bytes(fixture, content, config)
    assert record.status == ImportStatus.REJECTED
    assert record.accepted_rows == 0 and record.rejected_rows == record.input_rows
    assert record.input_rows == record.accepted_rows + record.rejected_rows
    assert code in {issue.code for issue in record.issues}
    assert repository.list_datasets() == []
    assert (repository.raw_root / record.import_id / record.stored_filename).read_bytes() == content


def test_parse_rejection_and_preflight_limits(
    service: ImportService, repository: DatasetRepository, config: ImportConfig
) -> None:
    malformed = service.import_bytes("broken.json", b"{", config)
    assert malformed.status == ImportStatus.REJECTED
    assert malformed.issues[0].code == "source_parse"
    with pytest.raises(ImportLimitError):
        service.import_bytes("x.txt", b"x", config)
    with pytest.raises(ImportLimitError):
        service.import_bytes("x.csv", b"", config)
    tiny = ImportService(repository, 2)
    with pytest.raises(ImportLimitError):
        tiny.import_bytes("x.csv", b"abc", config)


def test_storage_failure_rejects_without_publishing(
    service: ImportService,
    repository: DatasetRepository,
    config: ImportConfig,
    valid_csv: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(**_kwargs: object) -> None:
        raise OSError("simulated")

    monkeypatch.setattr(repository, "commit_snapshot", fail)
    record = service.import_bytes("events.csv", valid_csv, config)
    assert record.status == ImportStatus.REJECTED
    assert record.issues[0].code == "storage_transaction_failed"
    assert repository.list_datasets() == []


def test_unknown_dataset_queries(repository: DatasetRepository) -> None:
    queries = DescriptiveQueries(repository)
    assert queries.summary("missing") is None
    assert queries.annotation_history("missing", "i", "w") == []
    assert repository.get_dataset("missing") is None
    assert repository.provenance("missing", "test") is None
