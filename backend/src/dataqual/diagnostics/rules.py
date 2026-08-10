from __future__ import annotations

import datetime
import uuid
from collections.abc import Sequence

from dataqual.analysis.core import Annotation
from dataqual.diagnostics.config import DEFAULT_DIAGNOSTIC_CONFIG, DiagnosticThresholdConfig
from dataqual.schemas.diagnostics import ItemDisagreementFeatures, QualityFlag


def evaluate_item_diagnostics(
    features: ItemDisagreementFeatures,
    item_annotations: Sequence[Annotation],
    dataset_snapshot_id: str,
    project_id: str,
    cfg: DiagnosticThresholdConfig = DEFAULT_DIAGNOSTIC_CONFIG,
) -> list[QualityFlag]:
    flags: list[QualityFlag] = []
    now_str = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

    m_i = features.annotation_count
    entropy_norm = features.normalized_entropy if features.normalized_entropy is not None else 0.0
    margin = features.vote_margin

    # 1. Insufficient Evidence
    if m_i < cfg.min_annotations_for_consensus:
        flags.append(
            QualityFlag(
                quality_flag_id=f"qf-{uuid.uuid4().hex[:12]}",
                dataset_snapshot_id=dataset_snapshot_id,
                project_id=project_id,
                entity_type="item",
                entity_id=features.item_id,
                flag_type="insufficient_evidence",
                severity="info",
                evidence={
                    "annotation_count": m_i,
                    "min_required": cfg.min_annotations_for_consensus,
                },
                support_n=m_i,
                threshold_config_version=cfg.version,
                threshold_config_hash=cfg.config_hash(),
                thresholds_used={
                    "min_annotations_for_consensus": cfg.min_annotations_for_consensus
                },
                recommended_action="collect_more_labels",
                created_at=now_str,
                explanation=(
                    f"Item has only {m_i} annotation(s). Minimum "
                    f"{cfg.min_annotations_for_consensus} required for consensus diagnostics."
                ),
            )
        )
        return flags

    # Check for Dissenting Worker Defect vs Item Ambiguity
    top_prop = max(features.vote_proportions.values()) if features.vote_proportions else 0.0
    has_strong_consensus_lead = top_prop >= 0.60 or margin >= cfg.margin_small_threshold

    # Dissenting worker classification based on explicit reliability evidence states:
    # CREDIBLY_LOW: upper_bound < weak_threshold (0.50) -> strong evidence of weak worker
    # UNCERTAIN: lower_bound < weak_threshold AND upper_bound >= weak_threshold
    # NOT_LOW: lower_bound >= weak_threshold -> strong worker
    credibly_low_dissenters: list[str] = []
    uncertain_dissenters: list[str] = []
    not_low_dissenters: list[str] = []

    for w_id in features.dissenting_worker_ids:
        state = features.dissenting_worker_reliability_states.get(w_id, "NO_GOLD")
        if state == "CREDIBLY_LOW":
            credibly_low_dissenters.append(w_id)
        elif state == "UNCERTAIN":
            uncertain_dissenters.append(w_id)
        elif state == "NOT_LOW":
            not_low_dissenters.append(w_id)

    is_high_entropy = entropy_norm >= cfg.entropy_high_threshold
    is_small_margin = margin <= cfg.margin_small_threshold
    has_non_weak_dissent = (len(not_low_dissenters) + len(uncertain_dissenters)) >= 1
    is_split = has_non_weak_dissent and features.distinct_labels_count >= 2

    # Ambiguity evidence among non-weak/uncertain sources
    has_non_weak_ambiguity = (
        is_small_margin or is_split or (is_high_entropy and has_non_weak_dissent)
    )
    has_defect_evidence = len(credibly_low_dissenters) >= 1
    has_any_ambiguity = is_high_entropy or is_small_margin or is_split

    # 2. Mixed Evidence Flag (Contradictory Defect & Ambiguity Evidence)
    if has_defect_evidence and has_non_weak_ambiguity:
        flags.append(
            QualityFlag(
                quality_flag_id=f"qf-{uuid.uuid4().hex[:12]}",
                dataset_snapshot_id=dataset_snapshot_id,
                project_id=project_id,
                entity_type="item",
                entity_id=features.item_id,
                flag_type="mixed_evidence",
                severity="medium",
                evidence={
                    "normalized_entropy": entropy_norm,
                    "vote_margin": margin,
                    "credibly_low_dissenters": credibly_low_dissenters,
                    "uncertain_dissenters": uncertain_dissenters,
                    "not_low_dissenters": not_low_dissenters,
                },
                support_n=m_i,
                threshold_config_version=cfg.version,
                threshold_config_hash=cfg.config_hash(),
                thresholds_used={
                    "entropy_high_threshold": cfg.entropy_high_threshold,
                    "worker_weak_bound_threshold": cfg.worker_weak_bound_threshold,
                },
                recommended_action="inspect_overlap",
                created_at=now_str,
                explanation=(
                    "Item exhibits mixed diagnostic signals: combines both credibly low "
                    f"annotator dissent ({len(credibly_low_dissenters)} worker(s)) "
                    "and item ambiguity / non-weak worker dissent."
                ),
            )
        )

    # 3. Annotation-Level Defect Flag (Pure Defect Evidence)
    elif has_defect_evidence and has_strong_consensus_lead:
        for w_id in credibly_low_dissenters:
            diss_anno = next((a for a in item_annotations if a.annotator_id == w_id), None)
            entity_id = diss_anno.annotation_id if diss_anno else f"{features.item_id}#{w_id}"
            diss_label = diss_anno.label if diss_anno else "unknown"

            flags.append(
                QualityFlag(
                    quality_flag_id=f"qf-{uuid.uuid4().hex[:12]}",
                    dataset_snapshot_id=dataset_snapshot_id,
                    project_id=project_id,
                    entity_type="annotation",
                    entity_id=entity_id,
                    flag_type="probable_quality_defect",
                    severity="medium",
                    evidence={
                        "item_id": features.item_id,
                        "dissenting_annotator_id": w_id,
                        "dissenting_label": diss_label,
                        "consensus_lead_label": features.mv_label,
                        "vote_margin": margin,
                        "reliability_evidence_state": "CREDIBLY_LOW",
                        "weak_threshold": cfg.worker_weak_bound_threshold,
                    },
                    support_n=m_i,
                    threshold_config_version=cfg.version,
                    threshold_config_hash=cfg.config_hash(),
                    thresholds_used={
                        "worker_weak_bound_threshold": cfg.worker_weak_bound_threshold,
                        "margin_small_threshold": cfg.margin_small_threshold,
                    },
                    recommended_action="review_annotation",
                    created_at=now_str,
                    explanation=(
                        f"Dissenting annotation by worker '{w_id}' "
                        f"(submitted label '{diss_label}') "
                        f"conflicts with consensus lead '{features.mv_label}'. "
                        "Worker reliability evidence state is CREDIBLY_LOW "
                        f"(upper bound < {cfg.worker_weak_bound_threshold:.2f})."
                    ),
                )
            )

    # 4. Item-Level Probable Ambiguity / Policy Issue (Pure Ambiguity Evidence)
    elif has_any_ambiguity:
        severity_val = "high" if (is_high_entropy and is_small_margin) else "medium"
        flags.append(
            QualityFlag(
                quality_flag_id=f"qf-{uuid.uuid4().hex[:12]}",
                dataset_snapshot_id=dataset_snapshot_id,
                project_id=project_id,
                entity_type="item",
                entity_id=features.item_id,
                flag_type="probable_ambiguity_policy_issue",
                severity=severity_val,
                evidence={
                    "normalized_entropy": entropy_norm,
                    "vote_margin": margin,
                    "distinct_labels_count": features.distinct_labels_count,
                    "method_disagreement": features.method_disagreement,
                    "uncertain_dissenters": uncertain_dissenters,
                    "not_low_dissenters": not_low_dissenters,
                },
                support_n=m_i,
                threshold_config_version=cfg.version,
                threshold_config_hash=cfg.config_hash(),
                thresholds_used={
                    "entropy_high_threshold": cfg.entropy_high_threshold,
                    "margin_small_threshold": cfg.margin_small_threshold,
                },
                recommended_action="clarify_policy",
                created_at=now_str,
                explanation=(
                    f"Item shows high vote entropy ({entropy_norm:.2f}) and small vote margin "
                    f"({margin:.2f}) across {features.distinct_labels_count} distinct labels. "
                    "Disagreement persists without credibly low annotator reliability evidence."
                ),
            )
        )

    # 5. No Flag (Clean item)
    if not flags:
        flags.append(
            QualityFlag(
                quality_flag_id=f"qf-{uuid.uuid4().hex[:12]}",
                dataset_snapshot_id=dataset_snapshot_id,
                project_id=project_id,
                entity_type="item",
                entity_id=features.item_id,
                flag_type="no_flag",
                severity="info",
                evidence={
                    "vote_margin": margin,
                    "normalized_entropy": entropy_norm,
                },
                support_n=m_i,
                threshold_config_version=cfg.version,
                threshold_config_hash=cfg.config_hash(),
                thresholds_used={},
                recommended_action="no_action",
                created_at=now_str,
                explanation=(
                    "Item shows high consensus agreement and low vote entropy with "
                    "no quality defects."
                ),
            )
        )

    return flags
