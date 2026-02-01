from __future__ import annotations

from pathlib import Path

from browser_history.qp_whitelist import load_whitelist, process_url, _match_domain


def test_load_default_whitelist():
    wl = load_whitelist(None)
    assert "google.com" in wl
    assert "q" in wl["google.com"]
    assert "youtube.com" in wl
    assert "v" in wl["youtube.com"]


def test_load_custom_whitelist(tmp_path: Path):
    f = tmp_path / "wl.yaml"
    f.write_text("example.com:\n  - foo\n  - bar\n")
    wl = load_whitelist(f)
    assert wl == {"example.com": ["foo", "bar"]}


def test_load_whitelist_missing_file():
    wl = load_whitelist(Path("/nonexistent/file.yaml"))
    assert wl == {}


def test_load_whitelist_malformed(tmp_path: Path):
    f = tmp_path / "bad.yaml"
    f.write_text("not a mapping")
    wl = load_whitelist(f)
    assert wl == {}


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


def test_process_url_no_query_params():
    result = process_url("https://example.com/page", {})
    assert result["url"] == "https://example.com/page"
    assert result["domain"] == "example.com"
    assert result["stripped_qp"] == ""


def test_process_url_strip_all_no_whitelist():
    result = process_url("https://example.com/page?a=1&b=2", {})
    assert result["url"] == "https://example.com/page"
    assert result["domain"] == "example.com"
    assert result["stripped_qp"] == "a,b"


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
