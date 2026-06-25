# ============================================================
# AISP2 BASEBALL
# FILE: 05_chat_workspace/components/drag_manager.py
# PURPOSE: backend-safe drag configuration layer for the
# floating AISP2 AI assistant workspace
# ============================================================


# ============================================================
# SECTION 01 - DRAG CONSTANTS
# FILE: 05_chat_workspace/components/drag_manager.py
# PURPOSE: define drag behavior defaults and boundaries
# ============================================================

DRAG_ENABLED_DEFAULT = True

DRAG_HANDLE_SELECTOR = "[data-aisp2-chat-drag-handle]"
DRAG_TARGET_SELECTOR = "[data-aisp2-chat-window]"

DRAG_BOUNDARY_MODE_VIEWPORT = "viewport"
DRAG_BOUNDARY_MODE_CONTAINER = "container"

DEFAULT_DRAG_BOUNDARY_MODE = DRAG_BOUNDARY_MODE_VIEWPORT

DEFAULT_SNAP_ENABLED = True
DEFAULT_SNAP_DISTANCE = 24


# ============================================================
# SECTION 02 - POSITION CONSTANTS
# FILE: 05_chat_workspace/components/drag_manager.py
# PURPOSE: define default and fallback positions
# ============================================================

DEFAULT_CHAT_X = 28
DEFAULT_CHAT_Y = 28

MIN_CHAT_X = 8
MIN_CHAT_Y = 8

DEFAULT_ANCHOR = "bottom_right"

ALLOWED_ANCHORS = {
    "top_left",
    "top_right",
    "bottom_left",
    "bottom_right",
    "center",
}


# ============================================================
# SECTION 03 - DRAG POSITION VALIDATION
# FILE: 05_chat_workspace/components/drag_manager.py
# PURPOSE: clamp drag position values safely
# ============================================================

def clamp_drag_position(
    x: int | None,
    y: int | None,
) -> dict:
    safe_x = x if x is not None else DEFAULT_CHAT_X
    safe_y = y if y is not None else DEFAULT_CHAT_Y

    safe_x = max(
        MIN_CHAT_X,
        safe_x,
    )

    safe_y = max(
        MIN_CHAT_Y,
        safe_y,
    )

    return {
        "x": safe_x,
        "y": safe_y,
    }


# ============================================================
# SECTION 04 - ANCHOR VALIDATION
# FILE: 05_chat_workspace/components/drag_manager.py
# PURPOSE: normalize anchor location for floating assistant
# ============================================================

def normalize_drag_anchor(
    anchor: str | None,
) -> str:
    if anchor in ALLOWED_ANCHORS:
        return anchor

    return DEFAULT_ANCHOR


# ============================================================
# SECTION 05 - DRAG STATE BUILDER
# FILE: 05_chat_workspace/components/drag_manager.py
# PURPOSE: build reusable drag state records
# ============================================================

def build_drag_state(
    x: int | None = None,
    y: int | None = None,
    anchor: str | None = None,
    is_dragging: bool = False,
) -> dict:
    safe_position = clamp_drag_position(
        x=x,
        y=y,
    )

    return {
        "x": safe_position["x"],
        "y": safe_position["y"],
        "anchor": normalize_drag_anchor(
            anchor,
        ),
        "is_dragging": is_dragging,
    }


# ============================================================
# SECTION 06 - DRAG CONFIG BUILDER
# FILE: 05_chat_workspace/components/drag_manager.py
# PURPOSE: define frontend drag behavior and persistence
# ============================================================

def build_drag_config() -> dict:
    return {
        "enabled": DRAG_ENABLED_DEFAULT,
        "handle_selector": DRAG_HANDLE_SELECTOR,
        "target_selector": DRAG_TARGET_SELECTOR,
        "boundary_mode": DEFAULT_DRAG_BOUNDARY_MODE,
        "snap_enabled": DEFAULT_SNAP_ENABLED,
        "snap_distance": DEFAULT_SNAP_DISTANCE,
        "save_to_local_storage": True,
        "local_storage_key": "aisp2_chat_drag_state",
        "restore_on_load": True,
        "prevent_offscreen": True,
    }


# ============================================================
# SECTION 07 - DRAG PAYLOAD BUILDER
# FILE: 05_chat_workspace/components/drag_manager.py
# PURPOSE: return complete drag manager payload
# ============================================================

def build_drag_manager_payload() -> dict:
    return {
        "component": "drag_manager",
        "version": "phase_5_part_3",
        "config": build_drag_config(),
        "state": build_drag_state(),
        "capabilities": {
            "draggable": True,
            "viewport_bounds": True,
            "snap_to_edges": True,
            "position_persistence": True,
            "touch_support_future": True,
            "keyboard_move_future": True,
        },
    }


# ============================================================
# SECTION 08 - FUTURE DRAG MANAGER ROADMAP
# FILE: 05_chat_workspace/components/drag_manager.py
# PURPOSE: future drag upgrades and accessibility ledger
# ============================================================

"""
08.01 Add frontend pointer event handler.
08.02 Add touch drag support.
08.03 Add keyboard-accessible move controls.
08.04 Add snap-to-corner behavior.
08.05 Add viewport collision detection.
08.06 Add safe-area support for mobile devices.
08.07 Add drag ghost/preview state.
08.08 Add reset position control.
08.09 Add page-specific remembered positions.
08.10 Add accessibility labels for drag handle.
"""