"""F2.14 reporting unit tests."""

from __future__ import annotations

from app.evidence.pdf import build_simple_pdf
from app.reporting.exports import rows_to_csv, rows_to_xlsx, summary_to_pdf
from app.reporting.sanitize import sanitize_cell


def test_sanitize_cell_formula_injection() -> None:
    assert sanitize_cell("=SUM(A1)").startswith("'")
    assert sanitize_cell("hello") == "hello"


def test_csv_export_utf8() -> None:
    body = rows_to_csv(["ref", "title"], [{"ref": "=1+1", "title": "Ok"}])
    text = body.decode("utf-8-sig")
    assert "ref" in text
    assert text.count("'=1+1") == 1 or "'=1+1" in text


def test_xlsx_minimal_zip() -> None:
    data = rows_to_xlsx("Housing", ["ref"], [{"ref": "APP-1"}])
    assert data[:2] == b"PK"


def test_pdf_report_header() -> None:
    pdf = summary_to_pdf("Report", {"total": 3}, ["line"])
    assert pdf.startswith(b"%PDF")


def test_pdf_builder_still_valid() -> None:
    assert build_simple_pdf("T", ["x"]).startswith(b"%PDF")
