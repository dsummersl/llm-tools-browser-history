# MCP Server Setup

This guide explains how to run the browser history tool as a standalone MCP (Model Context Protocol) server, allowing it to be used with Claude Desktop, Claude Code, and other MCP-compatible clients.

## Installation

### For MCP Server Usage

Install the package with MCP support:

```bash
pip install llm-tools-browser-history[mcp]
```

Or if installing from source:

```bash
pip install -e ".[mcp]"
```

### For llm-tools Only

If you only want to use this with the `llm` command-line tool, you don't need the MCP extras:

```bash
pip install llm-tools-browser-history
```

## Running the MCP Server

Start the server:

```bash
browser-history-mcp
```

The server runs on stdio and communicates using the MCP protocol.

## Configuration for Claude Desktop

To use this tool with Claude Desktop, add it to your Claude Desktop configuration file:

### macOS

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "browser-history": {
      "command": "browser-history-mcp"
    }
  }
}
```

If you installed in a virtual environment, use the full path to the command:

```json
{
  "mcpServers": {
    "browser-history": {
      "command": "/path/to/venv/bin/browser-history-mcp"
    }
  }
}
```

### Linux

Edit `~/.config/Claude/claude_desktop_config.json` with the same configuration as above.

### Windows

Edit `%APPDATA%\Claude\claude_desktop_config.json` with the same configuration as above.

## Configuration for Claude Code

To use this tool with Claude Code, add it to your MCP settings file.

Create or edit `.claude/mcp_settings.json` in your project:

```json
{
  "mcpServers": {
    "browser-history": {
      "command": "browser-history-mcp"
    }
  }
}
```

## Using the Tool

Once configured, you can use the `search_browser_history` tool in your conversations with Claude:

### Example Queries

```
"What pages about Python did I visit recently?"

"Show me a table of my browser usage by browser type over the past month"

"Find all pages I visited from github.com in the last week"
```

### SQL Interface

The tool provides a SQL interface to query browser history. The schema is:

```sql
CREATE TABLE IF NOT EXISTS browser_history (
    browser     TEXT NOT NULL,          -- 'chrome' | 'firefox' | 'safari'
    profile     TEXT,                   -- Browser profile name if available
    url         TEXT NOT NULL,          -- The URL visited (query parameters stripped)
    title       TEXT,                   -- The title of the page visited
    referrer_url TEXT,                  -- The referrer URL (NULL on Safari)
    visited_dt  DATETIME NOT NULL       -- UTC datetime of visit
);
```

### Example SQL Queries

Find pages with "kubernetes" in the title:
```sql
SELECT url, title, visited_dt
FROM browser_history
WHERE lower(title) LIKE '%kubernetes%'
ORDER BY visited_dt DESC
```

Count visits by browser:
```sql
SELECT browser, COUNT(*) as visit_count
FROM browser_history
GROUP BY browser
```

Find most visited domains:
```sql
SELECT
    substr(url, instr(url, '//') + 2,
           instr(substr(url, instr(url, '//') + 2), '/') - 1) as domain,
    COUNT(*) as visits
FROM browser_history
GROUP BY domain
ORDER BY visits DESC
LIMIT 20
```

## Browser Support

The tool automatically detects and searches history from:
- **Firefox** - searches `places.sqlite` files
- **Chrome** - searches `History` database files
- **Safari** - searches `History.db` files

All browsers are queried by default. Multiple profiles are supported if present.

## Privacy and Security

The MCP server maintains the same security controls as the llm-tools version:

- **Read-only**: Operates on copies of browser databases to prevent locks or modifications
- **Limited results**: Returns maximum of 100 rows per query
- **Data sanitization**:
  - Query parameters are stripped from URLs
  - Only date (not time) is included in timestamps
  - Only essential fields are returned (url, title, visit date)

**Warning**: This tool has read access to your entire browser history. Be mindful of what data you're exposing when using it with cloud-based AI services.

## Troubleshooting

### Server not starting

1. Verify installation: `which browser-history-mcp`
2. Test manually: `browser-history-mcp` (should start and wait for input)
3. Check logs in Claude Desktop's developer console

### No browser history found

The tool looks for browser history in standard locations:
- Firefox: `~/.mozilla/firefox/*/places.sqlite`
- Chrome: `~/Library/Application Support/Google/Chrome/*/History` (macOS)
- Safari: `~/Library/Safari/History.db` (macOS)

Ensure your browsers have been used and have history files in these locations.

### Permission errors

On macOS, you may need to grant terminal or IDE permissions to access browser history files. Check System Preferences > Security & Privacy > Privacy > Full Disk Access.

## Development

To contribute or modify the MCP server implementation, see `browser_history/mcp_server.py`.

The implementation uses the official Python MCP SDK and maintains compatibility with the llm-tools interface by sharing the core query logic.
