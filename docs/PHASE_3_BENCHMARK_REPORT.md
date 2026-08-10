# Phase 3 benchmark report

## Protocol

The runner is `scripts/run_phase3_validation.py`. It uses the locked reporting seeds:

`1009, 2017, 3011, 4001, 5003, 6007, 7001, 8009, 9001, 10007`.

Eleven scenarios were fixed before review: perfect, homogeneous moderate,
heterogeneous, one weak worker, adversarial workers, class-specific confusion,
imbalanced classes, sparse overlap, disconnected groups, low development evidence,
and multiclass. Each run records truth, generator parameters, full worker matrices,
method configuration, accuracy, macro-F1, DS NLL/Brier/entropy, worker-matrix MAE,
worker-quality rank correlation where defined, runtime, peak traced memory, component
status, and Crowd-Kit reference differences. Summaries report mean, median, empirical
2.5/97.5 percentiles, valid-run counts, and failed/non-converged seeds.

The committed machine-readable result is
`spikes/phase3/results/phase3_validation.json`. Source benchmark review text is not
redistributed. Its SHA-256 is
`413b2c0d550dc507e3ff85928ad3f96f4fe15c6460b83b44ea751a2ef9e40f8e`.

## Predeclared reference interpretation

Exact floating-point parity was not required because DataQual uses the contract's
fixed additive smoothing and convergence rule while Crowd-Kit does not. Semantic hard
labels and numeric posterior/matrix differences are reported. The release-level real
benchmark gate was fixed before results:

- hard-label agreement at least 0.99;
- absolute gold-accuracy difference at most 0.002.

The Phase 0 frozen tiny fixture and a large perfect-worker fixture are isolated in
`backend/tests/reference/test_crowdkit_ds_parity.py`. Production consensus code has no
Crowd-Kit import.

## Synthetic results

There are 110 primary runs (11 scenarios × 10 seeds). Perfect workers gave accuracy
1.0 for MV, weighted vote, and DS. Negative and unstable results were retained:

- 12 DS runs were non-converged in total: sparse overlap 7, imbalanced 3,
  class-specific confusion 1, and low-evidence 1.
- Low development evidence produced weighted-vote coverage 0.0, as required by the
  minimum-20 guard; no fabricated accuracy is reported.
- Sparse overlap produced poor DS availability and recovery rather than being pooled
  into a plausible global answer.
- MV exceeded DS in several ordinary scenarios, including homogeneous moderate,
  heterogeneous, disconnected, one-weak-worker, multiclass, and imbalanced settings.
- The adversarial scenario was one of the cases where DS helped: its mean accuracy was
  about 0.962 versus approximately 0.836 among MV's resolved items.

Mean DataQual/Crowd-Kit synthetic hard-label agreement was 1.000 for perfect workers;
0.964 homogeneous; 0.981 heterogeneous; 0.973 with one weak worker; 0.991 adversarial;
0.944 class-specific; 0.895 imbalanced; 0.923 sparse; 0.972 disconnected; 0.975 low
development evidence; and 0.974 multiclass. These differences are retained rather
than relabelled as parity. Non-converged DataQual components are excluded from the
corresponding hard-label comparison denominator and remain separately counted.

These simulations show qualitative recovery, refusal behavior, and failure modes.
They do not establish general superiority of any method.

## Requirements Annotation Phase 3 benchmark

The checksum-gated Phase 2 canonical snapshot contains 448 items, 2,674 annotations,
121 workers, and five classes. Gold evaluation covers 447 items. There is no approved
development/evaluation gold split, so weighted vote is correctly unavailable.

| Method | Gold items scored | Coverage | Accuracy | Macro-F1 |
|---|---:|---:|---:|---:|
| DataQual MV (ties withheld) | 372 | 0.8322 | 0.7339 | 0.6932 |
| DataQual DS | 447 | 1.0000 | 0.5638 | 0.4017 |
| Crowd-Kit MV | 447 | 1.0000 | 0.6600 | 0.6234 |
| Crowd-Kit DS | 447 | 1.0000 | 0.6331 | 0.6094 |

DataQual DS converged in 84 iterations. DataQual/Crowd-Kit DS hard-label agreement was
0.6875 and their accuracy difference was 0.06935. Both are far outside the predeclared
limits. Therefore the real parity gate is **FAIL**.

The historical negative result remains reproducible: Crowd-Kit MV outperformed
Crowd-Kit DS. DataQual's tie-withholding MV has different coverage and must not be
compared as though it predicted all items.

## Investigation of the parity failure

The strongest identified explanation is a specification mismatch: the locked
DataQual M-step adds `lambda = 1` to every confusion cell, while Crowd-Kit is
unsmoothed. In this sparse benchmark, individual workers have roughly 3–30 events, so
the additive prior can materially dominate their estimates. This is an explanation
supported by implementation inspection and sensitivity evidence, not proof that it is
the only cause.

The production constant was not changed after observing results. Relaxing smoothing,
changing initialization, thresholding cases, or preprocessing the benchmark to make
parity pass would violate the approved protocol. Phase 4 must not begin until the
contract/parity expectation is reconciled in a new, prospective decision.

## Performance observations

On the 250-item synthetic runs, DS runtime was approximately 1.54 seconds on average
(median 1.12 seconds), with a maximum of about 12.41 seconds among difficult runs.
Peak Python memory traced around the DS call averaged about 184 kB and reached about
374 kB; this excludes interpreter, NumPy native allocations, and benchmark data.
The real benchmark DS run took about 2.65 seconds versus about 0.58 seconds for the
Crowd-Kit reference in this environment. These are local engineering observations,
not product performance claims.

## Conclusion

Synthetic recovery and refusal behavior are credible, and the real benchmark is
reproducible. The mandatory real Crowd-Kit parity gate fails materially. Phase 3 is
therefore not scientifically releasable as PASS under the current contract.
