# Log Level Parameter and Provider Debugging Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `-l/--log-level` parameter to the CLI and implement debug logging in browser providers to show search paths.

**Architecture:** 
- Define a central `LOG_LEVELS` mapping in `mcp_server.py`.
- Update the Click CLI to accept `--log-level` with choices derived from the mapping.
- Inject `logger.debug` statements into the discovery logic of Chrome, Firefox, and Safari providers.

**Tech Stack:** Python, Click, logging

---

### [x] Task 1: Add Log Level Parameter to CLI

**Files:**
- [x] Modify: `browser_history/mcp_server.py`
- [x] Create: `tests/test_mcp_cli.py`

**Step 1: Write the failing test** [x]

We want to verify that the CLI accepts the `-l` parameter and configures logging correctly.

**Step 2: Run test to verify it fails** [x]

Run: `pytest tests/test_mcp_cli.py`
Expected: FAIL (Option `-l` not recognized or `logging.basicConfig` called with `INFO`)

**Step 3: Write minimal implementation** [x]

Modify `browser_history/mcp_server.py`:
1. Define `LOG_LEVELS` mapping.
2. Add `@click.option("--log-level", "-l", ...)` to `cli`.
3. Update `logging.basicConfig(level=...)` in `cli`.

**Step 4: Run test to verify it passes** [x]

Run: `pytest tests/test_mcp_cli.py`
Expected: PASS

**Step 5: Commit** [x]

```bash
git add browser_history/mcp_server.py tests/test_mcp_cli.py
git commit -m "feat: add -l/--log-level parameter to CLI"
```

---

### [x] Task 2: Add Debug Logging to Chrome Provider

**Files:**
- [x] Modify: `browser_history/chrome.py`

**Step 1: Identify insertion point** [x]

Find where Chrome paths are checked.

**Step 2: Add debug logs** [x]

**Step 3: Verify manually** [x]

Run: `uv run browser-history-mcp -l debug` (then Ctrl+C)
Check stderr for "Checking for Chrome history at: ..."

**Step 4: Commit** [x]

```bash
git add browser_history/chrome.py
git commit -m "feat: add debug logging to Chrome provider"
```

---

### [x] Task 3: Add Debug Logging to Firefox Provider

**Files:**
- [x] Modify: `browser_history/firefox.py`

**Step 1: Identify insertion point** [x]

Find where Firefox profiles and paths are resolved.

**Step 2: Add debug logs** [x]

**Step 3: Verify manually** [x]

Run: `uv run browser-history-mcp -l debug` (then Ctrl+C)
Check stderr for Firefox logs.

**Step 4: Commit** [x]

```bash
git add browser_history/firefox.py
git commit -m "feat: add debug logging to Firefox provider"
```

---

### [ ] Task 4: Add Debug Logging to Safari Provider

**Files:**
- [ ] Modify: `browser_history/safari.py`

**Step 1: Identify insertion point** [ ]

Find where Safari history path is checked.

**Step 2: Add debug logs** [ ]

```python
# browser_history/safari.py
logger.debug(f"Checking for Safari history at: {safari_path}")
```

**Step 3: Verify manually** [ ]

Run: `uv run browser-history-mcp -l debug` (then Ctrl+C)
Check stderr for Safari logs.

**Step 4: Commit** [ ]

```bash
git add browser_history/safari.py
git commit -m "feat: add debug logging to Safari provider"
```

---

### [ ] Task 5: Final Verification and Cleanup

**Step 1: Run all tests** [ ]

Run: `make ci`
Expected: All tests pass, linting/typing OK.

**Step 2: Verify default behavior** [ ]

Run: `uv run browser-history-mcp`
Expected: No debug logs visible (defaulting to warning).

**Step 3: Final Commit** [ ]

```bash
git commit --allow-empty -m "chore: final verification complete for log-level feature"
```
