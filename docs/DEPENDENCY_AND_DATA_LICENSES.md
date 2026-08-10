# DataQual v4 — Dependency & Data License Audit

This document details the license compliance audit for Python dependencies, Node packages, third-party code references, and benchmark datasets.

## 1. Third-Party Code & Software Dependencies

- **FastAPI / Pydantic / Starlette**: MIT License.
- **DuckDB / PyArrow**: MIT / Apache 2.0 License.
- **NumPy / SciPy / Pandas**: BSD 3-Clause License.
- **React / TypeScript / Vite / TanStack Query**: MIT License.
- **Ruff / Pyright / pytest / Vitest / Playwright**: MIT / Apache 2.0 License.

## 2. Dataset Licensing & Attribution Audit

- **Requirements Annotation Dataset (Zenodo record `3626185`)**:
  - **License**: Creative Commons Attribution 4.0 International (CC BY 4.0).
  - **Attribution**: Requirements Annotation Dataset, Zenodo record `3626185`.
  - **Redistribution Policy**: The raw dataset files remain uncommitted and excluded from version control. Reproducible downloader/adapter scripts (`scripts/requirements_phase3_adapter.py`) process local source copies without committing raw text to Git.
- **Relevance-2 Dataset**:
  - **Licensing Audit**: Phase 0 audit rejected Relevance-2 for core benchmark redistribution due to restrictive terms.

## 3. Data Qual v4 Codebase License
DataQual v4 is released as an open research portfolio candidate under the MIT License.
