# 4. MCP Standalone Service

Date: 2025-12-10

## Status

accepted

## Context

Currently, this project is implemented as an llm-tools plugin that works exclusively with the `llm` command-line tool. While this integration is valuable, it limits the tool's usability in the broader LLM ecosystem.

We want to support additional LLM services and applications:
- Claude, OpenAI and Gemini's LLM cli tools.
- Other LLM systems (vim tools, desktop apps etc)

## Decision

Implement a standalone MCP server mode for the browser history tool while maintaining the existing llm-tools plugin functionality.

Key design decisions:

1. **Dual Interface**: Support both llm-tools plugin and MCP server modes
   - Keep existing `browser_history/__init__.py` for llm-tools integration
   - Add new `browser_history/mcp_server.py` for MCP server implementation

2. **MCP Server Implementation**:
   - Use the official Python MCP SDK (`mcp` package)
   - Expose a single MCP tool: `search_browser_history`
   - Accept the same SQL query interface as the existing tool
   - Maintain all existing security controls (row limits, data sanitization)

## Consequences

What becomes easier or more difficult to do and any risks introduced by the change that will need to be mitigated.
