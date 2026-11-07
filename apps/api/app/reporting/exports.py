"""CSV, PDF and Excel export generation."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime, timezone
from typing import Any, Sequence
from xml.sax.saxutils import escape

from app.evidence.pdf import build_simple_pdf
from app.reporting.sanitize import sanitize_cell


def rows_to_csv(headers: Sequence[str], rows: list[dict[str, Any]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([sanitize_cell(row.get(h)) for h in headers])
    return buf.getvalue().encode("utf-8-sig")


def summary_to_pdf(title: str, summary: dict[str, Any], row_lines: list[str] | None = None) -> bytes:
    lines = [f"Generated: {datetime.now(timezone.utc).isoformat()}"]
    for key, val in summary.items():
        if key in {"definitions", "trends_daily", "distribution_by_worker", "by_status", "by_priority"}:
            continue
        lines.append(f"{key}: {val}")
    if row_lines:
        lines.append("---")
        lines.extend(row_lines[:80])
    return build_simple_pdf(title, lines)


def _xlsx_cell(col: int, row: int, value: str) -> str:
    return f'<c r="{_col_letter(col)}{row}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'


def _col_letter(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def rows_to_xlsx(sheet_name: str, headers: Sequence[str], rows: list[dict[str, Any]]) -> bytes:
    """Minimal Office Open XML spreadsheet (no external dependency)."""
    sheet_rows = []
    sheet_rows.append("<row>" + "".join(_xlsx_cell(i + 1, 1, h) for i, h in enumerate(headers)) + "</row>")
    for ri, row in enumerate(rows, start=2):
        sheet_rows.append(
            "<row>" + "".join(_xlsx_cell(i + 1, ri, sanitize_cell(row.get(h))) for i, h in enumerate(headers)) + "</row>"
        )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{escape(sheet_name[:31])}" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return out.getvalue()
