from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from dataqual.schemas.imports import DatasetSummary
from dataqual.storage import DatasetRepository


def _one(
    connection: duckdb.DuckDBPyConnection, query: str, parameters: list[str]
) -> tuple[Any, ...]:
    row = connection.execute(query, parameters).fetchone()
    if row is None:
        raise RuntimeError("canonical artifact query returned no aggregate row")
    return row


class DescriptiveQueries:
    def __init__(self, repository: DatasetRepository) -> None:
        self.repository = repository

    @staticmethod
    def _parquet(path: Path, name: str) -> str:
        return str(path / f"{name}.parquet")

    def summary(self, dataset_id: str) -> DatasetSummary | None:
        path = self.repository.dataset_path(dataset_id)
        if path is None:
            return None
        annotations = self._parquet(path, "annotations")
        items = self._parquet(path, "items")
        annotators = self._parquet(path, "annotators")
        domain = self._parquet(path, "label_domain")
        gold = self._parquet(path, "gold_labels")
        with duckdb.connect() as connection:
            annotation_events = _one(
                connection, "SELECT count(*) FROM read_parquet(?)", [annotations]
            )[0]
            current_events = _one(
                connection,
                "SELECT count(*) FROM read_parquet(?) WHERE is_current",
                [annotations],
            )[0]
            unique_items = _one(connection, "SELECT count(*) FROM read_parquet(?)", [items])[0]
            unique_annotators = _one(
                connection, "SELECT count(*) FROM read_parquet(?)", [annotators]
            )[0]
            labels_json = _one(connection, "SELECT labels FROM read_parquet(?) LIMIT 1", [domain])[
                0
            ]
            label_classes = len(json.loads(labels_json))
            by_annotator = dict(
                connection.execute(
                    """SELECT annotator_id, count(*) AS n
                    FROM read_parquet(?) WHERE is_current
                    GROUP BY annotator_id ORDER BY n DESC, annotator_id LIMIT 100""",
                    [annotations],
                ).fetchall()
            )
            by_item = dict(
                connection.execute(
                    """SELECT item_id, count(*) AS n
                    FROM read_parquet(?) WHERE is_current
                    GROUP BY item_id ORDER BY n DESC, item_id LIMIT 100""",
                    [annotations],
                ).fetchall()
            )
            class_counts = dict(
                connection.execute(
                    """SELECT label, count(*) AS n
                    FROM read_parquet(?) WHERE is_current
                    GROUP BY label ORDER BY label""",
                    [annotations],
                ).fetchall()
            )
            missing_row = _one(
                connection,
                """SELECT
                    count(*) FILTER (WHERE timestamp IS NULL),
                    count(*) FILTER (WHERE confidence IS NULL),
                    count(*) FILTER (WHERE duration_ms IS NULL),
                    count(*) FILTER (WHERE ai_suggestion IS NULL)
                FROM read_parquet(?)""",
                [annotations],
            )
            gold_columns = {
                row[0]
                for row in connection.execute(
                    "DESCRIBE SELECT * FROM read_parquet(?)", [gold]
                ).fetchall()
            }
            gold_items = (
                0
                if "_empty" in gold_columns
                else _one(
                    connection,
                    "SELECT count(DISTINCT item_id) FROM read_parquet(?)",
                    [gold],
                )[0]
            )
            coannotated = _one(
                connection,
                """SELECT count(*) FROM (
                    SELECT item_id FROM read_parquet(?) WHERE is_current
                    GROUP BY item_id HAVING count(DISTINCT annotator_id) > 1
                )""",
                [annotations],
            )[0]
        return DatasetSummary(
            dataset_id=dataset_id,
            annotation_events=annotation_events,
            current_annotation_events=current_events,
            unique_items=unique_items,
            unique_annotators=unique_annotators,
            label_classes=label_classes,
            annotations_by_annotator_top=by_annotator,
            annotations_by_item_top=by_item,
            class_counts=class_counts,
            missing_optional_fields={
                "timestamp": missing_row[0],
                "confidence": missing_row[1],
                "duration_ms": missing_row[2],
                "ai_suggestion": missing_row[3],
            },
            gold_items=gold_items,
            gold_coverage=gold_items / unique_items if unique_items else 0.0,
            coannotated_items=coannotated,
        )

    def annotation_history(
        self, dataset_id: str, item_id: str, annotator_id: str
    ) -> list[dict[str, Any]]:
        path = self.repository.dataset_path(dataset_id)
        if path is None:
            return []
        annotations = self._parquet(path, "annotations")
        with duckdb.connect() as connection:
            cursor = connection.execute(
                """SELECT annotation_id, event_version, supersedes_annotation_id,
                            is_current, label
                    FROM read_parquet(?)
                    WHERE item_id = ? AND annotator_id = ?
                    ORDER BY event_version""",
                [annotations, item_id, annotator_id],
            )
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
