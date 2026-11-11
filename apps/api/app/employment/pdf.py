"""A4-oriented CV PDF generation using the existing minimal PDF builder."""

from __future__ import annotations

from typing import Any

from app.evidence.pdf import build_simple_pdf


def _lines_for_section(heading: str, body: list[str]) -> list[str]:
    out = [heading.upper(), "-" * min(40, len(heading) + 4)]
    out.extend(body or ["Not provided"])
    out.append("")
    return out


def render_cv_lines(*, title: str, template_id: str, content: dict[str, Any], section_order: list[str]) -> list[str]:
    lines: list[str] = [
        f"Template: {template_id.replace('_', ' ')}",
        "",
    ]
    contact = content.get("contact") if isinstance(content.get("contact"), dict) else {}
    for section in section_order:
        if section == "personal_profile":
            profile = content.get("personal_profile")
            lines.extend(_lines_for_section("Personal profile", [str(profile)] if profile else []))
        elif section == "contact":
            body = [
                f"{key}: {value}"
                for key, value in (contact or {}).items()
                if value not in (None, "")
            ]
            lines.extend(_lines_for_section("Contact", body))
        elif section in {"employment", "education", "qualifications", "skills", "certificates", "volunteer", "projects", "languages", "references"}:
            rows = content.get(section) or []
            body: list[str] = []
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, dict):
                        parts = [str(v) for v in row.values() if v not in (None, "")]
                        body.append(" — ".join(parts)[:110])
                    else:
                        body.append(str(row)[:110])
            lines.extend(_lines_for_section(section.replace("_", " "), body))
    lines.append("Self-reported information. Certificates listed separately from skills.")
    return lines


def build_cv_pdf(*, title: str, template_id: str, content: dict[str, Any], section_order: list[str]) -> bytes:
    lines = render_cv_lines(title=title, template_id=template_id, content=content, section_order=section_order)
    # Paginate by regenerating with chunks if needed — builder supports one page; truncate safely.
    return build_simple_pdf(title[:120], lines[:55])
