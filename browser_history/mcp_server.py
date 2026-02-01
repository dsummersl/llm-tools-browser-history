import logging
import importlib.metadata
import click
import atexit
from pathlib import Path
from typing import Any, Iterable, Literal, get_args

from mcp.server.fastmcp import FastMCP

from .browser_types import BrowserType
from .toolbox import BrowserHistory
from .sqlite import cleanup_unified_db
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
        browser_history = BrowserHistory(sources or None, max_rows, whitelist=whitelist)
        result = browser_history.search(single_query)
        click.echo(result)
        cleanup_unified_db()
        return

    atexit.register(cleanup_unified_db)
    transport_mode: Literal["stdio", "sse", "streamable-http"] = transport  # type: ignore[assignment]
    make_mcp(sources, max_rows, whitelist=whitelist).run(transport=transport_mode)


if __name__ == "__main__":
    cli()
