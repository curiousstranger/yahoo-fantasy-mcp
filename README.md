# yahoo-fantasy-mcp

An MCP server for Yahoo Fantasy Sports roster management. Exposes read-only tools that let an AI assistant (or any MCP client) list your leagues, inspect your roster, and find free agents and waiver wire pickups.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- A Yahoo Developer App (see [Setting up a Yahoo Developer App](#setting-up-a-yahoo-developer-app) below)

## Setting up a Yahoo Developer App

Yahoo requires each user to create their own developer app. It takes about 5 minutes and is free.

1. Go to [developer.yahoo.com/apps](https://developer.yahoo.com/apps/) and sign in with your Yahoo account.
2. Click **Create an App**.
3. Fill in the fields:
   - **Application Name:** anything you like, e.g. `Fantasy MCP`
   - **Application Type:** select **Installed Application**
   - **Callback Domain:** leave blank or enter `localhost`
4. Under **API Permissions**, expand **Fantasy Sports** and check **Read**.
5. Click **Create App**.
6. Copy your **Consumer Key** and **Consumer Secret** — you'll need both when configuring the server.

> **Why your own app?** Most OAuth2 APIs support PKCE, which lets an installed app ship a single public client ID and have each user authenticate without needing their own credentials. Yahoo's OAuth2 implementation does not support PKCE and requires a client secret for all flows. Since embedding a shared secret in a distributed app is a security risk, each user provides their own key/secret pair instead — your data stays yours and API rate limits apply per-user.

## Build & Install

Build the wheel and install it as a `uv` tool so the `yahoo-fantasy-mcp` binary is on your PATH:

```bash
uv build
uv tool install dist/yahoo_fantasy_mcp-*.whl
```

For development (editable install with test dependencies):

```bash
uv pip install -e ".[dev]"
```

This installs two entry points:

| Command | Purpose |
|---|---|
| `yahoo-fantasy-mcp` | Run the MCP server (stdio transport) |
| `yahoo-fantasy-mcp-auth` | One-time interactive OAuth setup |

## Running Tests

```bash
uv run pytest
```

The test suite covers `api.py`, `auth.py`, and `server.py`. No Yahoo credentials or network access required — all external calls are mocked.

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```dotenv
YAHOO_CLIENT_ID=your_consumer_key_here
YAHOO_CLIENT_SECRET=your_consumer_secret_here

# Optional: override where the OAuth token is stored
# YAHOO_OAUTH_TOKEN_FILE=~/.yahoo_fantasy_oauth2.json
```

The token file (`~/.yahoo_fantasy_oauth2.json` by default) is created automatically during authentication and refreshed on each run.

## Authentication

Run the auth command **once** in a real terminal (not inside an MCP client):

```bash
yahoo-fantasy-mcp-auth
```

If running locally from source without the installed binary:

```bash
uv run --env-file .env yahoo-fantasy-mcp-auth
```

This opens your browser to authorize the Yahoo app. After you approve, paste the verifier code at the prompt. The token is saved and will refresh automatically from then on.

## MCP Configuration

Add this block to your MCP client's config file. The server reads credentials from the `env` map.

```json
{
  "mcpServers": {
    "yahoo-fantasy": {
      "command": "yahoo-fantasy-mcp",
      "env": {
        "YAHOO_CLIENT_ID": "your_consumer_key_here",
        "YAHOO_CLIENT_SECRET": "your_consumer_secret_here"
      }
    }
  }
}
```

Config file locations:

| Client | Path |
|---|---|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Code (global) | `~/.claude/claude_desktop_config.json` |
| Claude Code (project) | `.claude/settings.json` |

## Packaging as an .mcpb Bundle

An `.mcpb` file is a ZIP archive containing the server and a `manifest.json`. It enables single-click installation in Claude Desktop and other MCP hosts without manual configuration.

### Prerequisites

```bash
npm install -g @anthropic-ai/mcpb
```

### manifest.json

A `manifest.json` is included at the project root. It uses the `python` server type and runs the server via `uv run --project`. Update the `author` field before publishing.

The `user_config` section declares `yahoo_client_id` and `yahoo_client_secret` — these are prompted at install time, with the secret stored in the OS keychain.

### Pack the bundle

```bash
mcpb pack
```

This produces `yahoo-fantasy-mcp-0.1.0.mcpb` in the current directory. The `.mcpb` file is a build artifact and is not committed to source control.

### Install the bundle

**Claude Desktop / Claude Code:** Double-click the `.mcpb` file. The host will prompt for your **Yahoo Consumer Key** and **Consumer Secret** — these are the credentials from your [Yahoo Developer App](#setting-up-a-yahoo-developer-app).

**CLI install:**

```bash
mcpb install yahoo-fantasy-mcp-0.1.0.mcpb
```

### First-use authentication

Installing the bundle does not complete authentication by itself. The first time you invoke any tool (e.g. asking Claude to list your leagues), the server returns an error with a ready-to-run command:

```
Yahoo OAuth setup incomplete. Run this command in your terminal:

  YAHOO_CLIENT_ID=<your_key> YAHOO_CLIENT_SECRET=<your_secret> uv run --project '<bundle_install_dir>' yahoo-fantasy-mcp-auth
```

The exact command — with your credentials and install path already filled in — is included in the error. Copy it, paste it into a terminal, and follow the prompts:

1. A browser window opens to Yahoo's authorization page.
2. Approve access for your app.
3. Yahoo shows a short code — paste it back at the terminal prompt.
4. The token is saved to `~/.yahoo_fantasy_oauth2.json` and refreshes automatically from then on.

---

## Available Tools

| Tool | Description |
|---|---|
| `list_leagues` | List all your leagues for a given sport |
| `get_stat_categories` | Get scoring stat categories (and valid `sort_by` values) for a league |
| `get_roster` | Get your current roster; pass `sort_by` to include stats for comparison |
| `get_free_agents` | Get available free agents, optionally filtered by position and sorted by stat |
| `get_waiver_players` | Get players on the waiver wire, optionally filtered and sorted |

Supported sports: `nfl`, `nba`, `mlb`, `nhl`

## Typical Workflow

1. **Find your league** — call `list_leagues(sport)` to get your `league_id`
2. **Check scoring** — call `get_stat_categories(league_id)` to see what stats are tracked and get valid `sort_by` values
3. **See your roster with stats** — call `get_roster(league_id, sort_by="PTS")` to view your players with recent stats
4. **Find pickups** — call `get_free_agents` or `get_waiver_players` with the same `sort_by` to find available talent ranked by the same stat
5. **Compare and decide** — ask the assistant to recommend add/drop moves by comparing the `stats` dicts across roster, free agents, and waivers
