from __future__ import annotations

import numpy as np
import pytest
from dataqual.analysis.core import Annotation
from dataqual.consensus.dawid_skene import (
    e_step,
    encode_components,
    fit_dawid_skene,
    initialize_posteriors,
    m_step,
    observed_log_likelihood,
)
from dataqual.consensus.models import ConsensusStatus, DawidSkeneConfig


def perfect_rows(items: int = 30) -> list[Annotation]:
    rows = []
    labels = ["a", "b", "c"]
    for item in range(items):
        truth = labels[item % 3]
        for worker in range(4):
            rows.append(Annotation(f"a-{item}-{worker}", f"i-{item}", f"w-{worker}", truth))
    return rows


def test_ds_initialization_e_and_m_steps_exact_contract_shapes() -> None:
    component = encode_components(perfect_rows(6), ["a", "b", "c"])[0]
    initial = initialize_posteriors(component)
    assert initial[0].tolist() == pytest.approx([13 / 15, 1 / 15, 1 / 15])
    prior, confusion = m_step(component, initial)
    assert prior.sum() == pytest.approx(1.0)
    assert np.allclose(confusion.sum(axis=2), 1.0)
    posterior = e_step(component, prior, confusion)
    assert np.allclose(posterior.sum(axis=1), 1.0)
    assert np.all(np.isfinite(posterior))
    assert np.isfinite(observed_log_likelihood(component, prior, confusion))


def test_ds_perfect_workers_recover_labels_and_converge_monotonically() -> None:
    fits = fit_dawid_skene(perfect_rows(), ["a", "b", "c"], DawidSkeneConfig())
    assert len(fits) == 1
    fit = fits[0]
    assert fit.status == ConsensusStatus.SUCCESS
    assert fit.converged
    inferred = np.argmax(fit.posteriors, axis=1)
    expected = [int(item_id.split("-")[1]) % 3 for item_id in fit.component.item_ids]
    assert inferred.tolist() == expected
    assert np.allclose(fit.posteriors.sum(axis=1), 1.0)
    assert np.allclose(fit.worker_confusion.sum(axis=2), 1.0)
    assert all(
        right - left >= -1e-8
        for left, right in zip(fit.likelihood_history, fit.likelihood_history[1:], strict=False)
    )


def test_ds_max_iteration_state_withholds_success() -> None:
    config = DawidSkeneConfig(max_iterations=1, absolute_tolerance=1e-30, relative_tolerance=1e-30)
    fit = fit_dawid_skene(perfect_rows(), ["a", "b", "c"], config)[0]
    assert fit.status == ConsensusStatus.NON_CONVERGED
    assert not fit.converged
    assert fit.stopping_reason == "max_iterations_reached"


def test_ds_disconnected_and_single_worker_components_are_explicit() -> None:
    rows = [
        Annotation("a1", "i1", "w1", "a"),
        Annotation("a2", "i1", "w2", "a"),
        Annotation("a3", "i2", "w1", "b"),
        Annotation("a4", "i2", "w2", "b"),
        Annotation("a5", "i3", "w3", "a"),
        Annotation("a6", "i4", "w3", "b"),
    ]
    fits = fit_dawid_skene(rows, ["a", "b"], DawidSkeneConfig())
    assert len(fits) == 2
    assert fits[1].status == ConsensusStatus.INSUFFICIENT_EVIDENCE
    assert fits[1].stopping_reason == "component_evidence_requirements_not_met"


def test_e_step_rejects_nonfinite_parameters() -> None:
    component = encode_components(perfect_rows(3), ["a", "b", "c"])[0]
    with pytest.raises(FloatingPointError):
        e_step(component, np.array([np.nan, 0.5, 0.5]), np.ones((4, 3, 3)) / 3)


def test_ds_semantics_are_invariant_to_row_order_and_category_names() -> None:
    rows = perfect_rows(12)
    first = fit_dawid_skene(rows, ["a", "b", "c"], DawidSkeneConfig())[0]
    renamed = {"a": "z", "b": "x", "c": "y"}
    transformed = [
        Annotation(row.annotation_id, row.item_id, row.annotator_id, renamed[row.label])
        for row in reversed(rows)
    ]
    second = fit_dawid_skene(transformed, ["z", "x", "y"], DawidSkeneConfig())[0]
    assert np.allclose(first.posteriors, second.posteriors)
    assert np.allclose(first.worker_confusion, second.worker_confusion)
