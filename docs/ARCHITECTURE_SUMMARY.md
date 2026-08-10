# DataQual v4 — Architecture & System Design

This document details the software architecture, data flow, storage contracts, and strict ground truth isolation boundaries of DataQual v4.

## 1. System Architecture

```mermaid
flowchart TB
    subgraph Frontend["React 19 + TypeScript SPA"]
        UI["Overview / Data / Consensus / Annotators / Diagnostics / Review Queue / Benchmarks"]
    end

    subgraph Backend["FastAPI REST API (Python 3.12)"]
        IngestService["Ingestion & Preflight Service"]
        EvidenceService["Evidence & Agreement Engine"]
        ConsensusService["Consensus Engine (MV & Dawid-Skene)"]
        IntelligenceService["Annotator Intelligence Service"]
        DiagnosticService["Disagreement Diagnostics Service"]
        PrioritizationService["Review Prioritization Service"]
    end

    subgraph Storage["Storage Foundation"]
        RawBytes["Raw Upload Retention (data/raw/)"]
        Parquet["Canonical Datasets (data/canonical/ .parquet)"]
        DuckDB["Catalog Index (data/catalog.duckdb)"]
        Analyses["Write-Once Analysis Payloads (data/analyses/)"]
    end

    subgraph SimulatorBoundary["Synthetic Simulator & Benchmark Suite (Isolated)"]
        SimGenerator["SyntheticDatasetGenerator (PCG64 Seed)"]
        ObservedEv["Observed Annotations & Dev Gold"]
        HiddenTruth["HIDDEN EVALUATION TRUTH (ISOLATED)"]
        BenchRunner["BenchmarkRunner & Metrics (AUREC@20%)"]
    end

    UI <--> Backend
    IngestService --> RawBytes & Parquet & DuckDB
    EvidenceService & ConsensusService & IntelligenceService & DiagnosticService & PrioritizationService <--> Parquet & DuckDB & Analyses
    SimGenerator --> ObservedEv & HiddenTruth
    ObservedEv --> IngestService
    HiddenTruth -->|Benchmark Scoring Only| BenchRunner
```

## 2. Strict Isolation Boundary

- **Production API & UI**: Can only access `observed_annotation_events` and `development_gold`.
- **Hidden Ground Truth**: Resides strictly inside `HiddenGroundTruth` schemas and is NEVER exposed through REST endpoints (`/api/v1/review-runs`). Leakage unit tests verify 100% invariance to modifications of hidden truth.
