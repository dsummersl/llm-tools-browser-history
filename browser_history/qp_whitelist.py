"""Query-parameter whitelist: load config and process URLs."""

from __future__ import annotations

import logging
from importlib import resources
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlparse, urlencode, parse_qs

import yaml

logger = logging.getLogger(__name__)

Whitelist = dict[str, list[str]]


class ProcessedURL(TypedDict):
    url: str
    domain: str
    stripped_qp: str


def load_whitelist(path: Path | None) -> Whitelist:
    """Load a whitelist YAML file.

    If *path* is ``None`` the built-in default is used.
    On any error the function logs a warning and returns an empty dict
    (which makes every domain fall back to "strip all").
    """
    if path is None:
        try:
            ref = resources.files("browser_history").joinpath("default_whitelist.yaml")
            text = ref.read_text(encoding="utf-8")
            data = yaml.safe_load(text)
        except Exception:
            logger.warning("Failed to load built-in default whitelist; stripping all query params")
            return {}
    else:
        try:
            text = path.read_text(encoding="utf-8")
            data = yaml.safe_load(text)
        except Exception:
            logger.warning(
                "Failed to load whitelist from %s; stripping all query params", path
            )
            return {}

    if not isinstance(data, dict):
        logger.warning("Whitelist YAML is not a mapping; stripping all query params")
        return {}

    # Normalise values to list[str]
    result: Whitelist = {}
    for domain, keys in data.items():
        if isinstance(keys, list):
            result[str(domain)] = [str(k) for k in keys]
        else:
            logger.warning("Ignoring non-list value for domain %s in whitelist", domain)
    return result


def _match_domain(hostname: str, whitelist: Whitelist) -> list[str] | None:
    """Return the allowed keys for *hostname*, walking up parent domains.

    Returns ``None`` when no rule matches (meaning "strip all").
    """
    # Try exact match first, then progressively strip subdomains.
    parts = hostname.lower().split(".")
    for i in range(len(parts)):
        candidate = ".".join(parts[i:])
        if candidate in whitelist:
            return whitelist[candidate]
    return None


def process_url(raw_url: str, whitelist: Whitelist) -> ProcessedURL:
    """Apply the whitelist to a single URL.

    Returns a :class:`ProcessedURL` with the cleaned URL, the domain,
    and a comma-separated list of stripped parameter *names*.
    """
    parsed = urlparse(raw_url)
    domain = parsed.hostname or ""

    if not parsed.query:
        return ProcessedURL(url=raw_url, domain=domain, stripped_qp="")

    query_params = parse_qs(parsed.query, keep_blank_values=True)
    allowed_keys = _match_domain(domain, whitelist)

    if allowed_keys is None:
        # No rule → strip all
        stripped_names = sorted(query_params.keys())
        clean_url = parsed._replace(query="").geturl()
        return ProcessedURL(
            url=clean_url,
            domain=domain,
            stripped_qp=",".join(stripped_names),
        )

    kept: dict[str, list[str]] = {}
    stripped_names: list[str] = []
    for key, values in query_params.items():
        if key in allowed_keys:
            kept[key] = values
        else:
            stripped_names.append(key)

    if kept:
        new_query = urlencode(
            [(k, v) for k in kept for v in kept[k]],
        )
        clean_url = parsed._replace(query=new_query).geturl()
    else:
        clean_url = parsed._replace(query="").geturl()

    return ProcessedURL(
        url=clean_url,
        domain=domain,
        stripped_qp=",".join(sorted(stripped_names)),
    )
