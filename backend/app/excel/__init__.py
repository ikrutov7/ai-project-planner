"""Excel column schema and helpers."""

from __future__ import annotations

REQUIRED_HEADERS = {
    "задача": "name",
    "описание": "description",
    "исполнитель": "assignee",
    "длительность": "duration",
    "предшественники": "predecessors",
}

# Also accept English aliases
HEADER_ALIASES = {
    **REQUIRED_HEADERS,
    "task": "name",
    "name": "name",
    "description": "description",
    "assignee": "assignee",
    "duration": "duration",
    "duration_days": "duration",
    "predecessors": "predecessors",
    "predecessor": "predecessors",
}

EXPORT_HEADERS_RU = ["задача", "описание", "исполнитель", "длительность", "предшественники"]
EXPORT_EXTRA = ["id", "start_date", "end_date"]
