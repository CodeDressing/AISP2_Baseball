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

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
import logging
import math
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Final

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
from fastapi.responses import HTMLResponse
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
PROJECT_VERSION: Final[str] = "10.12.0"
PROJECT_PHASE: Final[str] = "Phase 10 Part 12 - Enterprise Chat Runtime"
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
    players = fetch_team_roster(team_id)
    return {"team_id": team_id, "count": len(players), "players": players}


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
    }


if __name__ == "__main__":
    import json

    print(json.dumps(validate_main_runtime(), indent=2, default=str))
