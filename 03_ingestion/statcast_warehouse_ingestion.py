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
# SECTION 02 - IMPORT CONFIGURATION
# ============================================================

RAW_DATA_DIR = PROJECT_ROOT / "00_raw_data"

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
]


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
# SECTION 06 - FILE CATEGORY DETECTION
# ============================================================

def detect_import_category(file_path: Path) -> str:
    name = file_path.name.lower()

    if "percentile" in name:
        return "percentile_rankings"

    if "pitch_arsenal" in name or "pitch-arsenal" in name:
        return "pitch_arsenal"

    if "pitch_tempo" in name or "pitchtempo" in name:
        return "pitch_tempo"

    if "exit" in name:
        return "batted_ball_profile"

    if "stance" in name:
        return "batting_stance"

    if "homerun" in name or "home_run" in name:
        return "home_run_profile"

    if "pitcherstats" in name:
        return "advanced_batting_or_pitcher_stats"

    if name == "stats.csv":
        return "advanced_batting_stats"

    return "unknown"


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
# SECTION 17 - SINGLE FILE IMPORT
# ============================================================

def import_statcast_file(file_path: Path) -> dict:
    if not file_path.exists():
        return {
            "file": str(file_path),
            "status": "missing",
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
        }

    rows = load_csv_rows(file_path)

    category = detect_import_category(file_path)

    first_season = (
        infer_season_from_file(file_path, rows[0])
        if rows
        else None
    )

    with managed_database_session() as database_session:
        import_log = create_import_log(
            database_session=database_session,
            file_path=file_path,
            category=category,
            season=first_season,
            rows_seen=len(rows),
        )

        try:
            result = import_rows_by_category(
                database_session=database_session,
                file_path=file_path,
                category=category,
                rows=rows,
            )

            complete_import_log(
                import_log=import_log,
                rows_inserted=result["inserted"],
                rows_updated=result["updated"],
                rows_skipped=result["skipped"],
                status="completed",
            )

            return {
                "file": file_path.name,
                "category": category,
                "status": "completed",
                **result,
            }

        except Exception as error:
            complete_import_log(
                import_log=import_log,
                rows_inserted=0,
                rows_updated=0,
                rows_skipped=len(rows),
                status="failed",
                error_message=str(error),
            )

            return {
                "file": file_path.name,
                "category": category,
                "status": "failed",
                "error": str(error),
                "inserted": 0,
                "updated": 0,
                "skipped": len(rows),
            }


# ============================================================
# SECTION 18 - BULK IMPORT
# ============================================================

def import_default_statcast_files(
    raw_data_dir: Path = RAW_DATA_DIR,
) -> dict:
    results = []

    for file_name in DEFAULT_IMPORT_FILES:
        file_path = raw_data_dir / file_name

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