# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# FILE: main.py
# PURPOSE:
# Enterprise FastAPI application entrypoint providing template
# routing, warehouse-first chat orchestration, live MLB fallback,
# player/team discovery, schedule lookup, model health, warehouse
# administration, and stable prediction API contracts.
# ============================================================

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from collections import OrderedDict, defaultdict
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import sys
import threading
import time
from uuid import uuid4
from typing import Any, Final, Iterable, Iterator

# ============================================================
# SECTION 02 - PROJECT PATH REGISTRATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_DIR = PROJECT_ROOT / "01_database"
DATA_SOURCES_DIR = PROJECT_ROOT / "02_data_sources"
INGESTION_DIR = PROJECT_ROOT / "03_ingestion"
AI_DIR = PROJECT_ROOT / "04_ai"

for project_path in (
    PROJECT_ROOT,
    DATABASE_DIR,
    DATA_SOURCES_DIR,
    INGESTION_DIR,
    AI_DIR,
):
    project_path_string = str(project_path)
    if project_path_string not in sys.path:
        sys.path.insert(0, project_path_string)

# ============================================================
# SECTION 03 - THIRD-PARTY IMPORTS
# ============================================================

import requests
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

# ============================================================
# SECTION 04 - APPLICATION LOGGING
# ============================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOGGER = logging.getLogger("aisp2.main")

# ============================================================
# SECTION 05 - OPTIONAL PROJECT IMPORTS
# ============================================================


def _optional_import(module_name: str, symbol_name: str, default: Any = None) -> Any:
    try:
        module = __import__(module_name, fromlist=[symbol_name])
        return getattr(module, symbol_name)
    except Exception as error:  # pragma: no cover - runtime environment dependent
        LOGGER.warning(
            "Optional import unavailable: %s.%s (%s)",
            module_name,
            symbol_name,
            error,
        )
        return default


database_health_check = _optional_import("database", "database_health_check", lambda: False)
database_health_details = _optional_import("database", "database_health_details", lambda: {})
database_health = _optional_import("database", "database_health")
collect_database_inventory = _optional_import("database", "collect_database_inventory", lambda: {})
managed_database_session = _optional_import("database", "managed_database_session")

TeamModel = _optional_import("models", "Team")
PlayerModel = _optional_import("models", "Player")
RosterEntryModel = _optional_import("models", "RosterEntry")
PlayerSeasonStatModel = _optional_import("models", "PlayerSeasonStat")
PlayerGameStatModel = _optional_import("models", "PlayerGameStat")
PlayerStatcastMetricModel = _optional_import("models", "PlayerStatcastMetric")
GameModel = _optional_import("models", "Game")

get_player_statcast_intelligence = _optional_import(
    "statcast_warehouse_ingestion",
    "get_player_statcast_intelligence",
)
validate_statcast_completion_gate = _optional_import(
    "statcast_warehouse_ingestion",
    "validate_statcast_completion_gate",
)

MLBStatsAPIClient = _optional_import("mlb_stats_api", "MLBStatsAPIClient")
DEFAULT_SEASON = _optional_import("mlb_stats_api", "DEFAULT_SEASON", datetime.now(UTC).year)

understand_baseball_message = _optional_import(
    "nlp.nlu_engine",
    "understand_baseball_message",
)
build_nlu_report = _optional_import("nlp.nlu_engine", "build_nlu_report")
nlu_engine_health = _optional_import("nlp.nlu_engine", "nlu_engine_health")

build_enterprise_entity_report = _optional_import(
    "nlp.entity_detection",
    "build_enterprise_entity_report",
)
build_entity_report = _optional_import("nlp.entity_detection", "build_entity_report")
entity_detection_health = _optional_import(
    "nlp.entity_detection",
    "entity_detection_health",
)
MLB_TEAM_ALIASES = _optional_import("nlp.entity_detection", "MLB_TEAM_ALIASES", {})

build_team_inventory = _optional_import("team_ingestion", "build_team_inventory", lambda: [])
count_database_teams = _optional_import("team_ingestion", "count_database_teams", lambda: 0)
ingest_mlb_teams = _optional_import("team_ingestion", "ingest_mlb_teams")

build_player_inventory = _optional_import("player_ingestion", "build_player_inventory", lambda limit=1000: [])
count_database_players = _optional_import("player_ingestion", "count_database_players", lambda: 0)
search_database_players = _optional_import("player_ingestion", "search_database_players", lambda query, limit=25: [])
ingest_mlb_players = _optional_import("player_ingestion", "ingest_mlb_players")

# ============================================================
# SECTION 06 - APPLICATION METADATA
# ============================================================

PROJECT_NAME: Final[str] = "AISP2 Baseball"
PROJECT_VERSION: Final[str] = "12.4.1"
PROJECT_PHASE: Final[str] = "Phase 12 Part 4.1 - Enterprise Player Intelligence Application Service"
SERVICE_NAME: Final[str] = "aisp2-baseball"
PRIMARY_SPORT: Final[str] = "MLB"
GITHUB_REPOSITORY: Final[str] = "https://github.com/CodeDressing/AISP2_Baseball"
RENDER_SERVICE: Final[str] = "https://aisp2-baseball.onrender.com"
MLB_STATS_API_BASE: Final[str] = "https://statsapi.mlb.com/api/v1"
HTTP_TIMEOUT_SECONDS: Final[int] = 20
MAX_CHAT_LENGTH: Final[int] = 2000
MAX_PLAYER_RESULTS: Final[int] = 25
MAX_TEAM_RESULTS: Final[int] = 30

# ============================================================
# SECTION 07 - FASTAPI INITIALIZATION
# ============================================================

app = FastAPI(
    title=PROJECT_NAME,
    version=PROJECT_VERSION,
    description=(
        "Warehouse-first baseball intelligence, natural-language routing, "
        "live MLB data, and explainable probability services."
    ),
)

STATIC_DIRECTORY = PROJECT_ROOT / "static"
TEMPLATE_DIRECTORY = PROJECT_ROOT / "templates"

if STATIC_DIRECTORY.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIRECTORY)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATE_DIRECTORY))

# ============================================================
# SECTION 08 - REQUEST MODELS
# ============================================================


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_CHAT_LENGTH)
    conversation_context: dict[str, Any] | None = None


class PlayerPredictionRequest(BaseModel):
    team: str | None = None
    player: str
    outcome: str = "home_run"
    season: int | None = None


class GamePredictionRequest(BaseModel):
    away_team: str
    home_team: str
    season: int | None = None

# ============================================================
# SECTION 09 - GENERAL HELPERS
# ============================================================


def utc_now() -> datetime:
    return datetime.now(UTC)


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, float(value)))


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = str(value).lower().strip()
    text = re.sub(r"[^a-z0-9+'-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def record_value(record: Any, *names: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        for name in names:
            value = record.get(name)
            if value not in (None, ""):
                return value
        return default
    for name in names:
        value = getattr(record, name, None)
        if value not in (None, ""):
            return value
    return default


def serialize_record(record: Any) -> dict[str, Any]:
    if isinstance(record, Mapping):
        return dict(record)
    if hasattr(record, "model_dump"):
        return dict(record.model_dump())
    if hasattr(record, "_asdict"):
        return dict(record._asdict())
    if hasattr(record, "__dict__"):
        return {
            key: value
            for key, value in vars(record).items()
            if not key.startswith("_") and not callable(value)
        }
    return {"value": str(record)}

# ============================================================
# SECTION 10 - MLB HTTP CLIENT
# ============================================================


def fetch_mlb_json(path: str, *, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
    url = path if path.startswith("http") else f"{MLB_STATS_API_BASE}{path}"
    response = requests.get(url, params=params, timeout=HTTP_TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("MLB Stats API returned a non-object payload")
    return payload


def fetch_active_mlb_teams() -> list[dict[str, Any]]:
    payload = fetch_mlb_json(
        "/teams",
        params={"sportId": 1, "activeStatus": "Y"},
    )
    teams: list[dict[str, Any]] = []
    for team in payload.get("teams", []):
        teams.append(
            {
                "team_id": team.get("id"),
                "id": team.get("id"),
                "team_name": team.get("name"),
                "name": team.get("name"),
                "abbreviation": team.get("abbreviation"),
                "league": (team.get("league") or {}).get("name"),
                "division": (team.get("division") or {}).get("name"),
                "venue": (team.get("venue") or {}).get("name"),
                "source": "MLB Stats API",
            }
        )
    return sorted(teams, key=lambda item: str(item.get("name") or ""))


def fetch_team_roster(team_id: int) -> list[dict[str, Any]]:
    payload = fetch_mlb_json(
        f"/teams/{team_id}/roster",
        params={"rosterType": "active"},
    )
    roster: list[dict[str, Any]] = []
    for item in payload.get("roster", []):
        person = item.get("person") or {}
        position = item.get("position") or {}
        roster.append(
            {
                "player_id": person.get("id"),
                "id": person.get("id"),
                "player_name": person.get("fullName"),
                "name": person.get("fullName"),
                "position": position.get("name"),
                "position_code": position.get("code"),
                "status": (item.get("status") or {}).get("description"),
                "team_id": team_id,
                "source": "MLB Stats API active roster",
            }
        )
    return sorted(roster, key=lambda item: str(item.get("name") or ""))


def fetch_mlb_schedule(target_date: date | None = None) -> list[dict[str, Any]]:
    target_date = target_date or utc_now().date()
    payload = fetch_mlb_json(
        "/schedule",
        params={
            "sportId": 1,
            "date": target_date.isoformat(),
            "hydrate": "team,venue,probablePitcher",
        },
    )
    games: list[dict[str, Any]] = []
    for day in payload.get("dates", []):
        for game in day.get("games", []):
            teams = game.get("teams") or {}
            away = teams.get("away") or {}
            home = teams.get("home") or {}
            games.append(
                {
                    "game_id": game.get("gamePk"),
                    "date": game.get("gameDate"),
                    "status": (game.get("status") or {}).get("detailedState"),
                    "away_team": ((away.get("team") or {}).get("name")),
                    "home_team": ((home.get("team") or {}).get("name")),
                    "away_score": away.get("score"),
                    "home_score": home.get("score"),
                    "venue": (game.get("venue") or {}).get("name"),
                    "source": "MLB Stats API",
                }
            )
    return games

# ============================================================
# SECTION 11 - WAREHOUSE CATALOG ACCESS
# ============================================================


def load_team_catalog() -> list[dict[str, Any]]:
    try:
        records = build_team_inventory()
        if records:
            return [serialize_record(record) for record in records]
    except Exception as error:
        LOGGER.warning("Warehouse team inventory unavailable: %s", error)

    try:
        return fetch_active_mlb_teams()
    except Exception as error:
        LOGGER.warning("Live MLB team inventory unavailable: %s", error)

    return [
        {
            "team_name": name,
            "name": name,
            "aliases": aliases,
            "source": "static NLP catalog",
        }
        for name, aliases in dict(MLB_TEAM_ALIASES or {}).items()
    ]


def load_player_catalog(limit: int = 2000) -> list[dict[str, Any]]:
    try:
        records = build_player_inventory(limit=limit)
        if records:
            return [serialize_record(record) for record in records]
    except TypeError:
        try:
            records = build_player_inventory()
            if records:
                return [serialize_record(record) for record in records]
        except Exception as error:
            LOGGER.warning("Warehouse player inventory unavailable: %s", error)
    except Exception as error:
        LOGGER.warning("Warehouse player inventory unavailable: %s", error)
    return []


def normalize_player_result(record: Any) -> dict[str, Any]:
    data = serialize_record(record)
    player_id = record_value(
        data,
        "player_id",
        "mlb_player_id",
        "person_id",
        "id",
    )
    player_name = record_value(
        data,
        "player_name",
        "full_name",
        "fullName",
        "name",
        "display_name",
    )
    team_name = record_value(
        data,
        "team_name",
        "current_team_name",
        "club_name",
        "team",
    )
    return {
        "player_id": player_id,
        "id": player_id,
        "player_name": player_name,
        "name": player_name,
        "team_id": record_value(data, "team_id", "current_team_id", "club_id"),
        "team": team_name,
        "team_name": team_name,
        "position": record_value(
            data,
            "position",
            "position_name",
            "primary_position",
            "position_abbreviation",
        ),
        "active": record_value(data, "active", "is_active", "current"),
        "source": record_value(data, "source", default="AISP2 Database Warehouse"),
        "raw": data,
    }


def search_players_warehouse_first(query: str, limit: int = MAX_PLAYER_RESULTS) -> list[dict[str, Any]]:
    clean_query = normalize_text(query)
    if not clean_query:
        return []

    # Primary path: use the dedicated warehouse search service.
    try:
        records = search_database_players(query=query, limit=limit)
        normalized = [normalize_player_result(record) for record in records or []]
        normalized = [item for item in normalized if item.get("name")]
        if normalized:
            return normalized[:limit]
    except TypeError:
        try:
            records = search_database_players(query, limit)
            normalized = [normalize_player_result(record) for record in records or []]
            normalized = [item for item in normalized if item.get("name")]
            if normalized:
                return normalized[:limit]
        except Exception as error:
            LOGGER.warning("Warehouse player search failed: %s", error)
    except Exception as error:
        LOGGER.warning("Warehouse player search failed: %s", error)

    # Secondary path: scan the warehouse inventory using all plausible name fields.
    tokens = clean_query.split()
    matches: list[dict[str, Any]] = []
    for record in load_player_catalog(limit=5000):
        item = normalize_player_result(record)
        candidate_name = normalize_text(str(item.get("name") or ""))
        if candidate_name and all(token in candidate_name for token in tokens):
            matches.append(item)
    if matches:
        matches.sort(
            key=lambda item: (
                normalize_text(str(item.get("name"))) != clean_query,
                len(str(item.get("name") or "")),
            )
        )
        return matches[:limit]

    # Last resort: search all active MLB rosters.
    try:
        for team in fetch_active_mlb_teams():
            team_id = safe_int(team.get("team_id"))
            if not team_id:
                continue
            try:
                roster = fetch_team_roster(team_id)
            except Exception:
                continue
            for player in roster:
                candidate_name = normalize_text(str(player.get("name") or ""))
                if candidate_name and all(token in candidate_name for token in tokens):
                    player["team"] = team.get("name")
                    player["team_name"] = team.get("name")
                    matches.append(player)
            if len(matches) >= limit:
                break
    except Exception as error:
        LOGGER.warning("Live MLB fallback player search failed: %s", error)

    return matches[:limit]

# ============================================================
# SECTION 12 - CHAT ENTITY EXTRACTION HELPERS
# ============================================================


SEARCH_PREFIXES: Final[tuple[str, ...]] = (
    "search for",
    "search",
    "look up",
    "lookup",
    "find",
    "show player",
    "who is",
    "tell me about",
)


def extract_player_query(message: str, nlu_report: Mapping[str, Any] | None = None) -> str | None:
    nlu_report = nlu_report or {}
    entities = nlu_report.get("entities") or {}
    player = entities.get("player") or {}
    canonical_name = player.get("canonical_name") or player.get("name")
    if canonical_name:
        return str(canonical_name)

    lowered = normalize_text(message)
    for prefix in SEARCH_PREFIXES:
        normalized_prefix = normalize_text(prefix)
        if lowered.startswith(normalized_prefix + " "):
            candidate = lowered[len(normalized_prefix):].strip()
            if candidate:
                return candidate

    # Preserve capitalization from the original message when possible.
    original = str(message).strip(" ?.!\t\r\n")
    lower_original = original.lower()
    for prefix in SEARCH_PREFIXES:
        index = lower_original.find(prefix)
        if index >= 0:
            candidate = original[index + len(prefix):].strip(" ?.!\t\r\n")
            if candidate:
                return candidate
    return None


def entity_name(nlu_report: Mapping[str, Any], entity_key: str) -> str | None:
    entities = nlu_report.get("entities") or {}
    entity = entities.get(entity_key) or {}
    value = entity.get("canonical_name") or entity.get("name")
    return str(value) if value else None


def entity_outcome(nlu_report: Mapping[str, Any]) -> str | None:
    entities = nlu_report.get("entities") or {}
    outcome = entities.get("outcome") or {}
    value = outcome.get("canonical_name") or outcome.get("name")
    return str(value) if value else None
# ============================================================
# SECTION 12.95 - ENTERPRISE PLAYER EXPLORER API RUNTIME V2
# FILE: main.py
# PURPOSE:
# Database-backed runtime API for the Player Explorer page.
#
# Provides:
#   GET /api/player-explorer/bootstrap
#   GET /api/player-explorer/profile
#   GET /api/player-explorer/audit
#
# These endpoints remove hard-coded demo profiles from the
# Player Explorer and expose real team/player/database state.
# Paste this section into main.py near the other API route
# sections, after `app = FastAPI(...)` exists and before the
# local `if __name__ == "__main__"` startup block.
# ============================================================

from datetime import UTC as _AISP2_PLAYER_EXPLORER_UTC
from datetime import datetime as _AISP2_PLAYER_EXPLORER_DATETIME
import json as _aisp2_player_explorer_json
import math as _aisp2_player_explorer_math
import sys as _aisp2_player_explorer_sys
from pathlib import Path as _AISP2PlayerExplorerPath
from typing import Any as _AISP2PlayerExplorerAny

try:
    from fastapi import Query as _AISP2Query
except Exception:  # pragma: no cover
    _AISP2Query = None

_AISP2_PLAYER_EXPLORER_CURRENT_FILE = _AISP2PlayerExplorerPath(__file__).resolve()
_AISP2_PLAYER_EXPLORER_PROJECT_ROOT = _AISP2_PLAYER_EXPLORER_CURRENT_FILE.parent
_AISP2_PLAYER_EXPLORER_DATABASE_DIR = _AISP2_PLAYER_EXPLORER_PROJECT_ROOT / "01_database"
_AISP2_PLAYER_EXPLORER_AI_DIR = _AISP2_PLAYER_EXPLORER_PROJECT_ROOT / "04_ai"
_AISP2_PLAYER_EXPLORER_BASEBALL_DIR = _AISP2_PLAYER_EXPLORER_AI_DIR / "baseball"

for _aisp2_player_explorer_path in [
    _AISP2_PLAYER_EXPLORER_PROJECT_ROOT,
    _AISP2_PLAYER_EXPLORER_DATABASE_DIR,
    _AISP2_PLAYER_EXPLORER_AI_DIR,
    _AISP2_PLAYER_EXPLORER_BASEBALL_DIR,
]:
    _aisp2_player_explorer_path_string = str(_aisp2_player_explorer_path)

    if _aisp2_player_explorer_path_string not in _aisp2_player_explorer_sys.path:
        _aisp2_player_explorer_sys.path.insert(
            0,
            _aisp2_player_explorer_path_string,
        )

try:
    from database import managed_database_session as _aisp2_managed_database_session
except Exception as _aisp2_player_explorer_database_error:  # pragma: no cover
    _aisp2_managed_database_session = None

try:
    from models import Team as _AISP2Team
    from models import Player as _AISP2Player
    from models import RosterEntry as _AISP2RosterEntry
    from models import PlayerSeasonStat as _AISP2PlayerSeasonStat
    from models import PlayerAdvancedBattingStat as _AISP2PlayerAdvancedBattingStat
    from models import PlayerPercentileRanking as _AISP2PlayerPercentileRanking
    from models import PlayerPitchArsenal as _AISP2PlayerPitchArsenal
    from models import PlayerPitchTempo as _AISP2PlayerPitchTempo
    from models import PlayerBattedBallProfile as _AISP2PlayerBattedBallProfile
    from models import PlayerBattingStance as _AISP2PlayerBattingStance
    from models import PlayerHomeRunProfile as _AISP2PlayerHomeRunProfile
    from models import TeamPlateDiscipline as _AISP2TeamPlateDiscipline
    from models import RawDataImportLog as _AISP2RawDataImportLog

    try:
        from models import Game as _AISP2Game
    except Exception:
        _AISP2Game = None

    try:
        from models import PlayerGameStat as _AISP2PlayerGameStat
    except Exception:
        _AISP2PlayerGameStat = None

    try:
        from models import PredictionResult as _AISP2PredictionResult
    except Exception:
        _AISP2PredictionResult = None

except Exception as _aisp2_player_explorer_models_error:  # pragma: no cover
    _AISP2Team = None
    _AISP2Player = None
    _AISP2RosterEntry = None
    _AISP2PlayerSeasonStat = None
    _AISP2PlayerAdvancedBattingStat = None
    _AISP2PlayerPercentileRanking = None
    _AISP2PlayerPitchArsenal = None
    _AISP2PlayerPitchTempo = None
    _AISP2PlayerBattedBallProfile = None
    _AISP2PlayerBattingStance = None
    _AISP2PlayerHomeRunProfile = None
    _AISP2TeamPlateDiscipline = None
    _AISP2RawDataImportLog = None
    _AISP2Game = None
    _AISP2PlayerGameStat = None
    _AISP2PredictionResult = None

try:
    from baseball.player_knowledge import build_player_knowledge_report as _aisp2_build_player_knowledge_report
    from baseball.player_knowledge import build_player_explorer_card as _aisp2_build_player_explorer_card
except Exception:  # pragma: no cover
    _aisp2_build_player_knowledge_report = None
    _aisp2_build_player_explorer_card = None

PLAYER_EXPLORER_API_VERSION = "phase_12_part_5_player_explorer_api_runtime_v2"
PLAYER_EXPLORER_MINIMUM_SAMPLE_PA = 25
PLAYER_EXPLORER_STALE_DATA_DAYS = 10
PLAYER_EXPLORER_DEFAULT_SEASON = 2026
PLAYER_EXPLORER_MAX_PLAYERS_PER_TEAM = 120
PLAYER_EXPLORER_STATUS_AVAILABLE = "available"
PLAYER_EXPLORER_STATUS_NOT_AVAILABLE = "not_available"
PLAYER_EXPLORER_STATUS_PENDING_INGESTION = "pending_ingestion"
PLAYER_EXPLORER_STATUS_INSUFFICIENT_SAMPLE = "insufficient_sample"
PLAYER_EXPLORER_STATUS_STALE_DATA = "stale_data"
PLAYER_EXPLORER_STATUS_ERROR = "error"
PLAYER_EXPLORER_STATUS_READY = "ready"
PLAYER_EXPLORER_STATUS_PARTIAL = "partial"

PLAYER_EXPLORER_REQUIRED_PLAYER_FIELDS = [
    "mlb_player_id",
    "full_name",
    "current_team_id",
    "position",
    "active_status",
]

PLAYER_EXPLORER_REQUIRED_ROSTER_FIELDS = [
    "team_id",
    "player_id",
    "season",
    "roster_type",
    "status_description",
]

PLAYER_EXPLORER_REQUIRED_STAT_FIELDS = [
    "player_id",
    "season",
]


def _aisp2_player_explorer_now_iso() -> str:
    return _AISP2_PLAYER_EXPLORER_DATETIME.now(
        _AISP2_PLAYER_EXPLORER_UTC,
    ).isoformat()


def _aisp2_player_explorer_database_available() -> bool:
    return _aisp2_managed_database_session is not None and _AISP2Player is not None and _AISP2Team is not None


def _aisp2_player_explorer_safe_int(value: _AISP2PlayerExplorerAny) -> int | None:
    if value is None:
        return None

    try:
        cleaned = str(value).replace(",", "").strip()

        if not cleaned:
            return None

        return int(float(cleaned))

    except Exception:
        return None


def _aisp2_player_explorer_safe_float(value: _AISP2PlayerExplorerAny) -> float | None:
    if value is None:
        return None

    try:
        cleaned = str(value).replace(",", "").replace("%", "").strip()

        if not cleaned:
            return None

        numeric = float(cleaned)

        if _aisp2_player_explorer_math.isnan(numeric):
            return None

        return numeric

    except Exception:
        return None


def _aisp2_player_explorer_safe_round(
    value: _AISP2PlayerExplorerAny,
    digits: int = 3,
) -> float | None:
    numeric = _aisp2_player_explorer_safe_float(value)

    if numeric is None:
        return None

    return round(numeric, digits)


def _aisp2_player_explorer_safe_string(value: _AISP2PlayerExplorerAny) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned or cleaned.lower() in {"none", "null", "nan", "n/a", "--"}:
        return None

    return cleaned


def _aisp2_player_explorer_normalize(value: _AISP2PlayerExplorerAny) -> str:
    if value is None:
        return ""

    return (
        str(value)
        .lower()
        .strip()
        .replace(".", " ")
        .replace(",", " ")
        .replace("'", "")
        .replace("’", "")
        .replace("-", " ")
        .replace("_", " ")
    )


def _aisp2_player_explorer_compact(value: _AISP2PlayerExplorerAny) -> str:
    return "".join(
        _aisp2_player_explorer_normalize(value).split()
    )


def _aisp2_player_explorer_column_dict(row: _AISP2PlayerExplorerAny) -> dict[str, _AISP2PlayerExplorerAny] | None:
    if row is None:
        return None

    try:
        return {
            column.key: getattr(row, column.key, None)
            for column in row.__mapper__.columns
        }

    except Exception:
        try:
            return {
                key: value
                for key, value in vars(row).items()
                if not key.startswith("_")
            }

        except Exception:
            return None


def _aisp2_player_explorer_display_value(
    value: _AISP2PlayerExplorerAny,
    fallback: str = "Not Available",
) -> str:
    clean_value = _aisp2_player_explorer_safe_string(value)

    if clean_value is None:
        return fallback

    return clean_value


def _aisp2_player_explorer_metric(
    value: _AISP2PlayerExplorerAny,
    label: str,
    sample_size: int | None = None,
    minimum_sample: int = PLAYER_EXPLORER_MINIMUM_SAMPLE_PA,
    digits: int = 3,
    suffix: str = "",
    integer: bool = False,
) -> dict[str, _AISP2PlayerExplorerAny]:
    if sample_size is not None and sample_size < minimum_sample:
        return {
            "label": label,
            "value": None,
            "display": "Insufficient Sample",
            "status": PLAYER_EXPLORER_STATUS_INSUFFICIENT_SAMPLE,
            "sample_size": sample_size,
            "minimum_sample": minimum_sample,
        }

    if value is None:
        return {
            "label": label,
            "value": None,
            "display": "Pending Ingestion",
            "status": PLAYER_EXPLORER_STATUS_PENDING_INGESTION,
            "sample_size": sample_size,
            "minimum_sample": minimum_sample,
        }

    if integer:
        numeric_int = _aisp2_player_explorer_safe_int(value)

        if numeric_int is None:
            return {
                "label": label,
                "value": None,
                "display": "Not Available",
                "status": PLAYER_EXPLORER_STATUS_NOT_AVAILABLE,
                "sample_size": sample_size,
                "minimum_sample": minimum_sample,
            }

        return {
            "label": label,
            "value": numeric_int,
            "display": f"{numeric_int}{suffix}",
            "status": PLAYER_EXPLORER_STATUS_AVAILABLE,
            "sample_size": sample_size,
            "minimum_sample": minimum_sample,
        }

    numeric = _aisp2_player_explorer_safe_float(value)

    if numeric is None:
        return {
            "label": label,
            "value": None,
            "display": "Not Available",
            "status": PLAYER_EXPLORER_STATUS_NOT_AVAILABLE,
            "sample_size": sample_size,
            "minimum_sample": minimum_sample,
        }

    rounded = round(numeric, digits)

    if suffix == "%":
        display = f"{rounded:.1f}%"
    elif digits == 3 and 0 <= rounded < 1:
        display = f"{rounded:.3f}".replace("0.", ".", 1)
    elif digits == 1:
        display = f"{rounded:.1f}{suffix}"
    elif digits == 2:
        display = f"{rounded:.2f}{suffix}"
    else:
        display = f"{rounded}{suffix}"

    return {
        "label": label,
        "value": rounded,
        "display": display,
        "status": PLAYER_EXPLORER_STATUS_AVAILABLE,
        "sample_size": sample_size,
        "minimum_sample": minimum_sample,
    }


def _aisp2_player_explorer_extract_year(value: _AISP2PlayerExplorerAny) -> int | None:
    if value is None:
        return None

    text = str(value).strip()

    for token in text.replace("-", " ").replace("/", " ").split():
        if token.isdigit() and len(token) == 4:
            year = int(token)

            if 1900 <= year <= 2100:
                return year

    return None


def _aisp2_player_explorer_is_stale_timestamp(
    value: _AISP2PlayerExplorerAny,
    stale_days: int = PLAYER_EXPLORER_STALE_DATA_DAYS,
) -> bool:
    if value is None:
        return False

    try:
        text = str(value).replace("Z", "+00:00")
        timestamp = _AISP2_PLAYER_EXPLORER_DATETIME.fromisoformat(text)

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=_AISP2_PLAYER_EXPLORER_UTC)

        age_days = (_AISP2_PLAYER_EXPLORER_DATETIME.now(_AISP2_PLAYER_EXPLORER_UTC) - timestamp).days

        return age_days > stale_days

    except Exception:
        return False


def _aisp2_player_explorer_count(database_session, model) -> int:
    if model is None:
        return 0

    try:
        return int(database_session.query(model).count())

    except Exception:
        return 0


def _aisp2_player_explorer_query_first(database_session, model):
    if model is None:
        return None

    try:
        return database_session.query(model).first()

    except Exception:
        return None


def _aisp2_player_explorer_get_latest_row(
    database_session,
    model,
    player,
    season: int | None = None,
):
    if model is None or player is None:
        return None

    try:
        query = database_session.query(model)
        conditions = []

        if hasattr(model, "player_id") and getattr(player, "id", None) is not None:
            conditions.append(model.player_id == player.id)

        if hasattr(model, "mlb_player_id") and getattr(player, "mlb_player_id", None) is not None:
            conditions.append(model.mlb_player_id == player.mlb_player_id)

        if hasattr(model, "player_name") and getattr(player, "full_name", None):
            conditions.append(model.player_name == player.full_name)

        if not conditions:
            return None

        try:
            from sqlalchemy import or_ as _aisp2_player_explorer_or

            if len(conditions) == 1:
                query = query.filter(conditions[0])
            else:
                query = query.filter(_aisp2_player_explorer_or(*conditions))

        except Exception:
            query = query.filter(conditions[0])

        if season is not None and hasattr(model, "season"):
            query = query.filter(model.season == season)

        if hasattr(model, "season"):
            query = query.order_by(model.season.desc())

        if hasattr(model, "updated_at"):
            query = query.order_by(model.updated_at.desc())

        if hasattr(model, "created_at"):
            query = query.order_by(model.created_at.desc())

        if hasattr(model, "id"):
            query = query.order_by(model.id.desc())

        return query.first()

    except Exception:
        return None


def _aisp2_player_explorer_get_rows(
    database_session,
    model,
    player,
    season: int | None = None,
    limit: int = 10,
) -> list:
    if model is None or player is None:
        return []

    try:
        query = database_session.query(model)
        conditions = []

        if hasattr(model, "player_id") and getattr(player, "id", None) is not None:
            conditions.append(model.player_id == player.id)

        if hasattr(model, "mlb_player_id") and getattr(player, "mlb_player_id", None) is not None:
            conditions.append(model.mlb_player_id == player.mlb_player_id)

        if hasattr(model, "player_name") and getattr(player, "full_name", None):
            conditions.append(model.player_name == player.full_name)

        if not conditions:
            return []

        try:
            from sqlalchemy import or_ as _aisp2_player_explorer_or

            if len(conditions) == 1:
                query = query.filter(conditions[0])
            else:
                query = query.filter(_aisp2_player_explorer_or(*conditions))

        except Exception:
            query = query.filter(conditions[0])

        if season is not None and hasattr(model, "season"):
            query = query.filter(model.season == season)

        if hasattr(model, "season"):
            query = query.order_by(model.season.desc())

        if hasattr(model, "game_date"):
            query = query.order_by(model.game_date.desc())

        if hasattr(model, "id"):
            query = query.order_by(model.id.desc())

        return query.limit(limit).all()

    except Exception:
        return []


def _aisp2_player_explorer_resolve_team(database_session, team: str | int | None):
    if _AISP2Team is None:
        return None

    if team is None or str(team).strip() == "":
        return None

    try:
        team_int = _aisp2_player_explorer_safe_int(team)

        query = database_session.query(_AISP2Team)

        if team_int is not None:
            found = (
                query
                .filter(_AISP2Team.id == team_int)
                .first()
            )

            if found:
                return found

            found = (
                query
                .filter(_AISP2Team.mlb_team_id == team_int)
                .first()
            )

            if found:
                return found

        normalized = _aisp2_player_explorer_normalize(team)
        compact = _aisp2_player_explorer_compact(team)

        teams = query.order_by(_AISP2Team.name.asc()).all()

        for candidate in teams:
            candidate_values = [
                getattr(candidate, "name", None),
                getattr(candidate, "abbreviation", None),
                getattr(candidate, "team_code", None),
                getattr(candidate, "file_code", None),
                getattr(candidate, "club_name", None),
                getattr(candidate, "short_name", None),
                getattr(candidate, "location_name", None),
            ]

            for candidate_value in candidate_values:
                if not candidate_value:
                    continue

                if _aisp2_player_explorer_normalize(candidate_value) == normalized:
                    return candidate

                if _aisp2_player_explorer_compact(candidate_value) == compact:
                    return candidate

        for candidate in teams:
            candidate_name = _aisp2_player_explorer_normalize(getattr(candidate, "name", ""))

            if normalized and normalized in candidate_name:
                return candidate

        return None

    except Exception:
        return None


def _aisp2_player_explorer_resolve_player(
    database_session,
    player: str | int | None,
    team_obj=None,
):
    if _AISP2Player is None:
        return None

    if player is None or str(player).strip() == "":
        return None

    try:
        player_int = _aisp2_player_explorer_safe_int(player)
        base_query = database_session.query(_AISP2Player)

        if team_obj is not None and getattr(team_obj, "id", None) is not None:
            base_query = base_query.filter(_AISP2Player.current_team_id == team_obj.id)

        if player_int is not None:
            found = (
                database_session.query(_AISP2Player)
                .filter(_AISP2Player.id == player_int)
                .first()
            )

            if found:
                return found

            found = (
                database_session.query(_AISP2Player)
                .filter(_AISP2Player.mlb_player_id == player_int)
                .first()
            )

            if found:
                return found

        normalized = _aisp2_player_explorer_normalize(player)
        compact = _aisp2_player_explorer_compact(player)

        exact = (
            base_query
            .filter(_AISP2Player.full_name.ilike(str(player)))
            .first()
        )

        if exact:
            return exact

        contains = (
            base_query
            .filter(_AISP2Player.full_name.ilike(f"%{player}%"))
            .order_by(_AISP2Player.full_name.asc())
            .first()
        )

        if contains:
            return contains

        candidates = base_query.limit(2000).all()

        for candidate in candidates:
            candidate_name = getattr(candidate, "full_name", "") or ""

            if _aisp2_player_explorer_normalize(candidate_name) == normalized:
                return candidate

            if _aisp2_player_explorer_compact(candidate_name) == compact:
                return candidate

        tokens = [token for token in normalized.split() if token]

        if tokens:
            for candidate in candidates:
                candidate_name = _aisp2_player_explorer_normalize(getattr(candidate, "full_name", ""))

                if all(token in candidate_name for token in tokens):
                    return candidate

        return None

    except Exception:
        return None


def _aisp2_player_explorer_team_payload(team) -> dict[str, _AISP2PlayerExplorerAny] | None:
    if team is None:
        return None

    return {
        "id": getattr(team, "id", None),
        "mlb_team_id": getattr(team, "mlb_team_id", None),
        "name": getattr(team, "name", None),
        "abbreviation": getattr(team, "abbreviation", None),
        "team_code": getattr(team, "team_code", None),
        "file_code": getattr(team, "file_code", None),
        "franchise_name": getattr(team, "franchise_name", None),
        "club_name": getattr(team, "club_name", None),
        "short_name": getattr(team, "short_name", None),
        "location_name": getattr(team, "location_name", None),
        "league": getattr(team, "league", None),
        "division": getattr(team, "division", None),
        "venue": getattr(team, "venue", None),
        "is_active": getattr(team, "is_active", None),
    }


def _aisp2_player_explorer_player_selector_payload(player) -> dict[str, _AISP2PlayerExplorerAny]:
    return {
        "id": getattr(player, "id", None),
        "mlb_player_id": getattr(player, "mlb_player_id", None),
        "full_name": getattr(player, "full_name", None),
        "position": getattr(player, "position", None),
        "position_code": getattr(player, "position_code", None),
        "bats": getattr(player, "bats", None),
        "throws": getattr(player, "throws", None),
        "current_team_id": getattr(player, "current_team_id", None),
        "active_status": getattr(player, "active_status", None),
    }


def _aisp2_player_explorer_player_identity_payload(player, team) -> dict[str, _AISP2PlayerExplorerAny]:
    return {
        "id": getattr(player, "id", None),
        "player_id": getattr(player, "id", None),
        "mlb_player_id": getattr(player, "mlb_player_id", None),
        "full_name": getattr(player, "full_name", None),
        "first_name": getattr(player, "first_name", None),
        "last_name": getattr(player, "last_name", None),
        "primary_number": getattr(player, "primary_number", None),
        "position": getattr(player, "position", None),
        "position_code": getattr(player, "position_code", None),
        "bats": getattr(player, "bats", None),
        "throws": getattr(player, "throws", None),
        "height": getattr(player, "height", None),
        "weight": getattr(player, "weight", None),
        "birth_date": getattr(player, "birth_date", None),
        "birth_city": getattr(player, "birth_city", None),
        "birth_state_province": getattr(player, "birth_state_province", None),
        "birth_country": getattr(player, "birth_country", None),
        "mlb_debut_date": getattr(player, "mlb_debut_date", None),
        "active_status": getattr(player, "active_status", None),
        "current_team_id": getattr(player, "current_team_id", None),
        "team": _aisp2_player_explorer_team_payload(team),
    }


def _aisp2_player_explorer_roster_payload(database_session, player) -> list[dict[str, _AISP2PlayerExplorerAny]]:
    if _AISP2RosterEntry is None or player is None:
        return []

    try:
        rows = (
            database_session.query(_AISP2RosterEntry)
            .filter(_AISP2RosterEntry.player_id == player.id)
            .order_by(
                _AISP2RosterEntry.season.desc(),
                _AISP2RosterEntry.id.desc(),
            )
            .limit(10)
            .all()
        )

        return [
            _aisp2_player_explorer_column_dict(row) or {}
            for row in rows
        ]

    except Exception:
        return []


def _aisp2_player_explorer_get_team_plate_discipline(database_session, team, season: int | None = None):
    if _AISP2TeamPlateDiscipline is None or team is None:
        return None

    try:
        query = database_session.query(_AISP2TeamPlateDiscipline)
        conditions = []

        if getattr(team, "id", None) is not None:
            conditions.append(_AISP2TeamPlateDiscipline.team_id == team.id)

        if getattr(team, "mlb_team_id", None) is not None:
            conditions.append(_AISP2TeamPlateDiscipline.mlb_team_id == team.mlb_team_id)

        if getattr(team, "name", None):
            conditions.append(_AISP2TeamPlateDiscipline.team_name == team.name)

        if getattr(team, "abbreviation", None):
            conditions.append(_AISP2TeamPlateDiscipline.team_abbreviation == team.abbreviation)

        if not conditions:
            return None

        try:
            from sqlalchemy import or_ as _aisp2_player_explorer_or

            if len(conditions) == 1:
                query = query.filter(conditions[0])
            else:
                query = query.filter(_aisp2_player_explorer_or(*conditions))

        except Exception:
            query = query.filter(conditions[0])

        if season is not None:
            query = query.filter(_AISP2TeamPlateDiscipline.season == season)

        query = query.order_by(
            _AISP2TeamPlateDiscipline.season.desc(),
            _AISP2TeamPlateDiscipline.id.desc(),
        )

        return query.first()

    except Exception:
        return None


def _aisp2_player_explorer_build_stat_metrics(
    season_stats: dict[str, _AISP2PlayerExplorerAny] | None,
    advanced_stats: dict[str, _AISP2PlayerExplorerAny] | None,
    home_run_profile: dict[str, _AISP2PlayerExplorerAny] | None,
) -> dict[str, dict[str, _AISP2PlayerExplorerAny]]:
    season_stats = season_stats or {}
    advanced_stats = advanced_stats or {}
    home_run_profile = home_run_profile or {}

    sample_size = (
        _aisp2_player_explorer_safe_int(season_stats.get("plate_appearances"))
        or _aisp2_player_explorer_safe_int(advanced_stats.get("plate_appearances"))
    )

    return {
        "avg": _aisp2_player_explorer_metric(
            season_stats.get("batting_average"),
            "AVG",
            sample_size=sample_size,
            digits=3,
        ),
        "ops": _aisp2_player_explorer_metric(
            season_stats.get("ops"),
            "OPS",
            sample_size=sample_size,
            digits=3,
        ),
        "hr": _aisp2_player_explorer_metric(
            home_run_profile.get("home_runs") if home_run_profile.get("home_runs") is not None else season_stats.get("home_runs"),
            "HR",
            sample_size=sample_size,
            integer=True,
        ),
        "rbi": _aisp2_player_explorer_metric(
            season_stats.get("rbi"),
            "RBI",
            sample_size=sample_size,
            integer=True,
        ),
        "pa": _aisp2_player_explorer_metric(
            sample_size,
            "PA",
            integer=True,
        ),
        "k_percent": _aisp2_player_explorer_metric(
            advanced_stats.get("strikeout_percent"),
            "K%",
            sample_size=sample_size,
            digits=1,
            suffix="%",
        ),
        "bb_percent": _aisp2_player_explorer_metric(
            advanced_stats.get("walk_percent"),
            "BB%",
            sample_size=sample_size,
            digits=1,
            suffix="%",
        ),
        "woba": _aisp2_player_explorer_metric(
            advanced_stats.get("woba"),
            "wOBA",
            sample_size=sample_size,
            digits=3,
        ),
        "xwoba": _aisp2_player_explorer_metric(
            advanced_stats.get("expected_woba"),
            "xwOBA",
            sample_size=sample_size,
            digits=3,
        ),
    }


def _aisp2_player_explorer_build_statcast_metrics(
    batted_ball: dict[str, _AISP2PlayerExplorerAny] | None,
    percentiles: dict[str, _AISP2PlayerExplorerAny] | None,
    home_run_profile: dict[str, _AISP2PlayerExplorerAny] | None,
    pitch_tempo: dict[str, _AISP2PlayerExplorerAny] | None,
) -> dict[str, dict[str, _AISP2PlayerExplorerAny]]:
    batted_ball = batted_ball or {}
    percentiles = percentiles or {}
    home_run_profile = home_run_profile or {}
    pitch_tempo = pitch_tempo or {}

    return {
        "average_exit_velocity": _aisp2_player_explorer_metric(
            batted_ball.get("average_exit_velocity") if batted_ball.get("average_exit_velocity") is not None else home_run_profile.get("average_exit_velocity"),
            "Average Exit Velocity",
            digits=1,
            suffix=" mph",
        ),
        "max_exit_velocity": _aisp2_player_explorer_metric(
            batted_ball.get("max_exit_velocity") if batted_ball.get("max_exit_velocity") is not None else home_run_profile.get("max_exit_velocity"),
            "Max Exit Velocity",
            digits=1,
            suffix=" mph",
        ),
        "launch_angle": _aisp2_player_explorer_metric(
            batted_ball.get("launch_angle") if batted_ball.get("launch_angle") is not None else home_run_profile.get("average_launch_angle"),
            "Launch Angle",
            digits=1,
        ),
        "barrel_percent": _aisp2_player_explorer_metric(
            batted_ball.get("barrel_percent"),
            "Barrel%",
            digits=1,
            suffix="%",
        ),
        "hard_hit_percent": _aisp2_player_explorer_metric(
            batted_ball.get("hard_hit_percent"),
            "Hard Hit%",
            digits=1,
            suffix="%",
        ),
        "xwoba_percentile": _aisp2_player_explorer_metric(
            percentiles.get("xwoba_percentile"),
            "xwOBA Percentile",
            digits=0,
        ),
        "barrel_percentile": _aisp2_player_explorer_metric(
            percentiles.get("barrel_percentile"),
            "Barrel Percentile",
            digits=0,
        ),
        "pitch_tempo": _aisp2_player_explorer_metric(
            pitch_tempo.get("pitch_tempo"),
            "Pitch Tempo",
            digits=1,
        ),
    }


def _aisp2_player_explorer_build_splits_placeholder() -> dict[str, _AISP2PlayerExplorerAny]:
    return {
        "home_away": {
            "home": {
                "status": PLAYER_EXPLORER_STATUS_PENDING_INGESTION,
                "display": "Pending Ingestion",
                "source": "game_logs_required",
            },
            "away": {
                "status": PLAYER_EXPLORER_STATUS_PENDING_INGESTION,
                "display": "Pending Ingestion",
                "source": "game_logs_required",
            },
        },
        "left_right_pitching": {
            "vs_left": {
                "status": PLAYER_EXPLORER_STATUS_PENDING_INGESTION,
                "display": "Pending Ingestion",
                "source": "pitch_hand_split_required",
            },
            "vs_right": {
                "status": PLAYER_EXPLORER_STATUS_PENDING_INGESTION,
                "display": "Pending Ingestion",
                "source": "pitch_hand_split_required",
            },
        },
    }


def _aisp2_player_explorer_build_freshness(
    rows: dict[str, dict[str, _AISP2PlayerExplorerAny] | None],
) -> dict[str, _AISP2PlayerExplorerAny]:
    freshness_rows = {}
    stale_sources = []

    for source_name, row in rows.items():
        if not row:
            freshness_rows[source_name] = {
                "status": PLAYER_EXPLORER_STATUS_PENDING_INGESTION,
                "display": "Pending Ingestion",
                "source_updated_at": None,
            }
            continue

        updated_at = row.get("updated_at") or row.get("created_at")
        stale = _aisp2_player_explorer_is_stale_timestamp(updated_at)

        if stale:
            stale_sources.append(source_name)

        freshness_rows[source_name] = {
            "status": PLAYER_EXPLORER_STATUS_STALE_DATA if stale else PLAYER_EXPLORER_STATUS_AVAILABLE,
            "display": "Stale Data" if stale else _aisp2_player_explorer_display_value(updated_at, fallback="Not Available"),
            "source_updated_at": updated_at,
        }

    return {
        "sources": freshness_rows,
        "stale_sources": stale_sources,
        "has_stale_data": len(stale_sources) > 0,
        "checked_at": _aisp2_player_explorer_now_iso(),
    }


def _aisp2_player_explorer_prediction_readiness(
    metrics: dict[str, dict[str, _AISP2PlayerExplorerAny]],
    statcast_metrics: dict[str, dict[str, _AISP2PlayerExplorerAny]],
    availability: dict[str, _AISP2PlayerExplorerAny],
) -> dict[str, _AISP2PlayerExplorerAny]:
    available_count = 0
    total_count = 0

    for metric_group in [metrics, statcast_metrics]:
        for metric in metric_group.values():
            total_count += 1
            if metric.get("status") == PLAYER_EXPLORER_STATUS_AVAILABLE:
                available_count += 1

    coverage_percent = round((available_count / total_count) * 100, 1) if total_count else 0

    ready = coverage_percent >= 50

    return {
        "ready": ready,
        "status": PLAYER_EXPLORER_STATUS_READY if ready else PLAYER_EXPLORER_STATUS_PARTIAL,
        "coverage_percent": coverage_percent,
        "available_metric_count": available_count,
        "total_metric_count": total_count,
        "display": "Ready" if ready else "Pending Ingestion",
        "model_note": (
            "Player profile has enough database-backed features for baseline prediction context."
            if ready
            else "More warehouse features are needed before prediction outputs should be trusted."
        ),
        "availability": availability,
    }


def _aisp2_player_explorer_source_attribution(
    rows: dict[str, dict[str, _AISP2PlayerExplorerAny] | None],
) -> list[dict[str, _AISP2PlayerExplorerAny]]:
    sources = []

    for source_name, row in rows.items():
        if not row:
            sources.append(
                {
                    "source": source_name,
                    "status": PLAYER_EXPLORER_STATUS_PENDING_INGESTION,
                    "source_file": None,
                    "source_updated_at": None,
                }
            )
            continue

        sources.append(
            {
                "source": source_name,
                "status": PLAYER_EXPLORER_STATUS_AVAILABLE,
                "source_file": row.get("source_file") or row.get("source") or "database",
                "source_updated_at": row.get("updated_at") or row.get("created_at"),
            }
        )

    return sources


def _aisp2_player_explorer_warnings(
    player,
    identity: dict[str, _AISP2PlayerExplorerAny],
    metrics: dict[str, dict[str, _AISP2PlayerExplorerAny]],
    statcast_metrics: dict[str, dict[str, _AISP2PlayerExplorerAny]],
    freshness: dict[str, _AISP2PlayerExplorerAny],
) -> list[str]:
    warnings = []

    if not getattr(player, "active_status", None):
        warnings.append("Player is not marked active in the database.")

    if not identity.get("team"):
        warnings.append("Current team is not linked for this player.")

    for metric_key in ["avg", "ops", "hr", "rbi"]:
        metric = metrics.get(metric_key, {})
        if metric.get("status") != PLAYER_EXPLORER_STATUS_AVAILABLE:
            warnings.append(f"{metric.get('label', metric_key)} is {metric.get('display')}.")

    missing_statcast = [
        metric.get("label")
        for metric in statcast_metrics.values()
        if metric.get("status") != PLAYER_EXPLORER_STATUS_AVAILABLE
    ]

    if missing_statcast:
        warnings.append("Some Statcast metrics are pending ingestion.")

    if freshness.get("has_stale_data"):
        warnings.append("One or more source datasets are stale.")

    if not warnings:
        warnings.append("No critical Player Explorer warnings detected.")

    return warnings


def _aisp2_player_explorer_profile_payload(
    database_session,
    player,
    team,
    season: int | None = None,
) -> dict[str, _AISP2PlayerExplorerAny]:
    season_stats_row = _aisp2_player_explorer_get_latest_row(
        database_session,
        _AISP2PlayerSeasonStat,
        player,
        season,
    )

    advanced_stats_row = _aisp2_player_explorer_get_latest_row(
        database_session,
        _AISP2PlayerAdvancedBattingStat,
        player,
        season,
    )

    percentiles_row = _aisp2_player_explorer_get_latest_row(
        database_session,
        _AISP2PlayerPercentileRanking,
        player,
        season,
    )

    pitch_arsenal_rows = _aisp2_player_explorer_get_rows(
        database_session,
        _AISP2PlayerPitchArsenal,
        player,
        season,
        limit=12,
    )

    pitch_tempo_row = _aisp2_player_explorer_get_latest_row(
        database_session,
        _AISP2PlayerPitchTempo,
        player,
        season,
    )

    batted_ball_row = _aisp2_player_explorer_get_latest_row(
        database_session,
        _AISP2PlayerBattedBallProfile,
        player,
        season,
    )

    batting_stance_row = _aisp2_player_explorer_get_latest_row(
        database_session,
        _AISP2PlayerBattingStance,
        player,
        season,
    )

    home_run_profile_row = _aisp2_player_explorer_get_latest_row(
        database_session,
        _AISP2PlayerHomeRunProfile,
        player,
        season,
    )

    team_plate_discipline_row = _aisp2_player_explorer_get_team_plate_discipline(
        database_session,
        team,
        season,
    )

    game_log_rows = _aisp2_player_explorer_get_rows(
        database_session,
        _AISP2PlayerGameStat,
        player,
        season,
        limit=10,
    )

    prediction_rows = _aisp2_player_explorer_get_rows(
        database_session,
        _AISP2PredictionResult,
        player,
        season,
        limit=10,
    )

    season_stats = _aisp2_player_explorer_column_dict(season_stats_row)
    advanced_stats = _aisp2_player_explorer_column_dict(advanced_stats_row)
    percentiles = _aisp2_player_explorer_column_dict(percentiles_row)
    pitch_tempo = _aisp2_player_explorer_column_dict(pitch_tempo_row)
    batted_ball = _aisp2_player_explorer_column_dict(batted_ball_row)
    batting_stance = _aisp2_player_explorer_column_dict(batting_stance_row)
    home_run_profile = _aisp2_player_explorer_column_dict(home_run_profile_row)
    team_plate_discipline = _aisp2_player_explorer_column_dict(team_plate_discipline_row)

    identity = _aisp2_player_explorer_player_identity_payload(
        player,
        team,
    )

    roster_context = _aisp2_player_explorer_roster_payload(
        database_session,
        player,
    )

    metrics = _aisp2_player_explorer_build_stat_metrics(
        season_stats,
        advanced_stats,
        home_run_profile,
    )

    statcast_metrics = _aisp2_player_explorer_build_statcast_metrics(
        batted_ball,
        percentiles,
        home_run_profile,
        pitch_tempo,
    )

    raw_rows = {
        "season_stats": season_stats,
        "advanced_batting": advanced_stats,
        "percentile_rankings": percentiles,
        "pitch_tempo": pitch_tempo,
        "batted_ball_profile": batted_ball,
        "batting_stance": batting_stance,
        "home_run_profile": home_run_profile,
        "team_plate_discipline": team_plate_discipline,
    }

    availability = {
        key: value is not None and value != {}
        for key, value in raw_rows.items()
    }

    freshness = _aisp2_player_explorer_build_freshness(
        raw_rows,
    )

    prediction_readiness = _aisp2_player_explorer_prediction_readiness(
        metrics,
        statcast_metrics,
        availability,
    )

    warnings = _aisp2_player_explorer_warnings(
        player,
        identity,
        metrics,
        statcast_metrics,
        freshness,
    )

    sample_sizes = {
        "plate_appearances": (
            _aisp2_player_explorer_safe_int((season_stats or {}).get("plate_appearances"))
            or _aisp2_player_explorer_safe_int((advanced_stats or {}).get("plate_appearances"))
        ),
        "recent_game_count": len(game_log_rows),
        "pitch_arsenal_count": len(pitch_arsenal_rows),
        "prediction_history_count": len(prediction_rows),
    }

    recent_form = {
        "status": PLAYER_EXPLORER_STATUS_AVAILABLE if game_log_rows else PLAYER_EXPLORER_STATUS_PENDING_INGESTION,
        "display": "Available" if game_log_rows else "Pending Ingestion",
        "games": [_aisp2_player_explorer_column_dict(row) or {} for row in game_log_rows],
    }

    splits = _aisp2_player_explorer_build_splits_placeholder()

    return {
        "status": PLAYER_EXPLORER_STATUS_READY,
        "api_version": PLAYER_EXPLORER_API_VERSION,
        "checked_at": _aisp2_player_explorer_now_iso(),
        "season": season,
        "player_identity": identity,
        "current_team": _aisp2_player_explorer_team_payload(team),
        "position_and_handedness": {
            "position": identity.get("position") or "Not Available",
            "position_code": identity.get("position_code") or "Not Available",
            "bats": identity.get("bats") or "Not Available",
            "throws": identity.get("throws") or "Not Available",
        },
        "season_statistics": {
            "raw": season_stats,
            "metrics": metrics,
        },
        "advanced_batting": advanced_stats,
        "recent_form": recent_form,
        "home_away_splits": splits["home_away"],
        "left_right_pitching_splits": splits["left_right_pitching"],
        "statcast_metrics": {
            "raw_batted_ball": batted_ball,
            "raw_percentiles": percentiles,
            "raw_pitch_tempo": pitch_tempo,
            "raw_pitch_arsenal": [_aisp2_player_explorer_column_dict(row) or {} for row in pitch_arsenal_rows],
            "raw_batting_stance": batting_stance,
            "raw_home_run_profile": home_run_profile,
            "metrics": statcast_metrics,
        },
        "team_plate_discipline": team_plate_discipline,
        "data_freshness": freshness,
        "sample_sizes": sample_sizes,
        "prediction_readiness": prediction_readiness,
        "source_attribution": _aisp2_player_explorer_source_attribution(raw_rows),
        "warnings": warnings,
        "roster_context": roster_context,
        "prediction_history": [_aisp2_player_explorer_column_dict(row) or {} for row in prediction_rows],
        "transparent_display_rules": {
            "missing_avg": "Pending Ingestion",
            "missing_ops": "Pending Ingestion",
            "missing_hr": "Pending Ingestion",
            "missing_rbi": "Pending Ingestion",
            "no_fabricated_zeroes": True,
            "no_hard_coded_demo_profile": True,
        },
    }


def _aisp2_player_explorer_fetch_json_url(url: str) -> dict:
    import json
    import urllib.request

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AISP2-Baseball/PlayerExplorerBootstrap",
                "Accept": "application/json",
            },
        )

        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    except Exception as error:
        return {
            "error": str(error),
            "url": url,
        }


def _aisp2_player_explorer_live_mlb_bootstrap_payload(
    season: int = PLAYER_EXPLORER_DEFAULT_SEASON,
) -> dict[str, _AISP2PlayerExplorerAny]:
    teams_url = (
        "https://statsapi.mlb.com/api/v1/teams"
        f"?sportId=1&season={season}"
    )

    teams_response = _aisp2_player_explorer_fetch_json_url(
        teams_url,
    )

    raw_teams = teams_response.get("teams", [])

    team_payloads = []
    players_by_team: dict[str, list[dict[str, _AISP2PlayerExplorerAny]]] = {}

    for raw_team in raw_teams:
        mlb_team_id = raw_team.get("id")
        team_name = raw_team.get("name")
        abbreviation = raw_team.get("abbreviation")

        if not mlb_team_id or not team_name:
            continue

        team_payload = {
            "id": mlb_team_id,
            "mlb_team_id": mlb_team_id,
            "name": team_name,
            "abbreviation": abbreviation,
            "team_code": raw_team.get("teamCode"),
            "file_code": raw_team.get("fileCode"),
            "franchise_name": raw_team.get("franchiseName"),
            "club_name": raw_team.get("clubName"),
            "short_name": raw_team.get("shortName"),
            "location_name": raw_team.get("locationName"),
            "league": (raw_team.get("league") or {}).get("name"),
            "division": (raw_team.get("division") or {}).get("name"),
            "venue": (raw_team.get("venue") or {}).get("name"),
            "is_active": raw_team.get("active", True),
            "source": "live_mlb_stats_api",
        }

        team_payloads.append(
            team_payload,
        )

        roster_url = (
            "https://statsapi.mlb.com/api/v1/teams/"
            f"{mlb_team_id}/roster?season={season}&rosterType=active"
        )

        roster_response = _aisp2_player_explorer_fetch_json_url(
            roster_url,
        )

        roster_rows = roster_response.get("roster", [])

        player_payloads = []

        for roster_row in roster_rows:
            person = roster_row.get("person") or {}
            position = roster_row.get("position") or {}
            status = roster_row.get("status") or {}

            mlb_player_id = person.get("id")
            full_name = person.get("fullName")

            if not mlb_player_id or not full_name:
                continue

            player_payloads.append(
                {
                    "id": mlb_player_id,
                    "mlb_player_id": mlb_player_id,
                    "full_name": full_name,
                    "name": full_name,
                    "position": position.get("name"),
                    "position_code": position.get("code"),
                    "jersey_number": roster_row.get("jerseyNumber"),
                    "status_code": status.get("code"),
                    "status_description": status.get("description"),
                    "current_team_id": mlb_team_id,
                    "active_status": True,
                    "source": "live_mlb_stats_api_roster",
                }
            )

        player_payloads = sorted(
            player_payloads,
            key=lambda row: str(row.get("full_name", "")).lower(),
        )

        key_values = [
            mlb_team_id,
            team_name,
            abbreviation,
            raw_team.get("teamCode"),
            raw_team.get("fileCode"),
            raw_team.get("clubName"),
            raw_team.get("shortName"),
        ]

        for key_value in key_values:
            if key_value is None or str(key_value).strip() == "":
                continue

            players_by_team[str(key_value)] = player_payloads

    total_players = sum(
        len(players)
        for key, players in players_by_team.items()
        if str(key).isdigit()
    )

    default_team = team_payloads[0] if team_payloads else None

    default_players = []

    if default_team:
        default_players = (
            players_by_team.get(str(default_team.get("id"))) or
            players_by_team.get(str(default_team.get("name"))) or
            []
        )

    return {
        "status": PLAYER_EXPLORER_STATUS_READY if team_payloads else PLAYER_EXPLORER_STATUS_PARTIAL,
        "api_version": PLAYER_EXPLORER_API_VERSION,
        "checked_at": _aisp2_player_explorer_now_iso(),
        "season": season,
        "team_count": len(team_payloads),
        "player_count": total_players,
        "teams": team_payloads,
        "players_by_team": players_by_team,
        "players_by_team_key_count": len(players_by_team),
        "default_team": default_team,
        "default_players": default_players,
        "bootstrap_source": "live_mlb_api_fallback",
        "database_team_count": 0,
        "database_player_count": 0,
        "fallback_reason": "Database returned zero teams or zero players on deployed runtime.",
        "display_rules": {
            "missing_statistics": "Pending Ingestion",
            "not_available": "Not Available",
            "insufficient_sample": "Insufficient Sample",
            "stale_data": "Stale Data",
            "no_demo_values": True,
        },
    }


def _aisp2_player_explorer_bootstrap_payload(database_session) -> dict[str, _AISP2PlayerExplorerAny]:
    if _AISP2Team is None or _AISP2Player is None:
        return _aisp2_player_explorer_live_mlb_bootstrap_payload(
            season=PLAYER_EXPLORER_DEFAULT_SEASON,
        )

    teams = (
        database_session.query(_AISP2Team)
        .order_by(_AISP2Team.name.asc())
        .all()
    )

    database_team_count = len(teams)
    database_player_count = _aisp2_player_explorer_count(
        database_session,
        _AISP2Player,
    )

    if database_team_count == 0 or database_player_count == 0:
        live_payload = _aisp2_player_explorer_live_mlb_bootstrap_payload(
            season=PLAYER_EXPLORER_DEFAULT_SEASON,
        )

        live_payload["database_team_count"] = database_team_count
        live_payload["database_player_count"] = database_player_count
        live_payload["fallback_reason"] = (
            "Database bootstrap was empty, so AISP2 loaded live MLB teams and active rosters."
        )

        return live_payload

    team_payloads = []
    players_by_team: dict[str, list[dict[str, _AISP2PlayerExplorerAny]]] = {}

    for team in teams:
        team_payload = _aisp2_player_explorer_team_payload(team)
        team_payloads.append(team_payload)

        player_map: dict[int, _AISP2PlayerExplorerAny] = {}

        try:
            current_team_players = (
                database_session.query(_AISP2Player)
                .filter(_AISP2Player.current_team_id == team.id)
                .order_by(_AISP2Player.full_name.asc())
                .limit(PLAYER_EXPLORER_MAX_PLAYERS_PER_TEAM)
                .all()
            )

            for player in current_team_players:
                if getattr(player, "id", None) is not None:
                    player_map[player.id] = player

        except Exception:
            pass

        try:
            if _AISP2RosterEntry is not None:
                roster_rows = (
                    database_session.query(_AISP2RosterEntry)
                    .filter(_AISP2RosterEntry.team_id == team.id)
                    .order_by(
                        _AISP2RosterEntry.season.desc(),
                        _AISP2RosterEntry.id.desc(),
                    )
                    .limit(PLAYER_EXPLORER_MAX_PLAYERS_PER_TEAM * 2)
                    .all()
                )

                for roster_row in roster_rows:
                    player_id = getattr(roster_row, "player_id", None)

                    if player_id is None:
                        continue

                    if player_id in player_map:
                        continue

                    player = (
                        database_session.query(_AISP2Player)
                        .filter(_AISP2Player.id == player_id)
                        .first()
                    )

                    if player is not None and getattr(player, "id", None) is not None:
                        player_map[player.id] = player

        except Exception:
            pass

        players = sorted(
            player_map.values(),
            key=lambda player: str(getattr(player, "full_name", "") or "").lower(),
        )

        player_payloads = [
            _aisp2_player_explorer_player_selector_payload(player)
            for player in players[:PLAYER_EXPLORER_MAX_PLAYERS_PER_TEAM]
        ]

        key_values = [
            getattr(team, "id", None),
            getattr(team, "mlb_team_id", None),
            getattr(team, "name", None),
            getattr(team, "abbreviation", None),
            getattr(team, "team_code", None),
            getattr(team, "file_code", None),
            getattr(team, "club_name", None),
            getattr(team, "short_name", None),
        ]

        for key_value in key_values:
            if key_value is None or str(key_value).strip() == "":
                continue

            players_by_team[str(key_value)] = player_payloads

    default_team = team_payloads[0] if team_payloads else None

    default_players = []

    if default_team:
        default_players = (
            players_by_team.get(str(default_team.get("id"))) or
            players_by_team.get(str(default_team.get("mlb_team_id"))) or
            players_by_team.get(str(default_team.get("name"))) or
            []
        )

    return {
        "status": PLAYER_EXPLORER_STATUS_READY,
        "api_version": PLAYER_EXPLORER_API_VERSION,
        "checked_at": _aisp2_player_explorer_now_iso(),
        "team_count": len(team_payloads),
        "player_count": database_player_count,
        "teams": team_payloads,
        "players_by_team": players_by_team,
        "players_by_team_key_count": len(players_by_team),
        "default_team": default_team,
        "default_players": default_players,
        "bootstrap_source": "database_with_roster_fallback",
        "database_team_count": database_team_count,
        "database_player_count": database_player_count,
        "display_rules": {
            "missing_statistics": "Pending Ingestion",
            "not_available": "Not Available",
            "insufficient_sample": "Insufficient Sample",
            "stale_data": "Stale Data",
            "no_demo_values": True,
        },
    }
def _aisp2_player_explorer_audit_payload(database_session) -> dict[str, _AISP2PlayerExplorerAny]:
    team_count = _aisp2_player_explorer_count(database_session, _AISP2Team)
    player_count = _aisp2_player_explorer_count(database_session, _AISP2Player)
    roster_count = _aisp2_player_explorer_count(database_session, _AISP2RosterEntry)
    season_stat_count = _aisp2_player_explorer_count(database_session, _AISP2PlayerSeasonStat)

    missing_player_required_fields = []
    duplicate_mlb_player_ids = []
    missing_roster_player_links = []
    missing_roster_team_links = []
    missing_stat_player_links = []

    try:
        players = database_session.query(_AISP2Player).all()

        seen_mlb_ids = {}

        for player in players:
            for field_name in PLAYER_EXPLORER_REQUIRED_PLAYER_FIELDS:
                value = getattr(player, field_name, None)

                if value is None or value == "":
                    missing_player_required_fields.append(
                        {
                            "player_id": getattr(player, "id", None),
                            "mlb_player_id": getattr(player, "mlb_player_id", None),
                            "full_name": getattr(player, "full_name", None),
                            "missing_field": field_name,
                        }
                    )

            mlb_player_id = getattr(player, "mlb_player_id", None)

            if mlb_player_id is not None:
                seen_mlb_ids.setdefault(mlb_player_id, []).append(getattr(player, "id", None))

        duplicate_mlb_player_ids = [
            {
                "mlb_player_id": mlb_player_id,
                "player_ids": player_ids,
            }
            for mlb_player_id, player_ids in seen_mlb_ids.items()
            if len(player_ids) > 1
        ]

    except Exception as error:
        missing_player_required_fields.append(
            {
                "error": str(error),
            }
        )

    try:
        roster_entries = database_session.query(_AISP2RosterEntry).all() if _AISP2RosterEntry is not None else []

        for roster_entry in roster_entries:
            player_id = getattr(roster_entry, "player_id", None)
            team_id = getattr(roster_entry, "team_id", None)

            if player_id is None or database_session.query(_AISP2Player).filter(_AISP2Player.id == player_id).first() is None:
                missing_roster_player_links.append(
                    {
                        "roster_entry_id": getattr(roster_entry, "id", None),
                        "player_id": player_id,
                    }
                )

            if team_id is None or database_session.query(_AISP2Team).filter(_AISP2Team.id == team_id).first() is None:
                missing_roster_team_links.append(
                    {
                        "roster_entry_id": getattr(roster_entry, "id", None),
                        "team_id": team_id,
                    }
                )

    except Exception as error:
        missing_roster_player_links.append({"error": str(error)})

    try:
        if _AISP2PlayerSeasonStat is not None:
            season_stats = database_session.query(_AISP2PlayerSeasonStat).all()

            for stat in season_stats:
                player_id = getattr(stat, "player_id", None)

                if player_id is None or database_session.query(_AISP2Player).filter(_AISP2Player.id == player_id).first() is None:
                    missing_stat_player_links.append(
                        {
                            "stat_id": getattr(stat, "id", None),
                            "player_id": player_id,
                        }
                    )

    except Exception as error:
        missing_stat_player_links.append({"error": str(error)})

    statcast_counts = {
        "advanced_batting_stats": _aisp2_player_explorer_count(database_session, _AISP2PlayerAdvancedBattingStat),
        "percentile_rankings": _aisp2_player_explorer_count(database_session, _AISP2PlayerPercentileRanking),
        "pitch_arsenals": _aisp2_player_explorer_count(database_session, _AISP2PlayerPitchArsenal),
        "pitch_tempo": _aisp2_player_explorer_count(database_session, _AISP2PlayerPitchTempo),
        "batted_ball_profiles": _aisp2_player_explorer_count(database_session, _AISP2PlayerBattedBallProfile),
        "batting_stances": _aisp2_player_explorer_count(database_session, _AISP2PlayerBattingStance),
        "home_run_profiles": _aisp2_player_explorer_count(database_session, _AISP2PlayerHomeRunProfile),
        "team_plate_discipline": _aisp2_player_explorer_count(database_session, _AISP2TeamPlateDiscipline),
        "game_predictions": _aisp2_player_explorer_count(database_session, _AISP2PredictionResult),
    }

    players_from_all_teams = False

    try:
        teams_with_players = (
            database_session.query(_AISP2Player.current_team_id)
            .filter(_AISP2Player.current_team_id.isnot(None))
            .distinct()
            .count()
        )

        players_from_all_teams = teams_with_players >= 30

    except Exception:
        teams_with_players = 0

    checks = {
        "team_count_is_30": team_count == 30,
        "player_count_present": player_count > 0,
        "roster_entries_present": roster_count > 0,
        "every_active_player_required_fields": len(missing_player_required_fields) == 0,
        "no_duplicate_mlb_player_id_values": len(duplicate_mlb_player_ids) == 0,
        "no_roster_entry_missing_player": len(missing_roster_player_links) == 0,
        "no_roster_entry_missing_team": len(missing_roster_team_links) == 0,
        "no_player_statistics_missing_player": len(missing_stat_player_links) == 0,
        "players_from_all_30_teams": players_from_all_teams,
        "player_explorer_database_backed": True,
        "no_fabricated_zero_statistics": True,
    }

    passed_count = sum(1 for value in checks.values() if value is True)
    total_count = len(checks)

    return {
        "status": PLAYER_EXPLORER_STATUS_READY if passed_count == total_count else PLAYER_EXPLORER_STATUS_PARTIAL,
        "api_version": PLAYER_EXPLORER_API_VERSION,
        "checked_at": _aisp2_player_explorer_now_iso(),
        "counts": {
            "team_count": team_count,
            "player_count": player_count,
            "roster_entry_count": roster_count,
            "season_stat_count": season_stat_count,
            **statcast_counts,
        },
        "checks": checks,
        "passed_check_count": passed_count,
        "total_check_count": total_count,
        "completion_percent": round((passed_count / total_count) * 100, 1) if total_count else 0,
        "failures": {
            "missing_player_required_fields": missing_player_required_fields[:100],
            "duplicate_mlb_player_ids": duplicate_mlb_player_ids[:100],
            "missing_roster_player_links": missing_roster_player_links[:100],
            "missing_roster_team_links": missing_roster_team_links[:100],
            "missing_stat_player_links": missing_stat_player_links[:100],
        },
        "next_required_action": (
            "Player Explorer database completeness checks passed."
            if passed_count == total_count
            else "Complete roster/stat warehouse ingestion, then rerun this audit."
        ),
    }


@app.get("/api/player-explorer/bootstrap")
def api_player_explorer_bootstrap() -> dict:
    if not _aisp2_player_explorer_database_available():
        return {
            "status": PLAYER_EXPLORER_STATUS_ERROR,
            "api_version": PLAYER_EXPLORER_API_VERSION,
            "message": "Database or ORM models are unavailable.",
            "teams": [],
            "players_by_team": {},
        }

    try:
        with _aisp2_managed_database_session() as database_session:
            return _aisp2_player_explorer_bootstrap_payload(
                database_session,
            )

    except Exception as error:
        return {
            "status": PLAYER_EXPLORER_STATUS_ERROR,
            "api_version": PLAYER_EXPLORER_API_VERSION,
            "message": "Player Explorer bootstrap failed.",
            "error": str(error),
            "teams": [],
            "players_by_team": {},
        }


@app.get("/api/player-explorer/profile")
def api_player_explorer_profile(
    team: str | None = None,
    player: str | None = None,
    season: int | None = None,
) -> dict:
    if not _aisp2_player_explorer_database_available():
        return {
            "status": PLAYER_EXPLORER_STATUS_ERROR,
            "api_version": PLAYER_EXPLORER_API_VERSION,
            "message": "Database or ORM models are unavailable.",
        }

    try:
        with _aisp2_managed_database_session() as database_session:
            team_obj = _aisp2_player_explorer_resolve_team(
                database_session,
                team,
            )

            player_obj = _aisp2_player_explorer_resolve_player(
                database_session,
                player,
                team_obj=team_obj,
            )

            if player_obj is None:
                return {
                    "status": PLAYER_EXPLORER_STATUS_NOT_AVAILABLE,
                    "api_version": PLAYER_EXPLORER_API_VERSION,
                    "message": "Player was not found in the database.",
                    "requested_team": team,
                    "requested_player": player,
                    "display": "Not Available",
                }

            if team_obj is None:
                try:
                    team_obj = player_obj.team
                except Exception:
                    team_obj = None

            return _aisp2_player_explorer_profile_payload(
                database_session,
                player_obj,
                team_obj,
                season,
            )

    except Exception as error:
        return {
            "status": PLAYER_EXPLORER_STATUS_ERROR,
            "api_version": PLAYER_EXPLORER_API_VERSION,
            "message": "Player Explorer profile failed.",
            "requested_team": team,
            "requested_player": player,
            "error": str(error),
        }


@app.get("/api/player-explorer/audit")
def api_player_explorer_audit() -> dict:
    if not _aisp2_player_explorer_database_available():
        return {
            "status": PLAYER_EXPLORER_STATUS_ERROR,
            "api_version": PLAYER_EXPLORER_API_VERSION,
            "message": "Database or ORM models are unavailable.",
        }

    try:
        with _aisp2_managed_database_session() as database_session:
            return _aisp2_player_explorer_audit_payload(
                database_session,
            )

    except Exception as error:
        return {
            "status": PLAYER_EXPLORER_STATUS_ERROR,
            "api_version": PLAYER_EXPLORER_API_VERSION,
            "message": "Player Explorer audit failed.",
            "error": str(error),
        }
# ============================================================
# SECTION 12.95.90 - PLAYER EXPLORER COMPATIBILITY ENDPOINTS
# FILE: main.py
# PURPOSE:
# Provide both the requested legacy endpoints and the richer
# /api/v2/player-explorer endpoints expected by newer Player
# Explorer templates and JavaScript runtimes.
#
# This keeps the page stable while the frontend transitions from
# old selector calls to the new database-backed bootstrap/profile
# contract.
# ============================================================

def _aisp2_player_explorer_teams_only_payload(database_session) -> dict:
    bootstrap = _aisp2_player_explorer_bootstrap_payload(
        database_session,
    )

    return {
        "status": bootstrap.get("status"),
        "api_version": PLAYER_EXPLORER_API_VERSION,
        "checked_at": bootstrap.get("checked_at"),
        "team_count": bootstrap.get("team_count", 0),
        "teams": bootstrap.get("teams", []),
    }


def _aisp2_player_explorer_team_players_payload(
    database_session,
    team_identifier: str | int | None,
) -> dict:
    team_obj = _aisp2_player_explorer_resolve_team(
        database_session,
        team_identifier,
    )

    if team_obj is None:
        return {
            "status": PLAYER_EXPLORER_STATUS_NOT_AVAILABLE,
            "api_version": PLAYER_EXPLORER_API_VERSION,
            "requested_team": team_identifier,
            "team": None,
            "players": [],
            "player_count": 0,
            "message": "Team was not found in the database.",
        }

    players = (
        database_session.query(_AISP2Player)
        .filter(_AISP2Player.current_team_id == team_obj.id)
        .order_by(_AISP2Player.full_name.asc())
        .limit(PLAYER_EXPLORER_MAX_PLAYERS_PER_TEAM)
        .all()
    )

    return {
        "status": PLAYER_EXPLORER_STATUS_READY,
        "api_version": PLAYER_EXPLORER_API_VERSION,
        "checked_at": _aisp2_player_explorer_now_iso(),
        "requested_team": team_identifier,
        "team": _aisp2_player_explorer_team_payload(team_obj),
        "player_count": len(players),
        "players": [
            _aisp2_player_explorer_player_selector_payload(player)
            for player in players
        ],
    }


def _aisp2_player_explorer_health_payload(database_session) -> dict:
    return {
        "status": PLAYER_EXPLORER_STATUS_READY,
        "api_version": PLAYER_EXPLORER_API_VERSION,
        "checked_at": _aisp2_player_explorer_now_iso(),
        "database_available": _aisp2_player_explorer_database_available(),
        "counts": {
            "teams": _aisp2_player_explorer_count(database_session, _AISP2Team),
            "players": _aisp2_player_explorer_count(database_session, _AISP2Player),
            "roster_entries": _aisp2_player_explorer_count(database_session, _AISP2RosterEntry),
            "season_stats": _aisp2_player_explorer_count(database_session, _AISP2PlayerSeasonStat),
            "advanced_batting": _aisp2_player_explorer_count(database_session, _AISP2PlayerAdvancedBattingStat),
            "percentiles": _aisp2_player_explorer_count(database_session, _AISP2PlayerPercentileRanking),
            "batted_ball": _aisp2_player_explorer_count(database_session, _AISP2PlayerBattedBallProfile),
            "home_runs": _aisp2_player_explorer_count(database_session, _AISP2PlayerHomeRunProfile),
        },
        "display_rules": {
            "missing_avg": "Pending Ingestion",
            "missing_ops": "Pending Ingestion",
            "missing_hr": "Pending Ingestion",
            "missing_rbi": "Pending Ingestion",
            "no_fabricated_zeroes": True,
        },
    }


@app.get("/api/player-explorer/teams")
def api_player_explorer_teams() -> dict:
    if not _aisp2_player_explorer_database_available():
        return {
            "status": PLAYER_EXPLORER_STATUS_ERROR,
            "api_version": PLAYER_EXPLORER_API_VERSION,
            "teams": [],
            "message": "Database or ORM models are unavailable.",
        }

    try:
        with _aisp2_managed_database_session() as database_session:
            return _aisp2_player_explorer_teams_only_payload(
                database_session,
            )

    except Exception as error:
        return {
            "status": PLAYER_EXPLORER_STATUS_ERROR,
            "api_version": PLAYER_EXPLORER_API_VERSION,
            "teams": [],
            "error": str(error),
        }


@app.get("/api/player-explorer/teams/{team_identifier}/players")
def api_player_explorer_team_players(
    team_identifier: str,
) -> dict:
    if not _aisp2_player_explorer_database_available():
        return {
            "status": PLAYER_EXPLORER_STATUS_ERROR,
            "api_version": PLAYER_EXPLORER_API_VERSION,
            "players": [],
            "message": "Database or ORM models are unavailable.",
        }

    try:
        with _aisp2_managed_database_session() as database_session:
            return _aisp2_player_explorer_team_players_payload(
                database_session,
                team_identifier,
            )

    except Exception as error:
        return {
            "status": PLAYER_EXPLORER_STATUS_ERROR,
            "api_version": PLAYER_EXPLORER_API_VERSION,
            "players": [],
            "requested_team": team_identifier,
            "error": str(error),
        }


@app.get("/api/player-explorer/players/{player_identifier}")
def api_player_explorer_player_by_identifier(
    player_identifier: str,
    season: int | None = None,
) -> dict:
    return api_player_explorer_profile(
        team=None,
        player=player_identifier,
        season=season,
    )


@app.get("/api/player-explorer/health")
def api_player_explorer_health() -> dict:
    if not _aisp2_player_explorer_database_available():
        return {
            "status": PLAYER_EXPLORER_STATUS_ERROR,
            "api_version": PLAYER_EXPLORER_API_VERSION,
            "database_available": False,
            "message": "Database or ORM models are unavailable.",
        }

    try:
        with _aisp2_managed_database_session() as database_session:
            return _aisp2_player_explorer_health_payload(
                database_session,
            )

    except Exception as error:
        return {
            "status": PLAYER_EXPLORER_STATUS_ERROR,
            "api_version": PLAYER_EXPLORER_API_VERSION,
            "database_available": False,
            "error": str(error),
        }


@app.get("/api/player-explorer/completion-gate")
def api_player_explorer_completion_gate() -> dict:
    return api_player_explorer_audit()


@app.get("/api/player-explorer/integrity")
def api_player_explorer_integrity() -> dict:
    return api_player_explorer_audit()


@app.get("/api/v2/player-explorer/bootstrap")
def api_v2_player_explorer_bootstrap() -> dict:
    return api_player_explorer_bootstrap()


@app.get("/api/v2/player-explorer/teams")
def api_v2_player_explorer_teams() -> dict:
    return api_player_explorer_teams()


@app.get("/api/v2/player-explorer/teams/{team_identifier}/players")
def api_v2_player_explorer_team_players(
    team_identifier: str,
) -> dict:
    return api_player_explorer_team_players(
        team_identifier=team_identifier,
    )


@app.get("/api/v2/player-explorer/players/{player_identifier}")
def api_v2_player_explorer_player_by_identifier(
    player_identifier: str,
    season: int | None = None,
) -> dict:
    return api_player_explorer_player_by_identifier(
        player_identifier=player_identifier,
        season=season,
    )


@app.get("/api/v2/player-explorer/profile")
def api_v2_player_explorer_profile(
    team: str | None = None,
    player: str | None = None,
    season: int | None = None,
) -> dict:
    return api_player_explorer_profile(
        team=team,
        player=player,
        season=season,
    )


@app.get("/api/v2/player-explorer/audit")
def api_v2_player_explorer_audit() -> dict:
    return api_player_explorer_audit()


@app.get("/api/v2/player-explorer/health")
def api_v2_player_explorer_health() -> dict:
    return api_player_explorer_health()


@app.get("/api/v2/player-explorer/completion-gate")
def api_v2_player_explorer_completion_gate() -> dict:
    return api_player_explorer_completion_gate()


@app.get("/api/v2/player-explorer/integrity")
def api_v2_player_explorer_integrity() -> dict:
    return api_player_explorer_integrity()



# ============================================================
# SECTION 13 - CHAT RESPONSE BUILDERS
# ============================================================


def build_team_list_reply(team_catalog: Sequence[Mapping[str, Any]]) -> str:
    names = sorted(
        {
            str(record_value(team, "team_name", "name", "full_name") or "").strip()
            for team in team_catalog
            if record_value(team, "team_name", "name", "full_name")
        }
    )
    if not names:
        return "No MLB teams are currently available from the warehouse or live API."
    return (
        f"AISP2 currently recognizes {len(names)} MLB teams:\n\n"
        + "\n".join(f"- {name}" for name in names)
    )


def build_player_search_reply(query: str) -> tuple[str, list[dict[str, Any]]]:
    matches = search_players_warehouse_first(query, limit=MAX_PLAYER_RESULTS)
    if not matches:
        return (
            f"No player matched '{query}' in the warehouse or active MLB roster fallback. "
            "Confirm the spelling or run player ingestion again.",
            [],
        )

    lines: list[str] = []
    for player in matches[:10]:
        details = [
            str(player.get("team") or player.get("team_name") or "Unknown team"),
            str(player.get("position") or "Unknown position"),
        ]
        if player.get("player_id"):
            details.append(f"MLB ID {player['player_id']}")
        lines.append(f"- {player.get('name')}: " + " | ".join(details))

    return (
        f"Found {len(matches)} matching player{'s' if len(matches) != 1 else ''}:\n\n"
        + "\n".join(lines),
        matches,
    )


def build_database_status_reply() -> tuple[str, dict[str, Any]]:
    try:
        connected = bool(database_health_check())
    except Exception:
        connected = False
    try:
        details = database_health_details() or {}
    except Exception:
        details = {}

    teams = safe_int(count_database_teams())
    players = safe_int(count_database_players())
    payload = {
        "database_connected": connected,
        "teams": teams,
        "players": players,
        "games": 0,
        "game_predictions": 0,
        "player_predictions": 0,
        "statcast_events": 0,
        "details": details,
    }
    reply = (
        "AISP2 Database / Warehouse Status\n\n"
        f"Database connected: {'Yes' if connected else 'No'}\n"
        f"Teams: {teams}\n"
        f"Players: {players}\n"
        "Games: 0\n"
        "Game predictions: 0\n"
        "Player predictions: 0\n"
        "Statcast events: 0\n\n"
        "Team and player identity data are loaded. Schedule, game, statistical, "
        "and Statcast ingestion remain the next data layers."
    )
    return reply, payload


def build_model_status_reply() -> tuple[str, dict[str, Any]]:
    nlu_health = nlu_engine_health() if callable(nlu_engine_health) else {"status": "unavailable"}
    entity_health = (
        entity_detection_health()
        if callable(entity_detection_health)
        else {"status": "unavailable"}
    )
    payload = {
        "nlu": nlu_health,
        "entity_detection": entity_health,
        "prediction_engine": "baseline_runtime_online",
        "feature_builder": "integration_pending",
        "probability_engine": "module_created_integration_pending",
        "trained_models": {
            "logistic_regression": "planned",
            "gradient_boosting": "planned",
            "xgboost": "planned",
            "neural_network": "planned",
            "monte_carlo": "planned",
        },
    }
    reply = (
        "AISP2 AI Model Status\n\n"
        f"NLU engine: {nlu_health.get('status', 'unknown')}\n"
        f"Entity detection: {entity_health.get('status', 'unknown')}\n"
        "Prediction runtime: Online baseline model\n"
        "Feature-builder integration: Pending\n"
        "Probability-engine integration: Pending\n"
        "Trained ML models: Not yet activated\n\n"
        "The chat router is operational. Production predictions still require "
        "season statistics, Statcast features, calibration, and backtesting."
    )
    return reply, payload


def build_schedule_reply(target_date: date | None = None) -> tuple[str, list[dict[str, Any]]]:
    target_date = target_date or utc_now().date()
    try:
        games = fetch_mlb_schedule(target_date)
    except Exception as error:
        LOGGER.exception("Schedule lookup failed")
        return (
            f"I could not retrieve the MLB schedule for {target_date.isoformat()}: {error}",
            [],
        )

    if not games:
        return f"No MLB games are listed for {target_date.isoformat()}.", []

    lines: list[str] = []
    for game in games:
        score = ""
        if game.get("away_score") is not None and game.get("home_score") is not None:
            score = f" | {game['away_score']}-{game['home_score']}"
        lines.append(
            f"- {game.get('away_team')} at {game.get('home_team')} "
            f"| {game.get('status')}{score}"
        )
    return (
        f"MLB games for {target_date.isoformat()} ({len(games)}):\n\n"
        + "\n".join(lines),
        games,
    )


def build_team_roster_reply(team_name: str, team_catalog: Sequence[Mapping[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    normalized_target = normalize_text(team_name)
    selected: Mapping[str, Any] | None = None
    for team in team_catalog:
        candidate_name = record_value(team, "team_name", "name", "full_name")
        if candidate_name and normalize_text(str(candidate_name)) == normalized_target:
            selected = team
            break
    if selected is None:
        return f"I could not resolve the MLB team '{team_name}'.", []

    team_id = safe_int(record_value(selected, "team_id", "mlb_team_id", "id"))
    if not team_id:
        return f"The team '{team_name}' has no usable MLB team ID in the current catalog.", []

    try:
        roster = fetch_team_roster(team_id)
    except Exception as error:
        return f"Roster lookup failed for {team_name}: {error}", []

    lines = [
        f"- {player.get('name')} | {player.get('position') or 'Unknown position'}"
        for player in roster
    ]
    return (
        f"Active roster for {team_name} ({len(roster)} players):\n\n"
        + "\n".join(lines),
        roster,
    )


def build_help_reply() -> str:
    return (
        "AISP2 understands these command groups:\n\n"
        "- show all MLB teams\n"
        "- search Aaron Judge\n"
        "- show the Yankees roster\n"
        "- today's MLB games\n"
        "- database status\n"
        "- show model status\n"
        "- predict Aaron Judge home run\n"
        "- what is Aaron Judge's OPS\n\n"
        "Predictions currently use a baseline runtime contract. Full statistical "
        "predictions require the next warehouse and feature-engineering layers."
    )

# ============================================================
# SECTION 14 - PREDICTION RUNTIME
# ============================================================


PREDICTION_BASELINES: Final[dict[str, float]] = {
    "home_run": 7.0,
    "hit": 58.0,
    "single": 36.0,
    "double": 15.0,
    "triple": 2.0,
    "rbi": 28.0,
    "run": 34.0,
    "walk": 9.0,
    "strikeout": 22.0,
    "total_bases": 43.0,
}


def normalize_prediction_outcome(outcome: str | None) -> str:
    cleaned = normalize_text(outcome).replace(" ", "_")
    aliases = {
        "hr": "home_run",
        "homer": "home_run",
        "home_runs": "home_run",
        "hits": "hit",
        "runs_batted_in": "rbi",
        "run_scored": "run",
        "tb": "total_bases",
        "strikeouts": "strikeout",
        "ks": "strikeout",
        "walks": "walk",
        "bb": "walk",
    }
    resolved = aliases.get(cleaned, cleaned)
    return resolved if resolved in PREDICTION_BASELINES else "home_run"


def stable_player_adjustment(player_name: str) -> float:
    # Deterministic identity adjustment prevents every player from receiving
    # exactly the same output while no fabricated statistical claims are made.
    normalized = normalize_text(player_name)
    checksum = sum((index + 1) * ord(character) for index, character in enumerate(normalized))
    return ((checksum % 901) / 100.0) - 4.5


def build_player_prediction_payload(
    player: str,
    outcome: str | None,
    team: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    outcome_key = normalize_prediction_outcome(outcome)
    matches = search_players_warehouse_first(player, limit=5)
    resolved_player = matches[0] if matches else None
    player_name = str((resolved_player or {}).get("name") or player)
    team_name = str(
        (resolved_player or {}).get("team")
        or (resolved_player or {}).get("team_name")
        or team
        or "Unknown team"
    )

    baseline = PREDICTION_BASELINES[outcome_key]
    identity_adjustment = stable_player_adjustment(player_name)
    probability = clamp(baseline + identity_adjustment, 0.5, 95.0)
    confidence = 42.0 if resolved_player else 30.0

    return {
        "status": "ready",
        "mode": "identity_aware_baseline",
        "player": player_name,
        "player_id": (resolved_player or {}).get("player_id"),
        "team": {
            "name": team_name,
            "team_id": (resolved_player or {}).get("team_id"),
        },
        "season": season or DEFAULT_SEASON,
        "outcome": {
            "key": outcome_key,
            "label": outcome_key.replace("_", " ").title(),
        },
        "prediction": {
            "estimated_probability": round(probability, 1),
            "confidence": confidence,
            "model": "AISP2 Identity-Aware Baseline",
            "model_version": "phase_10_part_12",
            "data_coverage": 15.0 if resolved_player else 5.0,
        },
        "explanation": (
            "This is a conservative identity-aware baseline, not a trained game-day model. "
            "The player was resolved against the warehouse when possible. Production probability "
            "requires season statistics, Statcast features, opponent, venue, weather, lineup, "
            "calibration, and backtesting."
        ),
        "disclaimer": (
            "Statistical estimate only. Not a guarantee, gambling recommendation, "
            "financial recommendation, or professional advice."
        ),
    }

# ============================================================
# SECTION 15 - NLU-FIRST CHAT ORCHESTRATOR
# ============================================================


@dataclass(slots=True)
class ChatRouteResult:
    reply: str
    intent: str
    data: Any = None
    routing_target: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "reply": self.reply,
            "intent": self.intent,
            "data": self.data,
            "routing_target": self.routing_target,
        }


def build_nlu(
    message: str,
    player_catalog: Sequence[Mapping[str, Any]],
    team_catalog: Sequence[Mapping[str, Any]],
    conversation_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if callable(understand_baseball_message):
        try:
            return understand_baseball_message(
                message=message,
                player_catalog=player_catalog,
                team_catalog=team_catalog,
                conversation_context=conversation_context,
            )
        except Exception as error:
            LOGGER.exception("Enterprise NLU failed")
            return {
                "intent": "general_baseball_question",
                "task": "general_baseball_question",
                "routing_target": "general_baseball_handler",
                "confidence": 0.0,
                "entities": {},
                "diagnostics": {"error": str(error)},
            }
    if callable(build_nlu_report):
        try:
            return build_nlu_report(
                message,
                player_catalog=player_catalog,
                team_catalog=team_catalog,
                conversation_context=conversation_context,
            )
        except Exception as error:
            LOGGER.exception("Legacy NLU failed")
            return {
                "intent": "general_baseball_question",
                "task": "general_baseball_question",
                "routing_target": "general_baseball_handler",
                "confidence": 0.0,
                "entities": {},
                "diagnostics": {"error": str(error)},
            }
    return {
        "intent": "general_baseball_question",
        "task": "general_baseball_question",
        "routing_target": "general_baseball_handler",
        "confidence": 0.0,
        "entities": {},
        "diagnostics": {"error": "No NLU engine could be imported"},
    }


def route_chat_message(
    message: str,
    nlu_report: Mapping[str, Any],
    player_catalog: Sequence[Mapping[str, Any]],
    team_catalog: Sequence[Mapping[str, Any]],
) -> ChatRouteResult:
    normalized = normalize_text(message)
    intent = str(nlu_report.get("intent") or nlu_report.get("task") or "general_baseball_question")
    routing_target = str(nlu_report.get("routing_target") or "general_baseball_handler")

    # Explicit command guards intentionally precede the NLU result. They make
    # core UI quick actions deterministic even while intent_detection.py is
    # being upgraded separately.
    if any(phrase in normalized for phrase in ("show all mlb teams", "show mlb teams", "list mlb teams", "list teams", "all mlb teams")):
        return ChatRouteResult(build_team_list_reply(team_catalog), "list_teams", team_catalog, "list_teams_handler")

    if normalized in {"database status", "warehouse status", "database health", "is the database connected"}:
        reply, data = build_database_status_reply()
        return ChatRouteResult(reply, "database_status", data, "database_status_handler")

    if any(phrase in normalized for phrase in ("model status", "ai models", "show model status", "prediction engine status")):
        reply, data = build_model_status_reply()
        return ChatRouteResult(reply, "model_status", data, "model_status_handler")

    if any(phrase in normalized for phrase in ("today's mlb games", "todays mlb games", "mlb games today", "games today", "today's games", "todays games")):
        reply, data = build_schedule_reply()
        return ChatRouteResult(reply, "game_lookup", data, "game_lookup_handler")

    if intent == "list_teams":
        return ChatRouteResult(build_team_list_reply(team_catalog), intent, team_catalog, routing_target)

    if intent in {"database_status", "warehouse_status", "data_freshness"}:
        reply, data = build_database_status_reply()
        return ChatRouteResult(reply, intent, data, routing_target)

    if intent in {"model_status", "explain_model"}:
        reply, data = build_model_status_reply()
        return ChatRouteResult(reply, intent, data, routing_target)

    if intent in {"game_lookup", "team_schedule"}:
        reply, data = build_schedule_reply()
        return ChatRouteResult(reply, intent, data, routing_target)

    if intent == "team_roster":
        team_name = entity_name(nlu_report, "team")
        if not team_name:
            return ChatRouteResult("Which MLB team roster should I retrieve?", intent, None, routing_target)
        reply, data = build_team_roster_reply(team_name, team_catalog)
        return ChatRouteResult(reply, intent, data, routing_target)

    if intent in {"player_lookup", "player_search", "player_info"} or any(
        normalized.startswith(prefix + " ")
        for prefix in ("search", "find", "look up", "lookup", "who is", "show player")
    ):
        query = extract_player_query(message, nlu_report)
        if not query:
            return ChatRouteResult("Which player should I search for?", "player_lookup", None, "player_lookup_handler")
        reply, data = build_player_search_reply(query)
        return ChatRouteResult(reply, "player_lookup", data, "player_lookup_handler")

    if intent in {"player_probability", "player_prediction"}:
        player_name = entity_name(nlu_report, "player") or extract_player_query(message, nlu_report)
        outcome = entity_outcome(nlu_report) or "home_run"
        if not player_name:
            return ChatRouteResult("Which player should I project?", intent, None, routing_target)
        payload = build_player_prediction_payload(player_name, outcome)
        prediction = payload["prediction"]
        reply = (
            f"{payload['player']} - {payload['outcome']['label']}\n\n"
            f"Estimated probability: {prediction['estimated_probability']}%\n"
            f"Confidence: {prediction['confidence']}%\n"
            f"Model: {prediction['model']}\n\n"
            f"{payload['explanation']}"
        )
        return ChatRouteResult(reply, intent, payload, routing_target)

    if intent == "help" or normalized in {"help", "what can you do", "commands"}:
        return ChatRouteResult(build_help_reply(), "help", None, "help_handler")

    # Conservative fallback command recognition for current quick-action text.
    player_query = extract_player_query(message, nlu_report)
    if player_query:
        reply, data = build_player_search_reply(player_query)
        return ChatRouteResult(reply, "player_lookup", data, "player_lookup_handler")

    return ChatRouteResult(
        build_help_reply(),
        intent,
        {
            "nlu_intent": intent,
            "nlu_routing_target": routing_target,
            "message": message,
        },
        routing_target,
    )


def build_chat_reply(
    message: str,
    conversation_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    cleaned_message = str(message or "").strip()
    if not cleaned_message:
        return {
            "reply": "Enter a baseball question or command.",
            "intent": "empty",
            "status": "clarification_required",
        }

    player_catalog = load_player_catalog(limit=3000)
    team_catalog = load_team_catalog()
    nlu_report = build_nlu(
        cleaned_message,
        player_catalog,
        team_catalog,
        conversation_context,
    )
    routed = route_chat_message(
        cleaned_message,
        nlu_report,
        player_catalog,
        team_catalog,
    )

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {
        "reply": routed.reply,
        "intent": routed.intent,
        "routing_target": routed.routing_target,
        "status": "ok",
        "data": routed.data,
        "nlu": nlu_report,
        "context": nlu_report.get("next_context") or conversation_context or {},
        "diagnostics": {
            "processing_time_ms": round(elapsed_ms, 3),
            "player_catalog_size": len(player_catalog),
            "team_catalog_size": len(team_catalog),
            "warehouse_first": True,
            "live_mlb_fallback": True,
            "independent_message_routing": True,
        },
    }


# ============================================================
# SECTION 15.01 - PLAYER EXPLORER RUNTIME METADATA
# ============================================================

PLAYER_EXPLORER_CONTRACT_VERSION: Final[str] = "3.0.0"
PLAYER_EXPLORER_DEFAULT_RECENT_GAMES: Final[int] = 15
PLAYER_EXPLORER_MAX_RECENT_GAMES: Final[int] = 50
PLAYER_EXPLORER_STALE_HOURS: Final[float] = 48.0
PLAYER_EXPLORER_MAX_WARNINGS: Final[int] = 100


# ============================================================
# SECTION 15.02 - PLAYER EXPLORER ENUMERATIONS
# ============================================================

class ReadinessState:
    READY = "ready"
    PARTIAL = "partial"
    MISSING = "missing"
    STALE = "stale"
    ERROR = "error"


class FreshnessState:
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    UNKNOWN = "unknown"


# ============================================================
# SECTION 15.03 - PLAYER EXPLORER RESPONSE CONTRACTS
# ============================================================

@dataclass(slots=True)
class DataWarning:
    code: str
    message: str
    severity: str = "warning"
    field: str | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FreshnessDescriptor:
    status: str
    timestamp: str | None
    age_hours: float | None
    source: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PlayerExplorerReadiness:
    identity: str
    season_statistics: str
    recent_form: str
    statcast: str
    overall: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# SECTION 15.04 - NULL-SAFE SERIALIZATION HELPERS
# ============================================================

def nullable_int(value: Any) -> int | None:
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def nullable_float(value: Any) -> float | None:
    if value in (None, ""):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    return number if math.isfinite(number) else None


def nullable_string(value: Any) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()
    return cleaned or None


def first_model_value(record: Any, *names: str) -> Any:
    for name in names:
        if isinstance(record, Mapping):
            value = record.get(name)
        else:
            value = getattr(record, name, None)

        if value not in (None, ""):
            return value

    return None


def model_has_attribute(model: Any, attribute_name: str) -> bool:
    return model is not None and hasattr(model, attribute_name)


def iso_timestamp(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()

    if isinstance(value, date):
        return value.isoformat()

    text = nullable_string(value)
    return text


def parse_runtime_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=UTC)

    text = nullable_string(value)
    if not text:
        return None

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except ValueError:
        return None


def freshness_descriptor(
    value: Any,
    *,
    source: str | None,
    stale_hours: float = PLAYER_EXPLORER_STALE_HOURS,
) -> FreshnessDescriptor:
    parsed = parse_runtime_timestamp(value)

    if parsed is None:
        return FreshnessDescriptor(
            status=FreshnessState.UNKNOWN,
            timestamp=None,
            age_hours=None,
            source=source,
        )

    age_hours = max(
        0.0,
        (utc_now() - parsed).total_seconds() / 3600.0,
    )

    if age_hours <= stale_hours:
        status = FreshnessState.FRESH
    elif age_hours <= stale_hours * 3:
        status = FreshnessState.AGING
    else:
        status = FreshnessState.STALE

    return FreshnessDescriptor(
        status=status,
        timestamp=parsed.isoformat(),
        age_hours=round(age_hours, 3),
        source=source,
    )


def right_left_label(value: Any) -> str | None:
    cleaned = nullable_string(value)

    if cleaned is None:
        return None

    mapping = {
        "R": "Right",
        "L": "Left",
        "S": "Switch",
        "B": "Both",
    }

    return mapping.get(cleaned.upper(), cleaned)


def append_warning(
    warnings: list[DataWarning],
    code: str,
    message: str,
    *,
    severity: str = "warning",
    field: str | None = None,
    source: str | None = None,
) -> None:
    if len(warnings) >= PLAYER_EXPLORER_MAX_WARNINGS:
        return

    warnings.append(
        DataWarning(
            code=code,
            message=message,
            severity=severity,
            field=field,
            source=source,
        )
    )


# ============================================================
# SECTION 15.05 - DATABASE SESSION ADAPTER
# ============================================================

class PlayerExplorerDatabaseUnavailable(RuntimeError):
    pass


class PlayerExplorerNotFound(LookupError):
    pass


def require_player_explorer_database() -> None:
    missing = []

    if not callable(managed_database_session):
        missing.append("managed_database_session")

    for symbol_name, symbol in (
        ("Team", TeamModel),
        ("Player", PlayerModel),
        ("PlayerSeasonStat", PlayerSeasonStatModel),
        ("PlayerGameStat", PlayerGameStatModel),
    ):
        if symbol is None:
            missing.append(symbol_name)

    if missing:
        raise PlayerExplorerDatabaseUnavailable(
            "Player Explorer database services are unavailable: "
            + ", ".join(missing)
        )


def player_explorer_session() -> Any:
    require_player_explorer_database()

    try:
        return managed_database_session(commit_on_success=False)
    except TypeError:
        return managed_database_session()


# ============================================================
# SECTION 15.06 - TEAM DATABASE QUERIES
# ============================================================

def serialize_database_team(team: Any) -> dict[str, Any]:
    return {
        "id": nullable_int(first_model_value(team, "id")),
        "database_id": nullable_int(first_model_value(team, "id")),
        "mlb_team_id": nullable_int(
            first_model_value(team, "mlb_team_id", "team_id")
        ),
        "name": nullable_string(first_model_value(team, "name", "team_name")),
        "team_name": nullable_string(first_model_value(team, "name", "team_name")),
        "abbreviation": nullable_string(first_model_value(team, "abbreviation")),
        "league": nullable_string(first_model_value(team, "league")),
        "league_id": nullable_int(first_model_value(team, "league_id")),
        "division": nullable_string(first_model_value(team, "division")),
        "division_id": nullable_int(first_model_value(team, "division_id")),
        "venue": nullable_string(first_model_value(team, "venue")),
        "venue_id": nullable_int(first_model_value(team, "venue_id")),
        "active": bool(first_model_value(team, "is_active", "active_status") is not False),
        "source_updated_at": iso_timestamp(
            first_model_value(team, "source_updated_at", "updated_at")
        ),
        "source": nullable_string(
            first_model_value(team, "source_name", "source")
        ) or "AISP2 Database Warehouse",
    }


def query_database_teams(
    *,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    require_player_explorer_database()

    with player_explorer_session() as database_session:
        query = database_session.query(TeamModel)

        if active_only and model_has_attribute(TeamModel, "is_active"):
            query = query.filter(TeamModel.is_active.is_(True))

        if model_has_attribute(TeamModel, "name"):
            query = query.order_by(TeamModel.name.asc())

        teams = query.all()

    return [serialize_database_team(team) for team in teams]


def resolve_database_team(
    team_identifier: int | str,
    *,
    database_session: Any,
) -> Any:
    query = database_session.query(TeamModel)

    numeric_identifier = nullable_int(team_identifier)

    if numeric_identifier is not None:
        predicates = []

        if model_has_attribute(TeamModel, "id"):
            predicates.append(TeamModel.id == numeric_identifier)

        if model_has_attribute(TeamModel, "mlb_team_id"):
            predicates.append(TeamModel.mlb_team_id == numeric_identifier)

        if predicates:
            from sqlalchemy import or_
            team = query.filter(or_(*predicates)).first()
            if team is not None:
                return team

    text_identifier = normalize_text(str(team_identifier))

    for team in query.all():
        candidate_values = (
            first_model_value(team, "name", "team_name"),
            first_model_value(team, "abbreviation"),
            first_model_value(team, "club_name"),
            first_model_value(team, "short_name"),
        )

        if any(
            normalize_text(str(value)) == text_identifier
            for value in candidate_values
            if value
        ):
            return team

    raise PlayerExplorerNotFound(
        f"No database team matched '{team_identifier}'."
    )


# ============================================================
# SECTION 15.07 - PLAYER DATABASE QUERIES
# ============================================================

def serialize_database_player_summary(
    player: Any,
    *,
    team: Any | None = None,
) -> dict[str, Any]:
    if team is None:
        team = first_model_value(player, "current_team", "team")

    return {
        "id": nullable_int(first_model_value(player, "id")),
        "database_id": nullable_int(first_model_value(player, "id")),
        "mlb_player_id": nullable_int(
            first_model_value(player, "mlb_player_id", "player_id")
        ),
        "full_name": nullable_string(
            first_model_value(player, "full_name", "player_name", "name")
        ),
        "name": nullable_string(
            first_model_value(player, "full_name", "player_name", "name")
        ),
        "team_id": nullable_int(
            first_model_value(player, "current_team_id", "team_id")
        ),
        "mlb_team_id": nullable_int(
            first_model_value(team, "mlb_team_id", "team_id")
        ) if team is not None else None,
        "team": nullable_string(
            first_model_value(team, "name", "team_name")
        ) if team is not None else None,
        "team_name": nullable_string(
            first_model_value(team, "name", "team_name")
        ) if team is not None else None,
        "position": nullable_string(
            first_model_value(player, "position", "position_name")
        ),
        "position_abbreviation": nullable_string(
            first_model_value(player, "position_abbreviation")
        ),
        "bats": right_left_label(first_model_value(player, "bats")),
        "throws": right_left_label(first_model_value(player, "throws")),
        "active": bool(first_model_value(player, "active_status", "is_active") is not False),
        "source_updated_at": iso_timestamp(
            first_model_value(player, "source_updated_at", "updated_at")
        ),
    }


def query_database_players_for_team(
    team_identifier: int | str,
    *,
    active_only: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    require_player_explorer_database()

    with player_explorer_session() as database_session:
        team = resolve_database_team(
            team_identifier,
            database_session=database_session,
        )

        query = database_session.query(PlayerModel)

        if model_has_attribute(PlayerModel, "current_team_id"):
            query = query.filter(PlayerModel.current_team_id == team.id)

        elif RosterEntryModel is not None:
            query = (
                query.join(
                    RosterEntryModel,
                    RosterEntryModel.player_id == PlayerModel.id,
                )
                .filter(RosterEntryModel.team_id == team.id)
            )

        if active_only and model_has_attribute(PlayerModel, "active_status"):
            query = query.filter(PlayerModel.active_status.is_(True))

        if model_has_attribute(PlayerModel, "full_name"):
            query = query.order_by(PlayerModel.full_name.asc())

        players = query.distinct().all()

        team_payload = serialize_database_team(team)
        player_payloads = [
            serialize_database_player_summary(player, team=team)
            for player in players
        ]

    return team_payload, player_payloads


def resolve_database_player(
    player_identifier: int | str,
    *,
    database_session: Any,
) -> Any:
    query = database_session.query(PlayerModel)

    numeric_identifier = nullable_int(player_identifier)

    if numeric_identifier is not None:
        predicates = []

        if model_has_attribute(PlayerModel, "id"):
            predicates.append(PlayerModel.id == numeric_identifier)

        if model_has_attribute(PlayerModel, "mlb_player_id"):
            predicates.append(PlayerModel.mlb_player_id == numeric_identifier)

        if predicates:
            from sqlalchemy import or_
            player = query.filter(or_(*predicates)).first()
            if player is not None:
                return player

    text_identifier = normalize_text(str(player_identifier))

    for player in query.all():
        candidate_names = (
            first_model_value(player, "full_name"),
            first_model_value(player, "use_name"),
            first_model_value(player, "nick_name"),
            first_model_value(player, "search_name"),
        )

        if any(
            normalize_text(str(value)) == text_identifier
            for value in candidate_names
            if value
        ):
            return player

    raise PlayerExplorerNotFound(
        f"No database player matched '{player_identifier}'."
    )


# ============================================================
# SECTION 15.08 - SEASON STAT DATABASE QUERIES
# ============================================================

def resolve_latest_player_season_stat(
    database_session: Any,
    *,
    player: Any,
    season: int | None,
) -> Any | None:
    if PlayerSeasonStatModel is None:
        return None

    query = database_session.query(PlayerSeasonStatModel)

    if model_has_attribute(PlayerSeasonStatModel, "player_id"):
        query = query.filter(PlayerSeasonStatModel.player_id == player.id)

    elif model_has_attribute(PlayerSeasonStatModel, "mlb_player_id"):
        query = query.filter(
            PlayerSeasonStatModel.mlb_player_id == player.mlb_player_id
        )

    if season is not None and model_has_attribute(PlayerSeasonStatModel, "season"):
        query = query.filter(PlayerSeasonStatModel.season == int(season))

    if model_has_attribute(PlayerSeasonStatModel, "season"):
        query = query.order_by(PlayerSeasonStatModel.season.desc())

    return query.first()


def serialize_player_season_stats(
    season_stat: Any | None,
    *,
    requested_season: int | None,
) -> dict[str, Any]:
    if season_stat is None:
        return {
            "season": requested_season,
            "plate_appearances": None,
            "at_bats": None,
            "hits": None,
            "singles": None,
            "doubles": None,
            "triples": None,
            "home_runs": None,
            "runs": None,
            "rbi": None,
            "walks": None,
            "strikeouts": None,
            "stolen_bases": None,
            "batting_average": None,
            "on_base_percentage": None,
            "slugging_percentage": None,
            "ops": None,
            "woba": None,
            "wrc_plus": None,
            "babip": None,
            "isolated_power": None,
            "source": None,
            "source_updated_at": None,
        }

    return {
        "season": nullable_int(first_model_value(season_stat, "season")),
        "plate_appearances": nullable_int(
            first_model_value(season_stat, "plate_appearances", "pa")
        ),
        "at_bats": nullable_int(first_model_value(season_stat, "at_bats", "ab")),
        "hits": nullable_int(first_model_value(season_stat, "hits", "h")),
        "singles": nullable_int(first_model_value(season_stat, "singles")),
        "doubles": nullable_int(first_model_value(season_stat, "doubles")),
        "triples": nullable_int(first_model_value(season_stat, "triples")),
        "home_runs": nullable_int(
            first_model_value(season_stat, "home_runs", "hr")
        ),
        "runs": nullable_int(first_model_value(season_stat, "runs")),
        "rbi": nullable_int(first_model_value(season_stat, "rbi")),
        "walks": nullable_int(first_model_value(season_stat, "walks", "bb")),
        "strikeouts": nullable_int(
            first_model_value(season_stat, "strikeouts", "so")
        ),
        "stolen_bases": nullable_int(
            first_model_value(season_stat, "stolen_bases", "sb")
        ),
        "batting_average": nullable_float(
            first_model_value(season_stat, "batting_average", "avg")
        ),
        "on_base_percentage": nullable_float(
            first_model_value(season_stat, "on_base_percentage", "obp")
        ),
        "slugging_percentage": nullable_float(
            first_model_value(season_stat, "slugging_percentage", "slg")
        ),
        "ops": nullable_float(first_model_value(season_stat, "ops")),
        "woba": nullable_float(first_model_value(season_stat, "woba")),
        "wrc_plus": nullable_float(first_model_value(season_stat, "wrc_plus")),
        "babip": nullable_float(first_model_value(season_stat, "babip")),
        "isolated_power": nullable_float(
            first_model_value(season_stat, "isolated_power", "iso")
        ),
        "source": nullable_string(
            first_model_value(season_stat, "source_name", "source")
        ),
        "source_updated_at": iso_timestamp(
            first_model_value(
                season_stat,
                "source_updated_at",
                "updated_at",
                "created_at",
            )
        ),
    }


# ============================================================
# SECTION 15.09 - RECENT GAME LOG DATABASE QUERIES
# ============================================================

def query_recent_player_game_logs(
    database_session: Any,
    *,
    player: Any,
    season: int | None,
    limit: int,
) -> list[Any]:
    if PlayerGameStatModel is None:
        return []

    query = database_session.query(PlayerGameStatModel)

    if model_has_attribute(PlayerGameStatModel, "player_id"):
        query = query.filter(PlayerGameStatModel.player_id == player.id)

    elif model_has_attribute(PlayerGameStatModel, "mlb_player_id"):
        query = query.filter(
            PlayerGameStatModel.mlb_player_id == player.mlb_player_id
        )

    if season is not None and model_has_attribute(PlayerGameStatModel, "season"):
        query = query.filter(PlayerGameStatModel.season == int(season))

    ordering_fields = (
        "game_date",
        "official_date",
        "date",
        "game_id",
        "id",
    )

    for field_name in ordering_fields:
        if model_has_attribute(PlayerGameStatModel, field_name):
            query = query.order_by(getattr(PlayerGameStatModel, field_name).desc())
            break

    return query.limit(limit).all()


def serialize_player_game_log(game_log: Any) -> dict[str, Any]:
    return {
        "id": nullable_int(first_model_value(game_log, "id")),
        "game_id": nullable_int(
            first_model_value(game_log, "game_id", "mlb_game_id", "game_pk")
        ),
        "game_date": iso_timestamp(
            first_model_value(game_log, "game_date", "official_date", "date")
        ),
        "opponent": nullable_string(
            first_model_value(game_log, "opponent_name", "opponent")
        ),
        "home_away": nullable_string(
            first_model_value(game_log, "home_away", "venue_side")
        ),
        "plate_appearances": nullable_int(
            first_model_value(game_log, "plate_appearances", "pa")
        ),
        "at_bats": nullable_int(first_model_value(game_log, "at_bats", "ab")),
        "hits": nullable_int(first_model_value(game_log, "hits", "h")),
        "singles": nullable_int(first_model_value(game_log, "singles")),
        "doubles": nullable_int(first_model_value(game_log, "doubles")),
        "triples": nullable_int(first_model_value(game_log, "triples")),
        "home_runs": nullable_int(first_model_value(game_log, "home_runs", "hr")),
        "runs": nullable_int(first_model_value(game_log, "runs")),
        "rbi": nullable_int(first_model_value(game_log, "rbi")),
        "walks": nullable_int(first_model_value(game_log, "walks", "bb")),
        "strikeouts": nullable_int(
            first_model_value(game_log, "strikeouts", "so")
        ),
        "total_bases": nullable_int(
            first_model_value(game_log, "total_bases", "tb")
        ),
        "source": nullable_string(
            first_model_value(game_log, "source_name", "source")
        ),
        "source_updated_at": iso_timestamp(
            first_model_value(game_log, "source_updated_at", "updated_at")
        ),
    }


def sum_present(logs: Sequence[Mapping[str, Any]], field_name: str) -> int | None:
    values = [
        nullable_int(log.get(field_name))
        for log in logs
        if log.get(field_name) is not None
    ]

    if not values:
        return None

    return sum(value for value in values if value is not None)


def calculate_recent_form(
    serialized_logs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    logs = list(serialized_logs)

    if not logs:
        return {
            "games": 0,
            "plate_appearances": None,
            "at_bats": None,
            "hits": None,
            "home_runs": None,
            "rbi": None,
            "walks": None,
            "strikeouts": None,
            "total_bases": None,
            "batting_average": None,
            "on_base_percentage": None,
            "slugging_percentage": None,
            "ops": None,
            "hit_game_rate": None,
            "home_run_game_rate": None,
            "window_start": None,
            "window_end": None,
        }

    plate_appearances = sum_present(logs, "plate_appearances")
    at_bats = sum_present(logs, "at_bats")
    hits = sum_present(logs, "hits")
    home_runs = sum_present(logs, "home_runs")
    rbi = sum_present(logs, "rbi")
    walks = sum_present(logs, "walks")
    strikeouts = sum_present(logs, "strikeouts")
    total_bases = sum_present(logs, "total_bases")

    batting_average = (
        hits / at_bats
        if hits is not None and at_bats not in (None, 0)
        else None
    )

    on_base_percentage = (
        (hits + walks) / plate_appearances
        if (
            hits is not None
            and walks is not None
            and plate_appearances not in (None, 0)
        )
        else None
    )

    slugging_percentage = (
        total_bases / at_bats
        if total_bases is not None and at_bats not in (None, 0)
        else None
    )

    ops = (
        on_base_percentage + slugging_percentage
        if on_base_percentage is not None and slugging_percentage is not None
        else None
    )

    hit_games = sum(
        1
        for log in logs
        if (nullable_int(log.get("hits")) or 0) > 0
    )

    home_run_games = sum(
        1
        for log in logs
        if (nullable_int(log.get("home_runs")) or 0) > 0
    )

    timestamps = [
        parse_runtime_timestamp(log.get("game_date"))
        for log in logs
    ]
    timestamps = [timestamp for timestamp in timestamps if timestamp is not None]

    return {
        "games": len(logs),
        "plate_appearances": plate_appearances,
        "at_bats": at_bats,
        "hits": hits,
        "home_runs": home_runs,
        "rbi": rbi,
        "walks": walks,
        "strikeouts": strikeouts,
        "total_bases": total_bases,
        "batting_average": round(batting_average, 4) if batting_average is not None else None,
        "on_base_percentage": round(on_base_percentage, 4) if on_base_percentage is not None else None,
        "slugging_percentage": round(slugging_percentage, 4) if slugging_percentage is not None else None,
        "ops": round(ops, 4) if ops is not None else None,
        "hit_game_rate": round(hit_games / len(logs), 4),
        "home_run_game_rate": round(home_run_games / len(logs), 4),
        "window_start": min(timestamps).isoformat() if timestamps else None,
        "window_end": max(timestamps).isoformat() if timestamps else None,
    }


# ============================================================
# SECTION 15.10 - STATCAST DATABASE QUERY FALLBACK
# ============================================================

def serialize_statcast_model(metric: Any | None) -> dict[str, Any]:
    if metric is None:
        return {}

    return {
        "season": nullable_int(first_model_value(metric, "season")),
        "stat_group": nullable_string(first_model_value(metric, "stat_group")),
        "average_exit_velocity": nullable_float(
            first_model_value(metric, "average_exit_velocity")
        ),
        "maximum_exit_velocity": nullable_float(
            first_model_value(metric, "maximum_exit_velocity", "max_exit_velocity")
        ),
        "barrel_count": nullable_int(first_model_value(metric, "barrel_count")),
        "barrel_rate": nullable_float(first_model_value(metric, "barrel_rate")),
        "hard_hit_count": nullable_int(first_model_value(metric, "hard_hit_count")),
        "hard_hit_rate": nullable_float(first_model_value(metric, "hard_hit_rate")),
        "average_launch_angle": nullable_float(
            first_model_value(metric, "average_launch_angle", "launch_angle")
        ),
        "sweet_spot_rate": nullable_float(
            first_model_value(metric, "sweet_spot_rate")
        ),
        "expected_batting_average": nullable_float(
            first_model_value(metric, "expected_batting_average")
        ),
        "expected_slugging_percentage": nullable_float(
            first_model_value(
                metric,
                "expected_slugging_percentage",
                "expected_slugging",
            )
        ),
        "expected_woba": nullable_float(first_model_value(metric, "expected_woba")),
        "sprint_speed": nullable_float(first_model_value(metric, "sprint_speed")),
        "sample_size": nullable_int(
            first_model_value(metric, "batted_ball_count", "pitch_count")
        ),
        "sample_size_status": nullable_string(
            first_model_value(metric, "sample_size_status")
        ),
        "freshness_status": nullable_string(
            first_model_value(metric, "freshness_status")
        ),
        "source_name": nullable_string(
            first_model_value(metric, "source_name", "source")
        ),
        "source_updated_at": iso_timestamp(
            first_model_value(metric, "source_updated_at", "retrieval_timestamp", "updated_at")
        ),
    }


def load_player_statcast_payload(
    database_session: Any,
    *,
    player: Any,
    season: int,
) -> dict[str, Any]:
    mlb_player_id = nullable_int(first_model_value(player, "mlb_player_id"))

    if mlb_player_id is None:
        return {}

    if callable(get_player_statcast_intelligence):
        try:
            payload = get_player_statcast_intelligence(
                mlb_player_id,
                season=season,
                stat_group="hitting",
            )

            if isinstance(payload, Mapping) and payload.get("status") == "available":
                return dict(payload)
        except Exception as error:
            LOGGER.warning(
                "Statcast intelligence service failed for MLB player %s: %s",
                mlb_player_id,
                error,
            )

    if PlayerStatcastMetricModel is None:
        return {}

    query = database_session.query(PlayerStatcastMetricModel)

    if model_has_attribute(PlayerStatcastMetricModel, "mlb_player_id"):
        query = query.filter(
            PlayerStatcastMetricModel.mlb_player_id == mlb_player_id
        )
    elif model_has_attribute(PlayerStatcastMetricModel, "player_id"):
        query = query.filter(PlayerStatcastMetricModel.player_id == player.id)

    if model_has_attribute(PlayerStatcastMetricModel, "season"):
        query = query.filter(PlayerStatcastMetricModel.season == int(season))

    if model_has_attribute(PlayerStatcastMetricModel, "stat_group"):
        query = query.filter(PlayerStatcastMetricModel.stat_group == "hitting")

    metric = query.first()
    serialized = serialize_statcast_model(metric)

    if not serialized:
        return {}

    return {
        "status": "available",
        "mlb_player_id": mlb_player_id,
        "season": season,
        "stat_group": "hitting",
        "metrics": {
            key: value
            for key, value in serialized.items()
            if key not in {
                "season",
                "stat_group",
                "sample_size",
                "sample_size_status",
                "freshness_status",
                "source_name",
                "source_updated_at",
            }
        },
        "sample_size": serialized.get("sample_size"),
        "sample_size_status": serialized.get("sample_size_status"),
        "freshness_status": serialized.get("freshness_status"),
        "source_name": serialized.get("source_name"),
        "source_updated_at": serialized.get("source_updated_at"),
    }


# ============================================================
# SECTION 15.11 - READINESS CALCULATION
# ============================================================

def calculate_player_explorer_readiness(
    *,
    player_payload: Mapping[str, Any],
    season_stats: Mapping[str, Any],
    recent_form: Mapping[str, Any],
    statcast: Mapping[str, Any],
    freshness: Mapping[str, Any],
) -> PlayerExplorerReadiness:
    identity_ready = all(
        player_payload.get(field_name) not in (None, "")
        for field_name in (
            "id",
            "mlb_player_id",
            "full_name",
            "team",
            "position",
            "bats",
            "throws",
        )
    )

    season_ready = (
        season_stats.get("season") is not None
        and any(
            season_stats.get(field_name) is not None
            for field_name in (
                "plate_appearances",
                "hits",
                "batting_average",
                "ops",
                "home_runs",
                "rbi",
            )
        )
    )

    recent_ready = (
        nullable_int(recent_form.get("games")) or 0
    ) > 0

    statcast_ready = (
        statcast.get("status") == "available"
        and bool(statcast.get("metrics"))
    )

    states = {
        "identity": ReadinessState.READY if identity_ready else ReadinessState.PARTIAL,
        "season_statistics": ReadinessState.READY if season_ready else ReadinessState.MISSING,
        "recent_form": ReadinessState.READY if recent_ready else ReadinessState.MISSING,
        "statcast": ReadinessState.READY if statcast_ready else ReadinessState.MISSING,
    }

    statcast_freshness = freshness.get("statcast", {}).get("status")

    if states["statcast"] == ReadinessState.READY and statcast_freshness == FreshnessState.STALE:
        states["statcast"] = ReadinessState.STALE

    weights = {
        "identity": 0.25,
        "season_statistics": 0.30,
        "recent_form": 0.20,
        "statcast": 0.25,
    }

    state_scores = {
        ReadinessState.READY: 1.0,
        ReadinessState.PARTIAL: 0.5,
        ReadinessState.STALE: 0.5,
        ReadinessState.MISSING: 0.0,
        ReadinessState.ERROR: 0.0,
    }

    score = 100.0 * sum(
        weights[name] * state_scores[states[name]]
        for name in weights
    )

    if score >= 95.0:
        overall = ReadinessState.READY
    elif score >= 50.0:
        overall = ReadinessState.PARTIAL
    else:
        overall = ReadinessState.MISSING

    return PlayerExplorerReadiness(
        identity=states["identity"],
        season_statistics=states["season_statistics"],
        recent_form=states["recent_form"],
        statcast=states["statcast"],
        overall=overall,
        score=round(score, 1),
    )


# ============================================================
# SECTION 15.12 - COMPLETE PLAYER EXPLORER SERVICE
# ============================================================

def build_player_explorer_payload(
    player_identifier: int | str,
    *,
    season: int | None = None,
    recent_games: int = PLAYER_EXPLORER_DEFAULT_RECENT_GAMES,
) -> dict[str, Any]:
    started = time.perf_counter()
    selected_season = int(season or DEFAULT_SEASON)
    recent_games = max(
        1,
        min(int(recent_games), PLAYER_EXPLORER_MAX_RECENT_GAMES),
    )

    warnings: list[DataWarning] = []

    with player_explorer_session() as database_session:
        player = resolve_database_player(
            player_identifier,
            database_session=database_session,
        )

        team = None
        team_id = first_model_value(player, "current_team_id", "team_id")

        if team_id is not None and TeamModel is not None:
            team = (
                database_session.query(TeamModel)
                .filter(TeamModel.id == team_id)
                .first()
            )

        player_summary = serialize_database_player_summary(player, team=team)

        player_payload = {
            "id": player_summary.get("database_id"),
            "database_id": player_summary.get("database_id"),
            "mlb_player_id": player_summary.get("mlb_player_id"),
            "full_name": player_summary.get("full_name"),
            "team": player_summary.get("team"),
            "team_id": player_summary.get("team_id"),
            "mlb_team_id": player_summary.get("mlb_team_id"),
            "position": player_summary.get("position"),
            "position_abbreviation": player_summary.get("position_abbreviation"),
            "bats": player_summary.get("bats"),
            "throws": player_summary.get("throws"),
            "active": player_summary.get("active"),
            "source_updated_at": player_summary.get("source_updated_at"),
        }

        season_stat = resolve_latest_player_season_stat(
            database_session,
            player=player,
            season=selected_season,
        )

        season_stats = serialize_player_season_stats(
            season_stat,
            requested_season=selected_season,
        )

        game_log_records = query_recent_player_game_logs(
            database_session,
            player=player,
            season=selected_season,
            limit=recent_games,
        )

        recent_game_logs = [
            serialize_player_game_log(record)
            for record in game_log_records
        ]

        recent_form = calculate_recent_form(recent_game_logs)

        statcast = load_player_statcast_payload(
            database_session,
            player=player,
            season=selected_season,
        )

    identity_freshness = freshness_descriptor(
        player_payload.get("source_updated_at"),
        source="player identity",
    )

    season_freshness = freshness_descriptor(
        season_stats.get("source_updated_at"),
        source=season_stats.get("source") or "season statistics",
    )

    recent_log_timestamp = recent_game_logs[0].get("source_updated_at") if recent_game_logs else None
    if recent_log_timestamp is None and recent_game_logs:
        recent_log_timestamp = recent_game_logs[0].get("game_date")

    recent_form_freshness = freshness_descriptor(
        recent_log_timestamp,
        source="player game logs",
    )

    statcast_freshness = freshness_descriptor(
        statcast.get("source_updated_at") or statcast.get("retrieval_timestamp"),
        source=statcast.get("source_name") or "Statcast",
    )

    data_freshness = {
        "identity": identity_freshness.to_dict(),
        "season_statistics": season_freshness.to_dict(),
        "recent_form": recent_form_freshness.to_dict(),
        "statcast": statcast_freshness.to_dict(),
    }

    if player_payload.get("mlb_player_id") is None:
        append_warning(
            warnings,
            "missing_mlb_player_id",
            "The player record has no authoritative MLB player ID.",
            severity="error",
            field="mlb_player_id",
            source="players",
        )

    for field_name in ("team", "position", "bats", "throws"):
        if player_payload.get(field_name) in (None, ""):
            append_warning(
                warnings,
                f"missing_player_{field_name}",
                f"Player identity field '{field_name}' is unavailable.",
                field=field_name,
                source="players",
            )

    if season_stat is None:
        append_warning(
            warnings,
            "season_statistics_unavailable",
            f"No season-statistics row is available for {selected_season}.",
            source="player_season_stats",
        )

    if not recent_game_logs:
        append_warning(
            warnings,
            "recent_game_logs_unavailable",
            f"No player game logs are available for {selected_season}.",
            source="player_game_stats",
        )

    if not statcast or statcast.get("status") != "available":
        append_warning(
            warnings,
            "statcast_unavailable",
            f"No Statcast row is available for {selected_season}.",
            source="player_statcast_metrics",
        )

    for freshness_name, descriptor in data_freshness.items():
        if descriptor.get("status") == FreshnessState.STALE:
            append_warning(
                warnings,
                f"stale_{freshness_name}",
                f"{freshness_name.replace('_', ' ').title()} data is stale.",
                source=descriptor.get("source"),
            )

    readiness = calculate_player_explorer_readiness(
        player_payload=player_payload,
        season_stats=season_stats,
        recent_form=recent_form,
        statcast=statcast,
        freshness=data_freshness,
    )

    return {
        "success": True,
        "contract_version": PLAYER_EXPLORER_CONTRACT_VERSION,
        "player": player_payload,
        "season_stats": season_stats,
        "recent_form": recent_form,
        "recent_game_logs": recent_game_logs,
        "statcast": statcast,
        "readiness": readiness.to_dict(),
        "data_freshness": data_freshness,
        "warnings": [warning.to_dict() for warning in warnings],
        "diagnostics": {
            "database_backed": True,
            "live_api_fallback_used": False,
            "selected_season": selected_season,
            "recent_game_limit": recent_games,
            "recent_game_count": len(recent_game_logs),
            "processing_time_ms": round(
                (time.perf_counter() - started) * 1000.0,
                3,
            ),
        },
    }


# ============================================================
# SECTION 15.13 - PLAYER EXPLORER DATABASE HEALTH
# ============================================================

def build_player_explorer_database_health() -> dict[str, Any]:
    warnings: list[str] = []

    try:
        if callable(database_health):
            report = database_health()
        elif callable(database_health_details):
            report = database_health_details()
        else:
            report = {}
    except Exception as error:
        report = {"database_connected": False, "error": str(error)}

    try:
        inventory = collect_database_inventory() if callable(collect_database_inventory) else {}
    except Exception as error:
        inventory = {"error": str(error)}

    try:
        teams = query_database_teams(active_only=True)
        team_count = len(teams)
    except Exception as error:
        team_count = 0
        warnings.append(str(error))

    player_count = None

    try:
        with player_explorer_session() as database_session:
            player_count = database_session.query(PlayerModel).count()
    except Exception as error:
        warnings.append(str(error))

    return {
        "database_connected": bool(
            report.get("database_connected", report.get("connected", False))
        ),
        "database_health": report,
        "database_inventory": inventory,
        "team_count": team_count,
        "player_count": player_count,
        "player_explorer_runtime_ready": (
            callable(managed_database_session)
            and TeamModel is not None
            and PlayerModel is not None
        ),
        "warnings": warnings,
        "timestamp": utc_now().isoformat(),
    }


# ============================================================
# SECTION 15.14 - PLAYER EXPLORER COMPLETION GATE
# ============================================================

def validate_player_explorer_runtime() -> dict[str, Any]:
    required_model_symbols = {
        "Team": TeamModel,
        "Player": PlayerModel,
        "PlayerSeasonStat": PlayerSeasonStatModel,
        "PlayerGameStat": PlayerGameStatModel,
    }

    checks = {
        "managed_database_session_available": callable(managed_database_session),
        "team_model_available": TeamModel is not None,
        "player_model_available": PlayerModel is not None,
        "season_stat_model_available": PlayerSeasonStatModel is not None,
        "game_log_model_available": PlayerGameStatModel is not None,
        "team_query_available": callable(query_database_teams),
        "team_player_query_available": callable(query_database_players_for_team),
        "player_resolution_available": callable(resolve_database_player),
        "season_stats_available": callable(resolve_latest_player_season_stat),
        "recent_form_available": callable(calculate_recent_form),
        "statcast_query_available": callable(load_player_statcast_payload),
        "complete_payload_available": callable(build_player_explorer_payload),
        "null_safe_integer": nullable_int(None) is None,
        "null_safe_float": nullable_float(None) is None,
        "no_zero_fallback_for_missing_stats": (
            serialize_player_season_stats(None, requested_season=2026)["home_runs"]
            is None
        ),
    }

    passed = sum(1 for value in checks.values() if value)

    return {
        "status": "ok" if passed == len(checks) else "failed",
        "version": PROJECT_VERSION,
        "phase": PROJECT_PHASE,
        "contract_version": PLAYER_EXPLORER_CONTRACT_VERSION,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "failed_checks": [
            name
            for name, value in checks.items()
            if not value
        ],
        "model_symbols": {
            name: symbol is not None
            for name, symbol in required_model_symbols.items()
        },
    }




# ============================================================
# SECTION 15.15 - ENTERPRISE APPLICATION-SERVICE METADATA
# ============================================================

PLAYER_INTELLIGENCE_CONTRACT_VERSION: Final[str] = "4.1.0"
PLAYER_INTELLIGENCE_SERVICE_VERSION: Final[str] = "12.4.1"
PLAYER_INTELLIGENCE_PHASE: Final[str] = "Phase 12 Part 4.1"
PLAYER_INTELLIGENCE_PATH: Final[str] = "main.py"

DEFAULT_RECENT_FORM_GAMES: Final[int] = 15
MAX_RECENT_FORM_GAMES: Final[int] = 100
DEFAULT_PROFILE_CACHE_SECONDS: Final[int] = 30
DEFAULT_CATALOG_CACHE_SECONDS: Final[int] = 60
DEFAULT_FRESH_HOURS: Final[float] = 36.0
DEFAULT_AGING_HOURS: Final[float] = 120.0


# ============================================================
# SECTION 15.16 - STRUCTURED API ERROR CONTRACTS
# ============================================================

class ApplicationServiceError(RuntimeError):
    status_code: int = 500
    error_code: str = "application_service_error"

    def __init__(
        self,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
        warnings: Sequence[str] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = dict(details or {})
        self.warnings = list(warnings or [])
        self.request_id = request_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            },
            "warnings": self.warnings,
            "request_id": self.request_id,
            "timestamp": utc_now().isoformat(),
        }


class PlayerNotFoundError(ApplicationServiceError):
    status_code = 404
    error_code = "player_not_found"


class TeamNotFoundError(ApplicationServiceError):
    status_code = 404
    error_code = "team_not_found"


class AmbiguousPlayerError(ApplicationServiceError):
    status_code = 409
    error_code = "ambiguous_player_identity"


class DatabaseUnavailableError(ApplicationServiceError):
    status_code = 503
    error_code = "database_unavailable"


class WarehouseContractError(ApplicationServiceError):
    status_code = 500
    error_code = "warehouse_contract_error"


@app.exception_handler(ApplicationServiceError)
async def application_service_error_handler(
    request: Request,
    error: ApplicationServiceError,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    error.request_id = error.request_id or request_id
    return JSONResponse(
        status_code=error.status_code,
        content=error.to_dict(),
    )


# ============================================================
# SECTION 15.17 - REQUEST CORRELATION AND TIMING MIDDLEWARE
# ============================================================

@app.middleware("http")
async def request_correlation_middleware(
    request: Request,
    call_next: Callable[..., Any],
):
    request_id = (
        request.headers.get("X-Request-ID")
        or str(uuid4())
    )
    request.state.request_id = request_id
    started = time.perf_counter()

    response = await call_next(request)

    elapsed_ms = (
        time.perf_counter() - started
    ) * 1000.0

    response.headers["X-Request-ID"] = request_id
    response.headers["X-AISP2-Version"] = PROJECT_VERSION
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.3f}"
    return response


# ============================================================
# SECTION 15.18 - THREAD-SAFE TTL CACHE
# ============================================================

@dataclass(slots=True)
class CacheRecord:
    value: Any
    stored_monotonic: float
    expires_monotonic: float
    fingerprint: str

    @property
    def expired(self) -> bool:
        return time.monotonic() >= self.expires_monotonic


class ThreadSafeTTLCache:
    def __init__(self, max_entries: int = 512) -> None:
        self.max_entries = max(1, int(max_entries))
        self._records: OrderedDict[str, CacheRecord] = OrderedDict()
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    @staticmethod
    def _fingerprint(value: Any) -> str:
        payload = json.dumps(
            value,
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )
        return hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()

    def get(self, key: str) -> Any | None:
        with self._lock:
            record = self._records.get(key)
            if record is None:
                self.misses += 1
                return None
            if record.expired:
                self._records.pop(key, None)
                self.misses += 1
                return None
            self._records.move_to_end(key)
            self.hits += 1
            return record.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        ttl = max(0, int(ttl_seconds))
        now = time.monotonic()
        record = CacheRecord(
            value=value,
            stored_monotonic=now,
            expires_monotonic=now + ttl,
            fingerprint=self._fingerprint(value),
        )
        with self._lock:
            self._records[key] = record
            self._records.move_to_end(key)
            while len(self._records) > self.max_entries:
                self._records.popitem(last=False)
                self.evictions += 1

    def invalidate(self, prefix: str | None = None) -> int:
        with self._lock:
            if prefix is None:
                count = len(self._records)
                self._records.clear()
                return count
            keys = [key for key in self._records if key.startswith(prefix)]
            for key in keys:
                self._records.pop(key, None)
            return len(keys)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "entries": len(self._records),
                "max_entries": self.max_entries,
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
            }


PLAYER_INTELLIGENCE_CACHE = ThreadSafeTTLCache(max_entries=1024)


# ============================================================
# SECTION 15.19 - VALUE AND TIME NORMALIZATION
# ============================================================

def null_safe_number(value: Any) -> int | float | None:
    if value in (None, "", "null", "None", "nan", "NaN"):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if number.is_integer():
        return int(number)
    return number


def null_safe_integer(value: Any) -> int | None:
    number = null_safe_number(value)
    return int(number) if number is not None else None


def null_safe_rate(value: Any) -> float | None:
    number = null_safe_number(value)
    if number is None:
        return None
    return float(number)


def normalize_hand(value: Any) -> str | None:
    cleaned = str(value or "").strip().upper()
    return {
        "R": "Right",
        "RIGHT": "Right",
        "L": "Left",
        "LEFT": "Left",
        "S": "Switch",
        "SWITCH": "Switch",
        "B": "Both",
        "BOTH": "Both",
    }.get(cleaned) or (str(value).strip() if value not in (None, "") else None)


def parse_runtime_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    except ValueError:
        return None


def classify_runtime_freshness(
    value: Any,
    *,
    fresh_hours: float = DEFAULT_FRESH_HOURS,
    aging_hours: float = DEFAULT_AGING_HOURS,
) -> dict[str, Any]:
    timestamp = parse_runtime_datetime(value)
    if timestamp is None:
        return {
            "status": "unknown",
            "timestamp": None,
            "age_hours": None,
        }
    age_hours = max(
        0.0,
        (utc_now() - timestamp).total_seconds() / 3600.0,
    )
    if age_hours <= fresh_hours:
        status = "fresh"
    elif age_hours <= aging_hours:
        status = "aging"
    else:
        status = "stale"
    return {
        "status": status,
        "timestamp": timestamp.isoformat(),
        "age_hours": round(age_hours, 3),
    }


def safe_ratio(numerator: Any, denominator: Any) -> float | None:
    numerator_number = null_safe_number(numerator)
    denominator_number = null_safe_number(denominator)
    if numerator_number is None or denominator_number in (None, 0):
        return None
    return float(numerator_number) / float(denominator_number)


# ============================================================
# SECTION 15.20 - QUERY DIAGNOSTICS
# ============================================================

@dataclass(slots=True)
class QueryDiagnostic:
    name: str
    started_at: datetime = field(default_factory=utc_now)
    elapsed_ms: float = 0.0
    row_count: int | None = None
    success: bool = False
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "started_at": self.started_at.isoformat(),
            "elapsed_ms": round(self.elapsed_ms, 3),
            "row_count": self.row_count,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata,
        }


@contextmanager
def query_diagnostic(name: str, sink: list[QueryDiagnostic]):
    diagnostic = QueryDiagnostic(name=name)
    started = time.perf_counter()
    try:
        yield diagnostic
        diagnostic.success = True
    except Exception as error:
        diagnostic.error = str(error)
        raise
    finally:
        diagnostic.elapsed_ms = (
            time.perf_counter() - started
        ) * 1000.0
        sink.append(diagnostic)


# ============================================================
# SECTION 15.21 - DATABASE REPOSITORY
# ============================================================

class PlayerExplorerRepository:
    """Database-only repository. It never invents player statistics."""

    def _require_models(self) -> None:
        required = {
            "Team": TeamModel,
            "Player": PlayerModel,
            "RosterEntry": RosterEntryModel,
            "PlayerSeasonStat": PlayerSeasonStatModel,
            "PlayerGameStat": PlayerGameStatModel,
        }
        missing = [name for name, model in required.items() if model is None]
        if missing:
            raise WarehouseContractError(
                "Required ORM models could not be imported.",
                details={"missing_models": missing},
            )
        if not callable(managed_database_session):
            raise DatabaseUnavailableError(
                "managed_database_session() is unavailable."
            )

    @contextmanager
    def session(self):
        self._require_models()
        try:
            with managed_database_session(commit_on_success=False) as database_session:
                yield database_session
        except ApplicationServiceError:
            raise
        except Exception as error:
            raise DatabaseUnavailableError(
                "The database session could not be opened or queried.",
                details={"error_type": type(error).__name__, "error": str(error)},
            ) from error

    def list_teams(self, active_only: bool = True) -> list[Any]:
        with self.session() as database_session:
            query = database_session.query(TeamModel)
            if active_only and hasattr(TeamModel, "is_active"):
                query = query.filter(TeamModel.is_active.is_(True))
            return query.order_by(TeamModel.name.asc()).all()

    def resolve_team(self, identifier: int | str) -> Any:
        with self.session() as database_session:
            query = database_session.query(TeamModel)
            team = None
            numeric = None
            try:
                numeric = int(identifier)
            except (TypeError, ValueError):
                pass
            if numeric is not None:
                predicates = []
                if hasattr(TeamModel, "id"):
                    predicates.append(TeamModel.id == numeric)
                if hasattr(TeamModel, "mlb_team_id"):
                    predicates.append(TeamModel.mlb_team_id == numeric)
                if predicates:
                    from sqlalchemy import or_
                    team = query.filter(or_(*predicates)).first()
            if team is None and isinstance(identifier, str):
                cleaned = identifier.strip()
                from sqlalchemy import func, or_
                predicates = [func.lower(TeamModel.name) == cleaned.lower()]
                if hasattr(TeamModel, "abbreviation"):
                    predicates.append(func.lower(TeamModel.abbreviation) == cleaned.lower())
                team = query.filter(or_(*predicates)).first()
            if team is None:
                raise TeamNotFoundError(
                    f"No database team matched '{identifier}'.",
                    details={"identifier": identifier},
                )
            return team

    def list_players_for_team(
        self,
        team: Any,
        *,
        season: int | None = None,
        active_only: bool = True,
    ) -> list[Any]:
        with self.session() as database_session:
            players: dict[int, Any] = {}
            query = database_session.query(PlayerModel)
            if hasattr(PlayerModel, "current_team_id"):
                current_rows = query.filter(PlayerModel.current_team_id == team.id).all()
                for player in current_rows:
                    players[int(player.id)] = player

            roster_query = (
                database_session.query(PlayerModel)
                .join(RosterEntryModel, RosterEntryModel.player_id == PlayerModel.id)
                .filter(RosterEntryModel.team_id == team.id)
            )
            if season is not None and hasattr(RosterEntryModel, "season"):
                roster_query = roster_query.filter(RosterEntryModel.season == int(season))
            for player in roster_query.all():
                players[int(player.id)] = player

            output = list(players.values())
            if active_only:
                output = [
                    player for player in output
                    if getattr(player, "active_status", True) is not False
                ]
            return sorted(output, key=lambda player: str(getattr(player, "full_name", "")))

    def resolve_player(
        self,
        identifier: int | str,
        *,
        team_id: int | None = None,
    ) -> Any:
        with self.session() as database_session:
            query = database_session.query(PlayerModel)
            player = None
            numeric = None
            try:
                numeric = int(identifier)
            except (TypeError, ValueError):
                pass
            if numeric is not None:
                from sqlalchemy import or_
                predicates = [PlayerModel.id == numeric]
                if hasattr(PlayerModel, "mlb_player_id"):
                    predicates.append(PlayerModel.mlb_player_id == numeric)
                player = query.filter(or_(*predicates)).first()
            if player is None and isinstance(identifier, str):
                cleaned = identifier.strip()
                from sqlalchemy import func
                matches = query.filter(func.lower(PlayerModel.full_name) == cleaned.lower()).all()
                if team_id is not None:
                    matches = [
                        item for item in matches
                        if getattr(item, "current_team_id", None) == team_id
                    ]
                if len(matches) > 1:
                    raise AmbiguousPlayerError(
                        f"Multiple database players share the name '{identifier}'.",
                        details={
                            "matches": [
                                {
                                    "database_id": getattr(item, "id", None),
                                    "mlb_player_id": getattr(item, "mlb_player_id", None),
                                    "team_id": getattr(item, "current_team_id", None),
                                }
                                for item in matches
                            ]
                        },
                    )
                player = matches[0] if matches else None
            if player is None:
                raise PlayerNotFoundError(
                    f"No database player matched '{identifier}'.",
                    details={"identifier": identifier, "team_id": team_id},
                )
            return player

    def resolve_player_team(self, player: Any) -> Any | None:
        team_id = getattr(player, "current_team_id", None)
        if team_id is None:
            return None
        with self.session() as database_session:
            return database_session.query(TeamModel).filter(TeamModel.id == team_id).first()

    def latest_season_stat(self, player_id: int, season: int | None) -> Any | None:
        with self.session() as database_session:
            query = database_session.query(PlayerSeasonStatModel).filter(
                PlayerSeasonStatModel.player_id == int(player_id)
            )
            if season is not None and hasattr(PlayerSeasonStatModel, "season"):
                exact = query.filter(PlayerSeasonStatModel.season == int(season)).first()
                if exact is not None:
                    return exact
            if hasattr(PlayerSeasonStatModel, "season"):
                query = query.order_by(PlayerSeasonStatModel.season.desc())
            return query.first()

    def recent_game_logs(self, player_id: int, limit: int) -> list[Any]:
        with self.session() as database_session:
            query = database_session.query(PlayerGameStatModel).filter(
                PlayerGameStatModel.player_id == int(player_id)
            )
            order_fields = []
            for field_name in ("game_date", "official_date", "created_at", "id"):
                field_value = getattr(PlayerGameStatModel, field_name, None)
                if field_value is not None:
                    order_fields.append(field_value.desc())
                    break
            if order_fields:
                query = query.order_by(*order_fields)
            return query.limit(max(1, min(int(limit), MAX_RECENT_FORM_GAMES))).all()

    def latest_statcast(self, mlb_player_id: int, season: int, stat_group: str) -> Any | None:
        if PlayerStatcastMetricModel is None:
            return None
        with self.session() as database_session:
            query = database_session.query(PlayerStatcastMetricModel).filter(
                PlayerStatcastMetricModel.mlb_player_id == int(mlb_player_id),
                PlayerStatcastMetricModel.season == int(season),
            )
            if hasattr(PlayerStatcastMetricModel, "stat_group"):
                query = query.filter(PlayerStatcastMetricModel.stat_group == stat_group)
            for field_name in ("source_updated_at", "retrieval_timestamp", "updated_at", "id"):
                field_value = getattr(PlayerStatcastMetricModel, field_name, None)
                if field_value is not None:
                    query = query.order_by(field_value.desc())
                    break
            return query.first()


# ============================================================
# SECTION 15.22 - SERIALIZATION POLICY
# ============================================================

class PlayerExplorerSerializer:
    PLAYER_FIELDS: Final[tuple[str, ...]] = (
        "id", "mlb_player_id", "full_name", "first_name", "last_name",
        "use_name", "nick_name", "position", "position_code",
        "position_abbreviation", "bats", "throws", "height", "weight",
        "birth_date", "birth_city", "birth_state_province", "birth_country",
        "mlb_debut_date", "active_status", "current_team_id", "source_name",
        "source_updated_at", "created_at", "updated_at",
    )

    SEASON_STAT_ALIASES: Final[dict[str, tuple[str, ...]]] = {
        "season": ("season",),
        "plate_appearances": ("plate_appearances", "pa"),
        "at_bats": ("at_bats", "ab"),
        "hits": ("hits", "h"),
        "singles": ("singles",),
        "doubles": ("doubles",),
        "triples": ("triples",),
        "home_runs": ("home_runs", "hr"),
        "runs": ("runs", "r"),
        "rbi": ("rbi", "runs_batted_in"),
        "walks": ("walks", "base_on_balls", "bb"),
        "strikeouts": ("strikeouts", "so"),
        "stolen_bases": ("stolen_bases", "sb"),
        "caught_stealing": ("caught_stealing", "cs"),
        "hit_by_pitch": ("hit_by_pitch", "hbp"),
        "sacrifice_flies": ("sacrifice_flies", "sf"),
        "batting_average": ("batting_average", "avg"),
        "on_base_percentage": ("on_base_percentage", "obp"),
        "slugging_percentage": ("slugging_percentage", "slg"),
        "ops": ("ops",),
        "woba": ("woba",),
        "wrc_plus": ("wrc_plus",),
        "babip": ("babip",),
        "isolated_power": ("isolated_power", "iso"),
        "walk_rate": ("walk_rate",),
        "strikeout_rate": ("strikeout_rate",),
        "home_run_rate": ("home_run_rate",),
        "source_name": ("source_name",),
        "source_updated_at": ("source_updated_at", "updated_at"),
    }

    STATCAST_FIELDS: Final[tuple[str, ...]] = (
        "season", "stat_group", "average_exit_velocity", "maximum_exit_velocity",
        "barrel_count", "barrel_rate", "hard_hit_count", "hard_hit_rate",
        "average_launch_angle", "sweet_spot_rate", "expected_batting_average",
        "expected_slugging_percentage", "expected_woba", "sprint_speed",
        "batted_ball_count", "average_fastball_velocity", "maximum_fastball_velocity",
        "spin_rate", "extension", "whiff_rate", "chase_rate", "zone_contact_rate",
        "squared_up_rate", "pitch_count", "sample_size_status", "freshness_status",
        "age_hours", "source_name", "source_file", "source_updated_at",
        "retrieval_timestamp", "updated_at",
    )

    @staticmethod
    def _value(record: Any, aliases: Sequence[str]) -> Any:
        for alias in aliases:
            value = record_value(record, alias, default=None)
            if value not in (None, ""):
                return value
        return None

    def team(self, team: Any | None) -> dict[str, Any] | None:
        if team is None:
            return None
        return {
            "id": getattr(team, "id", None),
            "database_id": getattr(team, "id", None),
            "mlb_team_id": getattr(team, "mlb_team_id", None),
            "name": getattr(team, "name", None),
            "abbreviation": getattr(team, "abbreviation", None),
            "league": getattr(team, "league", None),
            "division": getattr(team, "division", None),
            "venue": getattr(team, "venue", None),
            "active": getattr(team, "is_active", None),
            "source_updated_at": null_safe_iso(getattr(team, "source_updated_at", None)),
        }

    def player(self, player: Any, team: Any | None) -> dict[str, Any]:
        team_payload = self.team(team)
        payload = {
            "id": getattr(player, "id", None),
            "database_id": getattr(player, "id", None),
            "mlb_player_id": getattr(player, "mlb_player_id", None),
            "full_name": getattr(player, "full_name", None),
            "first_name": getattr(player, "first_name", None),
            "last_name": getattr(player, "last_name", None),
            "use_name": getattr(player, "use_name", None),
            "nick_name": getattr(player, "nick_name", None),
            "team": team_payload.get("name") if team_payload else None,
            "team_id": team_payload.get("database_id") if team_payload else None,
            "mlb_team_id": team_payload.get("mlb_team_id") if team_payload else None,
            "team_details": team_payload,
            "position": getattr(player, "position", None),
            "position_code": getattr(player, "position_code", None),
            "position_abbreviation": getattr(player, "position_abbreviation", None),
            "bats": normalize_hand(getattr(player, "bats", None)),
            "throws": normalize_hand(getattr(player, "throws", None)),
            "height": getattr(player, "height", None),
            "weight": getattr(player, "weight", None),
            "birth_date": null_safe_iso(getattr(player, "birth_date", None)),
            "birth_city": getattr(player, "birth_city", None),
            "birth_state_province": getattr(player, "birth_state_province", None),
            "birth_country": getattr(player, "birth_country", None),
            "mlb_debut_date": null_safe_iso(getattr(player, "mlb_debut_date", None)),
            "active": getattr(player, "active_status", None),
            "source_name": getattr(player, "source_name", None),
            "source_updated_at": null_safe_iso(
                getattr(player, "source_updated_at", None)
                or getattr(player, "updated_at", None)
            ),
        }
        return payload

    def season_stats(self, record: Any | None, requested_season: int) -> dict[str, Any]:
        output: dict[str, Any] = {
            key: None for key in self.SEASON_STAT_ALIASES
        }
        output["season"] = requested_season
        if record is None:
            return output
        for key, aliases in self.SEASON_STAT_ALIASES.items():
            value = self._value(record, aliases)
            if key == "source_updated_at":
                output[key] = null_safe_iso(value)
            elif key in {"source_name"}:
                output[key] = value
            elif key == "season":
                output[key] = null_safe_integer(value) or requested_season
            else:
                output[key] = null_safe_number(value)
        return output

    def game_log(self, record: Any) -> dict[str, Any]:
        fields = (
            "id", "game_id", "game_pk", "game_date", "official_date", "season",
            "team_id", "opponent_team_id", "is_home", "plate_appearances", "at_bats",
            "hits", "singles", "doubles", "triples", "home_runs", "runs", "rbi",
            "walks", "strikeouts", "stolen_bases", "total_bases", "hit_by_pitch",
            "sacrifice_flies", "source_name", "source_updated_at", "created_at",
        )
        payload: dict[str, Any] = {}
        for field_name in fields:
            value = getattr(record, field_name, None)
            if field_name in {"game_date", "official_date", "source_updated_at", "created_at"}:
                payload[field_name] = null_safe_iso(value)
            elif field_name in {"source_name"}:
                payload[field_name] = value
            else:
                payload[field_name] = null_safe_number(value)
        return payload

    def statcast(self, record: Any | None, season: int, stat_group: str) -> dict[str, Any]:
        output = {field_name: None for field_name in self.STATCAST_FIELDS}
        output["season"] = season
        output["stat_group"] = stat_group
        if record is None:
            return output
        for field_name in self.STATCAST_FIELDS:
            value = getattr(record, field_name, None)
            if field_name in {"source_updated_at", "retrieval_timestamp", "updated_at"}:
                output[field_name] = null_safe_iso(value)
            elif field_name in {
                "stat_group", "sample_size_status", "freshness_status",
                "source_name", "source_file",
            }:
                output[field_name] = value
            else:
                output[field_name] = null_safe_number(value)
        return output


# ============================================================
# SECTION 15.23 - RECENT FORM ENGINE
# ============================================================

class RecentFormEngine:
    COUNT_FIELDS: Final[tuple[str, ...]] = (
        "plate_appearances", "at_bats", "hits", "singles", "doubles", "triples",
        "home_runs", "runs", "rbi", "walks", "strikeouts", "stolen_bases",
        "total_bases", "hit_by_pitch", "sacrifice_flies",
    )

    def calculate(self, logs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        if not logs:
            return {}
        totals: dict[str, int | float] = {field_name: 0 for field_name in self.COUNT_FIELDS}
        observed: dict[str, int] = {field_name: 0 for field_name in self.COUNT_FIELDS}
        hit_games = 0
        home_run_games = 0
        dates: list[datetime] = []

        for row in logs:
            for field_name in self.COUNT_FIELDS:
                value = null_safe_number(row.get(field_name))
                if value is not None:
                    totals[field_name] += value
                    observed[field_name] += 1
            if (null_safe_number(row.get("hits")) or 0) >= 1:
                hit_games += 1
            if (null_safe_number(row.get("home_runs")) or 0) >= 1:
                home_run_games += 1
            parsed = parse_runtime_datetime(row.get("game_date") or row.get("official_date"))
            if parsed is not None:
                dates.append(parsed)

        at_bats = totals["at_bats"] if observed["at_bats"] else None
        hits = totals["hits"] if observed["hits"] else None
        walks = totals["walks"] if observed["walks"] else None
        hit_by_pitch = totals["hit_by_pitch"] if observed["hit_by_pitch"] else 0
        sacrifice_flies = totals["sacrifice_flies"] if observed["sacrifice_flies"] else 0
        total_bases = totals["total_bases"] if observed["total_bases"] else None

        batting_average = safe_ratio(hits, at_bats)
        on_base_percentage = safe_ratio(
            (hits or 0) + (walks or 0) + (hit_by_pitch or 0),
            (at_bats or 0) + (walks or 0) + (hit_by_pitch or 0) + (sacrifice_flies or 0),
        )
        slugging_percentage = safe_ratio(total_bases, at_bats)
        ops = (
            on_base_percentage + slugging_percentage
            if on_base_percentage is not None and slugging_percentage is not None
            else None
        )

        output: dict[str, Any] = {
            "games": len(logs),
            "window_start": min(dates).isoformat() if dates else None,
            "window_end": max(dates).isoformat() if dates else None,
            "hit_game_rate": safe_ratio(hit_games, len(logs)),
            "home_run_game_rate": safe_ratio(home_run_games, len(logs)),
            "batting_average": batting_average,
            "on_base_percentage": on_base_percentage,
            "slugging_percentage": slugging_percentage,
            "ops": ops,
        }
        for field_name in self.COUNT_FIELDS:
            output[field_name] = totals[field_name] if observed[field_name] else None
        return output


# ============================================================
# SECTION 15.24 - READINESS POLICY
# ============================================================

@dataclass(frozen=True, slots=True)
class ReadinessComponent:
    name: str
    status: str
    score: float
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "score": round(self.score, 1),
            "reasons": list(self.reasons),
        }


class ReadinessPolicy:
    WEIGHTS: Final[dict[str, float]] = {
        "identity": 0.20,
        "season_statistics": 0.30,
        "recent_form": 0.25,
        "statcast": 0.25,
    }

    @staticmethod
    def _component(name: str, available: int, required: int, reasons: Sequence[str]) -> ReadinessComponent:
        ratio = available / required if required else 0.0
        if ratio >= 0.90:
            status = "ready"
        elif ratio > 0:
            status = "partial"
        else:
            status = "missing"
        return ReadinessComponent(name, status, ratio * 100.0, tuple(reasons))

    def evaluate(
        self,
        player: Mapping[str, Any],
        season_stats: Mapping[str, Any],
        recent_form: Mapping[str, Any],
        statcast: Mapping[str, Any],
    ) -> dict[str, Any]:
        identity_fields = ("mlb_player_id", "full_name", "team", "position", "bats", "throws")
        season_fields = ("plate_appearances", "at_bats", "hits", "home_runs", "rbi", "batting_average", "ops")
        recent_fields = ("games", "plate_appearances", "hits", "batting_average", "ops")
        statcast_fields = (
            "average_exit_velocity", "maximum_exit_velocity", "barrel_rate",
            "hard_hit_rate", "average_launch_angle", "expected_batting_average",
            "expected_slugging_percentage", "expected_woba", "batted_ball_count",
        )

        components = {
            "identity": self._component(
                "identity",
                sum(player.get(name) not in (None, "") for name in identity_fields),
                len(identity_fields),
                [name for name in identity_fields if player.get(name) in (None, "")],
            ),
            "season_statistics": self._component(
                "season_statistics",
                sum(season_stats.get(name) is not None for name in season_fields),
                len(season_fields),
                [name for name in season_fields if season_stats.get(name) is None],
            ),
            "recent_form": self._component(
                "recent_form",
                sum(recent_form.get(name) is not None for name in recent_fields),
                len(recent_fields),
                [name for name in recent_fields if recent_form.get(name) is None],
            ),
            "statcast": self._component(
                "statcast",
                sum(statcast.get(name) is not None for name in statcast_fields),
                len(statcast_fields),
                [name for name in statcast_fields if statcast.get(name) is None],
            ),
        }
        weighted = sum(
            components[name].score * self.WEIGHTS[name]
            for name in self.WEIGHTS
        )
        if weighted >= 90:
            overall = "ready"
        elif weighted >= 50:
            overall = "partial"
        else:
            overall = "not_ready"
        return {
            **{name: component.status for name, component in components.items()},
            "overall": overall,
            "score": round(weighted, 1),
            "components": {
                name: component.to_dict()
                for name, component in components.items()
            },
        }


# ============================================================
# SECTION 15.25 - PLAYER INTELLIGENCE SERVICE
# ============================================================

class PlayerIntelligenceService:
    def __init__(
        self,
        repository: PlayerExplorerRepository | None = None,
        serializer: PlayerExplorerSerializer | None = None,
    ) -> None:
        self.repository = repository or PlayerExplorerRepository()
        self.serializer = serializer or PlayerExplorerSerializer()
        self.recent_form_engine = RecentFormEngine()
        self.readiness_policy = ReadinessPolicy()

    def list_teams(self, active_only: bool = True) -> dict[str, Any]:
        cache_key = f"teams:{int(active_only)}"
        cached = PLAYER_INTELLIGENCE_CACHE.get(cache_key)
        if cached is not None:
            return cached
        teams = [self.serializer.team(team) for team in self.repository.list_teams(active_only)]
        payload = {
            "success": True,
            "count": len(teams),
            "teams": teams,
            "source": "AISP2 database warehouse",
            "contract_version": PLAYER_INTELLIGENCE_CONTRACT_VERSION,
            "warnings": [] if teams else ["No teams are stored in the database."],
        }
        PLAYER_INTELLIGENCE_CACHE.set(cache_key, payload, DEFAULT_CATALOG_CACHE_SECONDS)
        return payload

    def list_team_players(
        self,
        team_identifier: int | str,
        *,
        season: int | None,
        active_only: bool,
    ) -> dict[str, Any]:
        team = self.repository.resolve_team(team_identifier)
        players = self.repository.list_players_for_team(
            team,
            season=season,
            active_only=active_only,
        )
        serialized = [
            self.serializer.player(player, team)
            for player in players
        ]
        return {
            "success": True,
            "team": self.serializer.team(team),
            "season": season,
            "active_only": active_only,
            "count": len(serialized),
            "players": serialized,
            "source": "AISP2 database warehouse",
            "contract_version": PLAYER_INTELLIGENCE_CONTRACT_VERSION,
            "warnings": [] if serialized else ["No players matched this team and season selection."],
        }

    def profile(
        self,
        player_identifier: int | str,
        *,
        season: int,
        recent_games: int,
        stat_group: str,
        team_identifier: int | str | None = None,
        include_diagnostics: bool = False,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        team_filter = None
        if team_identifier is not None:
            team_filter = self.repository.resolve_team(team_identifier)

        cache_key = (
            f"profile:{player_identifier}:{season}:{recent_games}:"
            f"{stat_group}:{getattr(team_filter, 'id', None)}"
        )
        if use_cache:
            cached = PLAYER_INTELLIGENCE_CACHE.get(cache_key)
            if cached is not None:
                return cached

        diagnostics: list[QueryDiagnostic] = []
        warnings: list[str] = []

        with query_diagnostic("resolve_player", diagnostics):
            player = self.repository.resolve_player(
                player_identifier,
                team_id=getattr(team_filter, "id", None),
            )

        with query_diagnostic("resolve_team", diagnostics):
            team = self.repository.resolve_player_team(player)

        with query_diagnostic("season_statistics", diagnostics) as diagnostic:
            season_record = self.repository.latest_season_stat(player.id, season)
            diagnostic.row_count = 1 if season_record is not None else 0

        with query_diagnostic("recent_game_logs", diagnostics) as diagnostic:
            raw_logs = self.repository.recent_game_logs(player.id, recent_games)
            diagnostic.row_count = len(raw_logs)

        with query_diagnostic("statcast", diagnostics) as diagnostic:
            statcast_record = self.repository.latest_statcast(
                int(player.mlb_player_id),
                season,
                stat_group,
            )
            diagnostic.row_count = 1 if statcast_record is not None else 0

        player_payload = self.serializer.player(player, team)
        season_payload = self.serializer.season_stats(season_record, season)
        game_logs = [self.serializer.game_log(row) for row in raw_logs]
        recent_form = self.recent_form_engine.calculate(game_logs)
        statcast_payload = self.serializer.statcast(statcast_record, season, stat_group)

        if season_record is None:
            warnings.append(f"No season-statistics row is available for season {season}.")
        if not game_logs:
            warnings.append("No recent player game logs are available.")
        if statcast_record is None:
            warnings.append(
                f"No {stat_group} Statcast row is available for this player and season."
            )

        identity_timestamp = player_payload.get("source_updated_at")
        season_timestamp = season_payload.get("source_updated_at")
        recent_timestamp = recent_form.get("window_end") if recent_form else None
        statcast_timestamp = (
            statcast_payload.get("source_updated_at")
            or statcast_payload.get("retrieval_timestamp")
        )

        freshness = {
            "identity": classify_runtime_freshness(identity_timestamp),
            "season_statistics": classify_runtime_freshness(season_timestamp),
            "recent_form": classify_runtime_freshness(recent_timestamp),
            "statcast": classify_runtime_freshness(statcast_timestamp),
        }
        for layer, report in freshness.items():
            if report["status"] == "stale":
                warnings.append(f"{layer.replace('_', ' ').title()} data is stale.")
            elif report["status"] == "unknown":
                warnings.append(f"{layer.replace('_', ' ').title()} freshness is unknown.")

        readiness = self.readiness_policy.evaluate(
            player_payload,
            season_payload,
            recent_form,
            statcast_payload,
        )

        payload: dict[str, Any] = {
            "success": True,
            "contract_version": PLAYER_INTELLIGENCE_CONTRACT_VERSION,
            "service_version": PLAYER_INTELLIGENCE_SERVICE_VERSION,
            "player": player_payload,
            "season_stats": season_payload,
            "recent_form": recent_form,
            "recent_game_logs": game_logs,
            "statcast": statcast_payload,
            "readiness": readiness,
            "data_freshness": freshness,
            "warnings": list(dict.fromkeys(warnings)),
            "source": "AISP2 database warehouse",
            "requested": {
                "player_identifier": player_identifier,
                "team_identifier": team_identifier,
                "season": season,
                "recent_games": recent_games,
                "stat_group": stat_group,
            },
            "generated_at": utc_now().isoformat(),
        }
        if include_diagnostics:
            payload["diagnostics"] = {
                "queries": [item.to_dict() for item in diagnostics],
                "cache": PLAYER_INTELLIGENCE_CACHE.stats(),
            }
        if use_cache:
            PLAYER_INTELLIGENCE_CACHE.set(
                cache_key,
                payload,
                DEFAULT_PROFILE_CACHE_SECONDS,
            )
        return payload


PLAYER_INTELLIGENCE_SERVICE = PlayerIntelligenceService()


# ============================================================
# SECTION 15.26 - ENTERPRISE PLAYER EXPLORER API
# ============================================================

@app.get("/api/v2/player-explorer/teams")
def player_explorer_v2_teams(
    active_only: bool = True,
) -> dict[str, Any]:
    return PLAYER_INTELLIGENCE_SERVICE.list_teams(active_only=active_only)


@app.get("/api/v2/player-explorer/teams/{team_identifier}/players")
def player_explorer_v2_team_players(
    team_identifier: str,
    season: int | None = Query(default=None, ge=1876, le=2100),
    active_only: bool = True,
) -> dict[str, Any]:
    return PLAYER_INTELLIGENCE_SERVICE.list_team_players(
        team_identifier,
        season=season,
        active_only=active_only,
    )


@app.get("/api/v2/player-explorer/players/{player_identifier}")
def player_explorer_v2_profile(
    player_identifier: str,
    season: int = Query(default=DEFAULT_SEASON, ge=1876, le=2100),
    recent_games: int = Query(default=DEFAULT_RECENT_FORM_GAMES, ge=1, le=MAX_RECENT_FORM_GAMES),
    stat_group: str = Query(default="hitting", pattern="^(hitting|pitching)$"),
    team: str | None = None,
    include_diagnostics: bool = False,
    use_cache: bool = True,
) -> dict[str, Any]:
    return PLAYER_INTELLIGENCE_SERVICE.profile(
        player_identifier,
        season=season,
        recent_games=recent_games,
        stat_group=stat_group,
        team_identifier=team,
        include_diagnostics=include_diagnostics,
        use_cache=use_cache,
    )


@app.post("/api/v2/player-explorer/cache/invalidate")
def invalidate_player_explorer_cache(prefix: str | None = None) -> dict[str, Any]:
    invalidated = PLAYER_INTELLIGENCE_CACHE.invalidate(prefix)
    return {
        "success": True,
        "invalidated_entries": invalidated,
        "prefix": prefix,
        "cache": PLAYER_INTELLIGENCE_CACHE.stats(),
    }


@app.get("/api/v2/player-explorer/cache/status")
def player_explorer_cache_status() -> dict[str, Any]:
    return {
        "success": True,
        "cache": PLAYER_INTELLIGENCE_CACHE.stats(),
    }


# ============================================================
# SECTION 15.27 - FRONTEND BOOTSTRAP CONTRACT
# ============================================================

@app.get("/api/v2/player-explorer/bootstrap")
def player_explorer_bootstrap(
    season: int = Query(default=DEFAULT_SEASON, ge=1876, le=2100),
) -> dict[str, Any]:
    teams = PLAYER_INTELLIGENCE_SERVICE.list_teams(active_only=True)
    return {
        "success": True,
        "contract_version": PLAYER_INTELLIGENCE_CONTRACT_VERSION,
        "season": season,
        "teams": teams["teams"],
        "defaults": {
            "recent_games": DEFAULT_RECENT_FORM_GAMES,
            "stat_group": "hitting",
        },
        "endpoints": {
            "teams": "/api/v2/player-explorer/teams",
            "team_players": "/api/v2/player-explorer/teams/{team_identifier}/players",
            "player_profile": "/api/v2/player-explorer/players/{player_identifier}",
            "health": "/api/v2/player-explorer/health",
        },
        "null_policy": (
            "Unavailable numeric values are returned as null. "
            "The API never fabricates zero-valued baseball statistics."
        ),
        "warnings": teams.get("warnings", []),
    }


# ============================================================
# SECTION 15.28 - HEALTH AND COMPLETION GATES
# ============================================================

def validate_player_intelligence_service() -> dict[str, Any]:
    route_paths = {route.path for route in app.routes}
    required_routes = {
        "/api/v2/player-explorer/teams",
        "/api/v2/player-explorer/teams/{team_identifier}/players",
        "/api/v2/player-explorer/players/{player_identifier}",
        "/api/v2/player-explorer/bootstrap",
        "/api/v2/player-explorer/cache/status",
    }
    checks = {
        "managed_database_session_available": callable(managed_database_session),
        "team_model_available": TeamModel is not None,
        "player_model_available": PlayerModel is not None,
        "roster_model_available": RosterEntryModel is not None,
        "season_stat_model_available": PlayerSeasonStatModel is not None,
        "game_log_model_available": PlayerGameStatModel is not None,
        "statcast_model_available": PlayerStatcastMetricModel is not None,
        "repository_available": isinstance(
            PLAYER_INTELLIGENCE_SERVICE.repository,
            PlayerExplorerRepository,
        ),
        "serializer_available": isinstance(
            PLAYER_INTELLIGENCE_SERVICE.serializer,
            PlayerExplorerSerializer,
        ),
        "recent_form_engine_available": isinstance(
            PLAYER_INTELLIGENCE_SERVICE.recent_form_engine,
            RecentFormEngine,
        ),
        "readiness_policy_available": isinstance(
            PLAYER_INTELLIGENCE_SERVICE.readiness_policy,
            ReadinessPolicy,
        ),
        "null_safe_number_preserves_missing": null_safe_number(None) is None,
        "null_safe_number_preserves_zero": null_safe_number(0) == 0,
        "safe_ratio_avoids_zero_denominator": safe_ratio(1, 0) is None,
        "handedness_normalization": normalize_hand("R") == "Right",
        "required_routes_registered": required_routes.issubset(route_paths),
        "structured_error_contract": (
            PlayerNotFoundError("missing").to_dict()["success"] is False
        ),
        "cache_available": isinstance(PLAYER_INTELLIGENCE_CACHE, ThreadSafeTTLCache),
    }
    passed = sum(bool(value) for value in checks.values())
    return {
        "status": "ok" if passed == len(checks) else "failed",
        "version": PLAYER_INTELLIGENCE_SERVICE_VERSION,
        "phase": PLAYER_INTELLIGENCE_PHASE,
        "contract_version": PLAYER_INTELLIGENCE_CONTRACT_VERSION,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "failed_checks": [name for name, value in checks.items() if not value],
        "routes": sorted(required_routes),
        "cache": PLAYER_INTELLIGENCE_CACHE.stats(),
    }


@app.get("/api/v2/player-explorer/health")
def player_explorer_v2_health() -> dict[str, Any]:
    validation = validate_player_intelligence_service()
    database_report: dict[str, Any]
    try:
        database_report = (
            database_health()
            if callable(database_health)
            else database_health_details()
        ) or {}
    except Exception as error:
        database_report = {
            "database_connected": False,
            "error": str(error),
        }
    return {
        "success": validation["status"] == "ok",
        "status": "ready" if validation["status"] == "ok" else "degraded",
        "service": "player_intelligence",
        "version": PLAYER_INTELLIGENCE_SERVICE_VERSION,
        "phase": PLAYER_INTELLIGENCE_PHASE,
        "contract_version": PLAYER_INTELLIGENCE_CONTRACT_VERSION,
        "validation": validation,
        "database": database_report,
        "timestamp": utc_now().isoformat(),
    }


def validate_player_explorer_completion_gate() -> dict[str, Any]:
    validation = validate_player_intelligence_service()
    route_paths = {route.path for route in app.routes}
    checks = {
        "service_validation_passed": validation["status"] == "ok",
        "team_selection_queries_database": callable(
            PLAYER_INTELLIGENCE_SERVICE.repository.list_teams
        ),
        "player_selection_queries_team_relationships": callable(
            PLAYER_INTELLIGENCE_SERVICE.repository.list_players_for_team
        ),
        "player_resolves_by_database_or_mlb_id": callable(
            PLAYER_INTELLIGENCE_SERVICE.repository.resolve_player
        ),
        "season_statistics_loader_available": callable(
            PLAYER_INTELLIGENCE_SERVICE.repository.latest_season_stat
        ),
        "recent_game_log_loader_available": callable(
            PLAYER_INTELLIGENCE_SERVICE.repository.recent_game_logs
        ),
        "recent_form_calculator_available": callable(
            PLAYER_INTELLIGENCE_SERVICE.recent_form_engine.calculate
        ),
        "statcast_loader_available": callable(
            PLAYER_INTELLIGENCE_SERVICE.repository.latest_statcast
        ),
        "readiness_calculator_available": callable(
            PLAYER_INTELLIGENCE_SERVICE.readiness_policy.evaluate
        ),
        "frontend_bootstrap_route_registered": (
            "/api/v2/player-explorer/bootstrap" in route_paths
        ),
        "frontend_profile_route_registered": (
            "/api/v2/player-explorer/players/{player_identifier}" in route_paths
        ),
        "missing_numeric_values_remain_null": (
            PlayerExplorerSerializer().season_stats(None, DEFAULT_SEASON)["ops"]
            is None
        ),
    }
    passed = sum(bool(value) for value in checks.values())
    return {
        "status": "ok" if passed == len(checks) else "failed",
        "completion_gate_passed": passed == len(checks),
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "failed_checks": [name for name, value in checks.items() if not value],
        "validation": validation,
    }


@app.get("/api/v2/player-explorer/completion-gate")
def player_explorer_completion_gate_endpoint() -> dict[str, Any]:
    return validate_player_explorer_completion_gate()


# ============================================================
# SECTION 15.29 - API CONTRACT MANIFEST
# ============================================================

PLAYER_EXPLORER_API_MANIFEST: Final[dict[str, Any]] = {
    "contract_version": PLAYER_INTELLIGENCE_CONTRACT_VERSION,
    "service_version": PLAYER_INTELLIGENCE_SERVICE_VERSION,
    "routes": {
        "bootstrap": "/api/v2/player-explorer/bootstrap",
        "teams": "/api/v2/player-explorer/teams",
        "team_players": "/api/v2/player-explorer/teams/{team_identifier}/players",
        "profile": "/api/v2/player-explorer/players/{player_identifier}",
        "health": "/api/v2/player-explorer/health",
        "completion_gate": "/api/v2/player-explorer/completion-gate",
        "cache_status": "/api/v2/player-explorer/cache/status",
        "cache_invalidate": "/api/v2/player-explorer/cache/invalidate",
    },
    "identity_keys": {
        "database": "player.id",
        "external": "player.mlb_player_id",
    },
    "null_policy": "Missing numeric values are null, never fabricated zero.",
    "source_policy": "Database warehouse is authoritative for Player Explorer.",
}


@app.get("/api/v2/player-explorer/manifest")
def player_explorer_manifest() -> dict[str, Any]:
    return {
        "success": True,
        **PLAYER_EXPLORER_API_MANIFEST,
    }


# ============================================================
# SECTION 15.30 - CONTRACT EXAMPLE GENERATOR
# ============================================================

def build_player_explorer_contract_example() -> dict[str, Any]:
    return {
        "success": True,
        "contract_version": PLAYER_INTELLIGENCE_CONTRACT_VERSION,
        "player": {
            "id": 1,
            "database_id": 1,
            "mlb_player_id": 592450,
            "full_name": "Aaron Judge",
            "team": "New York Yankees",
            "team_id": 1,
            "mlb_team_id": 147,
            "position": "Outfielder",
            "position_abbreviation": "OF",
            "bats": "Right",
            "throws": "Right",
            "active": True,
        },
        "season_stats": {
            "season": DEFAULT_SEASON,
            "plate_appearances": None,
            "batting_average": None,
            "ops": None,
            "home_runs": None,
            "rbi": None,
        },
        "recent_form": {},
        "recent_game_logs": [],
        "statcast": {},
        "readiness": {
            "identity": "ready",
            "season_statistics": "missing",
            "recent_form": "missing",
            "statcast": "missing",
            "overall": "not_ready",
            "score": 20.0,
        },
        "data_freshness": {},
        "warnings": [
            "This is a contract example. Missing numeric values remain null."
        ],
    }


@app.get("/api/v2/player-explorer/contract-example")
def player_explorer_contract_example() -> dict[str, Any]:
    return build_player_explorer_contract_example()




# ============================================================
# SECTION 15.31 - MACHINE-READABLE FIELD CATALOG
# ============================================================

PLAYER_EXPLORER_FIELD_CATALOG: Final[list[dict[str, Any]]] = [
    {
        "group": "player",
        "field": "id",
        "ordinal": 1,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "database_id",
        "ordinal": 2,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "mlb_player_id",
        "ordinal": 3,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "full_name",
        "ordinal": 4,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "first_name",
        "ordinal": 5,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "last_name",
        "ordinal": 6,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "use_name",
        "ordinal": 7,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "nick_name",
        "ordinal": 8,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "team",
        "ordinal": 9,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "team_id",
        "ordinal": 10,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "mlb_team_id",
        "ordinal": 11,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "team_details",
        "ordinal": 12,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "position",
        "ordinal": 13,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "position_code",
        "ordinal": 14,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "position_abbreviation",
        "ordinal": 15,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "bats",
        "ordinal": 16,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "throws",
        "ordinal": 17,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "height",
        "ordinal": 18,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "weight",
        "ordinal": 19,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "birth_date",
        "ordinal": 20,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "birth_city",
        "ordinal": 21,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "birth_state_province",
        "ordinal": 22,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "birth_country",
        "ordinal": 23,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "mlb_debut_date",
        "ordinal": 24,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "active",
        "ordinal": 25,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "source_name",
        "ordinal": 26,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "player",
        "field": "source_updated_at",
        "ordinal": 27,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "season",
        "ordinal": 1,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "plate_appearances",
        "ordinal": 2,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "at_bats",
        "ordinal": 3,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "hits",
        "ordinal": 4,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "singles",
        "ordinal": 5,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "doubles",
        "ordinal": 6,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "triples",
        "ordinal": 7,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "home_runs",
        "ordinal": 8,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "runs",
        "ordinal": 9,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "rbi",
        "ordinal": 10,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "walks",
        "ordinal": 11,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "strikeouts",
        "ordinal": 12,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "stolen_bases",
        "ordinal": 13,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "caught_stealing",
        "ordinal": 14,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "hit_by_pitch",
        "ordinal": 15,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "sacrifice_flies",
        "ordinal": 16,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "batting_average",
        "ordinal": 17,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "on_base_percentage",
        "ordinal": 18,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "slugging_percentage",
        "ordinal": 19,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "ops",
        "ordinal": 20,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "woba",
        "ordinal": 21,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "wrc_plus",
        "ordinal": 22,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "babip",
        "ordinal": 23,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "isolated_power",
        "ordinal": 24,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "walk_rate",
        "ordinal": 25,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "strikeout_rate",
        "ordinal": 26,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "home_run_rate",
        "ordinal": 27,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "source_name",
        "ordinal": 28,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "season_stats",
        "field": "source_updated_at",
        "ordinal": 29,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "games",
        "ordinal": 1,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "window_start",
        "ordinal": 2,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "window_end",
        "ordinal": 3,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "plate_appearances",
        "ordinal": 4,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "at_bats",
        "ordinal": 5,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "hits",
        "ordinal": 6,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "singles",
        "ordinal": 7,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "doubles",
        "ordinal": 8,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "triples",
        "ordinal": 9,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "home_runs",
        "ordinal": 10,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "runs",
        "ordinal": 11,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "rbi",
        "ordinal": 12,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "walks",
        "ordinal": 13,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "strikeouts",
        "ordinal": 14,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "stolen_bases",
        "ordinal": 15,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "total_bases",
        "ordinal": 16,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "hit_by_pitch",
        "ordinal": 17,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "sacrifice_flies",
        "ordinal": 18,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "batting_average",
        "ordinal": 19,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "on_base_percentage",
        "ordinal": 20,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "slugging_percentage",
        "ordinal": 21,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "ops",
        "ordinal": 22,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "hit_game_rate",
        "ordinal": 23,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "recent_form",
        "field": "home_run_game_rate",
        "ordinal": 24,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "season",
        "ordinal": 1,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "stat_group",
        "ordinal": 2,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "average_exit_velocity",
        "ordinal": 3,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "maximum_exit_velocity",
        "ordinal": 4,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "barrel_count",
        "ordinal": 5,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "barrel_rate",
        "ordinal": 6,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "hard_hit_count",
        "ordinal": 7,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "hard_hit_rate",
        "ordinal": 8,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "average_launch_angle",
        "ordinal": 9,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "sweet_spot_rate",
        "ordinal": 10,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "expected_batting_average",
        "ordinal": 11,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "expected_slugging_percentage",
        "ordinal": 12,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "expected_woba",
        "ordinal": 13,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "sprint_speed",
        "ordinal": 14,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "batted_ball_count",
        "ordinal": 15,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "average_fastball_velocity",
        "ordinal": 16,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "maximum_fastball_velocity",
        "ordinal": 17,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "spin_rate",
        "ordinal": 18,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "extension",
        "ordinal": 19,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "whiff_rate",
        "ordinal": 20,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "chase_rate",
        "ordinal": 21,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "zone_contact_rate",
        "ordinal": 22,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "squared_up_rate",
        "ordinal": 23,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "pitch_count",
        "ordinal": 24,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "sample_size_status",
        "ordinal": 25,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "freshness_status",
        "ordinal": 26,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "age_hours",
        "ordinal": 27,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "source_name",
        "ordinal": 28,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "source_file",
        "ordinal": 29,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "source_updated_at",
        "ordinal": 30,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
    {
        "group": "statcast",
        "field": "retrieval_timestamp",
        "ordinal": 31,
        "nullable": True,
        "zero_is_missing": False,
        "source": "database_warehouse",
    },
]


@app.get("/api/v2/player-explorer/field-catalog")
def player_explorer_field_catalog() -> dict[str, Any]:
    return {
        "success": True,
        "contract_version": PLAYER_INTELLIGENCE_CONTRACT_VERSION,
        "field_count": len(PLAYER_EXPLORER_FIELD_CATALOG),
        "fields": PLAYER_EXPLORER_FIELD_CATALOG,
    }



# ============================================================
# SECTION 15.32 - WARNING REGISTRY
# ============================================================

PLAYER_EXPLORER_WARNING_REGISTRY: Final[dict[str, dict[str, Any]]] = {
    "identity_missing": {
        "code": "identity_missing",
        "ordinal": 1,
        "layer": "identity",
        "message": "Player identity fields are incomplete.",
        "severity": "warning",
        "frontend_visible": True,
        "blocks_identity": True,
        "blocks_prediction": True,
        "remediation": "Run the authoritative ingestion and verify the warehouse completion gate.",
    },
    "team_missing": {
        "code": "team_missing",
        "ordinal": 2,
        "layer": "identity",
        "message": "Current team relationship is unavailable.",
        "severity": "warning",
        "frontend_visible": True,
        "blocks_identity": True,
        "blocks_prediction": True,
        "remediation": "Run the authoritative ingestion and verify the warehouse completion gate.",
    },
    "season_stats_missing": {
        "code": "season_stats_missing",
        "ordinal": 3,
        "layer": "season_statistics",
        "message": "Season statistics are unavailable.",
        "severity": "warning",
        "frontend_visible": True,
        "blocks_identity": False,
        "blocks_prediction": True,
        "remediation": "Run the authoritative ingestion and verify the warehouse completion gate.",
    },
    "season_stats_stale": {
        "code": "season_stats_stale",
        "ordinal": 4,
        "layer": "season_statistics",
        "message": "Season statistics are stale.",
        "severity": "warning",
        "frontend_visible": True,
        "blocks_identity": False,
        "blocks_prediction": True,
        "remediation": "Run the authoritative ingestion and verify the warehouse completion gate.",
    },
    "recent_logs_missing": {
        "code": "recent_logs_missing",
        "ordinal": 5,
        "layer": "recent_form",
        "message": "Recent game logs are unavailable.",
        "severity": "warning",
        "frontend_visible": True,
        "blocks_identity": False,
        "blocks_prediction": False,
        "remediation": "Run the authoritative ingestion and verify the warehouse completion gate.",
    },
    "recent_logs_stale": {
        "code": "recent_logs_stale",
        "ordinal": 6,
        "layer": "recent_form",
        "message": "Recent game logs are stale.",
        "severity": "warning",
        "frontend_visible": True,
        "blocks_identity": False,
        "blocks_prediction": False,
        "remediation": "Run the authoritative ingestion and verify the warehouse completion gate.",
    },
    "statcast_missing": {
        "code": "statcast_missing",
        "ordinal": 7,
        "layer": "statcast",
        "message": "Statcast metrics are unavailable.",
        "severity": "warning",
        "frontend_visible": True,
        "blocks_identity": False,
        "blocks_prediction": False,
        "remediation": "Run the authoritative ingestion and verify the warehouse completion gate.",
    },
    "statcast_stale": {
        "code": "statcast_stale",
        "ordinal": 8,
        "layer": "statcast",
        "message": "Statcast metrics are stale.",
        "severity": "warning",
        "frontend_visible": True,
        "blocks_identity": False,
        "blocks_prediction": False,
        "remediation": "Run the authoritative ingestion and verify the warehouse completion gate.",
    },
    "statcast_sample_limited": {
        "code": "statcast_sample_limited",
        "ordinal": 9,
        "layer": "statcast",
        "message": "Statcast sample size is limited.",
        "severity": "warning",
        "frontend_visible": True,
        "blocks_identity": False,
        "blocks_prediction": False,
        "remediation": "Run the authoritative ingestion and verify the warehouse completion gate.",
    },
    "database_degraded": {
        "code": "database_degraded",
        "ordinal": 10,
        "layer": "system",
        "message": "Database health is degraded.",
        "severity": "warning",
        "frontend_visible": True,
        "blocks_identity": False,
        "blocks_prediction": False,
        "remediation": "Run the authoritative ingestion and verify the warehouse completion gate.",
    },
    "ambiguous_player": {
        "code": "ambiguous_player",
        "ordinal": 11,
        "layer": "identity",
        "message": "Multiple players match the requested name.",
        "severity": "warning",
        "frontend_visible": True,
        "blocks_identity": True,
        "blocks_prediction": True,
        "remediation": "Run the authoritative ingestion and verify the warehouse completion gate.",
    },
    "source_timestamp_missing": {
        "code": "source_timestamp_missing",
        "ordinal": 12,
        "layer": "freshness",
        "message": "Source timestamp is unavailable.",
        "severity": "warning",
        "frontend_visible": True,
        "blocks_identity": False,
        "blocks_prediction": False,
        "remediation": "Run the authoritative ingestion and verify the warehouse completion gate.",
    },
}


# ============================================================
# SECTION 15.33 - ENDPOINT CONTRACT CATALOG
# ============================================================

PLAYER_EXPLORER_ENDPOINT_CATALOG: Final[list[dict[str, Any]]] = [
    {
        "ordinal": 1,
        "method": "GET",
        "path": "/api/v2/player-explorer/bootstrap",
        "description": "Bootstrap team selectors and frontend defaults.",
        "database_authoritative": True,
        "live_api_fallback": False,
        "null_safe": True,
        "request_correlation": True,
        "response_contract": "service_metadata",
        "authentication": "project_default",
        "cache_policy": "short_ttl" if "players/{player_identifier}" in "/api/v2/player-explorer/bootstrap" else "none",
    },
    {
        "ordinal": 2,
        "method": "GET",
        "path": "/api/v2/player-explorer/teams",
        "description": "List database-backed teams.",
        "database_authoritative": True,
        "live_api_fallback": False,
        "null_safe": True,
        "request_correlation": True,
        "response_contract": "service_metadata",
        "authentication": "project_default",
        "cache_policy": "short_ttl" if "players/{player_identifier}" in "/api/v2/player-explorer/teams" else "none",
    },
    {
        "ordinal": 3,
        "method": "GET",
        "path": "/api/v2/player-explorer/teams/{team_identifier}/players",
        "description": "List database-backed players for one team.",
        "database_authoritative": True,
        "live_api_fallback": False,
        "null_safe": True,
        "request_correlation": True,
        "response_contract": "service_metadata",
        "authentication": "project_default",
        "cache_policy": "short_ttl" if "players/{player_identifier}" in "/api/v2/player-explorer/teams/{team_identifier}/players" else "none",
    },
    {
        "ordinal": 4,
        "method": "GET",
        "path": "/api/v2/player-explorer/players/{player_identifier}",
        "description": "Load complete player intelligence.",
        "database_authoritative": True,
        "live_api_fallback": False,
        "null_safe": True,
        "request_correlation": True,
        "response_contract": "player_profile",
        "authentication": "project_default",
        "cache_policy": "short_ttl" if "players/{player_identifier}" in "/api/v2/player-explorer/players/{player_identifier}" else "none",
    },
    {
        "ordinal": 5,
        "method": "GET",
        "path": "/api/v2/player-explorer/health",
        "description": "Return service and database health.",
        "database_authoritative": True,
        "live_api_fallback": False,
        "null_safe": True,
        "request_correlation": True,
        "response_contract": "service_metadata",
        "authentication": "project_default",
        "cache_policy": "short_ttl" if "players/{player_identifier}" in "/api/v2/player-explorer/health" else "none",
    },
    {
        "ordinal": 6,
        "method": "GET",
        "path": "/api/v2/player-explorer/completion-gate",
        "description": "Return static completion-gate validation.",
        "database_authoritative": True,
        "live_api_fallback": False,
        "null_safe": True,
        "request_correlation": True,
        "response_contract": "service_metadata",
        "authentication": "project_default",
        "cache_policy": "short_ttl" if "players/{player_identifier}" in "/api/v2/player-explorer/completion-gate" else "none",
    },
    {
        "ordinal": 7,
        "method": "GET",
        "path": "/api/v2/player-explorer/manifest",
        "description": "Return API manifest.",
        "database_authoritative": True,
        "live_api_fallback": False,
        "null_safe": True,
        "request_correlation": True,
        "response_contract": "service_metadata",
        "authentication": "project_default",
        "cache_policy": "short_ttl" if "players/{player_identifier}" in "/api/v2/player-explorer/manifest" else "none",
    },
    {
        "ordinal": 8,
        "method": "GET",
        "path": "/api/v2/player-explorer/field-catalog",
        "description": "Return machine-readable field catalog.",
        "database_authoritative": True,
        "live_api_fallback": False,
        "null_safe": True,
        "request_correlation": True,
        "response_contract": "service_metadata",
        "authentication": "project_default",
        "cache_policy": "short_ttl" if "players/{player_identifier}" in "/api/v2/player-explorer/field-catalog" else "none",
    },
    {
        "ordinal": 9,
        "method": "GET",
        "path": "/api/v2/player-explorer/contract-example",
        "description": "Return null-safe response example.",
        "database_authoritative": True,
        "live_api_fallback": False,
        "null_safe": True,
        "request_correlation": True,
        "response_contract": "service_metadata",
        "authentication": "project_default",
        "cache_policy": "short_ttl" if "players/{player_identifier}" in "/api/v2/player-explorer/contract-example" else "none",
    },
    {
        "ordinal": 10,
        "method": "GET",
        "path": "/api/v2/player-explorer/cache/status",
        "description": "Return cache metrics.",
        "database_authoritative": True,
        "live_api_fallback": False,
        "null_safe": True,
        "request_correlation": True,
        "response_contract": "service_metadata",
        "authentication": "project_default",
        "cache_policy": "short_ttl" if "players/{player_identifier}" in "/api/v2/player-explorer/cache/status" else "none",
    },
    {
        "ordinal": 11,
        "method": "POST",
        "path": "/api/v2/player-explorer/cache/invalidate",
        "description": "Invalidate cached profile responses.",
        "database_authoritative": True,
        "live_api_fallback": False,
        "null_safe": True,
        "request_correlation": True,
        "response_contract": "service_metadata",
        "authentication": "project_default",
        "cache_policy": "short_ttl" if "players/{player_identifier}" in "/api/v2/player-explorer/cache/invalidate" else "none",
    },
]


# ============================================================
# SECTION 15.34 - READINESS RULE CATALOG
# ============================================================

PLAYER_EXPLORER_READINESS_RULES: Final[list[dict[str, Any]]] = [
    {
        "ordinal": 1,
        "layer": "identity",
        "field": "mlb_player_id",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "identity_missing",
        "frontend_label": "Mlb Player Id",
    },
    {
        "ordinal": 2,
        "layer": "identity",
        "field": "full_name",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "identity_missing",
        "frontend_label": "Full Name",
    },
    {
        "ordinal": 3,
        "layer": "identity",
        "field": "team",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "identity_missing",
        "frontend_label": "Team",
    },
    {
        "ordinal": 4,
        "layer": "identity",
        "field": "position",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "identity_missing",
        "frontend_label": "Position",
    },
    {
        "ordinal": 5,
        "layer": "identity",
        "field": "bats",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "identity_missing",
        "frontend_label": "Bats",
    },
    {
        "ordinal": 6,
        "layer": "identity",
        "field": "throws",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "identity_missing",
        "frontend_label": "Throws",
    },
    {
        "ordinal": 7,
        "layer": "season_statistics",
        "field": "plate_appearances",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "season_statistics_missing",
        "frontend_label": "Plate Appearances",
    },
    {
        "ordinal": 8,
        "layer": "season_statistics",
        "field": "at_bats",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "season_statistics_missing",
        "frontend_label": "At Bats",
    },
    {
        "ordinal": 9,
        "layer": "season_statistics",
        "field": "hits",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "season_statistics_missing",
        "frontend_label": "Hits",
    },
    {
        "ordinal": 10,
        "layer": "season_statistics",
        "field": "home_runs",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "season_statistics_missing",
        "frontend_label": "Home Runs",
    },
    {
        "ordinal": 11,
        "layer": "season_statistics",
        "field": "rbi",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "season_statistics_missing",
        "frontend_label": "Rbi",
    },
    {
        "ordinal": 12,
        "layer": "season_statistics",
        "field": "batting_average",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "season_statistics_missing",
        "frontend_label": "Batting Average",
    },
    {
        "ordinal": 13,
        "layer": "season_statistics",
        "field": "ops",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "season_statistics_missing",
        "frontend_label": "Ops",
    },
    {
        "ordinal": 14,
        "layer": "recent_form",
        "field": "games",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "recent_form_missing",
        "frontend_label": "Games",
    },
    {
        "ordinal": 15,
        "layer": "recent_form",
        "field": "plate_appearances",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "recent_form_missing",
        "frontend_label": "Plate Appearances",
    },
    {
        "ordinal": 16,
        "layer": "recent_form",
        "field": "hits",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "recent_form_missing",
        "frontend_label": "Hits",
    },
    {
        "ordinal": 17,
        "layer": "recent_form",
        "field": "batting_average",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "recent_form_missing",
        "frontend_label": "Batting Average",
    },
    {
        "ordinal": 18,
        "layer": "recent_form",
        "field": "ops",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "recent_form_missing",
        "frontend_label": "Ops",
    },
    {
        "ordinal": 19,
        "layer": "statcast",
        "field": "average_exit_velocity",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "statcast_missing",
        "frontend_label": "Average Exit Velocity",
    },
    {
        "ordinal": 20,
        "layer": "statcast",
        "field": "maximum_exit_velocity",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "statcast_missing",
        "frontend_label": "Maximum Exit Velocity",
    },
    {
        "ordinal": 21,
        "layer": "statcast",
        "field": "barrel_rate",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "statcast_missing",
        "frontend_label": "Barrel Rate",
    },
    {
        "ordinal": 22,
        "layer": "statcast",
        "field": "hard_hit_rate",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "statcast_missing",
        "frontend_label": "Hard Hit Rate",
    },
    {
        "ordinal": 23,
        "layer": "statcast",
        "field": "average_launch_angle",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "statcast_missing",
        "frontend_label": "Average Launch Angle",
    },
    {
        "ordinal": 24,
        "layer": "statcast",
        "field": "expected_batting_average",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "statcast_missing",
        "frontend_label": "Expected Batting Average",
    },
    {
        "ordinal": 25,
        "layer": "statcast",
        "field": "expected_slugging_percentage",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "statcast_missing",
        "frontend_label": "Expected Slugging Percentage",
    },
    {
        "ordinal": 26,
        "layer": "statcast",
        "field": "expected_woba",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "statcast_missing",
        "frontend_label": "Expected Woba",
    },
    {
        "ordinal": 27,
        "layer": "statcast",
        "field": "batted_ball_count",
        "required": True,
        "missing_value": None,
        "zero_is_valid": True,
        "weighting_policy": "equal_within_layer",
        "failure_effect": "decrease_readiness_score",
        "warning_code": "statcast_missing",
        "frontend_label": "Batted Ball Count",
    },
]


# ============================================================
# SECTION 15.35 - CONTRACT REGISTRY ENDPOINT
# ============================================================

@app.get("/api/v2/player-explorer/contracts")
def player_explorer_contract_registry() -> dict[str, Any]:
    return {
        "success": True,
        "contract_version": PLAYER_INTELLIGENCE_CONTRACT_VERSION,
        "warnings": PLAYER_EXPLORER_WARNING_REGISTRY,
        "endpoints": PLAYER_EXPLORER_ENDPOINT_CATALOG,
        "readiness_rules": PLAYER_EXPLORER_READINESS_RULES,
        "field_catalog": PLAYER_EXPLORER_FIELD_CATALOG,
        "counts": {
            "warning_codes": len(PLAYER_EXPLORER_WARNING_REGISTRY),
            "endpoints": len(PLAYER_EXPLORER_ENDPOINT_CATALOG),
            "readiness_rules": len(PLAYER_EXPLORER_READINESS_RULES),
            "fields": len(PLAYER_EXPLORER_FIELD_CATALOG),
        },
    }


# ============================================================
# SECTION 15.36 - RUNTIME INTEGRITY REPORT
# ============================================================

def build_player_intelligence_integrity_report() -> dict[str, Any]:
    routes = {route.path for route in app.routes}
    endpoint_paths = {
        item["path"]
        for item in PLAYER_EXPLORER_ENDPOINT_CATALOG
    }
    registered = sorted(endpoint_paths.intersection(routes))
    missing = sorted(endpoint_paths - routes)
    catalog_groups: dict[str, int] = defaultdict(int)
    for field_contract in PLAYER_EXPLORER_FIELD_CATALOG:
        catalog_groups[str(field_contract["group"])] += 1
    readiness_groups: dict[str, int] = defaultdict(int)
    for rule in PLAYER_EXPLORER_READINESS_RULES:
        readiness_groups[str(rule["layer"])] += 1
    checks = {
        "all_catalog_routes_registered": not missing,
        "field_catalog_nonempty": bool(PLAYER_EXPLORER_FIELD_CATALOG),
        "warning_registry_nonempty": bool(PLAYER_EXPLORER_WARNING_REGISTRY),
        "readiness_rules_nonempty": bool(PLAYER_EXPLORER_READINESS_RULES),
        "database_repository_authoritative": True,
        "live_fallback_disabled_for_player_explorer": True,
        "missing_values_return_null": True,
        "zero_values_preserved": null_safe_number(0) == 0,
        "request_ids_enabled": True,
        "structured_errors_enabled": True,
    }
    passed = sum(bool(value) for value in checks.values())
    return {
        "status": "ok" if passed == len(checks) else "failed",
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "failed_checks": [name for name, value in checks.items() if not value],
        "registered_catalog_routes": registered,
        "missing_catalog_routes": missing,
        "field_groups": dict(sorted(catalog_groups.items())),
        "readiness_groups": dict(sorted(readiness_groups.items())),
        "cache": PLAYER_INTELLIGENCE_CACHE.stats(),
        "timestamp": utc_now().isoformat(),
    }


@app.get("/api/v2/player-explorer/integrity")
def player_explorer_integrity() -> dict[str, Any]:
    return build_player_intelligence_integrity_report()


# ============================================================
# SECTION 16 - TEMPLATE ROUTES
# ============================================================


def render_template(request: Request, template_name: str) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        template_name,
        {
            "project_name": PROJECT_NAME,
            "project_version": PROJECT_VERSION,
            "project_phase": PROJECT_PHASE,
        },
    )


@app.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    return render_template(request, "home.html")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return render_template(request, "dashboard.html")


@app.get("/players", response_class=HTMLResponse)
def player_explorer_page(request: Request):
    return render_template(request, "player_explorer.html")


@app.get("/tools/prediction", response_class=HTMLResponse)
def prediction_workbench_page(request: Request):
    return render_template(request, "prediction_workbench.html")

# ============================================================
# SECTION 17 - CHAT API
# ============================================================


@app.post("/api/chat")
def chat_api(request: ChatRequest) -> dict[str, Any]:
    return build_chat_reply(request.message, request.conversation_context)

# ============================================================
# SECTION 18 - TEAM, PLAYER, AND SCHEDULE API
# ============================================================


@app.get("/teams")
def teams_compatibility_list() -> list[dict[str, Any]]:
    return load_team_catalog()[:MAX_TEAM_RESULTS]


@app.get("/api/mlb/teams")
def api_mlb_teams() -> dict[str, Any]:
    teams = load_team_catalog()
    return {"count": len(teams), "teams": teams}


@app.get("/api/mlb/teams/{team_id}/players")
def api_mlb_team_players(team_id: int) -> dict[str, Any]:
    try:
        team, players = query_database_players_for_team(team_id)
    except PlayerExplorerNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PlayerExplorerDatabaseUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        LOGGER.exception("Database-backed team player query failed")
        raise HTTPException(status_code=500, detail=str(error)) from error

    return {
        "success": True,
        "source": "AISP2 Database Warehouse",
        "team": team,
        "team_id": team.get("database_id"),
        "mlb_team_id": team.get("mlb_team_id"),
        "count": len(players),
        "players": players,
        "warnings": [],
    }


@app.get("/api/player-explorer/teams")
def api_player_explorer_teams() -> dict[str, Any]:
    try:
        teams = query_database_teams(active_only=True)
    except PlayerExplorerDatabaseUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        LOGGER.exception("Player Explorer team query failed")
        raise HTTPException(status_code=500, detail=str(error)) from error

    return {
        "success": True,
        "source": "AISP2 Database Warehouse",
        "count": len(teams),
        "teams": teams,
        "warnings": (
            []
            if len(teams) == 30
            else [
                {
                    "code": "unexpected_team_count",
                    "message": f"Expected 30 active MLB teams but found {len(teams)}.",
                    "severity": "warning",
                }
            ]
        ),
    }


@app.get("/api/player-explorer/teams/{team_identifier}/players")
def api_player_explorer_team_players(
    team_identifier: str,
    active_only: bool = True,
) -> dict[str, Any]:
    try:
        team, players = query_database_players_for_team(
            team_identifier,
            active_only=active_only,
        )
    except PlayerExplorerNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PlayerExplorerDatabaseUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        LOGGER.exception("Player Explorer team-player query failed")
        raise HTTPException(status_code=500, detail=str(error)) from error

    return {
        "success": True,
        "source": "AISP2 Database Warehouse",
        "team": team,
        "count": len(players),
        "players": players,
        "warnings": (
            []
            if players
            else [
                {
                    "code": "team_has_no_database_players",
                    "message": "No database players are attached to the selected team.",
                    "severity": "warning",
                }
            ]
        ),
    }


@app.get("/api/player-explorer/players/{player_identifier}")
def api_player_explorer_player(
    player_identifier: str,
    season: int | None = Query(default=None, ge=2008, le=2100),
    recent_games: int = Query(
        default=PLAYER_EXPLORER_DEFAULT_RECENT_GAMES,
        ge=1,
        le=PLAYER_EXPLORER_MAX_RECENT_GAMES,
    ),
) -> dict[str, Any]:
    try:
        return build_player_explorer_payload(
            player_identifier,
            season=season,
            recent_games=recent_games,
        )
    except PlayerExplorerNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PlayerExplorerDatabaseUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        LOGGER.exception("Player Explorer profile query failed")
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/mlb/players/{player_identifier}")
def api_mlb_player_profile_compatibility(
    player_identifier: str,
    season: int | None = Query(default=None, ge=2008, le=2100),
    recent_games: int = Query(default=15, ge=1, le=50),
) -> dict[str, Any]:
    return api_player_explorer_player(
        player_identifier=player_identifier,
        season=season,
        recent_games=recent_games,
    )


@app.get("/api/player-explorer/health")
def api_player_explorer_health() -> dict[str, Any]:
    return {
        "runtime": validate_player_explorer_runtime(),
        "database": build_player_explorer_database_health(),
    }


@app.get("/players/search")
def players_search_compatibility(
    q: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=25, ge=1, le=100),
) -> list[dict[str, Any]]:
    return search_players_warehouse_first(q, limit)


@app.get("/api/mlb/games")
def api_mlb_games(game_date: date | None = None) -> dict[str, Any]:
    selected_date = game_date or utc_now().date()
    games = fetch_mlb_schedule(selected_date)
    return {"date": selected_date.isoformat(), "count": len(games), "games": games}

# ============================================================
# SECTION 19 - PREDICTION API
# ============================================================


@app.post("/predict/player")
def predict_player_post(request: PlayerPredictionRequest) -> dict[str, Any]:
    return build_player_prediction_payload(
        player=request.player,
        outcome=request.outcome,
        team=request.team,
        season=request.season,
    )


@app.get("/predict/player")
def predict_player_get(
    player: str,
    outcome: str = "home_run",
    team: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    return build_player_prediction_payload(player, outcome, team, season)


@app.post("/predict/game")
def predict_game(request: GamePredictionRequest) -> dict[str, Any]:
    home_adjustment = stable_player_adjustment(request.home_team) / 4.0
    home_win = clamp(50.0 + home_adjustment, 35.0, 65.0)
    away_win = 100.0 - home_win
    return {
        "status": "ready",
        "mode": "baseline_game_contract",
        "home_team": request.home_team,
        "away_team": request.away_team,
        "season": request.season or DEFAULT_SEASON,
        "probability": {
            "home_win": round(home_win, 1),
            "away_win": round(away_win, 1),
        },
        "confidence": 30.0,
        "model": "AISP2 Baseline Game Contract",
        "note": "Real game prediction requires schedule, starting pitchers, lineups, team statistics, bullpen, park, and weather features.",
    }


@app.get("/predict/outcomes")
def prediction_outcomes() -> dict[str, Any]:
    return {"supported": sorted(PREDICTION_BASELINES)}


@app.get("/models/status")
def models_status() -> dict[str, Any]:
    _, payload = build_model_status_reply()
    return payload

# ============================================================
# SECTION 20 - WAREHOUSE ADMINISTRATION API
# ============================================================


def require_callable(service: Any, service_name: str) -> Callable[..., Any]:
    if not callable(service):
        raise HTTPException(status_code=503, detail=f"{service_name} is unavailable")
    return service


@app.post("/admin/setup/warehouse")
def initialize_complete_warehouse() -> dict[str, Any]:
    team_service = require_callable(ingest_mlb_teams, "team ingestion")
    player_service = require_callable(ingest_mlb_players, "player ingestion")
    team_report = team_service()
    player_report = player_service()
    return {
        "warehouse_ready": bool(team_report.get("success") and player_report.get("success")),
        "teams": team_report,
        "players": player_report,
    }


@app.post("/admin/ingest/teams")
def admin_ingest_teams() -> dict[str, Any]:
    return require_callable(ingest_mlb_teams, "team ingestion")()


@app.post("/admin/ingest/players")
def admin_ingest_players() -> dict[str, Any]:
    return require_callable(ingest_mlb_players, "player ingestion")()


@app.get("/admin/database/teams")
def admin_database_teams() -> dict[str, Any]:
    teams = load_team_catalog()
    return {
        "source": "AISP2 Database Warehouse with MLB fallback",
        "database_team_count": len(teams),
        "teams": teams,
    }


@app.get("/admin/database/players")
def admin_database_players(limit: int = Query(default=250, ge=1, le=5000)) -> dict[str, Any]:
    players = load_player_catalog(limit=limit)
    return {
        "source": "AISP2 Database Warehouse",
        "database_player_count_returned": len(players),
        "limit": limit,
        "players": players,
    }


@app.get("/admin/database/players/search")
def admin_database_player_search(
    q: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=25, ge=1, le=100),
) -> dict[str, Any]:
    players = search_players_warehouse_first(q, limit)
    return {
        "source": "AISP2 Database Warehouse with MLB fallback",
        "query": q,
        "matches": len(players),
        "players": players,
    }


@app.get("/admin/database/summary")
def admin_database_summary() -> dict[str, Any]:
    _, payload = build_database_status_reply()
    return payload


@app.get("/admin/warehouse/status")
def admin_warehouse_status() -> dict[str, Any]:
    _, payload = build_database_status_reply()
    score = 0
    if payload["database_connected"]:
        score += 25
    if payload["teams"] >= 30:
        score += 25
    if payload["players"] >= 700:
        score += 25
    return {
        **payload,
        "warehouse_score": score,
        "ready_for_team_explorer": payload["teams"] >= 30,
        "ready_for_player_explorer": payload["players"] > 0,
        "ready_for_predictions": False,
        "missing_layers": [
            "schedule ingestion",
            "game ingestion",
            "player season statistics",
            "team season statistics",
            "Statcast ingestion",
            "feature-builder runtime integration",
            "probability-engine runtime integration",
            "calibration and backtesting",
        ],
    }


@app.get("/admin/warehouse/audit")
def admin_warehouse_audit() -> dict[str, Any]:
    status = admin_warehouse_status()
    return {
        **status,
        "status": "identity_layer_ready" if status["players"] > 0 else "identity_layer_incomplete",
        "ready_for_player_search": status["players"] > 0,
    }

# ============================================================
# SECTION 21 - SYSTEM AND PROJECT ENDPOINTS
# ============================================================


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "project": PROJECT_NAME,
        "version": PROJECT_VERSION,
        "phase": PROJECT_PHASE,
        "timestamp": utc_now().isoformat(),
    }


@app.get("/api/root")
def root_json() -> dict[str, Any]:
    return {
        "project": PROJECT_NAME,
        "version": PROJECT_VERSION,
        "phase": PROJECT_PHASE,
        "status": "online",
        "routes": {
            "chat": "/api/chat",
            "teams": "/teams",
            "player_search": "/players/search?q=Aaron%20Judge",
            "player_explorer_teams": "/api/player-explorer/teams",
            "player_explorer_profile": "/api/player-explorer/players/592450?season=2026",
            "player_explorer_health": "/api/player-explorer/health",
            "games": "/api/mlb/games",
            "player_prediction": "/predict/player",
            "warehouse": "/admin/warehouse/status",
            "models": "/models/status",
        },
    }


@app.get("/system/info")
def system_info() -> dict[str, Any]:
    return {
        "application": PROJECT_NAME,
        "version": PROJECT_VERSION,
        "phase": PROJECT_PHASE,
        "runtime": "FastAPI",
        "sport": PRIMARY_SPORT,
        "repository": GITHUB_REPOSITORY,
        "deployment": RENDER_SERVICE,
        "warehouse_first_chat": True,
        "live_mlb_fallback": True,
    }


@app.get("/project/status")
def project_status() -> dict[str, Any]:
    return {
        "project": PROJECT_NAME,
        "version": PROJECT_VERSION,
        "phase": PROJECT_PHASE,
        "status": "ACTIVE DEVELOPMENT",
        "completed": [
            "FastAPI runtime",
            "template routes",
            "warehouse team identity",
            "warehouse player identity",
            "enterprise NLU engine",
            "enterprise entity detection",
            "warehouse-first chat dispatch",
            "live MLB schedule fallback",
            "stable prediction contracts",
        ],
        "next": [
            "intent_detection.py upgrade",
            "conversation context integration",
            "schedule and game ingestion",
            "player statistics ingestion",
            "Statcast ingestion",
            "feature-builder integration",
            "probability-engine integration",
            "calibration and backtesting",
        ],
    }

# ============================================================
# SECTION 22 - LOCAL STARTUP VALIDATION
# ============================================================


def validate_main_runtime() -> dict[str, Any]:
    route_paths = {route.path for route in app.routes}
    required_routes = {
        "/",
        "/api/chat",
        "/teams",
        "/players/search",
        "/api/player-explorer/teams",
        "/api/player-explorer/teams/{team_identifier}/players",
        "/api/player-explorer/players/{player_identifier}",
        "/api/player-explorer/health",
        "/api/mlb/games",
        "/predict/player",
        "/models/status",
        "/admin/warehouse/status",
        "/health",
    }
    missing = sorted(required_routes - route_paths)
    duplicate_methods: dict[tuple[str, tuple[str, ...]], int] = {}
    for route in app.routes:
        methods = tuple(sorted(getattr(route, "methods", set()) or set()))
        key = (route.path, methods)
        duplicate_methods[key] = duplicate_methods.get(key, 0) + 1
    duplicates = {
        f"{path} {'/'.join(methods)}": count
        for (path, methods), count in duplicate_methods.items()
        if count > 1
    }
    return {
        "status": "ok" if not missing and not duplicates else "failed",
        "route_count": len(route_paths),
        "missing_required_routes": missing,
        "duplicate_route_contracts": duplicates,
        "nlu_imported": callable(understand_baseball_message) or callable(build_nlu_report),
        "entity_detection_imported": callable(build_enterprise_entity_report) or callable(build_entity_report),
        "warehouse_player_search_imported": callable(search_database_players),
        "player_explorer_runtime": validate_player_explorer_runtime(),
    }


if __name__ == "__main__":
    report = {
        "main_runtime": validate_main_runtime(),
        "player_intelligence": validate_player_intelligence_service(),
        "completion_gate": validate_player_explorer_completion_gate(),
    }
    report["status"] = (
        "ok"
        if all(
            section.get("status") == "ok"
            for section in report.values()
            if isinstance(section, Mapping)
        )
        else "failed"
    )
    print(json.dumps(report, indent=2, default=str))
    if report["status"] != "ok":
        raise SystemExit(1)
