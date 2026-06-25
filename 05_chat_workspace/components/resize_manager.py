# ============================================================
# AISP2 BASEBALL
# FILE: 05_chat_workspace/components/resize_manager.py
# PURPOSE: backend-safe resize configuration layer for the
# floating AISP2 AI assistant workspace
# ============================================================


# ============================================================
# SECTION 01 - RESIZE CONSTANTS
# FILE: 05_chat_workspace/components/resize_manager.py
# PURPOSE: define resize defaults, selectors, and handles
# ============================================================

RESIZE_ENABLED_DEFAULT = True

RESIZE_TARGET_SELECTOR = "[data-aisp2-chat-window]"
RESIZE_HANDLE_SELECTOR = "[data-aisp2-chat-resize-handle]"

RESIZE_HANDLE_BOTTOM_RIGHT = "bottom_right"
RESIZE_HANDLE_BOTTOM_LEFT = "bottom_left"
RESIZE_HANDLE_TOP_RIGHT = "top_right"
RESIZE_HANDLE_TOP_LEFT = "top_left"

DEFAULT_RESIZE_HANDLE = RESIZE_HANDLE_BOTTOM_RIGHT

ALLOWED_RESIZE_HANDLES = {
    RESIZE_HANDLE_BOTTOM_RIGHT,
    RESIZE_HANDLE_BOTTOM_LEFT,
    RESIZE_HANDLE_TOP_RIGHT,
    RESIZE_HANDLE_TOP_LEFT,
}


# ============================================================
# SECTION 02 - SIZE CONSTANTS
# FILE: 05_chat_workspace/components/resize_manager.py
# PURPOSE: define minimum, default, and maximum chat dimensions
# ============================================================

DEFAULT_CHAT_WIDTH = 560
DEFAULT_CHAT_HEIGHT = 680

MIN_CHAT_WIDTH = 380
MIN_CHAT_HEIGHT = 460

MAX_CHAT_WIDTH = 980
MAX_CHAT_HEIGHT = 920


# ============================================================
# SECTION 03 - RESIZE STEP CONSTANTS
# FILE: 05_chat_workspace/components/resize_manager.py
# PURPOSE: define resize increments and snap behavior
# ============================================================

RESIZE_STEP = 8

RESIZE_SNAP_ENABLED_DEFAULT = True
RESIZE_SNAP_DISTANCE = 16


# ============================================================
# SECTION 04 - SIZE VALIDATION
# FILE: 05_chat_workspace/components/resize_manager.py
# PURPOSE: clamp requested size to safe min/max values
# ============================================================

def clamp_resize_dimension(
    value: int | None,
    minimum: int,
    maximum: int,
    fallback: int,
) -> int:
    safe_value = value if value is not None else fallback

    return max(
        minimum,
        min(
            safe_value,
            maximum,
        ),
    )


def clamp_chat_size(
    width: int | None,
    height: int | None,
) -> dict:
    return {
        "width": clamp_resize_dimension(
            value=width,
            minimum=MIN_CHAT_WIDTH,
            maximum=MAX_CHAT_WIDTH,
            fallback=DEFAULT_CHAT_WIDTH,
        ),
        "height": clamp_resize_dimension(
            value=height,
            minimum=MIN_CHAT_HEIGHT,
            maximum=MAX_CHAT_HEIGHT,
            fallback=DEFAULT_CHAT_HEIGHT,
        ),
    }


# ============================================================
# SECTION 05 - HANDLE VALIDATION
# FILE: 05_chat_workspace/components/resize_manager.py
# PURPOSE: normalize resize handle choices
# ============================================================

def normalize_resize_handle(
    handle: str | None,
) -> str:
    if handle in ALLOWED_RESIZE_HANDLES:
        return handle

    return DEFAULT_RESIZE_HANDLE


# ============================================================
# SECTION 06 - RESIZE STATE BUILDER
# FILE: 05_chat_workspace/components/resize_manager.py
# PURPOSE: define runtime resize state
# ============================================================

def build_resize_state(
    width: int | None = None,
    height: int | None = None,
    handle: str | None = None,
    is_resizing: bool = False,
) -> dict:
    safe_size = clamp_chat_size(
        width=width,
        height=height,
    )

    return {
        "width": safe_size["width"],
        "height": safe_size["height"],
        "handle": normalize_resize_handle(
            handle,
        ),
        "is_resizing": is_resizing,
    }


# ============================================================
# SECTION 07 - RESIZE CONFIG BUILDER
# FILE: 05_chat_workspace/components/resize_manager.py
# PURPOSE: build frontend resize configuration
# ============================================================

def build_resize_config() -> dict:
    return {
        "enabled": RESIZE_ENABLED_DEFAULT,
        "target_selector": RESIZE_TARGET_SELECTOR,
        "handle_selector": RESIZE_HANDLE_SELECTOR,
        "default_handle": DEFAULT_RESIZE_HANDLE,
        "allowed_handles": sorted(ALLOWED_RESIZE_HANDLES),
        "min_width": MIN_CHAT_WIDTH,
        "min_height": MIN_CHAT_HEIGHT,
        "max_width": MAX_CHAT_WIDTH,
        "max_height": MAX_CHAT_HEIGHT,
        "default_width": DEFAULT_CHAT_WIDTH,
        "default_height": DEFAULT_CHAT_HEIGHT,
        "resize_step": RESIZE_STEP,
        "snap_enabled": RESIZE_SNAP_ENABLED_DEFAULT,
        "snap_distance": RESIZE_SNAP_DISTANCE,
        "save_to_local_storage": True,
        "local_storage_key": "aisp2_chat_resize_state",
        "restore_on_load": True,
    }


# ============================================================
# SECTION 08 - RESIZE PAYLOAD BUILDER
# FILE: 05_chat_workspace/components/resize_manager.py
# PURPOSE: return complete resize manager payload
# ============================================================

def build_resize_manager_payload() -> dict:
    return {
        "component": "resize_manager",
        "version": "phase_5_part_5",
        "config": build_resize_config(),
        "state": build_resize_state(),
        "capabilities": {
            "resizable": True,
            "min_max_constraints": True,
            "corner_handles": True,
            "size_persistence": True,
            "snap_resize": True,
            "touch_resize_future": True,
            "keyboard_resize_future": True,
        },
    }


# ============================================================
# SECTION 09 - FUTURE RESIZE MANAGER ROADMAP
# FILE: 05_chat_workspace/components/resize_manager.py
# PURPOSE: future resize upgrades and accessibility ledger
# ============================================================

"""
09.01 Add frontend pointer resize handler.
09.02 Add touch resize support.
09.03 Add keyboard-accessible resize controls.
09.04 Add viewport collision protection.
09.05 Add mobile-specific size presets.
09.06 Add fullscreen transition handling.
09.07 Add double-click reset size.
09.08 Add compact, standard, large presets.
09.09 Add page-specific remembered sizes.
09.10 Add accessibility labels for resize handles.
"""