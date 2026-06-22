# ============================================================
# AISP2 BASEBALL
# PHASE 1.00 PART 1
# ENTERPRISE DATABASE CONNECTION LAYER
# FILE: 01_database/database.py
# PURPOSE: centralized SQLAlchemy database engine, session
# factory, declarative base, database dependency helper,
# direct session helper, health checks, and local SQLite setup
# ============================================================


# ============================================================
# SECTION 01 - IMPORTS
# ============================================================

from __future__ import annotations

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

DATABASE_URL = "sqlite:///aisp2_baseball.db"

IS_SQLITE = DATABASE_URL.startswith(
    "sqlite"
)


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
# SECTION 07 - FASTAPI-STYLE DATABASE DEPENDENCY
# ============================================================

def get_database_session() -> Generator[Session, None, None]:
    """
    Creates a short-lived database session.

    This function is designed to support future FastAPI routes.

    Usage pattern:
        db = Depends(get_database_session)

    Responsibility:
        - Open a database session.
        - Yield that session to the caller.
        - Close the session safely afterward.
    """

    database_session = SessionLocal()

    try:
        yield database_session

    finally:
        database_session.close()


# ============================================================
# SECTION 08 - DIRECT SESSION HELPER
# ============================================================

def create_database_session() -> Session:
    """
    Creates and returns a direct SQLAlchemy session.

    This helper is intended for scripts, loaders, tests,
    ingestion utilities, and command-line workflows.

    Important:
        The caller is responsible for closing the session.
    """

    return SessionLocal()


# ============================================================
# SECTION 09 - MANAGED SESSION HELPER
# ============================================================

@contextmanager
def managed_database_session() -> Generator[Session, None, None]:
    """
    Creates a managed database session.

    This helper automatically:
        - Opens a session.
        - Commits if no error occurs.
        - Rolls back if an error occurs.
        - Closes the session at the end.

    This will be useful for future ingestion scripts.
    """

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
    """
    Verifies that the database engine can execute a simple query.
    """

    try:
        with engine.connect() as connection:
            connection.execute(
                text("SELECT 1")
            )

        return True

    except Exception:
        return False


# ============================================================
# SECTION 11 - DATABASE HEALTH DETAILS
# ============================================================

def database_health_details() -> dict:
    """
    Returns human-readable database health details.

    This will later support:
        - API health routes
        - dashboard status panels
        - deployment checks
        - Render diagnostics
    """

    return {
        "database_url_configured": bool(DATABASE_URL),
        "database_type": "sqlite" if IS_SQLITE else "external",
        "database_url": DATABASE_URL,
        "connection_ok": database_health_check(),
        "engine_echo": ENGINE_OPTIONS.get("echo"),
        "pool_pre_ping": ENGINE_OPTIONS.get("pool_pre_ping"),
    }


# ============================================================
# SECTION 12 - LOCAL FILE EXECUTION TEST
# ============================================================

if __name__ == "__main__":
    print("AISP2 database connection file loaded successfully.")
    print(f"Database URL: {DATABASE_URL}")
    print(f"Database healthy: {database_health_check()}")
    print(database_health_details())


# ============================================================
# SECTION 13 - FUTURE DATABASE ROADMAP
# ============================================================

"""
Future Database Expansion

Phase 1.01:
    Add init_db.py to create all database tables.

Phase 1.02:
    Add Team, Player, and PlayerSeasonStat models.

Phase 1.03:
    Add roster table.

Phase 1.04:
    Add Statcast event table.

Phase 1.05:
    Add game table.

Phase 1.06:
    Add prediction result tables.

Phase 2.00:
    Add PostgreSQL support for Render production.

Phase 3.00:
    Add analytics warehouse support.

Future Database Targets

SQLite:
    Local development and fast iteration.

PostgreSQL:
    Render production database.

DuckDB:
    Analytics warehouse for larger baseball datasets.

Redis:
    Caching, job state, and scheduled ingestion support.

Vector Database:
    Future AI analyst retrieval and player/team context search.
"""