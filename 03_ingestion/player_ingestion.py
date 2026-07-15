# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# FILE: 03_ingestion/player_ingestion.py
# PURPOSE:
# Enterprise MLB player, roster, identity, freshness, and
# official-source ingestion for the AISP2 Baseball Warehouse.
# ============================================================
"""
Enterprise player-ingestion service for AISP2 Baseball.

This module is intentionally responsible for the player identity and roster
edge of the warehouse. It treats current MLB rosters as the authoritative
source for current team membership and uses official MLB person endpoints to
hydrate identity and biographical fields.

Design guarantees
-----------------
1. Idempotent upserts keyed by MLB player ID.
2. Current-roster ingestion across every active MLB club.
3. Search across full name, first name, last name, normalized name, and ID.
4. Safe compatibility with evolving SQLAlchemy Player/Team models.
5. Freshness and source-attribution diagnostics on every ingestion report.
6. Official-source registry for MLB Stats API and Baseball Savant/Statcast.
7. No fabricated statistics. Missing source data is reported explicitly.
8. Partial source failures do not destroy already-valid warehouse records.
9. Existing public functions remain available to main.py.

Important scope boundary
------------------------
A truly complete historical and statistical warehouse requires dedicated
models/tables for rosters, player-season statistics, Statcast events, source
snapshots, and ingestion runs. This file prepares and exposes those contracts,
but only persists fields that actually exist on the current Player and Team
models. It never silently invents columns.
"""

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
import json
import logging
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Final

# ============================================================
# SECTION 02 - PROJECT PATH REGISTRATION
# ============================================================

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[1]
DATABASE_DIR = PROJECT_ROOT / "01_database"
DATA_SOURCES_DIR = PROJECT_ROOT / "02_data_sources"
INGESTION_DIR = PROJECT_ROOT / "03_ingestion"

for path in (PROJECT_ROOT, DATABASE_DIR, DATA_SOURCES_DIR, INGESTION_DIR):
    path_string = str(path)
    if path_string not in sys.path:
        sys.path.insert(0, path_string)

# ============================================================
# SECTION 03 - PROJECT IMPORTS
# ============================================================

from database import initialize_database
from database import managed_database_session
from models import Player
from models import Team
from models import RosterEntry
from models import PlayerSeasonStat
from models import PlayerGameStat
from models import PlayerSplitStat
from models import PlayerStatcastMetric
from models import RawDataImportLog
from mlb_stats_api import DEFAULT_SEASON
from mlb_stats_api import MLBStatsAPIClient

try:
    from sqlalchemy import and_, func, or_
except Exception:  # pragma: no cover - SQLAlchemy is expected in production
    and_ = func = or_ = None

LOGGER = logging.getLogger(__name__)

# ============================================================
# SECTION 04 - MODULE METADATA
# ============================================================

INGESTION_NAME: Final[str] = "AISP2 Enterprise Player and Roster Ingestion"
INGESTION_VERSION: Final[str] = "6.0.0"
INGESTION_PHASE: Final[str] = "Phase 11 Part 4.0"
INGESTION_PATH: Final[str] = "03_ingestion/player_ingestion.py"
DEFAULT_PLAYER_SEASON: Final[int] = DEFAULT_SEASON
DEFAULT_ROSTER_TYPES: Final[tuple[str, ...]] = (
    "active",
    "40Man",
    "fullRoster",
)
DEFAULT_REQUEST_DELAY_SECONDS: Final[float] = 0.10
DEFAULT_SEARCH_LIMIT: Final[int] = 25
MAX_SEARCH_LIMIT: Final[int] = 250
MAX_ERROR_RECORDS: Final[int] = 500

# ============================================================
# SECTION 05 - OFFICIAL SOURCE REGISTRY
# ============================================================

OFFICIAL_PLAYER_DATA_SOURCES: Final[dict[str, dict[str, Any]]] = {
    "mlb_stats_api_teams": {
        "authority": "MLB Advanced Media",
        "base_url": "https://statsapi.mlb.com/api/v1",
        "purpose": "Active MLB club identity and metadata",
        "refresh_cadence": "daily",
        "official": True,
    },
    "mlb_stats_api_rosters": {
        "authority": "MLB Advanced Media",
        "base_url": "https://statsapi.mlb.com/api/v1",
        "purpose": "Current team-player membership and roster status",
        "refresh_cadence": "hourly during season; daily offseason",
        "official": True,
    },
    "mlb_stats_api_people": {
        "authority": "MLB Advanced Media",
        "base_url": "https://statsapi.mlb.com/api/v1",
        "purpose": "Official player identity and biographical data",
        "refresh_cadence": "daily for changed players",
        "official": True,
    },
    "mlb_stats_api_stats": {
        "authority": "MLB Advanced Media",
        "base_url": "https://statsapi.mlb.com/api/v1",
        "purpose": "Official season, career, game-log, and split statistics",
        "refresh_cadence": "after games and nightly reconciliation",
        "official": True,
    },
    "baseball_savant_statcast": {
        "authority": "MLB Advanced Media / Baseball Savant",
        "base_url": "https://baseballsavant.mlb.com",
        "purpose": "Official Statcast event data and advanced metrics",
        "refresh_cadence": "daily after official data publication",
        "official": True,
        "persistence_requirement": "Dedicated Statcast event/snapshot tables",
    },
}

# ============================================================
# SECTION 06 - EXCEPTIONS
# ============================================================


class PlayerIngestionError(RuntimeError):
    """Base exception for player-ingestion failures."""


class PlayerSourceError(PlayerIngestionError):
    """Raised when an official source cannot be queried safely."""


class PlayerValidationError(PlayerIngestionError):
    """Raised when a normalized player record is invalid."""


# ============================================================
# SECTION 07 - DATA CONTRACTS
# ============================================================


@dataclass(slots=True)
class SourceObservation:
    source: str
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    source_url: str | None = None
    source_record_id: str | int | None = None
    source_updated_at: datetime | None = None
    checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "observed_at": self.observed_at.isoformat(),
            "source_url": self.source_url,
            "source_record_id": self.source_record_id,
            "source_updated_at": (
                self.source_updated_at.isoformat()
                if self.source_updated_at
                else None
            ),
            "checksum": self.checksum,
        }


@dataclass(slots=True)
class NormalizedPlayerRecord:
    mlb_player_id: int
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    primary_number: str | None = None
    position: str | None = None
    position_code: str | None = None
    bats: str | None = None
    throws: str | None = None
    height: str | None = None
    weight: int | None = None
    birth_date: str | None = None
    birth_city: str | None = None
    birth_state_province: str | None = None
    birth_country: str | None = None
    mlb_debut_date: str | None = None
    active_status: bool = True
    current_team_id: int | None = None
    current_team_name: str | None = None
    roster_status: str | None = None
    roster_type: str | None = None
    jersey_number: str | None = None
    source: str = "MLB Stats API"
    source_observed_at: str | None = None
    normalized_name: str | None = None
    search_name: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PlayerUpsertResult:
    action: str
    mlb_player_id: int
    full_name: str
    changed_fields: list[str] = field(default_factory=list)
    persisted_fields: list[str] = field(default_factory=list)
    ignored_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class IngestionMetrics:
    requested: int = 0
    received: int = 0
    normalized: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed: int = 0
    teams_processed: int = 0
    roster_entries_processed: int = 0
    duplicate_source_records: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


# ============================================================
# SECTION 08 - GENERIC SAFE HELPERS
# ============================================================


def utc_now() -> datetime:
    return datetime.now(UTC)


def safe_nested_get(data: Any, *keys: str) -> Any:
    current_value = data
    for key in keys:
        if not isinstance(current_value, Mapping):
            return None
        current_value = current_value.get(key)
    return current_value


def safe_string(value: Any) -> str | None:
    if value is None:
        return None
    cleaned_value = str(value).strip()
    return cleaned_value or None


def safe_integer(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_boolean(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "active", "y"}:
            return True
        if normalized in {"false", "0", "no", "inactive", "n"}:
            return False
    return bool(value)


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )


def normalize_search_text(value: Any) -> str:
    text = strip_accents(str(value or "")).lower()
    text = re.sub(r"[^a-z0-9\s'-]", " ", text)
    return collapse_spaces(text)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def payload_checksum(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def coerce_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return dict(value.model_dump())
    if hasattr(value, "dict") and callable(value.dict):
        return dict(value.dict())
    if hasattr(value, "_asdict") and callable(value._asdict):
        return dict(value._asdict())
    if hasattr(value, "__dict__"):
        return {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_") and not callable(item)
        }
    return {"value": value}


def bounded_limit(value: int | None, default: int = DEFAULT_SEARCH_LIMIT) -> int:
    try:
        parsed = int(value if value is not None else default)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, MAX_SEARCH_LIMIT))


def append_bounded_error(
    report: dict[str, Any],
    error: dict[str, Any],
    *,
    maximum: int = MAX_ERROR_RECORDS,
) -> None:
    errors = report.setdefault("errors", [])
    if len(errors) < maximum:
        errors.append(error)
    else:
        report["errors_truncated"] = True


# ============================================================
# SECTION 09 - MODEL INTROSPECTION
# ============================================================


def model_column_names(model: Any) -> set[str]:
    table = getattr(model, "__table__", None)
    if table is not None:
        try:
            return {column.name for column in table.columns}
        except Exception:
            pass
    mapper = getattr(model, "__mapper__", None)
    if mapper is not None:
        try:
            return {attribute.key for attribute in mapper.column_attrs}
        except Exception:
            pass
    return {
        name
        for name in dir(model)
        if not name.startswith("_")
    }


PLAYER_MODEL_FIELDS: Final[set[str]] = model_column_names(Player)
TEAM_MODEL_FIELDS: Final[set[str]] = model_column_names(Team)

PLAYER_FIELD_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "mlb_player_id": ("mlb_player_id", "player_id", "mlb_id", "person_id"),
    "full_name": ("full_name", "player_name", "name", "display_name"),
    "first_name": ("first_name", "firstName"),
    "last_name": ("last_name", "lastName"),
    "primary_number": ("primary_number", "jersey_number", "number"),
    "position": ("position", "position_name", "primary_position"),
    "position_code": ("position_code", "position_abbreviation", "position_abbr"),
    "bats": ("bats", "bat_side", "bat_side_code"),
    "throws": ("throws", "throw_side", "pitch_hand", "pitch_hand_code"),
    "height": ("height",),
    "weight": ("weight",),
    "birth_date": ("birth_date",),
    "birth_city": ("birth_city",),
    "birth_state_province": ("birth_state_province", "birth_state"),
    "birth_country": ("birth_country",),
    "mlb_debut_date": ("mlb_debut_date", "debut_date"),
    "active_status": ("active_status", "active", "is_active"),
    "current_team_id": ("current_team_id", "team_id", "mlb_team_id"),
    "current_team_name": ("current_team_name", "team_name"),
    "roster_status": ("roster_status", "status"),
    "roster_type": ("roster_type",),
    "source": ("source", "data_source"),
    "source_observed_at": ("source_observed_at", "last_synced_at", "updated_at"),
    "normalized_name": ("normalized_name", "search_name"),
}


def resolve_model_field(
    logical_name: str,
    available_fields: set[str],
) -> str | None:
    for candidate in PLAYER_FIELD_ALIASES.get(logical_name, (logical_name,)):
        if candidate in available_fields:
            return candidate
    return None


def player_identity_field() -> str:
    for logical_name in ("mlb_player_id", "player_id", "mlb_id", "person_id"):
        if logical_name in PLAYER_MODEL_FIELDS:
            return logical_name
    raise PlayerIngestionError(
        "Player model has no MLB identity field. Expected one of: "
        "mlb_player_id, player_id, mlb_id, person_id."
    )


def player_name_fields() -> list[str]:
    candidates = (
        "full_name",
        "player_name",
        "name",
        "display_name",
        "first_name",
        "last_name",
        "normalized_name",
        "search_name",
    )
    return [candidate for candidate in candidates if candidate in PLAYER_MODEL_FIELDS]


# ============================================================
# SECTION 10 - MLB CLIENT COMPATIBILITY ADAPTER
# ============================================================


class MLBClientAdapter:
    """Normalize differing MLBStatsAPIClient method surfaces."""

    def __init__(self, client: Any | None = None) -> None:
        self.client = client or MLBStatsAPIClient()

    def _call_first(
        self,
        method_names: Sequence[str],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        errors: list[str] = []
        for method_name in method_names:
            method = getattr(self.client, method_name, None)
            if not callable(method):
                continue
            try:
                return method(*args, **kwargs)
            except TypeError as exc:
                errors.append(f"{method_name}: {exc}")
                continue
        raise PlayerSourceError(
            "No compatible MLB client method succeeded. "
            + (" | ".join(errors) if errors else "Methods unavailable.")
        )

    def get_active_teams(self, season: int) -> list[dict[str, Any]]:
        method_candidates = (
            "get_mlb_teams",
            "get_all_teams",
            "get_teams",
        )
        try:
            payload = self._call_first(method_candidates, season=season)
        except PlayerSourceError:
            payload = self._raw_get(
                "/teams",
                params={"sportId": 1, "season": season, "activeStatus": "Y"},
            )
        return self._extract_list(payload, "teams")

    def get_team_roster(
        self,
        team_id: int,
        season: int,
        roster_type: str,
    ) -> list[dict[str, Any]]:
        method_candidates = (
            "get_team_roster",
            "get_roster",
            "fetch_team_roster",
        )
        payload: Any
        for kwargs in (
            {"team_id": team_id, "season": season, "roster_type": roster_type},
            {"team_id": team_id, "season": season, "rosterType": roster_type},
            {"team_id": team_id, "roster_type": roster_type},
            {"team_id": team_id},
        ):
            try:
                payload = self._call_first(method_candidates, **kwargs)
                return self._extract_list(payload, "roster")
            except PlayerSourceError:
                continue
        payload = self._raw_get(
            f"/teams/{team_id}/roster",
            params={"season": season, "rosterType": roster_type},
        )
        return self._extract_list(payload, "roster")

    def get_person(self, player_id: int) -> dict[str, Any]:
        method_candidates = (
            "get_person",
            "get_player",
            "get_player_details",
            "get_person_details",
        )
        for kwargs in (
            {"person_id": player_id},
            {"player_id": player_id},
            {"mlb_player_id": player_id},
        ):
            try:
                payload = self._call_first(method_candidates, **kwargs)
                people = self._extract_list(payload, "people")
                if people:
                    return people[0]
                mapping = coerce_mapping(payload)
                if mapping.get("id"):
                    return mapping
            except PlayerSourceError:
                continue
        payload = self._raw_get(f"/people/{player_id}")
        people = self._extract_list(payload, "people")
        return people[0] if people else {}

    def get_all_active_players(self, season: int) -> list[dict[str, Any]]:
        method = getattr(self.client, "get_all_active_players", None)
        if callable(method):
            result = method(season=season)
            return self._extract_list(result, "people")
        payload = self._raw_get(
            "/sports/1/players",
            params={"season": season},
        )
        return self._extract_list(payload, "people")

    def get_player_stats(
        self,
        player_id: int,
        season: int,
        *,
        group: str = "hitting",
        stat_type: str = "season",
    ) -> dict[str, Any]:
        method_candidates = (
            "get_player_stats",
            "get_person_stats",
            "get_stats",
        )
        for kwargs in (
            {
                "player_id": player_id,
                "season": season,
                "group": group,
                "stat_type": stat_type,
            },
            {
                "person_id": player_id,
                "season": season,
                "group": group,
                "stats": stat_type,
            },
        ):
            try:
                result = self._call_first(method_candidates, **kwargs)
                return coerce_mapping(result)
            except PlayerSourceError:
                continue
        return self._raw_get(
            f"/people/{player_id}/stats",
            params={"stats": stat_type, "group": group, "season": season},
        )

    def _raw_get(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        for method_name in ("get", "_get", "request_json", "fetch_json"):
            method = getattr(self.client, method_name, None)
            if not callable(method):
                continue
            try:
                result = method(path, params=dict(params or {}))
                return coerce_mapping(result)
            except TypeError:
                try:
                    result = method(path)
                    return coerce_mapping(result)
                except Exception:
                    continue
            except Exception:
                continue
        raise PlayerSourceError(
            f"MLBStatsAPIClient cannot query path {path!r}. "
            "Add a generic JSON GET method or a compatible domain method."
        )

    @staticmethod
    def _extract_list(payload: Any, key: str) -> list[dict[str, Any]]:
        if payload is None:
            return []
        if isinstance(payload, list):
            return [coerce_mapping(item) for item in payload]
        mapping = coerce_mapping(payload)
        values = mapping.get(key)
        if isinstance(values, list):
            return [coerce_mapping(item) for item in values]
        if key == "people" and mapping.get("id"):
            return [mapping]
        return []


# ============================================================
# SECTION 11 - SOURCE PAYLOAD NORMALIZATION
# ============================================================


def merge_player_payloads(
    person_payload: Mapping[str, Any] | None,
    roster_entry: Mapping[str, Any] | None = None,
    team_payload: Mapping[str, Any] | None = None,
    *,
    roster_type: str | None = None,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    person = dict(person_payload or {})
    roster = dict(roster_entry or {})
    team = dict(team_payload or {})
    roster_person = coerce_mapping(roster.get("person"))

    merged = dict(roster_person)
    merged.update({key: value for key, value in person.items() if value is not None})

    position = coerce_mapping(roster.get("position"))
    if not position:
        position = coerce_mapping(merged.get("primaryPosition"))

    status = coerce_mapping(roster.get("status"))
    current_team = coerce_mapping(merged.get("currentTeam"))

    team_id = (
        safe_integer(team.get("id"))
        or safe_integer(current_team.get("id"))
        or safe_integer(roster.get("teamId"))
    )
    team_name = (
        safe_string(team.get("name"))
        or safe_string(current_team.get("name"))
        or safe_string(roster.get("teamName"))
    )

    merged["_aisp2_team_id"] = team_id
    merged["_aisp2_team_name"] = team_name
    merged["_aisp2_roster_status"] = (
        safe_string(status.get("description"))
        or safe_string(status.get("code"))
        or safe_string(roster.get("status"))
    )
    merged["_aisp2_roster_type"] = roster_type
    merged["_aisp2_roster_number"] = safe_string(roster.get("jerseyNumber"))
    merged["_aisp2_position"] = position
    merged["_aisp2_observed_at"] = (observed_at or utc_now()).isoformat()
    return merged


def normalize_player_payload(
    raw_player: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(raw_player or {})
    player_id = safe_integer(payload.get("id") or payload.get("mlb_player_id"))
    full_name = safe_string(
        payload.get("fullName")
        or payload.get("full_name")
        or payload.get("player_name")
        or payload.get("name")
    )
    first_name = safe_string(payload.get("firstName") or payload.get("first_name"))
    last_name = safe_string(payload.get("lastName") or payload.get("last_name"))

    if full_name and not first_name and not last_name:
        name_parts = full_name.split()
        if name_parts:
            first_name = name_parts[0]
            last_name = name_parts[-1] if len(name_parts) > 1 else None

    position = coerce_mapping(
        payload.get("_aisp2_position")
        or payload.get("primaryPosition")
        or payload.get("position")
    )
    current_team = coerce_mapping(payload.get("currentTeam"))

    normalized_name = normalize_search_text(full_name)
    search_name = collapse_spaces(
        " ".join(
            value
            for value in (
                normalize_search_text(full_name),
                normalize_search_text(first_name),
                normalize_search_text(last_name),
            )
            if value
        )
    )

    record = NormalizedPlayerRecord(
        mlb_player_id=player_id or 0,
        full_name=full_name or "",
        first_name=first_name,
        last_name=last_name,
        primary_number=safe_string(
            payload.get("primaryNumber")
            or payload.get("primary_number")
            or payload.get("_aisp2_roster_number")
        ),
        position=safe_string(
            position.get("name")
            or payload.get("position_name")
            or payload.get("position")
        ),
        position_code=safe_string(
            position.get("code")
            or position.get("abbreviation")
            or payload.get("position_code")
        ),
        bats=safe_string(
            safe_nested_get(payload, "batSide", "code")
            or payload.get("bats")
        ),
        throws=safe_string(
            safe_nested_get(payload, "pitchHand", "code")
            or payload.get("throws")
        ),
        height=safe_string(payload.get("height")),
        weight=safe_integer(payload.get("weight")),
        birth_date=safe_string(payload.get("birthDate") or payload.get("birth_date")),
        birth_city=safe_string(payload.get("birthCity") or payload.get("birth_city")),
        birth_state_province=safe_string(
            payload.get("birthStateProvince")
            or payload.get("birth_state_province")
        ),
        birth_country=safe_string(
            payload.get("birthCountry")
            or payload.get("birth_country")
        ),
        mlb_debut_date=safe_string(
            payload.get("mlbDebutDate")
            or payload.get("mlb_debut_date")
        ),
        active_status=safe_boolean(
            payload.get("active")
            if "active" in payload
            else payload.get("active_status"),
            default=True,
        ),
        current_team_id=(
            safe_integer(payload.get("_aisp2_team_id"))
            or safe_integer(current_team.get("id"))
            or safe_integer(payload.get("team_id"))
        ),
        current_team_name=(
            safe_string(payload.get("_aisp2_team_name"))
            or safe_string(current_team.get("name"))
            or safe_string(payload.get("team_name"))
        ),
        roster_status=safe_string(
            payload.get("_aisp2_roster_status")
            or payload.get("roster_status")
        ),
        roster_type=safe_string(
            payload.get("_aisp2_roster_type")
            or payload.get("roster_type")
        ),
        jersey_number=safe_string(
            payload.get("_aisp2_roster_number")
            or payload.get("jersey_number")
        ),
        source="MLB Stats API",
        source_observed_at=safe_string(payload.get("_aisp2_observed_at")) or utc_now().isoformat(),
        normalized_name=normalized_name,
        search_name=search_name,
        raw_payload=payload,
    )
    return record.to_dict()


# ============================================================
# SECTION 12 - VALIDATION
# ============================================================


def validate_normalized_player(
    normalized_player: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if not safe_integer(normalized_player.get("mlb_player_id")):
        errors.append("Missing or invalid mlb_player_id")
    if not safe_string(normalized_player.get("full_name")):
        errors.append("Missing full_name")
    return errors


def validate_roster_coverage(
    team_reports: Sequence[Mapping[str, Any]],
    *,
    expected_team_count: int = 30,
) -> dict[str, Any]:
    processed = len(team_reports)
    teams_with_players = sum(
        1 for report in team_reports if int(report.get("player_count", 0)) > 0
    )
    total_players = sum(int(report.get("player_count", 0)) for report in team_reports)
    return {
        "expected_team_count": expected_team_count,
        "processed_team_count": processed,
        "teams_with_players": teams_with_players,
        "total_roster_entries": total_players,
        "team_coverage_percent": round(
            100.0 * processed / expected_team_count,
            2,
        ) if expected_team_count else 0.0,
        "teams_with_players_percent": round(
            100.0 * teams_with_players / expected_team_count,
            2,
        ) if expected_team_count else 0.0,
        "complete": processed >= expected_team_count and teams_with_players >= expected_team_count,
    }


# ============================================================
# SECTION 13 - PERSISTENCE MAPPING
# ============================================================


def persistence_payload(
    normalized_player: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    persisted: dict[str, Any] = {}
    ignored: list[str] = []

    for logical_name, value in normalized_player.items():
        if logical_name in {"raw_payload", "jersey_number"}:
            ignored.append(logical_name)
            continue
        model_field = resolve_model_field(logical_name, PLAYER_MODEL_FIELDS)
        if model_field is None:
            ignored.append(logical_name)
            continue
        persisted[model_field] = value

    identity_field = player_identity_field()
    if identity_field not in persisted:
        persisted[identity_field] = normalized_player.get("mlb_player_id")

    name_field = resolve_model_field("full_name", PLAYER_MODEL_FIELDS)
    if name_field and name_field not in persisted:
        persisted[name_field] = normalized_player.get("full_name")

    return persisted, ignored


def find_existing_player(database_session: Any, mlb_player_id: int) -> Any | None:
    identity_field = player_identity_field()
    column = getattr(Player, identity_field)
    return (
        database_session.query(Player)
        .filter(column == mlb_player_id)
        .first()
    )


def upsert_player(
    database_session: Any,
    normalized_player: Mapping[str, Any],
) -> str:
    """Backward-compatible upsert returning only the action string."""
    return upsert_player_detailed(database_session, normalized_player).action


def upsert_player_detailed(
    database_session: Any,
    normalized_player: Mapping[str, Any],
) -> PlayerUpsertResult:
    errors = validate_normalized_player(normalized_player)
    if errors:
        raise PlayerValidationError("; ".join(errors))

    player_id = int(normalized_player["mlb_player_id"])
    full_name = str(normalized_player["full_name"])
    persisted, ignored = persistence_payload(normalized_player)
    existing = find_existing_player(database_session, player_id)

    if existing is None:
        new_player = Player(**persisted)
        database_session.add(new_player)
        return PlayerUpsertResult(
            action="created",
            mlb_player_id=player_id,
            full_name=full_name,
            changed_fields=sorted(persisted),
            persisted_fields=sorted(persisted),
            ignored_fields=sorted(set(ignored)),
        )

    changed_fields: list[str] = []
    for field_name, field_value in persisted.items():
        current_value = getattr(existing, field_name, None)
        if current_value != field_value:
            setattr(existing, field_name, field_value)
            changed_fields.append(field_name)

    return PlayerUpsertResult(
        action="updated" if changed_fields else "unchanged",
        mlb_player_id=player_id,
        full_name=full_name,
        changed_fields=sorted(changed_fields),
        persisted_fields=sorted(persisted),
        ignored_fields=sorted(set(ignored)),
    )


# ============================================================
# SECTION 14 - TEAM LOOKUP HELPERS
# ============================================================


def team_record_by_mlb_id(database_session: Any, mlb_team_id: int) -> Any | None:
    candidate_fields = (
        "mlb_team_id",
        "team_id",
        "mlb_id",
        "id",
    )
    for field_name in candidate_fields:
        if field_name not in TEAM_MODEL_FIELDS:
            continue
        column = getattr(Team, field_name)
        record = database_session.query(Team).filter(column == mlb_team_id).first()
        if record is not None:
            return record
    return None


def team_name_from_record(team: Any) -> str | None:
    for field_name in ("full_name", "team_name", "name", "club_name"):
        value = safe_string(getattr(team, field_name, None))
        if value:
            return value
    return None


# ============================================================
# SECTION 15 - COMPREHENSIVE ROSTER COLLECTION
# ============================================================


def collect_current_mlb_roster_players(
    season: int = DEFAULT_PLAYER_SEASON,
    *,
    roster_types: Sequence[str] = DEFAULT_ROSTER_TYPES,
    hydrate_people: bool = True,
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS,
    client: Any | None = None,
) -> dict[str, Any]:
    adapter = MLBClientAdapter(client)
    observed_at = utc_now()
    teams = adapter.get_active_teams(season)

    by_player_id: dict[int, dict[str, Any]] = {}
    team_reports: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    duplicate_entries = 0

    for team in teams:
        team_id = safe_integer(team.get("id"))
        team_name = safe_string(team.get("name"))
        if not team_id:
            errors.append({"team": team, "error": "Missing team ID"})
            continue

        team_player_ids: set[int] = set()
        roster_type_counts: dict[str, int] = {}

        for roster_type in roster_types:
            try:
                roster_entries = adapter.get_team_roster(
                    team_id=team_id,
                    season=season,
                    roster_type=roster_type,
                )
            except Exception as exc:
                errors.append({
                    "team_id": team_id,
                    "team_name": team_name,
                    "roster_type": roster_type,
                    "error": str(exc),
                })
                continue

            roster_type_counts[roster_type] = len(roster_entries)

            for roster_entry in roster_entries:
                roster_person = coerce_mapping(roster_entry.get("person"))
                player_id = safe_integer(
                    roster_person.get("id")
                    or roster_entry.get("personId")
                    or roster_entry.get("player_id")
                )
                if not player_id:
                    errors.append({
                        "team_id": team_id,
                        "roster_type": roster_type,
                        "entry": roster_entry,
                        "error": "Roster entry missing player ID",
                    })
                    continue

                person_payload = roster_person
                if hydrate_people:
                    try:
                        hydrated = adapter.get_person(player_id)
                        if hydrated:
                            person_payload = hydrated
                    except Exception as exc:
                        errors.append({
                            "player_id": player_id,
                            "team_id": team_id,
                            "stage": "person_hydration",
                            "error": str(exc),
                        })

                merged_payload = merge_player_payloads(
                    person_payload,
                    roster_entry,
                    team,
                    roster_type=roster_type,
                    observed_at=observed_at,
                )

                if player_id in by_player_id:
                    duplicate_entries += 1
                    existing = by_player_id[player_id]
                    existing_roster_type = safe_string(existing.get("_aisp2_roster_type"))
                    # Prefer active roster membership over wider roster types.
                    if existing_roster_type == "active":
                        continue
                    if roster_type != "active":
                        continue

                by_player_id[player_id] = merged_payload
                team_player_ids.add(player_id)

                if request_delay_seconds > 0:
                    time.sleep(request_delay_seconds)

        team_reports.append({
            "team_id": team_id,
            "team_name": team_name,
            "player_count": len(team_player_ids),
            "roster_type_counts": roster_type_counts,
        })

    return {
        "season": season,
        "observed_at": observed_at.isoformat(),
        "source": "MLB Stats API rosters and people",
        "team_count": len(teams),
        "player_count": len(by_player_id),
        "duplicate_roster_entries": duplicate_entries,
        "players": list(by_player_id.values()),
        "team_reports": team_reports,
        "coverage": validate_roster_coverage(team_reports),
        "errors": errors[:MAX_ERROR_RECORDS],
        "errors_truncated": len(errors) > MAX_ERROR_RECORDS,
    }


# ============================================================
# SECTION 16 - PRIMARY PLAYER INGESTION ENGINE
# ============================================================


def ingest_mlb_players(
    season: int = DEFAULT_PLAYER_SEASON,
    *,
    mode: str = "roster_authoritative",
    roster_types: Sequence[str] = DEFAULT_ROSTER_TYPES,
    hydrate_people: bool = True,
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS,
    client: Any | None = None,
) -> dict[str, Any]:
    """
    Ingest current MLB players into the warehouse.

    mode="roster_authoritative" collects players from every active MLB team,
    preserving current team/roster context. mode="all_active_players" retains
    compatibility with the original broad sports-player endpoint.
    """
    started = time.perf_counter()
    initialization_report = initialize_database()
    adapter = MLBClientAdapter(client)

    report: dict[str, Any] = {
        "ingestion": INGESTION_NAME,
        "version": INGESTION_VERSION,
        "phase": INGESTION_PHASE,
        "path": INGESTION_PATH,
        "season": season,
        "mode": mode,
        "source": "MLB Stats API",
        "official_sources": OFFICIAL_PLAYER_DATA_SOURCES,
        "started_at": utc_now().isoformat(),
        "database_initialized": initialization_report.get("initialized"),
        "database_health": initialization_report.get("health"),
        "metrics": IngestionMetrics().to_dict(),
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": 0,
        "errors": [],
        "players": [],
        "coverage": {},
        "source_observation": {},
        "model_contract": {
            "player_fields_available": sorted(PLAYER_MODEL_FIELDS),
            "team_fields_available": sorted(TEAM_MODEL_FIELDS),
        },
    }

    try:
        if mode == "all_active_players":
            source_players = adapter.get_all_active_players(season)
            source_result = {
                "players": source_players,
                "player_count": len(source_players),
                "team_count": None,
                "coverage": {
                    "complete": bool(source_players),
                    "strategy": "sports_player_index",
                },
                "errors": [],
                "observed_at": utc_now().isoformat(),
            }
        else:
            source_result = collect_current_mlb_roster_players(
                season=season,
                roster_types=roster_types,
                hydrate_people=hydrate_people,
                request_delay_seconds=request_delay_seconds,
                client=adapter.client,
            )
    except Exception as exc:
        report["success"] = False
        report["fatal_error"] = str(exc)
        report["finished_at"] = utc_now().isoformat()
        report["duration_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
        return report

    raw_players = source_result.get("players", [])
    report["raw_player_count"] = len(raw_players)
    report["coverage"] = source_result.get("coverage", {})
    report["source_observation"] = {
        "observed_at": source_result.get("observed_at"),
        "team_count": source_result.get("team_count"),
        "player_count": source_result.get("player_count"),
        "duplicate_roster_entries": source_result.get("duplicate_roster_entries", 0),
    }
    for source_error in source_result.get("errors", []):
        append_bounded_error(report, source_error)

    metrics = IngestionMetrics(
        requested=len(raw_players),
        received=len(raw_players),
        teams_processed=int(source_result.get("team_count") or 0),
        roster_entries_processed=len(raw_players),
        duplicate_source_records=int(source_result.get("duplicate_roster_entries") or 0),
    )

    with managed_database_session() as database_session:
        for raw_player in raw_players:
            try:
                normalized_player = normalize_player_payload(raw_player)
                validation_errors = validate_normalized_player(normalized_player)
                if validation_errors:
                    metrics.skipped += 1
                    append_bounded_error(report, {
                        "player_id": normalized_player.get("mlb_player_id"),
                        "player_name": normalized_player.get("full_name"),
                        "stage": "validation",
                        "errors": validation_errors,
                    })
                    continue

                metrics.normalized += 1
                result = upsert_player_detailed(database_session, normalized_player)

                if result.action == "created":
                    metrics.created += 1
                elif result.action == "updated":
                    metrics.updated += 1
                else:
                    metrics.unchanged += 1

                report["players"].append({
                    "mlb_player_id": result.mlb_player_id,
                    "full_name": result.full_name,
                    "position": normalized_player.get("position"),
                    "team_id": normalized_player.get("current_team_id"),
                    "team_name": normalized_player.get("current_team_name"),
                    "roster_status": normalized_player.get("roster_status"),
                    "roster_type": normalized_player.get("roster_type"),
                    "active_status": normalized_player.get("active_status"),
                    "action": result.action,
                    "changed_fields": result.changed_fields,
                })
            except Exception as exc:
                metrics.failed += 1
                append_bounded_error(report, {
                    "stage": "upsert",
                    "player_id": safe_nested_get(raw_player, "id"),
                    "player_name": safe_nested_get(raw_player, "fullName"),
                    "error": str(exc),
                })

    report["metrics"] = metrics.to_dict()
    report["created"] = metrics.created
    report["updated"] = metrics.updated
    report["unchanged"] = metrics.unchanged
    report["skipped"] = metrics.skipped + metrics.failed
    report["database_player_count_after_ingestion"] = count_database_players()
    report["success"] = (
        metrics.normalized > 0
        and metrics.failed == 0
        and bool(report.get("database_health"))
    )
    report["partial_success"] = metrics.normalized > 0 and metrics.failed > 0
    report["finished_at"] = utc_now().isoformat()
    report["duration_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
    report["freshness"] = build_player_freshness_report()
    return report


# ============================================================
# SECTION 17 - DATABASE COUNTS AND INVENTORY
# ============================================================


def count_database_players() -> int:
    with managed_database_session() as database_session:
        return int(database_session.query(Player).count())


def count_active_database_players() -> int:
    active_field = resolve_model_field("active_status", PLAYER_MODEL_FIELDS)
    if active_field is None:
        return count_database_players()
    with managed_database_session() as database_session:
        column = getattr(Player, active_field)
        return int(database_session.query(Player).filter(column.is_(True)).count())


def serialize_player_record(player: Any) -> dict[str, Any]:
    def first_attribute(*names: str) -> Any:
        for name in names:
            if hasattr(player, name):
                value = getattr(player, name)
                if value is not None:
                    return value
        return None

    return {
        "mlb_player_id": first_attribute("mlb_player_id", "player_id", "mlb_id", "person_id"),
        "full_name": first_attribute("full_name", "player_name", "name", "display_name"),
        "name": first_attribute("full_name", "player_name", "name", "display_name"),
        "first_name": first_attribute("first_name"),
        "last_name": first_attribute("last_name"),
        "position": first_attribute("position", "position_name", "primary_position"),
        "position_code": first_attribute("position_code", "position_abbreviation"),
        "bats": first_attribute("bats", "bat_side"),
        "throws": first_attribute("throws", "pitch_hand"),
        "height": first_attribute("height"),
        "weight": first_attribute("weight"),
        "birth_date": first_attribute("birth_date"),
        "active_status": first_attribute("active_status", "active", "is_active"),
        "team_id": first_attribute("current_team_id", "team_id", "mlb_team_id"),
        "team_name": first_attribute("current_team_name", "team_name"),
        "roster_status": first_attribute("roster_status", "status"),
        "roster_type": first_attribute("roster_type"),
        "source_observed_at": first_attribute("source_observed_at", "last_synced_at", "updated_at"),
    }


def build_player_inventory(
    limit: int = 250,
    *,
    active_only: bool = False,
    team_id: int | None = None,
) -> list[dict[str, Any]]:
    limit = bounded_limit(limit, default=250)
    name_fields = player_name_fields()
    order_field_name = name_fields[0] if name_fields else player_identity_field()

    with managed_database_session() as database_session:
        query = database_session.query(Player)

        if active_only:
            active_field = resolve_model_field("active_status", PLAYER_MODEL_FIELDS)
            if active_field:
                query = query.filter(getattr(Player, active_field).is_(True))

        if team_id is not None:
            team_field = resolve_model_field("current_team_id", PLAYER_MODEL_FIELDS)
            if team_field:
                query = query.filter(getattr(Player, team_field) == team_id)

        players = (
            query
            .order_by(getattr(Player, order_field_name).asc())
            .limit(limit)
            .all()
        )
        return [serialize_player_record(player) for player in players]


# ============================================================
# SECTION 18 - ENTERPRISE PLAYER SEARCH
# ============================================================


def build_search_tokens(query: str) -> list[str]:
    normalized = normalize_search_text(query)
    stop_phrases = (
        "search for",
        "search",
        "look up",
        "lookup",
        "find",
        "show",
        "player",
        "players",
        "who is",
        "tell me about",
    )
    for phrase in stop_phrases:
        normalized = re.sub(
            rf"(?<!\w){re.escape(phrase)}(?!\w)",
            " ",
            normalized,
            flags=re.IGNORECASE,
        )
    return [token for token in collapse_spaces(normalized).split() if token]


def search_database_players(
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    *,
    active_only: bool = False,
    team_id: int | None = None,
) -> list[dict[str, Any]]:
    """Search player identity fields using AND semantics across query tokens."""
    clean_query = collapse_spaces(str(query or ""))
    if not clean_query:
        return []

    limit = bounded_limit(limit)
    tokens = build_search_tokens(clean_query)
    name_fields = player_name_fields()
    identity_field = player_identity_field()

    with managed_database_session() as database_session:
        query_object = database_session.query(Player)

        numeric_query = safe_integer(clean_query)
        if numeric_query is not None:
            query_object = query_object.filter(
                getattr(Player, identity_field) == numeric_query
            )
        elif tokens and or_ is not None and and_ is not None:
            token_filters = []
            for token in tokens:
                field_filters = [
                    getattr(Player, field_name).ilike(f"%{token}%")
                    for field_name in name_fields
                ]
                if field_filters:
                    token_filters.append(or_(*field_filters))
            if token_filters:
                query_object = query_object.filter(and_(*token_filters))
        else:
            # Conservative compatibility fallback.
            primary_name_field = name_fields[0] if name_fields else identity_field
            query_object = query_object.filter(
                getattr(Player, primary_name_field).ilike(f"%{clean_query}%")
            )

        if active_only:
            active_field = resolve_model_field("active_status", PLAYER_MODEL_FIELDS)
            if active_field:
                query_object = query_object.filter(
                    getattr(Player, active_field).is_(True)
                )

        if team_id is not None:
            team_field = resolve_model_field("current_team_id", PLAYER_MODEL_FIELDS)
            if team_field:
                query_object = query_object.filter(
                    getattr(Player, team_field) == team_id
                )

        order_field_name = name_fields[0] if name_fields else identity_field
        players = (
            query_object
            .order_by(getattr(Player, order_field_name).asc())
            .limit(limit)
            .all()
        )

    serialized = [serialize_player_record(player) for player in players]
    normalized_query = normalize_search_text(clean_query)

    def rank(item: Mapping[str, Any]) -> tuple[int, int, str]:
        full_name = normalize_search_text(item.get("full_name") or item.get("name"))
        last_name = normalize_search_text(item.get("last_name"))
        exact = int(full_name == normalized_query)
        surname_exact = int(last_name == normalized_query)
        starts = int(full_name.startswith(normalized_query))
        return (-exact, -surname_exact, -starts, full_name)

    serialized.sort(key=rank)
    return serialized[:limit]


def search_players_with_live_fallback(
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    *,
    season: int = DEFAULT_PLAYER_SEASON,
    sync_on_live_match: bool = True,
    client: Any | None = None,
) -> dict[str, Any]:
    warehouse_matches = search_database_players(query, limit=limit)
    if warehouse_matches:
        return {
            "query": query,
            "source": "AISP2 Database Warehouse",
            "matches": warehouse_matches,
            "match_count": len(warehouse_matches),
            "live_fallback_used": False,
        }

    adapter = MLBClientAdapter(client)
    live_players = adapter.get_all_active_players(season)
    tokens = build_search_tokens(query)
    live_matches: list[dict[str, Any]] = []

    for raw_player in live_players:
        normalized = normalize_player_payload(raw_player)
        full_name = normalize_search_text(normalized.get("full_name"))
        if tokens and not all(token in full_name for token in tokens):
            continue
        live_matches.append(normalized)
        if len(live_matches) >= bounded_limit(limit):
            break

    synced = 0
    if sync_on_live_match and live_matches:
        with managed_database_session() as database_session:
            for normalized in live_matches:
                try:
                    upsert_player_detailed(database_session, normalized)
                    synced += 1
                except Exception:
                    LOGGER.exception("Failed to sync live player match")

    return {
        "query": query,
        "source": "MLB Stats API live fallback",
        "matches": live_matches,
        "match_count": len(live_matches),
        "live_fallback_used": True,
        "synced_to_warehouse": synced,
    }


# ============================================================
# SECTION 19 - OFFICIAL PLAYER STAT SNAPSHOT FETCHING
# ============================================================


def fetch_official_player_stat_snapshots(
    player_id: int,
    season: int = DEFAULT_PLAYER_SEASON,
    *,
    groups: Sequence[str] = ("hitting", "pitching", "fielding"),
    stat_types: Sequence[str] = ("season",),
    client: Any | None = None,
) -> dict[str, Any]:
    """Fetch official MLB stat payloads without fabricating persistence."""
    adapter = MLBClientAdapter(client)
    snapshots: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    observed_at = utc_now()

    for group in groups:
        for stat_type in stat_types:
            try:
                payload = adapter.get_player_stats(
                    player_id=player_id,
                    season=season,
                    group=group,
                    stat_type=stat_type,
                )
                snapshots.append({
                    "player_id": player_id,
                    "season": season,
                    "group": group,
                    "stat_type": stat_type,
                    "source": "MLB Stats API",
                    "observed_at": observed_at.isoformat(),
                    "checksum": payload_checksum(payload),
                    "payload": payload,
                })
            except Exception as exc:
                errors.append({
                    "player_id": player_id,
                    "season": season,
                    "group": group,
                    "stat_type": stat_type,
                    "error": str(exc),
                })

    return {
        "player_id": player_id,
        "season": season,
        "source": "MLB Stats API",
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
        "errors": errors,
        "persistence_ready": False,
        "persistence_requirement": (
            "Add dedicated PlayerSeasonStat and PlayerStatSnapshot models before "
            "persisting these payloads."
        ),
    }


# ============================================================
# SECTION 20 - FRESHNESS AND AUDIT
# ============================================================


def build_player_freshness_report() -> dict[str, Any]:
    timestamp_fields = (
        "source_observed_at",
        "last_synced_at",
        "updated_at",
        "modified_at",
    )
    selected_field = next(
        (field_name for field_name in timestamp_fields if field_name in PLAYER_MODEL_FIELDS),
        None,
    )

    report: dict[str, Any] = {
        "player_count": count_database_players(),
        "active_player_count": count_active_database_players(),
        "timestamp_field": selected_field,
        "latest_observation": None,
        "oldest_observation": None,
        "age_hours": None,
        "fresh": None,
        "target_cadence": "hourly during season; daily reconciliation",
    }

    if selected_field is None or func is None:
        report["freshness_status"] = "timestamp_column_unavailable"
        return report

    with managed_database_session() as database_session:
        column = getattr(Player, selected_field)
        latest, oldest = database_session.query(func.max(column), func.min(column)).one()

    report["latest_observation"] = latest.isoformat() if hasattr(latest, "isoformat") else safe_string(latest)
    report["oldest_observation"] = oldest.isoformat() if hasattr(oldest, "isoformat") else safe_string(oldest)

    if isinstance(latest, datetime):
        normalized_latest = latest if latest.tzinfo else latest.replace(tzinfo=UTC)
        age_hours = (utc_now() - normalized_latest).total_seconds() / 3600.0
        report["age_hours"] = round(age_hours, 3)
        report["fresh"] = age_hours <= 24.0
        report["freshness_status"] = "fresh" if report["fresh"] else "stale"
    else:
        report["freshness_status"] = "timestamp_not_datetime"

    return report


def audit_player_warehouse() -> dict[str, Any]:
    sample = build_player_inventory(limit=25)
    missing_name = sum(1 for item in sample if not item.get("full_name"))
    missing_id = sum(1 for item in sample if not item.get("mlb_player_id"))
    return {
        "module": INGESTION_NAME,
        "version": INGESTION_VERSION,
        "warehouse_player_count": count_database_players(),
        "warehouse_active_player_count": count_active_database_players(),
        "sample_size": len(sample),
        "sample_missing_name": missing_name,
        "sample_missing_id": missing_id,
        "search_fields": player_name_fields(),
        "identity_field": player_identity_field(),
        "freshness": build_player_freshness_report(),
        "official_sources": OFFICIAL_PLAYER_DATA_SOURCES,
        "ready_for_identity_search": bool(player_name_fields()),
        "ready_for_roster_refresh": True,
        "ready_for_stat_persistence": False,
        "missing_persistence_models": [
            "RosterMembership",
            "PlayerSeasonStat",
            "PlayerGameLog",
            "PlayerStatSplit",
            "StatcastEvent",
            "SourceSnapshot",
            "IngestionRun",
        ],
    }


# ============================================================
# SECTION 21 - CONTINUOUS REFRESH PLANNING
# ============================================================


def build_continuous_refresh_plan(
    *,
    in_season: bool = True,
) -> dict[str, Any]:
    return {
        "mode": "continuous_official_source_refresh",
        "in_season": in_season,
        "jobs": [
            {
                "name": "roster_delta_refresh",
                "source": "MLB Stats API rosters",
                "cadence": "hourly" if in_season else "daily",
                "function": "ingest_mlb_players(mode='roster_authoritative')",
                "purpose": "Current player-team membership and roster status",
            },
            {
                "name": "player_identity_reconciliation",
                "source": "MLB Stats API people",
                "cadence": "daily",
                "purpose": "Name, position, handedness, status, and biography changes",
            },
            {
                "name": "player_season_stats_refresh",
                "source": "MLB Stats API stats",
                "cadence": "after games plus nightly reconciliation",
                "purpose": "Season, game-log, and split statistics",
                "requires": "PlayerSeasonStat and snapshot tables",
            },
            {
                "name": "statcast_refresh",
                "source": "Baseball Savant / Statcast",
                "cadence": "daily after official publication",
                "purpose": "Pitch-level and batted-ball advanced metrics",
                "requires": "StatcastEvent and StatcastAggregate tables",
            },
            {
                "name": "warehouse_audit",
                "source": "AISP2 warehouse",
                "cadence": "nightly",
                "purpose": "Coverage, duplicates, missing IDs, freshness, and source reconciliation",
            },
        ],
        "recommended_execution": (
            "Use a Render Cron Job, worker, or external scheduler. Web requests "
            "must not perform full-league synchronization."
        ),
        "conflict_policy": (
            "MLB roster membership outranks stale local team assignments; MLB person "
            "identity outranks aliases; source observations are append-only when "
            "snapshot tables are available."
        ),
    }


# ============================================================
# SECTION 22 - REPORTING
# ============================================================


def build_player_ingestion_summary(report: Mapping[str, Any]) -> str:
    metrics = report.get("metrics", {}) if isinstance(report, Mapping) else {}
    return (
        f"{INGESTION_NAME} completed | "
        f"Season: {report.get('season')} | "
        f"Mode: {report.get('mode')} | "
        f"Raw Players: {report.get('raw_player_count', 0)} | "
        f"Created: {report.get('created', metrics.get('created', 0))} | "
        f"Updated: {report.get('updated', metrics.get('updated', 0))} | "
        f"Unchanged: {report.get('unchanged', metrics.get('unchanged', 0))} | "
        f"Skipped: {report.get('skipped', metrics.get('skipped', 0))} | "
        f"Database Players: {report.get('database_player_count_after_ingestion', 0)}"
    )



# ============================================================
# SECTION 22.01 - PHASE 11 PLAYER WAREHOUSE MODEL REGISTRY
# ============================================================

ROSTER_MODEL_FIELDS: Final[set[str]] = model_column_names(RosterEntry)
SEASON_STAT_MODEL_FIELDS: Final[set[str]] = model_column_names(PlayerSeasonStat)
GAME_LOG_MODEL_FIELDS: Final[set[str]] = model_column_names(PlayerGameStat)
SPLIT_STAT_MODEL_FIELDS: Final[set[str]] = model_column_names(PlayerSplitStat)
STATCAST_MODEL_FIELDS: Final[set[str]] = model_column_names(PlayerStatcastMetric)
IMPORT_LOG_MODEL_FIELDS: Final[set[str]] = model_column_names(RawDataImportLog)


def filter_model_payload(
    payload: Mapping[str, Any],
    available_fields: set[str],
) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key in available_fields
    }


def apply_model_changes(
    instance: Any,
    payload: Mapping[str, Any],
    available_fields: set[str],
) -> list[str]:
    changed_fields: list[str] = []

    for field_name, field_value in payload.items():
        if field_name not in available_fields:
            continue

        if getattr(instance, field_name, None) != field_value:
            setattr(instance, field_name, field_value)
            changed_fields.append(field_name)

    return sorted(changed_fields)


# ============================================================
# SECTION 22.02 - TEAM AND PLAYER RESOLUTION
# ============================================================

def find_team_by_mlb_id(
    database_session: Any,
    mlb_team_id: int,
) -> Team | None:
    return (
        database_session.query(Team)
        .filter(Team.mlb_team_id == int(mlb_team_id))
        .first()
    )


def find_player_by_mlb_id(
    database_session: Any,
    mlb_player_id: int,
) -> Player | None:
    return (
        database_session.query(Player)
        .filter(Player.mlb_player_id == int(mlb_player_id))
        .first()
    )


def require_team_by_mlb_id(
    database_session: Any,
    mlb_team_id: int,
) -> Team:
    team = find_team_by_mlb_id(database_session, mlb_team_id)

    if team is None:
        raise PlayerValidationError(
            f"MLB team ID {mlb_team_id} is not present in the warehouse. "
            "Run team ingestion first."
        )

    return team


# ============================================================
# SECTION 22.03 - ROSTER ENTRY PERSISTENCE
# ============================================================

def upsert_roster_membership(
    database_session: Any,
    normalized_player: Mapping[str, Any],
    *,
    season: int,
) -> dict[str, Any]:
    mlb_player_id = safe_integer(normalized_player.get("mlb_player_id"))
    mlb_team_id = safe_integer(normalized_player.get("current_team_id"))
    roster_type = safe_string(normalized_player.get("roster_type")) or "active"

    if mlb_player_id is None:
        raise PlayerValidationError("Roster membership requires mlb_player_id")

    if mlb_team_id is None:
        raise PlayerValidationError("Roster membership requires current_team_id")

    player = find_player_by_mlb_id(database_session, mlb_player_id)

    if player is None:
        raise PlayerValidationError(
            f"Player {mlb_player_id} must be persisted before roster membership"
        )

    team = require_team_by_mlb_id(database_session, mlb_team_id)

    existing = (
        database_session.query(RosterEntry)
        .filter(
            RosterEntry.season == int(season),
            RosterEntry.roster_type == roster_type,
            RosterEntry.team_id == team.id,
            RosterEntry.player_id == player.id,
        )
        .first()
    )

    values = filter_model_payload(
        {
            "season": int(season),
            "roster_type": roster_type,
            "jersey_number": normalized_player.get("jersey_number"),
            "status_code": normalized_player.get("roster_status_code"),
            "status_description": normalized_player.get("roster_status"),
            "team_id": team.id,
            "player_id": player.id,
        },
        ROSTER_MODEL_FIELDS,
    )

    if existing is None:
        record = RosterEntry(**values)
        database_session.add(record)
        database_session.flush()
        action = "created"
        changed_fields = sorted(values)
    else:
        changed_fields = apply_model_changes(
            existing,
            values,
            ROSTER_MODEL_FIELDS,
        )
        action = "updated" if changed_fields else "unchanged"

    return {
        "action": action,
        "player_id": player.id,
        "team_id": team.id,
        "season": int(season),
        "roster_type": roster_type,
        "changed_fields": changed_fields,
    }


# ============================================================
# SECTION 22.04 - STAT PAYLOAD HELPERS
# ============================================================

def iter_mlb_stat_splits(
    payload: Mapping[str, Any],
) -> Iterable[tuple[dict[str, Any], dict[str, Any]]]:
    for stat_block in payload.get("stats", []) or []:
        stat_block = coerce_mapping(stat_block)

        for split in stat_block.get("splits", []) or []:
            split_mapping = coerce_mapping(split)
            yield split_mapping, coerce_mapping(split_mapping.get("stat"))


def first_mlb_stat_split(
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for split, stat in iter_mlb_stat_splits(payload):
        return split, stat

    return None


def calculate_rate(
    numerator: int | float | None,
    denominator: int | float | None,
) -> float | None:
    numerator_value = safe_float(numerator)
    denominator_value = safe_float(denominator)

    if numerator_value is None or denominator_value in (None, 0.0):
        return None

    return numerator_value / denominator_value


def derive_singles(
    hits: int | None,
    doubles: int | None,
    triples: int | None,
    home_runs: int | None,
) -> int | None:
    if any(value is None for value in (hits, doubles, triples, home_runs)):
        return None

    return max(0, int(hits) - int(doubles) - int(triples) - int(home_runs))


def normalize_mlb_stat_values(
    stat: Mapping[str, Any],
) -> dict[str, Any]:
    hits = safe_integer(stat.get("hits"))
    doubles = safe_integer(stat.get("doubles"))
    triples = safe_integer(stat.get("triples"))
    home_runs = safe_integer(stat.get("homeRuns") or stat.get("home_runs"))
    plate_appearances = safe_integer(
        stat.get("plateAppearances") or stat.get("plate_appearances")
    )
    walks = safe_integer(stat.get("baseOnBalls") or stat.get("walks"))
    strikeouts = safe_integer(stat.get("strikeOuts") or stat.get("strikeouts"))
    batting_average = safe_float(stat.get("avg") or stat.get("battingAverage"))
    slugging = safe_float(stat.get("slg") or stat.get("sluggingPercentage"))

    return {
        "games_played": safe_integer(stat.get("gamesPlayed") or stat.get("games")),
        "plate_appearances": plate_appearances,
        "at_bats": safe_integer(stat.get("atBats") or stat.get("at_bats")),
        "runs": safe_integer(stat.get("runs")),
        "hits": hits,
        "singles": derive_singles(hits, doubles, triples, home_runs),
        "doubles": doubles,
        "triples": triples,
        "home_runs": home_runs,
        "rbi": safe_integer(stat.get("rbi")),
        "walks": walks,
        "intentional_walks": safe_integer(stat.get("intentionalWalks")),
        "strikeouts": strikeouts,
        "hit_by_pitch": safe_integer(stat.get("hitByPitch")),
        "sacrifice_flies": safe_integer(stat.get("sacFlies")),
        "stolen_bases": safe_integer(stat.get("stolenBases")),
        "caught_stealing": safe_integer(stat.get("caughtStealing")),
        "batting_average": batting_average,
        "on_base_percentage": safe_float(stat.get("obp") or stat.get("onBasePercentage")),
        "slugging_percentage": slugging,
        "ops": safe_float(stat.get("ops")),
        "isolated_power": (
            slugging - batting_average
            if slugging is not None and batting_average is not None
            else None
        ),
        "babip": safe_float(stat.get("babip")),
        "walk_rate": calculate_rate(walks, plate_appearances),
        "strikeout_rate": calculate_rate(strikeouts, plate_appearances),
        "home_run_rate": calculate_rate(home_runs, plate_appearances),
        "woba": safe_float(stat.get("woba")),
        "wrc_plus": safe_float(stat.get("wrcPlus") or stat.get("wrc_plus")),
        "wins": safe_integer(stat.get("wins")),
        "losses": safe_integer(stat.get("losses")),
        "era": safe_float(stat.get("era")),
        "whip": safe_float(stat.get("whip")),
        "saves": safe_integer(stat.get("saves")),
        "innings_pitched": safe_float(stat.get("inningsPitched")),
    }


# ============================================================
# SECTION 22.05 - SEASON STAT PERSISTENCE
# ============================================================

def persist_player_season_stats(
    database_session: Any,
    *,
    player: Player,
    team: Team | None,
    season: int,
    stat_group: str,
    stat_payload: Mapping[str, Any],
    observed_at: datetime,
) -> dict[str, Any]:
    values = filter_model_payload(
        {
            "player_id": player.id,
            "season": int(season),
            "sport_id": 1,
            "team_id": team.id if team else None,
            "stat_group": stat_group,
            **normalize_mlb_stat_values(stat_payload),
            "source_name": "MLB Stats API",
            "source_updated_at": observed_at,
            "raw_stat_json": canonical_json(stat_payload),
        },
        SEASON_STAT_MODEL_FIELDS,
    )

    query = (
        database_session.query(PlayerSeasonStat)
        .filter(
            PlayerSeasonStat.player_id == player.id,
            PlayerSeasonStat.season == int(season),
            PlayerSeasonStat.stat_group == stat_group,
        )
    )

    if team is not None and "team_id" in SEASON_STAT_MODEL_FIELDS:
        query = query.filter(PlayerSeasonStat.team_id == team.id)

    existing = query.first()

    if existing is None:
        record = PlayerSeasonStat(**values)
        database_session.add(record)
        action = "created"
        changed_fields = sorted(values)
    else:
        changed_fields = apply_model_changes(
            existing,
            values,
            SEASON_STAT_MODEL_FIELDS,
        )
        action = "updated" if changed_fields else "unchanged"

    return {
        "action": action,
        "player_id": player.id,
        "season": int(season),
        "stat_group": stat_group,
        "changed_fields": changed_fields,
    }


# ============================================================
# SECTION 22.06 - GAME LOG PERSISTENCE
# ============================================================

def persist_player_game_log(
    database_session: Any,
    *,
    player: Player,
    season: int,
    stat_group: str,
    split: Mapping[str, Any],
    stat: Mapping[str, Any],
) -> dict[str, Any]:
    game = coerce_mapping(split.get("game"))
    team_source = coerce_mapping(split.get("team"))
    opponent_source = coerce_mapping(split.get("opponent"))

    team = find_team_by_mlb_id(database_session, safe_integer(team_source.get("id")) or -1)
    opponent_team = find_team_by_mlb_id(
        database_session,
        safe_integer(opponent_source.get("id")) or -1,
    )

    values = filter_model_payload(
        {
            "player_id": player.id,
            "game_pk": safe_integer(game.get("gamePk") or split.get("gamePk")),
            "season": int(season),
            "game_date": safe_string(split.get("date") or split.get("gameDate")),
            "team_id": team.id if team else None,
            "opponent_team_id": opponent_team.id if opponent_team else None,
            "player_name": player.full_name,
            "team_name": safe_string(team_source.get("name")),
            "opponent_team_name": safe_string(opponent_source.get("name")),
            **normalize_mlb_stat_values(stat),
            "pitcher_strikeouts": (
                safe_integer(stat.get("strikeOuts"))
                if stat_group == "pitching"
                else None
            ),
            "earned_runs": safe_integer(stat.get("earnedRuns")),
            "walks_allowed": safe_integer(stat.get("baseOnBalls")),
            "hits_allowed": safe_integer(stat.get("hits")),
            "raw_game_stat_json": canonical_json({
                "group": stat_group,
                "split": split,
                "stat": stat,
            }),
            "updated_at": utc_now().isoformat(),
        },
        GAME_LOG_MODEL_FIELDS,
    )

    query = database_session.query(PlayerGameStat).filter(
        PlayerGameStat.player_id == player.id
    )

    if values.get("game_pk") is not None:
        query = query.filter(PlayerGameStat.game_pk == values["game_pk"])
    else:
        query = query.filter(PlayerGameStat.game_date == values.get("game_date"))

    existing = query.first()

    if existing is None:
        database_session.add(PlayerGameStat(**values))
        action = "created"
        changed_fields = sorted(values)
    else:
        changed_fields = apply_model_changes(existing, values, GAME_LOG_MODEL_FIELDS)
        action = "updated" if changed_fields else "unchanged"

    return {
        "action": action,
        "player_id": player.id,
        "game_pk": values.get("game_pk"),
        "game_date": values.get("game_date"),
        "changed_fields": changed_fields,
    }


# ============================================================
# SECTION 22.07 - SPLIT STAT PERSISTENCE
# ============================================================

def resolve_split_identity(
    split: Mapping[str, Any],
) -> tuple[str, str, str | None]:
    source = coerce_mapping(split.get("split"))
    split_type = safe_string(source.get("type") or split.get("splitType")) or "unknown"
    split_key = safe_string(
        source.get("code")
        or source.get("id")
        or split.get("code")
        or split.get("description")
    ) or "unknown"
    split_label = safe_string(source.get("description") or split.get("description"))
    return split_type, split_key, split_label


def persist_player_split_stat(
    database_session: Any,
    *,
    player: Player,
    team: Team | None,
    season: int,
    stat_group: str,
    split: Mapping[str, Any],
    stat: Mapping[str, Any],
    observed_at: datetime,
) -> dict[str, Any]:
    split_type, split_key, split_label = resolve_split_identity(split)

    values = filter_model_payload(
        {
            "player_id": player.id,
            "team_id": team.id if team else None,
            "season": int(season),
            "stat_group": stat_group,
            "split_type": split_type,
            "split_key": split_key,
            "split_label": split_label,
            **normalize_mlb_stat_values(stat),
            "source_name": "MLB Stats API",
            "source_updated_at": observed_at,
            "raw_stat_json": canonical_json({"split": split, "stat": stat}),
        },
        SPLIT_STAT_MODEL_FIELDS,
    )

    query = (
        database_session.query(PlayerSplitStat)
        .filter(
            PlayerSplitStat.player_id == player.id,
            PlayerSplitStat.season == int(season),
            PlayerSplitStat.stat_group == stat_group,
            PlayerSplitStat.split_type == split_type,
            PlayerSplitStat.split_key == split_key,
        )
    )

    if team is not None and "team_id" in SPLIT_STAT_MODEL_FIELDS:
        query = query.filter(PlayerSplitStat.team_id == team.id)

    existing = query.first()

    if existing is None:
        database_session.add(PlayerSplitStat(**values))
        action = "created"
        changed_fields = sorted(values)
    else:
        changed_fields = apply_model_changes(existing, values, SPLIT_STAT_MODEL_FIELDS)
        action = "updated" if changed_fields else "unchanged"

    return {
        "action": action,
        "player_id": player.id,
        "season": int(season),
        "split_type": split_type,
        "split_key": split_key,
        "changed_fields": changed_fields,
    }


# ============================================================
# SECTION 22.08 - STATCAST AGGREGATE PERSISTENCE
# ============================================================

STATCAST_FIELD_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "average_exit_velocity": ("average_exit_velocity", "avg_exit_velocity", "avg_hit_speed"),
    "maximum_exit_velocity": ("maximum_exit_velocity", "max_exit_velocity"),
    "barrel_count": ("barrel_count", "barrels"),
    "barrel_rate": ("barrel_rate", "barrel_percent", "barrel_batted_rate"),
    "hard_hit_count": ("hard_hit_count", "hard_hits"),
    "hard_hit_rate": ("hard_hit_rate", "hard_hit_percent"),
    "average_launch_angle": ("average_launch_angle", "launch_angle", "avg_launch_angle"),
    "sweet_spot_rate": ("sweet_spot_rate", "sweet_spot_percent"),
    "expected_batting_average": ("expected_batting_average", "xba"),
    "expected_slugging_percentage": ("expected_slugging_percentage", "expected_slugging", "xslg"),
    "expected_woba": ("expected_woba", "xwoba"),
    "sprint_speed": ("sprint_speed",),
    "batted_ball_count": ("batted_ball_count", "batted_balls"),
    "whiff_rate": ("whiff_rate", "whiff_percent"),
    "chase_rate": ("chase_rate", "chase_percent"),
    "zone_contact_rate": ("zone_contact_rate", "zone_contact_percent"),
    "squared_up_rate": ("squared_up_rate", "squared_up_percent"),
}


def first_alias_value(
    payload: Mapping[str, Any],
    aliases: Sequence[str],
) -> Any:
    for alias in aliases:
        if payload.get(alias) not in (None, ""):
            return payload.get(alias)
    return None


def normalize_statcast_aggregate(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    values: dict[str, Any] = {}
    integer_fields = {"barrel_count", "hard_hit_count", "batted_ball_count"}

    for field_name, aliases in STATCAST_FIELD_ALIASES.items():
        raw_value = first_alias_value(payload, aliases)
        values[field_name] = (
            safe_integer(raw_value)
            if field_name in integer_fields
            else safe_float(raw_value)
        )

    sample_size = values.get("batted_ball_count")
    values["sample_size_status"] = (
        "unknown"
        if sample_size is None
        else "insufficient_sample"
        if sample_size < 25
        else "limited_sample"
        if sample_size < 100
        else "usable_sample"
    )
    return values


def persist_player_statcast_aggregate(
    database_session: Any,
    *,
    player: Player,
    team: Team | None,
    season: int,
    payload: Mapping[str, Any],
    observed_at: datetime,
) -> dict[str, Any]:
    values = filter_model_payload(
        {
            "player_id": player.id,
            "team_id": team.id if team else None,
            "mlb_player_id": player.mlb_player_id,
            "season": int(season),
            "stat_group": "hitting",
            **normalize_statcast_aggregate(payload),
            "source_name": "Baseball Savant",
            "source_updated_at": observed_at,
            "raw_stat_json": canonical_json(payload),
        },
        STATCAST_MODEL_FIELDS,
    )

    query = (
        database_session.query(PlayerStatcastMetric)
        .filter(
            PlayerStatcastMetric.player_id == player.id,
            PlayerStatcastMetric.season == int(season),
            PlayerStatcastMetric.stat_group == "hitting",
        )
    )

    if team is not None and "team_id" in STATCAST_MODEL_FIELDS:
        query = query.filter(PlayerStatcastMetric.team_id == team.id)

    existing = query.first()

    if existing is None:
        database_session.add(PlayerStatcastMetric(**values))
        action = "created"
        changed_fields = sorted(values)
    else:
        changed_fields = apply_model_changes(existing, values, STATCAST_MODEL_FIELDS)
        action = "updated" if changed_fields else "unchanged"

    return {
        "action": action,
        "player_id": player.id,
        "season": int(season),
        "changed_fields": changed_fields,
    }


# ============================================================
# SECTION 22.09 - PLAYER DETAIL INGESTION
# ============================================================

def ingest_player_detail_layers(
    database_session: Any,
    *,
    adapter: MLBClientAdapter,
    player: Player,
    team: Team | None,
    season: int,
    include_game_logs: bool = True,
    include_splits: bool = True,
    include_statcast: bool = True,
) -> dict[str, Any]:
    observed_at = utc_now()
    report = {
        "player_id": player.id,
        "mlb_player_id": player.mlb_player_id,
        "season": int(season),
        "season_stats": [],
        "game_logs": [],
        "splits": [],
        "statcast": None,
        "errors": [],
    }

    for stat_group in ("hitting", "pitching"):
        try:
            payload = adapter.get_player_stats(
                player.mlb_player_id,
                season,
                group=stat_group,
                stat_type="season",
            )
            first_split = first_mlb_stat_split(payload)

            if first_split:
                _, stat = first_split
                report["season_stats"].append(
                    persist_player_season_stats(
                        database_session,
                        player=player,
                        team=team,
                        season=season,
                        stat_group=stat_group,
                        stat_payload=stat,
                        observed_at=observed_at,
                    )
                )
        except Exception as error:
            report["errors"].append({
                "stage": "season_stats",
                "stat_group": stat_group,
                "error": str(error),
            })

        if include_game_logs:
            try:
                payload = adapter.get_player_stats(
                    player.mlb_player_id,
                    season,
                    group=stat_group,
                    stat_type="gameLog",
                )
                for split, stat in iter_mlb_stat_splits(payload):
                    report["game_logs"].append(
                        persist_player_game_log(
                            database_session,
                            player=player,
                            season=season,
                            stat_group=stat_group,
                            split=split,
                            stat=stat,
                        )
                    )
            except Exception as error:
                report["errors"].append({
                    "stage": "game_logs",
                    "stat_group": stat_group,
                    "error": str(error),
                })

        if include_splits:
            try:
                payload = adapter.get_player_stats(
                    player.mlb_player_id,
                    season,
                    group=stat_group,
                    stat_type="statSplits",
                )
                for split, stat in iter_mlb_stat_splits(payload):
                    report["splits"].append(
                        persist_player_split_stat(
                            database_session,
                            player=player,
                            team=team,
                            season=season,
                            stat_group=stat_group,
                            split=split,
                            stat=stat,
                            observed_at=observed_at,
                        )
                    )
            except Exception as error:
                report["errors"].append({
                    "stage": "splits",
                    "stat_group": stat_group,
                    "error": str(error),
                })

    if include_statcast:
        try:
            payload = adapter.get_statcast_aggregate(player.mlb_player_id, season)
            if payload:
                report["statcast"] = persist_player_statcast_aggregate(
                    database_session,
                    player=player,
                    team=team,
                    season=season,
                    payload=payload,
                    observed_at=observed_at,
                )
            else:
                report["errors"].append({
                    "stage": "statcast",
                    "warning": "No aggregate Statcast payload available",
                })
        except Exception as error:
            report["errors"].append({
                "stage": "statcast",
                "error": str(error),
            })

    return report


# ============================================================
# SECTION 22.10 - COMPLETE PLAYER WAREHOUSE INGESTION
# ============================================================

def ingest_complete_player_warehouse(
    season: int = DEFAULT_PLAYER_SEASON,
    *,
    roster_types: Sequence[str] = DEFAULT_ROSTER_TYPES,
    hydrate_people: bool = True,
    include_game_logs: bool = True,
    include_splits: bool = True,
    include_statcast: bool = True,
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS,
    player_limit: int | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    adapter = MLBClientAdapter(client)
    initialize_database()

    source_result = collect_current_mlb_roster_players(
        season=season,
        roster_types=roster_types,
        hydrate_people=hydrate_people,
        request_delay_seconds=request_delay_seconds,
        client=adapter.client,
    )

    players = list(source_result.get("players", []))
    if player_limit is not None:
        players = players[:max(0, int(player_limit))]

    report: dict[str, Any] = {
        "ingestion": "complete_player_warehouse",
        "version": INGESTION_VERSION,
        "phase": INGESTION_PHASE,
        "season": int(season),
        "started_at": utc_now().isoformat(),
        "source_player_count": len(players),
        "coverage": source_result.get("coverage", {}),
        "created_players": 0,
        "updated_players": 0,
        "unchanged_players": 0,
        "created_roster_entries": 0,
        "updated_roster_entries": 0,
        "unchanged_roster_entries": 0,
        "detail_reports": [],
        "errors": list(source_result.get("errors", [])),
    }

    with managed_database_session(commit_on_success=False) as database_session:
        try:
            for raw_player in players:
                savepoint = database_session.begin_nested()
                try:
                    normalized = normalize_player_payload(raw_player)
                    player_result = upsert_player_detailed(database_session, normalized)
                    report[f"{player_result.action}_players"] += 1

                    roster_result = upsert_roster_membership(
                        database_session,
                        normalized,
                        season=season,
                    )
                    report[f"{roster_result['action']}_roster_entries"] += 1

                    player = find_player_by_mlb_id(
                        database_session,
                        int(normalized["mlb_player_id"]),
                    )
                    team = find_team_by_mlb_id(
                        database_session,
                        int(normalized["current_team_id"]),
                    ) if normalized.get("current_team_id") else None

                    if player is None:
                        raise PlayerValidationError("Player could not be reloaded after upsert")

                    detail_report = ingest_player_detail_layers(
                        database_session,
                        adapter=adapter,
                        player=player,
                        team=team,
                        season=season,
                        include_game_logs=include_game_logs,
                        include_splits=include_splits,
                        include_statcast=include_statcast,
                    )
                    report["detail_reports"].append(detail_report)
                    savepoint.commit()
                except Exception as error:
                    savepoint.rollback()
                    append_bounded_error(report, {
                        "stage": "player_transaction",
                        "mlb_player_id": raw_player.get("id"),
                        "full_name": raw_player.get("fullName"),
                        "error": str(error),
                    })

            safe_commit(database_session, raise_on_error=True)
        except Exception:
            safe_rollback(database_session, raise_on_error=False)
            raise

    report["database_inventory"] = collect_database_inventory()
    report["player_explorer_readiness"] = player_explorer_database_readiness()
    report["status"] = "completed_with_errors" if report["errors"] else "completed"
    report["success"] = not bool(report["errors"])
    report["finished_at"] = utc_now().isoformat()
    report["duration_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
    return report


# ============================================================
# SECTION 22.11 - COMPLETE WAREHOUSE AUDIT
# ============================================================

def audit_complete_player_warehouse() -> dict[str, Any]:
    with managed_database_session(commit_on_success=False) as database_session:
        duplicate_ids = (
            database_session.query(Player.mlb_player_id, func.count(Player.id))
            .group_by(Player.mlb_player_id)
            .having(func.count(Player.id) > 1)
            .all()
        )

        counts = {
            "players": database_session.query(Player).count(),
            "active_players": database_session.query(Player).filter(Player.active_status.is_(True)).count(),
            "roster_entries": database_session.query(RosterEntry).count(),
            "season_stats": database_session.query(PlayerSeasonStat).count(),
            "game_logs": database_session.query(PlayerGameStat).count(),
            "split_stats": database_session.query(PlayerSplitStat).count(),
            "statcast_metrics": database_session.query(PlayerStatcastMetric).count(),
        }

        active_players_missing_team = (
            database_session.query(Player)
            .filter(Player.active_status.is_(True), Player.current_team_id.is_(None))
            .count()
        )

    checks = {
        "players_loaded": counts["players"] > 0,
        "active_players_loaded": counts["active_players"] > 0,
        "roster_entries_loaded": counts["roster_entries"] > 0,
        "season_stats_loaded": counts["season_stats"] > 0,
        "game_logs_loaded": counts["game_logs"] > 0,
        "split_stats_loaded": counts["split_stats"] > 0,
        "statcast_metrics_loaded": counts["statcast_metrics"] > 0,
        "no_duplicate_mlb_player_ids": len(duplicate_ids) == 0,
        "active_players_have_team": active_players_missing_team == 0,
    }

    return {
        "status": "ok" if all(checks.values()) else "incomplete",
        "checks": checks,
        "counts": counts,
        "duplicate_mlb_player_ids": [
            {"mlb_player_id": row[0], "count": row[1]}
            for row in duplicate_ids
        ],
        "active_players_missing_team": active_players_missing_team,
        "database_inventory": collect_database_inventory(),
        "player_explorer_readiness": player_explorer_database_readiness(),
    }


# ============================================================
# SECTION 23 - VALIDATION
# ============================================================


def validate_player_ingestion_module() -> dict[str, Any]:
    sample = {
        "id": 592450,
        "fullName": "Aaron Judge",
        "firstName": "Aaron",
        "lastName": "Judge",
        "primaryPosition": {"name": "Outfielder", "code": "O"},
        "batSide": {"code": "R"},
        "pitchHand": {"code": "R"},
        "active": True,
        "_aisp2_team_id": 147,
        "_aisp2_team_name": "New York Yankees",
        "_aisp2_roster_type": "active",
        "_aisp2_observed_at": utc_now().isoformat(),
    }
    normalized = normalize_player_payload(sample)
    validation_errors = validate_normalized_player(normalized)
    search_tokens = build_search_tokens("search Aaron Judge")
    persisted, ignored = persistence_payload(normalized)
    return {
        "status": "ok" if not validation_errors and search_tokens == ["aaron", "judge"] else "failed",
        "normalized_player_id": normalized.get("mlb_player_id"),
        "normalized_full_name": normalized.get("full_name"),
        "normalized_team_name": normalized.get("current_team_name"),
        "search_tokens": search_tokens,
        "validation_errors": validation_errors,
        "persisted_fields": sorted(persisted),
        "ignored_fields": sorted(ignored),
        "player_model_fields": sorted(PLAYER_MODEL_FIELDS),
        "identity_field": player_identity_field(),
        "search_fields": player_name_fields(),
    }


# ============================================================
# SECTION 24 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "INGESTION_NAME",
    "INGESTION_VERSION",
    "INGESTION_PHASE",
    "INGESTION_PATH",
    "DEFAULT_PLAYER_SEASON",
    "DEFAULT_ROSTER_TYPES",
    "OFFICIAL_PLAYER_DATA_SOURCES",
    "PlayerIngestionError",
    "PlayerSourceError",
    "PlayerValidationError",
    "SourceObservation",
    "NormalizedPlayerRecord",
    "PlayerUpsertResult",
    "IngestionMetrics",
    "safe_nested_get",
    "safe_string",
    "safe_integer",
    "safe_boolean",
    "normalize_search_text",
    "normalize_player_payload",
    "validate_normalized_player",
    "upsert_player",
    "upsert_player_detailed",
    "collect_current_mlb_roster_players",
    "ingest_mlb_players",
    "count_database_players",
    "count_active_database_players",
    "build_player_inventory",
    "search_database_players",
    "search_players_with_live_fallback",
    "fetch_official_player_stat_snapshots",
    "build_player_freshness_report",
    "audit_player_warehouse",
    "build_continuous_refresh_plan",
    "build_player_ingestion_summary",
    "validate_player_ingestion_module",
    "find_team_by_mlb_id",
    "find_player_by_mlb_id",
    "upsert_roster_membership",
    "normalize_mlb_stat_values",
    "persist_player_season_stats",
    "persist_player_game_log",
    "persist_player_split_stat",
    "normalize_statcast_aggregate",
    "persist_player_statcast_aggregate",
    "ingest_player_detail_layers",
    "ingest_complete_player_warehouse",
    "audit_complete_player_warehouse",
]


# ============================================================
# SECTION 25 - LOCAL EXECUTION
# ============================================================

if __name__ == "__main__":
    print(json.dumps(validate_player_ingestion_module(), indent=2, default=str))
    print(json.dumps(build_continuous_refresh_plan(), indent=2, default=str))
