from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from dataqual.analysis.core import Annotation
from dataqual.annotators import compute_beta_binomial_reliability
from dataqual.diagnostics import extract_item_disagreement_features
from dataqual.prioritization.config import DEFAULT_ERV_CONFIG, ErvConfig
from dataqual.schemas.core import GoldLabel
from dataqual.schemas.prioritization import ErvScoreComponents, ReviewCandidate


def generate_review_candidates(
    annotations: Sequence[Annotation],
    gold_labels: Sequence[GoldLabel],
    labels: Sequence[str],
    method: str,
    random_ranking_seed: int = 2026,
    erv_cfg: ErvConfig = DEFAULT_ERV_CONFIG,
    review_unit: str = "annotation",
) -> list[ReviewCandidate]:
    candidates: list[ReviewCandidate] = []
    dataset_annotations = list(annotations)
    dataset_golds = list(gold_labels)

    # Pre-extract item disagreement features for all items
    item_ids = sorted({a.item_id for a in dataset_annotations})
    item_features = {
        item_id: extract_item_disagreement_features(
            item_id,
            [a for a in dataset_annotations if a.item_id == item_id],
            labels,
            dataset_annotations,
            dataset_golds,
        )
        for item_id in item_ids
    }

    # Pre-compute worker gold reliability (development gold only)
    worker_ids = sorted({a.annotator_id for a in dataset_annotations})
    worker_gold_reliabilities = {
        w: compute_beta_binomial_reliability(dataset_annotations, dataset_golds, w)
        for w in worker_ids
    }

    if method == "random":
        rng = np.random.default_rng(random_ranking_seed)
        if review_unit == "annotation":
            annos = list(dataset_annotations)
            shuffled_indices = rng.permutation(len(annos))
            for idx, s_idx in enumerate(shuffled_indices):
                a = annos[int(s_idx)]
                candidates.append(
                    ReviewCandidate(
                        candidate_id=f"cand-rand-{a.annotation_id}",
                        review_unit="annotation",
                        item_id=a.item_id,
                        annotation_id=a.annotation_id,
                        annotator_id=a.annotator_id,
                        submitted_label=a.label,
                        prioritization_method="random",
                        score=float(len(annos) - idx),
                        score_components={"random_rank": float(idx + 1)},
                        rank=idx + 1,
                    )
                )
        else:
            shuffled_indices = rng.permutation(len(item_ids))
            for idx, s_idx in enumerate(shuffled_indices):
                item_id = item_ids[int(s_idx)]
                candidates.append(
                    ReviewCandidate(
                        candidate_id=f"cand-rand-{item_id}",
                        review_unit="item",
                        item_id=item_id,
                        prioritization_method="random",
                        score=float(len(item_ids) - idx),
                        score_components={"random_rank": float(idx + 1)},
                        rank=idx + 1,
                    )
                )

    elif method == "highest_entropy":
        if review_unit == "annotation":
            scored_annos: list[tuple[float, str, Annotation]] = []
            for a in dataset_annotations:
                feat = item_features[a.item_id]
                h_i = feat.normalized_entropy if feat.normalized_entropy is not None else 0.0
                scored_annos.append((h_i, a.annotation_id, a))
            scored_annos.sort(key=lambda x: (-x[0], x[1]))

            for idx, (h_i, _c_id, a) in enumerate(scored_annos):
                candidates.append(
                    ReviewCandidate(
                        candidate_id=f"cand-ent-{a.annotation_id}",
                        review_unit="annotation",
                        item_id=a.item_id,
                        annotation_id=a.annotation_id,
                        annotator_id=a.annotator_id,
                        submitted_label=a.label,
                        prioritization_method="highest_entropy",
                        score=float(h_i),
                        score_components={"normalized_entropy": float(h_i)},
                        rank=idx + 1,
                    )
                )
        else:
            scored_items: list[tuple[float, str]] = []
            for item_id in item_ids:
                feat = item_features[item_id]
                h_i = feat.normalized_entropy if feat.normalized_entropy is not None else 0.0
                scored_items.append((h_i, item_id))
            scored_items.sort(key=lambda x: (-x[0], x[1]))

            for idx, (h_i, item_id) in enumerate(scored_items):
                candidates.append(
                    ReviewCandidate(
                        candidate_id=f"cand-ent-{item_id}",
                        review_unit="item",
                        item_id=item_id,
                        prioritization_method="highest_entropy",
                        score=float(h_i),
                        score_components={"normalized_entropy": float(h_i)},
                        rank=idx + 1,
                    )
                )

    elif method == "lowest_consensus_confidence":
        if review_unit == "annotation":
            scored_ds_annos: list[tuple[float, bool, str, Annotation]] = []
            for a in dataset_annotations:
                feat = item_features[a.item_id]
                if feat.ds_status == "success" and feat.ds_max_posterior is not None:
                    u_i = float(1.0 - feat.ds_max_posterior)
                    eligible = True
                else:
                    u_i = 0.0
                    eligible = False
                scored_ds_annos.append((u_i, eligible, a.annotation_id, a))
            scored_ds_annos.sort(key=lambda x: (not x[1], -x[0], x[2]))

            for idx, (u_i, eligible, _c_id, a) in enumerate(scored_ds_annos):
                candidates.append(
                    ReviewCandidate(
                        candidate_id=f"cand-ds-{a.annotation_id}",
                        review_unit="annotation",
                        item_id=a.item_id,
                        annotation_id=a.annotation_id,
                        annotator_id=a.annotator_id,
                        submitted_label=a.label,
                        prioritization_method="lowest_consensus_confidence",
                        score=float(u_i),
                        score_components={"ds_uncertainty": float(u_i)},
                        rank=idx + 1,
                        eligible_coverage=eligible,
                    )
                )
        else:
            scored_ds_items: list[tuple[float, bool, str]] = []
            for item_id in item_ids:
                feat = item_features[item_id]
                if feat.ds_status == "success" and feat.ds_max_posterior is not None:
                    u_i = float(1.0 - feat.ds_max_posterior)
                    eligible = True
                else:
                    u_i = 0.0
                    eligible = False
                scored_ds_items.append((u_i, eligible, item_id))
            scored_ds_items.sort(key=lambda x: (not x[1], -x[0], x[2]))

            for idx, (u_i, eligible, item_id) in enumerate(scored_ds_items):
                candidates.append(
                    ReviewCandidate(
                        candidate_id=f"cand-ds-{item_id}",
                        review_unit="item",
                        item_id=item_id,
                        prioritization_method="lowest_consensus_confidence",
                        score=float(u_i),
                        score_components={"ds_uncertainty": float(u_i)},
                        rank=idx + 1,
                        eligible_coverage=eligible,
                    )
                )

    elif method == "lowest_worker_reliability":
        if review_unit == "annotation":
            scored_wrel_annos: list[tuple[float, bool, str, Annotation]] = []
            for a in dataset_annotations:
                w = a.annotator_id
                rel = worker_gold_reliabilities.get(w)
                if rel and rel.evaluated_gold_items > 0:
                    e_i = float(1.0 - rel.posterior_mean)
                    eligible = True
                else:
                    e_i = 0.0
                    eligible = False
                scored_wrel_annos.append((e_i, eligible, a.annotation_id, a))
            scored_wrel_annos.sort(key=lambda x: (not x[1], -x[0], x[2]))

            for idx, (e_i, eligible, _c_id, a) in enumerate(scored_wrel_annos):
                candidates.append(
                    ReviewCandidate(
                        candidate_id=f"cand-wrel-{a.annotation_id}",
                        review_unit="annotation",
                        item_id=a.item_id,
                        annotation_id=a.annotation_id,
                        annotator_id=a.annotator_id,
                        submitted_label=a.label,
                        prioritization_method="lowest_worker_reliability",
                        score=float(e_i),
                        score_components={"mean_worker_error": float(e_i)},
                        rank=idx + 1,
                        eligible_coverage=eligible,
                    )
                )
        else:
            scored_wrel_items: list[tuple[float, bool, str]] = []
            for item_id in item_ids:
                item_annos = [a for a in dataset_annotations if a.item_id == item_id]
                worker_errors = []
                for a in item_annos:
                    rel = worker_gold_reliabilities.get(a.annotator_id)
                    if rel and rel.evaluated_gold_items > 0:
                        worker_errors.append(1.0 - rel.posterior_mean)
                if worker_errors:
                    e_i = float(np.mean(worker_errors))
                    eligible = True
                else:
                    e_i = 0.0
                    eligible = False
                scored_wrel_items.append((e_i, eligible, item_id))
            scored_wrel_items.sort(key=lambda x: (not x[1], -x[0], x[2]))

            for idx, (e_i, eligible, item_id) in enumerate(scored_wrel_items):
                candidates.append(
                    ReviewCandidate(
                        candidate_id=f"cand-wrel-{item_id}",
                        review_unit="item",
                        item_id=item_id,
                        prioritization_method="lowest_worker_reliability",
                        score=float(e_i),
                        score_components={"mean_worker_error": float(e_i)},
                        rank=idx + 1,
                        eligible_coverage=eligible,
                    )
                )

    elif method == "erv":
        if review_unit == "annotation":
            scored_erv_annos: list[tuple[float, ErvScoreComponents, str, Annotation]] = []
            for a in dataset_annotations:
                item_id = a.item_id
                feat = item_features[item_id]

                if feat.ds_status == "success" and feat.ds_max_posterior is not None:
                    u_i = float(1.0 - feat.ds_max_posterior)
                else:
                    u_i = 0.0

                h_i = float(feat.normalized_entropy if feat.normalized_entropy is not None else 0.0)

                item_annos = [ann for ann in dataset_annotations if ann.item_id == item_id]
                worker_errors = []
                for ann in item_annos:
                    rel = worker_gold_reliabilities.get(ann.annotator_id)
                    if rel and rel.evaluated_gold_items > 0:
                        worker_errors.append(1.0 - rel.posterior_mean)
                    else:
                        worker_errors.append(0.50)
                e_i = float(np.mean(worker_errors)) if worker_errors else 0.50

                raw_score = float(
                    erv_cfg.weight_uncert * u_i
                    + erv_cfg.weight_entropy * h_i
                    + erv_cfg.weight_worker_error * e_i
                )

                comp = ErvScoreComponents(u_i=u_i, h_i=h_i, e_i=e_i, raw_score=raw_score)
                scored_erv_annos.append((raw_score, comp, a.annotation_id, a))
            scored_erv_annos.sort(key=lambda x: (-x[0], x[2]))

            for idx, (score_val, comp, _c_id, a) in enumerate(scored_erv_annos):
                candidates.append(
                    ReviewCandidate(
                        candidate_id=f"cand-erv-{a.annotation_id}",
                        review_unit="annotation",
                        item_id=a.item_id,
                        annotation_id=a.annotation_id,
                        annotator_id=a.annotator_id,
                        submitted_label=a.label,
                        prioritization_method="erv",
                        score=score_val,
                        score_components=comp,
                        rank=idx + 1,
                    )
                )
        else:
            scored_erv_items: list[tuple[float, ErvScoreComponents, str]] = []
            for item_id in item_ids:
                feat = item_features[item_id]

                if feat.ds_status == "success" and feat.ds_max_posterior is not None:
                    u_i = float(1.0 - feat.ds_max_posterior)
                else:
                    u_i = 0.0

                h_i = float(feat.normalized_entropy if feat.normalized_entropy is not None else 0.0)

                item_annos = [a for a in dataset_annotations if a.item_id == item_id]
                worker_errors = []
                for a in item_annos:
                    rel = worker_gold_reliabilities.get(a.annotator_id)
                    if rel and rel.evaluated_gold_items > 0:
                        worker_errors.append(1.0 - rel.posterior_mean)
                    else:
                        worker_errors.append(0.50)
                e_i = float(np.mean(worker_errors)) if worker_errors else 0.50

                raw_score = float(
                    erv_cfg.weight_uncert * u_i
                    + erv_cfg.weight_entropy * h_i
                    + erv_cfg.weight_worker_error * e_i
                )

                comp = ErvScoreComponents(u_i=u_i, h_i=h_i, e_i=e_i, raw_score=raw_score)
                scored_erv_items.append((raw_score, comp, item_id))
            scored_erv_items.sort(key=lambda x: (-x[0], x[2]))

            for idx, (score_val, comp, item_id) in enumerate(scored_erv_items):
                candidates.append(
                    ReviewCandidate(
                        candidate_id=f"cand-erv-{item_id}",
                        review_unit="item",
                        item_id=item_id,
                        prioritization_method="erv",
                        score=score_val,
                        score_components=comp,
                        rank=idx + 1,
                    )
                )

    return candidates
