# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/context_builder.py
# PURPOSE: convert raw user chat input into structured baseball
# context for intent routing, entity detection, probability
# routing, response generation, and future learning memory
# ============================================================


# ============================================================
# SECTION 01 - CONTEXT CONSTANTS
# FILE: 04_ai/context_builder.py
# PURPOSE: define supported context task categories
# ============================================================

TASK_GENERAL_CHAT = "general_chat"
TASK_TEAM_LOOKUP = "team_lookup"
TASK_PLAYER_LOOKUP = "player_lookup"
TASK_ROSTER_LOOKUP = "roster_lookup"
TASK_PLAYER_PROBABILITY = "player_probability"
TASK_BEST_TEAM_PROBABILITY = "best_team_probability"
TASK_PLAYER_COMPARISON = "player_comparison"
TASK_TEAM_COMPARISON = "team_comparison"
TASK_HELP = "help"


# ============================================================
# SECTION 02 - CONTEXT TEXT HELPERS
# FILE: 04_ai/context_builder.py
# PURPOSE: normalize text for context classification
# ============================================================

def normalize_context_text(value: str | None) -> str:
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
        .strip()
    )


def context_contains_any(
    message: str,
    phrases: list[str],
) -> bool:
    cleaned_message = normalize_context_text(message)

    return any(
        normalize_context_text(phrase) in cleaned_message
        for phrase in phrases
    )


# ============================================================
# SECTION 03 - TASK CLASSIFICATION
# FILE: 04_ai/context_builder.py
# PURPOSE: determine the actionable baseball task
# ============================================================

def classify_context_task(
    message: str,
    intent_report: dict,
    entity_report: dict,
    semantic_report: dict | None = None,
) -> str:
    semantic_report = semantic_report or {}

    final_intent = intent_report.get(
        "final_intent",
        "",
    )

    has_team = entity_report.get(
        "has_team",
        False,
    )

    has_player = entity_report.get(
        "has_player",
        False,
    )

    has_probability_target = entity_report.get(
        "has_probability_target",
        False,
    )

    player_count = len(
        entity_report.get("players", []),
    )

    team_count = len(
        entity_report.get("teams", []),
    )

    if final_intent == "help":
        return TASK_HELP

    if player_count >= 2:
        return TASK_PLAYER_COMPARISON

    if team_count >= 2:
        return TASK_TEAM_COMPARISON

    if has_team and has_probability_target and not has_player:
        return TASK_BEST_TEAM_PROBABILITY

    if has_player and (
        final_intent == "player_probability"
        or semantic_report.get("outcome")
    ):
        return TASK_PLAYER_PROBABILITY

    if has_team and context_contains_any(
        message,
        [
            "roster",
            "lineup",
            "who is on",
            "who plays for",
            "players on",
            "show me players",
        ],
    ):
        return TASK_ROSTER_LOOKUP

    if has_team:
        return TASK_TEAM_LOOKUP

    if has_player:
        return TASK_PLAYER_LOOKUP

    return TASK_GENERAL_CHAT


# ============================================================
# SECTION 04 - ENTITY VALUE EXTRACTION
# FILE: 04_ai/context_builder.py
# PURPOSE: extract canonical team, player, outcome, and subject
# values for downstream routing
# ============================================================

def extract_context_values(
    entity_report: dict,
    semantic_report: dict | None = None,
) -> dict:
    semantic_report = semantic_report or {}

    primary_team = entity_report.get(
        "primary_team",
    )

    primary_player = entity_report.get(
        "primary_player",
    )

    primary_subject = entity_report.get(
        "primary_subject",
    )

    return {
        "team": (
            primary_team.get("canonical_name")
            if primary_team
            else semantic_report.get("team")
        ),
        "player": (
            primary_player.get("canonical_name")
            if primary_player
            else semantic_report.get("player")
        ),
        "outcome": semantic_report.get("outcome"),
        "subject": (
            primary_subject.get("canonical_name")
            if primary_subject
            else None
        ),
        "teams": [
            team["canonical_name"]
            for team in entity_report.get("teams", [])
        ],
        "players": [
            player["canonical_name"]
            for player in entity_report.get("players", [])
        ],
        "subjects": [
            subject["canonical_name"]
            for subject in entity_report.get("subjects", [])
        ],
    }


# ============================================================
# SECTION 05 - CONTEXT CONFIDENCE
# FILE: 04_ai/context_builder.py
# PURPOSE: score context readiness for response routing
# ============================================================

def calculate_context_confidence(
    task: str,
    values: dict,
    intent_report: dict,
    entity_report: dict,
    semantic_report: dict | None = None,
) -> int:
    semantic_report = semantic_report or {}

    confidence = 35

    if task != TASK_GENERAL_CHAT:
        confidence += 15

    if values.get("team"):
        confidence += 15

    if values.get("player"):
        confidence += 15

    if values.get("outcome"):
        confidence += 12

    if entity_report.get("has_probability_target"):
        confidence += 10

    confidence += min(
        int(intent_report.get("confidence", 0) / 10),
        8,
    )

    confidence += min(
        int(semantic_report.get("confidence", 0) / 10),
        8,
    )

    return min(
        confidence,
        96,
    )


# ============================================================
# SECTION 06 - FULL CONTEXT BUILDER
# FILE: 04_ai/context_builder.py
# PURPOSE: build complete structured routing context from
# user input, intent report, entity report, and semantic report
# ============================================================

def build_baseball_context(
    message: str,
    intent_report: dict,
    entity_report: dict,
    semantic_report: dict | None = None,
) -> dict:
    semantic_report = semantic_report or {}

    task = classify_context_task(
        message=message,
        intent_report=intent_report,
        entity_report=entity_report,
        semantic_report=semantic_report,
    )

    values = extract_context_values(
        entity_report=entity_report,
        semantic_report=semantic_report,
    )

    confidence = calculate_context_confidence(
        task=task,
        values=values,
        intent_report=intent_report,
        entity_report=entity_report,
        semantic_report=semantic_report,
    )

    return {
        "message": message,
        "task": task,
        "confidence": confidence,
        "team": values.get("team"),
        "player": values.get("player"),
        "outcome": values.get("outcome"),
        "subject": values.get("subject"),
        "teams": values.get("teams", []),
        "players": values.get("players", []),
        "subjects": values.get("subjects", []),
        "intent": intent_report,
        "entities": entity_report,
        "semantic": semantic_report,
    }


# ============================================================
# SECTION 07 - FUTURE CONTEXT BUILDER ROADMAP
# FILE: 04_ai/context_builder.py
# PURPOSE: future multi-turn memory, live roster context,
# and probability routing expansion ledger
# ============================================================

"""
07.01 Add conversation follow-up resolution.
07.02 Add previous team/player memory.
07.03 Add live roster fallback if no demo players exist.
07.04 Add opponent extraction.
07.05 Add date/time/game context extraction.
07.06 Add sportsbook language normalization.
07.07 Add weather and ballpark context.
07.08 Add player role context: hitter, pitcher, reliever.
07.09 Add confidence calibration from user corrections.
07.10 Add persistent interaction memory storage.
"""