from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from crowdkit.aggregation import DawidSkene
from crowdkit.aggregation.classification.majority_vote import MajorityVote
from dataqual.analysis.core import Annotation
from dataqual.consensus.dawid_skene import (
    e_step_reference,
    encode_components,
    fit_dawid_skene,
    initialize_posteriors_raw,
    m_step_reference,
)
from dataqual.consensus.models import ConsensusStatus, DawidSkeneConfig


def _ref_config() -> DawidSkeneConfig:
    return DawidSkeneConfig(profile="dawid_skene_reference_compatible")


def _ck_error_matrix(ck_errors: pd.DataFrame, worker_id: str, labels: list[str]) -> np.ndarray:
    cols = [c if c in ck_errors.columns else (int(c) if c.isdigit() else c) for c in labels]
    if worker_id in ck_errors.index.get_level_values(0):
        slice_df = ck_errors.loc[worker_id]
        row_labels = [
            c if c in slice_df.index else (int(c) if str(c).isdigit() else c) for c in labels
        ]
        matrix_df = slice_df.reindex(index=row_labels, columns=cols, fill_value=1e-10)
    else:
        matrix_df = pd.DataFrame(1e-10, index=labels, columns=labels)
    return matrix_df.to_numpy().T


def test_phase0_frozen_tiny_fixture_has_semantic_hard_label_parity() -> None:
    fixture_path = (
        Path(__file__).parents[3] / "tests" / "reference_fixtures" / "crowdkit_ds_small.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    rows = [
        Annotation(
            f"frozen-{index}",
            row["task"],
            row["worker"],
            str(row["label"]),
        )
        for index, row in enumerate(fixture["input_annotations"])
    ]
    labels = ["0", "1"]
    ours = fit_dawid_skene(rows, labels, _ref_config())[0]
    assert ours.status == ConsensusStatus.SUCCESS
    inferred = {
        item_id: ours.component.labels[int(np.argmax(ours.posteriors[index]))]
        for index, item_id in enumerate(ours.component.item_ids)
    }
    expected = {
        item_id: str(label) for item_id, label in fixture["dawid_skene_reference"]["labels"].items()
    }
    assert inferred == expected

    # Verify smoothed_v1 is preserved and also runs on this fixture
    ds_config = DawidSkeneConfig(profile="dawid_skene_smoothed_v1")
    ours_smoothed = fit_dawid_skene(rows, labels, ds_config)[0]
    assert ours_smoothed.status in {ConsensusStatus.SUCCESS, ConsensusStatus.NON_CONVERGED}


def test_first_m_step_and_first_e_step_parity() -> None:
    labels = ["a", "b", "c"]
    rows = [
        Annotation("1", "item1", "w1", "a"),
        Annotation("2", "item1", "w2", "a"),
        Annotation("3", "item2", "w1", "b"),
        Annotation("4", "item2", "w2", "c"),
        Annotation("5", "item3", "w1", "c"),
        Annotation("6", "item3", "w2", "c"),
    ]
    component = encode_components(rows, labels, component_policy="global")[0]
    q0 = initialize_posteriors_raw(component)

    frame = pd.DataFrame(
        [(r.item_id, r.annotator_id, r.label) for r in rows],
        columns=["task", "worker", "label"],
    )
    ck_q0 = MajorityVote().fit_predict_proba(frame).loc[component.item_ids, labels].to_numpy()
    assert np.max(np.abs(q0 - ck_q0)) <= 1e-12

    prior0, confusion0 = m_step_reference(component, q0)
    ck_prior0 = ck_q0.mean(axis=0)
    ck_q0_df = pd.DataFrame(ck_q0, index=component.item_ids, columns=labels)
    ck_err0 = DawidSkene._m_step(frame, ck_q0_df)

    assert np.max(np.abs(prior0 - ck_prior0)) <= 1e-12
    for w_idx, w_id in enumerate(component.worker_ids):
        ck_mat = _ck_error_matrix(ck_err0, w_id, labels)
        assert np.max(np.abs(confusion0[w_idx] - ck_mat)) <= 1e-9

    q1 = e_step_reference(component, prior0, confusion0)
    ck_q1_df = DawidSkene._e_step(
        frame,
        pd.Series(ck_prior0, index=labels),
        ck_err0,
    )
    ck_q1 = ck_q1_df.loc[component.item_ids, labels].to_numpy()
    assert np.max(np.abs(q1 - ck_q1)) <= 1e-9


def test_binary_perfect_workers_parity() -> None:
    labels = ["0", "1"]
    rows = [
        Annotation(f"r-{i}-{w}", f"item-{i}", f"w-{w}", labels[i % 2])
        for i in range(20)
        for w in range(4)
    ]
    ours = fit_dawid_skene(rows, labels, _ref_config())[0]
    assert ours.status == ConsensusStatus.SUCCESS

    df = pd.DataFrame(
        [(r.item_id, r.annotator_id, r.label) for r in rows],
        columns=["task", "worker", "label"],
    )
    ck = DawidSkene(n_iter=200, tol=1e-6).fit(df)
    ck_probas = ck.probas_.loc[ours.component.item_ids, labels].to_numpy()
    assert np.max(np.abs(ours.posteriors - ck_probas)) <= 1e-5

    inferred = {
        item_id: ours.component.labels[int(np.argmax(ours.posteriors[idx]))]
        for idx, item_id in enumerate(ours.component.item_ids)
    }
    expected = ck.labels_.to_dict()
    assert inferred == expected


def test_controlled_disagreement_parity() -> None:
    labels = ["a", "b"]
    rows = []
    # item 0-9 true is 'a', item 10-19 true is 'b'
    for i in range(20):
        truth = "a" if i < 10 else "b"
        other = "b" if truth == "a" else "a"
        # w0 is 100% accurate
        rows.append(Annotation(f"r-{i}-w0", f"item-{i}", "w0", truth))
        # w1 is 80% accurate
        rows.append(Annotation(f"r-{i}-w1", f"item-{i}", "w1", truth if i % 5 != 0 else other))
        # w2 is 60% accurate
        rows.append(Annotation(f"r-{i}-w2", f"item-{i}", "w2", truth if i % 5 < 3 else other))

    ours = fit_dawid_skene(rows, labels, _ref_config())[0]
    assert ours.status == ConsensusStatus.SUCCESS

    df = pd.DataFrame(
        [(r.item_id, r.annotator_id, r.label) for r in rows],
        columns=["task", "worker", "label"],
    )
    ck = DawidSkene(n_iter=200, tol=1e-6).fit(df)

    ck_probas = ck.probas_.loc[ours.component.item_ids, labels].to_numpy()
    assert np.max(np.abs(ours.posteriors - ck_probas)) <= 1e-5

    inferred = {
        item_id: ours.component.labels[int(np.argmax(ours.posteriors[idx]))]
        for idx, item_id in enumerate(ours.component.item_ids)
    }
    expected = ck.labels_.to_dict()
    assert inferred == expected


def test_multiclass_parity() -> None:
    labels = ["c0", "c1", "c2"]
    rng = np.random.Generator(np.random.PCG64(42))
    items = [f"item-{i}" for i in range(30)]
    workers = [f"w-{w}" for w in range(6)]
    rows = []
    for item in items:
        truth = int(item.split("-")[1]) % 3
        for worker in workers:
            w_idx = int(worker.split("-")[1])
            # vary quality per worker
            acc = 0.8 if w_idx < 3 else 0.5
            emitted = truth if rng.random() < acc else rng.choice(3)
            rows.append(Annotation(f"r-{item}-{worker}", item, worker, labels[emitted]))

    ours = fit_dawid_skene(rows, labels, _ref_config())[0]
    assert ours.status == ConsensusStatus.SUCCESS

    df = pd.DataFrame(
        [(r.item_id, r.annotator_id, r.label) for r in rows],
        columns=["task", "worker", "label"],
    )
    ck = DawidSkene(n_iter=200, tol=1e-6).fit(df)

    ck_probas = ck.probas_.loc[ours.component.item_ids, labels].to_numpy()
    assert np.max(np.abs(ours.posteriors - ck_probas)) <= 1e-5


def test_missing_annotations_parity() -> None:
    labels = ["0", "1"]
    rows = [
        Annotation("r1", "item-0", "w0", "0"),
        Annotation("r2", "item-0", "w1", "0"),
        Annotation("r3", "item-1", "w1", "1"),
        Annotation("r4", "item-1", "w2", "1"),
        Annotation("r5", "item-2", "w0", "0"),
        Annotation("r6", "item-2", "w2", "1"),
    ]
    ours = fit_dawid_skene(rows, labels, _ref_config())[0]
    assert ours.status == ConsensusStatus.SUCCESS

    df = pd.DataFrame(
        [(r.item_id, r.annotator_id, r.label) for r in rows],
        columns=["task", "worker", "label"],
    )
    ck = DawidSkene(n_iter=200, tol=1e-6).fit(df)

    ck_probas = ck.probas_.loc[ours.component.item_ids, labels].to_numpy()
    assert np.max(np.abs(ours.posteriors - ck_probas)) <= 1e-5


def test_sparse_workers_parity() -> None:
    labels = ["a", "b", "c"]
    rng = np.random.Generator(np.random.PCG64(123))
    items = [f"item-{i:02d}" for i in range(50)]
    workers = [f"w-{w:02d}" for w in range(15)]
    rows = []
    for item in items:
        truth = int(item.split("-")[1]) % 3
        assigned = rng.choice(workers, size=2, replace=False)
        for w in assigned:
            emitted = truth if rng.random() < 0.7 else rng.choice(3)
            rows.append(Annotation(f"r-{item}-{w}", item, w, labels[emitted]))

    ours = fit_dawid_skene(rows, labels, _ref_config())[0]
    assert ours.status in {ConsensusStatus.SUCCESS, ConsensusStatus.NON_CONVERGED}

    df = pd.DataFrame(
        [(r.item_id, r.annotator_id, r.label) for r in rows],
        columns=["task", "worker", "label"],
    )
    ck = DawidSkene(n_iter=200, tol=1e-6).fit(df)

    ck_probas = ck.probas_.loc[ours.component.item_ids, labels].to_numpy()
    assert np.max(np.abs(ours.posteriors - ck_probas)) <= 1e-3

    inferred = {
        item_id: ours.component.labels[int(np.argmax(ours.posteriors[idx]))]
        for idx, item_id in enumerate(ours.component.item_ids)
    }
    expected = ck.labels_.to_dict()
    assert inferred == expected


def test_confusion_matrix_axis_alignment() -> None:
    labels = ["c0", "c1"]
    rows = [
        Annotation("1", "item1", "w1", "c0"),
        Annotation("2", "item1", "w2", "c1"),
        Annotation("3", "item2", "w1", "c0"),
        Annotation("4", "item2", "w2", "c0"),
    ]
    ours = fit_dawid_skene(rows, labels, _ref_config())[0]
    df = pd.DataFrame(
        [(r.item_id, r.annotator_id, r.label) for r in rows],
        columns=["task", "worker", "label"],
    )
    ck = DawidSkene(n_iter=200, tol=1e-6).fit(df)

    for w_idx, w_id in enumerate(ours.component.worker_ids):
        # DataQual row = latent class, column = emitted class
        # Crowd-Kit row = emitted label, column = latent class
        ck_matrix_transposed = _ck_error_matrix(ck.errors_, w_id, labels)
        assert np.max(np.abs(ours.worker_confusion[w_idx] - ck_matrix_transposed)) <= 1e-5


@pytest.mark.parametrize("label_order", [["a", "b", "c"], ["c", "a", "b"]])
def test_label_order_alignment(label_order: list[str]) -> None:
    rows = [
        Annotation("1", "item1", "w1", "a"),
        Annotation("2", "item1", "w2", "b"),
        Annotation("3", "item2", "w1", "c"),
        Annotation("4", "item2", "w2", "c"),
    ]
    ours = fit_dawid_skene(rows, label_order, _ref_config())[0]
    df = pd.DataFrame(
        [(r.item_id, r.annotator_id, r.label) for r in rows],
        columns=["task", "worker", "label"],
    )
    ck = DawidSkene(n_iter=200, tol=1e-6).fit(df)

    ck_probas = ck.probas_.loc[ours.component.item_ids, label_order].to_numpy()
    assert np.max(np.abs(ours.posteriors - ck_probas)) <= 1e-5


def test_crowdkit_is_absent_from_production_consensus_modules() -> None:
    import dataqual.consensus.dawid_skene as production_ds
    import dataqual.consensus.service as production_service

    assert "crowdkit" not in inspect.getsource(production_ds)
    assert "crowdkit" not in inspect.getsource(production_service)
