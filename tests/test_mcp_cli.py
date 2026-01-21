import logging
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from browser_history.mcp_server import cli


def test_cli_log_level_debug():
    runner = CliRunner()
    with (
        patch("logging.basicConfig") as mock_logging_config,
        patch("browser_history.mcp_server.make_mcp") as mock_make_mcp,
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
    ):
        mock_mcp = MagicMock()
        mock_make_mcp.return_value = mock_mcp

        result = runner.invoke(cli, [])

        assert result.exit_code == 0
        # The plan says default should be logging.WARNING
        mock_logging_config.assert_called_once_with(level=logging.WARNING)
