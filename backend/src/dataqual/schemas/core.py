from __future__ import annotations

import json
import math
import re
import unicodedata
from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "4.0.0"
ID_PATTERN = re.compile(r"^[^\x00-\x1f\x7f]{1,128}$")
Metadata = dict[str, Any]
CanonicalLabel = Annotated[str, Field(min_length=1, max_length=256)]


def validate_id(value: str) -> str:
    if not ID_PATTERN.fullmatch(value):
        raise ValueError("ID must be 1-128 characters and contain no control characters")
    return value


def validate_metadata(value: Metadata) -> Metadata:
    try:
        encoded = json.dumps(value, allow_nan=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("metadata_json must be finite JSON data") from exc
    if len(encoded) > 65_536:
        raise ValueError("metadata_json exceeds 64 KiB")
    return value


def canonical_label(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    if not normalized:
        raise ValueError("label must not be empty")
    if normalized != normalized.strip():
        raise ValueError("label must not contain leading or trailing whitespace")
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ValueError("label contains a control character")
    return normalized


def utc_timestamp(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp must be an RFC 3339 string")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError("timestamp must be valid RFC 3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include an explicit offset")
    normalized = parsed.astimezone(UTC)
    return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")


class CanonicalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["4.0.0"] = SCHEMA_VERSION


class Project(CanonicalModel):
    project_id: str
    name: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str | None, Field(max_length=4000)] = None
    annotation_type: Literal["categorical_single_label"] = "categorical_single_label"
    label_domain_id: str
    default_timezone: str | None = None
    created_at: str
    metadata_json: Metadata = Field(default_factory=dict)

    _project_id = field_validator("project_id")(validate_id)
    _label_domain_id = field_validator("label_domain_id")(validate_id)
    _created_at = field_validator("created_at")(utc_timestamp)
    _metadata = field_validator("metadata_json")(validate_metadata)

    @field_validator("default_timezone")
    @classmethod
    def timezone_exists(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("default_timezone must be a valid IANA timezone") from exc
        return value


class LabelDomain(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    label_domain_id: str
    project_id: str
    version: Annotated[int, Field(ge=1)] = 1
    labels: Annotated[list[CanonicalLabel], Field(min_length=2, max_length=100)]
    display_names: dict[str, str] = Field(default_factory=dict)
    created_at: str
    supersedes_label_domain_id: str | None = None

    _label_domain_id = field_validator("label_domain_id")(validate_id)
    _project_id = field_validator("project_id")(validate_id)
    _supersedes = field_validator("supersedes_label_domain_id")(
        lambda value: validate_id(value) if value else value
    )
    _created_at = field_validator("created_at")(utc_timestamp)
    _labels = field_validator("labels")(lambda labels: [canonical_label(label) for label in labels])

    @model_validator(mode="after")
    def unique_labels_and_aliases(self) -> LabelDomain:
        if len(set(self.labels)) != len(self.labels):
            raise ValueError("labels must be unique")
        if not set(self.display_names).issubset(self.labels):
            raise ValueError("display_names contains an unknown canonical label")
        return self


class Item(CanonicalModel):
    project_id: str
    item_id: str
    label_domain_id: str
    content_ref: Annotated[str | None, Field(max_length=2048)] = None
    task_family: Annotated[str | None, Field(max_length=128)] = None
    severity_weight: Annotated[float, Field(gt=0, le=100)] = 1.0
    expected_review_cost: Annotated[float, Field(gt=0)] = 1.0
    metadata_json: Metadata = Field(default_factory=dict)
    source_import_id: str

    _ids = field_validator("project_id", "item_id", "label_domain_id", "source_import_id")(
        validate_id
    )
    _metadata = field_validator("metadata_json")(validate_metadata)


class AnnotationEvent(CanonicalModel):
    annotation_id: str
    project_id: str
    item_id: str
    annotator_id: str
    label_domain_id: str
    label: CanonicalLabel
    event_version: Annotated[int, Field(ge=1)]
    supersedes_annotation_id: str | None = None
    is_current: bool
    timestamp: str | None = None
    confidence: Annotated[float | None, Field(ge=0, le=1)] = None
    duration_ms: Annotated[int | None, Field(ge=0, le=86_400_000)] = None
    annotation_source: Literal["human", "ai_assisted", "model", "gold_import"]
    ai_suggestion: str | None = None
    ai_confidence: Annotated[float | None, Field(ge=0, le=1)] = None
    metadata_json: Metadata = Field(default_factory=dict)
    source_import_id: str
    source_row_number: Annotated[int, Field(ge=1)]

    _ids = field_validator(
        "annotation_id",
        "project_id",
        "item_id",
        "annotator_id",
        "label_domain_id",
        "source_import_id",
    )(validate_id)
    _parent_id = field_validator("supersedes_annotation_id")(
        lambda value: validate_id(value) if value is not None else value
    )
    _label = field_validator("label")(canonical_label)
    _timestamp = field_validator("timestamp")(
        lambda value: utc_timestamp(value) if value is not None else value
    )
    _metadata = field_validator("metadata_json")(validate_metadata)

    @model_validator(mode="after")
    def source_consistency(self) -> AnnotationEvent:
        if self.event_version == 1 and self.supersedes_annotation_id is not None:
            raise ValueError("version 1 annotation cannot supersede another event")
        if self.event_version > 1 and self.supersedes_annotation_id is None:
            raise ValueError("reannotation requires supersedes_annotation_id")
        if self.annotation_source != "ai_assisted" and self.ai_suggestion is not None:
            raise ValueError("ai_suggestion is allowed only for ai_assisted events")
        if self.ai_confidence is not None and self.ai_suggestion is None:
            raise ValueError("ai_confidence requires ai_suggestion")
        if self.ai_suggestion is not None:
            canonical_label(self.ai_suggestion)
        return self


class Annotator(CanonicalModel):
    project_id: str
    annotator_id: str
    role: Annotated[str | None, Field(max_length=128)] = None
    team: Annotated[str | None, Field(max_length=128)] = None
    tenure_start: date | None = None
    language: Annotated[str | None, Field(max_length=128)] = None
    specialty: Annotated[str | None, Field(max_length=128)] = None
    active: bool = True
    metadata_json: Metadata = Field(default_factory=dict)
    source_import_id: str

    _ids = field_validator("project_id", "annotator_id", "source_import_id")(validate_id)
    _metadata = field_validator("metadata_json")(validate_metadata)


class GoldLabel(CanonicalModel):
    gold_label_id: str
    project_id: str
    item_id: str
    label_domain_id: str
    label: str | None = None
    distribution: dict[str, float] | None = None
    resolution_status: Literal["resolved_hard", "resolved_distributional", "unresolved"]
    gold_source: Literal[
        "expert_adjudication", "trusted_reference", "benchmark_truth", "simulation_truth"
    ]
    version: Annotated[int, Field(ge=1)]
    supersedes_gold_label_id: str | None = None
    created_at: str
    source_import_id: str | None = None
    metadata_json: Metadata = Field(default_factory=dict)

    _ids = field_validator("gold_label_id", "project_id", "item_id", "label_domain_id")(validate_id)
    _optional_ids = field_validator("supersedes_gold_label_id", "source_import_id")(
        lambda value: validate_id(value) if value else value
    )
    _label = field_validator("label")(
        lambda value: canonical_label(value) if value is not None else value
    )
    _created_at = field_validator("created_at")(utc_timestamp)
    _metadata = field_validator("metadata_json")(validate_metadata)

    @model_validator(mode="after")
    def gold_consistency(self) -> GoldLabel:
        if self.version == 1 and self.supersedes_gold_label_id is not None:
            raise ValueError("gold version 1 cannot supersede another record")
        if self.version > 1 and self.supersedes_gold_label_id is None:
            raise ValueError("later gold version requires supersedes_gold_label_id")
        if self.resolution_status == "resolved_hard":
            if self.label is None or self.distribution is not None:
                raise ValueError("resolved_hard requires only a hard label")
        elif self.resolution_status == "resolved_distributional":
            if self.distribution is None or self.label is not None:
                raise ValueError("resolved_distributional requires only a distribution")
            if any(not math.isfinite(value) or value < 0 for value in self.distribution.values()):
                raise ValueError("gold distribution values must be finite and nonnegative")
            if abs(sum(self.distribution.values()) - 1.0) > 1e-9:
                raise ValueError("gold distribution must sum to one within 1e-9")
        elif self.label is not None or self.distribution is not None:
            raise ValueError("unresolved gold cannot contain a label or distribution")
        return self


class ReviewEvent(CanonicalModel):
    review_event_id: str
    project_id: str
    item_id: str
    reviewer_id: str
    strategy_id: str
    queue_rank: Annotated[int, Field(ge=1)]
    review_budget_fraction: Annotated[float | None, Field(gt=0, le=1)] = None
    pre_review_label: str | None = None
    post_review_label: str | None = None
    post_review_distribution: dict[str, float] | None = None
    outcome: Literal["confirmed", "corrected", "unresolved", "policy_issue"]
    reason_code: str
    decision_timestamp: str
    review_duration_ms: Annotated[int | None, Field(ge=0)] = None
    source_snapshot_id: str
    metadata_json: Metadata = Field(default_factory=dict)

    _ids = field_validator(
        "review_event_id",
        "project_id",
        "item_id",
        "reviewer_id",
        "strategy_id",
        "reason_code",
        "source_snapshot_id",
    )(validate_id)
    _labels = field_validator("pre_review_label", "post_review_label")(
        lambda value: canonical_label(value) if value is not None else value
    )
    _timestamp = field_validator("decision_timestamp")(utc_timestamp)
    _metadata = field_validator("metadata_json")(validate_metadata)


class DatasetManifest(CanonicalModel):
    dataset_manifest_id: str
    dataset_name: str
    dataset_version: str
    source_uri: str
    license: str
    redistribution_allowed: bool
    raw_checksums: dict[str, str]
    canonical_snapshot_checksum: str
    schema_version_used: str
    adapter_version: str
    split_definition: Metadata
    known_limitations: list[str]
    created_at: str

    _id = field_validator("dataset_manifest_id")(validate_id)
    _created_at = field_validator("created_at")(utc_timestamp)

    @field_validator("raw_checksums")
    @classmethod
    def checksums_are_sha256(cls, value: dict[str, str]) -> dict[str, str]:
        if not value or any(
            not re.fullmatch(r"[0-9a-f]{64}", checksum) for checksum in value.values()
        ):
            raise ValueError("raw_checksums must contain lowercase SHA-256 values")
        return value

    @field_validator("canonical_snapshot_checksum")
    @classmethod
    def canonical_checksum_is_sha256(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("canonical_snapshot_checksum must be lowercase SHA-256")
        return value
