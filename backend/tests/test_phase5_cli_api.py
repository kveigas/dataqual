from __future__ import annotations

import pytest
from dataqual.api import create_app
from dataqual.cli import app as cli_app
from dataqual.config import Settings
from dataqual.schemas.imports import ImportConfig
from fastapi.testclient import TestClient
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def api_client(tmp_path) -> tuple[TestClient, str]:
    settings = Settings(data_root=tmp_path / "data")
    app = create_app(settings)
    client = TestClient(app)
    service = app.state.import_service

    config = ImportConfig(
        schema_version="4.0.0",
        project_id="p1",
        project_name="Phase5 Test Project",
        label_domain_id="d1",
        labels=["positive", "negative"],
        dataset_name="Phase5 Dataset",
        dataset_version="1.0.0",
        source_uri="test://phase5",
        license="CC0-1.0",
        redistribution_allowed=True,
    )
    csv_data = (
        b"annotation_id,item_id,annotator_id,label,event_version,annotation_source,gold_label,gold_source\n"
        b"a1,i1,w1,positive,1,human,positive,expert_adjudication\n"
        b"a2,i1,w2,positive,1,human,positive,expert_adjudication\n"
        b"a3,i1,w3,negative,1,human,positive,expert_adjudication\n"
        b"a4,i2,w1,negative,1,human,negative,expert_adjudication\n"
        b"a5,i2,w2,negative,1,human,negative,expert_adjudication\n"
    )
    record = service.import_bytes("p5_test.csv", csv_data, config)
    assert record.dataset_id is not None
    return client, record.dataset_id


def test_cli_benchmark_simulate():
    result = runner.invoke(cli_app, ["benchmark", "simulate", "--scenario", "S1", "--seed", "42"])
    assert result.exit_code == 0
    assert "Simulation completed for S1" in result.output


def test_cli_benchmark_run():
    result = runner.invoke(cli_app, ["benchmark", "run", "--scenario", "S1", "--seeds", "2"])
    assert result.exit_code == 0
    assert "Benchmark run complete" in result.output


def test_api_review_runs_flow(api_client):
    client, dataset_id = api_client

    # 1. Create Review Run
    res1 = client.post(
        f"/api/v1/datasets/{dataset_id}/review-runs?method=erv&review_unit=annotation"
    )
    assert res1.status_code == 200
    data1 = res1.json()
    run_id = data1["run_id"]
    assert data1["method"] == "erv"

    # 2. Get Run Candidates
    res2 = client.get(f"/api/v1/review-runs/{run_id}/candidates?limit=10")
    assert res2.status_code == 200
    candidates = res2.json()
    assert len(candidates) > 0

    # 3. Get Benchmark Results
    res3 = client.get("/api/v1/benchmark/results?scenario_id=S1&seeds=2")
    assert res3.status_code == 200
    bm = res3.json()
    assert bm["scenario_id"] == "S1"
