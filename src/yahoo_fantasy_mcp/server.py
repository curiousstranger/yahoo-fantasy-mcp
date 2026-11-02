"""Yahoo Fantasy Sports MCP server.

Provides read-only tools for roster management. Typical agent workflow:
  1. Call list_leagues(sport) to find your league_id.
  2. Call get_stat_categories(league_id) to see what stats are available.
  3. Call get_roster(league_id) to see your current team.
  4. Call get_free_agents or get_waiver_players to find available talent,
     optionally sorted by a stat category.
  5. Compare and recommend add/drop decisions.
"""

import logging
import sys

import fastmcp
from yahoo_oauth import OAuth2

from yahoo_fantasy_mcp import api
from yahoo_fantasy_mcp.auth import get_oauth

logging.basicConfig(stream=sys.stderr, level=logging.ERROR)
logging.getLogger("fastmcp").setLevel(logging.ERROR)
logging.getLogger("mcp").setLevel(logging.ERROR)

mcp = fastmcp.FastMCP(
    name="yahoo-fantasy-mcp",
    instructions=(
        "Yahoo Fantasy Sports roster management assistant.\n\n"
        "Workflow:\n"
        "1. Call list_leagues(sport) first to discover your league_id.\n"
        "2. Call get_stat_categories(league_id) to see scoring stats and valid sort_by values.\n"
        "3. Call get_roster(league_id) to see your current players.\n"
        "4. Call get_free_agents or get_waiver_players to find available talent.\n"
        "   Use sort_by with a stat name (e.g. 'PTS', 'HR') to rank by recent production.\n"
        "5. Analyze and recommend add/drop moves based on the data.\n\n"
        "All player keys follow the format: {sport}.p.{player_id} (e.g. 'nfl.p.30977').\n"
        "Supported sports: nfl, nba, mlb, nhl."
    ),
)


def _get_sc() -> OAuth2:
    """Get an authenticated OAuth2 session (handles token refresh)."""
    return get_oauth()


@mcp.tool()
def list_leagues(sport: str, season: int | None = None) -> list[dict]:
    """List your Yahoo Fantasy leagues for the given sport in one season.

    Call this first to discover your league_id values. Defaults to the
    current season; pass season only to look up a past season's league.

    Args:
        sport: Sport code — one of: nfl, nba, mlb, nhl.
        season: Season year (e.g. 2024). Omit for the current season.

    Returns:
        List of leagues with: league_id, name, num_teams, scoring_type, season.

    """
    sc = _get_sc()
    return api.list_leagues(sc, sport, season)


@mcp.tool()
def get_stat_categories(league_id: str) -> list[dict]:
    """Return the scoring stat categories for a league.

    Call this to discover valid sort_by values for get_free_agents and get_waiver_players.

    Args:
        league_id: League ID from list_leagues (e.g. "nfl.l.123456").

    Returns:
        List of dicts with: display_name (use this as sort_by), position_type.

    """
    sc = _get_sc()
    return api.get_stat_categories(sc, league_id)


@mcp.tool()
def get_roster(
    league_id: str,
    sort_by: str | None = None,
    stat_type: str = "lastmonth",
    date: str | None = None,
    week: int | None = None,
) -> list[dict]:
    """Get your roster for a fantasy league, today or as set on a past/future date.

    Pass sort_by to include stats so you can compare your players directly
    against free agents and waiver wire results from the same call.

    Pass date (NHL, NBA, MLB) or week (NFL) to see the lineup as set for
    that day or week instead of today's.

    Args:
        league_id: League ID from list_leagues (e.g. "nfl.l.123456").
        sort_by: Stat name to include per player (e.g. "PTS", "HR").
            Use get_stat_categories to see valid values.
            When set, each player includes a 'stats' dict.
        stat_type: Time range for stats. One of: lastmonth (default),
            lastweek, season, average_season. Stats always cover this
            window, not the roster date or week.
        date: Day to get the roster for, as "YYYY-MM-DD" (e.g. "2026-10-15").
            NHL, NBA and MLB only. Defaults to today.
        week: Week number to get the roster for (e.g. 3). NFL only.
            Defaults to the current week.

    Returns:
        List of players with: player_id, player_key, name, eligible_positions,
        selected_position, status. When sort_by is set, also includes
        a 'stats' dict with all stat values for that time range.

    """
    sc = _get_sc()
    return api.get_roster(
        sc, league_id, sort_by=sort_by, stat_type=stat_type, date=date, week=week
    )


@mcp.tool()
def get_free_agents(
    league_id: str,
    position: str | None = None,
    count: int = 25,
    sort_by: str | None = None,
    stat_type: str = "lastmonth",
) -> list[dict]:
    """Get free agent players available to add in a league.

    Position codes by sport:
      NFL: QB, WR, RB, TE, K, DEF
      NBA: PG, SG, SF, PF, C, G, F, UTIL
      MLB: C, 1B, 2B, 3B, SS, OF, SP, RP, P
      NHL: C, LW, RW, D, G

    Args:
        league_id: League ID from list_leagues (e.g. "nfl.l.123456").
        position: Position code to filter by. Omit to get all positions.
        count: Maximum players to return (default 25).
        sort_by: Stat name to sort by (e.g. "PTS", "HR", "QBRating").
            Use get_stat_categories to see valid values.
            Defaults to percent_owned if omitted.
        stat_type: Time range for stats. One of: lastmonth (default),
            lastweek, season, average_season.

    Returns:
        Players sorted by sort_by (or percent_owned) desc. Keys:
        player_id, player_key, name, eligible_positions, percent_owned, status.
        When sort_by is set, also includes a 'stats' dict with all stat values.

    """
    sc = _get_sc()
    return api.get_free_agents(sc, league_id, position, count, sort_by, stat_type)


@mcp.tool()
def get_waiver_players(
    league_id: str,
    position: str | None = None,
    count: int = 25,
    sort_by: str | None = None,
    stat_type: str = "lastmonth",
) -> list[dict]:
    """Get players on the waiver wire in a league.

    Position codes by sport:
      NFL: QB, WR, RB, TE, K, DEF
      NBA: PG, SG, SF, PF, C, G, F, UTIL
      MLB: C, 1B, 2B, 3B, SS, OF, SP, RP, P
      NHL: C, LW, RW, D, G

    Args:
        league_id: League ID from list_leagues (e.g. "nfl.l.123456").
        position: Position code to filter by. Omit to get all positions.
        count: Maximum players to return (default 25).
        sort_by: Stat name to sort by (e.g. "PTS", "HR", "QBRating").
            Use get_stat_categories to see valid values.
            Defaults to percent_owned if omitted.
        stat_type: Time range for stats. One of: lastmonth (default),
            lastweek, season, average_season.

    Returns:
        Players sorted by sort_by (or percent_owned) desc. Keys:
        player_id, player_key, name, eligible_positions, percent_owned, status.
        When sort_by is set, also includes a 'stats' dict with all stat values.

    """
    sc = _get_sc()
    return api.get_waiver_players(sc, league_id, position, count, sort_by, stat_type)


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
