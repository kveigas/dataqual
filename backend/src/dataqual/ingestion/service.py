from __future__ import annotations

from dataqual.ingestion.parser import SUPPORTED_EXTENSIONS, SourceParseError, parse_source
from dataqual.ingestion.validation import BatchValidationError, validate_and_normalize
from dataqual.provenance import sha256_bytes
from dataqual.schemas.imports import (
    ImportConfig,
    ImportRecord,
    ImportStatus,
    ValidationIssue,
)
from dataqual.storage import DatasetRepository, new_id, utc_now


class ImportLimitError(ValueError):
    pass


class ImportService:
    def __init__(self, repository: DatasetRepository, max_upload_bytes: int) -> None:
        self.repository = repository
        self.max_upload_bytes = max_upload_bytes

    def import_bytes(self, filename: str, content: bytes, config: ImportConfig) -> ImportRecord:
        if not content:
            raise ImportLimitError("import source is empty")
        if len(content) > self.max_upload_bytes:
            raise ImportLimitError(
                f"import exceeds configured limit of {self.max_upload_bytes} bytes"
            )
        extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        source_format = SUPPORTED_EXTENSIONS.get(extension)
        if source_format is None:
            raise ImportLimitError("only .csv and .json imports are supported")

        import_id = new_id("imp")
        imported_at = utc_now()
        raw_path, stored_filename = self.repository.preserve_raw(
            import_id, filename, source_format, content
        )
        raw_sha256 = sha256_bytes(content)
        base = {
            "import_id": import_id,
            "original_filename": filename,
            "stored_filename": stored_filename,
            "source_format": source_format,
            "detected_mime": "text/csv" if source_format == "csv" else "application/json",
            "size_bytes": len(content),
            "raw_sha256": raw_sha256,
            "import_timestamp": imported_at,
            "project_id": config.project_id,
        }
        try:
            parsed = parse_source(filename, raw_path.read_bytes())
            batch = validate_and_normalize(parsed, config, import_id, imported_at)
        except SourceParseError as exc:
            record = ImportRecord(
                **base,
                status=ImportStatus.REJECTED,
                input_rows=0,
                accepted_rows=0,
                rejected_rows=0,
                duplicate_identical_occurrences=0,
                issues=[ValidationIssue(code="source_parse", message=str(exc))],
            )
            self.repository.save_import_record(record)
            return record
        except BatchValidationError as exc:
            record = ImportRecord(
                **base,
                status=ImportStatus.REJECTED,
                input_rows=exc.input_rows,
                accepted_rows=0,
                rejected_rows=exc.input_rows,
                duplicate_identical_occurrences=0,
                issues=exc.issues,
            )
            self.repository.save_import_record(record)
            return record

        provisional = ImportRecord(
            **base,
            status=ImportStatus.ACCEPTED,
            input_rows=batch.input_rows,
            accepted_rows=batch.input_rows,
            rejected_rows=0,
            duplicate_identical_occurrences=batch.duplicate_identical_occurrences,
        )
        try:
            dataset_id, _, artifact_path, _ = self.repository.commit_snapshot(
                import_record=provisional,
                dataset_name=config.dataset_name,
                dataset_version=config.dataset_version,
                source_uri=config.source_uri,
                license_name=config.license,
                redistribution_allowed=config.redistribution_allowed,
                project=batch.project,
                label_domain=batch.label_domain,
                items=batch.items,
                annotators=batch.annotators,
                annotations=batch.annotations,
                gold_labels=batch.gold_labels,
            )
        except Exception as exc:
            rejected = provisional.model_copy(
                update={
                    "status": ImportStatus.REJECTED,
                    "accepted_rows": 0,
                    "rejected_rows": batch.input_rows,
                    "issues": [
                        ValidationIssue(
                            code="storage_transaction_failed",
                            message=f"canonical publication failed: {type(exc).__name__}",
                        )
                    ],
                }
            )
            self.repository.save_import_record(rejected)
            return rejected

        accepted = provisional.model_copy(
            update={"dataset_id": dataset_id, "canonical_artifact_path": artifact_path}
        )
        self.repository.save_import_record(accepted)
        return accepted
