import logging
import click
import atexit
from typing import Any, Iterable

from mcp.server.fastmcp import FastMCP

from .toolbox import BrowserHistory
from .sqlite import cleanup_unified_db

logger = logging.getLogger(__name__)


def make_mcp(sources: Iterable[str], max_rows: int) -> FastMCP:
    mcp = FastMCP("browser-history", stateless_http=True, json_response=True)

    # Pass sources and max_rows to BrowserHistory
    browser_history = BrowserHistory(sources, max_rows)

    @mcp.tool(description=browser_history.search.__doc__)
    def search(sql: str) -> list[Any]:
        return browser_history._do_search(sql)

    return mcp

@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help="Specify the transport method (stdio, sse, streamable-http)",
)
@click.option(
    "--sources",
    multiple=True,
    type=click.Choice(["firefox", "safari", "chrome"]),
    default=None,
    help="Specify one or more browsers (default: all detected browsers)"
)
@click.option(
    "--max-rows",
    type=int,
    default=100,
    show_default=True,
    help="Maximum rows to return from a search",
)
def cli(transport, sources, max_rows):
    logging.basicConfig(level=logging.INFO)
    atexit.register(cleanup_unified_db)
    make_mcp(sources, max_rows).run(transport=transport)

if __name__ == "__main__":
    cli()
