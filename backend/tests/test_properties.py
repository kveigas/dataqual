from __future__ import annotations

from datetime import datetime

import pytest
from dataqual.ingestion.parser import ParsedSource
from dataqual.ingestion.validation import BatchValidationError, validate_and_normalize
from dataqual.schemas.core import AnnotationEvent, utc_timestamp, validate_id
from dataqual.schemas.imports import ImportConfig
from hypothesis import given
from hypothesis import strategies as st


@given(
    st.text(
        alphabet=st.characters(min_codepoint=32, blacklist_characters="\x7f"),
        min_size=1,
        max_size=128,
    )
)
def test_printable_bounded_ids_round_trip(value: str) -> None:
    assert validate_id(value) == value


@given(st.datetimes(timezones=st.timezones()))
def test_aware_timestamps_normalize_to_utc(value: datetime) -> None:
    normalized = utc_timestamp(value.isoformat())
    assert normalized.endswith("Z")
    assert "+" not in normalized


@given(
    st.sampled_from(["positive", "neutral", "negative"]),
    st.integers(min_value=1, max_value=10_000),
)
def test_canonical_serialization_round_trip(label: str, duration: int) -> None:
    event = AnnotationEvent(
        annotation_id="a",
        project_id="p",
        item_id="i",
        annotator_id="w",
        label_domain_id="d",
        label=label,
        event_version=1,
        is_current=True,
        duration_ms=duration,
        annotation_source="human",
        source_import_id="imp",
        source_row_number=1,
    )
    assert AnnotationEvent.model_validate_json(event.model_dump_json()) == event


def _property_config() -> ImportConfig:
    return ImportConfig(
        project_id="p",
        project_name="P",
        label_domain_id="d",
        labels=["yes", "no"],
        dataset_name="D",
        dataset_version="1",
        source_uri="synthetic://property",
        license="CC0",
        redistribution_allowed=True,
        annotation_source_default="human",
    )


@given(st.lists(st.sampled_from(["yes", "no"]), min_size=1, max_size=20))
def test_normalization_is_deterministic_for_fixed_provenance(labels: list[str]) -> None:
    rows = [
        {
            "annotation_id": f"a{index}",
            "item_id": f"i{index}",
            "annotator_id": "w",
            "label": label,
            "event_version": 1,
        }
        for index, label in enumerate(labels)
    ]
    source = ParsedSource("json", "application/json", rows)
    first = validate_and_normalize(source, _property_config(), "imp_fixed", "2026-01-01T00:00:00Z")
    second = validate_and_normalize(source, _property_config(), "imp_fixed", "2026-01-01T00:00:00Z")
    assert first == second


def test_independent_row_order_preserves_logical_events() -> None:
    rows = [
        {
            "annotation_id": "a1",
            "item_id": "i1",
            "annotator_id": "w",
            "label": "yes",
            "event_version": 1,
        },
        {
            "annotation_id": "a2",
            "item_id": "i2",
            "annotator_id": "w",
            "label": "no",
            "event_version": 1,
        },
    ]
    forward = validate_and_normalize(
        ParsedSource("json", "application/json", rows),
        _property_config(),
        "imp",
        "2026-01-01T00:00:00Z",
    )
    reverse = validate_and_normalize(
        ParsedSource("json", "application/json", list(reversed(rows))),
        _property_config(),
        "imp",
        "2026-01-01T00:00:00Z",
    )
    forward_logical = [
        event.model_dump(exclude={"source_row_number"}, mode="json")
        for event in forward.annotations
    ]
    reverse_logical = [
        event.model_dump(exclude={"source_row_number"}, mode="json")
        for event in reverse.annotations
    ]
    assert forward_logical == reverse_logical


@given(st.sampled_from([("yes", "no"), ("no", "yes")]))
def test_conflicting_duplicate_is_always_atomic(labels: tuple[str, str]) -> None:
    rows = [
        {
            "annotation_id": "same",
            "item_id": "i",
            "annotator_id": "w",
            "label": label,
            "event_version": 1,
        }
        for label in labels
    ]
    with pytest.raises(BatchValidationError) as error:
        validate_and_normalize(
            ParsedSource("json", "application/json", rows),
            _property_config(),
            "imp",
            "2026-01-01T00:00:00Z",
        )
    assert "duplicate_annotation_id_conflict" in {issue.code for issue in error.value.issues}


@given(st.integers(min_value=2, max_value=12))
def test_append_only_chain_has_one_current_event(length: int) -> None:
    rows = []
    for version in range(1, length + 1):
        rows.append(
            {
                "annotation_id": f"a{version}",
                "item_id": "i",
                "annotator_id": "w",
                "label": "yes" if version % 2 else "no",
                "event_version": version,
                "supersedes_annotation_id": None if version == 1 else f"a{version - 1}",
            }
        )
    batch = validate_and_normalize(
        ParsedSource("json", "application/json", rows),
        _property_config(),
        "imp",
        "2026-01-01T00:00:00Z",
    )
    assert len(batch.annotations) == length
    assert sum(event.is_current for event in batch.annotations) == 1
    assert next(event for event in batch.annotations if event.is_current).event_version == length
