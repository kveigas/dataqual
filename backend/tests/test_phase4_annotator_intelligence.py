from __future__ import annotations

import pytest
import scipy.stats as stats
from dataqual.analysis.core import Annotation
from dataqual.annotators import (
    compute_annotator_calibration,
    compute_beta_binomial_reliability,
    compute_dirichlet_confusion,
)
from dataqual.schemas.core import GoldLabel


def test_beta_binomial_mathematical_validation() -> None:
    # 1. Zero successes / zero failures (no gold)
    annotations: list[Annotation] = []
    gold_labels: list[GoldLabel] = []

    res_no_gold = compute_beta_binomial_reliability(annotations, gold_labels, "w1")
    assert res_no_gold.successes == 0
    assert res_no_gold.failures == 0
    assert res_no_gold.evidence_status == "no_gold"
    assert res_no_gold.prior_source == "fallback_symmetric"
    assert res_no_gold.posterior_mean == 0.5
    assert res_no_gold.lower_bound == pytest.approx(stats.beta.ppf(0.025, 1.0, 1.0), abs=1e-5)

    # 2. Leave-one-out prior property with > 20 other gold evaluations
    annos = [
        Annotation("a1", "i1", "w1", "positive"),
        Annotation("a2", "i2", "w1", "positive"),
    ]
    # Add 30 gold annotations for w2 (24 correct, 6 incorrect)
    for k in range(30):
        item_id = f"gold_item_{k}"
        label = "positive" if k < 24 else "negative"
        annos.append(Annotation(f"a_w2_{k}", item_id, "w2", "positive"))
        gold_labels.append(
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

    res_w1 = compute_beta_binomial_reliability(annos, gold_labels, "w1")
    assert res_w1.prior_source == "leave_one_out_project"
    assert res_w1.prior_population_n == 30
    assert res_w1.prior_mean == pytest.approx(24.5 / 31.0, abs=1e-5)

    # SciPy exact check
    alpha_0 = 2.0 * (24.5 / 31.0)
    beta_0 = 2.0 * (1.0 - 24.5 / 31.0)
    assert res_w1.posterior_mean == pytest.approx(alpha_0 / (alpha_0 + beta_0), abs=1e-5)
    assert res_w1.lower_bound == pytest.approx(stats.beta.ppf(0.025, alpha_0, beta_0), abs=1e-5)


def test_dirichlet_confusion_marginal_intervals() -> None:
    labels = ["positive", "neutral", "negative"]
    annos = [
        Annotation("a1", "i1", "w1", "positive"),
        Annotation("a2", "i2", "w1", "negative"),
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
            label="positive",
            resolution_status="resolved_hard",
            gold_source="expert_adjudication",
            version=1,
            created_at="2026-08-09T00:00:00Z",
        ),
    ]

    conf = compute_dirichlet_confusion(annos, golds, labels, "w1")
    assert conf.annotator_id == "w1"
    assert conf.raw_counts[0] == [1, 0, 1]  # gold=positive: 1 positive, 1 negative
    assert conf.row_support["positive"] == 2
    assert conf.row_support["neutral"] == 0

    # Marginal Beta interval check for row 0 cell 0
    # n_c = 2, K = 3, count = 1 -> a = 1.5, b = 1.0 + 0.5*2 = 2.0
    cell0 = next(
        c
        for c in conf.cell_intervals
        if c.true_class == "positive" and c.emitted_label == "positive"
    )
    assert cell0.smoothed_probability == pytest.approx(1.5 / 3.5, abs=1e-5)
    assert cell0.marginal_lower_bound == pytest.approx(stats.beta.ppf(0.025, 1.5, 2.0), abs=1e-5)
    assert cell0.marginal_upper_bound == pytest.approx(stats.beta.ppf(0.975, 1.5, 2.0), abs=1e-5)


def test_calibration_metrics() -> None:
    annos = [
        Annotation("a1", "i1", "w1", "positive", confidence=0.9),
        Annotation("a2", "i2", "w1", "positive", confidence=0.8),
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

    cal = compute_annotator_calibration(annos, golds, "w1")
    assert cal.status == "available"
    assert cal.observations == 2
    # Brier: mean of (0.9 - 1)^2 and (0.8 - 0)^2 = mean(0.01, 0.64) = 0.325
    assert cal.brier_score == pytest.approx(0.325, abs=1e-4)

    # Unobserved confidence test
    annos_no_conf = [
        Annotation("a1", "i1", "w1", "positive"),
    ]
    cal_no_conf = compute_annotator_calibration(annos_no_conf, golds, "w1")
    assert cal_no_conf.status == "not_available"
    assert cal_no_conf.brier_score is None
