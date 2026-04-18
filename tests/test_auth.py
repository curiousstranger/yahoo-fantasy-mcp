"""Tests for yahoo_fantasy_mcp.auth"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# _token_path
# ---------------------------------------------------------------------------


def test_token_path_returns_default_in_home():
    from yahoo_fantasy_mcp.auth import _token_path

    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("YAHOO_OAUTH_TOKEN_FILE", None)
        path = _token_path()

    assert path == str(Path.home() / ".yahoo_fantasy_oauth2.json")


def test_token_path_uses_env_var_when_set():
    from yahoo_fantasy_mcp.auth import _token_path

    with patch.dict(os.environ, {"YAHOO_OAUTH_TOKEN_FILE": "/tmp/my_token.json"}):
        path = _token_path()

    assert path == "/tmp/my_token.json"


# ---------------------------------------------------------------------------
# get_oauth — credential validation
# ---------------------------------------------------------------------------


def test_get_oauth_raises_when_client_id_missing(tmp_path):
    from yahoo_fantasy_mcp.auth import get_oauth

    with (
        patch.dict(os.environ, {"YAHOO_CLIENT_SECRET": "secret"}, clear=True),
        patch(
            "yahoo_fantasy_mcp.auth._token_path",
            return_value=str(tmp_path / "token.json"),
        ),
    ):
        try:
            get_oauth()
            raise AssertionError("Expected OSError")
        except OSError as e:
            assert "YAHOO_CLIENT_ID" in str(e)


def test_get_oauth_raises_when_client_secret_missing(tmp_path):
    from yahoo_fantasy_mcp.auth import get_oauth

    with (
        patch.dict(os.environ, {"YAHOO_CLIENT_ID": "key"}, clear=True),
        patch(
            "yahoo_fantasy_mcp.auth._token_path",
            return_value=str(tmp_path / "token.json"),
        ),
    ):
        try:
            get_oauth()
            raise AssertionError("Expected OSError")
        except OSError as e:
            assert "YAHOO_CLIENT_SECRET" in str(e)


# ---------------------------------------------------------------------------
# get_oauth — token file seeding
# ---------------------------------------------------------------------------


def test_get_oauth_creates_token_file_when_missing(tmp_path):
    from yahoo_fantasy_mcp.auth import get_oauth

    token_file = tmp_path / "token.json"
    env = {"YAHOO_CLIENT_ID": "my_key", "YAHOO_CLIENT_SECRET": "my_secret"}

    with (
        patch.dict(os.environ, env, clear=True),
        patch("yahoo_fantasy_mcp.auth._token_path", return_value=str(token_file)),
        patch("yahoo_fantasy_mcp.auth.OAuth2", side_effect=Exception("not authed")),
        pytest.raises(RuntimeError),
    ):
        get_oauth()

    assert token_file.exists()
    data = json.loads(token_file.read_text())
    assert data["consumer_key"] == "my_key"
    assert data["consumer_secret"] == "my_secret"


def test_get_oauth_does_not_overwrite_existing_token_file(tmp_path):
    from yahoo_fantasy_mcp.auth import get_oauth

    token_file = tmp_path / "token.json"
    original = {
        "consumer_key": "old_key",
        "consumer_secret": "old_secret",
        "access_token": "existing_token",
    }
    token_file.write_text(json.dumps(original))

    env = {"YAHOO_CLIENT_ID": "new_key", "YAHOO_CLIENT_SECRET": "new_secret"}

    with (
        patch.dict(os.environ, env),
        patch("yahoo_fantasy_mcp.auth._token_path", return_value=str(token_file)),
        patch("yahoo_fantasy_mcp.auth.OAuth2") as mock_oauth,
    ):
        mock_oauth.return_value = MagicMock()
        get_oauth()

    data = json.loads(token_file.read_text())
    assert data["access_token"] == "existing_token"
    assert data["consumer_key"] == "old_key"


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
        patch("yahoo_fantasy_mcp.auth.OAuth2", side_effect=Exception("not authed")),
        pytest.raises(RuntimeError) as exc_info,
    ):
        get_oauth()

    msg = str(exc_info.value)
    assert "yahoo-fantasy-mcp-auth" in msg
    assert "YAHOO_CLIENT_ID=my_key" in msg
    assert "YAHOO_CLIENT_SECRET=my_secret" in msg
    assert "uv run --project" not in msg


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
        patch("yahoo_fantasy_mcp.auth.OAuth2", side_effect=Exception("not authed")),
        pytest.raises(RuntimeError) as exc_info,
    ):
        get_oauth()

    msg = str(exc_info.value)
    assert "uv run --project '/bundle/install/dir' yahoo-fantasy-mcp-auth" in msg
    assert "YAHOO_CLIENT_ID=my_key" in msg
    assert "YAHOO_CLIENT_SECRET=my_secret" in msg


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
    assert "YAHOO_CLIENT_ID=my_key" in str(exc_info.value)
    assert "YAHOO_CLIENT_SECRET=my_secret" in str(exc_info.value)


# ---------------------------------------------------------------------------
# run_initial_auth
# ---------------------------------------------------------------------------


def test_run_initial_auth_prints_success_when_token_valid(capsys):
    from yahoo_fantasy_mcp.auth import run_initial_auth

    sc = MagicMock()
    sc.token_is_valid.return_value = True

    with patch("yahoo_fantasy_mcp.auth.get_oauth", return_value=sc):
        run_initial_auth()

    out = capsys.readouterr().out
    assert "Success" in out


def test_run_initial_auth_prints_warning_when_token_invalid(capsys):
    from yahoo_fantasy_mcp.auth import run_initial_auth

    sc = MagicMock()
    sc.token_is_valid.return_value = False

    with patch("yahoo_fantasy_mcp.auth.get_oauth", return_value=sc):
        run_initial_auth()

    out = capsys.readouterr().out
    assert "Warning" in out
