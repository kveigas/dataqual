from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel


class DiagnosticThresholdConfig(BaseModel):
    version: str = "1.0.0"
    entropy_high_threshold: float = 0.5
    margin_small_threshold: float = 0.25
    ds_posterior_high_threshold: float = 0.75
    worker_weak_bound_threshold: float = 0.50
    worker_strong_bound_threshold: float = 0.70
    min_annotations_for_consensus: int = 2

    def config_hash(self) -> str:
        serialized = json.dumps(self.model_dump(), sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


DEFAULT_DIAGNOSTIC_CONFIG = DiagnosticThresholdConfig()
