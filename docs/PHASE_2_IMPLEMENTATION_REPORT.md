# Phase 2 Implementation Report

## EVIDENCE ENGINE:

PASS. Current-event counts, all/superseded-event counts, item/annotator/class/gold
counts, coverage, item/annotator distributions, class prevalence, and
co-annotation bands reconcile to canonical Parquet rows. Zero-annotation items
remain visible in item coverage. No field is labelled a quality score.

## OVERLAP ENGINE:

PASS. Sparse worker×item observations, every worker-pair shared-item count,
worker graph nodes/edges/components, largest component, isolated workers/items,
degree, and total shared-item summaries are derived from current events only.
Observed assignment coverage is not described as MCAR missingness.

## PAIRWISE AGREEMENT:

PASS. Each pair uses only the intersection of genuinely co-annotated current
items. Responses include agreements, disagreements, raw agreement, support `N`,
evidence level, warnings, and item-bootstrap CI when `N >= 10`. Zero overlap is
null/`unavailable`; the UI mutes tiny-N rows and offers a presentation-only
minimum-overlap filter.

## DATASET AGREEMENT:

PASS. The implementation pools agreeing unordered pairs over all comparable
unordered pairs. It does not average item percentages. Integer pair counts and
exact hand fixtures validate the definition.

## KRIPPENDORFF ALPHA:

PASS. Nominal Alpha and its coincidence/disagreement components are implemented
from scratch for arbitrary raters, sparse matrices, missing events, and multiple
classes. Single-class/zero-expected-disagreement and insufficient-pairable-item
cases return explicit non-success states without numeric substitution.

## ALPHA PARITY:

PASS. Five golden fixtures meet `1e-10` absolute tolerance against the approved
test-only NLTK implementation. One hundred seeded randomized candidates compare
all finite fixtures at `1e-8`. Production code does not import or call NLTK.

## BOOTSTRAP ENGINE:

PASS. The reusable engine uses item clusters, NumPy `Generator(PCG64(seed))`,
explicit seed, percentile intervals, 2,000 default replicates, exact support
population, and valid/failed counts. It refuses populations below ten items and
intervals with more than 5% undefined replicates. The selected real validation
had zero failed replicates for agreement, Alpha, accuracy, and macro metrics.

## GOLD METRICS:

PASS. Accuracy, macro/micro precision, recall, and F1 use only current annotation
events joined to latest `resolved_hard` gold. Dataset and per-annotator results
retain support. Per-class null/zero-division semantics follow the locked contract
and documented scikit-learn aggregate mapping. Distributional/unresolved gold is
excluded and counted.

## CONFUSION MATRICES:

PASS. Raw counts retain immutable domain order, gold is the row axis, submitted
annotation is the column axis, and counts reconcile exactly to evaluated event
support. Row-normalized output is explicit; unsupported gold rows contain nulls.

## STATISTICAL RESULT CONTRACT:

PASS. `StatisticalResult` exposes metric, value, evidence support/level,
uncertainty, status, method/version, canonical configuration/hash, warnings,
failure reason, and analysis provenance. Evidence/agreement/gold response models
are strict typed Pydantic contracts and frontend responses are independently
validated with Zod.

## ANALYSIS PROVENANCE:

PASS. Every run records analysis-run ID, dataset/snapshot ID, canonical checksum,
method/version, configuration hash, UTC timestamp, software version, and Git
identity when available. Complete bundles are persisted write-once under
`data/analyses/<analysis_run_id>/analysis.json`. Result event/gold IDs join back
to project/item/import records in the immutable canonical snapshot. This source
workspace is not a Git repository, so Git fields truthfully remain null.

## REAL DATASET VALIDATION:

PASS. The checksum-gated Requirements Annotation Phase 3 adapter reproduced the
locked 448 items, 2,674 deduplicated annotations, 121 annotators, and 447 joined
gold items. Ingestion, evidence, overlap, pooled agreement, Alpha, gold metrics,
confusion, item bootstrap, and analysis persistence completed. Aggregate evidence
is in `spikes/phase2/results/phase2_validation.json`; raw review text is absent.
The Phase 0B manifest and historical negative Majority Vote > Dawid–Skene result
remain preserved and unmodified.

## SYNTHETIC VALIDATION:

PASS. Cases A–J cover perfect/disagreeing/single-class/missing/imbalanced data,
perfect versus weak known workers, multiclass confusion, tiny samples,
disconnected worker groups, and reannotation. Expected behavior was encoded
before execution. Observed results are recorded in the validation report and
machine-readable artifact.

## PERFORMANCE OBSERVATIONS:

PASS for the Phase 2 gate. The selected-real standard analysis completed in
`24.77 s` locally with 2,000-replicate intervals. A deterministic 100,000-event /
20,000-item calculation completed pooled agreement plus Alpha in under `0.14 s`
after generation in the final run. Existing Phase 0 one-million-row architecture
evidence remains preserved. No timing is a public performance claim; full API
payload optimization at one million rows is deferred.

## API:

PASS. Versioned typed endpoints exist for evidence, agreement, pairwise cells,
Alpha, dataset gold metrics, per-annotator gold metrics, confusion, and annotator
evidence. Unsupported datasets/annotators/configurations return structured
errors. No fallback statistic is emitted.

## FRONTEND:

PASS. The restrained Phase 2 UI contains evidence overview, coverage/sparsity,
agreement and overlap support, non-ranked annotator evidence, gold metrics, and
raw-count confusion diagnostics. It displays explicit unavailable/limited states
and A/B/C truthfulness labels. No Phase 3 method or placeholder card was added.

## TEST COUNTS:

- Backend: 56 passed, including unit, property, randomized parity, integration,
  API, reannotation, and persistence coverage.
- Frontend unit/integration: 7 passed.
- Playwright: 2 passed.
- Hypothesis executes deterministic property examples beyond the collected test
  count.

## COVERAGE:

- Backend branch-aware total: `92.09%` (required `>= 90%`).
- Frontend: statements `91.30%`, lines `95.71%`.

## TYPE CHECK:

PASS. Pyright reports zero backend/script errors; TypeScript `tsc --noEmit`
passes.

## LINT:

PASS. Ruff lint and format checks pass for backend and scripts.

## BUILD:

PASS. Vite production build succeeds. Locked Python and pnpm dependency graphs
resolve; `pip check`/environment checks are included in the final gate record.

## ACCESSIBILITY:

PASS. Axe reports zero violations on the evidence workspace. Keyboard focus is
visible, tables have captions and scoped headers, status/errors use live semantic
roles, and the 390 px viewport has no document-level horizontal overflow.

## ADVERSARIAL REVIEW:

PASS after correction. Review explicitly checked coincidence-matrix math,
pair-weighted agreement, missing-event handling, item-cluster resampling,
small-N presentation, gold axes/leakage, domain ordering, reannotations,
duplicates, undefined values, aggregate zero-division semantics, provenance,
machine paths, and dataset-specific leakage. The macro-F1 aggregate mapping was
corrected; no genuine defect remains known within the locked Phase 2 scope.

## KNOWN LIMITATIONS:

- Nominal labels only; no ordinal/interval Alpha.
- Bootstrap models item sampling, not temporal dependence or selective assignment.
- Pairwise output is quadratic in annotator count and full sparse matrices can be
  large at production scale.
- Gold metrics are only as authoritative and representative as their source.
- Per-annotator point metrics are descriptive, not competence estimates.
- The UI standard run uses 2,000 rather than release-report 10,000 replicates.
- The app remains local-only with no authentication.
- Git revision is unavailable in the non-Git planning workspace.

## SCOPE DEVIATIONS:

No unapproved algorithm was added. The broader methods contract's Beta-Binomial
per-worker interval is intentionally deferred because the Phase 2 scope explicitly
prohibits Bayesian worker reliability. The larger deterministic timing uses
100,000 events rather than rerunning every Phase 2 endpoint on one million rows;
the preserved Phase 0 one-million-row architecture evidence remains the relevant
storage feasibility record. Both choices are documented limitations, not hidden
fallbacks.

## Final decision

PHASE 2: PASS

READY FOR PHASE 3: YES

Phase 3 has not started.
