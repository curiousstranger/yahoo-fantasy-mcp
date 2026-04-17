"""Tests for yahoo_fantasy_mcp.api"""

from unittest.mock import MagicMock, patch


def _make_league(
    roster_players=None,
    stats=None,
    free_agents=None,
    waivers=None,
    stat_categories=None,
    settings=None,
):
    league = MagicMock()
    league.team_key.return_value = "nba.l.99999.t.1"

    team = MagicMock()
    team.roster.return_value = roster_players or []
    league.to_team.return_value = team

    league.player_stats.return_value = stats or []
    league.free_agents.return_value = free_agents or []
    league.waivers.return_value = waivers or []
    league.stat_categories.return_value = stat_categories or []
    league.settings.return_value = settings or {}
    return league


def _make_game(league):
    game = MagicMock()
    game.to_league.return_value = league
    return game


# ---------------------------------------------------------------------------
# list_leagues
# ---------------------------------------------------------------------------


def test_list_leagues_returns_fields_from_settings():
    from yahoo_fantasy_mcp import api

    league = _make_league(
        settings={
            "name": "Monday Night Mayhem",
            "num_teams": 12,
            "scoring_type": "head",
            "season": "2024",
        }
    )
    game = _make_game(league)
    game.league_ids.return_value = ["nfl.l.123456"]

    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=game):
        result = api.list_leagues(MagicMock(), "nfl")

    assert len(result) == 1
    assert result[0] == {
        "league_id": "nfl.l.123456",
        "name": "Monday Night Mayhem",
        "num_teams": 12,
        "scoring_type": "head",
        "season": "2024",
    }


def test_list_leagues_returns_empty_for_failed_league():
    from yahoo_fantasy_mcp import api

    game = MagicMock()
    game.league_ids.return_value = ["nfl.l.bad"]
    game.to_league.side_effect = Exception("API error")

    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=game):
        result = api.list_leagues(MagicMock(), "nfl")

    assert len(result) == 1
    assert result[0]["league_id"] == "nfl.l.bad"
    assert result[0]["name"] == ""
    assert result[0]["num_teams"] == 0


def test_list_leagues_returns_multiple():
    from yahoo_fantasy_mcp import api

    league_a = _make_league(
        settings={
            "name": "League A",
            "num_teams": 10,
            "scoring_type": "head",
            "season": "2024",
        }
    )
    league_b = _make_league(
        settings={
            "name": "League B",
            "num_teams": 12,
            "scoring_type": "roto",
            "season": "2024",
        }
    )
    game = MagicMock()
    game.league_ids.return_value = ["nfl.l.111", "nfl.l.222"]
    game.to_league.side_effect = [league_a, league_b]

    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=game):
        result = api.list_leagues(MagicMock(), "nfl")

    assert len(result) == 2
    assert result[0]["name"] == "League A"
    assert result[1]["name"] == "League B"


# ---------------------------------------------------------------------------
# get_stat_categories
# ---------------------------------------------------------------------------


def test_get_stat_categories_delegates_to_league():
    from yahoo_fantasy_mcp import api

    cats = [
        {"display_name": "PTS", "position_type": "O"},
        {"display_name": "REB", "position_type": "O"},
    ]
    league = _make_league(stat_categories=cats)

    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=_make_game(league)):
        result = api.get_stat_categories(MagicMock(), "nba.l.99999")

    assert result == cats


def test_get_stat_categories_extracts_sport_from_league_id():
    from yahoo_fantasy_mcp import api

    league = _make_league(stat_categories=[])
    game = _make_game(league)

    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=game) as mock_game_cls:
        api.get_stat_categories(MagicMock(), "mlb.l.55555")

    mock_game_cls.assert_called_once()
    assert mock_game_cls.call_args[0][1] == "mlb"


# ---------------------------------------------------------------------------
# get_roster — no stats
# ---------------------------------------------------------------------------


def test_get_roster_returns_basic_fields():
    from yahoo_fantasy_mcp import api

    roster_players = [
        {
            "player_id": "5185",
            "name": "Nikola Jokic",
            "eligible_positions": ["C", "UTIL"],
            "selected_position": "C",
            "status": "",
        },
    ]
    league = _make_league(roster_players=roster_players)

    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=_make_game(league)):
        result = api.get_roster(MagicMock(), "nba.l.99999")

    assert len(result) == 1
    p = result[0]
    assert p["player_id"] == "5185"
    assert p["player_key"] == "nba.p.5185"
    assert p["name"] == "Nikola Jokic"
    assert p["eligible_positions"] == ["C", "UTIL"]
    assert p["selected_position"] == "C"
    assert p["status"] == ""
    assert "stats" not in p


def test_get_roster_status_mapped_from_status():
    from yahoo_fantasy_mcp import api

    roster_players = [
        {
            "player_id": "1",
            "name": "Player X",
            "eligible_positions": [],
            "selected_position": "BN",
            "status": "Q",
        },
    ]
    league = _make_league(roster_players=roster_players)

    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=_make_game(league)):
        result = api.get_roster(MagicMock(), "nba.l.99999")

    assert result[0]["status"] == "Q"


# ---------------------------------------------------------------------------
# get_roster — with stats
# ---------------------------------------------------------------------------


def test_get_roster_includes_stats_when_sort_by_given():
    from yahoo_fantasy_mcp import api

    roster_players = [
        {
            "player_id": "5185",
            "name": "Nikola Jokic",
            "eligible_positions": ["C"],
            "selected_position": "C",
            "status": "",
        },
    ]
    player_stats = [
        {
            "player_id": "5185",
            "name": "Nikola Jokic",
            "position_type": "C",
            "PTS": 26.4,
            "REB": 12.1,
            "AST": 9.0,
        },
    ]
    league = _make_league(roster_players=roster_players, stats=player_stats)

    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=_make_game(league)):
        result = api.get_roster(MagicMock(), "nba.l.99999", sort_by="PTS")

    p = result[0]
    assert "stats" in p
    assert p["stats"]["PTS"] == 26.4
    assert "name" not in p["stats"]
    assert "player_id" not in p["stats"]
    assert "position_type" not in p["stats"]


def test_get_roster_stat_type_passed_to_api():
    from yahoo_fantasy_mcp import api

    roster_players = [
        {
            "player_id": "5185",
            "name": "Nikola Jokic",
            "eligible_positions": ["C"],
            "selected_position": "C",
            "status": "",
        },
    ]
    league = _make_league(
        roster_players=roster_players, stats=[{"player_id": "5185", "PTS": 30.0}]
    )

    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=_make_game(league)):
        api.get_roster(MagicMock(), "nba.l.99999", sort_by="PTS", stat_type="lastweek")

    league.player_stats.assert_called_once_with(["5185"], "lastweek")


def test_get_roster_no_stats_call_when_sort_by_omitted():
    from yahoo_fantasy_mcp import api

    roster_players = [
        {
            "player_id": "5185",
            "name": "Nikola Jokic",
            "eligible_positions": ["C"],
            "selected_position": "C",
            "status": "",
        },
    ]
    league = _make_league(roster_players=roster_players)

    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=_make_game(league)):
        api.get_roster(MagicMock(), "nba.l.99999")

    league.player_stats.assert_not_called()


# ---------------------------------------------------------------------------
# get_free_agents
# ---------------------------------------------------------------------------


def test_get_free_agents_passes_empty_string_when_no_position():
    from yahoo_fantasy_mcp import api

    league = _make_league()
    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=_make_game(league)):
        api.get_free_agents(MagicMock(), "nba.l.99999")

    league.free_agents.assert_called_once_with("")


def test_get_free_agents_passes_position_when_given():
    from yahoo_fantasy_mcp import api

    league = _make_league()
    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=_make_game(league)):
        api.get_free_agents(MagicMock(), "nba.l.99999", position="PG")

    league.free_agents.assert_called_once_with("PG")


def test_get_free_agents_returns_sorted_by_percent_owned():
    from yahoo_fantasy_mcp import api

    players = [
        {
            "player_id": "1",
            "name": "A",
            "eligible_positions": [],
            "percent_owned": 30.0,
            "status": "",
        },
        {
            "player_id": "2",
            "name": "B",
            "eligible_positions": [],
            "percent_owned": 80.0,
            "status": "",
        },
    ]
    league = _make_league(free_agents=players)

    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=_make_game(league)):
        result = api.get_free_agents(MagicMock(), "nba.l.99999")

    assert result[0]["name"] == "B"
    assert result[1]["name"] == "A"


def test_get_free_agents_respects_count():
    from yahoo_fantasy_mcp import api

    players = [
        {
            "player_id": str(i),
            "name": f"P{i}",
            "eligible_positions": [],
            "percent_owned": float(i),
            "status": "",
        }
        for i in range(10)
    ]
    league = _make_league(free_agents=players)

    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=_make_game(league)):
        result = api.get_free_agents(MagicMock(), "nba.l.99999", count=3)

    assert len(result) == 3


# ---------------------------------------------------------------------------
# get_waiver_players
# ---------------------------------------------------------------------------


def test_get_waiver_players_calls_waivers():
    from yahoo_fantasy_mcp import api

    league = _make_league()
    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=_make_game(league)):
        api.get_waiver_players(MagicMock(), "nba.l.99999")

    league.waivers.assert_called_once()


def test_get_waiver_players_returns_sorted_by_percent_owned():
    from yahoo_fantasy_mcp import api

    players = [
        {
            "player_id": "1",
            "name": "A",
            "eligible_positions": [],
            "percent_owned": 10.0,
            "status": "",
        },
        {
            "player_id": "2",
            "name": "B",
            "eligible_positions": [],
            "percent_owned": 55.0,
            "status": "",
        },
    ]
    league = _make_league(waivers=players)

    with patch("yahoo_fantasy_mcp.api.yfa.Game", return_value=_make_game(league)):
        result = api.get_waiver_players(MagicMock(), "nba.l.99999")

    assert result[0]["name"] == "B"


# ---------------------------------------------------------------------------
# _format_players
# ---------------------------------------------------------------------------


def test_format_players_skips_non_dict_entries():
    from yahoo_fantasy_mcp.api import _format_players

    players = [
        "not a dict",
        {
            "player_id": "1",
            "name": "Good",
            "eligible_positions": [],
            "percent_owned": 50.0,
            "status": "",
        },
    ]
    result = _format_players(players, "nba", 25, MagicMock(), None, "lastmonth")
    assert len(result) == 1
    assert result[0]["name"] == "Good"


def test_format_players_builds_player_key():
    from yahoo_fantasy_mcp.api import _format_players

    players = [
        {
            "player_id": "42",
            "name": "X",
            "eligible_positions": [],
            "percent_owned": 0,
            "status": "",
        }
    ]
    result = _format_players(players, "nfl", 25, MagicMock(), None, "lastmonth")
    assert result[0]["player_key"] == "nfl.p.42"


def test_format_players_empty_player_key_when_no_id():
    from yahoo_fantasy_mcp.api import _format_players

    players = [
        {
            "player_id": "",
            "name": "X",
            "eligible_positions": [],
            "percent_owned": 0,
            "status": "",
        }
    ]
    result = _format_players(players, "nfl", 25, MagicMock(), None, "lastmonth")
    assert result[0]["player_key"] == ""


def test_format_players_sorts_by_stat_descending():
    from yahoo_fantasy_mcp.api import _format_players

    players = [
        {
            "player_id": "1",
            "name": "Low",
            "eligible_positions": [],
            "percent_owned": 90.0,
            "status": "",
        },
        {
            "player_id": "2",
            "name": "High",
            "eligible_positions": [],
            "percent_owned": 10.0,
            "status": "",
        },
    ]
    league = MagicMock()
    league.player_stats.return_value = [
        {"player_id": "1", "PTS": 5.0},
        {"player_id": "2", "PTS": 30.0},
    ]

    result = _format_players(players, "nba", 25, league, "PTS", "lastmonth")
    assert result[0]["name"] == "High"
    assert result[1]["name"] == "Low"


def test_format_players_no_sort_val_in_output():
    from yahoo_fantasy_mcp.api import _format_players

    players = [
        {
            "player_id": "1",
            "name": "X",
            "eligible_positions": [],
            "percent_owned": 50.0,
            "status": "",
        }
    ]
    league = MagicMock()
    league.player_stats.return_value = [{"player_id": "1", "PTS": 20.0}]

    result = _format_players(players, "nba", 25, league, "PTS", "lastmonth")
    assert "_sort_val" not in result[0]


def test_format_players_missing_stat_defaults_to_zero_for_sort():
    from yahoo_fantasy_mcp.api import _format_players

    players = [
        {
            "player_id": "1",
            "name": "Has stat",
            "eligible_positions": [],
            "percent_owned": 10.0,
            "status": "",
        },
        {
            "player_id": "2",
            "name": "No stat",
            "eligible_positions": [],
            "percent_owned": 90.0,
            "status": "",
        },
    ]
    league = MagicMock()
    league.player_stats.return_value = [
        {"player_id": "1", "PTS": 25.0},
        # player 2 has no PTS
    ]

    result = _format_players(players, "nba", 25, league, "PTS", "lastmonth")
    assert result[0]["name"] == "Has stat"


def test_format_players_non_numeric_stat_defaults_to_zero():
    from yahoo_fantasy_mcp.api import _format_players

    players = [
        {
            "player_id": "1",
            "name": "X",
            "eligible_positions": [],
            "percent_owned": 50.0,
            "status": "",
        }
    ]
    league = MagicMock()
    league.player_stats.return_value = [{"player_id": "1", "PTS": "N/A"}]

    result = _format_players(players, "nba", 25, league, "PTS", "lastmonth")
    assert result[0]["stats"]["PTS"] == "N/A"  # raw value preserved in stats
