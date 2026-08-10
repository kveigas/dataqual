"""Import and minimally exercise the proposed Python dependency boundary."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

import duckdb
import fastapi
import hypothesis
import httpx
import numpy as np
import pandas as pd
import pyarrow as pa
import pydantic
import pytest
import scipy
import sklearn
import statsmodels
import typer
import uvicorn
import yaml
from crowdkit.aggregation import DawidSkene, GLAD, MACE, MajorityVote
from pydantic import BaseModel


class ProbePayload(BaseModel):
    project_id: str
    rows: int


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    app = fastapi.FastAPI()

    @app.get("/phase0-probe")
    def phase0_probe() -> dict[str, bool]:
        return {"ok": True}

    payload = ProbePayload(project_id="phase0", rows=3)
    arrow_values = pa.array([1, 2, 3], type=pa.int8())
    duckdb_value = duckdb.connect(":memory:").execute("SELECT sum(i) FROM range(4) t(i)").fetchone()[0]
    yaml_value = yaml.safe_load("ok: true")
    pip_check = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True,
        text=True,
        check=False,
    )

    package_names = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "numpy",
        "scipy",
        "pandas",
        "duckdb",
        "pyarrow",
        "scikit-learn",
        "statsmodels",
        "typer",
        "PyYAML",
        "crowd-kit",
        "nltk",
        "hypothesis",
        "pytest",
        "pytest-cov",
        "httpx",
    ]
    result = {
        "status": "pass" if pip_check.returncode == 0 else "fail",
        "python": sys.version,
        "platform": platform.platform(),
        "packages": {name: metadata.version(name) for name in package_names},
        "pip_check": {
            "return_code": pip_check.returncode,
            "stdout": pip_check.stdout.strip(),
            "stderr": pip_check.stderr.strip(),
        },
        "checks": {
            "fastapi_route_count": len(app.routes),
            "pydantic_round_trip": payload.model_dump(),
            "numpy_sum": int(np.array([1, 2, 3]).sum()),
            "pandas_rows": int(len(pd.DataFrame({"x": [1, 2, 3]}))),
            "arrow_sum": int(sum(arrow_values.to_pylist())),
            "duckdb_sum_range_4": int(duckdb_value),
            "yaml_boolean": bool(yaml_value["ok"]),
            "crowdkit_classes": [cls.__name__ for cls in (MajorityVote, DawidSkene, GLAD, MACE)],
            "module_versions": {
                "fastapi": fastapi.__version__,
                "uvicorn": uvicorn.__version__,
                "pydantic": pydantic.__version__,
                "numpy": np.__version__,
                "scipy": scipy.__version__,
                "sklearn": sklearn.__version__,
                "statsmodels": statsmodels.__version__,
                "typer": typer.__version__,
                "hypothesis": hypothesis.__version__,
                "pytest": pytest.__version__,
                "httpx": httpx.__version__,
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
