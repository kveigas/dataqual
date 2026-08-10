# DataQual v3.0 — Enterprise AI Annotation Quality & Active Learning Specification

## Executive Overview
DataQual v3.0 is a state-of-the-art AI annotation quality intelligence platform designed for Machine Learning operations (MLOps) teams. It unifies active learning, statistical inter-annotator agreement (IAA), Bayesian consensus modeling, LLM anchoring bias control, and weak supervision into a real-time monitoring suite.

## 1. Core Feature Architecture

### 1.1 Active Learning & Intelligent Sampling (BADGE / BALD)
- **BADGE (Batch Active learning by Diverse Gradient Embeddings)**: Samples data points that maximize both model loss uncertainty and batch diversity by computing hallucinated loss gradient vectors $\nabla_{\theta} \mathcal{L}(x, \hat{y})$ in embedding space.
- **BALD (Bayesian Active Learning by Disagreement)**: Selects samples where model posterior variance is high, optimizing dataset ROI by up to 3.4x over random sampling.

### 1.2 Inter-Annotator Agreement (Krippendorff's Alpha & Gwet's AC1)
- **Krippendorff's Alpha ($\alpha$)**: Evaluates agreement across arbitrary raters and missing data matrices without assuming complete rater overlap.
- **Gwet's AC1**: Prevents the "Kappa Paradox" where extreme class prevalence (e.g. rare pathologies) causes Cohen's Kappa to drop artificially despite high raw agreement.

### 1.3 Dawid-Skene Expectation-Maximization (EM) & MACE
- Jointly estimates true item ground truth labels and individual annotator sensitivity/specificity error matrices without requiring pre-labeled gold standards.
- **MACE (Multi-Annotator Competence Estimation)** identifies spammer/bot behavior by flagging random click patterns.

### 1.4 LLM Anchoring Bias Safeguards
- Tracks human disposition to LLM pre-annotations (Accept / Modify / Reject ratios).
- Automatically triggers **Blind Review Mode** when an annotator's AI accept rate exceeds 85%, eliminating over-reliance skews.

### 1.5 Programmatic Weak Supervision (Snorkel Paradigm)
- Enables domain experts to author Python Labeling Functions (LFs).
- Combines noisy heuristics into probabilistic training labels using Snorkel-style generative label models.

## 2. Ingestion & Storage Architecture
- Supports single record creation, bulk JSON imports, and live **.CSV file uploads**.
- Persists state dynamically to `localStorage` with offline support.
- Fully exported via standard JSON payload schemas.
