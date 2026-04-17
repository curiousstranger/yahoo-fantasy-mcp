# Yahoo Fantasy MCP — Agent Reference

This MCP server provides read-only access to Yahoo Fantasy Sports data for roster management. Use it to inspect leagues, rosters, and available players, then recommend add/drop decisions.

## Canonical Call Sequence

Always follow this order — each step provides inputs for the next:

1. `list_leagues(sport)` → get `league_id`
2. `get_stat_categories(league_id)` → get valid `sort_by` values
3. `get_roster(league_id, sort_by=<stat>)` → see current team with stats
4. `get_free_agents(league_id, sort_by=<stat>)` or `get_waiver_players(league_id, sort_by=<stat>)` → find available talent with the same stat
5. Compare `stats` dicts across all three results and recommend add/drop moves

Use the same `sort_by` and `stat_type` across steps 3–4 so results are directly comparable.

## Tool Reference

### `list_leagues`

```
list_leagues(sport: str) -> list[dict]
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sport` | str | yes | One of: `nfl`, `nba`, `mlb`, `nhl` |

**Returns:** List of leagues you belong to.

```json
[
  {
    "league_id": "nfl.l.123456",
    "name": "Monday Night Mayhem",
    "num_teams": 12,
    "scoring_type": "head",
    "season": "2024"
  }
]
```

---

### `get_stat_categories`

```
get_stat_categories(league_id: str) -> list[dict]
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `league_id` | str | yes | From `list_leagues` (e.g. `"nfl.l.123456"`) |

**Returns:** Scoring categories for the league. The `display_name` values are valid inputs for `sort_by` in `get_roster`, `get_free_agents`, and `get_waiver_players`.

```json
[
  {"display_name": "PTS", "position_type": "O"},
  {"display_name": "REB", "position_type": "O"},
  {"display_name": "AST", "position_type": "O"}
]
```

---

### `get_roster`

```
get_roster(
    league_id: str,
    sort_by: str | None = None,
    stat_type: str = "lastmonth"
) -> list[dict]
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `league_id` | str | required | From `list_leagues` |
| `sort_by` | str \| None | `None` | Stat name from `get_stat_categories`. When set, each player includes a `stats` dict. |
| `stat_type` | str | `"lastmonth"` | Time window: `lastmonth`, `lastweek`, `season`, `average_season` |

**Returns:** Your current roster. Pass `sort_by` to include stats for direct comparison with `get_free_agents` / `get_waiver_players` results.

Without `sort_by`:
```json
[
  {
    "player_id": "5185",
    "player_key": "nba.p.5185",
    "name": "Nikola Jokic",
    "eligible_positions": ["C", "UTIL"],
    "selected_position": "C",
    "status": ""
  }
]
```

With `sort_by="PTS"`:
```json
[
  {
    "player_id": "5185",
    "player_key": "nba.p.5185",
    "name": "Nikola Jokic",
    "eligible_positions": ["C", "UTIL"],
    "selected_position": "C",
    "status": "",
    "stats": {"PTS": 26.4, "REB": 12.1, "AST": 9.0}
  }
]
```

`status` is empty string when healthy. Common values: `"Q"` (questionable), `"O"` (out), `"IR"` (injured reserve).

---

### `get_free_agents`

```
get_free_agents(
    league_id: str,
    position: str | None = None,
    count: int = 25,
    sort_by: str | None = None,
    stat_type: str = "lastmonth"
) -> list[dict]
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `league_id` | str | required | From `list_leagues` |
| `position` | str \| None | `None` | Position code to filter (see table below). `None` returns all. |
| `count` | int | `25` | Max players to return |
| `sort_by` | str \| None | `None` | Stat name from `get_stat_categories`. Defaults to `percent_owned`. |
| `stat_type` | str | `"lastmonth"` | Time window: `lastmonth`, `lastweek`, `season`, `average_season` |

**Returns:** Players sorted by `sort_by` (or `percent_owned`) descending. When `sort_by` is set, each player includes a `stats` dict.

```json
[
  {
    "player_id": "6026",
    "player_key": "nba.p.6026",
    "name": "Jalen Williams",
    "eligible_positions": ["SG", "SF", "G", "F", "UTIL"],
    "percent_owned": 94.0,
    "status": "",
    "stats": {"PTS": 24.1, "REB": 4.5, "AST": 5.2}
  }
]
```

---

### `get_waiver_players`

Same signature and return shape as `get_free_agents`. Queries the waiver wire instead of free agents.

```
get_waiver_players(
    league_id: str,
    position: str | None = None,
    count: int = 25,
    sort_by: str | None = None,
    stat_type: str = "lastmonth"
) -> list[dict]
```

---

## Player Key Format

All player keys follow the pattern: `{sport}.p.{player_id}`

Examples: `nfl.p.30977`, `nba.p.5185`, `mlb.p.9112`, `nhl.p.4024`

---

## Position Codes

| Sport | Positions |
|---|---|
| NFL | `QB`, `WR`, `RB`, `TE`, `K`, `DEF` |
| NBA | `PG`, `SG`, `SF`, `PF`, `C`, `G`, `F`, `UTIL` |
| MLB | `C`, `1B`, `2B`, `3B`, `SS`, `OF`, `SP`, `RP`, `P` |
| NHL | `C`, `LW`, `RW`, `D`, `G` |

---

## Stat Sorting

`sort_by` accepts any `display_name` from `get_stat_categories`. Common examples by sport:

| Sport | Common `sort_by` values |
|---|---|
| NFL | `PassYds`, `RushYds`, `RecYds`, `PassTD`, `RushTD`, `QBRating` |
| NBA | `PTS`, `REB`, `AST`, `STL`, `BLK`, `3PTM` |
| MLB | `HR`, `RBI`, `AVG`, `R`, `SB`, `ERA`, `WHIP`, `K` |
| NHL | `G`, `A`, `PTS`, `+/-`, `PIM`, `SHT%` |

Always call `get_stat_categories` to confirm valid values for the specific league — scoring varies by league settings.

`stat_type` values:
- `lastmonth` — last 30 days (default, best for recent form)
- `lastweek` — last 7 days
- `season` — cumulative season totals
- `average_season` — per-game season averages

---

## Error Patterns

| Condition | What happens |
|---|---|
| Missing `YAHOO_CLIENT_ID` / `YAHOO_CLIENT_SECRET` | `EnvironmentError` with instructions to set env vars |
| Token missing (auth not run) | OAuth error from `yahoo_oauth` — user must run `yahoo-fantasy-mcp-auth` |
| Invalid `league_id` | Exception from Yahoo API — verify with `list_leagues` first |
| Invalid `sort_by` | Players return but `_sort_val` defaults to 0; results effectively unsorted — use `get_stat_categories` to confirm valid names |
| League with no free agents | Empty list returned |
