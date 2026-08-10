# DataQual v4 Validation and Acceptance Gates

Status: **release contract**  
Applies to: v4 release-one scope in `V4_SCOPE_LOCK.md`

DataQual v4 is releasable only when every mandatory gate below is **PASS**. “Mostly passes,” visual inspection, or a successful demo is not sufficient. A waived gate requires a documented scope revision and a new version of this contract; it cannot be waived informally.

## 1. Gate result format

Each gate produces a machine-readable and human-readable record containing:

- gate ID and version
- PASS or FAIL
- command or procedure executed
- Git commit and dirty-tree status
- environment-lock checksum
- input artifact checksums
- observed values and required thresholds
- artifact paths
- UTC timestamp

Expected failures and skipped tests are FAIL unless the gate explicitly marks a condition as inapplicable. Flaky reruns do not replace the first result; both results remain attached.

## 2. G1 — Scope integrity

**PASS only if:**

1. Every release feature maps to an item in `V4_SCOPE_LOCK.md`.
2. No production route, UI control, database table, benchmark claim, or dependency implements a deferred algorithm or product area.
3. Drift has only a documented interface/extension point; no drift score, detector, chart, endpoint, or claim exists.
4. DataQual contains no Ghost Oort workflow, branding, monitoring subsystem, or deployment coupling.
5. Product copy distinguishes genuine computation, heuristic flags, simulator truth, and unavailable/not-computed values.

Any undocumented feature or scope crossover is FAIL.

## 3. G2 — Data integrity and provenance

**PASS only if all canonical-schema fixtures and import integration tests demonstrate:**

- Required fields, types, identifier rules, label-domain membership, timestamps, and foreign keys are enforced.
- Identical canonical duplicate events are deduplicated with a deterministic report.
- Conflicting duplicate event IDs reject the entire import; no partial commit and no last-row-wins behavior occur.
- Reannotations are append-only, versioned, and linked through `supersedes_event_id`; the active-event rule is deterministic.
- Missing, unresolved, abstained, and not-applicable values remain distinct.
- Raw uploads are byte-preserved with SHA-256 and are never mutated.
- Canonical snapshots and derived tables record schema version, source checksum, transformation version, code commit, and row counts.
- A failed import leaves no visible project snapshot or orphaned derived artifact.
- Parquet/DuckDB round trips preserve identifiers, null semantics, label values, and UTC timestamps on the full fixture suite.
- All migrations are forward-only, idempotent when specified, backed up before execution, and restore-tested.

Required fixture classes: valid minimum, valid full, Unicode identifiers, boundary timestamps, unknown labels, malformed rows, identical duplicates, conflicting duplicates, reannotation chains, missing values, unresolved consensus, and at least one million-row generated import.

Large-import criterion: the one-million-row fixture completes without process failure or data loss on the documented reference machine. Time and peak memory are recorded, not hidden behind a universal performance claim.

## 4. G3 — Mathematical correctness

### 4.1 Exact fixtures

**PASS only if:**

- Percent agreement, pairwise agreement, confusion matrices, accuracy, per-class precision/recall/F1, macro-F1, entropy, margin, Brier score, and ECE match hand-calculated fixtures to absolute error `<= 1e-12` where arithmetic is exactly representable, otherwise `<= 1e-10`.
- Nominal Krippendorff's alpha matches at least five published or independently calculated fixtures, including missing ratings, variable raters per item, perfect agreement, and zero expected disagreement. Absolute error must be `<= 1e-10` when the statistic is defined.
- Undefined denominators return the specified typed undefined result and reason, never zero, NaN serialized as JSON, or a fabricated score.
- Bootstrap confidence intervals use item resampling, the registered seed, requested confidence level, and exact replicate count; fixed fixtures reproduce identical bounds.
- Beta-Binomial and Dirichlet posterior summaries match analytic fixtures to absolute error `<= 1e-10`.
- Weighted-vote chance adjustment, clipping, exclusion, and tie behavior match the methods contract exactly.
- Weighted Vote excludes workers with fewer than 20 development-gold annotations. Simulator sensitivity levels 5/10/20/50/100 are experimental comparisons and do not alter this production default.

### 4.2 Dawid–Skene internal invariants

**PASS only if:**

- Posterior rows sum to one within `1e-12`.
- Worker confusion-matrix rows sum to one within `1e-12`.
- All reported probabilities are finite and within `[0,1]`.
- Observed-data log likelihood does not decrease by more than `1e-10` between accepted iterations.
- Permuting input row order changes no canonical result beyond `1e-12`.
- Canonically renaming item/worker IDs changes no numeric result after inverse mapping.
- Perfect, adversarial, sparse, disconnected, absent-class, and single-observation fixtures follow the registered eligibility/failure rules.
- Convergence, maximum-iteration, numeric-failure, and ineligible-component statuses are distinguishable.

## 5. G4 — Reference parity

Reference parity uses the pinned Crowd-Kit implementation and environment recorded in the benchmark manifest.

**PASS only if:**

- On fixed parity fixtures, maximum absolute posterior-probability difference is `<= 1e-3` and worker-confusion mean absolute error is `<= 1e-3`, after documented class/worker alignment.
- On eligible held-out items from the selected licensed requirements-annotation dataset, `ds_v4` versus `ds_ref` hard-label agreement is `>= 99%` and absolute gold-accuracy difference is `<= 0.002`.
- Every mismatch is retained in a parity artifact with inputs and both outputs.
- The implementation does not call Crowd-Kit internally or copy its result into the DataQual result.
- Smoothing/initialization differences are documented; tolerance is not widened after reporting data are opened.

Failure blocks the DS feature and any DS-derived ERV release claim. MV and descriptive analytics may not be rebranded as full v4 to bypass this gate.

## 6. G5 — Uncertainty and calibration validity

**PASS only if:**

- Entropy, normalized entropy, margin, consensus confidence, Brier score, and ECE follow `METHODS_CONTRACT.md` fixtures.
- Calibration is computed only where gold truth and a predictive distribution are present.
- Ambiguous/distributional-truth items are excluded from single-label calibration or evaluated by a separately labelled distributional rule.
- Confidence intervals display method, unit of resampling, replicate count, seed, confidence level, and eligible denominator.
- A monotonic synthetic fixture shows higher entropy and lower margin as the top probabilities approach a tie.
- The UI never transforms missing uncertainty into zero confidence or 100% confidence.

No minimum real-world calibration performance is a release gate; reporting honest poor calibration is preferable to tuning against locked evaluation data.

## 7. G6 — Reproducibility

**PASS only if:**

1. Starting from a clean checkout and the documented supported Python/Node versions, dependency installation and all tests succeed using locked dependencies.
2. Two complete benchmark runs on the same machine and environment produce byte-identical canonical Parquet/JSON outputs after excluding explicitly volatile manifest fields (`run_id`, path, start/end time). Sort order and float serialization are canonical.
3. A run on a second supported machine produces identical discrete outputs and numeric values within absolute `1e-10` for deterministic descriptive methods and `1e-8` for iterative DS values.
4. Each artifact can be traced to source checksum, configuration, schema/protocol version, algorithm version, seed, and Git commit.
5. A dirty working tree is recorded and disqualifies a release benchmark run.

The lock files are committed. Floating dependency ranges, unrecorded notebooks, or manual UI-only benchmark steps are FAIL.

## 8. G7 — Benchmark validity and leakage prevention

**PASS only if every requirement in Section 11 of `BENCHMARK_PROTOCOL.md` passes, plus:**

- An automated leakage test proves evaluation-gold columns are absent from fitting and queue-construction inputs.
- The deterministic selected-external-dataset split has no item overlap; worker overlap is reported rather than prohibited.
- Raw-data hash, authoritative source, license, citation, and split algorithm are recorded.
- All registered simulator scenarios, reporting seeds, algorithms, baselines, coverage values, failures, and negative results appear in the generated report.
- Paired comparisons share the same item set and review candidate pool.
- An independent rerun from the manifest reproduces the reported summary.
- A signed protocol checklist states that reporting results were not used for tuning.

Any opened evaluation data before the freeze is FAIL and requires a new split or external dataset.

Release benchmark coverage is tiered: deterministic simulator, analytical fixtures, and reference-parity fixtures establish core correctness; the explicitly licensed requirements-annotation dataset is required external validation for MV/DS only. Weighted Vote, ambiguity diagnostics, and review prioritization must pass their registered simulator evaluations. Real-data claims for those method-specific capabilities are prohibited unless a separately valid target and sufficient evidence coverage are pre-registered.

## 9. G8 — Simulator validity

**PASS only if:**

- Identical configuration and seed produce byte-identical canonical events and hidden truth.
- A changed operation sub-seed changes only its registered stochastic operation.
- Generated events satisfy the canonical data schema.
- Empirical class, assignment, missingness, and worker-confusion frequencies converge toward configured values in a large diagnostic run; each absolute frequency error is `<= 0.01` for probabilities `>= 0.05`, with rare-event checks using registered binomial intervals.
- Perfect, adversarial, class-confusion, ambiguity, correlated-worker, sparse, disconnected, and missing-not-random mechanisms are each isolated by targeted property tests.
- Aggregation code cannot import or access simulator truth artifacts.
- The UI labels simulator results as simulated and never mixes them with imported project evidence.

## 10. G9 — UI truthfulness and API consistency

**PASS only if:**

- Every displayed statistic is returned by a versioned API response with method ID, status, denominator, eligibility, and provenance.
- Loading, empty, undefined, ineligible, partial-coverage, non-converged, failed, and successful states have distinct UI fixtures.
- The frontend performs formatting and presentation only; it contains no parallel implementation of agreement, reliability, consensus, flags, calibration, or ERV.
- Displayed rounded values remain consistent with downloadable full-precision artifacts.
- Heuristics use “probable”/“priority” language and never assert proven defects, bad workers, or ground truth.
- Benchmark and simulator pages expose assumptions, coverage, failures, and negative results.
- Contract tests validate TypeScript API consumers against the generated OpenAPI schema.
- No mock/random/fallback metric appears in a production build.

Required browser flows: import/validation failure, successful project creation, overview, annotator evidence, consensus comparison, disputed-item review, adjudication with audit trail, benchmark result, and export.

## 11. G10 — Operational usefulness

This gate tests whether the release workflow is usable, not whether ERV wins every benchmark.

**PASS only if:**

- A user can import a canonical or supported source file, resolve validation errors, create a project snapshot, view evidence, open a prioritized queue, record adjudication, and export results without database editing or scripts.
- On a locked seeded fixture with known correctable errors, each queue strategy returns a deterministic, unique, eligibility-valid ordering and identical budget sizes.
- Review actions are append-only, auditable, and reflected in a new derived snapshot; original annotations and prior consensus remain recoverable.
- The benchmark reports ERV against random, entropy, lowest confidence, and lowest worker reliability at every registered budget.
- At least one non-random registered strategy must exceed the mean random baseline in error recall at 5% budget on at least one non-perfect locked scenario, with a positive paired interval lower bound. This establishes that prioritization can be operationally informative, not that ERV is universally superior.
- If ERV does not outperform a simpler baseline, the UI and report describe it as experimental and do not claim superiority.

## 12. G11 — Reliability, security, and failure behavior

**PASS only if:**

- API inputs enforce file-size, row-count, content-type, schema, and path-safety limits documented for the local/single-tenant release.
- Uploaded filenames cannot escape managed storage paths; archives and executable uploads are rejected unless explicitly supported.
- SQL identifiers and values are parameterized or mapped through safe internal names.
- Formula injection is neutralized in CSV exports for cells beginning with `=`, `+`, `-`, or `@`.
- Malformed input, unavailable artifacts, cancelled jobs, and computation failures return structured errors without stack traces or partial success claims.
- Concurrent reads never observe a partially committed snapshot.
- Secrets, tokens, raw local filesystem paths, and private source rows do not appear in logs or browser payloads beyond authorized project data.
- Dependency and secret scans have no unresolved critical/high findings. A lower-severity exception requires a written rationale.

Authentication, multi-tenancy, and internet-scale abuse resistance are outside release-one scope; deployment documentation must say the release is not a public multi-tenant service.

## 13. G12 — Performance budgets

Measured on the documented reference machine with warm-up excluded and inputs pre-generated:

- One-million-row canonical CSV validation plus snapshot creation: no crash, no row loss, peak RSS `<= 4 GB`, elapsed time recorded.
- Overview queries over one million events: p95 server execution `<= 2 s` over 20 deterministic queries.
- Pagination/filter requests: p95 server execution `<= 1 s` over 20 requests; no unbounded full-table browser payload.
- Initial production UI JavaScript transfer (compressed): `<= 500 KB`, excluding lazy-loaded visualization chunks; exact build report retained.
- A 2,000-item/40-worker/3-class DS default-scenario run: `<= 60 s`, peak RSS `<= 2 GB`, convergence status reported.

These are reference budgets, not universal latency claims. Exceeding one is FAIL until optimized or the budget is revised before evaluation with evidence.

## 14. G13 — Test coverage and quality

**PASS only if:**

- Backend statistical/core domain modules: `>= 95%` line and `>= 90%` branch coverage.
- Backend overall: `>= 90%` line and `>= 85%` branch coverage.
- Frontend application: `>= 85%` line and `>= 80%` branch coverage, excluding generated API types.
- Every methods-contract formula has at least one exact fixture, one edge-case fixture, and one property/invariant test where applicable.
- Every previously fixed correctness defect has a regression test.
- Integration tests use real DuckDB/Parquet artifacts, not only mocks.
- End-to-end tests cover all browser flows in G9 at desktop and mobile viewports.
- Mutation testing on backend statistical modules reaches `>= 80%` mutation score, excluding documented equivalent mutants.
- The complete test suite passes twice consecutively under the locked environment with no order dependency.

Coverage without required behavioral tests is FAIL even if numeric thresholds pass.

## 15. G14 — Accessibility and responsive behavior

**PASS only if:**

- Automated accessibility scans report zero critical or serious violations on every primary route and modal state.
- All workflows are keyboard-operable with visible focus, logical order, escape behavior, and focus restoration.
- Text and interactive contrast meet WCAG 2.2 AA; charts use more than color alone.
- Tables expose headers/captions and provide a non-visual equivalent for charted values.
- Dynamic computation/status changes use appropriate live-region behavior without excessive announcements.
- At `360×800`, `768×1024`, and `1440×900`, no essential control or data is clipped, overlapped, or horizontally inaccessible.
- Reduced-motion preference removes non-essential animation.
- Screen-reader smoke tests complete import, project overview, disputed-item review, and export flows.

## 16. G15 — Documentation and claim discipline

**PASS only if:**

- README provides purpose, supported scope, setup, local run, tests, benchmark reproduction, data privacy, and limitations.
- Canonical schema, API/OpenAPI, methods contract, benchmark protocol, simulator configuration, data migration, and architecture documents match the implementation.
- Every reported number can be regenerated from a committed command and immutable input manifest.
- Vetted-library use, from-scratch implementations, heuristics, and simulated behavior are clearly separated.
- Claims avoid “research-grade,” “production-grade,” “proven,” “optimal,” or universal superiority unless separately supported by evidence outside this acceptance contract.
- Deferred features remain documented as deferred, not “coming soon” promises.
- The selected requirements-annotation dataset's CC BY 4.0 attribution, source, and checksum obligations are satisfied.
- `relevance-2` remains excluded from release/public artifacts while its dataset license is unresolved; its historical manifest must not be presented as permission to use or redistribute it.

## 17. Required release evidence bundle

A release candidate must contain or link to:

1. Gate summary with all G1–G15 PASS.
2. Clean commit ID, dependency locks, build metadata, and environment manifest.
3. Raw-input and benchmark checksums where redistribution is allowed.
4. Unit, property, integration, contract, end-to-end, accessibility, security, coverage, and mutation reports.
5. DS parity report and mismatch artifact.
6. Full benchmark report, manifests, failures, predictions, worker estimates, and review queues.
7. Migration/restore test evidence.
8. Performance report with reference-machine specification.
9. Known limitations and unresolved empirical findings.

## 18. Stop-ship conditions

Regardless of other results, release is blocked by any of the following:

- Evaluation leakage or post-evaluation tuning
- Silent data loss, partial import commit, or raw-source mutation
- Fabricated/fallback/random production metrics
- DS reference-parity failure while DS is exposed
- Non-deterministic canonical outputs under a fixed seed/environment
- Hidden failed benchmark runs or omitted negative scenarios
- A UI claim that overstates heuristic, simulated, or non-gold evidence
- Unresolved critical/high security finding
- Missing dataset license/source/checksum
- Any mandatory gate marked FAIL, skipped, or “not tested”
