from __future__ import annotations

import json
import math
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from dataqual import __version__
from dataqual.analysis.core import Annotation, Gold
from dataqual.analysis.models import AnalysisProvenance
from dataqual.consensus.dawid_skene import ComponentFit, fit_dawid_skene
from dataqual.consensus.models import (
    ConsensusComparison,
    ConsensusComparisonItem,
    ConsensusMethod,
    ConsensusResult,
    ConsensusRun,
    ConsensusRunRequest,
    ConsensusStatus,
    ConvergenceDiagnostics,
    PaginatedConsensusItems,
    WeightedVoteCoverage,
    WorkerConfusionEstimate,
)
from dataqual.consensus.vote import VoteOutcome, majority_vote, reliability_weighted_vote
from dataqual.provenance import canonical_json_bytes, git_identity, sha256_bytes
from dataqual.storage import DatasetRepository

METHOD_VERSION = "phase3-consensus-1.0.0"


class ConsensusNotFoundError(KeyError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _read(path: Path) -> list[dict[str, Any]]:
    table = pq.read_table(path)
    return [] if "_empty" in table.column_names else table.to_pylist()


def _labels(value: Any) -> list[str]:
    return list(json.loads(value)) if isinstance(value, str) else list(value)


def _entropy(probabilities: dict[str, float]) -> float:
    return -math.fsum(value * math.log(value) for value in probabilities.values() if value > 0)


def _result_id(run_id: str, method: str, item_id: str) -> str:
    digest = sha256_bytes(canonical_json_bytes([run_id, method, item_id]))
    return f"result_{digest[:24]}"


class ConsensusService:
    def __init__(self, repository: DatasetRepository) -> None:
        self.repository = repository

    def create_run(self, dataset_id: str, request: ConsensusRunRequest) -> ConsensusRun:
        detail = self.repository.get_dataset(dataset_id)
        path = self.repository.dataset_path(dataset_id)
        if detail is None or path is None:
            raise ConsensusNotFoundError(dataset_id)
        annotation_rows = _read(path / "annotations.parquet")
        annotations = [
            Annotation(
                str(row["annotation_id"]),
                str(row["item_id"]),
                str(row["annotator_id"]),
                str(row["label"]),
            )
            for row in annotation_rows
            if row["is_current"] and row["annotation_source"] in {"human", "ai_assisted"}
        ]
        domain = _read(path / "label_domain.parquet")
        labels = _labels(domain[0]["labels"])
        project_id = detail.project_id
        gold_rows = _read(path / "gold_labels.parquet")
        latest_gold: dict[str, dict[str, Any]] = {}
        for row in gold_rows:
            previous = latest_gold.get(str(row["item_id"]))
            if previous is None or int(row["version"]) > int(previous["version"]):
                latest_gold[str(row["item_id"])] = row
        gold = [
            Gold(
                str(row["gold_label_id"]),
                str(row["item_id"]),
                str(row["label"]) if row["label"] is not None else None,
                str(row["resolution_status"]),
                str(row["gold_source"]),
            )
            for row in latest_gold.values()
        ]
        created_at = _now()
        run_id = f"consensus_{uuid.uuid4().hex}"
        configuration = request.model_dump(mode="json")
        config_hash = sha256_bytes(canonical_json_bytes(configuration))
        git_commit, git_dirty = git_identity(self.repository.root.parent)

        def provenance(method: str) -> AnalysisProvenance:
            return AnalysisProvenance(
                analysis_run_id=run_id,
                dataset_id=dataset_id,
                dataset_snapshot_id=dataset_id,
                canonical_artifact_checksum=detail.canonical_snapshot_checksum,
                method_identifier=method,
                method_version=METHOD_VERSION,
                configuration_hash=config_hash,
                computed_at=created_at,
                software_version=__version__,
                git_commit=git_commit,
                git_dirty=git_dirty,
            )

        results: list[ConsensusResult] = []
        weighted_coverage: WeightedVoteCoverage | None = None
        fits: list[ComponentFit] = []
        workers: list[WorkerConfusionEstimate] = []
        convergence: list[ConvergenceDiagnostics] = []
        if ConsensusMethod.MAJORITY_VOTE in request.methods:
            results.extend(
                self._vote_results(
                    majority_vote(annotations, labels),
                    ConsensusMethod.MAJORITY_VOTE,
                    run_id,
                    dataset_id,
                    project_id,
                    created_at,
                    config_hash,
                    configuration,
                    provenance("dataqual.consensus.majority_vote"),
                )
            )
        if ConsensusMethod.RELIABILITY_WEIGHTED_VOTE in request.methods:
            assert request.gold_partition is not None
            weighted, weighted_coverage = reliability_weighted_vote(
                annotations,
                gold,
                labels,
                request.gold_partition,
                request.minimum_development_gold,
            )
            results.extend(
                self._vote_results(
                    weighted,
                    ConsensusMethod.RELIABILITY_WEIGHTED_VOTE,
                    run_id,
                    dataset_id,
                    project_id,
                    created_at,
                    config_hash,
                    configuration,
                    provenance("dataqual.consensus.reliability_weighted_vote"),
                )
            )
        if ConsensusMethod.DAWID_SKENE in request.methods:
            fits = fit_dawid_skene(annotations, labels, request.ds)
            ds_results, workers, convergence = self._ds_results(
                fits,
                annotations,
                run_id,
                dataset_id,
                project_id,
                labels,
                created_at,
                config_hash,
                configuration,
                provenance("dataqual.consensus.dawid_skene"),
                request,
            )
            results.extend(ds_results)
        comparison = self._comparison(run_id, annotations, results)
        ds_statuses = {fit.status for fit in fits}
        if ConsensusStatus.FAILED in ds_statuses:
            run_status = ConsensusStatus.FAILED
        elif ConsensusStatus.NON_CONVERGED in ds_statuses:
            run_status = ConsensusStatus.NON_CONVERGED
        elif fits and all(fit.status == ConsensusStatus.INSUFFICIENT_EVIDENCE for fit in fits):
            run_status = ConsensusStatus.INSUFFICIENT_EVIDENCE
        else:
            run_status = ConsensusStatus.SUCCESS
        warnings = []
        if len(fits) > 1:
            warnings.append("worker_confusion_estimates_not_comparable_across_components")
        if weighted_coverage and weighted_coverage.coverage_fraction < 1:
            warnings.append("weighted_vote_coverage_loss")
        run = ConsensusRun(
            analysis_run_id=run_id,
            dataset_id=dataset_id,
            project_id=project_id,
            canonical_artifact_checksum=detail.canonical_snapshot_checksum,
            status=run_status,
            methods=request.methods,
            configuration=configuration,
            configuration_hash=config_hash,
            created_at=created_at,
            software_version=__version__,
            git_commit=git_commit,
            git_dirty=git_dirty,
            items=sorted(results, key=lambda row: (row.item_id, row.method.value)),
            workers=sorted(workers, key=lambda row: row.annotator_id),
            convergence=convergence,
            weighted_vote_coverage=weighted_coverage,
            comparison=comparison,
            warnings=warnings,
        )
        self.repository.save_consensus_run(run_id, run)
        return run

    @staticmethod
    def _vote_results(
        outcomes: list[VoteOutcome],
        method: ConsensusMethod,
        run_id: str,
        dataset_id: str,
        project_id: str,
        created_at: str,
        config_hash: str,
        configuration: dict[str, Any],
        provenance: AnalysisProvenance,
    ) -> list[ConsensusResult]:
        return [
            ConsensusResult(
                result_id=_result_id(run_id, method.value, row.item_id),
                analysis_run_id=run_id,
                dataset_id=dataset_id,
                project_id=project_id,
                item_id=row.item_id,
                method=method,
                method_version=METHOD_VERSION,
                status=row.status,
                label=row.label,
                probabilities=row.probabilities,
                vote_counts=row.counts,
                scores=row.scores,
                confidence=row.confidence,
                uncertainty=row.uncertainty,
                posterior_entropy=row.entropy,
                support=row.support,
                workers_used=row.workers_used,
                excluded_workers=row.excluded_workers,
                configuration=configuration,
                configuration_hash=config_hash,
                provenance=provenance,
                warnings=[
                    "vote_share_is_descriptive_not_calibrated_confidence"
                    if method == ConsensusMethod.MAJORITY_VOTE
                    else "gold_weight_transfer_assumption"
                ],
                created_at=created_at,
            )
            for row in outcomes
        ]

    @staticmethod
    def _ds_results(
        fits: list[ComponentFit],
        annotations: list[Annotation],
        run_id: str,
        dataset_id: str,
        project_id: str,
        labels: list[str],
        created_at: str,
        config_hash: str,
        configuration: dict[str, Any],
        provenance: AnalysisProvenance,
        request: ConsensusRunRequest,
    ) -> tuple[list[ConsensusResult], list[WorkerConfusionEstimate], list[ConvergenceDiagnostics]]:
        by_item: dict[str, list[Annotation]] = defaultdict(list)
        by_worker: dict[str, list[Annotation]] = defaultdict(list)
        for row in annotations:
            by_item[row.item_id].append(row)
            by_worker[row.annotator_id].append(row)
        results = []
        workers = []
        diagnostics = []
        for fit in fits:
            component = fit.component
            for index, item_id in enumerate(component.item_ids):
                probabilities = {
                    label: float(fit.posteriors[index, position])
                    for position, label in enumerate(labels)
                }
                maximum = max(probabilities.values())
                winners = [
                    label for label, value in probabilities.items() if abs(value - maximum) <= 1e-12
                ]
                successful = fit.status == ConsensusStatus.SUCCESS
                label = winners[0] if successful and len(winners) == 1 else None
                status = fit.status
                if successful and len(winners) != 1:
                    status = ConsensusStatus.UNRESOLVED
                rows = by_item[item_id]
                results.append(
                    ConsensusResult(
                        result_id=_result_id(run_id, "ds", item_id),
                        analysis_run_id=run_id,
                        dataset_id=dataset_id,
                        project_id=project_id,
                        item_id=item_id,
                        method=ConsensusMethod.DAWID_SKENE,
                        method_version=METHOD_VERSION,
                        status=status,
                        label=label,
                        probabilities=probabilities,
                        confidence=maximum if successful else None,
                        uncertainty=1.0 - maximum if successful else None,
                        posterior_entropy=_entropy(probabilities) if successful else None,
                        support=len(rows),
                        workers_used=sorted(row.annotator_id for row in rows),
                        excluded_workers={},
                        configuration=configuration,
                        configuration_hash=config_hash,
                        provenance=provenance,
                        component_id=component.component_id,
                        warnings=[
                            "posterior_is_model_conditional_not_calibrated",
                            *fit.warnings,
                        ],
                        created_at=created_at,
                    )
                )
            for worker_index, worker_id in enumerate(component.worker_ids):
                rows = by_worker[worker_id]
                workers.append(
                    WorkerConfusionEstimate(
                        annotator_id=worker_id,
                        analysis_run_id=run_id,
                        labels=labels,
                        probabilities=fit.worker_confusion[worker_index].tolist(),
                        support=len(rows),
                        classes_observed=sorted({row.label for row in rows}, key=labels.index),
                        component_id=component.component_id,
                        warnings=["model_estimated_latent_confusion_not_gold_accuracy"],
                    )
                )
            initial_prior = {
                label: float(fit.initial_class_prior[index]) for index, label in enumerate(labels)
            }
            final_prior = {
                label: float(fit.class_prior[index]) for index, label in enumerate(labels)
            }
            diagnostics.append(
                ConvergenceDiagnostics(
                    converged=fit.converged,
                    iterations=fit.iterations,
                    stopping_reason=fit.stopping_reason,
                    tolerance_absolute=request.ds.absolute_tolerance,
                    tolerance_relative=request.ds.relative_tolerance,
                    max_iterations=request.ds.max_iterations,
                    initialization_method=request.ds.initialization,
                    initial_class_prior=initial_prior,
                    final_class_prior=final_prior,
                    final_log_likelihood=fit.likelihood_history[-1]
                    if fit.likelihood_history
                    else None,
                    final_delta=fit.final_delta,
                    log_likelihood_history=fit.likelihood_history,
                    monotonicity_tolerance=1e-8,
                    component_id=component.component_id,
                    items=len(component.item_ids),
                    workers=len(component.worker_ids),
                    annotations=len(component.observations),
                    observed_classes=len({row[2] for row in component.observations}),
                )
            )
        return results, workers, diagnostics

    @staticmethod
    def _comparison(
        run_id: str, annotations: list[Annotation], results: list[ConsensusResult]
    ) -> ConsensusComparison:
        by_item_method = {(row.item_id, row.method.value): row for row in results}
        raw_by_item: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in annotations:
            raw_by_item[row.item_id].append({"annotator_id": row.annotator_id, "label": row.label})
        item_ids = sorted({row.item_id for row in results})
        comparison_items = []
        counters: Counter[str] = Counter()
        for item_id in item_ids:
            method_rows = {
                method: by_item_method[(item_id, method)]
                for method in (method.value for method in ConsensusMethod)
                if (item_id, method) in by_item_method
            }
            labels = {method: row.label for method, row in method_rows.items()}
            classes = []
            if any(row.status != ConsensusStatus.SUCCESS for row in method_rows.values()):
                classes.append("tie_or_unresolved")
                counters["tie_or_unresolved"] += 1
            mv, ds, weighted = (
                labels.get(ConsensusMethod.MAJORITY_VOTE.value),
                labels.get(ConsensusMethod.DAWID_SKENE.value),
                labels.get(ConsensusMethod.RELIABILITY_WEIGHTED_VOTE.value),
            )
            successful_labels = [row.label for row in method_rows.values() if row.label is not None]
            if len(successful_labels) >= 2 and len(set(successful_labels)) == 1:
                classes.append("same_label_all_methods")
                counters["same_label_all_methods"] += 1
            if mv is not None and ds is not None and mv != ds:
                classes.append("mv_vs_ds_disagreement")
                counters["mv_vs_ds_disagreement"] += 1
            if weighted is not None and mv is not None and weighted != mv:
                classes.append("weighted_vs_mv_disagreement")
                counters["weighted_vs_mv_disagreement"] += 1
            if weighted is not None and ds is not None and weighted != ds:
                classes.append("weighted_vs_ds_disagreement")
                counters["weighted_vs_ds_disagreement"] += 1
            comparison_items.append(
                ConsensusComparisonItem(
                    item_id=item_id,
                    classification=classes,
                    labels=labels,
                    probabilities={
                        method: row.probabilities for method, row in method_rows.items()
                    },
                    raw_votes=sorted(raw_by_item[item_id], key=lambda row: row["annotator_id"]),
                    analysis_run_id=run_id,
                )
            )
        dependent = sum(
            bool(
                set(row.classification)
                & {
                    "mv_vs_ds_disagreement",
                    "weighted_vs_mv_disagreement",
                    "weighted_vs_ds_disagreement",
                    "tie_or_unresolved",
                }
            )
            for row in comparison_items
        )
        return ConsensusComparison(
            analysis_run_id=run_id,
            compared_items=len(item_ids),
            same_label_all_methods=counters["same_label_all_methods"],
            mv_vs_ds_disagreement=counters["mv_vs_ds_disagreement"],
            weighted_vs_mv_disagreement=counters["weighted_vs_mv_disagreement"],
            weighted_vs_ds_disagreement=counters["weighted_vs_ds_disagreement"],
            tie_or_unresolved=counters["tie_or_unresolved"],
            method_dependent_fraction=dependent / len(item_ids) if item_ids else 0.0,
            items=comparison_items,
        )

    def get_run(self, run_id: str) -> ConsensusRun:
        payload = self.repository.load_consensus_run_bytes(run_id)
        if payload is None:
            raise ConsensusNotFoundError(run_id)
        return ConsensusRun.model_validate_json(payload)

    def items(
        self,
        run_id: str,
        *,
        offset: int,
        limit: int,
        method: ConsensusMethod | None = None,
    ) -> PaginatedConsensusItems:
        run = self.get_run(run_id)
        selected = [row for row in run.items if method is None or row.method == method]
        return PaginatedConsensusItems(
            analysis_run_id=run_id,
            total=len(selected),
            offset=offset,
            limit=limit,
            items=selected[offset : offset + limit],
        )
