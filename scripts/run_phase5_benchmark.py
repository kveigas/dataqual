from __future__ import annotations

import json
from pathlib import Path
from dataqual.benchmarking.runner import BenchmarkRunner


def run_full_phase5_benchmark():
    scenarios = [f"S{i}" for i in range(1, 13)]
    out_dir = Path("artifacts/phase5_benchmark_results")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("DATAQUAL V4 PHASE 5 FULL SYNTHETIC BENCHMARK RUNNER")
    print("=" * 80)

    all_summaries = []

    for sc in scenarios:
        print(f"\n---> Running Benchmark for Scenario {sc} (10 seeds)...")
        runner = BenchmarkRunner(scenario_id=sc, seed_count=10)
        manifest, candidates = runner.run_benchmark()

        manifest_file = out_dir / f"manifest_{sc.lower()}.json"
        manifest_file.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

        s = manifest.summary
        all_summaries.append(s)

        print(f"     AUREC@20% Means:")
        for m in s.methods:
            print(f"       - {m:28s}: {s.method_aurec_means[m]:.4f} ± {s.method_aurec_stds[m]:.4f}")

    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETED FOR ALL 12 SCENARIOS (S1-S12).")
    print(f"Artifacts saved to {out_dir}")
    print("=" * 80)


if __name__ == "__main__":
    run_full_phase5_benchmark()
