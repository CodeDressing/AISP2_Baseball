# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/nlp/nlu_engine.py
# PURPOSE: Natural Language Understanding layer for converting
# messy user questions into structured baseball meaning before
# intent routing, entity routing, probability routing, and
# response generation
# ============================================================


# ============================================================
# SECTION 01 - NLU TASK CONSTANTS
# ============================================================

NLU_TASK_GENERAL = "general_baseball_question"
NLU_TASK_HELP = "help"
NLU_TASK_LIST_TEAMS = "list_teams"
NLU_TASK_LIST_PLAYERS = "list_players"
NLU_TASK_TEAM_LOOKUP = "team_lookup"
NLU_TASK_PLAYER_LOOKUP = "player_lookup"
NLU_TASK_ROSTER_LOOKUP = "roster_lookup"
NLU_TASK_PLAYER_PROBABILITY = "player_probability"
NLU_TASK_BEST_TEAM_PROBABILITY = "best_team_probability"
NLU_TASK_BEST_OVERALL_PROBABILITY = "best_overall_probability"
NLU_TASK_COMPARE_PLAYERS = "compare_players"
NLU_TASK_COMPARE_TEAMS = "compare_teams"
NLU_TASK_MODEL_EXPLANATION = "model_explanation"


# ============================================================
# SECTION 02 - NLU SCOPE CONSTANTS
# ============================================================

NLU_SCOPE_UNKNOWN = "unknown"
NLU_SCOPE_ALL_PLAYERS = "all_players"
NLU_SCOPE_TEAM_PLAYERS = "team_players"
NLU_SCOPE_SINGLE_PLAYER = "single_player"
NLU_SCOPE_ALL_TEAMS = "all_teams"
NLU_SCOPE_TEAM = "team"


# ============================================================
# SECTION 03 - TEXT NORMALIZATION
# ============================================================

def normalize_nlu_text(value: str | None) -> str:
    if not value:
        return ""

    return (
        str(value)
        .lower()
        .replace("?", " ")
        .replace("!", " ")
        .replace(".", " ")
        .replace(",", " ")
        .replace("'", "")
        .replace('"', "")
        .replace("’", "")
        .replace("-", " ")
        .replace("/", " ")
        .replace("  ", " ")
        .strip()
    )


def nlu_contains_any(
    message: str,
    phrases: list[str],
) -> bool:
    cleaned_message = normalize_nlu_text(message)

    return any(
        normalize_nlu_text(phrase) in cleaned_message
        for phrase in phrases
    )


# ============================================================
# SECTION 04 - QUESTION TYPE DETECTION
# ============================================================

def detect_nlu_question_type(message: str) -> str:
    cleaned_message = normalize_nlu_text(message)

    if cleaned_message.startswith("who"):
        return "who_question"

    if cleaned_message.startswith("what"):
        return "what_question"

    if cleaned_message.startswith("which"):
        return "which_question"

    if cleaned_message.startswith("how"):
        return "how_question"

    if cleaned_message.startswith("why"):
        return "why_question"

    if cleaned_message.startswith("can") or cleaned_message.startswith("will"):
        return "probability_question"

    return "statement_or_command"


# ============================================================
# SECTION 05 - OUTCOME UNDERSTANDING
# ============================================================

NLU_OUTCOME_PHRASES = {
    "home_run": [
        "home run",
        "homer",
        "hr",
        "go deep",
        "go yard",
        "hit a bomb",
        "dinger",
        "long ball",
    ],
    "hit": [
        "hit",
        "base hit",
        "get a hit",
        "record a hit",
        "single",
    ],
    "rbi": [
        "rbi",
        "run batted in",
        "drive in",
        "knock in",
    ],
    "total_bases": [
        "total bases",
        "over 1.5",
        "extra bases",
        "slugging",
    ],
    "strikeout": [
        "strikeout",
        "strikeouts",
        "ks",
        "k total",
        "punchouts",
        "whiffs",
    ],
}


def detect_nlu_outcome(message: str) -> str | None:
    for outcome_key, phrases in NLU_OUTCOME_PHRASES.items():
        if nlu_contains_any(message, phrases):
            return outcome_key

    return None


# ============================================================
# SECTION 06 - GOAL DETECTION
# ============================================================

def detect_best_probability_goal(message: str) -> bool:
    return nlu_contains_any(
        message,
        [
            "highest probability",
            "best probability",
            "highest chance",
            "best chance",
            "most likely",
            "top probability",
            "top chance",
            "best projected",
            "highest projected",
            "who has the best",
            "who has the highest",
            "who is most likely",
        ],
    )


def detect_list_goal(message: str) -> str | None:
    if nlu_contains_any(
        message,
        [
            "all teams",
            "mlb teams",
            "list teams",
            "show teams",
            "show me teams",
            "how many teams",
            "what teams",
            "normal english list",
        ],
    ):
        return NLU_TASK_LIST_TEAMS

    if nlu_contains_any(
        message,
        [
            "all players",
            "mlb players",
            "list players",
            "show players",
            "show me players",
            "how many players",
            "what players",
        ],
    ):
        return NLU_TASK_LIST_PLAYERS

    return None


def detect_help_goal(message: str) -> bool:
    return nlu_contains_any(
        message,
        [
            "help",
            "what can you do",
            "how do i use",
            "examples",
            "sample questions",
            "capabilities",
        ],
    )


def detect_comparison_goal(message: str) -> str | None:
    if nlu_contains_any(
        message,
        [
            "compare",
            " vs ",
            " versus ",
            "who is better",
            "who is more likely",
            "between",
        ],
    ):
        return NLU_TASK_COMPARE_PLAYERS

    return None


# ============================================================
# SECTION 07 - SCOPE DETECTION
# ============================================================

def detect_entity_scope(
    message: str,
    entity_report: dict | None = None,
) -> str:
    entity_report = entity_report or {}

    has_team = entity_report.get(
        "has_team",
        False,
    )

    has_player = entity_report.get(
        "has_player",
        False,
    )

    if has_player:
        return NLU_SCOPE_SINGLE_PLAYER

    if has_team:
        return NLU_SCOPE_TEAM_PLAYERS

    if nlu_contains_any(
        message,
        [
            "any player",
            "someone",
            "which player",
            "what player",
            "who has",
            "who is most likely",
            "right now",
            "overall",
            "in mlb",
            "in baseball",
        ],
    ):
        return NLU_SCOPE_ALL_PLAYERS

    if nlu_contains_any(
        message,
        [
            "all teams",
            "every team",
            "mlb teams",
        ],
    ):
        return NLU_SCOPE_ALL_TEAMS

    return NLU_SCOPE_UNKNOWN


# ============================================================
# SECTION 08 - TASK CLASSIFICATION
# ============================================================

def classify_nlu_task(
    message: str,
    entity_report: dict | None = None,
) -> str:
    entity_report = entity_report or {}

    list_goal = detect_list_goal(message)

    if list_goal:
        return list_goal

    if detect_help_goal(message):
        return NLU_TASK_HELP

    comparison_goal = detect_comparison_goal(message)

    if comparison_goal:
        return comparison_goal

    has_team = entity_report.get(
        "has_team",
        False,
    )

    has_player = entity_report.get(
        "has_player",
        False,
    )

    has_best_probability_goal = detect_best_probability_goal(
        message,
    )

    if has_best_probability_goal and has_team and not has_player:
        return NLU_TASK_BEST_TEAM_PROBABILITY

    if has_best_probability_goal and not has_team and not has_player:
        return NLU_TASK_BEST_OVERALL_PROBABILITY

    if has_player and (
        detect_nlu_outcome(message)
        or nlu_contains_any(message, ["probability", "chance", "likely", "project"])
    ):
        return NLU_TASK_PLAYER_PROBABILITY

    if has_team and nlu_contains_any(
        message,
        [
            "roster",
            "lineup",
            "who plays for",
            "who is on",
            "players on",
        ],
    ):
        return NLU_TASK_ROSTER_LOOKUP

    if has_team:
        return NLU_TASK_TEAM_LOOKUP

    if has_player:
        return NLU_TASK_PLAYER_LOOKUP

    return NLU_TASK_GENERAL


# ============================================================
# SECTION 09 - MISSING INFORMATION DETECTION
# ============================================================

def detect_missing_information(
    task: str,
    entity_report: dict | None = None,
    outcome: str | None = None,
) -> dict:
    entity_report = entity_report or {}

    has_team = entity_report.get("has_team", False)
    has_player = entity_report.get("has_player", False)

    return {
        "missing_team": task == NLU_TASK_BEST_TEAM_PROBABILITY and not has_team,
        "missing_player": task == NLU_TASK_PLAYER_PROBABILITY and not has_player,
        "missing_outcome": task in [
            NLU_TASK_PLAYER_PROBABILITY,
            NLU_TASK_BEST_TEAM_PROBABILITY,
            NLU_TASK_BEST_OVERALL_PROBABILITY,
        ] and outcome is None,
    }


# ============================================================
# SECTION 10 - FULL NLU REPORT
# ============================================================

def build_nlu_report(
    message: str,
    entity_report: dict | None = None,
) -> dict:
    entity_report = entity_report or {}

    cleaned_message = normalize_nlu_text(
        message,
    )

    outcome = detect_nlu_outcome(
        cleaned_message,
    )

    task = classify_nlu_task(
        message=cleaned_message,
        entity_report=entity_report,
    )

    scope = detect_entity_scope(
        message=cleaned_message,
        entity_report=entity_report,
    )

    missing = detect_missing_information(
        task=task,
        entity_report=entity_report,
        outcome=outcome,
    )

    return {
        "message": message,
        "cleaned_message": cleaned_message,
        "question_type": detect_nlu_question_type(cleaned_message),
        "task": task,
        "scope": scope,
        "outcome": outcome,
        "best_probability_goal": detect_best_probability_goal(cleaned_message),
        "missing": missing,
        "confidence": calculate_nlu_confidence(
            task=task,
            scope=scope,
            outcome=outcome,
            entity_report=entity_report,
        ),
    }


# ============================================================
# SECTION 11 - CONFIDENCE SCORING
# ============================================================

def calculate_nlu_confidence(
    task: str,
    scope: str,
    outcome: str | None,
    entity_report: dict | None = None,
) -> int:
    entity_report = entity_report or {}

    confidence = 35

    if task != NLU_TASK_GENERAL:
        confidence += 25

    if scope != NLU_SCOPE_UNKNOWN:
        confidence += 15

    if outcome:
        confidence += 15

    if entity_report.get("has_team"):
        confidence += 10

    if entity_report.get("has_player"):
        confidence += 10

    return min(confidence, 96)


# ============================================================
# SECTION 12 - FUTURE NLU ROADMAP
# ============================================================

"""
12.01 Add fuzzy phrase matching.
12.02 Add typo recovery.
12.03 Add LLM-backed classification.
12.04 Add embedding similarity routing.
12.05 Add multi-turn context memory.
12.06 Add follow-up resolution.
12.07 Add sportsbook language normalization.
12.08 Add live lineup context extraction.
12.09 Add time/date/game context extraction.
12.10 Add NLG response-planning layer.
"""