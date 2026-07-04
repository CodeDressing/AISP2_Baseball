# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/nlp/nlu_engine.py
# PURPOSE: Natural Language Understanding layer for converting
# messy user questions into structured baseball meaning before
# intent routing, entity routing, probability routing, and
# response generation
# ============================================================


# ============================================================
# SECTION 01 - ENTERPRISE DATABASE IMPORTS
# FILE: 01_database/models.py
# PURPOSE:
# Centralized imports for the AISP2 Enterprise Baseball
# Warehouse.
#
# Every database model in the platform shares these imports.
#
# Supported Systems
# -----------------
# • MLB Teams
# • Players
# • Rosters
# • Games
# • Chat Memory
# • Continuous Learning
# • Prediction Engine
# • NLP
# • AI Chatbot
# • Future ML Pipelines
# • Data Warehouse
# ============================================================

from __future__ import annotations

from datetime import UTC
from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from database import Base


# ============================================================
# SECTION 01.01 - SHARED DATABASE DEFAULTS
# ============================================================

DEFAULT_STRING_LENGTH = 120

SHORT_STRING_LENGTH = 40

LONG_STRING_LENGTH = 255


# ============================================================
# SECTION 01.02 - SHARED TIMESTAMP FACTORY
# ============================================================

def utc_now() -> datetime:
    """
    Enterprise UTC timestamp.

    Every future model should use the same timestamp source.

    This replaces scattered timestamp generation throughout
    the project and keeps warehouse records consistent.
    """

    return datetime.now(UTC)


# ============================================================
# SECTION 01.03 - COMMON INDEX NAMES
# ============================================================

IDX_PLAYER = "idx_player"

IDX_TEAM = "idx_team"

IDX_SEASON = "idx_season"

IDX_GAME = "idx_game"

IDX_CREATED = "idx_created"

IDX_UPDATED = "idx_updated"


# ============================================================
# SECTION 01.04 - DATABASE VERSION
# ============================================================

DATABASE_MODEL_VERSION = "Phase_11_Part_1"

DATABASE_MODEL_DESCRIPTION = (
    "Enterprise Baseball Warehouse "
    "Continuous Learning Schema"
)
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
# SECTION 03 - ADVANCED LANGUAGE NORMALIZATION
# PURPOSE: clean messy human language, recover common typos,
# normalize baseball slang, normalize probability language,
# and prepare text for NLU routing
# ============================================================

NLU_DIRECT_REPLACEMENTS = {
    "whos": "who is",
    "whats": "what is",
    "wheres": "where is",
    "hows": "how is",
    "cant": "cannot",
    "wont": "will not",
    "dont": "do not",
    "doesnt": "does not",
    "isnt": "is not",
    "arent": "are not",
    "im": "i am",
    "ive": "i have",
    "id": "i would",
    "probablity": "probability",
    "probabilitys": "probability",
    "probalility": "probability",
    "likley": "likely",
    "most likley": "most likely",
    "prediciton": "prediction",
    "predicitons": "predictions",
    "projecton": "projection",
    "stat cast": "statcast",
    "basebal": "baseball",
    "baseabll": "baseball",
    "rostor": "roster",
    "rosterd": "roster",
    "homerun": "home run",
    "home-run": "home run",
    "homeurn": "home run",
    "home runn": "home run",
    "dinger": "home run",
    "dingers": "home run",
    "bomb": "home run",
    "bombs": "home run",
    "go yard": "home run",
    "goes yard": "home run",
    "long ball": "home run",
    "jack": "home run",
    "yard": "home run",
    "base knock": "hit",
    "knock": "hit",
    "ribbie": "rbi",
    "ribbies": "rbi",
    "runs batted in": "rbi",
    "run batted in": "rbi",
    "k's": "strikeouts",
    "ks": "strikeouts",
    "punchouts": "strikeouts",
    "whiffs": "strikeouts",
    "strike out": "strikeout",
    "strikout": "strikeout",
    "striekout": "strikeout",
    "total base": "total bases",
    "tb": "total bases",
    "chances": "probability",
    "chance": "probability",
    "likelyhood": "probability",
    "likelihood": "probability",
    "projection": "probability",
    "forecast": "probability",
    "odds": "probability",
    "best shot": "highest probability",
    "top shot": "highest probability",
    "best bet": "highest probability",
    "most probable": "most likely",
}


NLU_PHRASE_REPLACEMENTS = {
    "who got the best chance": "who has the highest probability",
    "who has best chance": "who has the highest probability",
    "who is the best chance": "who has the highest probability",
    "who is most likely": "who is most likely",
    "who most likely": "who is most likely",
    "whos most likely": "who is most likely",
    "whos got the best chance": "who has the highest probability",
    "who has the best shot": "who has the highest probability",
    "highest chance": "highest probability",
    "best chance": "highest probability",
    "top chance": "highest probability",
    "highest odds": "highest probability",
    "best odds": "highest probability",
    "hit home run": "hit a home run",
    "hitting home run": "hitting a home run",
    "to homer": "to hit a home run",
    "to go deep": "to hit a home run",
    "to go yard": "to hit a home run",
    "hit bomb": "hit a home run",
    "hit a bomb": "hit a home run",
    "get a hit": "record a hit",
    "gets hit": "record a hit",
    "gets a hit": "record a hit",
    "record hit": "record a hit",
}


def collapse_nlu_spaces(value: str) -> str:
    while "  " in value:
        value = value.replace("  ", " ")

    return value.strip()


def normalize_nlu_text(value: str | None) -> str:
    if not value:
        return ""

    cleaned = (
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
        .replace("_", " ")
        .replace(":", " ")
        .replace(";", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace("[", " ")
        .replace("]", " ")
        .strip()
    )

    cleaned = collapse_nlu_spaces(cleaned)

    for source_phrase, target_phrase in NLU_PHRASE_REPLACEMENTS.items():
        cleaned = cleaned.replace(
            source_phrase,
            target_phrase,
        )

    tokens = cleaned.split()
    normalized_tokens = []

    for token in tokens:
        normalized_tokens.append(
            NLU_DIRECT_REPLACEMENTS.get(
                token,
                token,
            )
        )

    cleaned = " ".join(normalized_tokens)

    for source_phrase, target_phrase in NLU_DIRECT_REPLACEMENTS.items():
        cleaned = cleaned.replace(
            source_phrase,
            target_phrase,
        )

    for source_phrase, target_phrase in NLU_PHRASE_REPLACEMENTS.items():
        cleaned = cleaned.replace(
            source_phrase,
            target_phrase,
        )

    return collapse_nlu_spaces(cleaned)


def build_language_normalization_report(
    original_message: str,
) -> dict:
    normalized_message = normalize_nlu_text(
        original_message,
    )

    return {
        "original_message": original_message,
        "normalized_message": normalized_message,
        "changed": normalized_message != normalize_nlu_text(
            str(original_message or "")
            .lower()
            .strip()
        ),
        "engine": "aisp2_nlu_language_normalizer",
    }


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
# PURPOSE: build complete normalized NLU diagnostics for
# routing, learning, fuzzy matching, and response generation
# ============================================================

def build_nlu_report(
    message: str,
    entity_report: dict | None = None,
) -> dict:
    entity_report = entity_report or {}

    language_report = build_language_normalization_report(
        message,
    )

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

    confidence = calculate_nlu_confidence(
        task=task,
        scope=scope,
        outcome=outcome,
        entity_report=entity_report,
    )

    return {
        "message": message,
        "cleaned_message": cleaned_message,
        "normalized_message": cleaned_message,
        "language": language_report,
        "question_type": detect_nlu_question_type(cleaned_message),
        "task": task,
        "scope": scope,
        "outcome": outcome,
        "best_probability_goal": detect_best_probability_goal(cleaned_message),
        "missing": missing,
        "confidence": confidence,
        "routing_ready": task != NLU_TASK_GENERAL or outcome is not None,
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
12.01 Connect fuzzy_matching.py directly into NLU reports.
12.02 Add database-backed learned typo normalization.
12.03 Add EntityAlias table lookup before entity detection.
12.04 Add player nickname normalization.
12.05 Add team nickname normalization.
12.06 Add follow-up resolution: him, that player, that team.
12.07 Add matchup parsing: Yankees vs Red Sox.
12.08 Add time parsing: tonight, tomorrow, next game.
12.09 Add stat-category parsing: OPS, ERA, WHIP, barrel rate.
12.10 Add LLM-backed fallback classifier for unknown questions.
12.11 Add training export from normalized NLU records.
12.12 Add semantic embedding routing.
"""