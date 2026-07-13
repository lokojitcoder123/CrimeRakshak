"""Agent tools for the conversational interface.

Phase 1 exposes a single grounded tool, ``query_crime_stats``, which lets the
LLM run a validated read-only SQL query against the DuckDB crime-statistics
tables. The tool schema is what the model sees; execution goes through the
safe executor in :mod:`app.chat.data.query`.

Later phases register additional tools (Neo4j case-level tools for Block 6)
into ``TOOL_SPECS`` / ``TOOL_IMPLS`` here.
"""
from __future__ import annotations

import json
from functools import lru_cache

from app.chat.data.query import run_query, UnsafeQueryError
from app.chat.data.schema_card import generate_schema_card
from app.chat.data.loader import build_database


@lru_cache
def get_schema_card() -> str:
    """Build the DuckDB (once) and cache its schema card for the prompt."""
    labels = build_database()
    return generate_schema_card(labels=labels)


# ── Tool implementations ─────────────────────────────────────────────────
def _tool_query_crime_stats(sql: str) -> dict:
    """Execute a read-only SQL query and return rows + provenance."""
    try:
        result = run_query(sql)
    except UnsafeQueryError as exc:
        return {"error": str(exc), "hint": "Only SELECT/WITH queries are allowed."}
    except Exception as exc:  # DuckDB parse/binder errors → let the model retry.
        return {"error": f"Query failed: {exc}"}
    return {
        "sql": result.sql,
        "columns": result.columns,
        "rows": result.rows,
        "row_count": result.row_count,
        "truncated": result.truncated,
    }


# ── OpenAI tool specs ────────────────────────────────────────────────────
TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "query_crime_stats",
            "description": (
                "Run a read-only DuckDB SQL query against Karnataka State "
                "Police aggregate crime-statistics tables to answer questions "
                "about reported cases by district, crime type and period. "
                "Use ONLY the tables/columns from the provided schema. Column "
                "names are case-sensitive; quote them with double quotes. "
                "Exclude summary rows such as 'Total'/'Karnataka' when ranking "
                "or comparing districts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "A single SELECT/WITH statement (no semicolon).",
                    }
                },
                "required": ["sql"],
            },
        },
    }
]

TOOL_IMPLS = {
    "query_crime_stats": _tool_query_crime_stats,
}


def dispatch_tool(name: str, arguments: str) -> tuple[dict, list[str]]:
    """Run a tool by name. Returns (result_dict, source_refs)."""
    impl = TOOL_IMPLS.get(name)
    if impl is None:
        return {"error": f"Unknown tool: {name}"}, []
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return {"error": "Malformed tool arguments."}, []

    result = impl(**args)
    # Provenance: the SQL that produced grounded numbers.
    sources: list[str] = []
    if isinstance(result, dict) and result.get("sql"):
        sources.append(f"crime-stats SQL: {result['sql']}")
    return result, sources
