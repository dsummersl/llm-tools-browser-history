# 2. Expose browser history as an LLM toolbox tool

Date: 2025-09-07

## Status

Accepted

## Context

We want a plugin for Simon Willison’s `llm` that lets models search local browser history. Requirements:
- Cross-platform (*nix first: macOS, Linux).
- Read-only access (copy DBs to avoid locks).
- Standardized schema: {url, title, browser, visited_at, visit_count, profile_path}.
- Extendable to multiple browsers.

## Decision

- Implement a `BrowserHistory` toolbox.
- Support Firefox (`places.sqlite`) and Chrome/Chromium (`History`).
- Default profile auto-detected, but user can provide explicit `(browser, path)` tuples.

## Consequences

What becomes easier or more difficult to do and any risks introduced by the change that will need to be mitigated.
- Safe queries even while browsers run.
- Pluggable for more browsers (Edge, Brave, Safari) later.
