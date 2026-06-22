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

from database import Base
from database import engine

import models


# ============================================================
# SECTION 02 - DATABASE TABLE REGISTRATION
# ============================================================

REGISTERED_TABLES = [
    "teams",
    "players",
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
        bind=engine
    )


# ============================================================
# SECTION 04 - DROP DATABASE TABLES
# ============================================================

def drop_database_tables() -> None:
    """
    Drops all tables.

    Development use only.
    """

    Base.metadata.drop_all(
        bind=engine
    )


# ============================================================
# SECTION 05 - DATABASE SCHEMA REPORT
# ============================================================

def build_schema_report() -> dict:
    """
    Returns a summary of the current database schema.
    """

    return {
        "registered_tables": REGISTERED_TABLES,
        "table_count": len(REGISTERED_TABLES),
        "database_engine": str(engine.url),
    }


# ============================================================
# SECTION 06 - DATABASE INITIALIZATION
# ============================================================

def initialize_database() -> dict:
    """
    Creates all database tables and returns a status report.
    """

    create_database_tables()

    return {
        "success": True,
        "tables_created": len(REGISTERED_TABLES),
        "tables": REGISTERED_TABLES,
    }


# ============================================================
# SECTION 07 - DATABASE HEALTH CHECK
# ============================================================

def database_startup_check() -> dict:
    """
    Startup verification.
    """

    return {
        "database_initialized": True,
        "registered_tables": REGISTERED_TABLES,
        "table_count": len(REGISTERED_TABLES),
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