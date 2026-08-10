# Crowd-Kit 1.4.2 Dawid–Skene reference contract

This document records behavioral semantics observed by inspecting the installed,
pinned Crowd-Kit 1.4.2 source. It does not copy Crowd-Kit into DataQual production.
Crowd-Kit remains an Apache-2.0 reference/dev dependency.

Inspected modules:

- `crowdkit.aggregation.classification.dawid_skene`;
- `crowdkit.aggregation.classification.majority_vote`;
- `crowdkit.aggregation.utils`.

## Input and labels

The reference selects `task`, `worker`, and `label`. Its effective label set contains
labels observed in the input. Majority Vote constructs task/label counts using pandas
`value_counts`, unstacks label columns, fills missing counts with zero, and normalizes
each task row. In the pinned pandas environment the label columns are deterministically
ordered by pandas' label-index ordering, not by a caller-supplied domain order.

Final hard labels use pandas `idxmax`, so an exact tie resolves to the first label
column. This differs from DataQual's operational Majority Vote, which deliberately
keeps ties unresolved. Reference tie behavior is reproduced only inside the
reference-compatible DS initialization/final-label comparison; it does not change
DataQual Majority Vote.

## Initialization

With no supplied `initial_error` and no gold labels:

1. `q(0)` is the raw Majority Vote fraction for every task and observed label. There
   is no pseudocount in the item probabilities.
2. `pi(0)` is the column mean of `q(0)`. There is no class-prior pseudocount.
3. Worker error counts are expected posterior counts from `q(0)`.
4. Each zero/error-count cell is clipped to `_EPS = 1e-10`.
5. For each worker and each latent class, emitted-label cells are normalized to sum to
   one. There is no additive pseudocount smoothing.

Crowd-Kit's optional `initial_error` paths are outside this parity profile and are not
used by the Phase 3/3R benchmark.

## Matrix orientation

Crowd-Kit stores a DataFrame indexed by `(worker, observed_label)` with latent/true
labels in columns:

`errors[worker, observed_label, true_label]`.

Thus its displayed rows are emitted labels and columns are latent labels. DataQual's
internal/output matrix is the transpose: row = latent label and column = emitted
label. All comparisons must align both labels and axes before calculating differences.

## E-step

For task `i` and latent class `c`, Crowd-Kit sums base-2 log error probabilities for
the observed worker labels and adds `log2(pi_c)`. It subtracts the row maximum,
exponentiates base 2, and normalizes each task row.

Before logging, class priors are clipped in place to `1e-10`; the clipped prior vector
is not explicitly renormalized. Error matrices were already clipped before their
M-step normalization. Base-2 versus natural logarithms is algebraically equivalent
apart from floating-point reduction effects.

## M-step and priors

Every iteration sets the class prior to the mean posterior across tasks, with no
Dirichlet pseudocount. Worker expected counts are grouped by worker and emitted label,
each cell is lower-clipped to `1e-10`, and each latent-class column within a worker is
normalized. There is no `lambda` pseudocount.

The reference does not apply an explicit low-evidence threshold, shrink sparse workers
toward a common population, or reject single-worker/disconnected components. All
tasks contribute to one global class prior even when the worker/item graph is
disconnected.

## Objective and stopping

The stored `loss_history_` is a per-annotation evidence lower bound (ELBO), not the
observed-data log likelihood recorded by DataQual smoothed v1. Entropy and expected
joint-log terms are calculated in natural logs, divided by the number of annotation
rows.

Defaults are `n_iter = 100` and `tol = 1e-5`; Phase 3 reference runs explicitly used
`n_iter = 200`, `tol = 1e-6`. Starting from negative infinity, each iteration runs
E-step, mean-prior update, M-step, and ELBO calculation. It stops when
`new_loss - previous_loss < tol`. The comparison is not absolute, does not require
multiple consecutive small changes, and also stops on a decreasing objective. The
class exposes no separate converged/non-converged flag or stopping reason.

## Epsilon behavior

- constant: `1e-10`;
- M-step: lower-clip expected-count cells, then normalize emitted labels per latent
  class;
- E-step: priors lower-clipped in place, without explicit post-clip renormalization;
- ELBO: priors and posteriors lower-clipped before logarithms;
- no general upper clip in ordinary Dawid–Skene.

Clipping a zero expected count is not equivalent to adding the same pseudocount to
every count. For well-supported nonzero cells, clipping changes nothing; additive
`lambda` changes every estimate.

## Missingness, unused classes, and components

Only submitted rows enter products/sums, so missing assignments are naturally absent.
Unobserved domain classes are not represented. Disconnected components are not split;
they share one learned class prior. A worker with very little evidence is still fitted.

## Verified differences from DataQual smoothed v1

| Dimension | Crowd-Kit 1.4.2 | DataQual smoothed v1 |
|---|---|---|
| Item initialization | raw MV fractions | MV counts plus `1/K` smoothing |
| Prior | posterior mean, no pseudocount | `gamma = 1` |
| Worker matrices | zero-cell clip only | additive `lambda = 1` |
| Epsilon | `1e-10` | `1e-12` floor and renormalization |
| Components | one global fit | separate overlap components |
| Stopping quantity | per-row ELBO | observed-data log likelihood |
| Stopping rule | one signed delta below tolerance | absolute/relative, three consecutive |
| Default/benchmark iterations | 100 / 200 | 200 |
| Tie hard label | first pandas label column | operational MV tie unresolved |
| Matrix storage | emitted × latent | latent × emitted |

These are candidate causes to isolate, not evidence that any one difference alone
caused the original real-benchmark divergence.

