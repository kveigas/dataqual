# DataQual v4 Phase 0 Verification Report

Verification date: **2026-08-09**  
Scope: environment, dataset, reference implementations, dependencies, licenses, reproducibility assumptions, and architecture feasibility only

No production application, statistical engine, frontend screen, or v3 modification was created during Phase 0.

## Executive result

**PHASE 0: FAIL**

The technical architecture is feasible and the Python 3.12/Crowd-Kit path works. Phase 0 nevertheless fails its stated purpose of removing benchmark and licensing uncertainty because:

1. no explicit redistribution or usage license was found for the `relevance-2` dataset; and
2. the approved deterministic development split leaves only six workers eligible under the locked minimum-20-gold weighted-vote rule, covering only 496 of 7,994 evaluation items.

Neither problem should be concealed by committing the raw data, assuming Crowd-Kit's software license applies to it, lowering the gold threshold after inspecting results, or reporting weighted-vote results on a non-representative 6.20% subset without prominent qualification.

**READY TO BEGIN PHASE 1: NO**

Before Phase 1, obtain explicit dataset terms or approve a licensed replacement, and formally resolve weighted-vote benchmark coverage through the existing planning change-control process. The implementation stack itself does not need redesign.

## Required summary

### ENVIRONMENT VERIFIED:

**YES.** Python 3.12.13 on Windows 11 installed the complete tested stack, passed `pip check`, imported the required modules, and executed the required reference methods. Node 24.12.0 and the pinned frontend/tooling probe also passed. Python 3.11 was not tested because no Python 3.12 compatibility problem occurred.

### RELEVANCE-2 VERIFIED:

**TECHNICALLY YES; LEGALLY NO.**

- Official Crowd-Kit 1.4.2 loader: `crowdkit.datasets._loaders.load_relevance2`
- Loader source: `crowdkit/datasets/_loaders.py`
- Loader archive URL: `https://tlk.s3.yandex.net/dataset/crowd-kit/relevance-2.zip`
- Upstream checksum URL: `https://tlk.s3.yandex.net/dataset/crowd-kit/relevance-2.md5`
- Source description: anonymized binary relevance labels collected in Yandex's Relevance 2 Gradations project in 2016
- Raw annotation schema: `performer`, `task`, `label`
- Crowd-Kit annotation schema: `worker`, `task`, `label`
- Ground-truth schema: raw `task`, `label`; loader returns a Series indexed by `task`, named `true_label`
- Labels: integers `0` and `1`
- Annotations: 475,536
- Items: 99,319
- Workers: 7,138
- Gold items: 10,079
- Null fields: none in either CSV
- Duplicate worker/item pairs: none
- Item annotation coverage: 1–5 annotations; 87,431 items have five and 11,888 have fewer
- Worker/item graph: three connected components—99,301 items/7,131 workers; 10/2; and 8/5

The complete observed schema, hashes, row counts, missingness, overlap, and split results are in `datasets/manifests/relevance_2.yaml`.

### DATASET LICENSE:

**UNVERIFIED.** Crowd-Kit is Apache-2.0 software, but its relevance-2 loader entry does not state a dataset license. The downloaded ZIP contains only `crowd_labels.csv` and `gt.csv`; it contains no license, README, citation, or terms file. Dataset-specific citation requirements are also not stated.

Policy: do not commit or redistribute the raw ZIP/CSVs. Retain only the downloader, manifest, and hashes until Toloka/Yandex supplies explicit terms.

### DATASET CHECKSUM:

- Archive MD5: `a39c3c30d9e946eeb80ca39954c96e95`—matches the official checksum endpoint
- Archive SHA-256: `0d8b5c4ffdb042cc1435ac20933bcf3218310e0bcc6dd27baef5bcfe64973bef`
- `crowd_labels.csv` SHA-256: `7dea85d1fe7a7a0adc5aef6267d6386aec6a632152d2960a6b48fa984aafa27c`
- `gt.csv` SHA-256: `f3e69c1cd3809bc929b720f995bdd072ea69a06bdfefcf71336e33716b4693f5`

### CROWD-KIT VERSION:

**1.4.2**, the newest release identified on official PyPI and tested here. Official release commit: `cad794bb64686fdd9868ce0ab1282ef61b639c7f`.

Required callability results on a generated binary fixture:

| Method | Result | Notes |
|---|---|---|
| MajorityVote | PASS | Produced deterministic labels |
| DawidSkene | PASS | Labels, probabilities, priors, worker errors, and loss history exposed |
| GLAD | PASS | Compatibility only; remains deferred from production scope |
| MACE | PASS | Compatibility only; remains deferred from production scope |
| `load_dataset('relevance-2')` | PASS | Loaded 475,536 annotations and 10,079 gold rows |

No method emitted a runtime warning on the fixture. `pip check` reported no broken requirements. Installation produced network-speed warnings only, not dependency-conflict warnings.

### SUPPORTED PYTHON VERSION:

**Python 3.12.13.** Verified with Crowd-Kit 1.4.2, NumPy 2.5.1, pandas 3.0.5, SciPy 1.18.0, scikit-learn 1.9.0, and the complete Phase 0 dependency set. Python 3.11 fallback testing was unnecessary under the requested rule.

### DAWID-SKENE REFERENCE VERIFIED:

**YES.** The generated eight-item/four-worker fixture used:

- `DawidSkene(n_iter=100, tol=1e-9)`;
- numeric labels ordered `[0, 1]` in observed probability/error outputs;
- 15 exposed loss-history entries before the configured tolerance stopped iteration;
- exposed `labels_`, `probas_`, `errors_`, `priors_`, and `loss_history_`;
- no separately exposed convergence boolean.

Crowd-Kit's constructor defaults are `n_iter=100`, `tol=1e-5`, and `initial_error_strategy=None`. The frozen fixture records inputs, exact expected outputs, configuration, environment versions, and observed iteration history in `tests/reference_fixtures/crowdkit_ds_small.json`. It contains no Crowd-Kit implementation code.

The fixture demonstrates reference behavior; it does not establish the final parity tolerance by itself.

### KRIPPENDORFF REFERENCE VERIFIED:

**YES, with dependency correction required.**

- Standalone `krippendorff` 0.8.2 returned nominal alpha `0.20408163265306123` on the missing-rating fixture, but it is GPL-3.0-or-later and is rejected from normal runtime/test dependencies.
- NLTK 3.10.2 returned the identical alpha on the same observations and is Apache-2.0.
- NLTK is selected as the independent parity reference. DataQual will still implement nominal alpha from scratch under `METHODS_CONTRACT.md`.

### FLEISS REFERENCE VERIFIED:

**YES.** statsmodels 0.14.6 `fleiss_kappa(..., method='fleiss')` was callable and returned `0.33333333333333326` on the fixed complete-item count matrix.

Convention warning: statsmodels accepts an item-by-category count matrix and classical Fleiss kappa assumes constant raters per item. Krippendorff alpha accepts missing and variable ratings. The statistics are not interchangeable.

### DUCKDB/PARQUET PATH VERIFIED:

**YES.** A 10,000-event synthetic path completed:

`CSV -> required-column/null/row validation -> Arrow -> Zstandard Parquet -> DuckDB query -> Arrow table -> JSON-shaped records`

Observed on the reference machine:

- CSV: 1,089,038 bytes
- Parquet: 64,037 bytes
- CSV write: 0.016 s
- CSV validation/read: 0.029 s
- Parquet write: 0.032 s
- DuckDB aggregate query: 0.118 s

These are single-run feasibility observations, not performance guarantees.

### 1M-ROW FEASIBILITY RESULT:

**PASS.** The deterministic spike generated 1,000,000 canonical-like annotation events, 200,000 items, 1,000 workers, and five annotations per item.

| Observation | Result |
|---|---:|
| CSV size | 112,889,040 bytes |
| Annotation Parquet | 6,274,114 bytes |
| Item Parquet | 561,420 bytes |
| Generation | 2.564 s |
| CSV write | 0.317 s |
| CSV read/ingestion | 0.212 s |
| Parquet writes | 1.001 s |
| Peak process RSS observed | 516,329,472 bytes |
| Annotations per worker query | 0.108 s |
| Annotations per item query | 0.052 s |
| Class distribution | 0.014 s |
| Worker/item overlap | 0.173 s |
| Filter one project | 0.016 s |
| Join annotations with items | 0.102 s |

The run used local NVMe storage, one synthetic distribution, one repetition, and an in-memory DuckDB connection. It validates feasibility, not worst-case CSV parsing, concurrency, production latency, or universal throughput.

### DEPENDENCY RISKS:

1. Crowd-Kit brings Transformers/NLTK/Hugging Face dependencies even for categorical methods; isolate it in the research/reference environment.
2. pandas should remain at reference-library boundaries; DuckDB/Arrow should remain the core table path. Polars adds no verified value yet.
3. Recharts requires accessible text/table equivalents and bundle monitoring.
4. Node 24/current frontend versions passed, but Playwright browsers were not installed because no UI exists yet.
5. The pnpm lockfile is valid and a networked fresh install passed. A newly empty offline store was not complete, so fully air-gapped reproducibility is not claimed.
6. Exact wheel availability and floating-point behavior may differ on non-Windows architectures.

### LICENSE RISKS:

1. `relevance-2` license and dataset-specific citation are missing—release blocker.
2. Standalone `krippendorff` is GPL-3.0-or-later—removed from the proposed dependency set in favor of Apache-2.0 NLTK.
3. Apache NOTICE and bundled numerical-library notices must be preserved in packaged distributions.
4. Playwright browser binaries may have additional notices when eventually downloaded.

### ARCHITECTURE CHANGES REQUIRED:

No change is required to React/FastAPI, DuckDB/Parquet/Arrow, canonical ingestion, or from-scratch DS architecture. Four Phase 0 corrections are required before implementation:

1. Maintain separate production and research/reference Python locks. Crowd-Kit must not enter the production runtime merely for parity tests.
2. Select NLTK, not `fast-krippendorff`, as the nominal-alpha parity reference.
3. Keep benchmark raw data in external local storage and acquire it through the checksum-verifying downloader.
4. Formally amend the benchmark plan: use `relevance-2` for MV/DS parity only unless licensing is resolved; do not use its 6.20%-coverage weighted-vote subset as general evidence. Evaluate gold-weighted vote in the deterministic simulator or pre-register a suitably licensed dataset with adequate worker/gold overlap.

The fourth item changes benchmark applicability, not the locked production algorithm scope, and therefore requires explicit planning change control.

### UNRESOLVED BLOCKERS:

1. Written or published `relevance-2` license/redistribution terms.
2. Dataset-specific citation/attribution requirements.
3. Approval of a licensed replacement if those terms cannot be obtained.
4. Approval of the revised weighted-vote benchmark applicability after the real split produced only six eligible workers and 496 covered evaluation items.

## Proposed minimal dependency sets

Exact release versions should be re-locked at Phase 1 start; the versions below are the tested Phase 0 baseline.

### Backend runtime

- FastAPI 0.141.1
- Uvicorn 0.52.1
- Pydantic 2.13.4
- NumPy 2.5.1
- SciPy 1.18.0
- pandas 3.0.5 only at required library boundaries
- DuckDB 1.5.5
- PyArrow 25.0.0
- scikit-learn 1.9.0
- statsmodels 0.14.6
- Typer 0.27.1
- PyYAML 6.0.3

### Research/reference

- Crowd-Kit 1.4.2
- NLTK 3.10.2 for alpha parity
- Hypothesis 6.165.2
- No standalone `krippendorff` package

### Frontend runtime

- React/React DOM 19.2.8
- Vite 8.2.1 and TypeScript 7.0.2 as build dependencies
- TanStack Query 5.101.4
- Zod 4.4.3
- only required Radix primitives, beginning with Dialog 1.1.23 and Tabs 1.1.21
- Recharts 3.10.1 with accessible table/text equivalents

### Testing

- pytest 9.1.1
- pytest-cov 7.1.0
- HTTPX 0.28.1
- Vitest 4.1.10
- Testing Library React 16.3.2 and jest-dom 7.0.0
- Playwright 1.62.1
- axe-core Playwright 4.12.1

### Tooling

- uv 0.12.3
- pnpm 11.16.0
- Ruff 0.16.2
- Pyright 1.1.411
- pre-commit 4.6.1

### Dependency decision rationale

- **pandas versus Polars:** pandas is necessary at Crowd-Kit/statsmodels-compatible boundaries. DuckDB/Arrow already cover the main table path; adding Polars without profiling evidence would create a third dataframe abstraction.
- **Charting:** Recharts was selected for direct React integration, deterministic SVG output, and maintainability. It is conditional on accessible table equivalents and a production bundle check.
- **UI primitives:** use scoped Radix primitives because they provide unstyled accessibility behavior without imposing a broad visual system. Install only components actually used.
- **Pyright versus mypy:** use Pyright for strict, fast editor/CI parity and because no required mypy plugin has been identified. Reconsider only after a concrete typing incompatibility.

## Reproducibility conclusion

The code, versions, commands, hashes, deterministic seed, fixture outputs, and machine specification are recorded. The architecture path is reproducible within the tested environment. Dataset acquisition is byte-verifiable but not legally reproducible in a public repository until usage/redistribution terms are clarified.

