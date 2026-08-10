"""Download approved Phase 0B Zenodo candidates outside the repository.

The script requires an explicit record-level SPDX-style license identifier, records
the authoritative Zenodo metadata, verifies the published MD5 checksum, and emits
SHA-256 checksums for reproducibility. It never writes raw data into the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


RECORDS = (5535744, 1472330, 3626185)
ALLOWED_LICENSES = {"cc-by-4.0", "cc-by-sa-4.0"}


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "DataQual-v4-Phase0B/1.0"})
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def download(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "DataQual-v4-Phase0B/1.0"})
    with urlopen(request, timeout=120) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    for record_id in RECORDS:
        metadata = fetch_json(f"https://zenodo.org/api/records/{record_id}")
        license_id = metadata.get("metadata", {}).get("license", {}).get("id")
        if license_id not in ALLOWED_LICENSES:
            raise RuntimeError(
                f"Record {record_id} lacks an approved explicit license: {license_id!r}"
            )

        record_dir = args.output_dir / str(record_id)
        record_dir.mkdir(exist_ok=True)
        files = []
        for entry in metadata.get("files", []):
            path = record_dir / entry["key"]
            path.parent.mkdir(parents=True, exist_ok=True)
            download(entry["links"]["self"], path)
            expected_type, expected_value = entry["checksum"].split(":", 1)
            actual_value = digest(path, expected_type)
            if actual_value != expected_value:
                raise RuntimeError(f"Checksum mismatch for {path}")
            files.append(
                {
                    "name": entry["key"],
                    "bytes": path.stat().st_size,
                    "published_checksum": entry["checksum"],
                    "sha256": digest(path, "sha256"),
                }
            )

        record_summary = {
            "record_id": record_id,
            "doi": metadata.get("doi"),
            "title": metadata.get("metadata", {}).get("title"),
            "license": license_id,
            "record_url": metadata.get("links", {}).get("html"),
            "files": files,
        }
        (record_dir / "acquisition.json").write_text(
            json.dumps(record_summary, indent=2) + "\n", encoding="utf-8"
        )
        summary.append(record_summary)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
