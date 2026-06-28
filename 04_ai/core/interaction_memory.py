# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/interaction_memory.py
# PURPOSE: lightweight chatbot learning memory for storing
# user questions, assistant responses, detected intent, entities,
# confidence, and future RAG/feedback learning signals
# ============================================================


# ============================================================
# SECTION 01 - ENTERPRISE MEMORY CONFIGURATION
# FILE: 04_ai/core/interaction_memory.py
# PURPOSE: define persistent memory categories, storage status,
# quality thresholds, text limits, learning signal defaults,
# fallback behavior, and long-term self-improvement controls
# for the AISP2 chatbot and future model-training pipeline.
# ============================================================

from __future__ import annotations

# ============================================================
# SECTION 01.01 - MEMORY CATEGORIES
# ============================================================

DEFAULT_MEMORY_CATEGORY = "baseball_chat"

MEMORY_CATEGORY_CHAT = "baseball_chat"
MEMORY_CATEGORY_PLAYER_SEARCH = "player_search"
MEMORY_CATEGORY_TEAM_SEARCH = "team_search"
MEMORY_CATEGORY_PREDICTION = "prediction"
MEMORY_CATEGORY_STAT_REQUEST = "stat_request"
MEMORY_CATEGORY_COMPARISON = "comparison"
MEMORY_CATEGORY_SYSTEM = "system"
MEMORY_CATEGORY_SECURITY = "security"


# ============================================================
# SECTION 01.02 - MEMORY STORAGE STATUSES
# ============================================================

MEMORY_STATUS_STORED = "stored"
MEMORY_STATUS_SKIPPED = "skipped"
MEMORY_STATUS_FALLBACK_STORED = "fallback_stored"
MEMORY_STATUS_FAILED = "failed"


# ============================================================
# SECTION 01.03 - MEMORY TEXT LIMITS
# ============================================================

MAX_MEMORY_TEXT_LENGTH = 2500
MAX_MEMORY_SUMMARY_LENGTH = 700
MAX_MEMORY_ENTITY_LENGTH = 160
MAX_FALLBACK_MEMORY_RECORDS = 500


# ============================================================
# SECTION 01.04 - LEARNING QUALITY THRESHOLDS
# ============================================================

MEMORY_IMPORTANCE_MINIMUM = 20
MEMORY_IMPORTANCE_DEFAULT = 35
MEMORY_IMPORTANCE_REVIEW_THRESHOLD = 60
MEMORY_IMPORTANCE_TRAINING_THRESHOLD = 75
MEMORY_IMPORTANCE_MAXIMUM = 100


# ============================================================
# SECTION 01.05 - LEARNING SIGNAL TYPES
# ============================================================

SIGNAL_TYPE_INTENT = "intent_signal"
SIGNAL_TYPE_TASK = "task_signal"
SIGNAL_TYPE_ENTITY = "entity_signal"
SIGNAL_TYPE_OUTCOME = "outcome_signal"
SIGNAL_TYPE_CORRECTION = "correction_signal"
SIGNAL_TYPE_REVIEW = "review_signal"
SIGNAL_TYPE_SECURITY = "security_signal"


# ============================================================
# SECTION 01.06 - ENTITY TYPES
# ============================================================

ENTITY_TYPE_PLAYER = "player"
ENTITY_TYPE_TEAM = "team"
ENTITY_TYPE_OUTCOME = "outcome"
ENTITY_TYPE_STAT = "stat"
ENTITY_TYPE_GAME = "game"
ENTITY_TYPE_UNKNOWN = "unknown"


# ============================================================
# SECTION 01.07 - MEMORY ENGINE CONFIGURATION
# ============================================================

MEMORY_ENGINE_CONFIGURATION = {
    "database_storage_enabled": True,
    "fallback_storage_enabled": True,
    "learning_signals_enabled": True,
    "training_examples_enabled": True,
    "alias_learning_enabled": True,
    "security_event_memory_enabled": True,
    "auto_trust_alias_usage_threshold": 5,
    "approved_for_training_default": False,
    "review_uncertain_examples": True,
}

# ============================================================
# SECTION 02 - MEMORY TEXT CLEANING
# FILE: 04_ai/interaction_memory.py
# PURPOSE: safely trim and normalize stored text
# ============================================================

def clean_memory_text(value: str | None) -> str:
    if not value:
        return ""

    cleaned_value = str(value).strip()

    if len(cleaned_value) > MAX_MEMORY_TEXT_LENGTH:
        cleaned_value = cleaned_value[:MAX_MEMORY_TEXT_LENGTH]

    return cleaned_value


# ============================================================
# SECTION 03 - MEMORY SUMMARY BUILDER
# FILE: 04_ai/interaction_memory.py
# PURPOSE: create compact summaries for future retrieval
# ============================================================

def build_interaction_summary(
    user_message: str,
    assistant_response: str,
    intent: str | None = None,
    team: str | None = None,
    player: str | None = None,
    outcome: str | None = None,
) -> str:
    summary_parts = []

    if intent:
        summary_parts.append(f"Intent: {intent}")

    if team:
        summary_parts.append(f"Team: {team}")

    if player:
        summary_parts.append(f"Player: {player}")

    if outcome:
        summary_parts.append(f"Outcome: {outcome}")

    if not summary_parts:
        summary_parts.append("General baseball chat interaction")

    return " | ".join(summary_parts)


# ============================================================
# SECTION 04 - MEMORY RECORD BUILDER
# FILE: 04_ai/interaction_memory.py
# PURPOSE: build structured memory entries from chat routing
# ============================================================

def build_chat_memory_record(
    user_message: str,
    assistant_response: str,
    intent: str | None = None,
    semantic: dict | None = None,
    security: dict | None = None,
    category: str = DEFAULT_MEMORY_CATEGORY,
) -> dict:
    semantic = semantic or {}
    security = security or {}

    team = semantic.get("team")
    player = semantic.get("player")
    outcome = semantic.get("outcome")

    summary = build_interaction_summary(
        user_message=user_message,
        assistant_response=assistant_response,
        intent=intent,
        team=team,
        player=player,
        outcome=outcome,
    )

    return {
        "status": MEMORY_STATUS_STORED,
        "category": category,
        "user_message": clean_memory_text(user_message),
        "assistant_response": clean_memory_text(assistant_response),
        "summary": summary,
        "intent": intent,
        "team": team,
        "player": player,
        "outcome": outcome,
        "semantic": semantic,
        "security": security,
        "importance_score": calculate_memory_importance(
            intent=intent,
            semantic=semantic,
            security=security,
        ),
    }


# ============================================================
# SECTION 05 - MEMORY IMPORTANCE SCORING
# FILE: 04_ai/interaction_memory.py
# PURPOSE: rank which interactions matter most for future AI
# ============================================================

def calculate_memory_importance(
    intent: str | None = None,
    semantic: dict | None = None,
    security: dict | None = None,
) -> int:
    semantic = semantic or {}
    security = security or {}

    if security.get("blocked"):
        return 20

    score = 35

    if intent:
        score += 10

    if semantic.get("team"):
        score += 10

    if semantic.get("player"):
        score += 10

    if semantic.get("outcome"):
        score += 10

    if semantic.get("players"):
        score += 5

    if semantic.get("teams"):
        score += 5

    return min(score, 95)


# ============================================================
# SECTION 06 - DATABASE-BACKED MEMORY STORE
# FILE: 04_ai/core/interaction_memory.py
# PURPOSE: permanently store chatbot interactions, learning
# signals, training examples, and alias candidates in SQLAlchemy
# while preserving an emergency in-memory fallback
# ============================================================

import json
from datetime import datetime


AISP2_CHAT_MEMORY_FALLBACK_STORE: list[dict] = []


def get_memory_timestamp() -> str:
    return datetime.utcnow().isoformat()


def serialize_memory_json(value: dict | list | None) -> str | None:
    if value is None:
        return None

    try:
        return json.dumps(
            value,
            default=str,
            ensure_ascii=False,
        )

    except Exception:
        return json.dumps(
            {
                "serialization_error": True,
                "value": str(value),
            },
            ensure_ascii=False,
        )


def store_fallback_memory_record(record: dict, reason: str) -> dict:
    AISP2_CHAT_MEMORY_FALLBACK_STORE.append(record)

    return {
        "status": "fallback_stored",
        "reason": reason,
        "fallback_count": len(AISP2_CHAT_MEMORY_FALLBACK_STORE),
        "latest_summary": record.get("summary"),
    }


def store_chat_memory_record(record: dict) -> dict:
    if not record:
        return {
            "status": MEMORY_STATUS_SKIPPED,
            "reason": "empty_record",
        }

    try:
        from database import managed_database_session
        from models import ChatMemory
        from models import LearningSignal
        from models import TrainingExample
        from models import EntityAlias

        with managed_database_session() as database_session:
            chat_memory = ChatMemory(
                conversation_id=record.get("conversation_id"),
                session_id=record.get("session_id"),
                user_message=record.get("user_message", ""),
                assistant_response=record.get("assistant_response", ""),
                detected_intent=record.get("intent"),
                detected_task=record.get("task"),
                detected_team=record.get("team"),
                detected_player=record.get("player"),
                detected_outcome=record.get("outcome"),
                nlu_confidence=record.get("nlu_confidence"),
                importance_score=record.get("importance_score"),
                raw_context_json=serialize_memory_json(record.get("context")),
                raw_nlu_json=serialize_memory_json(record.get("nlu")),
                raw_semantic_json=serialize_memory_json(record.get("semantic")),
                created_at=get_memory_timestamp(),
            )

            database_session.add(chat_memory)
            database_session.flush()

            learning_signals = build_memory_learning_signals(
                record=record,
                chat_memory_id=chat_memory.id,
            )

            for signal in learning_signals:
                database_session.add(
                    LearningSignal(
                        chat_memory_id=chat_memory.id,
                        signal_type=signal.get("signal_type", "unknown"),
                        signal_status=signal.get("signal_status", "ready"),
                        intent=signal.get("intent"),
                        task=signal.get("task"),
                        entity_type=signal.get("entity_type"),
                        entity_value=signal.get("entity_value"),
                        outcome=signal.get("outcome"),
                        confidence=signal.get("confidence"),
                        review_needed=signal.get("review_needed", False),
                        reason=signal.get("reason"),
                        raw_signal_json=serialize_memory_json(signal),
                        created_at=get_memory_timestamp(),
                    )
                )

            training_example = build_memory_training_example(
                record=record,
                chat_memory_id=chat_memory.id,
            )

            database_session.add(
                TrainingExample(
                    chat_memory_id=chat_memory.id,
                    input_text=training_example["input_text"],
                    target_intent=training_example.get("target_intent"),
                    target_task=training_example.get("target_task"),
                    target_team=training_example.get("target_team"),
                    target_player=training_example.get("target_player"),
                    target_outcome=training_example.get("target_outcome"),
                    correction_json=serialize_memory_json(
                        training_example.get("corrections")
                    ),
                    target_json=serialize_memory_json(
                        training_example.get("target")
                    ),
                    quality_score=training_example.get("quality_score"),
                    review_needed=training_example.get("review_needed", False),
                    approved_for_training=False,
                    created_at=get_memory_timestamp(),
                )
            )

            alias_candidates = build_memory_alias_candidates(record)

            for alias in alias_candidates:
                existing_alias = (
                    database_session.query(EntityAlias)
                    .filter(EntityAlias.entity_type == alias["entity_type"])
                    .filter(EntityAlias.canonical_value == alias["canonical_value"])
                    .filter(EntityAlias.alias_value == alias["alias_value"])
                    .first()
                )

                if existing_alias:
                    existing_alias.usage_count += 1
                    existing_alias.last_seen_at = get_memory_timestamp()

                    if existing_alias.usage_count >= 5:
                        existing_alias.is_trusted = True
                        existing_alias.review_needed = False

                else:
                    database_session.add(
                        EntityAlias(
                            entity_type=alias["entity_type"],
                            canonical_value=alias["canonical_value"],
                            alias_value=alias["alias_value"],
                            source="chat_memory",
                            confidence=alias.get("confidence", 0.65),
                            usage_count=1,
                            confirmation_count=0,
                            is_active=True,
                            is_trusted=False,
                            review_needed=True,
                            created_at=get_memory_timestamp(),
                            updated_at=get_memory_timestamp(),
                            last_seen_at=get_memory_timestamp(),
                        )
                    )

            return {
                "status": MEMORY_STATUS_STORED,
                "storage": "database",
                "chat_memory_id": chat_memory.id,
                "learning_signal_count": len(learning_signals),
                "training_example_created": True,
                "alias_candidate_count": len(alias_candidates),
                "latest_summary": record.get("summary"),
            }

    except Exception as error:
        return store_fallback_memory_record(
            record=record,
            reason=f"database_memory_failed: {error}",
        )


def get_recent_chat_memory(limit: int = 10) -> list[dict]:
    if limit <= 0:
        limit = 10

    try:
        from database import managed_database_session
        from models import ChatMemory

        with managed_database_session() as database_session:
            rows = (
                database_session.query(ChatMemory)
                .order_by(ChatMemory.id.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": row.id,
                    "user_message": row.user_message,
                    "assistant_response": row.assistant_response,
                    "intent": row.detected_intent,
                    "task": row.detected_task,
                    "team": row.detected_team,
                    "player": row.detected_player,
                    "outcome": row.detected_outcome,
                    "importance_score": row.importance_score,
                    "created_at": row.created_at,
                }
                for row in rows
            ]

    except Exception:
        return AISP2_CHAT_MEMORY_FALLBACK_STORE[-limit:]


# ============================================================
# SECTION 07 - CHAT MEMORY PIPELINE
# FILE: 04_ai/core/interaction_memory.py
# PURPOSE: one-call helper used by main.py after every chat reply
# to permanently store conversations and learning artifacts
# ============================================================

def build_memory_learning_signals(
    record: dict,
    chat_memory_id: int | None = None,
) -> list[dict]:
    signals = []

    if record.get("intent") or record.get("task"):
        signals.append(
            {
                "chat_memory_id": chat_memory_id,
                "signal_type": "intent_signal",
                "signal_status": "ready",
                "intent": record.get("intent"),
                "task": record.get("task"),
                "confidence": record.get("nlu_confidence"),
                "review_needed": False,
                "reason": "intent_or_task_detected",
            }
        )

    if record.get("team"):
        signals.append(
            {
                "chat_memory_id": chat_memory_id,
                "signal_type": "entity_signal",
                "signal_status": "ready",
                "entity_type": "team",
                "entity_value": record.get("team"),
                "confidence": record.get("nlu_confidence"),
                "review_needed": False,
                "reason": "team_detected",
            }
        )

    if record.get("player"):
        signals.append(
            {
                "chat_memory_id": chat_memory_id,
                "signal_type": "entity_signal",
                "signal_status": "ready",
                "entity_type": "player",
                "entity_value": record.get("player"),
                "confidence": record.get("nlu_confidence"),
                "review_needed": False,
                "reason": "player_detected",
            }
        )

    if record.get("outcome"):
        signals.append(
            {
                "chat_memory_id": chat_memory_id,
                "signal_type": "outcome_signal",
                "signal_status": "ready",
                "outcome": record.get("outcome"),
                "confidence": record.get("nlu_confidence"),
                "review_needed": False,
                "reason": "outcome_detected",
            }
        )

    if record.get("importance_score", 0) < 50:
        signals.append(
            {
                "chat_memory_id": chat_memory_id,
                "signal_type": "review_signal",
                "signal_status": "review_needed",
                "confidence": record.get("nlu_confidence"),
                "review_needed": True,
                "reason": "low_importance_or_uncertain_interaction",
            }
        )

    return signals


def build_memory_training_example(
    record: dict,
    chat_memory_id: int | None = None,
) -> dict:
    target = {
        "intent": record.get("intent"),
        "task": record.get("task"),
        "team": record.get("team"),
        "player": record.get("player"),
        "outcome": record.get("outcome"),
        "semantic": record.get("semantic", {}),
    }

    quality_score = float(record.get("importance_score", 50))

    review_needed = quality_score < 60

    return {
        "chat_memory_id": chat_memory_id,
        "input_text": record.get("user_message", ""),
        "target_intent": record.get("intent"),
        "target_task": record.get("task"),
        "target_team": record.get("team"),
        "target_player": record.get("player"),
        "target_outcome": record.get("outcome"),
        "target": target,
        "corrections": (
            record.get("semantic", {})
            .get("entity_report", {})
            .get("corrections", {})
        ),
        "quality_score": quality_score,
        "review_needed": review_needed,
    }


def build_memory_alias_candidates(record: dict) -> list[dict]:
    semantic = record.get("semantic", {}) or {}
    entity_report = semantic.get("entity_report", {}) or {}
    corrections_report = entity_report.get("corrections", {}) or {}
    corrections = corrections_report.get("corrections", []) or []

    alias_candidates = []

    for correction in corrections:
        original = clean_memory_text(correction.get("original"))
        corrected = clean_memory_text(correction.get("corrected"))

        if not original or not corrected:
            continue

        if original.lower() == corrected.lower():
            continue

        alias_candidates.append(
            {
                "entity_type": correction.get("entity_type", "unknown"),
                "canonical_value": corrected,
                "alias_value": original,
                "confidence": correction.get("confidence", 0.65),
            }
        )

    return alias_candidates


def remember_chat_interaction(
    user_message: str,
    chat_response: dict,
) -> dict:
    if not chat_response:
        return {
            "status": MEMORY_STATUS_SKIPPED,
            "reason": "empty_chat_response",
        }

    context = chat_response.get("context", {}) or {}
    nlu = chat_response.get("nlu", {}) or {}
    semantic = chat_response.get("semantic", {}) or {}

    record = build_chat_memory_record(
        user_message=user_message,
        assistant_response=chat_response.get("reply", ""),
        intent=chat_response.get("intent"),
        semantic=semantic,
        security=chat_response.get("security", {}),
    )

    record["task"] = context.get("task") or nlu.get("task")
    record["context"] = context
    record["nlu"] = nlu
    record["nlu_confidence"] = nlu.get("confidence")

    return store_chat_memory_record(record)


# ============================================================
# SECTION 08 - MEMORY ROADMAP
# FILE: 04_ai/core/interaction_memory.py
# PURPOSE: database, aliases, embeddings, RAG, and feedback
# learning roadmap
# ============================================================

"""
08.01 Database-backed ChatMemory storage is active.
08.02 LearningSignal creation is active.
08.03 TrainingExample creation is active.
08.04 EntityAlias candidate storage is active.
08.05 Add session_id and user_id.
08.06 Add helpful/not-helpful feedback UI.
08.07 Add embeddings for semantic retrieval.
08.08 Add vector database search.
08.09 Add RAG memory retrieval before answering.
08.10 Add memory summarization.
08.11 Add long-term project knowledge extraction.
08.12 Add alias trust promotion dashboard.
"""