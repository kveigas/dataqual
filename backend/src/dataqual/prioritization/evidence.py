"""Observed-evidence inputs for review ranking; never accepts hidden evaluation truth."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence

from dataqual.analysis.core import Annotation
from dataqual.consensus.dawid_skene import fit_dawid_skene
from dataqual.consensus.models import ConsensusStatus, DawidSkeneConfig
from dataqual.diagnostics.features import extract_item_disagreement_features
from dataqual.schemas.core import GoldLabel
from dataqual.schemas.diagnostics import ItemDisagreementFeatures

RANKING_VERSION = "review-evidence-2.0.0"
REVIEW_DS_CONFIG = DawidSkeneConfig(profile="dawid_skene_reference_compatible")


def review_features(
    annotations: Sequence[Annotation], gold: Sequence[GoldLabel], labels: Sequence[str]
) -> dict[str, ItemDisagreementFeatures]:
    by_item: dict[str, list[Annotation]] = defaultdict(list)
    for row in annotations:
        by_item[row.item_id].append(row)
    features = {
        item: extract_item_disagreement_features(item, rows, labels, annotations, gold)
        for item, rows in by_item.items()
    }
    # One fit per snapshot, not one per item. Gold never enters the unsupervised fit.
    for fit in fit_dawid_skene(annotations, labels, REVIEW_DS_CONFIG):
        for index, item_id in enumerate(fit.component.item_ids):
            feature = features[item_id]
            feature.ds_status = fit.status.value
            if fit.status != ConsensusStatus.SUCCESS:
                continue
            probs = dict(zip(fit.component.labels, map(float, fit.posteriors[index]), strict=True))
            top = max(probs.values())
            winners = [label for label, value in probs.items() if value == top]
            feature.ds_probabilities = probs
            feature.ds_max_posterior = top
            feature.ds_entropy = -math.fsum(p * math.log(p) for p in probs.values() if p > 0)
            feature.ds_label = winners[0] if len(winners) == 1 else None
            feature.method_disagreement = (
                feature.mv_label is not None
                and feature.ds_label is not None
                and feature.mv_label != feature.ds_label
            )
    return features
