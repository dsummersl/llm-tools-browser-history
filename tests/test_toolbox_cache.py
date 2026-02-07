from unittest.mock import patch, MagicMock
from browser_history.toolbox import BrowserHistory
from browser_history.sqlite import cleanup_unified_db
import pytest


@pytest.fixture(autouse=True)
def clean_db():
    cleanup_unified_db()
    yield
    cleanup_unified_db()


def test_browser_history_passes_use_cache():
    """Verify that BrowserHistory passes use_cache to get_or_create_unified_db."""
    with patch("browser_history.toolbox.get_or_create_unified_db") as mock_get_db:
        mock_get_db.return_value = MagicMock()

        # Test with use_cache=True
        bh = BrowserHistory(sources=[], use_cache=True)
        bh._do_search("SELECT 1")

        mock_get_db.assert_called_once()
        args, kwargs = mock_get_db.call_args
        assert kwargs["use_cache"] is True


def test_browser_history_defaults_to_no_cache():
    """Verify that BrowserHistory defaults to use_cache=False."""
    with patch("browser_history.toolbox.get_or_create_unified_db") as mock_get_db:
        mock_get_db.return_value = MagicMock()

        # Test default
        bh = BrowserHistory(sources=[])
        bh._do_search("SELECT 1")

        mock_get_db.assert_called_once()
        args, kwargs = mock_get_db.call_args
        assert kwargs["use_cache"] is False
