# ============================================================
# AISP2 BASEBALL
# PHASE 6 PART 4
# ENTERPRISE DATABASE INITIALIZATION ENGINE
# FILE: 01_database/init_db.py
# PURPOSE: create database tables, validate schema creation,
# verify AI learning infrastructure, provide startup diagnostics,
# and prepare future migration workflows
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
# SECTION 02 - REGISTERED TABLE GROUPS
# ============================================================

CORE_BASEBALL_TABLES = [
    "teams",
    "players",
    "roster_entries",
    "player_season_stats",
]


AI_MEMORY_TABLES = [
    "chat_memory",
    "learning_signals",
    "training_examples",
    "entity_aliases",
    "user_feedback",
]


REGISTERED_TABLES = [
    *CORE_BASEBALL_TABLES,
    *AI_MEMORY_TABLES,
]


# ============================================================
# SECTION 03 - CREATE DATABASE TABLES
# ============================================================

def create_database_tables() -> None:
    """
    Creates all SQLAlchemy tables registered under Base.
    """

    Base.metadata.create_all(
        bind=engine,
    )


# ============================================================
# SECTION 04 - DROP DATABASE TABLES
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
# SECTION 05 - TABLE DETECTION HELPERS
# ============================================================

def get_metadata_tables() -> list[str]:
    return sorted(
        Base.metadata.tables.keys()
    )


def get_missing_tables(
    expected_tables: list[str],
    detected_tables: list[str],
) -> list[str]:
    return sorted(
        table_name
        for table_name in expected_tables
        if table_name not in detected_tables
    )


def get_detected_tables(
    expected_tables: list[str],
    detected_tables: list[str],
) -> list[str]:
    return sorted(
        table_name
        for table_name in expected_tables
        if table_name in detected_tables
    )


# ============================================================
# SECTION 06 - BUILD SCHEMA REPORT
# ============================================================

def build_schema_report() -> dict:
    """
    Returns a full database schema report for startup diagnostics.
    """

    metadata_tables = get_metadata_tables()

    missing_registered_tables = get_missing_tables(
        expected_tables=REGISTERED_TABLES,
        detected_tables=metadata_tables,
    )

    missing_core_tables = get_missing_tables(
        expected_tables=CORE_BASEBALL_TABLES,
        detected_tables=metadata_tables,
    )

    missing_ai_tables = get_missing_tables(
        expected_tables=AI_MEMORY_TABLES,
        detected_tables=metadata_tables,
    )

    detected_core_tables = get_detected_tables(
        expected_tables=CORE_BASEBALL_TABLES,
        detected_tables=metadata_tables,
    )

    detected_ai_tables = get_detected_tables(
        expected_tables=AI_MEMORY_TABLES,
        detected_tables=metadata_tables,
    )

    return {
        "database_url": str(engine.url),
        "registered_tables": REGISTERED_TABLES,
        "core_baseball_tables": CORE_BASEBALL_TABLES,
        "ai_memory_tables": AI_MEMORY_TABLES,
        "metadata_tables": metadata_tables,
        "registered_table_count": len(REGISTERED_TABLES),
        "metadata_table_count": len(metadata_tables),
        "core_table_count": len(CORE_BASEBALL_TABLES),
        "ai_memory_table_count": len(AI_MEMORY_TABLES),
        "detected_core_tables": detected_core_tables,
        "detected_ai_tables": detected_ai_tables,
        "missing_registered_tables": missing_registered_tables,
        "missing_core_tables": missing_core_tables,
        "missing_ai_tables": missing_ai_tables,
        "all_registered_tables_detected": len(missing_registered_tables) == 0,
        "core_baseball_ready": len(missing_core_tables) == 0,
        "ai_learning_ready": len(missing_ai_tables) == 0,
    }


# ============================================================
# SECTION 07 - INITIALIZE DATABASE
# ============================================================

def initialize_database() -> dict:
    """
    Creates every registered SQLAlchemy table, validates the
    resulting schema, and returns a comprehensive startup report.
    """

    create_database_tables()

    schema_report = build_schema_report()

    return {
        "success": schema_report["all_registered_tables_detected"],
        "operation": "initialize_database",
        "engine": str(engine.url),
        "tables_created_or_verified": len(Base.metadata.tables.keys()),
        "registered_tables": len(REGISTERED_TABLES),
        "metadata_tables": schema_report["metadata_table_count"],
        "core_baseball_ready": schema_report["core_baseball_ready"],
        "ai_learning_ready": schema_report["ai_learning_ready"],
        "missing_tables": schema_report["missing_registered_tables"],
        "schema_report": schema_report,
        "database_health": database_health_details(),
    }


# ============================================================
# SECTION 08 - DATABASE STARTUP CHECK
# ============================================================

def database_startup_check() -> dict:
    """
    Performs a complete startup validation of the database,
    including baseball warehouse readiness and AI learning
    infrastructure readiness.
    """

    schema_report = build_schema_report()

    return {
        "database_initialized": database_health_check(),
        "registered_tables_detected": schema_report[
            "all_registered_tables_detected"
        ],
        "core_baseball_ready": schema_report["core_baseball_ready"],
        "ai_learning_ready": schema_report["ai_learning_ready"],
        "registered_tables": REGISTERED_TABLES,
        "metadata_tables": schema_report["metadata_tables"],
        "table_count": schema_report["metadata_table_count"],
        "missing_registered_tables": schema_report["missing_registered_tables"],
        "missing_core_tables": schema_report["missing_core_tables"],
        "missing_ai_tables": schema_report["missing_ai_tables"],
    }


# ============================================================
# SECTION 09 - AI MEMORY READINESS CHECK
# ============================================================

def ai_memory_startup_check() -> dict:
    """
    Verifies that permanent AI memory tables exist.

    These tables are required before AISP2 can permanently store:
        - every user question
        - every assistant response
        - every NLU report
        - every learning signal
        - every training example
        - every learned alias
        - every user feedback event
    """

    schema_report = build_schema_report()

    return {
        "ai_learning_ready": schema_report["ai_learning_ready"],
        "required_ai_tables": AI_MEMORY_TABLES,
        "detected_ai_tables": schema_report["detected_ai_tables"],
        "missing_ai_tables": schema_report["missing_ai_tables"],
        "ready_for_permanent_chat_memory": (
            "chat_memory" in schema_report["metadata_tables"]
        ),
        "ready_for_learning_signals": (
            "learning_signals" in schema_report["metadata_tables"]
        ),
        "ready_for_training_examples": (
            "training_examples" in schema_report["metadata_tables"]
        ),
        "ready_for_entity_alias_learning": (
            "entity_aliases" in schema_report["metadata_tables"]
        ),
        "ready_for_user_feedback": (
            "user_feedback" in schema_report["metadata_tables"]
        ),
    }


# ============================================================
# SECTION 10 - COMMAND LINE EXECUTION
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("AISP2 DATABASE INITIALIZATION")
    print("=" * 60)

    result = initialize_database()

    print()
    print("Initialization Result")
    print(result)

    print()
    print("Schema Report")
    print(build_schema_report())

    print()
    print("Startup Check")
    print(database_startup_check())

    print()
    print("AI Memory Check")
    print(ai_memory_startup_check())

    print()
    print("Database initialization completed.")
    print()


# ============================================================
# SECTION 11 - FUTURE ROADMAP
# ============================================================

"""
Phase 6.04
    Database initialization upgraded for AI memory readiness.

Phase 6.05
    interaction_memory.py database-backed persistence.

Phase 6.06
    learning_engine.py permanent LearningSignal persistence.

Phase 6.07
    training example export service.

Phase 6.08
    entity alias promotion engine.

Phase 6.09
    semantic embedding table and vector search.

Phase 6.10
    migration system with Alembic.

Long-Term Database Initialization Targets

- create all core baseball warehouse tables
- create all AI memory tables
- validate schema readiness
- validate AI learning readiness
- validate permanent chat storage readiness
- validate training dataset readiness
- report missing tables clearly
- prepare future migrations
- support local SQLite and production PostgreSQL
"""