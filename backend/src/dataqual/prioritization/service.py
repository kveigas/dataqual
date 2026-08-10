from __future__ import annotations

from collections.abc import Sequence

from dataqual.analysis.core import Annotation
from dataqual.prioritization.config import DEFAULT_ERV_CONFIG, ErvConfig
from dataqual.prioritization.methods import generate_review_candidates
from dataqual.schemas.core import GoldLabel
from dataqual.schemas.prioritization import ReviewCandidate


class ReviewPrioritizationService:
    def __init__(
        self,
        annotations: Sequence[Annotation],
        gold_labels: Sequence[GoldLabel],
        labels: Sequence[str],
        erv_cfg: ErvConfig = DEFAULT_ERV_CONFIG,
    ) -> None:
        self.annotations = list(annotations)
        self.gold_labels = list(gold_labels)
        self.labels = list(labels)
        self.erv_cfg = erv_cfg

    def get_candidates(
        self,
        method: str,
        review_unit: str = "annotation",
        random_ranking_seed: int = 2026,
    ) -> list[ReviewCandidate]:
        return generate_review_candidates(
            self.annotations,
            self.gold_labels,
            self.labels,
            method=method,
            random_ranking_seed=random_ranking_seed,
            erv_cfg=self.erv_cfg,
            review_unit=review_unit,
        )

    def get_all_method_candidates(
        self,
        review_unit: str = "annotation",
        random_ranking_seed: int = 2026,
    ) -> dict[str, list[ReviewCandidate]]:
        methods = [
            "random",
            "highest_entropy",
            "lowest_consensus_confidence",
            "lowest_worker_reliability",
            "erv",
        ]
        return {
            m: self.get_candidates(
                method=m,
                review_unit=review_unit,
                random_ranking_seed=random_ranking_seed,
            )
            for m in methods
        }
