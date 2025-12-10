# 4. MCP Standalone Service

Date: 2025-12-10

## Status

Proposed

## Context

Currently, this project is implemented as an llm-tools plugin that works exclusively with Simon Willison's `llm` command-line tool. While this integration is valuable, it limits the tool's usability to only the `llm` ecosystem.

There is growing demand to use browser history search capabilities with other LLM tools and platforms, including:
- Claude Desktop and Claude Code (via MCP)
- OpenAI's Codex and other development tools
- Custom LLM applications that support MCP (Model Context Protocol)
- Other AI assistants that implement MCP client functionality

The Model Context Protocol (MCP) is an open standard that allows AI models to securely access external data sources and tools. By implementing an MCP server, this tool could be used by any MCP-compatible client, dramatically expanding its utility while maintaining the security and privacy controls already established.

The current implementation already has good separation of concerns:
- Browser-specific history readers (Chrome, Firefox, Safari)
- Unified SQL interface for querying normalized history data
- Security controls (100 row limit, query parameter stripping, date-only timestamps)

This architecture makes it feasible to support both llm-tools and MCP interfaces from the same codebase.

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

3. **Configuration**:
   - Allow configuration of browser sources via environment variables or config file
   - Support standard MCP server configuration patterns
   - Provide clear documentation for connecting from Claude Desktop and other MCP clients

4. **Entry Point**:
   - Add a new console script entry point for running the MCP server
   - Example: `browser-history-mcp` command that starts the server

5. **Shared Core Logic**:
   - Extract common functionality (DB queries, browser readers) into shared modules
   - Both interfaces use the same underlying implementation
   - Maintain single source of truth for schema and security controls

## Consequences

### Benefits
- **Broader Compatibility**: Tool becomes usable with any MCP-compatible LLM client (Claude, Codex, custom apps)
- **Maintained Focus**: Existing llm-tools users are unaffected; both interfaces coexist
- **Standard Protocol**: MCP is an open standard with growing adoption across the AI ecosystem
- **Code Reuse**: Minimal duplication since core logic is already well-factored
- **Security Preservation**: All existing privacy and security controls apply to both interfaces

### Challenges
- **Additional Dependencies**: Need to add MCP SDK as a dependency (can be optional)
- **Testing Complexity**: Must test both interfaces and ensure feature parity
- **Documentation**: Need to document setup for both llm-tools and MCP usage
- **Maintenance**: Two interfaces to maintain, though they share core logic

### Risks to Mitigate
- **Version Drift**: Ensure both interfaces expose the same capabilities (automated tests)
- **Configuration Confusion**: Clear documentation on which mode to use for which use case
- **Dependency Bloat**: Make MCP dependencies optional via extras_require for users who only want llm-tools

### Implementation Plan
1. Add MCP SDK as an optional dependency in pyproject.toml
2. Implement MCP server with search_browser_history tool
3. Add console script entry point for MCP server
4. Create configuration examples for Claude Desktop
5. Update documentation with MCP setup instructions
6. Add integration tests for MCP interface
