# ============================================================
# AISP2 BASEBALL
# PHASE 10 PART 8
# ENTERPRISE WEIGHTED INTENT DETECTION ENGINE
# FILE: 04_ai/nlp/intent_detection.py
# PURPOSE:
# Deterministic, explainable, entity-aware intent detection for
# player/team lookup, statistics, schedules, games, predictions,
# comparisons, matchup analysis, model explanation, system
# diagnostics, and future machine-learning classification.
# ============================================================

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from collections import defaultdict
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
import math
import re
import unicodedata
from typing import Any
from typing import Iterable
from typing import Mapping
from typing import Sequence


# ============================================================
# SECTION 02 - ENGINE VERSION AND PUBLIC CONTRACT
# ============================================================

INTENT_DETECTION_VERSION = "phase_10_part_8_weighted_evidence_engine"
INTENT_DETECTION_SCHEMA_VERSION = "1.0.0"

DEFAULT_MINIMUM_CONFIDENCE = 0.35
DEFAULT_AMBIGUITY_MARGIN = 0.08
DEFAULT_MAX_CANDIDATES = 8
DEFAULT_FALLBACK_INTENT = "general_baseball_question"


# ============================================================
# SECTION 03 - INTENT CONSTANTS
# ============================================================

INTENT_LIST_TEAMS = "list_teams"
INTENT_LIST_PLAYERS = "list_players"
INTENT_TEAM_INFO = "team_info"
INTENT_PLAYER_INFO = "player_info"
INTENT_ROSTER_LOOKUP = "roster_lookup"
INTENT_SCHEDULE_LOOKUP = "schedule_lookup"
INTENT_GAME_LOOKUP = "game_lookup"

INTENT_PLAYER_STAT_REQUEST = "player_stat_request"
INTENT_TEAM_STAT_REQUEST = "team_stat_request"
INTENT_STAT_REQUEST = "stat_request"

INTENT_PLAYER_PROBABILITY = "player_probability"
INTENT_TEAM_PROBABILITY = "team_probability"
INTENT_GAME_PROBABILITY = "game_probability"
INTENT_GENERAL_PROBABILITY = "general_probability"

INTENT_COMPARE_PLAYERS = "compare_players"
INTENT_COMPARE_TEAMS = "compare_teams"
INTENT_MATCHUP_ANALYSIS = "matchup_analysis"

INTENT_EXPLAIN_MODEL = "explain_model"
INTENT_HELP = "help"

INTENT_WAREHOUSE_STATUS = "warehouse_status"
INTENT_DATABASE_STATUS = "database_status"
INTENT_MODEL_STATUS = "model_status"
INTENT_DATA_SOURCE_STATUS = "data_source_status"

INTENT_GENERAL_BASEBALL = DEFAULT_FALLBACK_INTENT


# ============================================================
# SECTION 04 - INTENT GROUPS
# ============================================================

LOOKUP_INTENTS = {
    INTENT_LIST_TEAMS,
    INTENT_LIST_PLAYERS,
    INTENT_TEAM_INFO,
    INTENT_PLAYER_INFO,
    INTENT_ROSTER_LOOKUP,
    INTENT_SCHEDULE_LOOKUP,
    INTENT_GAME_LOOKUP,
}

STAT_INTENTS = {
    INTENT_PLAYER_STAT_REQUEST,
    INTENT_TEAM_STAT_REQUEST,
    INTENT_STAT_REQUEST,
}

PREDICTION_INTENTS = {
    INTENT_PLAYER_PROBABILITY,
    INTENT_TEAM_PROBABILITY,
    INTENT_GAME_PROBABILITY,
    INTENT_GENERAL_PROBABILITY,
}

COMPARISON_INTENTS = {
    INTENT_COMPARE_PLAYERS,
    INTENT_COMPARE_TEAMS,
}

ANALYSIS_INTENTS = {
    INTENT_MATCHUP_ANALYSIS,
    *STAT_INTENTS,
    *COMPARISON_INTENTS,
}

SYSTEM_INTENTS = {
    INTENT_HELP,
    INTENT_EXPLAIN_MODEL,
    INTENT_WAREHOUSE_STATUS,
    INTENT_DATABASE_STATUS,
    INTENT_MODEL_STATUS,
    INTENT_DATA_SOURCE_STATUS,
}


# ============================================================
# SECTION 05 - INTENT PRECEDENCE
# PURPOSE:
# Explicit precedence is used only after evidence scoring.
# Higher precedence resolves near ties and known collisions.
# ============================================================

INTENT_PRECEDENCE = [
    INTENT_HELP,
    INTENT_WAREHOUSE_STATUS,
    INTENT_DATABASE_STATUS,
    INTENT_MODEL_STATUS,
    INTENT_DATA_SOURCE_STATUS,
    INTENT_EXPLAIN_MODEL,
    INTENT_COMPARE_PLAYERS,
    INTENT_COMPARE_TEAMS,
    INTENT_MATCHUP_ANALYSIS,
    INTENT_PLAYER_PROBABILITY,
    INTENT_TEAM_PROBABILITY,
    INTENT_GAME_PROBABILITY,
    INTENT_GENERAL_PROBABILITY,
    INTENT_SCHEDULE_LOOKUP,
    INTENT_GAME_LOOKUP,
    INTENT_ROSTER_LOOKUP,
    INTENT_PLAYER_STAT_REQUEST,
    INTENT_TEAM_STAT_REQUEST,
    INTENT_STAT_REQUEST,
    INTENT_LIST_TEAMS,
    INTENT_LIST_PLAYERS,
    INTENT_PLAYER_INFO,
    INTENT_TEAM_INFO,
    INTENT_GENERAL_BASEBALL,
]

INTENT_PRECEDENCE_INDEX = {
    intent_name: index
    for index, intent_name in enumerate(INTENT_PRECEDENCE)
}


# ============================================================
# SECTION 06 - ENUMERATIONS
# ============================================================

class EvidenceKind(str, Enum):
    EXACT_PHRASE = "exact_phrase"
    TOKEN = "token"
    TOKEN_SET = "token_set"
    REGEX = "regex"
    ENTITY = "entity"
    QUESTION_TYPE = "question_type"
    CONTEXT = "context"
    NEGATIVE = "negative"
    PRECEDENCE = "precedence"
    FALLBACK = "fallback"


class MatchMode(str, Enum):
    PHRASE = "phrase"
    TOKEN = "token"
    TOKEN_SET = "token_set"
    REGEX = "regex"
    PREFIX = "prefix"


# ============================================================
# SECTION 07 - DATA CLASSES
# ============================================================

@dataclass(frozen=True, slots=True)
class EvidenceRule:
    intent: str
    pattern: str
    weight: float
    mode: MatchMode = MatchMode.PHRASE
    label: str | None = None
    negative: bool = False
    case_sensitive: bool = False
    whole_word: bool = True


@dataclass(slots=True)
class EvidenceMatch:
    intent: str
    rule_label: str
    pattern: str
    weight: float
    kind: EvidenceKind
    negative: bool
    start: int | None = None
    end: int | None = None
    matched_text: str | None = None


@dataclass(slots=True)
class IntentCandidate:
    intent: str
    raw_score: float = 0.0
    positive_score: float = 0.0
    negative_score: float = 0.0
    normalized_score: float = 0.0
    probability: float = 0.0
    rank: int = 0
    evidence: list[EvidenceMatch] = field(default_factory=list)

    @property
    def net_score(self) -> float:
        return self.positive_score - self.negative_score


@dataclass(slots=True)
class IntentContext:
    detected_player: str | None = None
    detected_team: str | None = None
    detected_outcome: str | None = None
    detected_players: list[str] = field(default_factory=list)
    detected_teams: list[str] = field(default_factory=list)
    previous_intent: str | None = None
    conversation_topic: str | None = None


@dataclass(slots=True)
class IntentDecision:
    message: str
    normalized_message: str
    tokens: list[str]
    question_type: str
    base_intent: str
    final_intent: str
    confidence: float
    confidence_percent: int
    ambiguous: bool
    ambiguity_margin: float
    candidates: list[IntentCandidate]
    context: IntentContext
    engine_version: str
    schema_version: str
    routing_group: str
    precedence_applied: bool
    diagnostics: dict[str, Any] = field(default_factory=dict)


# ============================================================
# SECTION 08 - NORMALIZATION
# ============================================================

WHITESPACE_PATTERN = re.compile(r"\s+")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:\+[a-z0-9]+)?")
PUNCTUATION_PATTERN = re.compile(r"[^a-z0-9+\s/]")
SLASH_PATTERN = re.compile(r"\s*/\s*")


def normalize_intent_text(value: str | None) -> str:
    """
    Normalize text without destroying baseball-specific tokens
    such as wRC+, xwOBA, over/under, and team abbreviations.
    """
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = normalized.replace("’", "'")
    normalized = normalized.lower().strip()
    normalized = normalized.replace("what's", "what is")
    normalized = normalized.replace("whats", "what is")
    normalized = normalized.replace("who's", "who is")
    normalized = normalized.replace("cant", "cannot")
    normalized = normalized.replace("won't", "will not")
    normalized = normalized.replace("wont", "will not")
    normalized = normalized.replace("n't", " not")
    normalized = SLASH_PATTERN.sub("/", normalized)
    normalized = PUNCTUATION_PATTERN.sub(" ", normalized)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized.strip()


def tokenize_intent_text(value: str | None) -> list[str]:
    return TOKEN_PATTERN.findall(normalize_intent_text(value))


def build_token_set(value: str | None) -> set[str]:
    return set(tokenize_intent_text(value))


def phrase_exists(message: str, phrases: Sequence[str]) -> bool:
    normalized = normalize_intent_text(message)
    return any(_whole_phrase_match(normalized, normalize_intent_text(p)) for p in phrases)


def _whole_phrase_match(text: str, phrase: str) -> bool:
    if not text or not phrase:
        return False
    pattern = rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])"
    return re.search(pattern, text) is not None


# ============================================================
# SECTION 09 - QUESTION TYPE DETECTION
# ============================================================

QUESTION_PREFIXES = {
    "why": "why_question",
    "how many": "quantity_question",
    "how much": "quantity_question",
    "how likely": "probability_question",
    "what are the chances": "probability_question",
    "what is the chance": "probability_question",
    "will": "probability_question",
    "can": "probability_question",
    "does": "probability_question",
    "is": "yes_no_question",
    "are": "yes_no_question",
    "when": "when_question",
    "what time": "when_question",
    "where": "where_question",
    "which": "which_question",
    "who": "who_question",
    "what": "what_question",
    "show": "command",
    "list": "command",
    "compare": "comparison_command",
    "explain": "explanation_command",
    "predict": "prediction_command",
}


def detect_question_type(message: str) -> str:
    normalized = normalize_intent_text(message)

    for prefix, question_type in sorted(
        QUESTION_PREFIXES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if normalized == prefix or normalized.startswith(prefix + " "):
            return question_type

    return "statement_or_command"


# ============================================================
# SECTION 10 - WEIGHTED EVIDENCE RULE REGISTRY
# ============================================================

def _rules(intent: str, phrases: Sequence[str], weight: float) -> list[EvidenceRule]:
    return [
        EvidenceRule(
            intent=intent,
            pattern=phrase,
            weight=weight,
            mode=MatchMode.PHRASE,
            label=f"{intent}:{phrase}",
        )
        for phrase in phrases
    ]


def _token_rules(intent: str, tokens: Sequence[str], weight: float) -> list[EvidenceRule]:
    return [
        EvidenceRule(
            intent=intent,
            pattern=token,
            weight=weight,
            mode=MatchMode.TOKEN,
            label=f"{intent}:token:{token}",
        )
        for token in tokens
    ]


def _negative_rules(intent: str, phrases: Sequence[str], weight: float) -> list[EvidenceRule]:
    return [
        EvidenceRule(
            intent=intent,
            pattern=phrase,
            weight=weight,
            mode=MatchMode.PHRASE,
            label=f"{intent}:negative:{phrase}",
            negative=True,
        )
        for phrase in phrases
    ]


EVIDENCE_RULES: list[EvidenceRule] = []

# Help
EVIDENCE_RULES += _rules(INTENT_HELP, [
    "what can you do",
    "what can i ask",
    "show me what you can do",
    "how do i use this",
    "how does this work",
    "sample questions",
    "help me",
    "help",
    "commands",
    "capabilities",
], 8.0)

# Explicit system status
EVIDENCE_RULES += _rules(INTENT_WAREHOUSE_STATUS, [
    "warehouse status",
    "data warehouse status",
    "warehouse health",
    "warehouse readiness",
], 10.0)
EVIDENCE_RULES += _rules(INTENT_DATABASE_STATUS, [
    "database status",
    "database health",
    "database readiness",
    "orm status",
    "mapper status",
    "tables loaded",
], 10.0)
EVIDENCE_RULES += _rules(INTENT_MODEL_STATUS, [
    "model status",
    "prediction model status",
    "ml model status",
    "model health",
    "model readiness",
], 10.0)
EVIDENCE_RULES += _rules(INTENT_DATA_SOURCE_STATUS, [
    "data source status",
    "source status",
    "mlb api status",
    "statcast status",
    "baseball savant status",
], 10.0)

# List requests
EVIDENCE_RULES += _rules(INTENT_LIST_TEAMS, [
    "list teams",
    "show teams",
    "show me teams",
    "all teams",
    "every team",
    "teams available",
    "available teams",
    "which teams do you have",
    "what teams do you have",
    "team list",
    "mlb teams",
], 8.5)
EVIDENCE_RULES += _rules(INTENT_LIST_PLAYERS, [
    "list players",
    "show players",
    "show me players",
    "all players",
    "every player",
    "players available",
    "available players",
    "which players do you have",
    "what players do you have",
    "player list",
    "mlb players",
], 8.5)

# Roster
EVIDENCE_RULES += _rules(INTENT_ROSTER_LOOKUP, [
    "show roster",
    "show me the roster",
    "team roster",
    "active roster",
    "40 man roster",
    "40-man roster",
    "who is on the roster",
    "who is on this team",
    "roster for",
    "depth chart",
], 9.0)
EVIDENCE_RULES += _token_rules(INTENT_ROSTER_LOOKUP, ["roster"], 3.5)

# Schedule
EVIDENCE_RULES += _rules(INTENT_SCHEDULE_LOOKUP, [
    "schedule",
    "game schedule",
    "team schedule",
    "upcoming games",
    "next game",
    "next games",
    "when do they play",
    "when does he play",
    "when is the game",
    "what time is the game",
    "games this week",
    "games today",
    "games tomorrow",
], 8.5)
EVIDENCE_RULES += _token_rules(INTENT_SCHEDULE_LOOKUP, [
    "schedule",
    "upcoming",
    "tomorrow",
], 3.0)

# Game lookup
EVIDENCE_RULES += _rules(INTENT_GAME_LOOKUP, [
    "game details",
    "game information",
    "box score",
    "boxscore",
    "final score",
    "game result",
    "score of the game",
    "who played",
    "game recap",
], 8.0)
EVIDENCE_RULES += _token_rules(INTENT_GAME_LOOKUP, ["boxscore", "score"], 2.5)

# Comparison
EVIDENCE_RULES += _rules(INTENT_COMPARE_PLAYERS, [
    "compare players",
    "player comparison",
    "which player is better",
    "who is the better player",
    "who should i pick",
    "rank these players",
    "head to head players",
    "side by side players",
], 9.5)
EVIDENCE_RULES += _rules(INTENT_COMPARE_TEAMS, [
    "compare teams",
    "team comparison",
    "which team is better",
    "stronger team",
    "rank these teams",
    "head to head teams",
    "side by side teams",
], 9.5)
EVIDENCE_RULES += _token_rules(INTENT_COMPARE_PLAYERS, ["compare", "versus", "vs"], 2.0)
EVIDENCE_RULES += _token_rules(INTENT_COMPARE_TEAMS, ["compare", "versus", "vs"], 2.0)

# Predictions
EVIDENCE_RULES += _rules(INTENT_PLAYER_PROBABILITY, [
    "player probability",
    "player prediction",
    "player prop",
    "what are his chances",
    "what are her chances",
    "will he",
    "will she",
    "is he likely",
    "is she likely",
    "project this player",
    "predict this player",
    "chance he",
    "chance she",
], 8.5)
EVIDENCE_RULES += _rules(INTENT_TEAM_PROBABILITY, [
    "team probability",
    "team prediction",
    "chance they win",
    "chances they win",
    "will they win",
    "team win probability",
    "which team will win",
], 8.5)
EVIDENCE_RULES += _rules(INTENT_GAME_PROBABILITY, [
    "game probability",
    "game prediction",
    "predict the game",
    "who wins",
    "who will win",
    "game winner",
    "moneyline",
    "win probability",
], 9.0)
EVIDENCE_RULES += _rules(INTENT_GENERAL_PROBABILITY, [
    "probability",
    "what are the chances",
    "what is the chance",
    "how likely",
    "odds",
    "projection",
    "prediction",
    "forecast",
    "predict",
    "project",
    "best bet",
    "over under",
    "over/under",
], 5.5)
EVIDENCE_RULES += _token_rules(INTENT_GENERAL_PROBABILITY, [
    "probability",
    "chance",
    "chances",
    "odds",
    "predict",
    "prediction",
    "project",
    "projection",
    "forecast",
], 2.5)

# Matchup
EVIDENCE_RULES += _rules(INTENT_MATCHUP_ANALYSIS, [
    "matchup analysis",
    "batter vs pitcher",
    "batter versus pitcher",
    "pitcher matchup",
    "batter matchup",
    "matchup against",
    "how does he match up",
    "how do they match up",
    "platoon advantage",
    "handedness split",
    "park factor",
], 9.0)
EVIDENCE_RULES += _token_rules(INTENT_MATCHUP_ANALYSIS, [
    "matchup",
    "against",
    "facing",
    "platoon",
    "lefty",
    "righty",
], 2.2)

# Stats
EVIDENCE_RULES += _rules(INTENT_PLAYER_STAT_REQUEST, [
    "player stats",
    "his stats",
    "her stats",
    "season stats",
    "career stats",
    "game log",
    "recent games",
    "last five games",
    "last 5 games",
    "last ten games",
    "last 10 games",
], 7.5)
EVIDENCE_RULES += _rules(INTENT_TEAM_STAT_REQUEST, [
    "team stats",
    "team statistics",
    "offensive stats",
    "pitching stats",
    "bullpen stats",
    "team batting",
    "team pitching",
], 7.5)
EVIDENCE_RULES += _rules(INTENT_STAT_REQUEST, [
    "stats",
    "statistics",
    "stat line",
    "batting average",
    "on base percentage",
    "slugging percentage",
    "home runs",
    "strikeouts",
    "walk rate",
    "strikeout rate",
    "barrel rate",
    "hard hit rate",
    "exit velocity",
    "launch angle",
    "expected woba",
    "expected batting average",
    "total bases",
], 5.0)
EVIDENCE_RULES += _token_rules(INTENT_STAT_REQUEST, [
    "stats",
    "statistics",
    "avg",
    "obp",
    "slg",
    "ops",
    "woba",
    "xwoba",
    "xba",
    "xslg",
    "war",
    "era",
    "whip",
    "fip",
    "xfip",
    "hr",
    "rbi",
    "hits",
    "doubles",
    "triples",
    "strikeouts",
], 2.4)

# Explain model
EVIDENCE_RULES += _rules(INTENT_EXPLAIN_MODEL, [
    "explain the model",
    "how does the model work",
    "why that prediction",
    "why this prediction",
    "why that probability",
    "how did you calculate",
    "how did you determine",
    "what factors",
    "which factors",
    "model explanation",
    "confidence score",
    "why confidence",
], 9.0)
EVIDENCE_RULES += _token_rules(INTENT_EXPLAIN_MODEL, ["why", "explain", "reasoning"], 2.0)

# Player and team info
EVIDENCE_RULES += _rules(INTENT_PLAYER_INFO, [
    "player profile",
    "tell me about this player",
    "tell me about him",
    "tell me about her",
    "who is this player",
    "scouting report",
    "player overview",
    "player information",
    "what kind of player",
], 7.5)
EVIDENCE_RULES += _rules(INTENT_TEAM_INFO, [
    "team profile",
    "tell me about this team",
    "team overview",
    "team information",
    "club information",
    "franchise information",
    "team strength",
    "team weakness",
], 7.5)
EVIDENCE_RULES += _token_rules(INTENT_PLAYER_INFO, ["player", "hitter", "pitcher", "rookie", "prospect"], 1.5)
EVIDENCE_RULES += _token_rules(INTENT_TEAM_INFO, ["team", "club", "franchise", "division", "league"], 1.5)


# ============================================================
# SECTION 11 - NEGATIVE EVIDENCE
# PURPOSE:
# Reduce common false positives without blindly blocking an
# intent. Negative evidence is subtracted from positive evidence.
# ============================================================

EVIDENCE_RULES += _negative_rules(INTENT_PLAYER_INFO, [
    "player stats",
    "player probability",
    "player prediction",
    "compare players",
    "list players",
], 4.5)

EVIDENCE_RULES += _negative_rules(INTENT_TEAM_INFO, [
    "team stats",
    "team probability",
    "team prediction",
    "compare teams",
    "list teams",
    "team schedule",
], 4.5)

EVIDENCE_RULES += _negative_rules(INTENT_STAT_REQUEST, [
    "predict",
    "prediction",
    "probability",
    "what are the chances",
    "will he",
    "will they",
], 2.5)

EVIDENCE_RULES += _negative_rules(INTENT_GENERAL_PROBABILITY, [
    "past result",
    "final score",
    "box score",
    "career stats",
    "season stats",
], 3.5)

EVIDENCE_RULES += _negative_rules(INTENT_SCHEDULE_LOOKUP, [
    "final score",
    "box score",
    "game result",
], 4.0)

EVIDENCE_RULES += _negative_rules(INTENT_GAME_LOOKUP, [
    "next game",
    "upcoming games",
    "schedule",
], 3.0)

EVIDENCE_RULES += _negative_rules(INTENT_COMPARE_PLAYERS, [
    "compare teams",
    "which team is better",
], 6.0)

EVIDENCE_RULES += _negative_rules(INTENT_COMPARE_TEAMS, [
    "compare players",
    "which player is better",
], 6.0)


# ============================================================
# SECTION 12 - REGEX EVIDENCE RULES
# ============================================================

REGEX_RULES: list[EvidenceRule] = [
    EvidenceRule(
        intent=INTENT_COMPARE_PLAYERS,
        pattern=r"\b(?:who|which)\s+(?:player\s+)?is\s+better\b",
        weight=8.0,
        mode=MatchMode.REGEX,
        label="compare_players:better_pattern",
    ),
    EvidenceRule(
        intent=INTENT_COMPARE_TEAMS,
        pattern=r"\b(?:who|which)\s+(?:team\s+)?(?:wins|will win|is better)\b",
        weight=8.5,
        mode=MatchMode.REGEX,
        label="compare_teams:winner_pattern",
    ),
    EvidenceRule(
        intent=INTENT_PLAYER_PROBABILITY,
        pattern=r"\b(?:will|can|does|is)\s+(?:he|she|the player)\b",
        weight=6.5,
        mode=MatchMode.REGEX,
        label="player_probability:pronoun_future_pattern",
    ),
    EvidenceRule(
        intent=INTENT_TEAM_PROBABILITY,
        pattern=r"\b(?:will|can|do|does)\s+(?:they|the team)\b",
        weight=6.0,
        mode=MatchMode.REGEX,
        label="team_probability:team_future_pattern",
    ),
    EvidenceRule(
        intent=INTENT_SCHEDULE_LOOKUP,
        pattern=r"\bwhen\s+(?:do|does|is|are)\b.*\b(?:play|game)\b",
        weight=8.0,
        mode=MatchMode.REGEX,
        label="schedule_lookup:when_play_pattern",
    ),
    EvidenceRule(
        intent=INTENT_STAT_REQUEST,
        pattern=r"\b(?:last|past)\s+\d+\s+(?:games|starts|appearances)\b",
        weight=7.0,
        mode=MatchMode.REGEX,
        label="stat_request:rolling_window_pattern",
    ),
    EvidenceRule(
        intent=INTENT_MATCHUP_ANALYSIS,
        pattern=r"\b.+\s+(?:vs|versus|against|facing)\s+.+\b",
        weight=5.5,
        mode=MatchMode.REGEX,
        label="matchup_analysis:versus_pattern",
    ),
]

EVIDENCE_RULES.extend(REGEX_RULES)


# ============================================================
# SECTION 13 - RULE MATCHING
# ============================================================

def _match_rule(
    rule: EvidenceRule,
    normalized_message: str,
    tokens: Sequence[str],
    token_set: set[str],
) -> EvidenceMatch | None:
    pattern = rule.pattern if rule.case_sensitive else normalize_intent_text(rule.pattern)

    if rule.mode == MatchMode.PHRASE:
        regex = rf"(?<![a-z0-9]){re.escape(pattern)}(?![a-z0-9])"
        match = re.search(regex, normalized_message)
        if not match:
            return None
        return EvidenceMatch(
            intent=rule.intent,
            rule_label=rule.label or rule.pattern,
            pattern=rule.pattern,
            weight=rule.weight,
            kind=EvidenceKind.NEGATIVE if rule.negative else EvidenceKind.EXACT_PHRASE,
            negative=rule.negative,
            start=match.start(),
            end=match.end(),
            matched_text=match.group(0),
        )

    if rule.mode == MatchMode.TOKEN:
        if pattern not in token_set:
            return None
        return EvidenceMatch(
            intent=rule.intent,
            rule_label=rule.label or rule.pattern,
            pattern=rule.pattern,
            weight=rule.weight,
            kind=EvidenceKind.NEGATIVE if rule.negative else EvidenceKind.TOKEN,
            negative=rule.negative,
            matched_text=pattern,
        )

    if rule.mode == MatchMode.TOKEN_SET:
        expected = set(tokenize_intent_text(pattern))
        if not expected or not expected.issubset(token_set):
            return None
        return EvidenceMatch(
            intent=rule.intent,
            rule_label=rule.label or rule.pattern,
            pattern=rule.pattern,
            weight=rule.weight,
            kind=EvidenceKind.NEGATIVE if rule.negative else EvidenceKind.TOKEN_SET,
            negative=rule.negative,
            matched_text=" ".join(sorted(expected)),
        )

    if rule.mode == MatchMode.REGEX:
        flags = 0 if rule.case_sensitive else re.IGNORECASE
        match = re.search(rule.pattern, normalized_message, flags)
        if not match:
            return None
        return EvidenceMatch(
            intent=rule.intent,
            rule_label=rule.label or rule.pattern,
            pattern=rule.pattern,
            weight=rule.weight,
            kind=EvidenceKind.NEGATIVE if rule.negative else EvidenceKind.REGEX,
            negative=rule.negative,
            start=match.start(),
            end=match.end(),
            matched_text=match.group(0),
        )

    if rule.mode == MatchMode.PREFIX:
        if not normalized_message.startswith(pattern):
            return None
        return EvidenceMatch(
            intent=rule.intent,
            rule_label=rule.label or rule.pattern,
            pattern=rule.pattern,
            weight=rule.weight,
            kind=EvidenceKind.NEGATIVE if rule.negative else EvidenceKind.QUESTION_TYPE,
            negative=rule.negative,
            start=0,
            end=len(pattern),
            matched_text=pattern,
        )

    return None


def collect_rule_evidence(message: str) -> list[EvidenceMatch]:
    normalized = normalize_intent_text(message)
    tokens = tokenize_intent_text(message)
    token_set = set(tokens)

    evidence: list[EvidenceMatch] = []

    for rule in EVIDENCE_RULES:
        match = _match_rule(
            rule=rule,
            normalized_message=normalized,
            tokens=tokens,
            token_set=token_set,
        )
        if match is not None:
            evidence.append(match)

    return evidence


# ============================================================
# SECTION 14 - CONTEXT AND ENTITY EVIDENCE
# ============================================================

def build_entity_evidence(context: IntentContext) -> list[EvidenceMatch]:
    evidence: list[EvidenceMatch] = []

    player_count = len(_deduplicate_entities(context.detected_players))
    team_count = len(_deduplicate_entities(context.detected_teams))

    if context.detected_player:
        evidence.append(EvidenceMatch(
            intent=INTENT_PLAYER_INFO,
            rule_label="entity:single_player",
            pattern=context.detected_player,
            weight=2.0,
            kind=EvidenceKind.ENTITY,
            negative=False,
            matched_text=context.detected_player,
        ))

    if context.detected_team:
        evidence.append(EvidenceMatch(
            intent=INTENT_TEAM_INFO,
            rule_label="entity:single_team",
            pattern=context.detected_team,
            weight=2.0,
            kind=EvidenceKind.ENTITY,
            negative=False,
            matched_text=context.detected_team,
        ))

    if player_count >= 2:
        evidence.append(EvidenceMatch(
            intent=INTENT_COMPARE_PLAYERS,
            rule_label="entity:multiple_players",
            pattern="multiple_players",
            weight=8.5,
            kind=EvidenceKind.ENTITY,
            negative=False,
            matched_text=str(player_count),
        ))

    if team_count >= 2:
        evidence.append(EvidenceMatch(
            intent=INTENT_COMPARE_TEAMS,
            rule_label="entity:multiple_teams",
            pattern="multiple_teams",
            weight=8.5,
            kind=EvidenceKind.ENTITY,
            negative=False,
            matched_text=str(team_count),
        ))

    if context.detected_player and context.detected_outcome:
        evidence.append(EvidenceMatch(
            intent=INTENT_PLAYER_PROBABILITY,
            rule_label="entity:player_plus_outcome",
            pattern="player_plus_outcome",
            weight=9.0,
            kind=EvidenceKind.ENTITY,
            negative=False,
            matched_text=f"{context.detected_player}:{context.detected_outcome}",
        ))

    if context.detected_team and context.detected_outcome:
        evidence.append(EvidenceMatch(
            intent=INTENT_TEAM_PROBABILITY,
            rule_label="entity:team_plus_outcome",
            pattern="team_plus_outcome",
            weight=7.5,
            kind=EvidenceKind.ENTITY,
            negative=False,
            matched_text=f"{context.detected_team}:{context.detected_outcome}",
        ))

    if context.previous_intent:
        evidence.append(EvidenceMatch(
            intent=context.previous_intent,
            rule_label="context:previous_intent",
            pattern=context.previous_intent,
            weight=1.2,
            kind=EvidenceKind.CONTEXT,
            negative=False,
            matched_text=context.previous_intent,
        ))

    return evidence


def _deduplicate_entities(values: Sequence[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for value in values or []:
        normalized = normalize_intent_text(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(value)

    return result


# ============================================================
# SECTION 15 - QUESTION TYPE EVIDENCE
# ============================================================

def build_question_type_evidence(
    question_type: str,
) -> list[EvidenceMatch]:
    evidence: list[EvidenceMatch] = []

    mapping: dict[str, list[tuple[str, float]]] = {
        "why_question": [
            (INTENT_EXPLAIN_MODEL, 3.0),
        ],
        "explanation_command": [
            (INTENT_EXPLAIN_MODEL, 4.0),
        ],
        "comparison_command": [
            (INTENT_COMPARE_PLAYERS, 2.0),
            (INTENT_COMPARE_TEAMS, 2.0),
        ],
        "prediction_command": [
            (INTENT_GENERAL_PROBABILITY, 4.0),
        ],
        "probability_question": [
            (INTENT_GENERAL_PROBABILITY, 3.0),
        ],
        "when_question": [
            (INTENT_SCHEDULE_LOOKUP, 4.0),
        ],
        "quantity_question": [
            (INTENT_STAT_REQUEST, 2.0),
        ],
    }

    for intent, weight in mapping.get(question_type, []):
        evidence.append(EvidenceMatch(
            intent=intent,
            rule_label=f"question_type:{question_type}",
            pattern=question_type,
            weight=weight,
            kind=EvidenceKind.QUESTION_TYPE,
            negative=False,
            matched_text=question_type,
        ))

    return evidence


# ============================================================
# SECTION 16 - SCORE AGGREGATION
# ============================================================

def score_evidence(
    evidence: Sequence[EvidenceMatch],
) -> dict[str, IntentCandidate]:
    candidates: dict[str, IntentCandidate] = {}

    for item in evidence:
        candidate = candidates.setdefault(
            item.intent,
            IntentCandidate(intent=item.intent),
        )
        candidate.evidence.append(item)

        if item.negative:
            candidate.negative_score += abs(item.weight)
        else:
            candidate.positive_score += max(0.0, item.weight)

    for candidate in candidates.values():
        candidate.raw_score = candidate.net_score

    return candidates


def _score_saturation(score: float) -> float:
    if score <= 0:
        return 0.0
    return 1.0 - math.exp(-score / 10.0)


def normalize_candidate_scores(
    candidates: Mapping[str, IntentCandidate],
) -> list[IntentCandidate]:
    normalized_candidates = list(candidates.values())

    for candidate in normalized_candidates:
        candidate.normalized_score = _score_saturation(candidate.net_score)

    positive = [
        max(candidate.normalized_score, 0.0)
        for candidate in normalized_candidates
    ]
    total = sum(positive)

    if total > 0:
        for candidate in normalized_candidates:
            candidate.probability = max(candidate.normalized_score, 0.0) / total
    else:
        for candidate in normalized_candidates:
            candidate.probability = 0.0

    normalized_candidates.sort(
        key=lambda candidate: (
            -candidate.net_score,
            INTENT_PRECEDENCE_INDEX.get(candidate.intent, 9999),
        ),
    )

    for index, candidate in enumerate(normalized_candidates, start=1):
        candidate.rank = index

    return normalized_candidates


# ============================================================
# SECTION 17 - EXPLICIT CONFLICT RESOLUTION
# ============================================================

def _has_intent(candidates: Mapping[str, IntentCandidate], intent: str) -> bool:
    candidate = candidates.get(intent)
    return bool(candidate and candidate.net_score > 0)


def _candidate_score(candidates: Mapping[str, IntentCandidate], intent: str) -> float:
    candidate = candidates.get(intent)
    return candidate.net_score if candidate else 0.0


def apply_explicit_precedence(
    candidates: dict[str, IntentCandidate],
    context: IntentContext,
) -> tuple[str, bool, list[str]]:
    """
    Resolve known collision classes in a deterministic order.
    """
    reasons: list[str] = []

    # System commands are explicit and should not be overridden by
    # generic baseball nouns.
    for intent in (
        INTENT_HELP,
        INTENT_WAREHOUSE_STATUS,
        INTENT_DATABASE_STATUS,
        INTENT_MODEL_STATUS,
        INTENT_DATA_SOURCE_STATUS,
    ):
        if _candidate_score(candidates, intent) >= 6.0:
            reasons.append(f"explicit_system_precedence:{intent}")
            return intent, True, reasons

    # Multiple detected entities are strong comparison evidence.
    if len(_deduplicate_entities(context.detected_players)) >= 2:
        reasons.append("entity_precedence:multiple_players")
        return INTENT_COMPARE_PLAYERS, True, reasons

    if len(_deduplicate_entities(context.detected_teams)) >= 2:
        reasons.append("entity_precedence:multiple_teams")
        return INTENT_COMPARE_TEAMS, True, reasons

    # Explain-model requests override prediction/stat nouns when the
    # user explicitly asks why or how a prior result was calculated.
    if _candidate_score(candidates, INTENT_EXPLAIN_MODEL) >= 5.0:
        reasons.append("explanation_precedence")
        return INTENT_EXPLAIN_MODEL, True, reasons

    # Specific prediction intents override generic probability.
    for intent in (
        INTENT_PLAYER_PROBABILITY,
        INTENT_TEAM_PROBABILITY,
        INTENT_GAME_PROBABILITY,
    ):
        if _candidate_score(candidates, intent) >= 6.0:
            reasons.append(f"specific_prediction_precedence:{intent}")
            return intent, True, reasons

    # Schedule and completed-game lookup must remain separate.
    if _candidate_score(candidates, INTENT_SCHEDULE_LOOKUP) >= 6.0:
        reasons.append("schedule_precedence")
        return INTENT_SCHEDULE_LOOKUP, True, reasons

    if _candidate_score(candidates, INTENT_GAME_LOOKUP) >= 6.0:
        reasons.append("game_lookup_precedence")
        return INTENT_GAME_LOOKUP, True, reasons

    # Roster is more specific than team/player list.
    if _candidate_score(candidates, INTENT_ROSTER_LOOKUP) >= 6.0:
        reasons.append("roster_precedence")
        return INTENT_ROSTER_LOOKUP, True, reasons

    # Entity-aware stat specialization.
    stat_score = max(
        _candidate_score(candidates, INTENT_STAT_REQUEST),
        _candidate_score(candidates, INTENT_PLAYER_STAT_REQUEST),
        _candidate_score(candidates, INTENT_TEAM_STAT_REQUEST),
    )
    if stat_score >= 4.0:
        if context.detected_player:
            reasons.append("entity_precedence:player_stat")
            return INTENT_PLAYER_STAT_REQUEST, True, reasons
        if context.detected_team:
            reasons.append("entity_precedence:team_stat")
            return INTENT_TEAM_STAT_REQUEST, True, reasons

    # Generic highest-score fallback with stable precedence.
    ranked = normalize_candidate_scores(candidates)
    if ranked and ranked[0].net_score > 0:
        reasons.append("weighted_score_selection")
        return ranked[0].intent, False, reasons

    reasons.append("fallback_intent")
    return INTENT_GENERAL_BASEBALL, False, reasons


# ============================================================
# SECTION 18 - ENTITY-AWARE FINAL UPGRADE
# ============================================================

def upgrade_intent_with_entities(
    base_intent: str,
    detected_player: str | None = None,
    detected_team: str | None = None,
    detected_outcome: str | None = None,
    detected_players: list[str] | None = None,
    detected_teams: list[str] | None = None,
) -> str:
    """
    Backward-compatible entity upgrade function.
    """
    player_count = len(_deduplicate_entities(detected_players))
    team_count = len(_deduplicate_entities(detected_teams))

    if base_intent in SYSTEM_INTENTS:
        return base_intent

    if player_count >= 2:
        return INTENT_COMPARE_PLAYERS

    if team_count >= 2:
        return INTENT_COMPARE_TEAMS

    if detected_player and detected_outcome:
        return INTENT_PLAYER_PROBABILITY

    if detected_team and detected_outcome:
        return INTENT_TEAM_PROBABILITY

    if base_intent == INTENT_STAT_REQUEST:
        if detected_player:
            return INTENT_PLAYER_STAT_REQUEST
        if detected_team:
            return INTENT_TEAM_STAT_REQUEST

    if base_intent == INTENT_GENERAL_PROBABILITY:
        if detected_player:
            return INTENT_PLAYER_PROBABILITY
        if detected_team:
            return INTENT_TEAM_PROBABILITY

    if detected_player and base_intent == INTENT_GENERAL_BASEBALL:
        return INTENT_PLAYER_INFO

    if detected_team and base_intent == INTENT_GENERAL_BASEBALL:
        return INTENT_TEAM_INFO

    return base_intent


# ============================================================
# SECTION 19 - CONFIDENCE AND AMBIGUITY
# ============================================================

def calculate_decision_confidence(
    selected_intent: str,
    ranked_candidates: Sequence[IntentCandidate],
    precedence_applied: bool,
) -> tuple[float, float, bool]:
    selected = next(
        (candidate for candidate in ranked_candidates if candidate.intent == selected_intent),
        None,
    )

    if selected is None or selected.net_score <= 0:
        return 0.30, 0.0, True

    sorted_positive = [
        candidate
        for candidate in ranked_candidates
        if candidate.net_score > 0
    ]

    top_score = selected.normalized_score
    second_score = 0.0

    for candidate in sorted_positive:
        if candidate.intent != selected_intent:
            second_score = candidate.normalized_score
            break

    margin = max(0.0, top_score - second_score)
    evidence_count = len([
        item for item in selected.evidence
        if not item.negative
    ])
    evidence_bonus = min(0.14, evidence_count * 0.025)
    precedence_bonus = 0.05 if precedence_applied else 0.0

    confidence = (
        0.30
        + (top_score * 0.48)
        + (margin * 0.18)
        + evidence_bonus
        + precedence_bonus
    )

    confidence = max(0.0, min(confidence, 0.99))
    ambiguous = margin < DEFAULT_AMBIGUITY_MARGIN and len(sorted_positive) > 1

    return confidence, margin, ambiguous


def calculate_intent_confidence(
    message: str,
    final_intent: str,
    detected_player: str | None = None,
    detected_team: str | None = None,
    detected_outcome: str | None = None,
) -> int:
    """
    Backward-compatible integer confidence function.
    """
    decision = detect_intent(
        message=message,
        detected_player=detected_player,
        detected_team=detected_team,
        detected_outcome=detected_outcome,
    )

    if decision.final_intent == final_intent:
        return decision.confidence_percent

    candidate = next(
        (
            candidate
            for candidate in decision.candidates
            if candidate.intent == final_intent
        ),
        None,
    )

    if candidate is None:
        return 0

    return int(round(candidate.normalized_score * 100))


# ============================================================
# SECTION 20 - ROUTING GROUP CLASSIFICATION
# ============================================================

def classify_routing_group(intent: str) -> str:
    if intent in LOOKUP_INTENTS:
        return "lookup"

    if intent in STAT_INTENTS:
        return "statistics"

    if intent in PREDICTION_INTENTS:
        return "prediction"

    if intent in COMPARISON_INTENTS:
        return "comparison"

    if intent == INTENT_MATCHUP_ANALYSIS:
        return "matchup_analysis"

    if intent in SYSTEM_INTENTS:
        return "system"

    return "general"


# ============================================================
# SECTION 21 - PRIMARY DETECTION PIPELINE
# ============================================================

def detect_intent(
    message: str,
    detected_player: str | None = None,
    detected_team: str | None = None,
    detected_outcome: str | None = None,
    detected_players: list[str] | None = None,
    detected_teams: list[str] | None = None,
    previous_intent: str | None = None,
    conversation_topic: str | None = None,
) -> IntentDecision:
    context = IntentContext(
        detected_player=detected_player,
        detected_team=detected_team,
        detected_outcome=detected_outcome,
        detected_players=_deduplicate_entities(detected_players),
        detected_teams=_deduplicate_entities(detected_teams),
        previous_intent=previous_intent,
        conversation_topic=conversation_topic,
    )

    normalized_message = normalize_intent_text(message)
    tokens = tokenize_intent_text(message)
    question_type = detect_question_type(message)

    evidence = collect_rule_evidence(message)
    evidence.extend(build_question_type_evidence(question_type))
    evidence.extend(build_entity_evidence(context))

    candidate_map = score_evidence(evidence)

    selected_intent, precedence_applied, precedence_reasons = apply_explicit_precedence(
        candidates=candidate_map,
        context=context,
    )

    base_intent = selected_intent

    final_intent = upgrade_intent_with_entities(
        base_intent=base_intent,
        detected_player=detected_player,
        detected_team=detected_team,
        detected_outcome=detected_outcome,
        detected_players=detected_players,
        detected_teams=detected_teams,
    )

    if final_intent not in candidate_map:
        candidate_map[final_intent] = IntentCandidate(
            intent=final_intent,
            positive_score=0.5,
            raw_score=0.5,
            evidence=[
                EvidenceMatch(
                    intent=final_intent,
                    rule_label="entity_upgrade",
                    pattern=base_intent,
                    weight=0.5,
                    kind=EvidenceKind.ENTITY,
                    negative=False,
                    matched_text=final_intent,
                )
            ],
        )

    ranked_candidates = normalize_candidate_scores(candidate_map)

    confidence, ambiguity_margin, ambiguous = calculate_decision_confidence(
        selected_intent=final_intent,
        ranked_candidates=ranked_candidates,
        precedence_applied=precedence_applied,
    )

    if final_intent == INTENT_GENERAL_BASEBALL and not evidence:
        confidence = 0.30
        ambiguous = True

    return IntentDecision(
        message=message,
        normalized_message=normalized_message,
        tokens=tokens,
        question_type=question_type,
        base_intent=base_intent,
        final_intent=final_intent,
        confidence=confidence,
        confidence_percent=int(round(confidence * 100)),
        ambiguous=ambiguous,
        ambiguity_margin=ambiguity_margin,
        candidates=ranked_candidates[:DEFAULT_MAX_CANDIDATES],
        context=context,
        engine_version=INTENT_DETECTION_VERSION,
        schema_version=INTENT_DETECTION_SCHEMA_VERSION,
        routing_group=classify_routing_group(final_intent),
        precedence_applied=precedence_applied,
        diagnostics={
            "precedence_reasons": precedence_reasons,
            "evidence_count": len(evidence),
            "positive_evidence_count": len([item for item in evidence if not item.negative]),
            "negative_evidence_count": len([item for item in evidence if item.negative]),
            "fallback_used": final_intent == INTENT_GENERAL_BASEBALL,
        },
    )


# ============================================================
# SECTION 22 - BACKWARD-COMPATIBLE PUBLIC FUNCTIONS
# ============================================================

def score_intent_match(
    message: str,
    phrases: Sequence[str],
) -> int:
    normalized = normalize_intent_text(message)
    total = 0

    for phrase in phrases:
        normalized_phrase = normalize_intent_text(phrase)
        if _whole_phrase_match(normalized, normalized_phrase):
            total += max(1, len(tokenize_intent_text(normalized_phrase)))

    return total


def score_all_intents(message: str) -> dict[str, int]:
    decision = detect_intent(message)

    return {
        candidate.intent: int(round(max(candidate.net_score, 0.0) * 10))
        for candidate in decision.candidates
    }


def detect_primary_intent(message: str) -> str:
    return detect_intent(message).final_intent


def detect_possible_intents(message: str) -> list[str]:
    return [
        candidate.intent
        for candidate in detect_intent(message).candidates
        if candidate.net_score > 0
    ]


def build_intent_report(
    message: str,
    detected_player: str | None = None,
    detected_team: str | None = None,
    detected_outcome: str | None = None,
    detected_players: list[str] | None = None,
    detected_teams: list[str] | None = None,
    previous_intent: str | None = None,
    conversation_topic: str | None = None,
) -> dict[str, Any]:
    decision = detect_intent(
        message=message,
        detected_player=detected_player,
        detected_team=detected_team,
        detected_outcome=detected_outcome,
        detected_players=detected_players,
        detected_teams=detected_teams,
        previous_intent=previous_intent,
        conversation_topic=conversation_topic,
    )

    report = asdict(decision)

    report["possible_intents"] = [
        candidate["intent"]
        for candidate in report["candidates"]
        if candidate["raw_score"] > 0
    ]

    report["intent_scores"] = {
        candidate["intent"]: round(candidate["raw_score"], 4)
        for candidate in report["candidates"]
    }

    report["confidence"] = decision.confidence_percent
    report["confidence_probability"] = round(decision.confidence, 6)

    report["detected_player"] = detected_player
    report["detected_team"] = detected_team
    report["detected_outcome"] = detected_outcome
    report["detected_players"] = detected_players or []
    report["detected_teams"] = detected_teams or []

    return report


# ============================================================
# SECTION 23 - INTENT REGISTRY AND CAPABILITY HELPERS
# ============================================================

ALL_SUPPORTED_INTENTS = tuple(INTENT_PRECEDENCE)

INTENT_DESCRIPTIONS = {
    INTENT_LIST_TEAMS: "List all available MLB teams.",
    INTENT_LIST_PLAYERS: "List available MLB players.",
    INTENT_TEAM_INFO: "Retrieve general team information.",
    INTENT_PLAYER_INFO: "Retrieve general player information.",
    INTENT_ROSTER_LOOKUP: "Retrieve roster membership.",
    INTENT_SCHEDULE_LOOKUP: "Retrieve future or current schedule information.",
    INTENT_GAME_LOOKUP: "Retrieve a completed or specific game record.",
    INTENT_PLAYER_STAT_REQUEST: "Retrieve player statistics.",
    INTENT_TEAM_STAT_REQUEST: "Retrieve team statistics.",
    INTENT_STAT_REQUEST: "Retrieve general baseball statistics.",
    INTENT_PLAYER_PROBABILITY: "Predict a player outcome.",
    INTENT_TEAM_PROBABILITY: "Predict a team outcome.",
    INTENT_GAME_PROBABILITY: "Predict a game outcome.",
    INTENT_GENERAL_PROBABILITY: "Handle an unspecified probability request.",
    INTENT_COMPARE_PLAYERS: "Compare multiple players.",
    INTENT_COMPARE_TEAMS: "Compare multiple teams.",
    INTENT_MATCHUP_ANALYSIS: "Analyze matchup context.",
    INTENT_EXPLAIN_MODEL: "Explain a model result or confidence.",
    INTENT_HELP: "Describe chatbot capabilities.",
    INTENT_WAREHOUSE_STATUS: "Inspect warehouse readiness.",
    INTENT_DATABASE_STATUS: "Inspect database readiness.",
    INTENT_MODEL_STATUS: "Inspect model readiness.",
    INTENT_DATA_SOURCE_STATUS: "Inspect upstream data source readiness.",
    INTENT_GENERAL_BASEBALL: "Fallback for general baseball language.",
}


def get_supported_intents() -> list[str]:
    return list(ALL_SUPPORTED_INTENTS)


def get_intent_description(intent: str) -> str:
    return INTENT_DESCRIPTIONS.get(intent, "Unknown intent.")


def get_intent_group(intent: str) -> str:
    return classify_routing_group(intent)


def is_prediction_intent(intent: str) -> bool:
    return intent in PREDICTION_INTENTS


def is_lookup_intent(intent: str) -> bool:
    return intent in LOOKUP_INTENTS


def is_stat_intent(intent: str) -> bool:
    return intent in STAT_INTENTS


def is_system_intent(intent: str) -> bool:
    return intent in SYSTEM_INTENTS


# ============================================================
# SECTION 24 - MACHINE-LEARNING FEATURE EXPORT
# PURPOSE:
# Export deterministic lexical features that can later be used
# as input to supervised classifiers, calibration models, or an
# ensemble combining rules, embeddings, and transformers.
# ============================================================

def build_intent_feature_vector(
    message: str,
    *,
    detected_player: str | None = None,
    detected_team: str | None = None,
    detected_outcome: str | None = None,
    detected_players: list[str] | None = None,
    detected_teams: list[str] | None = None,
) -> dict[str, float]:
    decision = detect_intent(
        message=message,
        detected_player=detected_player,
        detected_team=detected_team,
        detected_outcome=detected_outcome,
        detected_players=detected_players,
        detected_teams=detected_teams,
    )

    features: dict[str, float] = {
        "message_length": float(len(decision.normalized_message)),
        "token_count": float(len(decision.tokens)),
        "unique_token_count": float(len(set(decision.tokens))),
        "contains_question_mark": 1.0 if "?" in message else 0.0,
        "has_player_entity": 1.0 if detected_player else 0.0,
        "has_team_entity": 1.0 if detected_team else 0.0,
        "has_outcome_entity": 1.0 if detected_outcome else 0.0,
        "detected_player_count": float(len(_deduplicate_entities(detected_players))),
        "detected_team_count": float(len(_deduplicate_entities(detected_teams))),
        "decision_confidence": decision.confidence,
        "decision_ambiguity_margin": decision.ambiguity_margin,
    }

    for intent in ALL_SUPPORTED_INTENTS:
        candidate = next(
            (
                candidate
                for candidate in decision.candidates
                if candidate.intent == intent
            ),
            None,
        )
        features[f"intent_score__{intent}"] = (
            float(candidate.net_score)
            if candidate
            else 0.0
        )

    return features


# ============================================================
# SECTION 25 - TRAINING LABEL NORMALIZATION
# ============================================================

LEGACY_INTENT_ALIASES = {
    "player_stats": INTENT_PLAYER_STAT_REQUEST,
    "team_stats": INTENT_TEAM_STAT_REQUEST,
    "stats": INTENT_STAT_REQUEST,
    "schedule": INTENT_SCHEDULE_LOOKUP,
    "game": INTENT_GAME_LOOKUP,
    "prediction": INTENT_GENERAL_PROBABILITY,
    "player_prediction": INTENT_PLAYER_PROBABILITY,
    "team_prediction": INTENT_TEAM_PROBABILITY,
    "game_prediction": INTENT_GAME_PROBABILITY,
}


def normalize_intent_label(intent: str | None) -> str:
    normalized = normalize_intent_text(intent).replace(" ", "_")

    if not normalized:
        return INTENT_GENERAL_BASEBALL

    return LEGACY_INTENT_ALIASES.get(normalized, normalized)


# ============================================================
# SECTION 26 - VALIDATION CASES
# ============================================================

VALIDATION_CASES: list[dict[str, Any]] = [
    {
        "message": "List all MLB teams",
        "expected": INTENT_LIST_TEAMS,
    },
    {
        "message": "Show me the Yankees active roster",
        "expected": INTENT_ROSTER_LOOKUP,
        "detected_team": "New York Yankees",
    },
    {
        "message": "When do the Mets play next?",
        "expected": INTENT_SCHEDULE_LOOKUP,
        "detected_team": "New York Mets",
    },
    {
        "message": "What was the final score of last night's Yankees game?",
        "expected": INTENT_GAME_LOOKUP,
        "detected_team": "New York Yankees",
    },
    {
        "message": "What are Aaron Judge's home run stats?",
        "expected": INTENT_PLAYER_STAT_REQUEST,
        "detected_player": "Aaron Judge",
    },
    {
        "message": "What is the Yankees bullpen ERA?",
        "expected": INTENT_TEAM_STAT_REQUEST,
        "detected_team": "New York Yankees",
    },
    {
        "message": "What are the chances Aaron Judge hits a home run?",
        "expected": INTENT_PLAYER_PROBABILITY,
        "detected_player": "Aaron Judge",
        "detected_outcome": "home_run",
    },
    {
        "message": "Will the Yankees win tonight?",
        "expected": INTENT_TEAM_PROBABILITY,
        "detected_team": "New York Yankees",
        "detected_outcome": "team_win",
    },
    {
        "message": "Who will win the Yankees versus Red Sox game?",
        "expected": INTENT_COMPARE_TEAMS,
        "detected_teams": ["New York Yankees", "Boston Red Sox"],
    },
    {
        "message": "Compare Aaron Judge and Juan Soto",
        "expected": INTENT_COMPARE_PLAYERS,
        "detected_players": ["Aaron Judge", "Juan Soto"],
    },
    {
        "message": "How does Judge match up against this left-handed pitcher?",
        "expected": INTENT_MATCHUP_ANALYSIS,
        "detected_player": "Aaron Judge",
    },
    {
        "message": "Why did the model give Judge a 42 percent home run probability?",
        "expected": INTENT_EXPLAIN_MODEL,
        "detected_player": "Aaron Judge",
        "detected_outcome": "home_run",
    },
    {
        "message": "What can you do?",
        "expected": INTENT_HELP,
    },
    {
        "message": "Tell me about Aaron Judge",
        "expected": INTENT_PLAYER_INFO,
        "detected_player": "Aaron Judge",
    },
    {
        "message": "Tell me about the Yankees",
        "expected": INTENT_TEAM_INFO,
        "detected_team": "New York Yankees",
    },
]


# ============================================================
# SECTION 27 - SELF-VALIDATION
# ============================================================

def validate_intent_detection_module() -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    for case in VALIDATION_CASES:
        decision = detect_intent(
            message=case["message"],
            detected_player=case.get("detected_player"),
            detected_team=case.get("detected_team"),
            detected_outcome=case.get("detected_outcome"),
            detected_players=case.get("detected_players"),
            detected_teams=case.get("detected_teams"),
        )

        passed = decision.final_intent == case["expected"]

        results.append({
            "message": case["message"],
            "expected": case["expected"],
            "actual": decision.final_intent,
            "confidence": decision.confidence_percent,
            "passed": passed,
        })

    passed_count = sum(1 for result in results if result["passed"])
    failed = [result for result in results if not result["passed"]]

    return {
        "status": "ok" if not failed else "failed",
        "engine_version": INTENT_DETECTION_VERSION,
        "schema_version": INTENT_DETECTION_SCHEMA_VERSION,
        "case_count": len(results),
        "passed_count": passed_count,
        "failed_count": len(failed),
        "accuracy": round(passed_count / len(results), 6) if results else 1.0,
        "failed_cases": failed,
        "results": results,
        "supported_intent_count": len(ALL_SUPPORTED_INTENTS),
        "rule_count": len(EVIDENCE_RULES),
    }


# ============================================================
# SECTION 28 - HUMAN-READABLE DIAGNOSTICS
# ============================================================

def build_intent_summary(
    decision_or_report: IntentDecision | Mapping[str, Any],
) -> str:
    if isinstance(decision_or_report, IntentDecision):
        decision = decision_or_report
        candidates = decision.candidates
        final_intent = decision.final_intent
        confidence = decision.confidence_percent
        ambiguous = decision.ambiguous
        routing_group = decision.routing_group
    else:
        final_intent = str(decision_or_report.get("final_intent"))
        confidence = int(decision_or_report.get("confidence", 0))
        ambiguous = bool(decision_or_report.get("ambiguous"))
        routing_group = str(decision_or_report.get("routing_group"))
        candidates = []

    lines = [
        "AISP2 Intent Detection",
        "=" * 48,
        f"Final Intent: {final_intent}",
        f"Routing Group: {routing_group}",
        f"Confidence: {confidence}%",
        f"Ambiguous: {ambiguous}",
    ]

    if candidates:
        lines.extend([
            "",
            "Top Candidates",
            "-" * 48,
        ])

        for candidate in candidates[:5]:
            lines.append(
                f"{candidate.rank}. {candidate.intent}: "
                f"net={candidate.net_score:.2f}, "
                f"normalized={candidate.normalized_score:.3f}, "
                f"probability={candidate.probability:.3f}"
            )

    return "\n".join(lines)


def print_intent_diagnostics(message: str, **kwargs: Any) -> IntentDecision:
    decision = detect_intent(message, **kwargs)
    print(build_intent_summary(decision))
    return decision


# ============================================================
# SECTION 29 - ENGINE CONFIGURATION EXPORT
# ============================================================

INTENT_DETECTION_CONFIGURATION = {
    "engine_version": INTENT_DETECTION_VERSION,
    "schema_version": INTENT_DETECTION_SCHEMA_VERSION,
    "weighted_evidence_enabled": True,
    "negative_evidence_enabled": True,
    "explicit_precedence_enabled": True,
    "entity_upgrade_enabled": True,
    "question_type_detection_enabled": True,
    "confidence_scoring_enabled": True,
    "multi_intent_reporting_enabled": True,
    "feature_vector_export_enabled": True,
    "fallback_to_general_baseball": True,
    "minimum_confidence": DEFAULT_MINIMUM_CONFIDENCE,
    "ambiguity_margin": DEFAULT_AMBIGUITY_MARGIN,
    "max_candidates": DEFAULT_MAX_CANDIDATES,
}


# ============================================================
# SECTION 30 - LOCAL VERIFICATION ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    validation_report = validate_intent_detection_module()

    print(
        "AISP2 Intent Detection Validation"
    )
    print("=" * 48)
    print(f"Status: {validation_report['status']}")
    print(f"Version: {validation_report['engine_version']}")
    print(f"Cases: {validation_report['case_count']}")
    print(f"Passed: {validation_report['passed_count']}")
    print(f"Failed: {validation_report['failed_count']}")
    print(f"Accuracy: {validation_report['accuracy']:.2%}")

    if validation_report["failed_cases"]:
        print("")
        print("Failed Cases")
        print("-" * 48)

        for failed_case in validation_report["failed_cases"]:
            print(
                f"- {failed_case['message']} "
                f"(expected={failed_case['expected']}, "
                f"actual={failed_case['actual']})"
            )
