"""Recompute versioned synthetic evidence; never overwrite frozen RC1 artifacts.

Run from the repository root: python scripts/revalidate_review_evidence.py --output <new-dir>
Five seeds are a smoke/revalidation run, not a broad superiority claim.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from dataqual.benchmarking.runner import BenchmarkRunner


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--scenarios", nargs="+", default=[f"S{i}" for i in range(1, 13)])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    for scenario in args.scenarios:
        start = perf_counter()
        manifest, _ = BenchmarkRunner(scenario, seed_count=args.seeds).run_benchmark()
        output = {
            "elapsed_seconds": perf_counter() - start,
            "manifest": manifest.model_dump(mode="json"),
        }
        (args.output / f"{scenario}.json").write_text(
            json.dumps(output, indent=2, allow_nan=False), encoding="utf-8"
        )
        print(
            f"{scenario}: {output['elapsed_seconds']:.2f}s; ERV recovery@10%={manifest.summary.method_recall_10_means['erv']:.4f}",
            flush=True,
        )


if __name__ == "__main__":
    main()
