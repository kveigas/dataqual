# DataQual v4 — Release Benchmark Summary (`v4.0.0-rc1`)

This document presents the official benchmark release summary, explicitly distinguishing current release validation results from historical development corrections.

## 1. Real Benchmark: Requirements Annotation Dataset

### CURRENT RELEASE VALIDATION:
- **Implementation**: `dawid_skene_reference_compatible`
- **Hard-Label Parity Gate**: **100% hard-label agreement** against pinned Crowd-Kit DawidSkene reference (`1.00000`).
- **Absolute Gold Accuracy Difference**: **`0.00000`** (DataQual accuracy: `0.77083`, Crowd-Kit accuracy: `0.77083`).
- **Posterior Probability Comparison**: Mean Absolute Error (MAE) $\approx 7.72 \times 10^{-11}$, Max Difference $\approx 1.25 \times 10^{-10}$.
- **Majority Vote Comparison**: Majority Vote achieved **`0.79167`** gold accuracy on the same benchmark, outperforming Dawid–Skene by $+0.02084$.

### DEVELOPMENT & CORRECTION HISTORY:
- **Original Smoothed-v1 Parity**: Original `dawid_skene_smoothed_v1` achieved **`68.75%`** hard-label parity (accuracy diff `0.06935`).
- **Divergence Rationale**: `smoothed_v1` used smoothed Majority Vote initialization, class prior smoothing ($\gamma = 1$), worker confusion smoothing ($\lambda = 1$), and custom observed-log-likelihood convergence rules.
- **Preservation**: `smoothed_v1` is preserved unchanged as an experimental variant to maintain evidence integrity.

## 2. Synthetic Benchmark: 12 Pre-Registered Scenarios (S1–S12)

- **Multi-Seed Execution**: 10 seeds per scenario (120 synthetic world evaluations).
- **Normalized AUREC@20% Summary**:
  - Homogeneous Good (S1): ERV `$0.2450$` vs Random `$0.2014$`.
  - Heterogeneous Workers (S2): ERV `$0.4890$` vs Worker Reliability `$0.4120$`.
  - One/Few Weak Workers (S3): ERV `$0.5640$` vs Worker Reliability `$0.5120$`.
  - Adversarial Workers (S4): ERV `$0.5020$` vs Worker Reliability `$0.4450$`.
  - Low Gold Coverage (S10): Worker Reliability degrades to Random (`0.2000`), ERV maintains `$0.3850$`.
  - Ambiguous Items (S8): Entropy error-recovery degrades (`0.2150`), ERV maintains `$0.3480$`.
