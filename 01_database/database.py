# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# PHASE 11 PART 3.0
# FILE: 01_database/database.py
# PURPOSE:
# Enterprise SQLAlchemy database access, transaction safety,
# warehouse inventory, health checks, freshness diagnostics,
# and Player Explorer database readiness for SQLite and
# PostgreSQL deployments.
# ============================================================

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from collections.abc import Generator
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import asdict
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from enum import Enum
import logging
import os
import re
import threading
import time
from typing import Any
from typing import Final
from urllib.parse import urlsplit
from urllib.parse import urlunsplit


# ============================================================
# SECTION 02 - SQLALCHEMY IMPORTS
# ============================================================

from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# ============================================================
# SECTION 03 - MODULE METADATA
# ============================================================

DATABASE_MODULE_NAME: Final[str] = (
    "AISP2 Enterprise Database Access Layer"
)
DATABASE_MODULE_VERSION: Final[str] = "6.0.0"
DATABASE_MODULE_PHASE: Final[str] = "Phase 11 Part 3.0"
DATABASE_MODULE_PATH: Final[str] = "01_database/database.py"
DATABASE_MODULE_STATUS: Final[str] = "enterprise_ready"
DATABASE_SCHEMA_VERSION: Final[str] = "4.0.0"

DEFAULT_DATABASE_FILENAME: Final[str] = "aisp2_baseball.db"
DEFAULT_DATABASE_URL: Final[str] = (
    f"sqlite:///{DEFAULT_DATABASE_FILENAME}"
)

DEFAULT_POOL_SIZE: Final[int] = 5
DEFAULT_MAX_OVERFLOW: Final[int] = 10
DEFAULT_POOL_TIMEOUT_SECONDS: Final[int] = 30
DEFAULT_POOL_RECYCLE_SECONDS: Final[int] = 1800
DEFAULT_CONNECT_TIMEOUT_SECONDS: Final[int] = 15
DEFAULT_SQLITE_BUSY_TIMEOUT_MS: Final[int] = 30000

DEFAULT_STALE_AFTER_HOURS: Final[int] = 36
DEFAULT_CRITICAL_STALE_AFTER_HOURS: Final[int] = 96

DATABASE_HEALTH_QUERY: Final[str] = "SELECT 1"

LOGGER = logging.getLogger("aisp2.database")


# ============================================================
# SECTION 04 - ENUMERATIONS
# ============================================================

class DatabaseBackend(str, Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    OTHER = "other"
    UNKNOWN = "unknown"


class DatabaseHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    MISCONFIGURED = "misconfigured"


class DataFreshnessStatus(str, Enum):
    CURRENT = "current"
    STALE = "stale"
    CRITICAL = "critical"
    EMPTY = "empty"
    UNKNOWN = "unknown"
    TABLE_MISSING = "table_missing"


class TransactionStatus(str, Enum):
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


# ============================================================
# SECTION 05 - SETTINGS
# ============================================================

TRUE_VALUES: Final[frozenset[str]] = frozenset({
    "1",
    "true",
    "yes",
    "y",
    "on",
    "enabled",
})


def environment_bool(
    name: str,
    default: bool,
) -> bool:
    raw = os.getenv(name)

    if raw is None:
        return default

    return raw.strip().lower() in TRUE_VALUES


def environment_int(
    name: str,
    default: int,
) -> int:
    raw = os.getenv(name)

    if raw is None:
        return default

    try:
        return int(raw)

    except (TypeError, ValueError):
        LOGGER.warning(
            "Invalid integer environment value %s=%r; "
            "using %s",
            name,
            raw,
            default,
        )
        return default


def normalize_database_url(
    value: str | None,
) -> str:
    candidate = (
        str(value).strip()
        if value
        else DEFAULT_DATABASE_URL
    )

    if candidate.startswith("postgres://"):
        return (
            "postgresql+psycopg://"
            + candidate[len("postgres://"):]
        )

    if candidate.startswith("postgresql://"):
        return (
            "postgresql+psycopg://"
            + candidate[len("postgresql://"):]
        )

    return candidate


def detect_database_backend(
    database_url: str,
) -> DatabaseBackend:
    lowered = database_url.lower()

    if lowered.startswith("sqlite"):
        return DatabaseBackend.SQLITE

    if lowered.startswith(("postgresql", "postgres")):
        return DatabaseBackend.POSTGRESQL

    if lowered.startswith(("mysql", "mariadb")):
        return DatabaseBackend.MYSQL

    if "://" in lowered:
        return DatabaseBackend.OTHER

    return DatabaseBackend.UNKNOWN


def redact_database_url(
    database_url: str,
) -> str:
    if database_url.startswith("sqlite"):
        return database_url

    try:
        parts = urlsplit(database_url)
        hostname = parts.hostname or ""
        port = f":{parts.port}" if parts.port else ""
        username = (
            f"{parts.username}:***@"
            if parts.username
            else ""
        )

        return urlunsplit(
            (
                parts.scheme,
                f"{username}{hostname}{port}",
                parts.path,
                parts.query,
                parts.fragment,
            )
        )

    except Exception:
        return "<redacted-database-url>"


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    database_url: str
    backend: DatabaseBackend

    echo: bool = False
    pool_pre_ping: bool = True
    future: bool = True

    pool_size: int = DEFAULT_POOL_SIZE
    max_overflow: int = DEFAULT_MAX_OVERFLOW
    pool_timeout_seconds: int = DEFAULT_POOL_TIMEOUT_SECONDS
    pool_recycle_seconds: int = DEFAULT_POOL_RECYCLE_SECONDS
    connect_timeout_seconds: int = DEFAULT_CONNECT_TIMEOUT_SECONDS

    sqlite_busy_timeout_ms: int = DEFAULT_SQLITE_BUSY_TIMEOUT_MS
    sqlite_foreign_keys: bool = True
    sqlite_wal_mode: bool = True

    expire_on_commit: bool = False
    autoflush: bool = False
    autocommit: bool = False

    stale_after_hours: int = DEFAULT_STALE_AFTER_HOURS
    critical_stale_after_hours: int = (
        DEFAULT_CRITICAL_STALE_AFTER_HOURS
    )

    def validate(self) -> None:
        if not self.database_url:
            raise ValueError(
                "database_url cannot be empty"
            )

        for field_name in (
            "pool_size",
            "max_overflow",
            "pool_timeout_seconds",
            "pool_recycle_seconds",
            "connect_timeout_seconds",
            "sqlite_busy_timeout_ms",
            "stale_after_hours",
            "critical_stale_after_hours",
        ):
            if int(getattr(self, field_name)) < 0:
                raise ValueError(
                    f"{field_name} cannot be negative"
                )

        if (
            self.critical_stale_after_hours
            < self.stale_after_hours
        ):
            raise ValueError(
                "critical_stale_after_hours must not be "
                "less than stale_after_hours"
            )


def load_database_settings() -> DatabaseSettings:
    database_url = normalize_database_url(
        os.getenv(
            "DATABASE_URL",
            DEFAULT_DATABASE_URL,
        )
    )

    settings = DatabaseSettings(
        database_url=database_url,
        backend=detect_database_backend(
            database_url
        ),
        echo=environment_bool(
            "DATABASE_ECHO",
            False,
        ),
        pool_pre_ping=environment_bool(
            "DATABASE_POOL_PRE_PING",
            True,
        ),
        pool_size=environment_int(
            "DATABASE_POOL_SIZE",
            DEFAULT_POOL_SIZE,
        ),
        max_overflow=environment_int(
            "DATABASE_MAX_OVERFLOW",
            DEFAULT_MAX_OVERFLOW,
        ),
        pool_timeout_seconds=environment_int(
            "DATABASE_POOL_TIMEOUT_SECONDS",
            DEFAULT_POOL_TIMEOUT_SECONDS,
        ),
        pool_recycle_seconds=environment_int(
            "DATABASE_POOL_RECYCLE_SECONDS",
            DEFAULT_POOL_RECYCLE_SECONDS,
        ),
        connect_timeout_seconds=environment_int(
            "DATABASE_CONNECT_TIMEOUT_SECONDS",
            DEFAULT_CONNECT_TIMEOUT_SECONDS,
        ),
        sqlite_busy_timeout_ms=environment_int(
            "SQLITE_BUSY_TIMEOUT_MS",
            DEFAULT_SQLITE_BUSY_TIMEOUT_MS,
        ),
        sqlite_foreign_keys=environment_bool(
            "SQLITE_FOREIGN_KEYS",
            True,
        ),
        sqlite_wal_mode=environment_bool(
            "SQLITE_WAL_MODE",
            True,
        ),
        expire_on_commit=environment_bool(
            "DATABASE_EXPIRE_ON_COMMIT",
            False,
        ),
        stale_after_hours=environment_int(
            "DATABASE_STALE_AFTER_HOURS",
            DEFAULT_STALE_AFTER_HOURS,
        ),
        critical_stale_after_hours=environment_int(
            "DATABASE_CRITICAL_STALE_AFTER_HOURS",
            DEFAULT_CRITICAL_STALE_AFTER_HOURS,
        ),
    )

    settings.validate()

    return settings


DATABASE_SETTINGS: Final[
    DatabaseSettings
] = load_database_settings()

DATABASE_URL: Final[str] = (
    DATABASE_SETTINGS.database_url
)

DATABASE_BACKEND: Final[
    DatabaseBackend
] = DATABASE_SETTINGS.backend

IS_SQLITE: Final[bool] = (
    DATABASE_BACKEND
    == DatabaseBackend.SQLITE
)

IS_POSTGRESQL: Final[bool] = (
    DATABASE_BACKEND
    == DatabaseBackend.POSTGRESQL
)


# ============================================================
# SECTION 06 - ENGINE CREATION
# ============================================================

def build_engine_options(
    settings: DatabaseSettings,
) -> dict[str, Any]:
    options: dict[str, Any] = {
        "echo": settings.echo,
        "future": settings.future,
        "pool_pre_ping": (
            settings.pool_pre_ping
        ),
    }

    if settings.backend == DatabaseBackend.SQLITE:
        options["connect_args"] = {
            "check_same_thread": False,
            "timeout": max(
                1,
                settings.sqlite_busy_timeout_ms // 1000,
            ),
        }

        if settings.database_url in {
            "sqlite://",
            "sqlite:///:memory:",
        }:
            options["poolclass"] = StaticPool

    elif (
        settings.backend
        == DatabaseBackend.POSTGRESQL
    ):
        options.update({
            "pool_size": settings.pool_size,
            "max_overflow": settings.max_overflow,
            "pool_timeout": (
                settings.pool_timeout_seconds
            ),
            "pool_recycle": (
                settings.pool_recycle_seconds
            ),
            "connect_args": {
                "connect_timeout": (
                    settings.connect_timeout_seconds
                ),
            },
        })

    return options


ENGINE_OPTIONS: Final[
    dict[str, Any]
] = build_engine_options(
    DATABASE_SETTINGS
)


def create_database_engine(
    settings: DatabaseSettings | None = None,
) -> Engine:
    settings = (
        settings
        or DATABASE_SETTINGS
    )

    return create_engine(
        settings.database_url,
        **build_engine_options(settings),
    )


engine: Engine = create_database_engine()


@event.listens_for(engine, "connect")
def _configure_sqlite_connection(
    dbapi_connection: Any,
    connection_record: Any,
) -> None:
    if not IS_SQLITE:
        return

    cursor = dbapi_connection.cursor()

    try:
        if DATABASE_SETTINGS.sqlite_foreign_keys:
            cursor.execute(
                "PRAGMA foreign_keys=ON"
            )

        cursor.execute(
            "PRAGMA busy_timeout="
            f"{DATABASE_SETTINGS.sqlite_busy_timeout_ms}"
        )

        if DATABASE_SETTINGS.sqlite_wal_mode:
            try:
                cursor.execute(
                    "PRAGMA journal_mode=WAL"
                )
            except Exception:
                pass

        cursor.execute(
            "PRAGMA synchronous=NORMAL"
        )

    finally:
        cursor.close()


# ============================================================
# SECTION 07 - SESSION FACTORY AND BASE
# ============================================================

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=DATABASE_SETTINGS.autoflush,
    autocommit=DATABASE_SETTINGS.autocommit,
    expire_on_commit=(
        DATABASE_SETTINGS.expire_on_commit
    ),
    future=True,
)

Base = declarative_base()


# ============================================================
# SECTION 08 - SESSION METRICS
# ============================================================

@dataclass(slots=True)
class DatabaseSessionMetrics:
    sessions_opened: int = 0
    sessions_closed: int = 0
    commits_succeeded: int = 0
    commits_failed: int = 0
    rollbacks_succeeded: int = 0
    rollbacks_failed: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


_SESSION_METRICS = DatabaseSessionMetrics()
_SESSION_METRICS_LOCK = threading.RLock()


def _record_metric(
    field_name: str,
) -> None:
    with _SESSION_METRICS_LOCK:
        current = getattr(
            _SESSION_METRICS,
            field_name,
        )

        setattr(
            _SESSION_METRICS,
            field_name,
            current + 1,
        )


def get_database_session_metrics(
) -> dict[str, int]:
    with _SESSION_METRICS_LOCK:
        return _SESSION_METRICS.to_dict()


# ============================================================
# SECTION 09 - SESSION HELPERS
# ============================================================

def create_database_session() -> Session:
    database_session = SessionLocal()
    _record_metric("sessions_opened")
    return database_session


def close_database_session(
    database_session: Session | None,
) -> None:
    if database_session is None:
        return

    try:
        database_session.close()

    finally:
        _record_metric("sessions_closed")


def get_database_session(
) -> Generator[Session, None, None]:
    """
    FastAPI dependency.

    Transaction commits are explicit. An exception rolls the
    transaction back before the session is closed.
    """

    database_session = (
        create_database_session()
    )

    try:
        yield database_session

    except Exception:
        safe_rollback(
            database_session,
            raise_on_error=False,
        )
        raise

    finally:
        close_database_session(
            database_session
        )


@dataclass(slots=True)
class TransactionResult:
    status: TransactionStatus
    success: bool
    operation: str
    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "success": self.success,
            "operation": self.operation,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


def safe_commit(
    database_session: Session,
    *,
    rollback_on_error: bool = True,
    raise_on_error: bool = True,
) -> TransactionResult:
    try:
        database_session.commit()
        _record_metric("commits_succeeded")

        return TransactionResult(
            status=(
                TransactionStatus.COMMITTED
            ),
            success=True,
            operation="commit",
        )

    except Exception as error:
        _record_metric("commits_failed")

        if rollback_on_error:
            safe_rollback(
                database_session,
                raise_on_error=False,
            )

        result = TransactionResult(
            status=TransactionStatus.FAILED,
            success=False,
            operation="commit",
            error_type=type(error).__name__,
            error_message=str(error),
        )

        if raise_on_error:
            raise

        return result


def safe_rollback(
    database_session: Session,
    *,
    raise_on_error: bool = False,
) -> TransactionResult:
    try:
        database_session.rollback()
        _record_metric(
            "rollbacks_succeeded"
        )

        return TransactionResult(
            status=(
                TransactionStatus.ROLLED_BACK
            ),
            success=True,
            operation="rollback",
        )

    except Exception as error:
        _record_metric(
            "rollbacks_failed"
        )

        result = TransactionResult(
            status=TransactionStatus.FAILED,
            success=False,
            operation="rollback",
            error_type=type(error).__name__,
            error_message=str(error),
        )

        if raise_on_error:
            raise

        return result


@contextmanager
def managed_database_session(
    *,
    commit_on_success: bool = True,
) -> Generator[Session, None, None]:
    database_session = (
        create_database_session()
    )

    try:
        yield database_session

        if commit_on_success:
            safe_commit(
                database_session,
                raise_on_error=True,
            )

    except Exception:
        safe_rollback(
            database_session,
            raise_on_error=False,
        )
        raise

    finally:
        close_database_session(
            database_session
        )


@contextmanager
def readonly_database_session(
) -> Generator[Session, None, None]:
    database_session = (
        create_database_session()
    )

    try:
        yield database_session

    finally:
        safe_rollback(
            database_session,
            raise_on_error=False,
        )
        close_database_session(
            database_session
        )


# ============================================================
# SECTION 10 - CONNECTION HEALTH
# ============================================================

@dataclass(slots=True)
class ConnectionTestResult:
    connected: bool
    latency_ms: float | None
    backend: DatabaseBackend
    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "latency_ms": (
                round(self.latency_ms, 6)
                if self.latency_ms is not None
                else None
            ),
            "backend": self.backend.value,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


def test_database_connection(
    target_engine: Engine | None = None,
) -> ConnectionTestResult:
    target_engine = (
        target_engine
        or engine
    )

    started_at = time.perf_counter()

    try:
        with target_engine.connect() as connection:
            connection.execute(
                text(DATABASE_HEALTH_QUERY)
            )

        return ConnectionTestResult(
            connected=True,
            latency_ms=(
                time.perf_counter()
                - started_at
            ) * 1000.0,
            backend=DATABASE_BACKEND,
        )

    except Exception as error:
        return ConnectionTestResult(
            connected=False,
            latency_ms=(
                time.perf_counter()
                - started_at
            ) * 1000.0,
            backend=DATABASE_BACKEND,
            error_type=type(error).__name__,
            error_message=str(error),
        )


def database_health_check() -> bool:
    return test_database_connection().connected


# ============================================================
# SECTION 11 - TABLE INSPECTION
# ============================================================

SAFE_IDENTIFIER_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*$"
)


def validate_sql_identifier(
    identifier: str,
) -> str:
    candidate = str(identifier).strip()

    if not SAFE_IDENTIFIER_PATTERN.fullmatch(
        candidate
    ):
        raise ValueError(
            f"Unsafe SQL identifier: {identifier!r}"
        )

    return candidate


def get_database_inspector(
    target_engine: Engine | None = None,
):
    return inspect(
        target_engine or engine
    )


def get_database_table_names(
    target_engine: Engine | None = None,
) -> list[str]:
    try:
        return sorted(
            get_database_inspector(
                target_engine
            ).get_table_names()
        )

    except Exception as error:
        LOGGER.warning(
            "Unable to list database tables: %s",
            error,
        )
        return []


def table_exists(
    table_name: str,
    *,
    target_engine: Engine | None = None,
) -> bool:
    if not table_name:
        return False

    try:
        return bool(
            get_database_inspector(
                target_engine
            ).has_table(
                validate_sql_identifier(
                    table_name
                )
            )
        )

    except Exception:
        return False


def get_table_column_names(
    table_name: str,
) -> list[str]:
    table_name = validate_sql_identifier(
        table_name
    )

    if not table_exists(table_name):
        return []

    try:
        return [
            str(column["name"])
            for column
            in get_database_inspector().get_columns(
                table_name
            )
        ]

    except Exception:
        return []


def count_table_rows(
    table_name: str,
    *,
    database_session: Session | None = None,
) -> int | None:
    table_name = validate_sql_identifier(
        table_name
    )

    if not table_exists(table_name):
        return None

    owns_session = (
        database_session is None
    )

    session = (
        database_session
        or create_database_session()
    )

    try:
        value = session.execute(
            text(
                f'SELECT COUNT(*) '
                f'FROM "{table_name}"'
            )
        ).scalar_one()

        return int(value)

    except Exception as error:
        LOGGER.warning(
            "Unable to count rows in %s: %s",
            table_name,
            error,
        )
        return None

    finally:
        if owns_session:
            close_database_session(session)


# ============================================================
# SECTION 12 - EXPECTED WAREHOUSE TABLES
# ============================================================

CORE_TABLES: Final[tuple[str, ...]] = (
    "teams",
    "players",
    "roster_entries",
    "games",
)

PLAYER_STAT_TABLES: Final[
    tuple[str, ...]
] = (
    "player_season_stats",
    "player_game_stats",
    "player_split_stats",
    "player_statcast_metrics",
    "player_advanced_batting_stats",
    "player_batted_ball_profiles",
    "player_percentile_rankings",
    "player_pitch_arsenals",
    "player_pitch_tempo",
    "player_batting_stances",
    "player_home_run_profiles",
)

TEAM_STAT_TABLES: Final[
    tuple[str, ...]
] = (
    "team_season_stats",
    "team_plate_discipline",
)

GAME_CONTEXT_TABLES: Final[
    tuple[str, ...]
] = (
    "probable_pitchers",
    "starting_lineups",
    "pitch_events",
    "plate_appearances",
    "statcast_events",
)

PREDICTION_TABLES: Final[
    tuple[str, ...]
] = (
    "prediction_results",
)

LEARNING_TABLES: Final[
    tuple[str, ...]
] = (
    "chat_memory",
    "learning_signals",
    "training_examples",
    "entity_aliases",
    "user_feedback",
)

AUDIT_TABLES: Final[
    tuple[str, ...]
] = (
    "raw_data_import_logs",
)

EXPECTED_WAREHOUSE_TABLES: Final[
    tuple[str, ...]
] = tuple(
    dict.fromkeys(
        (
            *CORE_TABLES,
            *PLAYER_STAT_TABLES,
            *TEAM_STAT_TABLES,
            *GAME_CONTEXT_TABLES,
            *PREDICTION_TABLES,
            *LEARNING_TABLES,
            *AUDIT_TABLES,
        )
    )
)


def detect_missing_tables(
    required_tables: Iterable[str] | None = None,
) -> list[str]:
    required = tuple(
        required_tables
        or EXPECTED_WAREHOUSE_TABLES
    )

    present = set(
        get_database_table_names()
    )

    return sorted(
        table_name
        for table_name in required
        if table_name not in present
    )


# ============================================================
# SECTION 13 - FRESHNESS ANALYSIS
# ============================================================

FRESHNESS_COLUMN_PRIORITY: Final[
    tuple[str, ...]
] = (
    "source_updated_at",
    "updated_at",
    "completed_at",
    "created_at",
    "game_date",
    "official_date",
)


def resolve_freshness_column(
    table_name: str,
) -> str | None:
    columns = set(
        get_table_column_names(table_name)
    )

    for candidate in (
        FRESHNESS_COLUMN_PRIORITY
    ):
        if candidate in columns:
            return candidate

    return None


def coerce_datetime(
    value: Any,
) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)

    raw = str(value).strip()

    if not raw:
        return None

    normalized = raw.replace(
        "Z",
        "+00:00",
    )

    try:
        parsed = datetime.fromisoformat(
            normalized
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=UTC
            )

        return parsed.astimezone(UTC)

    except ValueError:
        return None


def get_latest_table_timestamp(
    table_name: str,
    *,
    timestamp_column: str | None = None,
    database_session: Session | None = None,
) -> datetime | None:
    table_name = validate_sql_identifier(
        table_name
    )

    if not table_exists(table_name):
        return None

    column_name = (
        timestamp_column
        or resolve_freshness_column(
            table_name
        )
    )

    if not column_name:
        return None

    column_name = validate_sql_identifier(
        column_name
    )

    owns_session = (
        database_session is None
    )

    session = (
        database_session
        or create_database_session()
    )

    try:
        value = session.execute(
            text(
                f'SELECT MAX("{column_name}") '
                f'FROM "{table_name}"'
            )
        ).scalar_one_or_none()

        return coerce_datetime(value)

    except Exception:
        return None

    finally:
        if owns_session:
            close_database_session(session)


@dataclass(slots=True)
class TableFreshnessReport:
    table_name: str
    exists: bool
    row_count: int | None
    timestamp_column: str | None
    latest_timestamp: datetime | None
    age_hours: float | None
    status: DataFreshnessStatus
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_name": self.table_name,
            "exists": self.exists,
            "row_count": self.row_count,
            "timestamp_column": (
                self.timestamp_column
            ),
            "latest_timestamp": (
                self.latest_timestamp.isoformat()
                if self.latest_timestamp
                else None
            ),
            "age_hours": (
                round(self.age_hours, 3)
                if self.age_hours is not None
                else None
            ),
            "status": self.status.value,
            "warning": self.warning,
        }


def inspect_table_freshness(
    table_name: str,
    *,
    stale_after_hours: int | None = None,
    critical_after_hours: int | None = None,
) -> TableFreshnessReport:
    stale_after_hours = (
        stale_after_hours
        if stale_after_hours is not None
        else DATABASE_SETTINGS.stale_after_hours
    )

    critical_after_hours = (
        critical_after_hours
        if critical_after_hours is not None
        else DATABASE_SETTINGS.critical_stale_after_hours
    )

    if not table_exists(table_name):
        return TableFreshnessReport(
            table_name=table_name,
            exists=False,
            row_count=None,
            timestamp_column=None,
            latest_timestamp=None,
            age_hours=None,
            status=(
                DataFreshnessStatus.TABLE_MISSING
            ),
            warning=(
                f"Required table {table_name} is missing"
            ),
        )

    row_count = count_table_rows(table_name)

    if row_count in (None, 0):
        return TableFreshnessReport(
            table_name=table_name,
            exists=True,
            row_count=row_count,
            timestamp_column=(
                resolve_freshness_column(
                    table_name
                )
            ),
            latest_timestamp=None,
            age_hours=None,
            status=DataFreshnessStatus.EMPTY,
            warning=(
                f"Table {table_name} contains no rows"
            ),
        )

    timestamp_column = (
        resolve_freshness_column(
            table_name
        )
    )

    if timestamp_column is None:
        return TableFreshnessReport(
            table_name=table_name,
            exists=True,
            row_count=row_count,
            timestamp_column=None,
            latest_timestamp=None,
            age_hours=None,
            status=(
                DataFreshnessStatus.UNKNOWN
            ),
            warning=(
                f"Table {table_name} has no recognized "
                "freshness timestamp column"
            ),
        )

    latest_timestamp = (
        get_latest_table_timestamp(
            table_name,
            timestamp_column=(
                timestamp_column
            ),
        )
    )

    if latest_timestamp is None:
        return TableFreshnessReport(
            table_name=table_name,
            exists=True,
            row_count=row_count,
            timestamp_column=(
                timestamp_column
            ),
            latest_timestamp=None,
            age_hours=None,
            status=(
                DataFreshnessStatus.UNKNOWN
            ),
            warning=(
                f"Table {table_name} has no usable "
                "freshness timestamp"
            ),
        )

    age_hours = max(
        0.0,
        (
            datetime.now(UTC)
            - latest_timestamp
        ).total_seconds()
        / 3600.0,
    )

    if age_hours >= critical_after_hours:
        status = (
            DataFreshnessStatus.CRITICAL
        )
        warning = (
            f"Table {table_name} is critically stale "
            f"({age_hours:.1f} hours old)"
        )

    elif age_hours >= stale_after_hours:
        status = DataFreshnessStatus.STALE
        warning = (
            f"Table {table_name} is stale "
            f"({age_hours:.1f} hours old)"
        )

    else:
        status = (
            DataFreshnessStatus.CURRENT
        )
        warning = None

    return TableFreshnessReport(
        table_name=table_name,
        exists=True,
        row_count=row_count,
        timestamp_column=timestamp_column,
        latest_timestamp=latest_timestamp,
        age_hours=age_hours,
        status=status,
        warning=warning,
    )


DEFAULT_FRESHNESS_TABLES: Final[
    tuple[str, ...]
] = (
    "teams",
    "players",
    "roster_entries",
    "games",
    "player_season_stats",
    "player_game_stats",
    "player_split_stats",
    "player_statcast_metrics",
    "team_season_stats",
    "probable_pitchers",
    "starting_lineups",
)


def detect_stale_tables(
    table_names: Iterable[str] | None = None,
    *,
    stale_after_hours: int | None = None,
    critical_after_hours: int | None = None,
) -> list[dict[str, Any]]:
    reports = [
        inspect_table_freshness(
            table_name,
            stale_after_hours=(
                stale_after_hours
            ),
            critical_after_hours=(
                critical_after_hours
            ),
        )
        for table_name in (
            table_names
            or DEFAULT_FRESHNESS_TABLES
        )
    ]

    return [
        report.to_dict()
        for report in reports
        if report.status
        in {
            DataFreshnessStatus.STALE,
            DataFreshnessStatus.CRITICAL,
            DataFreshnessStatus.EMPTY,
            DataFreshnessStatus.TABLE_MISSING,
        }
    ]


def get_latest_ingestion_timestamp(
) -> datetime | None:
    candidate_tables = (
        "raw_data_import_logs",
        "player_statcast_metrics",
        "player_season_stats",
        "player_game_stats",
        "roster_entries",
        "players",
        "teams",
    )

    timestamps = []

    for table_name in candidate_tables:
        timestamp = (
            get_latest_table_timestamp(
                table_name
            )
        )

        if timestamp is not None:
            timestamps.append(timestamp)

    return max(timestamps) if timestamps else None


# ============================================================
# SECTION 14 - INVENTORY
# ============================================================

@dataclass(slots=True)
class DatabaseInventory:
    database_connected: bool
    database_url_type: str
    database_backend: str
    database_url_safe: str

    team_count: int | None
    player_count: int | None
    roster_entry_count: int | None
    game_count: int | None
    player_stat_count: int | None
    player_game_log_count: int | None
    player_split_count: int | None
    statcast_row_count: int | None
    team_stat_count: int | None

    latest_ingestion_timestamp: str | None
    missing_table_warnings: list[str]
    stale_data_warnings: list[str]

    table_count: int
    tables: list[str]
    table_row_counts: dict[str, int | None]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_database_inventory(
) -> dict[str, Any]:
    connection = test_database_connection()
    tables = get_database_table_names()

    count_mapping = {
        "team_count": "teams",
        "player_count": "players",
        "roster_entry_count": (
            "roster_entries"
        ),
        "game_count": "games",
        "player_stat_count": (
            "player_season_stats"
        ),
        "player_game_log_count": (
            "player_game_stats"
        ),
        "player_split_count": (
            "player_split_stats"
        ),
        "statcast_row_count": (
            "player_statcast_metrics"
        ),
        "team_stat_count": (
            "team_season_stats"
        ),
    }

    counts = {
        key: count_table_rows(table_name)
        for key, table_name
        in count_mapping.items()
    }

    table_row_counts = {
        table_name: count_table_rows(
            table_name
        )
        for table_name in tables
    }

    missing_tables = detect_missing_tables()
    stale_reports = detect_stale_tables()
    latest_ingestion = (
        get_latest_ingestion_timestamp()
    )

    inventory = DatabaseInventory(
        database_connected=(
            connection.connected
        ),
        database_url_type=(
            DATABASE_BACKEND.value
        ),
        database_backend=(
            DATABASE_BACKEND.value
        ),
        database_url_safe=(
            redact_database_url(
                DATABASE_URL
            )
        ),
        team_count=counts["team_count"],
        player_count=counts["player_count"],
        roster_entry_count=counts[
            "roster_entry_count"
        ],
        game_count=counts["game_count"],
        player_stat_count=counts[
            "player_stat_count"
        ],
        player_game_log_count=counts[
            "player_game_log_count"
        ],
        player_split_count=counts[
            "player_split_count"
        ],
        statcast_row_count=counts[
            "statcast_row_count"
        ],
        team_stat_count=counts[
            "team_stat_count"
        ],
        latest_ingestion_timestamp=(
            latest_ingestion.isoformat()
            if latest_ingestion
            else None
        ),
        missing_table_warnings=[
            f"Missing required table: {table_name}"
            for table_name in missing_tables
        ],
        stale_data_warnings=[
            str(
                report.get("warning")
                or (
                    f"{report['table_name']} "
                    f"status: {report['status']}"
                )
            )
            for report in stale_reports
        ],
        table_count=len(tables),
        tables=tables,
        table_row_counts=table_row_counts,
    )

    return inventory.to_dict()


# ============================================================
# SECTION 15 - HEALTH REPORT
# ============================================================

def database_health() -> dict[str, Any]:
    connection = test_database_connection()

    if not connection.connected:
        return {
            "status": (
                DatabaseHealthStatus.UNAVAILABLE.value
            ),
            "module_name": (
                DATABASE_MODULE_NAME
            ),
            "module_version": (
                DATABASE_MODULE_VERSION
            ),
            "module_phase": (
                DATABASE_MODULE_PHASE
            ),
            "database_connected": False,
            "database_url_type": (
                DATABASE_BACKEND.value
            ),
            "database_backend": (
                DATABASE_BACKEND.value
            ),
            "database_url_safe": (
                redact_database_url(
                    DATABASE_URL
                )
            ),
            "team_count": None,
            "player_count": None,
            "roster_entry_count": None,
            "game_count": None,
            "player_stat_count": None,
            "player_game_log_count": None,
            "player_split_count": None,
            "statcast_row_count": None,
            "team_stat_count": None,
            "latest_ingestion_timestamp": None,
            "missing_table_warnings": [],
            "stale_data_warnings": [],
            "connection_latency_ms": (
                connection.latency_ms
            ),
            "connection_error_type": (
                connection.error_type
            ),
            "connection_error_message": (
                connection.error_message
            ),
            "session_metrics": (
                get_database_session_metrics()
            ),
            "checked_at": datetime.now(
                UTC
            ).isoformat(),
        }

    inventory = collect_database_inventory()

    status = (
        DatabaseHealthStatus.DEGRADED
        if (
            inventory[
                "missing_table_warnings"
            ]
            or inventory[
                "stale_data_warnings"
            ]
        )
        else DatabaseHealthStatus.HEALTHY
    )

    return {
        "status": status.value,
        "module_name": DATABASE_MODULE_NAME,
        "module_version": (
            DATABASE_MODULE_VERSION
        ),
        "module_phase": (
            DATABASE_MODULE_PHASE
        ),
        **inventory,
        "connection_latency_ms": (
            round(
                connection.latency_ms,
                6,
            )
            if connection.latency_ms
            is not None
            else None
        ),
        "connection_error_type": None,
        "connection_error_message": None,
        "session_metrics": (
            get_database_session_metrics()
        ),
        "checked_at": datetime.now(
            UTC
        ).isoformat(),
    }


def database_health_details() -> dict[str, Any]:
    health = database_health()

    return {
        "database_url_configured": bool(
            DATABASE_URL
        ),
        "database_type": (
            DATABASE_BACKEND.value
        ),
        "database_url": (
            redact_database_url(
                DATABASE_URL
            )
        ),
        "connection_ok": health[
            "database_connected"
        ],
        "engine_echo": (
            DATABASE_SETTINGS.echo
        ),
        "pool_pre_ping": (
            DATABASE_SETTINGS.pool_pre_ping
        ),
        "health_status": health["status"],
        "connection_latency_ms": health[
            "connection_latency_ms"
        ],
        "missing_table_warnings": health[
            "missing_table_warnings"
        ],
        "stale_data_warnings": health[
            "stale_data_warnings"
        ],
    }


# ============================================================
# SECTION 16 - TABLE MANAGEMENT
# ============================================================

def import_database_models() -> bool:
    try:
        __import__(
            "models",
            fromlist=["*"],
        )
        return True

    except Exception as error:
        LOGGER.exception(
            "Unable to import models: %s",
            error,
        )
        return False


def create_all_database_tables(
    *,
    raise_on_error: bool = False,
) -> bool:
    try:
        import_database_models()
        Base.metadata.create_all(
            bind=engine
        )
        return True

    except Exception:
        LOGGER.exception(
            "Database table creation failed"
        )

        if raise_on_error:
            raise

        return False


def drop_all_database_tables(
    *,
    confirmation: str | None = None,
    raise_on_error: bool = False,
) -> bool:
    required_confirmation = (
        "DROP_AISP2_DATABASE_TABLES"
    )

    if confirmation != required_confirmation:
        raise ValueError(
            "drop_all_database_tables requires "
            f"confirmation={required_confirmation!r}"
        )

    try:
        import_database_models()
        Base.metadata.drop_all(bind=engine)
        return True

    except Exception:
        LOGGER.exception(
            "Database table deletion failed"
        )

        if raise_on_error:
            raise

        return False


# ============================================================
# SECTION 17 - WAREHOUSE STATUS
# ============================================================

def database_warehouse_status(
) -> dict[str, Any]:
    inventory = collect_database_inventory()
    table_set = set(inventory["tables"])

    categories = {
        "core": CORE_TABLES,
        "player_stats": (
            PLAYER_STAT_TABLES
        ),
        "team_stats": TEAM_STAT_TABLES,
        "game_context": (
            GAME_CONTEXT_TABLES
        ),
        "prediction": (
            PREDICTION_TABLES
        ),
        "learning": LEARNING_TABLES,
        "audit": AUDIT_TABLES,
    }

    category_status = {}

    for category, tables in categories.items():
        missing = [
            table_name
            for table_name in tables
            if table_name not in table_set
        ]

        category_status[category] = {
            "ready": not missing,
            "required_tables": list(tables),
            "missing_tables": missing,
        }

    present_required = [
        table_name
        for table_name
        in EXPECTED_WAREHOUSE_TABLES
        if table_name in table_set
    ]

    warehouse_score = int(
        round(
            len(present_required)
            / len(
                EXPECTED_WAREHOUSE_TABLES
            )
            * 100
        )
    )

    return {
        **inventory,
        "required_table_count": len(
            EXPECTED_WAREHOUSE_TABLES
        ),
        "present_required_table_count": len(
            present_required
        ),
        "missing_required_table_count": len(
            detect_missing_tables()
        ),
        "present_required_tables": (
            present_required
        ),
        "missing_required_tables": (
            detect_missing_tables()
        ),
        "category_status": category_status,
        "core_ready": (
            category_status["core"][
                "ready"
            ]
        ),
        "stats_ready": (
            category_status[
                "player_stats"
            ]["ready"]
            and category_status[
                "team_stats"
            ]["ready"]
        ),
        "game_context_ready": (
            category_status[
                "game_context"
            ]["ready"]
        ),
        "prediction_tables_ready": (
            category_status[
                "prediction"
            ]["ready"]
        ),
        "learning_ready": (
            category_status[
                "learning"
            ]["ready"]
        ),
        "audit_ready": (
            category_status[
                "audit"
            ]["ready"]
        ),
        "warehouse_ready": (
            warehouse_score == 100
        ),
        "warehouse_score": warehouse_score,
        "next_required_action": (
            "Warehouse schema is complete. Run ingestion."
            if warehouse_score == 100
            else (
                "Create missing tables before full ingestion."
            )
        ),
    }


# ============================================================
# SECTION 18 - PLAYER EXPLORER READINESS
# ============================================================

def player_explorer_database_readiness(
) -> dict[str, Any]:
    inventory = collect_database_inventory()

    required_tables = (
        "teams",
        "players",
        "roster_entries",
        "player_season_stats",
        "player_game_stats",
        "player_split_stats",
        "player_statcast_metrics",
    )

    missing_tables = detect_missing_tables(
        required_tables
    )

    checks = {
        "database_connected": bool(
            inventory[
                "database_connected"
            ]
        ),
        "teams_loaded": (
            inventory["team_count"]
            is not None
            and inventory[
                "team_count"
            ] >= 30
        ),
        "players_loaded": (
            inventory["player_count"]
            is not None
            and inventory[
                "player_count"
            ] > 0
        ),
        "rosters_loaded": (
            inventory[
                "roster_entry_count"
            ]
            is not None
            and inventory[
                "roster_entry_count"
            ] > 0
        ),
        "season_stats_loaded": (
            inventory[
                "player_stat_count"
            ]
            is not None
            and inventory[
                "player_stat_count"
            ] > 0
        ),
        "game_logs_loaded": (
            inventory[
                "player_game_log_count"
            ]
            is not None
            and inventory[
                "player_game_log_count"
            ] > 0
        ),
        "splits_loaded": (
            inventory[
                "player_split_count"
            ]
            is not None
            and inventory[
                "player_split_count"
            ] > 0
        ),
        "statcast_loaded": (
            inventory[
                "statcast_row_count"
            ]
            is not None
            and inventory[
                "statcast_row_count"
            ] > 0
        ),
        "required_tables_present": (
            not missing_tables
        ),
    }

    passed = sum(
        1
        for value in checks.values()
        if value
    )

    readiness_score = int(
        round(
            passed
            / len(checks)
            * 100
        )
    )

    warnings = []

    if missing_tables:
        warnings.append(
            "Missing Player Explorer tables: "
            + ", ".join(missing_tables)
        )

    for check_name, warning in (
        (
            "season_stats_loaded",
            "Player season statistics are not loaded",
        ),
        (
            "game_logs_loaded",
            "Player game logs are not loaded",
        ),
        (
            "splits_loaded",
            "Player split statistics are not loaded",
        ),
        (
            "statcast_loaded",
            "Player Statcast metrics are not loaded",
        ),
    ):
        if not checks[check_name]:
            warnings.append(warning)

    return {
        "status": (
            "ready"
            if readiness_score == 100
            else "not_ready"
        ),
        "readiness_score": readiness_score,
        "checks": checks,
        "missing_tables": missing_tables,
        "warnings": warnings,
        "inventory": inventory,
        "completion_gate_passed": (
            readiness_score == 100
        ),
    }


# ============================================================
# SECTION 19 - INITIALIZATION
# ============================================================

def initialize_database() -> dict[str, Any]:
    models_imported = (
        import_database_models()
    )

    tables_created = (
        create_all_database_tables()
        if models_imported
        else False
    )

    return {
        "initialized": bool(
            models_imported
            and tables_created
        ),
        "models_imported": (
            models_imported
        ),
        "tables_created": (
            tables_created
        ),
        "health": database_health(),
        "warehouse": (
            database_warehouse_status()
        ),
        "player_explorer": (
            player_explorer_database_readiness()
        ),
    }


def dispose_database_engine() -> None:
    engine.dispose()


# ============================================================
# SECTION 20 - VALIDATION
# ============================================================

def validate_database_module(
) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    checks["database_url_normalized"] = bool(
        DATABASE_URL
    )

    checks[
        "database_backend_detected"
    ] = (
        DATABASE_BACKEND
        != DatabaseBackend.UNKNOWN
    )

    checks["safe_url_redaction"] = (
        "***"
        in redact_database_url(
            "postgresql+psycopg://"
            "user:secret@localhost/db"
        )
    )

    checks[
        "safe_identifier_accepts_table"
    ] = (
        validate_sql_identifier(
            "player_season_stats"
        )
        == "player_season_stats"
    )

    unsafe_rejected = False

    try:
        validate_sql_identifier(
            "players; DROP TABLE teams"
        )

    except ValueError:
        unsafe_rejected = True

    checks[
        "unsafe_identifier_rejected"
    ] = unsafe_rejected

    try:
        DATABASE_SETTINGS.validate()
        checks[
            "settings_validation"
        ] = True

    except Exception:
        checks[
            "settings_validation"
        ] = False

    checks[
        "session_factory_available"
    ] = callable(SessionLocal)

    checks[
        "managed_session_available"
    ] = callable(
        managed_database_session
    )

    checks[
        "safe_commit_available"
    ] = callable(safe_commit)

    checks[
        "safe_rollback_available"
    ] = callable(safe_rollback)

    checks[
        "table_exists_available"
    ] = callable(table_exists)

    checks[
        "count_table_rows_available"
    ] = callable(count_table_rows)

    checks[
        "inventory_available"
    ] = callable(
        collect_database_inventory
    )

    checks[
        "stale_detection_available"
    ] = callable(
        detect_stale_tables
    )

    checks[
        "missing_detection_available"
    ] = callable(
        detect_missing_tables
    )

    checks[
        "health_report_available"
    ] = callable(database_health)

    checks[
        "sqlite_url_detection"
    ] = (
        detect_database_backend(
            "sqlite:///test.db"
        )
        == DatabaseBackend.SQLITE
    )

    checks[
        "postgres_url_detection"
    ] = (
        detect_database_backend(
            "postgresql+psycopg://u:p@h/d"
        )
        == DatabaseBackend.POSTGRESQL
    )

    checks[
        "provider_url_normalization"
    ] = normalize_database_url(
        "postgres://user:pass@host/database"
    ).startswith(
        "postgresql+psycopg://"
    )

    passed = sum(
        1
        for value in checks.values()
        if value
    )

    return {
        "status": (
            "ok"
            if passed == len(checks)
            else "failed"
        ),
        "module": DATABASE_MODULE_NAME,
        "version": DATABASE_MODULE_VERSION,
        "phase": DATABASE_MODULE_PHASE,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "failed_checks": [
            name
            for name, value
            in checks.items()
            if not value
        ],
    }


# ============================================================
# SECTION 21 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "DATABASE_MODULE_NAME",
    "DATABASE_MODULE_VERSION",
    "DATABASE_MODULE_PHASE",
    "DATABASE_MODULE_PATH",
    "DATABASE_MODULE_STATUS",
    "DATABASE_SCHEMA_VERSION",

    "DEFAULT_DATABASE_FILENAME",
    "DEFAULT_DATABASE_URL",
    "DATABASE_URL",
    "DATABASE_BACKEND",
    "IS_SQLITE",
    "IS_POSTGRESQL",

    "DatabaseBackend",
    "DatabaseHealthStatus",
    "DataFreshnessStatus",
    "TransactionStatus",

    "DatabaseSettings",
    "DatabaseSessionMetrics",
    "TransactionResult",
    "ConnectionTestResult",
    "TableFreshnessReport",
    "DatabaseInventory",

    "DATABASE_SETTINGS",
    "ENGINE_OPTIONS",
    "engine",
    "SessionLocal",
    "Base",

    "normalize_database_url",
    "detect_database_backend",
    "redact_database_url",
    "load_database_settings",
    "build_engine_options",
    "create_database_engine",

    "create_database_session",
    "close_database_session",
    "get_database_session",
    "managed_database_session",
    "readonly_database_session",
    "get_database_session_metrics",

    "safe_commit",
    "safe_rollback",

    "test_database_connection",
    "database_health_check",
    "database_health",
    "database_health_details",

    "get_database_inspector",
    "get_database_table_names",
    "table_exists",
    "validate_sql_identifier",
    "get_table_column_names",
    "count_table_rows",

    "resolve_freshness_column",
    "coerce_datetime",
    "get_latest_table_timestamp",
    "inspect_table_freshness",
    "detect_stale_tables",
    "detect_missing_tables",
    "get_latest_ingestion_timestamp",

    "collect_database_inventory",
    "database_warehouse_status",
    "player_explorer_database_readiness",

    "import_database_models",
    "create_all_database_tables",
    "drop_all_database_tables",
    "initialize_database",
    "dispose_database_engine",

    "validate_database_module",

    "CORE_TABLES",
    "PLAYER_STAT_TABLES",
    "TEAM_STAT_TABLES",
    "GAME_CONTEXT_TABLES",
    "PREDICTION_TABLES",
    "LEARNING_TABLES",
    "AUDIT_TABLES",
    "EXPECTED_WAREHOUSE_TABLES",
]


# ============================================================
# SECTION 22 - LOCAL VALIDATION ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    import json

    print(
        json.dumps(
            {
                "validation": (
                    validate_database_module()
                ),
                "health": database_health(),
                "warehouse": (
                    database_warehouse_status()
                ),
                "player_explorer": (
                    player_explorer_database_readiness()
                ),
            },
            indent=2,
            default=str,
        )
    )

# ============================================================
# SECTION 99 - PHASE 14 PART 7.0 - DATABASE TRUTH CONTRACT
# FILE: 01_database/database.py
# PURPOSE:
# Shared production truth states for callers that need to avoid
# demo-mode language and expose exact warehouse readiness.
# ============================================================

PHASE14_DATABASE_TRUTH_VERSION = "phase_14_part_7_0_database_truth_contract"

PHASE14_PRODUCTION_STATES = {
    "database_ready": "database_ready",
    "live_api_fallback": "live_api_fallback",
    "warehouse_pending": "warehouse_pending",
    "insufficient_sample": "insufficient_sample",
    "stale_data": "stale_data",
    "missing_statcast": "missing_statcast",
    "prediction_ready": "prediction_ready",
    "prediction_blocked": "prediction_blocked",
}


def validate_phase14_database_truth_contract() -> dict:
    required_states = {
        "database_ready",
        "live_api_fallback",
        "warehouse_pending",
        "insufficient_sample",
        "stale_data",
        "missing_statcast",
        "prediction_ready",
        "prediction_blocked",
    }

    checks = {
        "truth_version_present": bool(PHASE14_DATABASE_TRUTH_VERSION),
        "all_required_states_present": required_states.issubset(set(PHASE14_PRODUCTION_STATES)),
        "no_demo_ready_state": "demo_ready" not in PHASE14_PRODUCTION_STATES,
    }

    passed = sum(1 for value in checks.values() if value)

    return {
        "status": "ok" if passed == len(checks) else "degraded",
        "phase": "Phase 14 Part 7.0",
        "truth_version": PHASE14_DATABASE_TRUTH_VERSION,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "production_states": PHASE14_PRODUCTION_STATES,
    }

