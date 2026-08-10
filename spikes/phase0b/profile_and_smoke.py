"""Profile the three licensed Phase 0B candidates and run Crowd-Kit smoke tests.

Raw data stays in the caller-provided external directory. Only aggregate JSON is
written to the repository staging area.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from crowdkit.aggregation import DawidSkene, MajorityVote
from sklearn.metrics import accuracy_score, f1_score


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, value: str) -> str:
        self.parent.setdefault(value, value)
        if self.parent[value] != value:
            self.parent[value] = self.find(self.parent[value])
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def clean_text(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\s+", " ", regex=True).str.strip()


def load_crowd4sdg(raw: Path) -> tuple[pd.DataFrame, str]:
    source = raw / "5535744" / "albania_earthquake2019-mturk10.csv"
    data = pd.read_csv(source, dtype=str, keep_default_na=False)
    events = data.rename(
        columns={
            "HITId": "item_id",
            "WorkerId": "annotator_id",
            "Answer.image-contains.label": "label",
        }
    )[["item_id", "annotator_id", "label"]]
    events["gold_label"] = pd.NA
    note = (
        "The MTurk table has complete item-worker-label triples. The separate "
        "expert table has 907 task IDs but no shared item/media identifier, so it "
        "cannot be joined to MTurk items without inventing an order-based mapping."
    )
    return events, note


def load_crowdtruth(raw: Path) -> tuple[pd.DataFrame, str]:
    base = next((raw / "1472330" / "extracted").glob("CrowdTruth-*/data/output"))
    judgments = pd.read_csv(base / "worker_judgments.csv", dtype=str)
    aggregated = pd.read_csv(base / "aggregated_sentences.csv", dtype=str)
    relation_columns = [
        column
        for column in judgments.columns
        if column == "none" or column.startswith("org:") or column.startswith("per:")
    ]
    long = judgments[["unit", "worker", *relation_columns]].melt(
        id_vars=["unit", "worker"], var_name="relation", value_name="label"
    )
    long["label"] = long["label"].astype(float).astype(int).astype(str)
    long["item_id"] = long["unit"].astype(str) + "|" + long["relation"]
    source_relation = aggregated.set_index(aggregated.columns[0])["input.relation"]
    long["gold_label"] = (
        long["relation"] == long["unit"].map(source_relation)
    ).astype(int).astype(str)
    events = long.rename(columns={"worker": "annotator_id"})[
        ["item_id", "annotator_id", "label", "gold_label"]
    ]
    note = (
        "Each multilabel judgment is transparently expanded into 17 binary "
        "relation propositions. input.relation is distant-supervision provenance, "
        "not independent expert gold; scores against it are proxy diagnostics only."
    )
    return events, note


def load_requirements_phase3(raw: Path) -> tuple[pd.DataFrame, str]:
    base = raw / "3626185" / "extracted" / "Phase 3"
    data = pd.read_csv(base / "P3-RawOutput.csv", dtype=str, keep_default_na=False)
    gold = pd.read_excel(base / "P3-Golden.xlsx", dtype=str, keep_default_na=False)
    data = data.loc[data["_golden"].str.upper() == "FALSE"].copy()
    data["review_key"] = clean_text(data["reviews"])
    gold["review_key"] = clean_text(gold["Reviews"])
    gold_map = gold.drop_duplicates("review_key").set_index("review_key")["Judgment"]
    data["gold_label"] = data["review_key"].map(gold_map)
    events = data.rename(
        columns={
            "_unit_id": "item_id",
            "_worker_id": "annotator_id",
            "which_category_best_fits_this_feedback_sentence_": "label",
        }
    )[["item_id", "annotator_id", "label", "gold_label"]]
    for column in ("label", "gold_label"):
        events[column] = events[column].astype(str).str.strip().str.casefold()
    # The source contains 27 exact duplicate item-worker-label exports. They are
    # byte-equivalent repeat records, not independent judgments.
    events = events.drop_duplicates(["item_id", "annotator_id", "label"]).copy()
    note = (
        "The selected Phase 3 non-test-question subset has about six judgments per "
        "ordinary item and joins by normalized feedback text to the independent "
        "researcher Golden workbook. Platform test-question rows are excluded; 27 "
        "exact duplicate item-worker-label exports are de-duplicated."
    )
    return events, note


def graph_profile(events: pd.DataFrame) -> dict:
    graph = UnionFind()
    for row in events[["item_id", "annotator_id"]].itertuples(index=False):
        graph.union(f"i:{row.item_id}", f"w:{row.annotator_id}")
    components: Counter[str] = Counter(graph.find(node) for node in graph.parent)
    return {
        "connected_components": len(components),
        "largest_component_nodes": max(components.values()),
        "total_nodes": len(graph.parent),
    }


def smoke(events: pd.DataFrame, sample_prefixes: int | None = None) -> dict:
    tested = events
    if sample_prefixes is not None:
        prefixes = sorted({value.split("|", 1)[0] for value in events["item_id"]})[
            :sample_prefixes
        ]
        tested = events[events["item_id"].str.split("|", n=1).str[0].isin(prefixes)]
    crowdkit = tested.rename(
        columns={"item_id": "task", "annotator_id": "worker"}
    )[["task", "worker", "label"]]
    result: dict[str, object] = {
        "rows_tested": len(crowdkit),
        "items_tested": int(crowdkit["task"].nunique()),
    }
    predictions = {}
    for name, model in (
        ("majority_vote", MajorityVote()),
        ("dawid_skene", DawidSkene(n_iter=100, tol=1e-5)),
    ):
        try:
            prediction = model.fit_predict(crowdkit)
            predictions[name] = prediction
            result[name] = {"status": "PASS", "predicted_items": len(prediction)}
        except Exception as exc:  # evidence capture for exploratory spike
            result[name] = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}

    gold = tested.dropna(subset=["gold_label"]).drop_duplicates("item_id").set_index(
        "item_id"
    )["gold_label"]
    if len(gold):
        for name, prediction in predictions.items():
            common = gold.index.intersection(prediction.index)
            result[name].update(
                {
                    "gold_items_scored": len(common),
                    "accuracy": accuracy_score(gold.loc[common], prediction.loc[common]),
                    "macro_f1": f1_score(
                        gold.loc[common], prediction.loc[common], average="macro"
                    ),
                }
            )
    return result


def profile(name: str, events: pd.DataFrame, note: str, sample: int | None) -> dict:
    events = events.astype({"item_id": str, "annotator_id": str, "label": str})
    per_item = events.groupby("item_id").size()
    per_worker = events.groupby("annotator_id").size()
    item_disagreement = events.groupby("item_id")["label"].apply(
        lambda labels: 1.0 - labels.value_counts(normalize=True).iloc[0]
    )
    gold = events.dropna(subset=["gold_label"]).drop_duplicates("item_id")
    return {
        "dataset": name,
        "conversion_note": note,
        "items": int(events["item_id"].nunique()),
        "annotations": len(events),
        "annotators": int(events["annotator_id"].nunique()),
        "label_classes": sorted(events["label"].unique().tolist()),
        "labels_per_item": {
            "min": int(per_item.min()),
            "median": float(per_item.median()),
            "mean": float(per_item.mean()),
            "max": int(per_item.max()),
        },
        "annotations_per_worker": {
            "min": int(per_worker.min()),
            "median": float(per_worker.median()),
            "mean": float(per_worker.mean()),
            "max": int(per_worker.max()),
        },
        "fraction_items_ge_2": float((per_item >= 2).mean()),
        "fraction_items_ge_3": float((per_item >= 3).mean()),
        "gold_items": int(gold["item_id"].nunique()),
        "gold_coverage": float(gold["item_id"].nunique() / events["item_id"].nunique()),
        "annotation_class_distribution": events["label"].value_counts(normalize=True).to_dict(),
        "gold_class_distribution": gold["gold_label"].value_counts(normalize=True).to_dict(),
        "mean_raw_disagreement": float(item_disagreement.mean()),
        "fraction_non_unanimous": float((item_disagreement > 0).mean()),
        "graph": graph_profile(events),
        "duplicate_item_worker_pairs": int(events.duplicated(["item_id", "annotator_id"]).sum()),
        "crowdkit_smoke": smoke(events, sample),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    datasets = []
    for name, loader, sample in (
        ("Crowd4SDG Albania earthquake MTurk", load_crowd4sdg, None),
        ("CrowdTruth Open Domain Relation Extraction", load_crowdtruth, 200),
        ("Requirements annotation Phase 3", load_requirements_phase3, None),
    ):
        events, note = loader(args.raw_dir)
        datasets.append(profile(name, events, note, sample))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(datasets, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(datasets, indent=2))


if __name__ == "__main__":
    main()
