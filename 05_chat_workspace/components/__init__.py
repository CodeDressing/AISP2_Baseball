# ============================================================
# AISP2 BASEBALL
# FILE: 05_chat_workspace/components/__init__.py
# PURPOSE: public component exports for the AISP2 chat workspace
# ============================================================


# ============================================================
# SECTION 01 - PACKAGE METADATA
# ============================================================

"""
AISP2 Chat Workspace Components

This package contains backend-safe configuration and state helpers
for the AISP2 floating chat workspace.

Current component modules:
- chat_window
- conversation_manager
- drag_manager
- floating_panel
- resize_manager
- ui_state_manager
"""


__version__ = "1.0.0"


# ============================================================
# SECTION 02 - CHAT WINDOW EXPORTS
# ============================================================

from .chat_window import (
    build_chat_window_config,
    build_chat_window_payload,
    build_default_chat_window_config,
    clamp_chat_window_size,
    normalize_chat_window_state,
)


# ============================================================
# SECTION 03 - CONVERSATION EXPORTS
# ============================================================

from .conversation_manager import (
    append_message_to_conversation,
    append_user_and_assistant_exchange,
    build_assistant_message,
    build_conversation_manager_payload,
    build_conversation_message,
    build_conversation_record,
    build_conversation_storage_payload,
    build_conversation_summary,
    build_user_message,
    clean_conversation_text,
)


# ============================================================
# SECTION 04 - DRAG MANAGER EXPORTS
# ============================================================

from .drag_manager import (
    build_drag_config,
    build_drag_manager_payload,
    build_drag_state,
    clamp_drag_position,
    normalize_drag_anchor,
)


# ============================================================
# SECTION 05 - FLOATING PANEL EXPORTS
# ============================================================

from .floating_panel import (
    build_floating_panel_config,
    build_floating_panel_css_tokens,
    build_floating_panel_payload,
    build_floating_panel_state,
    normalize_floating_panel_anchor,
    normalize_floating_panel_mode,
)


# ============================================================
# SECTION 06 - RESIZE MANAGER EXPORTS
# ============================================================

from .resize_manager import (
    build_resize_config,
    build_resize_manager_payload,
    build_resize_state,
    clamp_chat_size,
    clamp_resize_dimension,
    normalize_resize_handle,
)


# ============================================================
# SECTION 07 - UI STATE MANAGER EXPORTS
# ============================================================

from .ui_state_manager import (
    build_ui_state_manager_payload,
    build_ui_state_record,
    build_ui_storage_payload,
    build_visibility_flags,
    normalize_active_tab,
    normalize_ui_state,
    switch_active_tab,
    transition_ui_state,
)


# ============================================================
# SECTION 08 - PUBLIC API
# ============================================================

__all__ = [
    "__version__",

    "build_chat_window_config",
    "build_chat_window_payload",
    "build_default_chat_window_config",
    "clamp_chat_window_size",
    "normalize_chat_window_state",

    "append_message_to_conversation",
    "append_user_and_assistant_exchange",
    "build_assistant_message",
    "build_conversation_manager_payload",
    "build_conversation_message",
    "build_conversation_record",
    "build_conversation_storage_payload",
    "build_conversation_summary",
    "build_user_message",
    "clean_conversation_text",

    "build_drag_config",
    "build_drag_manager_payload",
    "build_drag_state",
    "clamp_drag_position",
    "normalize_drag_anchor",

    "build_floating_panel_config",
    "build_floating_panel_css_tokens",
    "build_floating_panel_payload",
    "build_floating_panel_state",
    "normalize_floating_panel_anchor",
    "normalize_floating_panel_mode",

    "build_resize_config",
    "build_resize_manager_payload",
    "build_resize_state",
    "clamp_chat_size",
    "clamp_resize_dimension",
    "normalize_resize_handle",

    "build_ui_state_manager_payload",
    "build_ui_state_record",
    "build_ui_storage_payload",
    "build_visibility_flags",
    "normalize_active_tab",
    "normalize_ui_state",
    "switch_active_tab",
    "transition_ui_state",
]