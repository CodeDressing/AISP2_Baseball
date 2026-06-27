# ============================================================
# AISP2 BASEBALL
# PHASE 1.01 PART 2
# ENTERPRISE DATABASE INITIALIZATION ENGINE
# FILE: 01_database/init_db.py
# PURPOSE: create database tables, validate schema readiness,
# prepare schedule/game ingestion, and support future MLB
# prediction data expansion
# ============================================================


# ============================================================
# SECTION 01 - IMPORTS
# ============================================================

from __future__ import annotations

from database import Base
from database import database_health_check
from database import database_health_details
from database import engine

import models


# ============================================================
# SECTION 02 - ENTERPRISE DATABASE TABLE REGISTRY
# ============================================================

CORE_BASEBALL_TABLES = [
    "teams",
    "players",
    "roster_entries",
    "player_season_stats",
    "games",
]


AI_MEMORY_TABLES = [
    "chat_memory",
    "learning_signals",
    "training_examples",
    "entity_aliases",
    "user_feedback",
]


STATCAST_WAREHOUSE_TABLES = [
    "player_advanced_batting_stats",
    "player_percentile_rankings",
    "player_pitch_arsenals",
    "player_pitch_tempo",
    "player_batted_ball_profiles",
    "player_batting_stances",
    "player_home_run_profiles",
    "team_plate_discipline",
    "raw_data_import_logs",
]


SCHEDULE_READY_TABLES = [
    "teams",
    "games",
]


PLAYER_READY_TABLES = [
    "teams",
    "players",
    "roster_entries",
    "player_season_stats",
]


PREDICTION_FOUNDATION_TABLES = [
    "teams",
    "players",
    "roster_entries",
    "player_season_stats",
    "games",
    "player_advanced_batting_stats",
    "player_percentile_rankings",
    "player_pitch_arsenals",
    "player_pitch_tempo",
    "player_batted_ball_profiles",
    "player_batting_stances",
    "player_home_run_profiles",
    "team_plate_discipline",
]


CHATBOT_READY_TABLES = [
    "teams",
    "players",
    "roster_entries",
    "player_season_stats",
    "player_advanced_batting_stats",
    "player_percentile_rankings",
    "player_pitch_arsenals",
    "player_pitch_tempo",
    "player_batted_ball_profiles",
    "player_home_run_profiles",
    "team_plate_discipline",
    "chat_memory",
    "learning_signals",
    "training_examples",
    "entity_aliases",
]


REGISTERED_TABLES = [
    *CORE_BASEBALL_TABLES,
    *AI_MEMORY_TABLES,
    *STATCAST_WAREHOUSE_TABLES,
]
# ============================================================
# SECTION 03 - SCHEDULE INGESTION WINDOWS
# ============================================================

MLB_2026_SCHEDULE_WINDOWS = [
    {
        "label": "entire_2026_regular_season",
        "season": 2026,
        "start_date": None,
        "end_date": None,
        "endpoint": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&season=2026",
    },
    {
        "label": "april_2026",
        "season": 2026,
        "start_date": "2026-04-01",
        "end_date": "2026-04-30",
        "endpoint": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&season=2026&startDate=2026-04-01&endDate=2026-04-30",
    },
    {
        "label": "may_2026",
        "season": 2026,
        "start_date": "2026-05-01",
        "end_date": "2026-05-31",
        "endpoint": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&season=2026&startDate=2026-05-01&endDate=2026-05-31",
    },
    {
        "label": "june_2026",
        "season": 2026,
        "start_date": "2026-06-01",
        "end_date": "2026-06-30",
        "endpoint": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&season=2026&startDate=2026-06-01&endDate=2026-06-30",
    },
    {
        "label": "july_2026",
        "season": 2026,
        "start_date": "2026-07-01",
        "end_date": "2026-07-31",
        "endpoint": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&season=2026&startDate=2026-07-01&endDate=2026-07-31",
    },
    {
        "label": "august_2026",
        "season": 2026,
        "start_date": "2026-08-01",
        "end_date": "2026-08-31",
        "endpoint": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&season=2026&startDate=2026-08-01&endDate=2026-08-31",
    },
    {
        "label": "september_2026",
        "season": 2026,
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
        "endpoint": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&season=2026&startDate=2026-09-01&endDate=2026-09-30",
    },
]


# ============================================================
# SECTION 04 - CREATE DATABASE TABLES
# ============================================================

def create_database_tables() -> None:
    """
    Creates all SQLAlchemy tables registered under Base.
    """

    Base.metadata.create_all(
        bind=engine,
    )


# ============================================================
# SECTION 05 - DROP DATABASE TABLES
# ============================================================

def drop_database_tables() -> None:
    """
    Drops all SQLAlchemy tables registered under Base.

    Development use only.
    """

    Base.metadata.drop_all(
        bind=engine,
    )


# ============================================================
# SECTION 06 - TABLE DETECTION HELPERS
# ============================================================

def get_metadata_tables() -> list[str]:
    """
    Returns all SQLAlchemy metadata table names currently
    registered by imported model classes.
    """

    return sorted(
        Base.metadata.tables.keys()
    )


def get_missing_tables(
    expected_tables: list[str],
    detected_tables: list[str],
) -> list[str]:
    """
    Returns expected tables that are not detected.
    """

    return sorted(
        table_name
        for table_name in expected_tables
        if table_name not in detected_tables
    )


def get_detected_tables(
    expected_tables: list[str],
    detected_tables: list[str],
) -> list[str]:
    """
    Returns expected tables that are detected.
    """

    return sorted(
        table_name
        for table_name in expected_tables
        if table_name in detected_tables
    )


# ============================================================
# SECTION 07 - SCHEMA READINESS REPORT
# ============================================================

def build_schema_report() -> dict:
    """
    Returns database schema readiness information.

    Important:
        This checks SQLAlchemy registered models, not row counts.
    """

    metadata_tables = get_metadata_tables()

    missing_core_tables = get_missing_tables(CORE_BASEBALL_TABLES, metadata_tables)
    missing_schedule_tables = get_missing_tables(SCHEDULE_READY_TABLES, metadata_tables)
    missing_player_tables = get_missing_tables(PLAYER_READY_TABLES, metadata_tables)
    missing_prediction_tables = get_missing_tables(PREDICTION_FOUNDATION_TABLES, metadata_tables)
    missing_ai_memory_tables = get_missing_tables(AI_MEMORY_TABLES, metadata_tables)
    missing_statcast_tables = get_missing_tables(STATCAST_WAREHOUSE_TABLES, metadata_tables)
    missing_chatbot_tables = get_missing_tables(CHATBOT_READY_TABLES, metadata_tables)

    return {
        "database_url": str(engine.url),
        "metadata_tables": metadata_tables,
        "registered_tables": REGISTERED_TABLES,

        "core_baseball_tables": CORE_BASEBALL_TABLES,
        "ai_memory_tables": AI_MEMORY_TABLES,
        "statcast_warehouse_tables": STATCAST_WAREHOUSE_TABLES,
        "schedule_ready_tables": SCHEDULE_READY_TABLES,
        "player_ready_tables": PLAYER_READY_TABLES,
        "prediction_foundation_tables": PREDICTION_FOUNDATION_TABLES,
        "chatbot_ready_tables": CHATBOT_READY_TABLES,

        "metadata_table_count": len(metadata_tables),
        "registered_table_count": len(REGISTERED_TABLES),

        "detected_core_tables": get_detected_tables(CORE_BASEBALL_TABLES, metadata_tables),
        "detected_ai_memory_tables": get_detected_tables(AI_MEMORY_TABLES, metadata_tables),
        "detected_statcast_tables": get_detected_tables(STATCAST_WAREHOUSE_TABLES, metadata_tables),
        "detected_schedule_tables": get_detected_tables(SCHEDULE_READY_TABLES, metadata_tables),
        "detected_player_tables": get_detected_tables(PLAYER_READY_TABLES, metadata_tables),
        "detected_prediction_tables": get_detected_tables(PREDICTION_FOUNDATION_TABLES, metadata_tables),
        "detected_chatbot_tables": get_detected_tables(CHATBOT_READY_TABLES, metadata_tables),

        "missing_core_tables": missing_core_tables,
        "missing_ai_memory_tables": missing_ai_memory_tables,
        "missing_statcast_tables": missing_statcast_tables,
        "missing_schedule_tables": missing_schedule_tables,
        "missing_player_tables": missing_player_tables,
        "missing_prediction_tables": missing_prediction_tables,
        "missing_chatbot_tables": missing_chatbot_tables,

        "core_baseball_ready": len(missing_core_tables) == 0,
        "ai_memory_ready": len(missing_ai_memory_tables) == 0,
        "statcast_warehouse_ready": len(missing_statcast_tables) == 0,
        "schedule_ingestion_ready": len(missing_schedule_tables) == 0,
        "player_ingestion_ready": len(missing_player_tables) == 0,
        "prediction_foundation_ready": len(missing_prediction_tables) == 0,
        "chatbot_data_ready": len(missing_chatbot_tables) == 0,
    }
# ============================================================
# SECTION 08 - SCHEDULE PLAN REPORT
# ============================================================

def build_schedule_ingestion_plan() -> dict:
    """
    Returns the schedule ingestion plan for the 2026 MLB season.
    """

    monthly_windows = [
        window
        for window in MLB_2026_SCHEDULE_WINDOWS
        if window["start_date"] is not None
    ]

    entire_season_window = [
        window
        for window in MLB_2026_SCHEDULE_WINDOWS
        if window["start_date"] is None
    ]

    return {
        "season": 2026,
        "source": "MLB Stats API",
        "target_table": "games",
        "primary_key": "game_pk",
        "recommended_ingestion_mode": "monthly_windows_first",
        "why_monthly_first": (
            "Monthly ingestion is easier to debug, easier to retry, "
            "and safer before loading the entire season at once."
        ),
        "entire_season_window": entire_season_window,
        "monthly_windows": monthly_windows,
        "window_count": len(MLB_2026_SCHEDULE_WINDOWS),
        "monthly_window_count": len(monthly_windows),
        "requires_tables": SCHEDULE_READY_TABLES,
        "future_downstream_endpoints": [
            "/game/{gamePk}/feed/live",
            "/game/{gamePk}/boxscore",
            "/game/{gamePk}/linescore",
        ],
        "future_prediction_uses": [
            "team matchup lookup",
            "specific game prediction",
            "specific player in specific game prediction",
            "probable pitcher context",
            "completed-game stat ingestion",
            "chatbot game intent routing",
        ],
    }


# ============================================================
# SECTION 09 - INITIALIZE DATABASE
# ============================================================

def initialize_database() -> dict:
    """
    Creates all registered database tables and returns a startup
    report for baseball, AI memory, Statcast warehouse, chatbot,
    schedule, player, and prediction readiness.
    """

    create_database_tables()

    schema_report = build_schema_report()

    return {
        "success": (
            schema_report["core_baseball_ready"]
            and schema_report["ai_memory_ready"]
            and schema_report["statcast_warehouse_ready"]
        ),
        "operation": "initialize_database",
        "engine": str(engine.url),
        "tables_created_or_verified": schema_report["metadata_table_count"],

        "core_baseball_ready": schema_report["core_baseball_ready"],
        "ai_memory_ready": schema_report["ai_memory_ready"],
        "statcast_warehouse_ready": schema_report["statcast_warehouse_ready"],
        "schedule_ingestion_ready": schema_report["schedule_ingestion_ready"],
        "player_ingestion_ready": schema_report["player_ingestion_ready"],
        "prediction_foundation_ready": schema_report["prediction_foundation_ready"],
        "chatbot_data_ready": schema_report["chatbot_data_ready"],

        "missing_core_tables": schema_report["missing_core_tables"],
        "missing_ai_memory_tables": schema_report["missing_ai_memory_tables"],
        "missing_statcast_tables": schema_report["missing_statcast_tables"],
        "missing_schedule_tables": schema_report["missing_schedule_tables"],
        "missing_player_tables": schema_report["missing_player_tables"],
        "missing_prediction_tables": schema_report["missing_prediction_tables"],
        "missing_chatbot_tables": schema_report["missing_chatbot_tables"],

        "schema_report": schema_report,
        "schedule_ingestion_plan": build_schedule_ingestion_plan(),
        "database_health": database_health_details(),
    }
# ============================================================
# SECTION 10 - DATABASE STARTUP CHECK
# ============================================================

def database_startup_check() -> dict:
    """
    Performs startup validation without creating or dropping tables.
    """

    schema_report = build_schema_report()

    return {
        "database_initialized": database_health_check(),
        "metadata_tables": schema_report["metadata_tables"],
        "table_count": schema_report["metadata_table_count"],

        "core_baseball_ready": schema_report["core_baseball_ready"],
        "ai_memory_ready": schema_report["ai_memory_ready"],
        "statcast_warehouse_ready": schema_report["statcast_warehouse_ready"],
        "schedule_ingestion_ready": schema_report["schedule_ingestion_ready"],
        "player_ingestion_ready": schema_report["player_ingestion_ready"],
        "prediction_foundation_ready": schema_report["prediction_foundation_ready"],
        "chatbot_data_ready": schema_report["chatbot_data_ready"],

        "missing_core_tables": schema_report["missing_core_tables"],
        "missing_ai_memory_tables": schema_report["missing_ai_memory_tables"],
        "missing_statcast_tables": schema_report["missing_statcast_tables"],
        "missing_schedule_tables": schema_report["missing_schedule_tables"],
        "missing_player_tables": schema_report["missing_player_tables"],
        "missing_prediction_tables": schema_report["missing_prediction_tables"],
        "missing_chatbot_tables": schema_report["missing_chatbot_tables"],
    }
# ============================================================
# SECTION 11 - HUMAN-READABLE STARTUP SUMMARY
# ============================================================

def build_startup_summary() -> str:
    """
    Returns a short readable startup summary for terminal logs.
    """

    startup_report = database_startup_check()

    return (
        "AISP2 Database Startup | "
        f"Tables: {startup_report['table_count']} | "
        f"Core Ready: {startup_report['core_baseball_ready']} | "
        f"AI Memory Ready: {startup_report['ai_memory_ready']} | "
        f"Statcast Ready: {startup_report['statcast_warehouse_ready']} | "
        f"Schedule Ready: {startup_report['schedule_ingestion_ready']} | "
        f"Players Ready: {startup_report['player_ingestion_ready']} | "
        f"Prediction Ready: {startup_report['prediction_foundation_ready']} | "
        f"Chatbot Data Ready: {startup_report['chatbot_data_ready']}"
    )
# ============================================================
# SECTION 12 - COMMAND LINE EXECUTION
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("AISP2 DATABASE INITIALIZATION")
    print("=" * 70)

    result = initialize_database()

    print()
    print("Initialization Result")
    print(result)

    print()
    print("Startup Summary")
    print(build_startup_summary())

    print()
    print("Schema Report")
    print(build_schema_report())

    print()
    print("Schedule Ingestion Plan")
    print(build_schedule_ingestion_plan())

    print()
    print("Startup Check")
    print(database_startup_check())

    print()
    print("Database initialization completed.")
    print()


# ============================================================
# SECTION 13 - FUTURE ROADMAP
# ============================================================

"""
Immediate Next Step

Phase 3.04 Part 1:
    Create 03_ingestion/schedule_ingestion.py.

Phase 3.04 Part 2:
    Ingest monthly schedule windows:
        - April 2026
        - May 2026
        - June 2026
        - July 2026
        - August 2026
        - September 2026

Phase 3.04 Part 3:
    Add entire-season ingestion mode after monthly mode is verified.

Phase 3.04 Part 4:
    Upsert every game into the games table by game_pk.

Phase 3.05:
    Add completed-game detail ingestion:
        - /game/{gamePk}/feed/live
        - /game/{gamePk}/boxscore
        - /game/{gamePk}/linescore

Phase 3.06:
    Add PlayerGameStat table.

Phase 3.07:
    Add TeamGameStat table.

Phase 3.08:
    Add chatbot game lookup service.

Phase 3.09:
    Add prediction-ready matchup resolver.

Phase 3.10:
    Add player-in-game prediction context builder.

Long-Term Database Initialization Targets

- create all core baseball warehouse tables
- create schedule and game lookup tables
- validate prediction foundation readiness
- validate permanent game_pk lookup readiness
- prepare game feed ingestion
- prepare box score ingestion
- prepare player game stat ingestion
- prepare team game stat ingestion
- support local SQLite and production PostgreSQL
- support future Alembic migrations
"""