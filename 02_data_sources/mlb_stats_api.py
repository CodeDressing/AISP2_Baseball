# ============================================================
# AISP2 BASEBALL
# PHASE 2.00 PART 1
# ENTERPRISE MLB STATS API CLIENT
# FILE: 02_data_sources/mlb_stats_api.py
# PURPOSE: official MLB Stats API client for teams, rosters,
# players, schedules, standings, statistics, game data,
# health checks, and future warehouse ingestion support
# ============================================================


# ============================================================
# SECTION 01 - IMPORTS
# ============================================================

from __future__ import annotations

from typing import Any

import requests


# ============================================================
# SECTION 02 - MLB API CONFIGURATION
# ============================================================

MLB_API_BASE_URL = "https://statsapi.mlb.com/api/v1"

DEFAULT_TIMEOUT = 30

DEFAULT_SPORT_ID = 1

DEFAULT_SEASON = 2026


# ============================================================
# SECTION 03 - MLB STATS API CLIENT
# ============================================================

class MLBStatsAPIClient:
    """
    Enterprise MLB Stats API client.

    Responsibility:
        - Talk to MLB Stats API.
        - Return raw baseball data.
        - Avoid database logic.
        - Avoid prediction logic.
        - Support future ingestion services.
    """

    def __init__(
        self,
        base_url: str = MLB_API_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout


# ============================================================
# SECTION 04 - CORE REQUEST HANDLER
# ============================================================

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Sends a GET request to the MLB Stats API.
        """

        url = f"{self.base_url}/{path.lstrip('/')}"

        response = requests.get(
            url,
            params=params,
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.json()


# ============================================================
# SECTION 05 - API HEALTH CHECK
# ============================================================

    def health_check(self) -> dict[str, Any]:
        """
        Verifies that the MLB Stats API is reachable.
        """

        try:
            teams = self.get_teams(
                season=DEFAULT_SEASON,
            )

            return {
                "source": "MLB Stats API",
                "status": "healthy",
                "base_url": self.base_url,
                "teams_returned": len(teams),
            }

        except Exception as exc:
            return {
                "source": "MLB Stats API",
                "status": "unhealthy",
                "base_url": self.base_url,
                "error": str(exc),
            }


# ============================================================
# SECTION 06 - TEAM ENDPOINTS
# ============================================================

    def get_teams(
        self,
        season: int = DEFAULT_SEASON,
        sport_id: int = DEFAULT_SPORT_ID,
    ) -> list[dict[str, Any]]:
        """
        Returns MLB teams for a season.
        """

        payload = self._get(
            "teams",
            params={
                "sportId": sport_id,
                "season": season,
            },
        )

        return payload.get(
            "teams",
            [],
        )


    def get_team(
        self,
        team_id: int,
        season: int = DEFAULT_SEASON,
    ) -> dict[str, Any]:
        """
        Returns one MLB team by team ID.
        """

        payload = self._get(
            f"teams/{team_id}",
            params={
                "season": season,
            },
        )

        teams = payload.get(
            "teams",
            [],
        )

        if not teams:
            return {}

        return teams[0]


    def get_team_full_profile(
        self,
        team_id: int,
        season: int = DEFAULT_SEASON,
    ) -> dict[str, Any]:
        """
        Returns expanded team profile data.
        """

        return self._get(
            f"teams/{team_id}",
            params={
                "season": season,
                "hydrate": "venue,division,league,sport,leagueRecord,records,stats",
            },
        )


# ============================================================
# SECTION 07 - ROSTER ENDPOINTS
# ============================================================

    def get_roster(
        self,
        team_id: int,
        season: int = DEFAULT_SEASON,
        roster_type: str = "active",
    ) -> list[dict[str, Any]]:
        """
        Returns a team roster.
        """

        payload = self._get(
            f"teams/{team_id}/roster",
            params={
                "season": season,
                "rosterType": roster_type,
            },
        )

        return payload.get(
            "roster",
            [],
        )


    def get_active_roster(
        self,
        team_id: int,
        season: int = DEFAULT_SEASON,
    ) -> list[dict[str, Any]]:
        """
        Returns active roster.
        """

        return self.get_roster(
            team_id=team_id,
            season=season,
            roster_type="active",
        )


    def get_forty_man_roster(
        self,
        team_id: int,
        season: int = DEFAULT_SEASON,
    ) -> list[dict[str, Any]]:
        """
        Returns 40-man roster.
        """

        return self.get_roster(
            team_id=team_id,
            season=season,
            roster_type="40Man",
        )


    def get_all_team_rosters(
        self,
        season: int = DEFAULT_SEASON,
        roster_type: str = "active",
    ) -> list[dict[str, Any]]:
        """
        Returns rosters for all MLB teams.
        """

        teams = self.get_teams(
            season=season,
        )

        rosters: list[dict[str, Any]] = []

        for team in teams:
            team_id = team.get("id")

            if not team_id:
                continue

            try:
                roster = self.get_roster(
                    team_id=team_id,
                    season=season,
                    roster_type=roster_type,
                )

                rosters.append(
                    {
                        "team": team,
                        "team_id": team_id,
                        "team_name": team.get("name"),
                        "season": season,
                        "roster_type": roster_type,
                        "players": roster,
                        "player_count": len(roster),
                    }
                )

            except Exception as exc:
                rosters.append(
                    {
                        "team": team,
                        "team_id": team_id,
                        "team_name": team.get("name"),
                        "season": season,
                        "roster_type": roster_type,
                        "players": [],
                        "player_count": 0,
                        "error": str(exc),
                    }
                )

        return rosters


# ============================================================
# SECTION 08 - PLAYER ENDPOINTS
# ============================================================

    def get_player(
        self,
        player_id: int,
    ) -> dict[str, Any]:
        """
        Returns one MLB player profile.
        """

        payload = self._get(
            f"people/{player_id}",
        )

        people = payload.get(
            "people",
            [],
        )

        if not people:
            return {}

        return people[0]


    def get_players_by_ids(
        self,
        player_ids: list[int],
    ) -> list[dict[str, Any]]:
        """
        Returns player profiles for multiple MLB player IDs.
        """

        players: list[dict[str, Any]] = []

        for player_id in player_ids:
            try:
                player = self.get_player(
                    player_id=player_id,
                )

                if player:
                    players.append(player)

            except Exception:
                continue

        return players


    def get_all_active_players(
        self,
        season: int = DEFAULT_SEASON,
    ) -> list[dict[str, Any]]:
        """
        Returns all MLB players for a season.
        """

        payload = self._get(
            "sports/1/players",
            params={
                "season": season,
            },
        )

        return payload.get(
            "people",
            [],
        )


    def search_player_by_name(
        self,
        name: str,
        season: int = DEFAULT_SEASON,
    ) -> list[dict[str, Any]]:
        """
        Searches active MLB players by name.
        """

        players = self.get_all_active_players(
            season=season,
        )

        search_value = name.lower().strip()

        return [
            player
            for player in players
            if search_value in player.get("fullName", "").lower()
        ]


# ============================================================
# SECTION 09 - PLAYER STATISTICS ENDPOINTS
# ============================================================

    def get_player_season_stats(
        self,
        player_id: int,
        season: int = DEFAULT_SEASON,
        group: str = "hitting",
    ) -> dict[str, Any]:
        """
        Returns player season statistics.
        """

        return self._get(
            f"people/{player_id}/stats",
            params={
                "stats": "season",
                "season": season,
                "group": group,
            },
        )


    def get_player_career_stats(
        self,
        player_id: int,
        group: str = "hitting",
    ) -> dict[str, Any]:
        """
        Returns player career statistics.
        """

        return self._get(
            f"people/{player_id}/stats",
            params={
                "stats": "career",
                "group": group,
            },
        )


    def get_player_game_log(
        self,
        player_id: int,
        season: int = DEFAULT_SEASON,
        group: str = "hitting",
    ) -> dict[str, Any]:
        """
        Returns player game logs.
        """

        return self._get(
            f"people/{player_id}/stats",
            params={
                "stats": "gameLog",
                "season": season,
                "group": group,
            },
        )


    def get_player_splits(
        self,
        player_id: int,
        season: int = DEFAULT_SEASON,
        group: str = "hitting",
        split: str = "homeAndAway",
    ) -> dict[str, Any]:
        """
        Returns player split statistics.
        """

        return self._get(
            f"people/{player_id}/stats",
            params={
                "stats": split,
                "season": season,
                "group": group,
            },
        )


    def get_complete_player_profile(
        self,
        player_id: int,
        season: int = DEFAULT_SEASON,
    ) -> dict[str, Any]:
        """
        Returns a multi-part player profile bundle.
        """

        return {
            "player": self.get_player(
                player_id=player_id,
            ),
            "season_hitting": self.get_player_season_stats(
                player_id=player_id,
                season=season,
                group="hitting",
            ),
            "season_pitching": self.get_player_season_stats(
                player_id=player_id,
                season=season,
                group="pitching",
            ),
            "career_hitting": self.get_player_career_stats(
                player_id=player_id,
                group="hitting",
            ),
            "career_pitching": self.get_player_career_stats(
                player_id=player_id,
                group="pitching",
            ),
            "game_log_hitting": self.get_player_game_log(
                player_id=player_id,
                season=season,
                group="hitting",
            ),
        }


# ============================================================
# SECTION 10 - TEAM STATISTICS ENDPOINTS
# ============================================================

    def get_team_season_stats(
        self,
        team_id: int,
        season: int = DEFAULT_SEASON,
        group: str = "hitting",
    ) -> dict[str, Any]:
        """
        Returns team season statistics.
        """

        return self._get(
            f"teams/{team_id}/stats",
            params={
                "stats": "season",
                "season": season,
                "group": group,
            },
        )


# ============================================================
# SECTION 11 - SCHEDULE ENDPOINTS
# ============================================================

    def get_schedule(
        self,
        season: int = DEFAULT_SEASON,
        start_date: str | None = None,
        end_date: str | None = None,
        team_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Returns MLB schedule data.
        """

        params: dict[str, Any] = {
            "sportId": DEFAULT_SPORT_ID,
            "season": season,
        }

        if start_date:
            params["startDate"] = start_date

        if end_date:
            params["endDate"] = end_date

        if team_id:
            params["teamId"] = team_id

        return self._get(
            "schedule",
            params=params,
        )


    def get_schedule_games(
        self,
        season: int = DEFAULT_SEASON,
        start_date: str | None = None,
        end_date: str | None = None,
        team_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Returns flattened list of games from the schedule endpoint.
        """

        payload = self.get_schedule(
            season=season,
            start_date=start_date,
            end_date=end_date,
            team_id=team_id,
        )

        games: list[dict[str, Any]] = []

        for date_block in payload.get("dates", []):
            for game in date_block.get("games", []):
                games.append(game)

        return games


# ============================================================
# SECTION 12 - STANDINGS ENDPOINTS
# ============================================================

    def get_standings(
        self,
        season: int = DEFAULT_SEASON,
    ) -> dict[str, Any]:
        """
        Returns MLB standings.
        """

        return self._get(
            "standings",
            params={
                "leagueId": "103,104",
                "season": season,
                "standingsTypes": "regularSeason",
            },
        )


# ============================================================
# SECTION 13 - GAME ENDPOINTS
# ============================================================

    def get_game_feed(
        self,
        game_pk: int,
    ) -> dict[str, Any]:
        """
        Returns live game feed.
        """

        return self._get(
            f"game/{game_pk}/feed/live",
        )


    def get_game_boxscore(
        self,
        game_pk: int,
    ) -> dict[str, Any]:
        """
        Returns game box score.
        """

        return self._get(
            f"game/{game_pk}/boxscore",
        )


    def get_game_linescore(
        self,
        game_pk: int,
    ) -> dict[str, Any]:
        """
        Returns game line score.
        """

        return self._get(
            f"game/{game_pk}/linescore",
        )


    def get_game_content(
        self,
        game_pk: int,
    ) -> dict[str, Any]:
        """
        Returns game content.
        """

        return self._get(
            f"game/{game_pk}/content",
        )


# ============================================================
# SECTION 14 - TRANSACTION ENDPOINTS
# ============================================================

    def get_transactions(
        self,
        start_date: str,
        end_date: str,
        team_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Returns MLB transactions.
        """

        params: dict[str, Any] = {
            "sportId": DEFAULT_SPORT_ID,
            "startDate": start_date,
            "endDate": end_date,
        }

        if team_id:
            params["teamId"] = team_id

        return self._get(
            "transactions",
            params=params,
        )


# ============================================================
# SECTION 15 - REFERENCE ENDPOINTS
# ============================================================

    def get_divisions(
        self,
    ) -> list[dict[str, Any]]:
        """
        Returns MLB divisions.
        """

        payload = self._get(
            "divisions",
            params={
                "sportId": DEFAULT_SPORT_ID,
            },
        )

        return payload.get(
            "divisions",
            [],
        )


    def get_leagues(
        self,
    ) -> list[dict[str, Any]]:
        """
        Returns MLB leagues.
        """

        payload = self._get(
            "league",
            params={
                "sportId": DEFAULT_SPORT_ID,
            },
        )

        return payload.get(
            "leagues",
            [],
        )


    def get_venues(
        self,
    ) -> list[dict[str, Any]]:
        """
        Returns MLB venues.
        """

        payload = self._get(
            "venues",
        )

        return payload.get(
            "venues",
            [],
        )


# ============================================================
# SECTION 16 - HUMAN-FRIENDLY SUMMARY HELPERS
# ============================================================

    def summarize_teams(
        self,
        season: int = DEFAULT_SEASON,
    ) -> list[dict[str, Any]]:
        """
        Returns simplified team records for display and debugging.
        """

        teams = self.get_teams(
            season=season,
        )

        return [
            {
                "team_id": team.get("id"),
                "name": team.get("name"),
                "abbreviation": team.get("abbreviation"),
                "league": team.get("league", {}).get("name"),
                "division": team.get("division", {}).get("name"),
                "venue": team.get("venue", {}).get("name"),
            }
            for team in teams
        ]


    def summarize_roster(
        self,
        team_id: int,
        season: int = DEFAULT_SEASON,
        roster_type: str = "active",
    ) -> list[dict[str, Any]]:
        """
        Returns simplified roster records for display and debugging.
        """

        roster = self.get_roster(
            team_id=team_id,
            season=season,
            roster_type=roster_type,
        )

        return [
            {
                "player_id": item.get("person", {}).get("id"),
                "name": item.get("person", {}).get("fullName"),
                "position": item.get("position", {}).get("name"),
                "position_code": item.get("position", {}).get("code"),
                "jersey_number": item.get("jerseyNumber"),
                "status": item.get("status", {}).get("description"),
            }
            for item in roster
        ]


# ============================================================
# SECTION 17 - SOURCE CAPABILITY REPORT
# ============================================================

    def capability_report(self) -> dict[str, Any]:
        """
        Returns a report of this client's available capabilities.
        """

        return {
            "source": "MLB Stats API",
            "base_url": self.base_url,
            "status": "configured",
            "capabilities": [
                "teams",
                "team profiles",
                "rosters",
                "players",
                "player season stats",
                "player career stats",
                "player game logs",
                "team season stats",
                "schedules",
                "standings",
                "game feeds",
                "box scores",
                "line scores",
                "transactions",
                "divisions",
                "leagues",
                "venues",
            ],
            "future_usage": [
                "database ingestion",
                "feature engineering",
                "probability engine",
                "machine learning training",
                "dashboard display",
            ],
        }


# ============================================================
# SECTION 18 - LOCAL EXECUTION TEST
# ============================================================

if __name__ == "__main__":

    client = MLBStatsAPIClient()

    print()
    print("=" * 60)
    print("AISP2 MLB STATS API CLIENT TEST")
    print("=" * 60)

    print()
    print("Health Check")
    print(client.health_check())

    print()
    print("Team Summary Sample")
    teams = client.summarize_teams()
    print(f"Teams returned: {len(teams)}")

    for team in teams[:5]:
        print(team)

    print()
    print("Capability Report")
    print(client.capability_report())

    print()
    print("MLB Stats API client test completed.")
    print()


# ============================================================
# SECTION 19 - FUTURE DATA SOURCE ROADMAP
# ============================================================

"""
Phase 2.01
    Connect MLBStatsAPIClient to team ingestion.

Phase 2.02
    Connect roster ingestion.

Phase 2.03
    Connect player profile ingestion.

Phase 2.04
    Connect player season stat ingestion.

Phase 2.05
    Connect schedule and game ingestion.

Phase 2.06
    Add Baseball Savant / Statcast client.

Phase 2.07
    Add FanGraphs integration.

Phase 2.08
    Add Baseball Reference historical support.

Phase 2.09
    Add Retrosheet historical play-by-play support.

Phase 2.10
    Add Lahman historical database support.

Long-Term Data Source Strategy

Tier 1:
    MLB Stats API
    Baseball Savant / Statcast

Tier 2:
    FanGraphs
    Baseball Reference

Historical:
    Retrosheet
    Lahman Database

Context:
    Weather
    Injuries
    Transactions
    Lineups
    Ballpark factors
    Rest days
    Travel context
"""
