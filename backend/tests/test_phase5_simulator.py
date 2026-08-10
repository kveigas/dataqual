from __future__ import annotations

from dataqual.schemas.simulation import (
    ItemArchetypeConfig,
    SimulatorConfig,
)
from dataqual.simulation import SyntheticDatasetGenerator


def test_simulator_deterministic_regeneration():
    cfg = SimulatorConfig(
        version="1.0.0",
        simulation_world_seed=42,
        item_count=50,
        worker_count=5,
    )
    gen1 = SyntheticDatasetGenerator(cfg)
    annos1, golds1, truth1 = gen1.generate()

    gen2 = SyntheticDatasetGenerator(cfg)
    annos2, golds2, truth2 = gen2.generate()

    assert len(annos1) == len(annos2)
    assert len(golds1) == len(golds2)
    assert truth1.config_hash == truth2.config_hash

    for a1, a2 in zip(annos1, annos2, strict=False):
        assert a1.annotation_id == a2.annotation_id
        assert a1.item_id == a2.item_id
        assert a1.annotator_id == a2.annotator_id
        assert a1.label == a2.label


def test_simulator_different_seeds_produce_different_worlds():
    cfg1 = SimulatorConfig(simulation_world_seed=42, item_count=50, worker_count=5)
    cfg2 = SimulatorConfig(simulation_world_seed=999, item_count=50, worker_count=5)

    annos1, _, truth1 = SyntheticDatasetGenerator(cfg1).generate()
    annos2, _, truth2 = SyntheticDatasetGenerator(cfg2).generate()

    assert truth1.config_hash != truth2.config_hash
    labels1 = [a.label for a in annos1]
    labels2 = [a.label for a in annos2]
    assert labels1 != labels2


def test_simulator_ambiguous_items_handling():
    cfg = SimulatorConfig(
        simulation_world_seed=123,
        item_count=20,
        worker_count=5,
        item_archetypes=[
            ItemArchetypeConfig(archetype="EASY", count=10),
            ItemArchetypeConfig(archetype="AMBIGUOUS", count=10),
        ],
    )
    _annos, _golds, truth = SyntheticDatasetGenerator(cfg).generate()

    ambig_count = sum(1 for it in truth.items_truth.values() if it.item_truth_type == "ambiguous")
    assert ambig_count == 10

    for _item_id, it in truth.items_truth.items():
        if it.item_truth_type == "ambiguous":
            assert len(it.acceptable_labels) >= 2
