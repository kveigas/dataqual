# DataQual v4 Phase 0 Reference Environment

Recorded: **2026-08-09**  
Purpose: compatibility and architecture-feasibility observations only

Future performance reports must say whether they were collected on this machine. Results from another machine must record its own specification and must not be compared as if hardware were controlled.

## Hardware and operating system

| Property | Observed value |
|---|---|
| Operating system | Microsoft Windows 11 Home |
| OS version | 10.0.26200 |
| Architecture | 64-bit / AMD64 |
| CPU | 12th Gen Intel Core i5-1235U |
| Physical cores | 10 |
| Logical cores | 12 |
| Physical RAM | 8,301,043,712 bytes (approximately 7.73 GiB) |
| Primary disk | SAMSUNG MZAL4512HBLU-00BL2 |
| Disk type | NVMe SSD |
| Disk capacity | 512,110,190,592 bytes (approximately 476.94 GiB) |

Hardware values were obtained from Windows CIM and Storage providers. CPU frequency and thermal/power state were not controlled, so elapsed-time results are feasibility observations rather than stable benchmarks.

## Verified language and tool versions

| Tool | Version | Phase 0 result |
|---|---:|---|
| Python | 3.12.13, CPython 64-bit | PASS |
| Node.js | 24.12.0 | PASS |
| pnpm | 11.16.0 | PASS; pnpm reported 11.20.0 available but it was not substituted mid-spike |
| uv | 0.12.3 | PASS |
| Ruff | 0.16.2 | PASS |
| pre-commit | 4.6.1 | PASS |
| Pyright | 1.1.411 | PASS |

Python 3.11 was not tested because the required Python 3.12 environment installed cleanly, passed `pip check`, imported successfully, and executed the required Crowd-Kit methods.

## Verified Python analytical environment

| Package | Version |
|---|---:|
| Crowd-Kit | 1.4.2 |
| NumPy | 2.5.1 |
| pandas | 3.0.5 |
| SciPy | 1.18.0 |
| scikit-learn | 1.9.0 |
| statsmodels | 0.14.6 |
| DuckDB | 1.5.5 |
| PyArrow | 25.0.0 |
| FastAPI | 0.141.1 |
| Uvicorn | 0.52.1 |
| Pydantic | 2.13.4 |
| Typer | 0.27.1 |
| PyYAML | 6.0.3 |
| NLTK | 3.10.2 |
| standalone `krippendorff` | 0.8.2; tested and rejected from the normal dependency set because it is GPL-3.0-or-later |
| Hypothesis | 6.165.2 |
| pytest | 9.1.1 |
| pytest-cov | 7.1.0 |
| HTTPX | 0.28.1 |

The exact Phase 0 environment is captured in `spikes/phase0/python312_freeze.txt`. That freeze includes research-only and spike-only transitive packages and must not be copied wholesale into the production runtime lock.

## Verified frontend probe

| Package | Version |
|---|---:|
| React / React DOM | 19.2.8 |
| Vite | 8.2.1 |
| TypeScript | 7.0.2 |
| TanStack Query | 5.101.4 |
| Zod | 4.4.3 |
| Radix Dialog | 1.1.23 |
| Radix Tabs | 1.1.21 |
| Recharts | 3.10.1 |
| Vitest | 4.1.10 |
| Testing Library React | 16.3.2 |
| Playwright | 1.62.1 |
| axe-core Playwright integration | 4.12.1 |

The modules imported successfully on Node 24.12.0. Vite, TypeScript, Vitest, Playwright, and Pyright CLIs were callable. No browser binary was downloaded and no UI browser test was run because Phase 0 contains no frontend application.

The pinned frontend probe and lockfile are under `spikes/phase0/frontend_probe/`. A normal fresh networked install is verified. An offline install on a newly empty pnpm store was **not** verified; the local pnpm store did not contain every optional cross-platform and attestation artifact.

## Million-row feasibility context

The registered synthetic run used:

- 1,000,000 annotation events;
- 200,000 items;
- 1,000 workers;
- five annotations per item;
- one project;
- deterministic seed `20260809`;
- local NVMe storage;
- in-process Arrow generation and an in-memory DuckDB connection.

Observed values:

| Measurement | Result |
|---|---:|
| CSV size | 112,889,040 bytes (107.66 MiB) |
| Annotation Parquet size | 6,274,114 bytes (5.98 MiB) |
| Item Parquet size | 561,420 bytes (0.54 MiB) |
| Synthetic Arrow generation | 2.564 s |
| CSV write | 0.317 s |
| CSV read/ingestion | 0.212 s |
| Both Parquet writes | 1.001 s |
| Peak process RSS observed | 516,329,472 bytes (492.41 MiB) |
| Representative DuckDB queries | 0.014–0.173 s each |

These measurements show that the proposed path is feasible on this machine. They do not establish production throughput, worst-case memory, multi-user behavior, cold-cache latency, or performance on arbitrary CSV content.

## Reproduction caveats

- Package registries and dataset hosting are external services.
- Exact dependency versions are pinned in the spike artifacts, but binary wheels remain platform-specific.
- Floating-point DS results may vary slightly across future numerical-library builds; the parity fixture records the exact tested versions.
- Timings were single observations, not warmed repeated trials with controlled power and thermal state.
- The raw `relevance-2` archive is intentionally absent because its redistribution license is not stated.

