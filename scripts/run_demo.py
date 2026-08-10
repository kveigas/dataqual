from __future__ import annotations

import json
from pathlib import Path
import typer

from dataqual.api import create_app
from dataqual.config import Settings
from dataqual.ingestion import ImportService
from dataqual.schemas.imports import ImportConfig
from dataqual.simulation import SyntheticDatasetGenerator
from dataqual.simulation.scenarios import get_pre_registered_scenario_config
from dataqual.storage import DatasetRepository


def main():
    print("=" * 80)
    print("DATAQUAL V4.0.0-RC1 DETERMINISTIC DEMO WORKFLOW")
    print("=" * 80)

    demo_dir = Path("data/demo_workspace")
    demo_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate Synthetic Demo Dataset (Scenario S12 - Mixed Realistic World)
    print("\n1. Generating synthetic demo dataset (Scenario S12 - Mixed Realistic World)...")
    cfg = get_pre_registered_scenario_config("S12", world_seed=42, random_ranking_seed=2026)
    gen = SyntheticDatasetGenerator(cfg)
    annos, golds, hidden_truth = gen.generate()

    print(f"   Generated {len(annos)} annotation events on {len(hidden_truth.items_truth)} items across {len(hidden_truth.worker_parameters)} workers.")
    print(f"   Hidden Ground Truth: {hidden_truth.total_true_annotation_defects} true annotation defects, {hidden_truth.total_ambiguous_items} ambiguous items.")

    # 2. Ingest via ImportService
    print("\n2. Ingesting canonical dataset snapshot into DataQual storage foundation...")
    repo = DatasetRepository(demo_dir)
    service = ImportService(repo, max_upload_bytes=100 * 1024 * 1024)

    import_cfg = ImportConfig(
        schema_version="4.0.0",
        project_id="demo_project",
        project_name="DataQual Portfolio Demo Project",
        label_domain_id="sentiment_v1",
        labels=["positive", "neutral", "negative"],
        dataset_name="Realistic Annotation Fixture (S12)",
        dataset_version="1.0.0",
        source_uri="synthetic://s12-demo",
        license="CC0-1.0",
        redistribution_allowed=True,
    )

    # Convert annotations to CSV bytes
    lines = ["annotation_id,item_id,annotator_id,label,event_version,annotation_source"]
    for a in annos:
        lines.append(f"{a.annotation_id},{a.item_id},{a.annotator_id},{a.label},1,human")
    csv_bytes = "\n".join(lines).encode("utf-8")

    record = service.import_bytes("demo_s12.csv", csv_bytes, import_cfg)
    print(f"   Import status: {record.status.value.upper()} (Dataset ID: {record.dataset_id})")

    # 3. Print Summary Evidence
    print("\n3. Verifying evidence overview & agreement...")
    from dataqual.descriptive import DescriptiveQueries
    queries = DescriptiveQueries(repo)
    summary = queries.summary(record.dataset_id)
    if summary:
        print(f"   Items: {summary.unique_items} | Annotations: {summary.current_annotation_events} | Annotators: {summary.unique_annotators}")
        print(f"   Gold coverage: {summary.gold_coverage * 100:.1f}% | Co-annotated items: {summary.coannotated_items}")

    print("\n" + "=" * 80)
    print("DATAQUAL V4 DEMO WORKFLOW EXECUTED SUCCESSFULLY!")
    print("Launch API with 'uv run dataqual serve' and Frontend with 'pnpm --dir frontend dev'")
    print("=" * 80)


if __name__ == "__main__":
    main()
