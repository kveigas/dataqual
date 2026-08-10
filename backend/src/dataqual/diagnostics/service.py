from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from dataqual.analysis.core import Annotation
from dataqual.consensus.models import ConsensusRun
from dataqual.diagnostics.config import DEFAULT_DIAGNOSTIC_CONFIG, DiagnosticThresholdConfig
from dataqual.diagnostics.features import extract_item_disagreement_features
from dataqual.diagnostics.rules import evaluate_item_diagnostics
from dataqual.schemas.core import GoldLabel
from dataqual.schemas.diagnostics import DiagnosticSummary, ItemDisagreementFeatures, QualityFlag


class DisagreementDiagnosticsService:
    def __init__(
        self,
        annotations: Sequence[Annotation],
        gold_labels: Sequence[GoldLabel],
        labels: Sequence[str],
        dataset_snapshot_id: str,
        project_id: str,
        threshold_config: DiagnosticThresholdConfig = DEFAULT_DIAGNOSTIC_CONFIG,
    ) -> None:
        self.annotations = annotations
        self.gold_labels = gold_labels
        self.labels = list(labels)
        self.dataset_snapshot_id = dataset_snapshot_id
        self.project_id = project_id
        self.config = threshold_config

        # Group annotations by item
        self.by_item: dict[str, list[Annotation]] = defaultdict(list)
        for a in annotations:
            self.by_item[a.item_id].append(a)

    def extract_all_features(
        self, consensus_run: ConsensusRun | None = None
    ) -> dict[str, ItemDisagreementFeatures]:
        features_map: dict[str, ItemDisagreementFeatures] = {}
        for item_id, item_annos in self.by_item.items():
            feat = extract_item_disagreement_features(
                item_id,
                item_annos,
                self.labels,
                self.annotations,
                self.gold_labels,
                consensus_run=consensus_run,
            )
            features_map[item_id] = feat
        return features_map

    def generate_quality_flags(
        self, consensus_run: ConsensusRun | None = None
    ) -> list[QualityFlag]:
        features_map = self.extract_all_features(consensus_run=consensus_run)
        all_flags: list[QualityFlag] = []
        for item_id, feat in features_map.items():
            item_annos = self.by_item[item_id]
            flags = evaluate_item_diagnostics(
                feat,
                item_annos,
                self.dataset_snapshot_id,
                self.project_id,
                cfg=self.config,
            )
            all_flags.extend(flags)
        return all_flags

    def summarize(self, flags: list[QualityFlag]) -> DiagnosticSummary:
        flag_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        entity_type_counts = defaultdict(int)
        items_with_flags = set()

        for flag in flags:
            flag_counts[flag.flag_type] += 1
            severity_counts[flag.severity] += 1
            entity_type_counts[flag.entity_type] += 1
            if flag.flag_type != "no_flag":
                items_with_flags.add(flag.entity_id)

        return DiagnosticSummary(
            total_items=len(self.by_item),
            items_with_flags=len(items_with_flags),
            flag_counts=dict(flag_counts),
            severity_counts=dict(severity_counts),
            entity_type_counts=dict(entity_type_counts),
        )
