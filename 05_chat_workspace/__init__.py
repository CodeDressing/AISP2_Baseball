# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# PACKAGE: 05_chat_workspace
# FILE: __init__.py
# ============================================================

"""
05_chat_workspace

Enterprise chat workspace package for AISP2.

Responsibilities
----------------
- Chat workspace orchestration
- Conversation management
- Floating workspace support
- UI state management
- Intent routing
- Player and team interaction
- Prediction workspace integration

Frontend assets (HTML/CSS/JavaScript) live in the frontend/
directory and are not imported as Python modules.
"""

# ============================================================
# SECTION 01 - PACKAGE INFORMATION
# ============================================================

PACKAGE_NAME = "05_chat_workspace"

PACKAGE_TITLE = "AISP2 Chat Workspace"

PACKAGE_VERSION = "1.0.0"

PACKAGE_STATUS = "Development"

PACKAGE_AUTHOR = "Ryan M. Schuren"

PACKAGE_DESCRIPTION = (
    "Enterprise chat workspace for the AISP2 Baseball "
    "Intelligence Platform."
)

# ============================================================
# SECTION 02 - PUBLIC SUBPACKAGES
# ============================================================

from . import components

# ============================================================
# SECTION 03 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "components",
    "PACKAGE_NAME",
    "PACKAGE_TITLE",
    "PACKAGE_VERSION",
    "PACKAGE_STATUS",
    "PACKAGE_AUTHOR",
    "PACKAGE_DESCRIPTION",
]

# ============================================================
# SECTION 04 - PACKAGE STARTUP
# ============================================================

def package_information() -> dict:
    """
    Returns package metadata.
    """

    return {
        "name": PACKAGE_NAME,
        "title": PACKAGE_TITLE,
        "version": PACKAGE_VERSION,
        "status": PACKAGE_STATUS,
        "author": PACKAGE_AUTHOR,
        "description": PACKAGE_DESCRIPTION,
    }