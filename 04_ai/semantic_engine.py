# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/semantic_engine.py
# PURPOSE: semantic interpretation layer for chatbot questions,
# player detection, team detection, outcome detection, and future
# natural language baseball intelligence routing
# ============================================================


# ============================================================
# SECTION 01 - SEMANTIC ENGINE CONSTANTS
# FILE: 04_ai/semantic_engine.py
# PURPOSE: define supported intents, outcomes, and language maps
# ============================================================

OUTCOME_KEYWORDS = {
    "home_run": [
        "home run",
        "homer",
        "hr",
        "go deep",
        "yard",
        "hit one out",
    ],
    "hit": [
        "hit",
        "base hit",
        "get on base",
        "single",
        "batting",
    ],
    "rbi": [
        "rbi",
        "run batted in",
        "drive in",
        "runs batted in",
    ],
    "total_bases": [
        "total bases",
        "bases",
        "over 1.5",
        "slugging",
        "extra bases",
    ],
    "strikeout": [
        "strikeout",
        "strikeouts",
        "k",
        "ks",
        "punchout",
        "whiff",
    ],
    "run_scored": [
        "run",
        "score",
        "scores",
        "run scored",
    ],
}


GENERAL_INTENT_KEYWORDS = {
    "list_teams": [
        "what teams",
        "teams do you",
        "available teams",
        "teams available",
        "access to teams",
    ],
    "list_players": [
        "what players",
        "players do you",
        "available players",
        "players available",
        "access to players",
    ],
    "probability": [
        "probability",
        "chance",
        "odds",
        "projection",
        "predict",
        "prediction",
        "likely",
    ],
    "compare": [
        "compare",
        "versus",
        "vs",
        "better",
        "who is more likely",
    ],
    "team_info": [
        "team",
        "roster",
        "lineup",
        "club",
    ],
    "player_info": [
        "player",
        "profile",
        "scouting",
        "analyze",
        "analysis",
    ],
}


# ============================================================
# SECTION 02 - TEXT NORMALIZATION
# FILE: 04_ai/semantic_engine.py
# PURPOSE: clean user language for semantic matching
# ============================================================

def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    return (
        value.lower()
        .replace("?", " ")
        .replace("!", " ")
        .replace(".", " ")
        .replace(",", " ")
        .replace("'", "")
        .replace('"', "")
        .strip()
    )


def contains_any_keyword(text: str, keywords: list[str]) -> bool:
    normalized = normalize_text(text)

    return any(
        keyword in normalized
        for keyword in keywords
    )


# ============================================================
# SECTION 03 - ENTITY DETECTION
# FILE: 04_ai/semantic_engine.py
# PURPOSE: detect teams and players from available data
# ============================================================

def detect_team(
    message: str,
    teams: dict,
) -> str | None:
    cleaned = normalize_text(message)

    for team_name, team_data in teams.items():
        team_clean = normalize_text(team_name)
        abbreviation = normalize_text(
            team_data.get("abbreviation", "")
        )

        if team_clean in cleaned:
            return team_name

        if abbreviation and abbreviation in cleaned.split():
            return team_name

    return None


def detect_player(
    message: str,
    player_profiles: dict,
) -> str | None:
    cleaned = normalize_text(message)

    for player_name in player_profiles.keys():
        player_clean = normalize_text(player_name)

        if player_clean in cleaned:
            return player_name

        last_name = player_clean.split()[-1]

        if last_name in cleaned.split():
            return player_name

    return None


# ============================================================
# SECTION 04 - INTENT AND OUTCOME DETECTION
# FILE: 04_ai/semantic_engine.py
# PURPOSE: classify user intent and requested prediction outcome
# ============================================================

def detect_outcome(message: str) -> str | None:
    cleaned = normalize_text(message)

    for outcome_key, keywords in OUTCOME_KEYWORDS.items():
        if contains_any_keyword(cleaned, keywords):
            return outcome_key

    return None


def detect_general_intent(message: str) -> str:
    cleaned = normalize_text(message)

    for intent_key, keywords in GENERAL_INTENT_KEYWORDS.items():
        if contains_any_keyword(cleaned, keywords):
            return intent_key

    return "general_baseball_question"


def interpret_baseball_question(
    message: str,
    teams: dict,
    player_profiles: dict,
) -> dict:
    detected_player = detect_player(
        message,
        player_profiles,
    )

    detected_team = detect_team(
        message,
        teams,
    )

    detected_outcome = detect_outcome(
        message,
    )

    detected_intent = detect_general_intent(
        message,
    )

    if detected_player and detected_outcome:
        detected_intent = "player_probability"

    if detected_team and not detected_player:
        detected_intent = "team_info"

    return {
        "message": message,
        "intent": detected_intent,
        "player": detected_player,
        "team": detected_team,
        "outcome": detected_outcome,
    }


# ============================================================
# SECTION 05 - FUTURE SEMANTIC ENGINE ROADMAP
# FILE: 04_ai/semantic_engine.py
# PURPOSE: future NLP, NLU, embeddings, and RAG expansion ledger
# ============================================================

"""
05.01 Add fuzzy matching for misspelled player names.
05.02 Add aliases for common nicknames.
05.03 Add team nickname matching.
05.04 Add outcome confidence scoring.
05.05 Add multi-player comparison parsing.
05.06 Add embedding-based semantic search.
05.07 Add vector database support.
05.08 Add RAG retrieval from baseball knowledge documents.
05.09 Add model-generated reasoning.
05.10 Add conversation memory for follow-up questions.
"""