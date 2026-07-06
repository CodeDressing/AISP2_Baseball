# ============================================================
# AISP2 BASEBALL
# PHASE 8 PART 4
# ENTERPRISE DATABASE CONNECTION LAYER
# FILE: 01_database/database.py
# PURPOSE: centralized SQLAlchemy engine, session factory,
# declarative base, database helpers, health checks, and
# production-safe configuration
# ============================================================


# ============================================================
# SECTION 01 - IMPORTS
# ============================================================

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker


# ============================================================
# SECTION 02 - DATABASE CONFIGURATION
# ============================================================

DEFAULT_DATABASE_URL = "sqlite:///aisp2_baseball.db"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    DEFAULT_DATABASE_URL,
)

IS_SQLITE = DATABASE_URL.startswith("sqlite")


# ============================================================
# SECTION 03 - DATABASE ENGINE OPTIONS
# ============================================================

ENGINE_OPTIONS: dict = {
    "echo": False,
    "future": True,
    "pool_pre_ping": True,
}

if IS_SQLITE:
    ENGINE_OPTIONS["connect_args"] = {
        "check_same_thread": False,
    }


# ============================================================
# SECTION 04 - PRIMARY DATABASE ENGINE
# ============================================================

engine: Engine = create_engine(
    DATABASE_URL,
    **ENGINE_OPTIONS,
)


# ============================================================
# SECTION 05 - SESSION FACTORY
# ============================================================

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


# ============================================================
# SECTION 06 - DECLARATIVE BASE
# ============================================================

Base = declarative_base()


# ============================================================
# SECTION 07 - FASTAPI DATABASE DEPENDENCY
# ============================================================

def get_database_session() -> Generator[Session, None, None]:
    database_session = SessionLocal()

    try:
        yield database_session

    finally:
        database_session.close()


# ============================================================
# SECTION 08 - DIRECT SESSION HELPER
# ============================================================

def create_database_session() -> Session:
    return SessionLocal()


# ============================================================
# SECTION 09 - MANAGED SESSION HELPER
# ============================================================

@contextmanager
def managed_database_session() -> Generator[Session, None, None]:
    database_session = SessionLocal()

    try:
        yield database_session
        database_session.commit()

    except Exception:
        database_session.rollback()
        raise

    finally:
        database_session.close()


# ============================================================
# SECTION 10 - DATABASE HEALTH CHECK
# ============================================================

def database_health_check() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(
                text("SELECT 1"),
            )

        return True

    except Exception:
        return False


# ============================================================
# SECTION 11 - DATABASE HEALTH DETAILS
# ============================================================

def database_health_details() -> dict:
    return {
        "database_url_configured": bool(DATABASE_URL),
        "database_type": "sqlite" if IS_SQLITE else "external",
        "database_url": DATABASE_URL,
        "connection_ok": database_health_check(),
        "engine_echo": ENGINE_OPTIONS.get("echo"),
        "pool_pre_ping": ENGINE_OPTIONS.get("pool_pre_ping"),
    }


# ============================================================
# SECTION 12 - LOCAL EXECUTION TEST
# ============================================================

if __name__ == "__main__":
    print("AISP2 database connection layer loaded successfully.")
    print(f"Database type: {'sqlite' if IS_SQLITE else 'external'}")
    print(f"Database healthy: {database_health_check()}")
    print(database_health_details())

# ============================================================
# SECTION 13 - DATABASE TABLE MANAGEMENT
# PURPOSE: create and inspect database tables for warehouse
# ingestion, team sync, player sync, and prediction data.
# ============================================================

def create_all_database_tables() -> bool:
    try:
        Base.metadata.create_all(
            bind=engine,
        )

        return True

    except Exception:
        return False


def drop_all_database_tables() -> bool:
    try:
        Base.metadata.drop_all(
            bind=engine,
        )

        return True

    except Exception:
        return False


def get_database_table_names() -> list[str]:
    try:
        with engine.connect() as connection:
            if IS_SQLITE:
                result = connection.execute(
                    text(
                        "SELECT name FROM sqlite_master "
                        "WHERE type='table' "
                        "ORDER BY name"
                    )
                )

                return [
                    row[0]
                    for row in result.fetchall()
                ]

            result = connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public' "
                    "ORDER BY table_name"
                )
            )

            return [
                row[0]
                for row in result.fetchall()
            ]

    except Exception:
        return []


# ============================================================
# SECTION 14 - ENTERPRISE DATABASE WAREHOUSE STATUS
# FILE: 01_database/database.py
# PURPOSE: inspect whether the AISP2 warehouse has the actual
# tables needed for teams, players, rosters, schedules, Statcast
# data, chat memory, learning, and prediction-readiness.
# ============================================================

def database_warehouse_status() -> dict:
    table_names = get_database_table_names()

    table_set = set(table_names)

    required_core_tables = [
        "teams",
        "players",
        "roster_entries",
        "games",
    ]

    required_stat_tables = [
        "player_season_stats",
        "player_advanced_batting_stats",
        "player_percentile_rankings",
        "player_pitch_arsenals",
        "player_pitch_tempo",
        "player_batted_ball_profiles",
        "player_batting_stances",
        "player_home_run_profiles",
        "team_plate_discipline",
    ]

    required_learning_tables = [
        "chat_memory",
        "learning_signals",
        "training_examples",
        "entity_aliases",
        "user_feedback",
    ]

    required_audit_tables = [
        "raw_data_import_logs",
    ]

    all_required_tables = (
        required_core_tables
        + required_stat_tables
        + required_learning_tables
        + required_audit_tables
    )

    missing_tables = [
        table_name
        for table_name in all_required_tables
        if table_name not in table_set
    ]

    present_required_tables = [
        table_name
        for table_name in all_required_tables
        if table_name in table_set
    ]

    core_ready = all(
        table_name in table_set
        for table_name in required_core_tables
    )

    stats_ready = all(
        table_name in table_set
        for table_name in required_stat_tables
    )

    learning_ready = all(
        table_name in table_set
        for table_name in required_learning_tables
    )

    audit_ready = all(
        table_name in table_set
        for table_name in required_audit_tables
    )

    prediction_ready = (
        core_ready
        and stats_ready
        and audit_ready
    )

    warehouse_score = 0

    if core_ready:
        warehouse_score += 30

    if stats_ready:
        warehouse_score += 40

    if learning_ready:
        warehouse_score += 20

    if audit_ready:
        warehouse_score += 10

    return {
        "database_connected": database_health_check(),
        "database_type": "sqlite" if IS_SQLITE else "external",
        "database_url_configured": bool(DATABASE_URL),
        "tables_created": len(table_names),
        "tables": table_names,
        "required_table_count": len(all_required_tables),
        "present_required_table_count": len(present_required_tables),
        "missing_required_table_count": len(missing_tables),
        "present_required_tables": present_required_tables,
        "missing_required_tables": missing_tables,
        "core_ready": core_ready,
        "stats_ready": stats_ready,
        "learning_ready": learning_ready,
        "audit_ready": audit_ready,
        "warehouse_ready": len(missing_tables) == 0,
        "prediction_ready": prediction_ready,
        "warehouse_score": warehouse_score,
        "required_core_tables": required_core_tables,
        "required_stat_tables": required_stat_tables,
        "required_learning_tables": required_learning_tables,
        "required_audit_tables": required_audit_tables,
        "next_required_action": (
            "Warehouse tables are present. Next step is importing and validating rows."
            if len(missing_tables) == 0
            else "Run database initialization so missing warehouse tables are created."
        ),
    }
# ============================================================
# SECTION 15 - DATABASE INITIALIZATION ENTRYPOINT
# PURPOSE: one command used by scripts, Render, and local dev
# to initialize the AISP2 warehouse schema.
# ============================================================

def initialize_database() -> dict:
    created = create_all_database_tables()

    return {
        "initialized": created,
        "health": database_health_check(),
        "warehouse": database_warehouse_status(),
    }