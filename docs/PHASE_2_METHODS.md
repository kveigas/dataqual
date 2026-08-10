# Phase 2 Methods

Status: implementation methods record  
Method family version: `phase2-evidence-1.0.0`

Phase 2 analyzes only the current `AnnotationEvent` for each
item/annotator/domain identity in one immutable canonical snapshot. Superseded
events remain auditable but do not contribute. Missing ratings are absent events;
the implementation does not insert a missing-label category or assume assignment
missingness is MCAR.

## Percent Agreement

For item \(i\), let \(m_i\) be its current annotation count and \(n_{ic}\)
the count for class \(c\). DataQual reports pooled agreement over comparable
unordered pairs:

\[
A = \frac{\sum_i \sum_c {n_{ic} \choose 2}}
         {\sum_i {m_i \choose 2}}.
\]

Only items with at least two current annotations contribute. This is not an
unweighted average of item percentages. It is a directly calculated raw
agreement baseline, not reliability, accuracy, or consensus quality.

## Pairwise Agreement

For annotators \(a\) and \(b\), DataQual intersects their current annotated
items and reports:

\[
A_{ab} = \frac{\#\{i: y_{ia}=y_{ib}\}}{|I_{ab}|}.
\]

Every cell retains shared-item support `N`. Zero shared items produces a null
value with `unavailable` status, never 0%. Values below 20 shared items are
marked limited. The UI filters presentation by minimum overlap without removing
the raw API evidence.

## Krippendorff Alpha

Nominal Krippendorff's Alpha is implemented from scratch. For each pairable item,
the coincidence matrix receives:

\[
o_{cc'} \mathrel{+}= \frac{n_{ic}n_{ic'}}{m_i-1}\quad(c\ne c'),
\qquad
o_{cc} \mathrel{+}= \frac{n_{ic}(n_{ic}-1)}{m_i-1}.
\]

With \(N=\sum_{cc'}o_{cc'}\), \(n_c=\sum_{c'}o_{cc'}\), and nominal distance
\(\delta(c,c')=1[c\ne c']\):

\[
D_o=\frac{\sum_{cc'}o_{cc'}\delta(c,c')}{N},\quad
D_e=\frac{\sum_{cc'}n_cn_{c'}\delta(c,c')}{N(N-1)},\quad
\alpha=1-\frac{D_o}{D_e}.
\]

At least two pairable items and two observed classes are required. If expected
disagreement is zero, Alpha is `unavailable`; it is not replaced with 0 or 1.
Missing ratings and single-rating items are counted in evidence diagnostics but
do not enter the coincidence matrix. NLTK is test-only parity evidence and is
never called by the production path.

## Bootstrap CI

Percentile 95% confidence intervals use an explicit seed and NumPy
`Generator(PCG64(seed))`. The resampling unit is the item. Each sampled item
retains all of its current annotations (and its gold record where applicable),
preserving the multi-rater cluster structure.

- Standard/API default: 2,000 replicates.
- Release benchmark setting: 10,000 replicates.
- Minimum eligible population: 10 items.
- CI is unavailable when more than 5% of replicates are undefined.
- Undefined replicates are excluded and counted, never converted to zero.
- Output records valid/failed replicates, seed, population, confidence level,
  interval method, and resampling unit.

Intervals quantify item-sampling uncertainty under this resampling design. They
are not Bayesian credible intervals and do not repair assignment bias.

## Gold Accuracy

One evaluated observation is one current annotation on an item whose latest gold
record has `resolution_status = resolved_hard`. Accuracy is correct evaluated
events divided by all evaluated events. Distributional and unresolved gold are
excluded and counted. Results retain gold record IDs, event IDs, gold sources,
dataset snapshot identity, and canonical checksum.

Per-annotator point metrics are descriptive and support-labelled. The broader
contract's Beta-Binomial worker model is intentionally not implemented because
Phase 2 prohibits Bayesian worker reliability.

## Precision

For each registered class \(c\), precision is
\(TP_c/(TP_c+FP_c)\). It is null when a class is never predicted. For macro
precision only, a gold-supported but never-predicted class contributes zero,
matching the locked contract and the documented scikit-learn mapping while the
class-level value remains null with a warning.

## Recall

Recall is \(TP_c/(TP_c+FN_c)\). It is null when a class has no gold support.
Macro recall includes only classes with gold support.

## F1

Class F1 is the harmonic mean of precision and recall when both are defined.
The class value remains null if either component is null. In the macro aggregate,
a gold-supported class with undefined F1 contributes zero; classes without gold
support are excluded. This yields scikit-learn parity under `zero_division=0`
without falsifying the class-level undefined state.

## Confusion Matrix

Rows are authoritative hard-gold labels; columns are submitted current
annotation labels. Label order is the immutable label-domain order. Raw counts
are primary and exactly reconcile to evaluated event support. Row-normalized
values are also available; a zero-support gold row contains null cells, not
zeros.

## Evidence sufficiency

Evidence levels control presentation rather than mathematical existence:

- `limited`: fewer than 20 relevant items or fewer than five observations in a
  displayed class/cell;
- `adequate`: at least 20 relevant items and method-specific displayed support;
- `strong`: at least 100 relevant items without a material connectivity warning.

Methods still use explicit statuses: `success`, `insufficient_evidence`, and
`unavailable` are distinct. A poor estimate is never substituted for an undefined
one.

## UI truthfulness classification

- **A — directly observed:** item/event/annotator/class/gold counts, class counts,
  support, overlap counts, confusion raw counts, provenance IDs.
- **B — deterministically calculated:** proportions, distribution summaries,
  pooled agreement, pairwise agreement, Alpha point estimate, accuracy,
  precision, recall, F1, normalized confusion cells, graph components.
- **C — statistically estimated:** item-bootstrap confidence interval endpoints.

No Phase 2 display is a hard-coded demo statistic. Fixture values appear only
when the user imports an explicitly named synthetic fixture.

## Limitations

Agreement is not correctness. Gold metrics inherit the validity, independence,
and coverage limits of the gold source. Sparse or selective assignments can bias
worker comparisons. Item bootstrap does not model temporal dependence. Alpha is
nominal only and has no universal good/bad threshold. Per-annotator Phase 2
metrics are not rankings or competence estimates. Phase 2 does not aggregate
labels, infer latent truth, detect ambiguity, prioritize review, or measure drift.
