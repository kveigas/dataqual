from __future__ import annotations

import math
from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from dataqual.analysis.core import Annotation
from dataqual.consensus.models import ConsensusStatus, DawidSkeneConfig


@dataclass(frozen=True, slots=True)
class EncodedComponent:
    component_id: str
    item_ids: list[str]
    worker_ids: list[str]
    labels: list[str]
    observations: list[tuple[int, int, int]]


@dataclass(slots=True)
class ComponentFit:
    component: EncodedComponent
    status: ConsensusStatus
    posteriors: np.ndarray
    class_prior: np.ndarray
    worker_confusion: np.ndarray
    initial_class_prior: np.ndarray
    likelihood_history: list[float]
    iterations: int
    converged: bool
    stopping_reason: str
    final_delta: float | None
    warnings: list[str]


def initialize_posteriors(component: EncodedComponent) -> np.ndarray:
    item_count, class_count = len(component.item_ids), len(component.labels)
    counts = np.zeros((item_count, class_count), dtype=np.float64)
    totals = np.zeros(item_count, dtype=np.float64)
    for item, _worker, emitted in component.observations:
        counts[item, emitted] += 1.0
        totals[item] += 1.0
    return (counts + 1.0 / class_count) / (totals[:, None] + 1.0)


def initialize_posteriors_raw(component: EncodedComponent) -> np.ndarray:
    item_count, class_count = len(component.item_ids), len(component.labels)
    counts = np.zeros((item_count, class_count), dtype=np.float64)
    totals = np.zeros(item_count, dtype=np.float64)
    for item, _worker, emitted in component.observations:
        counts[item, emitted] += 1.0
        totals[item] += 1.0
    safe_totals = np.maximum(totals, 1.0)
    posteriors = counts / safe_totals[:, None]
    zero_mask = totals == 0
    if np.any(zero_mask):
        posteriors[zero_mask] = 1.0 / class_count
    return posteriors


def m_step(
    component: EncodedComponent,
    posteriors: np.ndarray,
    *,
    gamma: float = 1.0,
    smoothing_lambda: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    item_count, class_count = posteriors.shape
    worker_count = len(component.worker_ids)
    prior = (posteriors.sum(axis=0) + gamma) / (item_count + class_count * gamma)
    numerators = np.full(
        (worker_count, class_count, class_count), smoothing_lambda, dtype=np.float64
    )
    denominators = np.full((worker_count, class_count), class_count * smoothing_lambda)
    by_worker_item: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for item, worker, emitted in component.observations:
        by_worker_item[worker].append((item, emitted))
    for worker, observations in by_worker_item.items():
        for item, emitted in observations:
            numerators[worker, :, emitted] += posteriors[item]
            denominators[worker] += posteriors[item]
    confusion = numerators / denominators[:, :, None]
    return prior, confusion


def m_step_reference(
    component: EncodedComponent, posteriors: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    _item_count, class_count = posteriors.shape
    worker_count = len(component.worker_ids)
    prior = posteriors.mean(axis=0)
    numerators = np.zeros((worker_count, class_count, class_count), dtype=np.float64)
    for item, worker, emitted in component.observations:
        numerators[worker, :, emitted] += posteriors[item]
    numerators = np.maximum(numerators, 1e-10)
    confusion = numerators / numerators.sum(axis=2, keepdims=True)
    return prior, confusion


def _logsumexp(values: np.ndarray, axis: int) -> np.ndarray:
    maximum = np.max(values, axis=axis, keepdims=True)
    return np.squeeze(maximum, axis=axis) + np.log(np.sum(np.exp(values - maximum), axis=axis))


def e_step(
    component: EncodedComponent,
    class_prior: np.ndarray,
    worker_confusion: np.ndarray,
    *,
    probability_floor: float = 1e-12,
) -> np.ndarray:
    item_count = len(component.item_ids)
    prior = np.maximum(class_prior, probability_floor)
    prior /= prior.sum()
    confusion = np.maximum(worker_confusion, probability_floor)
    confusion /= confusion.sum(axis=2, keepdims=True)
    log_scores = np.tile(np.log(prior), (item_count, 1))
    for item, worker, emitted in component.observations:
        log_scores[item] += np.log(confusion[worker, :, emitted])
    normalizers = _logsumexp(log_scores, axis=1)
    if not np.all(np.isfinite(normalizers)):
        raise FloatingPointError("all class scores must have a finite normalizer")
    posterior = np.exp(log_scores - normalizers[:, None])
    posterior /= posterior.sum(axis=1, keepdims=True)
    if not np.all(np.isfinite(posterior)):
        raise FloatingPointError("posterior contains a non-finite value")
    return posterior


def e_step_reference(
    component: EncodedComponent,
    class_prior: np.ndarray,
    worker_confusion: np.ndarray,
) -> np.ndarray:
    item_count = len(component.item_ids)
    prior = np.maximum(class_prior, 1e-10)
    log_scores = np.tile(np.log2(prior), (item_count, 1))
    for item, worker, emitted in component.observations:
        log_scores[item] += np.log2(worker_confusion[worker, :, emitted])
    max_log = np.max(log_scores, axis=1, keepdims=True)
    scaled = np.power(2.0, log_scores - max_log)
    posterior = scaled / scaled.sum(axis=1, keepdims=True)
    if not np.all(np.isfinite(posterior)):
        raise FloatingPointError("posterior contains a non-finite value")
    return posterior


def elbo_reference(
    component: EncodedComponent,
    posteriors: np.ndarray,
    class_prior: np.ndarray,
    worker_confusion: np.ndarray,
) -> float:
    item_count, class_count = posteriors.shape
    prior = np.maximum(class_prior, 1e-10)
    log_prior = np.log(prior)
    log_obs = np.zeros((item_count, class_count), dtype=np.float64)
    for item, worker, emitted in component.observations:
        log_obs[item] += log_prior + np.log(worker_confusion[worker, :, emitted])
    joint_expectation = float(np.sum(posteriors * log_obs))
    q_clipped = np.maximum(posteriors, 1e-10)
    entropy = float(-np.sum(posteriors * np.log(q_clipped)))
    return joint_expectation + entropy


def observed_log_likelihood(
    component: EncodedComponent,
    class_prior: np.ndarray,
    worker_confusion: np.ndarray,
    *,
    probability_floor: float = 1e-12,
) -> float:
    item_count = len(component.item_ids)
    prior = np.maximum(class_prior, probability_floor)
    prior /= prior.sum()
    confusion = np.maximum(worker_confusion, probability_floor)
    confusion /= confusion.sum(axis=2, keepdims=True)
    log_scores = np.tile(np.log(prior), (item_count, 1))
    for item, worker, emitted in component.observations:
        log_scores[item] += np.log(confusion[worker, :, emitted])
    value = float(np.sum(_logsumexp(log_scores, axis=1)))
    if not math.isfinite(value):
        raise FloatingPointError("observed-data likelihood is non-finite")
    return value


def fit_component(component: EncodedComponent, config: DawidSkeneConfig) -> ComponentFit:
    if config.profile == "dawid_skene_reference_compatible":
        if (
            len(component.item_ids) == 0
            or len(component.worker_ids) == 0
            or len(component.observations) == 0
        ):
            initial_q = np.full(
                (len(component.item_ids), len(component.labels)), 1.0 / len(component.labels)
            )
            prior = np.full(len(component.labels), 1.0 / len(component.labels))
            confusion = np.full(
                (len(component.worker_ids), len(component.labels), len(component.labels)),
                1.0 / len(component.labels),
            )
            return ComponentFit(
                component=component,
                status=ConsensusStatus.INSUFFICIENT_EVIDENCE,
                posteriors=initial_q,
                class_prior=prior,
                worker_confusion=confusion,
                initial_class_prior=prior.copy(),
                likelihood_history=[],
                iterations=0,
                converged=False,
                stopping_reason="component_evidence_requirements_not_met",
                final_delta=None,
                warnings=["majority_vote_descriptives_only_for_ineligible_component"],
            )

        initial_q = initialize_posteriors_raw(component)
        initial_prior, initial_confusion = m_step_reference(component, initial_q)
        prior, confusion = initial_prior.copy(), initial_confusion.copy()
        posteriors = initial_q
        history: list[float] = []
        loss = -math.inf
        n_obs = len(component.observations)
        final_delta: float | None = None

        for iteration in range(1, config.max_iterations + 1):
            posteriors = e_step_reference(component, prior, confusion)
            prior, confusion = m_step_reference(component, posteriors)
            new_loss = elbo_reference(component, posteriors, prior, confusion) / n_obs
            final_delta = new_loss - loss
            history.append(new_loss)

            if iteration > 1 and final_delta < config.absolute_tolerance:
                return ComponentFit(
                    component=component,
                    status=ConsensusStatus.SUCCESS,
                    posteriors=posteriors,
                    class_prior=prior,
                    worker_confusion=confusion,
                    initial_class_prior=initial_prior,
                    likelihood_history=history,
                    iterations=iteration,
                    converged=True,
                    stopping_reason="reference_elbo_tolerance_reached",
                    final_delta=final_delta,
                    warnings=[],
                )
            loss = new_loss

        return ComponentFit(
            component=component,
            status=ConsensusStatus.NON_CONVERGED,
            posteriors=posteriors,
            class_prior=prior,
            worker_confusion=confusion,
            initial_class_prior=initial_prior,
            likelihood_history=history,
            iterations=config.max_iterations,
            converged=False,
            stopping_reason="max_iterations_reached",
            final_delta=final_delta,
            warnings=["hard_labels_withheld_non_converged"],
        )

    observed_classes = len({emitted for _item, _worker, emitted in component.observations})
    item_worker_counts = np.zeros(len(component.item_ids), dtype=np.int64)
    for item, _worker, _emitted in component.observations:
        item_worker_counts[item] += 1
    valid = (
        len(component.worker_ids) >= 2
        and len(component.item_ids) >= 2
        and observed_classes >= 2
        and bool(np.any(item_worker_counts >= 2))
    )
    initial_q = initialize_posteriors(component)
    initial_prior, initial_confusion = m_step(
        component,
        initial_q,
        gamma=config.gamma,
        smoothing_lambda=config.smoothing_lambda,
    )
    if not valid:
        return ComponentFit(
            component=component,
            status=ConsensusStatus.INSUFFICIENT_EVIDENCE,
            posteriors=initial_q,
            class_prior=initial_prior,
            worker_confusion=initial_confusion,
            initial_class_prior=initial_prior.copy(),
            likelihood_history=[],
            iterations=0,
            converged=False,
            stopping_reason="component_evidence_requirements_not_met",
            final_delta=None,
            warnings=["majority_vote_descriptives_only_for_ineligible_component"],
        )
    prior, confusion = initial_prior, initial_confusion
    history: list[float] = []
    try:
        history.append(
            observed_log_likelihood(
                component, prior, confusion, probability_floor=config.probability_floor
            )
        )
        consecutive = 0
        posteriors = initial_q
        final_delta: float | None = None
        for iteration in range(1, config.max_iterations + 1):
            posteriors = e_step(
                component, prior, confusion, probability_floor=config.probability_floor
            )
            new_prior, new_confusion = m_step(
                component,
                posteriors,
                gamma=config.gamma,
                smoothing_lambda=config.smoothing_lambda,
            )
            likelihood = observed_log_likelihood(
                component,
                new_prior,
                new_confusion,
                probability_floor=config.probability_floor,
            )
            final_delta = likelihood - history[-1]
            history.append(likelihood)
            if final_delta < -1e-8:
                return ComponentFit(
                    component,
                    ConsensusStatus.FAILED,
                    posteriors,
                    new_prior,
                    new_confusion,
                    initial_prior,
                    history,
                    iteration,
                    False,
                    "likelihood_decreased_materially",
                    final_delta,
                    ["em_monotonicity_violation"],
                )
            relative = abs(final_delta) / max(1.0, abs(history[-2]))
            if (
                abs(final_delta) <= config.absolute_tolerance
                or relative <= config.relative_tolerance
            ):
                consecutive += 1
            else:
                consecutive = 0
            prior, confusion = new_prior, new_confusion
            if consecutive >= config.consecutive_small_improvements:
                final_q = e_step(
                    component, prior, confusion, probability_floor=config.probability_floor
                )
                return ComponentFit(
                    component,
                    ConsensusStatus.SUCCESS,
                    final_q,
                    prior,
                    confusion,
                    initial_prior,
                    history,
                    iteration,
                    True,
                    "likelihood_tolerance_sustained",
                    final_delta,
                    [],
                )
        final_q = e_step(component, prior, confusion, probability_floor=config.probability_floor)
        return ComponentFit(
            component,
            ConsensusStatus.NON_CONVERGED,
            final_q,
            prior,
            confusion,
            initial_prior,
            history,
            config.max_iterations,
            False,
            "max_iterations_reached",
            final_delta,
            ["hard_labels_withheld_non_converged"],
        )
    except (FloatingPointError, OverflowError, ValueError) as exc:
        return ComponentFit(
            component,
            ConsensusStatus.FAILED,
            initial_q,
            initial_prior,
            initial_confusion,
            initial_prior,
            history,
            len(history) - 1,
            False,
            "numerical_failure",
            None,
            [f"{type(exc).__name__}: {exc}"],
        )


def encode_components(
    annotations: Sequence[Annotation],
    labels: Sequence[str],
    component_policy: str = "separate",
) -> list[EncodedComponent]:
    if component_policy == "global":
        items = sorted({row.item_id for row in annotations})
        workers = sorted({row.annotator_id for row in annotations})
        item_index = {item: index for index, item in enumerate(items)}
        worker_index = {worker: index for index, worker in enumerate(workers)}
        label_index = {label: index for index, label in enumerate(labels)}
        observations = [
            (item_index[row.item_id], worker_index[row.annotator_id], label_index[row.label])
            for row in annotations
            if row.label in label_index
        ]
        return [
            EncodedComponent(
                component_id="component_001",
                item_ids=items,
                worker_ids=workers,
                labels=list(labels),
                observations=observations,
            )
        ]
    by_item: dict[str, list[Annotation]] = defaultdict(list)
    worker_items: dict[str, set[str]] = defaultdict(set)
    for row in annotations:
        by_item[row.item_id].append(row)
        worker_items[row.annotator_id].add(row.item_id)
    unseen = set(by_item)
    raw_components: list[tuple[list[str], list[str]]] = []
    while unseen:
        start = min(unseen)
        comp_items_set: set[str] = set()
        comp_workers_set: set[str] = set()
        queue: deque[tuple[str, str]] = deque([("item", start)])
        while queue:
            kind, identifier = queue.popleft()
            if kind == "item":
                if identifier in comp_items_set:
                    continue
                comp_items_set.add(identifier)
                unseen.discard(identifier)
                for row in by_item[identifier]:
                    queue.append(("worker", row.annotator_id))
            else:
                if identifier in comp_workers_set:
                    continue
                comp_workers_set.add(identifier)
                for item_id in worker_items[identifier]:
                    queue.append(("item", item_id))
        raw_components.append((sorted(comp_items_set), sorted(comp_workers_set)))
    encoded = []
    label_index = {label: index for index, label in enumerate(labels)}
    for number, (component_items, component_workers) in enumerate(raw_components, 1):
        item_index = {item: index for index, item in enumerate(component_items)}
        worker_index = {worker: index for index, worker in enumerate(component_workers)}
        observations = [
            (item_index[row.item_id], worker_index[row.annotator_id], label_index[row.label])
            for item in component_items
            for row in by_item[item]
        ]
        encoded.append(
            EncodedComponent(
                component_id=f"component_{number:03d}",
                item_ids=component_items,
                worker_ids=component_workers,
                labels=list(labels),
                observations=observations,
            )
        )
    return encoded


def fit_dawid_skene(
    annotations: Sequence[Annotation], labels: Sequence[str], config: DawidSkeneConfig
) -> list[ComponentFit]:
    return [
        fit_component(component, config)
        for component in encode_components(
            annotations, labels, component_policy=config.component_policy
        )
    ]
