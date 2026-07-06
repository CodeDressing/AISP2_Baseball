# ============================================================
# AISP2 BASEBALL
# PHASE 3.00 PART 1
# ENTERPRISE TEAM INGESTION ENGINE
# FILE: 03_ingestion/team_ingestion.py
# PURPOSE: pull official MLB team data from MLB Stats API,
# validate it, upsert it into the AISP2 database, and return
# human-readable ingestion reports
# ============================================================


# ============================================================
# SECTION 01 - IMPORTS
# ============================================================

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


# ============================================================
# SECTION 02 - PROJECT PATH SETUP
# ============================================================

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[1]
DATABASE_DIR = PROJECT_ROOT / "01_database"
DATA_SOURCES_DIR = PROJECT_ROOT / "02_data_sources"

for path in [
    PROJECT_ROOT,
    DATABASE_DIR,
    DATA_SOURCES_DIR,
]:
    path_string = str(path)

    if path_string not in sys.path:
        sys.path.insert(
            0,
            path_string,
        )


# ============================================================
# SECTION 03 - PROJECT IMPORTS
# ============================================================

from database import managed_database_session
from models import Team
from mlb_stats_api import DEFAULT_SEASON
from mlb_stats_api import MLBStatsAPIClient


# ============================================================
# SECTION 04 - INGESTION CONFIGURATION
# ============================================================

INGESTION_NAME = "AISP2 Team Ingestion"

INGESTION_VERSION = "1.0.0"

DEFAULT_TEAM_SEASON = DEFAULT_SEASON


# ============================================================
# SECTION 05 - SAFE VALUE HELPERS
# ============================================================

def safe_nested_get(
    data: dict[str, Any],
    *keys: str,
) -> Any:
    """
    Safely retrieves nested dictionary values.

    Example:
        safe_nested_get(team, "league", "name")
    """

    current_value: Any = data

    for key in keys:
        if not isinstance(
            current_value,
            dict,
        ):
            return None

        current_value = current_value.get(
            key,
        )

    return current_value


def safe_string(
    value: Any,
) -> str | None:
    """
    Converts a value to a clean string or None.
    """

    if value is None:
        return None

    cleaned_value = str(value).strip()

    if not cleaned_value:
        return None

    return cleaned_value


def safe_boolean(
    value: Any,
    default: bool = True,
) -> bool:
    """
    Converts API values to booleans safely.
    """

    if value is None:
        return default

    return bool(value)


# ============================================================
# SECTION 06 - TEAM DATA NORMALIZATION
# ============================================================

def normalize_team_payload(
    raw_team: dict[str, Any],
) -> dict[str, Any]:
    """
    Converts raw MLB Stats API team data into the AISP2 Team schema.
    """

    return {
        "mlb_team_id": raw_team.get("id"),
        "name": safe_string(
            raw_team.get("name"),
        ),
        "abbreviation": safe_string(
            raw_team.get("abbreviation"),
        ),
        "team_code": safe_string(
            raw_team.get("teamCode"),
        ),
        "file_code": safe_string(
            raw_team.get("fileCode"),
        ),
        "franchise_name": safe_string(
            raw_team.get("franchiseName"),
        ),
        "club_name": safe_string(
            raw_team.get("clubName"),
        ),
        "short_name": safe_string(
            raw_team.get("shortName"),
        ),
        "location_name": safe_string(
            raw_team.get("locationName"),
        ),
        "league": safe_string(
            safe_nested_get(
                raw_team,
                "league",
                "name",
            )
        ),
        "division": safe_string(
            safe_nested_get(
                raw_team,
                "division",
                "name",
            )
        ),
        "venue": safe_string(
            safe_nested_get(
                raw_team,
                "venue",
                "name",
            )
        ),
        "first_year_of_play": safe_string(
            raw_team.get("firstYearOfPlay"),
        ),
        "is_active": safe_boolean(
            raw_team.get("active"),
            default=True,
        ),
    }


# ============================================================
# SECTION 07 - TEAM VALIDATION
# ============================================================

def validate_normalized_team(
    normalized_team: dict[str, Any],
) -> list[str]:
    """
    Validates normalized team data before database insertion.
    """

    errors: list[str] = []

    if not normalized_team.get("mlb_team_id"):
        errors.append(
            "Missing mlb_team_id"
        )

    if not normalized_team.get("name"):
        errors.append(
            "Missing team name"
        )

    return errors


# ============================================================
# SECTION 08 - TEAM UPSERT
# ============================================================

def upsert_team(
    database_session,
    normalized_team: dict[str, Any],
) -> str:
    """
    Inserts or updates one team record.

    Returns:
        "created" or "updated"
    """

    existing_team = (
        database_session.query(Team)
        .filter(
            Team.mlb_team_id == normalized_team["mlb_team_id"]
        )
        .first()
    )

    if existing_team is None:
        new_team = Team(
            **normalized_team,
        )

        database_session.add(
            new_team,
        )

        return "created"

    for field_name, field_value in normalized_team.items():
        setattr(
            existing_team,
            field_name,
            field_value,
        )

    return "updated"


# ============================================================
# SECTION 09 - ENTERPRISE TEAM, PLAYER, AND ROSTER INGESTION ENGINE
# FILE: 03_ingestion/team_ingestion.py
# PURPOSE: initialize warehouse tables, pull official MLB team
# data, upsert teams, pull each team's roster, upsert players,
# upsert roster entries, validate database counts, and return a
# complete ingestion report that proves the chatbot has usable
# team/player data.
# ============================================================

def ingest_mlb_teams(
    season: int = DEFAULT_TEAM_SEASON,
    roster_type: str = "fullRoster",
    include_rosters: bool = True,
) -> dict[str, Any]:
    """
    Pulls official MLB teams from MLB Stats API and stores them
    in the AISP2 database.

    This upgraded version also loads players and roster entries
    so the chatbot, player search, roster browser, and prediction
    engine have real database-backed player data.

    Parameters
    ----------
    season:
        MLB season to ingest.

    roster_type:
        MLB roster type. Recommended values:
            - "active"
            - "fullRoster"
            - "40Man"

        For AISP2 database bootstrapping, "fullRoster" is preferred
        because it loads a much larger player universe.

    include_rosters:
        If True, ingest team rosters and players after teams load.

    Returns
    -------
    dict
        Enterprise ingestion report with counts, errors, readiness,
        and post-ingestion database validation.
    """

    from database import initialize_database
    from models import Player
    from models import RosterEntry

    import requests

    MLB_STATS_API_BASE_URL = "https://statsapi.mlb.com/api/v1"

    def normalize_player_payload(
        raw_player: dict[str, Any],
        raw_roster_entry: dict[str, Any],
        team_id: int,
    ) -> dict[str, Any]:
        full_name = safe_string(
            raw_player.get("fullName"),
        )

        first_name = safe_string(
            raw_player.get("firstName"),
        )

        last_name = safe_string(
            raw_player.get("lastName"),
        )

        if full_name and (not first_name or not last_name):
            name_parts = full_name.split()

            if name_parts and not first_name:
                first_name = name_parts[0]

            if name_parts and not last_name:
                last_name = name_parts[-1]

        position_payload = (
            raw_roster_entry.get("position")
            or raw_player.get("primaryPosition")
            or {}
        )

        return {
            "mlb_player_id": raw_player.get("id"),
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "primary_number": safe_string(
                raw_player.get("primaryNumber")
                or raw_roster_entry.get("jerseyNumber")
            ),
            "position": safe_string(
                position_payload.get("name"),
            ),
            "position_code": safe_string(
                position_payload.get("code"),
            ),
            "bats": safe_string(
                safe_nested_get(
                    raw_player,
                    "batSide",
                    "code",
                )
            ),
            "throws": safe_string(
                safe_nested_get(
                    raw_player,
                    "pitchHand",
                    "code",
                )
            ),
            "height": safe_string(
                raw_player.get("height"),
            ),
            "weight": raw_player.get("weight"),
            "birth_date": safe_string(
                raw_player.get("birthDate"),
            ),
            "birth_city": safe_string(
                raw_player.get("birthCity"),
            ),
            "birth_state_province": safe_string(
                raw_player.get("birthStateProvince"),
            ),
            "birth_country": safe_string(
                raw_player.get("birthCountry"),
            ),
            "mlb_debut_date": safe_string(
                raw_player.get("mlbDebutDate"),
            ),
            "active_status": safe_boolean(
                raw_player.get("active"),
                default=True,
            ),
            "current_team_id": team_id,
        }

    def normalize_roster_entry_payload(
        raw_roster_entry: dict[str, Any],
        season_value: int,
        roster_type_value: str,
        team_id: int,
        player_id: int,
    ) -> dict[str, Any]:
        status_payload = raw_roster_entry.get("status") or {}

        return {
            "season": season_value,
            "roster_type": roster_type_value,
            "jersey_number": safe_string(
                raw_roster_entry.get("jerseyNumber"),
            ),
            "status_code": safe_string(
                status_payload.get("code"),
            ),
            "status_description": safe_string(
                status_payload.get("description"),
            ),
            "team_id": team_id,
            "player_id": player_id,
        }

    def validate_normalized_player(
        normalized_player: dict[str, Any],
    ) -> list[str]:
        errors: list[str] = []

        if not normalized_player.get("mlb_player_id"):
            errors.append("Missing mlb_player_id")

        if not normalized_player.get("full_name"):
            errors.append("Missing player full_name")

        return errors

    def upsert_player(
        database_session,
        normalized_player: dict[str, Any],
    ) -> tuple[str, Any]:
        existing_player = (
            database_session.query(Player)
            .filter(
                Player.mlb_player_id == normalized_player["mlb_player_id"]
            )
            .first()
        )

        if existing_player is None:
            new_player = Player(
                **normalized_player,
            )

            database_session.add(
                new_player,
            )

            database_session.flush()

            return "created", new_player

        for field_name, field_value in normalized_player.items():
            setattr(
                existing_player,
                field_name,
                field_value,
            )

        database_session.flush()

        return "updated", existing_player

    def upsert_roster_entry(
        database_session,
        normalized_roster_entry: dict[str, Any],
    ) -> str:
        existing_roster_entry = (
            database_session.query(RosterEntry)
            .filter(
                RosterEntry.season == normalized_roster_entry["season"]
            )
            .filter(
                RosterEntry.roster_type == normalized_roster_entry["roster_type"]
            )
            .filter(
                RosterEntry.team_id == normalized_roster_entry["team_id"]
            )
            .filter(
                RosterEntry.player_id == normalized_roster_entry["player_id"]
            )
            .first()
        )

        if existing_roster_entry is None:
            database_session.add(
                RosterEntry(
                    **normalized_roster_entry,
                )
            )

            return "created"

        for field_name, field_value in normalized_roster_entry.items():
            setattr(
                existing_roster_entry,
                field_name,
                field_value,
            )

        return "updated"

    def fetch_team_roster(
        mlb_team_id: int,
        season_value: int,
        roster_type_value: str,
    ) -> list[dict[str, Any]]:
        response = requests.get(
            (
                f"{MLB_STATS_API_BASE_URL}/teams/{mlb_team_id}/roster"
                f"?season={season_value}"
                f"&rosterType={roster_type_value}"
            ),
            timeout=20,
        )

        response.raise_for_status()

        payload = response.json()

        return payload.get(
            "roster",
            [],
        )

    initialization_report = initialize_database()

    client = MLBStatsAPIClient()

    raw_teams = client.get_teams(
        season=season,
    )

    report: dict[str, Any] = {
        "ingestion": INGESTION_NAME,
        "version": INGESTION_VERSION,
        "season": season,
        "source": "MLB Stats API",
        "database_initialized": initialization_report.get("initialized"),
        "database_health": initialization_report.get("health"),
        "roster_ingestion_enabled": include_rosters,
        "roster_type": roster_type,
        "raw_team_count": len(raw_teams),
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "player_created": 0,
        "player_updated": 0,
        "player_skipped": 0,
        "roster_created": 0,
        "roster_updated": 0,
        "roster_skipped": 0,
        "roster_fetch_errors": 0,
        "errors": [],
        "teams": [],
        "players_sample": [],
        "team_roster_counts": [],
    }

    with managed_database_session() as database_session:
        for raw_team in raw_teams:
            normalized_team = normalize_team_payload(
                raw_team,
            )

            validation_errors = validate_normalized_team(
                normalized_team,
            )

            if validation_errors:
                report["skipped"] += 1

                report["errors"].append(
                    {
                        "record_type": "team",
                        "raw_team": raw_team,
                        "errors": validation_errors,
                    }
                )

                continue

            team_action = upsert_team(
                database_session=database_session,
                normalized_team=normalized_team,
            )

            database_session.flush()

            database_team = (
                database_session.query(Team)
                .filter(
                    Team.mlb_team_id == normalized_team["mlb_team_id"]
                )
                .first()
            )

            if team_action == "created":
                report["created"] += 1

            elif team_action == "updated":
                report["updated"] += 1

            team_report = {
                "mlb_team_id": normalized_team["mlb_team_id"],
                "database_team_id": database_team.id if database_team else None,
                "name": normalized_team["name"],
                "abbreviation": normalized_team["abbreviation"],
                "league": normalized_team["league"],
                "division": normalized_team["division"],
                "venue": normalized_team["venue"],
                "action": team_action,
            }

            report["teams"].append(
                team_report,
            )

            if not include_rosters:
                continue

            if database_team is None:
                report["roster_skipped"] += 1

                report["errors"].append(
                    {
                        "record_type": "roster",
                        "team": normalized_team["name"],
                        "errors": [
                            "Team was not available after upsert."
                        ],
                    }
                )

                continue

            try:
                roster_entries = fetch_team_roster(
                    mlb_team_id=normalized_team["mlb_team_id"],
                    season_value=season,
                    roster_type_value=roster_type,
                )

            except Exception as roster_error:
                report["roster_fetch_errors"] += 1

                report["errors"].append(
                    {
                        "record_type": "roster_fetch",
                        "team": normalized_team["name"],
                        "mlb_team_id": normalized_team["mlb_team_id"],
                        "error": str(roster_error),
                    }
                )

                continue

            report["team_roster_counts"].append(
                {
                    "team": normalized_team["name"],
                    "mlb_team_id": normalized_team["mlb_team_id"],
                    "roster_count": len(roster_entries),
                }
            )

            for raw_roster_entry in roster_entries:
                raw_player = raw_roster_entry.get(
                    "person",
                    {},
                )

                normalized_player = normalize_player_payload(
                    raw_player=raw_player,
                    raw_roster_entry=raw_roster_entry,
                    team_id=database_team.id,
                )

                player_validation_errors = validate_normalized_player(
                    normalized_player,
                )

                if player_validation_errors:
                    report["player_skipped"] += 1

                    report["errors"].append(
                        {
                            "record_type": "player",
                            "team": normalized_team["name"],
                            "raw_player": raw_player,
                            "errors": player_validation_errors,
                        }
                    )

                    continue

                player_action, database_player = upsert_player(
                    database_session=database_session,
                    normalized_player=normalized_player,
                )

                if player_action == "created":
                    report["player_created"] += 1

                elif player_action == "updated":
                    report["player_updated"] += 1

                normalized_roster_entry = normalize_roster_entry_payload(
                    raw_roster_entry=raw_roster_entry,
                    season_value=season,
                    roster_type_value=roster_type,
                    team_id=database_team.id,
                    player_id=database_player.id,
                )

                roster_action = upsert_roster_entry(
                    database_session=database_session,
                    normalized_roster_entry=normalized_roster_entry,
                )

                if roster_action == "created":
                    report["roster_created"] += 1

                elif roster_action == "updated":
                    report["roster_updated"] += 1

                if len(report["players_sample"]) < 25:
                    report["players_sample"].append(
                        {
                            "mlb_player_id": normalized_player["mlb_player_id"],
                            "name": normalized_player["full_name"],
                            "team": normalized_team["name"],
                            "position": normalized_player["position"],
                            "player_action": player_action,
                            "roster_action": roster_action,
                        }
                    )

    report["database_team_count_after_ingestion"] = count_database_teams()

    try:
        with managed_database_session() as database_session:
            report["database_player_count_after_ingestion"] = (
                database_session.query(Player).count()
            )

            report["database_roster_entry_count_after_ingestion"] = (
                database_session.query(RosterEntry).count()
            )

    except Exception as count_error:
        report["database_player_count_after_ingestion"] = 0
        report["database_roster_entry_count_after_ingestion"] = 0

        report["errors"].append(
            {
                "record_type": "post_ingestion_count",
                "error": str(count_error),
            }
        )

    report["success"] = (
        report["raw_team_count"] > 0
        and report["database_health"] is True
        and report["database_team_count_after_ingestion"] >= 30
        and (
            not include_rosters
            or report["database_player_count_after_ingestion"] > 0
        )
    )

    report["prediction_data_foundation_ready"] = (
        report["database_team_count_after_ingestion"] >= 30
        and report.get("database_player_count_after_ingestion", 0) >= 500
        and report.get("database_roster_entry_count_after_ingestion", 0) >= 500
    )

    report["next_required_action"] = (
        "Team/player/roster foundation is loaded. Next import Statcast warehouse CSVs."
        if report["prediction_data_foundation_ready"]
        else "Roster/player ingestion did not produce enough rows. Verify roster_type and MLB API access."
    )

    return report
# ============================================================
# SECTION 10 - DATABASE TEAM COUNT
# ============================================================

def count_database_teams() -> int:
    """
    Counts teams currently stored in the database.
    """

    with managed_database_session() as database_session:
        return database_session.query(Team).count()


# ============================================================
# SECTION 11 - TEAM INVENTORY
# ============================================================

def build_team_inventory() -> list[dict[str, Any]]:
    """
    Returns a human-readable list of teams currently in the database.
    """

    with managed_database_session() as database_session:
        teams = (
            database_session.query(Team)
            .order_by(
                Team.name.asc(),
            )
            .all()
        )

        return [
            {
                "mlb_team_id": team.mlb_team_id,
                "name": team.name,
                "abbreviation": team.abbreviation,
                "league": team.league,
                "division": team.division,
                "venue": team.venue,
                "is_active": team.is_active,
            }
            for team in teams
        ]


# ============================================================
# SECTION 12 - INGESTION SUMMARY
# ============================================================

def build_ingestion_summary(
    report: dict[str, Any],
) -> str:
    """
    Builds a readable summary for terminal output.
    """

    return (
        f"{INGESTION_NAME} completed | "
        f"Season: {report['season']} | "
        f"Raw Teams: {report['raw_team_count']} | "
        f"Created: {report['created']} | "
        f"Updated: {report['updated']} | "
        f"Skipped: {report['skipped']} | "
        f"Database Teams: {report['database_team_count_after_ingestion']}"
    )


# ============================================================
# SECTION 13 - LOCAL EXECUTION TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("AISP2 TEAM INGESTION ENGINE")
    print("=" * 70)

    ingestion_report = ingest_mlb_teams()

    print()
    print("Ingestion Summary")
    print(build_ingestion_summary(ingestion_report))

    print()
    print("Teams Loaded")
    for team_record in ingestion_report["teams"]:
        print(
            f"{team_record['abbreviation']} | "
            f"{team_record['name']} | "
            f"{team_record['league']} | "
            f"{team_record['division']} | "
            f"{team_record['action']}"
        )

    print()
    print("Final Database Team Count")
    print(count_database_teams())

    print()
    print("Team ingestion completed.")
    print()


# ============================================================
# SECTION 14 - FUTURE INGESTION ROADMAP
# ============================================================

"""
Phase 3.01:
    Add player ingestion.

Phase 3.02:
    Add roster ingestion.

Phase 3.03:
    Add player season statistics ingestion.

Phase 3.04:
    Add schedule ingestion.

Phase 3.05:
    Add game result ingestion.

Phase 3.06:
    Add Statcast ingestion.

Phase 3.07:
    Add ingestion audit reports.

Phase 3.08:
    Add dashboard database counts.

Phase 3.09:
    Replace demo homepage values with live database counts.

Phase 3.10:
    Replace demo team dropdown with database-backed teams.
"""