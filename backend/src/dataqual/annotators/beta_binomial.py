from __future__ import annotations

from collections.abc import Sequence

import scipy.stats as stats

from dataqual.analysis.core import Annotation
from dataqual.schemas.core import GoldLabel
from dataqual.schemas.intelligence import BetaBinomialEstimate


def compute_beta_binomial_reliability(
    annotations: Sequence[Annotation],
    gold_labels: Sequence[GoldLabel],
    target_annotator_id: str,
) -> BetaBinomialEstimate:
    # 1. Filter resolved hard gold
    hard_gold = {
        g.item_id: g.label
        for g in gold_labels
        if str(g.resolution_status) == "resolved_hard" and g.label is not None
    }

    # 2. Group worker gold performance
    worker_successes: dict[str, int] = {}
    worker_failures: dict[str, int] = {}
    for row in annotations:
        if row.item_id in hard_gold:
            w = row.annotator_id
            correct = row.label == hard_gold[row.item_id]
            worker_successes[w] = worker_successes.get(w, 0) + (1 if correct else 0)
            worker_failures[w] = worker_failures.get(w, 0) + (0 if correct else 1)

    s_target = worker_successes.get(target_annotator_id, 0)
    f_target = worker_failures.get(target_annotator_id, 0)
    n_target = s_target + f_target

    # 3. Calculate leave-one-worker-out project prior
    s_other = sum(s for w, s in worker_successes.items() if w != target_annotator_id)
    f_other = sum(f for w, f in worker_failures.items() if w != target_annotator_id)
    n_other = s_other + f_other

    if n_other >= 20:
        prior_mean = float((s_other + 0.5) / (n_other + 1.0))
        prior_source = "leave_one_out_project"
    else:
        prior_mean = 0.5
        prior_source = "fallback_symmetric"

    kappa_0 = 2.0
    alpha_0 = float(kappa_0 * prior_mean)
    beta_0 = float(kappa_0 * (1.0 - prior_mean))

    # 4. Posterior distribution
    alpha_post = alpha_0 + s_target
    beta_post = beta_0 + f_target

    posterior_mean = float(alpha_post / (alpha_post + beta_post))
    posterior_median = float(stats.beta.ppf(0.5, alpha_post, beta_post))
    lower_bound = float(stats.beta.ppf(0.025, alpha_post, beta_post))
    upper_bound = float(stats.beta.ppf(0.975, alpha_post, beta_post))

    if n_target >= 100:
        evidence_status = "strong"
    elif n_target >= 20:
        evidence_status = "adequate"
    elif n_target >= 1:
        evidence_status = "limited"
    else:
        evidence_status = "no_gold"

    if n_target == 0:
        rel_state = "NO_GOLD"
    elif upper_bound < 0.50:
        rel_state = "CREDIBLY_LOW"
    elif lower_bound < 0.50 and upper_bound >= 0.50:
        rel_state = "UNCERTAIN"
    else:
        rel_state = "NOT_LOW"

    return BetaBinomialEstimate(
        annotator_id=target_annotator_id,
        successes=s_target,
        failures=f_target,
        evaluated_gold_items=n_target,
        posterior_mean=posterior_mean,
        posterior_median=posterior_median,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        confidence_level=0.95,
        prior_alpha=alpha_0,
        prior_beta=beta_0,
        prior_source=prior_source,
        prior_population_n=n_other,
        prior_mean=prior_mean,
        prior_strength=kappa_0,
        evidence_status=evidence_status,
        reliability_evidence_state=rel_state,
    )
