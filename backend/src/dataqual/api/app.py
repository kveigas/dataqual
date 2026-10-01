from __future__ import annotations

import datetime
import json
from functools import lru_cache
from typing import Annotated, Any, Literal, cast

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from dataqual import __version__
from dataqual.analysis import AnalysisBundle, AnalysisEngine
from dataqual.analysis.engine import DEFAULT_REPLICATES, DEFAULT_SEED, AnalysisNotFoundError
from dataqual.analysis.models import (
    AgreementResponse,
    AnnotatorEvidence,
    ConfusionMatrix,
    EvidenceSummary,
    GoldMetricsResponse,
    PairwiseAgreement,
    StatisticalResult,
)
from dataqual.config import Settings
from dataqual.consensus import ConsensusService
from dataqual.consensus.models import (
    ConsensusComparison,
    ConsensusMethod,
    ConsensusResult,
    ConsensusRun,
    ConsensusRunRequest,
    PaginatedConsensusItems,
    WorkerConfusionEstimate,
)
from dataqual.consensus.service import ConsensusNotFoundError
from dataqual.descriptive import DescriptiveQueries
from dataqual.ingestion import ImportLimitError, ImportService
from dataqual.prioritization.config import DEFAULT_ERV_CONFIG
from dataqual.prioritization.evidence import RANKING_VERSION, REVIEW_DS_CONFIG, review_features
from dataqual.prioritization.runs import ReviewRunQuotaError, ReviewRunStore, deterministic_run_id
from dataqual.schemas.imports import (
    DatasetDetail,
    DatasetSummary,
    ImportConfig,
    ImportRecord,
    ProvenanceResponse,
)
from dataqual.schemas.prioritization import ReviewUnit
from dataqual.storage import DatasetRepository
from dataqual.storage.repository import StorageError

Seed = Annotated[int, Query(ge=0)]
Replicates = Annotated[int, Query(ge=1, le=10_000)]


def _error(status: int, code: str, message: str, details: Any = None) -> JSONResponse:
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return JSONResponse(status_code=status, content=payload)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings.from_environment()
    repository = DatasetRepository(resolved.data_root)
    imports = ImportService(repository, resolved.max_upload_bytes)
    queries = DescriptiveQueries(repository)
    analysis = AnalysisEngine(repository)
    consensus = ConsensusService(repository)
    app = FastAPI(title="DataQual v4", version=__version__)
    app.state.repository = repository
    app.state.import_service = imports
    app.state.queries = queries
    app.state.analysis = analysis
    app.state.consensus = consensus

    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://kveigas.github.io",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_error(_request: Any, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            detail = cast(dict[str, Any], exc.detail)
            return _error(exc.status_code, str(detail["code"]), str(detail["message"]))
        return _error(exc.status_code, "http_error", str(exc.detail))

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.post("/api/v1/demo/bootstrap")
    def bootstrap_demo() -> dict[str, Any]:
        existing_datasets = repository.list_datasets()
        for ds in existing_datasets:
            if ds.dataset_name == "Synthetic Demo Dataset" and ds.dataset_version == "2.0.0":
                return {
                    "status": "ready",
                    "dataset_id": ds.dataset_id,
                    "dataset_name": ds.dataset_name,
                    "dataset_version": ds.dataset_version,
                    "is_existing": True,
                }

        from dataqual.simulation import SyntheticDatasetGenerator
        from dataqual.simulation.scenarios import get_pre_registered_scenario_config

        cfg = get_pre_registered_scenario_config("S12", world_seed=42)
        generator = SyntheticDatasetGenerator(cfg)
        annos, golds, _hidden_truth = generator.generate()

        gold_by_item = {g.item_id: g for g in golds}
        lines = [
            "annotation_id,item_id,annotator_id,label,event_version,annotation_source,gold_label,gold_source"
        ]
        for a in annos:
            gold = gold_by_item.get(a.item_id)
            lines.append(
                f"{a.annotation_id},{a.item_id},{a.annotator_id},{a.label},1,human,"
                f"{gold.label if gold else ''},{'simulation_truth' if gold else ''}"
            )
        csv_bytes = "\n".join(lines).encode("utf-8")

        import_cfg = ImportConfig(
            project_id="demo_s12",
            project_name="Synthetic Demo Project",
            label_domain_id="sentiment_v1",
            labels=["positive", "neutral", "negative"],
            dataset_name="Synthetic Demo Dataset",
            dataset_version="2.0.0",
            source_uri="synthetic://s12-demo",
            license="CC0-1.0",
            redistribution_allowed=True,
        )

        record = imports.import_bytes("demo_s12.csv", csv_bytes, import_cfg)
        assert record.dataset_id is not None

        return {
            "status": "ready",
            "dataset_id": record.dataset_id,
            "dataset_name": "Synthetic Demo Dataset",
            "dataset_version": "2.0.0",
            "imported_events": record.accepted_rows,
            "imported_golds": len(golds),
            "is_existing": False,
        }

    @app.post("/api/v1/imports", response_model=ImportRecord)
    async def create_import(
        file: Annotated[UploadFile, File()],
        config_json: Annotated[str, Form()],
    ) -> ImportRecord | JSONResponse:
        try:
            config = ImportConfig.model_validate_json(config_json)
        except ValidationError as exc:
            return _error(
                422,
                "invalid_import_config",
                "import configuration is invalid",
                exc.errors(include_url=False),
            )
        except json.JSONDecodeError:
            return _error(422, "invalid_import_config", "import configuration is not valid JSON")
        content = await file.read(resolved.max_upload_bytes + 1)
        try:
            return imports.import_bytes(file.filename or "source", content, config)
        except ImportLimitError as exc:
            return _error(413, "import_rejected", str(exc))

    @app.get("/api/v1/imports/{import_id}", response_model=ImportRecord)
    def get_import(import_id: str) -> ImportRecord:
        record = repository.get_import(import_id)
        if record is None:
            raise HTTPException(404, {"code": "not_found", "message": "import not found"})
        return record

    @app.get("/api/v1/datasets", response_model=list[DatasetDetail])
    def list_datasets() -> list[DatasetDetail]:
        return repository.list_datasets()

    @app.get("/api/v1/datasets/{dataset_id}", response_model=DatasetDetail)
    def get_dataset(dataset_id: str) -> DatasetDetail:
        dataset = repository.get_dataset(dataset_id)
        if dataset is None:
            raise HTTPException(404, {"code": "not_found", "message": "dataset not found"})
        return dataset

    @app.get("/api/v1/datasets/{dataset_id}/summary", response_model=DatasetSummary)
    def dataset_summary(dataset_id: str) -> DatasetSummary:
        summary = queries.summary(dataset_id)
        if summary is None:
            raise HTTPException(404, {"code": "not_found", "message": "dataset not found"})
        return summary

    @app.get("/api/v1/datasets/{dataset_id}/provenance", response_model=ProvenanceResponse)
    def dataset_provenance(dataset_id: str) -> ProvenanceResponse:
        provenance = repository.provenance(dataset_id, __version__)
        if provenance is None:
            raise HTTPException(404, {"code": "not_found", "message": "dataset not found"})
        return provenance

    def run_analysis(dataset_id: str, seed: int, replicates: int) -> AnalysisBundle:
        try:
            return analysis.analyze(dataset_id, seed=seed, replicates=replicates)
        except AnalysisNotFoundError:
            raise HTTPException(
                404, {"code": "not_found", "message": "dataset not found"}
            ) from None
        except ValueError as exc:
            raise HTTPException(
                422, {"code": "invalid_analysis_config", "message": str(exc)}
            ) from exc

    @app.get("/api/v1/datasets/{dataset_id}/evidence", response_model=EvidenceSummary)
    def dataset_evidence(
        dataset_id: str, seed: Seed = DEFAULT_SEED, replicates: Replicates = DEFAULT_REPLICATES
    ) -> EvidenceSummary:
        return run_analysis(dataset_id, seed, replicates).evidence

    @app.get("/api/v1/datasets/{dataset_id}/agreement", response_model=AgreementResponse)
    def dataset_agreement(
        dataset_id: str, seed: Seed = DEFAULT_SEED, replicates: Replicates = DEFAULT_REPLICATES
    ) -> AgreementResponse:
        return run_analysis(dataset_id, seed, replicates).agreement

    @app.get(
        "/api/v1/datasets/{dataset_id}/agreement/pairs",
        response_model=list[PairwiseAgreement],
    )
    def pairwise_agreement(
        dataset_id: str, seed: Seed = DEFAULT_SEED, replicates: Replicates = DEFAULT_REPLICATES
    ) -> list[PairwiseAgreement]:
        return run_analysis(dataset_id, seed, replicates).agreement.overlap.pairwise

    @app.get(
        "/api/v1/datasets/{dataset_id}/agreement/alpha",
        response_model=StatisticalResult,
    )
    def dataset_alpha(
        dataset_id: str, seed: Seed = DEFAULT_SEED, replicates: Replicates = DEFAULT_REPLICATES
    ) -> StatisticalResult:
        return run_analysis(dataset_id, seed, replicates).agreement.alpha

    @app.get("/api/v1/datasets/{dataset_id}/gold-metrics", response_model=GoldMetricsResponse)
    def dataset_gold_metrics(
        dataset_id: str, seed: Seed = DEFAULT_SEED, replicates: Replicates = DEFAULT_REPLICATES
    ) -> GoldMetricsResponse:
        return run_analysis(dataset_id, seed, replicates).gold_metrics

    @app.get(
        "/api/v1/datasets/{dataset_id}/annotators/{annotator_id}/gold-metrics",
        response_model=GoldMetricsResponse,
    )
    def annotator_gold_metrics(
        dataset_id: str,
        annotator_id: str,
        seed: Seed = DEFAULT_SEED,
        replicates: Replicates = DEFAULT_REPLICATES,
    ) -> GoldMetricsResponse:
        try:
            return analysis.gold_for_annotator(
                dataset_id, annotator_id, seed=seed, replicates=replicates
            )
        except AnalysisNotFoundError:
            raise HTTPException(
                404, {"code": "not_found", "message": "dataset or annotator not found"}
            ) from None

    @app.get("/api/v1/datasets/{dataset_id}/confusion", response_model=ConfusionMatrix)
    def dataset_confusion(
        dataset_id: str, seed: Seed = DEFAULT_SEED, replicates: Replicates = DEFAULT_REPLICATES
    ) -> ConfusionMatrix:
        return run_analysis(dataset_id, seed, replicates).gold_metrics.confusion

    @app.get(
        "/api/v1/datasets/{dataset_id}/annotators",
        response_model=list[AnnotatorEvidence],
    )
    def dataset_annotators(
        dataset_id: str, seed: Seed = DEFAULT_SEED, replicates: Replicates = DEFAULT_REPLICATES
    ) -> list[AnnotatorEvidence]:
        return run_analysis(dataset_id, seed, replicates).annotators

    @app.post(
        "/api/v1/datasets/{dataset_id}/consensus/runs",
        response_model=ConsensusRun,
    )
    def create_consensus_run(dataset_id: str, request: ConsensusRunRequest) -> ConsensusRun:
        try:
            return consensus.create_run(dataset_id, request)
        except ConsensusNotFoundError:
            raise HTTPException(
                404, {"code": "not_found", "message": "dataset not found"}
            ) from None

    @app.get("/api/v1/consensus/runs/{run_id}", response_model=ConsensusRun)
    def get_consensus_run(run_id: str) -> ConsensusRun:
        try:
            return consensus.get_run(run_id)
        except ConsensusNotFoundError:
            raise HTTPException(404, {"code": "not_found", "message": "run not found"}) from None

    @app.get(
        "/api/v1/consensus/runs/{run_id}/items",
        response_model=PaginatedConsensusItems,
    )
    def consensus_items(
        run_id: str,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        method: ConsensusMethod | None = None,
    ) -> PaginatedConsensusItems:
        try:
            return consensus.items(run_id, offset=offset, limit=limit, method=method)
        except ConsensusNotFoundError:
            raise HTTPException(404, {"code": "not_found", "message": "run not found"}) from None

    @app.get(
        "/api/v1/consensus/runs/{run_id}/items/{item_id}",
        response_model=list[ConsensusResult],
    )
    def consensus_item(run_id: str, item_id: str) -> list[ConsensusResult]:
        try:
            run = consensus.get_run(run_id)
        except ConsensusNotFoundError:
            raise HTTPException(404, {"code": "not_found", "message": "run not found"}) from None
        rows = [row for row in run.items if row.item_id == item_id]
        if not rows:
            raise HTTPException(404, {"code": "not_found", "message": "item not found"})
        return rows

    @app.get(
        "/api/v1/consensus/runs/{run_id}/workers",
        response_model=list[WorkerConfusionEstimate],
    )
    def consensus_workers(run_id: str) -> list[WorkerConfusionEstimate]:
        try:
            return consensus.get_run(run_id).workers
        except ConsensusNotFoundError:
            raise HTTPException(404, {"code": "not_found", "message": "run not found"}) from None

    @app.get(
        "/api/v1/consensus/runs/{run_id}/comparison",
        response_model=ConsensusComparison,
    )
    def consensus_comparison(run_id: str) -> ConsensusComparison:
        try:
            return consensus.get_run(run_id).comparison
        except ConsensusNotFoundError:
            raise HTTPException(404, {"code": "not_found", "message": "run not found"}) from None

    def load_snapshot_data(dataset_id: str):
        detail = repository.get_dataset(dataset_id)
        path = repository.dataset_path(dataset_id)
        if detail is None or path is None:
            raise HTTPException(404, {"code": "not_found", "message": "dataset not found"})
        import pyarrow.parquet as pq

        from dataqual.analysis.core import Annotation
        from dataqual.schemas.core import GoldLabel

        all_rows = pq.read_table(path / "annotations.parquet").to_pylist()
        current_rows = [
            row
            for row in all_rows
            if row.get("is_current", True)
            and row.get("annotation_source") in {"human", "ai_assisted"}
        ]
        annotations = [
            Annotation(
                str(row["annotation_id"]),
                str(row["item_id"]),
                str(row["annotator_id"]),
                str(row["label"]),
                confidence=row.get("confidence"),
            )
            for row in current_rows
        ]
        domain_rows = pq.read_table(path / "label_domain.parquet").to_pylist()
        raw_labels = domain_rows[0]["labels"]
        labels = list(json.loads(raw_labels)) if isinstance(raw_labels, str) else list(raw_labels)
        raw_gold = pq.read_table(path / "gold_labels.parquet").to_pylist()
        latest_gold = {}
        for row in raw_gold:
            previous = latest_gold.get(str(row["item_id"]))
            if previous is None or row["version"] > previous["version"]:
                latest_gold[str(row["item_id"])] = row
        gold_labels = [
            GoldLabel(
                gold_label_id=str(row.get("gold_label_id") or f"g-{row['item_id']}"),
                project_id=detail.project_id,
                item_id=str(row["item_id"]),
                label_domain_id=str(row["label_domain_id"]),
                label=str(row["label"]) if row.get("label") is not None else None,
                distribution=(
                    json.loads(row["distribution"])
                    if isinstance(row.get("distribution"), str)
                    else row.get("distribution")
                ),
                supersedes_gold_label_id=row.get("supersedes_gold_label_id"),
                resolution_status=cast(
                    Literal["resolved_hard", "resolved_distributional", "unresolved"],
                    str(row.get("resolution_status") or "resolved_hard"),
                ),
                gold_source=cast(
                    Literal[
                        "expert_adjudication",
                        "trusted_reference",
                        "benchmark_truth",
                        "simulation_truth",
                    ],
                    str(row.get("gold_source") or "expert_adjudication"),
                ),
                version=int(row.get("version") or 1),
                created_at=str(row.get("created_at") or "2026-08-09T00:00:00Z"),
            )
            for row in latest_gold.values()
        ]
        return detail, annotations, gold_labels, labels

    # Phase 4 API Endpoints
    @app.get("/api/v1/datasets/{dataset_id}/annotator-intelligence")
    def dataset_annotator_intelligence(dataset_id: str) -> list[dict[str, Any]]:
        _detail, annotations, gold_labels, labels = load_snapshot_data(dataset_id)
        from dataqual.annotators import AnnotatorIntelligenceService

        service = AnnotatorIntelligenceService(annotations, gold_labels, labels)
        return [p.model_dump(mode="json") for p in service.list_annotator_profiles()]

    @app.get("/api/v1/datasets/{dataset_id}/annotators/{annotator_id}/profile")
    def annotator_profile(dataset_id: str, annotator_id: str) -> dict[str, Any]:
        _detail, annotations, gold_labels, labels = load_snapshot_data(dataset_id)
        from dataqual.annotators import AnnotatorIntelligenceService

        service = AnnotatorIntelligenceService(annotations, gold_labels, labels)
        if annotator_id not in service.annotator_ids:
            raise HTTPException(404, {"code": "not_found", "message": "annotator not found"})
        return service.get_annotator_profile(annotator_id).model_dump(mode="json")

    @app.get("/api/v1/datasets/{dataset_id}/annotators/{annotator_id}/reliability")
    def annotator_reliability(dataset_id: str, annotator_id: str) -> dict[str, Any]:
        _detail, annotations, gold_labels, _labels = load_snapshot_data(dataset_id)
        from dataqual.annotators import compute_beta_binomial_reliability

        return compute_beta_binomial_reliability(annotations, gold_labels, annotator_id).model_dump(
            mode="json"
        )

    @app.get("/api/v1/datasets/{dataset_id}/annotators/{annotator_id}/confusion")
    def annotator_dirichlet_confusion(dataset_id: str, annotator_id: str) -> dict[str, Any]:
        _detail, annotations, gold_labels, labels = load_snapshot_data(dataset_id)
        from dataqual.annotators import compute_dirichlet_confusion

        return compute_dirichlet_confusion(
            annotations, gold_labels, labels, annotator_id
        ).model_dump(mode="json")

    @app.get("/api/v1/datasets/{dataset_id}/diagnostics/items")
    def dataset_diagnostics_items(dataset_id: str) -> list[dict[str, Any]]:
        detail, annotations, gold_labels, labels = load_snapshot_data(dataset_id)
        from dataqual.diagnostics import DisagreementDiagnosticsService

        service = DisagreementDiagnosticsService(
            annotations,
            gold_labels,
            labels,
            dataset_id,
            detail.project_id,
            precomputed_features=review_features(annotations, gold_labels, labels),
        )
        features_map = service.extract_all_features()
        return [f.model_dump(mode="json") for f in features_map.values()]

    @app.get("/api/v1/datasets/{dataset_id}/diagnostics/items/{item_id}")
    def dataset_diagnostics_item(dataset_id: str, item_id: str) -> dict[str, Any]:
        detail, annotations, gold_labels, labels = load_snapshot_data(dataset_id)
        from dataqual.diagnostics import DisagreementDiagnosticsService

        service = DisagreementDiagnosticsService(
            annotations,
            gold_labels,
            labels,
            dataset_id,
            detail.project_id,
            precomputed_features=review_features(annotations, gold_labels, labels),
        )
        features_map = service.extract_all_features()
        if item_id not in features_map:
            raise HTTPException(404, {"code": "not_found", "message": "item not found"})
        return features_map[item_id].model_dump(mode="json")

    @app.get("/api/v1/datasets/{dataset_id}/quality-flags")
    def dataset_quality_flags(
        dataset_id: str,
        flag_type: str | None = None,
        severity: str | None = None,
        entity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        detail, annotations, gold_labels, labels = load_snapshot_data(dataset_id)
        from dataqual.diagnostics import DisagreementDiagnosticsService

        service = DisagreementDiagnosticsService(
            annotations,
            gold_labels,
            labels,
            dataset_id,
            detail.project_id,
            precomputed_features=review_features(annotations, gold_labels, labels),
        )
        flags = service.generate_quality_flags()

        if flag_type is not None:
            flags = [f for f in flags if f.flag_type == flag_type]
        if severity is not None:
            flags = [f for f in flags if f.severity == severity]
        if entity_type is not None:
            flags = [f for f in flags if f.entity_type == entity_type]

        return [f.model_dump(mode="json") for f in flags]

    # Phase 5 Review Prioritization Endpoints
    review_runs_store = ReviewRunStore(repository.root)

    def review_run_or_404_optional(run_id: str) -> dict[str, Any] | None:
        try:
            return review_runs_store.load(run_id)
        except StorageError as error:
            raise HTTPException(
                500, {"code": "storage_error", "message": f"{error}; the run was not modified"}
            ) from None

    def review_run_or_404(run_id: str) -> dict[str, Any]:
        run = review_run_or_404_optional(run_id)
        if run is None:
            raise HTTPException(404, {"code": "not_found", "message": "review run not found"})
        return run

    @app.post("/api/v1/datasets/{dataset_id}/review-runs")
    def create_review_run(
        dataset_id: str,
        response: Response,
        method: Literal[
            "erv",
            "random",
            "highest_entropy",
            "lowest_consensus_confidence",
            "lowest_worker_reliability",
        ] = "erv",
        review_unit: ReviewUnit = "annotation",
        random_ranking_seed: Seed = 2026,
    ) -> dict[str, Any]:
        detail, annotations, gold_labels, labels = load_snapshot_data(dataset_id)
        from dataqual.prioritization.service import ReviewPrioritizationService

        # Ranking is deterministic in these inputs; the seed only matters for random ranking.
        identity = {
            "dataset_id": dataset_id,
            "canonical_snapshot_checksum": detail.canonical_snapshot_checksum,
            "method": method,
            "review_unit": review_unit,
            "random_ranking_seed": random_ranking_seed if method == "random" else None,
            "ranking_version": RANKING_VERSION,
            "erv_config_hash": DEFAULT_ERV_CONFIG.config_hash(),
            "ds_configuration": REVIEW_DS_CONFIG.model_dump(mode="json"),
        }
        run_id = deterministic_run_id(identity)
        existing = review_run_or_404_optional(run_id)
        if existing is not None:
            response.headers["X-Review-Run-Reused"] = "true"
            return {key: value for key, value in existing.items() if key != "candidates"}

        service = ReviewPrioritizationService(annotations, gold_labels, labels)
        candidates = service.get_candidates(
            method=method, review_unit=review_unit, random_ranking_seed=random_ranking_seed
        )

        run_record = {
            "run_id": run_id,
            "dataset_id": dataset_id,
            "method": method,
            "review_unit": review_unit,
            "total_candidates": len(candidates),
            "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "ranking_version": RANKING_VERSION,
            "canonical_snapshot_checksum": detail.canonical_snapshot_checksum,
            "random_ranking_seed": random_ranking_seed,
            "ds_configuration": REVIEW_DS_CONFIG.model_dump(mode="json"),
            "erv_config_hash": DEFAULT_ERV_CONFIG.config_hash(),
            "candidates": [c.model_dump(mode="json") for c in candidates],
        }
        try:
            review_runs_store.save(run_record)
        except ReviewRunQuotaError as error:
            raise HTTPException(429, {"code": "quota_exceeded", "message": str(error)}) from None

        response.headers["X-Review-Run-Reused"] = "false"
        return {key: value for key, value in run_record.items() if key != "candidates"}

    @app.get("/api/v1/review-runs/{run_id}")
    def get_review_run(run_id: str) -> dict[str, Any]:
        run = review_run_or_404(run_id)
        return {key: value for key, value in run.items() if key != "candidates"}

    @app.get("/api/v1/review-runs/{run_id}/candidates")
    def get_review_run_candidates(
        run_id: str,
        limit: Annotated[int, Query(ge=1, le=500)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[dict[str, Any]]:
        run = review_run_or_404(run_id)
        cands = run["candidates"]
        return cands[offset : offset + limit]

    @app.get("/api/v1/review-runs/{run_id}/summary")
    def get_review_run_summary(run_id: str) -> dict[str, Any]:
        run = review_run_or_404(run_id)
        return {
            "run_id": run["run_id"],
            "method": run["method"],
            "review_unit": run["review_unit"],
            "total_candidates": run["total_candidates"],
            "eligible_candidates": sum(
                1 for c in run["candidates"] if c.get("eligible_coverage", True)
            ),
        }

    @app.get("/api/v1/review-runs/{run_id}/page")
    def review_page(
        run_id: str,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
        q: Annotated[str, Query(max_length=200)] = "",
        eligible_only: bool = False,
    ) -> dict[str, Any]:
        run = review_run_or_404(run_id)
        needle = q.strip().casefold()
        rows = [
            c
            for c in run["candidates"]
            if (not eligible_only or c["eligible_coverage"])
            and (
                not needle
                or any(
                    needle in str(c.get(key) or "").casefold()
                    for key in ("item_id", "annotator_id", "annotation_id", "submitted_label")
                )
            )
        ]
        return {
            "items": rows[offset : offset + limit],
            "total": len(rows),
            "offset": offset,
            "limit": limit,
            "eligible_total": sum(c["eligible_coverage"] for c in run["candidates"]),
        }

    @app.get("/api/v1/datasets/{dataset_id}/label-collection-plan")
    def label_collection_plan(
        dataset_id: str,
        target_confidence: Annotated[float, Query(ge=0.6, le=0.999)] = 0.95,
        max_labels: Annotated[int, Query(ge=2, le=15)] = 7,
        limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    ) -> dict[str, Any]:
        """Which items are settled, which need more labels, and which need an expert."""
        _detail, annotations, _gold, labels = load_snapshot_data(dataset_id)
        from dataqual.collection import plan_label_collection

        plan = plan_label_collection(annotations, labels, target_confidence, max_labels)
        plan["items_returned"] = min(limit, len(plan["items"]))
        plan["items"] = plan["items"][:limit]
        return plan

    @lru_cache(maxsize=24)
    def cached_benchmark(scenario_id: str, seeds: int) -> dict[str, Any]:
        from dataqual.benchmarking.runner import BenchmarkRunner

        manifest, _ = BenchmarkRunner(scenario_id=scenario_id, seed_count=seeds).run_benchmark()
        return manifest.model_dump(mode="json")

    @app.get("/api/v1/benchmark/results")
    def get_benchmark_results(
        scenario_id: Annotated[str, Query(pattern=r"^S([1-9]|1[0-2])$")] = "S1",
        seeds: Annotated[int, Query(ge=2, le=20)] = 5,
    ) -> dict[str, Any]:
        # Deterministic for (scenario, seeds): serve repeats from a small bounded cache instead
        # of re-simulating every world on each request.
        return cached_benchmark(scenario_id, seeds)

    return app


app = create_app()
