"""Throwaway CSV -> validation -> Parquet -> DuckDB -> Arrow/JSON spike."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.csv as csv
import pyarrow.parquet as pq


REQUIRED_COLUMNS = {
    "event_id",
    "project_id",
    "item_id",
    "annotator_id",
    "label_id",
    "annotation_status",
    "annotated_at",
    "source_row_number",
    "event_version",
    "is_current",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=10_000)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "synthetic_annotations.csv"
    parquet_path = args.output_dir / "synthetic_annotations.parquet"

    rows = args.rows
    table = pa.table(
        {
            "event_id": [f"evt-{i:08d}" for i in range(rows)],
            "project_id": ["phase0-project"] * rows,
            "item_id": [f"item-{i // 5:07d}" for i in range(rows)],
            "annotator_id": [f"worker-{(i * 17) % 97:03d}" for i in range(rows)],
            "label_id": pa.array((i % 3 for i in range(rows)), type=pa.int8()),
            "annotation_status": ["submitted"] * rows,
            "annotated_at": ["2026-01-01T00:00:00Z"] * rows,
            "source_row_number": pa.array(range(1, rows + 1), type=pa.int64()),
            "event_version": pa.array([1] * rows, type=pa.int16()),
            "is_current": [True] * rows,
        }
    )

    started = time.perf_counter()
    csv.write_csv(table, csv_path)
    csv_write_seconds = time.perf_counter() - started

    started = time.perf_counter()
    canonical = csv.read_csv(csv_path)
    if set(canonical.column_names) != REQUIRED_COLUMNS:
        raise RuntimeError("Canonical column validation failed")
    if canonical.num_rows != rows:
        raise RuntimeError("Canonical row-count validation failed")
    if canonical["event_id"].null_count or canonical["label_id"].null_count:
        raise RuntimeError("Required-column null validation failed")
    validation_seconds = time.perf_counter() - started

    started = time.perf_counter()
    pq.write_table(canonical, parquet_path, compression="zstd")
    parquet_write_seconds = time.perf_counter() - started

    connection = duckdb.connect(":memory:")
    started = time.perf_counter()
    relation = connection.execute(
        """
        SELECT label_id, count(*) AS annotations
        FROM read_parquet(?)
        GROUP BY label_id
        ORDER BY label_id
        """,
        [str(parquet_path)],
    )
    arrow_result = relation.to_arrow_table()
    query_seconds = time.perf_counter() - started
    api_like_json = arrow_result.to_pylist()

    result = {
        "status": "pass",
        "rows": rows,
        "csv_bytes": csv_path.stat().st_size,
        "parquet_bytes": parquet_path.stat().st_size,
        "csv_write_seconds": csv_write_seconds,
        "csv_validation_seconds": validation_seconds,
        "parquet_write_seconds": parquet_write_seconds,
        "duckdb_query_seconds": query_seconds,
        "arrow_schema": str(arrow_result.schema),
        "api_like_json": api_like_json,
    }
    result_path = args.output_dir / "duckdb_arrow_result.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
