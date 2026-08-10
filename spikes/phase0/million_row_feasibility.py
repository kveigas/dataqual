"""Deterministic one-million-event architecture feasibility spike.

This is not a production module or a performance benchmark claim.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import time
from pathlib import Path

import duckdb
import numpy as np
import psutil
import pyarrow as pa
import pyarrow.csv as csv
import pyarrow.parquet as pq


def timed_query(connection: duckdb.DuckDBPyConnection, sql: str, parameters: list[str]) -> dict[str, object]:
    started = time.perf_counter()
    result = connection.execute(sql, parameters).to_arrow_table()
    return {
        "seconds": time.perf_counter() - started,
        "rows_returned": result.num_rows,
        "preview": result.slice(0, 5).to_pylist(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=1_000_000)
    parser.add_argument("--seed", type=int, default=20260809)
    args = parser.parse_args()
    if args.rows != 1_000_000:
        raise SystemExit("The registered Phase 0 feasibility run requires exactly 1,000,000 rows")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    process = psutil.Process(os.getpid())
    peak_rss = process.memory_info().rss

    rows = args.rows
    annotations_per_item = 5
    item_count = rows // annotations_per_item
    worker_count = 1_000
    index = np.arange(rows, dtype=np.int64)
    item_number = index // annotations_per_item
    slot = index % annotations_per_item
    worker_number = (item_number * 7 + slot * 137) % worker_count
    true_label = item_number % 3
    deterministic_error = ((index * 48271 + args.seed) % 100) < 12
    label = np.where(deterministic_error, (true_label + 1 + worker_number % 2) % 3, true_label).astype(np.int8)

    started = time.perf_counter()
    annotations = pa.table(
        {
            "event_id": pa.array([f"evt-{i:09d}" for i in index]),
            "project_id": pa.array(["phase0-project"] * rows),
            "item_id": pa.array([f"item-{i:07d}" for i in item_number]),
            "annotator_id": pa.array([f"worker-{i:04d}" for i in worker_number]),
            "label_id": pa.array(label, type=pa.int8()),
            "annotation_status": pa.array(["submitted"] * rows),
            "annotated_at": pa.array(["2026-01-01T00:00:00Z"] * rows),
            "source_row_number": pa.array(index + 1, type=pa.int64()),
            "event_version": pa.array(np.ones(rows, dtype=np.int16)),
            "is_current": pa.array(np.ones(rows, dtype=bool)),
        }
    )
    items = pa.table(
        {
            "project_id": pa.array(["phase0-project"] * item_count),
            "item_id": pa.array([f"item-{i:07d}" for i in range(item_count)]),
            "source_ref": pa.array([f"synthetic://item/{i}" for i in range(item_count)]),
        }
    )
    generation_seconds = time.perf_counter() - started
    peak_rss = max(peak_rss, process.memory_info().rss)

    csv_path = args.output_dir / "annotations_1m.csv"
    annotations_parquet = args.output_dir / "annotations_1m.parquet"
    items_parquet = args.output_dir / "items_200k.parquet"

    started = time.perf_counter()
    csv.write_csv(annotations, csv_path)
    csv_write_seconds = time.perf_counter() - started
    peak_rss = max(peak_rss, process.memory_info().rss)

    started = time.perf_counter()
    ingested = csv.read_csv(csv_path)
    ingestion_seconds = time.perf_counter() - started
    if ingested.num_rows != rows or ingested["event_id"].null_count:
        raise RuntimeError("CSV ingestion validation failed")
    peak_rss = max(peak_rss, process.memory_info().rss)

    started = time.perf_counter()
    pq.write_table(ingested, annotations_parquet, compression="zstd", row_group_size=100_000)
    pq.write_table(items, items_parquet, compression="zstd", row_group_size=100_000)
    parquet_write_seconds = time.perf_counter() - started
    peak_rss = max(peak_rss, process.memory_info().rss)

    connection = duckdb.connect(":memory:")
    annotation_parameter = [str(annotations_parquet)]
    queries = {
        "annotations_per_worker": timed_query(
            connection,
            "SELECT annotator_id, count(*) n FROM read_parquet(?) GROUP BY annotator_id ORDER BY annotator_id",
            annotation_parameter,
        ),
        "annotations_per_item": timed_query(
            connection,
            "SELECT item_id, count(*) n FROM read_parquet(?) GROUP BY item_id ORDER BY item_id LIMIT 1000",
            annotation_parameter,
        ),
        "class_distribution": timed_query(
            connection,
            "SELECT label_id, count(*) n FROM read_parquet(?) GROUP BY label_id ORDER BY label_id",
            annotation_parameter,
        ),
        "worker_item_overlap": timed_query(
            connection,
            "SELECT annotator_id, count(DISTINCT item_id) item_count FROM read_parquet(?) GROUP BY annotator_id ORDER BY annotator_id",
            annotation_parameter,
        ),
        "filter_one_project": timed_query(
            connection,
            "SELECT count(*) n FROM read_parquet(?) WHERE project_id = 'phase0-project'",
            annotation_parameter,
        ),
        "join_annotations_items": timed_query(
            connection,
            "SELECT count(*) n FROM read_parquet(?) a JOIN read_parquet(?) i USING (project_id, item_id)",
            [str(annotations_parquet), str(items_parquet)],
        ),
    }
    peak_rss = max(peak_rss, process.memory_info().rss)

    result = {
        "status": "pass",
        "scope_note": "Architecture feasibility observation; not a general performance benchmark.",
        "seed": args.seed,
        "row_count": rows,
        "item_count": item_count,
        "worker_count": worker_count,
        "csv_bytes": csv_path.stat().st_size,
        "parquet_annotation_bytes": annotations_parquet.stat().st_size,
        "parquet_item_bytes": items_parquet.stat().st_size,
        "generation_seconds": generation_seconds,
        "csv_write_seconds": csv_write_seconds,
        "csv_ingestion_seconds": ingestion_seconds,
        "parquet_write_seconds": parquet_write_seconds,
        "peak_process_rss_bytes_observed": peak_rss,
        "queries": queries,
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "duckdb": duckdb.__version__,
            "pyarrow": pa.__version__,
            "numpy": np.__version__,
        },
    }
    result_path = args.output_dir / "million_row_result.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
