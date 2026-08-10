# DataQual v4 Phase 0B Dataset Selection Report

Status: **verified selection evidence**  
Date: **2026-08-09**  
Rule: only author/institutional releases with explicit dataset terms are legally usable

## Decision

The release-one real external MV/DS dataset is **Crowd-Annotation Results: Identifying and Classifying User Requirements in Online Feedback**, Phase 3 ordinary-item subset. Its author-published [Zenodo record](https://zenodo.org/records/3626185) is CC BY 4.0 and cites the REFSQ 2020 paper. The selected conversion supplies stable item IDs, anonymized worker IDs, five categorical classes, approximately six judgments per item, independent researcher reference labels for 447/448 items, substantial disagreement, and a connected worker-item graph.

This selection is bounded. It validates that MV and DS can be run and evaluated on one licensed real categorical dataset. It does not validate weighted vote, ambiguity classification, review prioritization, or universal DS superiority.

## Candidate audit

### 1. Requirements annotation corpus — selected core dataset

| Field | Verified value |
|---|---|
| dataset | Crowd-Annotation Results: Identifying and Classifying User Requirements in Online Feedback, Phase 3 |
| authoritative_source | [Author-published Zenodo record 3626185](https://zenodo.org/records/3626185), DOI `10.5281/zenodo.3626185` |
| paper | van Vliet, Groen, Dalpiaz, Brinkkemper, “Identifying and Classifying User Requirements in Online Feedback via Crowdsourcing,” REFSQ 2020, pp. 143–159 ([proceedings](https://link.springer.com/book/10.1007/978-3-030-44429-7)) |
| license | CC BY 4.0 |
| license_scope | Zenodo dataset record and attached archive; underlying app-review text can retain third-party interests, so raw text is not committed |
| items | 448 ordinary Phase 3 items after excluding platform test questions |
| annotations | 2,674 after removing 27 exact duplicate exports |
| workers | 121 anonymized worker IDs |
| classes | 5: feature, none, performance, quality, stability |
| worker_ids | Yes, `_worker_id` |
| gold_labels | Independent researcher Golden workbook; 447/448 selected items matched by normalized review text |
| per_annotation_records | Yes, one Figure Eight export row per judgment |
| missingness | Sparse worker-item matrix; 5–6 labels/item; 100% items have >=3; one item lacks matched gold |
| download_method | Phase 0B Zenodo API downloader; archive MD5 and SHA-256 verified |
| redistribution_allowed | Yes with CC BY conditions; repository policy still excludes raw feedback text |
| attribution_required | Yes |
| DS_suitable | **Yes**: categorical, connected, sparse, multi-annotation, gold-scored |
| worker_reliability_suitable | Partly: structurally suitable, but only 3–30 ordinary annotations/worker and gold-derived per-worker evidence requires a leakage-safe design |
| weighted_vote_suitable | **No for required release evidence**: historical development-gold support per worker is not established at the fixed 20-event rule |
| ambiguity_suitable | No validated ambiguity target; disagreement alone is not ambiguity truth |
| review_prioritization_suitable | No observed review outcomes/correctability target for a release claim |
| risks | Modest domain/size; researcher gold is not infallible; text join and exact-deduplication rules must remain frozen; class imbalance |

### 2. Crowd4SDG earthquake damage assessment — licensed secondary

| Field | Verified value |
|---|---|
| dataset | Crowd4SDG — Crowdsourced image classification and damage assessment |
| authoritative_source | [Zenodo record 5535744](https://zenodo.org/records/5535744), DOI `10.5281/zenodo.5535744` |
| paper | Shankar et al., related article DOI `10.3390/math9080875` |
| license | CC BY 4.0 |
| license_scope | Zenodo dataset files; source social-media imagery/text can carry third-party rights, so raw redistribution is avoided |
| items | 907 MTurk items |
| annotations | 9,070 |
| workers | 171 |
| classes | 5 damage/relevance classes |
| worker_ids | Yes in MTurk table |
| gold_labels | Expert file exists for 907 tasks, but no shared task/media ID links it to MTurk items |
| per_annotation_records | Yes |
| missingness | Exactly 10 labels/item; sparse across workers |
| download_method | Zenodo API; each published MD5 plus SHA-256 verified |
| redistribution_allowed | CC BY permits it, subject to attribution and third-party-content caution |
| attribution_required | Yes |
| DS_suitable | Structurally yes; evaluative suitability limited by non-joinable expert references |
| worker_reliability_suitable | Structurally yes, but no mapped independent gold |
| weighted_vote_suitable | No defensible development-gold stream without a verified expert join |
| ambiguity_suitable | No validated ambiguity target |
| review_prioritization_suitable | No known review outcome/correctability target |
| risks | Any order-based expert join would be invented and is prohibited; disaster/social-media content rights |

### 3. CrowdTruth Open Domain Relation Extraction — licensed secondary

| Field | Verified value |
|---|---|
| dataset | CrowdTruth Corpus for Open Domain Relation Extraction from Sentences |
| authoritative_source | [Zenodo record 1472330](https://zenodo.org/records/1472330), DOI `10.5281/zenodo.1472330` |
| paper | Dumitrache, Aroyo, Welty, “Crowdsourcing Semantic Label Propagation in Relation Classification,” FEVER/EMNLP 2018, arXiv `1809.00537` |
| license | CC BY-SA 4.0 |
| license_scope | Zenodo corpus archive; share-alike/attribution apply; source sentences have upstream provenance |
| items | 4,101 source units; 69,717 binary propositions after transparent relation expansion |
| annotations | 1,046,044 binary proposition judgments |
| workers | 711 |
| classes | Binary per relation proposition, expanded from 17 selectable relations including `none` |
| worker_ids | Yes |
| gold_labels | `input.relation` is distant-supervision provenance, not independent expert gold |
| per_annotation_records | Yes; worker-level 17-column indicator rows |
| missingness | 14–16 workers/proposition; two graph components |
| download_method | Zenodo API; published MD5 and SHA-256 verified |
| redistribution_allowed | Yes under CC BY-SA 4.0, with attribution/share-alike and upstream-content caution |
| attribution_required | Yes; share-alike also required for adaptations |
| DS_suitable | Technically suitable after binary expansion; not selected because the target is multilabel and external “gold” is noisy provenance |
| worker_reliability_suitable | Structurally suitable; truth-based accuracy is not independently identified |
| weighted_vote_suitable | No independent historical-gold stream |
| ambiguity_suitable | Research-relevant disagreement, but not a simple validated ambiguity class target |
| review_prioritization_suitable | No known correction/review outcomes for the DataQual endpoint |
| risks | 92.6% negative event imbalance after expansion; transformation changes the task; sentence provenance; two components |

### 4. Crowd Deliberation — licensed but too small for core DS validation

| Field | Verified value |
|---|---|
| dataset | Crowd Deliberation official dataset |
| authoritative_source | [Official repository](https://github.com/crowd-deliberation/data) |
| paper | Repository is the authoritative companion release; citation must follow its linked study documentation |
| license | MIT |
| license_scope | Root repository data and documentation; no narrower exception displayed |
| items | 80 texts: 40 sarcasm, 40 relation extraction |
| annotations | Individual rows are published in `labels.csv`; not advanced to the top-three execution audit |
| workers | Stable `ANNOTATOR_ID` is published; exact count not advanced to execution audit |
| classes | Two binary domains |
| worker_ids | Yes |
| gold_labels | Only first 25 relation cases have ground truth |
| per_annotation_records | Yes |
| missingness | Sparse; deliberations contain three-member subsets |
| download_method | Git clone/raw files from official repository |
| redistribution_allowed | Yes under MIT, with notice |
| attribution_required | Preserve license/copyright notice |
| DS_suitable | Technically possible, but 80 items and only 25 gold cases are too small for the core external gate |
| worker_reliability_suitable | Limited by small evidence volume |
| weighted_vote_suitable | Not suitable at the fixed 20-development-gold rule |
| ambiguity_suitable | Potentially useful later because deliberation outcomes exist, but requires a separate target contract |
| review_prioritization_suitable | Potentially useful later; not a ready-made correctable-error endpoint |
| risks | Tiny, mixed domains, deliberation changes labels, limited gold |

### 5. CIFAR-10H — rejected for licensing

| Field | Verified value |
|---|---|
| dataset | CIFAR-10H |
| authoritative_source | Author repository `jcpeterson/cifar-10h`; [ICCV paper](https://openaccess.thecvf.com/content_ICCV_2019/html/Peterson_Human_Uncertainty_Makes_Classification_More_Robust_ICCV_2019_paper.html) |
| paper | Peterson et al., ICCV 2019 |
| license | **No explicit dataset license verified from the author release** |
| license_scope | Unresolved; public availability is not a redistribution/use license |
| items | 10,000 |
| annotations | More than 500,000 per the paper |
| workers | Worker-level judgments are described, but not audited further after license rejection |
| classes | 10 |
| worker_ids | Present in the release design; not relied on |
| gold_labels | CIFAR-10 reference labels |
| per_annotation_records | Available in author release design |
| missingness | Not audited after legal rejection |
| download_method | Would be author repository only |
| redistribution_allowed | **No** on current evidence |
| attribution_required | Citation expected, but citation does not cure missing license |
| DS_suitable | Technically promising; legally ineligible |
| worker_reliability_suitable | Technically promising; legally ineligible |
| weighted_vote_suitable | Not assessed after legal rejection |
| ambiguity_suitable | Strong distributional-label research candidate; legally ineligible |
| review_prioritization_suitable | No known review outcomes |
| risks | Ambiguous data rights; underlying CIFAR terms; must not use a mirror's license as a substitute |

### 6. CIFAR-10N — possible secondary only

| Field | Verified value |
|---|---|
| dataset | CIFAR-10N official UCSC-REAL release |
| authoritative_source | [UCSC-REAL repository](https://github.com/UCSC-REAL/cifar-10-100n); ICLR 2022 paper on OpenReview |
| paper | Wei et al., “Learning with Noisy Labels Revisited,” ICLR 2022 |
| license | CC BY-NC 4.0 |
| license_scope | Root license plus README identifying the repository as the official dataset release; no narrower file exception found; non-commercial restriction applies |
| items | 50,000 CIFAR-10 training items |
| annotations | Three 50,000-label arrays plus aggregate/worst derivatives |
| workers | 747 encrypted IDs across three side-info worker slots |
| classes | 10 |
| worker_ids | Batch-level `Worker1-id..Worker3-id` |
| gold_labels | `clean_label` array |
| per_annotation_records | Potentially reconstructable, but slot mapping is not explicitly guaranteed by the official README |
| missingness | Three label arrays/item; assignment information is grouped in 5,000 ten-image batches |
| download_method | Official raw repository files; hashes recorded in Phase 0B result artifact |
| redistribution_allowed | Non-commercial redistribution only with attribution; do not bundle in a general release artifact |
| attribution_required | Yes |
| DS_suitable | Potentially, only after authoritative confirmation that `random_labelN` maps to `WorkerN` per batch |
| worker_reliability_suitable | Same mapping blocker; timing is batch-level, not per annotation |
| weighted_vote_suitable | Potentially after mapping verification and a leakage-safe gold split; not required now |
| ambiguity_suitable | Useful as label-distribution/noise evidence, not validated semantic ambiguity truth |
| review_prioritization_suitable | No review-outcome/correctability target |
| risks | CC BY-NC limits use; worker-label slot mapping is inferred rather than explicitly documented; underlying CIFAR rights; only three labels/item |

### 7. `relevance-2` — rejected historical candidate

| Field | Verified value |
|---|---|
| dataset | Crowd-Kit `relevance-2` |
| authoritative_source | Crowd-Kit loader and Yandex-hosted archive; evidence retained in `datasets/manifests/relevance_2.yaml` |
| paper | Crowd-Kit JOSS paper is software citation, not dataset-specific rights evidence |
| license | **Unresolved** |
| license_scope | Crowd-Kit Apache-2.0 applies to software, not the dataset |
| items | 99,319 annotation items |
| annotations | 475,536 |
| workers | 7,138 |
| classes | 2 |
| worker_ids | Yes |
| gold_labels | 10,079 items |
| per_annotation_records | Yes |
| missingness | 1–5 labels/item; three components |
| download_method | Historical isolated downloader with MD5/SHA-256 verification |
| redistribution_allowed | No on current evidence |
| attribution_required | Dataset-specific requirement unresolved |
| DS_suitable | Technically yes, legally ineligible for release use |
| worker_reliability_suitable | Limited by gold overlap |
| weighted_vote_suitable | No: fixed threshold yields six eligible workers and 6.20% evaluation-item coverage |
| ambiguity_suitable | No validated ambiguity target |
| review_prioritization_suitable | No valid review-outcome target |
| risks | Unlicensed; inadequate WV coverage; public artifact prohibited |

## Top-three execution results

| Dataset/conversion | Items | Events | Workers | Labels/item | Graph | >=2 / >=3 | Gold coverage | Mean raw disagreement | Non-unanimous | Crowd-Kit MV / DS |
|---|---:|---:|---:|---|---|---|---:|---:|---:|---|
| Requirements Phase 3 ordinary items | 448 | 2,674 | 121 | min 5, median 6, max 6 | 1 component | 100% / 100% | 99.78% | 0.3554 | 88.17% | PASS / PASS; accuracy 0.6622 / 0.6331; macro-F1 0.6302 / 0.6094 |
| Crowd4SDG MTurk | 907 | 9,070 | 171 | exactly 10 | 1 component | 100% / 100% | 0% joinable | 0.2925 | 90.52% | PASS / PASS; no defensible gold score |
| CrowdTruth ORE binary expansion | 69,717 | 1,046,044 | 711 | median 15 | 2 components | 100% / 100% | 100% proxy only | 0.0436 | 23.78% | PASS / PASS on deterministic 200-unit smoke; scores against distant-supervision relation are not gold validation |

`raw disagreement` is the item-level mean of `1 - largest observed class share`. Connectivity is computed on the bipartite item-worker graph. The CrowdTruth smoke intentionally used 200 sorted source units (3,400 binary propositions; 51,000 events) to test API/algorithm viability without turning an exploratory adapter into release evidence.

## Acquisition and integrity

| Record | Published checksum | Verified SHA-256 |
|---|---|---|
| Requirements archive | MD5 `44b2f2446d0da3ed319833374d7b725f` | `1538ee6b9a1408fd098c06f0ab8e53a9c1867b9ba9769ccaaa712f0dcd2ec0f2` |
| Crowd4SDG MTurk CSV | MD5 `6deb3b0c61a7c8a0464ee09a73ddab76` | `3eb872460194857c51effbd8a39212ed851fde4814f36a58fcec1315e37c345a` |
| CrowdTruth archive | MD5 `4a2d16d2244c676a8990817ac1184646` | `b668f73874919ec1410902ff972a0a1b71fdc45d092dde30d07c87bbb69f7fe4` |

Raw files were kept under the isolated Phase 0B runtime, not the DataQual repository. Reproduction uses `spikes/phase0b/download_zenodo_candidates.py` and `spikes/phase0b/profile_and_smoke.py`.

## Selection limitations

- The selected smoke check is deliberately negative-friendly: DS did not beat MV. Phase 1 must preserve this result and must not tune against it.
- The conversion has already been inspected; therefore a new locked item split/config version is required before release reporting. The present full-data smoke is development evidence only.
- Matching gold by normalized text is acceptable only with one-to-one uniqueness checks and a frozen normalization implementation.
- No tested real dataset met the fixed historical-gold requirements for mandatory weighted-vote evaluation. That requirement therefore remains simulator-based.
