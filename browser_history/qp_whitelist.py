from __future__ import annotations

import logging
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlparse, urlencode, parse_qs

import yaml

logger = logging.getLogger(__name__)

Whitelist = dict[str, list[str]]


default_query_param_whitelist: Whitelist = {
    "google.com": ["q", "tbm"],
    "bing.com": ["q"],
    "duckduckgo.com": ["q", "tbm"],
    "ebay.com": ["_nkw", "_sacat"],
    "youtube.com": ["v", "t", "list", "search_query"],
    "vimeo.com": ["q"],
    "amazon.com": ["k", "field-keywords"],
    "github.com": ["q", "type", "l"],
    "reddit.com": ["q"],
    "wikipedia.org": ["search"],
    "maps.google.com": ["q"],
}


class ProcessedURL(TypedDict):
    url: str
    domain: str
    stripped_qp: str


def _read_yaml(path: Path | None) -> Whitelist:
    if path is not None:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            logger.warning("Error reading whitelist from %s; using default", path)
            return default_query_param_whitelist
        data: object = yaml.safe_load(text)
        return _validate_whitelist(data)
    else:
        return default_query_param_whitelist


def _validate_whitelist(data: object) -> Whitelist:
    if not isinstance(data, dict):
        logger.warning("Whitelist YAML is not a mapping; using default parameters")
        return default_query_param_whitelist
    result: Whitelist = {}
    for domain, keys in data.items():
        if isinstance(keys, list):
            result[str(domain)] = [str(k) for k in keys]
        else:
            logger.warning("Ignoring non-list value for domain %s in whitelist", domain)
    return result


def load_whitelist(path: Path | None) -> Whitelist:
    return _read_yaml(path)


def _match_domain(hostname: str, whitelist: Whitelist) -> list[str] | None:
    parts = hostname.lower().split(".")
    for i in range(len(parts)):
        candidate = ".".join(parts[i:])
        if candidate in whitelist:
            return whitelist[candidate]
    return None


def _partition_params(
    query_params: dict[str, list[str]], allowed_keys: list[str]
) -> tuple[dict[str, list[str]], list[str]]:
    kept: dict[str, list[str]] = {}
    stripped: list[str] = []
    for key, values in query_params.items():
        if key in allowed_keys:
            kept[key] = values
        else:
            stripped.append(key)
    return kept, stripped


def _replace_query(raw_url: str, query: str) -> str:
    return urlparse(raw_url)._replace(query=query).geturl()


def _apply_allowed_keys(
    raw_url: str, domain: str, query_params: dict[str, list[str]], allowed_keys: list[str]
) -> ProcessedURL:
    kept, stripped = _partition_params(query_params, allowed_keys)
    new_query = urlencode([(k, v) for k in kept for v in kept[k]]) if kept else ""
    return ProcessedURL(
        url=_replace_query(raw_url, new_query),
        domain=domain,
        stripped_qp=",".join(sorted(stripped)),
    )


def process_url(raw_url: str, whitelist: Whitelist) -> ProcessedURL:
    domain = urlparse(raw_url).hostname or ""
    query_params = parse_qs(urlparse(raw_url).query, keep_blank_values=True)

    if not query_params:
        return ProcessedURL(url=raw_url, domain=domain, stripped_qp="")

    allowed_keys = _match_domain(domain, whitelist)
    if allowed_keys is None:
        allowed_keys = []

    return _apply_allowed_keys(raw_url, domain, query_params, allowed_keys)
