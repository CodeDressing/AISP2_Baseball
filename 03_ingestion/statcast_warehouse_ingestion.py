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


# ============================================================
# SECTION 02 - ENTERPRISE STATCAST IMPORT CONFIGURATION
# FILE: 03_ingestion/statcast_warehouse_ingestion.py
# PURPOSE: define raw-data directory, supported warehouse
# datasets, default import files, filename detection aliases,
# import categories, readiness thresholds, and ML-ready data
# routing configuration for AISP2 predictions.
# ============================================================

RAW_DATA_DIR = PROJECT_ROOT / "00_raw_data"

STATCAST_INGESTION_VERSION = "phase_11_part_4_enterprise_statcast_warehouse"

DEFAULT_IMPORT_SEASON = 2026

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
# SECTION 18 - BULK IMPORT
# ============================================================

def discover_csv_files(
    raw_data_dir: Path = RAW_DATA_DIR,
) -> list[Path]:
    if not raw_data_dir.exists():
        return []

    return sorted(
        raw_data_dir.glob("*.csv"),
        key=lambda file_path: file_path.name.lower(),
    )


def import_default_statcast_files(
    raw_data_dir: Path = RAW_DATA_DIR,
) -> dict:
    results = []

    discovered_files = discover_csv_files(
        raw_data_dir=raw_data_dir,
    )

    if discovered_files:
        import_files = discovered_files
    else:
        import_files = [
            raw_data_dir / file_name
            for file_name in DEFAULT_IMPORT_FILES
        ]

    for file_path in import_files:
        results.append(
            import_statcast_file(file_path)
        )

    return {
        "operation": "import_default_statcast_files",
        "raw_data_dir": str(raw_data_dir),
        "file_count": len(results),
        "results": results,
        "total_inserted": sum(item.get("inserted", 0) for item in results),
        "total_updated": sum(item.get("updated", 0) for item in results),
        "total_skipped": sum(item.get("skipped", 0) for item in results),
        "completed_at": utc_now_string(),
    }

# ============================================================
# SECTION 19 - COMMAND LINE EXECUTION
# ============================================================

if __name__ == "__main__":
    print()
    print("=" * 70)
    print("AISP2 STATCAST WAREHOUSE IMPORT")
    print("=" * 70)

    report = import_default_statcast_files()

    print(json.dumps(report, indent=2))

    print()
    print("Statcast warehouse import completed.")
    print()