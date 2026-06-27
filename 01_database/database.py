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