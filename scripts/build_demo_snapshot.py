"""Pre-compute the public demo's API responses so the static frontend renders instantly.

The hosted API sleeps when idle and takes about a minute to wake. The demo dataset is
deterministic, so every response the demo views can request is computed here, at build time,
by the same code that serves the live API, and shipped with the frontend as static JSON.
The live API is still used for everything else (imports and user datasets).

Usage:
    uv run python scripts/build_demo_snapshot.py --output frontend/public/demo-snapshot
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit

from dataqual.api.app import create_app
from dataqual.config import Settings
from fastapi.testclient import TestClient

SNAPSHOT_VERSION = "demo-snapshot-1"
# These lists mirror the options the frontend offers; a test keeps them in sync.
LABEL_TARGETS = ["0.9", "0.95", "0.99"]
LABEL_MAX = ["3", "5", "7", "9"]
REVIEW_METHODS = [
    "erv",
    "highest_entropy",
    "lowest_consensus_confidence",
    "lowest_worker_reliability",
    "random",
]
REVIEW_UNITS = ["annotation", "item"]
SCENARIOS = [f"S{i}" for i in range(1, 13)]
SEED_COUNTS = ["5", "10"]


def request_key(method: str, path: str) -> str:
    """Canonical key shared with the frontend: method, path and sorted query parameters."""
    parts = urlsplit(path)
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    return f"{method.upper()} {parts.path}{'?' + query if query else ''}"


class SnapshotWriter:
    def __init__(self, client: TestClient, output: Path) -> None:
        self.client = client
        self.output = output
        self.entries: dict[str, str] = {}

    def _write(self, body: Any) -> str:
        text = json.dumps(body, separators=(",", ":"), sort_keys=True)
        name = hashlib.sha256(text.encode()).hexdigest()[:20] + ".json"
        (self.output / name).write_text(text, encoding="utf-8")
        return name

    def capture(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.client.request(method, path, **kwargs)
        if response.status_code != 200:
            raise RuntimeError(f"{method} {path} -> {response.status_code}: {response.text[:300]}")
        body = response.json()
        self.entries[request_key(method, path)] = self._write(body)
        return body

    def store(self, body: Any) -> str:
        return self._write(body)


def build(output: Path, *, benchmarks: bool = True) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="dataqual-snapshot-") as data_root:
        client = TestClient(create_app(Settings(data_root=Path(data_root))))
        writer = SnapshotWriter(client, output)

        demo = client.post("/api/v1/demo/bootstrap").json()
        dataset_id = demo["dataset_id"]
        dataset = next(
            d for d in client.get("/api/v1/datasets").json() if d["dataset_id"] == dataset_id
        )
        base = f"/api/v1/datasets/{dataset_id}"

        for suffix in [
            "",
            "/summary",
            "/provenance",
            "/evidence",
            "/agreement",
            "/gold-metrics",
            "/annotators",
            "/annotator-intelligence",
            "/quality-flags",
            "/diagnostics/items",
        ]:
            writer.capture("GET", base + suffix)

        for target in LABEL_TARGETS:
            for max_labels in LABEL_MAX:
                query = urlencode(
                    {"target_confidence": target, "max_labels": max_labels, "limit": "200"}
                )
                writer.capture("GET", f"{base}/label-collection-plan?{query}")

        writer.capture(
            "POST",
            f"{base}/consensus/runs",
            json={"methods": ["majority_vote", "dawid_skene"]},
        )

        review_runs: dict[str, str] = {}
        for method in REVIEW_METHODS:
            for unit in REVIEW_UNITS:
                run = writer.capture(
                    "POST", f"{base}/review-runs?method={method}&review_unit={unit}"
                )
                candidates: list[Any] = []
                while True:
                    page = client.get(
                        f"/api/v1/review-runs/{run['run_id']}/candidates",
                        params={"limit": 500, "offset": len(candidates)},
                    ).json()
                    candidates.extend(page)
                    if len(page) < 500:
                        break
                review_runs[run["run_id"]] = writer.store(candidates)

        if benchmarks:
            for scenario in SCENARIOS:
                for seeds in SEED_COUNTS:
                    writer.capture(
                        "GET", f"/api/v1/benchmark/results?scenario_id={scenario}&seeds={seeds}"
                    )

        health = client.get("/api/v1/health").json()

    manifest = {
        "snapshot_version": SNAPSHOT_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "api_version": health.get("version"),
        "demo_dataset": dataset,
        "entries": writer.entries,
        "review_runs": review_runs,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    elapsed = time.perf_counter() - started
    size = sum(f.stat().st_size for f in output.iterdir())
    print(
        f"Wrote {len(writer.entries)} responses and {len(review_runs)} review runs "
        f"({size / 1e6:.1f} MB) to {output} in {elapsed:.0f}s"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "Build the demo snapshot.").splitlines()[0]
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--skip-benchmarks", action="store_true", help="Faster build for local checks"
    )
    args = parser.parse_args()
    build(args.output, benchmarks=not args.skip_benchmarks)


if __name__ == "__main__":
    main()
