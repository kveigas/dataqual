# DataQual v4 — Phase 5 Benchmark Protocol & Metrics

This document defines the evaluation metrics, fixed budget settings, multi-seed aggregation rules, and paired statistical comparison protocols for Phase 5.

## 1. Review Budgets & Metrics

### Budgets
- Fixed budget fractions: **1%**, **5%**, **10%**, **20%**.
- Candidate rank conversion: $K = \max(1, \text{round}(b \cdot N))$.

### Primary Metrics
- **Errors Recovered @ Budget**: Number of true defects present in top-$K$.
- **Error Recall @ Budget**: $\text{Errors Recovered} / \text{Total Eligible Errors}$.
- **Precision@K**: $\text{Errors Recovered} / K$.
- **Cumulative Recovery Curve**: Stepwise error recall from budget $0\%$ to $20\%$.
- **Area Under Review-Efficiency Curve (AUREC@20%)**:
  - Trapezoidal integration of error recall curve over $b \in [0, 0.20]$.
  - Normalized AUREC@20% $= \text{AUREC} / 0.20 \in [0, 1.0]$.

## 2. Multi-Seed Aggregation & Paired Comparisons

- **Multi-Seed Protocol**: Runs 10 deterministic world seeds per scenario (`simulation_world_seed`) paired with 10 random ranking seeds (`random_ranking_seed`).
- **Statistics Reported**: Mean, Standard Deviation, and 95% Student-$t$ Confidence Intervals.
- **Paired Method Comparison**: Reports paired difference $\Delta = \text{AUREC}_{\text{ERV}} - \text{AUREC}_{\text{Baseline}}$, 95% CI of difference, and Win / Tie / Loss counts.
- **Negative-Result Preservation**: ERV parameters are frozen in `configs/erv_v1.yaml` prior to evaluation and are NEVER tuned on final evaluation scenarios. Negative results are preserved as valid scientific findings.
