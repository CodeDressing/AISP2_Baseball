# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# PHASE 10 PART 13.0
# FILE: 04_ai/nlp/context_builder.py
# PURPOSE:
# Enterprise multi-turn conversation context management for
# baseball chat routing, follow-up resolution, subject memory,
# pronoun handling, entity override behavior, diagnostics,
# expiration, reset, serialization, and downstream NLU support.
# ============================================================

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from dataclasses import is_dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from enum import Enum
from hashlib import sha256
import json
import re
import unicodedata
from typing import Any
from typing import Iterable
from typing import Mapping
from typing import MutableMapping
from typing import Sequence
from uuid import uuid4


# ============================================================
# SECTION 02 - ENGINE METADATA
# ============================================================

CONTEXT_ENGINE_NAME = "AISP2 Enterprise Baseball Context Builder"
CONTEXT_ENGINE_VERSION = "5.0.0"
CONTEXT_ENGINE_PHASE = "Phase 10 Part 13.0"
CONTEXT_ENGINE_PATH = "04_ai/nlp/context_builder.py"
CONTEXT_ENGINE_STATUS = "enterprise_ready"
CONTEXT_SCHEMA_VERSION = "1.0.0"


# ============================================================
# SECTION 03 - TASK CONSTANTS
# ============================================================

TASK_GENERAL_CHAT = "general_chat"
TASK_HELP = "help"

TASK_TEAM_LOOKUP = "team_lookup"
TASK_PLAYER_LOOKUP = "player_lookup"
TASK_ROSTER_LOOKUP = "roster_lookup"
TASK_SCHEDULE_LOOKUP = "schedule_lookup"
TASK_GAME_LOOKUP = "game_lookup"

TASK_PLAYER_STATS = "player_stats"
TASK_TEAM_STATS = "team_stats"
TASK_STAT_REQUEST = "stat_request"

TASK_PLAYER_PROBABILITY = "player_probability"
TASK_TEAM_PROBABILITY = "team_probability"
TASK_GAME_PROBABILITY = "game_probability"
TASK_BEST_TEAM_PROBABILITY = "best_team_probability"
TASK_GENERAL_PROBABILITY = "general_probability"

TASK_PLAYER_COMPARISON = "player_comparison"
TASK_TEAM_COMPARISON = "team_comparison"
TASK_MATCHUP_ANALYSIS = "matchup_analysis"

TASK_DATABASE_STATUS = "database_status"
TASK_WAREHOUSE_STATUS = "warehouse_status"
TASK_MODEL_STATUS = "model_status"
TASK_DATA_SOURCE_STATUS = "data_source_status"
TASK_EXPLAIN_MODEL = "explain_model"

TASK_CLARIFICATION = "clarification_required"
TASK_UNKNOWN = "unknown"


# ============================================================
# SECTION 04 - CONTEXT COMPLETENESS CONSTANTS
# ============================================================

CONTEXT_EMPTY = "empty"
CONTEXT_PARTIAL = "partial"
CONTEXT_COMPLETE = "complete"
CONTEXT_MULTI_ENTITY = "multi_entity"
CONTEXT_AMBIGUOUS = "ambiguous"
CONTEXT_EXPIRED = "expired"
CONTEXT_RESET = "reset"


# ============================================================
# SECTION 05 - CONFIDENCE CONSTANTS
# ============================================================

CONTEXT_CONFIDENCE_MINIMUM = 0.35
CONTEXT_CONFIDENCE_WEAK = 0.50
CONTEXT_CONFIDENCE_STANDARD = 0.65
CONTEXT_CONFIDENCE_STRONG = 0.80
CONTEXT_CONFIDENCE_HIGH = 0.90
CONTEXT_CONFIDENCE_MAXIMUM = 0.98


# ============================================================
# SECTION 06 - ENUMERATIONS
# ============================================================

class ContextSource(str, Enum):
    CURRENT_EXPLICIT = "current_explicit"
    CURRENT_INFERRED = "current_inferred"
    CURRENT_SEMANTIC = "current_semantic"
    PREVIOUS_CONTEXT = "previous_context"
    RESET = "reset"
    NONE = "none"


class ContextAction(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    REUSED = "reused"
    OVERRIDDEN = "overridden"
    IGNORED = "ignored"
    RESET = "reset"
    EXPIRED = "expired"


class FollowUpType(str, Enum):
    NONE = "none"
    PRONOUN = "pronoun"
    ELLIPTICAL = "elliptical"
    CONTINUATION = "continuation"
    CORRECTION = "correction"
    RESET = "reset"


class ContextStatus(str, Enum):
    EMPTY = CONTEXT_EMPTY
    PARTIAL = CONTEXT_PARTIAL
    COMPLETE = CONTEXT_COMPLETE
    MULTI_ENTITY = CONTEXT_MULTI_ENTITY
    AMBIGUOUS = CONTEXT_AMBIGUOUS
    EXPIRED = CONTEXT_EXPIRED
    RESET = CONTEXT_RESET


# ============================================================
# SECTION 07 - CORE DATA CONTRACTS
# ============================================================

@dataclass(slots=True)
class ContextEntity:
    entity_type: str
    entity_id: int | str | None = None
    canonical_name: str | None = None
    matched_text: str | None = None
    source: ContextSource = ContextSource.NONE
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "canonical_name": self.canonical_name,
            "matched_text": self.matched_text,
            "source": self.source.value,
            "confidence": round(float(self.confidence), 6),
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class ConversationMemory:
    conversation_id: str = field(default_factory=lambda: str(uuid4()))

    last_player_id: int | str | None = None
    last_player_name: str | None = None

    last_team_id: int | str | None = None
    last_team_name: str | None = None

    last_game_id: int | str | None = None
    last_game_label: str | None = None

    last_statistic: str | None = None
    last_outcome: str | None = None
    last_opponent_id: int | str | None = None
    last_opponent_name: str | None = None
    last_date: str | None = None
    last_season: int | None = None

    last_intent: str | None = None
    last_task: str | None = None
    last_scope: str | None = None

    last_message: str | None = None
    last_normalized_message: str | None = None

    turn_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_any(cls, value: Any) -> "ConversationMemory":
        if value is None:
            return cls()

        if isinstance(value, cls):
            return value

        if is_dataclass(value):
            value = asdict(value)

        if not isinstance(value, Mapping):
            return cls()

        created_at = parse_datetime(value.get("created_at")) or datetime.now(UTC)
        updated_at = parse_datetime(value.get("updated_at")) or created_at
        expires_at = parse_datetime(value.get("expires_at"))

        return cls(
            conversation_id=str(
                value.get("conversation_id")
                or value.get("session_id")
                or uuid4()
            ),
            last_player_id=value.get("last_player_id"),
            last_player_name=value.get("last_player_name"),
            last_team_id=value.get("last_team_id"),
            last_team_name=value.get("last_team_name"),
            last_game_id=value.get("last_game_id"),
            last_game_label=value.get("last_game_label"),
            last_statistic=value.get("last_statistic"),
            last_outcome=value.get("last_outcome"),
            last_opponent_id=value.get("last_opponent_id"),
            last_opponent_name=value.get("last_opponent_name"),
            last_date=value.get("last_date"),
            last_season=_coerce_optional_int(value.get("last_season")),
            last_intent=value.get("last_intent"),
            last_task=value.get("last_task"),
            last_scope=value.get("last_scope"),
            last_message=value.get("last_message"),
            last_normalized_message=value.get("last_normalized_message"),
            turn_count=_coerce_non_negative_int(value.get("turn_count")),
            created_at=created_at,
            updated_at=updated_at,
            expires_at=expires_at,
            metadata=dict(value.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "last_player_id": self.last_player_id,
            "last_player_name": self.last_player_name,
            "last_team_id": self.last_team_id,
            "last_team_name": self.last_team_name,
            "last_game_id": self.last_game_id,
            "last_game_label": self.last_game_label,
            "last_statistic": self.last_statistic,
            "last_outcome": self.last_outcome,
            "last_opponent_id": self.last_opponent_id,
            "last_opponent_name": self.last_opponent_name,
            "last_date": self.last_date,
            "last_season": self.last_season,
            "last_intent": self.last_intent,
            "last_task": self.last_task,
            "last_scope": self.last_scope,
            "last_message": self.last_message,
            "last_normalized_message": self.last_normalized_message,
            "turn_count": self.turn_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": (
                self.expires_at.isoformat()
                if self.expires_at
                else None
            ),
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class ContextResolution:
    follow_up_type: FollowUpType = FollowUpType.NONE
    context_used: bool = False
    context_reset: bool = False
    context_expired: bool = False

    player_from_context: bool = False
    team_from_context: bool = False
    statistic_from_context: bool = False
    outcome_from_context: bool = False
    game_from_context: bool = False
    opponent_from_context: bool = False
    date_from_context: bool = False
    season_from_context: bool = False

    current_player_overrode_previous: bool = False
    current_team_overrode_previous: bool = False
    current_game_overrode_previous: bool = False
    current_statistic_overrode_previous: bool = False
    current_outcome_overrode_previous: bool = False

    previous_intent_used_for_classification: bool = False
    previous_intent_preserved_for_diagnostics_only: bool = True

    reasons: list[str] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        action: ContextAction,
        field_name: str,
        reason: str,
        previous_value: Any = None,
        current_value: Any = None,
    ) -> None:
        self.actions.append({
            "action": action.value,
            "field": field_name,
            "reason": reason,
            "previous_value": previous_value,
            "current_value": current_value,
        })
        self.reasons.append(reason)

    def to_dict(self) -> dict[str, Any]:
        return {
            "follow_up_type": self.follow_up_type.value,
            "context_used": self.context_used,
            "context_reset": self.context_reset,
            "context_expired": self.context_expired,
            "player_from_context": self.player_from_context,
            "team_from_context": self.team_from_context,
            "statistic_from_context": self.statistic_from_context,
            "outcome_from_context": self.outcome_from_context,
            "game_from_context": self.game_from_context,
            "opponent_from_context": self.opponent_from_context,
            "date_from_context": self.date_from_context,
            "season_from_context": self.season_from_context,
            "current_player_overrode_previous": self.current_player_overrode_previous,
            "current_team_overrode_previous": self.current_team_overrode_previous,
            "current_game_overrode_previous": self.current_game_overrode_previous,
            "current_statistic_overrode_previous": self.current_statistic_overrode_previous,
            "current_outcome_overrode_previous": self.current_outcome_overrode_previous,
            "previous_intent_used_for_classification": (
                self.previous_intent_used_for_classification
            ),
            "previous_intent_preserved_for_diagnostics_only": (
                self.previous_intent_preserved_for_diagnostics_only
            ),
            "reasons": list(self.reasons),
            "actions": list(self.actions),
        }


@dataclass(slots=True)
class ContextBuildResult:
    request_id: str
    message: str
    normalized_message: str

    task: str
    intent: str
    scope: str | None

    confidence: float
    confidence_percent: int
    status: ContextStatus

    player: ContextEntity | None
    team: ContextEntity | None
    game: ContextEntity | None
    statistic: ContextEntity | None
    outcome: ContextEntity | None
    opponent: ContextEntity | None
    date: ContextEntity | None
    season: ContextEntity | None

    players: list[ContextEntity]
    teams: list[ContextEntity]

    resolution: ContextResolution
    previous_memory: ConversationMemory
    next_memory: ConversationMemory

    clarification_required: bool = False
    clarification_reason: str | None = None
    clarification_prompt: str | None = None

    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "message": self.message,
            "normalized_message": self.normalized_message,
            "task": self.task,
            "intent": self.intent,
            "scope": self.scope,
            "confidence": round(float(self.confidence), 6),
            "confidence_percent": self.confidence_percent,
            "status": self.status.value,
            "player": self.player.to_dict() if self.player else None,
            "team": self.team.to_dict() if self.team else None,
            "game": self.game.to_dict() if self.game else None,
            "statistic": self.statistic.to_dict() if self.statistic else None,
            "outcome": self.outcome.to_dict() if self.outcome else None,
            "opponent": self.opponent.to_dict() if self.opponent else None,
            "date": self.date.to_dict() if self.date else None,
            "season": self.season.to_dict() if self.season else None,
            "players": [item.to_dict() for item in self.players],
            "teams": [item.to_dict() for item in self.teams],
            "resolution": self.resolution.to_dict(),
            "context_used": self.resolution.context_used,
            "previous_memory": self.previous_memory.to_dict(),
            "next_memory": self.next_memory.to_dict(),
            "clarification_required": self.clarification_required,
            "clarification_reason": self.clarification_reason,
            "clarification_prompt": self.clarification_prompt,
            "diagnostics": dict(self.diagnostics),
            "engine": {
                "name": CONTEXT_ENGINE_NAME,
                "version": CONTEXT_ENGINE_VERSION,
                "phase": CONTEXT_ENGINE_PHASE,
                "path": CONTEXT_ENGINE_PATH,
                "schema_version": CONTEXT_SCHEMA_VERSION,
            },
        }


# ============================================================
# SECTION 08 - CONFIGURATION
# ============================================================

@dataclass(slots=True)
class ContextConfig:
    enable_memory: bool = True
    enable_pronoun_resolution: bool = True
    enable_ellipsis_resolution: bool = True
    enable_context_expiration: bool = True

    context_ttl_hours: float = 24.0
    minimum_entity_confidence: float = 0.35
    minimum_context_reuse_confidence: float = 0.65
    ambiguity_margin: float = 0.08

    preserve_player_when_team_named: bool = False
    preserve_team_when_player_named: bool = True
    preserve_previous_intent_for_diagnostics: bool = True

    require_followup_signal_for_context_reuse: bool = True
    allow_statistic_context_reuse: bool = True
    allow_outcome_context_reuse: bool = True
    allow_game_context_reuse: bool = True
    allow_date_context_reuse: bool = True
    allow_season_context_reuse: bool = True

    def validate(self) -> None:
        probability_fields = (
            "minimum_entity_confidence",
            "minimum_context_reuse_confidence",
            "ambiguity_margin",
        )

        for field_name in probability_fields:
            value = float(getattr(self, field_name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        if self.context_ttl_hours < 0:
            raise ValueError(
                "context_ttl_hours cannot be negative"
            )


DEFAULT_CONTEXT_CONFIG = ContextConfig()


# ============================================================
# SECTION 09 - NORMALIZATION
# ============================================================

WHITESPACE_PATTERN = re.compile(r"\s+")
NON_WORD_PATTERN = re.compile(r"[^a-z0-9+.%'\-/\s]")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:\+[a-z0-9]+)?")


def normalize_context_text(value: str | None) -> str:
    if not value:
        return ""

    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("’", "'")
    text = text.lower().strip()

    replacements = {
        "what's": "what is",
        "whats": "what is",
        "who's": "who is",
        "cant": "cannot",
        "wont": "will not",
        "won't": "will not",
        "doesnt": "does not",
        "isnt": "is not",
        "arent": "are not",
        "homerun": "home run",
        "home-run": "home run",
        "stat cast": "statcast",
    }

    for source, target in replacements.items():
        text = text.replace(source, target)

    text = NON_WORD_PATTERN.sub(" ", text)
    text = text.replace("/", " ")
    text = WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()


def tokenize_context_text(value: str | None) -> list[str]:
    return TOKEN_PATTERN.findall(normalize_context_text(value))


def context_contains_phrase(
    message: str,
    phrase: str,
) -> bool:
    normalized_message = normalize_context_text(message)
    normalized_phrase = normalize_context_text(phrase)

    if not normalized_message or not normalized_phrase:
        return False

    pattern = (
        rf"(?<![a-z0-9])"
        rf"{re.escape(normalized_phrase)}"
        rf"(?![a-z0-9])"
    )
    return re.search(pattern, normalized_message) is not None


def context_contains_any(
    message: str,
    phrases: Sequence[str],
) -> bool:
    return any(
        context_contains_phrase(message, phrase)
        for phrase in phrases
    )


# ============================================================
# SECTION 10 - FOLLOW-UP LANGUAGE TABLES
# ============================================================

PLAYER_PRONOUNS = {
    "he",
    "him",
    "his",
    "that player",
    "this player",
    "the player",
    "that hitter",
    "this hitter",
    "the hitter",
    "that pitcher",
    "this pitcher",
    "the pitcher",
}

TEAM_PRONOUNS = {
    "they",
    "them",
    "their",
    "that team",
    "this team",
    "the team",
    "that club",
    "this club",
    "the club",
}

GAME_PRONOUNS = {
    "that game",
    "this game",
    "the game",
    "that matchup",
    "this matchup",
    "the matchup",
}

STATISTIC_PRONOUNS = {
    "that stat",
    "this stat",
    "the stat",
    "same stat",
    "that number",
    "this number",
    "the number",
    "it",
}

OUTCOME_PRONOUNS = {
    "that outcome",
    "this outcome",
    "the outcome",
    "same outcome",
    "again",
    "do it again",
}

ELLIPTICAL_PREFIXES = (
    "what about ",
    "how about ",
    "and ",
    "also ",
    "then ",
    "now ",
    "same for ",
    "what if ",
)

CORRECTION_PREFIXES = (
    "no ",
    "not ",
    "i meant ",
    "actually ",
    "instead ",
    "correction ",
)

RESET_CONTEXT_PHRASES = {
    "new question",
    "forget that",
    "forget the previous question",
    "clear context",
    "clear memory",
    "reset context",
    "reset chat",
    "start over",
    "new topic",
}


# ============================================================
# SECTION 11 - ENTITY EXTRACTION HELPERS
# ============================================================

def _coerce_entity(
    value: Any,
    *,
    entity_type: str,
    default_source: ContextSource = ContextSource.CURRENT_EXPLICIT,
) -> ContextEntity | None:
    if value is None:
        return None

    if isinstance(value, ContextEntity):
        return value

    if is_dataclass(value):
        value = asdict(value)

    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        return ContextEntity(
            entity_type=entity_type,
            canonical_name=normalized,
            matched_text=normalized,
            source=default_source,
            confidence=0.90,
        )

    if not isinstance(value, Mapping):
        return None

    canonical_name = (
        value.get("canonical_name")
        or value.get("name")
        or value.get(f"{entity_type}_name")
        or value.get("display_name")
        or value.get("label")
    )

    entity_id = (
        value.get("entity_id")
        or value.get("id")
        or value.get(f"{entity_type}_id")
        or value.get("mlb_id")
    )

    if canonical_name is None and entity_id is None:
        return None

    source_value = value.get("source")
    source = default_source

    if isinstance(source_value, ContextSource):
        source = source_value
    elif isinstance(source_value, str):
        try:
            source = ContextSource(source_value)
        except ValueError:
            source = default_source

    confidence = _coerce_probability(
        value.get("confidence"),
        default=0.90,
    )

    metadata = dict(value.get("metadata") or {})

    return ContextEntity(
        entity_type=entity_type,
        entity_id=entity_id,
        canonical_name=(
            str(canonical_name)
            if canonical_name is not None
            else None
        ),
        matched_text=(
            value.get("matched_text")
            or value.get("match")
            or value.get("observed_text")
        ),
        source=source,
        confidence=confidence,
        metadata=metadata,
    )


def _extract_entity_list(
    report: Mapping[str, Any] | None,
    singular_key: str,
    plural_key: str,
    entity_type: str,
) -> list[ContextEntity]:
    report = report or {}
    results: list[ContextEntity] = []

    plural_value = report.get(plural_key)

    if isinstance(plural_value, Sequence) and not isinstance(
        plural_value,
        (str, bytes),
    ):
        for item in plural_value:
            entity = _coerce_entity(
                item,
                entity_type=entity_type,
            )
            if entity is not None:
                results.append(entity)

    singular_value = report.get(singular_key)

    if singular_value is not None:
        entity = _coerce_entity(
            singular_value,
            entity_type=entity_type,
        )
        if entity is not None:
            results.insert(0, entity)

    primary_key = f"primary_{singular_key}"
    primary_value = report.get(primary_key)

    if primary_value is not None:
        entity = _coerce_entity(
            primary_value,
            entity_type=entity_type,
        )
        if entity is not None:
            results.insert(0, entity)

    return deduplicate_context_entities(results)


def deduplicate_context_entities(
    values: Sequence[ContextEntity],
) -> list[ContextEntity]:
    output: list[ContextEntity] = []
    seen: set[tuple[str, str]] = set()

    for entity in values:
        identity = (
            str(entity.entity_id or ""),
            normalize_context_text(entity.canonical_name),
        )

        if identity in seen:
            continue

        seen.add(identity)
        output.append(entity)

    return output


def _extract_scalar_entity(
    entity_report: Mapping[str, Any] | None,
    semantic_report: Mapping[str, Any] | None,
    key: str,
    entity_type: str,
) -> ContextEntity | None:
    entity_report = entity_report or {}
    semantic_report = semantic_report or {}

    candidate_values = (
        entity_report.get(key),
        entity_report.get(f"primary_{key}"),
        semantic_report.get(key),
    )

    for value in candidate_values:
        entity = _coerce_entity(
            value,
            entity_type=entity_type,
            default_source=ContextSource.CURRENT_SEMANTIC,
        )
        if entity is not None:
            return entity

    return None


# ============================================================
# SECTION 12 - REPORT COMPATIBILITY HELPERS
# ============================================================

def extract_intent_name(
    intent_report: Mapping[str, Any] | None,
) -> str:
    intent_report = intent_report or {}

    return str(
        intent_report.get("final_intent")
        or intent_report.get("intent")
        or intent_report.get("task")
        or TASK_UNKNOWN
    )


def extract_intent_confidence(
    intent_report: Mapping[str, Any] | None,
) -> float:
    intent_report = intent_report or {}

    value = (
        intent_report.get("confidence_probability")
        or intent_report.get("confidence")
        or intent_report.get("confidence_score")
        or 0.0
    )

    return _coerce_probability(value, default=0.0)


def extract_scope(
    intent_report: Mapping[str, Any] | None,
    semantic_report: Mapping[str, Any] | None,
) -> str | None:
    intent_report = intent_report or {}
    semantic_report = semantic_report or {}

    scope = (
        intent_report.get("scope")
        or semantic_report.get("scope")
    )

    return str(scope) if scope is not None else None


# ============================================================
# SECTION 13 - FOLLOW-UP DETECTION
# ============================================================

def detect_follow_up_type(
    message: str,
    *,
    has_current_player: bool = False,
    has_current_team: bool = False,
    has_current_game: bool = False,
) -> FollowUpType:
    normalized = normalize_context_text(message)

    if not normalized:
        return FollowUpType.NONE

    if context_contains_any(normalized, RESET_CONTEXT_PHRASES):
        return FollowUpType.RESET

    if normalized.startswith(CORRECTION_PREFIXES):
        return FollowUpType.CORRECTION

    if (
        not has_current_player
        and context_contains_any(normalized, PLAYER_PRONOUNS)
    ):
        return FollowUpType.PRONOUN

    if (
        not has_current_team
        and context_contains_any(normalized, TEAM_PRONOUNS)
    ):
        return FollowUpType.PRONOUN

    if (
        not has_current_game
        and context_contains_any(normalized, GAME_PRONOUNS)
    ):
        return FollowUpType.PRONOUN

    if normalized.startswith(ELLIPTICAL_PREFIXES):
        return FollowUpType.ELLIPTICAL

    if context_contains_any(
        normalized,
        {
            "same player",
            "same team",
            "same game",
            "same matchup",
            "same one",
        },
    ):
        return FollowUpType.CONTINUATION

    return FollowUpType.NONE


def should_use_previous_context(
    follow_up_type: FollowUpType,
    config: ContextConfig,
) -> bool:
    if not config.enable_memory:
        return False

    if follow_up_type in {
        FollowUpType.PRONOUN,
        FollowUpType.ELLIPTICAL,
        FollowUpType.CONTINUATION,
    }:
        return True

    if config.require_followup_signal_for_context_reuse:
        return False

    return follow_up_type != FollowUpType.RESET


# ============================================================
# SECTION 14 - MEMORY EXPIRATION
# ============================================================

def context_memory_is_expired(
    memory: ConversationMemory,
    config: ContextConfig,
    *,
    now: datetime | None = None,
) -> bool:
    if not config.enable_context_expiration:
        return False

    now = now or datetime.now(UTC)

    if memory.expires_at is not None:
        return now >= memory.expires_at

    age = now - memory.updated_at
    return age > timedelta(hours=config.context_ttl_hours)


def refresh_memory_expiration(
    memory: ConversationMemory,
    config: ContextConfig,
    *,
    now: datetime | None = None,
) -> ConversationMemory:
    now = now or datetime.now(UTC)

    memory.updated_at = now
    memory.expires_at = (
        now + timedelta(hours=config.context_ttl_hours)
        if config.enable_context_expiration
        else None
    )
    return memory


# ============================================================
# SECTION 15 - TASK CLASSIFICATION
# ============================================================

INTENT_TO_TASK = {
    "help": TASK_HELP,

    "team_info": TASK_TEAM_LOOKUP,
    "team_lookup": TASK_TEAM_LOOKUP,
    "player_info": TASK_PLAYER_LOOKUP,
    "player_lookup": TASK_PLAYER_LOOKUP,
    "roster_lookup": TASK_ROSTER_LOOKUP,
    "team_roster": TASK_ROSTER_LOOKUP,
    "schedule_lookup": TASK_SCHEDULE_LOOKUP,
    "team_schedule": TASK_SCHEDULE_LOOKUP,
    "game_lookup": TASK_GAME_LOOKUP,

    "player_stat_request": TASK_PLAYER_STATS,
    "player_stats": TASK_PLAYER_STATS,
    "team_stat_request": TASK_TEAM_STATS,
    "team_stats": TASK_TEAM_STATS,
    "stat_request": TASK_STAT_REQUEST,

    "player_probability": TASK_PLAYER_PROBABILITY,
    "team_probability": TASK_TEAM_PROBABILITY,
    "team_prediction": TASK_TEAM_PROBABILITY,
    "game_probability": TASK_GAME_PROBABILITY,
    "game_prediction": TASK_GAME_PROBABILITY,
    "general_probability": TASK_GENERAL_PROBABILITY,
    "best_team_probability": TASK_BEST_TEAM_PROBABILITY,

    "compare_players": TASK_PLAYER_COMPARISON,
    "player_comparison": TASK_PLAYER_COMPARISON,
    "compare_teams": TASK_TEAM_COMPARISON,
    "team_comparison": TASK_TEAM_COMPARISON,
    "matchup_analysis": TASK_MATCHUP_ANALYSIS,

    "database_status": TASK_DATABASE_STATUS,
    "warehouse_status": TASK_WAREHOUSE_STATUS,
    "model_status": TASK_MODEL_STATUS,
    "data_source_status": TASK_DATA_SOURCE_STATUS,
    "explain_model": TASK_EXPLAIN_MODEL,

    "clarification_required": TASK_CLARIFICATION,
    "general_baseball_question": TASK_GENERAL_CHAT,
    "general_chat": TASK_GENERAL_CHAT,
}


def classify_context_task(
    message: str,
    intent_report: Mapping[str, Any] | None,
    entity_report: Mapping[str, Any] | None,
    semantic_report: Mapping[str, Any] | None = None,
) -> str:
    """
    Classify from the current intent report only.

    Previous conversation intent is intentionally not accepted by this
    function and therefore cannot lock the current request.
    """
    semantic_report = semantic_report or {}
    entity_report = entity_report or {}

    current_intent = extract_intent_name(intent_report)
    mapped_task = INTENT_TO_TASK.get(
        current_intent,
        TASK_UNKNOWN,
    )

    players = _extract_entity_list(
        entity_report,
        "player",
        "players",
        "player",
    )
    teams = _extract_entity_list(
        entity_report,
        "team",
        "teams",
        "team",
    )

    statistic = _extract_scalar_entity(
        entity_report,
        semantic_report,
        "statistic",
        "statistic",
    )
    outcome = _extract_scalar_entity(
        entity_report,
        semantic_report,
        "outcome",
        "outcome",
    )

    if len(players) >= 2:
        return TASK_PLAYER_COMPARISON

    if len(teams) >= 2 and mapped_task not in {
        TASK_GAME_PROBABILITY,
        TASK_MATCHUP_ANALYSIS,
    }:
        return TASK_TEAM_COMPARISON

    if teams and context_contains_any(
        message,
        (
            "roster",
            "lineup",
            "players on",
            "players for",
            "who is on",
            "who plays for",
        ),
    ):
        return TASK_ROSTER_LOOKUP

    if teams and context_contains_any(
        message,
        (
            "schedule",
            "next game",
            "when do",
            "upcoming games",
        ),
    ):
        return TASK_SCHEDULE_LOOKUP

    if players and statistic and mapped_task in {
        TASK_UNKNOWN,
        TASK_GENERAL_CHAT,
        TASK_PLAYER_LOOKUP,
        TASK_STAT_REQUEST,
    }:
        return TASK_PLAYER_STATS

    if teams and statistic and mapped_task in {
        TASK_UNKNOWN,
        TASK_GENERAL_CHAT,
        TASK_TEAM_LOOKUP,
        TASK_STAT_REQUEST,
    }:
        return TASK_TEAM_STATS

    if players and outcome and mapped_task in {
        TASK_UNKNOWN,
        TASK_GENERAL_CHAT,
        TASK_PLAYER_LOOKUP,
        TASK_GENERAL_PROBABILITY,
    }:
        return TASK_PLAYER_PROBABILITY

    if teams and outcome and mapped_task in {
        TASK_UNKNOWN,
        TASK_GENERAL_CHAT,
        TASK_TEAM_LOOKUP,
        TASK_GENERAL_PROBABILITY,
    }:
        return TASK_TEAM_PROBABILITY

    if mapped_task != TASK_UNKNOWN:
        return mapped_task

    if players:
        return TASK_PLAYER_LOOKUP

    if teams:
        return TASK_TEAM_LOOKUP

    return TASK_GENERAL_CHAT


# ============================================================
# SECTION 16 - CONTEXT VALUE EXTRACTION
# ============================================================

def extract_context_values(
    entity_report: Mapping[str, Any] | None,
    semantic_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    entity_report = entity_report or {}
    semantic_report = semantic_report or {}

    players = _extract_entity_list(
        entity_report,
        "player",
        "players",
        "player",
    )
    teams = _extract_entity_list(
        entity_report,
        "team",
        "teams",
        "team",
    )

    return {
        "player": players[0] if players else None,
        "team": teams[0] if teams else None,
        "players": players,
        "teams": teams,
        "game": _extract_scalar_entity(
            entity_report,
            semantic_report,
            "game",
            "game",
        ),
        "statistic": _extract_scalar_entity(
            entity_report,
            semantic_report,
            "statistic",
            "statistic",
        ),
        "outcome": _extract_scalar_entity(
            entity_report,
            semantic_report,
            "outcome",
            "outcome",
        ),
        "opponent": _extract_scalar_entity(
            entity_report,
            semantic_report,
            "opponent",
            "opponent",
        ),
        "date": _extract_scalar_entity(
            entity_report,
            semantic_report,
            "date",
            "date",
        ),
        "season": _extract_scalar_entity(
            entity_report,
            semantic_report,
            "season",
            "season",
        ),
    }


# ============================================================
# SECTION 17 - PRONOUN RESOLUTION
# ============================================================

def resolve_pronouns_from_memory(
    message: str,
    values: MutableMapping[str, Any],
    memory: ConversationMemory,
    resolution: ContextResolution,
    config: ContextConfig,
) -> None:
    if not config.enable_pronoun_resolution:
        return

    normalized = normalize_context_text(message)

    if (
        values.get("player") is None
        and memory.last_player_name
        and context_contains_any(normalized, PLAYER_PRONOUNS)
    ):
        values["player"] = ContextEntity(
            entity_type="player",
            entity_id=memory.last_player_id,
            canonical_name=memory.last_player_name,
            matched_text="conversation pronoun",
            source=ContextSource.PREVIOUS_CONTEXT,
            confidence=0.88,
        )
        values["players"] = [values["player"]]
        resolution.context_used = True
        resolution.player_from_context = True
        resolution.record(
            ContextAction.REUSED,
            "player",
            "player_pronoun_resolved",
            current_value=memory.last_player_name,
        )

    if (
        values.get("team") is None
        and memory.last_team_name
        and context_contains_any(normalized, TEAM_PRONOUNS)
    ):
        values["team"] = ContextEntity(
            entity_type="team",
            entity_id=memory.last_team_id,
            canonical_name=memory.last_team_name,
            matched_text="conversation pronoun",
            source=ContextSource.PREVIOUS_CONTEXT,
            confidence=0.86,
        )
        values["teams"] = [values["team"]]
        resolution.context_used = True
        resolution.team_from_context = True
        resolution.record(
            ContextAction.REUSED,
            "team",
            "team_pronoun_resolved",
            current_value=memory.last_team_name,
        )

    if (
        values.get("game") is None
        and memory.last_game_label
        and context_contains_any(normalized, GAME_PRONOUNS)
    ):
        values["game"] = ContextEntity(
            entity_type="game",
            entity_id=memory.last_game_id,
            canonical_name=memory.last_game_label,
            matched_text="conversation game pronoun",
            source=ContextSource.PREVIOUS_CONTEXT,
            confidence=0.84,
        )
        resolution.context_used = True
        resolution.game_from_context = True
        resolution.record(
            ContextAction.REUSED,
            "game",
            "game_pronoun_resolved",
            current_value=memory.last_game_label,
        )


# ============================================================
# SECTION 18 - ELLIPTICAL FOLLOW-UP RESOLUTION
# ============================================================

def resolve_elliptical_follow_up(
    message: str,
    values: MutableMapping[str, Any],
    memory: ConversationMemory,
    resolution: ContextResolution,
    config: ContextConfig,
) -> None:
    if not config.enable_ellipsis_resolution:
        return

    normalized = normalize_context_text(message)
    is_elliptical = normalized.startswith(ELLIPTICAL_PREFIXES)

    if not is_elliptical:
        return

    has_new_stat_or_outcome = bool(
        values.get("statistic")
        or values.get("outcome")
    )

    if (
        values.get("player") is None
        and values.get("team") is None
        and memory.last_player_name
        and has_new_stat_or_outcome
    ):
        values["player"] = ContextEntity(
            entity_type="player",
            entity_id=memory.last_player_id,
            canonical_name=memory.last_player_name,
            matched_text="elliptical follow-up",
            source=ContextSource.PREVIOUS_CONTEXT,
            confidence=0.80,
        )
        values["players"] = [values["player"]]
        resolution.context_used = True
        resolution.player_from_context = True
        resolution.record(
            ContextAction.REUSED,
            "player",
            "player_ellipsis_resolved",
            current_value=memory.last_player_name,
        )

    elif (
        values.get("player") is None
        and values.get("team") is None
        and memory.last_team_name
        and values.get("statistic") is not None
    ):
        values["team"] = ContextEntity(
            entity_type="team",
            entity_id=memory.last_team_id,
            canonical_name=memory.last_team_name,
            matched_text="elliptical follow-up",
            source=ContextSource.PREVIOUS_CONTEXT,
            confidence=0.78,
        )
        values["teams"] = [values["team"]]
        resolution.context_used = True
        resolution.team_from_context = True
        resolution.record(
            ContextAction.REUSED,
            "team",
            "team_ellipsis_resolved",
            current_value=memory.last_team_name,
        )


# ============================================================
# SECTION 19 - SCALAR CONTEXT REUSE
# ============================================================

def resolve_scalar_context(
    message: str,
    values: MutableMapping[str, Any],
    memory: ConversationMemory,
    resolution: ContextResolution,
    config: ContextConfig,
) -> None:
    normalized = normalize_context_text(message)

    if (
        config.allow_statistic_context_reuse
        and values.get("statistic") is None
        and memory.last_statistic
        and context_contains_any(normalized, STATISTIC_PRONOUNS)
    ):
        values["statistic"] = ContextEntity(
            entity_type="statistic",
            canonical_name=memory.last_statistic,
            matched_text="conversation statistic reference",
            source=ContextSource.PREVIOUS_CONTEXT,
            confidence=0.76,
        )
        resolution.context_used = True
        resolution.statistic_from_context = True
        resolution.record(
            ContextAction.REUSED,
            "statistic",
            "statistic_reference_resolved",
            current_value=memory.last_statistic,
        )

    if (
        config.allow_outcome_context_reuse
        and values.get("outcome") is None
        and memory.last_outcome
        and context_contains_any(normalized, OUTCOME_PRONOUNS)
    ):
        values["outcome"] = ContextEntity(
            entity_type="outcome",
            canonical_name=memory.last_outcome,
            matched_text="conversation outcome reference",
            source=ContextSource.PREVIOUS_CONTEXT,
            confidence=0.74,
        )
        resolution.context_used = True
        resolution.outcome_from_context = True
        resolution.record(
            ContextAction.REUSED,
            "outcome",
            "outcome_reference_resolved",
            current_value=memory.last_outcome,
        )


# ============================================================
# SECTION 20 - CURRENT ENTITY OVERRIDE POLICY
# ============================================================

def apply_current_entity_override_policy(
    values: MutableMapping[str, Any],
    memory: ConversationMemory,
    resolution: ContextResolution,
    config: ContextConfig,
) -> None:
    current_player = values.get("player")
    current_team = values.get("team")
    current_game = values.get("game")
    current_statistic = values.get("statistic")
    current_outcome = values.get("outcome")

    if (
        current_player
        and current_player.source != ContextSource.PREVIOUS_CONTEXT
        and memory.last_player_name
        and normalize_context_text(current_player.canonical_name)
        != normalize_context_text(memory.last_player_name)
    ):
        resolution.current_player_overrode_previous = True
        resolution.record(
            ContextAction.OVERRIDDEN,
            "player",
            "new_player_overrode_previous_player",
            previous_value=memory.last_player_name,
            current_value=current_player.canonical_name,
        )

    if (
        current_team
        and current_team.source != ContextSource.PREVIOUS_CONTEXT
        and memory.last_team_name
        and normalize_context_text(current_team.canonical_name)
        != normalize_context_text(memory.last_team_name)
    ):
        resolution.current_team_overrode_previous = True
        resolution.record(
            ContextAction.OVERRIDDEN,
            "team",
            "new_team_overrode_previous_team",
            previous_value=memory.last_team_name,
            current_value=current_team.canonical_name,
        )

    if (
        current_game
        and current_game.source != ContextSource.PREVIOUS_CONTEXT
        and memory.last_game_label
        and normalize_context_text(current_game.canonical_name)
        != normalize_context_text(memory.last_game_label)
    ):
        resolution.current_game_overrode_previous = True
        resolution.record(
            ContextAction.OVERRIDDEN,
            "game",
            "new_game_overrode_previous_game",
            previous_value=memory.last_game_label,
            current_value=current_game.canonical_name,
        )

    if (
        current_statistic
        and current_statistic.source != ContextSource.PREVIOUS_CONTEXT
        and memory.last_statistic
        and normalize_context_text(current_statistic.canonical_name)
        != normalize_context_text(memory.last_statistic)
    ):
        resolution.current_statistic_overrode_previous = True
        resolution.record(
            ContextAction.OVERRIDDEN,
            "statistic",
            "new_statistic_overrode_previous_statistic",
            previous_value=memory.last_statistic,
            current_value=current_statistic.canonical_name,
        )

    if (
        current_outcome
        and current_outcome.source != ContextSource.PREVIOUS_CONTEXT
        and memory.last_outcome
        and normalize_context_text(current_outcome.canonical_name)
        != normalize_context_text(memory.last_outcome)
    ):
        resolution.current_outcome_overrode_previous = True
        resolution.record(
            ContextAction.OVERRIDDEN,
            "outcome",
            "new_outcome_overrode_previous_outcome",
            previous_value=memory.last_outcome,
            current_value=current_outcome.canonical_name,
        )


# ============================================================
# SECTION 21 - MEMORY UPDATE POLICY
# ============================================================

def build_next_memory(
    previous_memory: ConversationMemory,
    *,
    message: str,
    normalized_message: str,
    current_intent: str,
    current_task: str,
    current_scope: str | None,
    values: Mapping[str, Any],
    clarification_required: bool,
    resolution: ContextResolution,
    config: ContextConfig,
) -> ConversationMemory:
    if resolution.context_reset:
        next_memory = ConversationMemory(
            conversation_id=previous_memory.conversation_id,
        )
    else:
        next_memory = ConversationMemory.from_any(
            previous_memory.to_dict()
        )

    if clarification_required:
        return next_memory

    player = values.get("player")
    team = values.get("team")
    game = values.get("game")
    statistic = values.get("statistic")
    outcome = values.get("outcome")
    opponent = values.get("opponent")
    date_entity = values.get("date")
    season = values.get("season")

    if player is not None:
        next_memory.last_player_id = player.entity_id
        next_memory.last_player_name = player.canonical_name

        if player.source != ContextSource.PREVIOUS_CONTEXT:
            next_memory.last_game_id = None
            next_memory.last_game_label = None

            if not config.preserve_team_when_player_named:
                next_memory.last_team_id = None
                next_memory.last_team_name = None

    if team is not None:
        next_memory.last_team_id = team.entity_id
        next_memory.last_team_name = team.canonical_name

        if (
            team.source != ContextSource.PREVIOUS_CONTEXT
            and not config.preserve_player_when_team_named
        ):
            next_memory.last_player_id = None
            next_memory.last_player_name = None

    if game is not None:
        next_memory.last_game_id = game.entity_id
        next_memory.last_game_label = game.canonical_name

    if statistic is not None:
        next_memory.last_statistic = statistic.canonical_name

    if outcome is not None:
        next_memory.last_outcome = outcome.canonical_name

    if opponent is not None:
        next_memory.last_opponent_id = opponent.entity_id
        next_memory.last_opponent_name = opponent.canonical_name

    if date_entity is not None:
        next_memory.last_date = date_entity.canonical_name

    if season is not None:
        next_memory.last_season = _coerce_optional_int(
            season.entity_id
            or season.canonical_name
        )

    next_memory.last_intent = current_intent
    next_memory.last_task = current_task
    next_memory.last_scope = current_scope
    next_memory.last_message = message
    next_memory.last_normalized_message = normalized_message
    next_memory.turn_count += 1

    refresh_memory_expiration(
        next_memory,
        config,
    )

    next_memory.metadata.update({
        "previous_intent_used_for_classification": False,
        "context_engine_version": CONTEXT_ENGINE_VERSION,
        "last_context_used": resolution.context_used,
    })

    return next_memory


# ============================================================
# SECTION 22 - CONTEXT CONFIDENCE
# ============================================================

def calculate_context_confidence(
    task: str,
    values: Mapping[str, Any],
    intent_report: Mapping[str, Any] | None,
    entity_report: Mapping[str, Any] | None,
    semantic_report: Mapping[str, Any] | None = None,
    resolution: ContextResolution | None = None,
) -> int:
    intent_confidence = extract_intent_confidence(
        intent_report
    )

    score = 0.30

    if task not in {
        TASK_GENERAL_CHAT,
        TASK_UNKNOWN,
    }:
        score += 0.15

    for key in (
        "player",
        "team",
        "game",
        "statistic",
        "outcome",
        "opponent",
        "date",
        "season",
    ):
        entity = values.get(key)

        if entity is not None:
            score += min(
                0.10,
                float(entity.confidence) * 0.10,
            )

    score += min(
        0.18,
        intent_confidence * 0.18,
    )

    if resolution is not None:
        if resolution.context_used:
            score += 0.03

        if resolution.context_expired:
            score -= 0.08

    score = max(
        0.0,
        min(score, CONTEXT_CONFIDENCE_MAXIMUM),
    )

    return int(round(score * 100))


# ============================================================
# SECTION 23 - CONTEXT STATUS
# ============================================================

def determine_context_status(
    values: Mapping[str, Any],
    resolution: ContextResolution,
    clarification_required: bool,
) -> ContextStatus:
    if resolution.context_reset:
        return ContextStatus.RESET

    if resolution.context_expired:
        return ContextStatus.EXPIRED

    if clarification_required:
        return ContextStatus.AMBIGUOUS

    entity_count = sum(
        bool(values.get(key))
        for key in (
            "player",
            "team",
            "game",
            "statistic",
            "outcome",
            "opponent",
            "date",
            "season",
        )
    )

    multi_count = max(
        len(values.get("players") or []),
        len(values.get("teams") or []),
    )

    if multi_count >= 2:
        return ContextStatus.MULTI_ENTITY

    if entity_count == 0:
        return ContextStatus.EMPTY

    if entity_count == 1:
        return ContextStatus.PARTIAL

    return ContextStatus.COMPLETE


# ============================================================
# SECTION 24 - CLARIFICATION HELPERS
# ============================================================

def determine_context_clarification(
    task: str,
    values: Mapping[str, Any],
) -> tuple[bool, str | None, str | None]:
    if task in {
        TASK_PLAYER_LOOKUP,
        TASK_PLAYER_STATS,
        TASK_PLAYER_PROBABILITY,
    } and values.get("player") is None:
        return (
            True,
            "missing_player",
            "Which player would you like me to use?",
        )

    if task in {
        TASK_TEAM_LOOKUP,
        TASK_TEAM_STATS,
        TASK_ROSTER_LOOKUP,
        TASK_SCHEDULE_LOOKUP,
        TASK_TEAM_PROBABILITY,
    } and values.get("team") is None:
        return (
            True,
            "missing_team",
            "Which MLB team would you like me to use?",
        )

    if (
        task == TASK_PLAYER_PROBABILITY
        and values.get("outcome") is None
    ):
        return (
            True,
            "missing_outcome",
            (
                "Which outcome should I project: hit, home run, "
                "walk, strikeout, RBI, run, or total bases?"
            ),
        )

    if (
        task in {
            TASK_PLAYER_STATS,
            TASK_TEAM_STATS,
        }
        and values.get("statistic") is None
    ):
        return (
            True,
            "missing_statistic",
            (
                "Which statistic would you like: AVG, OBP, SLG, "
                "OPS, home runs, hits, ERA, WHIP, or another metric?"
            ),
        )

    return False, None, None


# ============================================================
# SECTION 25 - PRIMARY CONTEXT BUILD PIPELINE
# ============================================================

def build_baseball_context(
    message: str,
    intent_report: Mapping[str, Any],
    entity_report: Mapping[str, Any],
    semantic_report: Mapping[str, Any] | None = None,
    conversation_context: Any = None,
    config: ContextConfig | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    config = config or ContextConfig()
    config.validate()

    request_id = request_id or str(uuid4())
    semantic_report = semantic_report or {}

    normalized_message = normalize_context_text(message)
    previous_memory = ConversationMemory.from_any(
        conversation_context
    )

    resolution = ContextResolution()

    values = extract_context_values(
        entity_report=entity_report,
        semantic_report=semantic_report,
    )

    follow_up_type = detect_follow_up_type(
        message,
        has_current_player=values.get("player") is not None,
        has_current_team=values.get("team") is not None,
        has_current_game=values.get("game") is not None,
    )
    resolution.follow_up_type = follow_up_type

    if follow_up_type == FollowUpType.RESET:
        resolution.context_reset = True
        resolution.record(
            ContextAction.RESET,
            "conversation",
            "explicit_context_reset",
        )
        previous_memory = ConversationMemory(
            conversation_id=previous_memory.conversation_id,
        )

    elif context_memory_is_expired(
        previous_memory,
        config,
    ):
        resolution.context_expired = True
        resolution.record(
            ContextAction.EXPIRED,
            "conversation",
            "conversation_context_expired",
            previous_value=previous_memory.updated_at.isoformat(),
        )
        previous_memory = ConversationMemory(
            conversation_id=previous_memory.conversation_id,
        )

    use_context = should_use_previous_context(
        follow_up_type,
        config,
    )

    if use_context:
        resolve_pronouns_from_memory(
            message=message,
            values=values,
            memory=previous_memory,
            resolution=resolution,
            config=config,
        )

        resolve_elliptical_follow_up(
            message=message,
            values=values,
            memory=previous_memory,
            resolution=resolution,
            config=config,
        )

        resolve_scalar_context(
            message=message,
            values=values,
            memory=previous_memory,
            resolution=resolution,
            config=config,
        )

    apply_current_entity_override_policy(
        values=values,
        memory=previous_memory,
        resolution=resolution,
        config=config,
    )

    current_intent = extract_intent_name(
        intent_report
    )
    current_scope = extract_scope(
        intent_report,
        semantic_report,
    )

    task = classify_context_task(
        message=message,
        intent_report=intent_report,
        entity_report={
            **dict(entity_report or {}),
            "player": (
                values["player"].to_dict()
                if values.get("player")
                else None
            ),
            "team": (
                values["team"].to_dict()
                if values.get("team")
                else None
            ),
            "players": [
                item.to_dict()
                for item in values.get("players") or []
            ],
            "teams": [
                item.to_dict()
                for item in values.get("teams") or []
            ],
            "statistic": (
                values["statistic"].to_dict()
                if values.get("statistic")
                else None
            ),
            "outcome": (
                values["outcome"].to_dict()
                if values.get("outcome")
                else None
            ),
        },
        semantic_report=semantic_report,
    )

    (
        clarification_required,
        clarification_reason,
        clarification_prompt,
    ) = determine_context_clarification(
        task,
        values,
    )

    confidence_percent = calculate_context_confidence(
        task=task,
        values=values,
        intent_report=intent_report,
        entity_report=entity_report,
        semantic_report=semantic_report,
        resolution=resolution,
    )
    confidence = confidence_percent / 100.0

    status = determine_context_status(
        values,
        resolution,
        clarification_required,
    )

    next_memory = build_next_memory(
        previous_memory=previous_memory,
        message=message,
        normalized_message=normalized_message,
        current_intent=current_intent,
        current_task=task,
        current_scope=current_scope,
        values=values,
        clarification_required=clarification_required,
        resolution=resolution,
        config=config,
    )

    diagnostics = {
        "current_message_is_authoritative": True,
        "previous_intent_used_for_classification": False,
        "previous_intent": previous_memory.last_intent,
        "current_intent": current_intent,
        "intent_changed": (
            previous_memory.last_intent is not None
            and previous_memory.last_intent != current_intent
        ),
        "follow_up_signal_required": (
            config.require_followup_signal_for_context_reuse
        ),
        "context_reuse_allowed": use_context,
        "memory_was_empty": (
            previous_memory.turn_count == 0
            and not previous_memory.last_player_name
            and not previous_memory.last_team_name
        ),
        "request_fingerprint": build_context_fingerprint({
            "message": normalized_message,
            "task": task,
            "intent": current_intent,
            "player": (
                values["player"].canonical_name
                if values.get("player")
                else None
            ),
            "team": (
                values["team"].canonical_name
                if values.get("team")
                else None
            ),
            "statistic": (
                values["statistic"].canonical_name
                if values.get("statistic")
                else None
            ),
            "outcome": (
                values["outcome"].canonical_name
                if values.get("outcome")
                else None
            ),
        }),
    }

    result = ContextBuildResult(
        request_id=request_id,
        message=message,
        normalized_message=normalized_message,
        task=task,
        intent=current_intent,
        scope=current_scope,
        confidence=confidence,
        confidence_percent=confidence_percent,
        status=status,
        player=values.get("player"),
        team=values.get("team"),
        game=values.get("game"),
        statistic=values.get("statistic"),
        outcome=values.get("outcome"),
        opponent=values.get("opponent"),
        date=values.get("date"),
        season=values.get("season"),
        players=list(values.get("players") or []),
        teams=list(values.get("teams") or []),
        resolution=resolution,
        previous_memory=previous_memory,
        next_memory=next_memory,
        clarification_required=clarification_required,
        clarification_reason=clarification_reason,
        clarification_prompt=clarification_prompt,
        diagnostics=diagnostics,
    )

    payload = result.to_dict()

    # Backward-compatible top-level values.
    payload["subject"] = (
        payload["player"]
        or payload["team"]
        or payload["game"]
    )
    payload["subjects"] = (
        payload["players"]
        or payload["teams"]
    )
    payload["entities"] = dict(entity_report or {})
    payload["semantic"] = dict(semantic_report or {})
    payload["intent_report"] = dict(intent_report or {})

    return payload


# ============================================================
# SECTION 26 - DIRECT MEMORY RESOLUTION API
# ============================================================

def resolve_conversation_context(
    message: str,
    current_entities: Mapping[str, Any] | None,
    previous_context: Any,
    *,
    current_intent: str | None = None,
    config: ContextConfig | None = None,
) -> dict[str, Any]:
    return build_baseball_context(
        message=message,
        intent_report={
            "final_intent": (
                current_intent
                or TASK_GENERAL_CHAT
            ),
            "confidence": 0.75,
        },
        entity_report=dict(current_entities or {}),
        semantic_report={},
        conversation_context=previous_context,
        config=config,
    )


# ============================================================
# SECTION 27 - MEMORY RESET API
# ============================================================

def reset_conversation_memory(
    previous_context: Any = None,
) -> dict[str, Any]:
    previous = ConversationMemory.from_any(
        previous_context
    )

    reset_memory = ConversationMemory(
        conversation_id=previous.conversation_id,
    )

    return reset_memory.to_dict()


# ============================================================
# SECTION 28 - MEMORY MERGE API
# ============================================================

def merge_conversation_memory(
    base_context: Any,
    updates: Mapping[str, Any],
) -> dict[str, Any]:
    memory = ConversationMemory.from_any(
        base_context
    )

    allowed_fields = {
        field_name
        for field_name in memory.__dataclass_fields__
    }

    for key, value in updates.items():
        if key not in allowed_fields:
            continue

        if key in {
            "created_at",
            "updated_at",
            "expires_at",
        }:
            value = parse_datetime(value)

        setattr(memory, key, value)

    return memory.to_dict()


# ============================================================
# SECTION 29 - SERIALIZATION HELPERS
# ============================================================

def serialize_conversation_memory(
    memory: Any,
) -> str:
    normalized = ConversationMemory.from_any(
        memory
    )

    return json.dumps(
        normalized.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )


def deserialize_conversation_memory(
    payload: str | bytes | None,
) -> ConversationMemory:
    if not payload:
        return ConversationMemory()

    if isinstance(payload, bytes):
        payload = payload.decode(
            "utf-8",
            errors="replace",
        )

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return ConversationMemory()

    return ConversationMemory.from_any(data)


# ============================================================
# SECTION 30 - CONTEXT FINGERPRINTING
# ============================================================

def build_context_fingerprint(
    value: Any,
) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_serializer,
    )

    return sha256(
        canonical.encode("utf-8")
    ).hexdigest()


# ============================================================
# SECTION 31 - HEALTH REPORT
# ============================================================

def context_engine_health() -> dict[str, Any]:
    validation = validate_context_builder()

    return {
        "name": CONTEXT_ENGINE_NAME,
        "version": CONTEXT_ENGINE_VERSION,
        "phase": CONTEXT_ENGINE_PHASE,
        "path": CONTEXT_ENGINE_PATH,
        "status": (
            CONTEXT_ENGINE_STATUS
            if validation["status"] == "ok"
            else "validation_failed"
        ),
        "multi_turn_memory_enabled": True,
        "pronouns_resolved_only_when_required": True,
        "new_entities_override_previous_context": True,
        "previous_intent_used_for_classification": False,
        "context_expiration_supported": True,
        "context_reset_supported": True,
        "serialization_supported": True,
        "validation": validation,
        "timestamp": datetime.now(UTC).isoformat(),
    }


# ============================================================
# SECTION 32 - VALIDATION FIXTURES
# ============================================================

def _player_entity(
    name: str,
    player_id: int,
) -> dict[str, Any]:
    return {
        "canonical_name": name,
        "entity_id": player_id,
        "confidence": 0.99,
        "source": "current_explicit",
    }


def _team_entity(
    name: str,
    team_id: int,
) -> dict[str, Any]:
    return {
        "canonical_name": name,
        "entity_id": team_id,
        "confidence": 0.99,
        "source": "current_explicit",
    }


# ============================================================
# SECTION 33 - SELF-VALIDATION
# ============================================================

def validate_context_builder() -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    first = build_baseball_context(
        message="Show me Aaron Judge",
        intent_report={
            "final_intent": "player_info",
            "confidence": 90,
        },
        entity_report={
            "player": _player_entity(
                "Aaron Judge",
                592450,
            ),
        },
    )

    results.append({
        "name": "initial_player_memory",
        "passed": (
            first["next_memory"]["last_player_name"]
            == "Aaron Judge"
        ),
    })

    second = build_baseball_context(
        message="What is his OPS?",
        intent_report={
            "final_intent": "player_stat_request",
            "confidence": 90,
        },
        entity_report={
            "statistic": {
                "canonical_name": "ops",
                "confidence": 0.99,
            },
        },
        conversation_context=first["next_memory"],
    )

    results.append({
        "name": "pronoun_player_resolution",
        "passed": (
            second["player"]["canonical_name"]
            == "Aaron Judge"
            and second["resolution"]["player_from_context"]
        ),
    })

    third = build_baseball_context(
        message="Predict Shohei Ohtani to hit a home run",
        intent_report={
            "final_intent": "player_probability",
            "confidence": 94,
        },
        entity_report={
            "player": _player_entity(
                "Shohei Ohtani",
                660271,
            ),
            "outcome": {
                "canonical_name": "home_run",
                "confidence": 0.99,
            },
        },
        conversation_context=second["next_memory"],
    )

    results.append({
        "name": "new_player_overrides_previous",
        "passed": (
            third["player"]["canonical_name"]
            == "Shohei Ohtani"
            and third["resolution"][
                "current_player_overrode_previous"
            ]
        ),
    })

    fourth = build_baseball_context(
        message="Show all MLB teams",
        intent_report={
            "final_intent": "list_teams",
            "confidence": 90,
        },
        entity_report={},
        conversation_context=third["next_memory"],
    )

    results.append({
        "name": "previous_player_not_reused_without_followup",
        "passed": (
            fourth["player"] is None
            and fourth["context_used"] is False
        ),
    })

    fifth = build_baseball_context(
        message="Show the Yankees roster",
        intent_report={
            "final_intent": "roster_lookup",
            "confidence": 92,
        },
        entity_report={
            "team": _team_entity(
                "New York Yankees",
                147,
            ),
        },
        conversation_context=third["next_memory"],
    )

    results.append({
        "name": "new_team_overrides_previous_subject",
        "passed": (
            fifth["team"]["canonical_name"]
            == "New York Yankees"
            and fifth["next_memory"]["last_player_name"]
            is None
        ),
    })

    sixth = build_baseball_context(
        message="When do they play next?",
        intent_report={
            "final_intent": "schedule_lookup",
            "confidence": 90,
        },
        entity_report={},
        conversation_context=fifth["next_memory"],
    )

    results.append({
        "name": "team_pronoun_resolution",
        "passed": (
            sixth["team"]["canonical_name"]
            == "New York Yankees"
            and sixth["resolution"]["team_from_context"]
        ),
    })

    seventh = build_baseball_context(
        message="Database status",
        intent_report={
            "final_intent": "database_status",
            "confidence": 95,
        },
        entity_report={},
        conversation_context=sixth["next_memory"],
    )

    results.append({
        "name": "previous_intent_does_not_lock_current",
        "passed": (
            seventh["task"]
            == TASK_DATABASE_STATUS
            and seventh["diagnostics"][
                "previous_intent_used_for_classification"
            ]
            is False
        ),
    })

    eighth = build_baseball_context(
        message="Forget that",
        intent_report={
            "final_intent": "general_baseball_question",
            "confidence": 60,
        },
        entity_report={},
        conversation_context=seventh["next_memory"],
    )

    results.append({
        "name": "context_reset",
        "passed": (
            eighth["resolution"]["context_reset"]
            and eighth["next_memory"]["last_player_name"]
            is None
            and eighth["next_memory"]["last_team_name"]
            is None
        ),
    })

    expired_memory = ConversationMemory(
        last_player_id=592450,
        last_player_name="Aaron Judge",
        updated_at=(
            datetime.now(UTC)
            - timedelta(hours=48)
        ),
    )

    ninth = build_baseball_context(
        message="What is his OPS?",
        intent_report={
            "final_intent": "player_stat_request",
            "confidence": 90,
        },
        entity_report={
            "statistic": {
                "canonical_name": "ops",
                "confidence": 0.99,
            },
        },
        conversation_context=expired_memory,
    )

    results.append({
        "name": "expired_context_not_reused",
        "passed": (
            ninth["resolution"]["context_expired"]
            and ninth["player"] is None
        ),
    })

    passed_count = sum(
        1
        for result in results
        if result["passed"]
    )

    failed = [
        result
        for result in results
        if not result["passed"]
    ]

    return {
        "status": (
            "ok"
            if not failed
            else "failed"
        ),
        "engine": CONTEXT_ENGINE_NAME,
        "version": CONTEXT_ENGINE_VERSION,
        "phase": CONTEXT_ENGINE_PHASE,
        "case_count": len(results),
        "passed_count": passed_count,
        "failed_count": len(failed),
        "accuracy": (
            round(
                passed_count / len(results),
                6,
            )
            if results
            else 1.0
        ),
        "failed_cases": failed,
        "results": results,
    }


# ============================================================
# SECTION 34 - GENERAL UTILITIES
# ============================================================

def parse_datetime(
    value: Any,
) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return (
            value
            if value.tzinfo
            else value.replace(tzinfo=UTC)
        )

    if isinstance(value, str):
        text = value.strip().replace(
            "Z",
            "+00:00",
        )

        if not text:
            return None

        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None

        return (
            parsed
            if parsed.tzinfo
            else parsed.replace(tzinfo=UTC)
        )

    return None


def _coerce_probability(
    value: Any,
    *,
    default: float,
) -> float:
    if value is None:
        return default

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default

    if numeric > 1.0:
        numeric /= 100.0

    return max(
        0.0,
        min(numeric, 1.0),
    )


def _coerce_non_negative_int(
    value: Any,
) -> int:
    try:
        return max(
            0,
            int(value or 0),
        )
    except (TypeError, ValueError):
        return 0


def _coerce_optional_int(
    value: Any,
) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _json_serializer(
    value: Any,
) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, Enum):
        return value.value

    if is_dataclass(value):
        return asdict(value)

    if isinstance(value, set):
        return sorted(value)

    raise TypeError(
        type(value).__name__
    )


# ============================================================
# SECTION 35 - CONFIGURATION EXPORT
# ============================================================

CONTEXT_ENGINE_CONFIGURATION = {
    "engine_name": CONTEXT_ENGINE_NAME,
    "engine_version": CONTEXT_ENGINE_VERSION,
    "engine_phase": CONTEXT_ENGINE_PHASE,
    "schema_version": CONTEXT_SCHEMA_VERSION,

    "entity_context_enabled": True,
    "multi_turn_memory_enabled": True,
    "pronoun_resolution_enabled": True,
    "ellipsis_resolution_enabled": True,
    "current_entity_override_enabled": True,
    "context_expiration_enabled": True,
    "context_reset_enabled": True,
    "serialization_enabled": True,

    "previous_intent_used_for_classification": False,
    "previous_intent_diagnostics_only": True,

    "default_context_ttl_hours": (
        DEFAULT_CONTEXT_CONFIG.context_ttl_hours
    ),
    "minimum_entity_confidence": (
        DEFAULT_CONTEXT_CONFIG.minimum_entity_confidence
    ),
    "minimum_context_reuse_confidence": (
        DEFAULT_CONTEXT_CONFIG.minimum_context_reuse_confidence
    ),
}


# ============================================================
# SECTION 36 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "CONTEXT_ENGINE_NAME",
    "CONTEXT_ENGINE_VERSION",
    "CONTEXT_ENGINE_PHASE",
    "CONTEXT_ENGINE_PATH",
    "CONTEXT_ENGINE_STATUS",
    "CONTEXT_SCHEMA_VERSION",

    "TASK_GENERAL_CHAT",
    "TASK_HELP",
    "TASK_TEAM_LOOKUP",
    "TASK_PLAYER_LOOKUP",
    "TASK_ROSTER_LOOKUP",
    "TASK_SCHEDULE_LOOKUP",
    "TASK_GAME_LOOKUP",
    "TASK_PLAYER_STATS",
    "TASK_TEAM_STATS",
    "TASK_STAT_REQUEST",
    "TASK_PLAYER_PROBABILITY",
    "TASK_TEAM_PROBABILITY",
    "TASK_GAME_PROBABILITY",
    "TASK_BEST_TEAM_PROBABILITY",
    "TASK_GENERAL_PROBABILITY",
    "TASK_PLAYER_COMPARISON",
    "TASK_TEAM_COMPARISON",
    "TASK_MATCHUP_ANALYSIS",
    "TASK_DATABASE_STATUS",
    "TASK_WAREHOUSE_STATUS",
    "TASK_MODEL_STATUS",
    "TASK_DATA_SOURCE_STATUS",
    "TASK_EXPLAIN_MODEL",
    "TASK_CLARIFICATION",
    "TASK_UNKNOWN",

    "ContextSource",
    "ContextAction",
    "FollowUpType",
    "ContextStatus",
    "ContextEntity",
    "ConversationMemory",
    "ContextResolution",
    "ContextBuildResult",
    "ContextConfig",

    "normalize_context_text",
    "tokenize_context_text",
    "context_contains_phrase",
    "context_contains_any",
    "detect_follow_up_type",
    "context_memory_is_expired",
    "classify_context_task",
    "extract_context_values",
    "calculate_context_confidence",
    "build_baseball_context",
    "resolve_conversation_context",
    "reset_conversation_memory",
    "merge_conversation_memory",
    "serialize_conversation_memory",
    "deserialize_conversation_memory",
    "build_context_fingerprint",
    "context_engine_health",
    "validate_context_builder",
]


# ============================================================
# SECTION 37 - LOCAL VALIDATION ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    print(
        json.dumps(
            context_engine_health(),
            indent=2,
            sort_keys=True,
        )
    )
