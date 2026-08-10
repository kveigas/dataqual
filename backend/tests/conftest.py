from __future__ import annotations

from pathlib import Path

import pytest
from dataqual.ingestion import ImportService
from dataqual.schemas.imports import ImportConfig
from dataqual.storage import DatasetRepository

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).parents[2]


@pytest.fixture
def config() -> ImportConfig:
    return ImportConfig.model_validate_json((ROOT / "configs" / "demo_import.json").read_bytes())


@pytest.fixture
def repository(tmp_path: Path) -> DatasetRepository:
    return DatasetRepository(tmp_path / "data")


@pytest.fixture
def service(repository: DatasetRepository) -> ImportService:
    return ImportService(repository, 1024 * 1024)


@pytest.fixture
def valid_csv() -> bytes:
    return (FIXTURES / "valid_annotations.csv").read_bytes()
