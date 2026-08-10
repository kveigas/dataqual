from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from typing import Any, Literal

SUPPORTED_EXTENSIONS = {".csv": "csv", ".json": "json"}


class SourceParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedSource:
    source_format: Literal["csv", "json"]
    detected_mime: str
    rows: list[dict[str, Any]]


def _decode(content: bytes) -> str:
    if b"\x00" in content[:4096]:
        raise SourceParseError("uploaded content appears to be binary")
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceParseError("source must be UTF-8 encoded") from exc


def parse_source(filename: str, content: bytes) -> ParsedSource:
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    source_format = SUPPORTED_EXTENSIONS.get(suffix)
    if source_format is None:
        raise SourceParseError("only .csv and .json imports are supported")
    text = _decode(content)
    if source_format == "csv":
        try:
            reader = csv.DictReader(io.StringIO(text), strict=True)
            if reader.fieldnames is None or any(not field for field in reader.fieldnames):
                raise SourceParseError("CSV requires a non-empty header row")
            if len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise SourceParseError("CSV header names must be unique")
            rows = [dict(row) for row in reader]
        except csv.Error as exc:
            raise SourceParseError(f"malformed CSV: {exc}") from exc
        return ParsedSource("csv", "text/csv", rows)

    try:
        payload = json.loads(
            text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value))
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise SourceParseError("malformed JSON or non-finite numeric value") from exc
    if isinstance(payload, dict):
        payload = payload.get("annotations")
    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise SourceParseError(
            "JSON must be an array of annotation objects or an object with annotations"
        )
    return ParsedSource("json", "application/json", payload)


def csv_value(row: dict[str, Any], field: str, kind: type[Any]) -> Any:
    value = row.get(field)
    if value is None or value == "":
        return None
    if kind is str:
        return value
    try:
        if kind is int:
            if not str(value).lstrip("-").isdigit():
                raise ValueError
            return int(value)
        if kind is float:
            return float(value)
        if kind is dict:
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise ValueError
            return parsed
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise SourceParseError(f"{field} has invalid {kind.__name__} syntax") from exc
    raise TypeError(f"unsupported CSV conversion kind: {kind}")
