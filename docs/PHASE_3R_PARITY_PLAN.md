# Phase 3R Dawid–Skene parity plan

Status: **frozen before Phase 3R experiments**  
Date: 2026-08-09  
Pinned reference: Crowd-Kit 1.4.2

## Historical evidence that must not change

Phase 3 failed. Its real Requirements Annotation benchmark recorded:

- DataQual/Crowd-Kit DS hard-label agreement: **0.6875**;
- absolute gold-accuracy difference: **0.06935123042505598**;
- benchmark artifact SHA-256:
  `413b2c0d550dc507e3ff85928ad3f96f4fe15c6460b83b44ea751a2ef9e40f8e`;
- 12 non-converged synthetic DS runs;
- Crowd-Kit Majority Vote accuracy above Crowd-Kit DS accuracy.

The existing algorithm is frozen and named **DataQual Dawid–Skene — smoothed v1**.
The Phase 3 artifact and reports are immutable historical evidence. Phase 3R writes
new files and does not overwrite that artifact.

## Frozen smoothed-v1 contract

- label order: canonical label-domain order; item and worker IDs sorted;
- component policy: disconnected bipartite components fitted separately;
- posterior initialization: `(n_i,c + 1/K) / (m_i + 1)`;
- initial prior: `(sum_i q_i,c + 1) / (I + K)`;
- initial worker matrices: the same smoothed M-step used in later iterations;
- class-prior pseudocount: `gamma = 1`;
- confusion pseudocount: `lambda = 1` in every emitted-label cell;
- E-step: log prior plus emitted-label log confusion, normalized by log-sum-exp;
- probability floor: `1e-12`, followed by renormalization;
- M-step confusion axes: row = latent class, column = worker-emitted class;
- likelihood: observed-data log likelihood under the fitted mixture;
- convergence: absolute delta `<= 1e-8` or relative delta `<= 1e-6` for three
  consecutive iterations;
- material likelihood decrease: more than `1e-8` is failure;
- maximum iterations: 200; maximum reached is non-converged and hard labels withheld.

No gold label is used for DS fitting.

## Questions and one-factor differential design

The smoothing hypothesis is not accepted in advance. Starting from the verified
Crowd-Kit contract, experiments will alter one factor at a time:

1. confusion smoothing (`lambda`);
2. epsilon/clipping and normalization;
3. posterior/worker initialization;
4. class-prior update;
5. stopping metric and convergence rule;
6. tolerance;
7. maximum iterations;
8. label order/alignment;
9. matrix-axis alignment;
10. low-evidence worker treatment;
11. unused classes;
12. disconnected components;
13. tie resolution in majority-vote initialization.

For each transition, record hard-label changes, posterior differences, aligned worker
matrix differences, prior differences, convergence/iterations, and benchmark metrics.
An attribution is allowed only when the corresponding one-factor transition changes
the result.

## Predeclared reference-compatible profile

A new explicit profile, `dawid_skene_reference_compatible`, will independently execute
DataQual E- and M-steps while matching verified Crowd-Kit mathematical choices. It
will never call Crowd-Kit. The frozen profile remains
`dawid_skene_smoothed_v1`. Method/profile identity must appear in configuration,
result provenance, API output, and UI.

The exact reference-compatible settings will be completed only from pinned-source
inspection and documented in `CROWDKIT_DS_REFERENCE_CONTRACT.md`; they will not be
chosen from real benchmark accuracy.

## Predeclared parity gates

These thresholds are fixed before the Phase 3R final experiment:

- deterministic, non-degenerate tiny-fixture hard-label parity: **100%**;
- real-benchmark hard-label parity: **at least 99%**;
- real-benchmark absolute gold-accuracy difference: **at most 0.002**;
- aligned posterior maximum absolute difference: **at most 1e-6** on controlled
  fixtures and **at most 1e-5** on the real benchmark;
- aligned worker-confusion maximum absolute difference: **at most 1e-6** on
  controlled fixtures and **at most 1e-5** on the real benchmark;
- aligned class-prior maximum absolute difference: **at most 1e-8** on controlled
  fixtures and **at most 1e-6** on the real benchmark.

The slightly wider real-data probability/matrix thresholds accommodate long EM
trajectories and library reduction-order differences; neither permits semantic label
divergence. No threshold may be relaxed after the final run.

## Parity ladder and escalation rule

The ladder order is fixed: binary perfect, binary controlled disagreement, three
classes, missing annotations, heterogeneous workers, sparse workers, class-specific
confusion, disconnected graph, frozen Phase 0 fixture, then Requirements Annotation
Phase 3. At each small-fixture level the comparison includes initialization, first
M-step, first E-step, next iteration, convergence, final posterior, priors, matrices,
and hard labels.

Escalation stops at the first unexplained meaningful divergence. That level must be
diagnosed before later levels are interpreted.

## Smoothing ablation

After reference semantics are frozen, DataQual will run `lambda` values
`0, 0.01, 0.1, 0.5, 1.0`. The grid is fixed now. It is diagnostic, not model
selection. Every value will report parity, hard-label differences, posterior
divergence, convergence, synthetic recovery, sparse-worker behavior, real accuracy,
macro-F1, NLL, and Brier score where gold permits. Evaluation gold will be used only
after fitting to score predictions.

## Recovery and initialization studies

Multiple locked seeds will cover abundant/sparse evidence, heterogeneous and
class-specific workers, imbalance, adversarial behavior, multiclass, and disconnected
components. Report all seeds, failures, convergence, iterations, entropy, consensus
metrics, worker-confusion MAE, and class-specific error MAE.

Smoothed-v1 initialization sensitivity is limited to scientifically motivated
strategies established before results: its frozen smoothed-vote initialization and
the verified reference initialization. No random restart is selected by evaluation
performance.

## Decision rule

Matching Crowd-Kit establishes reference compatibility, not superiority. Differing
from Crowd-Kit is not itself an error if equations and behavior are explicit. Phase 3R
will not choose a production default from the single real benchmark. If theoretical,
synthetic, convergence, calibration, and external evidence are mixed, both variants
remain explicit and no universal winner is claimed.

Phase 4 remains prohibited until Phase 3R reaches its own final disposition.

