# ============================================================
# AISP2 BASEBALL
# FILE: 05_chat_workspace/components/ui_state_manager.py
# PURPOSE: centralized UI state manager for the persistent
# floating AISP2 AI assistant workspace
# ============================================================


# ============================================================
# SECTION 01 - UI STATE CONSTANTS
# FILE: 05_chat_workspace/components/ui_state_manager.py
# PURPOSE: define workspace state names and defaults
# ============================================================

UI_STATE_OPEN = "open"
UI_STATE_COLLAPSED = "collapsed"
UI_STATE_MINIMIZED = "minimized"
UI_STATE_FULLSCREEN = "fullscreen"
UI_STATE_HIDDEN = "hidden"

DEFAULT_UI_STATE = UI_STATE_OPEN

ALLOWED_UI_STATES = {
    UI_STATE_OPEN,
    UI_STATE_COLLAPSED,
    UI_STATE_MINIMIZED,
    UI_STATE_FULLSCREEN,
    UI_STATE_HIDDEN,
}


# ============================================================
# SECTION 02 - UI ACTIVE TAB CONSTANTS
# FILE: 05_chat_workspace/components/ui_state_manager.py
# PURPOSE: define current and future assistant workspace tabs
# ============================================================

UI_TAB_CHAT = "chat"
UI_TAB_MEMORY = "memory"
UI_TAB_PREDICTIONS = "predictions"
UI_TAB_PLAYERS = "players"
UI_TAB_TEAMS = "teams"
UI_TAB_SETTINGS = "settings"

DEFAULT_ACTIVE_TAB = UI_TAB_CHAT

ALLOWED_UI_TABS = {
    UI_TAB_CHAT,
    UI_TAB_MEMORY,
    UI_TAB_PREDICTIONS,
    UI_TAB_PLAYERS,
    UI_TAB_TEAMS,
    UI_TAB_SETTINGS,
}


# ============================================================
# SECTION 03 - UI STORAGE CONSTANTS
# FILE: 05_chat_workspace/components/ui_state_manager.py
# PURPOSE: define frontend persistence keys
# ============================================================

UI_STATE_STORAGE_KEY = "aisp2_chat_ui_state"
UI_LAST_ACTIVE_TAB_STORAGE_KEY = "aisp2_chat_active_tab"
UI_WORKSPACE_STORAGE_KEY = "aisp2_chat_workspace_state"


# ============================================================
# SECTION 04 - UI STATE VALIDATION
# FILE: 05_chat_workspace/components/ui_state_manager.py
# PURPOSE: normalize state names before frontend use
# ============================================================

def normalize_ui_state(
    state: str | None,
) -> str:
    if state in ALLOWED_UI_STATES:
        return state

    return DEFAULT_UI_STATE


def normalize_active_tab(
    tab: str | None,
) -> str:
    if tab in ALLOWED_UI_TABS:
        return tab

    return DEFAULT_ACTIVE_TAB


# ============================================================
# SECTION 05 - UI VISIBILITY HELPERS
# FILE: 05_chat_workspace/components/ui_state_manager.py
# PURPOSE: derive readable visibility flags from state
# ============================================================

def build_visibility_flags(
    state: str | None,
) -> dict:
    normalized_state = normalize_ui_state(
        state,
    )

    return {
        "is_open": normalized_state == UI_STATE_OPEN,
        "is_collapsed": normalized_state == UI_STATE_COLLAPSED,
        "is_minimized": normalized_state == UI_STATE_MINIMIZED,
        "is_fullscreen": normalized_state == UI_STATE_FULLSCREEN,
        "is_hidden": normalized_state == UI_STATE_HIDDEN,
        "is_visible": normalized_state not in {
            UI_STATE_HIDDEN,
            UI_STATE_MINIMIZED,
        },
    }


# ============================================================
# SECTION 06 - UI STATE RECORD BUILDER
# FILE: 05_chat_workspace/components/ui_state_manager.py
# PURPOSE: create standardized UI state records
# ============================================================

def build_ui_state_record(
    state: str | None = None,
    active_tab: str | None = None,
    metadata: dict | None = None,
) -> dict:
    normalized_state = normalize_ui_state(
        state,
    )

    normalized_tab = normalize_active_tab(
        active_tab,
    )

    return {
        "state": normalized_state,
        "active_tab": normalized_tab,
        "visibility": build_visibility_flags(
            normalized_state,
        ),
        "metadata": metadata or {},
    }


# ============================================================
# SECTION 07 - UI STATE TRANSITION HELPERS
# FILE: 05_chat_workspace/components/ui_state_manager.py
# PURPOSE: safely transition between workspace states
# ============================================================

def transition_ui_state(
    current_state: dict,
    next_state: str,
) -> dict:
    current_state = current_state or build_ui_state_record()

    return build_ui_state_record(
        state=next_state,
        active_tab=current_state.get(
            "active_tab",
            DEFAULT_ACTIVE_TAB,
        ),
        metadata=current_state.get(
            "metadata",
            {},
        ),
    )


def switch_active_tab(
    current_state: dict,
    next_tab: str,
) -> dict:
    current_state = current_state or build_ui_state_record()

    return build_ui_state_record(
        state=current_state.get(
            "state",
            DEFAULT_UI_STATE,
        ),
        active_tab=next_tab,
        metadata=current_state.get(
            "metadata",
            {},
        ),
    )


# ============================================================
# SECTION 08 - UI STORAGE PAYLOAD BUILDER
# FILE: 05_chat_workspace/components/ui_state_manager.py
# PURPOSE: provide frontend persistence instructions
# ============================================================

def build_ui_storage_payload(
    ui_state: dict,
) -> dict:
    return {
        "workspace_storage_key": UI_WORKSPACE_STORAGE_KEY,
        "state_storage_key": UI_STATE_STORAGE_KEY,
        "active_tab_storage_key": UI_LAST_ACTIVE_TAB_STORAGE_KEY,
        "ui_state": ui_state,
        "persistent": True,
        "restore_on_load": True,
        "cross_page": True,
    }


# ============================================================
# SECTION 09 - UI STATE MANAGER PAYLOAD
# FILE: 05_chat_workspace/components/ui_state_manager.py
# PURPOSE: return complete UI state manager payload
# ============================================================

def build_ui_state_manager_payload() -> dict:
    default_state = build_ui_state_record()

    return {
        "component": "ui_state_manager",
        "version": "phase_5_part_6",
        "state": default_state,
        "storage": build_ui_storage_payload(
            default_state,
        ),
        "capabilities": {
            "open_close": True,
            "collapse": True,
            "minimize": True,
            "fullscreen": True,
            "tab_switching": True,
            "cross_page_persistence": True,
            "local_storage_enabled": True,
            "future_database_sync": True,
        },
    }


# ============================================================
# SECTION 10 - FUTURE UI STATE ROADMAP
# FILE: 05_chat_workspace/components/ui_state_manager.py
# PURPOSE: future state-management upgrades and expansion ledger
# ============================================================

"""
10.01 Add frontend event bus integration.
10.02 Add page-aware UI state.
10.03 Add workspace layout presets.
10.04 Add user preference persistence.
10.05 Add account-based cloud sync.
10.06 Add keyboard shortcuts.
10.07 Add accessibility focus restoration.
10.08 Add tab notification badges.
10.09 Add unread assistant message indicators.
10.10 Add AI workspace command palette.
"""