# Phase 3 consensus methods

## Scope and evidence categories

Phase 3 adds categorical consensus inference. Raw annotations are **observed (A)**,
majority and weighted votes are **deterministically computed (B)**, and Dawid–Skene
(DS) posteriors and confusion matrices are **statistically estimated (C)**. Consensus
is not ground-truth accuracy unless a separate, permitted evaluation explicitly uses
trusted gold.

Only current human or AI-assisted annotation events are inputs. Superseded events are
retained in canonical history but do not vote. Labels use the canonical label-domain
order, and item and worker identifiers are sorted for deterministic representation.

## Majority Vote

For item `i` and class `c`, the vote proportion is `n_ic / m_i`, where `m_i` is the
number of current annotations. A label is returned only when one class has a unique
maximum. Equal maxima remain unresolved. Counts, proportions, support, worker IDs,
and source-event provenance are retained. Vote proportions describe the observed
sample; they are not calibrated probabilities.

## Development-gold weighted vote

Weights use resolved hard **development** gold only. Development and evaluation item
IDs must be explicit, unique, and disjoint. The request model rejects overlap, and the
weighting implementation never reads evaluation gold.

Each worker needs at least 20 development-gold observations. For worker `w`, the
leave-one-worker baseline is

`m_-w = (S_-w + 0.5) / (N_-w + 1)` when `N_-w >= 20`, otherwise `0.5`.

With `kappa = 2`, the reliability posterior mean is

`r_w = (2 m_-w + s_w) / (2 + n_w)`.

For `K` classes the chance-adjusted weight is

`clip((r_w - 1/K) / (1 - 1/K), 0, 1)`.

Eligible positive weights are summed by emitted class and normalized. At least two
eligible workers must annotate an evaluation item. Ties and insufficient eligible
evidence remain explicit. Run output reports eligible/ineligible workers, their
development support, evaluation-item count, resolved weighted-item count, coverage,
threshold, equation identity, and partition identity. The method assumes development
reliability transfers to evaluation data; this is disclosed, not silently asserted.

## Multiclass Dawid–Skene

The production implementation is from scratch and does not import Crowd-Kit.
Crowd-Kit is restricted to reference tests and benchmark code.

For class prior `pi_c`, worker confusion `theta_w,c,k`, and observed worker label
`y_iw`, the E-step computes

`q_i,c ∝ pi_c product_w theta_w,c,y_iw`.

It is evaluated in log space and normalized with log-sum-exp. Probabilities are
floored at `1e-12` before logarithms. The M-step uses fixed smoothing:

- class prior: `(1 + sum_i q_i,c) / (K + I)` (`gamma = 1`);
- confusion: `(1 + sum_i q_i,c 1[y_iw=k]) / (K + sum_i q_i,c)`
  (`lambda = 1`).

Confusion axes are always **row = latent/true class** and **column = worker-emitted
class**. These are latent-model estimates, not gold accuracy.

Initialization is fixed to smoothed observed vote fractions:

`q_i,c = (n_i,c + 1/K) / (m_i + 1)`.

No seed is used. The initial prior and the initialization identifier are retained.

## Components, convergence, and failure states

Disconnected worker/item overlap components are fitted separately. A component needs
at least two workers, two items, two observed classes, and worker overlap. Otherwise it
is `insufficient_evidence`; it is not pooled with an unrelated component.

The maximum is 200 iterations. Convergence requires three consecutive improvements
small under either absolute tolerance `1e-8` or relative tolerance `1e-6`. A material
likelihood decrease greater than `1e-8` is a numerical failure. Maximum-iteration,
insufficient-evidence, invalid-input, and numerical-failure outcomes are preserved.
Hard labels are withheld for failed or non-converged fits. Diagnostics retain the
complete likelihood history, final likelihood and delta, iterations, stopping reason,
tolerances, initialization, component size, and final prior.

## Sensitivity and provenance

Per-item comparison records raw votes and each requested method's label and
distribution. It identifies all-method agreement, MV/DS disagreement, weighted/MV or
weighted/DS disagreement, and ties/unresolved outcomes. The dataset summary reports
the fraction whose final label depends on method choice. Evaluation gold is absent
from the operational comparison payload.

Every result records the analysis run, result ID, dataset/project IDs, canonical
artifact checksum, method and version, full configuration and hash, creation time,
software/Git identity when available, and source annotation-event IDs.

## Limitations

- Latent truth can be unidentifiable, especially in disconnected or sparse graphs.
- Worker errors may be correlated, contrary to DS conditional independence.
- Shared worker bias can produce a confident but wrong latent consensus.
- EM can encounter local optima and initialization sensitivity.
- Sparse worker evidence destabilizes confusion estimates.
- Fixed additive smoothing can dominate workers with few observations.
- DS assumes each worker has a stable confusion process across items.
- Posterior confidence is conditional on the model and is not calibrated by default.
- Separate component labels share names but their latent estimates are not necessarily
  comparable in strength.
- Consensus is not a substitute for independent, representative evaluation gold.

