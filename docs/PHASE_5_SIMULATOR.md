# DataQual v4 — Phase 5 Synthetic Simulator Specification

This document details the deterministic synthetic dataset simulator, hidden ground truth isolation architecture, and pre-registered scenario designs.

## 1. Ground Truth Isolation Architecture

The simulator produces three distinct, isolated outputs:
1. `observed_annotation_events`: What DataQual is allowed to see.
2. `development_gold`: Operational gold labels available to DataQual for Bayesian worker reliability.
3. `hidden_evaluation_truth`: True item labels, annotation defect status ($is\_actually\_wrong$), worker confusion matrices, and item ambiguity states.

**Isolation Rule**: `hidden_evaluation_truth` is strictly isolated and NEVER accessible to prioritization algorithms or production REST endpoints. Adversarial leakage tests verify 100% invariance to modifications of hidden truth.

## 2. Worker & Item Archetypes

### Worker Archetypes:
- `EXPERT`: High base accuracy ($\ge 90\%$).
- `AVERAGE`: Moderate base accuracy ($\sim 75\%$).
- `WEAK`: Low base accuracy ($\sim 40\%$).
- `RANDOM`: Near-uniform emission ($1/K$).
- `ADVERSARIAL`: Systematically mislabeling ($c \to (c+1)\%K$).
- `CLASS_SPECIFIC`: Strong on class 0, weak on others.
- `CORRELATED_COPYCAT`: Shares error pattern with another worker.

### Item Archetypes:
- `EASY`: Low noise / high agreement expected.
- `DIFFICULT`: High difficulty multiplier.
- `AMBIGUOUS`: Supports `acceptable_labels: list[str]` and `latent_label_distribution`. Emitted labels matching any acceptable label are NOT counted as true defects.

## 3. Pre-registered Scenarios (S1–S12)

- **Development Scenarios**: S1 (Homogeneous Good), S2 (Heterogeneous), S3 (One/Few Weak), S4 (Adversarial), S5 (Class-Specific Confusion), S6 (Class Imbalance).
- **Final Evaluation Scenarios**: S7 (Sparse Overlap), S8 (Ambiguous Items), S9 (Correlated Workers), S10 (Low Gold Coverage), S11 (Mixed Difficulty), S12 (Mixed Realistic World).
