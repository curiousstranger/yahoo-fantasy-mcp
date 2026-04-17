"""Yahoo Fantasy API wrapper.

All functions accept an OAuth2 session and return plain dicts/lists.
No Yahoo library objects escape this module.
"""

from __future__ import annotations

import logging
from typing import Any

import yahoo_fantasy_api as yfa
from yahoo_oauth import OAuth2

logger = logging.getLogger(__name__)


def list_leagues(sc: OAuth2, sport: str) -> list[dict]:
    """List all leagues for the given sport in the current season.

    Args:
        sc: Authenticated OAuth2 session.
        sport: Sport code — nfl, nba, mlb, or nhl.

    Returns:
        List of dicts with keys: league_id, name, num_teams, scoring_type, season.

    """
    game = yfa.Game(sc, sport)
    league_ids = game.league_ids()

    result = []
    for league_id in league_ids:
        try:
            league = game.to_league(league_id)
            settings = league.settings()
            result.append(
                {
                    "league_id": league_id,
                    "name": settings.get("name", ""),
                    "num_teams": settings.get("num_teams", 0),
                    "scoring_type": settings.get("scoring_type", ""),
                    "season": settings.get("season", ""),
                }
            )
        except Exception as exc:
            logger.warning("Failed to load league %s: %s", league_id, exc)
            result.append(
                {
                    "league_id": league_id,
                    "name": "",
                    "num_teams": 0,
                    "scoring_type": "",
                    "season": "",
                }
            )
    return result


def get_stat_categories(sc: OAuth2, league_id: str) -> list[dict]:
    """Return the scoring stat categories for a league.

    Args:
        sc: Authenticated OAuth2 session.
        league_id: League ID string (e.g. "nfl.l.123456").

    Returns:
        List of dicts with keys: display_name, position_type.
        display_name values are valid sort_by values for get_free_agents / get_waiver_players.

    """
    sport = league_id.split(".")[0]
    game = yfa.Game(sc, sport)
    league = game.to_league(league_id)
    return league.stat_categories()


def get_roster(
    sc: OAuth2,
    league_id: str,
    sort_by: str | None = None,
    stat_type: str = "lastmonth",
) -> list[dict]:
    """Get the current user's roster for a league.

    Args:
        sc: Authenticated OAuth2 session.
        league_id: League ID string (e.g. "nfl.l.123456").
        sort_by: Stat name to include per player (e.g. "PTS", "HR"). Use
            get_stat_categories to see valid values. When set, each player
            includes a 'stats' sub-dict for comparison with free agents / waivers.
        stat_type: Time range for stats when sort_by is set. One of:
            'lastmonth' (default), 'lastweek', 'season', 'average_season'.

    Returns:
        List of player dicts with keys: player_id, player_key, name, eligible_positions,
        selected_position, status. When sort_by is set, also includes a 'stats' dict.

    """
    sport = league_id.split(".")[0]
    game = yfa.Game(sc, sport)
    league = game.to_league(league_id)
    team = league.to_team(league.team_key())
    roster = team.roster()

    result = []
    for player in roster:
        player_id = player.get("player_id", "")
        result.append(
            {
                "player_id": player_id,
                "player_key": f"{sport}.p.{player_id}" if player_id else "",
                "name": player.get("name", ""),
                "eligible_positions": player.get("eligible_positions", []),
                "selected_position": player.get("selected_position", ""),
                "status": player.get("status", ""),
            }
        )

    if sort_by:
        player_ids = [p["player_id"] for p in result if p["player_id"]]
        stats_by_id = {}
        if player_ids:
            stats_list = league.player_stats(player_ids, stat_type)
            for s in stats_list:
                stats_by_id[s.get("player_id")] = s
        for p in result:
            s = stats_by_id.get(p["player_id"], {})
            p["stats"] = {
                k: v
                for k, v in s.items()
                if k not in ("player_id", "name", "position_type")
            }

    return result


def get_free_agents(
    sc: OAuth2,
    league_id: str,
    position: str | None = None,
    count: int = 25,
    sort_by: str | None = None,
    stat_type: str = "lastmonth",
) -> list[dict]:
    """Get free agent players available to add.

    NFL positions: QB, WR, RB, TE, K, DEF
    NBA positions: PG, SG, SF, PF, C, G, F, UTIL
    MLB positions: C, 1B, 2B, 3B, SS, OF, SP, RP, P
    NHL positions: C, LW, RW, D, G

    Args:
        sc: Authenticated OAuth2 session.
        league_id: League ID string (e.g. "nfl.l.123456").
        position: Filter by position code. None returns all positions.
        count: Maximum number of players to return (default 25).
        sort_by: Stat name to sort by (e.g. "PTS", "REB", "HR"). Use
            get_stat_categories to see valid values. Defaults to percent_owned.
        stat_type: Time range for stats when sort_by is set. One of:
            'lastmonth' (default), 'lastweek', 'season', 'average_season'.

    Returns:
        List of player dicts sorted by sort_by (or percent_owned) descending.
        Keys: player_id, player_key, name, eligible_positions, percent_owned, status.
        When sort_by is set, each dict also includes a 'stats' sub-dict.

    """
    sport = league_id.split(".")[0]
    game = yfa.Game(sc, sport)
    league = game.to_league(league_id)
    players = league.free_agents(position or "")
    return _format_players(players, sport, count, league, sort_by, stat_type)


def get_waiver_players(
    sc: OAuth2,
    league_id: str,
    position: str | None = None,
    count: int = 25,
    sort_by: str | None = None,
    stat_type: str = "lastmonth",
) -> list[dict]:
    """Get players on the waiver wire.

    NFL positions: QB, WR, RB, TE, K, DEF
    NBA positions: PG, SG, SF, PF, C, G, F, UTIL
    MLB positions: C, 1B, 2B, 3B, SS, OF, SP, RP, P
    NHL positions: C, LW, RW, D, G

    Args:
        sc: Authenticated OAuth2 session.
        league_id: League ID string (e.g. "nfl.l.123456").
        position: Filter by position code. None returns all positions.
        count: Maximum number of players to return (default 25).
        sort_by: Stat name to sort by (e.g. "PTS", "REB", "HR"). Use
            get_stat_categories to see valid values. Defaults to percent_owned.
        stat_type: Time range for stats when sort_by is set. One of:
            'lastmonth' (default), 'lastweek', 'season', 'average_season'.

    Returns:
        List of player dicts sorted by sort_by (or percent_owned) descending.
        Keys: player_id, player_key, name, eligible_positions, percent_owned, status.
        When sort_by is set, each dict also includes a 'stats' sub-dict.

    """
    sport = league_id.split(".")[0]
    game = yfa.Game(sc, sport)
    league = game.to_league(league_id)
    players = league.waivers()
    return _format_players(players, sport, count, league, sort_by, stat_type)


def _format_players(
    players: list,
    sport: str,
    count: int,
    league: Any,  # noqa: ANN401 — yfa has no public League type
    sort_by: str | None,
    stat_type: str,
) -> list[dict]:
    """Normalize players, optionally enrich with stats, sort, and slice."""
    result = []
    for player in players:
        if not isinstance(player, dict):
            continue
        player_id = player.get("player_id", "")
        pct = player.get("percent_owned", 0)
        result.append(
            {
                "player_id": player_id,
                "player_key": f"{sport}.p.{player_id}" if player_id else "",
                "name": player.get("name", ""),
                "eligible_positions": player.get("eligible_positions", []),
                "percent_owned": float(pct or 0),
                "status": player.get("status", ""),
            }
        )

    if sort_by:
        player_ids = [p["player_id"] for p in result if p["player_id"]]
        stats_by_id = {}
        if player_ids:
            stats_list = league.player_stats(player_ids, stat_type)
            for s in stats_list:
                stats_by_id[s.get("player_id")] = s

        for p in result:
            s = stats_by_id.get(p["player_id"], {})
            p["stats"] = {
                k: v
                for k, v in s.items()
                if k not in ("player_id", "name", "position_type")
            }
            try:
                p["_sort_val"] = float(s.get(sort_by) or 0)
            except (ValueError, TypeError):
                p["_sort_val"] = 0.0

        result.sort(key=lambda p: p["_sort_val"], reverse=True)
        for p in result:
            del p["_sort_val"]
    else:
        result.sort(key=lambda p: p["percent_owned"], reverse=True)

    return result[:count]
