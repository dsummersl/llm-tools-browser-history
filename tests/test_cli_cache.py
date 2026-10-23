from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from browser_history.mcp_server import cli


def test_cli_use_cache_passed_to_make_mcp():
    runner = CliRunner()
    with (
        patch("browser_history.mcp_server.make_mcp") as mock_make_mcp,
        patch("browser_history.mcp_server.load_whitelist", return_value={}),
    ):
        mock_mcp = MagicMock()
        mock_make_mcp.return_value = mock_mcp

        result = runner.invoke(cli, ["--use-cache"])

        assert result.exit_code == 0
        mock_make_mcp.assert_called_once()
        args, kwargs = mock_make_mcp.call_args
        assert kwargs.get("use_cache") is True


def test_cli_no_cache_passed_to_make_mcp():
    runner = CliRunner()
    with (
        patch("browser_history.mcp_server.make_mcp") as mock_make_mcp,
        patch("browser_history.mcp_server.load_whitelist", return_value={}),
    ):
        mock_mcp = MagicMock()
        mock_make_mcp.return_value = mock_mcp

        result = runner.invoke(cli, ["--no-cache"])

        assert result.exit_code == 0
        mock_make_mcp.assert_called_once()
        args, kwargs = mock_make_mcp.call_args
        assert kwargs.get("use_cache") is False


def test_cli_use_cache_passed_to_run_single_query():
    runner = CliRunner()
    with (
        patch("browser_history.mcp_server._run_single_query") as mock_run_query,
        patch("browser_history.mcp_server.load_whitelist", return_value={}),
    ):
        result = runner.invoke(cli, ["--use-cache", "--query", "SELECT 1"])

        assert result.exit_code == 0
        mock_run_query.assert_called_once()
        args, kwargs = mock_run_query.call_args
        assert kwargs.get("use_cache") is True
