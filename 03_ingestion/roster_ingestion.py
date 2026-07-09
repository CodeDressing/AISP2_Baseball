# ============================================================
# AISP2 BASEBALL
# PHASE 9 PART 3.0
# ENTERPRISE ROSTER INGESTION ENGINE
# FILE: 03_ingestion/roster_ingestion.py
# PURPOSE:
# Import official MLB roster data, connect players to teams,
# populate roster_entries, update Player.current_team_id, and
# prepare the warehouse for real player/team prediction features.
# ============================================================

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import requests


# ============================================================
# SECTION 01 - PROJECT PATH SETUP
# ============================================================

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[1]
DATABASE_DIR = PROJECT_ROOT / "01_database"
DATA_SOURCES_DIR = PROJECT_ROOT / "02_data_sources"
INGESTION_DIR = PROJECT_ROOT / "03_ingestion"

for path in [
    PROJECT_ROOT,
    DATABASE_DIR,
    DATA_SOURCES_DIR,
    INGESTION_DIR,
]:
    path_string = str(path)

    if path_string not in sys.path:
        sys.path.insert(0, path_string)


# ============================================================
# SECTION 02 - PROJECT IMPORTS
# ============================================================

from database import initialize_database
from database import managed_database_session

from models import Player
from models import RosterEntry
from models import Team

from mlb_stats_api import DEFAULT_SEASON

from team_ingestion import ingest_mlb_teams
from player_ingestion import ingest_mlb_players


# ============================================================
# SECTION 03 - CONFIGURATION
# ============================================================

INGESTION_NAME = "AISP2 Roster Ingestion"
INGESTION_VERSION = "1.0.0"

DEFAULT_ROSTER_SEASON = DEFAULT_SEASON
DEFAULT_ROSTER_TYPE = "active"

MLB_STATS_API_BASE_URL = "https://statsapi.mlb.com/api/v1"

SUPPORTED_ROSTER_TYPES = {
    "active",
    "fullRoster",
    "40Man",
    "depthChart",
    "nonRosterInvitees",
}


# ============================================================
# SECTION 04 - SAFE HELPERS
# ============================================================

def safe_string(value: Any) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned:
        return None

    return cleaned


def safe_integer(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None

        return int(value)

    except (TypeError, ValueError):
        return None


def safe_nested_get(
    data: dict[str, Any],
    *keys: str,
) -> Any:
    current: Any = data

    for key in keys:
        if not isinstance(current, dict):
            return None

        current = current.get(key)

    return current


def normalize_roster_type(
    roster_type: str | None,
) -> str:
    if not roster_type:
        return DEFAULT_ROSTER_TYPE

    cleaned = roster_type.strip()

    if cleaned not in SUPPORTED_ROSTER_TYPES:
        return DEFAULT_ROSTER_TYPE

    return cleaned


def serialize_json(data: Any) -> str:
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
    )


# ============================================================
# SECTION 05 - MLB API CLIENT HELPERS
# ============================================================

def fetch_mlb_json(
    path: str,
    timeout: int = 20,
) -> dict[str, Any]:
    response = requests.get(
        f"{MLB_STATS_API_BASE_URL}{path}",
        timeout=timeout,
    )

    response.raise_for_status()

    return response.json()


def fetch_team_roster_from_mlb(
    mlb_team_id: int,
    season: int = DEFAULT_ROSTER_SEASON,
    roster_type: str = DEFAULT_ROSTER_TYPE,
) -> list[dict[str, Any]]:
    normalized_roster_type = normalize_roster_type(
        roster_type,
    )

    payload = fetch_mlb_json(
        (
            f"/teams/{mlb_team_id}/roster"
            f"?season={season}"
            f"&rosterType={normalized_roster_type}"
        )
    )

    roster = payload.get(
        "roster",
        [],
    )

    if not isinstance(roster, list):
        return []

    return roster


# ============================================================
# SECTION 06 - TEAM / PLAYER LOOKUP HELPERS
# ============================================================

def get_database_team_by_mlb_id(
    database_session,
    mlb_team_id: int,
) -> Team | None:
    return (
        database_session.query(Team)
        .filter(Team.mlb_team_id == mlb_team_id)
        .first()
    )


def get_database_player_by_mlb_id(
    database_session,
    mlb_player_id: int,
) -> Player | None:
    return (
        database_session.query(Player)
        .filter(Player.mlb_player_id == mlb_player_id)
        .first()
    )


def build_team_lookup(
    database_session,
) -> dict[int, Team]:
    teams = database_session.query(Team).all()

    return {
        team.mlb_team_id: team
        for team in teams
        if team.mlb_team_id is not None
    }


def build_player_lookup(
    database_session,
) -> dict[int, Player]:
    players = database_session.query(Player).all()

    return {
        player.mlb_player_id: player
        for player in players
        if player.mlb_player_id is not None
    }


# ============================================================
# SECTION 07 - ROSTER NORMALIZATION
# ============================================================

def normalize_roster_entry_payload(
    raw_roster_entry: dict[str, Any],
    team: Team,
    player: Player,
    season: int,
    roster_type: str,
) -> dict[str, Any]:
    return {
        "season": season,
        "roster_type": roster_type,
        "jersey_number": safe_string(
            raw_roster_entry.get("jerseyNumber"),
        ),
        "status_code": safe_string(
            safe_nested_get(
                raw_roster_entry,
                "status",
                "code",
            )
        ),
        "status_description": safe_string(
            safe_nested_get(
                raw_roster_entry,
                "status",
                "description",
            )
        ),
        "team_id": team.id,
        "player_id": player.id,
    }


def extract_roster_player_id(
    raw_roster_entry: dict[str, Any],
) -> int | None:
    return safe_integer(
        safe_nested_get(
            raw_roster_entry,
            "person",
            "id",
        )
    )


def extract_roster_player_name(
    raw_roster_entry: dict[str, Any],
) -> str | None:
    return safe_string(
        safe_nested_get(
            raw_roster_entry,
            "person",
            "fullName",
        )
    )


# ============================================================
# SECTION 08 - ROSTER VALIDATION
# ============================================================

def validate_roster_entry(
    normalized_entry: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    if not normalized_entry.get("season"):
        errors.append("Missing season")

    if not normalized_entry.get("roster_type"):
        errors.append("Missing roster_type")

    if not normalized_entry.get("team_id"):
        errors.append("Missing team_id")

    if not normalized_entry.get("player_id"):
        errors.append("Missing player_id")

    return errors


# ============================================================
# SECTION 09 - ROSTER UPSERT
# ============================================================

def find_existing_roster_entry(
    database_session,
    team_id: int,
    player_id: int,
    season: int,
    roster_type: str,
) -> RosterEntry | None:
    return (
        database_session.query(RosterEntry)
        .filter(RosterEntry.team_id == team_id)
        .filter(RosterEntry.player_id == player_id)
        .filter(RosterEntry.season == season)
        .filter(RosterEntry.roster_type == roster_type)
        .first()
    )


def upsert_roster_entry(
    database_session,
    normalized_entry: dict[str, Any],
) -> str:
    existing_entry = find_existing_roster_entry(
        database_session=database_session,
        team_id=normalized_entry["team_id"],
        player_id=normalized_entry["player_id"],
        season=normalized_entry["season"],
        roster_type=normalized_entry["roster_type"],
    )

    if existing_entry is None:
        database_session.add(
            RosterEntry(
                **normalized_entry,
            )
        )

        return "created"

    for field_name, field_value in normalized_entry.items():
        setattr(
            existing_entry,
            field_name,
            field_value,
        )

    return "updated"


def update_player_current_team(
    player: Player,
    team: Team,
) -> None:
    player.current_team_id = team.id


# ============================================================
# SECTION 10 - PRE-INGESTION WAREHOUSE GUARANTEE
# ============================================================

def ensure_team_and_player_warehouse_ready(
    season: int,
) -> dict[str, Any]:
    database_report = initialize_database()

    team_report = ingest_mlb_teams(
        season=season,
    )

    player_report = ingest_mlb_players(
        season=season,
    )

    return {
        "database": database_report,
        "teams": {
            "success": team_report.get("success"),
            "created": team_report.get("created", 0),
            "updated": team_report.get("updated", 0),
            "database_count": team_report.get(
                "database_team_count_after_ingestion",
                0,
            ),
        },
        "players": {
            "success": player_report.get("success"),
            "created": player_report.get("created", 0),
            "updated": player_report.get("updated", 0),
            "database_count": player_report.get(
                "database_player_count_after_ingestion",
                0,
            ),
        },
    }


# ============================================================
# SECTION 11 - SINGLE TEAM ROSTER INGESTION
# ============================================================

def ingest_roster_for_team(
    database_session,
    team: Team,
    player_lookup: dict[int, Player],
    season: int,
    roster_type: str,
) -> dict[str, Any]:
    normalized_roster_type = normalize_roster_type(
        roster_type,
    )

    raw_roster = fetch_team_roster_from_mlb(
        mlb_team_id=team.mlb_team_id,
        season=season,
        roster_type=normalized_roster_type,
    )

    report: dict[str, Any] = {
        "team": team.name,
        "mlb_team_id": team.mlb_team_id,
        "season": season,
        "roster_type": normalized_roster_type,
        "raw_roster_count": len(raw_roster),
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "missing_players": [],
        "errors": [],
        "players": [],
    }

    for raw_entry in raw_roster:
        mlb_player_id = extract_roster_player_id(
            raw_entry,
        )

        player_name = extract_roster_player_name(
            raw_entry,
        )

        if mlb_player_id is None:
            report["skipped"] += 1
            report["errors"].append(
                {
                    "reason": "Missing MLB player id",
                    "raw_entry": raw_entry,
                }
            )
            continue

        player = player_lookup.get(
            mlb_player_id,
        )

        if player is None:
            report["skipped"] += 1
            report["missing_players"].append(
                {
                    "mlb_player_id": mlb_player_id,
                    "name": player_name,
                }
            )
            continue

        normalized_entry = normalize_roster_entry_payload(
            raw_roster_entry=raw_entry,
            team=team,
            player=player,
            season=season,
            roster_type=normalized_roster_type,
        )

        validation_errors = validate_roster_entry(
            normalized_entry,
        )

        if validation_errors:
            report["skipped"] += 1
            report["errors"].append(
                {
                    "mlb_player_id": mlb_player_id,
                    "name": player_name,
                    "errors": validation_errors,
                }
            )
            continue

        action = upsert_roster_entry(
            database_session=database_session,
            normalized_entry=normalized_entry,
        )

        update_player_current_team(
            player=player,
            team=team,
        )

        if action == "created":
            report["created"] += 1

        elif action == "updated":
            report["updated"] += 1

        report["players"].append(
            {
                "mlb_player_id": mlb_player_id,
                "name": player.full_name,
                "position": player.position,
                "team": team.name,
                "jersey_number": normalized_entry["jersey_number"],
                "status": normalized_entry["status_description"],
                "action": action,
            }
        )

    report["success"] = (
        report["raw_roster_count"] > 0
        and len(report["errors"]) == 0
    )

    return report


# ============================================================
# SECTION 12 - FULL MLB ROSTER INGESTION ENGINE
# ============================================================

def ingest_mlb_rosters(
    season: int = DEFAULT_ROSTER_SEASON,
    roster_type: str = DEFAULT_ROSTER_TYPE,
    ensure_base_data: bool = True,
) -> dict[str, Any]:
    normalized_roster_type = normalize_roster_type(
        roster_type,
    )

    preparation_report: dict[str, Any] | None = None

    if ensure_base_data:
        preparation_report = ensure_team_and_player_warehouse_ready(
            season=season,
        )
    else:
        initialize_database()

    report: dict[str, Any] = {
        "ingestion": INGESTION_NAME,
        "version": INGESTION_VERSION,
        "season": season,
        "roster_type": normalized_roster_type,
        "source": "MLB Stats API",
        "base_data_prepared": ensure_base_data,
        "preparation_report": preparation_report,
        "teams_processed": 0,
        "teams_successful": 0,
        "teams_failed": 0,
        "raw_roster_entries": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "missing_players": [],
        "errors": [],
        "team_reports": [],
    }

    with managed_database_session() as database_session:
        team_lookup = build_team_lookup(
            database_session,
        )

        player_lookup = build_player_lookup(
            database_session,
        )

        teams = sorted(
            team_lookup.values(),
            key=lambda team: team.name or "",
        )

        for team in teams:
            report["teams_processed"] += 1

            try:
                team_report = ingest_roster_for_team(
                    database_session=database_session,
                    team=team,
                    player_lookup=player_lookup,
                    season=season,
                    roster_type=normalized_roster_type,
                )

            except Exception as exc:
                report["teams_failed"] += 1
                report["errors"].append(
                    {
                        "team": team.name,
                        "mlb_team_id": team.mlb_team_id,
                        "error": str(exc),
                    }
                )
                continue

            report["team_reports"].append(
                team_report,
            )

            report["raw_roster_entries"] += team_report[
                "raw_roster_count"
            ]

            report["created"] += team_report[
                "created"
            ]

            report["updated"] += team_report[
                "updated"
            ]

            report["skipped"] += team_report[
                "skipped"
            ]

            report["missing_players"].extend(
                team_report["missing_players"]
            )

            report["errors"].extend(
                [
                    {
                        "team": team.name,
                        **error,
                    }
                    for error in team_report["errors"]
                ]
            )

            if team_report.get("success"):
                report["teams_successful"] += 1

    report["database_roster_count_after_ingestion"] = (
        count_database_roster_entries()
    )

    report["players_with_current_team_after_ingestion"] = (
        count_players_with_current_team()
    )

    report["success"] = (
        report["teams_processed"] > 0
        and report["raw_roster_entries"] > 0
        and report["teams_failed"] == 0
    )

    return report


# ============================================================
# SECTION 13 - DATABASE COUNT SERVICES
# ============================================================

def count_database_roster_entries() -> int:
    with managed_database_session() as database_session:
        return database_session.query(RosterEntry).count()


def count_players_with_current_team() -> int:
    with managed_database_session() as database_session:
        return (
            database_session.query(Player)
            .filter(Player.current_team_id.isnot(None))
            .count()
        )


def count_roster_entries_by_team() -> list[dict[str, Any]]:
    with managed_database_session() as database_session:
        teams = (
            database_session.query(Team)
            .order_by(Team.name.asc())
            .all()
        )

        inventory: list[dict[str, Any]] = []

        for team in teams:
            roster_count = (
                database_session.query(RosterEntry)
                .filter(RosterEntry.team_id == team.id)
                .count()
            )

            inventory.append(
                {
                    "mlb_team_id": team.mlb_team_id,
                    "team": team.name,
                    "abbreviation": team.abbreviation,
                    "league": team.league,
                    "division": team.division,
                    "roster_entries": roster_count,
                }
            )

        return inventory


# ============================================================
# SECTION 14 - ROSTER INVENTORY SERVICES
# ============================================================

def build_roster_inventory(
    limit: int = 1000,
) -> list[dict[str, Any]]:
    with managed_database_session() as database_session:
        entries = (
            database_session.query(RosterEntry)
            .join(Player, RosterEntry.player_id == Player.id)
            .join(Team, RosterEntry.team_id == Team.id)
            .order_by(Team.name.asc(), Player.full_name.asc())
            .limit(limit)
            .all()
        )

        inventory: list[dict[str, Any]] = []

        for entry in entries:
            inventory.append(
                {
                    "season": entry.season,
                    "roster_type": entry.roster_type,
                    "team": entry.team.name if entry.team else None,
                    "team_abbreviation": (
                        entry.team.abbreviation
                        if entry.team
                        else None
                    ),
                    "mlb_team_id": (
                        entry.team.mlb_team_id
                        if entry.team
                        else None
                    ),
                    "player": (
                        entry.player.full_name
                        if entry.player
                        else None
                    ),
                    "mlb_player_id": (
                        entry.player.mlb_player_id
                        if entry.player
                        else None
                    ),
                    "position": (
                        entry.player.position
                        if entry.player
                        else None
                    ),
                    "jersey_number": entry.jersey_number,
                    "status": entry.status_description,
                }
            )

        return inventory


def build_team_roster_inventory(
    team_query: str,
    season: int = DEFAULT_ROSTER_SEASON,
    roster_type: str | None = None,
) -> dict[str, Any]:
    clean_query = team_query.strip().lower()

    normalized_roster_type = (
        normalize_roster_type(roster_type)
        if roster_type
        else None
    )

    with managed_database_session() as database_session:
        team = (
            database_session.query(Team)
            .filter(
                Team.name.ilike(f"%{clean_query}%")
            )
            .first()
        )

        if team is None:
            team = (
                database_session.query(Team)
                .filter(
                    Team.abbreviation.ilike(f"%{clean_query}%")
                )
                .first()
            )

        if team is None:
            return {
                "found": False,
                "query": team_query,
                "team": None,
                "players": [],
            }

        query = (
            database_session.query(RosterEntry)
            .filter(RosterEntry.team_id == team.id)
            .filter(RosterEntry.season == season)
            .join(Player, RosterEntry.player_id == Player.id)
            .order_by(Player.full_name.asc())
        )

        if normalized_roster_type:
            query = query.filter(
                RosterEntry.roster_type == normalized_roster_type
            )

        entries = query.all()

        players = []

        for entry in entries:
            players.append(
                {
                    "mlb_player_id": entry.player.mlb_player_id,
                    "name": entry.player.full_name,
                    "position": entry.player.position,
                    "position_code": entry.player.position_code,
                    "bats": entry.player.bats,
                    "throws": entry.player.throws,
                    "jersey_number": entry.jersey_number,
                    "status": entry.status_description,
                }
            )

        return {
            "found": True,
            "season": season,
            "roster_type": normalized_roster_type or "all",
            "team": {
                "id": team.id,
                "mlb_team_id": team.mlb_team_id,
                "name": team.name,
                "abbreviation": team.abbreviation,
                "league": team.league,
                "division": team.division,
                "venue": team.venue,
            },
            "player_count": len(players),
            "players": players,
        }


# ============================================================
# SECTION 15 - PLAYER CURRENT TEAM SERVICE
# ============================================================

def get_player_current_team_profile(
    player_query: str,
) -> dict[str, Any]:
    clean_query = player_query.strip().lower()

    with managed_database_session() as database_session:
        player = (
            database_session.query(Player)
            .filter(Player.full_name.ilike(f"%{clean_query}%"))
            .first()
        )

        if player is None:
            return {
                "found": False,
                "query": player_query,
                "player": None,
                "team": None,
            }

        team = player.team

        return {
            "found": True,
            "player": {
                "id": player.id,
                "mlb_player_id": player.mlb_player_id,
                "name": player.full_name,
                "position": player.position,
                "position_code": player.position_code,
                "bats": player.bats,
                "throws": player.throws,
                "height": player.height,
                "weight": player.weight,
                "active_status": player.active_status,
            },
            "team": (
                {
                    "id": team.id,
                    "mlb_team_id": team.mlb_team_id,
                    "name": team.name,
                    "abbreviation": team.abbreviation,
                    "league": team.league,
                    "division": team.division,
                    "venue": team.venue,
                }
                if team
                else None
            ),
        }


# ============================================================
# SECTION 16 - WAREHOUSE READINESS REPORT
# ============================================================

def build_roster_warehouse_readiness_report() -> dict[str, Any]:
    roster_count = count_database_roster_entries()
    players_with_teams = count_players_with_current_team()
    by_team = count_roster_entries_by_team()

    teams_with_roster = [
        item
        for item in by_team
        if item["roster_entries"] > 0
    ]

    return {
        "source": "AISP2 Database Warehouse",
        "roster_entries": roster_count,
        "players_with_current_team": players_with_teams,
        "teams_with_roster": len(teams_with_roster),
        "team_roster_counts": by_team,
        "ready_for_team_roster_browser": roster_count > 0,
        "ready_for_player_team_lookup": players_with_teams > 0,
        "ready_for_prediction_feature_layer": (
            roster_count > 0
            and players_with_teams > 0
        ),
        "next_required_layers": [
            "game schedule ingestion",
            "player season statistics",
            "team season statistics",
            "Statcast features",
            "park factors",
            "probable pitchers",
            "weather context",
            "lineup context",
            "feature engineering",
        ],
    }


# ============================================================
# SECTION 17 - HUMAN READABLE SUMMARY
# ============================================================

def build_roster_ingestion_summary(
    report: dict[str, Any],
) -> str:
    return (
        f"{INGESTION_NAME} completed | "
        f"Season: {report['season']} | "
        f"Roster Type: {report['roster_type']} | "
        f"Teams Processed: {report['teams_processed']} | "
        f"Teams Successful: {report['teams_successful']} | "
        f"Raw Entries: {report['raw_roster_entries']} | "
        f"Created: {report['created']} | "
        f"Updated: {report['updated']} | "
        f"Skipped: {report['skipped']} | "
        f"Database Rosters: "
        f"{report['database_roster_count_after_ingestion']} | "
        f"Players With Team: "
        f"{report['players_with_current_team_after_ingestion']}"
    )


# ============================================================
# SECTION 18 - LOCAL EXECUTION TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 80)
    print("AISP2 ENTERPRISE ROSTER INGESTION ENGINE")
    print("=" * 80)

    ingestion_report = ingest_mlb_rosters()

    print()
    print("Roster Ingestion Summary")
    print(build_roster_ingestion_summary(ingestion_report))

    print()
    print("Team Roster Counts")
    readiness = build_roster_warehouse_readiness_report()

    for team_count in readiness["team_roster_counts"]:
        print(
            f"{team_count['abbreviation']} | "
            f"{team_count['team']} | "
            f"{team_count['roster_entries']}"
        )

    print()
    print("Warehouse Readiness")
    print(
        serialize_json(
            readiness,
        )
    )

    print()
    print("Roster ingestion completed.")
    print()


# ============================================================
# SECTION 19 - FUTURE ROSTER INGESTION ROADMAP
# ============================================================

"""
Phase 9.03:
    Connect roster ingestion endpoints to main.py.

Phase 9.04:
    Replace /players/search compatibility route with database-first
    player search plus team context.

Phase 9.05:
    Replace /teams route with database-first team list plus roster
    readiness.

Phase 9.06:
    Add active roster browser in frontend.

Phase 9.07:
    Add team roster cards.

Phase 9.08:
    Add player profile cards with current team, handedness, and
    roster status.

Phase 9.09:
    Add schedule ingestion.

Phase 9.10:
    Add player game log ingestion.

Phase 9.11:
    Add player season stat ingestion.

Phase 9.12:
    Add Statcast ingestion.

Phase 9.13:
    Add matchup feature table.

Phase 9.14:
    Add first supervised learning training table.

Phase 9.15:
    Add logistic regression baseline model.

Phase 9.16:
    Add Monte Carlo simulation layer.

Phase 9.17:
    Add Bayesian updating layer.

Phase 9.18:
    Add XGBoost feature ranking.

Phase 9.19:
    Add explainable AI prediction card builder.

Phase 9.20:
    Replace demo prediction engine with warehouse-backed model.
"""