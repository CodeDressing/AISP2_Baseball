# ============================================================
# AISP2 BASEBALL
# PHASE 10 PART 1.0
# ENTERPRISE MATHEMATICAL PROBABILITY ENGINE
# FILE: 04_ai/probability_engine.py
# PURPOSE:
# Convert player, team, roster, game, and future Statcast data
# into mathematically explainable probability estimates for
# future baseball outcomes.
# ============================================================

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


# ============================================================
# SECTION 01 - ENGINE CONFIGURATION
# ============================================================

ENGINE_NAME = "AISP2 Mathematical Probability Engine"
ENGINE_VERSION = "1.0.0"
ENGINE_PHASE = "Phase 10 Part 1.0"

SUPPORTED_OUTCOMES = {
    "hit",
    "single",
    "double",
    "triple",
    "home_run",
    "walk",
    "strikeout",
    "rbi",
    "run",
    "total_bases",
}


# ============================================================
# SECTION 02 - DATA STRUCTURES
# ============================================================

@dataclass
class PlayerFeatureProfile:
    player_name: str
    team_name: str | None = None
    plate_appearances: int | None = None
    at_bats: int | None = None
    hits: int | None = None
    doubles: int | None = None
    triples: int | None = None
    home_runs: int | None = None
    walks: int | None = None
    strikeouts: int | None = None
    rbi: int | None = None
    runs: int | None = None
    batting_average: float | None = None
    on_base_percentage: float | None = None
    slugging_percentage: float | None = None
    ops: float | None = None
    barrel_rate: float | None = None
    hard_hit_rate: float | None = None
    walk_rate: float | None = None
    strikeout_rate: float | None = None


@dataclass
class TeamFeatureProfile:
    team_name: str
    runs_per_game: float | None = None
    team_ops: float | None = None
    team_woba: float | None = None
    bullpen_fatigue_score: float | None = None
    lineup_strength_score: float | None = None


@dataclass
class GameContextProfile:
    opponent_team: str | None = None
    ballpark: str | None = None
    home_game: bool | None = None
    opponent_pitcher: str | None = None
    pitcher_era: float | None = None
    pitcher_whip: float | None = None
    pitcher_strikeout_rate: float | None = None
    weather_score: float | None = None
    park_factor: float | None = None


# ============================================================
# SECTION 03 - SAFE MATH HELPERS
# ============================================================

def safe_divide(
    numerator: float | int | None,
    denominator: float | int | None,
    default: float = 0.0,
) -> float:
    if numerator is None or denominator in (None, 0):
        return default

    try:
        return float(numerator) / float(denominator)

    except (TypeError, ValueError, ZeroDivisionError):
        return default


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def logistic(
    value: float,
) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def percentage(
    probability: float,
) -> float:
    return round(
        clamp(probability, 0.0, 1.0) * 100.0,
        2,
    )


def normalize_rate(
    value: float | None,
    fallback: float,
) -> float:
    if value is None:
        return fallback

    if value > 1:
        return value / 100.0

    return value


# ============================================================
# SECTION 04 - BASE OUTCOME RATE CALCULATIONS
# ============================================================

def calculate_hit_rate(
    player: PlayerFeatureProfile,
) -> float:
    if player.batting_average is not None:
        return clamp(player.batting_average, 0.05, 0.45)

    return clamp(
        safe_divide(player.hits, player.at_bats, 0.240),
        0.05,
        0.45,
    )


def calculate_home_run_rate(
    player: PlayerFeatureProfile,
) -> float:
    plate_appearances = player.plate_appearances or player.at_bats

    base_rate = safe_divide(
        player.home_runs,
        plate_appearances,
        0.035,
    )

    barrel_rate = normalize_rate(
        player.barrel_rate,
        0.08,
    )

    hard_hit_rate = normalize_rate(
        player.hard_hit_rate,
        0.38,
    )

    blended = (
        base_rate * 0.60
        + barrel_rate * 0.25
        + hard_hit_rate * 0.15 * 0.20
    )

    return clamp(blended, 0.005, 0.18)


def calculate_walk_rate(
    player: PlayerFeatureProfile,
) -> float:
    if player.walk_rate is not None:
        return clamp(
            normalize_rate(player.walk_rate, 0.085),
            0.02,
            0.25,
        )

    return clamp(
        safe_divide(player.walks, player.plate_appearances, 0.085),
        0.02,
        0.25,
    )


def calculate_strikeout_rate(
    player: PlayerFeatureProfile,
) -> float:
    if player.strikeout_rate is not None:
        return clamp(
            normalize_rate(player.strikeout_rate, 0.225),
            0.05,
            0.45,
        )

    return clamp(
        safe_divide(player.strikeouts, player.plate_appearances, 0.225),
        0.05,
        0.45,
    )


def calculate_extra_base_rate(
    player: PlayerFeatureProfile,
) -> float:
    extra_base_hits = (
        (player.doubles or 0)
        + (player.triples or 0)
        + (player.home_runs or 0)
    )

    base_rate = safe_divide(
        extra_base_hits,
        player.at_bats,
        0.075,
    )

    slugging = player.slugging_percentage or 0.400

    slugging_boost = clamp(
        (slugging - 0.400) * 0.18,
        -0.04,
        0.08,
    )

    return clamp(
        base_rate + slugging_boost,
        0.02,
        0.22,
    )


# ============================================================
# SECTION 05 - CONTEXT ADJUSTMENT FACTORS
# ============================================================

def calculate_park_adjustment(
    context: GameContextProfile | None,
) -> float:
    if context is None:
        return 1.0

    if context.park_factor is None:
        return 1.0

    return clamp(
        context.park_factor,
        0.82,
        1.22,
    )


def calculate_pitcher_adjustment(
    outcome: str,
    context: GameContextProfile | None,
) -> float:
    if context is None:
        return 1.0

    adjustment = 1.0

    if context.pitcher_era is not None:
        if outcome in {"hit", "single", "double", "triple", "home_run", "rbi"}:
            adjustment += clamp(
                (context.pitcher_era - 4.20) * 0.035,
                -0.18,
                0.18,
            )

    if context.pitcher_whip is not None:
        if outcome in {"hit", "walk", "rbi", "run"}:
            adjustment += clamp(
                (context.pitcher_whip - 1.28) * 0.18,
                -0.16,
                0.16,
            )

    if context.pitcher_strikeout_rate is not None:
        pitcher_k_rate = normalize_rate(
            context.pitcher_strikeout_rate,
            0.225,
        )

        if outcome == "strikeout":
            adjustment += clamp(
                (pitcher_k_rate - 0.225) * 1.25,
                -0.22,
                0.22,
            )

        if outcome in {"hit", "home_run"}:
            adjustment -= clamp(
                (pitcher_k_rate - 0.225) * 0.55,
                -0.10,
                0.10,
            )

    return clamp(
        adjustment,
        0.65,
        1.35,
    )


def calculate_team_context_adjustment(
    outcome: str,
    team: TeamFeatureProfile | None,
) -> float:
    if team is None:
        return 1.0

    adjustment = 1.0

    if outcome in {"rbi", "run"}:
        if team.runs_per_game is not None:
            adjustment += clamp(
                (team.runs_per_game - 4.40) * 0.045,
                -0.18,
                0.18,
            )

        if team.lineup_strength_score is not None:
            adjustment += clamp(
                (team.lineup_strength_score - 50.0) / 250.0,
                -0.15,
                0.15,
            )

    if outcome in {"hit", "home_run", "total_bases"}:
        if team.team_ops is not None:
            adjustment += clamp(
                (team.team_ops - 0.720) * 0.40,
                -0.12,
                0.12,
            )

    return clamp(
        adjustment,
        0.70,
        1.30,
    )


def calculate_home_field_adjustment(
    context: GameContextProfile | None,
) -> float:
    if context is None or context.home_game is None:
        return 1.0

    if context.home_game:
        return 1.025

    return 0.985


# ============================================================
# SECTION 06 - OUTCOME PROBABILITY MODEL
# ============================================================

def calculate_base_probability(
    outcome: str,
    player: PlayerFeatureProfile,
) -> float:
    if outcome == "hit":
        return calculate_hit_rate(player)

    if outcome == "single":
        hit_rate = calculate_hit_rate(player)
        extra_base_rate = calculate_extra_base_rate(player)
        return clamp(hit_rate - extra_base_rate, 0.03, 0.32)

    if outcome == "double":
        return clamp(
            safe_divide(player.doubles, player.at_bats, 0.045),
            0.005,
            0.12,
        )

    if outcome == "triple":
        return clamp(
            safe_divide(player.triples, player.at_bats, 0.006),
            0.001,
            0.035,
        )

    if outcome == "home_run":
        return calculate_home_run_rate(player)

    if outcome == "walk":
        return calculate_walk_rate(player)

    if outcome == "strikeout":
        return calculate_strikeout_rate(player)

    if outcome == "rbi":
        rbi_rate = safe_divide(
            player.rbi,
            player.plate_appearances,
            0.115,
        )
        return clamp(rbi_rate, 0.03, 0.34)

    if outcome == "run":
        run_rate = safe_divide(
            player.runs,
            player.plate_appearances,
            0.120,
        )
        return clamp(run_rate, 0.03, 0.34)

    if outcome == "total_bases":
        hit_rate = calculate_hit_rate(player)
        extra_base_rate = calculate_extra_base_rate(player)
        return clamp(
            hit_rate + extra_base_rate * 0.55,
            0.08,
            0.55,
        )

    return 0.10


def calculate_adjusted_probability(
    outcome: str,
    player: PlayerFeatureProfile,
    team: TeamFeatureProfile | None = None,
    context: GameContextProfile | None = None,
) -> dict[str, Any]:
    normalized_outcome = outcome.strip().lower().replace(" ", "_")

    if normalized_outcome not in SUPPORTED_OUTCOMES:
        normalized_outcome = "hit"

    base_probability = calculate_base_probability(
        outcome=normalized_outcome,
        player=player,
    )

    park_adjustment = calculate_park_adjustment(
        context,
    )

    pitcher_adjustment = calculate_pitcher_adjustment(
        outcome=normalized_outcome,
        context=context,
    )

    team_adjustment = calculate_team_context_adjustment(
        outcome=normalized_outcome,
        team=team,
    )

    home_adjustment = calculate_home_field_adjustment(
        context,
    )

    adjusted_probability = (
        base_probability
        * park_adjustment
        * pitcher_adjustment
        * team_adjustment
        * home_adjustment
    )

    adjusted_probability = clamp(
        adjusted_probability,
        0.001,
        0.900,
    )

    confidence = calculate_prediction_confidence(
        player=player,
        team=team,
        context=context,
    )

    return {
        "engine": ENGINE_NAME,
        "engine_version": ENGINE_VERSION,
        "phase": ENGINE_PHASE,
        "player": player.player_name,
        "team": player.team_name,
        "outcome": normalized_outcome,
        "probability": percentage(adjusted_probability),
        "probability_decimal": round(adjusted_probability, 6),
        "confidence": confidence,
        "base_probability": percentage(base_probability),
        "adjustments": {
            "park_adjustment": round(park_adjustment, 4),
            "pitcher_adjustment": round(pitcher_adjustment, 4),
            "team_adjustment": round(team_adjustment, 4),
            "home_field_adjustment": round(home_adjustment, 4),
        },
        "explanation": build_probability_explanation(
            outcome=normalized_outcome,
            player=player,
            base_probability=base_probability,
            adjusted_probability=adjusted_probability,
            confidence=confidence,
        ),
        "model_status": "mathematical_baseline_ready",
        "next_model_layers": [
            "database feature extraction",
            "rolling averages",
            "pitcher-batter matchup",
            "park factors",
            "weather",
            "lineup context",
            "logistic regression calibration",
            "Monte Carlo simulation",
            "XGBoost feature ranking",
            "Bayesian live updating",
        ],
    }


# ============================================================
# SECTION 07 - CONFIDENCE MODEL
# ============================================================

def calculate_prediction_confidence(
    player: PlayerFeatureProfile,
    team: TeamFeatureProfile | None = None,
    context: GameContextProfile | None = None,
) -> float:
    confidence = 45.0

    if player.plate_appearances and player.plate_appearances >= 100:
        confidence += 12

    if player.at_bats and player.at_bats >= 100:
        confidence += 8

    if player.ops is not None:
        confidence += 5

    if player.barrel_rate is not None:
        confidence += 5

    if player.hard_hit_rate is not None:
        confidence += 5

    if team is not None:
        confidence += 5

    if context is not None:
        confidence += 5

    if context and context.opponent_pitcher:
        confidence += 4

    if context and context.park_factor is not None:
        confidence += 3

    return round(
        clamp(confidence, 35.0, 92.0),
        2,
    )


# ============================================================
# SECTION 08 - EXPLANATION BUILDER
# ============================================================

def build_probability_explanation(
    outcome: str,
    player: PlayerFeatureProfile,
    base_probability: float,
    adjusted_probability: float,
    confidence: float,
) -> list[str]:
    return [
        f"Outcome analyzed: {outcome.replace('_', ' ')}.",
        f"Base probability was calculated from {player.player_name}'s available player rates.",
        f"Base probability: {percentage(base_probability)}%.",
        f"Adjusted probability after context: {percentage(adjusted_probability)}%.",
        f"Confidence score: {confidence}%.",
        "This is a mathematical baseline model, not a trained machine-learning model yet.",
    ]


# ============================================================
# SECTION 09 - DEMO / FALLBACK PROFILE BUILDER
# ============================================================

def build_player_profile_from_dict(
    data: dict[str, Any],
) -> PlayerFeatureProfile:
    return PlayerFeatureProfile(
        player_name=data.get("player_name") or data.get("name") or "Unknown Player",
        team_name=data.get("team_name") or data.get("team"),
        plate_appearances=data.get("plate_appearances"),
        at_bats=data.get("at_bats"),
        hits=data.get("hits"),
        doubles=data.get("doubles"),
        triples=data.get("triples"),
        home_runs=data.get("home_runs"),
        walks=data.get("walks"),
        strikeouts=data.get("strikeouts"),
        rbi=data.get("rbi"),
        runs=data.get("runs"),
        batting_average=data.get("batting_average"),
        on_base_percentage=data.get("on_base_percentage"),
        slugging_percentage=data.get("slugging_percentage"),
        ops=data.get("ops"),
        barrel_rate=data.get("barrel_rate"),
        hard_hit_rate=data.get("hard_hit_rate"),
        walk_rate=data.get("walk_rate"),
        strikeout_rate=data.get("strikeout_rate"),
    )


# ============================================================
# SECTION 10 - PUBLIC PREDICTION FUNCTION
# ============================================================

def predict_player_outcome(
    player_data: dict[str, Any],
    outcome: str,
    team_data: dict[str, Any] | None = None,
    game_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    player = build_player_profile_from_dict(
        player_data,
    )

    team = None

    if team_data:
        team = TeamFeatureProfile(
            team_name=team_data.get("team_name") or team_data.get("name") or "Unknown Team",
            runs_per_game=team_data.get("runs_per_game"),
            team_ops=team_data.get("team_ops"),
            team_woba=team_data.get("team_woba"),
            bullpen_fatigue_score=team_data.get("bullpen_fatigue_score"),
            lineup_strength_score=team_data.get("lineup_strength_score"),
        )

    context = None

    if game_context:
        context = GameContextProfile(
            opponent_team=game_context.get("opponent_team"),
            ballpark=game_context.get("ballpark"),
            home_game=game_context.get("home_game"),
            opponent_pitcher=game_context.get("opponent_pitcher"),
            pitcher_era=game_context.get("pitcher_era"),
            pitcher_whip=game_context.get("pitcher_whip"),
            pitcher_strikeout_rate=game_context.get("pitcher_strikeout_rate"),
            weather_score=game_context.get("weather_score"),
            park_factor=game_context.get("park_factor"),
        )

    return calculate_adjusted_probability(
        outcome=outcome,
        player=player,
        team=team,
        context=context,
    )


# ============================================================
# SECTION 11 - LOCAL EXECUTION TEST
# ============================================================

if __name__ == "__main__":
    sample_player = {
        "player_name": "Aaron Judge",
        "team_name": "New York Yankees",
        "plate_appearances": 704,
        "at_bats": 559,
        "hits": 180,
        "doubles": 36,
        "triples": 1,
        "home_runs": 58,
        "walks": 133,
        "strikeouts": 171,
        "rbi": 144,
        "runs": 122,
        "batting_average": 0.322,
        "on_base_percentage": 0.458,
        "slugging_percentage": 0.701,
        "ops": 1.159,
        "barrel_rate": 0.26,
        "hard_hit_rate": 0.61,
        "walk_rate": 0.189,
        "strikeout_rate": 0.243,
    }

    sample_team = {
        "team_name": "New York Yankees",
        "runs_per_game": 5.05,
        "team_ops": 0.760,
        "lineup_strength_score": 72,
    }

    sample_context = {
        "opponent_team": "Boston Red Sox",
        "ballpark": "Yankee Stadium",
        "home_game": True,
        "opponent_pitcher": "Example Pitcher",
        "pitcher_era": 4.65,
        "pitcher_whip": 1.34,
        "pitcher_strikeout_rate": 0.215,
        "park_factor": 1.08,
    }

    print(
        predict_player_outcome(
            player_data=sample_player,
            outcome="home_run",
            team_data=sample_team,
            game_context=sample_context,
        )
    )