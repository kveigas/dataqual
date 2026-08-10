from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field

WorkerArchetype = Literal[
    "EXPERT",
    "AVERAGE",
    "WEAK",
    "RANDOM",
    "ADVERSARIAL",
    "CLASS_SPECIFIC",
    "CORRELATED_COPYCAT",
]

ItemArchetype = Literal[
    "EASY",
    "DIFFICULT",
    "AMBIGUOUS",
    "IMBALANCED_CLASS",
    "CLASS_SPECIFIC_HARD",
]


class WorkerArchetypeConfig(BaseModel):
    archetype: WorkerArchetype
    count: int
    base_accuracy: float = 0.85
    confusion_matrix: list[list[float]] | None = None
    copycat_target_worker: str | None = None


class ItemArchetypeConfig(BaseModel):
    archetype: ItemArchetype
    count: int
    item_truth_type: Literal["deterministic", "ambiguous"] = "deterministic"
    acceptable_labels: list[str] = Field(default_factory=list)
    latent_label_distribution: dict[str, float] = Field(default_factory=dict)
    difficulty_multiplier: float = 1.0


class SimulatorConfig(BaseModel):
    version: str = "1.0.0"
    simulation_world_seed: int = 42
    random_ranking_seed: int = 2026
    item_count: int = 100
    worker_count: int = 10
    label_classes: list[str] = Field(default_factory=lambda: ["positive", "neutral", "negative"])
    class_prevalence: dict[str, float] = Field(
        default_factory=lambda: {"positive": 0.4, "neutral": 0.3, "negative": 0.3}
    )
    annotations_per_item_min: int = 3
    annotations_per_item_max: int = 5
    worker_archetypes: list[WorkerArchetypeConfig] = Field(default_factory=list)
    item_archetypes: list[ItemArchetypeConfig] = Field(default_factory=list)
    development_gold_fraction: float = 0.20
    adversarial_worker_prevalence: float = 0.0

    def config_hash(self) -> str:
        serialized = json.dumps(self.model_dump(), sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class SyntheticItemTruth(BaseModel):
    item_id: str
    canonical_true_label: str
    item_truth_type: Literal["deterministic", "ambiguous"]
    acceptable_labels: list[str]
    latent_label_distribution: dict[str, float]
    item_archetype: ItemArchetype
    difficulty: float


class SyntheticAnnotationTruth(BaseModel):
    annotation_id: str
    item_id: str
    annotator_id: str
    submitted_label: str
    is_actually_wrong: bool
    worker_archetype: WorkerArchetype
    worker_true_accuracy: float


class HiddenGroundTruth(BaseModel):
    simulator_version: str = "1.0.0"
    config_hash: str
    simulation_world_seed: int
    items_truth: dict[str, SyntheticItemTruth]
    annotations_truth: dict[str, SyntheticAnnotationTruth]
    worker_parameters: dict[str, dict[str, Any]]
    total_true_annotation_defects: int
    total_ambiguous_items: int
