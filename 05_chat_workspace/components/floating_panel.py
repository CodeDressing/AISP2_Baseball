# ============================================================
# AISP2 BASEBALL
# FILE: 05_chat_workspace/components/floating_panel.py
# PURPOSE: floating panel configuration layer for the persistent,
# draggable, resizable AISP2 AI assistant workspace
# ============================================================


# ============================================================
# SECTION 01 - FLOATING PANEL CONSTANTS
# FILE: 05_chat_workspace/components/floating_panel.py
# PURPOSE: define panel placement, behavior, and visual defaults
# ============================================================

FLOATING_PANEL_ENABLED_DEFAULT = True

FLOATING_PANEL_ID = "aisp2-floating-chat-panel"
FLOATING_PANEL_SELECTOR = "[data-aisp2-floating-panel]"

FLOATING_PANEL_DEFAULT_LAYER = 9000
FLOATING_PANEL_DEFAULT_ANCHOR = "bottom_right"

FLOATING_PANEL_MODE_DOCKED = "docked"
FLOATING_PANEL_MODE_FLOATING = "floating"
FLOATING_PANEL_MODE_FULLSCREEN = "fullscreen"

FLOATING_PANEL_DEFAULT_MODE = FLOATING_PANEL_MODE_FLOATING


# ============================================================
# SECTION 02 - FLOATING PANEL OFFSET CONSTANTS
# FILE: 05_chat_workspace/components/floating_panel.py
# PURPOSE: define default safe screen offsets
# ============================================================

FLOATING_PANEL_OFFSET_X = 28
FLOATING_PANEL_OFFSET_Y = 28

FLOATING_PANEL_MOBILE_OFFSET_X = 12
FLOATING_PANEL_MOBILE_OFFSET_Y = 12


# ============================================================
# SECTION 03 - FLOATING PANEL MODE VALIDATION
# FILE: 05_chat_workspace/components/floating_panel.py
# PURPOSE: normalize floating panel display mode
# ============================================================

def normalize_floating_panel_mode(
    mode: str | None,
) -> str:
    allowed_modes = {
        FLOATING_PANEL_MODE_DOCKED,
        FLOATING_PANEL_MODE_FLOATING,
        FLOATING_PANEL_MODE_FULLSCREEN,
    }

    if mode in allowed_modes:
        return mode

    return FLOATING_PANEL_DEFAULT_MODE


# ============================================================
# SECTION 04 - FLOATING PANEL ANCHOR VALIDATION
# FILE: 05_chat_workspace/components/floating_panel.py
# PURPOSE: normalize screen anchor location
# ============================================================

def normalize_floating_panel_anchor(
    anchor: str | None,
) -> str:
    allowed_anchors = {
        "top_left",
        "top_right",
        "bottom_left",
        "bottom_right",
        "center",
    }

    if anchor in allowed_anchors:
        return anchor

    return FLOATING_PANEL_DEFAULT_ANCHOR


# ============================================================
# SECTION 05 - FLOATING PANEL BASE CONFIG
# FILE: 05_chat_workspace/components/floating_panel.py
# PURPOSE: build default panel behavior configuration
# ============================================================

def build_floating_panel_config(
    mode: str | None = None,
    anchor: str | None = None,
) -> dict:
    return {
        "enabled": FLOATING_PANEL_ENABLED_DEFAULT,
        "panel_id": FLOATING_PANEL_ID,
        "selector": FLOATING_PANEL_SELECTOR,
        "mode": normalize_floating_panel_mode(mode),
        "anchor": normalize_floating_panel_anchor(anchor),
        "z_index": FLOATING_PANEL_DEFAULT_LAYER,
        "offset_x": FLOATING_PANEL_OFFSET_X,
        "offset_y": FLOATING_PANEL_OFFSET_Y,
        "mobile_offset_x": FLOATING_PANEL_MOBILE_OFFSET_X,
        "mobile_offset_y": FLOATING_PANEL_MOBILE_OFFSET_Y,
        "visible_on_all_pages": True,
        "persistent_position": True,
        "persistent_size": True,
        "can_dock": True,
        "can_float": True,
        "can_fullscreen": True,
        "local_storage_key": "aisp2_floating_panel_state",
    }


# ============================================================
# SECTION 06 - FLOATING PANEL STATE BUILDER
# FILE: 05_chat_workspace/components/floating_panel.py
# PURPOSE: define runtime state for frontend workspace
# ============================================================

def build_floating_panel_state(
    is_visible: bool = True,
    is_active: bool = True,
    mode: str | None = None,
    anchor: str | None = None,
) -> dict:
    return {
        "is_visible": is_visible,
        "is_active": is_active,
        "mode": normalize_floating_panel_mode(mode),
        "anchor": normalize_floating_panel_anchor(anchor),
        "is_docked": normalize_floating_panel_mode(mode) == FLOATING_PANEL_MODE_DOCKED,
        "is_fullscreen": normalize_floating_panel_mode(mode) == FLOATING_PANEL_MODE_FULLSCREEN,
    }


# ============================================================
# SECTION 07 - FLOATING PANEL CSS TOKEN BUILDER
# FILE: 05_chat_workspace/components/floating_panel.py
# PURPOSE: provide frontend-safe CSS variables for panel shell
# ============================================================

def build_floating_panel_css_tokens() -> dict:
    return {
        "--aisp2-chat-z-index": str(FLOATING_PANEL_DEFAULT_LAYER),
        "--aisp2-chat-offset-x": f"{FLOATING_PANEL_OFFSET_X}px",
        "--aisp2-chat-offset-y": f"{FLOATING_PANEL_OFFSET_Y}px",
        "--aisp2-chat-mobile-offset-x": f"{FLOATING_PANEL_MOBILE_OFFSET_X}px",
        "--aisp2-chat-mobile-offset-y": f"{FLOATING_PANEL_MOBILE_OFFSET_Y}px",
    }


# ============================================================
# SECTION 08 - FLOATING PANEL PAYLOAD BUILDER
# FILE: 05_chat_workspace/components/floating_panel.py
# PURPOSE: return complete floating panel payload for future API
# and template integration
# ============================================================

def build_floating_panel_payload() -> dict:
    return {
        "component": "floating_panel",
        "version": "phase_5_part_4",
        "config": build_floating_panel_config(),
        "state": build_floating_panel_state(),
        "css_tokens": build_floating_panel_css_tokens(),
        "capabilities": {
            "visible_on_all_pages": True,
            "floating_mode": True,
            "dockable": True,
            "fullscreen_mode": True,
            "persistent_position": True,
            "persistent_size": True,
            "mobile_safe_offsets": True,
            "future_multi_panel_support": True,
        },
    }


# ============================================================
# SECTION 09 - FUTURE FLOATING PANEL ROADMAP
# FILE: 05_chat_workspace/components/floating_panel.py
# PURPOSE: future floating workspace and shell expansion ledger
# ============================================================

"""
09.01 Connect frontend floating shell.
09.02 Add dock-left and dock-right layouts.
09.03 Add compact mobile launcher.
09.04 Add fullscreen workspace mode.
09.05 Add page-aware panel context.
09.06 Add route transition persistence.
09.07 Add multi-panel support.
09.08 Add AI tools sidebar.
09.09 Add active prediction card slot.
09.10 Add accessibility and focus-trap controls.
"""