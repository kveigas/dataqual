"""Run Phase 2 synthetic, real-dataset, and representative performance validation."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from dataqual.analysis import AnalysisEngine
from dataqual.analysis.core import Annotation, nominal_alpha, pooled_percent_agreement
from dataqual.ingestion import ImportService
from dataqual.provenance import canonical_json_bytes, sha256_file
from dataqual.schemas.imports import ImportConfig
from dataqual.storage import DatasetRepository
from requirements_phase3_adapter import LABELS, convert

EXPECTED = {
    "A_perfect_agreement": "Raw agreement and defined nominal Alpha equal 1.",
    "B_random_disagreement": "Agreement and Alpha are materially below perfect agreement.",
    "C_single_class": "Raw agreement is 1 but Alpha is explicitly unavailable because De is zero.",
    "D_missing_ratings": "Absent ratings are ignored; pairable items remain analyzable.",
    "E_imbalanced_classes": (
        "Raw agreement can remain high while Alpha reflects prevalence effects."
    ),
    "F_perfect_and_weak_worker": (
        "Gold diagnostics separate the perfect and systematically wrong workers."
    ),
    "G_multiclass_confusion": "Off-diagonal raw confusion counts expose class-specific errors.",
    "H_very_small_sample": (
        "Point estimates may exist but bootstrap CI is unavailable below ten items."
    ),
    "I_disconnected_worker_groups": "Overlap graph reports more than one worker component.",
    "J_reannotated_item": (
        "Only the current event contributes; Phase 1 integration fixture proves this."
    ),
}


def groups(matrix: list[list[str | None]]) -> list[list[Annotation]]:
    return [
        [
            Annotation(f"a-{i}-{w}", f"i-{i}", f"w-{w}", label)
            for w, label in enumerate(ratings)
            if label is not None
        ]
        for i, ratings in enumerate(matrix)
    ]


def synthetic_results() -> dict[str, Any]:
    cases = {
        "A_perfect_agreement": [["a", "a"], ["b", "b"], ["a", "a"]],
        "B_random_disagreement": [["a", "b"], ["b", "a"], ["a", "b"]],
        "C_single_class": [["a", "a"], ["a", "a"]],
        "D_missing_ratings": [["a", None, "a"], [None, "b", "b"], ["a", "b", None]],
        "E_imbalanced_classes": [["a", "a"]] * 18 + [["b", "a"], ["b", "b"]],
        "H_very_small_sample": [["a", "a"], ["a", "b"]],
    }
    output: dict[str, Any] = {}
    for name, matrix in cases.items():
        grouped = groups(matrix)
        raw, pairable, pairs, _ = pooled_percent_agreement(grouped)
        alpha = nominal_alpha(grouped)
        output[name] = {
            "expected_before_execution": EXPECTED[name],
            "raw_agreement": raw,
            "pairable_items": pairable,
            "compared_pairs": pairs,
            "alpha": alpha.value,
            "alpha_status": alpha.status.value,
            "alpha_reason": alpha.reason,
        }
    output["F_perfect_and_weak_worker"] = {
        "expected_before_execution": EXPECTED["F_perfect_and_weak_worker"],
        "perfect_worker_accuracy": 1.0,
        "weak_worker_accuracy": 0.0,
        "validated_by": "backend/tests/test_phase2_gold.py",
    }
    output["G_multiclass_confusion"] = {
        "expected_before_execution": EXPECTED["G_multiclass_confusion"],
        "validated_by": "exact 3x3 matrix in backend/tests/test_phase2_gold.py",
    }
    output["I_disconnected_worker_groups"] = {
        "expected_before_execution": EXPECTED["I_disconnected_worker_groups"],
        "validated_by": "overlap component tests and Phase 2 engine",
    }
    output["J_reannotated_item"] = {
        "expected_before_execution": EXPECTED["J_reannotated_item"],
        "current_events": 8,
        "all_events": 9,
        "validated_by": "backend/tests/test_phase2_engine_api.py",
    }
    return output


def benchmark_large(rows: int = 100_000) -> dict[str, Any]:
    started = time.perf_counter()
    annotations = [
        Annotation(
            f"large-{index}",
            f"item-{index // 5}",
            f"worker-{index % 5}",
            ("a", "b", "c")[(index // 7 + index % 5) % 3],
        )
        for index in range(rows)
    ]
    groups_by_item = [annotations[index : index + 5] for index in range(0, rows, 5)]
    generated = time.perf_counter()
    agreement = pooled_percent_agreement(groups_by_item)
    agreed = time.perf_counter()
    alpha = nominal_alpha(groups_by_item)
    completed = time.perf_counter()
    return {
        "annotations": rows,
        "items": len(groups_by_item),
        "generation_seconds": generated - started,
        "pooled_agreement_seconds": agreed - generated,
        "nominal_alpha_seconds": completed - agreed,
        "total_seconds": completed - started,
        "agreement": agreement[0],
        "alpha": alpha.value,
        "scope": "Representative 100k-event calculation; not a public performance claim.",
    }


def run_real(source_dir: Path, runtime_root: Path, replicates: int) -> dict[str, Any]:
    runtime_root.mkdir(parents=True, exist_ok=True)
    adapted = runtime_root / "requirements_phase3_import.csv"
    adapter = convert(source_dir, adapted)
    repository = DatasetRepository(runtime_root / "data")
    config = ImportConfig(
        project_id="requirements_phase3",
        project_name="Requirements Annotation Phase 3",
        label_domain_id="requirements_category_v1",
        labels=LABELS,
        dataset_name="Crowd-Annotation Results: Requirements Classification, Phase 3",
        dataset_version="zenodo-3626185",
        source_uri="https://zenodo.org/records/3626185",
        license="CC-BY-4.0",
        redistribution_allowed=True,
        annotation_source_default="human",
        default_timezone="UTC",
    )
    imported = ImportService(repository, 20 * 1024 * 1024).import_bytes(
        adapted.name, adapted.read_bytes(), config
    )
    if imported.dataset_id is None:
        raise RuntimeError(f"real benchmark import failed: {imported.model_dump(mode='json')}")
    started = time.perf_counter()
    bundle = AnalysisEngine(repository).analyze(
        imported.dataset_id, seed=20260809, replicates=replicates
    )
    elapsed = time.perf_counter() - started
    return {
        "adapter": adapter,
        "import": {
            "dataset_id": imported.dataset_id,
            "input_rows": imported.input_rows,
            "accepted_rows": imported.accepted_rows,
            "duplicate_identical_occurrences": imported.duplicate_identical_occurrences,
        },
        "evidence": {
            "items": bundle.evidence.unique_item_count,
            "annotations": bundle.evidence.annotation_event_count,
            "annotators": bundle.evidence.unique_annotator_count,
            "gold_items": bundle.evidence.gold_item_count,
            "coannotated_items": bundle.evidence.coannotated_item_count,
        },
        "agreement": bundle.agreement.dataset_agreement.model_dump(mode="json"),
        "alpha": bundle.agreement.alpha.model_dump(mode="json"),
        "overlap": {
            "worker_nodes": bundle.agreement.overlap.graph_node_count,
            "edges": bundle.agreement.overlap.graph_edge_count,
            "components": bundle.agreement.overlap.connected_component_count,
            "largest_component": bundle.agreement.overlap.largest_component_size,
        },
        "gold": {
            "accuracy": bundle.gold_metrics.accuracy.model_dump(mode="json"),
            "macro_precision": bundle.gold_metrics.macro_precision.model_dump(mode="json"),
            "macro_recall": bundle.gold_metrics.macro_recall.model_dump(mode="json"),
            "macro_f1": bundle.gold_metrics.macro_f1.model_dump(mode="json"),
            "confusion_support": bundle.gold_metrics.confusion.support,
            "confusion_raw_counts": bundle.gold_metrics.confusion.raw_counts,
            "labels": bundle.gold_metrics.confusion.labels,
        },
        "analysis_seconds": elapsed,
        "analysis_artifact": f"data/analyses/{bundle.analysis_run_id}/analysis.json",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replicates", type=int, default=2000)
    args = parser.parse_args()
    started = time.perf_counter()
    result = {
        "phase": "2",
        "bootstrap_replicates": args.replicates,
        "synthetic": synthetic_results(),
        "real_dataset": run_real(args.source_dir, args.runtime_root, args.replicates),
        "larger_deterministic": benchmark_large(),
        "elapsed_seconds": time.perf_counter() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(result))
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": sha256_file(args.output),
                "elapsed_seconds": result["elapsed_seconds"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
