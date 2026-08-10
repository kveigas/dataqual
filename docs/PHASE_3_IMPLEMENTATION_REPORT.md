# Phase 3 implementation report

## MAJORITY VOTE:

PASS. Deterministic canonical-event counts, proportions, support, stable ordering,
missing-data behavior, explicit ties, and unresolved outcomes are implemented. Current
reannotations replace superseded events in the operational input without erasing
history.

## WEIGHTED VOTE:

PASS. The exact contract equation, minimum development support of 20, positive
chance-adjusted weights, minimum two eligible workers per item, ties, exclusions, and
coverage loss are exposed. Evaluation-only datasets do not receive a fabricated
weighted result.

## GOLD LEAKAGE PROTECTION:

PASS. Development/evaluation roles and partition identity are explicit. Overlap is a
validation error. Weight computation only selects development IDs; deliberate
evaluation-gold mutation does not change weights or outputs.

## DAWID_SKENE:

IMPLEMENTED; RELEASE GATE FAIL. Multiclass DS is a from-scratch NumPy implementation
with fixed label order, explicit component encoding, contract initialization, fixed
priors/smoothing, posterior output, and failure states. Production code does not
import Crowd-Kit. The real parity gate nevertheless fails materially.

## E_STEP:

PASS. Log-space evaluation, `1e-12` flooring, log-sum-exp normalization, missing
ratings, deterministic ordering, finite-value rejection, and posterior normalization
are tested.

## M_STEP:

PASS. Class priors use `gamma = 1`; confusion matrices use `lambda = 1`. Expected
counts, normalized rows, fixed axes, and explicit support are independently tested.

## NUMERICAL STABILITY:

PASS for tested cases. No non-finite values are serialized. Underflow/log-zero guards,
unused evidence, perfect workers, adversarial workers, sparse overlap, imbalance,
multiple classes, and disconnected components are exercised. Numerical failure is an
explicit status rather than a plausible fallback.

## CONVERGENCE:

PASS. Runs retain all likelihood values, iterations, final likelihood/delta,
tolerances, initialization, stopping reason, and convergence. Three consecutive small
improvements are required. Material decreases fail, and max-iteration results remain
non-converged with hard labels withheld.

## CROWDKIT PARITY:

FAIL. Isolated reference tests confirm semantic parity on the Phase 0 tiny fixture and
numeric parity on a large perfect-worker fixture. The definitive real benchmark has
0.6875 hard-label agreement and a 0.06935 accuracy difference, versus required 0.99
and 0.002. Synthetic reference differences are retained for all predefined scenarios.

## SYNTHETIC RECOVERY:

PASS WITH VISIBLE FAILURES. The 11 scenarios run across all ten locked seeds. Perfect
workers recover perfectly. Adversarial and class-specific behavior is observable.
Twelve DS runs are non-converged, primarily under sparse overlap, and are retained.
Weighted coverage is zero in the low-development-evidence scenario.

## REAL BENCHMARK:

PASS for reproducibility; FAIL for parity. The checksum-gated Requirements Annotation
Phase 3 snapshot runs without redistributing source review text. DataQual MV scores
0.7339 accuracy on 372 non-tied gold items. DataQual DS scores 0.5638 on all 447 gold
items and converges in 84 iterations. Weighted vote is unavailable because no approved
development/evaluation split exists.

## NEGATIVE RESULTS:

PASS. Crowd-Kit MV (0.6600) remains above Crowd-Kit DS (0.6331). DataQual MV also
exceeds DataQual DS on the real benchmark, with different coverage. Non-convergence,
weak sparse recovery, smoothing sensitivity, and weighted coverage collapse are not
suppressed.

## CONSENSUS SENSITIVITY:

PASS. Per-item raw evidence, method outputs and distributions, disagreement classes,
ties, and dataset-level method-dependent fraction are stored and exposed. Normal
operational payloads omit gold.

## WORKER CONFUSION:

PASS. Per-worker matrices include support, observed classes, component, and fixed axes:
row is latent class; column is worker-emitted class. UI and API call these
model-estimated confusion, never gold accuracy.

## PROVENANCE:

PASS. Results retain result/run IDs, canonical checksum, method/version, configuration
and hash, partition when applicable, software/Git identity when available, timestamps,
and source annotation-event IDs. Saved run JSON is write-once.

## API:

PASS. Typed create/get/item/worker/comparison routes use explicit method selection and
configuration, structured failed states, provenance, and item pagination. Unknown
fields are rejected.

## FRONTEND:

PARTIAL. The UI provides an overview, method-dependence summary, representative item
detail, DS status/iterations/final likelihood/initialization, and a clearly labelled
worker matrix. The full likelihood history is present in the API but not plotted, and
the current compact UI does not yet provide selectors for browsing every comparison
item and worker. These truthful omissions are scope deviations, not fake outputs.

## TEST COUNTS:

PASS. 75 backend tests passed in the complete coverage run; the added frozen-fixture
test then passed in a five-test focused reference run (76 backend tests in the final
suite). Seven frontend unit/integration tests pass. Tests cover
MV/weighted/DS math, invariances, normalization, failures, leakage, serialization,
service/API behavior, reference isolation, and deterministic replay.

## COVERAGE:

PASS. Backend branch-aware coverage is 91.77% against the required 90%. Frontend line
coverage is 95.18%; statement coverage is 84.21% and branch coverage is 60.63%.

## TYPE CHECK:

PASS. Pyright reports zero errors for backend/source scripts. TypeScript `tsc --noEmit`
passes through the frontend build.

## LINT:

PASS. Ruff check and Ruff format verification pass after final formatting.

## BUILD:

PASS. Vite production build completes; the generated JS bundle is approximately
322.6 kB (94.9 kB gzip).

## ACCESSIBILITY:

PASS. Two Chromium Playwright tests pass, including an axe-core scan with zero
violations on the empty workspace and a 390 × 844 horizontal-overflow check. The test
server was started explicitly after an earlier orphaned-server port collision.

## PERFORMANCE:

RECORDED. The 250-item synthetic runs averaged about 1.54 seconds (median 1.12) before
adding reference-adapter overhead. DataQual DS took about 2.65 seconds on the selected
448-item real dataset. Peak `tracemalloc` values exclude NumPy native/interpreter
memory and are reported only as limited engineering observations.

## ADVERSARIAL REVIEW:

FAIL overall. Leakage, equations, axes, normalization, tie behavior, convergence,
component refusal, reference isolation, probability language, benchmark tuning, and
negative-result retention were audited. The audit identified fixed `lambda = 1`
smoothing as materially dominant for sparse real workers and a conflict between the
locked production contract and the locked real parity requirement.

## KNOWN LIMITATIONS:

Latent identifiability, correlated errors, shared bias, local optima, sparse overlap,
fixed smoothing, stable-confusion assumptions, disconnected components, and
conditional/un-calibrated posteriors remain. Separate component estimates should not
be interpreted as globally comparable worker quality.

## SCOPE DEVIATIONS:

- The required real Crowd-Kit parity threshold is not met.
- The frontend does not yet plot likelihood history or browse all items/workers.
- The performance study records tiny/medium/real workloads but does not yet include a
  separately reported larger deterministic workload.
- No Phase 4 algorithm or placeholder was started.

## Final disposition

**PHASE 3: FAIL**

**READY FOR PHASE 4: NO**

The correct next action is a prospective contract review of DS smoothing and parity,
not post-result tuning and not automatic Phase 4 work.
