# DataQual v4 — Phase 5 Methods Specification

This document details the methods and algorithms implemented in Phase 5 for Review Prioritization, baseline comparisons, and Expected Review Value (ERV) evaluation.

## 1. Prioritization Methods

### 1. Random Baseline (`random`)
- **Unit**: Annotation or Item.
- **Algorithm**: Seeded random permutation generated via NumPy `default_rng(random_ranking_seed)`.
- **Purpose**: Serves as a non-informative baseline for review efficiency.

### 2. Highest Vote Entropy Baseline (`highest_entropy`)
- **Unit**: Annotation or Item.
- **Algorithm**: Ranks candidates by descending normalized vote entropy $H_{\text{norm}} = H / \ln(K)$, where $H = -\sum_{c=1}^K p_c \ln(p_c)$.
- **Tie-Breaking**: Deterministic tie-breaker using string comparison on candidate ID.

### 3. Lowest Consensus Confidence Baseline (`lowest_consensus_confidence`)
- **Unit**: Annotation or Item.
- **Algorithm**: Ranks candidates by descending Dawid-Skene posterior uncertainty $u_i = 1 - \max_c q_{i,c}$, where $q_{i,c}$ is the Dawid-Skene item posterior probability vector.
- **Eligibility**: Only candidates from items where Dawid-Skene converged successfully are eligible. Unavailable items are sorted after eligible candidates.

### 4. Lowest Worker Reliability Baseline (`lowest_worker_reliability`)
- **Unit**: Annotation.
- **Algorithm**: Ranks candidates by descending mean worker error exposure $e_{i,a} = 1 - r_w$, where $r_w$ is the Bayesian Beta-Binomial posterior mean reliability evaluated from **development/operational gold ONLY**.
- **Rule**: Does NOT substitute Dawid-Skene diagonal estimates when gold is unavailable. Workers without gold evidence are marked as ineligible/uncertain.

### 5. Expected Review Value (`erv`)
- **Unit**: Annotation.
- **Formula**: $raw_i = 0.60 \cdot u_i + 0.20 \cdot h_i + 0.20 \cdot e_i$.
  - $u_i = 1 - \max(q_i)$: Dawid-Skene posterior uncertainty.
  - $h_i = H_{\text{norm}}$: Normalized vote entropy.
  - $e_i$: Mean worker error from development gold Beta posteriors (defaulting to prior mean 0.50 if gold is unavailable).
- **Properties**: Fully decomposable score components. Parameters frozen in `configs/erv_v1.yaml`. Score explicitly labeled as a heuristic score, not monetary ROI or calibrated probability.
