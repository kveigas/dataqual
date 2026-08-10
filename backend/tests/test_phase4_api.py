from __future__ import annotations

import pytest
from dataqual.api import create_app
from dataqual.config import Settings
from dataqual.schemas.imports import ImportConfig
from fastapi.testclient import TestClient


@pytest.fixture
def api_client(tmp_path) -> TestClient:
    settings = Settings(data_root=tmp_path / "data")
    app = create_app(settings)
    client = TestClient(app)
    service = app.state.import_service

    config = ImportConfig(
        schema_version="4.0.0",
        project_id="p1",
        project_name="Phase4 Test Project",
        label_domain_id="d1",
        labels=["positive", "negative"],
        dataset_name="Phase4 Dataset",
        dataset_version="1.0.0",
        source_uri="test://phase4",
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
    record = service.import_bytes("p4_test.csv", csv_data, config)
    client.app_dataset_id = record.dataset_id
    return client


def test_annotator_intelligence_endpoints(api_client: TestClient) -> None:
    dataset_id = api_client.app_dataset_id

    # 1. All Profiles
    res1 = api_client.get(f"/api/v1/datasets/{dataset_id}/annotator-intelligence")
    assert res1.status_code == 200
    profiles = res1.json()
    assert len(profiles) == 3  # w1, w2, w3

    # 2. Specific Profile
    res2 = api_client.get(f"/api/v1/datasets/{dataset_id}/annotators/w1/profile")
    assert res2.status_code == 200
    prof = res2.json()
    assert prof["annotator_id"] == "w1"
    assert prof["evaluated_gold_items"] == 2

    # 3. Reliability
    res3 = api_client.get(f"/api/v1/datasets/{dataset_id}/annotators/w1/reliability")
    assert res3.status_code == 200
    rel = res3.json()
    assert rel["successes"] == 2
    assert rel["failures"] == 0

    # 4. Confusion
    res4 = api_client.get(f"/api/v1/datasets/{dataset_id}/annotators/w1/confusion")
    assert res4.status_code == 200
    conf = res4.json()
    assert conf["annotator_id"] == "w1"


def test_diagnostics_and_quality_flags_endpoints(api_client: TestClient) -> None:
    dataset_id = api_client.app_dataset_id

    # 1. Item Diagnostics List
    res1 = api_client.get(f"/api/v1/datasets/{dataset_id}/diagnostics/items")
    assert res1.status_code == 200
    items = res1.json()
    assert len(items) == 2  # i1, i2

    # 2. Specific Item Diagnostic
    res2 = api_client.get(f"/api/v1/datasets/{dataset_id}/diagnostics/items/i1")
    assert res2.status_code == 200
    diag = res2.json()
    assert diag["item_id"] == "i1"
    assert diag["annotation_count"] == 3

    # 3. Quality Flags List & Filters
    res3 = api_client.get(f"/api/v1/datasets/{dataset_id}/quality-flags")
    assert res3.status_code == 200
    flags = res3.json()
    assert len(flags) > 0
