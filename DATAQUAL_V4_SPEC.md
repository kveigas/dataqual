# DataQual v4 — Technical & Research Specification

**Working title:** DataQual v4 — Research-Grade Annotation Quality Intelligence  
**Status:** Design specification / implementation contract  
**Primary goal:** Build a rigorous, reproducible, portfolio-grade system for diagnosing, quantifying, and improving human annotation quality from item-level evidence.

---

## 0. Executive decision

DataQual v4 will **not** be a broader version of v3 with more tabs and more algorithm names.

It will be a narrower, deeper system whose central promise is:

> Every important quality signal is computed from item-level annotation evidence, every algorithm is traceable to a documented implementation, and every performance claim is backed by reproducible experiments.

The v4 core will focus on **binary and multiclass categorical annotation**. This is deliberate. A research-grade implementation of one annotation regime is more credible than a shallow implementation of classification, segmentation, ranking, weak supervision, active learning, fairness, and LLM evaluation simultaneously.

Later extensions may support ordinal labels, pairwise preferences, free text, segmentation, and RLHF-style data, but they are not part of the v4 core release.

---

# 1. Why v4 exists

DataQual v3 already establishes a useful product direction: annotation quality monitoring, agreement, truth inference, active learning, AI-assist monitoring, weak supervision, CSV/JSON ingestion, and local persistence.

However, the v3 specification and implementation mix:
- genuine UI/workflow functionality,
- precomputed annotator metrics,
- simplified or simulated statistical outputs,
- and ambitious method names that are not always backed by full item-level computation.

v4 fixes this by making the **data and statistical engine the product**.

The project should be able to survive a skeptical technical interview where someone asks:

- “How exactly is this score computed?”
- “What happens when no gold labels exist?”
- “How do you know Dawid–Skene is implemented correctly?”
- “How do you distinguish bad annotators from hard items?”
- “How do you know your drift detector is not just noisy?”
- “Does review prioritization actually find more errors than random review?”
- “How do you handle legitimate disagreement?”
- “Can I reproduce your benchmark results?”

DataQual v4 must answer those questions with code, tests, plots, benchmark artifacts, and explicit assumptions.

---

# 2. Product thesis

## 2.1 Primary user

The primary user is an:
- AI Data Operations Manager,
- Annotation Quality Lead,
- Human Data Program Manager,
- Evaluation Operations Lead,
- or Technical QA / Data Quality Specialist.

## 2.2 Primary job to be done

Given a stream or batch of annotations from multiple annotators:

1. determine how trustworthy the current dataset is;
2. identify where quality risk is concentrated;
3. distinguish annotator problems from intrinsically difficult or ambiguous items;
4. infer consensus labels where appropriate;
5. prioritize scarce reviewer attention;
6. detect degradation over time;
7. preserve meaningful disagreement where a single hard label is not justified;
8. quantify uncertainty;
9. export auditable decisions;
10. validate whether the quality-control strategy itself works.

## 2.3 Core product statement

> **DataQual is an annotation quality intelligence system that turns raw multi-annotator judgments into calibrated consensus, annotator diagnostics, disagreement analysis, drift alerts, and evidence-based review priorities.**

---

# 3. Scientific principles

DataQual v4 must follow these rules.

## 3.1 No metric without provenance
Every displayed metric must have:
- a named computation,
- a documented formula or algorithm,
- a data dependency,
- a confidence/uncertainty treatment where appropriate,
- and test coverage.

## 3.2 No method-name theater
The UI must not say BADGE, BatchBALD, Dawid–Skene, GLAD, MACE, EBCC, BOCPD, etc. unless that method is actually executed or clearly labeled as an external/reference benchmark.

## 3.3 No unsupported performance claims
Never state “X% improvement,” “3.4× ROI,” “eliminates bias,” or “state of the art” unless the number is produced by a reproducible experiment in this repository.

## 3.4 Preserve disagreement when appropriate
Disagreement is not automatically annotation failure. It may reflect:
- item ambiguity,
- insufficient context,
- subjective interpretation,
- policy ambiguity,
- legitimate demographic/perspectival differences,
- or annotator error.

The system must support both:
- **consensus-seeking workflows**, and
- **disagreement-preserving workflows**.

## 3.5 Uncertainty is first-class
Point estimates are insufficient for:
- annotator reliability,
- class-level quality,
- subgroup comparisons,
- drift detection,
- consensus confidence.

Small samples must visibly produce wider uncertainty.

## 3.6 Benchmarks are part of the product
The benchmark suite is not an appendix. It is a first-class capability demonstrating that DataQual’s decisions are empirically grounded.

---

# 4. Scope

## 4.1 Core v4 scope

Supported:
- binary categorical annotation;
- multiclass categorical annotation;
- sparse multi-annotator matrices;
- optional gold labels;
- optional annotator confidence;
- optional timestamps;
- optional review/adjudication labels;
- optional model predictions/probabilities;
- optional item/annotator metadata;
- optional subgroup metadata;
- optional annotation duration.

Not core:
- image segmentation IoU QA;
- free-text aggregation;
- ranking/pairwise RLHF;
- bounding boxes/keypoints;
- programmatic weak supervision;
- LLM prompt evaluation;
- training large models;
- fully general active learning.

Those may appear later in **Labs** or in Ghost Oort.

---

# 5. Canonical data model

The core unit is an individual annotation event.

## 5.1 `annotations`

Required:
- `annotation_id`
- `project_id`
- `item_id`
- `annotator_id`
- `label`

Optional:
- `timestamp`
- `confidence`
- `duration_ms`
- `reviewer_id`
- `review_status`
- `adjudicated_label`
- `annotation_source` (`human`, `ai_assisted`, `model`, `gold`)
- `ai_suggestion`
- `ai_confidence`
- `metadata_json`

## 5.2 `items`

- `project_id`
- `item_id`
- `gold_label` optional
- `severity_weight` optional
- `subgroup` optional
- `task_family` optional
- `content_ref` optional
- `embedding_ref` optional
- `metadata_json`

## 5.3 `annotators`

- `annotator_id`
- `role`
- `team`
- `tenure_start`
- `language`
- `specialty`
- `metadata_json`

No demographic field is required. Sensitive metadata must be opt-in.

## 5.4 `model_outputs` optional

- `item_id`
- `model_id`
- `predicted_label`
- class probability vector
- embedding reference
- inference timestamp

## 5.5 `review_events`

- `review_event_id`
- `item_id`
- `reviewer_id`
- `pre_review_label`
- `post_review_label`
- `reason_code`
- `decision_timestamp`
- `review_duration_ms`

This table is essential for measuring whether review prioritization actually works.

## 5.6 Storage

Preferred:
- Parquet for immutable/imported analytical tables.
- DuckDB for local analytical querying.
- JSON only for compact configuration.
- SQLite may be used for application state if needed, but raw analytical events should not be trapped inside UI state.

---

# 6. System architecture

## 6.1 Frontend

- React
- Vite
- TypeScript
- accessible component primitives
- deterministic charting library
- no browser-side Babel
- no giant single-file application

Suggested structure:

```text
frontend/
  src/
    app/
    components/
    features/
      overview/
      annotators/
      items/
      consensus/
      adjudication/
      drift/
      review/
      benchmarks/
      labs/
    lib/
    types/
```

## 6.2 Analytics/API layer

- Python 3.12+
- FastAPI
- Pydantic
- pandas / Polars
- NumPy
- SciPy
- scikit-learn
- DuckDB
- PyArrow
- Crowd-Kit for independent/reference implementations where appropriate

Suggested structure:

```text
backend/
  dataqual/
    ingestion/
    schemas/
    agreement/
    aggregation/
    reliability/
    disagreement/
    drift/
    prioritization/
    calibration/
    simulation/
    benchmarks/
    reporting/
    api/
```

## 6.3 Research isolation

Statistical methods must be callable outside the UI.

A benchmark command such as:

```bash
python -m dataqual.benchmarks.run --config configs/relevance2.yaml
```

must work without starting the web app.

## 6.4 Reproducibility metadata

Every benchmark result artifact stores:
- git commit hash;
- package lock/hash;
- dataset identifier;
- dataset checksum;
- configuration;
- random seeds;
- algorithm parameters;
- execution timestamp;
- machine/runtime metadata.

---

# 7. Statistical engine

## 7.1 Descriptive quality layer

Compute from item-level records:

- annotation count;
- annotator count;
- item coverage;
- labels per item;
- labels per annotator;
- class prevalence;
- missingness;
- review rate;
- adjudication rate;
- raw agreement;
- label entropy;
- annotator-item overlap graph statistics;
- gold coverage;
- annotation duration distribution.

No synthetic values.

---

# 8. Agreement metrics

## 8.1 Required

### Percent agreement
Simple and interpretable baseline.

### Pairwise agreement matrix
Computed from actual co-annotated items only.

Every cell must display:
- number of shared items,
- agreement estimate,
- uncertainty or minimum-support warning.

### Krippendorff’s Alpha
Core metric for nominal data and missing annotation matrices.

Requirements:
- unit-tested against known examples;
- bootstrap confidence interval;
- explicit missing-data behavior;
- no claim that alpha alone determines dataset quality.

### Fleiss’ Kappa
Available when assumptions are satisfied.

### Gwet’s AC1
Retain as an optional alternative agreement statistic, but:
- document assumptions;
- independently unit-test;
- never frame it as universally “better” than kappa.

## 8.2 Agreement uncertainty

Use item-level bootstrap confidence intervals.

For time-series slices, preserve temporal ordering when the inferential target requires it.

---

# 9. Consensus / latent truth inference

Every consensus run outputs:
- hard label;
- posterior/probability distribution where available;
- confidence;
- method name;
- method configuration;
- diagnostics;
- convergence status.

## 9.1 Baselines

Required:
- Majority Vote
- reliability-weighted Majority Vote

## 9.2 Dawid–Skene

Implement and test a true multiclass EM algorithm.

Outputs:
- posterior label probabilities;
- estimated worker confusion matrices;
- log-likelihood history;
- convergence diagnostics.

Validation:
- parity tests against Crowd-Kit on identical inputs;
- synthetic recovery tests under known confusion matrices;
- robustness tests for sparse/missing labels.

## 9.3 GLAD

Use GLAD to model:
- annotator ability;
- item difficulty.

Purpose:
Prevent “low agreement” from automatically being blamed on the worker.

Validation:
- parity/reference comparison with Crowd-Kit;
- synthetic experiments where item difficulty is known.

## 9.4 MACE

Use as a benchmark/alternative competence model.

Purpose:
Evaluate robustness to spam-like annotators.

Do not describe MACE as a generic bot detector. Report what the model actually estimates.

## 9.5 EBCC — experimental advanced consensus

Add Enhanced Bayesian Classifier Combination as an advanced experimental method because it models worker correlation.

This is especially valuable for:
- correlated error patterns;
- workers trained from the same examples;
- copied heuristics;
- shared systematic biases.

If implementation risk is high, EBCC may be benchmark-only in the first v4 release.

## 9.6 Method comparison panel

For each dataset/project show:
- Majority Vote
- Dawid–Skene
- GLAD
- MACE
- EBCC if enabled

Compare:
- agreement with known gold where available;
- calibration;
- number of changed labels;
- method confidence;
- disagreement between aggregators.

A major product feature is **consensus sensitivity**:
> “Would the final dataset change materially depending on the aggregation method?”

---

# 10. Annotator intelligence

Do not use one opaque 0–100 quality score as the primary truth.

Each annotator profile contains separate dimensions.

## 10.1 Gold-based performance

When gold exists:
- accuracy;
- macro precision/recall/F1 where meaningful;
- class-specific sensitivity/recall;
- confusion matrix.

## 10.2 Reliability uncertainty

For binary correctness:
- Beta-Binomial posterior or equivalent shrinkage estimate;
- posterior mean;
- 95% credible interval.

For multiclass:
- Dirichlet-smoothed confusion probabilities.

Small sample sizes must visibly shrink toward a project prior.

## 10.3 No-gold performance

Use:
- Dawid–Skene confusion estimates;
- MACE/GLAD ability estimates;
- agreement residuals;
- co-annotation support.

Do not call these “accuracy” without gold.

## 10.4 Calibration

If annotator confidence is available:
- Brier score;
- calibration curve;
- Expected Calibration Error;
- overconfidence/underconfidence summary.

## 10.5 Coverage and evidence strength

Show:
- labels completed;
- co-annotated items;
- classes covered;
- gold items seen;
- time span observed.

An annotator with 15 labels must not visually outrank one with 5,000 labels without a conspicuous evidence warning.

---

# 11. Item difficulty and disagreement intelligence

This is a signature DataQual capability.

## 11.1 Item disagreement diagnostics

Per item:
- vote distribution;
- entropy;
- margin between top labels;
- posterior consensus uncertainty;
- annotator reliability distribution;
- model-vs-human disagreement if model outputs exist;
- item difficulty estimate from GLAD where applicable.

## 11.2 Two-queue disagreement model

Instead of one “bad item” queue, create:

### Queue A — Probable quality defect
Evidence may include:
- disagreement concentrated in historically weak annotators;
- gold mismatch;
- high posterior confidence against submitted label;
- sudden annotator drift;
- class-specific confusion pattern.

### Queue B — Probable ambiguity / policy issue
Evidence may include:
- strong annotators disagree;
- consensus posterior remains diffuse;
- high human label entropy;
- low model confidence;
- repeated disagreement across reviewers;
- no single annotator explains the conflict.

These are diagnostic categories, not ground-truth declarations.

## 11.3 Disagreement preservation

For subjective or ambiguous projects:
- store full label distribution;
- allow “distributional gold” or unresolved state;
- do not force adjudication to a single label unless project policy requires it.

---

# 12. Drift detection

Drift must be computed over ordered annotation events.

## 12.1 Signals

Track over time:
- gold accuracy;
- posterior reliability;
- class-specific error rate;
- disagreement residual;
- confidence calibration;
- annotation duration;
- AI acceptance behavior where applicable.

## 12.2 Algorithms

Required baseline:
- rolling window / EWMA

Required statistical detector:
- CUSUM or Page-Hinkley

Advanced:
- Bayesian Online Changepoint Detection (BOCPD)

## 12.3 Alert evidence

Every drift alert must answer:
- what metric changed?
- from what baseline?
- at approximately what time/task?
- estimated magnitude;
- statistical evidence;
- dominant class/failure mode;
- number of supporting observations.

Example:

> “Annotator A’s posterior gold accuracy declined from 0.93 [0.90, 0.95] to 0.82 [0.77, 0.86]. BOCPD assigns highest posterior change probability near task 642. The increase is concentrated in Neutral → Positive errors.”

## 12.4 Drift validation

Synthetic scenarios:
- abrupt 15% accuracy drop;
- gradual degradation;
- single-class degradation;
- speed/accuracy fatigue pattern;
- temporary disturbance;
- no-drift control.

Report:
- detection delay;
- false alarm rate;
- missed detection rate;
- precision/recall over known changepoints.

---

# 13. Review prioritization engine

This is the primary operational optimization feature.

## 13.1 Goal

Given a limited human review budget, prioritize items that maximize useful quality improvement.

## 13.2 Baselines

Always compare against:
- random review;
- highest disagreement;
- highest entropy;
- lowest consensus confidence;
- labels from lowest-reliability annotators.

## 13.3 DataQual Expected Review Value — experimental

Create an explicit, interpretable score built from validated components.

Conceptual form:

```text
Expected Review Value(i)
=
[
  P(consensus error_i) × error_cost_i
  + λ1 × consensus_entropy_i
  + λ2 × drift_exposure_i
  + λ3 × policy_ambiguity_value_i
]
÷ estimated_review_cost_i
```

Important:
- this is a DataQual experimental policy, not a published established statistic;
- every component is visible;
- weights are configurable;
- default weights are documented;
- no claim of superiority until benchmarked.

## 13.4 Two modes

### Error-correction priority
Optimize discovery of likely wrong labels.

### Policy/ambiguity priority
Optimize identification of unclear taxonomy/guideline cases.

This avoids treating ambiguity as error.

## 13.5 Evaluation

For each strategy measure:
- errors found per 100 reviews;
- recall of known errors at fixed review budgets;
- precision@K;
- review cost;
- cumulative errors recovered versus review fraction;
- area under the review-efficiency curve;
- uncertainty via bootstrap.

---

# 14. Model-aware sampling / Active Learning Labs

Active learning is useful but not core to annotation QA.

Move it into **Labs**.

Only enable model-aware acquisition when:
- model probabilities are available;
- embeddings or stochastic predictions are available as required.

Supported research baselines:
- random;
- least confidence;
- margin;
- predictive entropy;
- diversity / k-center;
- BADGE;
- BatchBALD when Bayesian/stochastic predictive samples are available.

Do not claim BADGE/BatchBALD from a UI simulation.

The system must show the inputs required by each method.

Evaluation:
- learning curves;
- model performance vs number of newly labeled items;
- label-efficiency comparison;
- compute cost;
- multiple seeds.

---

# 15. AI-assist / anchoring experiment

Replace the v3-style “acceptance rate > threshold implies anchoring” logic with a proper experimental diagnostic.

## 15.1 Required fields
- AI suggestion;
- AI confidence;
- whether suggestion was shown;
- annotator initial/final response where available;
- gold/adjudicated outcome.

## 15.2 Metrics

Measure:
- acceptance rate when AI is correct;
- acceptance rate when AI is wrong;
- incorrect-AI acceptance rate (over-reliance diagnostic);
- correct-AI rejection rate (under-reliance diagnostic);
- final accuracy with AI shown vs blind;
- time saved or added;
- confidence shift;
- subgroup or annotator heterogeneity.

## 15.3 Best design

If possible, support randomized blind/AI-assisted assignment so causal comparisons are possible.

Never claim “bias eliminated.” Report observed behavioral differences and uncertainty.

---

# 16. Subgroup / disparity audit

This remains secondary, not the product centerpiece.

When metadata exists, compute quality by subgroup:
- label error rate;
- disagreement;
- adjudication rate;
- model-human conflict;
- review allocation;
- consensus uncertainty.

Requirements:
- minimum-support thresholds;
- confidence intervals;
- no red/green “fair/unfair” verdict from tiny samples;
- explicit warning that observed disparity does not establish causal discrimination.

---

# 17. Simulation laboratory

The simulator is one of DataQual v4’s strongest portfolio assets.

## 17.1 Purpose

Create known ground-truth worlds in which the system can be stress-tested.

## 17.2 Configurable worker types

- expert;
- average;
- weak;
- random/spam;
- adversarial;
- class-specific specialist;
- class-specific confusion;
- correlated worker group;
- copycat;
- fatigued worker;
- drifting worker.

## 17.3 Configurable item properties

- easy/hard;
- class imbalance;
- ambiguous label distribution;
- missing context;
- varying severity;
- varying annotation cost.

## 17.4 Missingness

Support:
- MCAR-like random missing labels;
- uneven worker workload;
- worker/item assignment bias.

Do not imply missingness is ignorable by default.

## 17.5 Time

Simulate:
- abrupt drift;
- gradual drift;
- fatigue/recovery;
- policy change;
- calibration intervention.

## 17.6 Reproducibility

Every generated dataset has:
- seed;
- full configuration;
- hidden ground truth;
- known worker parameters;
- known changepoints.

---

# 18. Real benchmark suite

The first release should use a small number of credible datasets rather than dozens.

## 18.1 Crowd-Kit categorical benchmark

Use at least one Crowd-Kit classification dataset with:
- worker IDs;
- task IDs;
- labels;
- reference/gold labels.

Initial candidate:
- `relevance-2`

Purpose:
- reproduce reference aggregation algorithms;
- compare Majority Vote, Dawid–Skene, GLAD, MACE, etc.

## 18.2 CIFAR-10N

Use the official human noisy label release.

Advantages:
- real human annotation errors;
- multiple human label sets;
- clean reference labels;
- official side information including encrypted worker IDs and annotation time at batch level.

Purpose:
- real human noise benchmark;
- class-specific confusion;
- worker/behavior analysis where the granularity supports it;
- compare synthetic and real noise.

## 18.3 CIFAR-10H

Use for disagreement / distributional uncertainty.

Purpose:
- compare hard aggregation against human label distributions;
- assess whether DataQual preserves uncertainty;
- evaluate distributional metrics.

CIFAR-10H should not be used for annotator-level claims unless annotator identities are actually available in the released data.

## 18.4 Dataset license audit

Before automated download or redistribution:
- record license;
- record source;
- do not commit prohibited raw data;
- provide downloader scripts when redistribution is not appropriate.

---

# 19. Validation matrix

## 19.1 Consensus label recovery

Metrics:
- accuracy;
- macro-F1;
- negative log-likelihood;
- Brier score;
- calibration error where probabilities exist.

Baselines:
- majority vote;
- weighted vote;
- Dawid–Skene;
- GLAD;
- MACE;
- EBCC if implemented.

## 19.2 Worker reliability recovery

On synthetic/gold-supported data:
- Spearman rank correlation with true/observed worker accuracy;
- MAE of estimated competence;
- class-confusion matrix error;
- precision@K for identifying lowest-quality workers.

## 19.3 Difficulty recovery

On simulations:
- Spearman correlation between inferred and true difficulty;
- ability to separate hard-item disagreement from weak-worker error.

## 19.4 Drift

- median detection delay;
- false alarm rate;
- miss rate;
- precision/recall of changepoint alerts.

## 19.5 Review prioritization

- errors recovered at 1%, 5%, 10%, 20% review budgets;
- precision@K;
- cumulative recovery curve;
- review cost.

## 19.6 Distributional disagreement

Where human label distributions exist:
- cross-entropy;
- Jensen–Shannon divergence;
- Brier score for label distributions;
- hard-label accuracy as a secondary metric.

## 19.7 AI-assist behavior

- incorrect-AI acceptance rate;
- correct-AI acceptance rate;
- accuracy delta;
- time delta;
- confidence calibration delta.

---

# 20. Statistical reporting standard

## 20.1 Confidence intervals

Use:
- paired bootstrap over items for label-recovery comparisons;
- worker-level bootstrap for worker-ranking summaries where appropriate;
- Monte Carlo intervals across simulation seeds;
- credible intervals for Bayesian reliability estimates.

Default confidence level:
- 95%.

## 20.2 Seeds

For stochastic algorithms and simulations:
- use a predefined seed set;
- report all seeds;
- never report only the best seed.

## 20.3 Multiple comparisons

If many methods are tested simultaneously:
- report all comparisons;
- use Holm correction or clearly label exploratory comparisons.

## 20.4 Effect sizes before “significance”

Report:
- absolute difference;
- relative difference;
- confidence interval;
- practical consequence.

Avoid “statistically significant” as the main story.

## 20.5 Negative results

If DataQual’s custom review policy loses to entropy or random sampling in some scenario, show it.

This increases credibility.

---

# 21. Correctness validation

## 21.1 Golden unit tests

For small hand-computable examples:
- agreement;
- confusion matrices;
- posterior normalization;
- bootstrap sampling;
- review score components;
- drift test statistics.

## 21.2 Reference parity

Compare:
- DataQual Dawid–Skene vs Crowd-Kit;
- DataQual GLAD integration/reference outputs;
- MACE via verified library/reference path.

Define numeric tolerances in tests.

## 21.3 Property tests

Examples:
- probabilities sum to one;
- confusion-matrix rows sum to one;
- duplicated identical labels cannot lower raw agreement;
- posterior intervals narrow as evidence increases under controlled conditions;
- identical seeds reproduce identical simulation data;
- adding a perfect gold annotator should not reduce gold accuracy under defined aggregation settings.

## 21.4 Failure tests

Test:
- one annotator;
- one label class;
- no overlap between workers;
- extremely sparse data;
- duplicate annotations;
- malformed labels;
- missing timestamps;
- tiny gold set;
- perfect agreement;
- perfect disagreement;
- adversarial worker.

---

# 22. Benchmark runner

Command-driven, not UI-only.

Example:

```bash
dataqual benchmark run configs/benchmarks/relevance2.yaml
```

Outputs:

```text
artifacts/
  run_id/
    config.yaml
    manifest.json
    metrics.csv
    per_item_predictions.parquet
    per_worker_estimates.parquet
    plots/
    report.md
```

The UI may load these artifacts for interactive exploration.

---

# 23. Research questions / hypotheses

These are hypotheses to test, not claims.

### H1 — Worker heterogeneity
Probabilistic aggregation will outperform majority vote under heterogeneous worker confusion patterns.

### H2 — Item difficulty
Difficulty-aware modeling will reduce the tendency to falsely classify hard items as annotator-quality failures.

### H3 — Worker correlation
Correlation-aware aggregation will be more robust than independent-worker models when annotators share systematic errors.

### H4 — Review prioritization
A calibrated error-probability / expected-value review policy will recover more wrong labels per unit of review budget than random review.

### H5 — Drift
Statistical changepoint methods will detect real worker-quality changes with lower false-alarm rates than fixed rolling-threshold rules.

### H6 — Ambiguity
A disagreement-preserving workflow will reduce unnecessary forced adjudication on items whose disagreement is better explained by ambiguity than low worker reliability.

Each hypothesis must have a pre-defined experiment before results are generated.

---

# 24. UI / UX

The UI should feel like serious AI operations software, not a “metric showcase.”

## 24.1 Navigation

Core:
1. Overview
2. Items
3. Annotators
4. Consensus
5. Review Queue
6. Drift
7. Benchmarks

Secondary:
8. Data
9. Settings

Labs:
10. Active Learning
11. AI Assist
12. Subgroup Audit

## 24.2 Overview

Show:
- project health summary;
- evidence coverage;
- unresolved high-risk items;
- likely quality defects;
- ambiguity/policy queue;
- active drift alerts;
- review efficiency;
- consensus uncertainty.

No decorative synthetic KPIs.

## 24.3 Item detail

Must explain **why** an item is risky:
- vote distribution;
- annotators involved;
- annotator reliability;
- consensus posterior;
- item difficulty;
- model prediction;
- history;
- review events.

## 24.4 Annotator detail

Show:
- evidence volume;
- posterior reliability + interval;
- class confusion;
- gold performance;
- calibration;
- drift timeline;
- hardest task families;
- recent changes;
- flags with explanations.

## 24.5 Benchmark UI

A recruiter should be able to select:
- dataset;
- method;
- metric;
- seed/run;

and see:
- benchmark table;
- confidence intervals;
- learning/review curves;
- failure cases;
- downloadable result artifact.

---

# 25. Explainability contract

Every operational flag must include:

- `flag_type`
- `severity`
- `evidence`
- `support_n`
- `method`
- `threshold/config`
- `uncertainty`
- `recommended_action`

Example:

```json
{
  "flag_type": "annotator_drift",
  "severity": "high",
  "support_n": 184,
  "method": "BOCPD",
  "evidence": {
    "baseline_accuracy": 0.93,
    "recent_accuracy": 0.82,
    "dominant_confusion": "neutral->positive",
    "estimated_change_task": 642
  },
  "recommended_action": "recalibration_review"
}
```

No unexplained red badges.

---

# 26. What moves out of the v4 core

## 26.1 Weak supervision
The v3 Snorkel-style feature is interesting but dilutes the core product.

Move to Labs or a future extension.

## 26.2 BADGE/BALD
Move to Active Learning Labs.

They should only operate when their required model outputs exist.

## 26.3 Generic “quality score”
Do not use one opaque weighted score as the main ranking.

If a composite score is retained for convenience:
- show its components;
- allow configuration;
- label it as an operational heuristic;
- never use it as a substitute for statistical evidence.

## 26.4 Hard-coded 85% AI acceptance trigger
Remove as a universal bias rule.

Replace with AI-assist experimental diagnostics.

---

# 27. Engineering quality

Required:
- Ruff
- mypy or Pyright
- pytest
- coverage report
- pre-commit
- CI on GitHub Actions
- pinned dependencies
- deterministic simulation tests
- Dockerfile
- architecture decision records (ADRs)
- API schema docs
- benchmark documentation

Suggested CI gates:
- formatting/lint;
- type checks;
- unit tests;
- integration tests;
- benchmark smoke test on tiny fixture;
- frontend build;
- accessibility smoke;
- no secrets.

---

# 28. Documentation

Repository front page should include:

1. What problem DataQual solves
2. Architecture diagram
3. Five-minute demo
4. Data schema
5. Methods
6. Benchmark results
7. Reproducibility instructions
8. Limitations
9. Research references
10. Screenshots

A separate `METHODS.md` should document equations/assumptions.

A separate `BENCHMARKS.md` should document:
- datasets;
- licenses;
- splits;
- seeds;
- metrics;
- comparison protocol.

A separate `LIMITATIONS.md` should explicitly cover:
- no ground-truth identifiability guarantees in arbitrary crowd settings;
- uncertainty in small worker samples;
- subjective-label limitations;
- benchmark-to-production transfer;
- causal limitations in observational AI-assist analysis;
- subgroup analysis caveats.

---

# 29. Release acceptance gates

## Gate A — Data integrity
PASS only if:
- import validation is strict;
- duplicate handling is explicit;
- missingness is visible;
- raw annotation data is never silently overwritten.

## Gate B — Algorithmic correctness
PASS only if:
- core algorithms have unit tests;
- Dawid–Skene matches reference behavior within tolerance;
- GLAD/MACE reference paths are tested;
- simulation truth is recoverable in easy sanity cases.

## Gate C — Statistical rigor
PASS only if:
- benchmark outputs include uncertainty;
- stochastic methods use multiple seeds;
- no unsupported claims appear;
- results are reproducible from configs.

## Gate D — Operational value
PASS only if:
- review prioritization is compared with random and simple baselines;
- drift alerts are validated against known-change simulations;
- flags contain evidence.

## Gate E — UX credibility
PASS only if:
- every visible metric is traceable;
- no synthetic number is presented as measured;
- no advanced method is represented by a placeholder animation;
- empty/insufficient-data states are explicit.

## Gate F — Reproducibility
PASS only if:
- fresh clone → documented install → tests → benchmark smoke → frontend build works.

---

# 30. Implementation phases

## Phase 0 — Freeze v3
- preserve v3 as historical prototype;
- do not destructively rewrite it;
- create v4 in a new project/repository or clearly isolated branch.

## Phase 1 — Foundation
- Vite/React/TypeScript frontend;
- FastAPI backend;
- DuckDB/Parquet;
- schemas;
- CSV/JSON ingestion;
- deterministic demo dataset;
- tests/CI.

## Phase 2 — Core metrics
- descriptive quality;
- real pairwise agreement;
- Krippendorff alpha;
- bootstrap CIs;
- gold metrics;
- annotator profiles.

## Phase 3 — Consensus
- majority vote;
- weighted vote;
- Dawid–Skene;
- GLAD;
- MACE;
- method-comparison UI;
- reference parity tests.

## Phase 4 — Disagreement intelligence
- item entropy;
- difficulty;
- ambiguity vs defect queues;
- distributional output;
- explainable flags.

## Phase 5 — Drift
- EWMA;
- CUSUM/Page-Hinkley;
- BOCPD;
- simulation validation;
- alert explanations.

## Phase 6 — Review prioritization
- baseline ranking strategies;
- DataQual Expected Review Value;
- review-event capture;
- efficiency benchmarks.

## Phase 7 — Research lab
- benchmark runner;
- real datasets;
- synthetic stress tests;
- confidence intervals;
- saved artifacts;
- benchmark UI.

## Phase 8 — Labs
- model-aware active learning;
- AI-assist experiment;
- subgroup audit.

## Phase 9 — Polish
- docs;
- Docker;
- screenshots;
- accessibility;
- performance;
- public demo;
- portfolio integration.

---

# 31. Recruiter demo script

The final demo should take approximately 3–5 minutes.

### Step 1
Load a dataset.

DataQual immediately reports:
- data coverage;
- gold coverage;
- disagreement;
- worker evidence;
- missingness.

### Step 2
Open one annotator.

Show:
- posterior reliability interval;
- confusion matrix;
- calibration;
- recent drift.

### Step 3
Open one disputed item.

Show:
- votes;
- consensus probabilities;
- worker reliability;
- difficulty;
- why it is in “quality defect” or “ambiguity” queue.

### Step 4
Open Review Queue.

Switch strategy:
- random;
- entropy;
- DataQual review value.

Show benchmarked error-recovery curve.

### Step 5
Inject drift in the simulator.

Watch:
- quality degradation;
- detector trigger;
- explanation;
- queue reprioritization.

### Step 6
Open Benchmarks.

Show:
- Majority Vote vs Dawid–Skene vs GLAD vs MACE;
- real benchmark dataset;
- 95% CIs;
- downloadable artifact.

The demo should communicate:
> “This is not a dashboard full of invented KPIs. It is a tested statistical quality-control system.”

---

# 32. Research references guiding v4

These references motivate the design. They are not evidence that DataQual itself achieves any result until DataQual reproduces its own experiments.

1. Dawid, A. P. & Skene, A. M. (1979). Maximum Likelihood Estimation of Observer Error-Rates Using the EM Algorithm.
   https://doi.org/10.2307/2346806

2. Whitehill, J. et al. (2009). Whose Vote Should Count More: Optimal Integration of Labels from Labelers of Unknown Expertise.
   https://proceedings.neurips.cc/paper/2009/hash/f899139df5e1059396431415e770c6dd-Abstract.html

3. Hovy, D. et al. (2013). Learning Whom to Trust with MACE.
   https://aclanthology.org/N13-1132/

4. Li, Y., Rubinstein, B., & Cohn, T. (2019). Exploiting Worker Correlation for Label Aggregation in Crowdsourcing.
   https://proceedings.mlr.press/v97/li19i.html

5. Ustalov, D., Pavlichenko, N., & Tseitlin, B. Learning from Crowds with Crowd-Kit.
   https://arxiv.org/abs/2109.08584
   https://crowd-kit.readthedocs.io/

6. Burrell, N. & Schoenebeck, G. (2023). Testing conventional wisdom (of the crowd).
   https://proceedings.mlr.press/v216/burrell23a.html

7. Sandri, M. et al. (2023). Why Don’t You Do It Right? Analysing Annotators’ Disagreement in Subjective Tasks.
   https://aclanthology.org/2023.eacl-main.178/

8. Fleisig, E., Blodgett, S. L., Klein, D., & Talat, Z. (2024). The Perspectivist Paradigm Shift.
   https://aclanthology.org/2024.naacl-long.126/

9. Peterson, J. C. et al. (2019). Human uncertainty makes classification more robust / CIFAR-10H.
   https://arxiv.org/abs/1908.07086

10. Wei, J. et al. (2022). Learning with Noisy Labels Revisited / CIFAR-N.
    https://arxiv.org/abs/2110.12088
    https://github.com/UCSC-REAL/cifar-10-100n

11. Adams, R. P. & MacKay, D. J. C. Bayesian Online Changepoint Detection.
    https://arxiv.org/abs/0710.3742

12. Ash, J. T. et al. Deep Batch Active Learning by Diverse, Uncertain Gradient Lower Bounds (BADGE).
    https://arxiv.org/abs/1906.03671

13. Kirsch, A., van Amersfoort, J., & Gal, Y. (2019). BatchBALD.
    https://proceedings.neurips.cc/paper_files/paper/2019/hash/95323660ed2124450caaac2c46b5ed90-Abstract.html

---

# 33. Final definition of “world class”

For this project, “world class” means:

- **coherent**, not feature-bloated;
- **mathematically explicit**, not buzzword-heavy;
- **item-level**, not precomputed-demo-driven;
- **uncertainty-aware**, not score-only;
- **benchmark-backed**, not claim-backed;
- **reproducible**, not screenshot-only;
- **operationally useful**, not research-for-research’s-sake;
- **honest about failure cases**, not optimized for flattering results.

The project succeeds when a technically sophisticated reviewer can inspect the repository, rerun the experiments, disagree with a modeling choice, and still conclude that the work is serious.
