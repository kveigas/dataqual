"""Evaluate adaptive label collection against fixed redundancy on the synthetic scenarios.

For every registered scenario (run with simulator 1.1.0 so configured worker accuracies are
honoured) and world seed, a pilot share of items fits the Dawid-Skene worker model; the other
items reveal their labels one at a time until the posterior reaches the target confidence.
Hidden truth is used only to score accuracy (a label counts as correct when it is one of the
item's acceptable labels). Losses are reported, not filtered.

Usage:
    uv run python scripts/evaluate_adaptive_collection.py --output docs/evidence/adaptive-collection
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from dataqual.collection import replay_adaptive_collection
from dataqual.simulation import SyntheticDatasetGenerator
from dataqual.simulation.scenarios import get_pre_registered_scenario_config

SCENARIOS = [f"S{i}" for i in range(1, 13)]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "Evaluate adaptive label collection.").splitlines()[0]
    )
    parser.add_argument("--output", type=Path, required=True, help="New directory (must not exist)")
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--targets", type=float, nargs="+", default=[0.90, 0.95, 0.99])
    parser.add_argument(
        "--labels-per-item",
        type=int,
        nargs=2,
        metavar=("MIN", "MAX"),
        help="Exploratory override of the registered redundancy (reported as a non-registered design)",
    )
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"{args.output} already exists; choose a new directory")

    rows = []
    for scenario in SCENARIOS:
        for seed in range(100, 100 + args.seeds):
            update: dict = {"version": "1.1.0"}
            if args.labels_per_item:
                update["annotations_per_item_min"], update["annotations_per_item_max"] = (
                    args.labels_per_item
                )
            cfg = get_pre_registered_scenario_config(scenario, world_seed=seed).model_copy(
                update=update
            )
            annotations, _, truth = SyntheticDatasetGenerator(cfg).generate()
            labels = list(cfg.label_classes)
            acceptable = {item: set(t.acceptable_labels) for item, t in truth.items_truth.items()}
            for target in args.targets:
                result = replay_adaptive_collection(
                    annotations, labels, acceptable, target, seed=seed * 1000 + 7
                )
                rows.append({"scenario": scenario, "seed": seed, "target": target, **result})

    summary = []
    for scenario in SCENARIOS:
        for target in args.targets:
            group = [r for r in rows if r["scenario"] == scenario and r["target"] == target]

            def mean(policy: str, key: str, runs: list[dict] = group) -> float:
                return statistics.fmean(r[policy][key] for r in runs)

            summary.append(
                {
                    "scenario": scenario,
                    "target": target,
                    "adaptive_labels_per_item": mean("adaptive", "labels_per_item"),
                    "adaptive_accuracy": mean("adaptive", "accuracy"),
                    "full_labels_per_item": mean("full_model", "labels_per_item"),
                    "full_model_accuracy": mean("full_model", "accuracy"),
                    "full_majority_accuracy": mean("full_majority_vote", "accuracy"),
                    "labels_saved_share": 1
                    - mean("adaptive", "labels_per_item") / mean("full_model", "labels_per_item"),
                }
            )

    args.output.mkdir(parents=True)
    payload = {
        "design": {
            "scenarios": SCENARIOS,
            "simulator_version": "1.1.0",
            "seeds": list(range(100, 100 + args.seeds)),
            "targets": args.targets,
            "pilot_fraction": 0.3,
            "minimum_labels_before_stopping": 2,
            "labels_per_item_override": args.labels_per_item,
            "scoring": "label correct if in the item's acceptable labels (hidden truth, scoring only)",
        },
        "summary": summary,
        "runs": rows,
    }
    (args.output / "adaptive_collection.json").write_text(json.dumps(payload, indent=2), "utf-8")

    lines = [
        "| Scenario | Target | Labels/item (adaptive vs full) | Saved | Accuracy adaptive | "
        "Accuracy full model | Accuracy full MV |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for s in summary:
        lines.append(
            f"| {s['scenario']} | {s['target']:.2f} | {s['adaptive_labels_per_item']:.2f} vs "
            f"{s['full_labels_per_item']:.2f} | {s['labels_saved_share']:.0%} | "
            f"{s['adaptive_accuracy']:.1%} | {s['full_model_accuracy']:.1%} | "
            f"{s['full_majority_accuracy']:.1%} |"
        )
    (args.output / "summary.md").write_text("\n".join(lines) + "\n", "utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
