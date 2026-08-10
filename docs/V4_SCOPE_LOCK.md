# DataQual v4 Core Release Scope Lock

Status: implementation contract  
Scope version: `v4-core-1.0`  
Applies to: first research-grade DataQual v4 release  
Change policy: changes require a written architecture decision record (ADR) and explicit scope re-approval.

## 1. Product problem

Multi-annotator categorical datasets are often managed through aggregate dashboards that hide the evidence behind quality claims. Teams need to know:

- whether coverage and overlap are sufficient for trustworthy analysis;
- where annotators disagree and whether disagreement is more consistent with error or ambiguity;
- how consensus changes when reliability is modeled;
- which annotators have enough gold evidence to support performance claims;
- which items deserve scarce reviewer attention;
- whether a proposed quality-control policy outperforms simple baselines.

DataQual v4 solves this problem by computing every core signal from immutable item-level annotation evidence and exposing the method, support, uncertainty, and provenance behind each result.

## 2. Primary user

The primary user is an AI Data Operations or Annotation Quality professional responsible for categorical labeling programs:

- Annotation Quality Lead
- AI Data Operations Manager
- Human Data Program Manager
- Evaluation Operations Lead
- Technical QA / Dataset Quality Specialist

The first release is not designed for annotators performing labeling work inside DataQual. It analyzes imported annotation events and records subsequent review decisions.

## 3. Supported annotation types

The core release supports only:

- binary categorical labels;
- single-label multiclass categorical labels;
- sparse worker-item annotation matrices;
- optional gold labels;
- optional annotation confidence;
- optional timestamps and durations;
- optional adjudicated or reviewed labels;
- optional severity and task-family metadata.

Each annotation event contains exactly one label from the project's registered label domain. Multilabel rows must be transformed upstream into separate binary tasks or rejected.

## 4. Supported workflows

### 4.1 Import and validate

1. Register or select a project and label domain.
2. upload CSV or JSON data;
3. preserve the uploaded bytes unchanged;
4. calculate a checksum;
5. validate the schema and relationships;
6. produce an import report;
7. write accepted analytical tables to Parquet;
8. query them through DuckDB.

### 4.2 Diagnose dataset evidence

- coverage and missingness;
- labels per item and annotator;
- overlap graph diagnostics;
- class prevalence;
- percent and pairwise agreement;
- nominal Krippendorff's Alpha with uncertainty.

### 4.3 Diagnose annotators

- gold accuracy and class metrics where gold exists;
- evidence volume and coverage;
- Beta-Binomial reliability estimates;
- Dirichlet-smoothed class confusion;
- explicit insufficient-evidence states.

### 4.4 Infer and compare consensus

- Majority Vote;
- gold-reliability-weighted Majority Vote when eligible;
- from-scratch Dawid-Skene;
- posterior probabilities, convergence diagnostics, and method sensitivity.

### 4.5 Diagnose disputed items

- vote distribution, normalized entropy, and vote margin;
- consensus posterior and uncertainty;
- evidence-backed Probable Quality Defect flags;
- evidence-backed Probable Ambiguity / Policy Issue flags;
- unresolved and distributional outcomes.

These flags are diagnostic recommendations, never declarations of ground truth.

### 4.6 Prioritize and evaluate review

- random, entropy, confidence, and worker-reliability baselines;
- experimental DataQual Expected Review Value (ERV);
- review event capture;
- errors recovered and review-efficiency curves at fixed budgets.

### 4.7 Reproduce research results

- core correctness suite: deterministic simulator, analytical fixtures, and Crowd-Kit reference-parity fixtures;
- explicitly licensed external validation on the selected requirements-annotation dataset for Majority Vote and Dawid-Skene;
- method-specific simulator benchmarks for weighted vote, ambiguity diagnostics, and review prioritization;
- command-line benchmark runner;
- saved configurations, seeds, checksums, predictions, estimates, metrics, and reports.

External MV/DS validation is not evidence for every feature. Weighted Vote requires simulator validation and keeps its 20-development-gold-event minimum; real-data WV evidence is optional until adequate licensed historical-gold overlap exists. Ambiguity classification and review prioritization require simulator truth initially and may use real datasets only when their targets are identifiable. `relevance-2` remains historical audit evidence, not a release benchmark, until its dataset license is authoritatively resolved.

## 5. Explicit non-goals

The first release will not implement or imply support for:

- ordinal, multilabel, ranking, or pairwise-preference annotation;
- free-text aggregation;
- bounding boxes, segmentation, keypoints, or IoU quality;
- RLHF preference data;
- GLAD, MACE, or EBCC;
- drift detection, EWMA, CUSUM, Page-Hinkley, or BOCPD;
- BADGE, BALD, BatchBALD, active model training, or embedding acquisition;
- weak supervision or executable labeling functions;
- AI-assist causal experiments;
- subgroup/fairness auditing;
- CIFAR-10N or CIFAR-10H;
- webhooks, Slack/Teams integration, or workflow automation;
- authentication, multi-tenancy, RBAC, or regulated-data compliance;
- real-time streaming ingestion;
- a labeling interface;
- automatic correction of source annotations;
- a single universal annotator quality score;
- claims of causal bias, fairness, production ROI, or state-of-the-art performance.

Drift is anticipated only through timestamp-preserving schemas and module boundaries. No drift metric, alert, badge, or UI route may appear in the core release.

## 6. Core product flow

```text
raw upload
  -> immutable archive + checksum
  -> strict validation and import report
  -> canonical Parquet tables
  -> DuckDB analytical views
  -> descriptive evidence and agreement
  -> consensus and annotator estimates
  -> item diagnostics and explainable flags
  -> review queue strategies
  -> review events and efficiency evaluation
  -> reproducible benchmark artifacts
```

An invalid import stops before analytical storage. An insufficient-evidence method returns an explicit unavailable result; it does not substitute a synthetic value.

## 7. DataQual versus Ghost Oort

DataQual v4 is for single-label categorical annotation quality operations. It focuses on worker-item evidence, categorical consensus, reliability, disagreement, and review prioritization.

Ghost Oort remains the separate product concept for pairwise preferences, RLHF-style judgments, reward-model workflows, and preference-annotator behavior.

The projects must not share marketing claims or silently reuse incompatible statistical methods. Pairwise preference data must be rejected by the DataQual v4 core schema rather than coerced into categorical rows.

## 8. Release completion definition

The core release is complete only when all of the following are true:

1. All canonical entities in `DATA_MODEL.md` are implemented and versioned.
2. CSV and JSON imports preserve raw bytes and produce deterministic validation reports.
3. Duplicate, reannotation, missing-value, label-domain, and timestamp policies are enforced.
4. Descriptive and agreement metrics operate only on item-level evidence.
5. Alpha and bootstrap intervals pass golden and parity tests.
6. Gold-based annotator metrics include support and uncertainty.
7. Majority, eligible weighted vote, and Dawid-Skene return traceable results.
8. Dawid-Skene passes the parity thresholds in `METHODS_CONTRACT.md`.
9. Item diagnostic flags satisfy the explainability contract.
10. The simulator reproduces identical datasets for identical seeds.
11. The pre-registered core correctness suite and selected licensed external MV/DS benchmark run from the CLI without the web UI.
12. ERV is evaluated against every required baseline using frozen weights and held-out reporting scenarios.
13. Every benchmark run emits the required manifest and artifacts.
14. All binary gates in `VALIDATION_AND_ACCEPTANCE_GATES.md` pass.
15. A fresh clone can install, test, run the benchmark smoke suite, build the frontend, and launch the demo from documented instructions.

## 9. Scope-creep prohibitions

The following must not enter the release through “small” additions:

- disabled navigation entries for deferred methods;
- placeholder charts carrying deferred algorithm names;
- “coming soon” cards for Labs;
- model-training dependencies;
- demographic fields added without an approved governance design;
- generic quality tiers presented as statistical conclusions;
- drift-like trend warnings without a validated drift method;
- active-learning controls without model inputs;
- AI-assist acceptance rates without event data;
- synthetic metrics in the production demo;
- additional benchmark datasets before the core correctness suite and selected licensed external dataset pass reproducibility and license review.

## 10. Change-control rule

A proposed addition is out of scope unless it directly supports one of the workflows in section 4 and passes all of these tests:

- it requires no new annotation regime;
- it has a defined evidence dependency;
- it has a testable method contract;
- it has a release gate;
- it does not delay the core benchmark;
- it does not introduce a deferred algorithm or dataset.

Otherwise it is recorded as a post-core ADR and deferred.
