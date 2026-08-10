# DataQual v4 Benchmark Protocol

Status: **pre-registered design contract**  
Protocol version: **1.1.0**  
Scope: DataQual v4 release-one methods only

This document fixes the benchmark before implementation. A result that contradicts a hypothesis is a valid negative result; it must not be hidden, re-labelled, or tuned away. Any protocol change after an evaluation seed is opened creates a new protocol version and invalidates comparisons with the earlier version unless both are reported.

## 1. Questions and claims under test

The benchmark answers five bounded questions:

1. Does the from-scratch Dawid–Skene (DS) implementation reproduce a vetted reference implementation within the tolerances in `METHODS_CONTRACT.md`?
2. When their assumptions are approximately satisfied, do weighted vote and DS improve consensus over unweighted majority vote (MV)?
3. Do reported worker-quality estimates track known simulator truth and, where methodologically valid, independent real-data gold labels?
4. Do uncertainty scores identify incorrect or unstable consensus labels?
5. At a fixed review budget, does error-reduction value (ERV) prioritize more correctable errors than simple baselines?

The benchmark does **not** claim that one aggregation method is universally best, that simulated results establish field validity, or that review prioritization measures business value.

## 2. Freeze and leakage rules

- Development data and development seeds may be inspected while implementing.
- Reporting data and reporting seeds remain unopened until all method contracts, thresholds, and tests pass.
- No threshold, smoothing constant, convergence rule, feature, or simulator distribution may be changed in response to reporting results.
- Gold labels are used for evaluation and for the explicitly gold-derived weighted-vote estimator only. They are never passed to MV or DS fitting.
- Evaluation gold labels must not affect worker weights, algorithm selection, threshold selection, or queue construction.
- A failed, non-converged, or ineligible run remains in the run manifest. It may not be silently dropped.
- All algorithm comparisons use the identical eligible item set. Coverage is reported separately.
- Reporting includes every pre-registered scenario, including scenarios designed to violate DS assumptions.

## 3. Determinism and seed registry

Every stochastic operation receives an explicit 64-bit integer seed. A run derives sub-seeds with SHA-256 over `protocol_version | dataset_id | scenario_id | replicate | operation_name`, taking the first eight bytes as an unsigned integer. This prevents changes in call order from changing later random streams.

### 3.1 Seed partitions

- Development replicates: `101, 211, 307, 401, 503`
- Locked reporting replicates: `1009, 2017, 3011, 4001, 5003, 6007, 7001, 8009, 9001, 10007`
- Unit-test fixtures use separate seeds below `100`; they are not benchmark observations.

The reporting-seed list may be increased before any reporting seed is opened, but it may not be reduced afterward. Ten replicates are the minimum release report; simulator uncertainty must be disclosed as limited at that size.

## 4. Algorithms and fixed configurations

| ID | Algorithm | Configuration |
|---|---|---|
| `mv` | Majority vote | Unweighted; exact ties are unresolved. |
| `wv_gold` | Gold-derived weighted vote | Reliability computed only from development gold; minimum 20 gold annotations per worker; chance-adjusted clipped weight from `METHODS_CONTRACT.md`; workers below minimum excluded from this method. |
| `ds_v4` | DataQual from-scratch DS | Fixed initialization, priors, convergence, component and failure rules from `METHODS_CONTRACT.md`. |
| `ds_ref` | Crowd-Kit DS reference | Pinned version and explicit parameters recorded in manifest; benchmark/reference use only, not the primary implementation. |

No method-specific post-processing is permitted beyond the registered unresolved-label rule. `ds_ref` is for parity, not for a misleading “our method beats a library” claim.

## 5. Deterministic simulator

The simulator emits the canonical annotation-event schema plus an inaccessible truth table containing true item labels, item difficulty, ambiguity state, worker confusion matrices, worker group, and any correlation cluster. Truth is never available to aggregation code.

### 5.1 Common defaults

- 3 classes with class prior `[0.50, 0.30, 0.20]`
- 2,000 items, 40 workers, target 5 annotations per item
- Worker confusion matrices drawn once per replicate from scenario-specific distributions
- Item assignments sampled without replacement within an item
- Annotation probability is a registered function of true class, worker confusion matrix, difficulty, and scenario effects
- Every generated artifact includes simulator version, full parameters, seed derivation, and checksums

### 5.2 Registered scenarios

| Scenario | Controlled variation | Hypothesis | Scientific failure criterion |
|---|---|---|---|
| `perfect` | All workers return truth | All eligible algorithms reach 1.0 accuracy; uncertainty is zero or numerical epsilon. | Any wrong consensus label or material uncertainty. |
| `heterogeneous` | Worker diagonal accuracies span approximately 0.55–0.95 | `wv_gold` and `ds_v4` outperform or equal MV in mean macro-F1. | Both trail MV by more than 0.01 macro-F1. |
| `weak` | Most workers are only slightly above chance | None may claim confident reliability; coverage and calibration deteriorate visibly. | Confident predictions remain common while accuracy approaches chance. |
| `adversarial` | 15% workers use stable off-diagonal mappings | DS should detect structured confusion better than scalar weights. | DS worker matrices fail to distinguish adversarial structure from random error. |
| `class_confusion` | Workers systematically confuse classes 1 and 2 | DS confusion estimates recover the dominant confused pair. | Dominant confused pair is wrong in more than 20% of reporting runs. |
| `imbalance` | Class prior `[0.90, 0.08, 0.02]` | Macro-F1 and class-wise recall expose failures hidden by accuracy. | Report presents accuracy without class-wise metrics, or rare-class recall is undefined without explanation. |
| `sparse_overlap` | 2 annotations/item; worker graph barely connected | Estimates become less stable and intervals/warnings reflect this. | System reports normal-confidence worker estimates without sparse-overlap warning. |
| `disconnected` | Two worker–item components with deliberately different label support | DS follows component eligibility rules and does not fabricate cross-component comparability. | Ineligible component produces ordinary global scores without warning. |
| `difficult_items` | 25% items reduce all worker diagonals toward chance | Item uncertainty ranks difficult items above ordinary items on average. | AUROC for difficult-item detection is at or below 0.50. |
| `ambiguous_items` | 15% items have a registered two-label truth distribution | Distributional diagnostics mark ambiguity; forced-label accuracy is not treated as full truth. | Ambiguous items are evaluated only as single-label errors or rarely flagged. |
| `correlated_workers` | Worker clusters share a latent error shock | DS overconfidence is expected and must be measured, not concealed. | Report claims calibrated independence or omits the assumption violation. |
| `missing_not_random` | Assignment/response missingness depends on worker and class | Coverage changes and selection bias are disclosed. | Missing events are interpreted as incorrect labels or silently imputed. |

Scenario parameter files are immutable inputs once reporting begins. Exact numeric distributions belong in versioned benchmark configuration artifacts; changing them requires a protocol version bump.

## 6. Benchmark layers and external validation

### 6.1 Core correctness benchmarks

Core correctness is established with all three of the following, none of which may be replaced by a favorable real-data score:

- deterministic synthetic datasets with inaccessible truth and registered stress scenarios;
- hand-constructed analytical fixtures covering formulas, ties, absent classes, sparsity, disconnected components, and failure states;
- fixed reference-parity fixtures comparing `ds_v4` with the pinned Crowd-Kit implementation.

### 6.2 Required real-world external validation

Release one additionally requires at least one explicitly licensed categorical multi-annotation dataset with stable item/worker IDs, reproducible access, meaningful overlap, and a defensible external evaluation target. This requirement applies to MV and DS external validation; it is not evidence for every DataQual capability.

The selected release-one dataset is **Crowd-Annotation Results: Identifying and Classifying User Requirements in Online Feedback**, Zenodo record `3626185`, Phase 3 non-test-question subset. The record is licensed CC BY 4.0. The locked source archive SHA-256 is `1538ee6b9a1408fd098c06f0ab8e53a9c1867b9ba9769ccaaa712f0dcd2ec0f2`. Conversion and exclusions are fixed in `DATASET_SELECTION_REPORT.md` and the dataset manifest.

- Preserve downloaded bytes unchanged outside the repository; commit retrieval instructions, checksums, attribution, and aggregate evidence only.
- Exclude Figure Eight platform test-question rows (`_golden != FALSE`).
- Remove only the 27 verified exact duplicate item-worker-label exports; conflicting repeated labels would be a hard conversion failure.
- Join independent researcher gold by normalized feedback text. The single unmatched item is retained for unsupervised aggregation but excluded from gold-scored metrics.
- Use a deterministic item-hash split fixed before implementation. All annotations for an item remain together. Reporting gold is absent from fitting, threshold selection, and queue construction.
- MV/DS accuracy and macro-F1 are scored on the identical held-out gold item set. Coverage and unresolved results are separate outcomes.

This one dataset demonstrates external behavior in a bounded five-class requirements-classification setting. It does not establish cross-domain generalization, universal DS superiority, ambiguity classification validity, or review-policy effectiveness.

### 6.3 Method-specific benchmark requirements

- **Weighted Vote:** deterministic simulator validation is required. A real-data benchmark is optional unless an explicitly licensed dataset has adequate historical development-gold evidence per worker. The production minimum remains 20 development-gold annotations per worker.
- **Ambiguity diagnostics:** registered simulator ambiguity scenarios are required initially. Ordinary categorical gold disagreement must not be presented as validated ambiguity classification.
- **Review prioritization:** registered simulator scenarios with known correctable errors and review outcomes are required. A real benchmark is permitted only when its errors or review outcomes make the endpoint identifiable.

### 6.4 Weighted-vote evidence sensitivity experiment

This is a pre-registered sensitivity analysis; it does not tune the production threshold. Generate worker ability independently of item truth and assignments. Generate disjoint development-gold and evaluation item streams while allowing worker identities to span both. Estimate reliability only from development gold; workers below the tested evidence level receive no learned weight. Evaluation gold stays inaccessible until scoring.

Run evidence levels `5, 10, 20, 50, 100` under `homogeneous_workers`, `heterogeneous_workers`, `one_weak_worker`, `adversarial_workers`, `class_specific_errors`, and `sparse_overlap`. Use the identical evaluation events for MV, weighted vote, and DS within each scenario/replicate. Report eligible-worker fraction, evaluation-item coverage, accuracy, macro-F1, Brier score where a probability distribution is defined, worker-reliability MAE, Spearman rank correlation, and paired bootstrap 95% intervals. Coverage collapse is a result, not grounds to lower the rule. The release default remains 20 unless a later change-controlled, pre-registered study supports a revision.

The Phase 0B isolated spike in `WEIGHTED_VOTE_SENSITIVITY_REPORT.md` verifies that this design is executable and records mixed/negative exploratory results. It is development evidence, not the future locked release run; production implementation must reproduce the registered design independently.

### 6.5 `relevance-2` historical status

`relevance-2` is not a release benchmark because no explicit dataset license was verified. Its Phase 0 manifest, hashes, schema, and coverage findings remain as audit evidence with `license_status: unresolved`, `release_benchmark: false`, and `public_artifact_eligible: false`. Crowd-Kit's Apache-2.0 software license does not grant rights to this data. Re-entry requires authoritative dataset terms and formal change control.

## 7. Metrics

### 7.1 Consensus

- Accuracy, macro-F1, per-class precision/recall/F1
- Coverage and unresolved count
- Multiclass log loss (NLL), with probabilities clipped to `[1e-12, 1]`
- Multiclass Brier score
- Expected calibration error (ECE) using the fixed bins in `METHODS_CONTRACT.md`

### 7.2 Worker-quality recovery

For simulator truth and eligible real-data gold estimates:

- Pearson and Spearman correlation of scalar reliability
- Mean absolute error of scalar reliability
- Confusion-matrix mean absolute error where truth is defined
- Bottom-`K` precision and recall for `K = max(1, ceil(0.10 × eligible_workers))`; ties at the cutoff are resolved by canonical worker ID only for reproducibility and disclosed
- Eligible-worker coverage and gold-event coverage

### 7.3 Diagnostic quality

- AUROC and average precision for known simulated difficult/ambiguous items
- Precision, recall, and coverage of `probable_defect` and `probable_ambiguity`
- Calibration metrics on unambiguous single-truth items only; ambiguous items are reported separately

### 7.4 Review prioritization

Compare random ordering, highest entropy, lowest consensus confidence, lowest associated worker reliability, and ERV. Use item-level budgets of `1%, 5%, 10%, 20%` of the identical eligible candidate pool.

At each budget report:

- Correctable consensus errors recovered
- Error-recall (`recovered / all correctable errors`)
- Precision at budget
- Cumulative error reduction after substituting adjudicated truth
- Area under the error-recall-versus-budget curve through 20%

Random ordering uses 1,000 deterministic permutations per dataset/replicate. “Review saved” and monetary ROI are prohibited because neither time nor cost is measured.

## 8. Statistical analysis and intervals

- Simulator summaries use the replicate as the unit of analysis, never individual annotation rows.
- Pairwise algorithm differences use the same items and replicate seeds.
- Report the mean, median, standard deviation, and two-sided 95% percentile interval across reporting replicates. With only ten replicates, call this a simulation interval, not a population confidence interval.
- For item-level selected external-dataset metrics, use 10,000 paired stratified bootstrap resamples of held-out gold items, stratified by gold class, with seed derived under Section 3. Report percentile 95% intervals.
- Worker-recovery intervals resample workers only when at least 20 eligible workers exist; otherwise report point estimates and the limitation.
- No null-hypothesis significance stars. Report paired effect sizes and intervals.
- Multiple metrics are descriptive; no cherry-picked single “winner” score is permitted.

## 9. Experiment matrix

| Experiment | Data | Comparison | Primary endpoint | Required interpretation |
|---|---|---|---|---|
| E1 implementation parity | Fixed parity fixtures and eligible simulator reporting runs | `ds_v4` vs `ds_ref` | Posterior/label/confusion tolerances | Failure blocks release of DS. |
| E2 aggregation | All eligible simulator scenarios; selected external dataset for MV/DS only | MV, `wv_gold`, `ds_v4` as eligible | Accuracy and macro-F1 | Report scenario-specific trade-offs and coverage; do not require real-data WV. |
| E3 worker recovery | Simulator truth; development-gold-derived real estimates | Estimated vs known quality | Spearman, MAE, bottom-K P/R | Do not call real-data gold estimates latent truth. |
| E4 uncertainty | Simulator; selected external data only where the endpoint is identified | Entropy, margin, confidence | Error-detection AUROC/AP, ECE, Brier | Separate calibration from ranking quality. |
| E5 flags | Difficult/ambiguous simulator scenarios | Registered flag rules | Precision/recall/coverage | “Probable” flags are heuristics, not diagnoses. |
| E6 review prioritization | Simulator truth; real data only with known errors/review outcomes | Four baselines plus ERV | Error recall at 5% and AUC through 20% | Same candidate pool and budget for every queue. |
| E7 WV sensitivity | Six registered simulator scenarios at evidence levels 5/10/20/50/100 | MV, `wv_gold`, `ds_v4` | Performance, reliability recovery, and coverage | Experimental only; default threshold remains 20. |

## 10. Run and artifact contract

Each run writes an immutable directory containing:

- `manifest.json`: run ID, UTC time, Git commit, dirty-tree status, protocol/config/schema versions, environment lock hash, OS/architecture, dataset and raw-file checksums, seed registry, algorithm parameters
- `eligibility.json`: included/excluded items, workers, components, and exact reasons
- `metrics.parquet`: tidy metric rows with dataset, scenario, replicate, method, split, metric, value, denominator
- `predictions.parquet`: item-level predictions/probabilities and unresolved status
- `worker_estimates.parquet`: worker reliability/confusion outputs and eligibility
- `review_queues.parquet`: strategy, rank, score, and outcomes
- `failures.json`: convergence, numeric, schema, or reference-parity failures
- `report.md`: tables plus required limitations and negative results

Artifacts are written to a new run directory; benchmark runs never overwrite prior evidence.

## 11. Benchmark validity gates

The benchmark is valid only if all are true:

1. Dataset identity, license, checksum, and split are recorded.
2. Development/reporting seeds and gold roles remain separated.
3. Every registered scenario and method appears in the report, including failures.
4. Comparisons use paired eligible sets and expose coverage differences.
5. Reference parity meets the methods-contract tolerances.
6. Intervals use the registered resampling unit and seed.
7. No reporting-data-driven tuning occurred; a signed checklist records this assertion.
8. Re-running under the locked environment reproduces canonical numeric artifacts under the tolerances in `VALIDATION_AND_ACCEPTANCE_GATES.md`.

If any gate fails, the output may be retained as a development run but cannot support a v4 release claim.

## 12. Expected limitations

- DS assumes conditionally independent workers given the true class; the correlated-worker scenario intentionally violates this.
- Gold-derived weighted vote may have low worker coverage and selection bias.
- Simulator realism is bounded by its registered generative assumptions.
- The selected requirements dataset is one modest domain and cannot validate all annotation programs.
- The selected dataset's researcher gold is a defensible reference, not infallible latent truth.
- Weighted-vote release evidence is primarily simulated until adequate licensed historical-gold overlap is independently verified.
- Item-level review benefit assumes adjudicated gold is correct and instantly available; it does not estimate actual reviewer cost.
- Threshold-based defect/ambiguity flags require validation and should remain explicitly heuristic.
