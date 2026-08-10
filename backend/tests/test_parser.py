from __future__ import annotations

import pytest
from dataqual.ingestion.parser import SourceParseError, csv_value, parse_source


def test_csv_and_json_shapes() -> None:
    assert parse_source("x.csv", b"annotation_id,item_id\na,i\n").rows[0]["item_id"] == "i"
    assert parse_source("x.json", b'[{"annotation_id":"a"}]').source_format == "json"
    assert (
        parse_source("x.json", b'{"annotations":[{"annotation_id":"a"}]}').detected_mime
        == "application/json"
    )


@pytest.mark.parametrize(
    "filename,content",
    [
        ("x.txt", b"hello"),
        ("x.csv", b"\x00binary"),
        ("x.csv", b"\xff"),
        ("x.csv", b",bad\na,b\n"),
        ("x.json", b"{"),
        ("x.json", b'{"other":[]}'),
        ("x.json", b"[NaN]"),
    ],
)
def test_malformed_sources(filename: str, content: bytes) -> None:
    with pytest.raises(SourceParseError):
        parse_source(filename, content)


def test_csv_scalar_conversion() -> None:
    row = {"s": "x", "i": "2", "f": ".5", "d": '{"x":1}', "blank": ""}
    assert csv_value(row, "s", str) == "x"
    assert csv_value(row, "i", int) == 2
    assert csv_value(row, "f", float) == 0.5
    assert csv_value(row, "d", dict) == {"x": 1}
    assert csv_value(row, "blank", int) is None
    with pytest.raises(SourceParseError):
        csv_value({"i": "1.5"}, "i", int)
