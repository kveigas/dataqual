"""Durable, checksummed review runs. Rankings are immutable, not browser session state."""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from dataqual.provenance import canonical_json_bytes, sha256_bytes
from dataqual.storage.repository import StorageError

RUN_ID_PATTERN = r"run-[a-f0-9]{32}"
DEFAULT_MAX_RUNS = 1000


class ReviewRunQuotaError(StorageError):
    """Raised when the store holds the maximum number of distinct review runs."""


def deterministic_run_id(identity: dict[str, Any]) -> str:
    """Content-addressed ID: identical inputs (snapshot, method, settings) map to one run.

    Ranking is deterministic, so repeating a request reuses the stored run instead of writing
    another file; this also makes run creation naturally idempotent.
    """
    return f"run-{sha256_bytes(canonical_json_bytes(identity))[:32]}"


class ReviewRunStore:
    def __init__(self, data_root: Path, max_runs: int = DEFAULT_MAX_RUNS) -> None:
        self.root = data_root / "review-runs"
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_runs = max_runs

    def count(self) -> int:
        return sum(1 for _ in self.root.glob("run-*.json"))

    def save(self, run: dict[str, Any]) -> None:
        run_id = run["run_id"]
        if not re.fullmatch(RUN_ID_PATTERN, run_id):
            raise ValueError("invalid review run ID")
        if self.count() >= self.max_runs:
            raise ReviewRunQuotaError(
                f"review run quota reached ({self.max_runs}); reuse an existing run"
            )
        payload = canonical_json_bytes(run)
        envelope = canonical_json_bytes({"sha256": sha256_bytes(payload), "run": run})
        target = self.root / f"{run_id}.json"
        temporary = self.root / f".{uuid.uuid4().hex}.tmp"
        try:
            with temporary.open("xb") as handle:
                handle.write(envelope)
                handle.flush()
                os.fsync(handle.fileno())
            # Published runs are never updated.
            if target.exists():
                raise StorageError("review run already exists")
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    def load(self, run_id: str) -> dict[str, Any] | None:
        if not re.fullmatch(RUN_ID_PATTERN, run_id):
            return None
        path = self.root / f"{run_id}.json"
        if not path.is_file():
            return None
        try:
            envelope = json.loads(path.read_bytes())
            run: dict[str, Any] = envelope["run"]
            recorded = envelope["sha256"]
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise StorageError("review run file is corrupted") from error
        if recorded != sha256_bytes(canonical_json_bytes(run)):
            raise StorageError("review run checksum mismatch")
        return run
