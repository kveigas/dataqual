"""Inspect the official UCSC-REAL CIFAR-10N release without importing images."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


BASE = "https://raw.githubusercontent.com/UCSC-REAL/cifar-10-100n/main"
FILES = {
    "LICENSE.md": f"{BASE}/LICENSE.md",
    "README.md": f"{BASE}/README.md",
    "side_info_cifar10N.csv": f"{BASE}/side_info_cifar10N.csv",
    "CIFAR-10_human_ordered.npy": f"{BASE}/data/CIFAR-10_human_ordered.npy",
}


def download(url: str, path: Path) -> None:
    request = Request(url, headers={"User-Agent": "DataQual-v4-Phase0B/1.0"})
    with urlopen(request, timeout=180) as response, path.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    checksums = {}
    for name, url in FILES.items():
        path = args.output_dir / name
        download(url, path)
        checksums[name] = {"url": url, "bytes": path.stat().st_size, "sha256": sha256(path)}

    side = pd.read_csv(args.output_dir / "side_info_cifar10N.csv")
    labels = np.load(args.output_dir / "CIFAR-10_human_ordered.npy", allow_pickle=True).item()
    worker_columns = [column for column in side if column.startswith("Worker")]
    worker_count = pd.unique(side[worker_columns].to_numpy().ravel()).size
    raw_labels = np.stack([labels[f"random_label{index}"] for index in (1, 2, 3)])
    majority = np.apply_along_axis(
        lambda values: np.bincount(values, minlength=10).argmax(), 0, raw_labels
    )
    result = {
        "authoritative_repository": "https://github.com/UCSC-REAL/cifar-10-100n",
        "license": "CC BY-NC 4.0",
        "license_scope_evidence": (
            "Root LICENSE.md applies a CC BY-NC 4.0 license to the repository; "
            "README calls this repository the official dataset release. No narrower "
            "per-file exception was found. Non-commercial and attribution terms apply."
        ),
        "checksums": checksums,
        "side_info": {
            "rows": len(side),
            "columns": side.columns.tolist(),
            "unique_workers_across_slots": int(worker_count),
            "sample": side.head(3).astype(str).to_dict(orient="records"),
        },
        "label_arrays": {key: list(np.asarray(value).shape) for key, value in labels.items()},
        "structural_checks": {
            "aggregate_matches_simple_mode_fraction": float(
                np.mean(labels["aggre_label"] == majority)
            ),
            "worst_label_is_one_of_three_labels_fraction": float(
                np.mean(np.any(raw_labels == labels["worse_label"], axis=0))
            ),
        },
        "assessment": {
            "event_reconstruction": "plausible but not authoritatively documented",
            "reason": (
                "The label artifact exposes three per-item arrays named "
                "random_label1..3 and side_info exposes Worker1..3 for each ten-image "
                "batch. Slot-wise mapping is plausible, but the official README does "
                "not explicitly state that random_labelN belongs to WorkerN. Treat "
                "item-worker-label reconstruction as unresolved pending authoritative "
                "confirmation rather than relying on column-name inference."
            ),
            "dawid_skene": "potentially suitable only after slot mapping is verified",
            "worker_reliability": "potentially suitable only after slot mapping is verified",
            "weighted_vote": "potentially suitable; clean labels exist, but mapping and split must be verified",
            "class_specific_error_analysis": "suitable using noisy-label arrays versus clean labels",
            "timing": "batch-level only; not per annotation",
            "recommended_role": "secondary real human label-noise validation only",
        },
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
