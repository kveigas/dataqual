from __future__ import annotations

import datetime
import json
from typing import Annotated, Any, Literal, cast

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
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
from dataqual.schemas.imports import (
    DatasetDetail,
    DatasetSummary,
    ImportConfig,
    ImportRecord,
    ProvenanceResponse,
)
from dataqual.storage import DatasetRepository

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

    @app.exception_handler(HTTPException)
    async def http_error(_request: Any, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            detail = cast(dict[str, Any], exc.detail)
            return _error(exc.status_code, str(detail["code"]), str(detail["message"]))
        return _error(exc.status_code, "http_error", str(exc.detail))

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

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
        current_rows = [row for row in all_rows if row.get("is_current", True)]
        annotations = [
            Annotation(
                str(row["annotation_id"]),
                str(row["item_id"]),
                str(row["annotator_id"]),
                str(row["label"]),
            )
            for row in current_rows
        ]
        domain_rows = pq.read_table(path / "label_domain.parquet").to_pylist()
        raw_labels = domain_rows[0]["labels"]
        labels = list(json.loads(raw_labels)) if isinstance(raw_labels, str) else list(raw_labels)
        raw_gold = pq.read_table(path / "gold_labels.parquet").to_pylist()
        gold_labels = [
            GoldLabel(
                gold_label_id=str(row.get("gold_label_id") or f"g-{row['item_id']}"),
                project_id=detail.project_id,
                item_id=str(row["item_id"]),
                label_domain_id="domain",
                label=str(row["label"]) if row.get("label") is not None else None,
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
            for row in raw_gold
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
    review_runs_store: dict[str, dict[str, Any]] = {}

    @app.post("/api/v1/datasets/{dataset_id}/review-runs")
    def create_review_run(
        dataset_id: str,
        method: str = "erv",
        review_unit: str = "annotation",
        random_ranking_seed: int = 2026,
    ) -> dict[str, Any]:
        _detail, annotations, gold_labels, labels = load_snapshot_data(dataset_id)
        from dataqual.prioritization.service import ReviewPrioritizationService

        service = ReviewPrioritizationService(annotations, gold_labels, labels)
        candidates = service.get_candidates(
            method=method, review_unit=review_unit, random_ranking_seed=random_ranking_seed
        )

        import uuid

        run_id = f"run-{uuid.uuid4().hex[:12]}"
        run_record = {
            "run_id": run_id,
            "dataset_id": dataset_id,
            "method": method,
            "review_unit": review_unit,
            "total_candidates": len(candidates),
            "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "candidates": [c.model_dump(mode="json") for c in candidates],
        }
        review_runs_store[run_id] = run_record

        return {
            "run_id": run_id,
            "dataset_id": dataset_id,
            "method": method,
            "review_unit": review_unit,
            "total_candidates": len(candidates),
        }

    @app.get("/api/v1/review-runs/{run_id}")
    def get_review_run(run_id: str) -> dict[str, Any]:
        if run_id not in review_runs_store:
            raise HTTPException(404, {"code": "not_found", "message": "review run not found"})
        run = review_runs_store[run_id]
        return {
            "run_id": run["run_id"],
            "dataset_id": run["dataset_id"],
            "method": run["method"],
            "review_unit": run["review_unit"],
            "total_candidates": run["total_candidates"],
            "created_at": run["created_at"],
        }

    @app.get("/api/v1/review-runs/{run_id}/candidates")
    def get_review_run_candidates(
        run_id: str, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        if run_id not in review_runs_store:
            raise HTTPException(404, {"code": "not_found", "message": "review run not found"})
        run = review_runs_store[run_id]
        cands = run["candidates"]
        return cands[offset : offset + limit]

    @app.get("/api/v1/review-runs/{run_id}/summary")
    def get_review_run_summary(run_id: str) -> dict[str, Any]:
        if run_id not in review_runs_store:
            raise HTTPException(404, {"code": "not_found", "message": "review run not found"})
        run = review_runs_store[run_id]
        return {
            "run_id": run["run_id"],
            "method": run["method"],
            "review_unit": run["review_unit"],
            "total_candidates": run["total_candidates"],
            "eligible_candidates": sum(
                1 for c in run["candidates"] if c.get("eligible_coverage", True)
            ),
        }

    @app.get("/api/v1/benchmark/results")
    def get_benchmark_results(scenario_id: str = "S1", seeds: int = 5) -> dict[str, Any]:
        from dataqual.benchmarking.runner import BenchmarkRunner

        runner = BenchmarkRunner(scenario_id=scenario_id, seed_count=seeds)
        manifest, _ = runner.run_benchmark()
        return manifest.model_dump(mode="json")

    return app


app = create_app()
