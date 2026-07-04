# ============================================================
# AISP2 BASEBALL
# PHASE 9 PART 2.0
# ENTERPRISE PLAYER INGESTION ENGINE
# FILE: 03_ingestion/player_ingestion.py
# PURPOSE: pull official MLB player data, normalize it, upsert
# it into the AISP2 warehouse, and return readable reports
# ============================================================

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


# ============================================================
# SECTION 01 - PROJECT PATH SETUP
# ============================================================

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[1]
DATABASE_DIR = PROJECT_ROOT / "01_database"
DATA_SOURCES_DIR = PROJECT_ROOT / "02_data_sources"

for path in [PROJECT_ROOT, DATABASE_DIR, DATA_SOURCES_DIR]:
    path_string = str(path)

    if path_string not in sys.path:
        sys.path.insert(0, path_string)


# ============================================================
# SECTION 02 - PROJECT IMPORTS
# ============================================================

from database import initialize_database
from database import managed_database_session

from models import Player
from models import Team

from mlb_stats_api import DEFAULT_SEASON
from mlb_stats_api import MLBStatsAPIClient


# ============================================================
# SECTION 03 - CONFIGURATION
# ============================================================

INGESTION_NAME = "AISP2 Player Ingestion"
INGESTION_VERSION = "1.0.0"
DEFAULT_PLAYER_SEASON = DEFAULT_SEASON


# ============================================================
# SECTION 04 - SAFE HELPERS
# ============================================================

def safe_nested_get(
    data: dict[str, Any],
    *keys: str,
) -> Any:
    current_value: Any = data

    for key in keys:
        if not isinstance(current_value, dict):
            return None

        current_value = current_value.get(key)

    return current_value


def safe_string(value: Any) -> str | None:
    if value is None:
        return None

    cleaned_value = str(value).strip()

    if not cleaned_value:
        return None

    return cleaned_value


def safe_integer(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None

        return int(value)

    except (TypeError, ValueError):
        return None


def safe_boolean(
    value: Any,
    default: bool = True,
) -> bool:
    if value is None:
        return default

    return bool(value)


# ============================================================
# SECTION 05 - PLAYER NORMALIZATION
# ============================================================

def normalize_player_payload(
    raw_player: dict[str, Any],
) -> dict[str, Any]:
    return {
        "mlb_player_id": raw_player.get("id"),
        "full_name": safe_string(raw_player.get("fullName")),
        "first_name": safe_string(raw_player.get("firstName")),
        "last_name": safe_string(raw_player.get("lastName")),
        "primary_number": safe_string(raw_player.get("primaryNumber")),
        "position": safe_string(
            safe_nested_get(raw_player, "primaryPosition", "name")
        ),
        "position_code": safe_string(
            safe_nested_get(raw_player, "primaryPosition", "code")
        ),
        "bats": safe_string(
            safe_nested_get(raw_player, "batSide", "code")
        ),
        "throws": safe_string(
            safe_nested_get(raw_player, "pitchHand", "code")
        ),
        "height": safe_string(raw_player.get("height")),
        "weight": safe_integer(raw_player.get("weight")),
        "birth_date": safe_string(raw_player.get("birthDate")),
        "birth_city": safe_string(raw_player.get("birthCity")),
        "birth_state_province": safe_string(
            raw_player.get("birthStateProvince")
        ),
        "birth_country": safe_string(raw_player.get("birthCountry")),
        "mlb_debut_date": safe_string(raw_player.get("mlbDebutDate")),
        "active_status": safe_boolean(
            raw_player.get("active"),
            default=True,
        ),
    }


# ============================================================
# SECTION 06 - PLAYER VALIDATION
# ============================================================

def validate_normalized_player(
    normalized_player: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    if not normalized_player.get("mlb_player_id"):
        errors.append("Missing mlb_player_id")

    if not normalized_player.get("full_name"):
        errors.append("Missing full_name")

    return errors


# ============================================================
# SECTION 07 - PLAYER UPSERT
# ============================================================

def upsert_player(
    database_session,
    normalized_player: dict[str, Any],
) -> str:
    existing_player = (
        database_session.query(Player)
        .filter(Player.mlb_player_id == normalized_player["mlb_player_id"])
        .first()
    )

    if existing_player is None:
        new_player = Player(**normalized_player)

        database_session.add(new_player)

        return "created"

    for field_name, field_value in normalized_player.items():
        setattr(existing_player, field_name, field_value)

    return "updated"


# ============================================================
# SECTION 08 - PLAYER INGESTION ENGINE
# ============================================================

def ingest_mlb_players(
    season: int = DEFAULT_PLAYER_SEASON,
) -> dict[str, Any]:
    initialization_report = initialize_database()

    client = MLBStatsAPIClient()

    raw_players = client.get_all_active_players(
        season=season,
    )

    report: dict[str, Any] = {
        "ingestion": INGESTION_NAME,
        "version": INGESTION_VERSION,
        "season": season,
        "source": "MLB Stats API",
        "database_initialized": initialization_report.get("initialized"),
        "database_health": initialization_report.get("health"),
        "raw_player_count": len(raw_players),
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
        "players": [],
    }

    with managed_database_session() as database_session:
        for raw_player in raw_players:
            normalized_player = normalize_player_payload(raw_player)

            validation_errors = validate_normalized_player(
                normalized_player,
            )

            if validation_errors:
                report["skipped"] += 1
                report["errors"].append(
                    {
                        "raw_player": raw_player,
                        "errors": validation_errors,
                    }
                )
                continue

            action = upsert_player(
                database_session=database_session,
                normalized_player=normalized_player,
            )

            if action == "created":
                report["created"] += 1

            elif action == "updated":
                report["updated"] += 1

            report["players"].append(
                {
                    "mlb_player_id": normalized_player["mlb_player_id"],
                    "full_name": normalized_player["full_name"],
                    "position": normalized_player["position"],
                    "bats": normalized_player["bats"],
                    "throws": normalized_player["throws"],
                    "active_status": normalized_player["active_status"],
                    "action": action,
                }
            )

    report["success"] = (
        report["raw_player_count"] > 0
        and report["database_health"] is True
        and len(report["errors"]) == 0
    )

    report["database_player_count_after_ingestion"] = (
        count_database_players()
    )

    return report


# ============================================================
# SECTION 09 - DATABASE PLAYER COUNT
# ============================================================

def count_database_players() -> int:
    with managed_database_session() as database_session:
        return database_session.query(Player).count()


# ============================================================
# SECTION 10 - PLAYER INVENTORY
# ============================================================

def build_player_inventory(
    limit: int = 250,
) -> list[dict[str, Any]]:
    with managed_database_session() as database_session:
        players = (
            database_session.query(Player)
            .order_by(Player.full_name.asc())
            .limit(limit)
            .all()
        )

        return [
            {
                "mlb_player_id": player.mlb_player_id,
                "full_name": player.full_name,
                "first_name": player.first_name,
                "last_name": player.last_name,
                "position": player.position,
                "position_code": player.position_code,
                "bats": player.bats,
                "throws": player.throws,
                "height": player.height,
                "weight": player.weight,
                "birth_date": player.birth_date,
                "active_status": player.active_status,
            }
            for player in players
        ]


# ============================================================
# SECTION 11 - PLAYER SEARCH
# ============================================================

def search_database_players(
    query: str,
    limit: int = 25,
) -> list[dict[str, Any]]:
    clean_query = query.strip()

    if not clean_query:
        return []

    with managed_database_session() as database_session:
        players = (
            database_session.query(Player)
            .filter(Player.full_name.ilike(f"%{clean_query}%"))
            .order_by(Player.full_name.asc())
            .limit(limit)
            .all()
        )

        return [
            {
                "mlb_player_id": player.mlb_player_id,
                "full_name": player.full_name,
                "name": player.full_name,
                "position": player.position,
                "position_code": player.position_code,
                "bats": player.bats,
                "throws": player.throws,
                "active_status": player.active_status,
            }
            for player in players
        ]


# ============================================================
# SECTION 12 - INGESTION SUMMARY
# ============================================================

def build_player_ingestion_summary(
    report: dict[str, Any],
) -> str:
    return (
        f"{INGESTION_NAME} completed | "
        f"Season: {report['season']} | "
        f"Raw Players: {report['raw_player_count']} | "
        f"Created: {report['created']} | "
        f"Updated: {report['updated']} | "
        f"Skipped: {report['skipped']} | "
        f"Database Players: "
        f"{report['database_player_count_after_ingestion']}"
    )


# ============================================================
# SECTION 13 - LOCAL EXECUTION TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("AISP2 PLAYER INGESTION ENGINE")
    print("=" * 70)

    ingestion_report = ingest_mlb_players()

    print()
    print("Ingestion Summary")
    print(build_player_ingestion_summary(ingestion_report))

    print()
    print("Player Sample")
    for player_record in ingestion_report["players"][:25]:
        print(
            f"{player_record['mlb_player_id']} | "
            f"{player_record['full_name']} | "
            f"{player_record['position']} | "
            f"{player_record['action']}"
        )

    print()
    print("Final Database Player Count")
    print(count_database_players())

    print()
    print("Player ingestion completed.")
    print()


# ============================================================
# SECTION 14 - FUTURE PLAYER INGESTION ROADMAP
# ============================================================

"""
Phase 9.02:
    Connect player ingestion endpoint to main.py.

Phase 9.03:
    Connect roster ingestion.

Phase 9.04:
    Connect player statistics ingestion.

Phase 9.05:
    Add team-player current roster mapping.

Phase 9.06:
    Add player search to database-first chatbot.

Phase 9.07:
    Add player profile cards.

Phase 9.08:
    Add first prediction feature builder.

Phase 9.09:
    Add logistic regression dataset.

Phase 9.10:
    Add first real player outcome probability model.
"""