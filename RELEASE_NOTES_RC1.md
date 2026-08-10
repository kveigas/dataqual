# DataQual v4.0.0-rc1 Release Notes

DataQual v4.0.0-rc1 is a research-grade portfolio release candidate for AI annotation quality assurance, consensus inference, annotator intelligence, disagreement diagnostics, review queue prioritization, and reproducible synthetic benchmarking.

## Key Capabilities

1. **Immutable Evidence Foundation**: SHA-256 checksummed source intake, DuckDB catalog indexing, and atomic Parquet dataset snapshot storage.
2. **Deterministic Agreement & Gold Performance**: krippendorff Alpha, percentage agreement, macro precision/recall/F1, and confusion matrices with non-parametric bootstrap confidence intervals.
3. **Consensus Engine**: Majority Vote, development-gold weighted vote, from-scratch reference-compatible Dawid–Skene (100% Crowd-Kit parity), and experimental smoothed Dawid–Skene.
4. **Annotator Intelligence**: Bayesian Beta-Binomial worker reliability and Dirichlet-Multinomial confusion estimation with explicit evidence states (`CREDIBLY_LOW`, `UNCERTAIN`, `NOT_LOW`, `NO_GOLD`).
5. **Disagreement Diagnostics**: Evidence-backed heuristic flags (`probable_quality_defect`, `probable_ambiguity_policy_issue`, `mixed_evidence`).
6. **Review Queue Prioritization**: Operational candidates ranked by Expected Review Value ($ERV = 0.60 u_i + 0.20 h_i + 0.20 e_i$) with decomposable component scoring.
7. **Reproducible Synthetic Benchmarking**: 12 pre-registered scenarios (S1–S12) with isolated hidden ground truth and multi-seed AUREC@20% efficiency evaluation.

## Important Disclaimers & Known Limitations
- DataQual v4 is a research-grade portfolio prototype release candidate (`v4.0.0-rc1`), not an enterprise production SLA system.
- Dawid–Skene posteriors and ERV scores are model-estimated heuristic indicators, not calibrated probabilities or monetary ROI.
- On the real Requirements Annotation benchmark, Majority Vote outperformed Dawid–Skene by $+0.02084$ gold accuracy, confirming that EM consensus does not automatically beat simple voting under sparse co-annotation.

## Installation & Demo
```powershell
uv sync --all-groups --locked
pnpm install --frozen-lockfile
uv run python scripts/run_demo.py
```
