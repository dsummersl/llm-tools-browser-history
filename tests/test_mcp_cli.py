import logging
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from browser_history.mcp_server import cli, get_version


def test_cli_log_level_debug():
    runner = CliRunner()
    with (
        patch("logging.basicConfig") as mock_logging_config,
        patch("browser_history.mcp_server.make_mcp") as mock_make_mcp,
        patch("browser_history.mcp_server.load_whitelist", return_value={}),
    ):
        # Mock make_mcp to return a mock that has a run method
        mock_mcp = MagicMock()
        mock_make_mcp.return_value = mock_mcp

        # Test with -l debug
        result = runner.invoke(cli, ["-l", "debug"])

        assert result.exit_code == 0
        mock_logging_config.assert_called_once_with(level=logging.DEBUG)


def test_cli_log_level_default():
    runner = CliRunner()
    with (
        patch("logging.basicConfig") as mock_logging_config,
        patch("browser_history.mcp_server.make_mcp") as mock_make_mcp,
        patch("browser_history.mcp_server.load_whitelist", return_value={}),
    ):
        mock_mcp = MagicMock()
        mock_make_mcp.return_value = mock_mcp

        result = runner.invoke(cli, [])

        assert result.exit_code == 0
        # The plan says default should be logging.WARNING
        mock_logging_config.assert_called_once_with(level=logging.WARNING)


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "browser-history-mcp" in result.output


def test_get_version_returns_string():
    v = get_version()
    assert isinstance(v, str)
    assert len(v) > 0


def test_cli_query_flag():
    runner = CliRunner()
    with (
        patch("browser_history.mcp_server.BrowserHistory") as mock_bh_cls,
        patch("browser_history.mcp_server.load_whitelist", return_value={}),
        patch("browser_history.mcp_server.cleanup_unified_db"),
    ):
        mock_bh = MagicMock()
        mock_bh.search.return_value = '["result"]'
        mock_bh_cls.return_value = mock_bh

        result = runner.invoke(cli, ["--query", "SELECT 1"])

        assert result.exit_code == 0
        mock_bh.search.assert_called_once_with("SELECT 1")
        assert '["result"]' in result.output
