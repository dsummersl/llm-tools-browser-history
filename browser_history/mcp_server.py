import logging
import importlib.metadata
import click
import atexit
from pathlib import Path
from typing import Any, Iterable, Literal, get_args

from mcp.server.fastmcp import FastMCP

from .browser_types import BrowserType
from .toolbox import BrowserHistory
from .sqlite import cleanup_unified_db, get_or_create_unified_db, run_unified_query_with_headers
from .qp_whitelist import load_whitelist, Whitelist

logger = logging.getLogger(__name__)

LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def get_version() -> str:
    try:
        return importlib.metadata.version("llm-tools-browser-history")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0-dev"


def make_mcp(sources: Iterable[str], max_rows: int, whitelist: Whitelist | None = None) -> FastMCP:
    mcp = FastMCP("browser-history", stateless_http=True, json_response=True)

    # Pass sources and max_rows to BrowserHistory
    browser_history = BrowserHistory(sources, max_rows, whitelist=whitelist)

    @mcp.tool(description=browser_history.search.__doc__)
    def search(sql: str) -> list[Any]:
        return browser_history._do_search(sql)

    return mcp


def _stringify_row(row: Any) -> list[str]:
    """Convert a row of values to strings, replacing None with empty string."""
    return [str(v) if v is not None else "" for v in row]


def _column_widths(all_rows: list[list[str]]) -> list[int]:
    """Compute the max width for each column across all rows (including header)."""
    widths = [0] * (len(all_rows[0]) if all_rows else 0)
    for row in all_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    return widths


def _format_table(headers: list[str], rows: list[Any]) -> str:
    """Format *headers* and *rows* as an aligned text table."""
    str_rows = [_stringify_row(row) for row in rows]
    widths = _column_widths([headers] + str_rows)
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    separator = ["-" * w for w in widths]
    lines = [fmt.format(*headers), fmt.format(*separator)]
    lines.extend(fmt.format(*row) for row in str_rows)
    return "\n".join(lines)


def _run_single_query(
    sources: tuple[str, ...],
    max_rows: int,
    whitelist: Whitelist,
    sql: str,
) -> None:
    """Execute a single SQL query, print a human-readable table, then exit."""
    try:
        bh = BrowserHistory(sources or None, max_rows, whitelist=whitelist)
        conn = get_or_create_unified_db(bh.sources, whitelist=whitelist)
        headers, rows = run_unified_query_with_headers(conn, sql, max_rows=max_rows)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from None
    finally:
        cleanup_unified_db()

    if not rows:
        click.echo("(no results)")
        return

    click.echo(_format_table(headers, rows))
    click.echo(f"\n({len(rows)} row{'s' if len(rows) != 1 else ''})")


@click.command()
@click.version_option(version=get_version(), prog_name="browser-history-mcp")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help="Specify the transport method (stdio, sse, streamable-http)",
)
@click.option(
    "--sources",
    multiple=True,
    type=click.Choice(get_args(BrowserType)),
    default=None,
    help="Specify one or more browsers (default: all detected browsers)",
)
@click.option(
    "--max-rows",
    type=int,
    default=100,
    show_default=True,
    help="Maximum rows to return from a search",
)
@click.option(
    "--log-level",
    "-l",
    type=click.Choice(list(LOG_LEVELS.keys())),
    default="warning",
    show_default=True,
    help="Set the logging level",
)
@click.option(
    "--qp-whitelist",
    "qp_whitelist_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to a YAML file mapping domains to allowed query-parameter keys. "
    "When omitted the built-in default whitelist is used.",
)
@click.option(
    "--query",
    "single_query",
    type=str,
    default=None,
    help="Execute a single SQL query against the browser history, print results, and exit.",
)
def cli(
    transport: str,
    sources: tuple[str, ...],
    max_rows: int,
    log_level: str,
    qp_whitelist_path: Path | None,
    single_query: str | None,
) -> None:
    logging.basicConfig(level=LOG_LEVELS[log_level])

    whitelist = load_whitelist(qp_whitelist_path)

    if single_query is not None:
        _run_single_query(sources, max_rows, whitelist, single_query)
        return

    atexit.register(cleanup_unified_db)
    transport_mode: Literal["stdio", "sse", "streamable-http"] = transport  # type: ignore[assignment]
    make_mcp(sources, max_rows, whitelist=whitelist).run(transport=transport_mode)


if __name__ == "__main__":
    cli()
