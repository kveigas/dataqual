from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_root: Path
    max_upload_bytes: int = 10 * 1024 * 1024

    @classmethod
    def from_environment(cls) -> Settings:
        configured = os.environ.get("DATAQUAL_DATA_ROOT")
        root = Path(configured) if configured else Path.cwd() / "data"
        limit = int(os.environ.get("DATAQUAL_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
        return cls(data_root=root.resolve(), max_upload_bytes=limit)
