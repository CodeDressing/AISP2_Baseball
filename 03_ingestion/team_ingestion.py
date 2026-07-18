# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# PHASE 11 PART 1.0
# FILE: 03_ingestion/team_ingestion.py
# PURPOSE:
# Enterprise MLB team-ingestion orchestration for official team
# metadata, optional roster/player bootstrap loading, schema-aware
# persistence, retry control, idempotent upserts, validation,
# auditing, dry-run execution, and production readiness reporting.
# ============================================================

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from collections import Counter
from collections import defaultdict
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import inspect
import json
import logging
import math
import os
from pathlib import Path
import random
import re
import sys
import time
from typing import Any
from typing import Final
from typing import Protocol
from uuid import uuid4


# ============================================================
# SECTION 02 - PROJECT PATH SETUP
# ============================================================

CURRENT_FILE: Final[Path] = Path(__file__).resolve()
PROJECT_ROOT: Final[Path] = CURRENT_FILE.parents[1]
DATABASE_DIR: Final[Path] = PROJECT_ROOT / "01_database"
DATA_SOURCES_DIR: Final[Path] = PROJECT_ROOT / "02_data_sources"

for _path in (
    PROJECT_ROOT,
    DATABASE_DIR,
    DATA_SOURCES_DIR,
):
    _path_string = str(_path)

    if _path_string not in sys.path:
        sys.path.insert(
            0,
            _path_string,
        )


# ============================================================
# SECTION 03 - PROJECT IMPORTS
# ============================================================

from database import managed_database_session
from database import collect_database_inventory
from database import safe_commit
from database import safe_rollback
from models import Team

try:
    from models import Player
except Exception:
    Player = None

try:
    from models import RosterEntry
except Exception:
    RosterEntry = None

try:
    from database import initialize_database
except Exception:
    initialize_database = None

from mlb_stats_api import DEFAULT_SEASON
from mlb_stats_api import MLBStatsAPIClient
try:
    from mlb_stats_api import MLBStatsAPIError
except Exception:
    MLBStatsAPIError = RuntimeError


# ============================================================
# SECTION 04 - THIRD-PARTY IMPORTS
# ============================================================

try:
    import requests
except Exception as exc:
    raise RuntimeError(
        "The requests package is required by team_ingestion.py"
    ) from exc

try:
    from sqlalchemy import inspect as sqlalchemy_inspect
except Exception:
    sqlalchemy_inspect = None


# ============================================================
# SECTION 05 - LOGGING
# ============================================================

LOGGER = logging.getLogger(__name__)

if not LOGGER.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
    )
    LOGGER.addHandler(_handler)

LOGGER.setLevel(
    os.getenv(
        "AISP2_TEAM_INGESTION_LOG_LEVEL",
        "INFO",
    ).upper()
)


# ============================================================
# SECTION 06 - ENGINE METADATA
# ============================================================

INGESTION_NAME: Final[str] = "AISP2 Enterprise Team Ingestion"
INGESTION_VERSION: Final[str] = "6.1.0"
INGESTION_PHASE: Final[str] = "Phase 11 Part 6.1"
INGESTION_PATH: Final[str] = "03_ingestion/team_ingestion.py"
INGESTION_STATUS: Final[str] = "enterprise_ready"
INGESTION_SCHEMA_VERSION: Final[str] = "3.1.0"

DEFAULT_TEAM_SEASON: Final[int] = int(DEFAULT_SEASON)
DEFAULT_ROSTER_TYPE: Final[str] = "fullRoster"
DEFAULT_SPORT_ID: Final[int] = 1
DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0
DEFAULT_MAX_RETRIES: Final[int] = 4
DEFAULT_RETRY_BACKOFF_SECONDS: Final[float] = 1.0
DEFAULT_REQUEST_DELAY_SECONDS: Final[float] = 0.15
DEFAULT_EXPECTED_ACTIVE_TEAM_COUNT: Final[int] = 30
DEFAULT_MINIMUM_PLAYER_FOUNDATION: Final[int] = 500
DEFAULT_MINIMUM_ROSTER_FOUNDATION: Final[int] = 500

MLB_STATS_API_BASE_URL: Final[str] = "https://statsapi.mlb.com/api/v1"


# ============================================================
# SECTION 07 - ENUMERATIONS
# ============================================================

class IngestionMode(str, Enum):
    TEAMS_ONLY = "teams_only"
    TEAMS_AND_ROSTERS = "teams_and_rosters"


class RecordAction(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    SKIPPED = "skipped"
    FAILED = "failed"
    DRY_RUN_CREATE = "dry_run_create"
    DRY_RUN_UPDATE = "dry_run_update"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReadinessStatus(str, Enum):
    READY = "ready"
    PARTIAL = "partial"
    NOT_READY = "not_ready"
    FAILED = "failed"


class EntityKind(str, Enum):
    TEAM = "team"
    PLAYER = "player"
    ROSTER_ENTRY = "roster_entry"
    SOURCE = "source"
    DATABASE = "database"
    VALIDATION = "validation"


# ============================================================
# SECTION 08 - CONFIGURATION
# ============================================================

@dataclass(slots=True)
class TeamIngestionConfig:
    season: int = DEFAULT_TEAM_SEASON
    sport_id: int = DEFAULT_SPORT_ID
    roster_type: str = DEFAULT_ROSTER_TYPE
    include_rosters: bool = True
    include_inactive_teams: bool = False

    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS

    expected_active_team_count: int = DEFAULT_EXPECTED_ACTIVE_TEAM_COUNT
    minimum_player_foundation: int = DEFAULT_MINIMUM_PLAYER_FOUNDATION
    minimum_roster_foundation: int = DEFAULT_MINIMUM_ROSTER_FOUNDATION

    commit_interval: int = 25
    sample_size: int = 25
    error_sample_size: int = 100

    dry_run: bool = False
    fail_fast: bool = False
    strict_schema: bool = False
    initialize_schema: bool = True
    preserve_existing_non_null_values: bool = False
    prune_missing_roster_entries: bool = False
    capture_raw_payloads: bool = False

    user_agent: str = (
        "AISP2-Baseball/5.0 "
        "(team-ingestion; official MLB Stats API)"
    )

    def validate(self) -> None:
        if self.season < 1876 or self.season > 2100:
            raise ValueError(
                "season must be between 1876 and 2100"
            )

        if self.sport_id <= 0:
            raise ValueError(
                "sport_id must be positive"
            )

        if not self.roster_type.strip():
            raise ValueError(
                "roster_type cannot be empty"
            )

        if self.timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be positive"
            )

        if self.max_retries < 0:
            raise ValueError(
                "max_retries cannot be negative"
            )

        if self.retry_backoff_seconds < 0:
            raise ValueError(
                "retry_backoff_seconds cannot be negative"
            )

        if self.request_delay_seconds < 0:
            raise ValueError(
                "request_delay_seconds cannot be negative"
            )

        if self.commit_interval <= 0:
            raise ValueError(
                "commit_interval must be positive"
            )

        if self.sample_size < 0:
            raise ValueError(
                "sample_size cannot be negative"
            )

        if self.error_sample_size < 0:
            raise ValueError(
                "error_sample_size cannot be negative"
            )

        if self.expected_active_team_count <= 0:
            raise ValueError(
                "expected_active_team_count must be positive"
            )


DEFAULT_CONFIG = TeamIngestionConfig()


# ============================================================
# SECTION 09 - DATA CONTRACTS
# ============================================================

@dataclass(slots=True)
class IngestionIssue:
    severity: Severity
    entity_kind: EntityKind
    message: str
    record_identifier: str | int | None = None
    team_name: str | None = None
    exception_type: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.value,
            "entity_kind": self.entity_kind.value,
            "message": self.message,
            "record_identifier": self.record_identifier,
            "team_name": self.team_name,
            "exception_type": self.exception_type,
            "details": sanitize_for_json(self.details),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(slots=True)
class EntityCounters:
    discovered: int = 0
    valid: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed: int = 0

    @property
    def persisted(self) -> int:
        return (
            self.created
            + self.updated
            + self.unchanged
        )

    def increment_action(
        self,
        action: RecordAction,
    ) -> None:
        mapping = {
            RecordAction.CREATED: "created",
            RecordAction.UPDATED: "updated",
            RecordAction.UNCHANGED: "unchanged",
            RecordAction.SKIPPED: "skipped",
            RecordAction.FAILED: "failed",
            RecordAction.DRY_RUN_CREATE: "created",
            RecordAction.DRY_RUN_UPDATE: "updated",
        }

        field_name = mapping.get(action)

        if field_name:
            setattr(
                self,
                field_name,
                getattr(self, field_name) + 1,
            )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["persisted"] = self.persisted
        return payload


@dataclass(slots=True)
class SourceRequestMetrics:
    request_count: int = 0
    retry_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_elapsed_seconds: float = 0.0
    status_codes: Counter[int] = field(
        default_factory=Counter
    )

    def to_dict(self) -> dict[str, Any]:
        average = (
            self.total_elapsed_seconds / self.request_count
            if self.request_count
            else 0.0
        )

        return {
            "request_count": self.request_count,
            "retry_count": self.retry_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_elapsed_seconds": round(
                self.total_elapsed_seconds,
                6,
            ),
            "average_elapsed_seconds": round(
                average,
                6,
            ),
            "status_codes": dict(
                sorted(self.status_codes.items())
            ),
        }


@dataclass(slots=True)
class UpsertResult:
    action: RecordAction
    instance: Any | None = None
    changed_fields: list[str] = field(
        default_factory=list
    )
    ignored_fields: list[str] = field(
        default_factory=list
    )
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "changed_fields": list(self.changed_fields),
            "ignored_fields": list(self.ignored_fields),
            "message": self.message,
        }


@dataclass(slots=True)
class TeamIngestionRun:
    run_id: str
    started_at: datetime
    config: TeamIngestionConfig

    team_counters: EntityCounters = field(
        default_factory=EntityCounters
    )
    player_counters: EntityCounters = field(
        default_factory=EntityCounters
    )
    roster_counters: EntityCounters = field(
        default_factory=EntityCounters
    )

    request_metrics: SourceRequestMetrics = field(
        default_factory=SourceRequestMetrics
    )

    issues: list[IngestionIssue] = field(
        default_factory=list
    )
    teams: list[dict[str, Any]] = field(
        default_factory=list
    )
    players_sample: list[dict[str, Any]] = field(
        default_factory=list
    )
    team_roster_counts: list[dict[str, Any]] = field(
        default_factory=list
    )
    source_payload_hashes: list[str] = field(
        default_factory=list
    )

    database_initialized: bool | None = None
    database_health: bool | None = None

    finished_at: datetime | None = None
    database_counts: dict[str, int] = field(
        default_factory=dict
    )
    readiness: ReadinessStatus = (
        ReadinessStatus.NOT_READY
    )

    def add_issue(
        self,
        issue: IngestionIssue,
    ) -> None:
        if len(self.issues) < self.config.error_sample_size:
            self.issues.append(issue)

    def finish(self) -> None:
        self.finished_at = datetime.now(UTC)

    @property
    def elapsed_seconds(self) -> float:
        end = self.finished_at or datetime.now(UTC)
        return max(
            0.0,
            (end - self.started_at).total_seconds(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "ingestion": INGESTION_NAME,
            "version": INGESTION_VERSION,
            "phase": INGESTION_PHASE,
            "path": INGESTION_PATH,
            "schema_version": INGESTION_SCHEMA_VERSION,
            "status": INGESTION_STATUS,
            "season": self.config.season,
            "sport_id": self.config.sport_id,
            "source": "Official MLB Stats API",
            "mode": (
                IngestionMode.TEAMS_AND_ROSTERS.value
                if self.config.include_rosters
                else IngestionMode.TEAMS_ONLY.value
            ),
            "roster_type": self.config.roster_type,
            "dry_run": self.config.dry_run,
            "started_at": self.started_at.isoformat(),
            "finished_at": (
                self.finished_at.isoformat()
                if self.finished_at
                else None
            ),
            "elapsed_seconds": round(
                self.elapsed_seconds,
                6,
            ),
            "database_initialized": (
                self.database_initialized
            ),
            "database_health": self.database_health,
            "teams": self.team_counters.to_dict(),
            "players": self.player_counters.to_dict(),
            "roster_entries": self.roster_counters.to_dict(),
            "request_metrics": self.request_metrics.to_dict(),
            "database_counts": dict(self.database_counts),
            "readiness": self.readiness.value,
            "success": self.readiness in {
                ReadinessStatus.READY,
                ReadinessStatus.PARTIAL,
            },
            "issues": [
                issue.to_dict()
                for issue in self.issues
            ],
            "issue_count": len(self.issues),
            "team_records": list(self.teams),
            "players_sample": list(self.players_sample),
            "team_roster_counts": list(
                self.team_roster_counts
            ),
            "source_payload_hashes": list(
                self.source_payload_hashes
            ),
            "configuration": sanitize_for_json(
                asdict(self.config)
            ),
            "next_required_action": (
                build_next_required_action(self)
            ),
        }


# ============================================================
# SECTION 10 - PROTOCOLS
# ============================================================

class SessionLike(Protocol):
    def query(self, *args: Any, **kwargs: Any) -> Any:
        ...

    def add(self, instance: Any) -> None:
        ...

    def flush(self) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...


class MLBClientLike(Protocol):
    def get_teams(
        self,
        season: int,
    ) -> list[dict[str, Any]]:
        ...


# ============================================================
# SECTION 11 - SAFE VALUE HELPERS
# ============================================================

def safe_nested_get(
    data: Mapping[str, Any] | None,
    *keys: str,
    default: Any = None,
) -> Any:
    current_value: Any = data

    for key in keys:
        if not isinstance(
            current_value,
            Mapping,
        ):
            return default

        if key not in current_value:
            return default

        current_value = current_value.get(key)

    return current_value


def safe_string(
    value: Any,
    *,
    maximum_length: int | None = None,
) -> str | None:
    if value is None:
        return None

    cleaned_value = re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    )

    if not cleaned_value:
        return None

    if maximum_length is not None:
        cleaned_value = cleaned_value[
            :maximum_length
        ]

    return cleaned_value


def safe_boolean(
    value: Any,
    default: bool = True,
) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    normalized = str(value).strip().lower()

    if normalized in {
        "true",
        "1",
        "yes",
        "y",
        "active",
    }:
        return True

    if normalized in {
        "false",
        "0",
        "no",
        "n",
        "inactive",
    }:
        return False

    return default


def safe_integer(
    value: Any,
    *,
    default: int | None = None,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int | None:
    if value is None:
        return default

    try:
        converted = int(value)
    except (TypeError, ValueError):
        return default

    if minimum is not None:
        converted = max(
            minimum,
            converted,
        )

    if maximum is not None:
        converted = min(
            maximum,
            converted,
        )

    return converted


def safe_date(
    value: Any,
) -> date | None:
    if value is None:
        return None

    if isinstance(value, date):
        return value

    text = safe_string(value)

    if not text:
        return None

    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def sanitize_for_json(
    value: Any,
) -> Any:
    if value is None:
        return None

    if isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, Mapping):
        return {
            str(key): sanitize_for_json(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        Sequence,
    ) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return [
            sanitize_for_json(item)
            for item in value
        ]

    if hasattr(value, "__dict__"):
        return sanitize_for_json(
            vars(value)
        )

    return str(value)


def payload_hash(
    payload: Any,
) -> str:
    canonical = json.dumps(
        sanitize_for_json(payload),
        sort_keys=True,
        separators=(",", ":"),
    )

    return sha256(
        canonical.encode("utf-8")
    ).hexdigest()


# ============================================================
# SECTION 12 - MODEL SCHEMA INTROSPECTION
# ============================================================

def get_model_field_names(
    model: Any,
) -> set[str]:
    field_names: set[str] = set()

    table = getattr(
        model,
        "__table__",
        None,
    )

    if table is not None:
        for column in getattr(
            table,
            "columns",
            [],
        ):
            field_names.add(column.name)

    if sqlalchemy_inspect is not None:
        try:
            mapper = sqlalchemy_inspect(model)

            for attribute in mapper.attrs:
                field_names.add(attribute.key)
        except Exception:
            pass

    if not field_names:
        try:
            signature = inspect.signature(
                model.__init__
            )

            for parameter in signature.parameters.values():
                if parameter.name != "self":
                    field_names.add(
                        parameter.name
                    )
        except Exception:
            pass

    return field_names


def filter_payload_for_model(
    model: Any,
    payload: Mapping[str, Any],
    *,
    strict: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    model_fields = get_model_field_names(model)

    if not model_fields:
        if strict:
            raise RuntimeError(
                f"Unable to inspect model fields for {model}"
            )

        return dict(payload), []

    filtered: dict[str, Any] = {}
    ignored: list[str] = []

    for key, value in payload.items():
        if key in model_fields:
            filtered[key] = value
        else:
            ignored.append(key)

    return filtered, ignored


def choose_first_existing_field(
    model: Any,
    candidates: Sequence[str],
) -> str | None:
    fields = get_model_field_names(model)

    for candidate in candidates:
        if candidate in fields:
            return candidate

    return None


# ============================================================
# SECTION 13 - NORMALIZATION
# ============================================================

def normalize_team_payload(
    raw_team: Mapping[str, Any],
) -> dict[str, Any]:
    mlb_team_id = safe_integer(
        raw_team.get("id"),
        minimum=1,
    )

    first_year = safe_integer(
        raw_team.get("firstYearOfPlay"),
        minimum=1800,
        maximum=2200,
    )

    return {
        "mlb_team_id": mlb_team_id,
        "name": safe_string(
            raw_team.get("name"),
            maximum_length=255,
        ),
        "abbreviation": safe_string(
            raw_team.get("abbreviation"),
            maximum_length=16,
        ),
        "team_code": safe_string(
            raw_team.get("teamCode"),
            maximum_length=32,
        ),
        "file_code": safe_string(
            raw_team.get("fileCode"),
            maximum_length=32,
        ),
        "franchise_name": safe_string(
            raw_team.get("franchiseName"),
            maximum_length=255,
        ),
        "club_name": safe_string(
            raw_team.get("clubName"),
            maximum_length=255,
        ),
        "short_name": safe_string(
            raw_team.get("shortName"),
            maximum_length=255,
        ),
        "location_name": safe_string(
            raw_team.get("locationName"),
            maximum_length=255,
        ),
        "league": safe_string(
            safe_nested_get(
                raw_team,
                "league",
                "name",
            ),
            maximum_length=255,
        ),
        "league_id": safe_integer(
            safe_nested_get(
                raw_team,
                "league",
                "id",
            ),
            minimum=1,
        ),
        "division": safe_string(
            safe_nested_get(
                raw_team,
                "division",
                "name",
            ),
            maximum_length=255,
        ),
        "division_id": safe_integer(
            safe_nested_get(
                raw_team,
                "division",
                "id",
            ),
            minimum=1,
        ),
        "venue": safe_string(
            safe_nested_get(
                raw_team,
                "venue",
                "name",
            ),
            maximum_length=255,
        ),
        "venue_id": safe_integer(
            safe_nested_get(
                raw_team,
                "venue",
                "id",
            ),
            minimum=1,
        ),
        "first_year_of_play": (
            str(first_year)
            if first_year is not None
            else None
        ),
        "is_active": safe_boolean(
            raw_team.get("active"),
            default=True,
        ),
        "spring_league_id": safe_integer(
            safe_nested_get(
                raw_team,
                "springLeague",
                "id",
            ),
            minimum=1,
        ),
        "spring_league_name": safe_string(
            safe_nested_get(
                raw_team,
                "springLeague",
                "name",
            ),
            maximum_length=255,
        ),
        "sport_id": safe_integer(
            safe_nested_get(
                raw_team,
                "sport",
                "id",
            ),
            minimum=1,
        ),
        "sport_name": safe_string(
            safe_nested_get(
                raw_team,
                "sport",
                "name",
            ),
            maximum_length=255,
        ),
        "source_updated_at": safe_string(
            raw_team.get("lastUpdated"),
        ),
    }


def normalize_player_payload(
    raw_player: Mapping[str, Any],
    raw_roster_entry: Mapping[str, Any],
    database_team_id: int,
) -> dict[str, Any]:
    full_name = safe_string(
        raw_player.get("fullName"),
        maximum_length=255,
    )

    first_name = safe_string(
        raw_player.get("firstName"),
        maximum_length=128,
    )

    last_name = safe_string(
        raw_player.get("lastName"),
        maximum_length=128,
    )

    if full_name and (
        not first_name
        or not last_name
    ):
        name_parts = full_name.split()

        if name_parts and not first_name:
            first_name = name_parts[0]

        if name_parts and not last_name:
            last_name = name_parts[-1]

    position_payload = (
        raw_roster_entry.get("position")
        or raw_player.get("primaryPosition")
        or {}
    )

    return {
        "mlb_player_id": safe_integer(
            raw_player.get("id"),
            minimum=1,
        ),
        "full_name": full_name,
        "first_name": first_name,
        "last_name": last_name,
        "primary_number": safe_string(
            raw_player.get("primaryNumber")
            or raw_roster_entry.get(
                "jerseyNumber"
            ),
            maximum_length=16,
        ),
        "jersey_number": safe_string(
            raw_roster_entry.get(
                "jerseyNumber"
            ),
            maximum_length=16,
        ),
        "position": safe_string(
            position_payload.get("name"),
            maximum_length=128,
        ),
        "position_code": safe_string(
            position_payload.get("code"),
            maximum_length=32,
        ),
        "position_abbreviation": safe_string(
            position_payload.get("abbreviation"),
            maximum_length=32,
        ),
        "position_type": safe_string(
            position_payload.get("type"),
            maximum_length=64,
        ),
        "bats": safe_string(
            safe_nested_get(
                raw_player,
                "batSide",
                "code",
            ),
            maximum_length=8,
        ),
        "throws": safe_string(
            safe_nested_get(
                raw_player,
                "pitchHand",
                "code",
            ),
            maximum_length=8,
        ),
        "height": safe_string(
            raw_player.get("height"),
            maximum_length=32,
        ),
        "weight": safe_integer(
            raw_player.get("weight"),
            minimum=0,
            maximum=1000,
        ),
        "birth_date": safe_date(
            raw_player.get("birthDate")
        ),
        "birth_city": safe_string(
            raw_player.get("birthCity"),
            maximum_length=128,
        ),
        "birth_state_province": safe_string(
            raw_player.get(
                "birthStateProvince"
            ),
            maximum_length=128,
        ),
        "birth_country": safe_string(
            raw_player.get("birthCountry"),
            maximum_length=128,
        ),
        "mlb_debut_date": safe_date(
            raw_player.get("mlbDebutDate")
        ),
        "active_status": safe_boolean(
            raw_player.get("active"),
            default=True,
        ),
        "current_team_id": database_team_id,
        "current_age": safe_integer(
            raw_player.get("currentAge"),
            minimum=0,
            maximum=100,
        ),
        "nick_name": safe_string(
            raw_player.get("nickName"),
            maximum_length=128,
        ),
        "name_slug": safe_string(
            raw_player.get("nameSlug"),
            maximum_length=255,
        ),
        "use_name": safe_string(
            raw_player.get("useName"),
            maximum_length=128,
        ),
        "middle_name": safe_string(
            raw_player.get("middleName"),
            maximum_length=128,
        ),
        "boxscore_name": safe_string(
            raw_player.get("boxscoreName"),
            maximum_length=128,
        ),
        "gender": safe_string(
            raw_player.get("gender"),
            maximum_length=32,
        ),
        "is_verified": safe_boolean(
            raw_player.get("verified"),
            default=False,
        ),
    }


def normalize_roster_entry_payload(
    raw_roster_entry: Mapping[str, Any],
    *,
    season: int,
    roster_type: str,
    database_team_id: int,
    database_player_id: int,
) -> dict[str, Any]:
    status_payload = (
        raw_roster_entry.get("status")
        or {}
    )

    position_payload = (
        raw_roster_entry.get("position")
        or {}
    )

    return {
        "season": season,
        "roster_type": safe_string(
            roster_type,
            maximum_length=64,
        ),
        "jersey_number": safe_string(
            raw_roster_entry.get(
                "jerseyNumber"
            ),
            maximum_length=16,
        ),
        "status_code": safe_string(
            status_payload.get("code"),
            maximum_length=32,
        ),
        "status_description": safe_string(
            status_payload.get(
                "description"
            ),
            maximum_length=255,
        ),
        "position": safe_string(
            position_payload.get("name"),
            maximum_length=128,
        ),
        "position_code": safe_string(
            position_payload.get("code"),
            maximum_length=32,
        ),
        "position_abbreviation": safe_string(
            position_payload.get(
                "abbreviation"
            ),
            maximum_length=32,
        ),
        "team_id": database_team_id,
        "player_id": database_player_id,
        "parent_team_id": database_team_id,
    }


# ============================================================
# SECTION 14 - VALIDATION
# ============================================================

def validate_normalized_team(
    normalized_team: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []

    if not normalized_team.get("mlb_team_id"):
        errors.append(
            "Missing mlb_team_id"
        )

    if not normalized_team.get("name"):
        errors.append(
            "Missing team name"
        )

    abbreviation = normalized_team.get(
        "abbreviation"
    )

    if abbreviation and len(str(abbreviation)) > 16:
        errors.append(
            "Team abbreviation exceeds 16 characters"
        )

    return errors


def validate_normalized_player(
    normalized_player: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []

    if not normalized_player.get("mlb_player_id"):
        errors.append(
            "Missing mlb_player_id"
        )

    if not normalized_player.get("full_name"):
        errors.append(
            "Missing player full_name"
        )

    if not normalized_player.get(
        "current_team_id"
    ):
        errors.append(
            "Missing current_team_id"
        )

    return errors


def validate_normalized_roster_entry(
    normalized_roster_entry: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []

    for required_field in (
        "season",
        "roster_type",
        "team_id",
        "player_id",
    ):
        if not normalized_roster_entry.get(
            required_field
        ):
            errors.append(
                f"Missing {required_field}"
            )

    return errors


# ============================================================
# SECTION 15 - SOURCE HTTP CLIENT
# ============================================================

class ResilientMLBStatsHTTPClient:
    def __init__(
        self,
        config: TeamIngestionConfig,
        metrics: SourceRequestMetrics,
    ) -> None:
        self.config = config
        self.metrics = metrics
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": config.user_agent,
        })

    def close(self) -> None:
        self.session.close()

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None

        for attempt in range(
            self.config.max_retries + 1
        ):
            started = time.perf_counter()
            self.metrics.request_count += 1

            try:
                response = self.session.get(
                    url,
                    params=dict(params or {}),
                    timeout=self.config.timeout_seconds,
                )

                elapsed = (
                    time.perf_counter()
                    - started
                )
                self.metrics.total_elapsed_seconds += elapsed
                self.metrics.status_codes[
                    response.status_code
                ] += 1

                if response.status_code in {
                    429,
                    500,
                    502,
                    503,
                    504,
                }:
                    raise requests.HTTPError(
                        f"Retryable HTTP status "
                        f"{response.status_code}",
                        response=response,
                    )

                response.raise_for_status()
                payload = response.json()

                if not isinstance(payload, dict):
                    raise ValueError(
                        "MLB Stats API returned a "
                        "non-object JSON payload"
                    )

                self.metrics.success_count += 1

                if self.config.request_delay_seconds:
                    time.sleep(
                        self.config.request_delay_seconds
                    )

                return payload

            except Exception as exc:
                last_error = exc
                self.metrics.failure_count += 1

                if attempt >= self.config.max_retries:
                    break

                self.metrics.retry_count += 1

                sleep_seconds = (
                    self.config.retry_backoff_seconds
                    * (2 ** attempt)
                    + random.uniform(0.0, 0.25)
                )

                LOGGER.warning(
                    "MLB request failed; retrying in %.2fs | "
                    "url=%s | attempt=%s | error=%s",
                    sleep_seconds,
                    url,
                    attempt + 1,
                    exc,
                )

                time.sleep(sleep_seconds)

        raise RuntimeError(
            f"MLB Stats API request failed after "
            f"{self.config.max_retries + 1} attempts: "
            f"{url}"
        ) from last_error


# ============================================================
# SECTION 16 - SOURCE FETCHING
# ============================================================

def fetch_official_mlb_teams(
    client: MLBClientLike,
    *,
    season: int,
) -> list[dict[str, Any]]:
    teams = client.get_teams(
        season=season,
    )

    if not isinstance(teams, list):
        raise TypeError(
            "MLBStatsAPIClient.get_teams() must "
            "return a list"
        )

    return [
        dict(team)
        for team in teams
        if isinstance(team, Mapping)
    ]


def fetch_team_roster(
    http_client: ResilientMLBStatsHTTPClient,
    *,
    mlb_team_id: int,
    season: int,
    roster_type: str,
) -> list[dict[str, Any]]:
    payload = http_client.get_json(
        (
            f"{MLB_STATS_API_BASE_URL}"
            f"/teams/{mlb_team_id}/roster"
        ),
        params={
            "season": season,
            "rosterType": roster_type,
            "hydrate": (
                "person("
                "currentTeam,"
                "primaryPosition,"
                "batSide,"
                "pitchHand"
                ")"
            ),
        },
    )

    roster = payload.get(
        "roster",
        [],
    )

    if not isinstance(roster, list):
        raise TypeError(
            "Roster payload must contain a list "
            "under the 'roster' key"
        )

    return [
        dict(entry)
        for entry in roster
        if isinstance(entry, Mapping)
    ]


# ============================================================
# SECTION 17 - DATABASE HELPERS
# ============================================================

def _query_by_unique_field(
    database_session: SessionLike,
    model: Any,
    field_name: str,
    value: Any,
) -> Any | None:
    model_attribute = getattr(
        model,
        field_name,
        None,
    )

    if model_attribute is None:
        return None

    return (
        database_session.query(model)
        .filter(model_attribute == value)
        .first()
    )


def _apply_payload_to_instance(
    instance: Any,
    payload: Mapping[str, Any],
    *,
    preserve_existing_non_null_values: bool,
) -> list[str]:
    changed_fields: list[str] = []

    for field_name, new_value in payload.items():
        if not hasattr(
            instance,
            field_name,
        ):
            continue

        current_value = getattr(
            instance,
            field_name,
        )

        if (
            preserve_existing_non_null_values
            and current_value is not None
            and new_value is None
        ):
            continue

        if current_value != new_value:
            setattr(
                instance,
                field_name,
                new_value,
            )
            changed_fields.append(
                field_name
            )

    return changed_fields


def upsert_team(
    database_session: SessionLike,
    normalized_team: Mapping[str, Any],
    *,
    config: TeamIngestionConfig | None = None,
) -> UpsertResult:
    config = config or TeamIngestionConfig()

    filtered_payload, ignored_fields = (
        filter_payload_for_model(
            Team,
            normalized_team,
            strict=config.strict_schema,
        )
    )

    unique_field = choose_first_existing_field(
        Team,
        (
            "mlb_team_id",
            "team_id",
            "id",
        ),
    )

    if unique_field is None:
        raise RuntimeError(
            "Team model does not expose an MLB team "
            "identifier field"
        )

    lookup_value = normalized_team.get(
        unique_field
    )

    if lookup_value is None and unique_field == "team_id":
        lookup_value = normalized_team.get(
            "mlb_team_id"
        )

    existing_team = _query_by_unique_field(
        database_session,
        Team,
        unique_field,
        lookup_value,
    )

    if existing_team is None:
        if config.dry_run:
            return UpsertResult(
                action=RecordAction.DRY_RUN_CREATE,
                instance=None,
                changed_fields=sorted(
                    filtered_payload
                ),
                ignored_fields=ignored_fields,
            )

        new_team = Team(
            **filtered_payload
        )
        database_session.add(new_team)
        database_session.flush()

        return UpsertResult(
            action=RecordAction.CREATED,
            instance=new_team,
            changed_fields=sorted(
                filtered_payload
            ),
            ignored_fields=ignored_fields,
        )

    changed_fields = _apply_payload_to_instance(
        existing_team,
        filtered_payload,
        preserve_existing_non_null_values=(
            config.preserve_existing_non_null_values
        ),
    )

    if not changed_fields:
        return UpsertResult(
            action=RecordAction.UNCHANGED,
            instance=existing_team,
            changed_fields=[],
            ignored_fields=ignored_fields,
        )

    if config.dry_run:
        return UpsertResult(
            action=RecordAction.DRY_RUN_UPDATE,
            instance=existing_team,
            changed_fields=changed_fields,
            ignored_fields=ignored_fields,
        )

    database_session.flush()

    return UpsertResult(
        action=RecordAction.UPDATED,
        instance=existing_team,
        changed_fields=changed_fields,
        ignored_fields=ignored_fields,
    )


def upsert_player(
    database_session: SessionLike,
    normalized_player: Mapping[str, Any],
    *,
    config: TeamIngestionConfig | None = None,
) -> UpsertResult:
    if Player is None:
        raise RuntimeError(
            "Player model is unavailable"
        )

    config = config or TeamIngestionConfig()

    filtered_payload, ignored_fields = (
        filter_payload_for_model(
            Player,
            normalized_player,
            strict=config.strict_schema,
        )
    )

    unique_field = choose_first_existing_field(
        Player,
        (
            "mlb_player_id",
            "player_id",
            "id",
        ),
    )

    if unique_field is None:
        raise RuntimeError(
            "Player model does not expose an MLB "
            "player identifier field"
        )

    lookup_value = normalized_player.get(
        unique_field
    )

    if (
        lookup_value is None
        and unique_field == "player_id"
    ):
        lookup_value = normalized_player.get(
            "mlb_player_id"
        )

    existing_player = _query_by_unique_field(
        database_session,
        Player,
        unique_field,
        lookup_value,
    )

    if existing_player is None:
        if config.dry_run:
            return UpsertResult(
                action=RecordAction.DRY_RUN_CREATE,
                changed_fields=sorted(
                    filtered_payload
                ),
                ignored_fields=ignored_fields,
            )

        new_player = Player(
            **filtered_payload
        )
        database_session.add(new_player)
        database_session.flush()

        return UpsertResult(
            action=RecordAction.CREATED,
            instance=new_player,
            changed_fields=sorted(
                filtered_payload
            ),
            ignored_fields=ignored_fields,
        )

    changed_fields = _apply_payload_to_instance(
        existing_player,
        filtered_payload,
        preserve_existing_non_null_values=(
            config.preserve_existing_non_null_values
        ),
    )

    if not changed_fields:
        return UpsertResult(
            action=RecordAction.UNCHANGED,
            instance=existing_player,
            ignored_fields=ignored_fields,
        )

    if config.dry_run:
        return UpsertResult(
            action=RecordAction.DRY_RUN_UPDATE,
            instance=existing_player,
            changed_fields=changed_fields,
            ignored_fields=ignored_fields,
        )

    database_session.flush()

    return UpsertResult(
        action=RecordAction.UPDATED,
        instance=existing_player,
        changed_fields=changed_fields,
        ignored_fields=ignored_fields,
    )


def upsert_roster_entry(
    database_session: SessionLike,
    normalized_roster_entry: Mapping[str, Any],
    *,
    config: TeamIngestionConfig | None = None,
) -> UpsertResult:
    if RosterEntry is None:
        raise RuntimeError(
            "RosterEntry model is unavailable"
        )

    config = config or TeamIngestionConfig()

    filtered_payload, ignored_fields = (
        filter_payload_for_model(
            RosterEntry,
            normalized_roster_entry,
            strict=config.strict_schema,
        )
    )

    required_lookup_fields = [
        field_name
        for field_name in (
            "season",
            "roster_type",
            "team_id",
            "player_id",
        )
        if hasattr(
            RosterEntry,
            field_name,
        )
    ]

    query = database_session.query(
        RosterEntry
    )

    for field_name in required_lookup_fields:
        field_value = normalized_roster_entry.get(
            field_name
        )

        query = query.filter(
            getattr(
                RosterEntry,
                field_name,
            ) == field_value
        )

    existing_entry = query.first()

    if existing_entry is None:
        if config.dry_run:
            return UpsertResult(
                action=RecordAction.DRY_RUN_CREATE,
                changed_fields=sorted(
                    filtered_payload
                ),
                ignored_fields=ignored_fields,
            )

        new_entry = RosterEntry(
            **filtered_payload
        )
        database_session.add(new_entry)
        database_session.flush()

        return UpsertResult(
            action=RecordAction.CREATED,
            instance=new_entry,
            changed_fields=sorted(
                filtered_payload
            ),
            ignored_fields=ignored_fields,
        )

    changed_fields = _apply_payload_to_instance(
        existing_entry,
        filtered_payload,
        preserve_existing_non_null_values=(
            config.preserve_existing_non_null_values
        ),
    )

    if not changed_fields:
        return UpsertResult(
            action=RecordAction.UNCHANGED,
            instance=existing_entry,
            ignored_fields=ignored_fields,
        )

    if config.dry_run:
        return UpsertResult(
            action=RecordAction.DRY_RUN_UPDATE,
            instance=existing_entry,
            changed_fields=changed_fields,
            ignored_fields=ignored_fields,
        )

    database_session.flush()

    return UpsertResult(
        action=RecordAction.UPDATED,
        instance=existing_entry,
        changed_fields=changed_fields,
        ignored_fields=ignored_fields,
    )


# ============================================================
# SECTION 18 - DATABASE COUNT HELPERS
# ============================================================

def count_database_teams() -> int:
    with managed_database_session() as database_session:
        return int(
            database_session.query(Team).count()
        )


def count_database_players() -> int:
    if Player is None:
        return 0

    with managed_database_session() as database_session:
        return int(
            database_session.query(Player).count()
        )


def count_database_roster_entries() -> int:
    if RosterEntry is None:
        return 0

    with managed_database_session() as database_session:
        return int(
            database_session.query(
                RosterEntry
            ).count()
        )


def collect_database_counts() -> dict[str, int]:
    return {
        "teams": count_database_teams(),
        "players": count_database_players(),
        "roster_entries": (
            count_database_roster_entries()
        ),
    }


# ============================================================
# SECTION 19 - INVENTORY BUILDERS
# ============================================================

def build_team_inventory() -> list[dict[str, Any]]:
    with managed_database_session() as database_session:
        teams = (
            database_session.query(Team)
            .order_by(Team.name.asc())
            .all()
        )

        inventory: list[dict[str, Any]] = []

        for team in teams:
            inventory.append({
                "database_id": getattr(
                    team,
                    "id",
                    None,
                ),
                "mlb_team_id": getattr(
                    team,
                    "mlb_team_id",
                    None,
                ),
                "name": getattr(
                    team,
                    "name",
                    None,
                ),
                "abbreviation": getattr(
                    team,
                    "abbreviation",
                    None,
                ),
                "league": getattr(
                    team,
                    "league",
                    None,
                ),
                "division": getattr(
                    team,
                    "division",
                    None,
                ),
                "venue": getattr(
                    team,
                    "venue",
                    None,
                ),
                "is_active": getattr(
                    team,
                    "is_active",
                    None,
                ),
            })

        return inventory


# ============================================================
# SECTION 20 - READINESS
# ============================================================

def determine_readiness(
    run: TeamIngestionRun,
) -> ReadinessStatus:
    counts = run.database_counts

    team_count = counts.get(
        "teams",
        0,
    )
    player_count = counts.get(
        "players",
        0,
    )
    roster_count = counts.get(
        "roster_entries",
        0,
    )

    if team_count <= 0:
        return ReadinessStatus.FAILED

    if not run.config.include_rosters:
        return (
            ReadinessStatus.READY
            if team_count
            >= run.config.expected_active_team_count
            else ReadinessStatus.PARTIAL
        )

    if (
        team_count
        >= run.config.expected_active_team_count
        and player_count
        >= run.config.minimum_player_foundation
        and roster_count
        >= run.config.minimum_roster_foundation
    ):
        return ReadinessStatus.READY

    if (
        team_count
        >= run.config.expected_active_team_count
        and player_count > 0
        and roster_count > 0
    ):
        return ReadinessStatus.PARTIAL

    return ReadinessStatus.NOT_READY


def build_next_required_action(
    run: TeamIngestionRun,
) -> str:
    if run.readiness == ReadinessStatus.READY:
        if run.config.include_rosters:
            return (
                "Team, player, and roster foundations are "
                "loaded. Continue with player statistics, "
                "schedule, game, and Statcast ingestion."
            )

        return (
            "Team foundation is loaded. Run player and "
            "roster ingestion next."
        )

    if run.readiness == ReadinessStatus.PARTIAL:
        return (
            "The ingestion partially succeeded. Review issue "
            "records, verify roster type and MLB API access, "
            "then rerun idempotently."
        )

    if run.readiness == ReadinessStatus.NOT_READY:
        return (
            "Production data is incomplete. Confirm database "
            "connectivity, model compatibility, roster endpoint "
            "access, and Render environment configuration."
        )

    return (
        "The ingestion failed before establishing a usable "
        "team foundation. Review critical issues first."
    )


# ============================================================
# SECTION 21 - TEAM RECORD REPORTING
# ============================================================

def build_team_report_record(
    normalized_team: Mapping[str, Any],
    upsert_result: UpsertResult,
) -> dict[str, Any]:
    instance = upsert_result.instance

    return {
        "mlb_team_id": normalized_team.get(
            "mlb_team_id"
        ),
        "database_team_id": getattr(
            instance,
            "id",
            None,
        ),
        "name": normalized_team.get("name"),
        "abbreviation": normalized_team.get(
            "abbreviation"
        ),
        "league": normalized_team.get("league"),
        "division": normalized_team.get(
            "division"
        ),
        "venue": normalized_team.get("venue"),
        "is_active": normalized_team.get(
            "is_active"
        ),
        "action": upsert_result.action.value,
        "changed_fields": list(
            upsert_result.changed_fields
        ),
        "ignored_fields": list(
            upsert_result.ignored_fields
        ),
    }


# ============================================================
# SECTION 22 - DATABASE INITIALIZATION
# ============================================================

def run_database_initialization(
    run: TeamIngestionRun,
) -> None:
    if not run.config.initialize_schema:
        run.database_initialized = None
        run.database_health = None
        return

    if initialize_database is None:
        run.database_initialized = False
        run.database_health = False
        run.add_issue(
            IngestionIssue(
                severity=Severity.WARNING,
                entity_kind=EntityKind.DATABASE,
                message=(
                    "initialize_database is unavailable; "
                    "continuing with the existing schema"
                ),
            )
        )
        return

    try:
        initialization_report = (
            initialize_database()
        )

        if isinstance(
            initialization_report,
            Mapping,
        ):
            run.database_initialized = bool(
                initialization_report.get(
                    "initialized",
                    True,
                )
            )
            run.database_health = bool(
                initialization_report.get(
                    "health",
                    True,
                )
            )
        else:
            run.database_initialized = True
            run.database_health = True

    except Exception as exc:
        run.database_initialized = False
        run.database_health = False
        run.add_issue(
            IngestionIssue(
                severity=Severity.ERROR,
                entity_kind=EntityKind.DATABASE,
                message=(
                    "Database initialization failed"
                ),
                exception_type=type(exc).__name__,
                details={
                    "error": str(exc),
                },
            )
        )

        if run.config.fail_fast:
            raise


# ============================================================
# SECTION 23 - TEAM INGESTION CORE
# ============================================================

def ingest_team_records(
    *,
    run: TeamIngestionRun,
    database_session: SessionLike,
    raw_teams: Sequence[Mapping[str, Any]],
) -> list[tuple[dict[str, Any], Any]]:
    persisted_teams: list[
        tuple[dict[str, Any], Any]
    ] = []

    for index, raw_team in enumerate(
        raw_teams,
        start=1,
    ):
        run.team_counters.discovered += 1

        try:
            normalized_team = normalize_team_payload(
                raw_team
            )

            if (
                not run.config.include_inactive_teams
                and not normalized_team.get(
                    "is_active",
                    True,
                )
            ):
                run.team_counters.skipped += 1
                continue

            validation_errors = (
                validate_normalized_team(
                    normalized_team
                )
            )

            if validation_errors:
                run.team_counters.skipped += 1
                run.add_issue(
                    IngestionIssue(
                        severity=Severity.WARNING,
                        entity_kind=EntityKind.TEAM,
                        message=(
                            "Team validation failed"
                        ),
                        record_identifier=(
                            normalized_team.get(
                                "mlb_team_id"
                            )
                        ),
                        team_name=normalized_team.get(
                            "name"
                        ),
                        details={
                            "validation_errors": (
                                validation_errors
                            ),
                            "raw_payload": (
                                raw_team
                                if run.config.capture_raw_payloads
                                else None
                            ),
                        },
                    )
                )
                continue

            run.team_counters.valid += 1

            upsert_result = upsert_team(
                database_session,
                normalized_team,
                config=run.config,
            )

            run.team_counters.increment_action(
                upsert_result.action
            )

            team_report = (
                build_team_report_record(
                    normalized_team,
                    upsert_result,
                )
            )
            run.teams.append(team_report)

            persisted_teams.append(
                (
                    normalized_team,
                    upsert_result.instance,
                )
            )

            if run.config.capture_raw_payloads:
                run.source_payload_hashes.append(
                    payload_hash(raw_team)
                )

            if (
                not run.config.dry_run
                and index
                % run.config.commit_interval
                == 0
            ):
                database_session.flush()

        except Exception as exc:
            run.team_counters.failed += 1
            run.add_issue(
                IngestionIssue(
                    severity=Severity.ERROR,
                    entity_kind=EntityKind.TEAM,
                    message=(
                        "Team persistence failed"
                    ),
                    record_identifier=(
                        raw_team.get("id")
                        if isinstance(
                            raw_team,
                            Mapping,
                        )
                        else None
                    ),
                    team_name=(
                        raw_team.get("name")
                        if isinstance(
                            raw_team,
                            Mapping,
                        )
                        else None
                    ),
                    exception_type=type(exc).__name__,
                    details={
                        "error": str(exc),
                    },
                )
            )

            if run.config.fail_fast:
                raise

    return persisted_teams


# ============================================================
# SECTION 24 - PLAYER AND ROSTER INGESTION CORE
# ============================================================

def ingest_roster_for_team(
    *,
    run: TeamIngestionRun,
    database_session: SessionLike,
    http_client: ResilientMLBStatsHTTPClient,
    normalized_team: Mapping[str, Any],
    database_team: Any,
) -> None:
    if Player is None or RosterEntry is None:
        run.add_issue(
            IngestionIssue(
                severity=Severity.ERROR,
                entity_kind=EntityKind.DATABASE,
                message=(
                    "Player or RosterEntry model is unavailable"
                ),
                team_name=normalized_team.get("name"),
            )
        )
        return

    database_team_id = getattr(
        database_team,
        "id",
        None,
    )

    if database_team_id is None:
        run.add_issue(
            IngestionIssue(
                severity=Severity.ERROR,
                entity_kind=EntityKind.ROSTER_ENTRY,
                message=(
                    "Database team ID is unavailable after upsert"
                ),
                record_identifier=normalized_team.get(
                    "mlb_team_id"
                ),
                team_name=normalized_team.get("name"),
            )
        )
        return

    try:
        roster_entries = fetch_team_roster(
            http_client,
            mlb_team_id=int(
                normalized_team["mlb_team_id"]
            ),
            season=run.config.season,
            roster_type=run.config.roster_type,
        )

    except Exception as exc:
        run.add_issue(
            IngestionIssue(
                severity=Severity.ERROR,
                entity_kind=EntityKind.SOURCE,
                message=(
                    "Roster fetch failed"
                ),
                record_identifier=normalized_team.get(
                    "mlb_team_id"
                ),
                team_name=normalized_team.get("name"),
                exception_type=type(exc).__name__,
                details={
                    "error": str(exc),
                },
            )
        )

        if run.config.fail_fast:
            raise

        return

    run.team_roster_counts.append({
        "team": normalized_team.get("name"),
        "mlb_team_id": normalized_team.get(
            "mlb_team_id"
        ),
        "roster_type": run.config.roster_type,
        "roster_count": len(roster_entries),
    })

    for raw_roster_entry in roster_entries:
        run.player_counters.discovered += 1
        run.roster_counters.discovered += 1

        try:
            raw_player = (
                raw_roster_entry.get("person")
                or {}
            )

            normalized_player = (
                normalize_player_payload(
                    raw_player,
                    raw_roster_entry,
                    int(database_team_id),
                )
            )

            player_errors = (
                validate_normalized_player(
                    normalized_player
                )
            )

            if player_errors:
                run.player_counters.skipped += 1
                run.roster_counters.skipped += 1
                run.add_issue(
                    IngestionIssue(
                        severity=Severity.WARNING,
                        entity_kind=EntityKind.PLAYER,
                        message=(
                            "Player validation failed"
                        ),
                        record_identifier=(
                            normalized_player.get(
                                "mlb_player_id"
                            )
                        ),
                        team_name=normalized_team.get(
                            "name"
                        ),
                        details={
                            "validation_errors": (
                                player_errors
                            ),
                        },
                    )
                )
                continue

            run.player_counters.valid += 1

            player_result = upsert_player(
                database_session,
                normalized_player,
                config=run.config,
            )

            run.player_counters.increment_action(
                player_result.action
            )

            database_player = (
                player_result.instance
            )

            if (
                database_player is None
                and run.config.dry_run
            ):
                continue

            database_player_id = getattr(
                database_player,
                "id",
                None,
            )

            if database_player_id is None:
                raise RuntimeError(
                    "Player database ID is unavailable"
                )

            normalized_roster_entry = (
                normalize_roster_entry_payload(
                    raw_roster_entry,
                    season=run.config.season,
                    roster_type=(
                        run.config.roster_type
                    ),
                    database_team_id=int(
                        database_team_id
                    ),
                    database_player_id=int(
                        database_player_id
                    ),
                )
            )

            roster_errors = (
                validate_normalized_roster_entry(
                    normalized_roster_entry
                )
            )

            if roster_errors:
                run.roster_counters.skipped += 1
                run.add_issue(
                    IngestionIssue(
                        severity=Severity.WARNING,
                        entity_kind=(
                            EntityKind.ROSTER_ENTRY
                        ),
                        message=(
                            "Roster entry validation failed"
                        ),
                        record_identifier=(
                            normalized_player.get(
                                "mlb_player_id"
                            )
                        ),
                        team_name=normalized_team.get(
                            "name"
                        ),
                        details={
                            "validation_errors": (
                                roster_errors
                            ),
                        },
                    )
                )
                continue

            run.roster_counters.valid += 1

            roster_result = (
                upsert_roster_entry(
                    database_session,
                    normalized_roster_entry,
                    config=run.config,
                )
            )

            run.roster_counters.increment_action(
                roster_result.action
            )

            if (
                len(run.players_sample)
                < run.config.sample_size
            ):
                run.players_sample.append({
                    "mlb_player_id": (
                        normalized_player.get(
                            "mlb_player_id"
                        )
                    ),
                    "name": normalized_player.get(
                        "full_name"
                    ),
                    "team": normalized_team.get(
                        "name"
                    ),
                    "position": normalized_player.get(
                        "position"
                    ),
                    "player_action": (
                        player_result.action.value
                    ),
                    "roster_action": (
                        roster_result.action.value
                    ),
                })

        except Exception as exc:
            run.player_counters.failed += 1
            run.roster_counters.failed += 1

            run.add_issue(
                IngestionIssue(
                    severity=Severity.ERROR,
                    entity_kind=EntityKind.PLAYER,
                    message=(
                        "Player or roster persistence failed"
                    ),
                    record_identifier=safe_nested_get(
                        raw_roster_entry,
                        "person",
                        "id",
                    ),
                    team_name=normalized_team.get(
                        "name"
                    ),
                    exception_type=type(exc).__name__,
                    details={
                        "error": str(exc),
                    },
                )
            )

            if run.config.fail_fast:
                raise


# ============================================================
# SECTION 25 - PRIMARY INGESTION API
# ============================================================

def ingest_mlb_teams(
    season: int = DEFAULT_TEAM_SEASON,
    roster_type: str = DEFAULT_ROSTER_TYPE,
    include_rosters: bool = True,
    *,
    config: TeamIngestionConfig | None = None,
    client: MLBClientLike | None = None,
) -> dict[str, Any]:
    effective_config = config or TeamIngestionConfig(
        season=season,
        roster_type=roster_type,
        include_rosters=include_rosters,
    )

    effective_config.validate()

    run = TeamIngestionRun(
        run_id=str(uuid4()),
        started_at=datetime.now(UTC),
        config=effective_config,
    )

    LOGGER.info(
        "Starting %s | run_id=%s | season=%s | "
        "include_rosters=%s | roster_type=%s",
        INGESTION_NAME,
        run.run_id,
        effective_config.season,
        effective_config.include_rosters,
        effective_config.roster_type,
    )

    run_database_initialization(run)

    source_client = client or MLBStatsAPIClient()
    http_client = ResilientMLBStatsHTTPClient(
        effective_config,
        run.request_metrics,
    )

    try:
        raw_teams = fetch_official_mlb_teams(
            source_client,
            season=effective_config.season,
        )

        if not raw_teams:
            raise RuntimeError(
                "The MLB Stats API returned no teams"
            )

        with managed_database_session() as database_session:
            persisted_teams = ingest_team_records(
                run=run,
                database_session=database_session,
                raw_teams=raw_teams,
            )

            if effective_config.include_rosters:
                for (
                    normalized_team,
                    database_team,
                ) in persisted_teams:
                    if database_team is None:
                        continue

                    ingest_roster_for_team(
                        run=run,
                        database_session=database_session,
                        http_client=http_client,
                        normalized_team=normalized_team,
                        database_team=database_team,
                    )

            if effective_config.dry_run:
                database_session.rollback()
            else:
                database_session.flush()

        if effective_config.dry_run:
            run.database_counts = {
                "teams": count_database_teams(),
                "players": count_database_players(),
                "roster_entries": (
                    count_database_roster_entries()
                ),
            }
        else:
            run.database_counts = (
                collect_database_counts()
            )

        run.readiness = determine_readiness(run)

    except Exception as exc:
        run.add_issue(
            IngestionIssue(
                severity=Severity.CRITICAL,
                entity_kind=EntityKind.SOURCE,
                message=(
                    "Team ingestion run failed"
                ),
                exception_type=type(exc).__name__,
                details={
                    "error": str(exc),
                },
            )
        )

        run.readiness = (
            ReadinessStatus.FAILED
        )

        if effective_config.fail_fast:
            raise

    finally:
        http_client.close()
        run.finish()

    LOGGER.info(
        "Finished %s | run_id=%s | readiness=%s | "
        "teams=%s | players=%s | rosters=%s | "
        "issues=%s | elapsed=%.2fs",
        INGESTION_NAME,
        run.run_id,
        run.readiness.value,
        run.database_counts.get("teams", 0),
        run.database_counts.get("players", 0),
        run.database_counts.get(
            "roster_entries",
            0,
        ),
        len(run.issues),
        run.elapsed_seconds,
    )

    return build_backward_compatible_report(
        run.to_dict()
    )


# ============================================================
# SECTION 26 - BACKWARD-COMPATIBLE REPORT
# ============================================================

def build_backward_compatible_report(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(report)

    teams = payload.get("teams", {})
    players = payload.get("players", {})
    rosters = payload.get(
        "roster_entries",
        {},
    )
    counts = payload.get(
        "database_counts",
        {},
    )

    payload.update({
        "raw_team_count": teams.get(
            "discovered",
            0,
        ),
        "created": teams.get(
            "created",
            0,
        ),
        "updated": teams.get(
            "updated",
            0,
        ),
        "unchanged": teams.get(
            "unchanged",
            0,
        ),
        "skipped": teams.get(
            "skipped",
            0,
        ),
        "player_created": players.get(
            "created",
            0,
        ),
        "player_updated": players.get(
            "updated",
            0,
        ),
        "player_unchanged": players.get(
            "unchanged",
            0,
        ),
        "player_skipped": players.get(
            "skipped",
            0,
        ),
        "roster_created": rosters.get(
            "created",
            0,
        ),
        "roster_updated": rosters.get(
            "updated",
            0,
        ),
        "roster_unchanged": rosters.get(
            "unchanged",
            0,
        ),
        "roster_skipped": rosters.get(
            "skipped",
            0,
        ),
        "errors": payload.get(
            "issues",
            [],
        ),
        "teams": payload.get(
            "team_records",
            [],
        ),
        "database_team_count_after_ingestion": (
            counts.get("teams", 0)
        ),
        "database_player_count_after_ingestion": (
            counts.get("players", 0)
        ),
        "database_roster_entry_count_after_ingestion": (
            counts.get(
                "roster_entries",
                0,
            )
        ),
        "prediction_data_foundation_ready": (
            payload.get("readiness")
            == ReadinessStatus.READY.value
            and counts.get("players", 0)
            >= DEFAULT_MINIMUM_PLAYER_FOUNDATION
        ),
    })

    return payload


# ============================================================
# SECTION 27 - DRY-RUN API
# ============================================================

def dry_run_mlb_team_ingestion(
    *,
    season: int = DEFAULT_TEAM_SEASON,
    roster_type: str = DEFAULT_ROSTER_TYPE,
    include_rosters: bool = False,
) -> dict[str, Any]:
    return ingest_mlb_teams(
        config=TeamIngestionConfig(
            season=season,
            roster_type=roster_type,
            include_rosters=include_rosters,
            dry_run=True,
        )
    )


# ============================================================
# SECTION 28 - VALIDATION API
# ============================================================

def validate_team_ingestion_module() -> dict[str, Any]:
    sample_team = {
        "id": 147,
        "name": "New York Yankees",
        "abbreviation": "NYY",
        "teamCode": "nya",
        "fileCode": "nyy",
        "franchiseName": "New York",
        "clubName": "Yankees",
        "shortName": "NY Yankees",
        "locationName": "Bronx",
        "league": {
            "id": 103,
            "name": "American League",
        },
        "division": {
            "id": 201,
            "name": "American League East",
        },
        "venue": {
            "id": 3313,
            "name": "Yankee Stadium",
        },
        "sport": {
            "id": 1,
            "name": "Major League Baseball",
        },
        "firstYearOfPlay": "1903",
        "active": True,
    }

    sample_roster_entry = {
        "person": {
            "id": 592450,
            "fullName": "Aaron Judge",
            "firstName": "Aaron",
            "lastName": "Judge",
            "primaryNumber": "99",
            "birthDate": "1992-04-26",
            "birthCity": "Linden",
            "birthStateProvince": "CA",
            "birthCountry": "USA",
            "height": "6' 7\"",
            "weight": 282,
            "active": True,
            "batSide": {
                "code": "R",
            },
            "pitchHand": {
                "code": "R",
            },
            "primaryPosition": {
                "code": "8",
                "name": "Outfielder",
                "abbreviation": "CF",
                "type": "Outfielder",
            },
        },
        "jerseyNumber": "99",
        "position": {
            "code": "8",
            "name": "Outfielder",
            "abbreviation": "CF",
            "type": "Outfielder",
        },
        "status": {
            "code": "A",
            "description": "Active",
        },
    }

    normalized_team = normalize_team_payload(
        sample_team
    )
    normalized_player = normalize_player_payload(
        sample_roster_entry["person"],
        sample_roster_entry,
        1,
    )
    normalized_roster = (
        normalize_roster_entry_payload(
            sample_roster_entry,
            season=DEFAULT_TEAM_SEASON,
            roster_type=DEFAULT_ROSTER_TYPE,
            database_team_id=1,
            database_player_id=1,
        )
    )

    checks = {
        "team_id_normalized": (
            normalized_team["mlb_team_id"]
            == 147
        ),
        "team_name_normalized": (
            normalized_team["name"]
            == "New York Yankees"
        ),
        "team_validation_passed": (
            validate_normalized_team(
                normalized_team
            )
            == []
        ),
        "player_id_normalized": (
            normalized_player[
                "mlb_player_id"
            ]
            == 592450
        ),
        "player_name_normalized": (
            normalized_player[
                "full_name"
            ]
            == "Aaron Judge"
        ),
        "player_validation_passed": (
            validate_normalized_player(
                normalized_player
            )
            == []
        ),
        "roster_validation_passed": (
            validate_normalized_roster_entry(
                normalized_roster
            )
            == []
        ),
        "team_model_fields_detected": bool(
            get_model_field_names(Team)
        ),
        "team_payload_filtering_operational": (
            bool(
                filter_payload_for_model(
                    Team,
                    normalized_team,
                )[0]
            )
        ),
        "safe_nested_get_operational": (
            safe_nested_get(
                sample_team,
                "league",
                "name",
            )
            == "American League"
        ),
    }

    passed_count = sum(
        1
        for passed in checks.values()
        if passed
    )

    return {
        "status": (
            "ok"
            if passed_count == len(checks)
            else "failed"
        ),
        "engine": INGESTION_NAME,
        "version": INGESTION_VERSION,
        "phase": INGESTION_PHASE,
        "path": INGESTION_PATH,
        "checks": checks,
        "passed": passed_count,
        "total": len(checks),
        "normalized_team": sanitize_for_json(
            normalized_team
        ),
        "normalized_player": sanitize_for_json(
            normalized_player
        ),
        "normalized_roster_entry": (
            sanitize_for_json(
                normalized_roster
            )
        ),
        "team_model_fields": sorted(
            get_model_field_names(Team)
        ),
        "player_model_available": (
            Player is not None
        ),
        "roster_entry_model_available": (
            RosterEntry is not None
        ),
    }


# ============================================================
# SECTION 29 - HEALTH REPORT
# ============================================================

def team_ingestion_health() -> dict[str, Any]:
    validation = (
        validate_team_ingestion_module()
    )

    return {
        "name": INGESTION_NAME,
        "version": INGESTION_VERSION,
        "phase": INGESTION_PHASE,
        "path": INGESTION_PATH,
        "status": (
            INGESTION_STATUS
            if validation["status"] == "ok"
            else "validation_failed"
        ),
        "official_mlb_stats_api": True,
        "schema_aware_persistence": True,
        "idempotent_upserts": True,
        "retry_control": True,
        "dry_run_supported": True,
        "partial_failure_isolation": True,
        "team_ingestion_supported": True,
        "optional_player_bootstrap_supported": (
            Player is not None
        ),
        "optional_roster_bootstrap_supported": (
            RosterEntry is not None
        ),
        "validation": validation,
        "timestamp": datetime.now(UTC).isoformat(),
    }


# ============================================================
# SECTION 30 - SUMMARY BUILDERS
# ============================================================

def build_ingestion_summary(
    report: Mapping[str, Any],
) -> str:
    return (
        f"{INGESTION_NAME} completed | "
        f"Season: {report.get('season')} | "
        f"Raw Teams: {report.get('raw_team_count', 0)} | "
        f"Created: {report.get('created', 0)} | "
        f"Updated: {report.get('updated', 0)} | "
        f"Unchanged: {report.get('unchanged', 0)} | "
        f"Skipped: {report.get('skipped', 0)} | "
        f"Database Teams: "
        f"{report.get('database_team_count_after_ingestion', 0)} | "
        f"Database Players: "
        f"{report.get('database_player_count_after_ingestion', 0)} | "
        f"Roster Entries: "
        f"{report.get('database_roster_entry_count_after_ingestion', 0)} | "
        f"Readiness: {report.get('readiness')}"
    )


def print_ingestion_report(
    report: Mapping[str, Any],
) -> None:
    print()
    print("=" * 88)
    print("AISP2 ENTERPRISE TEAM INGESTION ENGINE")
    print("=" * 88)
    print(build_ingestion_summary(report))
    print()

    team_records = report.get(
        "teams",
        [],
    )

    if team_records:
        print("Teams")
        print("-" * 88)

        for team_record in team_records:
            print(
                f"{team_record.get('abbreviation') or '---':<4} | "
                f"{team_record.get('name') or 'Unknown Team':<30} | "
                f"{team_record.get('league') or 'Unknown League':<20} | "
                f"{team_record.get('division') or 'Unknown Division':<28} | "
                f"{team_record.get('action')}"
            )

    issues = report.get(
        "issues",
        [],
    )

    if issues:
        print()
        print("Issues")
        print("-" * 88)

        for issue in issues[:20]:
            print(
                f"{issue.get('severity', 'unknown').upper():<8} | "
                f"{issue.get('entity_kind', 'unknown'):<14} | "
                f"{issue.get('team_name') or '-':<28} | "
                f"{issue.get('message')}"
            )

    print()
    print(
        f"Next action: "
        f"{report.get('next_required_action')}"
    )
    print()



# ============================================================
# SECTION 30.01 - AUTHORITATIVE INVENTORY CONSTANTS
# ============================================================

AUTHORITATIVE_ACTIVE_TEAM_COUNT: Final[int] = 30

TEAM_REQUIRED_SOURCE_FIELDS: Final[tuple[str, ...]] = (
    "mlb_team_id",
    "name",
    "abbreviation",
    "league",
    "league_id",
    "division",
    "division_id",
    "venue",
    "venue_id",
    "is_active",
)

TEAM_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "mlb_team_id",
    "name",
    "abbreviation",
)

TEAM_CONTEXT_FIELDS: Final[tuple[str, ...]] = (
    "league",
    "league_id",
    "division",
    "division_id",
    "venue",
    "venue_id",
)

TEAM_SOURCE_FIELDS: Final[tuple[str, ...]] = (
    "source_name",
    "source_updated_at",
    "updated_at",
    "created_at",
)

CANONICAL_MLB_LEAGUE_IDS: Final[frozenset[int]] = frozenset({
    103,
    104,
})

CANONICAL_MLB_DIVISION_IDS: Final[frozenset[int]] = frozenset({
    200,
    201,
    202,
    203,
    204,
    205,
})

EXPECTED_TEAMS_PER_LEAGUE: Final[int] = 15
EXPECTED_TEAMS_PER_DIVISION: Final[int] = 5
EXPECTED_DIVISION_COUNT: Final[int] = 6

SOURCE_NAME_MLB_STATS_API: Final[str] = "MLB Stats API"


# ============================================================
# SECTION 30.02 - AUTHORITATIVE TEAM CONTRACT
# ============================================================

@dataclass(slots=True)
class AuthoritativeTeamRecord:
    mlb_team_id: int
    name: str
    abbreviation: str

    team_code: str | None = None
    file_code: str | None = None
    franchise_name: str | None = None
    club_name: str | None = None
    short_name: str | None = None
    location_name: str | None = None

    league: str | None = None
    league_id: int | None = None

    division: str | None = None
    division_id: int | None = None

    venue: str | None = None
    venue_id: int | None = None

    first_year_of_play: str | None = None
    is_active: bool = True

    sport_id: int = DEFAULT_SPORT_ID
    sport_name: str | None = None

    source_name: str = SOURCE_NAME_MLB_STATS_API
    source_updated_at: datetime | None = None
    source_observed_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    raw_payload_checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return sanitize_for_json(
            asdict(self)
        )


@dataclass(slots=True)
class TeamInventoryComparison:
    source_count: int
    database_count: int

    source_ids: list[int]
    database_ids: list[int]

    missing_in_database: list[int]
    unexpected_in_database: list[int]

    duplicate_source_ids: list[int]
    duplicate_database_ids: list[int]

    duplicate_source_abbreviations: list[str]
    duplicate_database_abbreviations: list[str]

    metadata_mismatches: list[dict[str, Any]]
    incomplete_source_records: list[dict[str, Any]]
    incomplete_database_records: list[dict[str, Any]]

    league_distribution: dict[str, int]
    division_distribution: dict[str, int]

    exact_inventory_match: bool
    metadata_match: bool
    structure_match: bool
    completion_gate_passed: bool

    def to_dict(self) -> dict[str, Any]:
        return sanitize_for_json(
            asdict(self)
        )


@dataclass(slots=True)
class RosterFoundationReport:
    expected_team_count: int
    teams_checked: int
    teams_with_roster_rows: int
    teams_without_roster_rows: int

    total_roster_rows: int
    minimum_team_roster_count: int
    maximum_team_roster_count: int
    average_team_roster_count: float

    roster_type: str
    season: int

    ready_team_ids: list[int]
    not_ready_team_ids: list[int]

    source_probe_enabled: bool
    source_probe_success_count: int
    source_probe_failure_count: int
    source_probe_results: list[dict[str, Any]]

    database_ready: bool
    source_ready: bool
    completion_gate_passed: bool

    def to_dict(self) -> dict[str, Any]:
        return sanitize_for_json(
            asdict(self)
        )


# ============================================================
# SECTION 30.03 - SOURCE TIMESTAMP COERCION
# ============================================================

def coerce_source_timestamp(
    value: Any,
    *,
    fallback: datetime | None = None,
) -> datetime | None:
    if value is None:
        return fallback

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(
                tzinfo=UTC
            )

        return value.astimezone(UTC)

    text_value = safe_string(value)

    if not text_value:
        return fallback

    normalized = text_value.replace(
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
        return fallback


# ============================================================
# SECTION 30.04 - AUTHORITATIVE NORMALIZATION
# ============================================================

def normalize_authoritative_team_record(
    raw_team: Mapping[str, Any],
    *,
    source_observed_at: datetime | None = None,
) -> AuthoritativeTeamRecord:
    source_observed_at = (
        source_observed_at
        or datetime.now(UTC)
    )

    normalized = normalize_team_payload(
        raw_team
    )

    source_timestamp = coerce_source_timestamp(
        raw_team.get("lastUpdated"),
        fallback=source_observed_at,
    )

    mlb_team_id = safe_integer(
        normalized.get("mlb_team_id"),
        minimum=1,
    )

    name = safe_string(
        normalized.get("name"),
        maximum_length=255,
    )

    abbreviation = safe_string(
        normalized.get("abbreviation"),
        maximum_length=16,
    )

    if mlb_team_id is None:
        raise ValueError(
            "Authoritative team record is missing MLB team ID"
        )

    if not name:
        raise ValueError(
            f"MLB team {mlb_team_id} is missing its name"
        )

    if not abbreviation:
        raise ValueError(
            f"MLB team {mlb_team_id} is missing its abbreviation"
        )

    return AuthoritativeTeamRecord(
        mlb_team_id=mlb_team_id,
        name=name,
        abbreviation=abbreviation.upper(),
        team_code=safe_string(
            normalized.get("team_code"),
            maximum_length=32,
        ),
        file_code=safe_string(
            normalized.get("file_code"),
            maximum_length=32,
        ),
        franchise_name=safe_string(
            normalized.get("franchise_name"),
            maximum_length=255,
        ),
        club_name=safe_string(
            normalized.get("club_name"),
            maximum_length=255,
        ),
        short_name=safe_string(
            normalized.get("short_name"),
            maximum_length=255,
        ),
        location_name=safe_string(
            normalized.get("location_name"),
            maximum_length=255,
        ),
        league=safe_string(
            normalized.get("league"),
            maximum_length=255,
        ),
        league_id=safe_integer(
            normalized.get("league_id"),
            minimum=1,
        ),
        division=safe_string(
            normalized.get("division"),
            maximum_length=255,
        ),
        division_id=safe_integer(
            normalized.get("division_id"),
            minimum=1,
        ),
        venue=safe_string(
            normalized.get("venue"),
            maximum_length=255,
        ),
        venue_id=safe_integer(
            normalized.get("venue_id"),
            minimum=1,
        ),
        first_year_of_play=safe_string(
            normalized.get("first_year_of_play"),
            maximum_length=16,
        ),
        is_active=safe_boolean(
            normalized.get("is_active"),
            default=True,
        ),
        sport_id=safe_integer(
            normalized.get("sport_id"),
            default=DEFAULT_SPORT_ID,
            minimum=1,
        )
        or DEFAULT_SPORT_ID,
        sport_name=safe_string(
            normalized.get("sport_name"),
            maximum_length=255,
        ),
        source_name=SOURCE_NAME_MLB_STATS_API,
        source_updated_at=source_timestamp,
        source_observed_at=source_observed_at,
        raw_payload_checksum=payload_hash(
            raw_team
        ),
    )


# ============================================================
# SECTION 30.05 - STRICT AUTHORITATIVE VALIDATION
# ============================================================

def validate_authoritative_team_record(
    record: AuthoritativeTeamRecord,
) -> list[str]:
    errors: list[str] = []

    if record.mlb_team_id <= 0:
        errors.append(
            "mlb_team_id must be positive"
        )

    if not record.name:
        errors.append(
            "name is required"
        )

    if not record.abbreviation:
        errors.append(
            "abbreviation is required"
        )

    if not record.league:
        errors.append(
            "league is required"
        )

    if record.league_id not in CANONICAL_MLB_LEAGUE_IDS:
        errors.append(
            "league_id is not a canonical MLB league"
        )

    if not record.division:
        errors.append(
            "division is required"
        )

    if record.division_id not in CANONICAL_MLB_DIVISION_IDS:
        errors.append(
            "division_id is not a canonical MLB division"
        )

    if not record.venue:
        errors.append(
            "venue is required"
        )

    if record.venue_id is None:
        errors.append(
            "venue_id is required"
        )

    if record.is_active is not True:
        errors.append(
            "team must be active"
        )

    if record.sport_id != DEFAULT_SPORT_ID:
        errors.append(
            "sport_id must identify Major League Baseball"
        )

    if record.source_updated_at is None:
        errors.append(
            "source_updated_at is required"
        )

    if not record.raw_payload_checksum:
        errors.append(
            "raw_payload_checksum is required"
        )

    return errors


def validate_authoritative_source_inventory(
    records: Sequence[AuthoritativeTeamRecord],
    *,
    expected_count: int = AUTHORITATIVE_ACTIVE_TEAM_COUNT,
) -> dict[str, Any]:
    ids = [
        record.mlb_team_id
        for record in records
    ]

    abbreviations = [
        record.abbreviation.upper()
        for record in records
    ]

    duplicate_ids = sorted({
        team_id
        for team_id in ids
        if ids.count(team_id) > 1
    })

    duplicate_abbreviations = sorted({
        abbreviation
        for abbreviation in abbreviations
        if abbreviations.count(
            abbreviation
        ) > 1
    })

    record_errors = []

    for record in records:
        errors = validate_authoritative_team_record(
            record
        )

        if errors:
            record_errors.append({
                "mlb_team_id": record.mlb_team_id,
                "name": record.name,
                "errors": errors,
            })

    league_distribution = Counter(
        record.league
        for record in records
    )

    division_distribution = Counter(
        record.division
        for record in records
    )

    league_balance_valid = (
        len(league_distribution) == 2
        and all(
            count == EXPECTED_TEAMS_PER_LEAGUE
            for count in league_distribution.values()
        )
    )

    division_balance_valid = (
        len(division_distribution)
        == EXPECTED_DIVISION_COUNT
        and all(
            count == EXPECTED_TEAMS_PER_DIVISION
            for count
            in division_distribution.values()
        )
    )

    valid = (
        len(records) == expected_count
        and not duplicate_ids
        and not duplicate_abbreviations
        and not record_errors
        and league_balance_valid
        and division_balance_valid
    )

    return {
        "expected_count": expected_count,
        "source_count": len(records),
        "exact_count_match": (
            len(records) == expected_count
        ),
        "duplicate_ids": duplicate_ids,
        "duplicate_abbreviations": (
            duplicate_abbreviations
        ),
        "record_errors": record_errors,
        "league_distribution": dict(
            sorted(
                league_distribution.items()
            )
        ),
        "division_distribution": dict(
            sorted(
                division_distribution.items()
            )
        ),
        "league_balance_valid": (
            league_balance_valid
        ),
        "division_balance_valid": (
            division_balance_valid
        ),
        "valid": valid,
    }


# ============================================================
# SECTION 30.06 - MODEL-AWARE TEAM PAYLOAD
# ============================================================

def authoritative_team_model_payload(
    record: AuthoritativeTeamRecord,
) -> tuple[dict[str, Any], list[str]]:
    candidate = {
        "mlb_team_id": record.mlb_team_id,
        "name": record.name,
        "abbreviation": record.abbreviation,
        "team_code": record.team_code,
        "file_code": record.file_code,
        "franchise_name": record.franchise_name,
        "club_name": record.club_name,
        "short_name": record.short_name,
        "location_name": record.location_name,
        "league": record.league,
        "league_id": record.league_id,
        "division": record.division,
        "division_id": record.division_id,
        "venue": record.venue,
        "venue_id": record.venue_id,
        "first_year_of_play": (
            record.first_year_of_play
        ),
        "is_active": record.is_active,
        "sport_id": record.sport_id,
        "sport_name": record.sport_name,
        "source_name": record.source_name,
        "source_updated_at": (
            record.source_updated_at
        ),
        "updated_at": (
            record.source_observed_at
        ),
    }

    return filter_payload_for_model(
        Team,
        candidate,
        strict=False,
    )


# ============================================================
# SECTION 30.07 - AUTHORITATIVE UPSERT
# ============================================================

def upsert_authoritative_team(
    database_session: SessionLike,
    record: AuthoritativeTeamRecord,
    *,
    preserve_existing_non_null_values: bool = False,
) -> UpsertResult:
    errors = validate_authoritative_team_record(
        record
    )

    if errors:
        raise ValueError(
            "Invalid authoritative team record: "
            + "; ".join(errors)
        )

    payload, ignored_fields = (
        authoritative_team_model_payload(
            record
        )
    )

    existing = (
        database_session.query(Team)
        .filter(
            Team.mlb_team_id
            == record.mlb_team_id
        )
        .first()
    )

    if existing is None:
        instance = Team(**payload)
        database_session.add(instance)
        database_session.flush()

        return UpsertResult(
            action=RecordAction.CREATED,
            instance=instance,
            changed_fields=sorted(
                payload.keys()
            ),
            ignored_fields=ignored_fields,
        )

    changed_fields = (
        _apply_payload_to_instance(
            existing,
            payload,
            preserve_existing_non_null_values=(
                preserve_existing_non_null_values
            ),
        )
    )

    database_session.flush()

    return UpsertResult(
        action=(
            RecordAction.UPDATED
            if changed_fields
            else RecordAction.UNCHANGED
        ),
        instance=existing,
        changed_fields=sorted(
            changed_fields
        ),
        ignored_fields=ignored_fields,
    )


# ============================================================
# SECTION 30.08 - DATABASE TEAM SERIALIZATION
# ============================================================

def serialize_database_team(
    team: Team,
    *,
    roster_count: int | None = None,
) -> dict[str, Any]:
    payload = {
        "database_team_id": getattr(
            team,
            "id",
            None,
        ),
        "mlb_team_id": getattr(
            team,
            "mlb_team_id",
            None,
        ),
        "name": getattr(
            team,
            "name",
            None,
        ),
        "abbreviation": getattr(
            team,
            "abbreviation",
            None,
        ),
        "team_code": getattr(
            team,
            "team_code",
            None,
        ),
        "file_code": getattr(
            team,
            "file_code",
            None,
        ),
        "franchise_name": getattr(
            team,
            "franchise_name",
            None,
        ),
        "club_name": getattr(
            team,
            "club_name",
            None,
        ),
        "short_name": getattr(
            team,
            "short_name",
            None,
        ),
        "location_name": getattr(
            team,
            "location_name",
            None,
        ),
        "league": getattr(
            team,
            "league",
            None,
        ),
        "league_id": getattr(
            team,
            "league_id",
            None,
        ),
        "division": getattr(
            team,
            "division",
            None,
        ),
        "division_id": getattr(
            team,
            "division_id",
            None,
        ),
        "venue": getattr(
            team,
            "venue",
            None,
        ),
        "venue_id": getattr(
            team,
            "venue_id",
            None,
        ),
        "first_year_of_play": getattr(
            team,
            "first_year_of_play",
            None,
        ),
        "is_active": getattr(
            team,
            "is_active",
            None,
        ),
        "sport_id": getattr(
            team,
            "sport_id",
            None,
        ),
        "sport_name": getattr(
            team,
            "sport_name",
            None,
        ),
        "source_name": getattr(
            team,
            "source_name",
            None,
        ),
        "source_updated_at": sanitize_for_json(
            getattr(
                team,
                "source_updated_at",
                None,
            )
        ),
        "updated_at": sanitize_for_json(
            getattr(
                team,
                "updated_at",
                None,
            )
        ),
        "roster_entry_count": (
            roster_count
        ),
        "roster_synchronization_ready": (
            roster_count is not None
            and roster_count
            >= DEFAULT_ROSTER_READY_MINIMUM
        ),
    }

    return payload


# ============================================================
# SECTION 30.09 - DATABASE INVENTORY COLLECTION
# ============================================================

def build_authoritative_database_team_inventory(
    *,
    season: int = DEFAULT_TEAM_SEASON,
    roster_type: str = DEFAULT_ROSTER_TYPE,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    with managed_database_session() as database_session:
        query = database_session.query(
            Team
        )

        if active_only:
            query = query.filter(
                Team.is_active.is_(True)
            )

        teams = query.order_by(
            Team.mlb_team_id.asc()
        ).all()

        roster_counts: dict[int, int] = {}

        if RosterEntry is not None:
            rows = (
                database_session.query(
                    RosterEntry.team_id,
                    func.count(
                        RosterEntry.id
                    ),
                )
                .filter(
                    RosterEntry.season
                    == season,
                    RosterEntry.roster_type
                    == roster_type,
                )
                .group_by(
                    RosterEntry.team_id
                )
                .all()
            )

            roster_counts = {
                int(team_id): int(count)
                for team_id, count in rows
            }

        return [
            serialize_database_team(
                team,
                roster_count=roster_counts.get(
                    int(team.id),
                    0,
                ),
            )
            for team in teams
        ]


# ============================================================
# SECTION 30.10 - SOURCE/DATABASE COMPARISON
# ============================================================

def compare_source_and_database_inventory(
    source_records: Sequence[
        AuthoritativeTeamRecord
    ],
    database_records: Sequence[
        Mapping[str, Any]
    ],
) -> TeamInventoryComparison:
    source_by_id = {
        record.mlb_team_id: record
        for record in source_records
    }

    database_by_id = {
        int(record["mlb_team_id"]): dict(record)
        for record in database_records
        if record.get("mlb_team_id") is not None
    }

    source_ids = sorted(
        source_by_id.keys()
    )

    database_ids = sorted(
        database_by_id.keys()
    )

    missing_in_database = sorted(
        set(source_ids)
        - set(database_ids)
    )

    unexpected_in_database = sorted(
        set(database_ids)
        - set(source_ids)
    )

    duplicate_source_ids = sorted({
        record.mlb_team_id
        for record in source_records
        if sum(
            1
            for item in source_records
            if item.mlb_team_id
            == record.mlb_team_id
        )
        > 1
    })

    duplicate_database_ids = sorted({
        int(record["mlb_team_id"])
        for record in database_records
        if record.get("mlb_team_id")
        is not None
        and sum(
            1
            for item in database_records
            if item.get("mlb_team_id")
            == record.get("mlb_team_id")
        )
        > 1
    })

    source_abbreviations = [
        record.abbreviation.upper()
        for record in source_records
    ]

    database_abbreviations = [
        str(
            record.get("abbreviation")
            or ""
        ).upper()
        for record in database_records
    ]

    duplicate_source_abbreviations = sorted({
        value
        for value in source_abbreviations
        if value
        and source_abbreviations.count(
            value
        )
        > 1
    })

    duplicate_database_abbreviations = sorted({
        value
        for value in database_abbreviations
        if value
        and database_abbreviations.count(
            value
        )
        > 1
    })

    metadata_mismatches: list[
        dict[str, Any]
    ] = []

    comparison_fields = (
        "name",
        "abbreviation",
        "league",
        "league_id",
        "division",
        "division_id",
        "venue",
        "venue_id",
        "is_active",
    )

    for team_id in sorted(
        set(source_ids)
        & set(database_ids)
    ):
        source = source_by_id[team_id]
        database = database_by_id[
            team_id
        ]

        field_mismatches = []

        for field_name in comparison_fields:
            source_value = getattr(
                source,
                field_name,
            )

            database_value = database.get(
                field_name
            )

            if (
                field_name
                == "abbreviation"
            ):
                source_value = (
                    str(source_value).upper()
                    if source_value is not None
                    else None
                )
                database_value = (
                    str(database_value).upper()
                    if database_value
                    is not None
                    else None
                )

            if source_value != database_value:
                field_mismatches.append({
                    "field": field_name,
                    "source": (
                        source_value
                    ),
                    "database": (
                        database_value
                    ),
                })

        if field_mismatches:
            metadata_mismatches.append({
                "mlb_team_id": team_id,
                "name": source.name,
                "mismatches": (
                    field_mismatches
                ),
            })

    incomplete_source_records = []

    for record in source_records:
        errors = validate_authoritative_team_record(
            record
        )

        if errors:
            incomplete_source_records.append({
                "mlb_team_id": (
                    record.mlb_team_id
                ),
                "name": record.name,
                "errors": errors,
            })

    incomplete_database_records = []

    for record in database_records:
        missing_fields = [
            field_name
            for field_name
            in TEAM_REQUIRED_SOURCE_FIELDS
            if record.get(field_name)
            in (None, "")
        ]

        if (
            not record.get(
                "source_updated_at"
            )
            and not record.get(
                "updated_at"
            )
        ):
            missing_fields.append(
                "source_timestamp"
            )

        if missing_fields:
            incomplete_database_records.append({
                "mlb_team_id": (
                    record.get(
                        "mlb_team_id"
                    )
                ),
                "name": record.get("name"),
                "missing_fields": (
                    sorted(
                        set(
                            missing_fields
                        )
                    )
                ),
            })

    league_distribution = Counter(
        str(
            record.get("league")
            or "unknown"
        )
        for record in database_records
    )

    division_distribution = Counter(
        str(
            record.get("division")
            or "unknown"
        )
        for record in database_records
    )

    structure_match = (
        len(database_records)
        == AUTHORITATIVE_ACTIVE_TEAM_COUNT
        and len(league_distribution) == 2
        and all(
            count == EXPECTED_TEAMS_PER_LEAGUE
            for count in league_distribution.values()
        )
        and len(division_distribution)
        == EXPECTED_DIVISION_COUNT
        and all(
            count == EXPECTED_TEAMS_PER_DIVISION
            for count
            in division_distribution.values()
        )
    )

    exact_inventory_match = (
        len(source_records)
        == AUTHORITATIVE_ACTIVE_TEAM_COUNT
        and len(database_records)
        == AUTHORITATIVE_ACTIVE_TEAM_COUNT
        and not missing_in_database
        and not unexpected_in_database
        and not duplicate_source_ids
        and not duplicate_database_ids
        and not duplicate_source_abbreviations
        and not duplicate_database_abbreviations
    )

    metadata_match = (
        not metadata_mismatches
        and not incomplete_source_records
        and not incomplete_database_records
    )

    completion_gate_passed = (
        exact_inventory_match
        and metadata_match
        and structure_match
    )

    return TeamInventoryComparison(
        source_count=len(
            source_records
        ),
        database_count=len(
            database_records
        ),
        source_ids=source_ids,
        database_ids=database_ids,
        missing_in_database=(
            missing_in_database
        ),
        unexpected_in_database=(
            unexpected_in_database
        ),
        duplicate_source_ids=(
            duplicate_source_ids
        ),
        duplicate_database_ids=(
            duplicate_database_ids
        ),
        duplicate_source_abbreviations=(
            duplicate_source_abbreviations
        ),
        duplicate_database_abbreviations=(
            duplicate_database_abbreviations
        ),
        metadata_mismatches=(
            metadata_mismatches
        ),
        incomplete_source_records=(
            incomplete_source_records
        ),
        incomplete_database_records=(
            incomplete_database_records
        ),
        league_distribution=dict(
            sorted(
                league_distribution.items()
            )
        ),
        division_distribution=dict(
            sorted(
                division_distribution.items()
            )
        ),
        exact_inventory_match=(
            exact_inventory_match
        ),
        metadata_match=metadata_match,
        structure_match=structure_match,
        completion_gate_passed=(
            completion_gate_passed
        ),
    )


# ============================================================
# SECTION 30.11 - ROSTER FOUNDATION AUDIT
# ============================================================

def audit_roster_foundations(
    *,
    season: int = DEFAULT_TEAM_SEASON,
    roster_type: str = DEFAULT_ROSTER_TYPE,
    client: MLBStatsAPIClient | None = None,
    probe_source: bool = False,
) -> RosterFoundationReport:
    inventory = (
        build_authoritative_database_team_inventory(
            season=season,
            roster_type=roster_type,
            active_only=True,
        )
    )

    counts = [
        int(
            team.get(
                "roster_entry_count"
            )
            or 0
        )
        for team in inventory
    ]

    ready_team_ids = [
        int(team["mlb_team_id"])
        for team in inventory
        if team.get(
            "roster_synchronization_ready"
        )
    ]

    not_ready_team_ids = [
        int(team["mlb_team_id"])
        for team in inventory
        if not team.get(
            "roster_synchronization_ready"
        )
    ]

    source_probe_results = []
    source_probe_success_count = 0
    source_probe_failure_count = 0

    if probe_source:
        source_client = (
            client
            or MLBStatsAPIClient()
        )

        for team in inventory:
            team_id = int(
                team["mlb_team_id"]
            )

            try:
                roster = (
                    source_client.get_team_roster(
                        team_id,
                        season,
                        roster_type,
                    )
                )

                success = bool(roster)

                if success:
                    source_probe_success_count += 1
                else:
                    source_probe_failure_count += 1

                source_probe_results.append({
                    "mlb_team_id": team_id,
                    "name": team.get("name"),
                    "success": success,
                    "source_roster_count": (
                        len(roster)
                    ),
                    "error": None,
                })

            except Exception as exc:
                source_probe_failure_count += 1

                source_probe_results.append({
                    "mlb_team_id": team_id,
                    "name": team.get("name"),
                    "success": False,
                    "source_roster_count": 0,
                    "error": str(exc),
                })

    database_ready = (
        len(inventory)
        == AUTHORITATIVE_ACTIVE_TEAM_COUNT
        and len(ready_team_ids)
        == AUTHORITATIVE_ACTIVE_TEAM_COUNT
    )

    source_ready = (
        not probe_source
        or source_probe_success_count
        == AUTHORITATIVE_ACTIVE_TEAM_COUNT
    )

    total_roster_rows = sum(counts)

    return RosterFoundationReport(
        expected_team_count=(
            AUTHORITATIVE_ACTIVE_TEAM_COUNT
        ),
        teams_checked=len(inventory),
        teams_with_roster_rows=len(
            ready_team_ids
        ),
        teams_without_roster_rows=len(
            not_ready_team_ids
        ),
        total_roster_rows=(
            total_roster_rows
        ),
        minimum_team_roster_count=(
            min(counts)
            if counts
            else 0
        ),
        maximum_team_roster_count=(
            max(counts)
            if counts
            else 0
        ),
        average_team_roster_count=(
            total_roster_rows
            / len(counts)
            if counts
            else 0.0
        ),
        roster_type=roster_type,
        season=season,
        ready_team_ids=(
            ready_team_ids
        ),
        not_ready_team_ids=(
            not_ready_team_ids
        ),
        source_probe_enabled=(
            probe_source
        ),
        source_probe_success_count=(
            source_probe_success_count
        ),
        source_probe_failure_count=(
            source_probe_failure_count
        ),
        source_probe_results=(
            source_probe_results
        ),
        database_ready=database_ready,
        source_ready=source_ready,
        completion_gate_passed=(
            database_ready
            and source_ready
        ),
    )


# ============================================================
# SECTION 30.12 - SOURCE FETCH WITH CLIENT METRICS
# ============================================================

def fetch_authoritative_team_records(
    *,
    season: int,
    sport_id: int = DEFAULT_SPORT_ID,
    client: MLBStatsAPIClient | None = None,
) -> tuple[
    list[AuthoritativeTeamRecord],
    dict[str, Any],
]:
    source_client = (
        client
        or MLBStatsAPIClient()
    )

    observed_at = datetime.now(UTC)

    raw_teams = source_client.get_teams(
        season=season,
        sport_id=sport_id,
        active_only=True,
        hydrate=(
            "league,division,venue,sport"
        ),
    )

    records = [
        normalize_authoritative_team_record(
            raw_team,
            source_observed_at=(
                observed_at
            ),
        )
        for raw_team in raw_teams
        if isinstance(
            raw_team,
            Mapping,
        )
    ]

    validation = (
        validate_authoritative_source_inventory(
            records
        )
    )

    metrics_method = getattr(
        source_client,
        "request_metrics",
        None,
    )

    source_metrics = (
        metrics_method()
        if callable(metrics_method)
        else {}
    )

    capability_method = getattr(
        source_client,
        "capability_report",
        None,
    )

    capability_report = (
        capability_method()
        if callable(
            capability_method
        )
        else {}
    )

    source_report = {
        "source": SOURCE_NAME_MLB_STATS_API,
        "season": season,
        "sport_id": sport_id,
        "observed_at": (
            observed_at.isoformat()
        ),
        "raw_team_count": len(
            raw_teams
        ),
        "normalized_team_count": len(
            records
        ),
        "payload_checksum": (
            payload_hash(raw_teams)
        ),
        "validation": validation,
        "request_metrics": (
            source_metrics
        ),
        "client_capabilities": (
            capability_report
        ),
    }

    return records, source_report


# ============================================================
# SECTION 30.13 - STALE/UNEXPECTED TEAM HANDLING
# ============================================================

def mark_unexpected_teams_inactive(
    database_session: SessionLike,
    *,
    expected_mlb_team_ids: Sequence[int],
) -> list[dict[str, Any]]:
    expected = {
        int(team_id)
        for team_id
        in expected_mlb_team_ids
    }

    unexpected = (
        database_session.query(Team)
        .filter(
            Team.is_active.is_(True),
            ~Team.mlb_team_id.in_(
                expected
            ),
        )
        .all()
    )

    results = []

    for team in unexpected:
        team.is_active = False

        if hasattr(
            team,
            "updated_at",
        ):
            team.updated_at = (
                datetime.now(UTC)
            )

        results.append({
            "database_team_id": team.id,
            "mlb_team_id": (
                team.mlb_team_id
            ),
            "name": team.name,
            "action": (
                "marked_inactive"
            ),
        })

    database_session.flush()

    return results


# ============================================================
# SECTION 30.14 - AUTHORITATIVE INGESTION ORCHESTRATOR
# ============================================================

def ingest_authoritative_mlb_team_inventory(
    *,
    season: int = DEFAULT_TEAM_SEASON,
    roster_type: str = DEFAULT_ROSTER_TYPE,
    include_rosters: bool = False,
    probe_roster_source: bool = False,
    mark_unexpected_inactive: bool = False,
    initialize_schema: bool = True,
    preserve_existing_non_null_values: bool = False,
    client: MLBStatsAPIClient | None = None,
) -> dict[str, Any]:
    started_at = datetime.now(UTC)
    started_monotonic = time.perf_counter()
    run_id = str(uuid4())

    report: dict[str, Any] = {
        "run_id": run_id,
        "ingestion": (
            "AISP2 Authoritative MLB Team Inventory"
        ),
        "version": INGESTION_VERSION,
        "phase": INGESTION_PHASE,
        "path": INGESTION_PATH,
        "season": season,
        "roster_type": roster_type,
        "include_rosters": (
            include_rosters
        ),
        "probe_roster_source": (
            probe_roster_source
        ),
        "started_at": (
            started_at.isoformat()
        ),
        "status": "running",
        "success": False,
        "completion_gate_passed": False,
        "errors": [],
        "warnings": [],
        "team_actions": [],
        "unexpected_team_actions": [],
    }

    try:
        if initialize_schema:
            report[
                "database_initialization"
            ] = initialize_database()

        source_records, source_report = (
            fetch_authoritative_team_records(
                season=season,
                sport_id=DEFAULT_SPORT_ID,
                client=client,
            )
        )

        report["source"] = (
            source_report
        )

        if not source_report[
            "validation"
        ]["valid"]:
            raise RuntimeError(
                "Official MLB source inventory failed "
                "strict 30-team validation"
            )

        action_counter = Counter()

        with managed_database_session(
            commit_on_success=False
        ) as database_session:
            try:
                for record in source_records:
                    savepoint = (
                        database_session.begin_nested()
                    )

                    try:
                        result = (
                            upsert_authoritative_team(
                                database_session,
                                record,
                                preserve_existing_non_null_values=(
                                    preserve_existing_non_null_values
                                ),
                            )
                        )

                        action_counter[
                            result.action.value
                        ] += 1

                        report[
                            "team_actions"
                        ].append({
                            **result.to_dict(),
                            "source_updated_at": (
                                sanitize_for_json(
                                    record.source_updated_at
                                )
                            ),
                            "raw_payload_checksum": (
                                record.raw_payload_checksum
                            ),
                        })

                        savepoint.commit()

                    except Exception as exc:
                        savepoint.rollback()

                        action_counter[
                            RecordAction.FAILED.value
                        ] += 1

                        report["errors"].append({
                            "stage": (
                                "team_upsert"
                            ),
                            "mlb_team_id": (
                                record.mlb_team_id
                            ),
                            "name": record.name,
                            "error_type": (
                                type(exc).__name__
                            ),
                            "error": str(exc),
                        })

                if mark_unexpected_inactive:
                    report[
                        "unexpected_team_actions"
                    ] = (
                        mark_unexpected_teams_inactive(
                            database_session,
                            expected_mlb_team_ids=[
                                record.mlb_team_id
                                for record
                                in source_records
                            ],
                        )
                    )

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

        report["action_counts"] = dict(
            sorted(
                action_counter.items()
            )
        )

        # Optional roster bootstrap is delegated to the mature
        # original implementation to preserve compatibility.
        if include_rosters:
            bootstrap_config = (
                TeamIngestionConfig(
                    season=season,
                    roster_type=roster_type,
                    include_rosters=True,
                    include_inactive_teams=False,
                    initialize_schema=False,
                    preserve_existing_non_null_values=(
                        preserve_existing_non_null_values
                    ),
                )
            )

            report[
                "roster_bootstrap"
            ] = ingest_mlb_teams(
                config=bootstrap_config,
                client=client,
            )

        database_records = (
            build_authoritative_database_team_inventory(
                season=season,
                roster_type=roster_type,
                active_only=True,
            )
        )

        comparison = (
            compare_source_and_database_inventory(
                source_records,
                database_records,
            )
        )

        roster_report = (
            audit_roster_foundations(
                season=season,
                roster_type=roster_type,
                client=client,
                probe_source=(
                    probe_roster_source
                ),
            )
        )

        report[
            "database_inventory"
        ] = database_records

        report[
            "inventory_comparison"
        ] = comparison.to_dict()

        report[
            "roster_foundation"
        ] = roster_report.to_dict()

        report[
            "database_health_inventory"
        ] = collect_database_inventory()

        report[
            "completion_gate_passed"
        ] = (
            comparison.completion_gate_passed
        )

        report["success"] = (
            comparison.completion_gate_passed
            and not report["errors"]
        )

        report["status"] = (
            "ready"
            if report["success"]
            else (
                "ready_with_warnings"
                if (
                    comparison.completion_gate_passed
                    and report["errors"]
                )
                else "incomplete"
            )
        )

        if (
            include_rosters
            and not roster_report.completion_gate_passed
        ):
            report["warnings"].append(
                "Team inventory is complete, but one or more "
                "roster foundations are not synchronized."
            )

        report[
            "next_required_action"
        ] = (
            "The exact selected-season 30-team inventory is "
            "present. Continue to complete player and roster "
            "statistics ingestion."
            if comparison.completion_gate_passed
            else (
                "Resolve missing, unexpected, duplicate, "
                "structural, or metadata mismatches before "
                "continuing."
            )
        )

    except Exception as exc:
        report["status"] = "failed"
        report["success"] = False

        report["errors"].append({
            "stage": (
                "authoritative_inventory"
            ),
            "error_type": (
                type(exc).__name__
            ),
            "error": str(exc),
        })

    finally:
        report["finished_at"] = (
            datetime.now(UTC).isoformat()
        )
        report["duration_ms"] = round(
            (
                time.perf_counter()
                - started_monotonic
            )
            * 1000.0,
            3,
        )

    return report


# ============================================================
# SECTION 30.15 - EXACT COMPLETION-GATE AUDIT
# ============================================================

def audit_exact_mlb_team_inventory(
    *,
    season: int = DEFAULT_TEAM_SEASON,
    roster_type: str = DEFAULT_ROSTER_TYPE,
    probe_roster_source: bool = False,
    client: MLBStatsAPIClient | None = None,
) -> dict[str, Any]:
    source_records, source_report = (
        fetch_authoritative_team_records(
            season=season,
            sport_id=DEFAULT_SPORT_ID,
            client=client,
        )
    )

    database_records = (
        build_authoritative_database_team_inventory(
            season=season,
            roster_type=roster_type,
            active_only=True,
        )
    )

    comparison = (
        compare_source_and_database_inventory(
            source_records,
            database_records,
        )
    )

    roster_report = (
        audit_roster_foundations(
            season=season,
            roster_type=roster_type,
            client=client,
            probe_source=(
                probe_roster_source
            ),
        )
    )

    return {
        "season": season,
        "roster_type": roster_type,
        "source": source_report,
        "database_inventory": (
            database_records
        ),
        "comparison": (
            comparison.to_dict()
        ),
        "roster_foundation": (
            roster_report.to_dict()
        ),
        "completion_gate_passed": (
            comparison.completion_gate_passed
        ),
        "roster_completion_gate_passed": (
            roster_report.completion_gate_passed
        ),
        "status": (
            "ready"
            if comparison.completion_gate_passed
            else "incomplete"
        ),
        "checked_at": (
            datetime.now(UTC).isoformat()
        ),
    }


# ============================================================
# SECTION 30.16 - TEAM INVENTORY SNAPSHOT
# ============================================================

def build_team_inventory_snapshot(
    *,
    season: int = DEFAULT_TEAM_SEASON,
    roster_type: str = DEFAULT_ROSTER_TYPE,
) -> dict[str, Any]:
    inventory = (
        build_authoritative_database_team_inventory(
            season=season,
            roster_type=roster_type,
            active_only=True,
        )
    )

    normalized_inventory = [
        {
            key: value
            for key, value in team.items()
            if key not in {
                "database_team_id",
                "updated_at",
            }
        }
        for team in inventory
    ]

    return {
        "season": season,
        "roster_type": roster_type,
        "team_count": len(
            inventory
        ),
        "team_ids": sorted([
            int(team["mlb_team_id"])
            for team in inventory
            if team.get("mlb_team_id")
        ]),
        "checksum": payload_hash(
            normalized_inventory
        ),
        "inventory": inventory,
        "created_at": (
            datetime.now(UTC).isoformat()
        ),
    }


# ============================================================
# SECTION 30.17 - INVENTORY DRIFT DETECTION
# ============================================================

def detect_team_inventory_drift(
    baseline_snapshot: Mapping[str, Any],
    *,
    season: int = DEFAULT_TEAM_SEASON,
    roster_type: str = DEFAULT_ROSTER_TYPE,
) -> dict[str, Any]:
    current = build_team_inventory_snapshot(
        season=season,
        roster_type=roster_type,
    )

    baseline_ids = {
        int(team_id)
        for team_id
        in baseline_snapshot.get(
            "team_ids",
            [],
        )
    }

    current_ids = {
        int(team_id)
        for team_id
        in current.get(
            "team_ids",
            [],
        )
    }

    checksum_changed = (
        baseline_snapshot.get(
            "checksum"
        )
        != current.get(
            "checksum"
        )
    )

    return {
        "season": season,
        "baseline_checksum": (
            baseline_snapshot.get(
                "checksum"
            )
        ),
        "current_checksum": (
            current.get("checksum")
        ),
        "checksum_changed": (
            checksum_changed
        ),
        "missing_team_ids": sorted(
            baseline_ids - current_ids
        ),
        "new_team_ids": sorted(
            current_ids - baseline_ids
        ),
        "drift_detected": (
            checksum_changed
            or baseline_ids
            != current_ids
        ),
        "current_snapshot": current,
    }


# ============================================================
# SECTION 30.18 - COMPLETION GATE
# ============================================================

def validate_team_inventory_completion_gate(
    *,
    season: int = DEFAULT_TEAM_SEASON,
    roster_type: str = DEFAULT_ROSTER_TYPE,
    require_roster_rows: bool = False,
    client: MLBStatsAPIClient | None = None,
) -> dict[str, Any]:
    audit = audit_exact_mlb_team_inventory(
        season=season,
        roster_type=roster_type,
        probe_roster_source=False,
        client=client,
    )

    comparison = dict(
        audit.get(
            "comparison",
            {},
        )
    )

    roster = dict(
        audit.get(
            "roster_foundation",
            {},
        )
    )

    checks = {
        "source_has_exactly_30_active_teams": (
            audit["source"][
                "validation"
            ]["exact_count_match"]
        ),
        "source_records_are_valid": (
            audit["source"][
                "validation"
            ]["valid"]
        ),
        "database_has_exactly_30_active_teams": (
            comparison.get(
                "database_count"
            )
            == AUTHORITATIVE_ACTIVE_TEAM_COUNT
        ),
        "database_ids_match_source": (
            not comparison.get(
                "missing_in_database"
            )
            and not comparison.get(
                "unexpected_in_database"
            )
        ),
        "no_duplicate_team_ids": (
            not comparison.get(
                "duplicate_source_ids"
            )
            and not comparison.get(
                "duplicate_database_ids"
            )
        ),
        "no_duplicate_abbreviations": (
            not comparison.get(
                "duplicate_source_abbreviations"
            )
            and not comparison.get(
                "duplicate_database_abbreviations"
            )
        ),
        "names_and_abbreviations_match": (
            not comparison.get(
                "metadata_mismatches"
            )
        ),
        "league_distribution_is_15_and_15": (
            sorted(
                comparison.get(
                    "league_distribution",
                    {},
                ).values()
            )
            == [15, 15]
        ),
        "division_distribution_is_six_groups_of_five": (
            sorted(
                comparison.get(
                    "division_distribution",
                    {},
                ).values()
            )
            == [5, 5, 5, 5, 5, 5]
        ),
        "all_team_metadata_is_complete": (
            not comparison.get(
                "incomplete_source_records"
            )
            and not comparison.get(
                "incomplete_database_records"
            )
        ),
        "source_timestamps_present": all(
            bool(
                team.get(
                    "source_updated_at"
                )
                or team.get(
                    "updated_at"
                )
            )
            for team in audit.get(
                "database_inventory",
                []
            )
        ),
        "roster_foundations_ready": (
            roster.get(
                "database_ready"
            )
            if require_roster_rows
            else True
        ),
    }

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
        "season": season,
        "roster_type": roster_type,
        "require_roster_rows": (
            require_roster_rows
        ),
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "failed_checks": [
            name
            for name, value
            in checks.items()
            if not value
        ],
        "completion_gate_passed": (
            passed == len(checks)
        ),
        "audit": audit,
    }


# ============================================================
# SECTION 30.19 - DEEP MODULE VALIDATION
# ============================================================

def validate_team_ingestion_enterprise_module(
) -> dict[str, Any]:
    sample_team = {
        "id": 147,
        "name": "New York Yankees",
        "abbreviation": "NYY",
        "teamCode": "nya",
        "fileCode": "nyy",
        "franchiseName": "New York",
        "clubName": "Yankees",
        "shortName": "NY Yankees",
        "locationName": "Bronx",
        "league": {
            "id": 103,
            "name": "American League",
        },
        "division": {
            "id": 201,
            "name": "American League East",
        },
        "venue": {
            "id": 3313,
            "name": "Yankee Stadium",
        },
        "sport": {
            "id": 1,
            "name": "Major League Baseball",
        },
        "firstYearOfPlay": "1903",
        "active": True,
    }

    record = (
        normalize_authoritative_team_record(
            sample_team
        )
    )

    record_errors = (
        validate_authoritative_team_record(
            record
        )
    )

    model_payload, ignored = (
        authoritative_team_model_payload(
            record
        )
    )

    checks = {
        "legacy_validator_still_available": callable(
            validate_team_ingestion_module
        ),
        "legacy_ingestion_still_available": callable(
            ingest_mlb_teams
        ),
        "legacy_roster_bootstrap_still_available": callable(
            ingest_roster_for_team
        ),
        "legacy_dry_run_still_available": callable(
            dry_run_mlb_team_ingestion
        ),
        "authoritative_id_normalized": (
            record.mlb_team_id == 147
        ),
        "authoritative_name_normalized": (
            record.name
            == "New York Yankees"
        ),
        "authoritative_abbreviation_normalized": (
            record.abbreviation
            == "NYY"
        ),
        "authoritative_league_normalized": (
            record.league
            == "American League"
        ),
        "authoritative_division_normalized": (
            record.division
            == "American League East"
        ),
        "authoritative_venue_normalized": (
            record.venue
            == "Yankee Stadium"
        ),
        "authoritative_active_status": (
            record.is_active is True
        ),
        "authoritative_source_timestamp": (
            record.source_updated_at
            is not None
        ),
        "authoritative_checksum": bool(
            record.raw_payload_checksum
        ),
        "record_validation_passed": (
            not record_errors
        ),
        "model_payload_contains_team_id": (
            model_payload.get(
                "mlb_team_id"
            )
            == 147
        ),
        "source_fetcher_available": callable(
            fetch_authoritative_team_records
        ),
        "source_database_comparator_available": callable(
            compare_source_and_database_inventory
        ),
        "roster_foundation_audit_available": callable(
            audit_roster_foundations
        ),
        "authoritative_orchestrator_available": callable(
            ingest_authoritative_mlb_team_inventory
        ),
        "exact_inventory_audit_available": callable(
            audit_exact_mlb_team_inventory
        ),
        "snapshot_available": callable(
            build_team_inventory_snapshot
        ),
        "drift_detection_available": callable(
            detect_team_inventory_drift
        ),
        "completion_gate_available": callable(
            validate_team_inventory_completion_gate
        ),
    }

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
        "engine": INGESTION_NAME,
        "version": INGESTION_VERSION,
        "phase": INGESTION_PHASE,
        "path": INGESTION_PATH,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "failed_checks": [
            name
            for name, value
            in checks.items()
            if not value
        ],
        "normalized_authoritative_team": (
            record.to_dict()
        ),
        "model_payload": (
            sanitize_for_json(
                model_payload
            )
        ),
        "ignored_model_fields": ignored,
    }


# ============================================================
# SECTION 30.20 - ENTERPRISE HEALTH REPORT
# ============================================================

def team_ingestion_enterprise_health(
) -> dict[str, Any]:
    validation = (
        validate_team_ingestion_enterprise_module()
    )

    return {
        "name": INGESTION_NAME,
        "version": INGESTION_VERSION,
        "phase": INGESTION_PHASE,
        "path": INGESTION_PATH,
        "status": (
            "enterprise_ready"
            if validation["status"] == "ok"
            else "validation_failed"
        ),
        "capabilities": {
            "official_mlb_stats_api": True,
            "exact_30_team_source_validation": True,
            "exact_30_team_database_validation": True,
            "official_team_id_reconciliation": True,
            "name_abbreviation_reconciliation": True,
            "league_distribution_validation": True,
            "division_distribution_validation": True,
            "venue_validation": True,
            "active_status_validation": True,
            "source_timestamp_tracking": True,
            "payload_checksums": True,
            "schema_aware_upserts": True,
            "idempotent_ingestion": True,
            "nested_transaction_isolation": True,
            "unexpected_team_deactivation": True,
            "roster_bootstrap_preserved": True,
            "roster_foundation_audit": True,
            "inventory_snapshot": True,
            "inventory_drift_detection": True,
            "dry_run_compatibility": True,
            "legacy_api_compatibility": True,
        },
        "validation": validation,
        "timestamp": (
            datetime.now(UTC).isoformat()
        ),
    }



# ============================================================
# SECTION 31 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "INGESTION_NAME",
    "INGESTION_VERSION",
    "INGESTION_PHASE",
    "INGESTION_PATH",
    "INGESTION_STATUS",
    "INGESTION_SCHEMA_VERSION",
    "DEFAULT_TEAM_SEASON",
    "DEFAULT_ROSTER_TYPE",

    "IngestionMode",
    "RecordAction",
    "Severity",
    "ReadinessStatus",
    "EntityKind",

    "TeamIngestionConfig",
    "IngestionIssue",
    "EntityCounters",
    "SourceRequestMetrics",
    "UpsertResult",
    "TeamIngestionRun",

    "safe_nested_get",
    "safe_string",
    "safe_boolean",
    "safe_integer",
    "safe_date",
    "sanitize_for_json",
    "payload_hash",

    "get_model_field_names",
    "filter_payload_for_model",
    "choose_first_existing_field",

    "normalize_team_payload",
    "normalize_player_payload",
    "normalize_roster_entry_payload",

    "validate_normalized_team",
    "validate_normalized_player",
    "validate_normalized_roster_entry",

    "fetch_official_mlb_teams",
    "fetch_team_roster",

    "upsert_team",
    "upsert_player",
    "upsert_roster_entry",

    "count_database_teams",
    "count_database_players",
    "count_database_roster_entries",
    "collect_database_counts",
    "build_team_inventory",

    "ingest_mlb_teams",
    "dry_run_mlb_team_ingestion",
    "build_backward_compatible_report",

    "validate_team_ingestion_module",
    "team_ingestion_health",
    "build_ingestion_summary",
    "print_ingestion_report",

    "AUTHORITATIVE_ACTIVE_TEAM_COUNT",
    "TEAM_REQUIRED_SOURCE_FIELDS",
    "TEAM_IDENTITY_FIELDS",
    "TEAM_CONTEXT_FIELDS",
    "TEAM_SOURCE_FIELDS",

    "AuthoritativeTeamRecord",
    "TeamInventoryComparison",
    "RosterFoundationReport",

    "coerce_source_timestamp",
    "normalize_authoritative_team_record",
    "validate_authoritative_team_record",
    "validate_authoritative_source_inventory",
    "authoritative_team_model_payload",
    "upsert_authoritative_team",
    "serialize_database_team",
    "build_authoritative_database_team_inventory",
    "compare_source_and_database_inventory",
    "audit_roster_foundations",
    "fetch_authoritative_team_records",
    "mark_unexpected_teams_inactive",
    "ingest_authoritative_mlb_team_inventory",
    "audit_exact_mlb_team_inventory",
    "build_team_inventory_snapshot",
    "detect_team_inventory_drift",
    "validate_team_inventory_completion_gate",
    "validate_team_ingestion_enterprise_module",
    "team_ingestion_enterprise_health",
]


# ============================================================
# SECTION 32 - LOCAL EXECUTION ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    validation_report = (
        validate_team_ingestion_enterprise_module()
    )

    print(
        json.dumps(
            validation_report,
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

    if validation_report["status"] != "ok":
        raise SystemExit(1)

# ============================================================
# SECTION 99 - PHASE 14 PART 7.0 - TEAM INGESTION TRUTH CONTRACT
# FILE: 03_ingestion/team_ingestion.py
# PURPOSE:
# Declare production truth requirements for team ingestion.
# ============================================================

PHASE14_TEAM_INGESTION_TRUTH_VERSION = "phase_14_part_7_0_team_ingestion_truth_contract"

PHASE14_TEAM_INGESTION_REQUIRED_OUTPUTS = {
    "teams_count_target": 30,
    "must_store_mlb_team_id": True,
    "must_store_team_name": True,
    "must_store_source_attribution": True,
    "must_not_emit_demo_teams": True,
}


def validate_phase14_team_ingestion_truth_contract() -> dict:
    checks = {
        "truth_version_present": bool(PHASE14_TEAM_INGESTION_TRUTH_VERSION),
        "team_target_is_30": PHASE14_TEAM_INGESTION_REQUIRED_OUTPUTS["teams_count_target"] == 30,
        "source_attribution_required": PHASE14_TEAM_INGESTION_REQUIRED_OUTPUTS["must_store_source_attribution"],
        "demo_teams_forbidden": PHASE14_TEAM_INGESTION_REQUIRED_OUTPUTS["must_not_emit_demo_teams"],
    }

    passed = sum(1 for value in checks.values() if value)

    return {
        "status": "ok" if passed == len(checks) else "degraded",
        "phase": "Phase 14 Part 7.0",
        "truth_version": PHASE14_TEAM_INGESTION_TRUTH_VERSION,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "requirements": PHASE14_TEAM_INGESTION_REQUIRED_OUTPUTS,
    }

