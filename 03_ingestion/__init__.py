# ============================================================
# AISP2 BASEBALL
# FILE: 03_ingestion/__init__.py
# PURPOSE: package initializer for ingestion engines, database
# loaders, source-to-database pipelines, reports, and future
# scheduled ingestion jobs
# ============================================================


# ============================================================
# SECTION 01 - TEAM INGESTION EXPORTS
# FILE: 03_ingestion/__init__.py
# PURPOSE: expose team ingestion functions
# ============================================================

from .team_ingestion import ingest_mlb_teams
from .team_ingestion import count_database_teams
from .team_ingestion import build_team_inventory
from .team_ingestion import build_ingestion_summary


# ============================================================
# SECTION 02 - PACKAGE METADATA
# FILE: 03_ingestion/__init__.py
# PURPOSE: ingestion package version and status
# ============================================================

INGESTION_PACKAGE_VERSION = "1.0.0"

PRIMARY_INGESTION_PIPELINE = "MLB Team Ingestion"


# ============================================================
# SECTION 03 - FUTURE INGESTION ROADMAP
# FILE: 03_ingestion/__init__.py
# PURPOSE: future ingestion expansion ledger
# ============================================================

"""
03.01 Add player ingestion.
03.02 Add roster ingestion.
03.03 Add player season stat ingestion.
03.04 Add schedule ingestion.
03.05 Add game result ingestion.
03.06 Add standings ingestion.
03.07 Add Statcast ingestion.
03.08 Add ingestion audit logging.
03.09 Add scheduled ingestion jobs.
03.10 Add ingestion dashboard summaries.
"""