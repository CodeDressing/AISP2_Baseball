# ============================================================
# AISP2 BASEBALL
# FILE: 05_chat_workspace/components/chat_window.py
# PURPOSE: backend-safe chat window configuration layer for
# floating, resizable, persistent AI assistant workspace
# ============================================================


# ============================================================
# SECTION 01 - CHAT WINDOW SIZE CONSTANTS
# ============================================================

CHAT_WINDOW_DEFAULT_WIDTH = 560
CHAT_WINDOW_DEFAULT_HEIGHT = 680

CHAT_WINDOW_MIN_WIDTH = 380
CHAT_WINDOW_MIN_HEIGHT = 460

CHAT_WINDOW_MAX_WIDTH = 980
CHAT_WINDOW_MAX_HEIGHT = 920


# ============================================================
# SECTION 02 - CHAT WINDOW POSITION CONSTANTS
# ============================================================

CHAT_WINDOW_DEFAULT_POSITION = "bottom_right"

CHAT_WINDOW_DEFAULT_OFFSET_X = 28
CHAT_WINDOW_DEFAULT_OFFSET_Y = 28


# ============================================================
# SECTION 03 - CHAT WINDOW STATE CONSTANTS
# ============================================================

CHAT_WINDOW_STATE_OPEN = "open"
CHAT_WINDOW_STATE_COLLAPSED = "collapsed"
CHAT_WINDOW_STATE_MINIMIZED = "minimized"
CHAT_WINDOW_STATE_FULLSCREEN = "fullscreen"


# ============================================================
# SECTION 04 - CHAT WINDOW DEFAULT CONFIG
# ============================================================

def build_default_chat_window_config() -> dict:
    return {
        "enabled": True,
        "state": CHAT_WINDOW_STATE_OPEN,
        "position": CHAT_WINDOW_DEFAULT_POSITION,
        "width": CHAT_WINDOW_DEFAULT_WIDTH,
        "height": CHAT_WINDOW_DEFAULT_HEIGHT,
        "min_width": CHAT_WINDOW_MIN_WIDTH,
        "min_height": CHAT_WINDOW_MIN_HEIGHT,
        "max_width": CHAT_WINDOW_MAX_WIDTH,
        "max_height": CHAT_WINDOW_MAX_HEIGHT,
        "offset_x": CHAT_WINDOW_DEFAULT_OFFSET_X,
        "offset_y": CHAT_WINDOW_DEFAULT_OFFSET_Y,
        "draggable": True,
        "resizable": True,
        "collapsible": True,
        "fullscreen_enabled": True,
        "persistent_across_pages": True,
        "local_storage_key": "aisp2_chat_window_state",
    }


# ============================================================
# SECTION 05 - CHAT WINDOW SIZE VALIDATION
# ============================================================

def clamp_chat_window_size(
    width: int | None,
    height: int | None,
) -> dict:
    safe_width = width or CHAT_WINDOW_DEFAULT_WIDTH
    safe_height = height or CHAT_WINDOW_DEFAULT_HEIGHT

    safe_width = max(
        CHAT_WINDOW_MIN_WIDTH,
        min(
            safe_width,
            CHAT_WINDOW_MAX_WIDTH,
        ),
    )

    safe_height = max(
        CHAT_WINDOW_MIN_HEIGHT,
        min(
            safe_height,
            CHAT_WINDOW_MAX_HEIGHT,
        ),
    )

    return {
        "width": safe_width,
        "height": safe_height,
    }


# ============================================================
# SECTION 06 - CHAT WINDOW STATE VALIDATION
# ============================================================

def normalize_chat_window_state(
    state: str | None,
) -> str:
    allowed_states = {
        CHAT_WINDOW_STATE_OPEN,
        CHAT_WINDOW_STATE_COLLAPSED,
        CHAT_WINDOW_STATE_MINIMIZED,
        CHAT_WINDOW_STATE_FULLSCREEN,
    }

    if state in allowed_states:
        return state

    return CHAT_WINDOW_STATE_OPEN


# ============================================================
# SECTION 07 - CHAT WINDOW CONFIG MERGE
# ============================================================

def build_chat_window_config(
    width: int | None = None,
    height: int | None = None,
    state: str | None = None,
    position: str | None = None,
) -> dict:
    config = build_default_chat_window_config()

    safe_size = clamp_chat_window_size(
        width=width,
        height=height,
    )

    config["width"] = safe_size["width"]
    config["height"] = safe_size["height"]
    config["state"] = normalize_chat_window_state(
        state,
    )

    if position:
        config["position"] = position

    return config


# ============================================================
# SECTION 08 - CHAT WINDOW PAYLOAD BUILDER
# ============================================================

def build_chat_window_payload() -> dict:
    return {
        "component": "chat_window",
        "version": "phase_5_part_1",
        "config": build_default_chat_window_config(),
        "capabilities": {
            "floating": True,
            "resizable": True,
            "draggable": True,
            "persistent": True,
            "cross_page": True,
            "future_tabs": [
                "chat",
                "memory",
                "predictions",
                "saved_players",
                "saved_teams",
            ],
        },
    }


# ============================================================
# SECTION 09 - FUTURE CHAT WINDOW ROADMAP
# ============================================================

"""
09.01 Connect frontend floating shell.
09.02 Connect resize manager.
09.03 Connect drag manager.
09.04 Save position to localStorage.
09.05 Save width and height to localStorage.
09.06 Add minimize/maximize controls.
09.07 Add fullscreen mode.
09.08 Add chat tabs.
09.09 Add memory panel.
09.10 Add prediction card panel.
"""