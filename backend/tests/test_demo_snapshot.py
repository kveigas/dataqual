"""The instant-demo snapshot must match the live API and cover every option the UI offers."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

import pytest
from dataqual.api.app import create_app
from dataqual.config import Settings
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = ROOT / "frontend" / "src" / "components"


def load_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "build_demo_snapshot", ROOT / "scripts" / "build_demo_snapshot.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_builder()


@pytest.fixture(scope="module")
def snapshot(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    output = tmp_path_factory.mktemp("snapshot") / "demo-snapshot"
    manifest = builder.build(output, benchmarks=False)
    return output, manifest


def read(output: Path, name: str) -> object:
    return json.loads((output / name).read_text(encoding="utf-8"))


def test_request_key_sorts_query_parameters() -> None:
    assert builder.request_key("get", "/a?b=2&a=1") == "GET /a?a=1&b=2"
    assert builder.request_key("POST", "/a") == "POST /a"


def test_snapshot_covers_every_demo_view(snapshot: tuple[Path, dict]) -> None:
    _output, manifest = snapshot
    dataset_id = manifest["demo_dataset"]["dataset_id"]
    keys = set(manifest["entries"])
    base = f"/api/v1/datasets/{dataset_id}"
    for suffix in ["/evidence", "/agreement", "/gold-metrics", "/annotators", "/provenance"]:
        assert f"GET {base}{suffix}" in keys
    assert f"GET {base}/annotator-intelligence" in keys
    assert f"GET {base}/quality-flags" in keys
    assert f"GET {base}/diagnostics/items" in keys
    assert f"POST {base}/consensus/runs" in keys
    plans = [k for k in keys if "/label-collection-plan?" in k]
    assert len(plans) == len(builder.LABEL_TARGETS) * len(builder.LABEL_MAX)
    assert len(manifest["review_runs"]) == len(builder.REVIEW_METHODS) * len(builder.REVIEW_UNITS)


def test_snapshot_responses_equal_a_fresh_live_api(
    snapshot: tuple[Path, dict], tmp_path: Path
) -> None:
    output, manifest = snapshot
    client = TestClient(create_app(Settings(data_root=tmp_path)))
    live_id = client.post("/api/v1/demo/bootstrap").json()["dataset_id"]
    snap_id = manifest["demo_dataset"]["dataset_id"]

    # Identity fields differ between two independent imports by design (random ids, timestamps
    # and checksums over id-bearing artifacts); every statistical value must be identical.
    identity = {
        "analysis_run_id",
        "computed_at",
        "canonical_artifact_checksum",
        "canonical_snapshot_checksum",
        "dataset_id",
        "dataset_snapshot_id",
        "import_id",
    }

    def strip(value: object) -> object:
        if isinstance(value, dict):
            return {k: "<id>" if k in identity else strip(v) for k, v in value.items()}
        if isinstance(value, list):
            return [strip(v) for v in value]
        if isinstance(value, str):
            return value.replace(snap_id, "<ds>").replace(live_id, "<ds>")
        return value

    for suffix in ["/agreement", "/annotators", "/label-collection-plan?limit=200&max_labels=7"]:
        path = f"/api/v1/datasets/{{}}{suffix}"
        if "label-collection-plan" in suffix:
            path += "&target_confidence=0.95"
        key = builder.request_key("GET", path.format(snap_id))
        stored = read(output, manifest["entries"][key])
        assert strip(stored) == strip(client.get(path.format(live_id)).json()), suffix


def test_builder_options_match_the_frontend_menus() -> None:
    collection = (COMPONENTS / "LabelCollectionView.tsx").read_text(encoding="utf-8")
    targets = re.findall(r"<option value=\{(0\.\d+)\}", collection)
    assert targets == builder.LABEL_TARGETS
    max_labels = re.search(r"\[([\d, ]+)\]\.map", collection)
    assert max_labels and [v.strip() for v in max_labels.group(1).split(",")] == builder.LABEL_MAX

    review = (COMPONENTS / "ReviewQueueView.tsx").read_text(encoding="utf-8")
    block = re.search(r"const methods[^{]*\{(.*?)\};", review, re.S)
    assert block
    assert sorted(re.findall(r"^\s*(\w+):", block.group(1), re.M)) == sorted(builder.REVIEW_METHODS)

    benchmark = (COMPONENTS / "BenchmarkView.tsx").read_text(encoding="utf-8")
    assert re.findall(r'<option value="(S\d+)"', benchmark) == builder.SCENARIOS
    assert re.findall(r"<option value=\{(\d+)\}>\d+ Seeds", benchmark) == builder.SEED_COUNTS
