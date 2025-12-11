import logging
import click
from typing import Any

from mcp.server.fastmcp import FastMCP

from .toolbox import BrowserHistory

logger = logging.getLogger(__name__)


def make_mcp() -> FastMCP:
    mcp = FastMCP("browser-history", stateless_http=True, json_response=True)

    # TODO add additional configuration options that BrowserHistory supports.
    browser_history = BrowserHistory()

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
def cli(transport):
    logging.basicConfig(level=logging.INFO)
    make_mcp().run(transport=transport)


if __name__ == "__main__":
    cli()
