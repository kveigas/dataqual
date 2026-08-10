# DataQual v4 Core Architecture

Status: implementation contract  
Architecture version: `v4-core-1.0`

## 1. Architecture goals

- statistical methods remain independent of the UI and HTTP framework;
- raw input is immutable and every derived table is reproducible;
- frontend displays backend evidence rather than computing research metrics;
- benchmark execution works without launching FastAPI or React;
- analytical and application state have explicit boundaries;
- deferred modules have extension points but no placeholder implementation.

## 2. Technology decisions

### Frontend

- React
- Vite
- TypeScript in strict mode
- TanStack Query for server state
- Zod only for client response validation and form feedback; backend Pydantic schemas remain authoritative
- accessible component primitives
- deterministic charting library
- Vitest, Testing Library, Playwright, and axe-core

### Backend

- Python 3.12, subject to a dependency compatibility spike
- FastAPI
- Pydantic
- Uvicorn
- generated OpenAPI schema

### Analytics and storage

- DuckDB as the analytical query engine
- Parquet as the canonical persisted analytical format
- Arrow as the process/interchange representation
- NumPy and SciPy for numerical methods
- scikit-learn for standard evaluation metrics and calibration references
- statsmodels for vetted statistics such as Fleiss' Kappa when applicable
- Crowd-Kit as the Dawid-Skene parity reference and benchmark dataset adapter

Pandas is confined to Crowd-Kit and library adapters. Polars may be added only if profiling shows a concrete need; it is not a required core dependency because DuckDB and Arrow already cover the principal table operations.

## 3. Repository structure

```text
dataqual-v4/
  README.md
  METHODS.md
  BENCHMARKS.md
  LIMITATIONS.md
  pyproject.toml
  uv.lock
  package.json
  pnpm-lock.yaml
  Dockerfile

  frontend/
    src/
      app/
      api/
      components/
      charts/
      features/
        overview/
        data/
        items/
        annotators/
        consensus/
        review/
        benchmarks/
      types/
      test/
    vite.config.ts

  backend/
    src/dataqual/
      api/
      schemas/
      ingestion/
      storage/
      descriptive/
      agreement/
      aggregation/
      reliability/
      calibration/
      disagreement/
      flags/
      review/
      simulation/
      benchmarks/
      reporting/
      provenance/
    tests/
      unit/
      property/
      parity/
      integration/
      fixtures/

  configs/
    simulations/
    benchmarks/
    review_policies/

  datasets/
    manifests/
    downloaders/
    README.md

  artifacts/
    examples/
    .gitignore

  docs/
    adr/
    architecture/

  v3_reference/
```

## 4. Module boundaries

### `schemas`

Owns canonical Pydantic models, schema versions, label-domain constraints, and serialized result contracts. It contains no database queries or statistical calculations.

### `ingestion`

Owns file identification, raw-byte checksums, CSV/JSON decoding, column mapping, row validation, duplicate detection, relationship validation, import reports, and conversion to canonical Arrow tables.

It never mutates an existing accepted raw import.

### `storage`

Owns immutable raw-import paths, Parquet layouts, DuckDB catalogs/views, transactions, and dataset snapshots. Statistical modules receive typed tables or arrays rather than issuing hidden file writes.

### `descriptive`

Owns counts, coverage, missingness, prevalence, duration summaries, and overlap-graph diagnostics.

### `agreement`

Owns percent agreement, pairwise agreement, nominal Alpha, bootstrap intervals, and applicability checks.

### `aggregation`

Owns Majority Vote, weighted vote, from-scratch Dawid-Skene, and the isolated Crowd-Kit adapter used for parity. It returns `ConsensusResult` objects and diagnostics.

### `reliability`

Owns gold metrics, Beta-Binomial estimates, Dirichlet-smoothed confusion matrices, evidence-strength rules, and typed `AnnotatorEstimate` results.

### `calibration`

Owns Brier score, ECE, calibration bins, and support checks.

### `disagreement`

Owns vote distributions, entropy, vote margin, posterior uncertainty, and evidence features. It does not assign final flags.

### `flags`

Owns deterministic flag rules, thresholds, severity, evidence payloads, support, and recommended actions. All rules are configuration-versioned.

### `review`

Owns baseline rankings, frozen ERV policy, review budgets, review-event outcome evaluation, cumulative recovery curves, and review-efficiency metrics.

### `simulation`

Owns seeded generation of item truth, ambiguity distributions, worker parameters, assignments, labels, and hidden evaluation truth.

### `benchmarks`

Owns dataset adapters, experiment orchestration, pre-registered configurations, seed execution, method comparisons, and artifact assembly. It imports analytics modules directly and never imports FastAPI.

### `reporting`

Owns result tables, plots, Markdown reports, and machine-readable artifact serialization. It does not recompute algorithms.

### `provenance`

Owns commit identity, environment lock hash, dataset/config checksums, timestamps, machine metadata, and run manifests.

### `api`

Maps HTTP requests to application services. It must not contain statistical formulas.

## 5. Frontend/backend boundary

Frontend responsibilities:

- upload interaction and validation feedback;
- project and dataset selection;
- data tables and visualizations;
- explicit loading, error, unavailable, and insufficient-evidence states;
- rendering formulas/method descriptions supplied through metadata;
- triggering analyses and review actions;
- downloading artifacts.

Frontend prohibitions:

- no agreement, consensus, reliability, uncertainty, or benchmark calculation;
- no synthetic fallback metrics;
- no interpretation based only on colors or thresholds hidden in components;
- no algorithm name unless the API result confirms execution and status.

Backend responsibilities:

- schema authority;
- import, preservation, and storage;
- all analytical calculations;
- evidence checks and method eligibility;
- provenance and artifact creation;
- deterministic errors for unsupported inputs.

## 6. API boundaries

Initial route groups:

```text
/api/v1/projects
/api/v1/imports
/api/v1/datasets
/api/v1/analysis/descriptive
/api/v1/analysis/agreement
/api/v1/analysis/annotators
/api/v1/analysis/consensus
/api/v1/analysis/items
/api/v1/flags
/api/v1/review/strategies
/api/v1/review/events
/api/v1/benchmarks/runs
/api/v1/artifacts
```

Long-running benchmark runs are not performed synchronously through a normal request. The CLI is authoritative. The UI reads completed or explicitly queued benchmark artifacts.

Every analysis response includes:

- schema version;
- dataset snapshot ID;
- method name and version;
- method configuration hash;
- execution status;
- support counts;
- warnings;
- provenance reference.

## 7. Storage flow

```text
uploaded bytes
  -> raw/imports/{import_id}/source.ext
  -> sha256 checksum
  -> decoded staging table (memory/temp only)
  -> validation report
  -> accepted canonical Arrow tables
  -> datasets/{snapshot_id}/{entity}.parquet
  -> DuckDB registered views/catalog
  -> analysis result artifacts
```

Rejected imports retain raw bytes and the rejection report unless the user explicitly deletes the import record. Reprocessing produces a new import attempt and never overwrites the earlier record.

## 8. Analytical snapshot rule

An analysis always references an immutable dataset snapshot. New review events or accepted reannotations create a new snapshot. Existing benchmark results remain tied to the earlier snapshot checksum.

No query may mix tables from different snapshot IDs.

## 9. Benchmark execution flow

```text
CLI config path
  -> config schema validation
  -> dataset manifest + checksum validation
  -> environment/provenance capture
  -> deterministic dataset/split loading
  -> algorithms called from analytics modules
  -> per-seed raw results
  -> aggregate metrics + uncertainty
  -> acceptance/failure evaluation
  -> immutable artifact directory
```

Command target:

```text
dataqual benchmark run configs/benchmarks/core.yaml
```

The command must work with no frontend build and no FastAPI process.

## 10. Artifact flow

Each run writes:

```text
artifacts/{run_id}/
  config.yaml
  manifest.json
  environment.json
  metrics.csv
  seed_metrics.csv
  per_item_predictions.parquet
  per_worker_estimates.parquet
  review_rankings.parquet
  plots/
  report.md
```

Artifacts are write-once. Re-running the same configuration creates a new run ID; the manifest records whether input/config hashes match a prior run.

## 11. Provenance flow

Provenance is created at import, dataset snapshot, analysis, and benchmark-run boundaries.

Minimum fields:

- Git commit hash and dirty-tree indicator;
- dependency-lock checksum;
- schema and method versions;
- dataset and source checksums;
- configuration checksum;
- ordered seed list;
- UTC timestamps;
- Python and operating-system versions;
- CPU architecture;
- benchmark command.

User-supplied personal metadata is not copied into public benchmark manifests.

## 12. Failure isolation

- An invalid import cannot create an analytical snapshot.
- One failed method does not erase successful results from other methods.
- An ineligible method returns `status = unavailable` with reason codes.
- A failed benchmark seed remains visible; it is not silently dropped.
- Partial benchmark runs cannot receive a PASS status.

## 13. Deferred drift extension point

Timestamp fields and ordered-event query interfaces are retained. A future `drift/` module may consume immutable annotation sequences and emit versioned flags. The core release contains no drift implementation, API route, UI entry, or metric.

## 14. Architecture prohibitions

- statistical algorithms inside React components;
- algorithm formulas inside API route handlers;
- benchmark code that depends on HTTP calls to the local app;
- mutable benchmark datasets;
- raw analytical events stored only in SQLite or UI state;
- importing Crowd-Kit directly throughout the codebase instead of through one adapter;
- runtime fallback to fake/demo values after an analytical failure;
- hidden conversions between dataset snapshots.
