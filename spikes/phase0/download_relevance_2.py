"""Reproducibly acquire the exact relevance-2 archive used by Crowd-Kit 1.4.2.

The dataset's redistribution license is not stated by the loader or archive.
Keep the downloaded archive outside version control until the maintainer supplies
an explicit license. This script never changes the downloaded bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATA_URL = "https://tlk.s3.yandex.net/dataset/crowd-kit/relevance-2.zip"
MD5_URL = "https://tlk.s3.yandex.net/dataset/crowd-kit/relevance-2.md5"
EXPECTED_MD5 = "a39c3c30d9e946eeb80ca39954c96e95"
EXPECTED_SHA256 = "0d8b5c4ffdb042cc1435ac20933bcf3218310e0bcc6dd27baef5bcfe64973bef"


def digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    archive = args.output_dir / "relevance-2.zip"
    upstream_md5 = args.output_dir / "relevance-2.md5"
    if archive.exists() and not args.force:
        raise SystemExit(f"Refusing to overwrite existing raw archive: {archive}")

    urllib.request.urlretrieve(DATA_URL, archive)
    urllib.request.urlretrieve(MD5_URL, upstream_md5)
    actual_md5 = digest(archive, "md5")
    actual_sha256 = digest(archive, "sha256")
    stated_md5 = upstream_md5.read_text(encoding="utf-8").strip().lower()

    if stated_md5 != EXPECTED_MD5 or actual_md5 != EXPECTED_MD5:
        raise RuntimeError(f"MD5 mismatch: upstream={stated_md5}, actual={actual_md5}, expected={EXPECTED_MD5}")
    if actual_sha256 != EXPECTED_SHA256:
        raise RuntimeError(f"SHA-256 mismatch: actual={actual_sha256}, expected={EXPECTED_SHA256}")

    result = {
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": DATA_URL,
        "checksum_url": MD5_URL,
        "archive": str(archive.resolve()),
        "bytes": archive.stat().st_size,
        "md5": actual_md5,
        "sha256": actual_sha256,
        "license": None,
        "redistribution": "not authorized; keep raw archive out of version control",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
