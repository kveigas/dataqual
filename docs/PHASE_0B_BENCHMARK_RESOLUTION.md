# DataQual v4 Phase 0B Benchmark Resolution

Date: **2026-08-09**  
Scope: **benchmark blocker resolution only; no production or Phase 1 code**

## RELEVANCE-2 STATUS:

Removed from mandatory release-one benchmarking. The historical manifest and Phase 0 evidence remain, now explicitly marked:

```yaml
license_status: unresolved
release_benchmark: false
public_artifact_eligible: false
historical_audit_only: true
```

Crowd-Kit's Apache-2.0 software license was not treated as a dataset license. Re-entry requires explicit authoritative dataset terms and change control.

## LICENSED CANDIDATES FOUND:

Three strongest candidates were downloaded and verified from author-published Zenodo records:

1. Requirements annotation corpus — CC BY 4.0.
2. Crowd4SDG earthquake image assessment — CC BY 4.0.
3. CrowdTruth Open Domain Relation Extraction — CC BY-SA 4.0.

Crowd Deliberation (MIT) was also legally usable but too small for the core gate. CIFAR-10N is CC BY-NC 4.0 and remains a possible secondary dataset. CIFAR-10H and `relevance-2` were rejected because explicit dataset rights were not verified from their authoritative releases.

## SELECTED CORE REAL DATASET:

**Crowd-Annotation Results: Identifying and Classifying User Requirements in Online Feedback**, Phase 3 non-test-question subset, Zenodo DOI `10.5281/zenodo.3626185`.

Verified conversion after removing 27 exact duplicate exports: 448 items, 2,674 annotations, 121 workers, five classes, 5–6 labels per item, one connected worker-item component, and researcher reference labels for 447 items. Crowd-Kit 1.4.2 MV and DS both completed on all 448 items.

## SELECTED DATASET LICENSE:

**CC BY 4.0**, stated on the author-published Zenodo dataset record. Attribution is required. Although redistribution is permitted, the repository will not commit the raw archive because it includes third-party app-review text; retrieval and checksums are sufficient for reproducibility.

## SELECTED DATASET CHECKSUM:

- Upstream archive MD5: `44b2f2446d0da3ed319833374d7b725f`
- Verified archive SHA-256: `1538ee6b9a1408fd098c06f0ab8e53a9c1867b9ba9769ccaaa712f0dcd2ec0f2`
- Phase 3 raw CSV SHA-256: `5e7f0ec51e74a8ec7e196123a3e370986396e7c5ed01fbb759f2ca3169102253`
- Phase 3 Golden workbook SHA-256: `d39fbc5357201264589ed3d749500827427498620923dc988a88c13723aee69e`

## SELECTED DATASET DS SUITABILITY:

**Suitable for meaningful external MV/DS validation.** It is categorical, sparse, multi-annotator, connected, nontrivially disputed, and nearly fully matched to independent researcher reference labels. A non-production smoke check passed:

| Method | Accuracy | Macro-F1 |
|---|---:|---:|
| Crowd-Kit MajorityVote | 0.6622 | 0.6302 |
| Crowd-Kit DawidSkene | 0.6331 | 0.6094 |

MV's better smoke result is retained. The selection is not a claim that DS is better, and the inspected data cannot serve as an unopened release split without a new locked split/configuration.

## SELECTED DATASET WORKER-RELIABILITY SUITABILITY:

**Partially suitable.** Worker IDs and overlap support latent DS confusion estimation, but ordinary-item volume is only 3–30 labels per worker and the corpus was not designed as a leakage-safe historical-gold worker evaluation. Any truth-based worker reliability claim needs a pre-registered split and sufficient per-worker support; it is not required to pass the real MV/DS gate.

## WEIGHTED-VOTE BENCHMARK PLAN:

Weighted Vote remains core. Required validation moves to the deterministic simulator and no longer depends on `relevance-2` or any inadequate real gold subset. The production minimum remains 20 development-gold annotations per worker.

The pre-registered sensitivity matrix tests evidence levels 5, 10, 20, 50, and 100 across homogeneous, heterogeneous, one-weak-worker, adversarial, class-specific-error, and sparse-overlap scenarios. Worker ability is generated independently; development and evaluation items are disjoint; worker IDs may span streams; evaluation gold is hidden until scoring. MV, weighted vote, and DS use paired evaluation events. Outputs include eligible-worker fraction, item coverage, accuracy, macro-F1, Brier score where applicable, reliability MAE/rank correlation, and paired bootstrap intervals.

An isolated ten-replicate Phase 0B spike executed the full matrix. At threshold 20, weighted-vote coverage was approximately 0.95–0.99 in five-label scenarios but only 0.154 in sparse overlap. Weighted vote did not beat MV in mean accuracy at threshold 20 in any registered spike scenario; DS helped strongly for adversarial and class-specific errors but did not universally win. The mixed/negative result is retained in `WEIGHTED_VOTE_SENSITIVITY_REPORT.md`. It validates the coverage-risk design and does not change the production threshold.

## CIFAR-10N STATUS:

**Possible secondary human label-noise dataset; not core.** The official UCSC-REAL repository uses CC BY-NC 4.0. The release contains 50,000 clean labels, aggregate/worst labels, three 50,000-label arrays, and 5,000 ten-image side-information rows with three worker IDs/times per batch (747 unique workers).

`random_label1..3` and `Worker1..3` make item-worker reconstruction plausible, and the worst label is always one of the three arrays; however, the official README does not explicitly guarantee slot-wise mapping. Timing is batch-level. DS, worker reliability, and weighted vote remain conditional on authoritative mapping confirmation. Class-specific human label-noise analysis against clean labels is already structurally supported. Non-commercial licensing also makes it a poor default release artifact.

## BENCHMARK PROTOCOL CHANGES:

- Added three benchmark layers: core correctness, required real external MV/DS validation, and method-specific validation.
- Replaced mandatory `relevance-2` use with the licensed requirements corpus for real MV/DS validation.
- Kept analytical fixtures, deterministic simulator stress tests, and pinned Crowd-Kit parity fixtures mandatory.
- Made real weighted-vote validation optional until adequate licensed historical-gold overlap exists; simulator validation remains mandatory.
- Restricted ambiguity claims and review-prioritization claims to simulator truth unless a real dataset exposes a valid target.
- Added the weighted-vote evidence sensitivity design without changing the 20-event default.
- Updated acceptance gates and scope language so one real dataset is not treated as evidence for every capability.

## REMAINING LICENSE RISKS:

- The selected archive contains third-party app-review text; raw data remains outside the public repository despite CC BY 4.0 record terms.
- Crowd4SDG includes social-media content and image references with possible third-party rights.
- CrowdTruth's sentences originate from prior corpora and adaptations inherit CC BY-SA obligations.
- CIFAR-10N is non-commercial and underlying CIFAR rights remain relevant.
- CIFAR-10H and `relevance-2` remain ineligible until explicit data terms are verified.

## REMAINING METHODOLOGICAL RISKS:

- The selected real dataset is small and domain-specific; it cannot establish cross-domain generalization.
- Researcher gold can contain judgment error and does not identify semantic ambiguity.
- The full dataset was inspected during Phase 0B, so release reporting requires a newly frozen deterministic split and strict leakage controls.
- DS assumes conditional worker independence; the selected platform process may violate it.
- Weighted-vote evidence is simulator-primary and therefore demonstrates controlled validity, not field effectiveness.
- Review-prioritization and ambiguity endpoints remain simulator-only until valid real outcomes are available.
- CIFAR-10N worker-slot mapping remains unverified.

## Acceptance decision

1. Release one no longer depends on unlicensed `relevance-2`: **PASS**.
2. An explicitly licensed real dataset suitable for meaningful MV/DS external validation was verified: **PASS**.
3. Weighted-vote evaluation no longer depends on inadequate real-world gold coverage: **PASS**.
4. No evidence threshold, license requirement, or scientific gate was weakened to obtain this result: **PASS**.

**PHASE 0B: PASS**  
**READY TO BEGIN PHASE 1: YES**
