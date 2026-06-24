# ============================================================
# AISP2 BASEBALL
# FILE: 01_database/__init__.py
# PURPOSE: package initializer for database infrastructure,
# models, sessions, initialization utilities, and future
# database services
# ============================================================


# ============================================================
# SECTION 01 - DATABASE EXPORTS
# FILE: 01_database/__init__.py
# PURPOSE: expose common database objects for easy imports
# ============================================================

from .database import Base
from .database import engine
from .database import SessionLocal

from .database import create_database_session
from .database import managed_database_session
from .database import get_database_session

from .database import database_health_check
from .database import database_health_details


# ============================================================
# SECTION 02 - MODEL EXPORTS
# FILE: 01_database/__init__.py
# PURPOSE: expose core ORM models
# ============================================================

from .models import Team
from .models import Player
from .models import RosterEntry
from .models import PlayerSeasonStat


# ============================================================
# SECTION 03 - INITIALIZATION EXPORTS
# FILE: 01_database/__init__.py
# PURPOSE: expose database initialization helpers
# ============================================================

from .init_db import initialize_database
from .init_db import database_startup_check
from .init_db import create_database_tables
from .init_db import drop_database_tables


# ============================================================
# SECTION 04 - PACKAGE VERSIONING
# FILE: 01_database/__init__.py
# PURPOSE: database package metadata
# ============================================================

DATABASE_PACKAGE_VERSION = "1.0.0"


# ============================================================
# SECTION 05 - FUTURE PACKAGE ROADMAP
# FILE: 01_database/__init__.py
# PURPOSE: package expansion ledger
# ============================================================

"""
Future Exports

05.01 TeamSeasonStat
05.02 Game
05.03 StatcastEvent
05.04 FeatureSnapshot
05.05 PlayerPrediction
05.06 GamePrediction
05.07 AnalyticsWarehouse
05.08 PostgreSQL Integration Layer
05.09 Redis Cache Layer
05.10 Vector Database Layer
"""