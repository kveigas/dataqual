from __future__ import annotations

import json
import uuid
from collections import Counter, defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from dataqual import __version__
from dataqual.analysis.core import (
    Annotation,
    Gold,
    bootstrap_item_statistic,
    distribution,
    evidence_level,
    group_annotations,
    mean,
    median_float,
    nominal_alpha,
    pooled_percent_agreement,
)
from dataqual.analysis.gold import (
    annotations_by_item,
    calculate_gold_metrics,
    gold_metric_from_groups,
    gold_status_counts,
)
from dataqual.analysis.models import (
    AgreementResponse,
    AnalysisBundle,
    AnalysisProvenance,
    AnnotatorEvidence,
    EvidenceLevel,
    EvidenceSummary,
    GoldMetricsResponse,
    OverlapSummary,
    PairwiseAgreement,
    ResultStatus,
    StatisticalResult,
)
from dataqual.provenance import canonical_json_bytes, git_identity, sha256_bytes
from dataqual.storage import DatasetRepository

METHOD_VERSION = "phase2-evidence-1.0.0"
DEFAULT_SEED = 20260809
DEFAULT_REPLICATES = 2000


class AnalysisNotFoundError(KeyError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _read_rows(path: Path) -> list[dict[str, Any]]:
    table = pq.read_table(path)
    if "_empty" in table.column_names:
        return []
    return table.to_pylist()


def _decode_labels(value: Any) -> list[str]:
    if isinstance(value, str):
        return list(json.loads(value))
    return list(value)


class AnalysisEngine:
    def __init__(self, repository: DatasetRepository) -> None:
        self.repository = repository
        self._cache: dict[tuple[str, int, int], AnalysisBundle] = {}

    def analyze(
        self, dataset_id: str, *, seed: int = DEFAULT_SEED, replicates: int = DEFAULT_REPLICATES
    ) -> AnalysisBundle:
        if seed < 0 or replicates < 1 or replicates > 10_000:
            raise ValueError("seed must be nonnegative and replicates must be between 1 and 10000")
        cache_key = (dataset_id, seed, replicates)
        if cache_key in self._cache:
            return self._cache[cache_key]
        detail = self.repository.get_dataset(dataset_id)
        path = self.repository.dataset_path(dataset_id)
        if detail is None or path is None:
            raise AnalysisNotFoundError(dataset_id)
        all_rows = _read_rows(path / "annotations.parquet")
        current_rows = [row for row in all_rows if row["is_current"]]
        annotations = [
            Annotation(
                str(row["annotation_id"]),
                str(row["item_id"]),
                str(row["annotator_id"]),
                str(row["label"]),
            )
            for row in current_rows
        ]
        item_rows = _read_rows(path / "items.parquet")
        annotator_rows = _read_rows(path / "annotators.parquet")
        domain_rows = _read_rows(path / "label_domain.parquet")
        labels = _decode_labels(domain_rows[0]["labels"])
        raw_gold = _read_rows(path / "gold_labels.parquet")
        latest_gold: dict[str, dict[str, Any]] = {}
        for row in raw_gold:
            current = latest_gold.get(str(row["item_id"]))
            if current is None or int(row["version"]) > int(current["version"]):
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
        configuration = {
            "seed": seed,
            "replicates": replicates,
            "confidence_level": 0.95,
            "resampling_unit": "item",
            "interval_method": "percentile",
            "event_selection": "current_only",
        }
        configuration_hash = sha256_bytes(canonical_json_bytes(configuration))
        run_id = f"analysis_{uuid.uuid4().hex}"
        computed_at = _now()
        git_commit, git_dirty = git_identity(self.repository.root.parent)

        def provenance(method: str) -> AnalysisProvenance:
            return AnalysisProvenance(
                analysis_run_id=run_id,
                dataset_id=dataset_id,
                dataset_snapshot_id=dataset_id,
                canonical_artifact_checksum=detail.canonical_snapshot_checksum,
                method_identifier=method,
                method_version=METHOD_VERSION,
                configuration_hash=configuration_hash,
                computed_at=computed_at,
                software_version=__version__,
                git_commit=git_commit,
                git_dirty=git_dirty,
            )

        groups_by_item = group_annotations(annotations)
        all_item_ids = [str(row["item_id"]) for row in item_rows]
        item_counts = [len(groups_by_item.get(item_id, [])) for item_id in all_item_ids]
        worker_counts = Counter(row.annotator_id for row in annotations)
        class_counts = dict.fromkeys(labels, 0)
        class_counts.update(Counter(row.label for row in annotations))
        hard_gold_items = {row.item_id for row in gold if row.resolution_status == "resolved_hard"}
        coannotated = sum(count >= 2 for count in item_counts)
        evidence = EvidenceSummary(
            dataset_id=dataset_id,
            analysis_run_id=run_id,
            annotation_event_count=len(annotations),
            all_annotation_event_count=len(all_rows),
            superseded_annotation_event_count=len(all_rows) - len(annotations),
            unique_item_count=len(item_rows),
            unique_annotator_count=len(annotator_rows),
            class_count=len(labels),
            gold_item_count=len(hard_gold_items),
            gold_coverage_fraction=len(hard_gold_items) / len(item_rows) if item_rows else 0.0,
            mean_annotations_per_item=mean(item_counts),
            median_annotations_per_item=median_float(item_counts),
            min_annotations_per_item=min(item_counts, default=0),
            max_annotations_per_item=max(item_counts, default=0),
            mean_annotations_per_annotator=mean(list(worker_counts.values())),
            median_annotations_per_annotator=median_float(list(worker_counts.values())),
            coannotated_item_count=coannotated,
            coannotated_item_fraction=coannotated / len(item_rows) if item_rows else 0.0,
            items_with_1_annotation=sum(count == 1 for count in item_counts),
            items_with_2_annotations=sum(count == 2 for count in item_counts),
            items_with_3plus_annotations=sum(count >= 3 for count in item_counts),
            class_counts=dict(class_counts),
            class_proportions={
                label: count / len(annotations) if annotations else 0.0
                for label, count in class_counts.items()
            },
            labels_per_item_distribution=distribution(item_counts),
            labels_per_annotator_distribution=distribution(worker_counts.values()),
            evidence_level=evidence_level(len(item_rows)),
            provenance=provenance("dataqual.descriptive.evidence"),
        )

        overlap, pair_groups = self._overlap(annotations, all_item_ids)
        pairable_groups = [group for group in groups_by_item.values() if len(group) >= 2]
        agreement_value, pairable_items, compared_pairs, agreeing_pairs = pooled_percent_agreement(
            pairable_groups
        )
        agreement_ci = None
        agreement_warning = None
        if agreement_value is not None:
            agreement_ci, agreement_warning = bootstrap_item_statistic(
                pairable_groups,
                lambda sampled: pooled_percent_agreement(sampled)[0],
                estimate=agreement_value,
                seed=seed,
                replicates=replicates,
                population="items with at least two current annotation events",
            )
        agreement_warnings = [agreement_warning] if agreement_warning else []
        dataset_agreement = self._result(
            metric="raw_percent_agreement",
            value=agreement_value,
            status=ResultStatus.SUCCESS
            if agreement_value is not None
            else ResultStatus.INSUFFICIENT_EVIDENCE,
            level=evidence_level(pairable_items),
            support={
                "pairable_items": pairable_items,
                "compared_unordered_pairs": compared_pairs,
                "agreeing_unordered_pairs": agreeing_pairs,
            },
            uncertainty=agreement_ci,
            method="dataqual.agreement.pooled_unordered_pairs",
            configuration=configuration,
            config_hash=configuration_hash,
            provenance=provenance("dataqual.agreement.pooled_unordered_pairs"),
            warnings=agreement_warnings,
            reason=None if agreement_value is not None else "no_pairable_items",
        )
        alpha_components = nominal_alpha(pairable_groups)
        alpha_ci = None
        alpha_warning = None
        if alpha_components.value is not None:
            alpha_ci, alpha_warning = bootstrap_item_statistic(
                pairable_groups,
                lambda sampled: nominal_alpha(sampled).value,
                estimate=alpha_components.value,
                seed=seed,
                replicates=replicates,
                population="pairable items contributing to nominal Krippendorff alpha",
            )
        alpha_warnings = [alpha_warning] if alpha_warning else []
        alpha = self._result(
            metric="krippendorff_alpha_nominal",
            value=alpha_components.value,
            status=alpha_components.status,
            level=evidence_level(alpha_components.pairable_items),
            support={
                "pairable_items": alpha_components.pairable_items,
                "annotations": alpha_components.annotations,
                "categories": alpha_components.categories,
                "observed_disagreement": alpha_components.observed_disagreement
                if alpha_components.observed_disagreement is not None
                else "undefined",
                "expected_disagreement": alpha_components.expected_disagreement
                if alpha_components.expected_disagreement is not None
                else "undefined",
            },
            uncertainty=alpha_ci,
            method="dataqual.agreement.krippendorff_alpha_nominal",
            configuration=configuration,
            config_hash=configuration_hash,
            provenance=provenance("dataqual.agreement.krippendorff_alpha_nominal"),
            warnings=alpha_warnings,
            reason=alpha_components.reason,
        )
        # Add pairwise CIs after the common configuration is known.
        for pair in overlap.pairwise:
            if pair.shared_item_count >= 10 and pair.raw_percent_agreement is not None:
                groups = pair_groups[(pair.annotator_a, pair.annotator_b)]
                ci, warning = bootstrap_item_statistic(
                    groups,
                    lambda sampled: pooled_percent_agreement(sampled)[0],
                    estimate=pair.raw_percent_agreement,
                    seed=seed,
                    replicates=replicates,
                    population=f"items shared by {pair.annotator_a} and {pair.annotator_b}",
                )
                pair.uncertainty = ci
                if warning:
                    pair.warnings.append(warning)
        agreement = AgreementResponse(
            dataset_id=dataset_id,
            analysis_run_id=run_id,
            dataset_agreement=dataset_agreement,
            alpha=alpha,
            overlap=overlap,
        )
        overall_gold = self._gold_response(
            dataset_id,
            run_id,
            annotations,
            gold,
            labels,
            configuration,
            configuration_hash,
            provenance,
            seed,
            replicates,
            None,
        )
        annotator_evidence = []
        by_worker: dict[str, list[Annotation]] = defaultdict(list)
        for row in annotations:
            by_worker[row.annotator_id].append(row)
        pair_counts = Counter()
        for pair in overlap.pairwise:
            if pair.shared_item_count:
                pair_counts[pair.annotator_a] += 1
                pair_counts[pair.annotator_b] += 1
        for worker_id in sorted(str(row["annotator_id"]) for row in annotator_rows):
            rows = by_worker.get(worker_id, [])
            worker_gold = calculate_gold_metrics(rows, gold, labels)
            annotator_evidence.append(
                AnnotatorEvidence(
                    annotator_id=worker_id,
                    annotation_count=len(rows),
                    items_covered=len({row.item_id for row in rows}),
                    gold_items=len({row.item_id for row in worker_gold.evaluated}),
                    classes_used=len({row.label for row in rows}),
                    overlapping_annotators=pair_counts[worker_id],
                    gold_accuracy=worker_gold.accuracy,
                    macro_f1=worker_gold.macro_f1,
                    gold_support=len(worker_gold.evaluated),
                    evidence_level=evidence_level(len(worker_gold.evaluated)),
                )
            )
        bundle = AnalysisBundle(
            dataset_id=dataset_id,
            analysis_run_id=run_id,
            evidence=evidence,
            agreement=agreement,
            gold_metrics=overall_gold,
            annotators=annotator_evidence,
        )
        self.repository.save_analysis_result(run_id, bundle)
        self._cache[cache_key] = bundle
        return bundle

    @staticmethod
    def _result(
        *,
        metric: str,
        value: Any,
        status: ResultStatus,
        level: EvidenceLevel,
        support: dict[str, int | float | str],
        uncertainty: Any,
        method: str,
        configuration: dict[str, Any],
        config_hash: str,
        provenance: AnalysisProvenance,
        warnings: list[str],
        reason: str | None,
    ) -> StatisticalResult:
        return StatisticalResult(
            metric_name=metric,
            value=value,
            status=status,
            evidence_level=level,
            support=support,
            uncertainty=uncertainty,
            method_identifier=method,
            method_version=METHOD_VERSION,
            configuration=configuration,
            configuration_hash=config_hash,
            provenance=provenance,
            warnings=warnings,
            failure_reason=reason,
        )

    @staticmethod
    def _overlap(
        annotations: list[Annotation], all_item_ids: list[str]
    ) -> tuple[OverlapSummary, dict[tuple[str, str], list[list[Annotation]]]]:
        by_item = group_annotations(annotations)
        workers = sorted({row.annotator_id for row in annotations})
        overlap_counts = {worker: {} for worker in workers}
        pair_groups: dict[tuple[str, str], list[list[Annotation]]] = defaultdict(list)
        for item_id, group in by_item.items():
            unique = {row.annotator_id: row for row in group}
            ids = sorted(unique)
            for worker in ids:
                overlap_counts[worker][item_id] = 1
            for left_index, left in enumerate(ids):
                for right in ids[left_index + 1 :]:
                    pair_groups[(left, right)].append([unique[left], unique[right]])
        pairs: list[PairwiseAgreement] = []
        adjacency = {worker: set() for worker in workers}
        shared_totals = Counter()
        for left_index, left in enumerate(workers):
            for right in workers[left_index + 1 :]:
                groups = pair_groups.get((left, right), [])
                shared = len(groups)
                agreements = sum(group[0].label == group[1].label for group in groups)
                value = agreements / shared if shared else None
                status = ResultStatus.SUCCESS if shared else ResultStatus.UNAVAILABLE
                warnings = []
                if 0 < shared < 20:
                    warnings.append("shared_item_support_below_20")
                if shared:
                    adjacency[left].add(right)
                    adjacency[right].add(left)
                    shared_totals[left] += shared
                    shared_totals[right] += shared
                pairs.append(
                    PairwiseAgreement(
                        annotator_a=left,
                        annotator_b=right,
                        shared_item_count=shared,
                        agreements=agreements,
                        disagreements=shared - agreements,
                        raw_percent_agreement=value,
                        status=status,
                        evidence_level=evidence_level(shared),
                        warnings=warnings,
                    )
                )
        components = 0
        largest = 0
        unseen = set(workers)
        while unseen:
            components += 1
            start = min(unseen)
            queue = deque([start])
            unseen.remove(start)
            size = 0
            while queue:
                node = queue.popleft()
                size += 1
                for neighbor in adjacency[node] & unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
            largest = max(largest, size)
        return OverlapSummary(
            worker_item_overlap_counts=overlap_counts,
            graph_node_count=len(workers),
            graph_edge_count=sum(bool(groups) for groups in pair_groups.values()),
            connected_component_count=components,
            largest_component_size=largest,
            isolated_workers=sorted(worker for worker in workers if not adjacency[worker]),
            isolated_items=sorted(item for item in all_item_ids if len(by_item.get(item, [])) <= 1),
            worker_degrees={worker: len(adjacency[worker]) for worker in workers},
            worker_shared_item_totals={worker: shared_totals[worker] for worker in workers},
            pairwise=pairs,
        ), pair_groups

    def _gold_response(
        self,
        dataset_id: str,
        run_id: str,
        annotations: list[Annotation],
        gold: list[Gold],
        labels: list[str],
        config: dict[str, Any],
        config_hash: str,
        provenance_factory: Any,
        seed: int,
        replicates: int,
        annotator_id: str | None,
    ) -> GoldMetricsResponse:
        selected = [
            row for row in annotations if annotator_id is None or row.annotator_id == annotator_id
        ]
        calculated = calculate_gold_metrics(selected, gold, labels)
        status_counts = gold_status_counts(gold)
        groups = annotations_by_item(calculated.evaluated)
        metrics = {
            "accuracy": calculated.accuracy,
            "macro_precision": calculated.macro_precision,
            "macro_recall": calculated.macro_recall,
            "macro_f1": calculated.macro_f1,
            "micro_precision": calculated.micro_precision,
            "micro_recall": calculated.micro_recall,
            "micro_f1": calculated.micro_f1,
        }
        results: dict[str, StatisticalResult] = {}
        for offset, (name, value) in enumerate(metrics.items()):
            ci = None
            warnings: list[str] = []
            if (
                value is not None
                and annotator_id is None
                and name in {"accuracy", "macro_precision", "macro_recall", "macro_f1"}
            ):
                ci, warning = bootstrap_item_statistic(
                    groups,
                    lambda sampled, metric=name: gold_metric_from_groups(
                        sampled, gold, labels, metric
                    ),
                    estimate=value,
                    seed=seed + offset,
                    replicates=replicates,
                    population="items with resolved hard gold and current annotations",
                )
                if warning:
                    warnings.append(warning)
            if annotator_id is not None:
                warnings.append("per_annotator_bayesian_reliability_deferred_by_phase2_scope")
            method = f"dataqual.gold.{name}"
            results[name] = self._result(
                metric=f"gold_{name}",
                value=value,
                status=ResultStatus.SUCCESS if value is not None else ResultStatus.UNAVAILABLE,
                level=evidence_level(
                    len(calculated.evaluated),
                    smallest_display_support=min(
                        (
                            metric.gold_support
                            for metric in calculated.per_class
                            if metric.gold_support
                        ),
                        default=None,
                    ),
                ),
                support={
                    "evaluated_annotation_events": len(calculated.evaluated),
                    "evaluated_items": len({row.item_id for row in calculated.evaluated}),
                },
                uncertainty=ci,
                method=method,
                configuration=config,
                config_hash=config_hash,
                provenance=provenance_factory(method),
                warnings=warnings,
                reason=None if value is not None else "no_resolved_hard_gold_support",
            )
        return GoldMetricsResponse(
            dataset_id=dataset_id,
            analysis_run_id=run_id,
            annotator_id=annotator_id,
            gold_sources=sorted({record.gold_source for record in calculated.gold_records}),
            gold_label_record_ids=[record.gold_label_id for record in calculated.gold_records],
            evaluated_annotation_event_ids=[row.annotation_id for row in calculated.evaluated],
            excluded_distributional_gold_items=status_counts["resolved_distributional"],
            excluded_unresolved_gold_items=status_counts["unresolved"],
            accuracy=results["accuracy"],
            macro_precision=results["macro_precision"],
            macro_recall=results["macro_recall"],
            macro_f1=results["macro_f1"],
            micro_precision=results["micro_precision"],
            micro_recall=results["micro_recall"],
            micro_f1=results["micro_f1"],
            per_class=calculated.per_class,
            confusion=calculated.confusion,
        )

    def gold_for_annotator(
        self,
        dataset_id: str,
        annotator_id: str,
        *,
        seed: int = DEFAULT_SEED,
        replicates: int = DEFAULT_REPLICATES,
    ) -> GoldMetricsResponse:
        bundle = self.analyze(dataset_id, seed=seed, replicates=replicates)
        # Reuse the canonical result payload to reject unknown workers honestly.
        if annotator_id not in {row.annotator_id for row in bundle.annotators}:
            raise AnalysisNotFoundError(annotator_id)
        # The cached aggregate does not retain source rows; reload this immutable snapshot.
        # would create a different run. Instead filter through a compact copy of the same snapshot.
        path = self.repository.dataset_path(dataset_id)
        assert path is not None
        rows = _read_rows(path / "annotations.parquet")
        annotations = [
            Annotation(
                str(row["annotation_id"]),
                str(row["item_id"]),
                str(row["annotator_id"]),
                str(row["label"]),
            )
            for row in rows
            if row["is_current"]
        ]
        domain = _read_rows(path / "label_domain.parquet")
        labels = _decode_labels(domain[0]["labels"])
        raw_gold = _read_rows(path / "gold_labels.parquet")
        gold = [
            Gold(
                str(row["gold_label_id"]),
                str(row["item_id"]),
                str(row["label"]) if row["label"] is not None else None,
                str(row["resolution_status"]),
                str(row["gold_source"]),
            )
            for row in raw_gold
        ]
        config = bundle.gold_metrics.accuracy.configuration
        config_hash = bundle.gold_metrics.accuracy.configuration_hash
        base_prov = bundle.gold_metrics.accuracy.provenance
        return self._gold_response(
            dataset_id,
            bundle.analysis_run_id,
            annotations,
            gold,
            labels,
            config,
            config_hash,
            lambda method: base_prov.model_copy(update={"method_identifier": method}),
            seed,
            replicates,
            annotator_id,
        )
