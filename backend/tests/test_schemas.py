from __future__ import annotations

import math

import pytest
from dataqual.schemas.core import (
    AnnotationEvent,
    DatasetManifest,
    GoldLabel,
    Project,
    ReviewEvent,
    canonical_label,
    utc_timestamp,
    validate_id,
)
from dataqual.schemas.imports import ImportConfig
from pydantic import ValidationError


def annotation(**changes: object) -> AnnotationEvent:
    payload = {
        "annotation_id": "a1",
        "project_id": "p1",
        "item_id": "i1",
        "annotator_id": "w1",
        "label_domain_id": "d1",
        "label": "yes",
        "event_version": 1,
        "is_current": True,
        "annotation_source": "human",
        "source_import_id": "imp1",
        "source_row_number": 1,
    }
    payload.update(changes)
    return AnnotationEvent.model_validate(payload)


def test_id_label_and_timestamp_contracts() -> None:
    assert validate_id("item-1") == "item-1"
    assert canonical_label("café") == "café"
    assert utc_timestamp("2026-01-01T05:30:00+05:30") == "2026-01-01T00:00:00.000000Z"
    for invalid in ("", "bad\nvalue", "x" * 129):
        with pytest.raises(ValueError):
            validate_id(invalid)
    with pytest.raises(ValueError):
        canonical_label(" padded ")
    with pytest.raises(ValueError):
        utc_timestamp("2026-01-01T00:00:00")


def test_project_metadata_and_timezone_validation() -> None:
    project = Project(
        project_id="p",
        name="Project",
        label_domain_id="d",
        created_at="2026-01-01T00:00:00Z",
        default_timezone="UTC",
    )
    assert project.created_at.endswith("Z")
    with pytest.raises(ValidationError):
        Project(
            project_id="p",
            name="Project",
            label_domain_id="d",
            created_at="2026-01-01T00:00:00Z",
            default_timezone="Mars/Olympus",
        )
    with pytest.raises(ValidationError):
        Project(
            project_id="p",
            name="Project",
            label_domain_id="d",
            created_at="2026-01-01T00:00:00Z",
            metadata_json={"bad": math.nan},
        )


def test_annotation_source_and_reannotation_constraints() -> None:
    assert (
        annotation(
            annotation_source="ai_assisted", ai_suggestion="yes", ai_confidence=0.8
        ).ai_confidence
        == 0.8
    )
    invalid = [
        {"supersedes_annotation_id": "a0"},
        {"event_version": 2},
        {"ai_suggestion": "yes"},
        {"ai_confidence": 0.2},
        {"confidence": 1.1},
    ]
    for changes in invalid:
        with pytest.raises(ValidationError):
            annotation(**changes)


def test_gold_hard_distributional_and_unresolved_contracts() -> None:
    base = {
        "gold_label_id": "g1",
        "project_id": "p",
        "item_id": "i",
        "label_domain_id": "d",
        "gold_source": "trusted_reference",
        "version": 1,
        "created_at": "2026-01-01T00:00:00Z",
    }
    assert GoldLabel(**base, resolution_status="resolved_hard", label="yes").label == "yes"
    assert (
        GoldLabel(
            **base,
            resolution_status="resolved_distributional",
            distribution={"yes": 0.7, "no": 0.3},
        ).distribution
        is not None
    )
    assert GoldLabel(**base, resolution_status="unresolved").label is None
    for extra in (
        {"resolution_status": "resolved_hard"},
        {"resolution_status": "resolved_distributional", "distribution": {"yes": 0.5}},
        {"resolution_status": "unresolved", "label": "yes"},
    ):
        with pytest.raises(ValidationError):
            GoldLabel(**base, **extra)
    later = {**base, "version": 2}
    with pytest.raises(ValidationError):
        GoldLabel(**later, resolution_status="resolved_hard", label="yes")


def test_review_and_manifest_models() -> None:
    review = ReviewEvent(
        review_event_id="r",
        project_id="p",
        item_id="i",
        reviewer_id="w",
        strategy_id="manual",
        queue_rank=1,
        outcome="confirmed",
        reason_code="ok",
        decision_timestamp="2026-01-01T00:00:00Z",
        source_snapshot_id="s",
    )
    assert review.queue_rank == 1
    manifest = DatasetManifest(
        dataset_manifest_id="m",
        dataset_name="name",
        dataset_version="1",
        source_uri="synthetic://x",
        license="CC0",
        redistribution_allowed=True,
        raw_checksums={"a.csv": "a" * 64},
        canonical_snapshot_checksum="b" * 64,
        schema_version_used="4.0.0",
        adapter_version="1",
        split_definition={},
        known_limitations=[],
        created_at="2026-01-01T00:00:00Z",
    )
    assert manifest.redistribution_allowed
    with pytest.raises(ValidationError):
        manifest.model_copy(update={"canonical_snapshot_checksum": "bad"}).model_validate(
            manifest.model_copy(update={"canonical_snapshot_checksum": "bad"}).model_dump()
        )


def test_import_config_rejects_duplicate_labels() -> None:
    with pytest.raises(ValidationError):
        ImportConfig(
            project_id="p",
            project_name="P",
            label_domain_id="d",
            labels=["yes", "yes"],
            dataset_name="D",
            dataset_version="1",
            source_uri="x",
            license="CC0",
            redistribution_allowed=True,
        )
