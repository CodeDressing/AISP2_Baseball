# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# PHASE 10 PART 15.0
# FILE: 04_ai/nlp/semantic_engine.py
# PURPOSE:
# Enterprise fallback semantic analyzer for AISP2 Baseball.
#
# ARCHITECTURAL CONTRACT:
# - This module is NOT the primary intent router.
# - This module MUST NOT compete with nlu_engine.py.
# - This module activates only when the primary route is absent,
#   unresolved, explicitly requests fallback, or falls beneath
#   a configurable confidence threshold.
# - This module may enrich, clarify, rank, and recommend.
# - This module may never silently replace an accepted primary
#   route with a different intent.
# ============================================================

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from collections import Counter
from collections import defaultdict
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
import math
import re
import unicodedata
from typing import Any
from typing import Final


# ============================================================
# SECTION 02 - ENGINE METADATA
# ============================================================

SEMANTIC_ENGINE_NAME: Final[str] = (
    "AISP2 Enterprise Fallback Semantic Analyzer"
)
SEMANTIC_ENGINE_VERSION: Final[str] = "6.0.0"
SEMANTIC_ENGINE_PHASE: Final[str] = "Phase 10 Part 15.0"
SEMANTIC_ENGINE_PATH: Final[str] = "04_ai/nlp/semantic_engine.py"
SEMANTIC_ENGINE_STATUS: Final[str] = "fallback_only"
SEMANTIC_SCHEMA_VERSION: Final[str] = "3.0.0"

SEMANTIC_ENGINE_ROLE: Final[str] = "fallback_semantic_analyzer"
SEMANTIC_ENGINE_PRIMARY_ROUTER: Final[str] = "nlu_engine"
SEMANTIC_ENGINE_CAN_OVERRIDE_PRIMARY: Final[bool] = False
SEMANTIC_ENGINE_CAN_ENRICH_PRIMARY: Final[bool] = True


# ============================================================
# SECTION 03 - CONFIDENCE CONSTANTS
# ============================================================

SEMANTIC_CONFIDENCE_MINIMUM: Final[int] = 35
SEMANTIC_CONFIDENCE_WEAK: Final[int] = 50
SEMANTIC_CONFIDENCE_STANDARD: Final[int] = 65
SEMANTIC_CONFIDENCE_STRONG: Final[int] = 80
SEMANTIC_CONFIDENCE_HIGH: Final[int] = 90
SEMANTIC_CONFIDENCE_MAXIMUM: Final[int] = 95

PRIMARY_CONFIDENCE_ACCEPTED: Final[float] = 0.78
PRIMARY_CONFIDENCE_FALLBACK: Final[float] = 0.62
PRIMARY_CONFIDENCE_UNRESOLVED: Final[float] = 0.40

DEFAULT_MAX_EVIDENCE_ITEMS: Final[int] = 24
DEFAULT_MAX_ENTITY_CANDIDATES: Final[int] = 8
DEFAULT_AMBIGUITY_MARGIN: Final[float] = 0.07


# ============================================================
# SECTION 04 - ENUMERATIONS
# ============================================================

class SemanticActivationDecision(str, Enum):
    SKIP_PRIMARY_ACCEPTED = "skip_primary_accepted"
    ACTIVATE_NO_PRIMARY_RESULT = "activate_no_primary_result"
    ACTIVATE_PRIMARY_UNRESOLVED = "activate_primary_unresolved"
    ACTIVATE_LOW_CONFIDENCE = "activate_low_confidence"
    ACTIVATE_EXPLICIT_REQUEST = "activate_explicit_request"
    ACTIVATE_MISSING_REQUIRED_ENTITY = "activate_missing_required_entity"
    ACTIVATE_AMBIGUOUS_PRIMARY = "activate_ambiguous_primary"


class SemanticAnalysisStatus(str, Enum):
    SKIPPED = "skipped"
    ENRICHED = "enriched"
    FALLBACK_RECOMMENDATION = "fallback_recommendation"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNRESOLVED = "unresolved"
    ERROR = "error"


class SemanticEvidenceKind(str, Enum):
    EXACT_PHRASE = "exact_phrase"
    KEYWORD = "keyword"
    ENTITY = "entity"
    OUTCOME = "outcome"
    COMPARISON = "comparison"
    TEMPORAL = "temporal"
    QUANTIFIER = "quantifier"
    NEGATION = "negation"
    PRIMARY_ROUTE = "primary_route"
    FUZZY_MATCH = "fuzzy_match"
    CONTEXT = "context"
    STRUCTURE = "structure"


class SemanticIntentFamily(str, Enum):
    LIST_TEAMS = "list_teams"
    LIST_PLAYERS = "list_players"
    PLAYER_INFO = "player_info"
    TEAM_INFO = "team_info"
    PLAYER_PROBABILITY = "player_probability"
    TEAM_PROBABILITY = "team_probability"
    COMPARE_PLAYERS = "compare_players"
    COMPARE_TEAMS = "compare_teams"
    ROSTER = "roster"
    SCHEDULE = "schedule"
    STANDINGS = "standings"
    MODEL_STATUS = "model_status"
    DATA_STATUS = "data_status"
    GENERAL_BASEBALL = "general_baseball_question"
    UNKNOWN = "unknown"


class SemanticEntityType(str, Enum):
    PLAYER = "player"
    TEAM = "team"
    OUTCOME = "outcome"
    DATE = "date"
    NUMBER = "number"
    POSITION = "position"
    LEAGUE = "league"
    DIVISION = "division"


class SemanticRiskFlag(str, Enum):
    PRIMARY_ROUTE_CONFLICT = "primary_route_conflict"
    LOW_EVIDENCE = "low_evidence"
    AMBIGUOUS_ENTITY = "ambiguous_entity"
    MISSING_REQUIRED_ENTITY = "missing_required_entity"
    MULTIPLE_POSSIBLE_INTENTS = "multiple_possible_intents"
    ORDINARY_WORD_COLLISION = "ordinary_word_collision"
    EMPTY_WAREHOUSE = "empty_warehouse"
    FALLBACK_ONLY = "fallback_only"


# ============================================================
# SECTION 05 - CONFIGURATION
# ============================================================

@dataclass(slots=True)
class SemanticFallbackConfig:
    primary_acceptance_threshold: float = PRIMARY_CONFIDENCE_ACCEPTED
    fallback_activation_threshold: float = PRIMARY_CONFIDENCE_FALLBACK
    unresolved_threshold: float = PRIMARY_CONFIDENCE_UNRESOLVED
    ambiguity_margin: float = DEFAULT_AMBIGUITY_MARGIN

    max_evidence_items: int = DEFAULT_MAX_EVIDENCE_ITEMS
    max_entity_candidates: int = DEFAULT_MAX_ENTITY_CANDIDATES

    enable_player_detection: bool = True
    enable_team_detection: bool = True
    enable_outcome_detection: bool = True
    enable_temporal_detection: bool = True
    enable_comparison_detection: bool = True
    enable_constraint_detection: bool = True
    enable_fuzzy_support: bool = True
    enable_context_support: bool = True

    allow_primary_enrichment: bool = True
    allow_fallback_recommendation: bool = True
    allow_primary_override: bool = False

    require_primary_handoff: bool = False
    preserve_primary_intent: bool = True
    emit_diagnostics: bool = True

    def validate(self) -> None:
        for field_name in (
            "primary_acceptance_threshold",
            "fallback_activation_threshold",
            "unresolved_threshold",
            "ambiguity_margin",
        ):
            value = float(getattr(self, field_name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        if self.max_evidence_items <= 0:
            raise ValueError(
                "max_evidence_items must be positive"
            )

        if self.max_entity_candidates <= 0:
            raise ValueError(
                "max_entity_candidates must be positive"
            )

        if self.allow_primary_override:
            raise ValueError(
                "semantic fallback cannot override the primary router"
            )


DEFAULT_SEMANTIC_CONFIG = SemanticFallbackConfig()


# ============================================================
# SECTION 06 - DATA CONTRACTS
# ============================================================

@dataclass(slots=True)
class PrimaryRouteState:
    intent: str | None = None
    confidence: float = 0.0
    accepted: bool = False
    unresolved: bool = False
    ambiguous: bool = False
    fallback_requested: bool = False

    player: str | None = None
    team: str | None = None
    outcome: str | None = None

    players: list[str] = field(default_factory=list)
    teams: list[str] = field(default_factory=list)
    outcomes: list[str] = field(default_factory=list)

    missing_required_entities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any] | None,
    ) -> "PrimaryRouteState":
        if not payload:
            return cls()

        confidence = coerce_confidence(
            payload.get("confidence", 0.0)
        )

        accepted = bool(
            payload.get("accepted")
            or payload.get("matched")
            or payload.get("route_accepted")
        )

        unresolved = bool(
            payload.get("unresolved")
            or payload.get("needs_fallback")
            or payload.get("status") in {
                "unresolved",
                "unknown",
                "no_match",
            }
        )

        ambiguous = bool(
            payload.get("ambiguous")
            or payload.get("decision") == "ambiguous"
        )

        fallback_requested = bool(
            payload.get("fallback_requested")
            or payload.get("use_semantic_fallback")
            or payload.get("needs_semantic_support")
        )

        return cls(
            intent=(
                payload.get("intent")
                or payload.get("route")
                or payload.get("intent_name")
            ),
            confidence=confidence,
            accepted=accepted,
            unresolved=unresolved,
            ambiguous=ambiguous,
            fallback_requested=fallback_requested,
            player=payload.get("player"),
            team=payload.get("team"),
            outcome=payload.get("outcome"),
            players=list(payload.get("players") or []),
            teams=list(payload.get("teams") or []),
            outcomes=list(payload.get("outcomes") or []),
            missing_required_entities=list(
                payload.get("missing_required_entities")
                or payload.get("missing_entities")
                or []
            ),
            metadata=dict(payload.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SemanticEvidence:
    kind: SemanticEvidenceKind
    label: str
    value: Any
    score: float
    source_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "label": self.label,
            "value": self.value,
            "score": round(float(self.score), 6),
            "source_text": self.source_text,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class SemanticEntityCandidate:
    entity_type: SemanticEntityType
    canonical_value: str
    observed_value: str
    score: float
    entity_id: int | str | None = None
    source: str = "semantic"
    ambiguous: bool = False
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type.value,
            "canonical_value": self.canonical_value,
            "observed_value": self.observed_value,
            "score": round(float(self.score), 6),
            "entity_id": self.entity_id,
            "source": self.source,
            "ambiguous": self.ambiguous,
            "alternatives": list(self.alternatives),
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class SemanticFallbackResult:
    message: str
    normalized_message: str

    activation_decision: SemanticActivationDecision
    status: SemanticAnalysisStatus

    primary_route: PrimaryRouteState
    primary_route_preserved: bool

    recommended_intent: str | None = None
    recommended_confidence: float = 0.0

    player: str | None = None
    team: str | None = None
    outcome: str | None = None

    players: list[str] = field(default_factory=list)
    teams: list[str] = field(default_factory=list)
    outcomes: list[str] = field(default_factory=list)

    entity_candidates: list[SemanticEntityCandidate] = field(
        default_factory=list
    )
    evidence: list[SemanticEvidence] = field(default_factory=list)
    risk_flags: list[SemanticRiskFlag] = field(default_factory=list)

    clarification_required: bool = False
    clarification_question: str | None = None

    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_name": SEMANTIC_ENGINE_NAME,
            "engine_version": SEMANTIC_ENGINE_VERSION,
            "engine_phase": SEMANTIC_ENGINE_PHASE,
            "engine_role": SEMANTIC_ENGINE_ROLE,
            "can_override_primary": SEMANTIC_ENGINE_CAN_OVERRIDE_PRIMARY,
            "message": self.message,
            "normalized_message": self.normalized_message,
            "activation_decision": self.activation_decision.value,
            "status": self.status.value,
            "primary_route": self.primary_route.to_dict(),
            "primary_route_preserved": self.primary_route_preserved,
            "recommended_intent": self.recommended_intent,
            "recommended_confidence": round(
                float(self.recommended_confidence),
                6,
            ),
            "player": self.player,
            "team": self.team,
            "outcome": self.outcome,
            "players": list(self.players),
            "teams": list(self.teams),
            "outcomes": list(self.outcomes),
            "entity_candidates": [
                item.to_dict()
                for item in self.entity_candidates
            ],
            "evidence": [
                item.to_dict()
                for item in self.evidence
            ],
            "risk_flags": [
                item.value
                for item in self.risk_flags
            ],
            "clarification_required": self.clarification_required,
            "clarification_question": self.clarification_question,
            "diagnostics": dict(self.diagnostics),
        }


# ============================================================
# SECTION 07 - NORMALIZATION
# ============================================================

WHITESPACE_PATTERN = re.compile(r"\s+")
NON_ALPHANUMERIC_PATTERN = re.compile(r"[^a-z0-9+\-.\s]")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")


def normalize_text(
    value: str | None,
) -> str:
    if not value:
        return ""

    text = unicodedata.normalize(
        "NFKD",
        str(value),
    )

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    text = text.lower()
    text = text.replace("’", "'")
    text = text.replace("&", " and ")
    text = text.replace("_", " ")
    text = text.replace("/", " ")
    text = text.replace("-", " ")

    text = NON_ALPHANUMERIC_PATTERN.sub(
        " ",
        text,
    )

    return WHITESPACE_PATTERN.sub(
        " ",
        text,
    ).strip()


def tokenize_text(
    value: str | None,
) -> list[str]:
    return TOKEN_PATTERN.findall(
        normalize_text(value)
    )


def contains_phrase(
    text: str,
    phrase: str,
) -> bool:
    normalized_text = normalize_text(text)
    normalized_phrase = normalize_text(phrase)

    if not normalized_text or not normalized_phrase:
        return False

    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(normalized_phrase)
        + r"(?![a-z0-9])"
    )

    return bool(
        re.search(pattern, normalized_text)
    )


def contains_any_keyword(
    text: str,
    keywords: Sequence[str],
) -> bool:
    return any(
        contains_phrase(text, keyword)
        for keyword in keywords
    )


def unique_preserving_order(
    values: Iterable[str],
) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = normalize_text(value)

        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        output.append(str(value))

    return output


def coerce_confidence(
    value: Any,
) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0

    if confidence > 1.0:
        confidence = confidence / 100.0

    return max(0.0, min(1.0, confidence))


# ============================================================
# SECTION 08 - OUTCOME VOCABULARY
# ============================================================

OUTCOME_KEYWORDS: Final[
    dict[str, tuple[str, ...]]
] = {
    "home_run": (
        "home run",
        "home runs",
        "homer",
        "homers",
        "hr",
        "go deep",
        "go yard",
        "dinger",
        "long ball",
        "hit one out",
        "leave the park",
        "hit a bomb",
    ),
    "hit": (
        "hit",
        "hits",
        "base hit",
        "get a hit",
        "record a hit",
        "safe hit",
    ),
    "single": (
        "single",
        "one base hit",
        "1b",
    ),
    "double": (
        "double",
        "two bagger",
        "2b",
    ),
    "triple": (
        "triple",
        "three bagger",
        "3b",
    ),
    "rbi": (
        "rbi",
        "rbis",
        "run batted in",
        "runs batted in",
        "drive in",
        "knock in",
    ),
    "run_scored": (
        "run scored",
        "score a run",
        "scores",
        "cross the plate",
    ),
    "walk": (
        "walk",
        "walks",
        "base on balls",
        "bb",
    ),
    "strikeout": (
        "strikeout",
        "strikeouts",
        "strike out",
        "punchout",
        "whiff",
        "fan",
        "ks",
    ),
    "stolen_base": (
        "stolen base",
        "steal",
        "steals",
        "stolen bases",
        "sb",
    ),
    "total_bases": (
        "total bases",
        "total base",
        "tb",
        "extra bases",
    ),
    "earned_runs": (
        "earned runs",
        "runs allowed",
        "er",
    ),
    "hits_allowed": (
        "hits allowed",
        "allow hits",
    ),
    "outs_recorded": (
        "outs recorded",
        "pitching outs",
    ),
    "innings_pitched": (
        "innings pitched",
        "ip",
    ),
}


HITTING_OUTCOMES: Final[frozenset[str]] = frozenset({
    "home_run",
    "hit",
    "single",
    "double",
    "triple",
    "rbi",
    "run_scored",
    "walk",
    "total_bases",
})

PITCHING_OUTCOMES: Final[frozenset[str]] = frozenset({
    "strikeout",
    "earned_runs",
    "hits_allowed",
    "outs_recorded",
    "innings_pitched",
})

BASERUNNING_OUTCOMES: Final[frozenset[str]] = frozenset({
    "stolen_base",
})


# ============================================================
# SECTION 09 - TEAM ALIASES
# ============================================================

TEAM_ALIASES: Final[
    dict[str, tuple[str, ...]]
] = {
    "Arizona Diamondbacks": (
        "diamondbacks", "dbacks", "d backs", "ari",
    ),
    "Athletics": (
        "athletics", "a's", "as", "athletics club",
    ),
    "Atlanta Braves": (
        "braves", "atl", "atlanta",
    ),
    "Baltimore Orioles": (
        "orioles", "o's", "os", "bal", "baltimore",
    ),
    "Boston Red Sox": (
        "red sox", "bos", "boston", "sox",
    ),
    "Chicago Cubs": (
        "cubs", "chc", "chicago cubs",
    ),
    "Chicago White Sox": (
        "white sox", "chw", "cws",
    ),
    "Cincinnati Reds": (
        "reds", "cin", "cincinnati",
    ),
    "Cleveland Guardians": (
        "guardians", "cle", "cleveland",
    ),
    "Colorado Rockies": (
        "rockies", "col", "colorado",
    ),
    "Detroit Tigers": (
        "tigers", "det", "detroit",
    ),
    "Houston Astros": (
        "astros", "hou", "houston",
    ),
    "Kansas City Royals": (
        "royals", "kc", "kcr", "kansas city",
    ),
    "Los Angeles Angels": (
        "angels", "laa", "la angels", "anaheim",
    ),
    "Los Angeles Dodgers": (
        "dodgers", "lad", "la dodgers",
    ),
    "Miami Marlins": (
        "marlins", "mia", "miami",
    ),
    "Milwaukee Brewers": (
        "brewers", "mil", "milwaukee",
    ),
    "Minnesota Twins": (
        "twins", "min", "minnesota",
    ),
    "New York Mets": (
        "mets", "nym", "ny mets",
    ),
    "New York Yankees": (
        "yankees", "nyy", "bronx bombers", "yanks",
    ),
    "Philadelphia Phillies": (
        "phillies", "phi", "phils", "philadelphia",
    ),
    "Pittsburgh Pirates": (
        "pirates", "pit", "bucs", "pittsburgh",
    ),
    "San Diego Padres": (
        "padres", "sd", "sdp", "san diego",
    ),
    "San Francisco Giants": (
        "giants", "sf", "sfg", "san francisco",
    ),
    "Seattle Mariners": (
        "mariners", "sea", "seattle", "m's",
    ),
    "St. Louis Cardinals": (
        "cardinals", "cards", "stl", "st louis",
    ),
    "Tampa Bay Rays": (
        "rays", "tb", "tbr", "tampa bay",
    ),
    "Texas Rangers": (
        "rangers", "tex", "texas",
    ),
    "Toronto Blue Jays": (
        "blue jays", "jays", "tor", "toronto",
    ),
    "Washington Nationals": (
        "nationals", "nats", "wsh", "washington",
    ),
}


# ============================================================
# SECTION 10 - INTENT SUPPORT VOCABULARY
# ============================================================

INTENT_EVIDENCE: Final[
    dict[str, tuple[str, ...]]
] = {
    SemanticIntentFamily.LIST_TEAMS.value: (
        "show all teams",
        "list teams",
        "what teams",
        "which teams",
        "teams do you have",
        "teams do you know",
    ),
    SemanticIntentFamily.LIST_PLAYERS.value: (
        "show all players",
        "list players",
        "what players",
        "which players",
        "players do you have",
        "players do you know",
    ),
    SemanticIntentFamily.ROSTER.value: (
        "roster",
        "team roster",
        "active roster",
        "full roster",
        "players on",
        "who plays for",
    ),
    SemanticIntentFamily.SCHEDULE.value: (
        "schedule",
        "next game",
        "games today",
        "upcoming games",
        "who do they play",
    ),
    SemanticIntentFamily.STANDINGS.value: (
        "standings",
        "division standings",
        "league standings",
        "record",
        "win loss",
    ),
    SemanticIntentFamily.MODEL_STATUS.value: (
        "model status",
        "prediction model status",
        "ai status",
        "engine status",
    ),
    SemanticIntentFamily.DATA_STATUS.value: (
        "data status",
        "warehouse status",
        "database status",
        "ingestion status",
    ),
    SemanticIntentFamily.COMPARE_PLAYERS.value: (
        "compare players",
        "compare",
        "versus",
        "vs",
        "who is better",
        "who is more likely",
    ),
    SemanticIntentFamily.COMPARE_TEAMS.value: (
        "compare teams",
        "team comparison",
        "versus",
        "vs",
    ),
    SemanticIntentFamily.PLAYER_PROBABILITY.value: (
        "probability",
        "chance",
        "odds",
        "projection",
        "predict",
        "prediction",
        "likely",
        "will he",
        "can he",
    ),
    SemanticIntentFamily.TEAM_PROBABILITY.value: (
        "win probability",
        "chance to win",
        "team prediction",
        "game prediction",
    ),
    SemanticIntentFamily.PLAYER_INFO.value: (
        "player profile",
        "player stats",
        "tell me about",
        "search player",
        "find player",
        "analyze player",
    ),
    SemanticIntentFamily.TEAM_INFO.value: (
        "team info",
        "team profile",
        "tell me about the team",
        "club information",
    ),
}


# ============================================================
# SECTION 11 - TEMPORAL VOCABULARY
# ============================================================

TEMPORAL_KEYWORDS: Final[
    dict[str, tuple[str, ...]]
] = {
    "today": ("today", "tonight", "this evening"),
    "tomorrow": ("tomorrow", "tomorrow night"),
    "yesterday": ("yesterday", "last night"),
    "this_week": ("this week", "current week"),
    "next_week": ("next week",),
    "this_month": ("this month",),
    "this_season": ("this season", "current season"),
    "career": ("career", "all time"),
    "last_game": ("last game", "most recent game"),
    "next_game": ("next game", "upcoming game"),
}


# ============================================================
# SECTION 12 - ACTIVATION POLICY
# ============================================================

def decide_semantic_fallback_activation(
    primary_route: PrimaryRouteState | Mapping[str, Any] | None,
    *,
    config: SemanticFallbackConfig | None = None,
) -> SemanticActivationDecision:
    config = config or SemanticFallbackConfig()
    config.validate()

    state = (
        primary_route
        if isinstance(primary_route, PrimaryRouteState)
        else PrimaryRouteState.from_mapping(primary_route)
    )

    has_primary_information = bool(
        state.intent
        or state.accepted
        or state.unresolved
        or state.confidence
        or state.metadata
    )

    if not has_primary_information:
        return (
            SemanticActivationDecision.ACTIVATE_NO_PRIMARY_RESULT
        )

    if state.fallback_requested:
        return (
            SemanticActivationDecision.ACTIVATE_EXPLICIT_REQUEST
        )

    if state.missing_required_entities:
        return (
            SemanticActivationDecision.ACTIVATE_MISSING_REQUIRED_ENTITY
        )

    if state.ambiguous:
        return (
            SemanticActivationDecision.ACTIVATE_AMBIGUOUS_PRIMARY
        )

    if state.unresolved:
        return (
            SemanticActivationDecision.ACTIVATE_PRIMARY_UNRESOLVED
        )

    if (
        state.accepted
        and state.confidence
        >= config.primary_acceptance_threshold
    ):
        return (
            SemanticActivationDecision.SKIP_PRIMARY_ACCEPTED
        )

    if (
        state.confidence
        < config.fallback_activation_threshold
    ):
        return (
            SemanticActivationDecision.ACTIVATE_LOW_CONFIDENCE
        )

    if state.accepted:
        return (
            SemanticActivationDecision.SKIP_PRIMARY_ACCEPTED
        )

    return (
        SemanticActivationDecision.ACTIVATE_LOW_CONFIDENCE
    )


# ============================================================
# SECTION 13 - TEAM DETECTION
# ============================================================

def _team_payload_aliases(
    team_name: str,
    team_data: Mapping[str, Any] | None,
) -> list[str]:
    aliases = list(
        TEAM_ALIASES.get(team_name, ())
    )
    aliases.append(team_name)

    if team_data:
        for key in (
            "abbreviation",
            "short_name",
            "club_name",
            "franchise_name",
            "location_name",
            "team_code",
            "file_code",
        ):
            value = team_data.get(key)
            if value:
                aliases.append(str(value))

    return unique_preserving_order(aliases)


def detect_team_candidates(
    message: str,
    teams: Mapping[str, Any] | None,
    *,
    max_candidates: int = DEFAULT_MAX_ENTITY_CANDIDATES,
) -> list[SemanticEntityCandidate]:
    if not teams:
        return []

    normalized_message = normalize_text(message)
    candidates: list[SemanticEntityCandidate] = []

    for team_name, raw_data in teams.items():
        team_data = (
            raw_data
            if isinstance(raw_data, Mapping)
            else {}
        )

        aliases = _team_payload_aliases(
            str(team_name),
            team_data,
        )

        best_score = 0.0
        best_observed = ""

        for alias in aliases:
            normalized_alias = normalize_text(alias)

            if not normalized_alias:
                continue

            if contains_phrase(
                normalized_message,
                normalized_alias,
            ):
                score = min(
                    1.0,
                    0.88
                    + min(
                        len(normalized_alias) / 100.0,
                        0.12,
                    ),
                )

                if score > best_score:
                    best_score = score
                    best_observed = alias

        if best_score > 0:
            candidates.append(
                SemanticEntityCandidate(
                    entity_type=SemanticEntityType.TEAM,
                    canonical_value=str(team_name),
                    observed_value=best_observed,
                    score=best_score,
                    entity_id=(
                        team_data.get("mlb_team_id")
                        or team_data.get("id")
                    ),
                    source="exact_semantic_alias",
                    metadata={
                        "abbreviation": team_data.get(
                            "abbreviation"
                        ),
                    },
                )
            )

    candidates.sort(
        key=lambda item: (
            item.score,
            len(item.observed_value),
        ),
        reverse=True,
    )

    return candidates[:max_candidates]


def detect_teams(
    message: str,
    teams: Mapping[str, Any],
) -> list[str]:
    return [
        candidate.canonical_value
        for candidate in detect_team_candidates(
            message,
            teams,
        )
    ]


def detect_team(
    message: str,
    teams: Mapping[str, Any],
) -> str | None:
    detected = detect_teams(
        message,
        teams,
    )
    return detected[0] if detected else None


# ============================================================
# SECTION 14 - PLAYER DETECTION
# ============================================================

ORDINARY_PLAYER_COLLISION_WORDS: Final[frozenset[str]] = frozenset({
    "best",
    "judge",
    "smith",
    "young",
    "king",
    "ray",
    "bell",
    "walker",
    "story",
    "turner",
})


def _player_payload_aliases(
    player_name: str,
    player_data: Mapping[str, Any] | None,
) -> list[str]:
    aliases = [player_name]

    if player_data:
        for key in (
            "aliases",
            "nick_name",
            "nickname",
            "use_name",
            "boxscore_name",
            "name_slug",
        ):
            value = player_data.get(key)

            if isinstance(value, str):
                aliases.append(value)

            elif isinstance(value, Sequence):
                aliases.extend(
                    str(item)
                    for item in value
                    if item
                )

        first_name = (
            player_data.get("first_name")
            or player_data.get("use_name")
        )
        last_name = player_data.get("last_name")

        if first_name and last_name:
            aliases.append(
                f"{first_name} {last_name}"
            )

    return unique_preserving_order(aliases)


def detect_player_candidates(
    message: str,
    player_profiles: Mapping[str, Any] | None,
    *,
    max_candidates: int = DEFAULT_MAX_ENTITY_CANDIDATES,
) -> list[SemanticEntityCandidate]:
    if not player_profiles:
        return []

    normalized_message = normalize_text(message)
    tokens = set(tokenize_text(message))
    candidates: list[SemanticEntityCandidate] = []

    for player_name, raw_data in player_profiles.items():
        player_data = (
            raw_data
            if isinstance(raw_data, Mapping)
            else {}
        )

        aliases = _player_payload_aliases(
            str(player_name),
            player_data,
        )

        best_score = 0.0
        best_observed = ""

        for alias in aliases:
            normalized_alias = normalize_text(alias)

            if not normalized_alias:
                continue

            alias_tokens = tokenize_text(
                normalized_alias
            )

            if contains_phrase(
                normalized_message,
                normalized_alias,
            ):
                score = 1.0

                if (
                    len(alias_tokens) == 1
                    and alias_tokens[0]
                    in ORDINARY_PLAYER_COLLISION_WORDS
                ):
                    score = 0.68

                if score > best_score:
                    best_score = score
                    best_observed = alias

        name_tokens = tokenize_text(
            str(player_name)
        )

        if (
            len(name_tokens) >= 2
            and name_tokens[-1] in tokens
            and best_score < 0.82
        ):
            last_name = name_tokens[-1]

            if last_name not in ORDINARY_PLAYER_COLLISION_WORDS:
                best_score = 0.82
                best_observed = last_name

        if best_score > 0:
            candidates.append(
                SemanticEntityCandidate(
                    entity_type=SemanticEntityType.PLAYER,
                    canonical_value=str(player_name),
                    observed_value=best_observed,
                    score=best_score,
                    entity_id=(
                        player_data.get("mlb_player_id")
                        or player_data.get("id")
                    ),
                    source="exact_semantic_name",
                )
            )

    candidates.sort(
        key=lambda item: (
            item.score,
            len(item.observed_value),
        ),
        reverse=True,
    )

    return candidates[:max_candidates]


def detect_players(
    message: str,
    player_profiles: Mapping[str, Any],
) -> list[str]:
    return [
        candidate.canonical_value
        for candidate in detect_player_candidates(
            message,
            player_profiles,
        )
    ]


def detect_player(
    message: str,
    player_profiles: Mapping[str, Any],
) -> str | None:
    detected = detect_players(
        message,
        player_profiles,
    )
    return detected[0] if detected else None


# ============================================================
# SECTION 15 - FUZZY SUPPORT ADAPTER
# ============================================================

def _load_fuzzy_support() -> Any | None:
    try:
        from nlp import fuzzy_matching
        return fuzzy_matching
    except Exception:
        pass

    try:
        import fuzzy_matching
        return fuzzy_matching
    except Exception:
        return None


def apply_fuzzy_semantic_support(
    message: str,
    *,
    player_profiles: Mapping[str, Any] | None = None,
    teams: Mapping[str, Any] | None = None,
    config: SemanticFallbackConfig | None = None,
) -> list[SemanticEntityCandidate]:
    config = config or SemanticFallbackConfig()

    if not config.enable_fuzzy_support:
        return []

    fuzzy_module = _load_fuzzy_support()

    if fuzzy_module is None:
        return []

    candidates: list[SemanticEntityCandidate] = []

    try:
        if player_profiles:
            player_result = (
                fuzzy_module.find_fuzzy_player_match(
                    message,
                    list(player_profiles.keys()),
                    use_warehouse=False,
                )
            )

            if (
                player_result.get("matched")
                and player_result.get("best_match")
            ):
                best = player_result["best_match"]

                candidates.append(
                    SemanticEntityCandidate(
                        entity_type=SemanticEntityType.PLAYER,
                        canonical_value=best[
                            "canonical_name"
                        ],
                        observed_value=best.get(
                            "observed_phrase",
                            "",
                        ),
                        score=float(
                            best.get(
                                "adjusted_score",
                                0.0,
                            )
                        ),
                        entity_id=best.get("entity_id"),
                        source="fuzzy_matching_engine",
                        alternatives=player_result.get(
                            "ranked_candidates",
                            [],
                        )[1:4],
                    )
                )
    except Exception:
        pass

    try:
        if teams:
            team_result = (
                fuzzy_module.find_fuzzy_team_match(
                    message,
                    list(teams.keys()),
                    use_warehouse=False,
                )
            )

            if (
                team_result.get("matched")
                and team_result.get("best_match")
            ):
                best = team_result["best_match"]

                candidates.append(
                    SemanticEntityCandidate(
                        entity_type=SemanticEntityType.TEAM,
                        canonical_value=best[
                            "canonical_name"
                        ],
                        observed_value=best.get(
                            "observed_phrase",
                            "",
                        ),
                        score=float(
                            best.get(
                                "adjusted_score",
                                0.0,
                            )
                        ),
                        entity_id=best.get("entity_id"),
                        source="fuzzy_matching_engine",
                        alternatives=team_result.get(
                            "ranked_candidates",
                            [],
                        )[1:4],
                    )
                )
    except Exception:
        pass

    return candidates


# ============================================================
# SECTION 16 - OUTCOME DETECTION
# ============================================================

def detect_outcome_candidates(
    message: str,
) -> list[SemanticEntityCandidate]:
    normalized_message = normalize_text(message)
    candidates: list[SemanticEntityCandidate] = []

    for outcome_key, keywords in (
        OUTCOME_KEYWORDS.items()
    ):
        best_score = 0.0
        best_observed = ""

        for keyword in keywords:
            if contains_phrase(
                normalized_message,
                keyword,
            ):
                normalized_keyword = normalize_text(
                    keyword
                )

                score = min(
                    1.0,
                    0.80
                    + min(
                        len(normalized_keyword)
                        / 80.0,
                        0.20,
                    ),
                )

                if score > best_score:
                    best_score = score
                    best_observed = keyword

        if best_score > 0:
            candidates.append(
                SemanticEntityCandidate(
                    entity_type=SemanticEntityType.OUTCOME,
                    canonical_value=outcome_key,
                    observed_value=best_observed,
                    score=best_score,
                    source="semantic_outcome_vocabulary",
                )
            )

    candidates.sort(
        key=lambda item: item.score,
        reverse=True,
    )

    return candidates


def detect_outcomes(
    message: str,
) -> list[str]:
    return [
        candidate.canonical_value
        for candidate in detect_outcome_candidates(
            message
        )
    ]


def detect_outcome(
    message: str,
) -> str | None:
    detected = detect_outcomes(message)
    return detected[0] if detected else None


# ============================================================
# SECTION 17 - TEMPORAL DETECTION
# ============================================================

def detect_temporal_references(
    message: str,
) -> list[str]:
    detected: list[str] = []

    for canonical, keywords in (
        TEMPORAL_KEYWORDS.items()
    ):
        if contains_any_keyword(
            message,
            keywords,
        ):
            detected.append(canonical)

    years = re.findall(
        r"\b(?:19|20)\d{2}\b",
        normalize_text(message),
    )

    detected.extend(
        f"year:{year}"
        for year in years
    )

    return unique_preserving_order(
        detected
    )


# ============================================================
# SECTION 18 - NUMERIC CONSTRAINTS
# ============================================================

NUMERIC_OPERATOR_PATTERNS: Final[
    tuple[tuple[str, str], ...]
] = (
    (r"\bover\s+([0-9]+(?:\.[0-9]+)?)\b", "over"),
    (r"\bunder\s+([0-9]+(?:\.[0-9]+)?)\b", "under"),
    (r"\bat least\s+([0-9]+(?:\.[0-9]+)?)\b", "at_least"),
    (r"\bat most\s+([0-9]+(?:\.[0-9]+)?)\b", "at_most"),
    (r"\bmore than\s+([0-9]+(?:\.[0-9]+)?)\b", "greater_than"),
    (r"\bless than\s+([0-9]+(?:\.[0-9]+)?)\b", "less_than"),
    (r"\bexactly\s+([0-9]+(?:\.[0-9]+)?)\b", "exactly"),
)


def detect_numeric_constraints(
    message: str,
) -> list[dict[str, Any]]:
    normalized = normalize_text(message)
    constraints: list[dict[str, Any]] = []

    for pattern, operator in (
        NUMERIC_OPERATOR_PATTERNS
    ):
        for match in re.finditer(
            pattern,
            normalized,
        ):
            constraints.append({
                "operator": operator,
                "value": float(match.group(1)),
                "source_text": match.group(0),
            })

    return constraints


# ============================================================
# SECTION 19 - COMPARISON DETECTION
# ============================================================

COMPARISON_KEYWORDS: Final[
    tuple[str, ...]
] = (
    "compare",
    "versus",
    "vs",
    "who is better",
    "who is more likely",
    "difference between",
    "which is better",
)


def detect_comparison_request(
    message: str,
) -> bool:
    return contains_any_keyword(
        message,
        COMPARISON_KEYWORDS,
    )


# ============================================================
# SECTION 20 - NEGATION DETECTION
# ============================================================

NEGATION_KEYWORDS: Final[
    tuple[str, ...]
] = (
    "not",
    "dont",
    "don't",
    "do not",
    "without",
    "exclude",
    "excluding",
    "except",
)


def detect_negation(
    message: str,
) -> bool:
    return contains_any_keyword(
        message,
        NEGATION_KEYWORDS,
    )


# ============================================================
# SECTION 21 - INTENT EVIDENCE SCORING
# ============================================================

def score_intent_evidence(
    message: str,
) -> dict[str, float]:
    scores: dict[str, float] = {}

    for intent, phrases in (
        INTENT_EVIDENCE.items()
    ):
        score = 0.0

        for phrase in phrases:
            if contains_phrase(
                message,
                phrase,
            ):
                normalized_phrase = normalize_text(
                    phrase
                )

                score += min(
                    0.55,
                    0.24
                    + len(normalized_phrase)
                    / 100.0,
                )

        scores[intent] = min(
            1.0,
            score,
        )

    return scores


# ============================================================
# SECTION 22 - INTENT RECOMMENDATION
# ============================================================

def recommend_fallback_intent(
    message: str,
    *,
    players: Sequence[str],
    teams: Sequence[str],
    outcomes: Sequence[str],
    primary_route: PrimaryRouteState,
) -> tuple[str, float, list[SemanticEvidence]]:
    evidence: list[SemanticEvidence] = []
    scores = score_intent_evidence(message)

    comparison = detect_comparison_request(
        message
    )

    if comparison:
        evidence.append(
            SemanticEvidence(
                kind=SemanticEvidenceKind.COMPARISON,
                label="comparison_request",
                value=True,
                score=0.88,
                source_text=message,
            )
        )

        if len(players) >= 2:
            scores[
                SemanticIntentFamily.COMPARE_PLAYERS.value
            ] = max(
                scores.get(
                    SemanticIntentFamily.COMPARE_PLAYERS.value,
                    0.0,
                ),
                0.94,
            )

        if len(teams) >= 2:
            scores[
                SemanticIntentFamily.COMPARE_TEAMS.value
            ] = max(
                scores.get(
                    SemanticIntentFamily.COMPARE_TEAMS.value,
                    0.0,
                ),
                0.94,
            )

    if players and outcomes:
        scores[
            SemanticIntentFamily.PLAYER_PROBABILITY.value
        ] = max(
            scores.get(
                SemanticIntentFamily.PLAYER_PROBABILITY.value,
                0.0,
            ),
            0.88,
        )

    if teams and not players:
        if contains_phrase(message, "roster"):
            scores[
                SemanticIntentFamily.ROSTER.value
            ] = max(
                scores.get(
                    SemanticIntentFamily.ROSTER.value,
                    0.0,
                ),
                0.90,
            )
        else:
            scores[
                SemanticIntentFamily.TEAM_INFO.value
            ] = max(
                scores.get(
                    SemanticIntentFamily.TEAM_INFO.value,
                    0.0,
                ),
                0.75,
            )

    if players and not outcomes:
        scores[
            SemanticIntentFamily.PLAYER_INFO.value
        ] = max(
            scores.get(
                SemanticIntentFamily.PLAYER_INFO.value,
                0.0,
            ),
            0.74,
        )

    if primary_route.intent:
        evidence.append(
            SemanticEvidence(
                kind=SemanticEvidenceKind.PRIMARY_ROUTE,
                label="primary_intent",
                value=primary_route.intent,
                score=primary_route.confidence,
            )
        )

    ranked = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    if not ranked or ranked[0][1] <= 0:
        return (
            SemanticIntentFamily.GENERAL_BASEBALL.value,
            0.35,
            evidence,
        )

    best_intent, best_score = ranked[0]

    for intent, score in ranked[:4]:
        if score <= 0:
            continue

        evidence.append(
            SemanticEvidence(
                kind=SemanticEvidenceKind.KEYWORD,
                label="intent_evidence",
                value=intent,
                score=score,
                source_text=message,
            )
        )

    return best_intent, best_score, evidence


# ============================================================
# SECTION 23 - CONFIDENCE CALCULATION
# ============================================================

def calculate_semantic_confidence(
    detected_player: str | None = None,
    detected_team: str | None = None,
    detected_outcome: str | None = None,
    detected_players: list[str] | None = None,
    detected_teams: list[str] | None = None,
) -> int:
    confidence = SEMANTIC_CONFIDENCE_MINIMUM

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
        SEMANTIC_CONFIDENCE_MAXIMUM,
    )


def calculate_fallback_confidence(
    *,
    intent_score: float,
    entity_candidates: Sequence[SemanticEntityCandidate],
    evidence: Sequence[SemanticEvidence],
    primary_route: PrimaryRouteState,
) -> float:
    entity_score = (
        sum(
            candidate.score
            for candidate in entity_candidates[:4]
        )
        / min(4, len(entity_candidates))
        if entity_candidates
        else 0.0
    )

    evidence_score = (
        sum(
            item.score
            for item in evidence[:8]
        )
        / min(8, len(evidence))
        if evidence
        else 0.0
    )

    primary_support = (
        primary_route.confidence
        if primary_route.intent
        else 0.0
    )

    result = (
        intent_score * 0.50
        + entity_score * 0.30
        + evidence_score * 0.15
        + primary_support * 0.05
    )

    return max(
        0.0,
        min(0.95, result),
    )


# ============================================================
# SECTION 24 - ENTITY MERGING
# ============================================================

def merge_entity_candidates(
    *candidate_groups: Sequence[SemanticEntityCandidate],
) -> list[SemanticEntityCandidate]:
    best_by_key: dict[
        tuple[str, str],
        SemanticEntityCandidate,
    ] = {}

    for group in candidate_groups:
        for candidate in group:
            key = (
                candidate.entity_type.value,
                normalize_text(
                    candidate.canonical_value
                ),
            )

            existing = best_by_key.get(key)

            if (
                existing is None
                or candidate.score > existing.score
            ):
                best_by_key[key] = candidate

    output = list(
        best_by_key.values()
    )

    output.sort(
        key=lambda item: item.score,
        reverse=True,
    )

    return output


# ============================================================
# SECTION 25 - AMBIGUITY ANALYSIS
# ============================================================

def mark_entity_ambiguity(
    candidates: list[SemanticEntityCandidate],
    *,
    margin: float,
) -> list[SemanticEntityCandidate]:
    grouped: dict[
        SemanticEntityType,
        list[SemanticEntityCandidate],
    ] = defaultdict(list)

    for candidate in candidates:
        grouped[
            candidate.entity_type
        ].append(candidate)

    for group in grouped.values():
        group.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        if len(group) < 2:
            continue

        if (
            group[0].score - group[1].score
            < margin
        ):
            group[0].ambiguous = True
            group[1].ambiguous = True

            group[0].alternatives.append(
                group[1].to_dict()
            )
            group[1].alternatives.append(
                group[0].to_dict()
            )

    return candidates


# ============================================================
# SECTION 26 - CLARIFICATION POLICY
# ============================================================

def build_clarification_question(
    *,
    recommended_intent: str | None,
    players: Sequence[str],
    teams: Sequence[str],
    outcomes: Sequence[str],
    ambiguous_candidates: Sequence[SemanticEntityCandidate],
) -> str | None:
    if ambiguous_candidates:
        names = unique_preserving_order(
            candidate.canonical_value
            for candidate in ambiguous_candidates
        )

        if len(names) >= 2:
            return (
                "Which did you mean: "
                + ", ".join(names[:3])
                + "?"
            )

    if recommended_intent == SemanticIntentFamily.PLAYER_PROBABILITY.value:
        if not players:
            return (
                "Which player should I evaluate?"
            )

        if not outcomes:
            return (
                "Which outcome should I predict for "
                f"{players[0]}?"
            )

    if recommended_intent == SemanticIntentFamily.ROSTER.value:
        if not teams:
            return (
                "Which team roster should I open?"
            )

    if recommended_intent == SemanticIntentFamily.TEAM_INFO.value:
        if not teams:
            return (
                "Which MLB team should I analyze?"
            )

    if recommended_intent == SemanticIntentFamily.PLAYER_INFO.value:
        if not players:
            return (
                "Which player should I search for?"
            )

    return None


# ============================================================
# SECTION 27 - FALLBACK ANALYZER
# ============================================================

def analyze_semantic_fallback(
    message: str,
    *,
    primary_route: Mapping[str, Any] | PrimaryRouteState | None = None,
    teams: Mapping[str, Any] | None = None,
    player_profiles: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
    config: SemanticFallbackConfig | None = None,
) -> dict[str, Any]:
    config = config or SemanticFallbackConfig()
    config.validate()

    primary_state = (
        primary_route
        if isinstance(primary_route, PrimaryRouteState)
        else PrimaryRouteState.from_mapping(
            primary_route
        )
    )

    activation = (
        decide_semantic_fallback_activation(
            primary_state,
            config=config,
        )
    )

    normalized_message = normalize_text(
        message
    )

    if (
        activation
        == SemanticActivationDecision.SKIP_PRIMARY_ACCEPTED
    ):
        result = SemanticFallbackResult(
            message=message,
            normalized_message=normalized_message,
            activation_decision=activation,
            status=SemanticAnalysisStatus.SKIPPED,
            primary_route=primary_state,
            primary_route_preserved=True,
            recommended_intent=primary_state.intent,
            recommended_confidence=(
                primary_state.confidence
            ),
            player=primary_state.player,
            team=primary_state.team,
            outcome=primary_state.outcome,
            players=list(primary_state.players),
            teams=list(primary_state.teams),
            outcomes=list(primary_state.outcomes),
            risk_flags=[
                SemanticRiskFlag.FALLBACK_ONLY,
            ],
            diagnostics={
                "reason": (
                    "primary router already accepted the route"
                ),
                "semantic_analysis_executed": False,
            },
        )

        return result.to_dict()

    exact_players = (
        detect_player_candidates(
            message,
            player_profiles,
            max_candidates=(
                config.max_entity_candidates
            ),
        )
        if config.enable_player_detection
        else []
    )

    exact_teams = (
        detect_team_candidates(
            message,
            teams,
            max_candidates=(
                config.max_entity_candidates
            ),
        )
        if config.enable_team_detection
        else []
    )

    outcome_candidates = (
        detect_outcome_candidates(message)
        if config.enable_outcome_detection
        else []
    )

    fuzzy_candidates = (
        apply_fuzzy_semantic_support(
            message,
            player_profiles=player_profiles,
            teams=teams,
            config=config,
        )
        if config.enable_fuzzy_support
        else []
    )

    all_candidates = merge_entity_candidates(
        exact_players,
        exact_teams,
        outcome_candidates,
        fuzzy_candidates,
    )

    all_candidates = mark_entity_ambiguity(
        all_candidates,
        margin=config.ambiguity_margin,
    )

    players = unique_preserving_order(
        [
            primary_state.player,
            *primary_state.players,
            *[
                candidate.canonical_value
                for candidate in all_candidates
                if candidate.entity_type
                == SemanticEntityType.PLAYER
            ],
        ]
    )

    teams_found = unique_preserving_order(
        [
            primary_state.team,
            *primary_state.teams,
            *[
                candidate.canonical_value
                for candidate in all_candidates
                if candidate.entity_type
                == SemanticEntityType.TEAM
            ],
        ]
    )

    outcomes = unique_preserving_order(
        [
            primary_state.outcome,
            *primary_state.outcomes,
            *[
                candidate.canonical_value
                for candidate in all_candidates
                if candidate.entity_type
                == SemanticEntityType.OUTCOME
            ],
        ]
    )

    recommended_intent, intent_score, evidence = (
        recommend_fallback_intent(
            message,
            players=players,
            teams=teams_found,
            outcomes=outcomes,
            primary_route=primary_state,
        )
    )

    for candidate in all_candidates:
        evidence.append(
            SemanticEvidence(
                kind=SemanticEvidenceKind.ENTITY,
                label=candidate.entity_type.value,
                value=candidate.canonical_value,
                score=candidate.score,
                source_text=candidate.observed_value,
                metadata={
                    "source": candidate.source,
                },
            )
        )

    temporal_references = (
        detect_temporal_references(message)
        if config.enable_temporal_detection
        else []
    )

    for reference in temporal_references:
        evidence.append(
            SemanticEvidence(
                kind=SemanticEvidenceKind.TEMPORAL,
                label="temporal_reference",
                value=reference,
                score=0.80,
                source_text=message,
            )
        )

    numeric_constraints = (
        detect_numeric_constraints(message)
        if config.enable_constraint_detection
        else []
    )

    for constraint in numeric_constraints:
        evidence.append(
            SemanticEvidence(
                kind=SemanticEvidenceKind.QUANTIFIER,
                label="numeric_constraint",
                value=constraint,
                score=0.88,
                source_text=constraint[
                    "source_text"
                ],
            )
        )

    if detect_negation(message):
        evidence.append(
            SemanticEvidence(
                kind=SemanticEvidenceKind.NEGATION,
                label="negation",
                value=True,
                score=0.80,
                source_text=message,
            )
        )

    ambiguous_candidates = [
        candidate
        for candidate in all_candidates
        if candidate.ambiguous
    ]

    fallback_confidence = (
        calculate_fallback_confidence(
            intent_score=intent_score,
            entity_candidates=all_candidates,
            evidence=evidence,
            primary_route=primary_state,
        )
    )

    risk_flags = [
        SemanticRiskFlag.FALLBACK_ONLY,
    ]

    if not all_candidates:
        risk_flags.append(
            SemanticRiskFlag.LOW_EVIDENCE
        )

    if ambiguous_candidates:
        risk_flags.append(
            SemanticRiskFlag.AMBIGUOUS_ENTITY
        )

    if primary_state.missing_required_entities:
        risk_flags.append(
            SemanticRiskFlag.MISSING_REQUIRED_ENTITY
        )

    if (
        primary_state.intent
        and recommended_intent
        and primary_state.intent != recommended_intent
    ):
        risk_flags.append(
            SemanticRiskFlag.PRIMARY_ROUTE_CONFLICT
        )

    clarification_question = (
        build_clarification_question(
            recommended_intent=recommended_intent,
            players=players,
            teams=teams_found,
            outcomes=outcomes,
            ambiguous_candidates=ambiguous_candidates,
        )
    )

    clarification_required = bool(
        clarification_question
    )

    if clarification_required:
        status = (
            SemanticAnalysisStatus.NEEDS_CLARIFICATION
        )

    elif recommended_intent:
        status = (
            SemanticAnalysisStatus.FALLBACK_RECOMMENDATION
        )

    elif all_candidates:
        status = (
            SemanticAnalysisStatus.ENRICHED
        )

    else:
        status = (
            SemanticAnalysisStatus.UNRESOLVED
        )

    preserved_intent = (
        primary_state.intent
        if (
            config.preserve_primary_intent
            and primary_state.intent
        )
        else recommended_intent
    )

    result = SemanticFallbackResult(
        message=message,
        normalized_message=normalized_message,
        activation_decision=activation,
        status=status,
        primary_route=primary_state,
        primary_route_preserved=True,
        recommended_intent=preserved_intent,
        recommended_confidence=fallback_confidence,
        player=(
            players[0]
            if players
            else None
        ),
        team=(
            teams_found[0]
            if teams_found
            else None
        ),
        outcome=(
            outcomes[0]
            if outcomes
            else None
        ),
        players=players,
        teams=teams_found,
        outcomes=outcomes,
        entity_candidates=all_candidates,
        evidence=evidence[
            :config.max_evidence_items
        ],
        risk_flags=unique_risk_flags(
            risk_flags
        ),
        clarification_required=(
            clarification_required
        ),
        clarification_question=(
            clarification_question
        ),
        diagnostics={
            "semantic_analysis_executed": True,
            "primary_intent": primary_state.intent,
            "fallback_intent_candidate": (
                recommended_intent
            ),
            "returned_intent": preserved_intent,
            "primary_override_attempted": False,
            "primary_override_allowed": False,
            "temporal_references": (
                temporal_references
            ),
            "numeric_constraints": (
                numeric_constraints
            ),
            "context_available": bool(context),
            "candidate_count": len(
                all_candidates
            ),
        },
    )

    return result.to_dict()


# ============================================================
# SECTION 28 - RISK UTILITIES
# ============================================================

def unique_risk_flags(
    values: Iterable[SemanticRiskFlag],
) -> list[SemanticRiskFlag]:
    output: list[SemanticRiskFlag] = []
    seen: set[str] = set()

    for value in values:
        key = value.value

        if key in seen:
            continue

        seen.add(key)
        output.append(value)

    return output


# ============================================================
# SECTION 29 - LEGACY GENERAL INTENT DETECTOR
# ============================================================

def detect_general_intent(
    message: str,
) -> str:
    scores = score_intent_evidence(
        message
    )

    ranked = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    if not ranked or ranked[0][1] <= 0:
        return (
            SemanticIntentFamily.GENERAL_BASEBALL.value
        )

    return ranked[0][0]


# ============================================================
# SECTION 30 - BACKWARD-COMPATIBLE INTERPRETER
# ============================================================

def interpret_baseball_question(
    message: str,
    teams: Mapping[str, Any],
    player_profiles: Mapping[str, Any],
) -> dict[str, Any]:
    fallback = analyze_semantic_fallback(
        message,
        primary_route={
            "unresolved": True,
            "fallback_requested": True,
            "confidence": 0.0,
        },
        teams=teams,
        player_profiles=player_profiles,
    )

    confidence_percent = int(
        round(
            fallback[
                "recommended_confidence"
            ]
            * 100
        )
    )

    return {
        "message": message,
        "intent": (
            fallback["recommended_intent"]
            or SemanticIntentFamily.GENERAL_BASEBALL.value
        ),
        "confidence": confidence_percent,
        "player": fallback["player"],
        "team": fallback["team"],
        "outcome": fallback["outcome"],
        "players": fallback["players"],
        "teams": fallback["teams"],
        "outcomes": fallback["outcomes"],
        "semantic_role": SEMANTIC_ENGINE_ROLE,
        "fallback_only": True,
        "primary_override_allowed": False,
        "activation_decision": (
            fallback["activation_decision"]
        ),
        "status": fallback["status"],
        "clarification_required": (
            fallback[
                "clarification_required"
            ]
        ),
        "clarification_question": (
            fallback[
                "clarification_question"
            ]
        ),
        "diagnostics": fallback[
            "diagnostics"
        ],
    }


# ============================================================
# SECTION 31 - PRIMARY ROUTER MERGE CONTRACT
# ============================================================

def merge_semantic_fallback_with_primary(
    primary_result: Mapping[str, Any],
    fallback_result: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(primary_result)

    primary_state = (
        PrimaryRouteState.from_mapping(
            primary_result
        )
    )

    fallback_intent = fallback_result.get(
        "recommended_intent"
    )

    if primary_state.intent:
        merged["intent"] = primary_state.intent

    elif fallback_intent:
        merged["intent"] = fallback_intent

    merged["semantic_fallback"] = dict(
        fallback_result
    )

    merged["semantic_fallback_used"] = (
        fallback_result.get("status")
        != SemanticAnalysisStatus.SKIPPED.value
    )

    merged["semantic_primary_preserved"] = True
    merged["semantic_override_allowed"] = False

    for singular, plural in (
        ("player", "players"),
        ("team", "teams"),
        ("outcome", "outcomes"),
    ):
        if not merged.get(singular):
            merged[singular] = fallback_result.get(
                singular
            )

        primary_values = list(
            merged.get(plural)
            or []
        )
        fallback_values = list(
            fallback_result.get(plural)
            or []
        )

        merged[plural] = (
            unique_preserving_order(
                [
                    *primary_values,
                    *fallback_values,
                ]
            )
        )

    return merged


# ============================================================
# SECTION 32 - HEALTH REPORT
# ============================================================

def semantic_engine_health(
) -> dict[str, Any]:
    validation = (
        validate_semantic_engine_module()
    )

    return {
        "name": SEMANTIC_ENGINE_NAME,
        "version": SEMANTIC_ENGINE_VERSION,
        "phase": SEMANTIC_ENGINE_PHASE,
        "path": SEMANTIC_ENGINE_PATH,
        "status": (
            SEMANTIC_ENGINE_STATUS
            if validation["status"] == "ok"
            else "validation_failed"
        ),
        "role": SEMANTIC_ENGINE_ROLE,
        "primary_router": (
            SEMANTIC_ENGINE_PRIMARY_ROUTER
        ),
        "can_override_primary": False,
        "can_enrich_primary": True,
        "fallback_activation_policy": True,
        "ambiguity_detection": True,
        "clarification_policy": True,
        "fuzzy_support_adapter": True,
        "backward_compatible_api": True,
        "validation": validation,
        "timestamp": datetime.now(
            UTC
        ).isoformat(),
    }


# ============================================================
# SECTION 33 - VALIDATION
# ============================================================

def validate_semantic_engine_module(
) -> dict[str, Any]:
    teams = {
        "New York Yankees": {
            "id": 147,
            "abbreviation": "NYY",
            "club_name": "Yankees",
        },
        "Boston Red Sox": {
            "id": 111,
            "abbreviation": "BOS",
            "club_name": "Red Sox",
        },
    }

    players = {
        "Aaron Judge": {
            "id": 592450,
            "first_name": "Aaron",
            "last_name": "Judge",
        },
        "Shohei Ohtani": {
            "id": 660271,
            "first_name": "Shohei",
            "last_name": "Ohtani",
        },
    }

    checks: dict[str, bool] = {}

    accepted_primary = (
        analyze_semantic_fallback(
            "show Aaron Judge stats",
            primary_route={
                "intent": "player_stats",
                "confidence": 0.95,
                "accepted": True,
                "player": "Aaron Judge",
            },
            teams=teams,
            player_profiles=players,
        )
    )

    checks[
        "accepted_primary_is_skipped"
    ] = (
        accepted_primary["status"]
        == SemanticAnalysisStatus.SKIPPED.value
    )

    checks[
        "accepted_primary_intent_preserved"
    ] = (
        accepted_primary[
            "recommended_intent"
        ]
        == "player_stats"
    )

    unresolved = analyze_semantic_fallback(
        "what is the chance Aaron Judge hits a home run",
        primary_route={
            "unresolved": True,
            "confidence": 0.20,
        },
        teams=teams,
        player_profiles=players,
    )

    checks[
        "unresolved_primary_activates_fallback"
    ] = (
        unresolved["status"]
        != SemanticAnalysisStatus.SKIPPED.value
    )

    checks[
        "player_probability_recommended"
    ] = (
        unresolved["recommended_intent"]
        == SemanticIntentFamily.PLAYER_PROBABILITY.value
    )

    checks[
        "player_detected"
    ] = (
        unresolved["player"]
        == "Aaron Judge"
    )

    checks[
        "outcome_detected"
    ] = (
        unresolved["outcome"]
        == "home_run"
    )

    roster = analyze_semantic_fallback(
        "show the Yankees roster",
        primary_route={
            "fallback_requested": True,
            "confidence": 0.40,
        },
        teams=teams,
        player_profiles=players,
    )

    checks["team_detected"] = (
        roster["team"]
        == "New York Yankees"
    )

    checks["roster_intent_detected"] = (
        roster["recommended_intent"]
        == SemanticIntentFamily.ROSTER.value
    )

    comparison = (
        analyze_semantic_fallback(
            "compare Aaron Judge and Shohei Ohtani",
            primary_route={
                "unresolved": True,
                "confidence": 0.15,
            },
            teams=teams,
            player_profiles=players,
        )
    )

    checks[
        "multiple_players_detected"
    ] = (
        "Aaron Judge"
        in comparison["players"]
        and "Shohei Ohtani"
        in comparison["players"]
    )

    checks[
        "comparison_intent_detected"
    ] = (
        comparison[
            "recommended_intent"
        ]
        == SemanticIntentFamily.COMPARE_PLAYERS.value
    )

    preservation_test = (
        analyze_semantic_fallback(
            "show Yankees roster",
            primary_route={
                "intent": "custom_primary_route",
                "confidence": 0.30,
                "accepted": False,
                "fallback_requested": True,
            },
            teams=teams,
            player_profiles=players,
        )
    )

    checks[
        "low_confidence_primary_intent_preserved"
    ] = (
        preservation_test[
            "recommended_intent"
        ]
        == "custom_primary_route"
    )

    merged = (
        merge_semantic_fallback_with_primary(
            {
                "intent": "primary_route",
                "confidence": 0.55,
            },
            roster,
        )
    )

    checks[
        "merge_never_replaces_primary_intent"
    ] = (
        merged["intent"]
        == "primary_route"
    )

    legacy = interpret_baseball_question(
        "show the Yankees roster",
        teams,
        players,
    )

    checks[
        "legacy_interpreter_operational"
    ] = (
        legacy["team"]
        == "New York Yankees"
    )

    checks[
        "override_flag_is_false"
    ] = (
        SEMANTIC_ENGINE_CAN_OVERRIDE_PRIMARY
        is False
    )

    checks[
        "configuration_rejects_override"
    ] = False

    try:
        SemanticFallbackConfig(
            allow_primary_override=True
        ).validate()
    except ValueError:
        checks[
            "configuration_rejects_override"
        ] = True

    passed = sum(
        1
        for value in checks.values()
        if value
    )

    return {
        "status": (
            "ok"
            if passed == len(checks)
            else "failed"
        ),
        "engine": SEMANTIC_ENGINE_NAME,
        "version": SEMANTIC_ENGINE_VERSION,
        "phase": SEMANTIC_ENGINE_PHASE,
        "role": SEMANTIC_ENGINE_ROLE,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "failed_checks": [
            name
            for name, value
            in checks.items()
            if not value
        ],
    }


# ============================================================
# SECTION 34 - ENGINE CONFIGURATION EXPORT
# ============================================================

SEMANTIC_ENGINE_CONFIGURATION: Final[
    dict[str, Any]
] = {
    "engine_name": SEMANTIC_ENGINE_NAME,
    "engine_version": SEMANTIC_ENGINE_VERSION,
    "engine_phase": SEMANTIC_ENGINE_PHASE,
    "engine_role": SEMANTIC_ENGINE_ROLE,
    "primary_router": SEMANTIC_ENGINE_PRIMARY_ROUTER,
    "fallback_only": True,
    "can_override_primary": False,
    "can_enrich_primary": True,
    "activation_policy_enabled": True,
    "team_detection_enabled": True,
    "player_detection_enabled": True,
    "outcome_detection_enabled": True,
    "comparison_detection_enabled": True,
    "temporal_detection_enabled": True,
    "constraint_detection_enabled": True,
    "fuzzy_support_enabled": True,
    "clarification_policy_enabled": True,
    "minimum_confidence": (
        SEMANTIC_CONFIDENCE_MINIMUM
    ),
}


# ============================================================
# SECTION 35 - FINGERPRINT
# ============================================================

def semantic_fingerprint(
    payload: Any,
) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    return sha256(
        canonical.encode("utf-8")
    ).hexdigest()


# ============================================================
# SECTION 36 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "SEMANTIC_ENGINE_NAME",
    "SEMANTIC_ENGINE_VERSION",
    "SEMANTIC_ENGINE_PHASE",
    "SEMANTIC_ENGINE_PATH",
    "SEMANTIC_ENGINE_STATUS",
    "SEMANTIC_SCHEMA_VERSION",
    "SEMANTIC_ENGINE_ROLE",
    "SEMANTIC_ENGINE_PRIMARY_ROUTER",
    "SEMANTIC_ENGINE_CAN_OVERRIDE_PRIMARY",
    "SEMANTIC_ENGINE_CAN_ENRICH_PRIMARY",

    "SEMANTIC_CONFIDENCE_MINIMUM",
    "SEMANTIC_CONFIDENCE_WEAK",
    "SEMANTIC_CONFIDENCE_STANDARD",
    "SEMANTIC_CONFIDENCE_STRONG",
    "SEMANTIC_CONFIDENCE_HIGH",
    "SEMANTIC_CONFIDENCE_MAXIMUM",

    "SemanticActivationDecision",
    "SemanticAnalysisStatus",
    "SemanticEvidenceKind",
    "SemanticIntentFamily",
    "SemanticEntityType",
    "SemanticRiskFlag",

    "SemanticFallbackConfig",
    "PrimaryRouteState",
    "SemanticEvidence",
    "SemanticEntityCandidate",
    "SemanticFallbackResult",

    "OUTCOME_KEYWORDS",
    "HITTING_OUTCOMES",
    "PITCHING_OUTCOMES",
    "BASERUNNING_OUTCOMES",
    "TEAM_ALIASES",
    "INTENT_EVIDENCE",
    "TEMPORAL_KEYWORDS",

    "normalize_text",
    "tokenize_text",
    "contains_phrase",
    "contains_any_keyword",
    "unique_preserving_order",
    "coerce_confidence",

    "decide_semantic_fallback_activation",
    "detect_team_candidates",
    "detect_teams",
    "detect_team",
    "detect_player_candidates",
    "detect_players",
    "detect_player",
    "apply_fuzzy_semantic_support",
    "detect_outcome_candidates",
    "detect_outcomes",
    "detect_outcome",
    "detect_temporal_references",
    "detect_numeric_constraints",
    "detect_comparison_request",
    "detect_negation",
    "score_intent_evidence",
    "recommend_fallback_intent",
    "calculate_semantic_confidence",
    "calculate_fallback_confidence",
    "merge_entity_candidates",
    "mark_entity_ambiguity",
    "build_clarification_question",
    "analyze_semantic_fallback",
    "unique_risk_flags",
    "detect_general_intent",
    "interpret_baseball_question",
    "merge_semantic_fallback_with_primary",
    "semantic_engine_health",
    "validate_semantic_engine_module",
    "SEMANTIC_ENGINE_CONFIGURATION",
    "semantic_fingerprint",
]


# ============================================================
# SECTION 37 - LOCAL VALIDATION ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    print(
        json.dumps(
            semantic_engine_health(),
            indent=2,
            sort_keys=True,
        )
    )
