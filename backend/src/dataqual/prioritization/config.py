from __future__ import annotations

from pathlib import Path

from dataqual.schemas.prioritization import ErvConfig


def load_frozen_erv_config(config_path: Path | None = None) -> ErvConfig:
    if config_path is None:
        config_path = Path("configs/erv_v1.yaml")

    if config_path.exists():
        text = config_path.read_text(encoding="utf-8")
        lines = text.strip().splitlines()
        kv: dict[str, float | str] = {}
        for line in lines:
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip().strip('"')
                try:
                    kv[k] = float(v)
                except ValueError:
                    kv[k] = v
        return ErvConfig(
            version=str(kv.get("version", "1.0.0")),
            weight_uncert=float(kv.get("weight_uncert", 0.60)),
            weight_entropy=float(kv.get("weight_entropy", 0.20)),
            weight_worker_error=float(kv.get("weight_worker_error", 0.20)),
            default_cost=float(kv.get("default_cost", 1.0)),
        )

    return ErvConfig()


DEFAULT_ERV_CONFIG = load_frozen_erv_config()
