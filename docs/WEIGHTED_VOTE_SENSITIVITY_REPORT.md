# Phase 0B Weighted-Vote Sensitivity Spike

Status: **exploratory non-production evidence**  
Replicates: **10 per scenario**  
Production minimum: **20 development-gold annotations per worker — unchanged**

## Design

The isolated spike generated worker confusion matrices independently of item truth and assignment. Each worker received an independently sampled amount of development-gold evidence. Evaluation items were disjoint and their truth was not used in reliability estimation. Worker identities spanned both streams. Within a scenario/replicate, MV, weighted vote, and Crowd-Kit DS received identical evaluation events.

Evidence eligibility thresholds `5, 10, 20, 50, 100` were crossed with six scenarios: homogeneous workers, heterogeneous workers, one weak worker, adversarial workers, class-specific errors, and sparse overlap. Weighted-vote reliability used the methods-contract leave-one-worker empirical-Bayes prior and chance-adjusted clipped scalar weight. Items required at least two eligible positive-weight workers. Ten replicates were summarized with 2,000 deterministic replicate-bootstrap resamples; these intervals characterize this simulator experiment, not a population.

The exact aggregate and replicate rows are in `spikes/phase0b/results/weighted_vote_sensitivity.json`.

## Coverage sensitivity

Mean weighted-vote evaluation-item coverage:

| Scenario | T=5 | T=10 | T=20 | T=50 | T=100 |
|---|---:|---:|---:|---:|---:|
| Homogeneous | 1.000 | 1.000 | 0.991 | 0.670 | 0.177 |
| Heterogeneous | 1.000 | 1.000 | 0.993 | 0.745 | 0.179 |
| One weak worker | 1.000 | 1.000 | 0.988 | 0.660 | 0.106 |
| Adversarial | 0.999 | 0.997 | 0.948 | 0.507 | 0.106 |
| Class-specific errors | 1.000 | 1.000 | 0.988 | 0.681 | 0.178 |
| Sparse overlap | 0.807 | 0.460 | 0.154 | 0.007 | 0.000 |

At the production threshold of 20, the sparse-overlap 95% bootstrap interval for coverage was `[0.118, 0.187]`; the mean eligible-worker fraction was `0.393` (`[0.342, 0.438]`). This is direct evidence that high worker-level support does not guarantee item-level weighted-vote availability when overlap is sparse.

## Method comparison at threshold 20

| Scenario | MV acc / F1 | WV acc / F1 / coverage | DS acc / F1 |
|---|---|---|---|
| Homogeneous | 0.938 / 0.931 | 0.890 / 0.880 / 0.991 | 0.929 / 0.921 |
| Heterogeneous | 0.939 / 0.933 | 0.909 / 0.901 / 0.993 | 0.945 / 0.940 |
| One weak worker | 0.969 / 0.965 | 0.937 / 0.931 / 0.988 | 0.966 / 0.961 |
| Adversarial | 0.881 / 0.869 | 0.880 / 0.870 / 0.948 | 0.950 / 0.944 |
| Class-specific errors | 0.826 / 0.812 | 0.760 / 0.740 / 0.988 | 0.881 / 0.870 |
| Sparse overlap | 0.833 / 0.804 | 0.782 / 0.759 / 0.154 | 0.779 / 0.760 |

Weighted vote did not outperform MV in mean accuracy at threshold 20 in these scenarios. Its scalar reliability cannot model class-specific or adversarial confusion as fully as DS, and evidence filtering can discard useful votes. DS substantially helped in the adversarial and class-specific scenarios but did not universally win. These are valid negative/mixed results, not grounds to tune the threshold or simulator after inspection.

At threshold 20, heterogeneous-worker reliability MAE was `0.0416` (`[0.0367, 0.0464]`) and Spearman correlation was `0.888` (`[0.863, 0.910]`). Rank correlation is undefined in scenarios where true scalar reliabilities are constant; it is recorded as missing rather than zero.

## Interpretation and limits

- Lower thresholds improved coverage in this simulation but also changed the eligible worker set. This result alone cannot justify changing the default.
- Higher thresholds selected fewer workers and caused item coverage to collapse before reliability estimation necessarily improved enough to compensate.
- A single scalar weight is intentionally limited; it should not be advertised as a substitute for class-specific confusion modeling.
- The exploratory spike validates the planned measurement design. Phase 1 must implement the locked simulator independently and reproduce or explain differences before any release claim.
- The fixed production default remains 20. Any future change requires a new pre-registered study, change control, and evidence beyond this Phase 0B spike.
