# Design: Improved Auth Error Message for .mcpb Install

Date: 2026-04-17

## Problem

When a user installs yahoo-fantasy-mcp via the `.mcpb` bundle, they must complete a one-time OAuth flow before the server can make API calls. The bundle prompts for `YAHOO_CLIENT_ID` and `YAHOO_CLIENT_SECRET` at install time, but there is no mechanism in the `.mcpb` standard to display a post-install message. When the user invokes any tool without having run the auth flow, `yahoo_oauth` attempts an interactive terminal session that hangs or fails silently in the MCP context.

The current error message is generic and does not provide a copy/pastable command the user can run.

## Goals

- Surface a clear, actionable error when OAuth setup is incomplete
- Provide a fully copy/pastable terminal command — no user lookup of credentials or paths required
- Work for both `.mcpb` installs (via Claude Desktop) and manual installs (via `uv tool install`)

## Non-Goals

- Changes to `server.py`, `api.py`, or tests
- README updates
- Any post-install hook or `.mcpb` manifest extension

## Design

### 1. `manifest.json` — add `YAHOO_PROJECT_DIR`

Add one env entry to `mcp_config.env`:

```json
"YAHOO_PROJECT_DIR": "${__dirname}"
```

The `.mcpb` host (Claude Desktop) substitutes `${__dirname}` with the absolute path to the bundle's install directory when starting the server process. This makes the install path available to the running server without any path arithmetic.

For non-`.mcpb` users (manual `claude_desktop_config.json` setup), `YAHOO_PROJECT_DIR` is not set — this is the signal to use a simpler command.

### 2. `auth.py` — `_auth_setup_error()` helper

A private helper that builds the `RuntimeError` with the appropriate copy/pastable command:

```python
def _auth_setup_error(client_id: str, client_secret: str) -> RuntimeError:
    project_dir = os.environ.get("YAHOO_PROJECT_DIR")
    if project_dir:
        cmd = (
            f"YAHOO_CLIENT_ID={client_id} "
            f"YAHOO_CLIENT_SECRET={client_secret} "
            f"uv run --project {project_dir} yahoo-fantasy-mcp-auth"
        )
    else:
        cmd = (
            f"YAHOO_CLIENT_ID={client_id} "
            f"YAHOO_CLIENT_SECRET={client_secret} "
            f"yahoo-fantasy-mcp-auth"
        )
    return RuntimeError(
        "Yahoo OAuth setup incomplete. Run this command in your terminal:\n\n"
        f"  {cmd}"
    )
```

### 3. `auth.py` — `get_oauth()` changes

Two additions inside `get_oauth()`, after the token file is seeded:

**Proactive check** (primary path — handles 99% of cases):
```python
token_data = json.loads(token_path.read_text())
if "access_token" not in token_data:
    raise _auth_setup_error(client_id, client_secret)
```

**Catch-as-fallback** (safety net — wraps the `OAuth2()` call):
```python
try:
    return OAuth2(client_id, client_secret, from_file=token_file)
except Exception as exc:
    raise _auth_setup_error(client_id, client_secret) from exc
```

### Error surfacing

FastMCP automatically converts unhandled exceptions from tool functions into MCP tool error responses (`isError=True`). The exception message is what the LLM and user see. No additional wiring in `server.py` is needed.

## Why `Path(__file__)` was rejected

An earlier approach derived the project root via `Path(__file__).parents[2]`. This fails because `uv run --project <dir>` performs a regular (non-editable) install, so `__file__` points to the site-packages copy inside `.venv/lib/python3.x/site-packages/yahoo_fantasy_mcp/auth.py` — not the source tree. `parents[2]` gives `.venv/lib/python3.x/`, not the project root.

The `YAHOO_PROJECT_DIR` env var set from `${__dirname}` in `manifest.json` is the authoritative source of the bundle path.

## Files Changed

| File | Change |
|---|---|
| `manifest.json` | Add `"YAHOO_PROJECT_DIR": "${__dirname}"` to `mcp_config.env` |
| `src/yahoo_fantasy_mcp/auth.py` | Add `_auth_setup_error()`, proactive token check, catch-as-fallback around `OAuth2()` |
