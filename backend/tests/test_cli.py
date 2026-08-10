from __future__ import annotations

from pathlib import Path

from conftest import FIXTURES, ROOT
from dataqual.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def test_cli_import_and_summary(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    imported = runner.invoke(
        app,
        [
            "import-file",
            str(FIXTURES / "valid_annotations.csv"),
            "--config",
            str(ROOT / "configs" / "demo_import.json"),
            "--data-root",
            str(data_root),
        ],
    )
    assert imported.exit_code == 0, imported.output
    import_id_marker = '"dataset_id": "'
    dataset_id = imported.output.split(import_id_marker, 1)[1].split('"', 1)[0]
    summary = runner.invoke(app, ["summary", dataset_id, "--data-root", str(data_root)])
    assert summary.exit_code == 0
    assert '"unique_items": 4' in summary.output


def test_cli_rejection_and_missing_dataset(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    rejected = runner.invoke(
        app,
        [
            "import-file",
            str(FIXTURES / "invalid_unknown_label.csv"),
            "--config",
            str(ROOT / "configs" / "demo_import.json"),
            "--data-root",
            str(data_root),
        ],
    )
    assert rejected.exit_code == 1
    missing = runner.invoke(app, ["summary", "missing", "--data-root", str(data_root)])
    assert missing.exit_code == 1
    assert "dataset not found" in missing.output
