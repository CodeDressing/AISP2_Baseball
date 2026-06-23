# ============================================================
# AISP2 BASEBALL
# FILE: 02_data_sources/__init__.py
# PURPOSE: package initializer for external baseball data
# sources, MLB Stats API clients, future Statcast clients,
# and source capability helpers
# ============================================================


# ============================================================
# SECTION 01 - MLB STATS API EXPORTS
# FILE: 02_data_sources/__init__.py
# PURPOSE: expose official MLB Stats API client and defaults
# ============================================================

from .mlb_stats_api import MLBStatsAPIClient
from .mlb_stats_api import MLB_API_BASE_URL
from .mlb_stats_api import DEFAULT_TIMEOUT
from .mlb_stats_api import DEFAULT_SPORT_ID
from .mlb_stats_api import DEFAULT_SEASON


# ============================================================
# SECTION 02 - DEFAULT CLIENT INSTANCE
# FILE: 02_data_sources/__init__.py
# PURPOSE: provide reusable default MLB Stats API client
# ============================================================

mlb_stats_client = MLBStatsAPIClient()


# ============================================================
# SECTION 03 - PACKAGE METADATA
# FILE: 02_data_sources/__init__.py
# PURPOSE: package version and source status
# ============================================================

DATA_SOURCES_PACKAGE_VERSION = "1.0.0"

PRIMARY_DATA_SOURCE = "MLB Stats API"


# ============================================================
# SECTION 04 - FUTURE DATA SOURCE ROADMAP
# FILE: 02_data_sources/__init__.py
# PURPOSE: future source expansion ledger
# ============================================================

"""
04.01 Add Baseball Savant / Statcast client.
04.02 Add FanGraphs client.
04.03 Add Baseball Reference client.
04.04 Add Retrosheet historical parser.
04.05 Add Lahman database loader.
04.06 Add weather context client.
04.07 Add injury/news context client.
04.08 Add betting market context layer.
04.09 Add source reliability scoring.
04.10 Add source caching layer.
"""