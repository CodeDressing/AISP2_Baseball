# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/security_guardrails.py
# PURPOSE: chat input safety, message cleanup, unsafe request
# detection, safe fallback responses, and future AI security
# policy expansion for AISP2
# ============================================================


# ============================================================
# SECTION 01 - ENTERPRISE SECURITY CONFIGURATION
# FILE: 04_ai/core/security_guardrails.py
# PURPOSE: central security configuration for AISP2 chat,
# NLP pipeline, prediction engine, public API endpoints,
# future authentication, abuse detection, and enterprise
# request validation.
# ============================================================

from __future__ import annotations

import re

# ============================================================
# SECTION 01.01 - CHAT LIMITS
# ============================================================

MAX_CHAT_MESSAGE_LENGTH = 750

MAX_PLAYER_NAME_LENGTH = 100

MAX_TEAM_NAME_LENGTH = 100

MAX_SEARCH_RESULTS = 25

MAX_CONVERSATION_DEPTH = 100


# ============================================================
# SECTION 01.02 - REQUEST CLASSIFICATION
# ============================================================

REQUEST_TYPE_CHAT = "chat"

REQUEST_TYPE_PLAYER = "player_lookup"

REQUEST_TYPE_TEAM = "team_lookup"

REQUEST_TYPE_PREDICTION = "prediction"

REQUEST_TYPE_DATABASE = "database"

REQUEST_TYPE_ADMIN = "admin"

REQUEST_TYPE_UNKNOWN = "unknown"


# ============================================================
# SECTION 01.03 - HIGH RISK PROMPT PATTERNS
# ============================================================

BLOCKED_CHAT_PHRASES = [

    "ignore previous instructions",

    "ignore all previous instructions",

    "ignore system",

    "ignore developer",

    "system prompt",

    "developer prompt",

    "developer message",

    "hidden prompt",

    "hidden instructions",

    "reveal your instructions",

    "reveal your system",

    "show system prompt",

    "jailbreak",

    "bypass safety",

    "disable safety",

    "override safety",

    "drop database",

    "delete database",

    "delete table",

    "truncate table",

    "erase files",

    "delete all files",

    "execute command",

    "run shell",

    "run terminal",

    "run powershell",

    "cmd.exe",

    "bash -c",

    "python -c",

    "api key",

    "secret key",

    "private key",

    "password",

    "token",

    "session cookie",

]


# ============================================================
# SECTION 01.04 - SAFE BASEBALL DOMAINS
# ============================================================

BASEBALL_TOPICS = {

    "players",

    "teams",

    "games",

    "matchups",

    "probability",

    "prediction",

    "statistics",

    "rosters",

    "pitchers",

    "batters",

    "stadiums",

    "schedule",

    "standings",

    "statcast",

    "sabermetrics",

    "fantasy",

    "injuries",

    "transactions",

}


# ============================================================
# SECTION 01.05 - NORMALIZATION EXPRESSIONS
# ============================================================

MULTI_SPACE_PATTERN = re.compile(r"\s+")

NON_PRINTABLE_PATTERN = re.compile(
    r"[\x00-\x08\x0B\x0C\x0E-\x1F]"
)


# ============================================================
# SECTION 01.06 - SECURITY CONFIGURATION
# ============================================================

SECURITY_CONFIGURATION = {

    "public_chat_enabled": True,

    "persistent_memory_enabled": True,

    "continuous_learning_enabled": True,

    "prediction_requests_enabled": True,

    "database_lookup_enabled": True,

    "warehouse_lookup_enabled": True,

    "allow_fallback_profiles": True,

    "allow_live_api": True,

    "strict_prompt_injection_detection": True,

    "strict_secret_detection": True,

}
# ============================================================
# SECTION 02 - MESSAGE CLEANING
# FILE: 04_ai/security_guardrails.py
# PURPOSE: normalize and limit chat input before AI routing
# ============================================================

def clean_chat_message(message: str | None) -> str:
    if not message:
        return ""

    cleaned_message = str(message).strip()

    if len(cleaned_message) > MAX_CHAT_MESSAGE_LENGTH:
        cleaned_message = cleaned_message[:MAX_CHAT_MESSAGE_LENGTH]

    return cleaned_message


# ============================================================
# SECTION 03 - UNSAFE REQUEST DETECTION
# FILE: 04_ai/security_guardrails.py
# PURPOSE: detect unsafe, system-bypass, or destructive requests
# ============================================================

def is_blocked_chat_message(message: str) -> bool:
    lowered_message = message.lower()

    return any(
        phrase in lowered_message
        for phrase in BLOCKED_CHAT_PHRASES
    )


def classify_security_reason(message: str) -> str:
    lowered_message = message.lower()

    if any(
        phrase in lowered_message
        for phrase in [
            "ignore previous instructions",
            "system prompt",
            "developer message",
            "reveal your instructions",
            "jailbreak",
        ]
    ):
        return "instruction_bypass_attempt"

    if any(
        phrase in lowered_message
        for phrase in [
            "drop database",
            "delete database",
            "delete all files",
            "erase files",
        ]
    ):
        return "destructive_system_request"

    if any(
        phrase in lowered_message
        for phrase in [
            "api key",
            "secret key",
            "password",
            "steal",
        ]
    ):
        return "credential_or_secret_request"

    if any(
        phrase in lowered_message
        for phrase in [
            "run shell",
            "execute command",
            "run powershell",
            "run terminal",
        ]
    ):
        return "unsafe_execution_request"

    return "blocked_request"


# ============================================================
# SECTION 04 - SAFE RESPONSE BUILDER
# FILE: 04_ai/security_guardrails.py
# PURPOSE: return safe user-facing responses for blocked input
# ============================================================

def build_safe_chat_response(reason: str = "blocked_request") -> dict:
    return {
        "reply": (
            "I can help with baseball teams, players, rosters, stats, "
            "matchups, and probability-style analysis. I cannot help with "
            "unsafe system, database, credential, or instruction-bypass requests."
        ),
        "intent": "security_guardrail",
        "security": {
            "blocked": True,
            "reason": reason,
        },
    }


# ============================================================
# SECTION 05 - SECURITY REPORT
# FILE: 04_ai/security_guardrails.py
# PURPOSE: produce reusable diagnostics for chat routing
# ============================================================

def build_chat_security_report(message: str | None) -> dict:
    cleaned_message = clean_chat_message(message)

    blocked = is_blocked_chat_message(
        cleaned_message,
    )

    reason = (
        classify_security_reason(cleaned_message)
        if blocked
        else None
    )

    return {
        "cleaned_message": cleaned_message,
        "blocked": blocked,
        "reason": reason,
        "message_length": len(cleaned_message),
        "max_length": MAX_CHAT_MESSAGE_LENGTH,
    }


# ============================================================
# SECTION 06 - FUTURE SECURITY ROADMAP
# FILE: 04_ai/security_guardrails.py
# PURPOSE: future safety, auth, rate limiting, and abuse controls
# ============================================================

"""
06.01 Add rate limiting by IP/session.
06.02 Add request logging for abuse diagnostics.
06.03 Add structured security event table.
06.04 Add authenticated admin-only endpoints.
06.05 Add prompt-injection pattern scoring.
06.06 Add SQL/action separation policy.
06.07 Add read-only mode for public chat.
06.08 Add endpoint-level permissions.
06.09 Add production secret scanning.
06.10 Add model-output safety checks.
"""