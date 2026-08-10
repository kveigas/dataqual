from __future__ import annotations

import math
from collections.abc import Sequence

from dataqual.analysis.core import Annotation
from dataqual.annotators.beta_binomial import compute_beta_binomial_reliability
from dataqual.consensus.models import ConsensusRun
from dataqual.schemas.core import GoldLabel
from dataqual.schemas.diagnostics import ItemDisagreementFeatures


def extract_item_disagreement_features(
    item_id: str,
    item_annotations: Sequence[Annotation],
    labels: Sequence[str],
    all_annotations: Sequence[Annotation],
    gold_labels: Sequence[GoldLabel],
    consensus_run: ConsensusRun | None = None,
) -> ItemDisagreementFeatures:
    domain_labels = list(labels)
    K = len(domain_labels)
    m_i = len(item_annotations)

    # 1. Vote counts & proportions
    vote_counts = dict.fromkeys(domain_labels, 0)
    for row in item_annotations:
        if row.label in vote_counts:
            vote_counts[row.label] += 1

    vote_props = {
        label: float(count / m_i) if m_i > 0 else 0.0 for label, count in vote_counts.items()
    }

    # 2. Vote Entropy (categorical)
    # H = -sum_c p_c ln(p_c) for p_c > 0
    entropy_nats = 0.0
    for p in vote_props.values():
        if p > 0.0:
            entropy_nats -= p * math.log(p)

    normalized_entropy = float(entropy_nats / math.log(K)) if K > 1 else None

    # 3. Vote Margin
    sorted_props = sorted(vote_props.values(), reverse=True)
    vote_margin = float(sorted_props[0] - sorted_props[1]) if len(sorted_props) > 1 else 1.0

    # 4. Majority Vote consensus extraction
    if not sorted_props or (len(sorted_props) > 1 and sorted_props[0] == sorted_props[1]):
        mv_status = "unresolved"
        mv_label = None
    else:
        mv_status = "success"
        mv_label = max(vote_props, key=lambda lbl: vote_props[lbl])

    # 5. Dawid-Skene consensus extraction
    ds_status = "unavailable"
    ds_probs: dict[str, float] | None = None
    ds_max_post: float | None = None
    ds_entropy: float | None = None
    ds_label: str | None = None

    if consensus_run is not None:
        ds_detail = next(
            (item for item in consensus_run.comparison.items if item.item_id == item_id), None
        )
        if ds_detail is not None and "dawid_skene" in ds_detail.labels:
            ds_label = ds_detail.labels["dawid_skene"]
            ds_status = "success" if ds_label is not None else "unresolved"

        fit_diag = next(
            (fit for fit in consensus_run.convergence if fit.component_id is not None),
            None,
        )
        if fit_diag is not None and fit_diag.converged:
            ds_status = "success"

    # 6. Consensus method disagreement
    method_disagreement = False
    if mv_label is not None and ds_label is not None:
        method_disagreement = mv_label != ds_label
    elif (mv_label is None or ds_label is None) and (m_i >= 2):
        method_disagreement = True

    # 7. Distinct labels emitted & gold status
    distinct_labels_count = len({row.label for row in item_annotations})
    gold = next((g for g in gold_labels if g.item_id == item_id), None)
    gold_status = str(gold.resolution_status) if gold else None

    # 8. Dissenting workers & trusted gold reliability
    consensus_lead = mv_label or ds_label
    dissenting_worker_ids = [
        row.annotator_id
        for row in item_annotations
        if consensus_lead and row.label != consensus_lead
    ]

    dissenting_reliabilities: dict[str, float | None] = {}
    dissenting_states: dict[str, str] = {}
    for w in dissenting_worker_ids:
        rel = compute_beta_binomial_reliability(all_annotations, gold_labels, w)
        dissenting_reliabilities[w] = rel.posterior_mean if rel.evaluated_gold_items > 0 else None
        dissenting_states[w] = rel.reliability_evidence_state

    return ItemDisagreementFeatures(
        item_id=item_id,
        annotation_count=m_i,
        vote_counts=vote_counts,
        vote_proportions=vote_props,
        vote_entropy=entropy_nats,
        normalized_entropy=normalized_entropy,
        vote_margin=vote_margin,
        mv_status=mv_status,
        mv_label=mv_label,
        ds_status=ds_status,
        ds_probabilities=ds_probs,
        ds_max_posterior=ds_max_post,
        ds_entropy=ds_entropy,
        method_disagreement=method_disagreement,
        distinct_labels_count=distinct_labels_count,
        gold_status=gold_status,
        dissenting_worker_ids=dissenting_worker_ids,
        dissenting_worker_gold_reliabilities=dissenting_reliabilities,
        dissenting_worker_reliability_states=dissenting_states,
    )
