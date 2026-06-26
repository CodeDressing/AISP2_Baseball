# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/core/learning_engine.py
# PURPOSE: self-learning signal engine for turning every user
# chatbot interaction into structured NLP improvement data,
# future training examples, alias candidates, and RAG memory
# ============================================================


# ============================================================
# SECTION 01 - LEARNING CONSTANTS
# ============================================================

LEARNING_ENGINE_VERSION = "phase_6_part_1"

LEARNING_STATUS_READY = "ready"
LEARNING_STATUS_SKIPPED = "skipped"
LEARNING_STATUS_REVIEW_NEEDED = "review_needed"

SIGNAL_TYPE_INTENT = "intent_signal"
SIGNAL_TYPE_ENTITY = "entity_signal"
SIGNAL_TYPE_OUTCOME = "outcome_signal"
SIGNAL_TYPE_FAILURE = "failure_signal"
SIGNAL_TYPE_ALIAS = "alias_candidate"
SIGNAL_TYPE_TRAINING = "training_example"

MAX_LEARNING_TEXT_LENGTH = 3000


# ============================================================
# SECTION 02 - TEXT NORMALIZATION
# ============================================================

def clean_learning_text(value: str | None) -> str:
    if not value:
        return ""

    cleaned_value = str(value).strip()

    if len(cleaned_value) > MAX_LEARNING_TEXT_LENGTH:
        cleaned_value = cleaned_value[:MAX_LEARNING_TEXT_LENGTH]

    return cleaned_value


def normalize_learning_text(value: str | None) -> str:
    return (
        clean_learning_text(value)
        .lower()
        .replace("?", " ")
        .replace("!", " ")
        .replace(".", " ")
        .replace(",", " ")
        .replace("'", "")
        .replace('"', "")
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )


# ============================================================
# SECTION 03 - INTERACTION EXTRACTION
# ============================================================

def extract_learning_fields(
    user_message: str,
    chat_response: dict | None = None,
) -> dict:
    chat_response = chat_response or {}

    semantic = chat_response.get("semantic", {}) or {}
    context = chat_response.get("context", {}) or {}
    nlu = chat_response.get("nlu", {}) or {}

    return {
        "user_message": clean_learning_text(user_message),
        "assistant_response": clean_learning_text(chat_response.get("reply", "")),
        "intent": chat_response.get("intent") or context.get("task") or nlu.get("task"),
        "task": context.get("task") or nlu.get("task"),
        "team": context.get("team") or semantic.get("team"),
        "player": context.get("player") or semantic.get("player"),
        "outcome": context.get("outcome") or semantic.get("outcome") or nlu.get("outcome"),
        "teams": context.get("teams") or semantic.get("teams") or [],
        "players": context.get("players") or semantic.get("players") or [],
        "nlu": nlu,
        "context": context,
        "semantic": semantic,
        "memory": chat_response.get("memory", {}),
    }


# ============================================================
# SECTION 04 - FAILURE DETECTION
# ============================================================

def detect_learning_failure(
    extracted: dict,
) -> dict:
    user_message = normalize_learning_text(
        extracted.get("user_message"),
    )

    assistant_response = normalize_learning_text(
        extracted.get("assistant_response"),
    )

    failure_reasons = []

    if not extracted.get("assistant_response"):
        failure_reasons.append("empty_assistant_response")

    if "need a little more structure" in assistant_response:
        failure_reasons.append("fallback_response")

    if "could not find" in assistant_response:
        failure_reasons.append("entity_not_found")

    if "not available" in assistant_response:
        failure_reasons.append("data_unavailable")

    if "try asking" in assistant_response and len(user_message.split()) >= 5:
        failure_reasons.append("overly_generic_guidance")

    if extracted.get("nlu", {}).get("confidence", 100) < 55:
        failure_reasons.append("low_nlu_confidence")

    return {
        "has_failure": len(failure_reasons) > 0,
        "failure_reasons": failure_reasons,
        "status": LEARNING_STATUS_REVIEW_NEEDED if failure_reasons else LEARNING_STATUS_READY,
    }


# ============================================================
# SECTION 05 - ALIAS CANDIDATE DETECTION
# ============================================================

def build_alias_candidates(
    extracted: dict,
) -> list[dict]:
    message = normalize_learning_text(
        extracted.get("user_message"),
    )

    candidates = []

    known_player = extracted.get("player")
    known_team = extracted.get("team")

    if known_player:
        normalized_player = normalize_learning_text(known_player)

        if normalized_player not in message:
            candidates.append(
                {
                    "type": SIGNAL_TYPE_ALIAS,
                    "entity_type": "player",
                    "canonical_value": known_player,
                    "observed_phrase": extracted.get("user_message"),
                    "reason": "player_detected_without_exact_phrase",
                }
            )

    if known_team:
        normalized_team = normalize_learning_text(known_team)

        if normalized_team not in message:
            candidates.append(
                {
                    "type": SIGNAL_TYPE_ALIAS,
                    "entity_type": "team",
                    "canonical_value": known_team,
                    "observed_phrase": extracted.get("user_message"),
                    "reason": "team_detected_without_exact_phrase",
                }
            )

    return candidates


# ============================================================
# SECTION 06 - TRAINING EXAMPLE BUILDER
# ============================================================

def build_training_example(
    extracted: dict,
    failure_report: dict,
) -> dict:
    return {
        "type": SIGNAL_TYPE_TRAINING,
        "input_text": extracted.get("user_message"),
        "target": {
            "intent": extracted.get("intent"),
            "task": extracted.get("task"),
            "team": extracted.get("team"),
            "player": extracted.get("player"),
            "outcome": extracted.get("outcome"),
            "teams": extracted.get("teams", []),
            "players": extracted.get("players", []),
        },
        "quality": {
            "review_needed": failure_report.get("has_failure", False),
            "failure_reasons": failure_report.get("failure_reasons", []),
            "nlu_confidence": extracted.get("nlu", {}).get("confidence"),
        },
        "source": "chat_interaction",
        "engine_version": LEARNING_ENGINE_VERSION,
    }


# ============================================================
# SECTION 07 - LEARNING SIGNAL BUILDER
# ============================================================

def build_learning_signals(
    extracted: dict,
    failure_report: dict,
) -> list[dict]:
    signals = []

    if extracted.get("intent") or extracted.get("task"):
        signals.append(
            {
                "type": SIGNAL_TYPE_INTENT,
                "intent": extracted.get("intent"),
                "task": extracted.get("task"),
                "message": extracted.get("user_message"),
            }
        )

    if extracted.get("team") or extracted.get("player"):
        signals.append(
            {
                "type": SIGNAL_TYPE_ENTITY,
                "team": extracted.get("team"),
                "player": extracted.get("player"),
                "teams": extracted.get("teams", []),
                "players": extracted.get("players", []),
                "message": extracted.get("user_message"),
            }
        )

    if extracted.get("outcome"):
        signals.append(
            {
                "type": SIGNAL_TYPE_OUTCOME,
                "outcome": extracted.get("outcome"),
                "message": extracted.get("user_message"),
            }
        )

    if failure_report.get("has_failure"):
        signals.append(
            {
                "type": SIGNAL_TYPE_FAILURE,
                "reasons": failure_report.get("failure_reasons", []),
                "message": extracted.get("user_message"),
                "assistant_response": extracted.get("assistant_response"),
            }
        )

    signals.extend(
        build_alias_candidates(
            extracted,
        )
    )

    signals.append(
        build_training_example(
            extracted=extracted,
            failure_report=failure_report,
        )
    )

    return signals


# ============================================================
# SECTION 08 - LEARNING REPORT BUILDER
# ============================================================

def build_learning_report(
    user_message: str,
    chat_response: dict | None = None,
) -> dict:
    extracted = extract_learning_fields(
        user_message=user_message,
        chat_response=chat_response,
    )

    if not extracted.get("user_message"):
        return {
            "status": LEARNING_STATUS_SKIPPED,
            "reason": "empty_user_message",
            "engine_version": LEARNING_ENGINE_VERSION,
        }

    failure_report = detect_learning_failure(
        extracted,
    )

    signals = build_learning_signals(
        extracted=extracted,
        failure_report=failure_report,
    )

    return {
        "status": failure_report.get("status", LEARNING_STATUS_READY),
        "engine_version": LEARNING_ENGINE_VERSION,
        "extracted": extracted,
        "failure_report": failure_report,
        "signals": signals,
        "signal_count": len(signals),
        "training_example": build_training_example(
            extracted=extracted,
            failure_report=failure_report,
        ),
    }


# ============================================================
# SECTION 09 - IN-MEMORY LEARNING STORE
# ============================================================

AISP2_LEARNING_SIGNAL_STORE: list[dict] = []


def store_learning_report(
    learning_report: dict,
) -> dict:
    if not learning_report:
        return {
            "status": LEARNING_STATUS_SKIPPED,
            "reason": "empty_learning_report",
        }

    AISP2_LEARNING_SIGNAL_STORE.append(
        learning_report,
    )

    return {
        "status": "stored",
        "stored_count": len(AISP2_LEARNING_SIGNAL_STORE),
        "latest_status": learning_report.get("status"),
        "signal_count": learning_report.get("signal_count", 0),
    }


def get_recent_learning_reports(
    limit: int = 10,
) -> list[dict]:
    if limit <= 0:
        limit = 10

    return AISP2_LEARNING_SIGNAL_STORE[-limit:]


# ============================================================
# SECTION 10 - ONE-CALL LEARNING PIPELINE
# ============================================================

def learn_from_chat_interaction(
    user_message: str,
    chat_response: dict | None = None,
) -> dict:
    learning_report = build_learning_report(
        user_message=user_message,
        chat_response=chat_response,
    )

    storage_status = store_learning_report(
        learning_report,
    )

    return {
        "learning_report": learning_report,
        "storage": storage_status,
    }


# ============================================================
# SECTION 11 - FUTURE DATABASE AND MODEL ROADMAP
# ============================================================

"""
11.01 Store learning reports in database table: learning_signals.
11.02 Store training examples in database table: training_examples.
11.03 Store user questions in database table: chat_memory.
11.04 Add feedback labels: helpful, incorrect, incomplete, unsafe.
11.05 Add human review status for failed interactions.
11.06 Export curated training examples to JSONL.
11.07 Add fuzzy alias promotion from repeated misspellings.
11.08 Add embeddings for semantic retrieval.
11.09 Add RAG memory retrieval before chat response.
11.10 Add supervised fine-tuning export after enough clean examples.
"""