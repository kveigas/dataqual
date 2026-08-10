from __future__ import annotations

import subprocess
from pathlib import Path
from shutil import which


def git_identity(root: Path) -> tuple[str | None, bool | None]:
    executable = which("git")
    if executable is None:
        return None, None
    try:
        commit = subprocess.run(  # noqa: S603 - executable resolved; fixed arguments
            [executable, "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(  # noqa: S603 - executable resolved; fixed arguments
                [executable, "-C", str(root), "status", "--porcelain"],
                capture_output=True,
                check=True,
                text=True,
                timeout=5,
            ).stdout.strip()
        )
        return commit, dirty
    except (FileNotFoundError, subprocess.SubprocessError):
        return None, None
