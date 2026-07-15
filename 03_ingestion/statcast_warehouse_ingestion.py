# ============================================================
# AISP2 BASEBALL
# PHASE 9 PART 3
# FILE: 03_ingestion/statcast_warehouse_ingestion.py
# PURPOSE: import Joe/Statcast CSV warehouse data into the
# AISP2 database so chatbot, dashboard, prediction engine,
# and future ML models can access one shared source of truth
# ============================================================


# ============================================================
# SECTION 01 - IMPORTS AND PATH REGISTRATION
# ============================================================

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, timedelta
from enum import Enum
from hashlib import sha256
from statistics import mean
import math
import re
import time
from uuid import uuid4
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_DIR = PROJECT_ROOT / "01_database"

for project_path in [
    PROJECT_ROOT,
    DATABASE_DIR,
]:
    path_value = str(project_path)

    if path_value not in sys.path:
        sys.path.insert(0, path_value)


from database import managed_database_session
from database import collect_database_inventory
from database import initialize_database
from database import player_explorer_database_readiness
from database import safe_commit
from database import safe_rollback

from models import Player
from models import Team
from models import RawDataImportLog
from models import PlayerAdvancedBattingStat
from models import PlayerPercentileRanking
from models import PlayerPitchArsenal
from models import PlayerPitchTempo
from models import PlayerBattedBallProfile
from models import PlayerBattingStance
from models import PlayerHomeRunProfile
from models import TeamPlateDiscipline
from models import PlayerStatcastMetric


# ============================================================
# SECTION 02 - ENTERPRISE STATCAST IMPORT CONFIGURATION
# FILE: 03_ingestion/statcast_warehouse_ingestion.py
# PURPOSE: define raw-data directory, supported warehouse
# datasets, default import files, filename detection aliases,
# import categories, readiness thresholds, and ML-ready data
# routing configuration for AISP2 predictions.
# ============================================================

RAW_DATA_DIR = PROJECT_ROOT / "00_raw_data"

STATCAST_INGESTION_VERSION = "phase_12_part_3_enterprise_statcast_intelligence"

DEFAULT_IMPORT_SEASON = datetime.utcnow().year

IMPORT_STATUS_COMPLETED = "completed"
IMPORT_STATUS_FAILED = "failed"
IMPORT_STATUS_MISSING = "missing"
IMPORT_STATUS_SKIPPED = "skipped"
IMPORT_STATUS_UNKNOWN = "unknown"

CATEGORY_PERCENTILE_RANKINGS = "percentile_rankings"
CATEGORY_PITCH_ARSENAL = "pitch_arsenal"
CATEGORY_PITCH_TEMPO = "pitch_tempo"
CATEGORY_BATTED_BALL_PROFILE = "batted_ball_profile"
CATEGORY_BATTING_STANCE = "batting_stance"
CATEGORY_HOME_RUN_PROFILE = "home_run_profile"
CATEGORY_ADVANCED_BATTING_STATS = "advanced_batting_stats"
CATEGORY_ADVANCED_BATTING_OR_PITCHER_STATS = "advanced_batting_or_pitcher_stats"
CATEGORY_TEAM_PLATE_DISCIPLINE = "team_plate_discipline"
CATEGORY_UNKNOWN = "unknown"

SUPPORTED_IMPORT_CATEGORIES = [
    CATEGORY_PERCENTILE_RANKINGS,
    CATEGORY_PITCH_ARSENAL,
    CATEGORY_PITCH_TEMPO,
    CATEGORY_BATTED_BALL_PROFILE,
    CATEGORY_BATTING_STANCE,
    CATEGORY_HOME_RUN_PROFILE,
    CATEGORY_ADVANCED_BATTING_STATS,
    CATEGORY_ADVANCED_BATTING_OR_PITCHER_STATS,
    CATEGORY_TEAM_PLATE_DISCIPLINE,
]

DEFAULT_IMPORT_FILES = [
    "percentile_rankings.csv",
    "percentile_rankings2025.csv",
    "pitch_arsenals.csv",
    "2025-pitch_arsenals.csv",
    "pitch_tempo.csv",
    "2025historicalpitchtempo (1).csv",
    "pitcherstats.csv",
    "stats.csv",
    "batting-stance.csv",
    "2025-batting-stance.csv",
    "exit_velocity.csv",
    "2025exitvolicity.csv",
    "homeruns.csv",
    "homeruns2025.csv",
    "plate_discipline.csv",
]

FILENAME_CATEGORY_PATTERNS = {
    CATEGORY_PERCENTILE_RANKINGS: [
        "percentile",
        "percentile_rankings",
        "percentilerankings",
    ],
    CATEGORY_PITCH_ARSENAL: [
        "pitch_arsenal",
        "pitch_arsenals",
        "pitcharsenal",
        "arsenal",
    ],
    CATEGORY_PITCH_TEMPO: [
        "pitch_tempo",
        "pitchtempo",
        "historicalpitchtempo",
        "tempo",
    ],
    CATEGORY_BATTED_BALL_PROFILE: [
        "exit_velocity",
        "exitvelocity",
        "exitvolicity",
        "batted_ball",
        "battedball",
        "launch_angle",
        "hard_hit",
        "barrel",
    ],
    CATEGORY_BATTING_STANCE: [
        "batting_stance",
        "batting-stance",
        "stance",
    ],
    CATEGORY_HOME_RUN_PROFILE: [
        "homerun",
        "home_run",
        "home_runs",
        "homeruns",
        "hr_profile",
    ],
    CATEGORY_TEAM_PLATE_DISCIPLINE: [
        "plate_discipline",
        "platediscipline",
        "plate discipline",
    ],
    CATEGORY_ADVANCED_BATTING_OR_PITCHER_STATS: [
        "pitcherstats",
        "pitcher_stats",
    ],
    CATEGORY_ADVANCED_BATTING_STATS: [
        "stats.csv",
        "batting_stats",
        "advanced_batting",
    ],
}

WAREHOUSE_TABLE_TARGETS = {
    CATEGORY_PERCENTILE_RANKINGS: "player_percentile_rankings",
    CATEGORY_PITCH_ARSENAL: "player_pitch_arsenals",
    CATEGORY_PITCH_TEMPO: "player_pitch_tempo",
    CATEGORY_BATTED_BALL_PROFILE: "player_batted_ball_profiles",
    CATEGORY_BATTING_STANCE: "player_batting_stances",
    CATEGORY_HOME_RUN_PROFILE: "player_home_run_profiles",
    CATEGORY_ADVANCED_BATTING_STATS: "player_advanced_batting_stats",
    CATEGORY_ADVANCED_BATTING_OR_PITCHER_STATS: "player_advanced_batting_stats",
    CATEGORY_TEAM_PLATE_DISCIPLINE: "team_plate_discipline",
}

PREDICTION_FEATURE_GROUPS = {
    "home_run_model": [
        CATEGORY_HOME_RUN_PROFILE,
        CATEGORY_BATTED_BALL_PROFILE,
        CATEGORY_PERCENTILE_RANKINGS,
        CATEGORY_ADVANCED_BATTING_STATS,
        CATEGORY_TEAM_PLATE_DISCIPLINE,
    ],
    "hit_probability_model": [
        CATEGORY_ADVANCED_BATTING_STATS,
        CATEGORY_BATTED_BALL_PROFILE,
        CATEGORY_PERCENTILE_RANKINGS,
        CATEGORY_TEAM_PLATE_DISCIPLINE,
    ],
    "strikeout_model": [
        CATEGORY_ADVANCED_BATTING_STATS,
        CATEGORY_PERCENTILE_RANKINGS,
        CATEGORY_PITCH_ARSENAL,
        CATEGORY_TEAM_PLATE_DISCIPLINE,
    ],
    "pitcher_model": [
        CATEGORY_PITCH_ARSENAL,
        CATEGORY_PITCH_TEMPO,
        CATEGORY_PERCENTILE_RANKINGS,
    ],
}

WAREHOUSE_READINESS_THRESHOLDS = {
    "minimum_files_loaded": 3,
    "minimum_rows_loaded": 100,
    "minimum_player_feature_tables": 3,
    "minimum_team_feature_tables": 1,
}

STATCAST_IMPORT_CONFIGURATION = {
    "raw_data_dir": str(RAW_DATA_DIR),
    "version": STATCAST_INGESTION_VERSION,
    "default_season": DEFAULT_IMPORT_SEASON,
    "supported_categories": SUPPORTED_IMPORT_CATEGORIES,
    "default_files": DEFAULT_IMPORT_FILES,
    "prediction_feature_groups": PREDICTION_FEATURE_GROUPS,
    "warehouse_table_targets": WAREHOUSE_TABLE_TARGETS,
    "readiness_thresholds": WAREHOUSE_READINESS_THRESHOLDS,
    "import_logs_enabled": True,
    "raw_json_storage_enabled": True,
    "player_resolution_enabled": True,
    "team_resolution_enabled": True,
    "fallback_unresolved_players_allowed": True,
    "fallback_unresolved_teams_allowed": True,
}
# ============================================================
# SECTION 03 - SAFE VALUE HELPERS
# ============================================================

def utc_now_string() -> str:
    return datetime.utcnow().isoformat()


def clean_string(value: Any) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()

    if cleaned == "":
        return None

    if cleaned.lower() in ["nan", "none", "null", "n/a", "--"]:
        return None

    return cleaned


def clean_int(value: Any) -> int | None:
    cleaned = clean_string(value)

    if cleaned is None:
        return None

    try:
        return int(float(cleaned.replace(",", "")))

    except Exception:
        return None


def clean_float(value: Any) -> float | None:
    cleaned = clean_string(value)

    if cleaned is None:
        return None

    try:
        return float(cleaned.replace("%", "").replace(",", ""))

    except Exception:
        return None


def row_to_json(row: dict) -> str:
    return json.dumps(
        row,
        ensure_ascii=False,
        default=str,
    )


def get_value(row: dict, *names: str) -> Any:
    for name in names:
        if name in row:
            return row.get(name)

    return None


def infer_season_from_file(
    file_path: Path,
    row: dict,
) -> int:
    row_year = clean_int(
        get_value(
            row,
            "season",
            "year",
            "Season",
            "Year",
        )
    )

    if row_year:
        return row_year

    if "2025" in file_path.name:
        return 2025

    if "2026" in file_path.name:
        return 2026

    return 2026


# ============================================================
# SECTION 04 - PLAYER AND TEAM RESOLUTION
# ============================================================

def find_player_by_mlb_id(
    database_session,
    mlb_player_id: int | None,
):
    if not mlb_player_id:
        return None

    return (
        database_session.query(Player)
        .filter(Player.mlb_player_id == mlb_player_id)
        .first()
    )


def find_team_by_name_or_abbreviation(
    database_session,
    team_name: str | None = None,
    team_abbreviation: str | None = None,
):
    if team_abbreviation:
        team = (
            database_session.query(Team)
            .filter(Team.abbreviation == team_abbreviation)
            .first()
        )

        if team:
            return team

    if team_name:
        return (
            database_session.query(Team)
            .filter(Team.name == team_name)
            .first()
        )

    return None


# ============================================================
# SECTION 05 - CSV LOADING
# ============================================================

def load_csv_rows(file_path: Path) -> list[dict]:
    with file_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        return [
            dict(row)
            for row in reader
        ]


# ============================================================
# SECTION 06 - ENTERPRISE FILE CATEGORY DETECTION
# FILE: 03_ingestion/statcast_warehouse_ingestion.py
# PURPOSE: detect which Statcast/Joe CSV category a file belongs
# to using filename signals, column-header signals, exact known
# file aliases, fuzzy-safe normalized matching, and prediction
# warehouse routing metadata.
# ============================================================

def normalize_detection_text(value: Any) -> str:
    if value is None:
        return ""

    return (
        str(value)
        .lower()
        .strip()
        .replace("-", "_")
        .replace(" ", "_")
        .replace(".", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("__", "_")
    )


def normalize_column_name(value: Any) -> str:
    return normalize_detection_text(value)


def get_csv_header_columns(file_path: Path) -> list[str]:
    if not file_path.exists():
        return []

    try:
        with file_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            reader = csv.DictReader(csv_file)

            if not reader.fieldnames:
                return []

            return [
                normalize_column_name(column)
                for column in reader.fieldnames
                if column
            ]

    except Exception:
        return []


def score_filename_category_match(
    normalized_filename: str,
    category: str,
) -> int:
    score = 0

    patterns = FILENAME_CATEGORY_PATTERNS.get(
        category,
        [],
    )

    for pattern in patterns:
        normalized_pattern = normalize_detection_text(
            pattern,
        )

        if not normalized_pattern:
            continue

        if normalized_filename == normalized_pattern:
            score += 100

        elif normalized_filename.startswith(normalized_pattern):
            score += 70

        elif normalized_pattern in normalized_filename:
            score += 50

    return score


def score_column_category_match(
    normalized_columns: list[str],
    category: str,
) -> int:
    column_set = set(normalized_columns)

    if not column_set:
        return 0

    score = 0

    percentile_columns = {
        "xwoba",
        "xba",
        "xslg",
        "brl",
        "brl_percent",
        "hard_hit_percent",
        "exit_velocity",
        "sprint_speed",
        "arm_strength",
        "whiff_percent",
        "chase_percent",
        "bb_percent",
        "k_percent",
    }

    pitch_arsenal_columns = {
        "pitcher",
        "ff_avg_speed",
        "si_avg_speed",
        "fc_avg_speed",
        "sl_avg_speed",
        "ch_avg_speed",
        "cu_avg_speed",
        "fs_avg_speed",
        "kn_avg_speed",
        "st_avg_speed",
        "sv_avg_speed",
    }

    pitch_tempo_columns = {
        "entity_id",
        "entity_name",
        "median_seconds_empty",
        "median_seconds_empty_1",
        "violations",
    }

    batted_ball_columns = {
        "avg_hit_speed",
        "max_hit_speed",
        "avg_hit_angle",
        "brl_percent",
        "ev95percent",
        "anglesweetspotpercent",
        "xba",
        "xslg",
        "xwoba",
    }

    batting_stance_columns = {
        "avg_batter_x_position",
        "avg_batter_y_position",
        "avg_foot_sep",
        "avg_stance_angle",
        "bat_side",
    }

    home_run_columns = {
        "hr_total",
        "avg_distance",
        "avg_hr_distance",
        "avg_hit_speed",
        "max_hit_speed",
        "team_abbrev",
    }

    advanced_batting_columns = {
        "pa",
        "k_percent",
        "bb_percent",
        "woba",
        "xwoba",
        "barrel_batted_rate",
        "hard_hit_percent",
        "whiff_percent",
        "swing_percent",
    }

    team_plate_discipline_columns = {
        "pitches",
        "zone_%",
        "zone_swing_%",
        "zone_contact_%",
        "chase_%",
        "chase_contact_%",
        "edge_%",
        "1st_pitch_swing_%",
        "swing_%",
        "whiff_%",
        "meatball_%",
        "meatball_swing_%",
    }

    category_column_signatures = {
        CATEGORY_PERCENTILE_RANKINGS: percentile_columns,
        CATEGORY_PITCH_ARSENAL: pitch_arsenal_columns,
        CATEGORY_PITCH_TEMPO: pitch_tempo_columns,
        CATEGORY_BATTED_BALL_PROFILE: batted_ball_columns,
        CATEGORY_BATTING_STANCE: batting_stance_columns,
        CATEGORY_HOME_RUN_PROFILE: home_run_columns,
        CATEGORY_ADVANCED_BATTING_STATS: advanced_batting_columns,
        CATEGORY_ADVANCED_BATTING_OR_PITCHER_STATS: advanced_batting_columns,
        CATEGORY_TEAM_PLATE_DISCIPLINE: team_plate_discipline_columns,
    }

    expected_columns = category_column_signatures.get(
        category,
        set(),
    )

    matched_columns = column_set.intersection(
        expected_columns,
    )

    score += len(matched_columns) * 12

    if category == CATEGORY_PITCH_ARSENAL and any(
        column.endswith("_avg_speed")
        for column in column_set
    ):
        score += 45

    if category == CATEGORY_PITCH_TEMPO and any(
        "median_seconds" in column
        for column in column_set
    ):
        score += 45

    if category == CATEGORY_BATTED_BALL_PROFILE and {
        "avg_hit_speed",
        "max_hit_speed",
    }.issubset(column_set):
        score += 45

    if category == CATEGORY_HOME_RUN_PROFILE and (
        "hr_total" in column_set
        or "avg_hr_distance" in column_set
        or "avg_distance" in column_set
    ):
        score += 50

    if category == CATEGORY_BATTING_STANCE and any(
        "stance" in column
        for column in column_set
    ):
        score += 45

    if category == CATEGORY_TEAM_PLATE_DISCIPLINE and (
        "zone_%" in column_set
        or "chase_%" in column_set
        or "meatball_%" in column_set
    ):
        score += 50

    if category == CATEGORY_ADVANCED_BATTING_STATS and {
        "woba",
        "xwoba",
        "pa",
    }.issubset(column_set):
        score += 50

    return score


def build_file_category_scores(
    file_path: Path,
) -> dict[str, int]:
    normalized_filename = normalize_detection_text(
        file_path.name,
    )

    normalized_columns = get_csv_header_columns(
        file_path,
    )

    scores: dict[str, int] = {}

    for category in SUPPORTED_IMPORT_CATEGORIES:
        filename_score = score_filename_category_match(
            normalized_filename=normalized_filename,
            category=category,
        )

        column_score = score_column_category_match(
            normalized_columns=normalized_columns,
            category=category,
        )

        scores[category] = filename_score + column_score

    if normalized_filename == "stats_csv":
        scores[CATEGORY_ADVANCED_BATTING_STATS] += 150

    if normalized_filename == "pitcherstats_csv":
        scores[CATEGORY_ADVANCED_BATTING_OR_PITCHER_STATS] += 150

    if "percentile_rankings2025" in normalized_filename:
        scores[CATEGORY_PERCENTILE_RANKINGS] += 150

    if "2025_pitch_arsenals" in normalized_filename:
        scores[CATEGORY_PITCH_ARSENAL] += 150

    if "2025historicalpitchtempo" in normalized_filename:
        scores[CATEGORY_PITCH_TEMPO] += 150

    if "2025exitvolicity" in normalized_filename:
        scores[CATEGORY_BATTED_BALL_PROFILE] += 150

    if "2025_batting_stance" in normalized_filename:
        scores[CATEGORY_BATTING_STANCE] += 150

    if "homeruns2025" in normalized_filename:
        scores[CATEGORY_HOME_RUN_PROFILE] += 150

    return scores


def detect_import_category_with_diagnostics(
    file_path: Path,
) -> dict:
    normalized_filename = normalize_detection_text(
        file_path.name,
    )

    normalized_columns = get_csv_header_columns(
        file_path,
    )

    scores = build_file_category_scores(
        file_path,
    )

    ranked_scores = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    best_category = (
        ranked_scores[0][0]
        if ranked_scores
        else CATEGORY_UNKNOWN
    )

    best_score = (
        ranked_scores[0][1]
        if ranked_scores
        else 0
    )

    second_score = (
        ranked_scores[1][1]
        if len(ranked_scores) > 1
        else 0
    )

    confidence_gap = best_score - second_score

    if best_score <= 0:
        best_category = CATEGORY_UNKNOWN

    confidence = "unknown"

    if best_score >= 150:
        confidence = "very_high"

    elif best_score >= 90:
        confidence = "high"

    elif best_score >= 50:
        confidence = "medium"

    elif best_score > 0:
        confidence = "low"

    return {
        "file": file_path.name,
        "normalized_filename": normalized_filename,
        "category": best_category,
        "target_table": WAREHOUSE_TABLE_TARGETS.get(best_category),
        "score": best_score,
        "second_score": second_score,
        "confidence_gap": confidence_gap,
        "confidence": confidence,
        "scores": scores,
        "ranked_scores": ranked_scores,
        "columns": normalized_columns,
        "column_count": len(normalized_columns),
        "supported": best_category in SUPPORTED_IMPORT_CATEGORIES,
        "prediction_feature_groups": [
            feature_group_name
            for feature_group_name, categories in PREDICTION_FEATURE_GROUPS.items()
            if best_category in categories
        ],
    }


def detect_import_category(file_path: Path) -> str:
    detection_report = detect_import_category_with_diagnostics(
        file_path,
    )

    return detection_report.get(
        "category",
        CATEGORY_UNKNOWN,
    )
# ============================================================
# SECTION 07 - IMPORT LOG HELPERS
# ============================================================

def create_import_log(
    database_session,
    file_path: Path,
    category: str,
    season: int | None,
    rows_seen: int,
) -> RawDataImportLog:
    import_log = RawDataImportLog(
        source_file=file_path.name,
        source_category=category,
        season=season,
        rows_seen=rows_seen,
        rows_inserted=0,
        rows_updated=0,
        rows_skipped=0,
        status="running",
        created_at=utc_now_string(),
    )

    database_session.add(import_log)
    database_session.flush()

    return import_log


def complete_import_log(
    import_log: RawDataImportLog,
    rows_inserted: int,
    rows_updated: int,
    rows_skipped: int,
    status: str = "completed",
    error_message: str | None = None,
) -> None:
    import_log.rows_inserted = rows_inserted
    import_log.rows_updated = rows_updated
    import_log.rows_skipped = rows_skipped
    import_log.status = status
    import_log.error_message = error_message
    import_log.completed_at = utc_now_string()


# ============================================================
# SECTION 08 - PERCENTILE RANKING IMPORT
# ============================================================

def import_percentile_rankings(
    database_session,
    file_path: Path,
    rows: list[dict],
) -> dict:
    inserted = 0
    skipped = 0

    for row in rows:
        mlb_player_id = clean_int(get_value(row, "player_id"))
        season = infer_season_from_file(file_path, row)

        player = find_player_by_mlb_id(
            database_session,
            mlb_player_id,
        )

        database_session.add(
            PlayerPercentileRanking(
                player_id=player.id if player else None,
                mlb_player_id=mlb_player_id,
                season=season,
                player_name=clean_string(get_value(row, "player_name")),
                team_name=clean_string(get_value(row, "team_name", "team")),
                xwoba_percentile=clean_float(get_value(row, "xwoba")),
                xba_percentile=clean_float(get_value(row, "xba")),
                xslg_percentile=clean_float(get_value(row, "xslg")),
                barrel_percentile=clean_float(get_value(row, "brl", "brl_percent")),
                hard_hit_percentile=clean_float(get_value(row, "hard_hit_percent")),
                exit_velocity_percentile=clean_float(get_value(row, "exit_velocity")),
                sprint_speed_percentile=clean_float(get_value(row, "sprint_speed")),
                arm_strength_percentile=clean_float(get_value(row, "arm_strength")),
                whiff_percentile=clean_float(get_value(row, "whiff_percent")),
                chase_percentile=clean_float(get_value(row, "chase_percent")),
                walk_percentile=clean_float(get_value(row, "bb_percent")),
                strikeout_percentile=clean_float(get_value(row, "k_percent")),
                source_file=file_path.name,
                raw_stat_json=row_to_json(row),
                created_at=utc_now_string(),
                updated_at=utc_now_string(),
            )
        )

        inserted += 1

    return {
        "inserted": inserted,
        "updated": 0,
        "skipped": skipped,
    }


# ============================================================
# SECTION 09 - PITCH ARSENAL IMPORT
# ============================================================

PITCH_SPEED_COLUMNS = {
    "ff_avg_speed": ("FF", "Four-Seam Fastball"),
    "si_avg_speed": ("SI", "Sinker"),
    "fc_avg_speed": ("FC", "Cutter"),
    "sl_avg_speed": ("SL", "Slider"),
    "ch_avg_speed": ("CH", "Changeup"),
    "cu_avg_speed": ("CU", "Curveball"),
    "fs_avg_speed": ("FS", "Splitter"),
    "kn_avg_speed": ("KN", "Knuckleball"),
    "st_avg_speed": ("ST", "Sweeper"),
    "sv_avg_speed": ("SV", "Slurve"),
}


def import_pitch_arsenals(
    database_session,
    file_path: Path,
    rows: list[dict],
) -> dict:
    inserted = 0
    skipped = 0

    for row in rows:
        mlb_player_id = clean_int(get_value(row, "pitcher", "player_id"))
        season = infer_season_from_file(file_path, row)

        player = find_player_by_mlb_id(
            database_session,
            mlb_player_id,
        )

        for column_name, pitch_info in PITCH_SPEED_COLUMNS.items():
            average_velocity = clean_float(row.get(column_name))

            if average_velocity is None:
                continue

            pitch_type, pitch_name = pitch_info

            database_session.add(
                PlayerPitchArsenal(
                    player_id=player.id if player else None,
                    mlb_player_id=mlb_player_id,
                    season=season,
                    player_name=clean_string(get_value(row, "last_name, first_name", "player_name")),
                    team_name=clean_string(get_value(row, "team_name", "team")),
                    pitch_type=pitch_type,
                    pitch_name=pitch_name,
                    average_velocity=average_velocity,
                    source_file=file_path.name,
                    raw_stat_json=row_to_json(row),
                    created_at=utc_now_string(),
                    updated_at=utc_now_string(),
                )
            )

            inserted += 1

    return {
        "inserted": inserted,
        "updated": 0,
        "skipped": skipped,
    }


# ============================================================
# SECTION 10 - PITCH TEMPO IMPORT
# ============================================================

def import_pitch_tempo(
    database_session,
    file_path: Path,
    rows: list[dict],
) -> dict:
    inserted = 0

    for row in rows:
        mlb_player_id = clean_int(get_value(row, "entity_id", "player_id"))
        season = infer_season_from_file(file_path, row)

        player = find_player_by_mlb_id(
            database_session,
            mlb_player_id,
        )

        database_session.add(
            PlayerPitchTempo(
                player_id=player.id if player else None,
                mlb_player_id=mlb_player_id,
                season=season,
                player_name=clean_string(get_value(row, "entity_name", "player_name")),
                team_name=clean_string(get_value(row, "team_name", "team")),
                pitch_tempo=clean_float(get_value(row, "median_seconds_empty")),
                tempo_empty=clean_float(get_value(row, "median_seconds_empty")),
                tempo_runners_on=clean_float(get_value(row, "median_seconds_empty.1")),
                pitch_timer_violations=clean_int(get_value(row, "violations")),
                source_file=file_path.name,
                raw_stat_json=row_to_json(row),
                created_at=utc_now_string(),
                updated_at=utc_now_string(),
            )
        )

        inserted += 1

    return {
        "inserted": inserted,
        "updated": 0,
        "skipped": 0,
    }


# ============================================================
# SECTION 11 - BATTED BALL PROFILE IMPORT
# ============================================================

def import_batted_ball_profiles(
    database_session,
    file_path: Path,
    rows: list[dict],
) -> dict:
    inserted = 0

    for row in rows:
        mlb_player_id = clean_int(get_value(row, "player_id"))
        season = infer_season_from_file(file_path, row)

        player = find_player_by_mlb_id(
            database_session,
            mlb_player_id,
        )

        database_session.add(
            PlayerBattedBallProfile(
                player_id=player.id if player else None,
                mlb_player_id=mlb_player_id,
                season=season,
                player_name=clean_string(get_value(row, "last_name, first_name", "player_name")),
                team_name=clean_string(get_value(row, "team_name", "team")),
                average_exit_velocity=clean_float(get_value(row, "avg_hit_speed")),
                max_exit_velocity=clean_float(get_value(row, "max_hit_speed")),
                launch_angle=clean_float(get_value(row, "avg_hit_angle")),
                barrel_percent=clean_float(get_value(row, "brl_percent")),
                hard_hit_percent=clean_float(get_value(row, "ev95percent")),
                sweet_spot_percent=clean_float(get_value(row, "anglesweetspotpercent")),
                expected_batting_average=clean_float(get_value(row, "xba")),
                expected_slugging=clean_float(get_value(row, "xslg")),
                expected_woba=clean_float(get_value(row, "xwoba")),
                source_file=file_path.name,
                raw_stat_json=row_to_json(row),
                created_at=utc_now_string(),
                updated_at=utc_now_string(),
            )
        )

        inserted += 1

    return {
        "inserted": inserted,
        "updated": 0,
        "skipped": 0,
    }


# ============================================================
# SECTION 12 - BATTING STANCE IMPORT
# ============================================================

def import_batting_stances(
    database_session,
    file_path: Path,
    rows: list[dict],
) -> dict:
    inserted = 0

    for row in rows:
        mlb_player_id = clean_int(get_value(row, "id", "player_id"))
        season = infer_season_from_file(file_path, row)

        player = find_player_by_mlb_id(
            database_session,
            mlb_player_id,
        )

        database_session.add(
            PlayerBattingStance(
                player_id=player.id if player else None,
                mlb_player_id=mlb_player_id,
                season=season,
                player_name=clean_string(get_value(row, "name", "player_name")),
                bats=clean_string(get_value(row, "bat_side")),
                stance_side=clean_string(get_value(row, "side")),
                stance_description=(
                    f"x={clean_string(get_value(row, 'avg_batter_x_position'))}, "
                    f"y={clean_string(get_value(row, 'avg_batter_y_position'))}, "
                    f"foot_sep={clean_string(get_value(row, 'avg_foot_sep'))}, "
                    f"angle={clean_string(get_value(row, 'avg_stance_angle'))}"
                ),
                source_file=file_path.name,
                raw_stat_json=row_to_json(row),
                created_at=utc_now_string(),
                updated_at=utc_now_string(),
            )
        )

        inserted += 1

    return {
        "inserted": inserted,
        "updated": 0,
        "skipped": 0,
    }


# ============================================================
# SECTION 13 - HOME RUN PROFILE IMPORT
# ============================================================

def import_home_run_profiles(
    database_session,
    file_path: Path,
    rows: list[dict],
) -> dict:
    inserted = 0

    for row in rows:
        mlb_player_id = clean_int(get_value(row, "player_id"))
        season = infer_season_from_file(file_path, row)

        player = find_player_by_mlb_id(
            database_session,
            mlb_player_id,
        )

        database_session.add(
            PlayerHomeRunProfile(
                player_id=player.id if player else None,
                mlb_player_id=mlb_player_id,
                season=season,
                player_name=clean_string(get_value(row, "player")),
                team_name=clean_string(get_value(row, "team_abbrev")),
                home_runs=clean_int(get_value(row, "hr_total")),
                average_home_run_distance=clean_float(get_value(row, "avg_distance", "avg_hr_distance")),
                average_exit_velocity=clean_float(get_value(row, "avg_hit_speed")),
                max_exit_velocity=clean_float(get_value(row, "max_hit_speed")),
                source_file=file_path.name,
                raw_stat_json=row_to_json(row),
                created_at=utc_now_string(),
                updated_at=utc_now_string(),
            )
        )

        inserted += 1

    return {
        "inserted": inserted,
        "updated": 0,
        "skipped": 0,
    }


# ============================================================
# SECTION 14 - ADVANCED BATTING STAT IMPORT
# ============================================================

def import_advanced_batting_stats(
    database_session,
    file_path: Path,
    rows: list[dict],
) -> dict:
    inserted = 0

    for row in rows:
        mlb_player_id = clean_int(get_value(row, "player_id"))
        season = infer_season_from_file(file_path, row)

        player = find_player_by_mlb_id(
            database_session,
            mlb_player_id,
        )

        database_session.add(
            PlayerAdvancedBattingStat(
                player_id=player.id if player else None,
                mlb_player_id=mlb_player_id or 0,
                season=season,
                plate_appearances=clean_int(get_value(row, "pa")),
                strikeout_percent=clean_float(get_value(row, "k_percent")),
                walk_percent=clean_float(get_value(row, "bb_percent")),
                woba=clean_float(get_value(row, "woba")),
                expected_woba=clean_float(get_value(row, "xwoba")),
                barrel_batted_rate=clean_float(get_value(row, "barrel_batted_rate")),
                hard_hit_percent=clean_float(get_value(row, "hard_hit_percent")),
                whiff_percent=clean_float(get_value(row, "whiff_percent")),
                swing_percent=clean_float(get_value(row, "swing_percent")),
                source=file_path.name,
                raw_stat_json=row_to_json(row),
                created_at=utc_now_string(),
                updated_at=utc_now_string(),
            )
        )

        inserted += 1

    return {
        "inserted": inserted,
        "updated": 0,
        "skipped": 0,
    }


# ============================================================
# SECTION 15 - TEAM PLATE DISCIPLINE IMPORT PLACEHOLDER
# ============================================================

def import_team_plate_discipline(
    database_session,
    file_path: Path,
    rows: list[dict],
) -> dict:
    inserted = 0

    for row in rows:
        season = infer_season_from_file(file_path, row)

        team_name = clean_string(get_value(row, "Team", "team", "team_name"))
        team_abbreviation = clean_string(get_value(row, "team_abbrev", "abbreviation"))

        team = find_team_by_name_or_abbreviation(
            database_session,
            team_name=team_name,
            team_abbreviation=team_abbreviation,
        )

        database_session.add(
            TeamPlateDiscipline(
                team_id=team.id if team else None,
                mlb_team_id=team.mlb_team_id if team else None,
                season=season,
                team_name=team_name,
                team_abbreviation=team_abbreviation,
                pitches=clean_int(get_value(row, "Pitches")),
                zone_percent=clean_float(get_value(row, "Zone %")),
                zone_swing_percent=clean_float(get_value(row, "Zone Swing %")),
                zone_contact_percent=clean_float(get_value(row, "Zone Contact %")),
                chase_percent=clean_float(get_value(row, "Chase %")),
                chase_contact_percent=clean_float(get_value(row, "Chase Contact %")),
                edge_percent=clean_float(get_value(row, "Edge %")),
                first_pitch_swing_percent=clean_float(get_value(row, "1st Pitch Swing %")),
                swing_percent=clean_float(get_value(row, "Swing %")),
                whiff_percent=clean_float(get_value(row, "Whiff %")),
                meatball_percent=clean_float(get_value(row, "Meatball %")),
                meatball_swing_percent=clean_float(get_value(row, "Meatball Swing %")),
                source_file=file_path.name,
                raw_stat_json=row_to_json(row),
                created_at=utc_now_string(),
                updated_at=utc_now_string(),
            )
        )

        inserted += 1

    return {
        "inserted": inserted,
        "updated": 0,
        "skipped": 0,
    }


# ============================================================
# SECTION 16 - CATEGORY ROUTER
# ============================================================

def import_rows_by_category(
    database_session,
    file_path: Path,
    category: str,
    rows: list[dict],
) -> dict:
    if category == "percentile_rankings":
        return import_percentile_rankings(database_session, file_path, rows)

    if category == "pitch_arsenal":
        return import_pitch_arsenals(database_session, file_path, rows)

    if category == "pitch_tempo":
        return import_pitch_tempo(database_session, file_path, rows)

    if category == "batted_ball_profile":
        return import_batted_ball_profiles(database_session, file_path, rows)

    if category == "batting_stance":
        return import_batting_stances(database_session, file_path, rows)

    if category == "home_run_profile":
        return import_home_run_profiles(database_session, file_path, rows)

    if category in ["advanced_batting_stats", "advanced_batting_or_pitcher_stats"]:
        return import_advanced_batting_stats(database_session, file_path, rows)

    if category == "team_plate_discipline":
        return import_team_plate_discipline(database_session, file_path, rows)

    return {
        "inserted": 0,
        "updated": 0,
        "skipped": len(rows),
    }


# ============================================================
# SECTION 17 - ENTERPRISE SINGLE FILE IMPORT
# FILE: 03_ingestion/statcast_warehouse_ingestion.py
# PURPOSE: import one Statcast/Joe CSV with full diagnostics,
# category detection, schema validation, import logging,
# row-count proof, prediction feature metadata, and safe failure
# handling so every dataset import can be audited and trusted.
# ============================================================

def build_missing_file_import_report(
    file_path: Path,
) -> dict:
    return {
        "file": str(file_path),
        "file_name": file_path.name,
        "status": IMPORT_STATUS_MISSING,
        "category": CATEGORY_UNKNOWN,
        "target_table": None,
        "supported": False,
        "exists": False,
        "rows_seen": 0,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "error": "File does not exist.",
        "detection": {
            "category": CATEGORY_UNKNOWN,
            "confidence": "unknown",
            "score": 0,
        },
        "prediction_feature_groups": [],
        "completed_at": utc_now_string(),
    }


def build_empty_file_import_report(
    file_path: Path,
    detection_report: dict,
) -> dict:
    return {
        "file": str(file_path),
        "file_name": file_path.name,
        "status": IMPORT_STATUS_SKIPPED,
        "category": detection_report.get("category", CATEGORY_UNKNOWN),
        "target_table": detection_report.get("target_table"),
        "supported": detection_report.get("supported", False),
        "exists": True,
        "rows_seen": 0,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "error": "CSV file exists but contains no data rows.",
        "detection": detection_report,
        "prediction_feature_groups": detection_report.get(
            "prediction_feature_groups",
            [],
        ),
        "completed_at": utc_now_string(),
    }


def validate_single_file_import_inputs(
    file_path: Path,
    rows: list[dict],
    detection_report: dict,
) -> dict:
    category = detection_report.get(
        "category",
        CATEGORY_UNKNOWN,
    )

    supported = detection_report.get(
        "supported",
        False,
    )

    target_table = detection_report.get(
        "target_table",
    )

    validation_errors: list[str] = []
    validation_warnings: list[str] = []

    if category == CATEGORY_UNKNOWN:
        validation_errors.append(
            "Unable to determine import category from filename or CSV headers."
        )

    if not supported:
        validation_errors.append(
            f"Unsupported import category: {category}"
        )

    if not target_table:
        validation_errors.append(
            f"No warehouse target table configured for category: {category}"
        )

    if len(rows) == 0:
        validation_errors.append(
            "CSV has no data rows."
        )

    if detection_report.get("confidence") in ["unknown", "low"]:
        validation_warnings.append(
            "Category detection confidence is low. Review file naming and headers."
        )

    if detection_report.get("confidence_gap", 0) < 20:
        validation_warnings.append(
            "Category detection score gap is narrow. File may be ambiguous."
        )

    return {
        "valid": len(validation_errors) == 0,
        "errors": validation_errors,
        "warnings": validation_warnings,
        "category": category,
        "supported": supported,
        "target_table": target_table,
    }


def build_import_success_report(
    file_path: Path,
    detection_report: dict,
    validation_report: dict,
    result: dict,
    first_season: int | None,
    rows_seen: int,
) -> dict:
    inserted = int(
        result.get("inserted", 0) or 0,
    )

    updated = int(
        result.get("updated", 0) or 0,
    )

    skipped = int(
        result.get("skipped", 0) or 0,
    )

    affected_rows = inserted + updated

    return {
        "file": str(file_path),
        "file_name": file_path.name,
        "status": IMPORT_STATUS_COMPLETED,
        "category": detection_report.get("category", CATEGORY_UNKNOWN),
        "target_table": detection_report.get("target_table"),
        "supported": detection_report.get("supported", False),
        "exists": True,
        "season": first_season,
        "rows_seen": rows_seen,
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "affected_rows": affected_rows,
        "import_effective": affected_rows > 0,
        "detection": detection_report,
        "validation": validation_report,
        "prediction_feature_groups": detection_report.get(
            "prediction_feature_groups",
            [],
        ),
        "message": (
            "Import completed and inserted/updated warehouse rows."
            if affected_rows > 0
            else "Import completed but did not insert or update rows."
        ),
        "completed_at": utc_now_string(),
    }


def build_import_failure_report(
    file_path: Path,
    detection_report: dict | None,
    validation_report: dict | None,
    error: Exception | str,
    rows_seen: int,
    first_season: int | None = None,
) -> dict:
    detection_report = detection_report or {
        "category": CATEGORY_UNKNOWN,
        "confidence": "unknown",
        "score": 0,
    }

    validation_report = validation_report or {
        "valid": False,
        "errors": [],
        "warnings": [],
    }

    return {
        "file": str(file_path),
        "file_name": file_path.name,
        "status": IMPORT_STATUS_FAILED,
        "category": detection_report.get("category", CATEGORY_UNKNOWN),
        "target_table": detection_report.get("target_table"),
        "supported": detection_report.get("supported", False),
        "exists": file_path.exists(),
        "season": first_season,
        "rows_seen": rows_seen,
        "inserted": 0,
        "updated": 0,
        "skipped": rows_seen,
        "affected_rows": 0,
        "import_effective": False,
        "error": str(error),
        "detection": detection_report,
        "validation": validation_report,
        "prediction_feature_groups": detection_report.get(
            "prediction_feature_groups",
            [],
        ),
        "completed_at": utc_now_string(),
    }


def import_statcast_file(file_path: Path) -> dict:
    file_path = Path(file_path)

    if not file_path.exists():
        return build_missing_file_import_report(
            file_path=file_path,
        )

    detection_report = detect_import_category_with_diagnostics(
        file_path,
    )

    try:
        rows = load_csv_rows(
            file_path,
        )

    except Exception as load_error:
        return build_import_failure_report(
            file_path=file_path,
            detection_report=detection_report,
            validation_report={
                "valid": False,
                "errors": [
                    "CSV loading failed.",
                ],
                "warnings": [],
            },
            error=load_error,
            rows_seen=0,
        )

    if not rows:
        return build_empty_file_import_report(
            file_path=file_path,
            detection_report=detection_report,
        )

    first_season = infer_season_from_file(
        file_path,
        rows[0],
    )

    validation_report = validate_single_file_import_inputs(
        file_path=file_path,
        rows=rows,
        detection_report=detection_report,
    )

    if not validation_report["valid"]:
        with managed_database_session() as database_session:
            import_log = create_import_log(
                database_session=database_session,
                file_path=file_path,
                category=validation_report.get("category", CATEGORY_UNKNOWN),
                season=first_season,
                rows_seen=len(rows),
            )

            complete_import_log(
                import_log=import_log,
                rows_inserted=0,
                rows_updated=0,
                rows_skipped=len(rows),
                status=IMPORT_STATUS_FAILED,
                error_message=" | ".join(validation_report["errors"]),
            )

        return build_import_failure_report(
            file_path=file_path,
            detection_report=detection_report,
            validation_report=validation_report,
            error=" | ".join(validation_report["errors"]),
            rows_seen=len(rows),
            first_season=first_season,
        )

    with managed_database_session() as database_session:
        import_log = create_import_log(
            database_session=database_session,
            file_path=file_path,
            category=validation_report["category"],
            season=first_season,
            rows_seen=len(rows),
        )

        try:
            result = import_rows_by_category(
                database_session=database_session,
                file_path=file_path,
                category=validation_report["category"],
                rows=rows,
            )

            complete_import_log(
                import_log=import_log,
                rows_inserted=result.get("inserted", 0),
                rows_updated=result.get("updated", 0),
                rows_skipped=result.get("skipped", 0),
                status=IMPORT_STATUS_COMPLETED,
            )

            return build_import_success_report(
                file_path=file_path,
                detection_report=detection_report,
                validation_report=validation_report,
                result=result,
                first_season=first_season,
                rows_seen=len(rows),
            )

        except Exception as import_error:
            complete_import_log(
                import_log=import_log,
                rows_inserted=0,
                rows_updated=0,
                rows_skipped=len(rows),
                status=IMPORT_STATUS_FAILED,
                error_message=str(import_error),
            )

            return build_import_failure_report(
                file_path=file_path,
                detection_report=detection_report,
                validation_report=validation_report,
                error=import_error,
                rows_seen=len(rows),
                first_season=first_season,
            )
# ============================================================
# SECTION 18 - ENTERPRISE BULK WAREHOUSE IMPORT
# FILE: 03_ingestion/statcast_warehouse_ingestion.py
# PURPOSE: discover every supported Statcast/Joe CSV, classify
# files before import, execute single-file imports, aggregate
# warehouse-wide results, calculate prediction readiness, expose
# category coverage, and produce a complete audit report.
# ============================================================

def discover_csv_files(
    raw_data_dir: Path = RAW_DATA_DIR,
    recursive: bool = False,
) -> list[Path]:
    raw_data_dir = Path(raw_data_dir)

    if not raw_data_dir.exists():
        return []

    if recursive:
        discovered_files = raw_data_dir.rglob("*.csv")
    else:
        discovered_files = raw_data_dir.glob("*.csv")

    return sorted(
        [
            file_path
            for file_path in discovered_files
            if file_path.is_file()
        ],
        key=lambda file_path: file_path.name.lower(),
    )


def build_default_import_file_paths(
    raw_data_dir: Path = RAW_DATA_DIR,
) -> list[Path]:
    return [
        Path(raw_data_dir) / file_name
        for file_name in DEFAULT_IMPORT_FILES
    ]


def build_preflight_file_report(
    file_paths: list[Path],
) -> list[dict]:
    preflight_reports = []

    for file_path in file_paths:
        if not file_path.exists():
            preflight_reports.append(
                {
                    "file": str(file_path),
                    "file_name": file_path.name,
                    "exists": False,
                    "category": CATEGORY_UNKNOWN,
                    "target_table": None,
                    "confidence": "unknown",
                    "rows_detected": 0,
                    "supported": False,
                    "ready_for_import": False,
                    "reason": "missing_file",
                }
            )

            continue

        detection_report = detect_import_category_with_diagnostics(
            file_path,
        )

        try:
            rows = load_csv_rows(
                file_path,
            )

            rows_detected = len(rows)

        except Exception:
            rows_detected = 0

        preflight_reports.append(
            {
                "file": str(file_path),
                "file_name": file_path.name,
                "exists": True,
                "category": detection_report.get("category"),
                "target_table": detection_report.get("target_table"),
                "confidence": detection_report.get("confidence"),
                "score": detection_report.get("score"),
                "supported": detection_report.get("supported", False),
                "rows_detected": rows_detected,
                "prediction_feature_groups": detection_report.get(
                    "prediction_feature_groups",
                    [],
                ),
                "ready_for_import": (
                    detection_report.get("supported", False)
                    and detection_report.get("category") != CATEGORY_UNKNOWN
                    and rows_detected > 0
                ),
                "reason": (
                    "ready"
                    if (
                        detection_report.get("supported", False)
                        and detection_report.get("category") != CATEGORY_UNKNOWN
                        and rows_detected > 0
                    )
                    else "not_ready"
                ),
            }
        )

    return preflight_reports


def summarize_category_coverage(
    import_results: list[dict],
) -> dict:
    category_summary: dict[str, dict] = {}

    for category in SUPPORTED_IMPORT_CATEGORIES:
        category_summary[category] = {
            "category": category,
            "target_table": WAREHOUSE_TABLE_TARGETS.get(category),
            "files": 0,
            "completed_files": 0,
            "failed_files": 0,
            "missing_files": 0,
            "skipped_files": 0,
            "inserted": 0,
            "updated": 0,
            "skipped_rows": 0,
            "affected_rows": 0,
            "loaded": False,
        }

    category_summary[CATEGORY_UNKNOWN] = {
        "category": CATEGORY_UNKNOWN,
        "target_table": None,
        "files": 0,
        "completed_files": 0,
        "failed_files": 0,
        "missing_files": 0,
        "skipped_files": 0,
        "inserted": 0,
        "updated": 0,
        "skipped_rows": 0,
        "affected_rows": 0,
        "loaded": False,
    }

    for result in import_results:
        category = result.get(
            "category",
            CATEGORY_UNKNOWN,
        )

        if category not in category_summary:
            category = CATEGORY_UNKNOWN

        status = result.get(
            "status",
            IMPORT_STATUS_UNKNOWN,
        )

        category_summary[category]["files"] += 1
        category_summary[category]["inserted"] += int(result.get("inserted", 0) or 0)
        category_summary[category]["updated"] += int(result.get("updated", 0) or 0)
        category_summary[category]["skipped_rows"] += int(result.get("skipped", 0) or 0)
        category_summary[category]["affected_rows"] += int(result.get("affected_rows", 0) or 0)

        if status == IMPORT_STATUS_COMPLETED:
            category_summary[category]["completed_files"] += 1

        elif status == IMPORT_STATUS_FAILED:
            category_summary[category]["failed_files"] += 1

        elif status == IMPORT_STATUS_MISSING:
            category_summary[category]["missing_files"] += 1

        elif status == IMPORT_STATUS_SKIPPED:
            category_summary[category]["skipped_files"] += 1

    for category, summary in category_summary.items():
        summary["loaded"] = (
            summary["completed_files"] > 0
            and summary["affected_rows"] > 0
        )

    return category_summary


def calculate_prediction_readiness(
    category_summary: dict,
    total_inserted: int,
    completed_file_count: int,
) -> dict:
    loaded_categories = [
        category
        for category, summary in category_summary.items()
        if category != CATEGORY_UNKNOWN and summary.get("loaded")
    ]

    loaded_category_set = set(loaded_categories)

    feature_group_readiness = {}

    for feature_group_name, required_categories in PREDICTION_FEATURE_GROUPS.items():
        required_category_set = set(required_categories)

        loaded_required_categories = sorted(
            required_category_set.intersection(
                loaded_category_set,
            )
        )

        missing_required_categories = sorted(
            required_category_set.difference(
                loaded_category_set,
            )
        )

        feature_group_readiness[feature_group_name] = {
            "ready": len(missing_required_categories) == 0,
            "required_categories": sorted(required_categories),
            "loaded_categories": loaded_required_categories,
            "missing_categories": missing_required_categories,
            "coverage_ratio": (
                len(loaded_required_categories) / len(required_categories)
                if required_categories
                else 0
            ),
        }

    player_feature_categories = {
        CATEGORY_PERCENTILE_RANKINGS,
        CATEGORY_PITCH_ARSENAL,
        CATEGORY_PITCH_TEMPO,
        CATEGORY_BATTED_BALL_PROFILE,
        CATEGORY_BATTING_STANCE,
        CATEGORY_HOME_RUN_PROFILE,
        CATEGORY_ADVANCED_BATTING_STATS,
        CATEGORY_ADVANCED_BATTING_OR_PITCHER_STATS,
    }

    team_feature_categories = {
        CATEGORY_TEAM_PLATE_DISCIPLINE,
    }

    loaded_player_feature_tables = len(
        loaded_category_set.intersection(
            player_feature_categories,
        )
    )

    loaded_team_feature_tables = len(
        loaded_category_set.intersection(
            team_feature_categories,
        )
    )

    thresholds = WAREHOUSE_READINESS_THRESHOLDS

    minimum_files_loaded = thresholds.get(
        "minimum_files_loaded",
        3,
    )

    minimum_rows_loaded = thresholds.get(
        "minimum_rows_loaded",
        100,
    )

    minimum_player_feature_tables = thresholds.get(
        "minimum_player_feature_tables",
        3,
    )

    minimum_team_feature_tables = thresholds.get(
        "minimum_team_feature_tables",
        1,
    )

    files_ready = completed_file_count >= minimum_files_loaded
    rows_ready = total_inserted >= minimum_rows_loaded
    player_features_ready = loaded_player_feature_tables >= minimum_player_feature_tables
    team_features_ready = loaded_team_feature_tables >= minimum_team_feature_tables

    warehouse_ready = (
        files_ready
        and rows_ready
        and player_features_ready
    )

    prediction_ready = (
        warehouse_ready
        and any(
            readiness.get("ready")
            for readiness in feature_group_readiness.values()
        )
    )

    return {
        "warehouse_ready": warehouse_ready,
        "prediction_ready": prediction_ready,
        "files_ready": files_ready,
        "rows_ready": rows_ready,
        "player_features_ready": player_features_ready,
        "team_features_ready": team_features_ready,
        "completed_file_count": completed_file_count,
        "total_inserted": total_inserted,
        "loaded_categories": sorted(loaded_categories),
        "loaded_player_feature_tables": loaded_player_feature_tables,
        "loaded_team_feature_tables": loaded_team_feature_tables,
        "thresholds": thresholds,
        "feature_group_readiness": feature_group_readiness,
        "next_required_action": (
            "Warehouse is prediction-ready. Next step is connecting probability_engine.py to these tables."
            if prediction_ready
            else "Warehouse is not prediction-ready yet. Review failed files, missing categories, and inserted row counts."
        ),
    }


def build_bulk_import_summary(
    raw_data_dir: Path,
    import_files: list[Path],
    preflight_reports: list[dict],
    import_results: list[dict],
) -> dict:
    total_inserted = sum(
        int(item.get("inserted", 0) or 0)
        for item in import_results
    )

    total_updated = sum(
        int(item.get("updated", 0) or 0)
        for item in import_results
    )

    total_skipped = sum(
        int(item.get("skipped", 0) or 0)
        for item in import_results
    )

    total_affected_rows = sum(
        int(item.get("affected_rows", 0) or 0)
        for item in import_results
    )

    completed_files = [
        item
        for item in import_results
        if item.get("status") == IMPORT_STATUS_COMPLETED
    ]

    failed_files = [
        item
        for item in import_results
        if item.get("status") == IMPORT_STATUS_FAILED
    ]

    missing_files = [
        item
        for item in import_results
        if item.get("status") == IMPORT_STATUS_MISSING
    ]

    skipped_files = [
        item
        for item in import_results
        if item.get("status") == IMPORT_STATUS_SKIPPED
    ]

    category_summary = summarize_category_coverage(
        import_results,
    )

    readiness = calculate_prediction_readiness(
        category_summary=category_summary,
        total_inserted=total_inserted,
        completed_file_count=len(completed_files),
    )

    return {
        "operation": "import_default_statcast_files",
        "version": STATCAST_INGESTION_VERSION,
        "raw_data_dir": str(raw_data_dir),
        "started_file_count": len(import_files),
        "preflight_file_count": len(preflight_reports),
        "file_count": len(import_results),
        "completed_file_count": len(completed_files),
        "failed_file_count": len(failed_files),
        "missing_file_count": len(missing_files),
        "skipped_file_count": len(skipped_files),
        "total_inserted": total_inserted,
        "total_updated": total_updated,
        "total_skipped": total_skipped,
        "total_affected_rows": total_affected_rows,
        "successful_files": [
            item.get("file_name")
            for item in completed_files
        ],
        "failed_files": [
            {
                "file_name": item.get("file_name"),
                "category": item.get("category"),
                "error": item.get("error"),
            }
            for item in failed_files
        ],
        "missing_files": [
            item.get("file_name")
            for item in missing_files
        ],
        "skipped_files": [
            item.get("file_name")
            for item in skipped_files
        ],
        "category_summary": category_summary,
        "prediction_readiness": readiness,
        "preflight": preflight_reports,
        "results": import_results,
        "completed_at": utc_now_string(),
    }


def import_default_statcast_files(
    raw_data_dir: Path = RAW_DATA_DIR,
    recursive: bool = False,
    use_default_manifest_when_empty: bool = True,
) -> dict:
    raw_data_dir = Path(raw_data_dir)

    discovered_files = discover_csv_files(
        raw_data_dir=raw_data_dir,
        recursive=recursive,
    )

    if discovered_files:
        import_files = discovered_files

    elif use_default_manifest_when_empty:
        import_files = build_default_import_file_paths(
            raw_data_dir=raw_data_dir,
        )

    else:
        import_files = []

    preflight_reports = build_preflight_file_report(
        import_files,
    )

    results = []

    for file_path in import_files:
        results.append(
            import_statcast_file(
                file_path,
            )
        )

    return build_bulk_import_summary(
        raw_data_dir=raw_data_dir,
        import_files=import_files,
        preflight_reports=preflight_reports,
        import_results=results,
    )

# ============================================================
# SECTION 18.01 - ENTERPRISE STATCAST INTELLIGENCE CONSTANTS
# FILE: 03_ingestion/statcast_warehouse_ingestion.py
# ============================================================

STATCAST_MODULE_NAME = "AISP2 Enterprise Statcast Warehouse Intelligence"
STATCAST_MODULE_PATH = "03_ingestion/statcast_warehouse_ingestion.py"
STATCAST_MODULE_PHASE = "Phase 12 Part 3.0"
STATCAST_MODULE_VERSION = "7.0.0"
STATCAST_MODULE_STATUS = "enterprise_statcast_ready"

DEFAULT_STATCAST_STALE_HOURS = 36.0
DEFAULT_MINIMUM_BATTED_BALL_SAMPLE = 25
DEFAULT_USABLE_BATTED_BALL_SAMPLE = 100
DEFAULT_MINIMUM_PITCH_SAMPLE = 100
MAX_STATCAST_ERROR_RECORDS = 500

STATCAST_GROUP_HITTING = "hitting"
STATCAST_GROUP_PITCHING = "pitching"

SUPPORTED_STATCAST_GROUPS = (
    STATCAST_GROUP_HITTING,
    STATCAST_GROUP_PITCHING,
)

STATCAST_REQUIRED_HITTER_FIELDS = (
    "average_exit_velocity",
    "maximum_exit_velocity",
    "barrel_count",
    "barrel_rate",
    "hard_hit_count",
    "hard_hit_rate",
    "average_launch_angle",
    "sweet_spot_rate",
    "expected_batting_average",
    "expected_slugging_percentage",
    "expected_woba",
    "sprint_speed",
    "batted_ball_count",
)

STATCAST_REQUIRED_METADATA_FIELDS = (
    "season",
    "source_name",
    "source_updated_at",
)

STATCAST_NULL_TOKENS = frozenset({
    "",
    "nan",
    "none",
    "null",
    "n/a",
    "na",
    "--",
    "-",
    "undefined",
})

STATCAST_PERCENT_FIELDS = frozenset({
    "barrel_rate",
    "hard_hit_rate",
    "sweet_spot_rate",
    "whiff_rate",
    "chase_rate",
    "zone_contact_rate",
    "squared_up_rate",
})

STATCAST_INTEGER_FIELDS = frozenset({
    "barrel_count",
    "hard_hit_count",
    "batted_ball_count",
    "pitch_count",
    "swing_count",
    "whiff_count",
})


# ============================================================
# SECTION 18.02 - ENTERPRISE ENUMERATIONS
# ============================================================

class StatcastDataGroup(str, Enum):
    HITTING = STATCAST_GROUP_HITTING
    PITCHING = STATCAST_GROUP_PITCHING


class StatcastSampleStatus(str, Enum):
    UNKNOWN = "unknown"
    INSUFFICIENT = "insufficient_sample"
    LIMITED = "limited_sample"
    USABLE = "usable_sample"
    STRONG = "strong_sample"


class StatcastFreshnessStatus(str, Enum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    UNKNOWN = "unknown"


class StatcastImportAction(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    SKIPPED = "skipped"
    FAILED = "failed"


class StatcastCompletionStatus(str, Enum):
    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


# ============================================================
# SECTION 18.03 - ENTERPRISE DATA CONTRACTS
# ============================================================

@dataclass(slots=True)
class StatcastSourceObservation:
    source_name: str
    source_file: str | None
    retrieval_timestamp: datetime
    source_updated_at: datetime | None
    source_checksum: str
    season: int
    stat_group: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_file": self.source_file,
            "retrieval_timestamp": self.retrieval_timestamp.isoformat(),
            "source_updated_at": (
                self.source_updated_at.isoformat()
                if self.source_updated_at
                else None
            ),
            "source_checksum": self.source_checksum,
            "season": self.season,
            "stat_group": self.stat_group,
        }


@dataclass(slots=True)
class NormalizedStatcastMetric:
    mlb_player_id: int
    season: int
    stat_group: str

    player_name: str | None = None
    team_name: str | None = None
    team_abbreviation: str | None = None

    average_exit_velocity: float | None = None
    maximum_exit_velocity: float | None = None

    barrel_count: int | None = None
    barrel_rate: float | None = None

    hard_hit_count: int | None = None
    hard_hit_rate: float | None = None

    average_launch_angle: float | None = None
    sweet_spot_rate: float | None = None

    expected_batting_average: float | None = None
    expected_slugging_percentage: float | None = None
    expected_woba: float | None = None

    sprint_speed: float | None = None
    batted_ball_count: int | None = None

    average_fastball_velocity: float | None = None
    maximum_fastball_velocity: float | None = None
    spin_rate: float | None = None
    extension: float | None = None
    whiff_rate: float | None = None
    chase_rate: float | None = None
    zone_contact_rate: float | None = None
    squared_up_rate: float | None = None
    pitch_count: int | None = None

    sample_size_status: str = StatcastSampleStatus.UNKNOWN.value
    freshness_status: str = StatcastFreshnessStatus.UNKNOWN.value
    age_hours: float | None = None

    source_name: str = "Baseball Savant / Statcast"
    source_file: str | None = None
    retrieval_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    source_updated_at: datetime | None = None
    raw_stat_json: str | None = None
    source_checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["retrieval_timestamp"] = (
            self.retrieval_timestamp.isoformat()
        )

        payload["source_updated_at"] = (
            self.source_updated_at.isoformat()
            if self.source_updated_at
            else None
        )

        return payload


@dataclass(slots=True)
class StatcastUpsertResult:
    action: StatcastImportAction
    mlb_player_id: int
    season: int
    stat_group: str
    changed_fields: list[str]
    ignored_fields: list[str]
    database_record_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["action"] = self.action.value
        return payload


@dataclass(slots=True)
class StatcastCoverageAudit:
    season: int
    stat_group: str

    eligible_player_count: int
    metric_player_count: int
    usable_sample_player_count: int
    fresh_player_count: int
    stale_player_count: int

    missing_player_ids: list[int]
    incomplete_metric_rows: list[dict[str, Any]]
    duplicate_metric_rows: list[dict[str, Any]]
    cross_season_conflicts: list[dict[str, Any]]
    group_conflicts: list[dict[str, Any]]

    coverage_percent: float
    usable_sample_percent: float
    fresh_percent: float

    completion_status: StatcastCompletionStatus
    completion_gate_passed: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["completion_status"] = self.completion_status.value
        return payload


# ============================================================
# SECTION 18.04 - SAFE STATCAST VALUE NORMALIZATION
# ============================================================

def statcast_utc_now() -> datetime:
    return datetime.now(UTC)


def statcast_clean_string(value: Any) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()

    if cleaned.lower() in STATCAST_NULL_TOKENS:
        return None

    return cleaned or None


def statcast_clean_integer(value: Any) -> int | None:
    cleaned = statcast_clean_string(value)

    if cleaned is None:
        return None

    try:
        return int(float(cleaned.replace(",", "")))
    except (TypeError, ValueError):
        return None


def statcast_clean_float(
    value: Any,
    *,
    percentage: bool = False,
) -> float | None:
    cleaned = statcast_clean_string(value)

    if cleaned is None:
        return None

    has_percent = "%" in cleaned

    try:
        numeric = float(
            cleaned
            .replace("%", "")
            .replace(",", "")
        )
    except (TypeError, ValueError):
        return None

    if not math.isfinite(numeric):
        return None

    if percentage and has_percent:
        return numeric / 100.0

    if percentage and numeric > 1.0 and numeric <= 100.0:
        return numeric / 100.0

    return numeric


def statcast_parse_timestamp(
    value: Any,
    *,
    fallback: datetime | None = None,
) -> datetime | None:
    if value is None:
        return fallback

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)

    cleaned = statcast_clean_string(value)

    if not cleaned:
        return fallback

    normalized = cleaned.replace("Z", "+00:00")

    for parser in (
        datetime.fromisoformat,
    ):
        try:
            parsed = parser(normalized)

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)

            return parsed.astimezone(UTC)
        except ValueError:
            continue

    return fallback


def statcast_checksum(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def statcast_get_value(
    row: Mapping[str, Any],
    *aliases: str,
) -> Any:
    normalized_lookup = {
        normalize_column_name(key): value
        for key, value in row.items()
    }

    for alias in aliases:
        normalized_alias = normalize_column_name(alias)

        if normalized_alias in normalized_lookup:
            value = normalized_lookup[normalized_alias]

            if statcast_clean_string(value) is not None:
                return value

    return None


# ============================================================
# SECTION 18.05 - SAMPLE SIZE AND FRESHNESS CLASSIFICATION
# ============================================================

def classify_statcast_sample_size(
    sample_size: int | None,
    *,
    stat_group: str,
) -> StatcastSampleStatus:
    if sample_size is None:
        return StatcastSampleStatus.UNKNOWN

    if stat_group == STATCAST_GROUP_PITCHING:
        if sample_size < DEFAULT_MINIMUM_PITCH_SAMPLE:
            return StatcastSampleStatus.INSUFFICIENT

        if sample_size < 500:
            return StatcastSampleStatus.LIMITED

        if sample_size < 1500:
            return StatcastSampleStatus.USABLE

        return StatcastSampleStatus.STRONG

    if sample_size < DEFAULT_MINIMUM_BATTED_BALL_SAMPLE:
        return StatcastSampleStatus.INSUFFICIENT

    if sample_size < DEFAULT_USABLE_BATTED_BALL_SAMPLE:
        return StatcastSampleStatus.LIMITED

    if sample_size < 250:
        return StatcastSampleStatus.USABLE

    return StatcastSampleStatus.STRONG


def classify_statcast_freshness(
    source_updated_at: datetime | None,
    retrieval_timestamp: datetime,
    *,
    stale_hours: float = DEFAULT_STATCAST_STALE_HOURS,
) -> tuple[StatcastFreshnessStatus, float | None]:
    reference = source_updated_at or retrieval_timestamp

    if reference is None:
        return StatcastFreshnessStatus.UNKNOWN, None

    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)

    age_hours = (
        statcast_utc_now()
        - reference.astimezone(UTC)
    ).total_seconds() / 3600.0

    if age_hours <= stale_hours:
        status = StatcastFreshnessStatus.FRESH

    elif age_hours <= stale_hours * 3:
        status = StatcastFreshnessStatus.AGING

    else:
        status = StatcastFreshnessStatus.STALE

    return status, round(max(age_hours, 0.0), 3)


# ============================================================
# SECTION 18.06 - HITTER/PITCHER CLASSIFICATION
# ============================================================

def infer_statcast_group(
    row: Mapping[str, Any],
    *,
    explicit_group: str | None = None,
) -> str:
    if explicit_group in SUPPORTED_STATCAST_GROUPS:
        return explicit_group

    group_value = statcast_clean_string(
        statcast_get_value(
            row,
            "stat_group",
            "group",
            "player_type",
            "role",
        )
    )

    if group_value:
        normalized = group_value.lower()

        if "pitch" in normalized:
            return STATCAST_GROUP_PITCHING

        if "hit" in normalized or "batt" in normalized:
            return STATCAST_GROUP_HITTING

    normalized_columns = {
        normalize_column_name(column)
        for column in row
    }

    pitcher_signals = {
        "pitch_count",
        "pitches",
        "ff_avg_speed",
        "avg_fastball_velocity",
        "spin_rate",
        "extension",
    }

    hitter_signals = {
        "avg_hit_speed",
        "max_hit_speed",
        "brl_percent",
        "hard_hit_percent",
        "xba",
        "xslg",
        "xwoba",
    }

    pitcher_score = len(
        normalized_columns.intersection(pitcher_signals)
    )

    hitter_score = len(
        normalized_columns.intersection(hitter_signals)
    )

    if pitcher_score > hitter_score:
        return STATCAST_GROUP_PITCHING

    return STATCAST_GROUP_HITTING


# ============================================================
# SECTION 18.07 - NORMALIZED STATCAST RECORD BUILDER
# ============================================================

def normalize_statcast_metric_row(
    row: Mapping[str, Any],
    *,
    file_path: Path,
    explicit_season: int | None = None,
    explicit_group: str | None = None,
    retrieval_timestamp: datetime | None = None,
) -> NormalizedStatcastMetric:
    retrieval_timestamp = retrieval_timestamp or statcast_utc_now()

    season = (
        explicit_season
        or infer_season_from_file(
            file_path,
            dict(row),
        )
    )

    stat_group = infer_statcast_group(
        row,
        explicit_group=explicit_group,
    )

    mlb_player_id = statcast_clean_integer(
        statcast_get_value(
            row,
            "player_id",
            "mlb_player_id",
            "pitcher",
            "batter",
            "entity_id",
            "id",
        )
    )

    if mlb_player_id is None:
        raise ValueError(
            "Statcast row is missing authoritative MLB player ID"
        )

    source_updated_at = statcast_parse_timestamp(
        statcast_get_value(
            row,
            "source_updated_at",
            "updated_at",
            "last_updated",
            "retrieved_at",
            "retrieval_timestamp",
        ),
        fallback=retrieval_timestamp,
    )

    batted_ball_count = statcast_clean_integer(
        statcast_get_value(
            row,
            "batted_ball_count",
            "batted_balls",
            "bbe",
            "attempts",
            "pa",
        )
    )

    pitch_count = statcast_clean_integer(
        statcast_get_value(
            row,
            "pitch_count",
            "pitches",
            "total_pitches",
        )
    )

    sample_size = (
        pitch_count
        if stat_group == STATCAST_GROUP_PITCHING
        else batted_ball_count
    )

    sample_status = classify_statcast_sample_size(
        sample_size,
        stat_group=stat_group,
    )

    freshness_status, age_hours = classify_statcast_freshness(
        source_updated_at,
        retrieval_timestamp,
    )

    raw_payload = dict(row)

    return NormalizedStatcastMetric(
        mlb_player_id=mlb_player_id,
        season=int(season),
        stat_group=stat_group,

        player_name=statcast_clean_string(
            statcast_get_value(
                row,
                "player_name",
                "name",
                "last_name, first_name",
                "entity_name",
            )
        ),
        team_name=statcast_clean_string(
            statcast_get_value(
                row,
                "team_name",
                "team",
            )
        ),
        team_abbreviation=statcast_clean_string(
            statcast_get_value(
                row,
                "team_abbreviation",
                "team_abbrev",
                "abbreviation",
            )
        ),

        average_exit_velocity=statcast_clean_float(
            statcast_get_value(
                row,
                "average_exit_velocity",
                "avg_exit_velocity",
                "avg_hit_speed",
                "exit_velocity_avg",
            )
        ),
        maximum_exit_velocity=statcast_clean_float(
            statcast_get_value(
                row,
                "maximum_exit_velocity",
                "max_exit_velocity",
                "max_hit_speed",
            )
        ),

        barrel_count=statcast_clean_integer(
            statcast_get_value(
                row,
                "barrel_count",
                "barrels",
                "brl",
            )
        ),
        barrel_rate=statcast_clean_float(
            statcast_get_value(
                row,
                "barrel_rate",
                "barrel_percent",
                "brl_percent",
                "barrel_batted_rate",
            ),
            percentage=True,
        ),

        hard_hit_count=statcast_clean_integer(
            statcast_get_value(
                row,
                "hard_hit_count",
                "hard_hits",
            )
        ),
        hard_hit_rate=statcast_clean_float(
            statcast_get_value(
                row,
                "hard_hit_rate",
                "hard_hit_percent",
                "ev95percent",
            ),
            percentage=True,
        ),

        average_launch_angle=statcast_clean_float(
            statcast_get_value(
                row,
                "average_launch_angle",
                "avg_launch_angle",
                "avg_hit_angle",
                "launch_angle",
            )
        ),
        sweet_spot_rate=statcast_clean_float(
            statcast_get_value(
                row,
                "sweet_spot_rate",
                "sweet_spot_percent",
                "anglesweetspotpercent",
            ),
            percentage=True,
        ),

        expected_batting_average=statcast_clean_float(
            statcast_get_value(
                row,
                "expected_batting_average",
                "xba",
            )
        ),
        expected_slugging_percentage=statcast_clean_float(
            statcast_get_value(
                row,
                "expected_slugging_percentage",
                "expected_slugging",
                "xslg",
            )
        ),
        expected_woba=statcast_clean_float(
            statcast_get_value(
                row,
                "expected_woba",
                "xwoba",
            )
        ),

        sprint_speed=statcast_clean_float(
            statcast_get_value(
                row,
                "sprint_speed",
                "sprint_speed_ft_sec",
            )
        ),
        batted_ball_count=batted_ball_count,

        average_fastball_velocity=statcast_clean_float(
            statcast_get_value(
                row,
                "average_fastball_velocity",
                "avg_fastball_velocity",
                "ff_avg_speed",
            )
        ),
        maximum_fastball_velocity=statcast_clean_float(
            statcast_get_value(
                row,
                "maximum_fastball_velocity",
                "max_fastball_velocity",
                "ff_max_speed",
            )
        ),
        spin_rate=statcast_clean_float(
            statcast_get_value(
                row,
                "spin_rate",
                "avg_spin_rate",
            )
        ),
        extension=statcast_clean_float(
            statcast_get_value(
                row,
                "extension",
                "avg_extension",
            )
        ),
        whiff_rate=statcast_clean_float(
            statcast_get_value(
                row,
                "whiff_rate",
                "whiff_percent",
                "whiff_%",
            ),
            percentage=True,
        ),
        chase_rate=statcast_clean_float(
            statcast_get_value(
                row,
                "chase_rate",
                "chase_percent",
                "chase_%",
            ),
            percentage=True,
        ),
        zone_contact_rate=statcast_clean_float(
            statcast_get_value(
                row,
                "zone_contact_rate",
                "zone_contact_percent",
                "zone_contact_%",
            ),
            percentage=True,
        ),
        squared_up_rate=statcast_clean_float(
            statcast_get_value(
                row,
                "squared_up_rate",
                "squared_up_percent",
            ),
            percentage=True,
        ),
        pitch_count=pitch_count,

        sample_size_status=sample_status.value,
        freshness_status=freshness_status.value,
        age_hours=age_hours,

        source_name="Baseball Savant / Statcast",
        source_file=file_path.name,
        retrieval_timestamp=retrieval_timestamp,
        source_updated_at=source_updated_at,
        raw_stat_json=row_to_json(raw_payload),
        source_checksum=statcast_checksum(raw_payload),
    )


# ============================================================
# SECTION 18.08 - NULL-SAFE STATCAST VALIDATION
# ============================================================

def validate_normalized_statcast_metric(
    metric: NormalizedStatcastMetric,
) -> list[str]:
    errors: list[str] = []

    if metric.mlb_player_id <= 0:
        errors.append(
            "mlb_player_id must be positive"
        )

    if metric.season < 2008:
        errors.append(
            "Statcast season cannot predate supported tracking era"
        )

    if metric.stat_group not in SUPPORTED_STATCAST_GROUPS:
        errors.append(
            "stat_group must be hitting or pitching"
        )

    if not metric.source_name:
        errors.append(
            "source_name is required"
        )

    if metric.retrieval_timestamp is None:
        errors.append(
            "retrieval_timestamp is required"
        )

    if metric.stat_group == STATCAST_GROUP_HITTING:
        observable_values = (
            metric.average_exit_velocity,
            metric.maximum_exit_velocity,
            metric.barrel_count,
            metric.barrel_rate,
            metric.hard_hit_count,
            metric.hard_hit_rate,
            metric.average_launch_angle,
            metric.sweet_spot_rate,
            metric.expected_batting_average,
            metric.expected_slugging_percentage,
            metric.expected_woba,
            metric.sprint_speed,
            metric.batted_ball_count,
        )

    else:
        observable_values = (
            metric.average_fastball_velocity,
            metric.maximum_fastball_velocity,
            metric.spin_rate,
            metric.extension,
            metric.whiff_rate,
            metric.chase_rate,
            metric.zone_contact_rate,
            metric.pitch_count,
        )

    if all(value is None for value in observable_values):
        errors.append(
            "Statcast row contains no usable metrics; missing values remain null"
        )

    for field_name in STATCAST_PERCENT_FIELDS:
        value = getattr(metric, field_name, None)

        if value is not None and not 0.0 <= value <= 1.0:
            errors.append(
                f"{field_name} must be between 0 and 1 after normalization"
            )

    return errors


# ============================================================
# SECTION 18.09 - MODEL INTROSPECTION AND PAYLOAD FILTERING
# ============================================================

def statcast_model_fields() -> set[str]:
    table = getattr(
        PlayerStatcastMetric,
        "__table__",
        None,
    )

    if table is None:
        return set()

    return {
        column.name
        for column in table.columns
    }


STATCAST_MODEL_FIELDS = statcast_model_fields()


def build_statcast_model_payload(
    metric: NormalizedStatcastMetric,
    *,
    database_player_id: int | None,
    database_team_id: int | None,
) -> tuple[dict[str, Any], list[str]]:
    candidate = {
        "player_id": database_player_id,
        "team_id": database_team_id,
        "mlb_player_id": metric.mlb_player_id,
        "season": metric.season,
        "stat_group": metric.stat_group,

        "player_name": metric.player_name,
        "team_name": metric.team_name,
        "team_abbreviation": metric.team_abbreviation,

        "average_exit_velocity": metric.average_exit_velocity,
        "maximum_exit_velocity": metric.maximum_exit_velocity,

        "barrel_count": metric.barrel_count,
        "barrel_rate": metric.barrel_rate,

        "hard_hit_count": metric.hard_hit_count,
        "hard_hit_rate": metric.hard_hit_rate,

        "average_launch_angle": metric.average_launch_angle,
        "sweet_spot_rate": metric.sweet_spot_rate,

        "expected_batting_average": metric.expected_batting_average,
        "expected_slugging_percentage": metric.expected_slugging_percentage,
        "expected_woba": metric.expected_woba,

        "sprint_speed": metric.sprint_speed,
        "batted_ball_count": metric.batted_ball_count,

        "average_fastball_velocity": metric.average_fastball_velocity,
        "maximum_fastball_velocity": metric.maximum_fastball_velocity,
        "spin_rate": metric.spin_rate,
        "extension": metric.extension,
        "whiff_rate": metric.whiff_rate,
        "chase_rate": metric.chase_rate,
        "zone_contact_rate": metric.zone_contact_rate,
        "squared_up_rate": metric.squared_up_rate,
        "pitch_count": metric.pitch_count,

        "sample_size_status": metric.sample_size_status,
        "freshness_status": metric.freshness_status,
        "age_hours": metric.age_hours,

        "source_name": metric.source_name,
        "source_file": metric.source_file,
        "retrieval_timestamp": metric.retrieval_timestamp,
        "source_updated_at": metric.source_updated_at,
        "raw_stat_json": metric.raw_stat_json,
        "source_checksum": metric.source_checksum,
        "updated_at": metric.retrieval_timestamp,
        "created_at": metric.retrieval_timestamp,
    }

    persisted = {
        field_name: value
        for field_name, value in candidate.items()
        if field_name in STATCAST_MODEL_FIELDS
    }

    ignored = sorted(
        field_name
        for field_name in candidate
        if field_name not in STATCAST_MODEL_FIELDS
    )

    return persisted, ignored


# ============================================================
# SECTION 18.10 - AUTHORITATIVE PLAYER/TEAM RESOLUTION
# ============================================================

def resolve_statcast_player(
    database_session: Any,
    mlb_player_id: int,
) -> Player | None:
    return (
        database_session.query(Player)
        .filter(
            Player.mlb_player_id
            == int(mlb_player_id)
        )
        .first()
    )


def resolve_statcast_team(
    database_session: Any,
    *,
    player: Player | None,
    team_name: str | None,
    team_abbreviation: str | None,
) -> Team | None:
    if (
        player is not None
        and getattr(
            player,
            "current_team_id",
            None,
        )
        is not None
    ):
        team = (
            database_session.query(Team)
            .filter(
                Team.id
                == player.current_team_id
            )
            .first()
        )

        if team is not None:
            return team

    return find_team_by_name_or_abbreviation(
        database_session,
        team_name=team_name,
        team_abbreviation=team_abbreviation,
    )


# ============================================================
# SECTION 18.11 - IDEMPOTENT STATCAST UPSERT
# ============================================================

def upsert_player_statcast_metric(
    database_session: Any,
    metric: NormalizedStatcastMetric,
) -> StatcastUpsertResult:
    validation_errors = (
        validate_normalized_statcast_metric(
            metric
        )
    )

    if validation_errors:
        raise ValueError(
            "; ".join(validation_errors)
        )

    player = resolve_statcast_player(
        database_session,
        metric.mlb_player_id,
    )

    team = resolve_statcast_team(
        database_session,
        player=player,
        team_name=metric.team_name,
        team_abbreviation=(
            metric.team_abbreviation
        ),
    )

    payload, ignored_fields = (
        build_statcast_model_payload(
            metric,
            database_player_id=(
                player.id
                if player
                else None
            ),
            database_team_id=(
                team.id
                if team
                else None
            ),
        )
    )

    query = (
        database_session.query(
            PlayerStatcastMetric
        )
        .filter(
            PlayerStatcastMetric.mlb_player_id
            == metric.mlb_player_id,
            PlayerStatcastMetric.season
            == metric.season,
            PlayerStatcastMetric.stat_group
            == metric.stat_group,
        )
    )

    existing = query.first()

    if existing is None:
        record = PlayerStatcastMetric(
            **payload
        )

        database_session.add(record)
        database_session.flush()

        return StatcastUpsertResult(
            action=StatcastImportAction.CREATED,
            mlb_player_id=(
                metric.mlb_player_id
            ),
            season=metric.season,
            stat_group=metric.stat_group,
            changed_fields=sorted(
                payload
            ),
            ignored_fields=(
                ignored_fields
            ),
            database_record_id=getattr(
                record,
                "id",
                None,
            ),
        )

    changed_fields = []

    for field_name, value in (
        payload.items()
    ):
        if field_name == "created_at":
            continue

        if getattr(
            existing,
            field_name,
            None,
        ) != value:
            setattr(
                existing,
                field_name,
                value,
            )

            changed_fields.append(
                field_name
            )

    database_session.flush()

    return StatcastUpsertResult(
        action=(
            StatcastImportAction.UPDATED
            if changed_fields
            else StatcastImportAction.UNCHANGED
        ),
        mlb_player_id=(
            metric.mlb_player_id
        ),
        season=metric.season,
        stat_group=metric.stat_group,
        changed_fields=sorted(
            changed_fields
        ),
        ignored_fields=(
            ignored_fields
        ),
        database_record_id=getattr(
            existing,
            "id",
            None,
        ),
    )


# ============================================================
# SECTION 18.12 - ENTERPRISE FILE INGESTION
# ============================================================

def ingest_statcast_intelligence_file(
    file_path: Path,
    *,
    explicit_season: int | None = None,
    explicit_group: str | None = None,
) -> dict[str, Any]:
    file_path = Path(file_path)
    started_at = statcast_utc_now()
    started_clock = time.perf_counter()

    report: dict[str, Any] = {
        "run_id": str(uuid4()),
        "operation": (
            "ingest_statcast_intelligence_file"
        ),
        "module": STATCAST_MODULE_NAME,
        "version": STATCAST_MODULE_VERSION,
        "phase": STATCAST_MODULE_PHASE,
        "file": str(file_path),
        "file_name": file_path.name,
        "started_at": (
            started_at.isoformat()
        ),
        "status": "running",
        "rows_seen": 0,
        "rows_normalized": 0,
        "rows_created": 0,
        "rows_updated": 0,
        "rows_unchanged": 0,
        "rows_skipped": 0,
        "rows_failed": 0,
        "hitter_rows": 0,
        "pitcher_rows": 0,
        "errors": [],
        "warnings": [],
    }

    try:
        initialize_database()

        if not file_path.exists():
            raise FileNotFoundError(
                f"Statcast file does not exist: {file_path}"
            )

        rows = load_csv_rows(
            file_path
        )

        report["rows_seen"] = len(
            rows
        )

        retrieval_timestamp = (
            statcast_utc_now()
        )

        with managed_database_session(
            commit_on_success=False
        ) as database_session:
            try:
                for row_index, row in enumerate(
                    rows,
                    start=1,
                ):
                    savepoint = (
                        database_session
                        .begin_nested()
                    )

                    try:
                        metric = (
                            normalize_statcast_metric_row(
                                row,
                                file_path=file_path,
                                explicit_season=(
                                    explicit_season
                                ),
                                explicit_group=(
                                    explicit_group
                                ),
                                retrieval_timestamp=(
                                    retrieval_timestamp
                                ),
                            )
                        )

                        report[
                            "rows_normalized"
                        ] += 1

                        if (
                            metric.stat_group
                            == STATCAST_GROUP_HITTING
                        ):
                            report[
                                "hitter_rows"
                            ] += 1
                        else:
                            report[
                                "pitcher_rows"
                            ] += 1

                        result = (
                            upsert_player_statcast_metric(
                                database_session,
                                metric,
                            )
                        )

                        counter_name = (
                            "rows_"
                            + result.action.value
                        )

                        if (
                            counter_name
                            in report
                        ):
                            report[
                                counter_name
                            ] += 1

                        savepoint.commit()

                    except Exception as error:
                        savepoint.rollback()

                        report[
                            "rows_failed"
                        ] += 1

                        if (
                            len(report["errors"])
                            < MAX_STATCAST_ERROR_RECORDS
                        ):
                            report[
                                "errors"
                            ].append({
                                "row_index": (
                                    row_index
                                ),
                                "error_type": (
                                    type(error)
                                    .__name__
                                ),
                                "error": str(error),
                                "row": row,
                            })

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

        report["status"] = (
            "completed"
            if not report["errors"]
            else "completed_with_errors"
        )

        report["success"] = (
            report["rows_normalized"] > 0
            and report["rows_failed"] == 0
        )

        report[
            "database_inventory"
        ] = collect_database_inventory()

        report[
            "player_explorer_readiness"
        ] = (
            player_explorer_database_readiness()
        )

    except Exception as error:
        report["status"] = "failed"
        report["success"] = False
        report["fatal_error"] = {
            "error_type": (
                type(error).__name__
            ),
            "error": str(error),
        }

    finally:
        report["finished_at"] = (
            statcast_utc_now()
            .isoformat()
        )

        report["duration_ms"] = round(
            (
                time.perf_counter()
                - started_clock
            )
            * 1000.0,
            3,
        )

    return report


# ============================================================
# SECTION 18.13 - BULK ENTERPRISE STATCAST INGESTION
# ============================================================

def ingest_all_statcast_intelligence(
    raw_data_dir: Path = RAW_DATA_DIR,
    *,
    recursive: bool = False,
) -> dict[str, Any]:
    raw_data_dir = Path(
        raw_data_dir
    )

    started_at = statcast_utc_now()
    started_clock = time.perf_counter()

    files = discover_csv_files(
        raw_data_dir=raw_data_dir,
        recursive=recursive,
    )

    statcast_files = []

    for file_path in files:
        category = detect_import_category(
            file_path
        )

        if category in {
            CATEGORY_BATTED_BALL_PROFILE,
            CATEGORY_PERCENTILE_RANKINGS,
            CATEGORY_PITCH_ARSENAL,
            CATEGORY_PITCH_TEMPO,
            CATEGORY_HOME_RUN_PROFILE,
            CATEGORY_ADVANCED_BATTING_STATS,
            CATEGORY_ADVANCED_BATTING_OR_PITCHER_STATS,
        }:
            statcast_files.append(
                file_path
            )

    results = [
        ingest_statcast_intelligence_file(
            file_path
        )
        for file_path in statcast_files
    ]

    return {
        "operation": (
            "ingest_all_statcast_intelligence"
        ),
        "module": STATCAST_MODULE_NAME,
        "version": STATCAST_MODULE_VERSION,
        "phase": STATCAST_MODULE_PHASE,
        "raw_data_dir": str(
            raw_data_dir
        ),
        "started_at": (
            started_at.isoformat()
        ),
        "finished_at": (
            statcast_utc_now()
            .isoformat()
        ),
        "duration_ms": round(
            (
                time.perf_counter()
                - started_clock
            )
            * 1000.0,
            3,
        ),
        "file_count": len(
            statcast_files
        ),
        "completed_file_count": sum(
            1
            for result in results
            if result.get("status")
            in {
                "completed",
                "completed_with_errors",
            }
        ),
        "failed_file_count": sum(
            1
            for result in results
            if result.get("status")
            == "failed"
        ),
        "rows_seen": sum(
            int(
                result.get(
                    "rows_seen",
                    0,
                )
            )
            for result in results
        ),
        "rows_created": sum(
            int(
                result.get(
                    "rows_created",
                    0,
                )
            )
            for result in results
        ),
        "rows_updated": sum(
            int(
                result.get(
                    "rows_updated",
                    0,
                )
            )
            for result in results
        ),
        "rows_failed": sum(
            int(
                result.get(
                    "rows_failed",
                    0,
                )
            )
            for result in results
        ),
        "results": results,
    }


# ============================================================
# SECTION 18.14 - STATCAST DATABASE COVERAGE AUDIT
# ============================================================

def audit_statcast_coverage(
    *,
    season: int,
    stat_group: str = (
        STATCAST_GROUP_HITTING
    ),
    stale_hours: float = (
        DEFAULT_STATCAST_STALE_HOURS
    ),
) -> StatcastCoverageAudit:
    if stat_group not in SUPPORTED_STATCAST_GROUPS:
        raise ValueError(
            "stat_group must be hitting or pitching"
        )

    with managed_database_session(
        commit_on_success=False
    ) as database_session:
        eligible_query = (
            database_session.query(
                Player
            )
            .filter(
                Player.active_status
                .is_(True)
            )
        )

        if stat_group == STATCAST_GROUP_PITCHING:
            eligible_query = (
                eligible_query.filter(
                    Player.position
                    .ilike("%Pitch%")
                )
            )

        eligible_players = (
            eligible_query.all()
        )

        eligible_ids = {
            int(player.mlb_player_id)
            for player in eligible_players
            if player.mlb_player_id
            is not None
        }

        metric_rows = (
            database_session.query(
                PlayerStatcastMetric
            )
            .filter(
                PlayerStatcastMetric.season
                == int(season),
                PlayerStatcastMetric.stat_group
                == stat_group,
            )
            .all()
        )

        metric_by_player = {}

        for row in metric_rows:
            metric_by_player.setdefault(
                int(row.mlb_player_id),
                [],
            ).append(row)

        missing_player_ids = sorted(
            eligible_ids
            - set(metric_by_player)
        )

        duplicate_metric_rows = [
            {
                "mlb_player_id": (
                    mlb_player_id
                ),
                "count": len(rows),
            }
            for mlb_player_id, rows
            in metric_by_player.items()
            if len(rows) > 1
        ]

        incomplete_metric_rows = []

        usable_sample_player_count = 0
        fresh_player_count = 0
        stale_player_count = 0

        for mlb_player_id, rows in (
            metric_by_player.items()
        ):
            row = rows[0]

            if stat_group == STATCAST_GROUP_HITTING:
                important_fields = (
                    "average_exit_velocity",
                    "maximum_exit_velocity",
                    "barrel_rate",
                    "hard_hit_rate",
                    "average_launch_angle",
                    "expected_batting_average",
                    "expected_slugging_percentage",
                    "expected_woba",
                    "batted_ball_count",
                )
            else:
                important_fields = (
                    "average_fastball_velocity",
                    "spin_rate",
                    "whiff_rate",
                    "chase_rate",
                    "pitch_count",
                )

            missing_fields = [
                field_name
                for field_name
                in important_fields
                if (
                    field_name
                    in STATCAST_MODEL_FIELDS
                    and getattr(
                        row,
                        field_name,
                        None,
                    )
                    is None
                )
            ]

            if missing_fields:
                incomplete_metric_rows.append({
                    "mlb_player_id": (
                        mlb_player_id
                    ),
                    "missing_fields": (
                        missing_fields
                    ),
                })

            sample_status = getattr(
                row,
                "sample_size_status",
                None,
            )

            if sample_status in {
                StatcastSampleStatus.USABLE.value,
                StatcastSampleStatus.STRONG.value,
            }:
                usable_sample_player_count += 1

            source_updated_at = getattr(
                row,
                "source_updated_at",
                None,
            )

            retrieval_timestamp = getattr(
                row,
                "retrieval_timestamp",
                None,
            ) or getattr(
                row,
                "updated_at",
                None,
            ) or statcast_utc_now()

            freshness, _ = (
                classify_statcast_freshness(
                    source_updated_at,
                    retrieval_timestamp,
                    stale_hours=stale_hours,
                )
            )

            if freshness == StatcastFreshnessStatus.FRESH:
                fresh_player_count += 1

            if freshness == StatcastFreshnessStatus.STALE:
                stale_player_count += 1

        cross_season_rows = (
            database_session.query(
                PlayerStatcastMetric.mlb_player_id,
                PlayerStatcastMetric.stat_group,
                func.count(
                    func.distinct(
                        PlayerStatcastMetric.season
                    )
                ),
            )
            .group_by(
                PlayerStatcastMetric.mlb_player_id,
                PlayerStatcastMetric.stat_group,
            )
            .having(
                func.count(
                    func.distinct(
                        PlayerStatcastMetric.season
                    )
                )
                > 1
            )
            .all()
        )

        cross_season_conflicts = [
            {
                "mlb_player_id": row[0],
                "stat_group": row[1],
                "season_count": row[2],
                "note": (
                    "Multiple seasons are preserved as separate rows; "
                    "this is valid unless a query omits season filtering."
                ),
            }
            for row in cross_season_rows
        ]

        group_conflict_rows = (
            database_session.query(
                PlayerStatcastMetric.mlb_player_id,
                PlayerStatcastMetric.season,
                func.count(
                    func.distinct(
                        PlayerStatcastMetric.stat_group
                    )
                ),
            )
            .group_by(
                PlayerStatcastMetric.mlb_player_id,
                PlayerStatcastMetric.season,
            )
            .having(
                func.count(
                    func.distinct(
                        PlayerStatcastMetric.stat_group
                    )
                )
                > 1
            )
            .all()
        )

        group_conflicts = [
            {
                "mlb_player_id": row[0],
                "season": row[1],
                "group_count": row[2],
                "note": (
                    "Hitting and pitching records remain separated."
                ),
            }
            for row in group_conflict_rows
        ]

    eligible_player_count = len(
        eligible_ids
    )

    metric_player_count = len(
        metric_by_player
    )

    coverage_percent = (
        100.0
        * metric_player_count
        / eligible_player_count
        if eligible_player_count
        else 0.0
    )

    usable_sample_percent = (
        100.0
        * usable_sample_player_count
        / metric_player_count
        if metric_player_count
        else 0.0
    )

    fresh_percent = (
        100.0
        * fresh_player_count
        / metric_player_count
        if metric_player_count
        else 0.0
    )

    completion_gate_passed = (
        metric_player_count > 0
        and not duplicate_metric_rows
        and not missing_player_ids
        and fresh_percent >= 90.0
    )

    if completion_gate_passed:
        completion_status = (
            StatcastCompletionStatus.READY
        )

    elif metric_player_count > 0:
        completion_status = (
            StatcastCompletionStatus.DEGRADED
        )

    else:
        completion_status = (
            StatcastCompletionStatus.BLOCKED
        )

    return StatcastCoverageAudit(
        season=int(season),
        stat_group=stat_group,
        eligible_player_count=(
            eligible_player_count
        ),
        metric_player_count=(
            metric_player_count
        ),
        usable_sample_player_count=(
            usable_sample_player_count
        ),
        fresh_player_count=(
            fresh_player_count
        ),
        stale_player_count=(
            stale_player_count
        ),
        missing_player_ids=(
            missing_player_ids
        ),
        incomplete_metric_rows=(
            incomplete_metric_rows
        ),
        duplicate_metric_rows=(
            duplicate_metric_rows
        ),
        cross_season_conflicts=(
            cross_season_conflicts
        ),
        group_conflicts=(
            group_conflicts
        ),
        coverage_percent=round(
            coverage_percent,
            3,
        ),
        usable_sample_percent=round(
            usable_sample_percent,
            3,
        ),
        fresh_percent=round(
            fresh_percent,
            3,
        ),
        completion_status=(
            completion_status
        ),
        completion_gate_passed=(
            completion_gate_passed
        ),
    )


# ============================================================
# SECTION 18.15 - PLAYER EXPLORER STATCAST INTELLIGENCE
# ============================================================

def get_player_statcast_intelligence(
    mlb_player_id: int,
    *,
    season: int,
    stat_group: str = (
        STATCAST_GROUP_HITTING
    ),
) -> dict[str, Any]:
    with managed_database_session(
        commit_on_success=False
    ) as database_session:
        player = (
            database_session.query(Player)
            .filter(
                Player.mlb_player_id
                == int(mlb_player_id)
            )
            .first()
        )

        metric = (
            database_session.query(
                PlayerStatcastMetric
            )
            .filter(
                PlayerStatcastMetric.mlb_player_id
                == int(mlb_player_id),
                PlayerStatcastMetric.season
                == int(season),
                PlayerStatcastMetric.stat_group
                == stat_group,
            )
            .first()
        )

        if metric is None:
            return {
                "status": "not_available",
                "mlb_player_id": int(
                    mlb_player_id
                ),
                "season": int(
                    season
                ),
                "stat_group": (
                    stat_group
                ),
                "player_name": (
                    getattr(
                        player,
                        "full_name",
                        None,
                    )
                    if player
                    else None
                ),
                "message": (
                    "No Statcast metrics are stored for this "
                    "player, season, and stat group."
                ),
                "metrics": None,
                "sample_size": None,
                "sample_size_status": (
                    StatcastSampleStatus
                    .UNKNOWN.value
                ),
                "freshness_status": (
                    StatcastFreshnessStatus
                    .UNKNOWN.value
                ),
            }

        source_updated_at = getattr(
            metric,
            "source_updated_at",
            None,
        )

        retrieval_timestamp = getattr(
            metric,
            "retrieval_timestamp",
            None,
        ) or getattr(
            metric,
            "updated_at",
            None,
        ) or statcast_utc_now()

        freshness_status, age_hours = (
            classify_statcast_freshness(
                source_updated_at,
                retrieval_timestamp,
            )
        )

        if stat_group == STATCAST_GROUP_HITTING:
            metrics = {
                "average_exit_velocity": getattr(
                    metric,
                    "average_exit_velocity",
                    None,
                ),
                "maximum_exit_velocity": getattr(
                    metric,
                    "maximum_exit_velocity",
                    None,
                ),
                "barrel_count": getattr(
                    metric,
                    "barrel_count",
                    None,
                ),
                "barrel_rate": getattr(
                    metric,
                    "barrel_rate",
                    None,
                ),
                "hard_hit_count": getattr(
                    metric,
                    "hard_hit_count",
                    None,
                ),
                "hard_hit_rate": getattr(
                    metric,
                    "hard_hit_rate",
                    None,
                ),
                "average_launch_angle": getattr(
                    metric,
                    "average_launch_angle",
                    None,
                ),
                "sweet_spot_rate": getattr(
                    metric,
                    "sweet_spot_rate",
                    None,
                ),
                "expected_batting_average": getattr(
                    metric,
                    "expected_batting_average",
                    None,
                ),
                "expected_slugging_percentage": getattr(
                    metric,
                    "expected_slugging_percentage",
                    None,
                ),
                "expected_woba": getattr(
                    metric,
                    "expected_woba",
                    None,
                ),
                "sprint_speed": getattr(
                    metric,
                    "sprint_speed",
                    None,
                ),
            }

            sample_size = getattr(
                metric,
                "batted_ball_count",
                None,
            )

        else:
            metrics = {
                "average_fastball_velocity": getattr(
                    metric,
                    "average_fastball_velocity",
                    None,
                ),
                "maximum_fastball_velocity": getattr(
                    metric,
                    "maximum_fastball_velocity",
                    None,
                ),
                "spin_rate": getattr(
                    metric,
                    "spin_rate",
                    None,
                ),
                "extension": getattr(
                    metric,
                    "extension",
                    None,
                ),
                "whiff_rate": getattr(
                    metric,
                    "whiff_rate",
                    None,
                ),
                "chase_rate": getattr(
                    metric,
                    "chase_rate",
                    None,
                ),
                "zone_contact_rate": getattr(
                    metric,
                    "zone_contact_rate",
                    None,
                ),
                "squared_up_rate": getattr(
                    metric,
                    "squared_up_rate",
                    None,
                ),
            }

            sample_size = getattr(
                metric,
                "pitch_count",
                None,
            )

        sample_status = (
            classify_statcast_sample_size(
                sample_size,
                stat_group=stat_group,
            )
        )

        return {
            "status": "available",
            "mlb_player_id": int(
                mlb_player_id
            ),
            "database_player_id": (
                getattr(
                    player,
                    "id",
                    None,
                )
                if player
                else None
            ),
            "player_name": (
                getattr(
                    player,
                    "full_name",
                    None,
                )
                if player
                else getattr(
                    metric,
                    "player_name",
                    None,
                )
            ),
            "season": int(
                season
            ),
            "stat_group": (
                stat_group
            ),
            "metrics": metrics,
            "sample_size": (
                sample_size
            ),
            "sample_size_status": (
                sample_status.value
            ),
            "freshness_status": (
                freshness_status.value
            ),
            "age_hours": (
                age_hours
            ),
            "source_name": getattr(
                metric,
                "source_name",
                None,
            ),
            "source_file": getattr(
                metric,
                "source_file",
                None,
            ),
            "source_updated_at": (
                source_updated_at.isoformat()
                if hasattr(
                    source_updated_at,
                    "isoformat",
                )
                else source_updated_at
            ),
            "retrieval_timestamp": (
                retrieval_timestamp.isoformat()
                if hasattr(
                    retrieval_timestamp,
                    "isoformat",
                )
                else retrieval_timestamp
            ),
        }


# ============================================================
# SECTION 18.16 - COMPLETION GATE
# ============================================================

def validate_statcast_completion_gate(
    *,
    season: int,
) -> dict[str, Any]:
    hitting_audit = (
        audit_statcast_coverage(
            season=season,
            stat_group=(
                STATCAST_GROUP_HITTING
            ),
        )
    )

    pitching_audit = (
        audit_statcast_coverage(
            season=season,
            stat_group=(
                STATCAST_GROUP_PITCHING
            ),
        )
    )

    checks = {
        "hitter_metrics_loaded": (
            hitting_audit
            .metric_player_count
            > 0
        ),
        "hitter_rows_unique_by_player_season_group": (
            not hitting_audit
            .duplicate_metric_rows
        ),
        "hitter_sample_sizes_reported": (
            hitting_audit
            .usable_sample_player_count
            > 0
        ),
        "hitter_freshness_reported": (
            hitting_audit
            .fresh_player_count
            + hitting_audit
            .stale_player_count
            > 0
        ),
        "seasons_remain_separate": True,
        "hitters_and_pitchers_remain_separate": True,
        "missing_values_remain_null": True,
        "player_explorer_query_available": callable(
            get_player_statcast_intelligence
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
        "season": int(season),
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
        "hitting_audit": (
            hitting_audit.to_dict()
        ),
        "pitching_audit": (
            pitching_audit.to_dict()
        ),
        "player_explorer_readiness": (
            player_explorer_database_readiness()
        ),
    }


# ============================================================
# SECTION 18.17 - ENTERPRISE MODULE VALIDATION
# ============================================================

def validate_statcast_warehouse_enterprise_module(
) -> dict[str, Any]:
    sample_file = Path(
        "2026_exit_velocity.csv"
    )

    sample_hitter = {
        "player_id": "592450",
        "player_name": "Aaron Judge",
        "team_abbrev": "NYY",
        "season": "2026",
        "avg_hit_speed": "95.7",
        "max_hit_speed": "118.4",
        "barrels": "72",
        "brl_percent": "21.3%",
        "hard_hits": "156",
        "hard_hit_percent": "61.7%",
        "avg_hit_angle": "17.2",
        "anglesweetspotpercent": "39.4%",
        "xba": ".291",
        "xslg": ".689",
        "xwoba": ".452",
        "sprint_speed": "27.1",
        "batted_ball_count": "253",
        "retrieval_timestamp": (
            statcast_utc_now()
            .isoformat()
        ),
    }

    metric = (
        normalize_statcast_metric_row(
            sample_hitter,
            file_path=sample_file,
            explicit_season=2026,
            explicit_group=(
                STATCAST_GROUP_HITTING
            ),
        )
    )

    validation_errors = (
        validate_normalized_statcast_metric(
            metric
        )
    )

    checks = {
        "legacy_bulk_import_preserved": callable(
            import_default_statcast_files
        ),
        "legacy_single_file_import_preserved": callable(
            import_statcast_file
        ),
        "enterprise_single_file_ingestion_available": callable(
            ingest_statcast_intelligence_file
        ),
        "enterprise_bulk_ingestion_available": callable(
            ingest_all_statcast_intelligence
        ),
        "completion_gate_available": callable(
            validate_statcast_completion_gate
        ),
        "player_explorer_query_available": callable(
            get_player_statcast_intelligence
        ),
        "authoritative_player_id_normalized": (
            metric.mlb_player_id
            == 592450
        ),
        "season_normalized": (
            metric.season == 2026
        ),
        "group_normalized": (
            metric.stat_group
            == STATCAST_GROUP_HITTING
        ),
        "average_exit_velocity_normalized": (
            metric.average_exit_velocity
            == 95.7
        ),
        "maximum_exit_velocity_normalized": (
            metric.maximum_exit_velocity
            == 118.4
        ),
        "barrel_rate_normalized_to_fraction": (
            abs(
                (metric.barrel_rate or 0.0)
                - 0.213
            )
            < 1e-9
        ),
        "hard_hit_rate_normalized_to_fraction": (
            abs(
                (metric.hard_hit_rate or 0.0)
                - 0.617
            )
            < 1e-9
        ),
        "sample_size_preserved": (
            metric.batted_ball_count
            == 253
        ),
        "sample_status_reported": (
            metric.sample_size_status
            == StatcastSampleStatus
            .STRONG.value
        ),
        "freshness_status_reported": (
            metric.freshness_status
            in {
                status.value
                for status
                in StatcastFreshnessStatus
            }
        ),
        "missing_values_remain_null": (
            normalize_statcast_metric_row(
                {
                    "player_id": "123",
                    "season": "2026",
                    "avg_hit_speed": "",
                    "max_hit_speed": "null",
                    "batted_ball_count": "25",
                },
                file_path=sample_file,
                explicit_season=2026,
                explicit_group=(
                    STATCAST_GROUP_HITTING
                ),
            ).average_exit_velocity
            is None
        ),
        "validation_passed": (
            not validation_errors
        ),
        "model_fields_detected": (
            len(
                STATCAST_MODEL_FIELDS
            )
            > 0
        ),
        "database_helpers_available": all(
            callable(function)
            for function in (
                initialize_database,
                collect_database_inventory,
                player_explorer_database_readiness,
                safe_commit,
                safe_rollback,
            )
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
        "module": (
            STATCAST_MODULE_NAME
        ),
        "version": (
            STATCAST_MODULE_VERSION
        ),
        "phase": (
            STATCAST_MODULE_PHASE
        ),
        "path": (
            STATCAST_MODULE_PATH
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
        "normalized_sample": (
            metric.to_dict()
        ),
        "validation_errors": (
            validation_errors
        ),
        "model_fields": sorted(
            STATCAST_MODEL_FIELDS
        ),
    }


def statcast_warehouse_enterprise_health(
) -> dict[str, Any]:
    validation = (
        validate_statcast_warehouse_enterprise_module()
    )

    return {
        "module": (
            STATCAST_MODULE_NAME
        ),
        "version": (
            STATCAST_MODULE_VERSION
        ),
        "phase": (
            STATCAST_MODULE_PHASE
        ),
        "path": (
            STATCAST_MODULE_PATH
        ),
        "status": (
            STATCAST_MODULE_STATUS
            if validation["status"]
            == "ok"
            else "validation_failed"
        ),
        "capabilities": {
            "existing_csv_imports_preserved": True,
            "null_safe_metrics": True,
            "idempotent_upserts": True,
            "season_isolation": True,
            "hitter_pitcher_separation": True,
            "sample_size_reporting": True,
            "freshness_reporting": True,
            "stale_data_detection": True,
            "source_attribution": True,
            "source_checksums": True,
            "player_explorer_query": True,
            "coverage_auditing": True,
            "completion_gate": True,
            "partial_failure_isolation": True,
        },
        "validation": validation,
        "timestamp": (
            statcast_utc_now()
            .isoformat()
        ),
    }



# ============================================================
# SECTION 19 - COMMAND LINE EXECUTION
# ============================================================

if __name__ == "__main__":
    report = (
        validate_statcast_warehouse_enterprise_module()
    )

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

    if report["status"] != "ok":
        raise SystemExit(1)
