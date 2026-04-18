# MCPB Auth Error Message Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When OAuth setup is incomplete, surface a clear RuntimeError containing a fully copy/pastable terminal command so the user can complete auth without any manual lookup.

**Architecture:** Two-pronged detection in `get_oauth()`: proactive check for missing `access_token` in the token file, plus catch-as-fallback around the `OAuth2()` call. A private `_auth_setup_error()` helper constructs the command using `YAHOO_PROJECT_DIR` (set via `manifest.json`) when available, falling back to the bare entry-point name.

**Tech Stack:** Python, FastMCP (exception → tool error conversion is automatic), `yahoo_oauth.OAuth2`, `manifest.json` `${__dirname}` variable substitution.

---

### Task 1: Update existing tests and add new failing tests

**Files:**
- Modify: `tests/test_auth.py`

Two existing tests will break with the new implementation because they call `get_oauth()` with no `access_token` in the token file and expect it to succeed. We update them and add new tests covering the new error paths — all before touching implementation.

- [ ] **Step 1: Update `test_get_oauth_creates_token_file_when_missing`**

The new `get_oauth()` raises `RuntimeError` after seeding a file with no `access_token`. The test should still verify the file was created, but now expects the error to be raised. Replace the existing test:

```python
def test_get_oauth_creates_token_file_when_missing(tmp_path):
    from yahoo_fantasy_mcp.auth import get_oauth

    token_file = tmp_path / "token.json"
    env = {"YAHOO_CLIENT_ID": "my_key", "YAHOO_CLIENT_SECRET": "my_secret"}

    with (
        patch.dict(os.environ, env, clear=True),
        patch("yahoo_fantasy_mcp.auth._token_path", return_value=str(token_file)),
        pytest.raises(RuntimeError),
    ):
        get_oauth()

    assert token_file.exists()
    data = json.loads(token_file.read_text())
    assert data["consumer_key"] == "my_key"
    assert data["consumer_secret"] == "my_secret"
```

Add `import pytest` at the top of the file.

- [ ] **Step 2: Update `test_get_oauth_passes_credentials_to_oauth2`**

Pre-write a token file that already has an `access_token` so the proactive check passes and `OAuth2()` gets called:

```python
def test_get_oauth_passes_credentials_to_oauth2(tmp_path):
    from yahoo_fantasy_mcp.auth import get_oauth

    token_file = tmp_path / "token.json"
    token_file.write_text(json.dumps({
        "consumer_key": "my_key",
        "consumer_secret": "my_secret",
        "access_token": "tok",
    }))
    env = {"YAHOO_CLIENT_ID": "my_key", "YAHOO_CLIENT_SECRET": "my_secret"}

    with (
        patch.dict(os.environ, env),
        patch("yahoo_fantasy_mcp.auth._token_path", return_value=str(token_file)),
        patch("yahoo_fantasy_mcp.auth.OAuth2") as mock_oauth,
    ):
        mock_oauth.return_value = MagicMock()
        get_oauth()

    mock_oauth.assert_called_once_with("my_key", "my_secret", from_file=str(token_file))
```

- [ ] **Step 3: Add new test — raises with simple command when `YAHOO_PROJECT_DIR` not set**

```python
def test_get_oauth_raises_with_simple_command_when_no_project_dir(tmp_path):
    from yahoo_fantasy_mcp.auth import get_oauth

    token_file = tmp_path / "token.json"
    env = {
        "YAHOO_CLIENT_ID": "my_key",
        "YAHOO_CLIENT_SECRET": "my_secret",
    }

    with (
        patch.dict(os.environ, env, clear=True),
        patch("yahoo_fantasy_mcp.auth._token_path", return_value=str(token_file)),
        pytest.raises(RuntimeError) as exc_info,
    ):
        get_oauth()

    msg = str(exc_info.value)
    assert "yahoo-fantasy-mcp-auth" in msg
    assert "YAHOO_CLIENT_ID=my_key" in msg
    assert "YAHOO_CLIENT_SECRET=my_secret" in msg
    assert "uv run --project" not in msg
```

- [ ] **Step 4: Add new test — raises with `uv run --project` command when `YAHOO_PROJECT_DIR` is set**

```python
def test_get_oauth_raises_with_uv_command_when_project_dir_set(tmp_path):
    from yahoo_fantasy_mcp.auth import get_oauth

    token_file = tmp_path / "token.json"
    env = {
        "YAHOO_CLIENT_ID": "my_key",
        "YAHOO_CLIENT_SECRET": "my_secret",
        "YAHOO_PROJECT_DIR": "/bundle/install/dir",
    }

    with (
        patch.dict(os.environ, env, clear=True),
        patch("yahoo_fantasy_mcp.auth._token_path", return_value=str(token_file)),
        pytest.raises(RuntimeError) as exc_info,
    ):
        get_oauth()

    msg = str(exc_info.value)
    assert "uv run --project /bundle/install/dir yahoo-fantasy-mcp-auth" in msg
    assert "YAHOO_CLIENT_ID=my_key" in msg
    assert "YAHOO_CLIENT_SECRET=my_secret" in msg
```

- [ ] **Step 5: Add new test — `OAuth2()` exception is caught and re-raised as `RuntimeError`**

```python
def test_get_oauth_raises_when_oauth2_throws(tmp_path):
    from yahoo_fantasy_mcp.auth import get_oauth

    token_file = tmp_path / "token.json"
    token_file.write_text(json.dumps({
        "consumer_key": "my_key",
        "consumer_secret": "my_secret",
        "access_token": "tok",
    }))
    env = {"YAHOO_CLIENT_ID": "my_key", "YAHOO_CLIENT_SECRET": "my_secret"}

    with (
        patch.dict(os.environ, env, clear=True),
        patch("yahoo_fantasy_mcp.auth._token_path", return_value=str(token_file)),
        patch("yahoo_fantasy_mcp.auth.OAuth2", side_effect=Exception("auth failed")),
        pytest.raises(RuntimeError) as exc_info,
    ):
        get_oauth()

    assert "yahoo-fantasy-mcp-auth" in str(exc_info.value)
```

- [ ] **Step 6: Run the tests and confirm they fail**

```bash
uv run pytest tests/test_auth.py -v
```

Expected: several failures. The two updated tests will fail (implementation not changed yet), and the three new tests will fail with `Failed: DID NOT RAISE` or `AssertionError`.

---

### Task 2: Implement `_auth_setup_error()` and update `get_oauth()`

**Files:**
- Modify: `src/yahoo_fantasy_mcp/auth.py`

- [ ] **Step 1: Add `_auth_setup_error()` helper**

Add this private function after the `_token_path()` function (after line 16):

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

- [ ] **Step 2: Add proactive check and catch-as-fallback in `get_oauth()`**

Replace the final line of `get_oauth()` (currently `return OAuth2(client_id, client_secret, from_file=token_file)`) with the proactive check and wrapped `OAuth2()` call. The full updated `get_oauth()` function body after the existing credential check should look like:

```python
    token_file = _token_path()

    token_path = Path(token_file)
    if not token_path.exists():
        old_umask = os.umask(0o077)
        try:
            token_path.write_text(
                json.dumps(
                    {
                        "consumer_key": client_id,
                        "consumer_secret": client_secret,
                    }
                )
            )
        finally:
            os.umask(old_umask)

    token_data = json.loads(token_path.read_text())
    if "access_token" not in token_data:
        raise _auth_setup_error(client_id, client_secret)

    try:
        return OAuth2(client_id, client_secret, from_file=token_file)
    except Exception as exc:
        raise _auth_setup_error(client_id, client_secret) from exc
```

- [ ] **Step 3: Run the tests and confirm they pass**

```bash
uv run pytest tests/test_auth.py -v
```

Expected: all tests pass.

- [ ] **Step 4: Run the full test suite**

```bash
uv run pytest -v
```

Expected: all tests pass with no regressions.

---

### Task 3: Update `manifest.json`

**Files:**
- Modify: `manifest.json`

- [ ] **Step 1: Add `YAHOO_PROJECT_DIR` to `mcp_config.env`**

Add one line to the `env` block in `manifest.json`. The full updated `env` object:

```json
"env": {
  "PYTHONUNBUFFERED": "1",
  "YAHOO_CLIENT_ID": "${user_config.yahoo_client_id}",
  "YAHOO_CLIENT_SECRET": "${user_config.yahoo_client_secret}",
  "YAHOO_OAUTH_TOKEN_FILE": "${HOME}/.yahoo_fantasy_oauth2.json",
  "YAHOO_PROJECT_DIR": "${__dirname}"
}
```

- [ ] **Step 2: Commit all changes**

```bash
git add tests/test_auth.py src/yahoo_fantasy_mcp/auth.py manifest.json
git commit -m "feat: surface copy/pastable auth command in OAuth setup error"
```
