"""MCP server implementation for browser history search."""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Sequence
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

from .firefox import find_firefox_places_sqlite
from .chrome import find_chrome_history_paths
from .safari import find_safari_history_paths
from .sqlite import get_or_create_unified_db, run_unified_query

logger = logging.getLogger(__name__)


def get_browser_sources(
    sources: Sequence[str] | None = None,
) -> list[tuple[str, Any]]:
    """Get browser history database paths for specified sources."""
    result: list[tuple[str, Any]] = []

    if not sources:
        sources = ["firefox", "chrome", "safari"]

    if "firefox" in sources:
        for p in find_firefox_places_sqlite():
            result.append(("firefox", p))
    if "chrome" in sources:
        for p in find_chrome_history_paths():
            result.append(("chrome", p))
    if "safari" in sources:
        for p in find_safari_history_paths():
            result.append(("safari", p))

    return result


async def serve() -> None:
    """Run the MCP server."""
    server = Server("browser-history")

    # Initialize browser sources once at startup
    browser_sources = get_browser_sources()
    logger.info(f"Initialized with {len(browser_sources)} browser history sources")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="search_browser_history",
                description="""Execute a SQL query against a normalized, unified browser history database.

The query can reference the following schema:

    CREATE TABLE IF NOT EXISTS browser_history (
        browser     TEXT NOT NULL,          -- 'chrome' | 'firefox' | 'safari'
        profile     TEXT,                   -- Browser profile name if available
        url         TEXT NOT NULL,          -- The URL visited (query parameters stripped)
        title       TEXT,                   -- The title of the page visited
        referrer_url TEXT,                  -- The referrer URL (NULL on Safari)
        visited_dt  DATETIME NOT NULL       -- UTC datetime of visit
    );

Returns no more than 100 rows. Query parameters are stripped from URLs and timestamps include only the date (not time) for privacy.

Examples:
- SELECT * FROM browser_history WHERE url LIKE '%github.com%' ORDER BY visited_dt DESC
- SELECT * FROM browser_history WHERE lower(title) LIKE lower('%python%') ORDER BY visited_dt DESC
- SELECT browser, COUNT(*) as visits FROM browser_history GROUP BY browser
""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "SQLite SQL query to execute against the browser history database",
                        }
                    },
                    "required": ["sql"],
                },
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
        """Handle tool calls."""
        if name != "search_browser_history":
            raise ValueError(f"Unknown tool: {name}")

        if not isinstance(arguments, dict):
            raise ValueError("Arguments must be a dictionary")

        sql = arguments.get("sql")
        if not sql:
            raise ValueError("Missing required argument: sql")

        try:
            # Get or create unified database
            unified_db = get_or_create_unified_db(browser_sources)

            # Run query
            rows = run_unified_query(unified_db, sql, {})

            # Format results as JSON
            result = json.dumps(rows, indent=2)

            return [TextContent(type="text", text=result)]
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise ValueError(f"Query execution failed: {str(e)}")

    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main() -> None:
    """Main entry point for the MCP server."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())


if __name__ == "__main__":
    main()
