# DataQual v4 Core Methods Contract

Status: implementation contract  
Methods contract version: `v4-core-1.0`

## 1. Global rules

Every method returns:

- method name and semantic version;
- canonical configuration and SHA-256 configuration hash;
- dataset snapshot ID;
- result status;
- support counts;
- output values;
- uncertainty where specified;
- warnings and failure reason codes;
- provenance reference.

Permitted statuses:

- `success`
- `unresolved`
- `insufficient_evidence`
- `assumption_violation`
- `non_converged`
- `unavailable`
- `failed`

No method substitutes a project average, demo value, zero, or stale result after a non-success status.

All label vectors and matrices follow the immutable order in the label-domain registry. Missing annotations are absent events, not label values.

## 2. Evidence levels

The following defaults control UI presentation, not whether a mathematically defined point estimate can be calculated:

- `minimal`: method's mathematical minimum is met, but interpretation is fragile;
- `limited`: fewer than 20 relevant items or fewer than 5 observations in a displayed class/cell;
- `adequate`: at least 20 relevant items and all displayed estimates meet their method-specific support threshold;
- `strong`: at least 100 relevant items and no material overlap/connectivity warning.

The UI must display the evidence level and exact support. “Adequate” is not a claim of external validity.

## 3. Percent Agreement

**Purpose:** interpretable raw agreement baseline.

For item `i` with `m_i >= 2` current labels and class counts `n_ic`, item pair agreement is:

```text
A_i = sum_c n_ic (n_ic - 1) / [m_i (m_i - 1)]
```

Overall percent agreement is the weighted proportion of agreeing unordered pairs:

```text
A = sum_i sum_c C(n_ic, 2) / sum_i C(m_i, 2)
```

- Inputs: current categorical AnnotationEvents.
- Output: `A`, pairable item count, total compared pairs.
- Assumptions: compared labels share one label domain.
- Minimum: one pairable item; fewer than 20 pairable items is `limited`.
- Failure: no item has two labels, mixed domains, or invalid labels.
- Uncertainty: item bootstrap CI when at least 10 pairable items; otherwise unavailable.
- Implementation: from scratch using integer pair counts.
- Validation: hand examples, permutation properties, duplicate-identical-label property.
- UI: call it raw agreement; never reliability, accuracy, or consensus quality.

## 4. Pairwise Agreement

**Purpose:** show agreement and overlap between specific annotator pairs.

For workers `a,b`, on the intersection `I_ab` of current co-annotated items:

```text
A_ab = count(label_ia = label_ib) / |I_ab|
```

- Output: symmetric matrix of agreement, shared-item support, and CI/warning.
- Minimum point estimate: one shared item; `limited` below 20 shared items.
- CI: item bootstrap over the shared items when `|I_ab| >= 10`.
- Failure/unavailable: zero shared items; cell is null, never 0%.
- Multiple annotations: only each worker's current event is used.
- Validation: symmetry, diagonal treatment, known sparse matrices.
- UI: diagonal shows “self / not applicable,” not 100%; every cell displays `n`.

## 5. Nominal Krippendorff's Alpha

**Purpose:** chance-corrected agreement for multiple coders and missing annotation matrices.

Only pairable items (`m_i >= 2`) contribute. Build the coincidence matrix `o_cc'`:

```text
for c != c': o_cc' += n_ic * n_ic' / (m_i - 1)
for c == c': o_cc  += n_ic * (n_ic - 1) / (m_i - 1)
```

Let `N = sum_cc' o_cc'` and `n_c = sum_c' o_cc'`. For nominal distance `delta(c,c') = 1[c != c']`:

```text
D_o = sum_cc' o_cc' delta(c,c') / N
D_e = sum_cc' n_c n_c' delta(c,c') / [N (N - 1)]
alpha = 1 - D_o / D_e
```

- Inputs: current categorical events in one label domain.
- Minimum: at least two pairable items, `N > 1`, and at least two observed classes.
- Degenerate perfect single-class data: `D_e = 0`; return `unavailable`, not alpha 1.
- Missingness: absent events are ignored; items with fewer than two labels do not contribute and are counted separately.
- Output: alpha, observed/expected disagreement, pairable items, coder/item counts.
- Uncertainty: percentile item bootstrap, section 6.
- Implementation: from scratch, nominal only.
- Reference: parity against a vetted Krippendorff implementation and published hand examples.
- Tolerance: absolute difference `<= 1e-10` on golden fixtures and `<= 1e-8` on randomized finite fixtures.
- UI: no universal “good/bad” threshold. Show prevalence, support, missingness, and CI.

## 6. Bootstrap Confidence Interval

**Purpose:** quantify item-sampling uncertainty for item-level estimates and paired method comparisons.

Default:

- resampling unit: item;
- eligible population: exactly the items used by the point estimate;
- replicates: 2,000 for UI/standard artifacts, 10,000 for release benchmark reports;
- method: percentile 95% interval;
- RNG: NumPy `Generator(PCG64(seed))`;
- seed: explicit, never implicit;
- paired comparisons: identical resampled item indices for all compared methods.

Failure rules:

- fewer than 10 eligible items: CI unavailable;
- statistic undefined in more than 5% of replicates: CI unavailable with diagnostic;
- undefined replicates are not converted to zero;
- temporal/block bootstrap is out of core scope.

Output includes point estimate, interval endpoints, replicate count, valid count, seed, and bootstrap population definition.

Validation: exact resample-index fixtures, deterministic-seed property, constant-statistic interval, and paired-difference fixtures.

UI: visually distinguish confidence intervals from Bayesian credible intervals.

## 7. Gold-based Accuracy

**Purpose:** fraction of current annotations equal to resolved hard gold.

```text
accuracy = correct gold-supported annotations / all gold-supported annotations
```

- One observation is one current annotation on an item with current `resolved_hard` gold.
- Distributional or unresolved gold is excluded and counted.
- Output: overall and per-annotator accuracy with numerator/denominator.
- Minimum: one supported annotation for point estimate; fewer than 20 is limited.
- Uncertainty: Beta-Binomial credible interval for per-annotator reliability; item bootstrap for aggregate comparisons.
- UI: the word “accuracy” is prohibited without hard gold support.

## 8. Precision, Recall, and F1

For each registered class `c`:

```text
precision_c = TP_c / (TP_c + FP_c)
recall_c    = TP_c / (TP_c + FN_c)
F1_c        = 2 * precision_c * recall_c / (precision_c + recall_c)
```

Rules:

- Inputs: current annotations or hard consensus predictions paired with resolved hard gold.
- If `TP + FP = 0`, precision is null, not zero.
- If `TP + FN = 0`, recall is null because class has no gold support.
- If precision or recall is null, F1 is null.
- Macro recall/F1 average only classes with gold support; null class values remain reported.
- Macro precision averages classes with gold support and treats a supported but never-predicted class precision as 0 for the macro aggregate while preserving the class-level null and warning.
- Micro metrics are also reported for context.
- Minimum for a class display: support 1; below 5 receives a conspicuous limited warning.
- Validation: scikit-learn parity under the documented zero-division mapping and hand confusion matrices.
- UI: show class support beside every metric.

## 9. Confusion Matrix

**Purpose:** expose class-specific error patterns.

- Rows: authoritative/gold class.
- Columns: submitted/predicted class.
- Order: label-domain order.
- Output: raw counts and row-normalized probabilities.
- A row with zero gold support has null normalized cells, not zeros.
- Annotator matrices require resolved hard gold.
- Dawid-Skene worker matrices follow section 15 and are clearly labeled latent estimates, not observed gold confusion.
- Dirichlet-smoothed matrices follow section 11.
- Validation: exact hand fixtures, row totals, and label-order properties.

## 10. Beta-Binomial Reliability

**Purpose:** shrink binary correctness estimates when gold support is small.

For annotator `w`, let `s_w` and `f_w` be correct/incorrect hard-gold judgments. Define a leave-one-worker-out project prior mean:

```text
m_-w = (S_-w + 0.5) / (N_-w + 1)      when N_-w >= 20
m_-w = 0.5                              otherwise
kappa_0 = 2
alpha_0 = kappa_0 * m_-w
beta_0  = kappa_0 * (1 - m_-w)
posterior = Beta(alpha_0 + s_w, beta_0 + f_w)
```

- Output: posterior mean, equal-tail 95% credible interval, `s`, `f`, prior mean/strength/provenance.
- Minimum: one gold-supported judgment; below 20 is limited.
- Assumptions: conditional Bernoulli correctness; prior is an operational shrinkage model, not a full hierarchical truth.
- Failure: no resolved hard gold.
- Implementation: from scratch using SciPy distribution quantiles.
- Validation: analytic posterior fixtures, interval narrowing property, leave-one-out prior tests.
- UI: call it posterior gold correctness, not general worker accuracy or competence.

## 11. Dirichlet-smoothed Multiclass Reliability

**Purpose:** stabilize class-specific observed confusion probabilities against hard gold.

For each gold class `c` and observed label `k`:

```text
theta_wc,* ~ Dirichlet(alpha_1...alpha_K)
alpha_k = 0.5  (Jeffreys-style symmetric smoothing)
posterior mean theta_wc,k = (count_wc,k + 0.5) / (n_wc + 0.5K)
```

- Output: posterior row means, marginal 95% Beta intervals per cell, raw counts, class support.
- Minimum: one gold observation in row for a row estimate; below 5 is limited.
- No-support rows remain unavailable; the prior-only row is not displayed as evidence.
- Assumptions: class outcomes within a row are exchangeable and the symmetric prior is documented.
- Validation: normalization, analytic fixtures, interval narrowing.
- UI: display raw support and distinguish observed-smoothed from Dawid-Skene latent confusion.

## 12. Majority Vote

**Purpose:** transparent consensus baseline.

For item `i`:

```text
p_i(c) = n_ic / m_i
```

Hard label is the unique class with maximum count.

- Tie: `hard_label = null`, status `unresolved`.
- Minimum: one current human annotation; support 1 is explicitly single-source, not consensus.
- Output: vote fractions, hard label if unique, top support, tie status.
- Uncertainty: vote entropy and margin; vote fractions are descriptive, not Bayesian posteriors.
- Validation: ties, label-order invariance, sparse items.
- UI: never call `max p_i` calibrated confidence.

## 13. Reliability-weighted Majority Vote

**Purpose:** compare a transparent gold-informed weighting baseline with unweighted vote and Dawid-Skene.

Eligibility:

- only resolved hard gold-derived Beta-Binomial estimates;
- each contributing worker needs at least 20 gold-supported labels;
- at least two eligible workers must label the item;
- gold items used to estimate weights must be from the benchmark development split, never evaluation labels.

For `K` classes and worker posterior mean `r_w`, convert accuracy above random chance to a nonnegative weight:

```text
w_w = clip((r_w - 1/K) / (1 - 1/K), 0, 1)
score_i(c) = sum_{w labels i as c} w_w
p_i(c) = score_i(c) / sum_c score_i(c)
```

- If total weight is zero or fewer than two workers are eligible: unavailable; do not fall back silently.
- Tie: unresolved.
- Output: scores, normalized shares, workers/weights used, excluded-worker reasons.
- Assumptions: gold performance transfers to evaluated items and class mixture; limitations must be shown.
- Validation: hand fixtures, equal-weight equivalence to majority vote, no-gold failure tests.
- UI: label as gold-reliability-weighted vote. Do not show on projects with no eligible gold split.

## 14. Dawid-Skene Purpose and Model

**Purpose:** infer latent categorical labels and worker confusion matrices without requiring gold labels.

For labels `c,k in {1...K}`:

```text
pi_c = P(true label = c)
theta_w,c,k = P(worker w emits k | true label c)
q_i,c = P(true label_i = c | observed labels)
```

Conditional-independence assumption: worker labels are independent given the item's latent true label. This assumption is explicitly disclosed and is violated by copycat/correlated workers.

## 15. Dawid-Skene Initialization

1. Fix class order from the label-domain registry.
2. Initialize item posteriors from smoothed vote fractions:

```text
q_i,c = (n_ic + 1/K) / (m_i + 1)
```

3. Initialize class prior using expected counts with symmetric Dirichlet smoothing `gamma = 1`:

```text
pi_c = (sum_i q_i,c + gamma) / (N + K*gamma)
```

4. Initialize worker confusion matrices through the M-step rule below with `lambda = 1`.

Initialization is deterministic. Random restarts are not part of core v1.

## 16. Dawid-Skene E-step

For item `i` and class `c`:

```text
log r_i,c = log(pi_c) + sum_{(w,k) in labels_i} log(theta_w,c,k)
q_i,* = softmax(log r_i,*)
```

- Compute with log-sum-exp.
- Floor probabilities at `1e-12` before logarithms, then renormalize.
- Missing worker-item labels contribute no term.
- If all class log probabilities are non-finite after validation, fail the run.

## 17. Dawid-Skene M-step

Class prior:

```text
pi_c = (sum_i q_i,c + gamma) / (N + K*gamma), gamma = 1
```

Worker confusion:

```text
theta_w,c,k =
  [lambda + sum_{i labeled by w} q_i,c * 1(y_iw = k)]
  / [K*lambda + sum_{i labeled by w} q_i,c]

lambda = 1
```

Every row is normalized and all cells remain positive.

## 18. Dawid-Skene Likelihood and convergence

Observed-data log likelihood:

```text
L = sum_i log(sum_c pi_c * product_{(w,k) in labels_i} theta_w,c,k)
```

Defaults:

- maximum iterations: 200;
- absolute likelihood tolerance: `1e-8`;
- relative likelihood tolerance: `1e-6`;
- convergence requires relative improvement `<= 1e-6` for three consecutive iterations;
- a likelihood decrease greater than `1e-8` fails the run as a numerical/implementation error;
- reaching 200 iterations returns `non_converged`, while retaining diagnostics but not release-grade hard labels.

The entire likelihood history, final delta, iteration count, and stop reason are output.

## 19. Dawid-Skene graph and evidence rules

Construct the bipartite worker-item graph from current annotations.

- Empty items are excluded and counted.
- Single-worker items may receive a posterior only if that worker is connected elsewhere to an identifiable multi-worker component.
- A component with one worker only is `insufficient_evidence` for Dawid-Skene; return Majority Vote descriptives instead as a separately named result.
- Multiple disconnected multi-worker components are fit separately with the same label ordering and smoothing.
- Worker confusion estimates are explicitly not comparable across disconnected components.
- Each component requires at least two workers, two items, two observed classes, and at least one item with worker overlap.
- Graph component IDs and support diagnostics are emitted.

## 20. Dawid-Skene outputs

- posterior probability vector for every eligible item;
- unique argmax hard label or unresolved tie;
- posterior confidence and uncertainty;
- worker confusion matrices;
- class priors;
- likelihood history;
- convergence status;
- graph-component diagnostics;
- items/workers excluded and reasons;
- configuration and label ordering.

Gold labels are not injected into core Dawid-Skene fitting. Gold is reserved for evaluation, avoiding train/evaluation contamination.

## 21. Dawid-Skene implementation and validation

- Implementation: from scratch in NumPy/SciPy.
- Reference: isolated Crowd-Kit Dawid-Skene adapter.
- Golden fixtures: exact E-step/M-step/likelihood values on hand-computable data.
- Synthetic recovery: known worker confusion, imbalance, sparsity, and adversarial cases.

Parity gates:

1. On deterministic parity fixtures designed to match initialization/smoothing, item posterior maximum absolute difference `<= 1e-3` and worker-confusion MAE `<= 1e-3`.
2. On held-out eligible items from the selected licensed requirements-annotation dataset, hard-label agreement with Crowd-Kit `>= 99%` and accuracy difference versus researcher reference labels `<= 0.002` absolute.
3. Material differences must be attributable to documented initialization/smoothing behavior and cannot be waived merely because DataQual has higher accuracy.
4. The parity adapter and DataQual implementation receive the same canonical rows and label order.

UI rules:

- show convergence and component warnings near results;
- call confusion matrices latent estimates;
- never call posterior confidence calibrated without separate calibration evidence;
- explain conditional independence and correlated-worker risk.

## 22. Vote Entropy

**Purpose:** quantify spread in observed votes.

For vote fractions `p_i(c)` and `K` registered classes:

```text
H_i = -sum_c p_i(c) ln p_i(c)
H_norm_i = H_i / ln K
```

Use `0 ln 0 = 0`.

- Output: raw nats and normalized `[0,1]` value.
- Minimum: two labels for disagreement interpretation; one label returns 0 with single-source warning.
- Assumptions: all votes have equal descriptive weight.
- Validation: uniform maximum, unanimous zero, permutation invariance.
- UI: call it vote entropy, not item difficulty or error probability.

## 23. Vote Margin

**Purpose:** show how close the top two observed vote shares are.

```text
margin_i = p_(1) - p_(2)
```

where shares are sorted descending. For one registered class the dataset is invalid; for one observed class `p_(2)=0`.

- Range `[0,1]`; smaller means closer votes.
- Tie gives 0.
- Same evidence warnings as entropy.
- UI: descriptive only.

## 24. Consensus Uncertainty

For Dawid-Skene:

```text
U_i = 1 - max_c q_i,c
```

- Output only when Dawid-Skene status is success.
- This is model-implied posterior uncertainty under Dawid-Skene assumptions, not empirical error probability.
- Majority Vote has vote entropy/margin and must not expose this field as posterior uncertainty.
- Validation: normalization and monotonic hand fixtures.

## 25. Expected Calibration Error

**Purpose:** assess whether reported confidence corresponds to correctness when confidence and resolved hard gold exist.

Defaults:

- ten fixed equal-width bins: `[0,.1), ... [.9,1]`;
- `confidence` is confidence in submitted/predicted label;
- correctness is 1 when label equals hard gold;

```text
ECE = sum_b (n_b / N) * |accuracy_b - mean_confidence_b|
```

- Empty bins are omitted and shown as empty.
- Minimum: 50 supported observations; below 200 is limited.
- Output: ECE, bin boundaries/counts/accuracy/confidence.
- Uncertainty: item bootstrap CI.
- Limitations: bin-dependent; report Brier score alongside it.
- Validation: scikit-learn-compatible fixtures and perfect/overconfident cases.
- UI: never show if confidence semantics differ across imported sources.

## 26. Brier Score

**Purpose:** proper scoring rule for probabilistic predictions against hard gold.

For complete probability vector `p_i` and one-hot gold `y_i`:

```text
Brier = (1/N) * sum_i sum_c (p_i,c - y_i,c)^2
```

- The multiclass score is not divided by `K`; this convention is fixed in manifests.
- Inputs require complete normalized probabilities and resolved hard gold.
- Minimum: one item; below 20 limited.
- Uncertainty: item bootstrap CI.
- Validation: exact one-hot, uniform, and malformed-vector tests.
- UI: lower is better; display convention and support.

## 27. Probable Quality Defect Diagnostic

This is a deterministic evidence flag, not a learned classifier.

An item receives the flag when at least one primary condition and one support condition hold.

Primary conditions:

- current consensus hard label conflicts with resolved hard gold; or
- Dawid-Skene `max(q) >= 0.85` and at least one submitted current label differs from the posterior argmax; or
- at least two gold-eligible workers with posterior mean reliability `< 0.65` agree on a label rejected by a unique Majority Vote from at least three other eligible workers.

Support conditions:

- at least three current labels;
- eligible analysis component passes connectivity checks;
- relevant thresholds have the minimum evidence defined above.

Severity:

- high: hard-gold mismatch with support >=3;
- medium: DS condition with posterior >=0.90 and support >=4;
- low: other qualifying condition.

Every flag includes the exact triggered clauses. No defect flag is emitted from entropy alone.

## 28. Probable Ambiguity / Policy Issue Diagnostic

Also deterministic and non-causal.

Required conditions:

- at least four current labels;
- normalized vote entropy `>= 0.70`;
- vote margin `<= 0.25`;
- either Dawid-Skene maximum posterior `<= 0.70` or Dawid-Skene unavailable due model/evidence limitations;
- disagreement is not explained solely by workers with gold posterior mean below 0.65 when gold estimates are available.

Supporting evidence may raise severity:

- at least two gold-supported workers with posterior mean `>= 0.80` disagree;
- prior review outcome was `policy_issue` or `unresolved`;
- distributional gold has normalized entropy `>= 0.50`.

The default recommended action is `clarify_policy` or `collect_more_labels`, never automatic relabeling.

Thresholds are frozen in versioned configuration before benchmarks. Sensitivity analysis may be reported but cannot replace the primary result.

## 29. Expected Review Value

**Purpose:** experimental, interpretable ranking for error-correction review. It is not a published statistic and not used for ambiguity-policy queue ranking in the core benchmark.

Components, all in `[0,1]`:

- `u_i = 1 - max(q_i)` from successful Dawid-Skene; when unavailable, the item is ineligible for core ERV;
- `h_i = normalized vote entropy`;
- `e_i = mean(1 - r_w)` over contributing workers, using gold Beta posterior means when eligible and otherwise Dawid-Skene expected diagonal accuracy; provenance records the source;
- `s_i = min(severity_weight / 5, 1)`;
- `c_i = clip(expected_review_cost, 0.25, 4) / 4`.

Frozen core formula:

```text
raw_i = 0.60*u_i + 0.20*h_i + 0.20*e_i
ERV_i = raw_i * (0.5 + 0.5*s_i) / max(c_i, 0.0625)
```

Ranking is descending ERV. Components, weights, and cost transform are included in every output.

Rules:

- weights are fixed before reporting benchmark results;
- weights may be developed only on designated development scenarios;
- reporting scenarios and selected external-dataset evaluation gold cannot tune weights;
- missing review cost uses documented `1.0` and a warning;
- ERV does not claim calibrated expected monetary value;
- no superiority claim unless confidence intervals beat required baselines on held-out scenarios;
- separate policy/ambiguity prioritization is deferred.

Validation:

- exact component fixtures;
- monotonicity when one component increases and others remain fixed;
- invariance to item input order;
- fixed-weight/config checksum tests;
- benchmark comparison against all required baselines.

UI:

- label “Experimental DataQual Review Value”;
- show component breakdown and review-cost assumption;
- show benchmark evidence or “not yet benchmarked”;
- never display as a percentage probability or ROI.

## 30. Review-prioritization baselines

- Random: seeded random permutation.
- Highest entropy: descending normalized vote entropy; deterministic item-ID tie break.
- Lowest consensus confidence: descending Dawid-Skene uncertainty; only eligible successful results.
- Lowest worker reliability: descending mean worker error exposure `e_i` from section 29.
- ERV: section 29.

All strategies receive the same candidate set for a given comparison. Items ineligible for a strategy are excluded from the entire primary comparison or handled in a separately reported coverage analysis; strategies may not receive different denominators silently.
