"""Safe custom form schema validation (no executable definitions)."""

from __future__ import annotations

import re
from typing import Any, Literal

from fastapi import HTTPException, status

FieldType = Literal[
    "short_text",
    "long_text",
    "number",
    "date",
    "select",
    "single_choice",
    "multiple_choice",
    "checkbox",
    "yes_no",
    "file_reference",
]

ALLOWED_FIELD_TYPES: frozenset[str] = frozenset(
    {
        "short_text",
        "long_text",
        "number",
        "date",
        "select",
        "single_choice",
        "multiple_choice",
        "checkbox",
        "yes_no",
        "file_reference",
    }
)

FIELD_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
UNSAFE_PATTERNS = re.compile(r"(<\s*script|javascript:|on\w+\s*=)", re.IGNORECASE)


def _reject_unsafe_string(value: str) -> None:
    if UNSAFE_PATTERNS.search(value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsafe form content rejected")


def validate_form_schema(schema: dict[str, Any]) -> dict[str, Any]:
    fields = schema.get("fields")
    if not isinstance(fields, list) or not fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Form requires at least one field")
    if len(fields) > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Too many form fields")
    seen: set[str] = set()
    normalised: list[dict[str, Any]] = []
    for idx, raw in enumerate(fields):
        if not isinstance(raw, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid field at index {idx}")
        key = raw.get("key")
        if not isinstance(key, str) or not FIELD_KEY_RE.match(key):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid field key: {key!r}")
        if key in seen:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Duplicate field key: {key}")
        seen.add(key)
        field_type = raw.get("type")
        if field_type not in ALLOWED_FIELD_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported field type: {field_type}")
        label = raw.get("label", "")
        if not isinstance(label, str) or not label.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Field {key} requires a label")
        _reject_unsafe_string(label)
        description = raw.get("description")
        if description is not None:
            if not isinstance(description, str):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Field description must be a string")
            _reject_unsafe_string(description)
        required = bool(raw.get("required", False))
        order = raw.get("order", idx)
        if not isinstance(order, int) or order < 0:
            order = idx
        field: dict[str, Any] = {
            "key": key,
            "type": field_type,
            "label": label.strip(),
            "required": required,
            "order": order,
        }
        if description:
            field["description"] = description.strip()
        options = raw.get("options")
        if field_type in {"select", "single_choice", "multiple_choice"}:
            if not isinstance(options, list) or not options:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Field {key} requires options")
            clean_opts: list[str] = []
            for opt in options:
                if not isinstance(opt, str) or not opt.strip():
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid option in {key}")
                _reject_unsafe_string(opt)
                clean_opts.append(opt.strip())
            field["options"] = clean_opts
        validation = raw.get("validation")
        if validation is not None:
            if not isinstance(validation, dict):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Validation must be an object")
            allowed_validation = {k: validation[k] for k in ("min_length", "max_length", "min", "max") if k in validation}
            field["validation"] = allowed_validation
        normalised.append(field)
    normalised.sort(key=lambda f: f.get("order", 0))
    return {"fields": normalised}


def validate_answers(schema: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    schema = validate_form_schema(schema)
    if not isinstance(answers, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Answers must be an object")
    validated: dict[str, Any] = {}
    for field in schema["fields"]:
        key = field["key"]
        value = answers.get(key)
        if value is None or value == "":
            if field.get("required"):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing required field: {key}")
            continue
        ftype = field["type"]
        if ftype == "short_text":
            if not isinstance(value, str):
                raise HTTPException(status_code=400, detail=f"{key} must be text")
            _reject_unsafe_string(value)
            validated[key] = value.strip()
        elif ftype == "long_text":
            if not isinstance(value, str):
                raise HTTPException(status_code=400, detail=f"{key} must be text")
            _reject_unsafe_string(value)
            validated[key] = value
        elif ftype == "number":
            if not isinstance(value, (int, float)):
                raise HTTPException(status_code=400, detail=f"{key} must be a number")
            validated[key] = value
        elif ftype == "date":
            if not isinstance(value, str) or len(value) > 32:
                raise HTTPException(status_code=400, detail=f"{key} must be an ISO date string")
            validated[key] = value
        elif ftype in {"select", "single_choice"}:
            if not isinstance(value, str):
                raise HTTPException(status_code=400, detail=f"{key} must be a string option")
            if value not in field.get("options", []):
                raise HTTPException(status_code=400, detail=f"Invalid option for {key}")
            validated[key] = value
        elif ftype == "multiple_choice":
            if not isinstance(value, list):
                raise HTTPException(status_code=400, detail=f"{key} must be a list")
            opts = field.get("options", [])
            for item in value:
                if item not in opts:
                    raise HTTPException(status_code=400, detail=f"Invalid option for {key}")
            validated[key] = value
        elif ftype == "checkbox":
            validated[key] = bool(value)
        elif ftype == "yes_no":
            if value not in (True, False, "yes", "no"):
                raise HTTPException(status_code=400, detail=f"{key} must be yes/no")
            validated[key] = value is True or value == "yes"
        elif ftype == "file_reference":
            if not isinstance(value, str):
                raise HTTPException(status_code=400, detail=f"{key} must be a file reference id")
            validated[key] = value
    extra = set(answers.keys()) - set(validated.keys()) - {f["key"] for f in schema["fields"] if not f.get("required")}
    if extra:
        raise HTTPException(status_code=400, detail=f"Unexpected answer keys: {', '.join(sorted(extra))}")
    return validated
