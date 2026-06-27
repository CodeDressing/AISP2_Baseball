# ============================================================
# AISP2 BASEBALL
# PHASE 3.04 PART 1
# ENTERPRISE SCHEDULE INGESTION ENGINE
# FILE: 03_ingestion/schedule_ingestion.py
# PURPOSE: ingest MLB 2026 schedule data into the games table
# for matchup lookup, game-specific predictions, and chatbot
# schedule intelligence
# ============================================================


# ============================================================
# SECTION 01 - IMPORTS
# ============================================================

from __future__ import annotations

import json
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

for path in [PROJECT_ROOT, DATABASE_DIR, DATA_SOURCES_DIR]:
    path_string = str(path)

    if path_string not in sys.path:
        sys.path.insert(0, path_string)


# ============================================================
# SECTION 03 - PROJECT IMPORTS
# ============================================================

from database import managed_database_session
from mlb_stats_api import DEFAULT_SEASON
from mlb_stats_api import MLBStatsAPIClient
from models import Game
from models import Team


# ============================================================
# SECTION 04 - INGESTION CONFIGURATION
# ============================================================

INGESTION_NAME = "AISP2 Schedule Ingestion"
INGESTION_VERSION = "1.0.0"

DEFAULT_SCHEDULE_SEASON = DEFAULT_SEASON


MLB_2026_SCHEDULE_WINDOWS = [
    {
        "label": "april_2026",
        "start_date": "2026-04-01",
        "end_date": "2026-04-30",
    },
    {
        "label": "may_2026",
        "start_date": "2026-05-01",
        "end_date": "2026-05-31",
    },
    {
        "label": "june_2026",
        "start_date": "2026-06-01",
        "end_date": "2026-06-30",
    },
    {
        "label": "july_2026",
        "start_date": "2026-07-01",
        "end_date": "2026-07-31",
    },
    {
        "label": "august_2026",
        "start_date": "2026-08-01",
        "end_date": "2026-08-31",
    },
    {
        "label": "september_2026",
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
    },
]


# ============================================================
# SECTION 05 - SAFE VALUE HELPERS
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
    if value is None:
        return None

    try:
        return int(value)

    except (TypeError, ValueError):
        return None


def is_final_status(status_value: str | None) -> bool:
    if not status_value:
        return False

    return status_value.lower().strip() in {
        "final",
        "game over",
        "completed early",
    }


def is_postponed_status(status_value: str | None) -> bool:
    if not status_value:
        return False

    return "postponed" in status_value.lower().strip()


# ============================================================
# SECTION 06 - TEAM LOOKUP HELPERS
# ============================================================

def get_team_database_id_by_mlb_id(
    database_session,
    mlb_team_id: int | None,
) -> int | None:
    if mlb_team_id is None:
        return None

    team = (
        database_session.query(Team)
        .filter(Team.mlb_team_id == mlb_team_id)
        .first()
    )

    if team is None:
        return None

    return team.id


# ============================================================
# SECTION 07 - SCHEDULE NORMALIZATION
# ============================================================

def normalize_schedule_game(
    raw_game: dict[str, Any],
    season: int,
    database_session,
) -> dict[str, Any]:
    game_pk = safe_integer(raw_game.get("gamePk"))

    home_mlb_team_id = safe_integer(
        safe_nested_get(raw_game, "teams", "home", "team", "id")
    )

    away_mlb_team_id = safe_integer(
        safe_nested_get(raw_game, "teams", "away", "team", "id")
    )

    home_score = safe_integer(
        safe_nested_get(raw_game, "teams", "home", "score")
    )

    away_score = safe_integer(
        safe_nested_get(raw_game, "teams", "away", "score")
    )

    status_description = safe_string(
        safe_nested_get(raw_game, "status", "detailedState")
    )

    abstract_game_state = safe_string(
        safe_nested_get(raw_game, "status", "abstractGameState")
    )

    return {
        "game_pk": game_pk,
        "season": season,
        "game_date": safe_string(raw_game.get("gameDate")),
        "official_date": safe_string(raw_game.get("officialDate")),
        "game_type": safe_string(raw_game.get("gameType")),
        "series_description": safe_string(raw_game.get("seriesDescription")),
        "status_code": safe_string(
            safe_nested_get(raw_game, "status", "statusCode")
        ),
        "status_description": status_description,
        "abstract_game_state": abstract_game_state,
        "coded_game_state": safe_string(
            safe_nested_get(raw_game, "status", "codedGameState")
        ),
        "detailed_state": status_description,
        "venue_name": safe_string(
            safe_nested_get(raw_game, "venue", "name")
        ),
        "home_team_id": get_team_database_id_by_mlb_id(
            database_session=database_session,
            mlb_team_id=home_mlb_team_id,
        ),
        "away_team_id": get_team_database_id_by_mlb_id(
            database_session=database_session,
            mlb_team_id=away_mlb_team_id,
        ),
        "home_mlb_team_id": home_mlb_team_id,
        "away_mlb_team_id": away_mlb_team_id,
        "home_team_name": safe_string(
            safe_nested_get(raw_game, "teams", "home", "team", "name")
        ),
        "away_team_name": safe_string(
            safe_nested_get(raw_game, "teams", "away", "team", "name")
        ),
        "home_score": home_score,
        "away_score": away_score,
        "home_probable_pitcher_id": safe_integer(
            safe_nested_get(raw_game, "teams", "home", "probablePitcher", "id")
        ),
        "away_probable_pitcher_id": safe_integer(
            safe_nested_get(raw_game, "teams", "away", "probablePitcher", "id")
        ),
        "home_probable_pitcher_name": safe_string(
            safe_nested_get(raw_game, "teams", "home", "probablePitcher", "fullName")
        ),
        "away_probable_pitcher_name": safe_string(
            safe_nested_get(raw_game, "teams", "away", "probablePitcher", "fullName")
        ),
        "double_header": safe_string(raw_game.get("doubleHeader")),
        "game_number": safe_integer(raw_game.get("gameNumber")),
        "day_night": safe_string(raw_game.get("dayNight")),
        "scheduled_innings": safe_integer(raw_game.get("scheduledInnings")),
        "is_final": is_final_status(status_description),
        "is_completed": abstract_game_state == "Final",
        "is_postponed": is_postponed_status(status_description),
        "raw_schedule_json": json.dumps(raw_game, ensure_ascii=False),
    }


# ============================================================
# SECTION 08 - SCHEDULE VALIDATION
# ============================================================

def validate_normalized_game(
    normalized_game: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    if not normalized_game.get("game_pk"):
        errors.append("Missing game_pk")

    if not normalized_game.get("season"):
        errors.append("Missing season")

    if not normalized_game.get("home_mlb_team_id"):
        errors.append("Missing home_mlb_team_id")

    if not normalized_game.get("away_mlb_team_id"):
        errors.append("Missing away_mlb_team_id")

    return errors


# ============================================================
# SECTION 09 - GAME UPSERT
# ============================================================

def upsert_game(
    database_session,
    normalized_game: dict[str, Any],
) -> str:
    existing_game = (
        database_session.query(Game)
        .filter(Game.game_pk == normalized_game["game_pk"])
        .first()
    )

    if existing_game is None:
        new_game = Game(**normalized_game)

        database_session.add(new_game)

        return "created"

    for field_name, field_value in normalized_game.items():
        setattr(existing_game, field_name, field_value)

    return "updated"


# ============================================================
# SECTION 10 - SINGLE WINDOW INGESTION
# ============================================================

def ingest_schedule_window(
    season: int = DEFAULT_SCHEDULE_SEASON,
    start_date: str | None = None,
    end_date: str | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    client = MLBStatsAPIClient()

    raw_games = client.get_schedule_games(
        season=season,
        start_date=start_date,
        end_date=end_date,
    )

    report: dict[str, Any] = {
        "ingestion": INGESTION_NAME,
        "version": INGESTION_VERSION,
        "season": season,
        "label": label or "custom_window",
        "start_date": start_date,
        "end_date": end_date,
        "source": "MLB Stats API",
        "raw_game_count": len(raw_games),
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
        "games": [],
    }

    with managed_database_session() as database_session:
        for raw_game in raw_games:
            normalized_game = normalize_schedule_game(
                raw_game=raw_game,
                season=season,
                database_session=database_session,
            )

            validation_errors = validate_normalized_game(
                normalized_game=normalized_game,
            )

            if validation_errors:
                report["skipped"] += 1

                report["errors"].append(
                    {
                        "game_pk": normalized_game.get("game_pk"),
                        "errors": validation_errors,
                    }
                )

                continue

            action = upsert_game(
                database_session=database_session,
                normalized_game=normalized_game,
            )

            if action == "created":
                report["created"] += 1

            elif action == "updated":
                report["updated"] += 1

            report["games"].append(
                {
                    "game_pk": normalized_game["game_pk"],
                    "official_date": normalized_game["official_date"],
                    "away": normalized_game["away_team_name"],
                    "home": normalized_game["home_team_name"],
                    "venue": normalized_game["venue_name"],
                    "status": normalized_game["status_description"],
                    "action": action,
                }
            )

    report["success"] = (
        report["raw_game_count"] > 0
        and len(report["errors"]) == 0
    )

    report["database_game_count_after_ingestion"] = count_database_games()

    return report


# ============================================================
# SECTION 11 - MONTHLY 2026 INGESTION
# ============================================================

def ingest_2026_monthly_schedule() -> dict[str, Any]:
    monthly_reports: list[dict[str, Any]] = []

    total_raw_games = 0
    total_created = 0
    total_updated = 0
    total_skipped = 0
    total_errors: list[dict[str, Any]] = []

    for window in MLB_2026_SCHEDULE_WINDOWS:
        report = ingest_schedule_window(
            season=2026,
            start_date=window["start_date"],
            end_date=window["end_date"],
            label=window["label"],
        )

        monthly_reports.append(report)

        total_raw_games += report["raw_game_count"]
        total_created += report["created"]
        total_updated += report["updated"]
        total_skipped += report["skipped"]
        total_errors.extend(report["errors"])

    return {
        "ingestion": INGESTION_NAME,
        "version": INGESTION_VERSION,
        "mode": "monthly_2026_windows",
        "season": 2026,
        "window_count": len(MLB_2026_SCHEDULE_WINDOWS),
        "raw_game_count": total_raw_games,
        "created": total_created,
        "updated": total_updated,
        "skipped": total_skipped,
        "errors": total_errors,
        "success": len(total_errors) == 0,
        "database_game_count_after_ingestion": count_database_games(),
        "monthly_reports": monthly_reports,
    }


# ============================================================
# SECTION 12 - FULL SEASON INGESTION
# ============================================================

def ingest_full_2026_schedule() -> dict[str, Any]:
    return ingest_schedule_window(
        season=2026,
        start_date=None,
        end_date=None,
        label="full_2026_schedule",
    )


# ============================================================
# SECTION 13 - DATABASE COUNTS AND INVENTORY
# ============================================================

def count_database_games() -> int:
    with managed_database_session() as database_session:
        return database_session.query(Game).count()


def build_game_inventory(
    limit: int = 50,
) -> list[dict[str, Any]]:
    with managed_database_session() as database_session:
        games = (
            database_session.query(Game)
            .order_by(Game.official_date.asc(), Game.game_pk.asc())
            .limit(limit)
            .all()
        )

        return [
            {
                "game_pk": game.game_pk,
                "official_date": game.official_date,
                "away": game.away_team_name,
                "home": game.home_team_name,
                "venue": game.venue_name,
                "status": game.status_description,
            }
            for game in games
        ]


# ============================================================
# SECTION 14 - HUMAN-READABLE SUMMARY
# ============================================================

def build_ingestion_summary(
    report: dict[str, Any],
) -> str:
    return (
        f"{INGESTION_NAME} completed | "
        f"Mode/Label: {report.get('mode') or report.get('label')} | "
        f"Season: {report.get('season')} | "
        f"Raw Games: {report.get('raw_game_count')} | "
        f"Created: {report.get('created')} | "
        f"Updated: {report.get('updated')} | "
        f"Skipped: {report.get('skipped')} | "
        f"Database Games: {report.get('database_game_count_after_ingestion')}"
    )


# ============================================================
# SECTION 15 - LOCAL EXECUTION TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("AISP2 SCHEDULE INGESTION ENGINE")
    print("=" * 70)

    ingestion_report = ingest_2026_monthly_schedule()

    print()
    print("Ingestion Summary")
    print(build_ingestion_summary(ingestion_report))

    print()
    print("Game Inventory Sample")
    for game_record in build_game_inventory(limit=25):
        print(
            f"{game_record['official_date']} | "
            f"{game_record['away']} at {game_record['home']} | "
            f"{game_record['venue']} | "
            f"{game_record['status']}"
        )

    print()
    print("Final Database Game Count")
    print(count_database_games())

    print()
    print("Schedule ingestion completed.")
    print()


# ============================================================
# SECTION 16 - FUTURE INGESTION ROADMAP
# ============================================================

"""
Phase 3.04 Part 2:
    Add CSV export for monthly schedule windows.

Phase 3.04 Part 3:
    Add command-line flags:
        --month april
        --full-season
        --date 2026-04-01

Phase 3.05:
    Add game feed ingestion:
        /game/{gamePk}/feed/live

Phase 3.06:
    Add box score ingestion:
        /game/{gamePk}/boxscore

Phase 3.07:
    Add PlayerGameStat model and ingestion.

Phase 3.08:
    Add TeamGameStat model and ingestion.

Phase 3.09:
    Add chatbot game lookup service.

Phase 3.10:
    Add prediction context builder.
"""