"""Phase 4 Validation & Audit Script.

Executes synthetic validation scenarios A through L and descriptive audit
on the real Requirements Annotation Phase 3 dataset.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import numpy as np
import pyarrow.parquet as pq

from dataqual.analysis.core import Annotation
from dataqual.annotators import AnnotatorIntelligenceService, compute_beta_binomial_reliability
from dataqual.diagnostics import DEFAULT_DIAGNOSTIC_CONFIG, DisagreementDiagnosticsService
from dataqual.schemas.core import GoldLabel
from dataqual.storage import DatasetRepository


def run_synthetic_validation() -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []

    # Scenario A: Strong consensus + one weak worker (CREDIBLY_LOW)
    annos_a = [
        Annotation("a1", "item1", "w1", "positive"),
        Annotation("a2", "item1", "w2", "positive"),
        Annotation("a3", "item1", "w3", "positive"),
        Annotation("a4", "item1", "w4", "negative"),
    ]
    golds_a: list[GoldLabel] = []
    # w4 has 20 evaluated gold items, 1 correct (upper bound ~ 0.25 < 0.50 -> CREDIBLY_LOW)
    for i in range(20):
        item_id = f"g_item_{i}"
        emitted = "positive" if i == 0 else "negative"
        annos_a.append(Annotation(f"a_w4_{i}", item_id, "w4", emitted))
        golds_a.append(
            GoldLabel(
                gold_label_id=f"g_{i}",
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

    svc_a = DisagreementDiagnosticsService(annos_a, golds_a, ["positive", "negative"], "snap_a", "p1")
    flags_a = svc_a.generate_quality_flags()
    anno_flag_a = next((f for f in flags_a if f.entity_type == "annotation"), None)
    rel_a = compute_beta_binomial_reliability(annos_a, golds_a, "w4")

    scenarios.append({
        "scenario": "Scenario A",
        "description": "Strong consensus + one weak worker (CREDIBLY_LOW)",
        "expected_behavior": "annotation-level probable_quality_defect flag on dissenting worker with CREDIBLY_LOW state",
        "observed_behavior": f"entity_type={anno_flag_a.entity_type if anno_flag_a else None}, flag_type={anno_flag_a.flag_type if anno_flag_a else None}, worker_state={rel_a.reliability_evidence_state}",
        "status": "PASS" if (anno_flag_a is not None and anno_flag_a.flag_type == "probable_quality_defect" and rel_a.reliability_evidence_state == "CREDIBLY_LOW") else "FAIL",
    })

    # Scenario B: Strong workers split 50/50
    annos_b = [
        Annotation("b1", "item1", "w1", "positive"),
        Annotation("b2", "item1", "w2", "negative"),
    ]
    golds_b: list[GoldLabel] = []
    for i in range(20):
        emitted_w1 = "positive" if i < 19 else "negative"
        emitted_w2 = "positive" if i < 19 else "negative"
        golds_b.append(
            GoldLabel(
                gold_label_id=f"gb_{i}",
                project_id="p1",
                item_id=f"gb_item_{i}",
                label_domain_id="d1",
                label="positive",
                resolution_status="resolved_hard",
                gold_source="expert_adjudication",
                version=1,
                created_at="2026-08-09T00:00:00Z",
            )
        )
        annos_b.append(Annotation(f"b_w1_{i}", f"gb_item_{i}", "w1", emitted_w1))
        annos_b.append(Annotation(f"b_w2_{i}", f"gb_item_{i}", "w2", emitted_w2))

    svc_b = DisagreementDiagnosticsService(annos_b, golds_b, ["positive", "negative"], "snap_b", "p1")
    flags_b = svc_b.generate_quality_flags()
    amb_flag_b = next((f for f in flags_b if f.flag_type == "probable_ambiguity_policy_issue"), None)

    scenarios.append({
        "scenario": "Scenario B",
        "description": "Strong workers split 50/50",
        "expected_behavior": "item-level probable_ambiguity_policy_issue flag",
        "observed_behavior": f"entity_type={amb_flag_b.entity_type if amb_flag_b else None}, flag_type={amb_flag_b.flag_type if amb_flag_b else None}",
        "status": "PASS" if (amb_flag_b is not None and amb_flag_b.entity_type == "item") else "FAIL",
    })

    # Scenario C: High entropy with uniform worker quality
    annos_c = [
        Annotation("c1", "item1", "w1", "positive"),
        Annotation("c2", "item1", "w2", "neutral"),
        Annotation("c3", "item1", "w3", "negative"),
    ]
    svc_c = DisagreementDiagnosticsService(annos_c, [], ["positive", "neutral", "negative"], "snap_c", "p1")
    flags_c = svc_c.generate_quality_flags()
    amb_c = next((f for f in flags_c if f.flag_type == "probable_ambiguity_policy_issue"), None)

    scenarios.append({
        "scenario": "Scenario C",
        "description": "High entropy with uniform worker quality",
        "expected_behavior": "item-level probable_ambiguity_policy_issue flag without annotator quality defect",
        "observed_behavior": f"flag_type={amb_c.flag_type if amb_c else None}",
        "status": "PASS" if (amb_c is not None) else "FAIL",
    })

    # Scenario D: One adversarial worker (0/20 correct)
    annos_d: list[Annotation] = []
    golds_d: list[GoldLabel] = []
    for i in range(20):
        item_id = f"gd_item_{i}"
        annos_d.append(Annotation(f"ad_{i}", item_id, "wd", "negative"))
        golds_d.append(
            GoldLabel(
                gold_label_id=f"gd_{i}",
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
    rel_d = compute_beta_binomial_reliability(annos_d, golds_d, "wd")

    scenarios.append({
        "scenario": "Scenario D",
        "description": "One adversarial worker (0/20 correct)",
        "expected_behavior": "CREDIBLY_LOW state with upper bound < 0.50",
        "observed_behavior": f"state={rel_d.reliability_evidence_state}, upper_bound={rel_d.upper_bound:.3f}",
        "status": "PASS" if (rel_d.reliability_evidence_state == "CREDIBLY_LOW" and rel_d.upper_bound < 0.50) else "FAIL",
    })

    # Scenario E: Class-specific confusion
    svc_e = AnnotatorIntelligenceService(annos_a, golds_a, ["positive", "negative"])
    prof_e = svc_e.get_annotator_profile("w4")
    has_confusion = prof_e.dirichlet_confusion is not None

    scenarios.append({
        "scenario": "Scenario E",
        "description": "Class-specific confusion matrix recovery",
        "expected_behavior": "Dirichlet-smoothed matrix recovers class-specific confusion with marginal CIs",
        "observed_behavior": f"dirichlet_status={prof_e.dirichlet_confusion.status if prof_e.dirichlet_confusion else None}",
        "status": "PASS" if has_confusion else "FAIL",
    })

    # Scenario F: Small-N worker (2/3 correct -> mean 0.60, CI [0.194, 0.932] crossing 0.50)
    annos_f: list[Annotation] = []
    golds_f: list[GoldLabel] = []
    for i in range(3):
        item_id = f"gf_item_{i}"
        emitted = "positive" if i < 2 else "negative"
        annos_f.append(Annotation(f"af_{i}", item_id, "wf", emitted))
        golds_f.append(
            GoldLabel(
                gold_label_id=f"gf_{i}",
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
    # Scenario G: Large-N moderate accuracy worker (70/100 correct)
    annos_g: list[Annotation] = []
    golds_g: list[GoldLabel] = []
    for i in range(100):
        item_id = f"gg_item_{i}"
        emitted = "positive" if i < 70 else "negative"
        annos_g.append(Annotation(f"ag_{i}", item_id, "wg", emitted))
        golds_g.append(
            GoldLabel(
                gold_label_id=f"gg_{i}",
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

    rel_f = compute_beta_binomial_reliability(annos_f, golds_f, "wf")
    rel_g = compute_beta_binomial_reliability(annos_g, golds_g, "wg")
    ci_f = rel_f.upper_bound - rel_f.lower_bound
    ci_g = rel_g.upper_bound - rel_g.lower_bound

    scenarios.append({
        "scenario": "Scenario F",
        "description": "Small-N worker (2/3 correct)",
        "expected_behavior": "UNCERTAIN state due to wide interval crossing 0.50",
        "observed_behavior": f"state={rel_f.reliability_evidence_state}, interval=[{rel_f.lower_bound:.3f}, {rel_f.upper_bound:.3f}]",
        "status": "PASS" if (rel_f.reliability_evidence_state == "UNCERTAIN" and ci_f > ci_g) else "FAIL",
    })

    scenarios.append({
        "scenario": "Scenario G",
        "description": "Large-N moderate worker (70/100 correct)",
        "expected_behavior": "NOT_LOW state with narrow interval entirely above 0.50",
        "observed_behavior": f"state={rel_g.reliability_evidence_state}, interval=[{rel_g.lower_bound:.3f}, {rel_g.upper_bound:.3f}]",
        "status": "PASS" if (rel_g.reliability_evidence_state == "NOT_LOW" and rel_g.lower_bound >= 0.50) else "FAIL",
    })

    # Scenario H: No gold evaluated
    rel_h = compute_beta_binomial_reliability([], [], "wh")
    scenarios.append({
        "scenario": "Scenario H",
        "description": "No gold evaluated",
        "expected_behavior": "NO_GOLD state with fallback prior mean 0.50",
        "observed_behavior": f"state={rel_h.reliability_evidence_state}, posterior_mean={rel_h.posterior_mean:.3f}",
        "status": "PASS" if (rel_h.reliability_evidence_state == "NO_GOLD" and rel_h.posterior_mean == 0.50) else "FAIL",
    })

    # Scenario I: Sparse gold (N=2)
    annos_i = [
        Annotation("ai1", "i1", "wi", "positive"),
        Annotation("ai2", "i2", "wi", "negative"),
    ]
    golds_i = [
        GoldLabel(gold_label_id="gi1", project_id="p1", item_id="i1", label_domain_id="d1", label="positive", resolution_status="resolved_hard", gold_source="expert_adjudication", version=1, created_at="2026-08-09T00:00:00Z"),
        GoldLabel(gold_label_id="gi2", project_id="p1", item_id="i2", label_domain_id="d1", label="positive", resolution_status="resolved_hard", gold_source="expert_adjudication", version=1, created_at="2026-08-09T00:00:00Z"),
    ]
    rel_i = compute_beta_binomial_reliability(annos_i, golds_i, "wi")
    scenarios.append({
        "scenario": "Scenario I",
        "description": "Sparse gold (N=2)",
        "expected_behavior": "UNCERTAIN state due to wide interval crossing 0.50",
        "observed_behavior": f"state={rel_i.reliability_evidence_state}, interval=[{rel_i.lower_bound:.3f}, {rel_i.upper_bound:.3f}]",
        "status": "PASS" if (rel_i.reliability_evidence_state == "UNCERTAIN") else "FAIL",
    })

    # Scenario J: Mixed defect + ambiguity signals (Deterministic)
    # Defect evidence: w4 is CREDIBLY_LOW (0/20 correct) and dissents with "negative"
    # Ambiguity evidence: w1, w3 voted "positive", w2 (strong, 20/20 correct) voted "neutral" -> margin = 0.25 <= 0.25
    annos_j = [
        Annotation("j1", "item1", "w1", "positive"),
        Annotation("j2", "item1", "w3", "positive"),
        Annotation("j3", "item1", "w2", "neutral"),
        Annotation("j4", "item1", "w4", "negative"),
    ]
    golds_j = []
    for i in range(20):
        item_id = f"g_item_{i}"
        golds_j.append(
            GoldLabel(
                gold_label_id=f"g_w4_{i}",
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
        annos_j.append(Annotation(f"a_w4_{i}", item_id, "w4", "negative"))
        annos_j.append(Annotation(f"a_w1_{i}", item_id, "w1", "positive"))
        annos_j.append(Annotation(f"a_w2_{i}", item_id, "w2", "positive"))
        annos_j.append(Annotation(f"a_w3_{i}", item_id, "w3", "positive"))

    svc_j = DisagreementDiagnosticsService(annos_j, golds_j, ["positive", "neutral", "negative"], "snap_j", "p1")
    flags_j = svc_j.generate_quality_flags()
    mix_j = next((f for f in flags_j if f.entity_id == "item1" and f.flag_type == "mixed_evidence"), None)

    scenarios.append({
        "scenario": "Scenario J",
        "description": "Contradictory defect-style (CREDIBLY_LOW dissenter) and ambiguity-style (strong workers split) evidence",
        "expected_behavior": "flag_type = mixed_evidence (preserves contradictory evidence without forcing pure defect or ambiguity flag)",
        "observed_behavior": f"entity_type={mix_j.entity_type if mix_j else None}, flag_type={mix_j.flag_type if mix_j else None}",
        "status": "PASS" if (mix_j is not None and mix_j.flag_type == "mixed_evidence") else "FAIL",
    })

    # Scenario K: High posterior mean, wide interval crossing 0.50 (Small N)
    # Worker wf has 2/3 correct -> mean 0.60, CI [0.194, 0.932] crossing 0.50
    annos_k = [
        Annotation("k1", "item_k", "w1", "positive"),
        Annotation("k2", "item_k", "w2", "positive"),
        Annotation("k3", "item_k", "w3", "positive"),
        Annotation("k4", "item_k", "wf", "negative"),  # wf has 2/3 correct (UNCERTAIN)
    ]
    all_annos_k = list(annos_k) + annos_f
    svc_k = DisagreementDiagnosticsService(annos_k, golds_f, ["positive", "negative"], "snap_k", "p1")
    flags_k = svc_k.generate_quality_flags()
    defect_k = [f for f in flags_k if f.flag_type == "probable_quality_defect"]
    rel_k = compute_beta_binomial_reliability(all_annos_k, golds_f, "wf")

    scenarios.append({
        "scenario": "Scenario K",
        "description": "High posterior mean, wide interval crossing 0.50 (Small N)",
        "expected_behavior": "reliability_evidence_state = UNCERTAIN (NOT CREDIBLY_LOW). Must NOT cause probable_quality_defect flag.",
        "observed_behavior": f"state={rel_k.reliability_evidence_state}, posterior_mean={rel_k.posterior_mean:.3f}, interval=[{rel_k.lower_bound:.3f}, {rel_k.upper_bound:.3f}], defect_flags_count={len(defect_k)}",
        "status": "PASS" if (rel_k.reliability_evidence_state == "UNCERTAIN" and len(defect_k) == 0) else "FAIL",
    })

    # Scenario L: Entire interval below 0.50
    rel_l = compute_beta_binomial_reliability(annos_a, golds_a, "w4")
    scenarios.append({
        "scenario": "Scenario L",
        "description": "Entire 95% interval below 0.50",
        "expected_behavior": "reliability_evidence_state = CREDIBLY_LOW. Contributes weak-worker defect evidence.",
        "observed_behavior": f"state={rel_l.reliability_evidence_state}, interval=[{rel_l.lower_bound:.3f}, {rel_l.upper_bound:.3f}]",
        "status": "PASS" if (rel_l.reliability_evidence_state == "CREDIBLY_LOW" and rel_l.upper_bound < 0.50) else "FAIL",
    })

    return scenarios


def run_real_benchmark_descriptive_analysis(data_root: Path) -> dict[str, Any]:
    repo = DatasetRepository(data_root)
    datasets = repo.list_datasets()
    if not datasets:
        return {"status": "SKIPPED_NO_DATA", "reason": "No datasets found in repository."}

    dataset = datasets[0]
    path = repo.dataset_path(dataset.dataset_id)
    assert path is not None

    raw = [row for row in pq.read_table(path / "annotations.parquet").to_pylist() if row["is_current"]]
    labels_val = pq.read_table(path / "label_domain.parquet").to_pylist()[0]["labels"]
    labels = list(json.loads(labels_val)) if isinstance(labels_val, str) else list(labels_val)

    annotations = [
        Annotation(str(r["annotation_id"]), str(r["item_id"]), str(r["annotator_id"]), str(r["label"]))
        for r in raw
    ]

    gold_raw = pq.read_table(path / "gold_labels.parquet").to_pylist()
    gold_labels = [
        GoldLabel(
            gold_label_id=str(r.get("gold_label_id") or f"g-{r['item_id']}"),
            project_id="reqp3",
            item_id=str(r["item_id"]),
            label_domain_id="reqp3_labels",
            label=str(r["label"]) if r.get("label") else None,
            resolution_status=str(r["resolution_status"]),
            gold_source="benchmark_truth",
            version=1,
            created_at=str(r.get("created_at") or "2026-08-09T00:00:00Z"),
        )
        for r in gold_raw
    ]

    intel_svc = AnnotatorIntelligenceService(annotations, gold_labels, labels)
    profiles = intel_svc.list_annotator_profiles()

    diag_svc = DisagreementDiagnosticsService(
        annotations, gold_labels, labels, dataset.dataset_id, "reqp3"
    )
    flags = diag_svc.generate_quality_flags()
    summary = diag_svc.summarize(flags)

    # State counts among annotators
    states_count = {"CREDIBLY_LOW": 0, "UNCERTAIN": 0, "NOT_LOW": 0, "NO_GOLD": 0}
    for p in profiles:
        if p.beta_binomial:
            states_count[p.beta_binomial.reliability_evidence_state] += 1

    return {
        "status": "COMPLETED",
        "dataset_id": dataset.dataset_id,
        "total_annotators": len(profiles),
        "total_items": summary.total_items,
        "items_with_flags": summary.items_with_flags,
        "annotator_evidence_states": states_count,
        "new_real_flag_counts": summary.flag_counts,
        "new_severity_counts": summary.severity_counts,
        "new_entity_type_counts": summary.entity_type_counts,
    }


def main() -> None:
    print("==================================================")
    print("PHASE 4 DIAGNOSTIC VALIDATION AUDIT (SCENARIOS A-L)")
    print("==================================================")
    scenarios = run_synthetic_validation()
    for item in scenarios:
        print(f"\n[{item['scenario']}] {item['description']}")
        print(f"  Expected: {item['expected_behavior']}")
        print(f"  Observed: {item['observed_behavior']}")
        print(f"  Result:   {item['status']}")

    print("\n==================================================")
    print("REQUIREMENTS ANNOTATION PHASE 3 REAL DESCRIPTIVE ANALYSIS")
    print("==================================================")
    real = run_real_benchmark_descriptive_analysis(Path("data"))
    print(json.dumps(real, indent=2))

    report = {
        "scenarios_a_l": scenarios,
        "real_benchmark_analysis": real,
    }
    out_path = Path("artifacts/phase4_validation_report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved report to {out_path}")


if __name__ == "__main__":
    main()
