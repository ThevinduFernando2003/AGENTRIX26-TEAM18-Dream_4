"""Shared helper: pull the first JSON object out of an LLM response.

Replaces the per-module ``_JSON_RE = re.compile(r"\\{.*\\}", re.DOTALL)`` scanners.
That greedy regex matched from the first ``{`` to the *last* ``}`` in the whole
string, so any trailing prose containing a brace (or a second JSON blob) broke the
parse. This scanner walks the string once, is string-aware (ignores braces inside
quoted strings) and nesting-aware, and returns the first *balanced* object.
"""

from __future__ import annotations

import json


def extract_first_json(raw: str) -> dict | None:
    """Return the first *balanced* {...} object in an LLM response, else None.

    String-aware (ignores braces inside quoted strings) and nesting-aware.
    """
    if not raw:
        return None
    start = raw.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = esc = False
    for i in range(start, len(raw)):
        ch = raw[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(raw[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None
