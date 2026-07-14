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
INGESTION_VERSION: Final[str] = "5.0.0"
INGESTION_PHASE: Final[str] = "Phase 11 Part 1.0"
INGESTION_PATH: Final[str] = "03_ingestion/team_ingestion.py"
INGESTION_STATUS: Final[str] = "enterprise_ready"
INGESTION_SCHEMA_VERSION: Final[str] = "2.0.0"

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
]


# ============================================================
# SECTION 32 - LOCAL EXECUTION ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    validation_report = (
        validate_team_ingestion_module()
    )

    print(
        json.dumps(
            validation_report,
            indent=2,
            sort_keys=True,
        )
    )

    if validation_report["status"] != "ok":
        raise SystemExit(1)

    ingestion_report = ingest_mlb_teams()
    print_ingestion_report(
        ingestion_report
    )
