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
# SECTION 09 - TEAM INGESTION ENGINE
# ============================================================

def ingest_mlb_teams(
    season: int = DEFAULT_TEAM_SEASON,
) -> dict[str, Any]:
    """
    Pulls official MLB teams from MLB Stats API and stores them
    in the AISP2 database.
    """

    client = MLBStatsAPIClient()

    raw_teams = client.get_teams(
        season=season,
    )

    report: dict[str, Any] = {
        "ingestion": INGESTION_NAME,
        "version": INGESTION_VERSION,
        "season": season,
        "source": "MLB Stats API",
        "raw_team_count": len(raw_teams),
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
        "teams": [],
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
                        "raw_team": raw_team,
                        "errors": validation_errors,
                    }
                )

                continue

            action = upsert_team(
                database_session=database_session,
                normalized_team=normalized_team,
            )

            if action == "created":
                report["created"] += 1

            elif action == "updated":
                report["updated"] += 1

            report["teams"].append(
                {
                    "mlb_team_id": normalized_team["mlb_team_id"],
                    "name": normalized_team["name"],
                    "abbreviation": normalized_team["abbreviation"],
                    "league": normalized_team["league"],
                    "division": normalized_team["division"],
                    "action": action,
                }
            )

    report["success"] = (
        report["raw_team_count"] > 0
        and len(report["errors"]) == 0
    )

    report["database_team_count_after_ingestion"] = count_database_teams()

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