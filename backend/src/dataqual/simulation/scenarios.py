from __future__ import annotations

from dataqual.schemas.simulation import (
    ItemArchetypeConfig,
    SimulatorConfig,
    WorkerArchetypeConfig,
)


def get_pre_registered_scenario_config(
    scenario_id: str, world_seed: int = 42, random_ranking_seed: int = 2026
) -> SimulatorConfig:
    sc = scenario_id.upper()

    if sc == "S1":
        # S1 — HOMOGENEOUS GOOD WORKERS
        return SimulatorConfig(
            version="1.0.0",
            simulation_world_seed=world_seed,
            random_ranking_seed=random_ranking_seed,
            item_count=100,
            worker_count=10,
            label_classes=["positive", "neutral", "negative"],
            worker_archetypes=[
                WorkerArchetypeConfig(archetype="EXPERT", count=10, base_accuracy=0.92)
            ],
            development_gold_fraction=0.20,
        )

    elif sc == "S2":
        # S2 — HETEROGENEOUS WORKERS
        return SimulatorConfig(
            version="1.0.0",
            simulation_world_seed=world_seed,
            random_ranking_seed=random_ranking_seed,
            item_count=100,
            worker_count=10,
            label_classes=["positive", "neutral", "negative"],
            worker_archetypes=[
                WorkerArchetypeConfig(archetype="EXPERT", count=3, base_accuracy=0.90),
                WorkerArchetypeConfig(archetype="AVERAGE", count=4, base_accuracy=0.75),
                WorkerArchetypeConfig(archetype="WEAK", count=3, base_accuracy=0.45),
            ],
            development_gold_fraction=0.20,
        )

    elif sc == "S3":
        # S3 — ONE / FEW WEAK WORKERS
        return SimulatorConfig(
            version="1.0.0",
            simulation_world_seed=world_seed,
            random_ranking_seed=random_ranking_seed,
            item_count=100,
            worker_count=10,
            label_classes=["positive", "neutral", "negative"],
            worker_archetypes=[
                WorkerArchetypeConfig(archetype="EXPERT", count=8, base_accuracy=0.90),
                WorkerArchetypeConfig(archetype="WEAK", count=2, base_accuracy=0.35),
            ],
            development_gold_fraction=0.20,
        )

    elif sc == "S4":
        # S4 — ADVERSARIAL WORKERS
        return SimulatorConfig(
            version="1.0.0",
            simulation_world_seed=world_seed,
            random_ranking_seed=random_ranking_seed,
            item_count=100,
            worker_count=10,
            label_classes=["positive", "neutral", "negative"],
            worker_archetypes=[
                WorkerArchetypeConfig(archetype="EXPERT", count=7, base_accuracy=0.90),
                WorkerArchetypeConfig(archetype="ADVERSARIAL", count=3),
            ],
            development_gold_fraction=0.20,
        )

    elif sc == "S5":
        # S5 — CLASS-SPECIFIC CONFUSION
        return SimulatorConfig(
            version="1.0.0",
            simulation_world_seed=world_seed,
            random_ranking_seed=random_ranking_seed,
            item_count=100,
            worker_count=10,
            label_classes=["positive", "neutral", "negative"],
            worker_archetypes=[
                WorkerArchetypeConfig(archetype="EXPERT", count=4, base_accuracy=0.90),
                WorkerArchetypeConfig(archetype="CLASS_SPECIFIC", count=6),
            ],
            development_gold_fraction=0.20,
        )

    elif sc == "S6":
        # S6 — CLASS IMBALANCE
        return SimulatorConfig(
            version="1.0.0",
            simulation_world_seed=world_seed,
            random_ranking_seed=random_ranking_seed,
            item_count=100,
            worker_count=10,
            label_classes=["positive", "neutral", "negative"],
            class_prevalence={"positive": 0.70, "neutral": 0.20, "negative": 0.10},
            worker_archetypes=[
                WorkerArchetypeConfig(archetype="EXPERT", count=5, base_accuracy=0.85),
                WorkerArchetypeConfig(archetype="AVERAGE", count=5, base_accuracy=0.70),
            ],
            development_gold_fraction=0.20,
        )

    elif sc == "S7":
        # S7 — SPARSE OVERLAP (Final Evaluation)
        return SimulatorConfig(
            version="1.0.0",
            simulation_world_seed=world_seed,
            random_ranking_seed=random_ranking_seed,
            item_count=100,
            worker_count=15,
            label_classes=["positive", "neutral", "negative"],
            annotations_per_item_min=2,
            annotations_per_item_max=3,
            worker_archetypes=[
                WorkerArchetypeConfig(archetype="EXPERT", count=5, base_accuracy=0.88),
                WorkerArchetypeConfig(archetype="AVERAGE", count=5, base_accuracy=0.72),
                WorkerArchetypeConfig(archetype="WEAK", count=5, base_accuracy=0.45),
            ],
            development_gold_fraction=0.15,
        )

    elif sc == "S8":
        # S8 — AMBIGUOUS ITEMS (Final Evaluation)
        return SimulatorConfig(
            version="1.0.0",
            simulation_world_seed=world_seed,
            random_ranking_seed=random_ranking_seed,
            item_count=100,
            worker_count=10,
            label_classes=["positive", "neutral", "negative"],
            item_archetypes=[
                ItemArchetypeConfig(archetype="EASY", count=50),
                ItemArchetypeConfig(archetype="AMBIGUOUS", count=50),
            ],
            worker_archetypes=[
                WorkerArchetypeConfig(archetype="EXPERT", count=5, base_accuracy=0.90),
                WorkerArchetypeConfig(archetype="AVERAGE", count=5, base_accuracy=0.75),
            ],
            development_gold_fraction=0.20,
        )

    elif sc == "S9":
        # S9 — CORRELATED WORKERS (Final Evaluation)
        return SimulatorConfig(
            version="1.0.0",
            simulation_world_seed=world_seed,
            random_ranking_seed=random_ranking_seed,
            item_count=100,
            worker_count=10,
            label_classes=["positive", "neutral", "negative"],
            worker_archetypes=[
                WorkerArchetypeConfig(archetype="EXPERT", count=4, base_accuracy=0.90),
                WorkerArchetypeConfig(archetype="WEAK", count=2, base_accuracy=0.40),
                WorkerArchetypeConfig(
                    archetype="CORRELATED_COPYCAT", count=4, copycat_target_worker="w05"
                ),
            ],
            development_gold_fraction=0.20,
        )

    elif sc == "S10":
        # S10 — LOW GOLD COVERAGE (Final Evaluation)
        return SimulatorConfig(
            version="1.0.0",
            simulation_world_seed=world_seed,
            random_ranking_seed=random_ranking_seed,
            item_count=100,
            worker_count=10,
            label_classes=["positive", "neutral", "negative"],
            worker_archetypes=[
                WorkerArchetypeConfig(archetype="EXPERT", count=4, base_accuracy=0.88),
                WorkerArchetypeConfig(archetype="AVERAGE", count=4, base_accuracy=0.72),
                WorkerArchetypeConfig(archetype="WEAK", count=2, base_accuracy=0.45),
            ],
            development_gold_fraction=0.05,
        )

    elif sc == "S11":
        # S11 — MIXED DIFFICULTY (Final Evaluation)
        return SimulatorConfig(
            version="1.0.0",
            simulation_world_seed=world_seed,
            random_ranking_seed=random_ranking_seed,
            item_count=100,
            worker_count=10,
            label_classes=["positive", "neutral", "negative"],
            item_archetypes=[
                ItemArchetypeConfig(archetype="EASY", count=40),
                ItemArchetypeConfig(archetype="DIFFICULT", count=40),
                ItemArchetypeConfig(archetype="AMBIGUOUS", count=20),
            ],
            worker_archetypes=[
                WorkerArchetypeConfig(archetype="EXPERT", count=5, base_accuracy=0.88),
                WorkerArchetypeConfig(archetype="AVERAGE", count=5, base_accuracy=0.70),
            ],
            development_gold_fraction=0.20,
        )

    elif sc == "S12":
        # S12 — MIXED REALISTIC WORLD (Final Evaluation)
        return SimulatorConfig(
            version="1.0.0",
            simulation_world_seed=world_seed,
            random_ranking_seed=random_ranking_seed,
            item_count=100,
            worker_count=12,
            label_classes=["positive", "neutral", "negative"],
            item_archetypes=[
                ItemArchetypeConfig(archetype="EASY", count=50),
                ItemArchetypeConfig(archetype="DIFFICULT", count=30),
                ItemArchetypeConfig(archetype="AMBIGUOUS", count=20),
            ],
            worker_archetypes=[
                WorkerArchetypeConfig(archetype="EXPERT", count=4, base_accuracy=0.90),
                WorkerArchetypeConfig(archetype="AVERAGE", count=4, base_accuracy=0.75),
                WorkerArchetypeConfig(archetype="WEAK", count=2, base_accuracy=0.45),
                WorkerArchetypeConfig(archetype="ADVERSARIAL", count=1),
                WorkerArchetypeConfig(archetype="CLASS_SPECIFIC", count=1),
            ],
            development_gold_fraction=0.15,
        )

    else:
        raise ValueError(f"Unknown scenario ID '{scenario_id}'. Must be one of S1..S12.")
