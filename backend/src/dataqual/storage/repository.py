from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel

from dataqual.provenance import canonical_json_bytes, git_identity, sha256_bytes, sha256_file
from dataqual.schemas.core import DatasetManifest
from dataqual.schemas.imports import DatasetDetail, ImportRecord, ProvenanceResponse

TRANSFORMATION_VERSION = "phase1-canonical-1.0.0"
SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


class StorageError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def sanitize_filename(filename: str, source_format: str) -> str:
    leaf = Path(filename.replace("\\", "/")).name
    cleaned = SAFE_FILENAME.sub("_", leaf).strip("._")
    extension = f".{source_format}"
    if not cleaned:
        cleaned = f"source{extension}"
    if not cleaned.lower().endswith(extension):
        cleaned += extension
    return cleaned[:180]


def _portable(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _storage_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return canonical_json_bytes(value).decode("utf-8")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _rows(models: Sequence[BaseModel]) -> list[dict[str, Any]]:
    return [
        {key: _storage_value(value) for key, value in model.model_dump(mode="python").items()}
        for model in models
    ]


def _write_models(path: Path, models: Sequence[BaseModel]) -> None:
    rows = _rows(models)
    if not rows:
        # Stable empty artifact with an explicit marker column; consumers use counts
        # and never infer a canonical schema from an empty optional table.
        table = pa.table({"_empty": pa.array([], type=pa.bool_())})
    else:
        table = pa.Table.from_pylist(rows)
    pq.write_table(table, path, compression="zstd", use_dictionary=True)


class DatasetRepository:
    def __init__(self, data_root: Path) -> None:
        self.root = data_root.resolve()
        self.raw_root = self.root / "raw" / "imports"
        self.dataset_root = self.root / "canonical" / "datasets"
        self.manifest_root = self.root / "manifests" / "imports"
        self.analysis_root = self.root / "analyses"
        self.consensus_root = self.root / "consensus"
        self.staging_root = self.root / ".staging"
        for directory in (
            self.raw_root,
            self.dataset_root,
            self.manifest_root,
            self.analysis_root,
            self.consensus_root,
            self.staging_root,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        self.catalog_path = self.root / "catalog.duckdb"
        self._initialize_catalog()

    @contextmanager
    def connection(self) -> Iterator[duckdb.DuckDBPyConnection]:
        connection = duckdb.connect(str(self.catalog_path))
        try:
            yield connection
        finally:
            connection.close()

    def _initialize_catalog(self) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS datasets (
                    dataset_id VARCHAR PRIMARY KEY,
                    dataset_name VARCHAR NOT NULL,
                    dataset_version VARCHAR NOT NULL,
                    project_id VARCHAR NOT NULL,
                    import_id VARCHAR NOT NULL UNIQUE,
                    created_at VARCHAR NOT NULL,
                    canonical_snapshot_checksum VARCHAR NOT NULL,
                    artifact_path VARCHAR NOT NULL
                )
                """
            )

    def preserve_raw(
        self, import_id: str, original_filename: str, source_format: str, content: bytes
    ) -> tuple[Path, str]:
        import_dir = self.raw_root / import_id
        import_dir.mkdir(parents=False, exist_ok=False)
        stored_name = sanitize_filename(original_filename, source_format)
        path = import_dir / stored_name
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        path.chmod(0o444)
        return path, stored_name

    def save_import_record(self, record: ImportRecord) -> None:
        target = self.manifest_root / f"{record.import_id}.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_bytes(canonical_json_bytes(record.model_dump(mode="json")))
        os.replace(temporary, target)

    def get_import(self, import_id: str) -> ImportRecord | None:
        path = self.manifest_root / f"{import_id}.json"
        if not path.exists():
            return None
        return ImportRecord.model_validate_json(path.read_bytes())

    def commit_snapshot(
        self,
        *,
        import_record: ImportRecord,
        dataset_name: str,
        dataset_version: str,
        source_uri: str,
        license_name: str,
        redistribution_allowed: bool,
        project: BaseModel,
        label_domain: BaseModel,
        items: Sequence[BaseModel],
        annotators: Sequence[BaseModel],
        annotations: Sequence[BaseModel],
        gold_labels: Sequence[BaseModel],
    ) -> tuple[str, str, str, dict[str, str]]:
        canonical_payload = {
            "project": _rows([project]),
            "label_domain": _rows([label_domain]),
            "items": _rows(items),
            "annotators": _rows(annotators),
            "annotations": _rows(annotations),
            "gold_labels": _rows(gold_labels),
            "transformation_version": TRANSFORMATION_VERSION,
        }
        snapshot_checksum = sha256_bytes(canonical_json_bytes(canonical_payload))
        dataset_id = f"ds_{import_record.import_id.removeprefix('imp_')}"
        staging = self.staging_root / import_record.import_id
        final = self.dataset_root / dataset_id
        if staging.exists() or final.exists():
            raise StorageError("snapshot target already exists")
        staging.mkdir(parents=False)
        artifact_paths: dict[str, str] = {}
        try:
            entities = {
                "project": [project],
                "label_domain": [label_domain],
                "items": items,
                "annotators": annotators,
                "annotations": annotations,
                "gold_labels": gold_labels,
            }
            for name, models in entities.items():
                artifact = staging / f"{name}.parquet"
                _write_models(artifact, models)
                artifact_paths[name] = artifact.name
            manifest = DatasetManifest(
                dataset_manifest_id=f"manifest_{import_record.import_id.removeprefix('imp_')}",
                dataset_name=dataset_name,
                dataset_version=dataset_version,
                source_uri=source_uri,
                license=license_name,
                redistribution_allowed=redistribution_allowed,
                raw_checksums={import_record.stored_filename: import_record.raw_sha256},
                canonical_snapshot_checksum=snapshot_checksum,
                schema_version_used="4.0.0",
                adapter_version=TRANSFORMATION_VERSION,
                split_definition={"role": "phase1_import", "split": "none"},
                known_limitations=[
                    "Phase 1 provides evidence storage and descriptive counts only."
                ],
                created_at=import_record.import_timestamp,
            )
            (staging / "dataset_manifest.json").write_bytes(
                canonical_json_bytes(manifest.model_dump(mode="json"))
            )
            artifact_paths["dataset_manifest"] = "dataset_manifest.json"
            checksums = {
                name: sha256_file(staging / filename)
                for name, filename in sorted(artifact_paths.items())
            }
            (staging / "artifact_checksums.json").write_bytes(canonical_json_bytes(checksums))
            artifact_paths["artifact_checksums"] = "artifact_checksums.json"
            os.replace(staging, final)
            try:
                with self.connection() as connection:
                    connection.execute("BEGIN TRANSACTION")
                    connection.execute(
                        "INSERT INTO datasets VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        [
                            dataset_id,
                            dataset_name,
                            dataset_version,
                            import_record.project_id,
                            import_record.import_id,
                            import_record.import_timestamp,
                            snapshot_checksum,
                            _portable(final, self.root),
                        ],
                    )
                    connection.execute("COMMIT")
            except Exception:
                if final.is_dir() and final.parent == self.dataset_root:
                    shutil.rmtree(final)
                raise
        except Exception:
            if staging.is_dir() and staging.parent == self.staging_root:
                shutil.rmtree(staging)
            raise
        return dataset_id, snapshot_checksum, _portable(final, self.root), artifact_paths

    def list_datasets(self) -> list[DatasetDetail]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT dataset_id, dataset_name, dataset_version, project_id, import_id,
                       created_at, canonical_snapshot_checksum
                FROM datasets ORDER BY created_at, dataset_id
                """
            ).fetchall()
        return [
            DatasetDetail(
                dataset_id=row[0],
                dataset_name=row[1],
                dataset_version=row[2],
                project_id=row[3],
                import_id=row[4],
                created_at=row[5],
                canonical_snapshot_checksum=row[6],
            )
            for row in rows
        ]

    def get_dataset(self, dataset_id: str) -> DatasetDetail | None:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT dataset_id, dataset_name, dataset_version, project_id, import_id,
                       created_at, canonical_snapshot_checksum
                FROM datasets WHERE dataset_id = ?
                """,
                [dataset_id],
            ).fetchone()
        if row is None:
            return None
        return DatasetDetail(
            dataset_id=row[0],
            dataset_name=row[1],
            dataset_version=row[2],
            project_id=row[3],
            import_id=row[4],
            created_at=row[5],
            canonical_snapshot_checksum=row[6],
        )

    def dataset_path(self, dataset_id: str) -> Path | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT artifact_path FROM datasets WHERE dataset_id = ?", [dataset_id]
            ).fetchone()
        if row is None:
            return None
        candidate = (self.root / row[0]).resolve()
        if candidate.parent != self.dataset_root:
            raise StorageError("catalog artifact path escaped the canonical dataset root")
        return candidate

    def provenance(self, dataset_id: str, software_version: str) -> ProvenanceResponse | None:
        detail = self.get_dataset(dataset_id)
        path = self.dataset_path(dataset_id)
        if detail is None or path is None:
            return None
        import_record = self.get_import(detail.import_id)
        if import_record is None:
            raise StorageError("dataset import manifest is missing")
        checksums = json.loads((path / "artifact_checksums.json").read_text(encoding="utf-8"))
        git_commit, git_dirty = git_identity(self.root.parent)
        warnings = []
        if git_commit is None:
            warnings.append(
                "Git identity is unavailable because the source workspace is not a Git repository."
            )
        return ProvenanceResponse(
            dataset_id=dataset_id,
            import_id=detail.import_id,
            project_id=detail.project_id,
            raw_sha256=import_record.raw_sha256,
            canonical_snapshot_checksum=detail.canonical_snapshot_checksum,
            schema_version_used="4.0.0",
            transformation_version=TRANSFORMATION_VERSION,
            input_rows=import_record.input_rows,
            accepted_rows=import_record.accepted_rows,
            rejected_rows=import_record.rejected_rows,
            import_timestamp=import_record.import_timestamp,
            original_filename=import_record.original_filename,
            source_format=import_record.source_format,
            software_version=software_version,
            git_commit=git_commit,
            git_dirty=git_dirty,
            artifact_files=checksums,
            warnings=warnings,
        )

    def save_analysis_result(self, analysis_run_id: str, result: BaseModel) -> tuple[str, str]:
        """Persist one immutable analysis payload and return portable path/checksum."""
        target_dir = self.analysis_root / analysis_run_id
        if target_dir.exists():
            raise StorageError("analysis run target already exists")
        target_dir.mkdir(parents=False)
        target = target_dir / "analysis.json"
        payload = canonical_json_bytes(result.model_dump(mode="json"))
        try:
            with target.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            target.chmod(0o444)
        except Exception:
            if target_dir.is_dir() and target_dir.parent == self.analysis_root:
                shutil.rmtree(target_dir)
            raise
        return _portable(target, self.root), sha256_bytes(payload)

    def save_consensus_run(self, analysis_run_id: str, result: BaseModel) -> tuple[str, str]:
        target_dir = self.consensus_root / analysis_run_id
        if target_dir.exists():
            raise StorageError("consensus run target already exists")
        target_dir.mkdir(parents=False)
        target = target_dir / "run.json"
        payload = canonical_json_bytes(result.model_dump(mode="json"))
        try:
            with target.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            target.chmod(0o444)
        except Exception:
            if target_dir.is_dir() and target_dir.parent == self.consensus_root:
                shutil.rmtree(target_dir)
            raise
        return _portable(target, self.root), sha256_bytes(payload)

    def load_consensus_run_bytes(self, analysis_run_id: str) -> bytes | None:
        target = (self.consensus_root / analysis_run_id / "run.json").resolve()
        if target.parent.parent != self.consensus_root or not target.is_file():
            return None
        return target.read_bytes()
