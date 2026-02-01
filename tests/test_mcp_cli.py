import logging
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from browser_history.mcp_server import cli, get_version, _format_table


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
        patch("browser_history.mcp_server.get_or_create_unified_db") as mock_get_db,
        patch("browser_history.mcp_server.run_unified_query_with_headers") as mock_query,
        patch("browser_history.mcp_server.cleanup_unified_db"),
    ):
        mock_bh = MagicMock()
        mock_bh.sources = []
        mock_bh_cls.return_value = mock_bh
        mock_get_db.return_value = MagicMock()
        mock_query.return_value = (["name", "val"], [("alice", 1), ("bob", 2)])

        result = runner.invoke(cli, ["--query", "SELECT 1"])

        assert result.exit_code == 0
        assert "name" in result.output
        assert "alice" in result.output
        assert "bob" in result.output
        assert "(2 rows)" in result.output


def test_cli_query_no_results():
    runner = CliRunner()
    with (
        patch("browser_history.mcp_server.BrowserHistory") as mock_bh_cls,
        patch("browser_history.mcp_server.load_whitelist", return_value={}),
        patch("browser_history.mcp_server.get_or_create_unified_db") as mock_get_db,
        patch("browser_history.mcp_server.run_unified_query_with_headers") as mock_query,
        patch("browser_history.mcp_server.cleanup_unified_db"),
    ):
        mock_bh = MagicMock()
        mock_bh.sources = []
        mock_bh_cls.return_value = mock_bh
        mock_get_db.return_value = MagicMock()
        mock_query.return_value = (["name"], [])

        result = runner.invoke(cli, ["--query", "SELECT 1"])

        assert result.exit_code == 0
        assert "(no results)" in result.output


def test_cli_query_error():
    runner = CliRunner()
    with (
        patch("browser_history.mcp_server.BrowserHistory") as mock_bh_cls,
        patch("browser_history.mcp_server.load_whitelist", return_value={}),
        patch("browser_history.mcp_server.get_or_create_unified_db") as mock_get_db,
        patch("browser_history.mcp_server.cleanup_unified_db"),
    ):
        mock_bh = MagicMock()
        mock_bh.sources = []
        mock_bh_cls.return_value = mock_bh
        mock_get_db.side_effect = Exception("bad sql")

        result = runner.invoke(cli, ["--query", "INVALID SQL"])

        assert result.exit_code == 1
        assert "Error: bad sql" in result.output


def test_format_table_basic():
    output = _format_table(["name", "val"], [("alice", 1), ("bob", 2)])
    lines = output.split("\n")
    assert len(lines) == 4  # header + separator + 2 data rows
    assert lines[0] == "name   val"
    assert lines[1] == "-----  ---"
    assert lines[2] == "alice  1  "
    assert lines[3] == "bob    2  "


def test_format_table_columns_widen_for_data():
    output = _format_table(["a", "b"], [("longvalue", "x")])
    lines = output.split("\n")
    # Column 'a' should widen to fit 'longvalue' (9 chars)
    assert lines[0] == "a          b"
    assert lines[1] == "---------  -"
    assert lines[2] == "longvalue  x"


def test_format_table_none_values():
    output = _format_table(["col"], [(None,), ("ok",)])
    lines = output.split("\n")
    assert lines[2].strip() == ""  # None renders as empty string
    assert lines[3].strip() == "ok"


def test_format_table_single_row():
    output = _format_table(["id"], [("only",)])
    lines = output.split("\n")
    assert len(lines) == 3  # header + separator + 1 data row
    assert lines[0] == "id  "
    assert lines[1] == "----"
    assert lines[2] == "only"


def test_cli_query_single_row_says_row_not_rows():
    runner = CliRunner()
    with (
        patch("browser_history.mcp_server.BrowserHistory") as mock_bh_cls,
        patch("browser_history.mcp_server.load_whitelist", return_value={}),
        patch("browser_history.mcp_server.get_or_create_unified_db") as mock_get_db,
        patch("browser_history.mcp_server.run_unified_query_with_headers") as mock_query,
        patch("browser_history.mcp_server.cleanup_unified_db"),
    ):
        mock_bh = MagicMock()
        mock_bh.sources = []
        mock_bh_cls.return_value = mock_bh
        mock_get_db.return_value = MagicMock()
        mock_query.return_value = (["x"], [("one",)])

        result = runner.invoke(cli, ["--query", "SELECT 1"])

        assert result.exit_code == 0
        assert "(1 row)" in result.output
        assert "(1 rows)" not in result.output
