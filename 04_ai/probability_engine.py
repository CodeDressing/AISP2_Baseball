# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/probability_engine.py
# PURPOSE: centralized probability calculations, player scoring,
# team ranking, outcome ranking, and future ML model routing
# ============================================================


# ============================================================
# SECTION 01 - OUTCOME WEIGHTS
# FILE: 04_ai/probability_engine.py
# PURPOSE: scoring weights used by demo probability models
# ============================================================

OUTCOME_WEIGHTS = {
    "home_run": {
        "power": 0.50,
        "form": 0.30,
        "confidence": 0.20,
    },
    "hit": {
        "contact": 0.45,
        "form": 0.35,
        "confidence": 0.20,
    },
    "rbi": {
        "power": 0.35,
        "form": 0.35,
        "confidence": 0.30,
    },
    "total_bases": {
        "power": 0.40,
        "form": 0.35,
        "confidence": 0.25,
    },
}


# ============================================================
# SECTION 02 - PROFILE NORMALIZATION
# FILE: 04_ai/probability_engine.py
# PURPOSE: convert profile language into numeric scoring
# ============================================================

FORM_SCORES = {
    "elite": 95,
    "excellent": 90,
    "hot": 85,
    "good": 75,
    "average": 60,
    "cold": 40,
}

STYLE_POWER_SCORES = {
    "power hitter": 95,
    "slugger": 92,
    "power": 90,
    "balanced": 75,
    "contact": 60,
    "speed": 50,
}


def normalize_form_score(value: str | None) -> int:
    if not value:
        return 60

    value = value.lower().strip()

    return FORM_SCORES.get(
        value,
        60,
    )


def normalize_style_score(value: str | None) -> int:
    if not value:
        return 70

    value = value.lower().strip()

    return STYLE_POWER_SCORES.get(
        value,
        70,
    )


# ============================================================
# SECTION 03 - PLAYER PROBABILITY MODEL
# FILE: 04_ai/probability_engine.py
# PURPOSE: calculate outcome probability from profile data
# ============================================================

def calculate_player_probability(
    player_name: str,
    outcome_key: str,
    player_profiles: dict,
) -> dict:

    profile = player_profiles.get(
        player_name,
    )

    if not profile:
        return {
            "player": player_name,
            "probability": 0,
            "confidence": 0,
            "profile": {},
        }

    style_score = normalize_style_score(
        profile.get("style"),
    )

    form_score = normalize_form_score(
        profile.get("recent_form"),
    )

    confidence_score = int(
        profile.get(
            "confidence",
            60,
        )
    )

    weights = OUTCOME_WEIGHTS.get(
        outcome_key,
        OUTCOME_WEIGHTS["home_run"],
    )

    probability = int(
        (
            style_score * weights.get("power", 0.4)
            + form_score * weights.get("form", 0.4)
            + confidence_score * weights.get("confidence", 0.2)
        )
    )

    probability = max(
        1,
        min(
            probability,
            99,
        ),
    )

    return {
        "player": player_name,
        "probability": probability,
        "confidence": confidence_score,
        "profile": profile,
        "outcome": outcome_key,
    }


# ============================================================
# SECTION 04 - TEAM PROBABILITY RANKING
# FILE: 04_ai/probability_engine.py
# PURPOSE: rank all players on a team for a given outcome
# ============================================================

def rank_team_players(
    team_name: str,
    outcome_key: str,
    demo_teams: dict,
    player_profiles: dict,
) -> list[dict]:

    team = demo_teams.get(
        team_name,
    )

    if not team:
        return []

    players = team.get(
        "players",
        [],
    )

    rankings = []

    for player_name in players:
        result = calculate_player_probability(
            player_name=player_name,
            outcome_key=outcome_key,
            player_profiles=player_profiles,
        )

        rankings.append(result)

    rankings.sort(
        key=lambda item: item["probability"],
        reverse=True,
    )

    return rankings


# ============================================================
# SECTION 05 - BEST PLAYER FINDER
# FILE: 04_ai/probability_engine.py
# PURPOSE: identify highest projected player on a team
# ============================================================

def get_best_team_probability(
    team_name: str,
    outcome_key: str,
    demo_teams: dict,
    player_profiles: dict,
) -> dict | None:

    rankings = rank_team_players(
        team_name=team_name,
        outcome_key=outcome_key,
        demo_teams=demo_teams,
        player_profiles=player_profiles,
    )

    if not rankings:
        return None

    return rankings[0]


# ============================================================
# SECTION 06 - TOP N PLAYER RANKINGS
# FILE: 04_ai/probability_engine.py
# PURPOSE: support top 3, top 5, top 10 style queries
# ============================================================

def get_top_team_players(
    team_name: str,
    outcome_key: str,
    demo_teams: dict,
    player_profiles: dict,
    limit: int = 5,
) -> list[dict]:

    rankings = rank_team_players(
        team_name=team_name,
        outcome_key=outcome_key,
        demo_teams=demo_teams,
        player_profiles=player_profiles,
    )

    return rankings[:limit]


# ============================================================
# SECTION 07 - PROBABILITY REPORT BUILDER
# FILE: 04_ai/probability_engine.py
# PURPOSE: standardized diagnostics for chat routing
# ============================================================

def build_probability_report(
    team_name: str | None = None,
    player_name: str | None = None,
    outcome_key: str = "home_run",
) -> dict:

    return {
        "team": team_name,
        "player": player_name,
        "outcome": outcome_key,
        "engine_version": "phase_4_part_10",
    }


# ============================================================
# SECTION 08 - FUTURE ML ROADMAP
# FILE: 04_ai/probability_engine.py
# PURPOSE: evolution from demo scoring to true ML models
# ============================================================

"""
08.01 Moneyline model
08.02 Run differential model
08.03 Total runs model
08.04 Team totals model
08.05 NRFI model
08.06 YRFI model
08.07 F5 moneyline model
08.08 Pitcher strikeout model
08.09 Batter hit model
08.10 Total bases model
08.11 Home run model
08.12 RBI model
08.13 Monte Carlo simulation engine
08.14 XGBoost model integration
08.15 Bayesian probability updates
08.16 Live in-game win probability
08.17 Weather factor engine
08.18 Ballpark factor engine
08.19 Bullpen strength model
08.20 Full sportsbook-grade prediction stack
"""