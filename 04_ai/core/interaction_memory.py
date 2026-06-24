# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/interaction_memory.py
# PURPOSE: lightweight chatbot learning memory for storing
# user questions, assistant responses, detected intent, entities,
# confidence, and future RAG/feedback learning signals
# ============================================================


# ============================================================
# SECTION 01 - MEMORY CONSTANTS
# FILE: 04_ai/interaction_memory.py
# PURPOSE: define memory defaults and categories
# ============================================================

DEFAULT_MEMORY_CATEGORY = "baseball_chat"

MEMORY_STATUS_STORED = "stored"
MEMORY_STATUS_SKIPPED = "skipped"

MAX_MEMORY_TEXT_LENGTH = 2000


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
# SECTION 06 - IN-MEMORY DEVELOPMENT STORE
# FILE: 04_ai/interaction_memory.py
# PURPOSE: temporary development memory before database-backed
# persistent memory is connected
# ============================================================

AISP2_CHAT_MEMORY_STORE: list[dict] = []


def store_chat_memory_record(record: dict) -> dict:
    if not record:
        return {
            "status": MEMORY_STATUS_SKIPPED,
            "reason": "empty_record",
        }

    AISP2_CHAT_MEMORY_STORE.append(record)

    return {
        "status": MEMORY_STATUS_STORED,
        "stored_count": len(AISP2_CHAT_MEMORY_STORE),
        "latest_summary": record.get("summary"),
    }


def get_recent_chat_memory(limit: int = 10) -> list[dict]:
    if limit <= 0:
        limit = 10

    return AISP2_CHAT_MEMORY_STORE[-limit:]


# ============================================================
# SECTION 07 - CHAT MEMORY PIPELINE
# FILE: 04_ai/interaction_memory.py
# PURPOSE: one-call helper used by main.py after every chat reply
# ============================================================

def remember_chat_interaction(
    user_message: str,
    chat_response: dict,
) -> dict:
    if not chat_response:
        return {
            "status": MEMORY_STATUS_SKIPPED,
            "reason": "empty_chat_response",
        }

    record = build_chat_memory_record(
        user_message=user_message,
        assistant_response=chat_response.get("reply", ""),
        intent=chat_response.get("intent"),
        semantic=chat_response.get("semantic", {}),
        security=chat_response.get("security", {}),
    )

    return store_chat_memory_record(record)


# ============================================================
# SECTION 08 - FUTURE MEMORY ROADMAP
# FILE: 04_ai/interaction_memory.py
# PURPOSE: future database, embeddings, RAG, and feedback learning
# ============================================================

"""
08.01 Add database-backed ChatMemory model.
08.02 Store session_id and user_id.
08.03 Add created_at timestamp.
08.04 Add helpful/not-helpful feedback.
08.05 Add correction tracking.
08.06 Add embeddings for semantic retrieval.
08.07 Add vector database search.
08.08 Add RAG memory retrieval before answering.
08.09 Add memory summarization.
08.10 Add long-term project knowledge extraction.
"""