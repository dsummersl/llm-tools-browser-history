# Design: Log Level Parameter and Provider Debugging

Add a `-l/--log-level` parameter to the CLI to control logging verbosity and add debug statements to browser providers for better transparency.

## Architecture

### CLI Configuration
- **File:** `browser_history/mcp_server.py`
- **Mapping:** A constant `LOG_LEVELS` mapping lowercase strings (`debug`, `info`, `warning`, `error`, `critical`) to `logging` constants.
- **Option:** `-l/--log-level` using `click.Choice` derived from `LOG_LEVELS.keys()`.
- **Default:** `warning`.

### Provider Logging
- **Chrome:** `browser_history/chrome.py` will log each path it attempts to check for history files.
- **Firefox:** `browser_history/firefox.py` will log profile discovery and specific database paths.
- **Safari:** `browser_history/safari.py` will log the Safari history database path it checks.

## Implementation Steps

1. **Update CLI:**
    - Define `LOG_LEVELS` in `mcp_server.py`.
    - Add `--log-level` option to the `cli` command.
    - Update `logging.basicConfig` to use the mapped level.
2. **Add Debug Logs:**
    - Inject `logger.debug` statements into browser discovery logic.
3. **Verification:**
    - Run with `-l debug` to confirm provider paths are visible.
    - Run without flags to confirm `warning` default (debug logs hidden).
    - Run `make ci` to ensure no regressions.

## Success Criteria
- User can specify log level via CLI.
- Default level is `warning`.
- Debug logs reveal the filesystem paths being searched by providers.
