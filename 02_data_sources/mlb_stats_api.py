# ============================================================
# AISP2 BASEBALL
# PHASE 1.00 PART 5
# ENTERPRISE DATABASE INITIALIZATION ENGINE
# FILE: 01_database/init_db.py
# PURPOSE: create database tables, validate schema creation,
# provide startup diagnostics, and prepare future migrations
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
# SECTION 02 - REGISTERED TABLES
# ============================================================

REGISTERED_TABLES = [
    "teams",
    "players",
    "roster_entries",
    "player_season_stats",
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
# SECTION 05 - BUILD SCHEMA REPORT
# ============================================================

def build_schema_report() -> dict:
    """
    Returns a human-readable database schema report.
    """

    metadata_tables = sorted(
        Base.metadata.tables.keys()
    )

    return {
        "database_url": str(engine.url),
        "registered_tables": REGISTERED_TABLES,
        "metadata_tables": metadata_tables,
        "registered_table_count": len(REGISTERED_TABLES),
        "metadata_table_count": len(metadata_tables),
        "all_registered_tables_detected": all(
            table_name in metadata_tables
            for table_name in REGISTERED_TABLES
        ),
    }


# ============================================================
# SECTION 06 - INITIALIZE DATABASE
# ============================================================

def initialize_database() -> dict:
    """
    Creates all database tables and returns a status report.
    """

    create_database_tables()

    return {
        "success": True,
        "operation": "initialize_database",
        "tables_created_or_verified": len(Base.metadata.tables.keys()),
        "schema_report": build_schema_report(),
        "database_health": database_health_details(),
    }


# ============================================================
# SECTION 07 - DATABASE STARTUP CHECK
# ============================================================

def database_startup_check() -> dict:
    """
    Verifies database readiness after initialization.
    """

    schema_report = build_schema_report()

    return {
        "database_initialized": database_health_check(),
        "registered_tables_detected": schema_report[
            "all_registered_tables_detected"
        ],
        "registered_tables": REGISTERED_TABLES,
        "metadata_tables": schema_report["metadata_tables"],
        "table_count": schema_report["metadata_table_count"],
    }


# ============================================================
# SECTION 08 - COMMAND LINE EXECUTION
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
    print("Database initialization completed.")
    print()


# ============================================================
# SECTION 09 - FUTURE ROADMAP
# ============================================================

"""
Phase 1.01
    Team ingestion

Phase 1.02
    Player ingestion

Phase 1.03
    Roster ingestion

Phase 1.04
    Team statistics

Phase 1.05
    Player statistics

Phase 1.06
    Statcast ingestion

Phase 2.00
    PostgreSQL migration

Phase 3.00
    Warehouse architecture

Phase 4.00
    Feature engineering layer

Phase 5.00
    Machine learning feature store
"""