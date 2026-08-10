from __future__ import annotations

import datetime
from typing import Any

import numpy as np
import scipy.stats as stats
from pydantic import BaseModel

from dataqual.benchmarking.metrics import BenchmarkResult, evaluate_review_candidates
from dataqual.prioritization.config import DEFAULT_ERV_CONFIG
from dataqual.prioritization.service import ReviewPrioritizationService
from dataqual.simulation import SyntheticDatasetGenerator
from dataqual.simulation.scenarios import get_pre_registered_scenario_config


class PairedComparison(BaseModel):
    baseline_method: str
    target_method: str = "erv"
    metric_name: str
    mean_difference: float
    std_difference: float
    ci_lower_95: float
    ci_upper_95: float
    win_count: int
    tie_count: int
    loss_count: int


class ScenarioBenchmarkSummary(BaseModel):
    scenario_id: str
    review_unit: str
    seed_count: int
    methods: list[str]
    method_aurec_means: dict[str, float]
    method_aurec_stds: dict[str, float]
    method_precision_10_means: dict[str, float]
    method_recall_10_means: dict[str, float]
    paired_comparisons: list[PairedComparison]


class BenchmarkManifest(BaseModel):
    benchmark_run_id: str
    generated_at: str
    scenario_id: str
    seed_count: int
    world_seeds: list[int]
    random_ranking_seeds: list[int]
    erv_config_hash: str
    methods: list[str]
    summary: ScenarioBenchmarkSummary
    software_version: str = "4.0.0"


class BenchmarkRunner:
    def __init__(
        self,
        scenario_id: str,
        seed_count: int = 10,
        base_world_seed: int = 100,
        base_ranking_seed: int = 2026,
        review_unit: str = "annotation",
    ) -> None:
        self.scenario_id = scenario_id
        self.seed_count = seed_count
        self.world_seeds = [base_world_seed + i for i in range(seed_count)]
        self.ranking_seeds = [base_ranking_seed + i for i in range(seed_count)]
        self.review_unit = review_unit

    def run_benchmark(self) -> tuple[BenchmarkManifest, list[dict[str, Any]]]:
        methods = [
            "random",
            "highest_entropy",
            "lowest_consensus_confidence",
            "lowest_worker_reliability",
            "erv",
        ]

        raw_results_by_seed: list[dict[str, BenchmarkResult]] = []
        all_candidate_payloads: list[dict[str, Any]] = []

        for idx in range(self.seed_count):
            w_seed = self.world_seeds[idx]
            r_seed = self.ranking_seeds[idx]

            cfg = get_pre_registered_scenario_config(
                self.scenario_id, world_seed=w_seed, random_ranking_seed=r_seed
            )
            generator = SyntheticDatasetGenerator(cfg)
            annos, golds, hidden_truth = generator.generate()

            labels = list(cfg.label_classes)
            svc = ReviewPrioritizationService(annos, golds, labels)

            seed_results: dict[str, BenchmarkResult] = {}
            for m in methods:
                cands = svc.get_candidates(
                    method=m,
                    review_unit=self.review_unit,
                    random_ranking_seed=r_seed,
                )
                res = evaluate_review_candidates(cands, hidden_truth)
                seed_results[m] = res

                for c in cands:
                    all_candidate_payloads.append(
                        {
                            "seed_index": idx,
                            "world_seed": w_seed,
                            "random_ranking_seed": r_seed,
                            "scenario_id": self.scenario_id,
                            "method": m,
                            "rank": c.rank,
                            "candidate_id": c.candidate_id,
                            "item_id": c.item_id,
                            "annotation_id": c.annotation_id,
                            "score": c.score,
                            "is_eligible": c.eligible_coverage,
                        }
                    )

            raw_results_by_seed.append(seed_results)

        # Compute multi-seed summary
        method_aurecs: dict[str, list[float]] = {m: [] for m in methods}
        method_p10s: dict[str, list[float]] = {m: [] for m in methods}
        method_r10s: dict[str, list[float]] = {m: [] for m in methods}

        for seed_res in raw_results_by_seed:
            for m in methods:
                res = seed_res[m]
                method_aurecs[m].append(res.normalized_aurec_20)
                p10 = res.budget_metrics.get(
                    "10%", res.budget_metrics[next(iter(res.budget_metrics.keys()))]
                ).precision_at_k
                r10 = res.budget_metrics.get(
                    "10%", res.budget_metrics[next(iter(res.budget_metrics.keys()))]
                ).error_recall
                method_p10s[m].append(p10)
                method_r10s[m].append(r10)

        aurec_means = {m: float(np.mean(method_aurecs[m])) for m in methods}
        aurec_stds = {m: float(np.std(method_aurecs[m])) for m in methods}
        p10_means = {m: float(np.mean(method_p10s[m])) for m in methods}
        r10_means = {m: float(np.mean(method_r10s[m])) for m in methods}

        # Paired Comparisons: ERV vs each baseline
        paired_comps: list[PairedComparison] = []
        erv_aurecs = np.array(method_aurecs["erv"])

        for base_m in methods:
            if base_m == "erv":
                continue
            base_aurecs = np.array(method_aurecs[base_m])
            diffs = erv_aurecs - base_aurecs
            mean_diff = float(np.mean(diffs))
            std_diff = float(np.std(diffs))

            if self.seed_count > 1:
                se = std_diff / np.sqrt(self.seed_count)
                t_crit = stats.t.ppf(0.975, df=self.seed_count - 1)
                ci_l = float(mean_diff - t_crit * se)
                ci_u = float(mean_diff + t_crit * se)
            else:
                ci_l = mean_diff
                ci_u = mean_diff

            wins = int(np.sum(diffs > 1e-6))
            ties = int(np.sum(np.abs(diffs) <= 1e-6))
            losses = int(np.sum(diffs < -1e-6))

            paired_comps.append(
                PairedComparison(
                    baseline_method=base_m,
                    target_method="erv",
                    metric_name="normalized_aurec_20",
                    mean_difference=mean_diff,
                    std_difference=std_diff,
                    ci_lower_95=ci_l,
                    ci_upper_95=ci_u,
                    win_count=wins,
                    tie_count=ties,
                    loss_count=losses,
                )
            )

        summary = ScenarioBenchmarkSummary(
            scenario_id=self.scenario_id,
            review_unit=self.review_unit,
            seed_count=self.seed_count,
            methods=methods,
            method_aurec_means=aurec_means,
            method_aurec_stds=aurec_stds,
            method_precision_10_means=p10_means,
            method_recall_10_means=r10_means,
            paired_comparisons=paired_comps,
        )

        now_str = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")
        manifest = BenchmarkManifest(
            benchmark_run_id=f"run-{self.scenario_id.lower()}-{self.seed_count}seeds",
            generated_at=now_str,
            scenario_id=self.scenario_id,
            seed_count=self.seed_count,
            world_seeds=self.world_seeds,
            random_ranking_seeds=self.ranking_seeds,
            erv_config_hash=DEFAULT_ERV_CONFIG.config_hash(),
            methods=methods,
            summary=summary,
        )

        return manifest, all_candidate_payloads
