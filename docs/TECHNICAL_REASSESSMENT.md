# DataQual: technical reassessment and local improvements

Review window: 29–30 September 2026. Starting code: `cdf484c`, the complete v4 RC1 checkout, not the older v3 reference or Downloads Phase 3 snapshot. Changes stayed local for review until their release on 1 October 2026 ([kveigas/dataqual#1](https://github.com/kveigas/dataqual/pull/1)). Existing unrelated portfolio screenshots/scripts were preserved.

## Verdict

The statistical core is worth preserving, but the integration layer did not justify every research claim. In particular, the review queue could display consensus-derived scores without consuming a successful consensus fit. Scientific correctness and evidence transparency take priority over adding more algorithms.

This pass is a tested improvement, not certification that the whole system is production-ready or state of the art. The API, ingestion/storage boundary, consensus/agreement core, diagnostic/ranking/benchmark path, dependency declarations, frontend workflows, and existing tests were examined. No claim of a formal security proof or exhaustive verification of every possible input is made.

## Findings and implemented corrections

| Finding | Correction and evidence |
|---|---|
| Review ranking lacked real DS posterior inputs; uncertainty could collapse to zero | One reference-compatible DS fit per service snapshot; actual item posterior, entropy, fit status and method disagreement propagate into ranking. Regression compares scores to direct fits. |
| Missing DS was conflated with disagreement | Missing evidence is explicitly unavailable, not a claim that two methods disagree. The diagnostic UI does not render an unfitted comparison as “No.” |
| Worker confidence was discarded by the Phase 4/5 API adapter | Preserve observed confidence, use current human/AI-assisted events, and select latest gold versions with their distributions and ancestry. API regression verifies current-event Brier evidence. |
| Demo gold was written after snapshot checksums | Version 2 demo imports gold through normal validated ingestion before publication. Existing snapshots are not rewritten. Artifact hash regression covers the new demo. |
| Review runs disappeared on process restart | Checksummed immutable JSON envelopes, full UUIDs, temp-file publication, restart retrieval and corruption/path-validation tests. This is filesystem persistence, not multi-tenant storage. |
| Gold used for worker reliability also appeared in recovery evaluation | Exclude all development-gold items from the evaluated queue, then rerank. DS remains transductive and unsupervised; hidden truth never enters ranking. |
| Paired intervals used population rather than sample standard deviation | Use `ddof=1`; one seed has no interval rather than a misleading zero-width interval. SciPy is now an explicit runtime dependency. |
| Review queue truncated evidence and obscured score meaning | Full-queue search and server pagination, explicit item/annotation unit, per-candidate votes, score decomposition, worker support, and provenance. Changed controls do not relabel old results. |
| Benchmark requests ran implicitly on control changes | Explicit run action, bounded parameters, no automatic retry, stale-setting notice, uncertainty/synthetic limitations alongside results. |
| Mobile/keyboard gaps | Full-width workspace, collapsible import, bounded queue scrolling, keyboard candidate selection and scrollable tables, wrapping model IDs/details, visible focus, skip link. |
| Git provenance depended on the storage location | New provenance looks at the code location, not the data directory. Prior immutable records remain historical records. |

The preserved core includes canonical schema validation, immutable source events, ingestion diagnostics, agreement/alpha, majority vote, development-gold weighted vote, the from-scratch DS implementation, and its Crowd-Kit parity tests. No estimator weights, simulation scenarios, reference fixtures, or frozen RC1 benchmark files were retuned to obtain a better result.

## Revalidation results and interpretation

Local verification: **120 backend tests passed**, including reference parity; **91.47% backend branch-inclusive coverage**, above the unchanged 90% gate. Frontend: **10 tests passed** and production build succeeded. Python type checking and Ruff checks passed. The frontend test runner must be started from the physical checkout when using a Windows junction; a junction-path setup-resolution failure was rerun successfully there, not hidden by weakening tests.

The first corrected run uses scenarios S1–S12, five paired world seeds 100–104, ranking seeds 2026–2030, annotation review, and `review-evidence-2.0.0`. Each scenario uses its existing registered configuration. Known development-gold items are excluded from recovery evaluation.

Selected mean error recall at a 10% review budget:

| Scenario | Random | Vote entropy | Worker reliability | ERV |
|---|---:|---:|---:|---:|
| S1: homogeneous workers | 9.11% | 58.16% | 7.19% | 58.47% |
| S2: heterogeneous workers | 12.08% | 21.09% | 19.30% | 19.17% |
| S9: correlated workers | 11.73% | 16.58% | 15.74% | 15.17% |
| S12: mixed world | 12.06% | 21.40% | 30.97% | 20.63% |

These are small synthetic revalidation results, not real-world savings or evidence of general superiority. Different rows have different error prevalence. Comparing the largest percentage across scenarios is not a fair method comparison. Paired intervals are exploratory, unadjusted for multiple comparisons, and unreliable as broad research conclusions with only five worlds. Keep negative results. The fixed ERV formula often loses to a simpler baseline; that is a finding, not a reason to tune against held-out scenarios.

Reproduce into a **new** output directory:

```powershell
uv run python scripts/revalidate_review_evidence.py --output artifacts/review-evidence-v2 --seeds 5
uv run pytest --cov=dataqual
pnpm --dir frontend test:unit
pnpm --dir frontend build
```

The local review bundle outside this repository contains all 12 JSON manifests, screenshots, browser checks and a cross-project result index. The runner refuses to overwrite an existing output directory. Historical RC1 real-data parity findings remain historical: passing reference tests preserves the algorithm contract, not a new benchmark claim on every dataset.

## Research-informed direction

1. **Preserve label variation, not just a “correct” label.** Recent research distinguishes plausible human perspectives from annotation noise. This informs the explicit ambiguity cautions and observed vote display; it does not validate DataQual's heuristic flags. A later distributional-evaluation module should be tested on licensed multi-annotator data before training annotator-specific models. [Gruber et al., 2025](https://aclanthology.org/2025.nlperspectives-1.7/), [Yung et al., 2026](https://aclanthology.org/2026.lrec-1.388/).
2. **Vetted numerical references, transparent educational implementations.** Keep the scratch DS/majority-vote/entropy implementations to demonstrate understanding, with differential parity against [Crowd-Kit](https://crowd-kit.readthedocs.io/en/latest/classification/). Use SciPy distributions and intervals instead of hand-written numerical approximations. Agreement with a reference does not imply agreement with truth.
3. **Decision-oriented review UX.** Show the source evidence, model assumptions, missing support and human decision boundary together. A score should support a review, not silently “correct” a minority viewpoint. No LLM adjudicator or opaque generated explanation was added.

## Remaining release and research risks

- **Security:** no claim of user authentication, per-tenant isolation, abuse controls or secure client-data hosting. Do not upload confidential annotation data to the public demo. This pass did not perform a penetration test or complete advisory audit.
- **Deployment persistence:** runs survive application restart only when `DATAQUAL_DATA_ROOT` survives. Ephemeral hosting can still erase the filesystem. A durable-volume/backup/restore drill is required before relying on preservation claims.
- **Resource limits:** analysis caching is process-local and unbounded; expensive requests remain synchronous. Bounded query parameters do not replace job cancellation, rate limits, job deduplication and resource quotas.
- **Diagnostic integration:** the general diagnostic endpoint still does not attach a selected consensus run. It honestly shows unavailable DS evidence; it is not equivalent to the newly fitted review workspace. Version an explicit run-selection API before combining diagnostics from different configurations.
- **Model limitations:** DS assumes conditional independence and an identifiable latent-label structure. Sparse/disconnected graphs, correlated workers, class imbalance and non-convergence remain real limitations. A DS posterior is not a calibrated annotation-error probability.
- **Prioritization limitations:** ERV is a fixed heuristic, not expected monetary value or proven value of information. Item features can repeat across annotations on an item; real review cost, dependence, and duplicate context-reading effort are not modeled.
- **Benchmark validity:** five seeds and small synthetic worlds are not enough. Pre-register larger repetitions and annotation-vs-item objectives; report coverage, non-convergence, no-error worlds, confidence intervals, and all baseline losses. The current item-level benchmark targets simulated ambiguity, not all data defects.
- **Human workflow:** there is still no complete persisted adjudication lifecycle with authenticated reviewer identity, rationale, disagreement resolution and export. Do not confuse “inspect candidates” with a finished labeling platform.
- **Scale:** test millions of events, realistic uploads, concurrent jobs and memory ceilings before scalability claims. Feature extraction still repeats some per-worker calculations.
- **Testing:** preserve the 90% backend coverage gate; full-suite coverage results are reported separately. Automated accessibility scans do not substitute for screen-reader and human task-completion testing.

## Prioritized next increments

1. Release evidence: increase registered seed counts, add an independently licensed multi-annotator dataset, keep all losses and fit failures, publish reproducible manifests.
2. Human review: append-only adjudication events against a pinned snapshot/run, reason codes, unresolved/policy outcomes, review cost and export; keep original annotations immutable.
3. Production boundary: user/tenant ownership, durable storage, backups, idempotent queued jobs, quotas and operational metrics. This requires an explicit hosting/privacy decision.
4. Research extensions only after the above: distribution-aware evaluation and cost-aware acquisition compared against simple baselines. Do not add GLAD/MACE/EBCC/LLM judging merely to expand a methods list.

---

## Addendum — second pass, 30 September – 1 October 2026

Released 1 October 2026 ([kveigas/dataqual#1](https://github.com/kveigas/dataqual/pull/1)).

### Defects found and fixed

| Defect | Fix |
| --- | --- |
| Simulator ignored configured `base_accuracy` for EXPERT/AVERAGE/WEAK workers (fixed 0.95/0.75/0.40), so scenario descriptions such as S1 "0.92" were not what was simulated | Honoured from simulator version 1.1.0. Registered scenarios stay 1.0.0, so RC1/frozen evidence remains bit-identical and reproducible |
| Every review-run request wrote a new file (unbounded disk use on a public API) | Content-addressed run IDs: identical inputs reuse one immutable run (`X-Review-Run-Reused` header); store quota returns 429; corrupted run files return a clear storage error |
| Diagnostics endpoints always reported Dawid–Skene as unavailable | Diagnostics use the same fitted DS evidence as the review queue (flag rules unchanged; they are vote-based) |
| Benchmark endpoint re-simulated every world on each request | Bounded in-process cache (deterministic results) |
| Corrected ranking evidence lived outside the repository | Copied to `docs/evidence/review-ranking-v2/` |

### New: adaptive label collection

`dataqual/collection/adaptive.py`, endpoint `GET /api/v1/datasets/{id}/label-collection-plan`, and a **Label collection** view.
Each item is marked *settled* (posterior ≥ target with at least two labels), *needs more labels* (optimistic count of
further agreeing labels), or *expert review* (still contested at the maximum — often genuine ambiguity). Worker model:
smoothed Dawid–Skene; no gold is used for planning.

An initial version using the unsmoothed reference fit was **overconfident** on small pilots (it stopped after ~1.3 labels
even at a 99% target and lost 5–10 accuracy points). It was replaced before release with the smoothed fit plus a two-label
minimum; the overconfident run was discarded, and this note records why.

Evaluation (`scripts/evaluate_adaptive_collection.py`, S1–S12 at simulator 1.1.0, seeds 100–104, 30% pilot, hidden truth
used only for scoring):

- Registered redundancy (3–5 labels/item), target 95%: **identical accuracy to using every label in all 12 scenarios**, 0–14%
  fewer labels (little to save at this redundancy). Results: `docs/evidence/adaptive-collection/summary.md`.
- Exploratory high redundancy (7–9 labels/item; not a registered design): **25–63% fewer labels, within 0.8 accuracy points**.
  Results: `docs/evidence/adaptive-collection-high-redundancy/summary.md`.
- Side finding: the smoothed DS worker model beats majority vote substantially where workers are adversarial or correlated
  (S4, S9) and in the mixed world (S12).

Limits: synthetic worlds; the simulator does not change label emission for "ambiguous" items; independence assumptions;
the plan's additional-label count is optimistic.

### Verification

Backend 127 tests, 91.52% branch-inclusive coverage (gate 90%), ruff, ruff format, pyright clean. Frontend 12 unit tests,
typecheck, build; Label collection view verified in a browser on the synthetic demo with no console errors.

---

## Addendum — instant public demo, 1 October 2026

**Problem.** The API runs on Render's free tier, which sleeps after 15 minutes idle; a measured cold start took 32 s,
during which a first-time visitor saw only a loading message.

**Design.** The demo dataset is deterministic, so `scripts/build_demo_snapshot.py` imports it during the Pages build with
the same analysis code and stores every response the demo views and controls can request: 57 responses, including every
label-plan and benchmark option and 10 complete review runs, in 3.1 MB. The frontend answers demo requests from this
snapshot (review-queue paging and search are applied client-side exactly as the API does) and wakes the live API in the
background for imports and uploaded datasets, which join the list once it answers.

**Verification.** Tests assert that the snapshot covers every demo view and option, that sampled responses (agreement,
annotators, a label plan) equal a freshly bootstrapped API with identity fields masked, and that the builder's options
match the frontend menus. Backend 131 tests, 92.25% branch-inclusive coverage, Ruff, Ruff
format and Pyright clean; frontend 17 unit tests, typecheck, build. In a browser with the API unreachable, the
workspace rendered in 0.2 s and every view and action responded in under 0.2 s.
