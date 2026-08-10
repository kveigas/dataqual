from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from dataqual.ingestion.parser import ParsedSource, SourceParseError, csv_value
from dataqual.schemas.core import (
    AnnotationEvent,
    Annotator,
    GoldLabel,
    Item,
    LabelDomain,
    Project,
    canonical_label,
)
from dataqual.schemas.imports import ImportConfig, ValidationIssue


@dataclass(frozen=True)
class CanonicalBatch:
    project: Project
    label_domain: LabelDomain
    items: list[Item]
    annotators: list[Annotator]
    annotations: list[AnnotationEvent]
    gold_labels: list[GoldLabel]
    input_rows: int
    duplicate_identical_occurrences: int


class BatchValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue], input_rows: int) -> None:
        super().__init__("import validation failed")
        self.issues = issues
        self.input_rows = input_rows


def _issue(row: int | None, code: str, message: str, field: str | None = None) -> ValidationIssue:
    return ValidationIssue(source_row_number=row, code=code, field=field, message=message)


def _gold_id(project_id: str, item_id: str) -> str:
    digest = hashlib.sha256(f"{project_id}|{item_id}|gold|1".encode()).hexdigest()[:24]
    return f"gold_{digest}"


def _value(row: dict[str, Any], field: str, kind: type[Any], source_format: str) -> Any:
    if source_format == "csv":
        return csv_value(row, field, kind)
    value = row.get(field)
    if value is None:
        return None
    if kind is float and type(value) not in (int, float):
        raise SourceParseError(f"{field} must be a JSON number")
    if kind is int and type(value) is not int:
        raise SourceParseError(f"{field} must be a JSON integer")
    if kind is dict and type(value) is not dict:
        raise SourceParseError(f"{field} must be a JSON object")
    if kind is str and type(value) is not str:
        raise SourceParseError(f"{field} must be a JSON string")
    return value


def _annotation_payload(
    row: dict[str, Any], row_number: int, parsed: ParsedSource, config: ImportConfig, import_id: str
) -> dict[str, Any]:
    for relation_field, expected in (
        ("project_id", config.project_id),
        ("label_domain_id", config.label_domain_id),
        ("schema_version", config.schema_version),
    ):
        supplied = _value(row, relation_field, str, parsed.source_format)
        if supplied is not None and supplied != expected:
            raise SourceParseError(f"{relation_field} conflicts with import configuration")
    annotation_source = _value(row, "annotation_source", str, parsed.source_format)
    if annotation_source is None:
        annotation_source = config.annotation_source_default
    return {
        "schema_version": config.schema_version,
        "annotation_id": _value(row, "annotation_id", str, parsed.source_format),
        "project_id": config.project_id,
        "item_id": _value(row, "item_id", str, parsed.source_format),
        "annotator_id": _value(row, "annotator_id", str, parsed.source_format),
        "label_domain_id": config.label_domain_id,
        "label": _value(row, "label", str, parsed.source_format),
        "event_version": _value(row, "event_version", int, parsed.source_format),
        "supersedes_annotation_id": _value(
            row, "supersedes_annotation_id", str, parsed.source_format
        ),
        "is_current": True,
        "timestamp": _value(row, "timestamp", str, parsed.source_format),
        "confidence": _value(row, "confidence", float, parsed.source_format),
        "duration_ms": _value(row, "duration_ms", int, parsed.source_format),
        "annotation_source": annotation_source,
        "ai_suggestion": _value(row, "ai_suggestion", str, parsed.source_format),
        "ai_confidence": _value(row, "ai_confidence", float, parsed.source_format),
        "metadata_json": _value(row, "metadata_json", dict, parsed.source_format) or {},
        "source_import_id": import_id,
        "source_row_number": row_number,
    }


def _logical_annotation(event: AnnotationEvent) -> dict[str, Any]:
    return event.model_dump(exclude={"source_row_number", "is_current"}, mode="json")


def _deduplicate(
    events: list[AnnotationEvent],
) -> tuple[list[AnnotationEvent], int, list[ValidationIssue]]:
    retained: list[AnnotationEvent] = []
    by_annotation: dict[str, AnnotationEvent] = {}
    by_identity: dict[tuple[str, str, str, str, int], AnnotationEvent] = {}
    duplicates = 0
    issues: list[ValidationIssue] = []
    for event in events:
        identity = (
            event.project_id,
            event.item_id,
            event.annotator_id,
            event.label_domain_id,
            event.event_version,
        )
        prior_id = by_annotation.get(event.annotation_id)
        prior_identity = by_identity.get(identity)
        if prior_id is not None:
            if _logical_annotation(prior_id) == _logical_annotation(event):
                duplicates += 1
                continue
            issues.append(
                _issue(
                    event.source_row_number,
                    "duplicate_annotation_id_conflict",
                    "annotation_id has conflicting canonical content",
                    "annotation_id",
                )
            )
            continue
        if prior_identity is not None:
            issues.append(
                _issue(
                    event.source_row_number,
                    "duplicate_identity_conflict",
                    "worker/item/domain/version identity has conflicting canonical content",
                )
            )
            continue
        by_annotation[event.annotation_id] = event
        by_identity[identity] = event
        retained.append(event)
    return retained, duplicates, issues


def _validate_chains(events: list[AnnotationEvent]) -> list[ValidationIssue]:
    by_id = {event.annotation_id: event for event in events}
    children: dict[str, list[AnnotationEvent]] = {}
    issues: list[ValidationIssue] = []
    for event in events:
        parent_id = event.supersedes_annotation_id
        if parent_id is None:
            continue
        parent = by_id.get(parent_id)
        if parent is None:
            issues.append(
                _issue(
                    event.source_row_number,
                    "missing_reannotation_parent",
                    "superseded annotation does not exist",
                    "supersedes_annotation_id",
                )
            )
            continue
        if (parent.project_id, parent.item_id, parent.annotator_id, parent.label_domain_id) != (
            event.project_id,
            event.item_id,
            event.annotator_id,
            event.label_domain_id,
        ):
            issues.append(
                _issue(
                    event.source_row_number,
                    "reannotation_relationship_conflict",
                    "reannotation parent must have the same project/item/annotator/domain",
                )
            )
        if event.event_version != parent.event_version + 1:
            issues.append(
                _issue(
                    event.source_row_number,
                    "illegal_reannotation_version",
                    "event_version must be parent version + 1",
                    "event_version",
                )
            )
        children.setdefault(parent_id, []).append(event)
    for parent_id, descendants in children.items():
        if len(descendants) > 1:
            issues.append(
                _issue(
                    None,
                    "reannotation_branch_conflict",
                    f"annotation {parent_id} has multiple active descendants",
                )
            )

    for event in events:
        visited: set[str] = set()
        current = event
        while current.supersedes_annotation_id is not None:
            if current.annotation_id in visited:
                issues.append(
                    _issue(
                        event.source_row_number,
                        "reannotation_cycle",
                        "reannotation chain contains a cycle",
                    )
                )
                break
            visited.add(current.annotation_id)
            parent = by_id.get(current.supersedes_annotation_id)
            if parent is None:
                break
            current = parent
    return issues


def _derive_current(events: list[AnnotationEvent]) -> list[AnnotationEvent]:
    superseded = {
        event.supersedes_annotation_id for event in events if event.supersedes_annotation_id
    }
    return [
        event.model_copy(update={"is_current": event.annotation_id not in superseded})
        for event in events
    ]


def validate_and_normalize(
    parsed: ParsedSource, config: ImportConfig, import_id: str, import_timestamp: str
) -> CanonicalBatch:
    issues: list[ValidationIssue] = []
    parsed_events: list[AnnotationEvent] = []
    raw_rows: dict[int, dict[str, Any]] = {}
    for row_number, row in enumerate(parsed.rows, start=1):
        raw_rows[row_number] = row
        try:
            parsed_events.append(
                AnnotationEvent.model_validate(
                    _annotation_payload(row, row_number, parsed, config, import_id)
                )
            )
        except (ValidationError, SourceParseError) as exc:
            if isinstance(exc, ValidationError):
                for error in exc.errors(include_url=False):
                    field = ".".join(str(part) for part in error["loc"])
                    issues.append(_issue(row_number, "schema_validation", error["msg"], field))
            else:
                issues.append(_issue(row_number, "source_value_invalid", str(exc)))

    if issues:
        raise BatchValidationError(issues, len(parsed.rows))
    events, duplicate_count, duplicate_issues = _deduplicate(parsed_events)
    issues.extend(duplicate_issues)
    issues.extend(_validate_chains(events))
    label_set = set(config.labels)
    for event in events:
        if event.label not in label_set:
            issues.append(
                _issue(
                    event.source_row_number,
                    "unknown_label",
                    f"label {event.label!r} is not in the registered domain",
                    "label",
                )
            )
        if event.ai_suggestion is not None and event.ai_suggestion not in label_set:
            issues.append(
                _issue(
                    event.source_row_number,
                    "unknown_ai_suggestion",
                    "ai_suggestion is not in the registered domain",
                    "ai_suggestion",
                )
            )

    items: dict[str, Item] = {}
    annotators: dict[str, Annotator] = {}
    gold: dict[str, GoldLabel] = {}
    for event in events:
        row = raw_rows[event.source_row_number]
        item = Item(
            project_id=config.project_id,
            item_id=event.item_id,
            label_domain_id=config.label_domain_id,
            content_ref=_value(row, "content_ref", str, parsed.source_format),
            task_family=_value(row, "task_family", str, parsed.source_format),
            severity_weight=_value(row, "severity_weight", float, parsed.source_format) or 1.0,
            expected_review_cost=_value(row, "expected_review_cost", float, parsed.source_format)
            or 1.0,
            metadata_json=_value(row, "item_metadata_json", dict, parsed.source_format) or {},
            source_import_id=import_id,
        )
        prior_item = items.get(item.item_id)
        if prior_item is not None and prior_item != item:
            issues.append(
                _issue(
                    event.source_row_number,
                    "item_definition_conflict",
                    "item fields conflict across source rows",
                    "item_id",
                )
            )
        items[item.item_id] = prior_item or item

        annotator = Annotator(
            project_id=config.project_id,
            annotator_id=event.annotator_id,
            role=_value(row, "annotator_role", str, parsed.source_format),
            team=_value(row, "annotator_team", str, parsed.source_format),
            language=_value(row, "annotator_language", str, parsed.source_format),
            specialty=_value(row, "annotator_specialty", str, parsed.source_format),
            source_import_id=import_id,
        )
        prior_annotator = annotators.get(annotator.annotator_id)
        if prior_annotator is not None and prior_annotator != annotator:
            issues.append(
                _issue(
                    event.source_row_number,
                    "annotator_definition_conflict",
                    "annotator fields conflict across source rows",
                    "annotator_id",
                )
            )
        annotators[annotator.annotator_id] = prior_annotator or annotator

        gold_value = _value(row, "gold_label", str, parsed.source_format)
        if gold_value is not None:
            try:
                gold_value = canonical_label(gold_value)
            except ValueError as exc:
                issues.append(
                    _issue(event.source_row_number, "invalid_gold_label", str(exc), "gold_label")
                )
                continue
            if gold_value not in label_set:
                issues.append(
                    _issue(
                        event.source_row_number,
                        "unknown_gold_label",
                        "gold_label is not in the registered domain",
                        "gold_label",
                    )
                )
                continue
            gold_source = _value(row, "gold_source", str, parsed.source_format)
            if gold_source is None:
                issues.append(
                    _issue(
                        event.source_row_number,
                        "missing_gold_source",
                        "gold_source is required when gold_label is present",
                        "gold_source",
                    )
                )
                continue
            created_at = (
                _value(row, "gold_created_at", str, parsed.source_format) or import_timestamp
            )
            candidate = GoldLabel(
                gold_label_id=_gold_id(config.project_id, event.item_id),
                project_id=config.project_id,
                item_id=event.item_id,
                label_domain_id=config.label_domain_id,
                label=gold_value,
                resolution_status="resolved_hard",
                gold_source=gold_source,
                version=1,
                created_at=created_at,
                source_import_id=import_id,
            )
            prior_gold = gold.get(event.item_id)
            if prior_gold is not None and prior_gold != candidate:
                issues.append(
                    _issue(
                        event.source_row_number,
                        "gold_definition_conflict",
                        "gold label conflicts across source rows",
                        "gold_label",
                    )
                )
            gold[event.item_id] = prior_gold or candidate

    if issues:
        raise BatchValidationError(issues, len(parsed.rows))
    project = Project(
        project_id=config.project_id,
        name=config.project_name,
        label_domain_id=config.label_domain_id,
        default_timezone=config.default_timezone,
        created_at=import_timestamp,
    )
    domain = LabelDomain(
        label_domain_id=config.label_domain_id,
        project_id=config.project_id,
        labels=config.labels,
        created_at=import_timestamp,
    )
    return CanonicalBatch(
        project=project,
        label_domain=domain,
        items=sorted(items.values(), key=lambda item: item.item_id),
        annotators=sorted(annotators.values(), key=lambda annotator: annotator.annotator_id),
        annotations=sorted(_derive_current(events), key=lambda event: event.annotation_id),
        gold_labels=sorted(gold.values(), key=lambda label: label.item_id),
        input_rows=len(parsed.rows),
        duplicate_identical_occurrences=duplicate_count,
    )
