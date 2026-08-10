# DataQual v4 — Statistical Methods Matrix

| Method Name | Purpose | Evidence Classification | Inputs | Outputs | Validation Method | Production / Experimental |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Observed Coverage** | Summarizes annotations per item | Observed | `AnnotationEvents` | Counts, sparsity graph | Fixture exact match | Production |
| **Percent Agreement** | Pairwise raw agreement | Deterministically Computed | Co-annotated items | Proportion $[0,1]$ | Exact calculation | Production |
| **Krippendorff Alpha** | Nominal inter-annotator agreement | Deterministically Computed | Annotation matrix | Alpha score $[-1, 1]$ | Unbiased estimator fixture | Production |
| **Non-parametric Bootstrap** | 95% confidence intervals | Statistically Estimated | Resampled items | 95% percentile interval | 2000 replicates fixture | Production |
| **Majority Vote Consensus** | Deterministic vote argmax | Deterministically Computed | Annotation matrix | Hard labels, tie flags | Deterministic argmax | Production |
| **Weighted Vote Consensus** | Development-gold weighted vote | Statistically Estimated | Annotations, Gold | Hard labels | Gold-weighted argmax | Production |
| **Dawid–Skene Reference-Compatible** | Latent class EM consensus | Statistically Estimated | Annotations | Argmax labels, posteriors | Crowd-Kit 100% parity gate | Production |
| **Dawid–Skene Smoothed v1** | EM with prior smoothing | Statistically Estimated | Annotations | Posteriors | Retained experimental | Experimental |
| **Beta-Binomial Reliability** | Bayesian worker accuracy | Statistically Estimated | Annotations, Gold | Posterior mean, 95% CI | Beta conjugate update | Production |
| **Dirichlet Confusion** | Worker confusion matrix | Statistically Estimated | Annotations, Gold | Smoothed probabilities, CIs | Dirichlet-Multinomial | Production |
| **Normalized Vote Entropy** | Item disagreement measure | Deterministically Computed | Item vote vector | $H / \ln(K) \in [0,1]$ | Exact entropy fixture | Production |
| **Vote Margin** | Consensus margin | Deterministically Computed | Top 2 vote counts | Margin $\in [0,1]$ | Exact margin fixture | Production |
| **Probable Quality Defect** | Evidence flag for worker errors | Heuristic Diagnostic | Features, Gold | Flag, severity, explanation | Predeclared rule engine | Production |
| **Probable Ambiguity Issue** | Evidence flag for guideline ambiguity | Heuristic Diagnostic | Features, Entropy | Flag, severity, action | Predeclared rule engine | Production |
| **Random Prioritization** | Permutation baseline | Synthetic Benchmark Result | Candidate list | Seeded rank | PCG64 random seed | Experimental |
| **Entropy Prioritization** | Rank by highest vote entropy | Synthetic Benchmark Result | Item features | Ranked queue | Descending entropy | Production |
| **Consensus Confidence** | Rank by Dawid-Skene uncertainty | Synthetic Benchmark Result | DS posteriors | Ranked queue | Descending uncertainty | Production |
| **Worker Reliability Prioritizer** | Rank by worker gold error | Synthetic Benchmark Result | Development gold | Ranked queue | Descending error | Production |
| **Expected Review Value (ERV)** | Multi-component review score | Heuristic Diagnostic | DS, Entropy, Gold | $raw = 0.60u_i + 0.20h_i + 0.20e_i$ | Decomposable component test | Production |
