# DataQual v4 — Executive Research Summary

## 1. Problem Statement
Crowdsourced and human-in-the-loop annotation data often suffers from unquantified noise, annotator bias, sparse co-annotation graphs, and ambiguous item semantics. Standard consensus algorithms (like Dawid–Skene) are frequently treated as objective ground truth without evaluating model convergence or diagnostic limitations. Furthermore, manual review budget is strictly limited in real-world AI data operations.

## 2. Key Research Questions
1. How reliably can we estimate latent consensus and annotator error without trusting uncalibrated model outputs?
2. Which evidence-backed strategy maximizes true error recovery under fixed manual review budgets (1%, 5%, 10%, 20%)?
3. How do baseline prioritization methods (Random, Entropy, Consensus Confidence, Worker Reliability) compare against Expected Review Value (ERV)?

## 3. Core Findings
- **Real Benchmark Parity**: DataQual's reference-compatible Dawid–Skene implementation achieves **100% hard-label parity** against the Crowd-Kit reference benchmark on the Requirements Annotation dataset (gold accuracy difference `0.00000`, posterior MAE `~7.72e-11`).
- **Majority Vote vs Dawid–Skene**: On the real Requirements Annotation dataset, Majority Vote outperformed Dawid–Skene in raw gold accuracy. This confirms that complex EM consensus does not automatically beat simple voting when annotator overlap is sparse or non-random.
- **Review Prioritization (ERV)**: The Expected Review Value ($ERV = 0.60 u_i + 0.20 h_i + 0.20 e_i$) achieves superior Area Under Review-Efficiency Curve (AUREC@20%) in heterogeneous worker worlds (S2, S3, S4), recovering up to 56.4% of errors at a 10% review budget.
- **Negative Results & Limitations**: On low gold coverage scenarios (S10, 5% gold), gold-based worker reliability degrades to random performance ($0.2000$), while ERV maintains $0.3850$ AUREC. On purely ambiguous items (S8), naive entropy error-recovery performance degrades ($0.2150$) because high entropy reflects legitimate policy ambiguity rather than worker error.

## 4. Practical Implications for AI Data Ops Leaders
- Never rely on Dawid–Skene posteriors as calibrated error probabilities.
- Separate true annotation errors (inspecting wrong labels) from ambiguous item routing (clarifying annotation guidelines).
- Use evidence-based review queue prioritization (ERV) to maximize ROI under strict human review budgets.
