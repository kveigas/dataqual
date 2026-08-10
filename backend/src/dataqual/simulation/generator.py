from __future__ import annotations

import datetime

import numpy as np

from dataqual.analysis.core import Annotation
from dataqual.schemas.core import GoldLabel
from dataqual.schemas.simulation import (
    HiddenGroundTruth,
    ItemArchetypeConfig,
    SimulatorConfig,
    SyntheticAnnotationTruth,
    SyntheticItemTruth,
    WorkerArchetypeConfig,
)


class SyntheticDatasetGenerator:
    def __init__(self, config: SimulatorConfig) -> None:
        self.config = config
        self.rng = np.random.default_rng(config.simulation_world_seed)

    def generate(self) -> tuple[list[Annotation], list[GoldLabel], HiddenGroundTruth]:
        K = len(self.config.label_classes)
        classes = list(self.config.label_classes)

        # 1. Generate Workers
        workers: list[str] = [f"w{i + 1:02d}" for i in range(self.config.worker_count)]
        worker_configs: dict[str, WorkerArchetypeConfig] = {}

        if self.config.worker_archetypes:
            idx = 0
            for wa in self.config.worker_archetypes:
                for _ in range(wa.count):
                    if idx < len(workers):
                        worker_configs[workers[idx]] = wa
                        idx += 1
        # Fill remaining workers with AVERAGE archetype
        for w in workers:
            if w not in worker_configs:
                worker_configs[w] = WorkerArchetypeConfig(
                    archetype="AVERAGE", count=1, base_accuracy=0.75
                )

        # Build confusion matrices for workers
        worker_confusion_matrices: dict[str, np.ndarray] = {}
        for w, wa in worker_configs.items():
            if wa.confusion_matrix:
                cm = np.array(wa.confusion_matrix, dtype=float)
            elif wa.archetype == "EXPERT":
                cm = self._build_diagonal_cm(K, 0.95)
            elif wa.archetype == "AVERAGE":
                cm = self._build_diagonal_cm(K, 0.75)
            elif wa.archetype == "WEAK":
                cm = self._build_diagonal_cm(K, 0.40)
            elif wa.archetype == "RANDOM":
                cm = np.full((K, K), 1.0 / K)
            elif wa.archetype == "ADVERSARIAL":
                # Systematically shift class c to (c+1)%K
                cm = np.zeros((K, K))
                for c in range(K):
                    cm[c, (c + 1) % K] = 1.0
            elif wa.archetype == "CLASS_SPECIFIC":
                # Strong on class 0, weak on others
                cm = np.full((K, K), (1.0 - 0.9) / (K - 1) if K > 1 else 1.0)
                cm[0, :] = 0.1 / (K - 1) if K > 1 else 0.0
                cm[0, 0] = 0.9
                for c in range(1, K):
                    cm[c, c] = 0.35
            else:
                cm = self._build_diagonal_cm(K, wa.base_accuracy)
            worker_confusion_matrices[w] = cm

        # Handle CORRELATED_COPYCAT workers
        for w, wa in worker_configs.items():
            if wa.archetype == "CORRELATED_COPYCAT" and wa.copycat_target_worker:
                target = wa.copycat_target_worker
                if target in worker_confusion_matrices:
                    worker_confusion_matrices[w] = worker_confusion_matrices[target].copy()

        # 2. Generate Items
        items: list[str] = [f"item_{i + 1:04d}" for i in range(self.config.item_count)]
        items_truth: dict[str, SyntheticItemTruth] = {}

        # Class prevalence distribution
        probs = np.array([self.config.class_prevalence.get(c, 1.0 / K) for c in classes])
        probs = probs / np.sum(probs)

        # Distribute item archetypes
        item_archetypes_list: list[ItemArchetypeConfig] = []
        if self.config.item_archetypes:
            for ia in self.config.item_archetypes:
                item_archetypes_list.extend([ia] * ia.count)
        while len(item_archetypes_list) < len(items):
            item_archetypes_list.append(ItemArchetypeConfig(archetype="EASY", count=1))

        for idx, item_id in enumerate(items):
            ia = item_archetypes_list[idx]
            true_class_idx = int(self.rng.choice(K, p=probs))
            true_label = classes[true_class_idx]

            if ia.archetype == "AMBIGUOUS":
                item_truth_type = "ambiguous"
                # Acceptable labels: top 2 classes
                second_class = classes[(true_class_idx + 1) % K]
                acceptable_labels = [true_label, second_class]
                latent_dist = {true_label: 0.5, second_class: 0.5}
                difficulty = 2.0
            else:
                item_truth_type = "deterministic"
                acceptable_labels = [true_label]
                latent_dist = {true_label: 1.0}
                difficulty = 1.0 if ia.archetype == "EASY" else 2.5

            items_truth[item_id] = SyntheticItemTruth(
                item_id=item_id,
                canonical_true_label=true_label,
                item_truth_type=item_truth_type,
                acceptable_labels=acceptable_labels,
                latent_label_distribution=latent_dist,
                item_archetype=ia.archetype,
                difficulty=difficulty,
            )

        # 3. Generate Annotations
        observed_annotations: list[Annotation] = []
        annotations_truth: dict[str, SyntheticAnnotationTruth] = {}
        anno_counter = 1
        now_str = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

        for item_id in items:
            it = items_truth[item_id]
            m_i = int(
                self.rng.integers(
                    self.config.annotations_per_item_min,
                    self.config.annotations_per_item_max + 1,
                )
            )
            assigned_workers = self.rng.choice(workers, size=min(m_i, len(workers)), replace=False)

            for w in assigned_workers:
                cm = worker_confusion_matrices[w]
                true_c_idx = classes.index(it.canonical_true_label)

                # Sample emitted label from worker confusion row
                row_probs = cm[true_c_idx]
                row_probs = row_probs / np.sum(row_probs)
                emitted_c_idx = int(self.rng.choice(K, p=row_probs))
                emitted_label = classes[emitted_c_idx]

                # Check true correctness:
                # If ambiguous item, emitted_label in acceptable_labels is NOT wrong
                is_wrong = emitted_label not in it.acceptable_labels

                anno_id = f"a_{anno_counter:06d}"
                anno_counter += 1

                observed_annotations.append(
                    Annotation(
                        annotation_id=anno_id,
                        item_id=item_id,
                        annotator_id=w,
                        label=emitted_label,
                    )
                )

                wa = worker_configs[w]
                annotations_truth[anno_id] = SyntheticAnnotationTruth(
                    annotation_id=anno_id,
                    item_id=item_id,
                    annotator_id=w,
                    submitted_label=emitted_label,
                    is_actually_wrong=is_wrong,
                    worker_archetype=wa.archetype,
                    worker_true_accuracy=float(np.trace(cm) / K),
                )

        # 4. Generate Development Gold (Operational Gold available to DataQual)
        development_gold: list[GoldLabel] = []
        gold_count = int(np.round(self.config.development_gold_fraction * len(items)))
        if gold_count > 0:
            gold_item_ids = self.rng.choice(items, size=gold_count, replace=False)
            for g_idx, item_id in enumerate(gold_item_ids):
                it = items_truth[item_id]
                development_gold.append(
                    GoldLabel(
                        gold_label_id=f"g_dev_{g_idx + 1:04d}",
                        project_id="synthetic_sim",
                        item_id=item_id,
                        label_domain_id="domain_sim",
                        label=it.canonical_true_label,
                        resolution_status="resolved_hard",
                        gold_source="expert_adjudication",
                        version=1,
                        created_at=now_str,
                    )
                )

        # 5. Build Hidden Ground Truth Payload
        total_defects = sum(1 for at in annotations_truth.values() if at.is_actually_wrong)
        total_ambiguous = sum(1 for it in items_truth.values() if it.item_truth_type == "ambiguous")

        worker_params_payload: dict[str, dict] = {
            w: {
                "archetype": worker_configs[w].archetype,
                "confusion_matrix": worker_confusion_matrices[w].tolist(),
                "base_accuracy": float(np.trace(worker_confusion_matrices[w]) / K),
            }
            for w in workers
        }

        hidden_truth = HiddenGroundTruth(
            simulator_version=self.config.version,
            config_hash=self.config.config_hash(),
            simulation_world_seed=self.config.simulation_world_seed,
            items_truth=items_truth,
            annotations_truth=annotations_truth,
            worker_parameters=worker_params_payload,
            total_true_annotation_defects=total_defects,
            total_ambiguous_items=total_ambiguous,
        )

        return observed_annotations, development_gold, hidden_truth

    def _build_diagonal_cm(self, K: int, accuracy: float) -> np.ndarray:
        cm = np.zeros((K, K))
        off_diag = (1.0 - accuracy) / (K - 1) if K > 1 else 0.0
        for i in range(K):
            for j in range(K):
                cm[i, j] = accuracy if i == j else off_diag
        return cm
