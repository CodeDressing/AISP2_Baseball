# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/semantic_engine.py
# PURPOSE: advanced semantic interpretation layer for chatbot
# questions, entity detection, aliases, outcome detection,
# confidence scoring, and future baseball NLP routing
# ============================================================


# ============================================================
# SECTION 01 - OUTCOME KEYWORDS
# FILE: 04_ai/semantic_engine.py
# PURPOSE: map baseball outcome language to prediction outcomes
# ============================================================

OUTCOME_KEYWORDS = {
    "home_run": [
        "home run", "homer", "hr", "go deep", "yard",
        "hit one out", "go yard", "dinger", "long ball",
        "leave the park", "hit a bomb",
    ],
    "hit": [
        "hit", "base hit", "single", "get a hit",
        "record a hit", "safe hit", "batting hit",
    ],
    "rbi": [
        "rbi", "run batted in", "runs batted in",
        "drive in", "drive home", "knock in",
    ],
    "total_bases": [
        "total bases", "bases", "over 1.5", "over one and a half",
        "extra bases", "slugging", "tb",
    ],
    "strikeout": [
        "strikeout", "strikeouts", "k", "ks", "punchout",
        "punchouts", "whiff", "whiffs", "fan", "fans",
    ],
    "run_scored": [
        "run scored", "score a run", "scores", "run",
        "cross the plate",
    ],
}


# ============================================================
# SECTION 02 - TEAM ALIASES
# FILE: 04_ai/semantic_engine.py
# PURPOSE: recognize team nicknames, abbreviations, cities,
# and common fan language
# ============================================================

TEAM_ALIASES = {
    "New York Yankees": ["yankees", "nyy", "bronx bombers", "new york yankees"],
    "Boston Red Sox": ["red sox", "bos", "boston", "sox", "boston red sox"],
    "Baltimore Orioles": ["orioles", "o's", "os", "bal", "baltimore"],
    "Cleveland Guardians": ["guardians", "cle", "cleveland"],
    "Detroit Tigers": ["tigers", "det", "detroit"],
    "Houston Astros": ["astros", "hou", "houston"],
    "Texas Rangers": ["rangers", "tex", "texas"],
    "Seattle Mariners": ["mariners", "sea", "seattle", "m's", "ms"],
    "New York Mets": ["mets", "nym", "new york mets"],
    "Atlanta Braves": ["braves", "atl", "atlanta"],
    "Philadelphia Phillies": ["phillies", "phi", "philadelphia", "phils"],
    "Los Angeles Dodgers": ["dodgers", "lad", "los angeles dodgers", "la dodgers"],
    "San Diego Padres": ["padres", "sd", "san diego"],
    "Chicago Cubs": ["cubs", "chc", "chicago cubs"],
}


# ============================================================
# SECTION 03 - TEXT NORMALIZATION
# FILE: 04_ai/semantic_engine.py
# PURPOSE: clean language for matching and semantic parsing
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
        .replace("’", "")
        .replace("-", " ")
        .replace("/", " ")
        .strip()
    )


def tokenize_text(value: str | None) -> list[str]:
    return [
        token
        for token in normalize_text(value).split()
        if token
    ]


def contains_any_keyword(text: str, keywords: list[str]) -> bool:
    cleaned = normalize_text(text)

    return any(
        normalize_text(keyword) in cleaned
        for keyword in keywords
    )


# ============================================================
# SECTION 04 - TEAM DETECTION
# FILE: 04_ai/semantic_engine.py
# PURPOSE: detect one or many teams from user language
# ============================================================

def detect_team(
    message: str,
    teams: dict,
) -> str | None:
    detected_teams = detect_teams(
        message,
        teams,
    )

    if not detected_teams:
        return None

    return detected_teams[0]


def detect_teams(
    message: str,
    teams: dict,
) -> list[str]:
    cleaned = normalize_text(message)
    tokens = tokenize_text(message)
    detected: list[str] = []

    for team_name, team_data in teams.items():
        team_clean = normalize_text(team_name)
        abbreviation = normalize_text(
            team_data.get("abbreviation", "")
        )

        aliases = TEAM_ALIASES.get(
            team_name,
            [],
        )

        possible_names = [
            team_clean,
            abbreviation,
            *aliases,
        ]

        for possible_name in possible_names:
            possible_clean = normalize_text(possible_name)

            if not possible_clean:
                continue

            if possible_clean in cleaned:
                detected.append(team_name)
                break

            if possible_clean in tokens:
                detected.append(team_name)
                break

    return list(dict.fromkeys(detected))


# ============================================================
# SECTION 05 - PLAYER DETECTION
# FILE: 04_ai/semantic_engine.py
# PURPOSE: detect one or many players from user language
# ============================================================

def detect_player(
    message: str,
    player_profiles: dict,
) -> str | None:
    detected_players = detect_players(
        message,
        player_profiles,
    )

    if not detected_players:
        return None

    return detected_players[0]


def detect_players(
    message: str,
    player_profiles: dict,
) -> list[str]:
    cleaned = normalize_text(message)
    tokens = tokenize_text(message)
    detected: list[str] = []

    for player_name in player_profiles.keys():
        player_clean = normalize_text(player_name)
        name_parts = player_clean.split()

        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[-1] if name_parts else ""

        if player_clean in cleaned:
            detected.append(player_name)
            continue

        if last_name and last_name in tokens:
            detected.append(player_name)
            continue

        if first_name and last_name:
            loose_pattern = f"{first_name} {last_name}"

            if loose_pattern in cleaned:
                detected.append(player_name)

    return list(dict.fromkeys(detected))


# ============================================================
# SECTION 06 - OUTCOME DETECTION
# FILE: 04_ai/semantic_engine.py
# PURPOSE: detect requested player outcome or stat target
# ============================================================

def detect_outcome(message: str) -> str | None:
    detected_outcomes = detect_outcomes(
        message,
    )

    if not detected_outcomes:
        return None

    return detected_outcomes[0]


def detect_outcomes(message: str) -> list[str]:
    cleaned = normalize_text(message)
    detected: list[str] = []

    for outcome_key, keywords in OUTCOME_KEYWORDS.items():
        for keyword in keywords:
            if normalize_text(keyword) in cleaned:
                detected.append(outcome_key)
                break

    return list(dict.fromkeys(detected))


# ============================================================
# SECTION 07 - GENERAL INTENT DETECTION
# FILE: 04_ai/semantic_engine.py
# PURPOSE: lightweight fallback intent detection
# ============================================================

GENERAL_INTENT_KEYWORDS = {
    "list_teams": [
        "what teams", "which teams", "show teams", "list teams",
        "teams do you have", "teams do you know",
    ],
    "list_players": [
        "what players", "which players", "show players", "list players",
        "players do you have", "players do you know",
    ],
    "probability": [
        "probability", "chance", "odds", "projection",
        "predict", "prediction", "likely", "can he", "will he",
    ],
    "compare": [
        "compare", "versus", "vs", "better", "who is more likely",
    ],
    "team_info": [
        "team", "roster", "lineup", "club", "organization",
    ],
    "player_info": [
        "player", "profile", "scouting", "analyze", "analysis",
    ],
}


def detect_general_intent(message: str) -> str:
    cleaned = normalize_text(message)

    for intent_key, keywords in GENERAL_INTENT_KEYWORDS.items():
        if contains_any_keyword(cleaned, keywords):
            return intent_key

    return "general_baseball_question"


# ============================================================
# SECTION 08 - CONFIDENCE SCORING
# FILE: 04_ai/semantic_engine.py
# PURPOSE: estimate semantic match confidence
# ============================================================

def calculate_semantic_confidence(
    detected_player: str | None = None,
    detected_team: str | None = None,
    detected_outcome: str | None = None,
    detected_players: list[str] | None = None,
    detected_teams: list[str] | None = None,
) -> int:
    confidence = 35

    if detected_player:
        confidence += 20

    if detected_team:
        confidence += 15

    if detected_outcome:
        confidence += 20

    if detected_players and len(detected_players) >= 2:
        confidence += 15

    if detected_teams and len(detected_teams) >= 2:
        confidence += 12

    return min(
        confidence,
        95,
    )


# ============================================================
# SECTION 09 - QUESTION INTERPRETER
# FILE: 04_ai/semantic_engine.py
# PURPOSE: combine entity, outcome, and intent detection
# into a single semantic report
# ============================================================

def interpret_baseball_question(
    message: str,
    teams: dict,
    player_profiles: dict,
) -> dict:
    detected_players = detect_players(
        message,
        player_profiles,
    )

    detected_teams = detect_teams(
        message,
        teams,
    )

    detected_outcomes = detect_outcomes(
        message,
    )

    detected_player = detected_players[0] if detected_players else None
    detected_team = detected_teams[0] if detected_teams else None
    detected_outcome = detected_outcomes[0] if detected_outcomes else None

    detected_intent = detect_general_intent(
        message,
    )

    if len(detected_players) >= 2:
        detected_intent = "compare_players"

    elif len(detected_teams) >= 2:
        detected_intent = "compare_teams"

    elif detected_player and detected_outcome:
        detected_intent = "player_probability"

    elif detected_team and not detected_player:
        detected_intent = "team_info"

    elif detected_player:
        detected_intent = "player_info"

    confidence = calculate_semantic_confidence(
        detected_player=detected_player,
        detected_team=detected_team,
        detected_outcome=detected_outcome,
        detected_players=detected_players,
        detected_teams=detected_teams,
    )

    return {
        "message": message,
        "intent": detected_intent,
        "confidence": confidence,
        "player": detected_player,
        "team": detected_team,
        "outcome": detected_outcome,
        "players": detected_players,
        "teams": detected_teams,
        "outcomes": detected_outcomes,
    }


# ============================================================
# SECTION 10 - FUTURE SEMANTIC ENGINE ROADMAP
# FILE: 04_ai/semantic_engine.py
# PURPOSE: future NLP, NLU, embeddings, and RAG expansion ledger
# ============================================================

"""
10.01 Add fuzzy matching for misspelled player names.
10.02 Add richer aliases for every MLB team.
10.03 Add player nickname matching.
10.04 Add abbreviation disambiguation.
10.05 Add outcome confidence scoring by phrase strength.
10.06 Add multi-player comparison parsing.
10.07 Add embedding-based semantic search.
10.08 Add vector database support.
10.09 Add RAG retrieval from baseball knowledge documents.
10.10 Add conversation memory for follow-up questions.
10.11 Add model-generated reasoning.
10.12 Add advanced entity relationship graph.
"""