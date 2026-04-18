# README Restructure Design

**Goal:** Reorganize the README so users are routed to the correct install path immediately — Claude Desktop / Claude Code users see the `.mcpb` flow first, all other client users follow the manual install path — without either audience having to skip irrelevant content.

**Problem:** The current README is linear and buries the `.mcpb` installation section at the bottom. A Claude Desktop user follows the entire manual wheel-build flow before discovering the simpler bundle install exists.

**Audience:** Anyone who wants to use the Yahoo Fantasy MCP with their AI agent, regardless of client.

---

## Structure

### Shared: Top

1. **Description** — unchanged
2. **Setting up a Yahoo Developer App** — unchanged, moved up before the install paths since it applies to both

### Path A: Claude Desktop / Claude Code

Self-contained section covering everything a Claude Desktop or Claude Code user needs:

- Install the `.mcpb` bundle: double-click or `mcpb install <file>`
- Prompt at install time for Yahoo Client ID and Client Secret
- First-use authentication: the server returns a copy/pastable error command the first time a tool is invoked; user pastes it in a terminal, approves in browser, pastes verifier code

No wheel build, no `.env`, no manual JSON config needed.

### Path B: All Other Clients

Self-contained section covering everything users of other MCP clients (Cursor, Windsurf, etc.) need:

- Prerequisites: Python 3.11+, uv
- Build the wheel and install as a uv tool
- Configuration: copy `.env.example` to `.env`, fill in credentials
- Authentication: run `yahoo-fantasy-mcp-auth` once in a terminal
- MCP Configuration: JSON snippet and config file locations per client

### Shared: Bottom

- **Development / Running Tests** — for contributors
- **Available Tools** — tool reference table
- **Typical Workflow** — usage guide

---

## Design Decisions

- **`.mcpb` is Claude-only.** The bundle format (`@anthropic-ai/mcpb`) is supported only by Claude Desktop and Claude Code. Other clients use their own config formats. The path labels reflect this precisely.
- **Yahoo Developer App setup stays shared.** Both paths require the user to create a Yahoo app and obtain a Client ID and Secret. It makes sense to do this once, before the paths diverge.
- **Development section stays at the bottom.** Contributors need it; end users don't. Keeping it below the install paths avoids cluttering the primary user journey.
- **No content is removed.** All existing information is preserved; only the order and grouping changes.
