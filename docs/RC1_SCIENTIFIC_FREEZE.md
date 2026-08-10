# DataQual v4 — RC1 Scientific Core Freeze

This document formalizes the scientific core freeze for DataQual `v4.0.0-rc1`. All statistical models, methods, configurations, thresholds, parameters, and benchmark protocols are frozen.

## 1. Frozen Method & Configuration Registry

| Subsystem / Method | Version / Identifier | Config Hash / Lock | Status |
| :--- | :--- | :--- | :--- |
| **Data Foundation Schema** | `4.0.0` | Ingest validation schema | Frozen |
| **Krippendorff Alpha** | Nominal / Interval | Unbiased estimator | Frozen |
| **Majority Vote Consensus** | Exact tie-resolution | Deterministic argmax | Frozen |
| **Dawid–Skene Reference-Compatible** | `dawid_skene_reference_compatible` | Crowd-Kit pinned parity | Frozen |
| **Dawid–Skene Smoothed** | `dawid_skene_smoothed_v1` | Custom EM smoothing | Frozen (Experimental) |
| **Bayesian Worker Reliability** | Beta-Binomial | `configs/thresholds_v1.json` | Frozen |
| **Dirichlet Worker Confusion** | Dirichlet-Multinomial | Marginal Beta credible intervals | Frozen |
| **Probable Quality Defect Diagnostic** | `1.0.0` | `threshold_config_v1` | Frozen |
| **Probable Ambiguity Diagnostic** | `1.0.0` | `threshold_config_v1` | Frozen |
| **Expected Review Value (ERV)** | `1.0.0` | `configs/erv_v1.yaml` (`hash: 4c...`) | Frozen |
| **Synthetic Dataset Simulator** | `1.0.0` | `SimulatorConfig` PCG64 | Frozen |

## 2. Frozen Parameters & Thresholds

- **Beta-Binomial Worker Reliability**: Weak threshold $= 0.50$, Credible level $= 0.95$.
- **Diagnostic Rules**: Vote entropy threshold $= 0.70$, Vote margin threshold $= 0.25$, Support threshold $= 3$ annotations.
- **Expected Review Value Score**: $raw_i = 0.60 u_i + 0.20 h_i + 0.20 e_i$.
- **Dawid–Skene EM Parameters**: Max iterations $= 100$, Relative tolerance $= 1 \times 10^{-5}$, Absolute tolerance $= 1 \times 10^{-7}$.

## 3. Preservation of Negative Evidence & Historical Benchmarks

- **Phase 0 Relevance-2 Licensing Rejection**: Documented under `docs/DEPENDENCY_AND_DATA_LICENSES.md`.
- **Phase 3 Crowd-Kit Parity Trace**: Reference-compatible DS achieves 100% hard-label parity on Requirements Annotation benchmark (gold accuracy diff `0.00000`). Original smoothed-v1 implementation achieved `68.75%` parity and is retained separately as an experimental variant.
- **Phase 5 ERV Benchmark**: ERV parameters were frozen before evaluation and were NOT tuned on held-out scenarios.
