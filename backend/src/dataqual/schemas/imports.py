from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from dataqual.schemas.core import SCHEMA_VERSION, canonical_label, utc_timestamp, validate_id


class ImportStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ImportConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["4.0.0"] = SCHEMA_VERSION
    project_id: str
    project_name: str = Field(min_length=1, max_length=200)
    label_domain_id: str
    labels: list[str] = Field(min_length=2, max_length=100)
    dataset_name: str = Field(min_length=1, max_length=200)
    dataset_version: str = Field(min_length=1, max_length=64)
    source_uri: str = Field(min_length=1, max_length=2048)
    license: str = Field(min_length=1, max_length=128)
    redistribution_allowed: bool
    annotation_source_default: Literal["human", "ai_assisted", "model", "gold_import"] | None = None
    default_timezone: str | None = None

    _ids = field_validator("project_id", "label_domain_id")(validate_id)

    @field_validator("labels")
    @classmethod
    def canonical_unique_labels(cls, labels: list[str]) -> list[str]:
        normalized = [canonical_label(label) for label in labels]
        if len(set(normalized)) != len(normalized):
            raise ValueError("labels must be unique")
        return normalized


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source_row_number: int | None = None
    code: str
    field: str | None = None
    message: str
    fatal: bool = True


class ImportRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["4.0.0"] = SCHEMA_VERSION
    import_id: str
    status: ImportStatus
    original_filename: str
    stored_filename: str
    source_format: Literal["csv", "json"]
    detected_mime: str
    size_bytes: int
    raw_sha256: str
    import_timestamp: str
    project_id: str
    input_rows: int
    accepted_rows: int
    rejected_rows: int
    duplicate_identical_occurrences: int
    dataset_id: str | None = None
    canonical_artifact_path: str | None = None
    issues: list[ValidationIssue] = Field(default_factory=list)

    _import_id = field_validator("import_id", "project_id")(validate_id)
    _timestamp = field_validator("import_timestamp")(utc_timestamp)


class DatasetSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["4.0.0"] = SCHEMA_VERSION
    dataset_id: str
    annotation_events: int
    current_annotation_events: int
    unique_items: int
    unique_annotators: int
    label_classes: int
    annotations_by_annotator_top: dict[str, int]
    annotations_by_item_top: dict[str, int]
    class_counts: dict[str, int]
    missing_optional_fields: dict[str, int]
    gold_items: int
    gold_coverage: float
    coannotated_items: int


class DatasetDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["4.0.0"] = SCHEMA_VERSION
    dataset_id: str
    dataset_name: str
    dataset_version: str
    project_id: str
    import_id: str
    created_at: str
    canonical_snapshot_checksum: str


class ProvenanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["4.0.0"] = SCHEMA_VERSION
    dataset_id: str
    import_id: str
    project_id: str
    raw_sha256: str
    canonical_snapshot_checksum: str
    schema_version_used: str
    transformation_version: str
    input_rows: int
    accepted_rows: int
    rejected_rows: int
    import_timestamp: str
    original_filename: str
    source_format: str
    software_version: str
    git_commit: str | None
    git_dirty: bool | None
    artifact_files: dict[str, str]
    warnings: list[str]
