"""Safe template rendering — no code execution; placeholders validated against allow-list."""

from __future__ import annotations

import re
from string import Template

_ALLOWED_NAME = re.compile(r"^[a-z][a-z0-9_]{0,48}$")


def render_simple_template(body_template: str, variables: dict[str, str], allowed: list[str] | None) -> str:
    if allowed is not None:
        for key in variables:
            if key not in allowed:
                raise ValueError(f"Disallowed template variable: {key}")
        for name in allowed:
            if not _ALLOWED_NAME.match(name):
                raise ValueError(f"Invalid placeholder name in catalog: {name}")
    # string.Template uses $name or ${name}
    tpl = Template(body_template)
    return tpl.safe_substitute(variables)
