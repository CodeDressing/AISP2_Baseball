# ============================================================
# AISP2 BASEBALL
# FILE: 05_chat_workspace/components/conversation_manager.py
# PURPOSE: conversation state management for the persistent
# floating AISP2 AI assistant workspace
# ============================================================


# ============================================================
# SECTION 01 - CONVERSATION CONSTANTS
# ============================================================

DEFAULT_CONVERSATION_TITLE = "AISP2 Chat"
DEFAULT_CONVERSATION_STATUS = "active"

MESSAGE_ROLE_USER = "user"
MESSAGE_ROLE_ASSISTANT = "assistant"
MESSAGE_ROLE_SYSTEM = "system"

MAX_CONVERSATION_MESSAGES = 200
MAX_MESSAGE_TEXT_LENGTH = 3000


# ============================================================
# SECTION 02 - TEXT SAFETY HELPERS
# ============================================================

def clean_conversation_text(value: str | None) -> str:
    if not value:
        return ""

    cleaned_value = str(value).strip()

    if len(cleaned_value) > MAX_MESSAGE_TEXT_LENGTH:
        cleaned_value = cleaned_value[:MAX_MESSAGE_TEXT_LENGTH]

    return cleaned_value


# ============================================================
# SECTION 03 - MESSAGE BUILDERS
# ============================================================

def build_conversation_message(
    role: str,
    content: str,
    metadata: dict | None = None,
) -> dict:
    metadata = metadata or {}

    if role not in {
        MESSAGE_ROLE_USER,
        MESSAGE_ROLE_ASSISTANT,
        MESSAGE_ROLE_SYSTEM,
    }:
        role = MESSAGE_ROLE_SYSTEM

    return {
        "role": role,
        "content": clean_conversation_text(content),
        "metadata": metadata,
    }


def build_user_message(
    content: str,
    metadata: dict | None = None,
) -> dict:
    return build_conversation_message(
        role=MESSAGE_ROLE_USER,
        content=content,
        metadata=metadata,
    )


def build_assistant_message(
    content: str,
    metadata: dict | None = None,
) -> dict:
    return build_conversation_message(
        role=MESSAGE_ROLE_ASSISTANT,
        content=content,
        metadata=metadata,
    )


# ============================================================
# SECTION 04 - CONVERSATION RECORD BUILDER
# ============================================================

def build_conversation_record(
    conversation_id: str,
    title: str | None = None,
    status: str | None = None,
    messages: list[dict] | None = None,
    metadata: dict | None = None,
) -> dict:
    return {
        "conversation_id": conversation_id,
        "title": title or DEFAULT_CONVERSATION_TITLE,
        "status": status or DEFAULT_CONVERSATION_STATUS,
        "messages": messages or [],
        "metadata": metadata or {},
        "message_count": len(messages or []),
    }


# ============================================================
# SECTION 05 - MESSAGE APPEND HELPERS
# ============================================================

def append_message_to_conversation(
    conversation: dict,
    message: dict,
) -> dict:
    messages = conversation.get(
        "messages",
        [],
    )

    messages.append(message)

    if len(messages) > MAX_CONVERSATION_MESSAGES:
        messages = messages[-MAX_CONVERSATION_MESSAGES:]

    conversation["messages"] = messages
    conversation["message_count"] = len(messages)

    return conversation


def append_user_and_assistant_exchange(
    conversation: dict,
    user_message: str,
    assistant_response: str,
    metadata: dict | None = None,
) -> dict:
    metadata = metadata or {}

    conversation = append_message_to_conversation(
        conversation=conversation,
        message=build_user_message(
            content=user_message,
            metadata=metadata.get("user", {}),
        ),
    )

    conversation = append_message_to_conversation(
        conversation=conversation,
        message=build_assistant_message(
            content=assistant_response,
            metadata=metadata.get("assistant", {}),
        ),
    )

    return conversation


# ============================================================
# SECTION 06 - CONVERSATION SUMMARY
# ============================================================

def build_conversation_summary(
    conversation: dict,
    limit: int = 8,
) -> dict:
    messages = conversation.get(
        "messages",
        [],
    )

    recent_messages = messages[-limit:]

    return {
        "conversation_id": conversation.get("conversation_id"),
        "title": conversation.get("title"),
        "status": conversation.get("status"),
        "message_count": len(messages),
        "recent_messages": recent_messages,
    }


# ============================================================
# SECTION 07 - LOCAL STORAGE PAYLOAD
# ============================================================

def build_conversation_storage_payload(
    conversation: dict,
) -> dict:
    return {
        "storage_key": "aisp2_conversation_state",
        "conversation": conversation,
        "persistent": True,
        "cross_page": True,
        "restore_on_load": True,
    }


# ============================================================
# SECTION 08 - CONVERSATION MANAGER PAYLOAD
# ============================================================

def build_conversation_manager_payload() -> dict:
    starter_conversation = build_conversation_record(
        conversation_id="default",
        title="AISP2 Baseball Assistant",
        messages=[
            build_assistant_message(
                "Welcome to AISP2. Ask me about players, teams, rosters, matchups, probabilities, or projections."
            ),
        ],
    )

    return {
        "component": "conversation_manager",
        "version": "phase_5_part_2",
        "conversation": starter_conversation,
        "storage": build_conversation_storage_payload(
            starter_conversation,
        ),
        "capabilities": {
            "persistent_conversation": True,
            "cross_page_memory": True,
            "message_limit": MAX_CONVERSATION_MESSAGES,
            "local_storage_enabled": True,
            "future_database_sync": True,
        },
    }


# ============================================================
# SECTION 09 - FUTURE CONVERSATION ROADMAP
# ============================================================

"""
09.01 Add database-backed conversation persistence.
09.02 Add conversation IDs per browser session.
09.03 Add user-account conversation history.
09.04 Add conversation titles from first user question.
09.05 Add automatic conversation summaries.
09.06 Add searchable message history.
09.07 Add feedback per assistant response.
09.08 Add saved conversations.
09.09 Add export conversation feature.
09.10 Add RAG retrieval from prior conversations.
"""