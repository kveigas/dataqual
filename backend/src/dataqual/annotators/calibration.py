from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from dataqual.analysis.core import Annotation
from dataqual.schemas.core import GoldLabel
from dataqual.schemas.intelligence import AnnotatorCalibration, ECEBin


def compute_annotator_calibration(
    annotations: Sequence[Annotation],
    gold_labels: Sequence[GoldLabel],
    target_annotator_id: str,
) -> AnnotatorCalibration:
    hard_gold = {
        g.item_id: g.label
        for g in gold_labels
        if str(g.resolution_status) == "resolved_hard" and g.label is not None
    }

    pairs: list[tuple[float, bool]] = []
    for row in annotations:
        if row.annotator_id == target_annotator_id and row.item_id in hard_gold:
            conf_val = getattr(row, "confidence", None)
            if conf_val is not None and np.isfinite(conf_val):
                is_correct = row.label == hard_gold[row.item_id]
                pairs.append((float(conf_val), is_correct))

    if not pairs:
        return AnnotatorCalibration(
            annotator_id=target_annotator_id,
            status="not_available",
            observations=0,
            reason="No annotations with observed confidence scores on evaluated gold items.",
        )

    # 1. Brier Score: Mean squared difference (confidence - 1[correct])^2
    confidences = np.array([p[0] for p in pairs], dtype=np.float64)
    corrects = np.array([1.0 if p[1] else 0.0 for p in pairs], dtype=np.float64)
    brier_score = float(np.mean((confidences - corrects) ** 2))

    # 2. 10 fixed equal-width ECE bins [0, 0.1), ..., [0.9, 1.0]
    bins: list[ECEBin] = []
    ece = 0.0
    total_n = len(pairs)

    for i in range(10):
        low = i * 0.1
        high = (i + 1) * 0.1
        if i == 9:
            mask = (confidences >= low) & (confidences <= high)
        else:
            mask = (confidences >= low) & (confidences < high)

        bin_count = int(np.sum(mask))
        if bin_count > 0:
            bin_conf = float(np.mean(confidences[mask]))
            bin_acc = float(np.mean(corrects[mask]))
            ece += (bin_count / total_n) * abs(bin_acc - bin_conf)
        else:
            bin_conf = None
            bin_acc = None

        bins.append(
            ECEBin(
                bin_index=i,
                lower_bound=low,
                upper_bound=high,
                count=bin_count,
                mean_confidence=bin_conf,
                accuracy=bin_acc,
            )
        )

    return AnnotatorCalibration(
        annotator_id=target_annotator_id,
        status="available",
        observations=total_n,
        brier_score=brier_score,
        ece=ece,
        bins=bins,
    )


def math_isfinite(val: float) -> bool:
    try:
        import math

        return math.isfinite(val)
    except Exception:
        return False
