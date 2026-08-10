from __future__ import annotations

import math

import pytest
from dataqual.analysis.core import Annotation
from dataqual.annotators import compute_beta_binomial_reliability
from dataqual.diagnostics import (
    DEFAULT_DIAGNOSTIC_CONFIG,
    evaluate_item_diagnostics,
    extract_item_disagreement_features,
)
from dataqual.schemas.core import GoldLabel


def test_normalized_entropy_calculation() -> None:
    labels = ["positive", "neutral", "negative"]  # K = 3
    annos = [
        Annotation("a1", "i1", "w1", "positive"),
        Annotation("a2", "i1", "w2", "positive"),
        Annotation("a3", "i1", "w3", "negative"),
    ]

    feat = extract_item_disagreement_features("i1", annos, labels, annos, [])
    assert feat.annotation_count == 3
    expected_h = -(2 / 3 * math.log(2 / 3) + 1 / 3 * math.log(1 / 3))
    expected_hnorm = expected_h / math.log(3)

    assert feat.vote_entropy == pytest.approx(expected_h, abs=1e-4)
    assert feat.normalized_entropy == pytest.approx(expected_hnorm, abs=1e-4)
    assert feat.vote_margin == pytest.approx(2 / 3 - 1 / 3, abs=1e-4)

    # Single domain class (K=1) returns None
    feat_k1 = extract_item_disagreement_features("i1", annos, ["positive"], annos, [])
    assert feat_k1.normalized_entropy is None


def test_annotation_entity_semantics_for_dissenting_weak_worker() -> None:
    labels = ["positive", "negative"]
    annos = [
        Annotation("a1", "i1", "w1", "positive"),
        Annotation("a2", "i1", "w2", "positive"),
        Annotation("a3", "i1", "w3", "positive"),
        Annotation("a4", "i1", "w4", "negative"),
    ]

    # W4 has weak trusted gold reliability (1 correct out of 20 = upper bound ~ 0.25 < 0.50)
    gold_labels: list[GoldLabel] = []
    all_annos = list(annos)
    for k in range(20):
        item_id = f"g_item_{k}"
        emitted = "positive" if k == 0 else "negative"
        all_annos.append(Annotation(f"a_w4_{k}", item_id, "w4", emitted))
        gold_labels.append(
            GoldLabel(
                gold_label_id=f"g_{k}",
                project_id="p1",
                item_id=item_id,
                label_domain_id="d1",
                label="positive",
                resolution_status="resolved_hard",
                gold_source="expert_adjudication",
                version=1,
                created_at="2026-08-09T00:00:00Z",
            )
        )

    feat = extract_item_disagreement_features("i1", annos, labels, all_annos, gold_labels)
    flags = evaluate_item_diagnostics(feat, annos, "snap1", "p1")

    # Should produce an ANNOTATION entity flag for w4 (Amendment 1)
    anno_flag = next((f for f in flags if f.entity_type == "annotation"), None)
    assert anno_flag is not None
    assert anno_flag.flag_type == "probable_quality_defect"
    assert anno_flag.recommended_action == "review_annotation"
    assert anno_flag.threshold_config_version == DEFAULT_DIAGNOSTIC_CONFIG.version
    assert anno_flag.threshold_config_hash == DEFAULT_DIAGNOSTIC_CONFIG.config_hash()
    assert "CREDIBLY_LOW" in anno_flag.explanation


def test_lower_bound_below_threshold_does_not_imply_credibly_low() -> None:
    # Worker with 3/3 correct -> lower bound ~ 0.28 < 0.50, upper bound ~ 0.95 >= 0.50
    annos: list[Annotation] = []
    golds: list[GoldLabel] = []
    for k in range(3):
        item_id = f"i_{k}"
        annos.append(Annotation(f"a_{k}", item_id, "w1", "positive"))
        golds.append(
            GoldLabel(
                gold_label_id=f"g_{k}",
                project_id="p1",
                item_id=item_id,
                label_domain_id="d1",
                label="positive",
                resolution_status="resolved_hard",
                gold_source="expert_adjudication",
                version=1,
                created_at="2026-08-09T00:00:00Z",
            )
        )

    est = compute_beta_binomial_reliability(annos, golds, "w1")
    assert est.lower_bound < 0.50
    assert est.upper_bound >= 0.50
    # MUST NOT be CREDIBLY_LOW
    assert est.reliability_evidence_state == "UNCERTAIN"


def test_interval_crossing_threshold_yields_uncertain_state() -> None:
    annos = [
        Annotation("a1", "i1", "w1", "positive"),
        Annotation("a2", "i2", "w1", "positive"),
    ]
    golds = [
        GoldLabel(
            gold_label_id="g1",
            project_id="p1",
            item_id="i1",
            label_domain_id="d1",
            label="positive",
            resolution_status="resolved_hard",
            gold_source="expert_adjudication",
            version=1,
            created_at="2026-08-09T00:00:00Z",
        ),
        GoldLabel(
            gold_label_id="g2",
            project_id="p1",
            item_id="i2",
            label_domain_id="d1",
            label="negative",
            resolution_status="resolved_hard",
            gold_source="expert_adjudication",
            version=1,
            created_at="2026-08-09T00:00:00Z",
        ),
    ]

    est = compute_beta_binomial_reliability(annos, golds, "w1")
    assert est.lower_bound < 0.50
    assert est.upper_bound >= 0.50
    assert est.reliability_evidence_state == "UNCERTAIN"


def test_upper_bound_below_threshold_yields_credibly_low_state() -> None:
    annos: list[Annotation] = []
    golds: list[GoldLabel] = []
    # 1 correct out of 20
    for k in range(20):
        item_id = f"i_{k}"
        label = "positive" if k == 0 else "negative"
        annos.append(Annotation(f"a_{k}", item_id, "w1", "positive"))
        golds.append(
            GoldLabel(
                gold_label_id=f"g_{k}",
                project_id="p1",
                item_id=item_id,
                label_domain_id="d1",
                label=label,
                resolution_status="resolved_hard",
                gold_source="expert_adjudication",
                version=1,
                created_at="2026-08-09T00:00:00Z",
            )
        )

    est = compute_beta_binomial_reliability(annos, golds, "w1")
    assert est.upper_bound < 0.50
    assert est.reliability_evidence_state == "CREDIBLY_LOW"


def test_small_n_uncertainty_is_not_defect_flag() -> None:
    labels = ["positive", "negative"]
    # Item has consensus lead positive (3 votes positive from w1, w2, w3)
    # Worker w_small dissents with negative. w_small has only 3 gold items
    # (3/3 correct = UNCERTAIN state)
    item_annos = [
        Annotation("a1", "target_item", "w1", "positive"),
        Annotation("a2", "target_item", "w2", "positive"),
        Annotation("a3", "target_item", "w3", "positive"),
        Annotation("a4", "target_item", "w_small", "negative"),
    ]
    all_annos = list(item_annos)
    golds: list[GoldLabel] = []
    for k in range(3):
        item_id = f"g_small_{k}"
        all_annos.append(Annotation(f"a_s_{k}", item_id, "w_small", "positive"))
        golds.append(
            GoldLabel(
                gold_label_id=f"g_s_{k}",
                project_id="p1",
                item_id=item_id,
                label_domain_id="d1",
                label="positive",
                resolution_status="resolved_hard",
                gold_source="expert_adjudication",
                version=1,
                created_at="2026-08-09T00:00:00Z",
            )
        )

    feat = extract_item_disagreement_features("target_item", item_annos, labels, all_annos, golds)
    assert feat.dissenting_worker_reliability_states.get("w_small") == "UNCERTAIN"

    flags = evaluate_item_diagnostics(feat, item_annos, "snap1", "p1")
    # Small-N uncertainty must NOT trigger probable_quality_defect!
    defect_flags = [f for f in flags if f.flag_type == "probable_quality_defect"]
    assert len(defect_flags) == 0


def test_rule_explanation_reports_interval_n_threshold_and_state() -> None:
    labels = ["positive", "negative"]
    item_annos = [
        Annotation("a1", "i1", "w1", "positive"),
        Annotation("a2", "i1", "w2", "positive"),
        Annotation("a3", "i1", "w3", "positive"),
        Annotation("a4", "i1", "w_weak", "negative"),
    ]
    all_annos = list(item_annos)
    golds: list[GoldLabel] = []
    for k in range(20):
        item_id = f"g_{k}"
        label = "positive" if k == 0 else "negative"
        all_annos.append(Annotation(f"a_w_{k}", item_id, "w_weak", "positive"))
        golds.append(
            GoldLabel(
                gold_label_id=f"g_{k}",
                project_id="p1",
                item_id=item_id,
                label_domain_id="d1",
                label=label,
                resolution_status="resolved_hard",
                gold_source="expert_adjudication",
                version=1,
                created_at="2026-08-09T00:00:00Z",
            )
        )

    feat = extract_item_disagreement_features("i1", item_annos, labels, all_annos, golds)
    flags = evaluate_item_diagnostics(feat, item_annos, "snap1", "p1")

    defect_flag = next(f for f in flags if f.flag_type == "probable_quality_defect")
    assert "CREDIBLY_LOW" in defect_flag.explanation
    assert "0.50" in defect_flag.explanation
    assert defect_flag.entity_type == "annotation"


def test_item_entity_probable_ambiguity() -> None:
    labels = ["positive", "neutral", "negative"]
    annos = [
        Annotation("a1", "i1", "w1", "positive"),
        Annotation("a2", "i1", "w2", "negative"),
    ]
    feat = extract_item_disagreement_features("i1", annos, labels, annos, [])
    flags = evaluate_item_diagnostics(feat, annos, "snap1", "p1")

    ambiguity_flag = next(
        (f for f in flags if f.flag_type == "probable_ambiguity_policy_issue"), None
    )
    assert ambiguity_flag is not None
    assert ambiguity_flag.entity_type == "item"
    assert ambiguity_flag.recommended_action == "clarify_policy"


def test_insufficient_evidence_flag() -> None:
    labels = ["positive", "negative"]
    annos = [Annotation("a1", "i1", "w1", "positive")]  # only 1 annotation
    feat = extract_item_disagreement_features("i1", annos, labels, annos, [])
    flags = evaluate_item_diagnostics(feat, annos, "snap1", "p1")

    assert len(flags) == 1
    assert flags[0].flag_type == "insufficient_evidence"
    assert flags[0].recommended_action == "collect_more_labels"
