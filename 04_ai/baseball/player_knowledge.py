# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/baseball/player_knowledge.py
# PURPOSE:
# Enterprise player knowledge layer for AISP2.
#
# This module converts database player records, roster context,
# season statistics, advanced batting metrics, Statcast warehouse
# tables, home run profiles, pitch profiles, plate discipline,
# and prediction-ready feature signals into one unified player
# intelligence object.
#
# Primary Consumers
# -----------------
# - Chatbot
# - Player Explorer
# - Prediction Workbench
# - Probability Engine
# - Future ML feature engineering
# - Future deep learning player embeddings
# ============================================================


# ============================================================
# SECTION 01 - IMPORTS AND PATH REGISTRATION
# ============================================================

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from sqlalchemy import or_
except Exception:  # pragma: no cover
    or_ = None


CURRENT_FILE = Path(__file__).resolve()

# 04_ai/baseball/player_knowledge.py
# parents[0] = baseball
# parents[1] = 04_ai
# parents[2] = project root
PROJECT_ROOT = CURRENT_FILE.parents[2]
DATABASE_DIR = PROJECT_ROOT / "01_database"
AI_DIR = PROJECT_ROOT / "04_ai"
BASEBALL_DIR = AI_DIR / "baseball"

for project_path in [
    PROJECT_ROOT,
    DATABASE_DIR,
    AI_DIR,
    BASEBALL_DIR,
]:
    path_string = str(project_path)

    if path_string not in sys.path:
        sys.path.insert(
            0,
            path_string,
        )


# ============================================================
# SECTION 02 - SAFE DATABASE IMPORTS
# ============================================================

DATABASE_IMPORT_ERROR: str | None = None
MODELS_IMPORT_ERROR: str | None = None

try:
    from database import managed_database_session
except Exception as error:  # pragma: no cover
    managed_database_session = None
    DATABASE_IMPORT_ERROR = str(error)


try:
    from models import Team
    from models import Player
    from models import RosterEntry
    from models import PlayerSeasonStat
    from models import PlayerAdvancedBattingStat
    from models import PlayerPercentileRanking
    from models import PlayerPitchArsenal
    from models import PlayerPitchTempo
    from models import PlayerBattedBallProfile
    from models import PlayerBattingStance
    from models import PlayerHomeRunProfile
    from models import TeamPlateDiscipline
    from models import RawDataImportLog

    try:
        from models import Game
    except Exception:
        Game = None

    try:
        from models import PlayerGameStat
    except Exception:
        PlayerGameStat = None

    try:
        from models import PitchEvent
    except Exception:
        PitchEvent = None

    try:
        from models import PlateAppearance
    except Exception:
        PlateAppearance = None

    try:
        from models import StatcastEvent
    except Exception:
        StatcastEvent = None

    try:
        from models import PredictionResult
    except Exception:
        PredictionResult = None

except Exception as error:  # pragma: no cover
    MODELS_IMPORT_ERROR = str(error)

    Team = None
    Player = None
    RosterEntry = None
    PlayerSeasonStat = None
    PlayerAdvancedBattingStat = None
    PlayerPercentileRanking = None
    PlayerPitchArsenal = None
    PlayerPitchTempo = None
    PlayerBattedBallProfile = None
    PlayerBattingStance = None
    PlayerHomeRunProfile = None
    TeamPlateDiscipline = None
    RawDataImportLog = None
    Game = None
    PlayerGameStat = None
    PitchEvent = None
    PlateAppearance = None
    StatcastEvent = None
    PredictionResult = None


# ============================================================
# SECTION 03 - PLAYER KNOWLEDGE CONFIGURATION
# ============================================================

PLAYER_KNOWLEDGE_VERSION = "phase_12_player_knowledge_enterprise_v1"

DEFAULT_PLAYER_SEARCH_LIMIT = 12
DEFAULT_RECENT_GAME_LIMIT = 10
DEFAULT_PITCH_ARSENAL_LIMIT = 12
DEFAULT_PREDICTION_HISTORY_LIMIT = 10

KNOWLEDGE_STATUS_READY = "ready"
KNOWLEDGE_STATUS_PARTIAL = "partial"
KNOWLEDGE_STATUS_NOT_FOUND = "not_found"
KNOWLEDGE_STATUS_DATABASE_UNAVAILABLE = "database_unavailable"
KNOWLEDGE_STATUS_ERROR = "error"

DATASET_PLAYER_IDENTITY = "player_identity"
DATASET_TEAM_CONTEXT = "team_context"
DATASET_ROSTER_CONTEXT = "roster_context"
DATASET_SEASON_STATS = "season_stats"
DATASET_ADVANCED_BATTING = "advanced_batting"
DATASET_PERCENTILE_RANKINGS = "percentile_rankings"
DATASET_PITCH_ARSENAL = "pitch_arsenal"
DATASET_PITCH_TEMPO = "pitch_tempo"
DATASET_BATTED_BALL_PROFILE = "batted_ball_profile"
DATASET_BATTING_STANCE = "batting_stance"
DATASET_HOME_RUN_PROFILE = "home_run_profile"
DATASET_TEAM_PLATE_DISCIPLINE = "team_plate_discipline"
DATASET_GAME_LOGS = "game_logs"
DATASET_STATCAST_EVENTS = "statcast_events"
DATASET_PREDICTION_HISTORY = "prediction_history"

PLAYER_KNOWLEDGE_DATASETS = [
    DATASET_PLAYER_IDENTITY,
    DATASET_TEAM_CONTEXT,
    DATASET_ROSTER_CONTEXT,
    DATASET_SEASON_STATS,
    DATASET_ADVANCED_BATTING,
    DATASET_PERCENTILE_RANKINGS,
    DATASET_PITCH_ARSENAL,
    DATASET_PITCH_TEMPO,
    DATASET_BATTED_BALL_PROFILE,
    DATASET_BATTING_STANCE,
    DATASET_HOME_RUN_PROFILE,
    DATASET_TEAM_PLATE_DISCIPLINE,
    DATASET_GAME_LOGS,
    DATASET_STATCAST_EVENTS,
    DATASET_PREDICTION_HISTORY,
]

PLAYER_KNOWLEDGE_CONFIGURATION = {
    "version": PLAYER_KNOWLEDGE_VERSION,
    "database_first": True,
    "warehouse_enabled": True,
    "statcast_enabled": True,
    "prediction_feature_output_enabled": True,
    "chatbot_summary_enabled": True,
    "player_explorer_card_enabled": True,
    "safe_fallback_enabled": True,
    "default_search_limit": DEFAULT_PLAYER_SEARCH_LIMIT,
    "recent_game_limit": DEFAULT_RECENT_GAME_LIMIT,
    "pitch_arsenal_limit": DEFAULT_PITCH_ARSENAL_LIMIT,
}


# ============================================================
# SECTION 04 - OUTCOME AND FEATURE CONFIGURATION
# ============================================================

SUPPORTED_PLAYER_OUTCOMES = {
    "home_run": {
        "label": "Home Run",
        "feature_group": "power",
        "primary_features": [
            "home_runs",
            "barrel_percent",
            "hard_hit_percent",
            "average_exit_velocity",
            "max_exit_velocity",
            "average_home_run_distance",
            "xslg",
            "xwoba",
        ],
    },
    "hit": {
        "label": "Hit",
        "feature_group": "contact",
        "primary_features": [
            "batting_average",
            "expected_batting_average",
            "woba",
            "expected_woba",
            "strikeout_percent",
            "whiff_percent",
        ],
    },
    "total_bases": {
        "label": "Total Bases",
        "feature_group": "slugging",
        "primary_features": [
            "slugging_percentage",
            "ops",
            "expected_slugging",
            "average_exit_velocity",
            "barrel_percent",
            "home_runs",
        ],
    },
    "rbi": {
        "label": "RBI",
        "feature_group": "run_production",
        "primary_features": [
            "rbi",
            "home_runs",
            "ops",
            "team_context",
            "lineup_context",
        ],
    },
    "walk": {
        "label": "Walk",
        "feature_group": "plate_discipline",
        "primary_features": [
            "walk_percent",
            "chase_percentile",
            "team_chase_percent",
            "zone_swing_percent",
        ],
    },
    "strikeout": {
        "label": "Strikeout",
        "feature_group": "swing_miss",
        "primary_features": [
            "strikeout_percent",
            "whiff_percent",
            "whiff_percentile",
            "chase_percentile",
        ],
    },
}

FEATURE_SCORE_WEIGHTS = {
    "power_score": 0.25,
    "contact_score": 0.18,
    "discipline_score": 0.14,
    "batted_ball_score": 0.18,
    "statcast_percentile_score": 0.15,
    "data_coverage_score": 0.10,
}


# ============================================================
# SECTION 05 - DATA CLASSES
# ============================================================

@dataclass
class PlayerResolution:
    status: str
    player_id: int | None = None
    mlb_player_id: int | None = None
    full_name: str | None = None
    matched_name: str | None = None
    match_type: str | None = None
    confidence: int = 0
    candidates: list[dict[str, Any]] | None = None
    error: str | None = None


@dataclass
class KnowledgeRequest:
    player_name: str
    season: int | None = None
    outcome: str | None = None
    include_raw: bool = False
    include_prediction_features: bool = True
    include_recent_games: bool = True
    include_statcast_events: bool = False


# ============================================================
# SECTION 06 - SAFE VALUE HELPERS
# ============================================================

def normalize_text(value: Any) -> str:
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
        .replace("/", " ")
    )


def normalize_compact(value: Any) -> str:
    return "".join(
        normalize_text(value).split()
    )


def safe_string(value: Any) -> str | None:
    if value is None:
        return None

    cleaned_value = str(value).strip()

    if not cleaned_value:
        return None

    if cleaned_value.lower() in {"none", "null", "nan", "n/a", "--"}:
        return None

    return cleaned_value


def safe_int(value: Any) -> int | None:
    if value is None:
        return None

    try:
        cleaned_value = str(value).replace(",", "").strip()

        if not cleaned_value:
            return None

        return int(float(cleaned_value))

    except Exception:
        return None


def safe_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        cleaned_value = str(value).replace(",", "").replace("%", "").strip()

        if not cleaned_value:
            return None

        return float(cleaned_value)

    except Exception:
        return None


def safe_round(
    value: Any,
    digits: int = 3,
) -> float | None:
    numeric_value = safe_float(value)

    if numeric_value is None:
        return None

    return round(
        numeric_value,
        digits,
    )


def clamp(
    value: float,
    minimum: float = 0,
    maximum: float = 100,
) -> float:
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def percent_to_score(value: Any) -> float | None:
    numeric_value = safe_float(value)

    if numeric_value is None:
        return None

    return clamp(
        numeric_value,
        0,
        100,
    )


def metric_to_score(
    value: Any,
    low: float,
    high: float,
    invert: bool = False,
) -> float | None:
    numeric_value = safe_float(value)

    if numeric_value is None:
        return None

    if high == low:
        return None

    score = ((numeric_value - low) / (high - low)) * 100

    if invert:
        score = 100 - score

    return clamp(
        score,
        0,
        100,
    )


def average_available(values: list[float | None]) -> float | None:
    clean_values = [
        value
        for value in values
        if value is not None and not math.isnan(value)
    ]

    if not clean_values:
        return None

    return sum(clean_values) / len(clean_values)


def object_to_dict(
    row: Any,
    include_private: bool = False,
) -> dict[str, Any] | None:
    if row is None:
        return None

    try:
        mapper = row.__mapper__

        return {
            column.key: getattr(
                row,
                column.key,
                None,
            )
            for column in mapper.columns
            if include_private or not column.key.startswith("_")
        }

    except Exception:
        result: dict[str, Any] = {}

        for key, value in vars(row).items():
            if key.startswith("_") and not include_private:
                continue

            result[key] = value

        return result


def compact_row(
    row: Any,
    excluded_keys: set[str] | None = None,
) -> dict[str, Any] | None:
    row_dict = object_to_dict(
        row,
    )

    if row_dict is None:
        return None

    excluded_keys = excluded_keys or {
        "raw_stat_json",
        "raw_schedule_json",
        "raw_game_stat_json",
        "raw_pitch_json",
        "raw_plate_appearance_json",
        "raw_statcast_json",
        "raw_prediction_json",
        "feature_json",
        "explanation_json",
    }

    return {
        key: value
        for key, value in row_dict.items()
        if key not in excluded_keys
    }


# ============================================================
# SECTION 07 - DATABASE AVAILABILITY
# ============================================================

def database_available() -> bool:
    return managed_database_session is not None and Player is not None


def build_database_unavailable_report() -> dict[str, Any]:
    return {
        "status": KNOWLEDGE_STATUS_DATABASE_UNAVAILABLE,
        "database_available": False,
        "database_error": DATABASE_IMPORT_ERROR,
        "models_error": MODELS_IMPORT_ERROR,
        "message": (
            "The player knowledge layer cannot access the database or ORM models."
        ),
    }


def safe_count_query(
    database_session,
    model,
) -> int:
    if model is None:
        return 0

    try:
        return database_session.query(model).count()

    except Exception:
        return 0


def build_player_knowledge_system_status() -> dict[str, Any]:
    if not database_available():
        return build_database_unavailable_report()

    try:
        with managed_database_session() as database_session:
            return {
                "status": KNOWLEDGE_STATUS_READY,
                "version": PLAYER_KNOWLEDGE_VERSION,
                "database_available": True,
                "players": safe_count_query(database_session, Player),
                "teams": safe_count_query(database_session, Team),
                "roster_entries": safe_count_query(database_session, RosterEntry),
                "season_stats": safe_count_query(database_session, PlayerSeasonStat),
                "advanced_batting_stats": safe_count_query(database_session, PlayerAdvancedBattingStat),
                "percentile_rankings": safe_count_query(database_session, PlayerPercentileRanking),
                "pitch_arsenals": safe_count_query(database_session, PlayerPitchArsenal),
                "pitch_tempo": safe_count_query(database_session, PlayerPitchTempo),
                "batted_ball_profiles": safe_count_query(database_session, PlayerBattedBallProfile),
                "batting_stances": safe_count_query(database_session, PlayerBattingStance),
                "home_run_profiles": safe_count_query(database_session, PlayerHomeRunProfile),
                "team_plate_discipline": safe_count_query(database_session, TeamPlateDiscipline),
                "raw_import_logs": safe_count_query(database_session, RawDataImportLog),
                "prediction_results": safe_count_query(database_session, PredictionResult),
            }

    except Exception as error:
        return {
            "status": KNOWLEDGE_STATUS_ERROR,
            "version": PLAYER_KNOWLEDGE_VERSION,
            "database_available": False,
            "error": str(error),
        }


# ============================================================
# SECTION 08 - PLAYER SEARCH AND RESOLUTION
# ============================================================

def player_to_search_result(
    player: Any,
    confidence: int = 80,
    match_type: str = "database_match",
) -> dict[str, Any]:
    team_name = None
    team_abbreviation = None

    try:
        if getattr(player, "team", None):
            team_name = player.team.name
            team_abbreviation = player.team.abbreviation
    except Exception:
        pass

    return {
        "id": getattr(player, "id", None),
        "player_id": getattr(player, "id", None),
        "mlb_player_id": getattr(player, "mlb_player_id", None),
        "full_name": getattr(player, "full_name", None),
        "name": getattr(player, "full_name", None),
        "first_name": getattr(player, "first_name", None),
        "last_name": getattr(player, "last_name", None),
        "position": getattr(player, "position", None),
        "position_code": getattr(player, "position_code", None),
        "primary_number": getattr(player, "primary_number", None),
        "bats": getattr(player, "bats", None),
        "throws": getattr(player, "throws", None),
        "current_team_id": getattr(player, "current_team_id", None),
        "team": team_name,
        "team_abbreviation": team_abbreviation,
        "active_status": getattr(player, "active_status", None),
        "confidence": confidence,
        "match_type": match_type,
    }


def search_players_by_name(
    query: str,
    limit: int = DEFAULT_PLAYER_SEARCH_LIMIT,
) -> list[dict[str, Any]]:
    if not database_available():
        return []

    clean_query = safe_string(query)

    if not clean_query:
        return []

    normalized_query = normalize_text(clean_query)
    compact_query = normalize_compact(clean_query)

    try:
        with managed_database_session() as database_session:
            base_query = database_session.query(Player)

            direct_matches = (
                base_query
                .filter(Player.full_name.ilike(f"%{clean_query}%"))
                .limit(limit)
                .all()
            )

            results: list[dict[str, Any]] = []

            for player in direct_matches:
                player_name = getattr(player, "full_name", "") or ""
                normalized_player = normalize_text(player_name)
                compact_player = normalize_compact(player_name)

                if normalized_player == normalized_query:
                    confidence = 100
                    match_type = "exact_name"

                elif compact_player == compact_query:
                    confidence = 98
                    match_type = "compact_exact_name"

                elif normalized_query in normalized_player:
                    confidence = 90
                    match_type = "contains_name"

                elif compact_query in compact_player:
                    confidence = 86
                    match_type = "compact_contains_name"

                else:
                    confidence = 70
                    match_type = "database_fuzzy_name"

                results.append(
                    player_to_search_result(
                        player=player,
                        confidence=confidence,
                        match_type=match_type,
                    )
                )

            if len(results) < limit:
                tokens = [
                    token
                    for token in normalized_query.split()
                    if token
                ]

                if tokens:
                    token_matches = base_query.limit(2000).all()

                    existing_ids = {
                        result["id"]
                        for result in results
                    }

                    for player in token_matches:
                        if len(results) >= limit:
                            break

                        if getattr(player, "id", None) in existing_ids:
                            continue

                        player_name = getattr(player, "full_name", "") or ""
                        normalized_player = normalize_text(player_name)

                        if all(token in normalized_player for token in tokens):
                            results.append(
                                player_to_search_result(
                                    player=player,
                                    confidence=78,
                                    match_type="all_tokens",
                                )
                            )

            results.sort(
                key=lambda item: item.get("confidence", 0),
                reverse=True,
            )

            return results[:limit]

    except Exception:
        return []


def resolve_player(
    player_name: str,
) -> PlayerResolution:
    matches = search_players_by_name(
        query=player_name,
        limit=DEFAULT_PLAYER_SEARCH_LIMIT,
    )

    if not matches:
        return PlayerResolution(
            status=KNOWLEDGE_STATUS_NOT_FOUND,
            matched_name=None,
            match_type="no_match",
            confidence=0,
            candidates=[],
        )

    best_match = matches[0]

    return PlayerResolution(
        status=KNOWLEDGE_STATUS_READY,
        player_id=best_match.get("player_id"),
        mlb_player_id=best_match.get("mlb_player_id"),
        full_name=best_match.get("full_name"),
        matched_name=best_match.get("full_name"),
        match_type=best_match.get("match_type"),
        confidence=best_match.get("confidence", 0),
        candidates=matches,
    )


def get_player_by_database_id(
    database_session,
    player_id: int | None,
):
    if player_id is None or Player is None:
        return None

    try:
        return (
            database_session.query(Player)
            .filter(Player.id == player_id)
            .first()
        )

    except Exception:
        return None


def get_player_by_mlb_id(
    database_session,
    mlb_player_id: int | None,
):
    if mlb_player_id is None or Player is None:
        return None

    try:
        return (
            database_session.query(Player)
            .filter(Player.mlb_player_id == mlb_player_id)
            .first()
        )

    except Exception:
        return None


# ============================================================
# SECTION 09 - QUERY HELPERS
# ============================================================

def build_player_identity_conditions(
    model,
    player,
) -> list[Any]:
    conditions = []

    player_id = getattr(player, "id", None)
    mlb_player_id = getattr(player, "mlb_player_id", None)
    full_name = getattr(player, "full_name", None)

    try:
        if player_id is not None and hasattr(model, "player_id"):
            conditions.append(
                model.player_id == player_id,
            )

        if mlb_player_id is not None and hasattr(model, "mlb_player_id"):
            conditions.append(
                model.mlb_player_id == mlb_player_id,
            )

        if full_name and hasattr(model, "player_name"):
            conditions.append(
                model.player_name == full_name,
            )

    except Exception:
        return []

    return conditions


def apply_player_filter(
    query,
    model,
    player,
):
    conditions = build_player_identity_conditions(
        model=model,
        player=player,
    )

    if not conditions:
        return query.filter(False)

    if len(conditions) == 1:
        return query.filter(
            conditions[0],
        )

    if or_ is None:
        return query.filter(
            conditions[0],
        )

    return query.filter(
        or_(*conditions),
    )


def apply_season_filter(
    query,
    model,
    season: int | None,
):
    if season is None:
        return query

    if not hasattr(model, "season"):
        return query

    try:
        return query.filter(
            model.season == season,
        )

    except Exception:
        return query


def order_latest_first(
    query,
    model,
):
    try:
        if hasattr(model, "season"):
            query = query.order_by(
                model.season.desc(),
            )

        if hasattr(model, "created_at"):
            query = query.order_by(
                model.created_at.desc(),
            )

        if hasattr(model, "id"):
            query = query.order_by(
                model.id.desc(),
            )

        return query

    except Exception:
        return query


def get_latest_player_row(
    database_session,
    model,
    player,
    season: int | None = None,
):
    if model is None or player is None:
        return None

    try:
        query = database_session.query(model)

        query = apply_player_filter(
            query=query,
            model=model,
            player=player,
        )

        query = apply_season_filter(
            query=query,
            model=model,
            season=season,
        )

        query = order_latest_first(
            query=query,
            model=model,
        )

        return query.first()

    except Exception:
        return None


def get_player_rows(
    database_session,
    model,
    player,
    season: int | None = None,
    limit: int = 25,
) -> list[Any]:
    if model is None or player is None:
        return []

    try:
        query = database_session.query(model)

        query = apply_player_filter(
            query=query,
            model=model,
            player=player,
        )

        query = apply_season_filter(
            query=query,
            model=model,
            season=season,
        )

        query = order_latest_first(
            query=query,
            model=model,
        )

        return query.limit(limit).all()

    except Exception:
        return []


def get_team_plate_discipline_row(
    database_session,
    team,
    season: int | None = None,
):
    if TeamPlateDiscipline is None or team is None:
        return None

    try:
        query = database_session.query(TeamPlateDiscipline)

        conditions = []

        team_id = getattr(team, "id", None)
        mlb_team_id = getattr(team, "mlb_team_id", None)
        team_name = getattr(team, "name", None)
        abbreviation = getattr(team, "abbreviation", None)

        if team_id is not None:
            conditions.append(
                TeamPlateDiscipline.team_id == team_id,
            )

        if mlb_team_id is not None:
            conditions.append(
                TeamPlateDiscipline.mlb_team_id == mlb_team_id,
            )

        if team_name:
            conditions.append(
                TeamPlateDiscipline.team_name == team_name,
            )

        if abbreviation:
            conditions.append(
                TeamPlateDiscipline.team_abbreviation == abbreviation,
            )

        if not conditions:
            return None

        if len(conditions) == 1:
            query = query.filter(
                conditions[0],
            )

        elif or_ is not None:
            query = query.filter(
                or_(*conditions),
            )

        else:
            query = query.filter(
                conditions[0],
            )

        if season is not None:
            query = query.filter(
                TeamPlateDiscipline.season == season,
            )

        query = order_latest_first(
            query=query,
            model=TeamPlateDiscipline,
        )

        return query.first()

    except Exception:
        return None


# ============================================================
# SECTION 10 - IDENTITY AND CONTEXT BUILDERS
# ============================================================

def build_player_identity(
    player,
) -> dict[str, Any]:
    if player is None:
        return {}

    team = None

    try:
        team = getattr(player, "team", None)
    except Exception:
        team = None

    return {
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
        "team": {
            "team_id": getattr(team, "id", None) if team else None,
            "mlb_team_id": getattr(team, "mlb_team_id", None) if team else None,
            "name": getattr(team, "name", None) if team else None,
            "abbreviation": getattr(team, "abbreviation", None) if team else None,
            "league": getattr(team, "league", None) if team else None,
            "division": getattr(team, "division", None) if team else None,
            "venue": getattr(team, "venue", None) if team else None,
        },
    }


def build_roster_context(
    database_session,
    player,
    limit: int = 5,
) -> list[dict[str, Any]]:
    if RosterEntry is None or player is None:
        return []

    try:
        rows = (
            database_session.query(RosterEntry)
            .filter(RosterEntry.player_id == player.id)
            .order_by(
                RosterEntry.season.desc(),
                RosterEntry.id.desc(),
            )
            .limit(limit)
            .all()
        )

        return [
            compact_row(row) or {}
            for row in rows
        ]

    except Exception:
        return []


# ============================================================
# SECTION 11 - WAREHOUSE DATASET BUILDER
# ============================================================

def build_player_warehouse_data(
    database_session,
    player,
    season: int | None = None,
    include_recent_games: bool = True,
    include_statcast_events: bool = False,
) -> dict[str, Any]:
    season_stats = get_latest_player_row(
        database_session,
        PlayerSeasonStat,
        player,
        season,
    )

    advanced_batting = get_latest_player_row(
        database_session,
        PlayerAdvancedBattingStat,
        player,
        season,
    )

    percentiles = get_latest_player_row(
        database_session,
        PlayerPercentileRanking,
        player,
        season,
    )

    pitch_arsenal_rows = get_player_rows(
        database_session,
        PlayerPitchArsenal,
        player,
        season,
        limit=DEFAULT_PITCH_ARSENAL_LIMIT,
    )

    pitch_tempo = get_latest_player_row(
        database_session,
        PlayerPitchTempo,
        player,
        season,
    )

    batted_ball = get_latest_player_row(
        database_session,
        PlayerBattedBallProfile,
        player,
        season,
    )

    batting_stance = get_latest_player_row(
        database_session,
        PlayerBattingStance,
        player,
        season,
    )

    home_run_profile = get_latest_player_row(
        database_session,
        PlayerHomeRunProfile,
        player,
        season,
    )

    team = None

    try:
        team = player.team
    except Exception:
        team = None

    team_plate_discipline = get_team_plate_discipline_row(
        database_session,
        team=team,
        season=season,
    )

    game_log_rows: list[Any] = []

    if include_recent_games:
        game_log_rows = get_player_rows(
            database_session,
            PlayerGameStat,
            player,
            season,
            limit=DEFAULT_RECENT_GAME_LIMIT,
        )

    statcast_event_rows: list[Any] = []

    if include_statcast_events:
        statcast_event_rows = get_player_rows(
            database_session,
            StatcastEvent,
            player,
            season,
            limit=25,
        )

    prediction_rows = get_player_rows(
        database_session,
        PredictionResult,
        player,
        season,
        limit=DEFAULT_PREDICTION_HISTORY_LIMIT,
    )

    return {
        DATASET_SEASON_STATS: compact_row(season_stats),
        DATASET_ADVANCED_BATTING: compact_row(advanced_batting),
        DATASET_PERCENTILE_RANKINGS: compact_row(percentiles),
        DATASET_PITCH_ARSENAL: [
            compact_row(row) or {}
            for row in pitch_arsenal_rows
        ],
        DATASET_PITCH_TEMPO: compact_row(pitch_tempo),
        DATASET_BATTED_BALL_PROFILE: compact_row(batted_ball),
        DATASET_BATTING_STANCE: compact_row(batting_stance),
        DATASET_HOME_RUN_PROFILE: compact_row(home_run_profile),
        DATASET_TEAM_PLATE_DISCIPLINE: compact_row(team_plate_discipline),
        DATASET_GAME_LOGS: [
            compact_row(row) or {}
            for row in game_log_rows
        ],
        DATASET_STATCAST_EVENTS: [
            compact_row(row) or {}
            for row in statcast_event_rows
        ],
        DATASET_PREDICTION_HISTORY: [
            compact_row(row) or {}
            for row in prediction_rows
        ],
    }


# ============================================================
# SECTION 12 - DATA AVAILABILITY AND QUALITY
# ============================================================

def dataset_has_value(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, list):
        return len(value) > 0

    if isinstance(value, dict):
        return any(
            item_value not in [None, "", [], {}]
            for item_value in value.values()
        )

    return True


def build_data_availability(
    identity: dict[str, Any],
    roster_context: list[dict[str, Any]],
    warehouse_data: dict[str, Any],
) -> dict[str, Any]:
    availability = {
        DATASET_PLAYER_IDENTITY: dataset_has_value(identity),
        DATASET_TEAM_CONTEXT: dataset_has_value(identity.get("team")),
        DATASET_ROSTER_CONTEXT: dataset_has_value(roster_context),
    }

    for dataset_name, dataset_value in warehouse_data.items():
        availability[dataset_name] = dataset_has_value(dataset_value)

    available_datasets = [
        dataset_name
        for dataset_name, is_available in availability.items()
        if is_available
    ]

    missing_datasets = [
        dataset_name
        for dataset_name, is_available in availability.items()
        if not is_available
    ]

    coverage_ratio = (
        len(available_datasets) / len(availability)
        if availability
        else 0
    )

    return {
        "availability": availability,
        "available_datasets": available_datasets,
        "missing_datasets": missing_datasets,
        "available_count": len(available_datasets),
        "missing_count": len(missing_datasets),
        "total_dataset_count": len(availability),
        "coverage_ratio": round(coverage_ratio, 3),
        "coverage_percent": round(coverage_ratio * 100, 1),
        "knowledge_status": (
            KNOWLEDGE_STATUS_READY
            if coverage_ratio >= 0.65
            else KNOWLEDGE_STATUS_PARTIAL
        ),
    }


def build_data_quality_notes(
    availability_report: dict[str, Any],
) -> list[str]:
    notes = []

    missing = set(
        availability_report.get("missing_datasets", []),
    )

    if DATASET_ADVANCED_BATTING in missing:
        notes.append(
            "Advanced batting data is missing, reducing hit/home-run model quality."
        )

    if DATASET_PERCENTILE_RANKINGS in missing:
        notes.append(
            "Percentile ranking data is missing, reducing Statcast comparison quality."
        )

    if DATASET_BATTED_BALL_PROFILE in missing:
        notes.append(
            "Batted-ball profile data is missing, reducing exit-velocity and barrel analysis."
        )

    if DATASET_HOME_RUN_PROFILE in missing:
        notes.append(
            "Home run profile data is missing, reducing power-outcome analysis."
        )

    if DATASET_TEAM_PLATE_DISCIPLINE in missing:
        notes.append(
            "Team plate-discipline data is missing, reducing contextual plate approach analysis."
        )

    if DATASET_GAME_LOGS in missing:
        notes.append(
            "Recent game logs are missing, so rolling-form analysis is not available yet."
        )

    if not notes:
        notes.append(
            "Core player knowledge datasets are available."
        )

    return notes


# ============================================================
# SECTION 13 - FEATURE ENGINEERING HELPERS
# ============================================================

def get_metric(
    data: dict[str, Any] | None,
    *names: str,
) -> Any:
    if not data:
        return None

    for name in names:
        if name in data and data[name] is not None:
            return data[name]

    return None


def build_power_score(
    warehouse_data: dict[str, Any],
) -> float | None:
    home_run = warehouse_data.get(DATASET_HOME_RUN_PROFILE) or {}
    batted_ball = warehouse_data.get(DATASET_BATTED_BALL_PROFILE) or {}
    advanced = warehouse_data.get(DATASET_ADVANCED_BATTING) or {}
    percentile = warehouse_data.get(DATASET_PERCENTILE_RANKINGS) or {}

    scores = [
        metric_to_score(get_metric(home_run, "home_runs"), 0, 60),
        metric_to_score(get_metric(home_run, "average_home_run_distance"), 350, 440),
        metric_to_score(get_metric(home_run, "average_exit_velocity"), 85, 100),
        metric_to_score(get_metric(batted_ball, "average_exit_velocity"), 85, 98),
        metric_to_score(get_metric(batted_ball, "max_exit_velocity"), 100, 120),
        percent_to_score(get_metric(batted_ball, "barrel_percent")),
        percent_to_score(get_metric(batted_ball, "hard_hit_percent")),
        percent_to_score(get_metric(percentile, "barrel_percentile")),
        percent_to_score(get_metric(percentile, "hard_hit_percentile")),
        percent_to_score(get_metric(percentile, "exit_velocity_percentile")),
        percent_to_score(get_metric(advanced, "barrel_batted_rate")),
        percent_to_score(get_metric(advanced, "hard_hit_percent")),
    ]

    return safe_round(
        average_available(scores),
        2,
    )


def build_contact_score(
    warehouse_data: dict[str, Any],
) -> float | None:
    season = warehouse_data.get(DATASET_SEASON_STATS) or {}
    advanced = warehouse_data.get(DATASET_ADVANCED_BATTING) or {}
    batted_ball = warehouse_data.get(DATASET_BATTED_BALL_PROFILE) or {}
    percentile = warehouse_data.get(DATASET_PERCENTILE_RANKINGS) or {}

    scores = [
        metric_to_score(get_metric(season, "batting_average"), 0.180, 0.340),
        metric_to_score(get_metric(season, "on_base_percentage"), 0.260, 0.450),
        metric_to_score(get_metric(advanced, "woba"), 0.250, 0.450),
        metric_to_score(get_metric(advanced, "expected_woba"), 0.250, 0.450),
        metric_to_score(get_metric(batted_ball, "expected_batting_average"), 0.180, 0.340),
        percent_to_score(get_metric(percentile, "xba_percentile")),
        percent_to_score(get_metric(percentile, "xwoba_percentile")),
        metric_to_score(get_metric(advanced, "strikeout_percent"), 35, 10, invert=False),
        metric_to_score(get_metric(advanced, "whiff_percent"), 40, 10, invert=False),
    ]

    return safe_round(
        average_available(scores),
        2,
    )


def build_discipline_score(
    warehouse_data: dict[str, Any],
) -> float | None:
    advanced = warehouse_data.get(DATASET_ADVANCED_BATTING) or {}
    percentile = warehouse_data.get(DATASET_PERCENTILE_RANKINGS) or {}
    team_discipline = warehouse_data.get(DATASET_TEAM_PLATE_DISCIPLINE) or {}

    scores = [
        metric_to_score(get_metric(advanced, "walk_percent"), 3, 18),
        metric_to_score(get_metric(advanced, "strikeout_percent"), 35, 10, invert=False),
        percent_to_score(get_metric(percentile, "walk_percentile")),
        percent_to_score(get_metric(percentile, "chase_percentile")),
        percent_to_score(get_metric(percentile, "strikeout_percentile")),
        metric_to_score(get_metric(team_discipline, "chase_percent"), 35, 20, invert=False),
        metric_to_score(get_metric(team_discipline, "zone_contact_percent"), 75, 90),
        metric_to_score(get_metric(team_discipline, "whiff_percent"), 30, 18, invert=False),
    ]

    return safe_round(
        average_available(scores),
        2,
    )


def build_batted_ball_score(
    warehouse_data: dict[str, Any],
) -> float | None:
    batted_ball = warehouse_data.get(DATASET_BATTED_BALL_PROFILE) or {}
    percentile = warehouse_data.get(DATASET_PERCENTILE_RANKINGS) or {}

    scores = [
        metric_to_score(get_metric(batted_ball, "average_exit_velocity"), 85, 98),
        metric_to_score(get_metric(batted_ball, "max_exit_velocity"), 100, 120),
        metric_to_score(get_metric(batted_ball, "launch_angle"), 0, 25),
        percent_to_score(get_metric(batted_ball, "barrel_percent")),
        percent_to_score(get_metric(batted_ball, "hard_hit_percent")),
        percent_to_score(get_metric(batted_ball, "sweet_spot_percent")),
        metric_to_score(get_metric(batted_ball, "expected_slugging"), 0.300, 0.650),
        metric_to_score(get_metric(batted_ball, "expected_woba"), 0.250, 0.450),
        percent_to_score(get_metric(percentile, "xslg_percentile")),
        percent_to_score(get_metric(percentile, "hard_hit_percentile")),
    ]

    return safe_round(
        average_available(scores),
        2,
    )


def build_percentile_score(
    warehouse_data: dict[str, Any],
) -> float | None:
    percentile = warehouse_data.get(DATASET_PERCENTILE_RANKINGS) or {}

    scores = [
        percent_to_score(get_metric(percentile, "xwoba_percentile")),
        percent_to_score(get_metric(percentile, "xba_percentile")),
        percent_to_score(get_metric(percentile, "xslg_percentile")),
        percent_to_score(get_metric(percentile, "barrel_percentile")),
        percent_to_score(get_metric(percentile, "hard_hit_percentile")),
        percent_to_score(get_metric(percentile, "exit_velocity_percentile")),
        percent_to_score(get_metric(percentile, "whiff_percentile")),
        percent_to_score(get_metric(percentile, "chase_percentile")),
        percent_to_score(get_metric(percentile, "walk_percentile")),
        percent_to_score(get_metric(percentile, "strikeout_percentile")),
    ]

    return safe_round(
        average_available(scores),
        2,
    )


def build_data_coverage_score(
    availability_report: dict[str, Any],
) -> float:
    return safe_round(
        availability_report.get("coverage_percent", 0),
        2,
    ) or 0.0


def build_player_feature_vector(
    warehouse_data: dict[str, Any],
    availability_report: dict[str, Any],
) -> dict[str, Any]:
    power_score = build_power_score(
        warehouse_data,
    )

    contact_score = build_contact_score(
        warehouse_data,
    )

    discipline_score = build_discipline_score(
        warehouse_data,
    )

    batted_ball_score = build_batted_ball_score(
        warehouse_data,
    )

    percentile_score = build_percentile_score(
        warehouse_data,
    )

    data_coverage_score = build_data_coverage_score(
        availability_report,
    )

    weighted_components = {
        "power_score": power_score,
        "contact_score": contact_score,
        "discipline_score": discipline_score,
        "batted_ball_score": batted_ball_score,
        "statcast_percentile_score": percentile_score,
        "data_coverage_score": data_coverage_score,
    }

    weighted_values = []

    for key, weight in FEATURE_SCORE_WEIGHTS.items():
        component_value = weighted_components.get(key)

        if component_value is None:
            continue

        weighted_values.append(
            component_value * weight,
        )

    overall_feature_score = (
        sum(weighted_values)
        if weighted_values
        else None
    )

    return {
        "power_score": power_score,
        "contact_score": contact_score,
        "discipline_score": discipline_score,
        "batted_ball_score": batted_ball_score,
        "statcast_percentile_score": percentile_score,
        "data_coverage_score": data_coverage_score,
        "overall_feature_score": safe_round(overall_feature_score, 2),
        "feature_weights": FEATURE_SCORE_WEIGHTS,
    }


# ============================================================
# SECTION 14 - OUTCOME CONTEXT BUILDER
# ============================================================

def build_outcome_context(
    outcome: str | None,
    feature_vector: dict[str, Any],
    warehouse_data: dict[str, Any],
) -> dict[str, Any]:
    selected_outcome = outcome or "home_run"

    outcome_config = SUPPORTED_PLAYER_OUTCOMES.get(
        selected_outcome,
        SUPPORTED_PLAYER_OUTCOMES["home_run"],
    )

    feature_group = outcome_config["feature_group"]

    if selected_outcome == "home_run":
        estimated_readiness_score = average_available(
            [
                feature_vector.get("power_score"),
                feature_vector.get("batted_ball_score"),
                feature_vector.get("statcast_percentile_score"),
                feature_vector.get("data_coverage_score"),
            ]
        )

    elif selected_outcome == "hit":
        estimated_readiness_score = average_available(
            [
                feature_vector.get("contact_score"),
                feature_vector.get("discipline_score"),
                feature_vector.get("batted_ball_score"),
                feature_vector.get("data_coverage_score"),
            ]
        )

    elif selected_outcome == "strikeout":
        estimated_readiness_score = average_available(
            [
                feature_vector.get("discipline_score"),
                feature_vector.get("statcast_percentile_score"),
                feature_vector.get("data_coverage_score"),
            ]
        )

    else:
        estimated_readiness_score = average_available(
            [
                feature_vector.get("overall_feature_score"),
                feature_vector.get("data_coverage_score"),
            ]
        )

    return {
        "outcome": selected_outcome,
        "label": outcome_config["label"],
        "feature_group": feature_group,
        "primary_features": outcome_config["primary_features"],
        "prediction_feature_readiness_score": safe_round(
            estimated_readiness_score,
            2,
        ),
        "model_ready": (
            estimated_readiness_score is not None
            and estimated_readiness_score >= 55
        ),
        "note": (
            "Feature context is ready for baseline probability modeling."
            if estimated_readiness_score is not None and estimated_readiness_score >= 55
            else "Feature context is incomplete. Import more warehouse data before trusting prediction outputs."
        ),
    }


# ============================================================
# SECTION 15 - INTELLIGENCE SUMMARY BUILDER
# ============================================================

def classify_player_archetype(
    identity: dict[str, Any],
    feature_vector: dict[str, Any],
) -> str:
    power_score = feature_vector.get("power_score")
    contact_score = feature_vector.get("contact_score")
    discipline_score = feature_vector.get("discipline_score")

    if power_score is not None and power_score >= 75:
        if discipline_score is not None and discipline_score >= 65:
            return "Power hitter with strong underlying plate-discipline indicators."

        return "Power-oriented hitter with Statcast impact indicators."

    if contact_score is not None and contact_score >= 75:
        return "Contact-oriented hitter with strong hit-profile indicators."

    if discipline_score is not None and discipline_score >= 75:
        return "Plate-discipline driven hitter with strong approach indicators."

    position = identity.get("position") or ""

    if "Pitcher" in position:
        return "Pitcher profile. Pitch arsenal and tempo data should drive the analysis."

    return "General MLB player profile with partial warehouse context."


def build_strength_indicators(
    feature_vector: dict[str, Any],
) -> list[str]:
    indicators = []

    if (feature_vector.get("power_score") or 0) >= 70:
        indicators.append("Power indicators are above baseline.")

    if (feature_vector.get("contact_score") or 0) >= 70:
        indicators.append("Contact indicators are above baseline.")

    if (feature_vector.get("discipline_score") or 0) >= 70:
        indicators.append("Plate-discipline indicators are above baseline.")

    if (feature_vector.get("batted_ball_score") or 0) >= 70:
        indicators.append("Batted-ball quality indicators are strong.")

    if (feature_vector.get("statcast_percentile_score") or 0) >= 70:
        indicators.append("Statcast percentile profile is strong.")

    if not indicators:
        indicators.append("No dominant strength indicator is available yet.")

    return indicators


def build_risk_indicators(
    feature_vector: dict[str, Any],
    availability_report: dict[str, Any],
) -> list[str]:
    indicators = []

    if (feature_vector.get("data_coverage_score") or 0) < 50:
        indicators.append("Data coverage is limited; model confidence should remain conservative.")

    if feature_vector.get("contact_score") is not None and feature_vector["contact_score"] < 45:
        indicators.append("Contact score is below baseline.")

    if feature_vector.get("discipline_score") is not None and feature_vector["discipline_score"] < 45:
        indicators.append("Plate-discipline score is below baseline.")

    if DATASET_GAME_LOGS in availability_report.get("missing_datasets", []):
        indicators.append("Recent game logs are missing; rolling-form analysis is not active.")

    if not indicators:
        indicators.append("No major risk indicator is available from the loaded warehouse data.")

    return indicators


def build_player_intelligence_summary(
    identity: dict[str, Any],
    feature_vector: dict[str, Any],
    availability_report: dict[str, Any],
) -> dict[str, Any]:
    archetype = classify_player_archetype(
        identity=identity,
        feature_vector=feature_vector,
    )

    strengths = build_strength_indicators(
        feature_vector=feature_vector,
    )

    risks = build_risk_indicators(
        feature_vector=feature_vector,
        availability_report=availability_report,
    )

    return {
        "archetype": archetype,
        "strength_indicators": strengths,
        "risk_indicators": risks,
        "coverage_percent": availability_report.get("coverage_percent"),
        "knowledge_status": availability_report.get("knowledge_status"),
    }


# ============================================================
# SECTION 16 - FULL PLAYER KNOWLEDGE REPORT
# ============================================================

def build_player_knowledge_report(
    player_name: str,
    season: int | None = None,
    outcome: str | None = None,
    include_raw: bool = False,
    include_prediction_features: bool = True,
    include_recent_games: bool = True,
    include_statcast_events: bool = False,
) -> dict[str, Any]:
    if not database_available():
        return build_database_unavailable_report()

    resolution = resolve_player(
        player_name,
    )

    if resolution.status != KNOWLEDGE_STATUS_READY:
        return {
            "status": KNOWLEDGE_STATUS_NOT_FOUND,
            "version": PLAYER_KNOWLEDGE_VERSION,
            "query": player_name,
            "season": season,
            "resolution": {
                "status": resolution.status,
                "candidates": resolution.candidates or [],
                "error": resolution.error,
            },
            "message": (
                f"No player found for: {player_name}. "
                "Run player/team/roster ingestion first or check spelling."
            ),
        }

    try:
        with managed_database_session() as database_session:
            player = get_player_by_database_id(
                database_session,
                resolution.player_id,
            )

            if player is None:
                return {
                    "status": KNOWLEDGE_STATUS_NOT_FOUND,
                    "version": PLAYER_KNOWLEDGE_VERSION,
                    "query": player_name,
                    "season": season,
                    "resolution": resolution.__dict__,
                    "message": "Player was resolved but could not be loaded from the database.",
                }

            identity = build_player_identity(
                player,
            )

            roster_context = build_roster_context(
                database_session=database_session,
                player=player,
            )

            warehouse_data = build_player_warehouse_data(
                database_session=database_session,
                player=player,
                season=season,
                include_recent_games=include_recent_games,
                include_statcast_events=include_statcast_events,
            )

            availability_report = build_data_availability(
                identity=identity,
                roster_context=roster_context,
                warehouse_data=warehouse_data,
            )

            quality_notes = build_data_quality_notes(
                availability_report,
            )

            feature_vector = build_player_feature_vector(
                warehouse_data=warehouse_data,
                availability_report=availability_report,
            )

            outcome_context = build_outcome_context(
                outcome=outcome,
                feature_vector=feature_vector,
                warehouse_data=warehouse_data,
            )

            intelligence_summary = build_player_intelligence_summary(
                identity=identity,
                feature_vector=feature_vector,
                availability_report=availability_report,
            )

            report = {
                "status": availability_report.get("knowledge_status", KNOWLEDGE_STATUS_PARTIAL),
                "version": PLAYER_KNOWLEDGE_VERSION,
                "query": player_name,
                "season": season,
                "outcome": outcome_context,
                "resolution": {
                    "status": resolution.status,
                    "player_id": resolution.player_id,
                    "mlb_player_id": resolution.mlb_player_id,
                    "full_name": resolution.full_name,
                    "match_type": resolution.match_type,
                    "confidence": resolution.confidence,
                    "candidates": resolution.candidates or [],
                },
                "identity": identity,
                "roster_context": roster_context,
                "warehouse_data": warehouse_data,
                "availability": availability_report,
                "quality_notes": quality_notes,
                "feature_vector": feature_vector if include_prediction_features else {},
                "intelligence_summary": intelligence_summary,
                "message": "Player knowledge report generated from database and warehouse context.",
            }

            if not include_raw:
                report["raw_omitted"] = True

            return report

    except Exception as error:
        return {
            "status": KNOWLEDGE_STATUS_ERROR,
            "version": PLAYER_KNOWLEDGE_VERSION,
            "query": player_name,
            "season": season,
            "resolution": resolution.__dict__,
            "error": str(error),
            "message": "Player knowledge report failed during database assembly.",
        }


# ============================================================
# SECTION 17 - CHATBOT RESPONSE FORMATTERS
# ============================================================

def format_metric_line(
    label: str,
    value: Any,
    suffix: str = "",
) -> str | None:
    if value is None:
        return None

    return f"- {label}: {value}{suffix}"


def format_player_knowledge_answer(
    report: dict[str, Any],
    detail_level: str = "standard",
) -> str:
    status = report.get("status")

    if status == KNOWLEDGE_STATUS_DATABASE_UNAVAILABLE:
        return (
            "The player knowledge database is not available right now. "
            "Verify the database connection and ORM imports."
        )

    if status == KNOWLEDGE_STATUS_NOT_FOUND:
        candidates = report.get("resolution", {}).get("candidates", [])

        if candidates:
            candidate_names = [
                candidate.get("full_name") or candidate.get("name")
                for candidate in candidates[:5]
            ]

            return (
                f"I could not find an exact player match for {report.get('query')}.\n\n"
                "Closest candidates:\n"
                + "\n".join(f"- {name}" for name in candidate_names if name)
            )

        return report.get(
            "message",
            "I could not find that player in the database.",
        )

    if status == KNOWLEDGE_STATUS_ERROR:
        return (
            "I found the player request, but the player knowledge assembly failed.\n\n"
            f"Error: {report.get('error')}"
        )

    identity = report.get("identity", {}) or {}
    team = identity.get("team", {}) or {}
    warehouse = report.get("warehouse_data", {}) or {}
    feature_vector = report.get("feature_vector", {}) or {}
    intelligence = report.get("intelligence_summary", {}) or {}
    availability = report.get("availability", {}) or {}
    outcome = report.get("outcome", {}) or {}

    advanced = warehouse.get(DATASET_ADVANCED_BATTING) or {}
    batted_ball = warehouse.get(DATASET_BATTED_BALL_PROFILE) or {}
    home_run = warehouse.get(DATASET_HOME_RUN_PROFILE) or {}
    percentiles = warehouse.get(DATASET_PERCENTILE_RANKINGS) or {}

    lines = [
        f"{identity.get('full_name', 'Player')}",
        "",
        f"Team: {team.get('name') or 'Unknown'}",
        f"Position: {identity.get('position') or 'Unknown'}",
        f"Bats/Throws: {identity.get('bats') or 'N/A'} / {identity.get('throws') or 'N/A'}",
        "",
        "Player Intelligence",
        f"- Archetype: {intelligence.get('archetype')}",
        f"- Knowledge Coverage: {availability.get('coverage_percent')}%",
        f"- Outcome Context: {outcome.get('label')}",
        f"- Model Ready: {outcome.get('model_ready')}",
        "",
        "Feature Scores",
    ]

    for label, key in [
        ("Power", "power_score"),
        ("Contact", "contact_score"),
        ("Discipline", "discipline_score"),
        ("Batted Ball", "batted_ball_score"),
        ("Statcast Percentile", "statcast_percentile_score"),
        ("Overall Feature", "overall_feature_score"),
    ]:
        line = format_metric_line(
            label,
            feature_vector.get(key),
        )

        if line:
            lines.append(line)

    lines.extend(
        [
            "",
            "Key Loaded Metrics",
        ]
    )

    key_metric_lines = [
        format_metric_line("PA", advanced.get("plate_appearances")),
        format_metric_line("K%", advanced.get("strikeout_percent"), "%"),
        format_metric_line("BB%", advanced.get("walk_percent"), "%"),
        format_metric_line("wOBA", advanced.get("woba")),
        format_metric_line("xwOBA", advanced.get("expected_woba")),
        format_metric_line("Avg EV", batted_ball.get("average_exit_velocity"), " mph"),
        format_metric_line("Max EV", batted_ball.get("max_exit_velocity"), " mph"),
        format_metric_line("Barrel%", batted_ball.get("barrel_percent"), "%"),
        format_metric_line("Hard Hit%", batted_ball.get("hard_hit_percent"), "%"),
        format_metric_line("HR", home_run.get("home_runs")),
        format_metric_line("xwOBA Percentile", percentiles.get("xwoba_percentile")),
        format_metric_line("Barrel Percentile", percentiles.get("barrel_percentile")),
    ]

    for line in key_metric_lines:
        if line:
            lines.append(line)

    if detail_level in ["standard", "detailed"]:
        lines.extend(
            [
                "",
                "Strengths",
            ]
        )

        for strength in intelligence.get("strength_indicators", []):
            lines.append(f"- {strength}")

        lines.extend(
            [
                "",
                "Risks / Missing Data",
            ]
        )

        for risk in intelligence.get("risk_indicators", []):
            lines.append(f"- {risk}")

    if detail_level == "detailed":
        lines.extend(
            [
                "",
                "Missing Datasets",
            ]
        )

        for dataset_name in availability.get("missing_datasets", []):
            lines.append(f"- {dataset_name}")

    return "\n".join(
        str(line)
        for line in lines
        if line is not None
    )


def answer_player_question(
    player_name: str,
    season: int | None = None,
    outcome: str | None = None,
    detail_level: str = "standard",
) -> str:
    report = build_player_knowledge_report(
        player_name=player_name,
        season=season,
        outcome=outcome,
        include_prediction_features=True,
        include_recent_games=True,
        include_statcast_events=False,
    )

    return format_player_knowledge_answer(
        report=report,
        detail_level=detail_level,
    )


# ============================================================
# SECTION 18 - PLAYER EXPLORER CARD FORMAT
# ============================================================

def build_player_explorer_card(
    player_name: str,
    season: int | None = None,
) -> dict[str, Any]:
    report = build_player_knowledge_report(
        player_name=player_name,
        season=season,
        include_prediction_features=True,
        include_recent_games=True,
        include_statcast_events=False,
    )

    if report.get("status") in [
        KNOWLEDGE_STATUS_NOT_FOUND,
        KNOWLEDGE_STATUS_DATABASE_UNAVAILABLE,
        KNOWLEDGE_STATUS_ERROR,
    ]:
        return {
            "status": report.get("status"),
            "message": report.get("message"),
            "error": report.get("error"),
            "query": player_name,
        }

    identity = report.get("identity", {}) or {}
    warehouse = report.get("warehouse_data", {}) or {}
    feature_vector = report.get("feature_vector", {}) or {}
    intelligence = report.get("intelligence_summary", {}) or {}
    availability = report.get("availability", {}) or {}

    season_stats = warehouse.get(DATASET_SEASON_STATS) or {}
    advanced = warehouse.get(DATASET_ADVANCED_BATTING) or {}
    batted_ball = warehouse.get(DATASET_BATTED_BALL_PROFILE) or {}
    home_run = warehouse.get(DATASET_HOME_RUN_PROFILE) or {}

    return {
        "status": report.get("status"),
        "player": identity,
        "headline": {
            "name": identity.get("full_name"),
            "team": (identity.get("team") or {}).get("name"),
            "position": identity.get("position"),
            "archetype": intelligence.get("archetype"),
        },
        "cards": {
            "avg": season_stats.get("batting_average"),
            "ops": season_stats.get("ops"),
            "home_runs": home_run.get("home_runs") or season_stats.get("home_runs"),
            "woba": advanced.get("woba"),
            "xwoba": advanced.get("expected_woba"),
            "barrel_percent": batted_ball.get("barrel_percent"),
            "hard_hit_percent": batted_ball.get("hard_hit_percent"),
            "average_exit_velocity": batted_ball.get("average_exit_velocity"),
            "power_score": feature_vector.get("power_score"),
            "contact_score": feature_vector.get("contact_score"),
            "overall_feature_score": feature_vector.get("overall_feature_score"),
        },
        "availability": availability,
        "feature_vector": feature_vector,
        "strengths": intelligence.get("strength_indicators", []),
        "risks": intelligence.get("risk_indicators", []),
        "quality_notes": report.get("quality_notes", []),
    }


# ============================================================
# SECTION 19 - PROBABILITY ENGINE FEATURE FORMAT
# ============================================================

def build_prediction_feature_context(
    player_name: str,
    outcome: str = "home_run",
    season: int | None = None,
) -> dict[str, Any]:
    report = build_player_knowledge_report(
        player_name=player_name,
        season=season,
        outcome=outcome,
        include_prediction_features=True,
        include_recent_games=True,
        include_statcast_events=False,
    )

    if report.get("status") in [
        KNOWLEDGE_STATUS_NOT_FOUND,
        KNOWLEDGE_STATUS_DATABASE_UNAVAILABLE,
        KNOWLEDGE_STATUS_ERROR,
    ]:
        return {
            "ready": False,
            "status": report.get("status"),
            "message": report.get("message"),
            "error": report.get("error"),
            "player_name": player_name,
            "outcome": outcome,
        }

    feature_vector = report.get("feature_vector", {}) or {}
    outcome_context = report.get("outcome", {}) or {}
    availability = report.get("availability", {}) or {}

    return {
        "ready": bool(outcome_context.get("model_ready")),
        "status": report.get("status"),
        "player_name": report.get("identity", {}).get("full_name"),
        "player_id": report.get("identity", {}).get("player_id"),
        "mlb_player_id": report.get("identity", {}).get("mlb_player_id"),
        "team": report.get("identity", {}).get("team"),
        "season": season,
        "outcome": outcome,
        "outcome_context": outcome_context,
        "feature_vector": feature_vector,
        "availability": availability,
        "warehouse_data": report.get("warehouse_data", {}),
        "quality_notes": report.get("quality_notes", []),
        "model_guidance": (
            "Use this context for baseline model calculation."
            if outcome_context.get("model_ready")
            else "Do not trust model output yet; warehouse features are incomplete."
        ),
    }


# ============================================================
# SECTION 20 - PLAYER COMPARISON
# ============================================================

def compare_players(
    player_names: list[str],
    season: int | None = None,
    outcome: str = "home_run",
) -> dict[str, Any]:
    reports = [
        build_player_knowledge_report(
            player_name=player_name,
            season=season,
            outcome=outcome,
            include_prediction_features=True,
            include_recent_games=True,
            include_statcast_events=False,
        )
        for player_name in player_names
    ]

    comparison_rows = []

    for report in reports:
        identity = report.get("identity", {}) or {}
        feature_vector = report.get("feature_vector", {}) or {}
        outcome_context = report.get("outcome", {}) or {}

        comparison_rows.append(
            {
                "query": report.get("query"),
                "status": report.get("status"),
                "player": identity.get("full_name"),
                "team": (identity.get("team") or {}).get("name"),
                "power_score": feature_vector.get("power_score"),
                "contact_score": feature_vector.get("contact_score"),
                "discipline_score": feature_vector.get("discipline_score"),
                "overall_feature_score": feature_vector.get("overall_feature_score"),
                "outcome_readiness": outcome_context.get("prediction_feature_readiness_score"),
                "model_ready": outcome_context.get("model_ready"),
            }
        )

    comparison_rows.sort(
        key=lambda item: item.get("overall_feature_score") or 0,
        reverse=True,
    )

    return {
        "status": KNOWLEDGE_STATUS_READY,
        "season": season,
        "outcome": outcome,
        "players": comparison_rows,
        "winner_by_feature_score": comparison_rows[0] if comparison_rows else None,
        "reports": reports,
    }


# ============================================================
# SECTION 21 - PUBLIC API COMPATIBILITY FUNCTIONS
# ============================================================

def get_player_knowledge(
    player_name: str,
    season: int | None = None,
    outcome: str | None = None,
) -> dict[str, Any]:
    return build_player_knowledge_report(
        player_name=player_name,
        season=season,
        outcome=outcome,
    )


def build_player_profile(
    player_name: str,
    season: int | None = None,
) -> dict[str, Any]:
    return build_player_explorer_card(
        player_name=player_name,
        season=season,
    )


def build_player_answer(
    player_name: str,
    season: int | None = None,
    outcome: str | None = None,
) -> str:
    return answer_player_question(
        player_name=player_name,
        season=season,
        outcome=outcome,
    )


def search_player_knowledge(
    query: str,
    limit: int = DEFAULT_PLAYER_SEARCH_LIMIT,
) -> dict[str, Any]:
    matches = search_players_by_name(
        query=query,
        limit=limit,
    )

    return {
        "query": query,
        "count": len(matches),
        "players": matches,
        "status": KNOWLEDGE_STATUS_READY if matches else KNOWLEDGE_STATUS_NOT_FOUND,
    }


# ============================================================
# SECTION 22 - LOCAL DIAGNOSTICS
# ============================================================

def run_player_knowledge_diagnostic(
    player_name: str = "Aaron Judge",
) -> dict[str, Any]:
    status = build_player_knowledge_system_status()

    report = build_player_knowledge_report(
        player_name=player_name,
        outcome="home_run",
    )

    return {
        "system_status": status,
        "sample_player": report,
    }


if __name__ == "__main__":
    diagnostic = run_player_knowledge_diagnostic()

    print(
        json.dumps(
            diagnostic,
            indent=2,
            default=str,
        )
    )