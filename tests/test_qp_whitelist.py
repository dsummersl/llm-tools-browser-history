from __future__ import annotations
import pytest

from pathlib import Path

from browser_history.qp_whitelist import (
    load_whitelist,
    process_url,
    _match_domain,
    default_query_param_whitelist,
)


def test_load_default_whitelist():
    wl = load_whitelist(None)
    assert "google.com" in wl
    assert "q" in wl["google.com"]
    assert "youtube.com" in wl
    assert "v" in wl["youtube.com"]


def test_load_whitelist_missing_file():
    with pytest.raises(FileNotFoundError):
        load_whitelist(Path("/nonexistent/file.yaml"))


@pytest.mark.parametrize(
    "file_content,expected",
    [
        ("example.com:\n  - foo\n  - bar\n", {"example.com": ["foo", "bar"]}),
        ("not a mapping", default_query_param_whitelist),
    ],
)
def test_load_whitelist(tmp_path: Path, file_content, expected):
    f = tmp_path / "wl.yaml"
    f.write_text(file_content)
    wl = load_whitelist(f)
    assert wl == expected


def test_match_domain_exact():
    wl = {"google.com": ["q"]}
    assert _match_domain("google.com", wl) == ["q"]


def test_match_domain_subdomain():
    wl = {"google.com": ["q"]}
    assert _match_domain("images.google.com", wl) == ["q"]
    assert _match_domain("www.google.com", wl) == ["q"]


def test_match_domain_specific_over_general():
    wl = {"google.com": ["q"], "images.google.com": ["imgtype"]}
    assert _match_domain("images.google.com", wl) == ["imgtype"]
    assert _match_domain("www.google.com", wl) == ["q"]


def test_match_domain_no_match():
    wl = {"google.com": ["q"]}
    assert _match_domain("example.com", wl) is None


@pytest.mark.parametrize(
    "url, whitelist, expected_url, expected_domain, expected_stripped_qp",
    [
        ("https://example.com/page", {}, "https://example.com/page", "example.com", ""),
        ("https://example.com/page?a=1&b=2", {}, "https://example.com/page", "example.com", "a,b"),
    ],
)
def test_process_url(url, whitelist, expected_url, expected_domain, expected_stripped_qp):
    result = process_url(url, whitelist)
    assert result["url"] == expected_url
    assert result["domain"] == expected_domain
    assert result["stripped_qp"] == expected_stripped_qp


def test_process_url_whitelist_preserves_allowed():
    wl = {"google.com": ["q", "tbm"]}
    result = process_url("https://www.google.com/search?q=pottery+glazes&client=safari", wl)
    assert "q=pottery" in result["url"]
    assert "client" not in result["url"]
    assert result["domain"] == "www.google.com"
    assert result["stripped_qp"] == "client"


def test_process_url_whitelist_strips_all_non_allowed():
    wl = {"google.com": ["q"]}
    result = process_url("https://www.google.com/search?client=safari&source=hp", wl)
    assert "?" not in result["url"]
    assert result["stripped_qp"] == "client,source"


def test_process_url_youtube_video():
    wl = {"youtube.com": ["v", "t"]}
    result = process_url("https://www.youtube.com/watch?v=abc123&feature=share&t=42", wl)
    assert "v=abc123" in result["url"]
    assert "t=42" in result["url"]
    assert "feature" not in result["url"]
    assert result["stripped_qp"] == "feature"


def test_process_url_domain_not_in_whitelist_strips_all():
    wl = {"google.com": ["q"]}
    result = process_url("https://unknown.com/page?secret=token&id=5", wl)
    assert "?" not in result["url"]
    assert result["stripped_qp"] == "id,secret"
