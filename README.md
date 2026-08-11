# DataQual

> **Research-Grade AI Annotation Quality & Review Prioritization System**  
> *Release Candidate `v4.0.0-rc1`*

DataQual is an evidence-backed system for preserving, validating, and analyzing crowdsourced and human-in-the-loop annotation data. It combines an immutable storage foundation, agreement statistics (Krippendorff's Alpha), multi-class Dawid–Skene consensus EM, Bayesian worker reliability, disagreement diagnostics, and review queue prioritization.

## Live Interactive Demo

Try DataQual v4 live in your browser:  
**https://kveigas.github.io/dataqual/**

- **Deterministic Synthetic Demo**: Click **Explore Demo Dataset** to instantly bootstrap and analyze a 100-item, 12-annotator synthetic environment (Scenario S12, seed 42).
- **Genuine Analytics Engine**: All agreement metrics, Dawid–Skene consensus, annotator intelligence profiles, quality flags, and review prioritization queues are computed live by the DataQual API service.
- **Synthetic Benchmark Research**: Synthetic simulation benchmark metrics (AUREC@20%) compare prioritization strategies under controlled ground truth.
- **Data Isolation**: User-uploaded CSV/JSON datasets remain strictly isolated from demo fixtures.

## Key Capabilities

- **Immutable Evidence Storage**: SHA-256 intake checksums, DuckDB catalog, Parquet snapshot storage.
- **Agreement & Gold Performance**: Raw agreement, Krippendorff's Alpha, macro precision/recall/F1, Brier score, ECE.
- **Consensus Engine**: Majority Vote, development-gold weighted vote, from-scratch reference-compatible Dawid–Skene (100% Crowd-Kit parity).
- **Annotator Intelligence**: Bayesian Beta-Binomial worker reliability and Dirichlet confusion with explicit evidence states (`CREDIBLY_LOW`, `UNCERTAIN`, `NOT_LOW`).
- **Disagreement Diagnostics**: Evidence-backed heuristic quality flags (`probable_quality_defect`, `probable_ambiguity_policy_issue`, `mixed_evidence`).
- **Review Prioritization & Simulation**: Decomposable Expected Review Value ($ERV$), 12 controlled synthetic scenarios (S1–S12), and multi-seed budget evaluation (AUREC@20%).

## Key Research Findings

- **Real Benchmark Parity**: DataQual reference-compatible Dawid–Skene achieves **100% hard-label parity** against the Crowd-Kit reference benchmark on the Requirements Annotation dataset (`0.00000` gold accuracy difference, posterior MAE $\approx 7.72 \times 10^{-11}$).
- **Majority Vote vs Dawid–Skene**: Majority Vote achieved `0.79167` gold accuracy vs `0.77083` for Dawid–Skene on the real benchmark, confirming that EM consensus does not automatically beat simple voting when the co-annotation graph is sparse.
- **Review Efficiency (ERV)**: Expected Review Value ($raw_i = 0.60 u_i + 0.20 h_i + 0.20 e_i$) achieves up to 56.4% error recovery at a 10% review budget in heterogeneous worker scenarios.

## Quick Start & Local Execution

### Requirements
- Python 3.12 (`uv` package manager)
- Node.js 24 (`pnpm`)

### Setup & One-Click Demo
```powershell
uv sync --all-groups --locked
pnpm install --frozen-lockfile
uv run python scripts/run_demo.py
```

### Launch Interactive Application
```powershell
# Terminal 1: Backend API
uv run dataqual serve

# Terminal 2: Frontend UI
pnpm --dir frontend dev
```
Open `http://127.0.0.1:5173`. Vite proxies `/api` requests to `http://127.0.0.1:8000`.

## Documentation Suite

- [RESEARCH_SUMMARY.md](docs/RESEARCH_SUMMARY.md): Executive summary of research questions, methods, and practical implications.
- [ARCHITECTURE_SUMMARY.md](docs/ARCHITECTURE_SUMMARY.md): System architecture, data flow, and ground-truth isolation boundaries.
- [METHODS_MATRIX.md](docs/METHODS_MATRIX.md): Detailed matrix of all 20+ implemented statistical methods.
- [RELEASE_BENCHMARK_SUMMARY.md](docs/RELEASE_BENCHMARK_SUMMARY.md): Complete real-dataset and synthetic scenario benchmark results.
- [RC1_SCIENTIFIC_FREEZE.md](docs/RC1_SCIENTIFIC_FREEZE.md): Scientific core freeze registry and configuration hashes.
- [RC1_PROVENANCE_AUDIT.md](docs/RC1_PROVENANCE_AUDIT.md): End-to-end evidence chain audit.
- [DEPENDENCY_AND_DATA_LICENSES.md](docs/DEPENDENCY_AND_DATA_LICENSES.md): Dependency and benchmark dataset attribution.

## Honest Research Limitations

- **Model-Estimated Scores**: Dawid–Skene posteriors and ERV scores are heuristic indicators, not calibrated probabilities or monetary ROI.
- **Scope Exclusion**: Drift, BOCPD, GLAD, MACE, EBCC, active learning, AI-assist, fairness/subgroup analysis, weak supervision, and model training are explicitly excluded.

## License

DataQual's original source code is licensed under the Apache License 2.0. Third-party dependencies and benchmark datasets remain subject to their respective licenses; see [docs/DEPENDENCY_AND_DATA_LICENSES.md](docs/DEPENDENCY_AND_DATA_LICENSES.md).

