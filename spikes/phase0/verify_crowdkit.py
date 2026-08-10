"""Phase 0 callability and reference-behavior verification for Crowd-Kit."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import inspect
import json
import platform
import sys
import warnings
from pathlib import Path
from typing import Any

import pandas as pd
from crowdkit.aggregation import DawidSkene, GLAD, MACE, MajorityVote
from crowdkit.datasets import load_dataset


INPUT_LABELS: dict[str, dict[str, int]] = {
    "i1": {"w1": 0, "w2": 0, "w3": 0, "w4": 1},
    "i2": {"w1": 0, "w2": 0, "w3": 1, "w4": 0},
    "i3": {"w1": 1, "w2": 1, "w3": 1, "w4": 0},
    "i4": {"w1": 1, "w2": 1, "w3": 0, "w4": 1},
    "i5": {"w1": 0, "w2": 0, "w3": 0, "w4": 0},
    "i6": {"w1": 1, "w2": 1, "w3": 1, "w4": 1},
    "i7": {"w1": 0, "w2": 1, "w3": 0, "w4": 0},
    "i8": {"w1": 1, "w2": 0, "w3": 1, "w4": 1},
}


def records() -> list[dict[str, Any]]:
    return [{"task": task, "worker": worker, "label": label} for task, answers in INPUT_LABELS.items() for worker, label in answers.items()]


def JSON_value(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-cache", type=Path)
    args = parser.parse_args()
    frame = pd.DataFrame.from_records(records())

    versions = {
        name: metadata.version(name)
        for name in (
            "crowd-kit",
            "numpy",
            "pandas",
            "scipy",
            "scikit-learn",
        )
    }
    results: dict[str, Any] = {
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "packages": versions,
        },
        "input_annotations": records(),
        "signatures": {},
        "callability": {},
    }

    configs = {
        "MajorityVote": (MajorityVote, {}),
        "DawidSkene": (DawidSkene, {"n_iter": 100, "tol": 1e-9}),
        "GLAD": (GLAD, {"n_iter": 10, "tol": 1e-5}),
        "MACE": (MACE, {"n_restarts": 2, "n_iter": 10, "random_state": 0}),
    }
    for name, (method, kwargs) in configs.items():
        results["signatures"][name] = str(inspect.signature(method))
        model = method(**kwargs)
        with warnings.catch_warnings(record=True) as caught:
            labels = model.fit_predict(frame)
        results["callability"][name] = {
            "status": "pass",
            "configuration": kwargs,
            "labels": {str(k): JSON_value(v) for k, v in labels.sort_index().items()},
            "warnings": [str(w.message) for w in caught],
        }
        if name == "DawidSkene":
            results["dawid_skene_reference"] = {
                "labels": {str(k): JSON_value(v) for k, v in model.labels_.sort_index().items()},
                "probabilities": {
                    str(task): {str(label): float(value) for label, value in row.items()}
                    for task, row in model.probas_.sort_index().to_dict(orient="index").items()
                },
                "priors": {str(k): float(v) for k, v in model.priors_.items()},
                "errors": [
                    {
                        "worker": str(worker),
                        "observed_label": JSON_value(observed),
                        "true_label": JSON_value(true_label),
                        "probability": float(value),
                    }
                    for (worker, observed), row in model.errors_.sort_index().iterrows()
                    for true_label, value in row.items()
                ],
                "loss_history": [float(value) for value in model.loss_history_],
                "iterations_observed": len(model.loss_history_),
                "note": "Crowd-Kit exposes loss history but no separate convergence flag.",
            }

    if args.dataset_cache:
        annotations, ground_truth = load_dataset("relevance-2", data_dir=str(args.dataset_cache))
        results["relevance_2_loader"] = {
            "status": "pass",
            "annotation_rows": int(len(annotations)),
            "ground_truth_rows": int(len(ground_truth)),
            "columns": list(annotations.columns),
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
