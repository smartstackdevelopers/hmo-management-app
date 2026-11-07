"""Text extraction for files HMore already accepts.

PDF and plain text use local parsing. Images are recognised by magic bytes.
No OCR engine is installed in this service, so image text is not invented.
"""

from __future__ import annotations

import re
import zlib
from typing import Any

CHECKER_VERSION = "1.0.0"
SUPPORTED_TEXT_TYPES = frozenset({"application/pdf", "text/plain"})
IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


def detect_type(data: bytes, declared: str | None) -> str:
    declared_norm = (declared or "application/octet-stream").split(";")[0].strip().lower()
    if not data:
        return declared_norm or "application/octet-stream"
    if data.startswith(b"%PDF"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"PK\x03\x04"):
        if declared_norm.endswith("wordprocessingml.document"):
            return declared_norm
        return "application/zip"
    if declared_norm == "text/plain":
        sample = data[:512]
        if sample and all(32 <= b <= 126 or b in (9, 10, 13) for b in sample):
            return "text/plain"
    return declared_norm or "application/octet-stream"


def _unescape_pdf(raw: str) -> str:
    return (
        raw.replace(r"\(", "(")
        .replace(r"\)", ")")
        .replace(r"\\", "\\")
        .replace(r"\n", "\n")
        .replace(r"\r", "\r")
        .replace(r"\t", "\t")
    )


def _literals(blob: bytes) -> str:
    parts: list[str] = []
    for match in re.finditer(rb"\((?:\\.|[^\\)])*\)", blob):
        inner = match.group(0)[1:-1].decode("latin-1", errors="replace")
        text = _unescape_pdf(inner).strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def extract_pdf_text(data: bytes) -> tuple[str, int, list[dict[str, Any]]]:
    page_count = len(re.findall(rb"/Type\s*/Page(?!s)", data)) or 1
    pages: list[dict[str, Any]] = []
    chunks: list[str] = []
    for index, match in enumerate(re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S), start=1):
        raw = match.group(1)
        header = data[max(0, match.start() - 300) : match.start()]
        blob = raw
        if b"FlateDecode" in header:
            try:
                blob = zlib.decompress(raw)
            except zlib.error:
                pages.append({"page_number": index, "text": "", "readable": False})
                continue
        text = _literals(blob)
        pages.append({"page_number": index, "text": text, "readable": bool(text)})
        if text:
            chunks.append(text)
    if not pages and chunks:
        pages = [{"page_number": 1, "text": "\n".join(chunks), "readable": True}]
    return "\n".join(chunks).strip(), page_count, pages


def extract_document(data: bytes, declared_type: str | None) -> dict[str, Any]:
    detected = detect_type(data, declared_type)
    base: dict[str, Any] = {
        "detected_type": detected,
        "declared_type": (declared_type or "").split(";")[0].strip().lower(),
        "text": "",
        "page_count": None,
        "pages": [],
        "extraction_status": "failed",
        "error": None,
    }
    if not data:
        base["error"] = "empty_file"
        return base
    if detected in IMAGE_TYPES:
        base["extraction_status"] = "ocr_unavailable"
        base["page_count"] = 1
        base["pages"] = [{"page_number": 1, "text": "", "readable": False}]
        base["error"] = "ocr_engine_not_configured"
        return base
    if detected == "text/plain":
        text = data.decode("utf-8", errors="replace").strip()
        base["text"] = text
        base["page_count"] = 1
        base["pages"] = [{"page_number": 1, "text": text, "readable": bool(text)}]
        base["extraction_status"] = "extracted" if text else "empty"
        return base
    if detected == "application/pdf":
        if not data.startswith(b"%PDF"):
            base["error"] = "corrupt_pdf"
            return base
        try:
            text, page_count, pages = extract_pdf_text(data)
        except Exception:
            base["error"] = "corrupt_pdf"
            return base
        base["text"] = text
        base["page_count"] = page_count
        base["pages"] = pages
        if not text:
            base["extraction_status"] = "empty"
            base["error"] = "no_embedded_text"
        elif len(text) < 15:
            base["extraction_status"] = "partial"
        else:
            base["extraction_status"] = "extracted"
        return base
    base["extraction_status"] = "unsupported"
    base["error"] = "format_not_implemented"
    return base
