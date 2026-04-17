"""OAuth2 setup for Yahoo Fantasy API.

Run `yahoo-fantasy-mcp-auth` once in your terminal to complete the OAuth flow.
Afterwards, the token is saved and refreshed automatically.
"""

import json
import os
from pathlib import Path

from yahoo_oauth import OAuth2


def _token_path() -> str:
    default = Path.home() / ".yahoo_fantasy_oauth2.json"
    return os.environ.get("YAHOO_OAUTH_TOKEN_FILE", str(default))


def get_oauth() -> OAuth2:
    """Return an authenticated OAuth2 session.

    Reads YAHOO_CLIENT_ID and YAHOO_CLIENT_SECRET from environment.
    Token is stored at YAHOO_OAUTH_TOKEN_FILE (default: ~/.yahoo_fantasy_oauth2.json).

    Raises EnvironmentError if credentials are missing.
    """
    client_id = os.environ.get("YAHOO_CLIENT_ID")
    client_secret = os.environ.get("YAHOO_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise OSError(
            "Missing Yahoo OAuth credentials. Set YAHOO_CLIENT_ID and "
            "YAHOO_CLIENT_SECRET environment variables.\n"
            "Get credentials at: https://developer.yahoo.com/apps/"
        )

    token_file = _token_path()

    # yahoo_oauth reads credentials from the file; seed it on first run
    token_path = Path(token_file)
    if not token_path.exists():
        token_path.write_text(
            json.dumps(
                {
                    "consumer_key": client_id,
                    "consumer_secret": client_secret,
                }
            )
        )

    return OAuth2(client_id, client_secret, from_file=token_file)


def run_initial_auth() -> None:
    """One-time interactive OAuth setup. Run this in a real terminal.

    Opens your browser to authorize the Yahoo app, then prompts you to
    paste the verifier code. Saves the token to the configured token file.
    """
    token_file = _token_path()
    print(f"Starting Yahoo OAuth flow. Token will be saved to: {token_file}")
    print("A browser window will open. Log in and authorize the app.")
    print("Paste the verifier code when prompted.\n")

    sc = get_oauth()

    if sc.token_is_valid():
        print(f"\nSuccess! Token saved to {token_file}")
        print("You can now run the MCP server: yahoo-fantasy-mcp")
    else:
        print("\nWarning: token may not be valid. Try running again.")
