from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from dataqual.analysis.core import Annotation
from dataqual.annotators.beta_binomial import compute_beta_binomial_reliability
from dataqual.annotators.calibration import compute_annotator_calibration
from dataqual.annotators.dirichlet_confusion import compute_dirichlet_confusion
from dataqual.annotators.model_comparison import compare_gold_vs_ds_confusion
from dataqual.schemas.core import GoldLabel
from dataqual.schemas.intelligence import AnnotatorProfile


class AnnotatorIntelligenceService:
    def __init__(
        self,
        annotations: Sequence[Annotation],
        gold_labels: Sequence[GoldLabel],
        labels: Sequence[str],
    ) -> None:
        self.annotations = annotations
        self.gold_labels = gold_labels
        self.labels = list(labels)
        self.annotator_ids = sorted({a.annotator_id for a in annotations})

    def get_annotator_profile(
        self,
        annotator_id: str,
        ds_matrix: np.ndarray | None = None,
        ds_labels: list[str] | None = None,
        ds_support: int = 0,
    ) -> AnnotatorProfile:
        worker_annotations = [a for a in self.annotations if a.annotator_id == annotator_id]
        total_annotations = len(worker_annotations)

        beta_est = compute_beta_binomial_reliability(
            self.annotations, self.gold_labels, annotator_id
        )
        dirichlet_est = compute_dirichlet_confusion(
            self.annotations, self.gold_labels, self.labels, annotator_id
        )
        cal_est = compute_annotator_calibration(self.annotations, self.gold_labels, annotator_id)

        gold_vs_ds = None
        if ds_matrix is not None and ds_labels is not None:
            gold_vs_ds = compare_gold_vs_ds_confusion(
                dirichlet_est, ds_matrix, ds_labels, ds_support
            )

        if total_annotations >= 100:
            evidence_level = "strong"
        elif total_annotations >= 20:
            evidence_level = "adequate"
        elif total_annotations >= 1:
            evidence_level = "limited"
        else:
            evidence_level = "minimal"

        return AnnotatorProfile(
            annotator_id=annotator_id,
            total_annotations=total_annotations,
            evaluated_gold_items=beta_est.evaluated_gold_items,
            evidence_level=evidence_level,
            beta_binomial=beta_est,
            dirichlet_confusion=dirichlet_est,
            gold_vs_ds=gold_vs_ds,
            calibration=cal_est,
        )

    def list_annotator_profiles(self) -> list[AnnotatorProfile]:
        return [self.get_annotator_profile(w) for w in self.annotator_ids]
