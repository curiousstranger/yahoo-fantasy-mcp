"""Tests for yahoo_fantasy_mcp.server — verifies tools delegate to api correctly."""

from unittest.mock import MagicMock, patch


def _mock_sc():
    return MagicMock()


# ---------------------------------------------------------------------------
# list_leagues
# ---------------------------------------------------------------------------


def test_list_leagues_delegates_to_api():
    import yahoo_fantasy_mcp.server as server

    expected = [{"league_id": "nfl.l.1"}]
    sc = _mock_sc()

    with patch.object(server, "_get_sc", return_value=sc), patch.object(
        server.api, "list_leagues", return_value=expected
    ) as mock_api:
        result = server.list_leagues("nfl")

    mock_api.assert_called_once_with(sc, "nfl")
    assert result == expected


# ---------------------------------------------------------------------------
# get_stat_categories
# ---------------------------------------------------------------------------


def test_get_stat_categories_delegates_to_api():
    import yahoo_fantasy_mcp.server as server

    expected = [{"display_name": "PTS", "position_type": "O"}]
    sc = _mock_sc()

    with patch.object(server, "_get_sc", return_value=sc), patch.object(
        server.api, "get_stat_categories", return_value=expected
    ) as mock_api:
        result = server.get_stat_categories("nba.l.99999")

    mock_api.assert_called_once_with(sc, "nba.l.99999")
    assert result == expected


# ---------------------------------------------------------------------------
# get_roster
# ---------------------------------------------------------------------------


def test_get_roster_delegates_to_api_no_stats():
    import yahoo_fantasy_mcp.server as server

    sc = _mock_sc()
    with patch.object(server, "_get_sc", return_value=sc), patch.object(
        server.api, "get_roster", return_value=[]
    ) as mock_api:
        server.get_roster("nba.l.99999")

    mock_api.assert_called_once_with(
        sc, "nba.l.99999", sort_by=None, stat_type="lastmonth"
    )


def test_get_roster_passes_sort_by_and_stat_type():
    import yahoo_fantasy_mcp.server as server

    sc = _mock_sc()
    with patch.object(server, "_get_sc", return_value=sc), patch.object(
        server.api, "get_roster", return_value=[]
    ) as mock_api:
        server.get_roster("nba.l.99999", sort_by="PTS", stat_type="lastweek")

    mock_api.assert_called_once_with(
        sc, "nba.l.99999", sort_by="PTS", stat_type="lastweek"
    )


# ---------------------------------------------------------------------------
# get_free_agents
# ---------------------------------------------------------------------------


def test_get_free_agents_delegates_to_api():
    import yahoo_fantasy_mcp.server as server

    sc = _mock_sc()
    with patch.object(server, "_get_sc", return_value=sc), patch.object(
        server.api, "get_free_agents", return_value=[]
    ) as mock_api:
        server.get_free_agents(
            "nba.l.99999",
            position="PG",
            count=10,
            sort_by="PTS",
            stat_type="lastweek",
        )

    mock_api.assert_called_once_with(sc, "nba.l.99999", "PG", 10, "PTS", "lastweek")


def test_get_free_agents_passes_defaults():
    import yahoo_fantasy_mcp.server as server

    sc = _mock_sc()
    with patch.object(server, "_get_sc", return_value=sc), patch.object(
        server.api, "get_free_agents", return_value=[]
    ) as mock_api:
        server.get_free_agents("nba.l.99999")

    mock_api.assert_called_once_with(sc, "nba.l.99999", None, 25, None, "lastmonth")


# ---------------------------------------------------------------------------
# get_waiver_players
# ---------------------------------------------------------------------------


def test_get_waiver_players_delegates_to_api():
    import yahoo_fantasy_mcp.server as server

    sc = _mock_sc()
    with patch.object(server, "_get_sc", return_value=sc), patch.object(
        server.api, "get_waiver_players", return_value=[]
    ) as mock_api:
        server.get_waiver_players(
            "nba.l.99999", position="C", count=5, sort_by="REB", stat_type="season"
        )

    mock_api.assert_called_once_with(sc, "nba.l.99999", "C", 5, "REB", "season")


def test_get_waiver_players_passes_defaults():
    import yahoo_fantasy_mcp.server as server

    sc = _mock_sc()
    with patch.object(server, "_get_sc", return_value=sc), patch.object(
        server.api, "get_waiver_players", return_value=[]
    ) as mock_api:
        server.get_waiver_players("nba.l.99999")

    mock_api.assert_called_once_with(sc, "nba.l.99999", None, 25, None, "lastmonth")
