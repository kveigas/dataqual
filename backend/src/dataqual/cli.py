from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from dataqual.benchmarking import BenchmarkRunner
from dataqual.config import Settings
from dataqual.descriptive import DescriptiveQueries
from dataqual.ingestion import ImportService
from dataqual.schemas.imports import ImportConfig
from dataqual.simulation import SyntheticDatasetGenerator
from dataqual.simulation.scenarios import get_pre_registered_scenario_config
from dataqual.storage import DatasetRepository

app = typer.Typer(no_args_is_help=True, help="DataQual v4 data-foundation & benchmark commands.")
benchmark_app = typer.Typer(
    no_args_is_help=True, help="Reproducible simulation & benchmarking framework."
)
app.add_typer(benchmark_app, name="benchmark")


@app.command("import-file")
def import_file(
    source: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    config: Annotated[Path, typer.Option("--config", exists=True, dir_okay=False, readable=True)],
    data_root: Annotated[Path, typer.Option("--data-root")] = Path("data"),
) -> None:
    parsed_config = ImportConfig.model_validate_json(config.read_bytes())
    repository = DatasetRepository(data_root)
    record = ImportService(repository, Settings(data_root).max_upload_bytes).import_bytes(
        source.name, source.read_bytes(), parsed_config
    )
    typer.echo(json.dumps(record.model_dump(mode="json"), indent=2))
    if record.status.value != "accepted":
        raise typer.Exit(1)


@app.command()
def summary(
    dataset_id: str,
    data_root: Annotated[Path, typer.Option("--data-root")] = Path("data"),
) -> None:
    result = DescriptiveQueries(DatasetRepository(data_root)).summary(dataset_id)
    if result is None:
        typer.echo("dataset not found", err=True)
        raise typer.Exit(1)
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))


@app.command()
def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    import uvicorn

    from dataqual.api import create_app

    uvicorn.run(create_app(), host=host, port=port)


@benchmark_app.command("simulate")
def benchmark_simulate(
    scenario: str = typer.Option("S1", help="Scenario ID (S1..S12)"),
    seed: int = typer.Option(42, help="Simulation world seed"),
    output: Annotated[Path, typer.Option("--output")] = Path("artifacts/sim_output.json"),
) -> None:
    cfg = get_pre_registered_scenario_config(scenario, world_seed=seed)
    generator = SyntheticDatasetGenerator(cfg)
    annos, golds, hidden_truth = generator.generate()

    output.parent.mkdir(parents=True, exist_ok=True)
    res = {
        "scenario": scenario,
        "world_seed": seed,
        "observed_annotations_count": len(annos),
        "development_gold_count": len(golds),
        "total_true_defects": hidden_truth.total_true_annotation_defects,
        "total_ambiguous_items": hidden_truth.total_ambiguous_items,
    }
    output.write_text(json.dumps(res, indent=2), encoding="utf-8")
    typer.echo(f"Simulation completed for {scenario}. Summary saved to {output}")


@benchmark_app.command("run")
def benchmark_run(
    scenario: str = typer.Option("S1", help="Scenario ID (S1..S12)"),
    seeds: int = typer.Option(10, help="Number of seeds"),
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("artifacts"),
) -> None:
    runner = BenchmarkRunner(scenario_id=scenario, seed_count=seeds)
    manifest, _candidates = runner.run_benchmark()

    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"manifest_{scenario.lower()}_{seeds}seeds.json"
    out_file.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Benchmark run complete. Manifest saved to {out_file}")


@benchmark_app.command("compare")
def benchmark_compare(
    manifest_file: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
) -> None:
    text = manifest_file.read_text(encoding="utf-8")
    typer.echo(text)
