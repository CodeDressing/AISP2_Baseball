# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/nlp/fuzzy_matching.py
# PURPOSE: fuzzy NLP matching for misspelled players, teams,
# baseball terms, aliases, abbreviations, and user typo recovery
# ============================================================


# ============================================================
# SECTION 01 - IMPORTS
# ============================================================

from difflib import SequenceMatcher


# ============================================================
# SECTION 02 - FUZZY MATCH CONSTANTS
# ============================================================

FUZZY_ENGINE_VERSION = "phase_6_part_2"

DEFAULT_MATCH_THRESHOLD = 0.72
STRONG_MATCH_THRESHOLD = 0.86
WEAK_MATCH_THRESHOLD = 0.62

ENTITY_PLAYER = "player"
ENTITY_TEAM = "team"
ENTITY_TERM = "baseball_term"


# ============================================================
# SECTION 03 - TEXT NORMALIZATION
# ============================================================

def normalize_fuzzy_text(value: str | None) -> str:
    if not value:
        return ""

    return (
        str(value)
        .lower()
        .replace(".", "")
        .replace(",", "")
        .replace("'", "")
        .replace('"', "")
        .replace("?", "")
        .replace("!", "")
        .replace("-", " ")
        .replace("_", " ")
        .replace("  ", " ")
        .strip()
    )


# ============================================================
# SECTION 04 - SIMILARITY SCORING
# ============================================================

def calculate_similarity(
    user_value: str,
    candidate_value: str,
) -> float:
    cleaned_user_value = normalize_fuzzy_text(user_value)
    cleaned_candidate_value = normalize_fuzzy_text(candidate_value)

    if not cleaned_user_value or not cleaned_candidate_value:
        return 0.0

    if cleaned_user_value == cleaned_candidate_value:
        return 1.0

    return SequenceMatcher(
        None,
        cleaned_user_value,
        cleaned_candidate_value,
    ).ratio()


# ============================================================
# SECTION 05 - BEST MATCH FINDER
# ============================================================

def find_best_fuzzy_match(
    user_value: str,
    candidates: list[str],
    threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> dict:
    best_candidate = None
    best_score = 0.0

    for candidate in candidates:
        score = calculate_similarity(
            user_value=user_value,
            candidate_value=candidate,
        )

        if score > best_score:
            best_score = score
            best_candidate = candidate

    return {
        "matched": best_candidate is not None and best_score >= threshold,
        "query": user_value,
        "best_match": best_candidate,
        "score": round(best_score, 4),
        "threshold": threshold,
        "confidence": classify_fuzzy_confidence(best_score),
    }


# ============================================================
# SECTION 06 - CONFIDENCE CLASSIFICATION
# ============================================================

def classify_fuzzy_confidence(score: float) -> str:
    if score >= STRONG_MATCH_THRESHOLD:
        return "strong"

    if score >= DEFAULT_MATCH_THRESHOLD:
        return "moderate"

    if score >= WEAK_MATCH_THRESHOLD:
        return "weak"

    return "none"


# ============================================================
# SECTION 07 - TOKEN WINDOW MATCHING
# PURPOSE: detect misspelled names inside full sentences
# ============================================================

def build_token_windows(
    message: str,
    max_window_size: int = 4,
) -> list[str]:
    tokens = normalize_fuzzy_text(message).split()

    windows = []

    for window_size in range(1, max_window_size + 1):
        for index in range(0, len(tokens) - window_size + 1):
            windows.append(
                " ".join(tokens[index:index + window_size])
            )

    return windows


def find_best_fuzzy_entity_in_message(
    message: str,
    candidates: list[str],
    threshold: float = DEFAULT_MATCH_THRESHOLD,
    max_window_size: int = 4,
) -> dict:
    windows = build_token_windows(
        message=message,
        max_window_size=max_window_size,
    )

    best_result = {
        "matched": False,
        "query": message,
        "observed_phrase": None,
        "best_match": None,
        "score": 0.0,
        "threshold": threshold,
        "confidence": "none",
    }

    for window in windows:
        result = find_best_fuzzy_match(
            user_value=window,
            candidates=candidates,
            threshold=threshold,
        )

        if result["score"] > best_result["score"]:
            best_result = {
                **result,
                "observed_phrase": window,
            }

    return best_result


# ============================================================
# SECTION 08 - PLAYER FUZZY MATCHING
# ============================================================

def find_fuzzy_player_match(
    message: str,
    player_names: list[str],
) -> dict:
    return {
        "entity_type": ENTITY_PLAYER,
        **find_best_fuzzy_entity_in_message(
            message=message,
            candidates=player_names,
            threshold=DEFAULT_MATCH_THRESHOLD,
            max_window_size=4,
        ),
    }


# ============================================================
# SECTION 09 - TEAM FUZZY MATCHING
# ============================================================

def find_fuzzy_team_match(
    message: str,
    team_names: list[str],
) -> dict:
    return {
        "entity_type": ENTITY_TEAM,
        **find_best_fuzzy_entity_in_message(
            message=message,
            candidates=team_names,
            threshold=DEFAULT_MATCH_THRESHOLD,
            max_window_size=4,
        ),
    }


# ============================================================
# SECTION 10 - BASEBALL TERM FUZZY MATCHING
# ============================================================

BASEBALL_TERM_ALIASES = {
    "home_run": [
        "home run",
        "homer",
        "homerun",
        "homeurn",
        "hr",
        "dinger",
        "long ball",
        "go yard",
    ],
    "hit": [
        "hit",
        "base hit",
        "hitt",
        "ht",
        "get a hit",
    ],
    "strikeout": [
        "strikeout",
        "strike out",
        "strikout",
        "striekout",
        "k",
        "ks",
        "punchout",
    ],
    "rbi": [
        "rbi",
        "runs batted in",
        "run batted in",
        "rib",
        "drive in",
    ],
    "total_bases": [
        "total bases",
        "total base",
        "bases",
        "tb",
    ],
}


def flatten_baseball_terms() -> dict:
    flattened = {}

    for canonical_term, aliases in BASEBALL_TERM_ALIASES.items():
        for alias in aliases:
            flattened[alias] = canonical_term

    return flattened


def find_fuzzy_baseball_term_match(
    message: str,
) -> dict:
    flattened_terms = flatten_baseball_terms()

    result = find_best_fuzzy_entity_in_message(
        message=message,
        candidates=list(flattened_terms.keys()),
        threshold=WEAK_MATCH_THRESHOLD,
        max_window_size=3,
    )

    canonical_value = None

    if result["best_match"]:
        canonical_value = flattened_terms.get(
            result["best_match"],
        )

    return {
        "entity_type": ENTITY_TERM,
        "canonical_value": canonical_value,
        **result,
    }


# ============================================================
# SECTION 11 - FULL FUZZY NLP REPORT
# ============================================================

def build_fuzzy_nlp_report(
    message: str,
    player_names: list[str] | None = None,
    team_names: list[str] | None = None,
) -> dict:
    player_names = player_names or []
    team_names = team_names or []

    player_match = find_fuzzy_player_match(
        message=message,
        player_names=player_names,
    ) if player_names else None

    team_match = find_fuzzy_team_match(
        message=message,
        team_names=team_names,
    ) if team_names else None

    term_match = find_fuzzy_baseball_term_match(
        message=message,
    )

    return {
        "engine_version": FUZZY_ENGINE_VERSION,
        "message": message,
        "player_match": player_match,
        "team_match": team_match,
        "term_match": term_match,
        "has_player_correction": bool(player_match and player_match["matched"]),
        "has_team_correction": bool(team_match and team_match["matched"]),
        "has_term_correction": bool(term_match and term_match["matched"]),
    }


# ============================================================
# SECTION 12 - FUTURE FUZZY NLP ROADMAP
# ============================================================

"""
12.01 Connect database-backed player names.
12.02 Connect database-backed team names.
12.03 Add nickname dictionary.
12.04 Add abbreviation dictionary.
12.05 Add repeated typo learning from learning_engine.py.
12.06 Add alias promotion into EntityAliases database table.
12.07 Add phonetic matching.
12.08 Add embeddings for semantic similarity.
12.09 Add multilingual baseball phrase normalization.
12.10 Add human-review queue for new aliases.
"""