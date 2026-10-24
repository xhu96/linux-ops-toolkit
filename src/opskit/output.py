"""Render a list of dict rows as a table, JSON or Markdown."""

from __future__ import annotations

import json
from collections.abc import Sequence


def render(rows: Sequence[dict], columns: Sequence[str], fmt: str = "table") -> str:
    if fmt == "json":
        return json.dumps(list(rows), indent=2, default=str)
    if not rows:
        return "(none)"
    cells = [[str(r.get(c, "")) for c in columns] for r in rows]
    if fmt == "markdown":
        lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
        lines += ["| " + " | ".join(row) + " |" for row in cells]
        return "\n".join(lines)
    widths = [max(len(c), *(len(row[i]) for row in cells)) for i, c in enumerate(columns)]
    lines = ["  ".join(c.upper().ljust(w) for c, w in zip(columns, widths, strict=True))]
    lines += ["  ".join(v.ljust(w) for v, w in zip(row, widths, strict=True)) for row in cells]
    return "\n".join(lines)
