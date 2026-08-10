# Phase 2 Validation Report

Status: pending final gate rerun; statistical validation passed  
Validation artifact: `spikes/phase2/results/phase2_validation.json`

## Validation design

Expected qualitative behavior for synthetic cases A–J was written into the
validation runner before execution. Production Alpha was compared with NLTK only
in tests. Gold metric parity used scikit-learn only in tests. The selected real
dataset was converted with the checksum-gated adapter, and raw source/review text
was not committed.

## Synthetic validation

| Case | Expected behavior | Observed |
|---|---|---|
| A — perfect agreement | Defined raw agreement and Alpha equal 1 | raw `1.0`; Alpha `1.0` |
| B — disagreement | Materially below perfect | raw `0.0`; Alpha `-0.6667` |
| C — single class | Alpha unavailable because expected disagreement is zero | raw `1.0`; Alpha `unavailable` |
| D — missing ratings | Absent ratings ignored; pairable items remain | raw `0.6667`; Alpha `0.4444` |
| E — imbalance | Raw agreement can be high while Alpha reflects prevalence | raw `0.95`; Alpha `0.6486` |
| F — perfect/weak worker | Gold diagnostics distinguish known behavior | exact unit fixtures passed |
| G — multiclass confusion | Off-diagonal errors remain visible | exact 3×3 raw matrix passed |
| H — very small sample | Point estimate may exist; CI unavailable | point estimates defined; population below CI minimum |
| I — disconnected groups | Multiple components and isolated worker reported | exact overlap fixture passed |
| J — reannotation | Only current event contributes | 8 current of 9 immutable events |

## Alpha parity

- Five golden fixtures cover perfect, partial, missing, multiclass, and sparse
  matrices at absolute tolerance `1e-10`.
- One hundred deterministic randomized sparse/multiclass candidates compare all
  finite cases at tolerance `1e-8`.
- Degenerate single-class behavior is intentionally not forced to match a finite
  value; DataQual returns `unavailable` with `zero_expected_disagreement`.

## Gold metric parity

Accuracy, macro precision, macro recall, and macro F1 match scikit-learn under
the documented `zero_division=0` aggregate mapping. Class-level undefined values
remain null. Exact confusion rows (gold) and columns (submitted annotation)
reconcile to evaluated support.

## Selected real dataset

Dataset: Requirements Annotation Phase 3, Zenodo record `3626185`, CC BY 4.0.

- Source checksums matched the locked manifest.
- 2,701 ordinary source rows became 2,674 annotation events after removing 27
  exact duplicate exports.
- 448 items, 121 annotators, five registered classes.
- 447 items have independently joined `benchmark_truth`; one unmatched item is
  retained for unsupervised evidence and excluded from gold metrics.
- All 448 items are co-annotated.
- Worker overlap graph: 121 nodes, 1,120 observed edges, one connected component.
- Pooled raw agreement: `0.457293`; item-bootstrap 95% CI
  `[0.434006, 0.481145]`; 2,000/2,000 valid replicates.
- Nominal Alpha: `0.300493`; item-bootstrap 95% CI
  `[0.269153, 0.330709]`; 2,000/2,000 valid replicates.
- Gold evaluation support: 2,668 current annotation events on 447 items.
- Gold accuracy: `0.538231`; item-bootstrap 95% CI
  `[0.511410, 0.564468]`.
- Macro F1: `0.511598`; item-bootstrap 95% CI
  `[0.482967, 0.539083]`.

These values validate computation and traceability only. They are not evidence
that this dataset, annotator pool, or any algorithm is generally high or low
quality. The preserved Phase 0B negative result—Majority Vote outperforming
Dawid–Skene on this conversion—remains unchanged and is not recomputed in Phase 2.

## Performance observations

- Full selected-real analysis with four gold intervals, agreement interval, Alpha
  interval, overlap, persistence, and 2,000 replicates completed in the recorded
  local validation run; exact runtime is in the machine-readable artifact.
- A deterministic 100,000-event / 20,000-item five-rater calculation recorded
  pooled agreement in approximately `0.048 s` and Alpha in approximately
  `0.088 s` after data generation on this machine.
- The earlier Phase 0 one-million-row storage/scan evidence remains preserved.
  Phase 2 did not claim that every API payload is optimized for one million rows.

Timing is environmental evidence, not a public performance claim.

## Adversarial findings

- Confirmed pooled agreement is weighted by comparable pairs, not item averages.
- Confirmed bootstraps sample item clusters and retain every annotation in each
  sampled item.
- Confirmed only current events contribute; superseded rows remain counted only
  as provenance/evidence history.
- Confirmed gold matrices use true/gold rows and submitted labels as columns.
- Confirmed zero-support class rows normalize to null.
- Confirmed pairwise cells with no overlap are null and tiny-N cells retain `N`.
- Corrected macro F1 handling so gold-supported, never-predicted classes
  contribute zero to the aggregate while remaining null at class level.
- Removed machine-specific runtime paths from the committed validation artifact.

## Remaining validation limits

The external benchmark has selective crowd-platform assignment and only one
source domain. Bootstrap intervals do not correct assignment bias or gold-source
error. Release-grade 10,000-replicate benchmark intervals remain a later explicit
release run; Phase 2 standard artifacts use the contracted 2,000 replicates.
