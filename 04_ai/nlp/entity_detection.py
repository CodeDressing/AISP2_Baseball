Friday 2:44 PM
Sunday 7:10 PM
Today 1:21 AM
probability_engine.py
Python
ok lets doi this Warehouse ingestion verification
        ↓
04_ai/probability_engine.py
        ↓
04_ai/feature_builder.py integration verification
        ↓
04_ai/game_context_engine.py
        ↓
04_ai/player_projection_engine.py
        ↓
04_ai/team_projection_engine.py
        ↓
04_ai/model_calibration.py
        ↓
04_ai/monte_carlo_engine.py
        ↓
04_ai/explainability_engine.pyupgrade  
        ↓
04_ai/prediction_service.py
        ↓
main.py API routes
        ↓
Backtesting and production validation lets do 04_ai/probability_engine.py upgrade, make it perfect make it massive, make it enterprise level perfection, i know you are capable of 3000 line plus outputs for machine and  deep learning functions, please perform according. begin even if it is a whole file replacement done perfectly at an excellent execution 3000k lines plus i have the itme and need perfection every time, machine learning, deep learning, ai level enterprise perfection, take your time on as perfect output and being Alfred, if we are at the point of 3000 line sections thae that is what we need to be doing ,  good sir 
feature_builder(1).py
Python
2. 04_ai/feature_builder.py
   Converts player/team/game data into prediction-ready features. upgrade, make it perfect make it massive, make it enterprise level perfection, i know you are capable of 3 000 line plus outputs for machine and  deep learning functions, please perform according. begin even if it is a whole file replacement done perfectly at an excellent execution 3000k lines plus i have the time and need perfection every time, machine learning, deep learning, ai level enterprise perfection, take your time on as perfect output and being Alfred, if we are at the point of 2000 line sections then that is what we need to be doing ,  good sir  
okay we need three things to bre done, at least one accompliushed within the enxt two hours. we needthe chatbor to be able to undertand more NPL and answer more questions right now it barely answseres anything at all or is not learning or bot. then we need to really make the data for every player is actually aplied to the players so statistics can run through mathmatical formulas in order to make a prediction
context_builder.py
Python
entity_detection.py
Python
fuzzy_matching.py
Python
intent_detection.py
Python
nlu_engine.py
Python
semantic_engine.py
Python
entity_detection.cpython-314.pyc
File
fuzzy_matching.cpython-314.pyc
File
nlu_engine.cpython-314.pyc
File
therres more
chat_window.py
Python
conversation_manager.py
Python
drag_manager.py
Python
floating_panel.py
Python
resize_manager.py
Python
ui_state_manager.py
Python
__init__.py
Python

These files are useful, but they are UI configuration and state helpers, not the backend message receiver or NLP orchestrator.

What they control:

chat_window.py — window dimensions and state.
conversation_manager.py — stores user/assistant messages and conversation history.
drag_manager.py — drag position behavior.
floating_panel.py — floating panel configuration.
resize_manager.py — resize behavior.
ui_state_manager.py — open, collapsed, minimized, tabs, persistence.
components/__init__.py — exports those helpers.

The one file here that will matter later is:

05_chat_workspace/components/conversation_manager.py

It should eventually be upgraded to store lightweight semantic context such as:

last_player_id
last_player_name
last_team_id
last_team_name
last_game_id
last_outcome
last_statistic
last_intent

But it is not the first file to change.

Still needed

Send these exact files next:

1. The Python route that receives the chat POST request
2. The Python service that calls the NLP files
3. The JavaScript file containing fetch() or sendMessage()
4. The HTML template containing the chat input and quick-action buttons
5. main.py
6. The player-search/database service
7. 01_database/models.py
8. 01_database/database.py

Search your project for:

request.get_json
request.json
request.form
@app.route
@blueprint.route
/chat
/api/chat
fetch(
sendMessage
build_nlu_report
build_entity_report
build_intent_report
build_baseball_context

The most important next upload is the file containing the endpoint resembling:

@...route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message")

That is the file where the current routing failure begins.

context_builder(1).py
Python
entity_detection(1).py
Python
fuzzy_matching(1).py
Python
intent_detection(1).py
Python
nlu_engine(1).py
Python
semantic_engine(1).py
Python
entity_detection.cpython-314(1).pyc
File
fuzzy_matching.cpython-314(1).pyc
File
nlu_engine.cpython-314(1).pyc
File
heres everything for NLP except the innit is empty

Excellent, Master Wayne. I now have the complete editable NLP package:

04_ai/nlp/
├── __init__.py                 # currently empty
├── context_builder.py
├── entity_detection.py
├── fuzzy_matching.py
├── intent_detection.py
├── nlu_engine.py
└── semantic_engine.py

Ignore and delete the .pyc files from source control. They are generated Python cache files, not editable project code.

What the audit shows

Your NLP package has strong individual components, but they are not yet operating as one coordinated engine:

context_builder.py does not implement the conversation-memory roadmap it documents, so follow-up references such as “his OPS” or “that team” cannot yet be resolved reliably.
entity_detection.py depends on a supplied player_profiles dictionary. If that dictionary contains only demo players or is empty, the chatbot cannot recognize the full warehouse roster.
fuzzy_matching.py can recover spelling errors, but it is still disconnected from database-backed player and team names.
intent_detection.py has substantial keyword coverage, but its broad phrases can create collisions. For example, ordinary stat or team questions may be incorrectly upgraded to player-probability requests.
nlu_engine.py currently contains misplaced SQLAlchemy model imports and references undefined constants such as NLU_TASK_LIST_TEAMS, NLU_TASK_HELP, and NLU_TASK_PLAYER_PROBABILITY. This file cannot function as a clean independent NLP engine in its present form.
semantic_engine.py independently repeats team, player, outcome, and intent detection, creating a second routing authority that can disagree with the other modules.
Correct NLP upgrade order

Use this exact order:

1. 04_ai/nlp/nlu_engine.py
   - Remove accidental database-model code
   - Define every task and scope constant
   - Establish one normalized message contract
   - Coordinate the other NLP engines
   - Reclassify every new message independently

2. 04_ai/nlp/entity_detection.py
   - Add database-backed player and team catalogs
   - Improve boundary-safe matching
   - Support IDs, aliases, nicknames, and ambiguity results
   - Prevent team questions from becoming player searches

3. 04_ai/nlp/intent_detection.py
   - Replace fragile substring scoring
   - Add weighted evidence and negative evidence
   - Add explicit intent precedence
   - Separate lookup, stat, schedule, and prediction requests

4. 04_ai/nlp/context_builder.py
   - Add lightweight multi-turn memory
   - Resolve pronouns only when required
   - Let every newly named player or team override old context
   - Never let previous intent lock the next question

5. 04_ai/nlp/fuzzy_matching.py
   - Use warehouse names
   - Add ambiguity margins
   - Avoid replacing ordinary words with incorrect entities
   - Return ranked candidate matches

6. 04_ai/nlp/semantic_engine.py
   - Convert it into a fallback semantic analyzer
   - Stop it from acting as a competing primary router

7. 04_ai/nlp/__init__.py
   - Export one clean public NLP API
   - Expose a single orchestration function
Target public API

After the package upgrade, the chat service should need only one primary call:

from nlp import understand_baseball_message

report = understand_baseball_message(
    message=user_message,
    player_catalog=player_catalog,
    team_catalog=team_catalog,
    conversation_context=conversation_context,
)

The returned report should resemble:

{
    "request_id": "...",
    "original_message": "What is his OPS?",
    "normalized_message": "what is his ops",
    "intent": "player_stats",
    "confidence": 0.94,
    "entities": {
        "player": {
            "id": 682998,
            "name": "Corbin Carroll",
            "source": "conversation_context",
        },
        "team": None,
        "statistic": "ops",
        "outcome": None,
    },
    "context_used": True,
    "clarification_required": False,
    "routing_target": "player_stats_handler",
}
What I still need outside NLP

The NLP package alone cannot repair the live chatbot. I still need:

1. Python chat POST route
2. Python chat service/orchestrator
3. JavaScript file that calls fetch()
4. Chat HTML template
5. File that loads player_profiles and teams
6. Player/team database query service
7. main.py

However, there is now enough material to begin the complete replacement of 04_ai/nlp/nlu_engine.py first. That is the highest-priority NLP file because it currently contains the most serious architectural and import defects.

nlu_engine(2).py
Python
04_ai/nlp/nlu_engine.py
   - Remove accidental database-model code
   - Define every task and scope constant
   - Establish one normalized message contract
   - Coordinate the other NLP engines
   - Reclassify every new message independently
Worked for 3m 41s

Master Wayne, the complete replacement for 04_ai/nlp/nlu_engine.py is finished. It removes the accidental database-model code, defines every task and scope constant, establishes a single normalized message contract, coordinates the surrounding NLP engines, and independently reclassifies every new message.

nlu_engine.py

Verification completed
2,702 lines
101,052 bytes
Python compilation passed
Internal enterprise validation passed
12 of 12 routing tests passed
No SQLAlchemy dependency
No database model declarations
All NLU task constants defined
All NLU scope constants defined
Previous intent is never used as a classifier
Conversation context is used only for incomplete follow-ups
Newly named players override prior player context
Team questions override prior player context
Pronoun follow-ups resolve correctly
Confirmed routing tests
show all mlb teams
→ list_teams

find Corbin Carroll
→ player_lookup

what is Corbin Carroll's OPS
→ player_stats

predict Aaron Judge home run
→ player_probability

show the Yankees roster
→ team_roster

when do the Mets play next
→ team_schedule

is the database connected
→ database_status

compare Aaron Judge and Shohei Ohtani
→ compare_players
Confirmed continuous-conversation behavior

This sequence now works without resetting the chat:

show Corbin Carroll
→ active player: Corbin Carroll

what is his OPS
→ resolves “his” to Corbin Carroll

predict Aaron Judge home run
→ replaces Corbin Carroll with Aaron Judge

show all MLB teams
→ ignores prior player and routes to list_teams

The engine records this diagnostic explicitly:

"previous_intent_used_for_classification": False
Primary public API

The chat service should call:

from nlp.nlu_engine import understand_baseball_message

report = understand_baseball_message(
    message=user_message,
    player_catalog=player_catalog,
    team_catalog=team_catalog,
    conversation_context=conversation_context,
)

The result includes:

{
    "request_id": "...",
    "original_message": "...",
    "normalized_message": "...",
    "intent": "player_stats",
    "scope": "single_player",
    "confidence": 0.91,
    "routing_target": "player_stats_handler",
    "entities": {
        "player": {...},
        "team": None,
        "statistic": {...},
        "outcome": None,
        "season": None,
        "date": None,
        "limit": None,
    },
    "context_used": True,
    "clarification_required": False,
    "next_context": {...},
}
Major architecture added
One authoritative NLU orchestration engine
Fresh per-message classification
Weighted intent scoring
Negative evidence and collision guards
Explicit routing targets
Player and team catalog normalization
Built-in MLB team fallback catalog
Exact name matching
Alias matching
Fuzzy player and team matching
Statistic extraction
Outcome extraction
Season extraction
Relative date extraction
Query-limit extraction
Pronoun resolution
Elliptical follow-up resolution
Context expiration
Context reset commands
Ambiguity detection
Clarification prompts
Request fingerprints
Processing-time diagnostics
Backward-compatible functions
Batch conversation processing
Health and validation endpoints

Place it at:

04_ai/nlp/nlu_engine.py

Recommended commit:

git add 04_ai/nlp/nlu_engine.py
git commit -m "Phase 10 Part 10.0 - Enterprise Independent NLU Orchestration and Conversation Routing Upgrade - July 14 2026"
git push

The next NLP file should be:

04_ai/nlp/entity_detection.py

That upgrade will connect full warehouse-backed player and team catalogs, improve ambiguity handling, and stop entity detection from relying on limited demo-player dictionaries.



2. 04_ai/nlp/entity_detection.py
   - Add database-backed player and team catalogs
   - Improve boundary-safe matching
   - Support IDs, aliases, nicknames, and ambiguity results
   - Prevent team questions from becoming player searches
Worked for 2m 31s

Master Wayne, the full replacement for 04_ai/nlp/entity_detection.py is complete. It preserves the existing public functions while replacing static substring matching with warehouse-aware, boundary-safe entity resolution.

entity_detection.py

Verification completed
1,312 lines
59,405 bytes
Python compilation passed
Enterprise entity validation passed
6 of 6 routing tests passed
Ambiguous surname handling passed
Generic team-list queries no longer invent a specific team
Player-ID questions no longer trigger false team matches
Team roster questions suppress player searching
Exact player names and player IDs resolve correctly
Confirmed behavior
show all MLB teams
→ no specific team selected
→ player search suppressed
→ ready for list_teams routing
show the Yankees roster
→ team: New York Yankees
→ player search suppressed
find Corbin Carroll
→ player: Corbin Carroll
predict Aaron Judge home run
→ player: Aaron Judge
→ outcome: home_run
what is player 682998 ops
→ player ID 682998
→ Corbin Carroll
→ statistic: OPS
show smith
→ ambiguous
→ returns multiple ranked Smith candidates
→ does not silently choose the wrong player
Major upgrades
Database and warehouse catalog support

The NLP layer no longer needs hard-coded demo-player dictionaries. It accepts already-fetched warehouse or database records through:

from nlp.entity_detection import (
    build_player_catalog_from_records,
    build_team_catalog_from_records,
    build_enterprise_entity_report,
)

Example:

player_catalog = build_player_catalog_from_records(
    database_players,
)

team_catalog = build_team_catalog_from_records(
    database_teams,
)

report = build_enterprise_entity_report(
    message=user_message,
    player_catalog=player_catalog,
    team_catalog=team_catalog,
)

Supported record formats include:

dictionaries;
SQLAlchemy ORM objects;
dataclasses;
Pydantic objects;
named tuples;
lists;
name-keyed dictionaries;
plain strings.

The module does not import SQLAlchemy or own a database session. The database service retrieves records; this engine resolves them.

Boundary-safe matching

The original logic used checks resembling:

alias in message

That can create severe false positives. The upgrade uses token boundaries, so:

as

does not automatically resolve the Athletics, and abbreviations or names do not match inside unrelated words.

Resolution precedence

Entity candidates are ranked in this order:

explicit ID
↓
exact canonical name
↓
exact alias
↓
nickname
↓
abbreviation
↓
surname
↓
conservative fuzzy match
IDs, aliases, and nicknames

Supported player records may include:

{
    "player_id": 592450,
    "player_name": "Aaron Judge",
    "team_id": 147,
    "team_name": "New York Yankees",
    "position": "RF",
    "aliases": ["A. Judge"],
    "nicknames": ["The Judge"],
}

Supported team records may include:

{
    "team_id": 147,
    "team_name": "New York Yankees",
    "abbreviation": "NYY",
    "aliases": ["Yankees", "Yanks"],
    "nicknames": ["Bronx Bombers"],
}
Ambiguity reporting

A surname request such as:

show smith

can now return:

{
    "status": "ambiguous",
    "resolved": False,
    "candidates": [
        {
            "canonical_name": "Will Smith",
            "team_name": "Los Angeles Dodgers",
            "position": "C",
        },
        {
            "canonical_name": "John Smith",
            "team_name": "Boston Red Sox",
            "position": "P",
        },
    ],
}

A readable clarification can be generated with:

from nlp.entity_detection import build_ambiguity_prompt

prompt = build_ambiguity_prompt(
    report["player_resolution"],
)
Team-to-player routing protection

The new resolver explicitly suppresses player searching for team-scoped requests such as:

show all MLB teams
show the Yankees roster
when do the Mets play next
what is the Dodgers record

This addresses the current failure where team commands were incorrectly routed into player searches.

Primary report API
from nlp.entity_detection import build_enterprise_entity_report

report = build_enterprise_entity_report(
    message=user_message,
    player_catalog=player_catalog,
    team_catalog=team_catalog,
)

The report includes:

{
    "request_id": "...",
    "original_message": "...",
    "normalized_message": "...",
    "primary_team": {...},
    "primary_player": {...},
    "primary_outcome": {...},
    "primary_statistic": {...},
    "team_resolution": {
        "status": "resolved",
        "primary": {...},
        "candidates": [...],
    },
    "player_resolution": {
        "status": "ambiguous",
        "primary": None,
        "candidates": [...],
    },
    "clarification_required": True,
    "diagnostics": {
        "team_catalog_size": 30,
        "player_catalog_size": ...,
        "player_resolution_suppressed": False,
        "independent_message_resolution": True,
    },
}

Place the file at:

04_ai/nlp/entity_detection.py

Recommended commit:

git add 04_ai/nlp/entity_detection.py
git commit -m "Phase 10 Part 11.0 - Enterprise Warehouse Entity Resolution and Ambiguity Handling Upgrade - July 14 2026"
git push

The next file is:

04_ai/nlp/intent_detection.py

That upgrade should replace broad substring scoring with weighted intent evidence, negative evidence, strict priority rules, and distinct player-stat, team-stat, schedule, roster, and prediction intents.

Library
/
Sports Predicti.
/
entity_detection.py
# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# PACKAGE: 04_ai/nlp
# FILE: entity_detection.py
# PURPOSE:
# Enterprise entity resolution for MLB teams, players, games,
# outcomes, statistics, aliases, nicknames, IDs, warehouse
# records, ambiguity handling, and downstream chat routing.
# ============================================================
"""
AISP2 enterprise entity detection and resolution engine.

This module converts free-form baseball language into normalized, auditable,
warehouse-compatible entities. It is deliberately independent from Flask,
SQLAlchemy, and any specific persistence layer. Callers may supply dictionaries,
dataclasses, ORM rows, Pydantic models, named tuples, or plain strings.

Primary guarantees
------------------
1. Every message is resolved independently.
2. Team-only questions are never forced into player-search routing.
3. Exact IDs outrank exact names; exact names outrank aliases; aliases outrank
   fuzzy candidates.
4. Matching is token-boundary safe. "as" cannot accidentally resolve Oakland
   Athletics and "sox" will not match inside unrelated words.
5. Ambiguous surnames and abbreviations produce ranked ambiguity results rather
   than silently selecting the wrong entity.
6. Database-backed catalogs are supported through adapters without importing a
   database package here.
7. Existing public functions from the earlier implementation remain available.
"""

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
from difflib import SequenceMatcher
from enum import Enum
from hashlib import sha256
import json
import math
import re
import time
from typing import Any, Final, Protocol, TypeVar
from uuid import uuid4

# ============================================================
# SECTION 02 - MODULE METADATA
# ============================================================

MODULE_NAME: Final[str] = "entity_detection"
MODULE_PATH: Final[str] = "04_ai/nlp/entity_detection.py"
MODULE_VERSION: Final[str] = "4.0.0"
MODULE_STATUS: Final[str] = "enterprise"
ENTITY_DETECTION_VERSION: Final[str] = "phase_10_part_11_enterprise_entity_resolution"

# ============================================================
# SECTION 03 - ENTITY TYPES
# ============================================================

ENTITY_TYPE_TEAM = "team"
ENTITY_TYPE_PLAYER = "player"
ENTITY_TYPE_SUBJECT = "subject"
ENTITY_TYPE_OUTCOME = "outcome"
ENTITY_TYPE_STAT = "stat"
ENTITY_TYPE_GAME = "game"
ENTITY_TYPE_SEASON = "season"
ENTITY_TYPE_DATE = "date"
ENTITY_TYPE_VENUE = "venue"
ENTITY_TYPE_POSITION = "position"
ENTITY_TYPE_UNKNOWN = "unknown"

# ============================================================
# SECTION 04 - CONFIDENCE LEVELS
# ============================================================

ENTITY_CONFIDENCE_ID = 1.00
ENTITY_CONFIDENCE_EXACT = 0.99
ENTITY_CONFIDENCE_ALIAS = 0.94
ENTITY_CONFIDENCE_NICKNAME = 0.91
ENTITY_CONFIDENCE_FULL_NAME = 0.96
ENTITY_CONFIDENCE_LAST_NAME = 0.78
ENTITY_CONFIDENCE_FUZZY_STRONG = 0.88
ENTITY_CONFIDENCE_FUZZY_MINIMUM = 0.74
ENTITY_CONFIDENCE_REVIEW = 0.66
ENTITY_AMBIGUITY_MARGIN = 0.035
MAX_ENTITY_CANDIDATES = 8

# Legacy integer constants retained for compatibility.
ENTITY_CONFIDENCE_STRONG = 90
ENTITY_CONFIDENCE_STANDARD = 82
ENTITY_CONFIDENCE_WEAK = 70

# ============================================================
# SECTION 05 - ENUMERATIONS
# ============================================================

class MatchMethod(str, Enum):
    ID = "id"
    EXACT_NAME = "exact_name"
    ALIAS = "alias"
    NICKNAME = "nickname"
    ABBREVIATION = "abbreviation"
    FULL_NAME = "full_name"
    LAST_NAME = "last_name"
    FIRST_LAST = "first_last"
    FUZZY = "fuzzy"
    CONTEXT = "context"


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"
    SUPPRESSED = "suppressed"


class CatalogSource(str, Enum):
    WAREHOUSE = "warehouse"
    DATABASE = "database"
    STATIC = "static"
    CALLER = "caller"
    CONTEXT = "context"

# ============================================================
# SECTION 06 - EXCEPTIONS
# ============================================================

class EntityDetectionError(RuntimeError):
    """Base exception for entity resolution failures."""


class EntityCatalogError(EntityDetectionError):
    """Raised when an entity catalog cannot be normalized."""


class EntityResolutionError(EntityDetectionError):
    """Raised when strict entity resolution fails."""

# ============================================================
# SECTION 07 - PROTOCOLS AND TYPE ALIASES
# ============================================================

T = TypeVar("T")


class SupportsModelDump(Protocol):
    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...


class SupportsDict(Protocol):
    def dict(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

# ============================================================
# SECTION 08 - MLB TEAM CATALOG
# ============================================================

MLB_TEAM_ALIASES: Final[dict[str, list[str]]] = {
    "Arizona Diamondbacks": ["arizona diamondbacks", "diamondbacks", "d backs", "dbacks", "ari", "arizona"],
    "Atlanta Braves": ["atlanta braves", "braves", "atl", "atlanta"],
    "Baltimore Orioles": ["baltimore orioles", "orioles", "os", "o s", "bal", "baltimore"],
    "Boston Red Sox": ["boston red sox", "red sox", "bos", "boston"],
    "Chicago Cubs": ["chicago cubs", "cubs", "chc", "north siders", "northsiders"],
    "Chicago White Sox": ["chicago white sox", "white sox", "cws", "chisox", "chi sox", "south siders", "southsiders"],
    "Cincinnati Reds": ["cincinnati reds", "reds", "cin", "cincinnati"],
    "Cleveland Guardians": ["cleveland guardians", "guardians", "cle", "cleveland"],
    "Colorado Rockies": ["colorado rockies", "rockies", "col", "colorado"],
    "Detroit Tigers": ["detroit tigers", "tigers", "det", "detroit"],
    "Houston Astros": ["houston astros", "astros", "hou", "houston"],
    "Kansas City Royals": ["kansas city royals", "royals", "kc", "kcr", "kansas city"],
    "Los Angeles Angels": ["los angeles angels", "angels", "la angels", "anaheim", "laa"],
    "Los Angeles Dodgers": ["los angeles dodgers", "dodgers", "la dodgers", "lad"],
    "Miami Marlins": ["miami marlins", "marlins", "mia", "miami"],
    "Milwaukee Brewers": ["milwaukee brewers", "brewers", "mil", "milwaukee"],
    "Minnesota Twins": ["minnesota twins", "twins", "min", "minnesota"],
    "New York Mets": ["new york mets", "mets", "nym", "ny mets"],
    "New York Yankees": ["new york yankees", "yankees", "nyy", "bronx bombers", "new york yanks", "ny yanks", "yanks"],
    "Oakland Athletics": ["oakland athletics", "athletics", "oakland", "oak"],
    "Philadelphia Phillies": ["philadelphia phillies", "phillies", "phils", "phi", "philadelphia"],
    "Pittsburgh Pirates": ["pittsburgh pirates", "pirates", "pit", "pittsburgh", "bucs"],
    "San Diego Padres": ["san diego padres", "padres", "sd", "sdp", "san diego"],
    "San Francisco Giants": ["san francisco giants", "giants", "sf", "sfg", "san francisco"],
    "Seattle Mariners": ["seattle mariners", "mariners", "sea", "seattle"],
    "St. Louis Cardinals": ["st louis cardinals", "saint louis cardinals", "cardinals", "cards", "stl", "st louis", "saint louis"],
    "Tampa Bay Rays": ["tampa bay rays", "rays", "tb", "tbr", "tampa bay", "tampa"],
    "Texas Rangers": ["texas rangers", "rangers", "tex", "texas"],
    "Toronto Blue Jays": ["toronto blue jays", "blue jays", "jays", "tor", "toronto"],
    "Washington Nationals": ["washington nationals", "nationals", "nats", "wsh", "washington"],
}

MLB_TEAM_IDS: Final[dict[str, int]] = {
    "Arizona Diamondbacks": 109, "Atlanta Braves": 144, "Baltimore Orioles": 110,
    "Boston Red Sox": 111, "Chicago Cubs": 112, "Chicago White Sox": 145,
    "Cincinnati Reds": 113, "Cleveland Guardians": 114, "Colorado Rockies": 115,
    "Detroit Tigers": 116, "Houston Astros": 117, "Kansas City Royals": 118,
    "Los Angeles Angels": 108, "Los Angeles Dodgers": 119, "Miami Marlins": 146,
    "Milwaukee Brewers": 158, "Minnesota Twins": 142, "New York Mets": 121,
    "New York Yankees": 147, "Oakland Athletics": 133, "Philadelphia Phillies": 143,
    "Pittsburgh Pirates": 134, "San Diego Padres": 135, "San Francisco Giants": 137,
    "Seattle Mariners": 136, "St. Louis Cardinals": 138, "Tampa Bay Rays": 139,
    "Texas Rangers": 140, "Toronto Blue Jays": 141, "Washington Nationals": 120,
}

MLB_TEAM_ABBREVIATIONS: Final[dict[str, str]] = {
    "Arizona Diamondbacks": "ARI", "Atlanta Braves": "ATL", "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS", "Chicago Cubs": "CHC", "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE", "Colorado Rockies": "COL",
    "Detroit Tigers": "DET", "Houston Astros": "HOU", "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD", "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN", "New York Mets": "NYM",
    "New York Yankees": "NYY", "Oakland Athletics": "OAK", "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT", "San Diego Padres": "SD", "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH",
}

# Ambiguous tokens must never resolve alone without supporting language.
AMBIGUOUS_TEAM_TOKENS: Final[frozenset[str]] = frozenset({
    "as", "a", "sox", "new york", "los angeles", "chicago", "washington",
    "giants", "rangers", "cardinals", "reds", "twins", "angels",
})

TEAM_LANGUAGE_MARKERS: Final[frozenset[str]] = frozenset({
    "team", "teams", "club", "clubs", "franchise", "roster", "lineup",
    "schedule", "record", "standings", "division", "bullpen", "rotation",
    "play", "plays", "game", "games", "mlb", "baseball",
})

PLAYER_LANGUAGE_MARKERS: Final[frozenset[str]] = frozenset({
    "player", "players", "hitter", "batter", "pitcher", "starter", "reliever",
    "closer", "rookie", "prospect", "profile", "stats", "statistics", "ops",
    "average", "era", "whip", "home run", "hit", "walk", "strikeout",
})

# ============================================================
# SECTION 09 - SUBJECT, OUTCOME, AND STAT VOCABULARY
# ============================================================

ENTITY_SUBJECT_KEYWORDS: Final[dict[str, list[str]]] = {
    "team": ["team", "club", "franchise", "organization", "squad"],
    "player": ["player", "batter", "hitter", "pitcher", "starter", "closer", "reliever"],
    "roster": ["roster", "lineup", "active roster", "players on", "who plays for", "who is on"],
    "probability_target": ["highest probability", "best probability", "highest chance", "best chance", "most likely", "best projection"],
    "schedule": ["schedule", "next game", "when do", "when does", "play next", "upcoming game"],
    "standings": ["standings", "record", "wins", "losses", "division rank"],
}

OUTCOME_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "home_run": ("home run", "homer", "homerun", "hr", "dinger", "go yard", "go deep", "long ball"),
    "hit": ("hit", "base hit", "record a hit", "get a hit"),
    "single": ("single", "one bagger"),
    "double": ("double", "two bagger"),
    "triple": ("triple", "three bagger"),
    "walk": ("walk", "base on balls", "bb"),
    "strikeout": ("strikeout", "strike out", "k", "punchout", "whiff"),
    "rbi": ("rbi", "run batted in", "drive in"),
    "run": ("run scored", "score a run"),
    "total_bases": ("total bases", "tb"),
    "stolen_base": ("stolen base", "steal a base", "sb"),
}

STAT_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "batting_average": ("batting average", "average", "avg", "ba"),
    "on_base_percentage": ("on base percentage", "on base", "obp"),
    "slugging_percentage": ("slugging percentage", "slugging", "slg"),
    "ops": ("ops", "on base plus slugging"),
    "home_runs": ("home runs", "homers", "hr"),
    "hits": ("hits", "base hits"),
    "doubles": ("doubles", "2b"),
    "triples": ("triples", "3b"),
    "walks": ("walks", "bb"),
    "strikeouts": ("strikeouts", "ks", "so"),
    "rbi": ("rbi", "runs batted in"),
    "runs": ("runs", "runs scored"),
    "stolen_bases": ("stolen bases", "sb"),
    "era": ("era", "earned run average"),
    "whip": ("whip",),
    "fip": ("fip",),
    "xfip": ("xfip",),
    "war": ("war",),
    "woba": ("woba",),
    "wrc_plus": ("wrc+", "wrc plus"),
    "barrel_rate": ("barrel rate", "barrels"),
    "hard_hit_rate": ("hard hit rate", "hard hit"),
    "exit_velocity": ("exit velocity", "ev"),
    "launch_angle": ("launch angle",),
}

# ============================================================
# SECTION 10 - DATA MODELS
# ============================================================

@dataclass(slots=True)
class CatalogEntity:
    entity_type: str
    canonical_id: str | int | None
    canonical_name: str
    aliases: tuple[str, ...] = ()
    nicknames: tuple[str, ...] = ()
    abbreviation: str | None = None
    team_id: str | int | None = None
    team_name: str | None = None
    position: str | None = None
    active: bool | None = None
    source: str = CatalogSource.CALLER.value
    metadata: dict[str, Any] = field(default_factory=dict)

    def all_names(self) -> tuple[str, ...]:
        values = [self.canonical_name, *self.aliases, *self.nicknames]
        if self.abbreviation:
            values.append(self.abbreviation)
        return tuple(dict.fromkeys(value for value in values if value))


@dataclass(slots=True)
class EntityCandidate:
    entity_type: str
    canonical_id: str | int | None
    canonical_name: str
    matched_text: str
    confidence: float
    match_method: str
    source: str
    start: int | None = None
    end: int | None = None
    team_id: str | int | None = None
    team_name: str | None = None
    position: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EntityResolution:
    entity_type: str
    status: ResolutionStatus
    primary: EntityCandidate | None
    candidates: list[EntityCandidate] = field(default_factory=list)
    query: str = ""
    reason: str = ""
    ambiguity_margin: float | None = None
    suppressed: bool = False

    @property
    def resolved(self) -> bool:
        return self.status == ResolutionStatus.RESOLVED and self.primary is not None

    @property
    def ambiguous(self) -> bool:
        return self.status == ResolutionStatus.AMBIGUOUS

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "status": self.status.value,
            "resolved": self.resolved,
            "ambiguous": self.ambiguous,
            "primary": self.primary.to_dict() if self.primary else None,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "query": self.query,
            "reason": self.reason,
            "ambiguity_margin": self.ambiguity_margin,
            "suppressed": self.suppressed,
        }


@dataclass(slots=True)
class EntityReport:
    request_id: str
    original_message: str
    normalized_message: str
    team_resolution: EntityResolution
    player_resolution: EntityResolution
    outcomes: list[EntityCandidate]
    statistics: list[EntityCandidate]
    subjects: list[EntityCandidate]
    all_entities: list[EntityCandidate]
    corrections: list[dict[str, Any]] = field(default_factory=list)
    processing_time_ms: float = 0.0
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        teams = [item.to_dict() for item in self.team_resolution.candidates]
        players = [item.to_dict() for item in self.player_resolution.candidates]
        subjects = [item.to_dict() for item in self.subjects]
        outcomes = [item.to_dict() for item in self.outcomes]
        statistics = [item.to_dict() for item in self.statistics]
        primary_team = self.team_resolution.primary.to_dict() if self.team_resolution.primary else None
        primary_player = self.player_resolution.primary.to_dict() if self.player_resolution.primary else None
        return {
            "request_id": self.request_id,
            "original_message": self.original_message,
            "message": self.normalized_message,
            "normalized_message": self.normalized_message,
            "teams": teams,
            "players": players,
            "subjects": subjects,
            "outcomes": outcomes,
            "statistics": statistics,
            "entities": [item.to_dict() for item in self.all_entities],
            "primary_team": primary_team,
            "primary_player": primary_player,
            "primary_subject": subjects[0] if subjects else None,
            "primary_outcome": outcomes[0] if outcomes else None,
            "primary_statistic": statistics[0] if statistics else None,
            "team_resolution": self.team_resolution.to_dict(),
            "player_resolution": self.player_resolution.to_dict(),
            "has_team": self.team_resolution.resolved or bool(self.team_resolution.candidates),
            "has_player": self.player_resolution.resolved or bool(self.player_resolution.candidates),
            "has_probability_target": any(item.canonical_name == "probability_target" for item in self.subjects),
            "team_ambiguous": self.team_resolution.ambiguous,
            "player_ambiguous": self.player_resolution.ambiguous,
            "clarification_required": self.team_resolution.ambiguous or self.player_resolution.ambiguous,
            "corrections": self.corrections,
            "processing_time_ms": round(self.processing_time_ms, 3),
            "diagnostics": self.diagnostics,
        }

# ============================================================
# SECTION 11 - GENERIC RECORD NORMALIZATION
# ============================================================

def object_to_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return dict(value.model_dump())
    if hasattr(value, "dict") and callable(value.dict):
        return dict(value.dict())
    if hasattr(value, "_asdict") and callable(value._asdict):
        return dict(value._asdict())
    if hasattr(value, "__table__"):
        try:
            return {column.name: getattr(value, column.name) for column in value.__table__.columns}
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        return {key: item for key, item in vars(value).items() if not key.startswith("_") and not callable(item)}
    if isinstance(value, str):
        return {"name": value}
    raise EntityCatalogError(f"Unsupported catalog record type: {type(value).__name__}")


def records_from_any(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        # Mapping may be name->record or a single record.
        record_markers = {"name", "player_name", "team_name", "id", "player_id", "team_id"}
        if record_markers.intersection(value.keys()):
            return [value]
        output = []
        for key, item in value.items():
            if isinstance(item, Mapping):
                merged = dict(item)
                merged.setdefault("name", key)
                output.append(merged)
            else:
                output.append({"name": key, "value": item})
        return output
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, Iterable):
        return list(value)
    return [value]


def first_present(record: Mapping[str, Any], candidates: Sequence[str], default: Any = None) -> Any:
    for candidate in candidates:
        value = record.get(candidate)
        if value not in (None, ""):
            return value
    return default


def sequence_value(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        chunks = re.split(r"[,;|]", value)
        return tuple(chunk.strip() for chunk in chunks if chunk.strip())
    if isinstance(value, Iterable) and not isinstance(value, (bytes, Mapping)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return (str(value).strip(),)

# ============================================================
# SECTION 12 - TEXT NORMALIZATION AND BOUNDARY MATCHING
# ============================================================

_APOSTROPHE_RE = re.compile(r"[’'`]")
_NON_WORD_RE = re.compile(r"[^a-z0-9+#]+")
_SPACE_RE = re.compile(r"\s+")


def normalize_entity_text(value: str | None) -> str:
    if not value:
        return ""
    text = str(value).lower().strip()
    text = _APOSTROPHE_RE.sub("", text)
    text = text.replace("&", " and ")
    text = _NON_WORD_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def tokenize_entity_text(value: str | None) -> list[str]:
    return normalize_entity_text(value).split()


def phrase_pattern(phrase: str) -> re.Pattern[str]:
    normalized = normalize_entity_text(phrase)
    if not normalized:
        return re.compile(r"(?!x)x")
    parts = [re.escape(part) for part in normalized.split()]
    return re.compile(r"(?<![a-z0-9])" + r"\s+".join(parts) + r"(?![a-z0-9])", re.IGNORECASE)


def find_boundary_matches(message: str, phrase: str) -> list[tuple[int, int, str]]:
    normalized_message = normalize_entity_text(message)
    pattern = phrase_pattern(phrase)
    return [(match.start(), match.end(), match.group(0)) for match in pattern.finditer(normalized_message)]


def boundary_contains(message: str, phrase: str) -> bool:
    return bool(find_boundary_matches(message, phrase))


def token_overlap(left: str, right: str) -> float:
    a = set(tokenize_entity_text(left))
    b = set(tokenize_entity_text(right))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def similarity(left: str, right: str) -> float:
    a = normalize_entity_text(left)
    b = normalize_entity_text(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    seq = SequenceMatcher(None, a, b).ratio()
    overlap = token_overlap(a, b)
    prefix = 1.0 if a.startswith(b) or b.startswith(a) else 0.0
    return max(seq, 0.68 * seq + 0.25 * overlap + 0.07 * prefix)


def canonical_fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()

# ============================================================
# SECTION 13 - CATALOG NORMALIZATION
# ============================================================

class CatalogNormalizer:
    TEAM_NAME_FIELDS = ("team_name", "name", "full_name", "club_name", "canonical_name")
    TEAM_ID_FIELDS = ("team_id", "mlb_team_id", "id", "teamId")
    PLAYER_NAME_FIELDS = ("player_name", "full_name", "name", "display_name", "canonical_name")
    PLAYER_ID_FIELDS = ("player_id", "mlb_player_id", "person_id", "id", "personId")

    def normalize_team(self, value: Any, source: str = CatalogSource.CALLER.value) -> CatalogEntity:
        record = object_to_mapping(value)
        name = str(first_present(record, self.TEAM_NAME_FIELDS, "")).strip()
        if not name:
            raise EntityCatalogError("Team record is missing a name")
        team_id = first_present(record, self.TEAM_ID_FIELDS, MLB_TEAM_IDS.get(name))
        abbreviation = first_present(record, ("abbreviation", "abbr", "team_code", "file_code"), MLB_TEAM_ABBREVIATIONS.get(name))
        aliases = sequence_value(first_present(record, ("aliases", "alias", "alternate_names", "team_aliases"), ()))
        nicknames = sequence_value(first_present(record, ("nicknames", "nickname", "short_name"), ()))
        static_aliases = tuple(MLB_TEAM_ALIASES.get(name, ()))
        merged_aliases = tuple(dict.fromkeys((*aliases, *static_aliases)))
        return CatalogEntity(
            entity_type=ENTITY_TYPE_TEAM,
            canonical_id=team_id,
            canonical_name=name,
            aliases=merged_aliases,
            nicknames=nicknames,
            abbreviation=str(abbreviation).strip() if abbreviation else None,
            source=source,
            metadata={key: item for key, item in record.items() if key not in {"aliases", "nicknames"}},
        )

    def normalize_player(self, value: Any, source: str = CatalogSource.CALLER.value) -> CatalogEntity:
        record = object_to_mapping(value)
        name = str(first_present(record, self.PLAYER_NAME_FIELDS, "")).strip()
        if not name:
            raise EntityCatalogError("Player record is missing a name")
        player_id = first_present(record, self.PLAYER_ID_FIELDS)
        team_id = first_present(record, ("team_id", "current_team_id", "mlb_team_id", "club_id"))
        team_name = first_present(record, ("team_name", "current_team_name", "club_name"))
        aliases = sequence_value(first_present(record, ("aliases", "alias", "alternate_names", "player_aliases"), ()))
        nicknames = sequence_value(first_present(record, ("nicknames", "nickname", "known_as"), ()))
        position = first_present(record, ("position", "position_name", "primary_position", "position_abbreviation"))
        active = first_present(record, ("active", "is_active", "current"))
        return CatalogEntity(
            entity_type=ENTITY_TYPE_PLAYER,
            canonical_id=player_id,
            canonical_name=name,
            aliases=aliases,
            nicknames=nicknames,
            team_id=team_id,
            team_name=str(team_name) if team_name else None,
            position=str(position) if position else None,
            active=bool(active) if active is not None else None,
            source=source,
            metadata={key: item for key, item in record.items() if key not in {"aliases", "nicknames"}},
        )

    def normalize_catalog(self, values: Any, entity_type: str, source: str = CatalogSource.CALLER.value) -> list[CatalogEntity]:
        entities: list[CatalogEntity] = []
        for value in records_from_any(values):
            try:
                entity = self.normalize_team(value, source) if entity_type == ENTITY_TYPE_TEAM else self.normalize_player(value, source)
                entities.append(entity)
            except EntityCatalogError:
                continue
        return self._deduplicate(entities)

    @staticmethod
    def _deduplicate(entities: Sequence[CatalogEntity]) -> list[CatalogEntity]:
        by_key: dict[tuple[str, str], CatalogEntity] = {}
        for entity in entities:
            key = (entity.entity_type, str(entity.canonical_id) if entity.canonical_id is not None else normalize_entity_text(entity.canonical_name))
            if key not in by_key:
                by_key[key] = entity
                continue
            existing = by_key[key]
            existing.aliases = tuple(dict.fromkeys((*existing.aliases, *entity.aliases)))
            existing.nicknames = tuple(dict.fromkeys((*existing.nicknames, *entity.nicknames)))
            existing.metadata.update(entity.metadata)
        return list(by_key.values())

# ============================================================
# SECTION 14 - STATIC TEAM CATALOG BUILDER
# ============================================================

def build_static_team_catalog() -> list[CatalogEntity]:
    normalizer = CatalogNormalizer()
    rows = []
    for name, aliases in MLB_TEAM_ALIASES.items():
        rows.append({
            "team_id": MLB_TEAM_IDS.get(name),
            "team_name": name,
            "abbreviation": MLB_TEAM_ABBREVIATIONS.get(name),
            "aliases": aliases,
        })
    return normalizer.normalize_catalog(rows, ENTITY_TYPE_TEAM, CatalogSource.STATIC.value)

# ============================================================
# SECTION 15 - INDEXES
# ============================================================

class EntityCatalogIndex:
    def __init__(self, entities: Sequence[CatalogEntity]) -> None:
        self.entities = list(entities)
        self.by_id: dict[str, CatalogEntity] = {}
        self.by_exact_name: dict[str, list[CatalogEntity]] = defaultdict(list)
        self.by_alias: dict[str, list[tuple[CatalogEntity, MatchMethod]]] = defaultdict(list)
        self.by_last_name: dict[str, list[CatalogEntity]] = defaultdict(list)
        self._build()

    def _build(self) -> None:
        for entity in self.entities:
            if entity.canonical_id is not None:
                self.by_id[str(entity.canonical_id)] = entity
            canonical = normalize_entity_text(entity.canonical_name)
            self.by_exact_name[canonical].append(entity)
            if entity.entity_type == ENTITY_TYPE_PLAYER:
                parts = canonical.split()
                if parts:
                    self.by_last_name[parts[-1]].append(entity)
            for alias in entity.aliases:
                normalized = normalize_entity_text(alias)
                if normalized:
                    self.by_alias[normalized].append((entity, MatchMethod.ALIAS))
            for nickname in entity.nicknames:
                normalized = normalize_entity_text(nickname)
                if normalized:
                    self.by_alias[normalized].append((entity, MatchMethod.NICKNAME))
            if entity.abbreviation:
                normalized = normalize_entity_text(entity.abbreviation)
                if normalized:
                    self.by_alias[normalized].append((entity, MatchMethod.ABBREVIATION))

    def fingerprint(self) -> str:
        return canonical_fingerprint([
            {
                "type": entity.entity_type,
                "id": entity.canonical_id,
                "name": entity.canonical_name,
                "aliases": entity.aliases,
                "nicknames": entity.nicknames,
                "abbreviation": entity.abbreviation,
            }
            for entity in self.entities
        ])

# ============================================================
# SECTION 16 - MESSAGE SIGNALS
# ============================================================

@dataclass(slots=True)
class MessageSignals:
    tokens: set[str]
    has_team_language: bool
    has_player_language: bool
    explicit_team_list: bool
    explicit_player_list: bool
    explicit_roster: bool
    explicit_schedule: bool
    explicit_prediction: bool
    numeric_ids: list[str]


def analyze_message_signals(message: str) -> MessageSignals:
    normalized = normalize_entity_text(message)
    tokens = set(normalized.split())
    return MessageSignals(
        tokens=tokens,
        has_team_language=bool(tokens & TEAM_LANGUAGE_MARKERS),
        has_player_language=bool(tokens & PLAYER_LANGUAGE_MARKERS),
        explicit_team_list=any(boundary_contains(normalized, phrase) for phrase in ("all teams", "list teams", "show teams", "mlb teams", "every team")),
        explicit_player_list=any(boundary_contains(normalized, phrase) for phrase in ("all players", "list players", "show players", "mlb players", "every player")),
        explicit_roster=any(boundary_contains(normalized, phrase) for phrase in ("roster", "lineup", "who is on", "players on")),
        explicit_schedule=any(boundary_contains(normalized, phrase) for phrase in ("schedule", "next game", "play next", "plays next")),
        explicit_prediction=any(boundary_contains(normalized, phrase) for phrase in ("predict", "probability", "chance", "odds", "projection", "likely")),
        numeric_ids=re.findall(r"\b\d{3,10}\b", normalized),
    )

# ============================================================
# SECTION 17 - ENTITY RESOLVER
# ============================================================

class EntityResolver:
    def __init__(
        self,
        *,
        team_catalog: Any = None,
        player_catalog: Any = None,
        source: str = CatalogSource.CALLER.value,
        fuzzy_threshold: float = ENTITY_CONFIDENCE_FUZZY_MINIMUM,
        ambiguity_margin: float = ENTITY_AMBIGUITY_MARGIN,
        max_candidates: int = MAX_ENTITY_CANDIDATES,
    ) -> None:
        normalizer = CatalogNormalizer()
        supplied_teams = normalizer.normalize_catalog(team_catalog, ENTITY_TYPE_TEAM, source) if team_catalog is not None else []
        static_teams = build_static_team_catalog()
        merged_teams = normalizer._deduplicate([*supplied_teams, *static_teams])
        players = normalizer.normalize_catalog(player_catalog, ENTITY_TYPE_PLAYER, source) if player_catalog is not None else []
        self.team_index = EntityCatalogIndex(merged_teams)
        self.player_index = EntityCatalogIndex(players)
        self.fuzzy_threshold = fuzzy_threshold
        self.ambiguity_margin = ambiguity_margin
        self.max_candidates = max_candidates

    def resolve_team(self, message: str, *, allow_fuzzy: bool = True) -> EntityResolution:
        signals = analyze_message_signals(message)
        # Generic collection requests do not identify one team, and player-only
        # questions must not manufacture a team through fuzzy similarity.
        fuzzy_allowed = (
            allow_fuzzy
            and signals.has_team_language
            and not signals.explicit_team_list
            and not signals.explicit_player_list
        )
        return self._resolve(
            message,
            self.team_index,
            ENTITY_TYPE_TEAM,
            allow_fuzzy=fuzzy_allowed,
        )

    def resolve_player(self, message: str, *, allow_fuzzy: bool = True, suppress_for_team_only: bool = True) -> EntityResolution:
        signals = analyze_message_signals(message)
        if suppress_for_team_only and self._is_team_only_question(signals, message):
            return EntityResolution(
                entity_type=ENTITY_TYPE_PLAYER,
                status=ResolutionStatus.SUPPRESSED,
                primary=None,
                candidates=[],
                query=message,
                reason="Player resolution suppressed because the message is explicitly team-scoped.",
                suppressed=True,
            )
        return self._resolve(message, self.player_index, ENTITY_TYPE_PLAYER, allow_fuzzy=allow_fuzzy)

    @staticmethod
    def _is_team_only_question(signals: MessageSignals, message: str) -> bool:
        if signals.explicit_player_list:
            return False
        if signals.explicit_team_list or signals.explicit_roster or signals.explicit_schedule:
            return True
        if signals.has_team_language and not signals.has_player_language:
            # Prediction language plus a player-like full name should still permit player resolution.
            normalized = normalize_entity_text(message)
            person_pattern = re.search(r"\b[a-z]{2,}\s+[a-z]{2,}\b", normalized)
            return not bool(signals.explicit_prediction and person_pattern)
        return False

    def _resolve(self, message: str, index: EntityCatalogIndex, entity_type: str, *, allow_fuzzy: bool) -> EntityResolution:
        normalized = normalize_entity_text(message)
        candidates: list[EntityCandidate] = []
        signals = analyze_message_signals(message)

        # 17.01 ID matches.
        for numeric_id in signals.numeric_ids:
            entity = index.by_id.get(numeric_id)
            if entity:
                candidates.append(self._candidate(entity, numeric_id, ENTITY_CONFIDENCE_ID, MatchMethod.ID))

        # 17.02 Exact canonical names.
        for canonical, entities in index.by_exact_name.items():
            matches = find_boundary_matches(normalized, canonical)
            for start, end, matched in matches:
                for entity in entities:
                    candidates.append(self._candidate(entity, matched, ENTITY_CONFIDENCE_EXACT, MatchMethod.EXACT_NAME, start, end))

        # 17.03 Aliases and abbreviations.
        for alias, entries in index.by_alias.items():
            if alias in AMBIGUOUS_TEAM_TOKENS and entity_type == ENTITY_TYPE_TEAM and not signals.has_team_language:
                continue
            matches = find_boundary_matches(normalized, alias)
            for start, end, matched in matches:
                for entity, method in entries:
                    base = ENTITY_CONFIDENCE_ALIAS
                    if method == MatchMethod.NICKNAME:
                        base = ENTITY_CONFIDENCE_NICKNAME
                    elif method == MatchMethod.ABBREVIATION:
                        base = 0.93 if len(alias) >= 3 else 0.86
                    candidates.append(self._candidate(entity, matched, base, method, start, end))

        # 17.04 Player surname matching only when meaningful.
        if entity_type == ENTITY_TYPE_PLAYER:
            for surname, entities in index.by_last_name.items():
                if len(surname) < 3 or not boundary_contains(normalized, surname):
                    continue
                for entity in entities:
                    confidence = ENTITY_CONFIDENCE_LAST_NAME
                    candidates.append(self._candidate(entity, surname, confidence, MatchMethod.LAST_NAME))

        # 17.05 Conservative fuzzy fallback.
        if allow_fuzzy and not candidates and index.entities:
            candidates.extend(self._fuzzy_candidates(normalized, index, entity_type))

        candidates = self._dedupe_rank(candidates)
        return self._finalize_resolution(entity_type, message, candidates)

    def _fuzzy_candidates(self, message: str, index: EntityCatalogIndex, entity_type: str) -> list[EntityCandidate]:
        tokens = message.split()
        windows: list[str] = []
        max_window = 4 if entity_type == ENTITY_TYPE_PLAYER else 3
        for size in range(1, min(max_window, len(tokens)) + 1):
            for position in range(0, len(tokens) - size + 1):
                window = " ".join(tokens[position:position + size])
                if len(window) >= 3:
                    windows.append(window)
        results: list[EntityCandidate] = []
        for entity in index.entities:
            best_score = 0.0
            best_text = ""
            for candidate_name in entity.all_names():
                normalized_name = normalize_entity_text(candidate_name)
                for window in windows:
                    score = similarity(window, normalized_name)
                    # Penalize one-token fuzzy player matches to prevent generic words.
                    if entity_type == ENTITY_TYPE_PLAYER and len(window.split()) == 1 and len(normalized_name.split()) > 1:
                        score *= 0.88
                    if score > best_score:
                        best_score = score
                        best_text = window
            if best_score >= self.fuzzy_threshold:
                results.append(self._candidate(entity, best_text, best_score, MatchMethod.FUZZY))
        return sorted(results, key=lambda item: item.confidence, reverse=True)[:self.max_candidates]

    @staticmethod
    def _candidate(
        entity: CatalogEntity,
        matched_text: str,
        confidence: float,
        method: MatchMethod,
        start: int | None = None,
        end: int | None = None,
    ) -> EntityCandidate:
        return EntityCandidate(
            entity_type=entity.entity_type,
            canonical_id=entity.canonical_id,
            canonical_name=entity.canonical_name,
            matched_text=matched_text,
            confidence=round(min(max(confidence, 0.0), 1.0), 4),
            match_method=method.value,
            source=entity.source,
            start=start,
            end=end,
            team_id=entity.team_id,
            team_name=entity.team_name,
            position=entity.position,
            metadata=dict(entity.metadata),
        )

    def _dedupe_rank(self, candidates: Sequence[EntityCandidate]) -> list[EntityCandidate]:
        best: dict[tuple[str, str], EntityCandidate] = {}
        for candidate in candidates:
            key = (candidate.entity_type, str(candidate.canonical_id) if candidate.canonical_id is not None else normalize_entity_text(candidate.canonical_name))
            existing = best.get(key)
            if existing is None or candidate.confidence > existing.confidence:
                best[key] = candidate
        return sorted(best.values(), key=lambda item: (-item.confidence, item.canonical_name))[:self.max_candidates]

    def _finalize_resolution(self, entity_type: str, query: str, candidates: list[EntityCandidate]) -> EntityResolution:
        if not candidates:
            return EntityResolution(entity_type, ResolutionStatus.NOT_FOUND, None, [], query, "No catalog entity matched the message.")
        if len(candidates) == 1:
            return EntityResolution(entity_type, ResolutionStatus.RESOLVED, candidates[0], candidates, query, "Single high-confidence entity resolved.")
        top, second = candidates[0], candidates[1]
        margin = top.confidence - second.confidence
        # Full-name and ID matches are authoritative unless duplicated by catalog corruption.
        authoritative = top.match_method in {MatchMethod.ID.value, MatchMethod.EXACT_NAME.value, MatchMethod.FULL_NAME.value}
        same_confidence = abs(top.confidence - second.confidence) <= self.ambiguity_margin
        same_surname = top.match_method == MatchMethod.LAST_NAME.value and second.match_method == MatchMethod.LAST_NAME.value
        if not authoritative and (same_confidence or same_surname):
            return EntityResolution(
                entity_type=entity_type,
                status=ResolutionStatus.AMBIGUOUS,
                primary=None,
                candidates=candidates,
                query=query,
                reason="Multiple plausible catalog entities matched the message.",
                ambiguity_margin=round(margin, 4),
            )
        return EntityResolution(
            entity_type=entity_type,
            status=ResolutionStatus.RESOLVED,
            primary=top,
            candidates=candidates,
            query=query,
            reason="Top-ranked entity exceeded competing candidates.",
            ambiguity_margin=round(margin, 4),
        )

# ============================================================
# SECTION 18 - VOCABULARY ENTITY DETECTION
# ============================================================

def detect_vocabulary_entities(message: str, vocabulary: Mapping[str, Sequence[str]], entity_type: str) -> list[EntityCandidate]:
    normalized = normalize_entity_text(message)
    candidates: list[EntityCandidate] = []
    for canonical, aliases in vocabulary.items():
        ordered_aliases = sorted(aliases, key=lambda item: len(normalize_entity_text(item)), reverse=True)
        for alias in ordered_aliases:
            matches = find_boundary_matches(normalized, alias)
            if not matches:
                continue
            start, end, matched = matches[0]
            confidence = 0.98 if normalize_entity_text(alias) == normalize_entity_text(canonical) else 0.93
            candidates.append(EntityCandidate(
                entity_type=entity_type,
                canonical_id=None,
                canonical_name=canonical,
                matched_text=matched,
                confidence=confidence,
                match_method=MatchMethod.ALIAS.value,
                source=CatalogSource.STATIC.value,
                start=start,
                end=end,
            ))
            break
    return sorted(candidates, key=lambda item: (-item.confidence, -(len(item.matched_text))))


def detect_subject_entities(message: str) -> list[dict[str, Any]]:
    return [item.to_dict() for item in detect_vocabulary_entities(message, ENTITY_SUBJECT_KEYWORDS, ENTITY_TYPE_SUBJECT)]


def detect_outcome_entities(message: str) -> list[dict[str, Any]]:
    return [item.to_dict() for item in detect_vocabulary_entities(message, OUTCOME_ALIASES, ENTITY_TYPE_OUTCOME)]


def detect_stat_entities(message: str) -> list[dict[str, Any]]:
    return [item.to_dict() for item in detect_vocabulary_entities(message, STAT_ALIASES, ENTITY_TYPE_STAT)]

# ============================================================
# SECTION 19 - PUBLIC ENTERPRISE REPORT BUILDER
# ============================================================

def build_enterprise_entity_report(
    message: str,
    *,
    player_catalog: Any = None,
    team_catalog: Any = None,
    player_profiles: Any = None,
    teams: Any = None,
    allow_fuzzy: bool = True,
    request_id: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    original = str(message or "")
    normalized = normalize_entity_text(original)
    player_catalog = player_catalog if player_catalog is not None else player_profiles
    team_catalog = team_catalog if team_catalog is not None else teams

    resolver = EntityResolver(team_catalog=team_catalog, player_catalog=player_catalog)
    team_resolution = resolver.resolve_team(normalized, allow_fuzzy=allow_fuzzy)
    player_resolution = resolver.resolve_player(normalized, allow_fuzzy=allow_fuzzy)

    outcome_objects = detect_vocabulary_entities(normalized, OUTCOME_ALIASES, ENTITY_TYPE_OUTCOME)
    stat_objects = detect_vocabulary_entities(normalized, STAT_ALIASES, ENTITY_TYPE_STAT)
    subject_objects = detect_vocabulary_entities(normalized, ENTITY_SUBJECT_KEYWORDS, ENTITY_TYPE_SUBJECT)

    all_entities = [
        *team_resolution.candidates,
        *player_resolution.candidates,
        *outcome_objects,
        *stat_objects,
        *subject_objects,
    ]

    report = EntityReport(
        request_id=request_id or str(uuid4()),
        original_message=original,
        normalized_message=normalized,
        team_resolution=team_resolution,
        player_resolution=player_resolution,
        outcomes=outcome_objects,
        statistics=stat_objects,
        subjects=subject_objects,
        all_entities=all_entities,
        processing_time_ms=(time.perf_counter() - started) * 1000.0,
        diagnostics={
            "module_version": MODULE_VERSION,
            "team_catalog_size": len(resolver.team_index.entities),
            "player_catalog_size": len(resolver.player_index.entities),
            "team_catalog_hash": resolver.team_index.fingerprint(),
            "player_catalog_hash": resolver.player_index.fingerprint(),
            "player_resolution_suppressed": player_resolution.suppressed,
            "independent_message_resolution": True,
        },
    )
    return report.to_dict()

# ============================================================
# SECTION 20 - BACKWARD-COMPATIBLE TEAM API
# ============================================================

def detect_team_entities(message: str, team_catalog: Any = None) -> list[dict[str, Any]]:
    report = build_enterprise_entity_report(message, team_catalog=team_catalog, allow_fuzzy=False)
    return report["teams"]


def detect_primary_team_entity(message: str, team_catalog: Any = None) -> dict[str, Any] | None:
    report = build_enterprise_entity_report(message, team_catalog=team_catalog, allow_fuzzy=True)
    return report["primary_team"]

# ============================================================
# SECTION 21 - BACKWARD-COMPATIBLE PLAYER API
# ============================================================

def detect_player_entities(message: str, player_profiles: Any) -> list[dict[str, Any]]:
    report = build_enterprise_entity_report(message, player_catalog=player_profiles, allow_fuzzy=True)
    return report["players"]


def detect_primary_player_entity(message: str, player_profiles: Any) -> dict[str, Any] | None:
    report = build_enterprise_entity_report(message, player_catalog=player_profiles, allow_fuzzy=True)
    return report["primary_player"]

# ============================================================
# SECTION 22 - LEGACY HELPERS
# ============================================================

def calculate_alias_confidence(alias: str) -> int:
    token_count = len(tokenize_entity_text(alias))
    if token_count >= 3:
        return 95
    if token_count == 2:
        return 88
    return 72


def deduplicate_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for entity in entities:
        key = (str(entity.get("entity_type")), str(entity.get("canonical_id") or entity.get("canonical_name")))
        existing = best.get(key)
        if existing is None or float(entity.get("confidence", 0.0)) > float(existing.get("confidence", 0.0)):
            best[key] = entity
    return sorted(best.values(), key=lambda item: float(item.get("confidence", 0.0)), reverse=True)


def build_entity_report(message: str, player_profiles: Any = None, team_catalog: Any = None) -> dict[str, Any]:
    return build_enterprise_entity_report(
        message,
        player_catalog=player_profiles,
        team_catalog=team_catalog,
    )

# ============================================================
# SECTION 23 - FUZZY CORRECTION COMPATIBILITY
# ============================================================

def apply_fuzzy_entity_corrections(message: str, player_profiles: Any = None, team_catalog: Any = None) -> dict[str, Any]:
    report = build_enterprise_entity_report(
        message,
        player_catalog=player_profiles,
        team_catalog=team_catalog,
        allow_fuzzy=True,
    )
    corrections: list[dict[str, Any]] = []
    corrected = str(message or "")
    for resolution_name in ("team_resolution", "player_resolution"):
        resolution = report[resolution_name]
        primary = resolution.get("primary")
        if not primary or primary.get("match_method") != MatchMethod.FUZZY.value:
            continue
        observed = primary.get("matched_text")
        canonical = primary.get("canonical_name")
        if observed and canonical:
            pattern = re.compile(re.escape(str(observed)), re.IGNORECASE)
            corrected = pattern.sub(str(canonical), corrected, count=1)
            corrections.append({
                "entity_type": primary.get("entity_type"),
                "original": observed,
                "corrected": canonical,
                "confidence": primary.get("confidence"),
            })
    return {
        "original_message": message,
        "corrected_message": corrected,
        "corrections": corrections,
        "fuzzy_report": report,
        "has_corrections": bool(corrections),
    }

# ============================================================
# SECTION 24 - DATABASE/Warehouse CATALOG ADAPTERS
# ============================================================

class WarehouseCatalogAdapter:
    """Convert warehouse query results into entity catalogs.

    The adapter intentionally accepts already-fetched records. It does not own a
    database session and therefore cannot leak persistence concerns into NLP.
    """

    def __init__(self, *, source: str = CatalogSource.WAREHOUSE.value) -> None:
        self.source = source
        self.normalizer = CatalogNormalizer()

    def teams(self, records: Any) -> list[CatalogEntity]:
        return self.normalizer.normalize_catalog(records, ENTITY_TYPE_TEAM, self.source)

    def players(self, records: Any) -> list[CatalogEntity]:
        return self.normalizer.normalize_catalog(records, ENTITY_TYPE_PLAYER, self.source)

    def catalogs(self, *, teams: Any, players: Any) -> dict[str, list[CatalogEntity]]:
        return {"teams": self.teams(teams), "players": self.players(players)}


def build_team_catalog_from_records(records: Any, source: str = CatalogSource.WAREHOUSE.value) -> list[CatalogEntity]:
    return CatalogNormalizer().normalize_catalog(records, ENTITY_TYPE_TEAM, source)


def build_player_catalog_from_records(records: Any, source: str = CatalogSource.WAREHOUSE.value) -> list[CatalogEntity]:
    return CatalogNormalizer().normalize_catalog(records, ENTITY_TYPE_PLAYER, source)

# ============================================================
# SECTION 25 - AMBIGUITY HELPERS
# ============================================================

def build_ambiguity_prompt(resolution: Mapping[str, Any], *, limit: int = 5) -> str | None:
    if resolution.get("status") != ResolutionStatus.AMBIGUOUS.value:
        return None
    candidates = resolution.get("candidates", [])[:limit]
    if not candidates:
        return "I found multiple possible matches. Please provide more detail."
    labels = []
    for candidate in candidates:
        label = candidate.get("canonical_name", "Unknown")
        team = candidate.get("team_name")
        position = candidate.get("position")
        details = ", ".join(part for part in (team, position) if part)
        labels.append(f"{label} ({details})" if details else label)
    return "I found multiple matches: " + "; ".join(labels) + ". Which one did you mean?"


def resolution_candidates(report: Mapping[str, Any], entity_type: str) -> list[dict[str, Any]]:
    key = "team_resolution" if entity_type == ENTITY_TYPE_TEAM else "player_resolution"
    return list(report.get(key, {}).get("candidates", []))

# ============================================================
# SECTION 26 - VALIDATION AND HEALTH
# ============================================================

def validate_entity_detection() -> dict[str, Any]:
    players = [
        {"player_id": 682998, "player_name": "Corbin Carroll", "team_id": 109, "team_name": "Arizona Diamondbacks", "position": "CF"},
        {"player_id": 592450, "player_name": "Aaron Judge", "team_id": 147, "team_name": "New York Yankees", "position": "RF", "nicknames": ["The Judge"]},
        {"player_id": 660271, "player_name": "Shohei Ohtani", "team_id": 119, "team_name": "Los Angeles Dodgers", "position": "DH"},
        {"player_id": 100001, "player_name": "Will Smith", "team_id": 119, "team_name": "Los Angeles Dodgers", "position": "C"},
        {"player_id": 100002, "player_name": "John Smith", "team_id": 111, "team_name": "Boston Red Sox", "position": "P"},
    ]
    cases = [
        ("show all MLB teams", False, False, True),
        ("show the Yankees roster", True, False, True),
        ("find Corbin Carroll", False, True, False),
        ("predict Aaron Judge home run", False, True, False),
        ("what is player 682998 ops", False, True, False),
        ("show smith", False, False, False),
    ]
    results = []
    passed = 0
    for message, expect_team, expect_player, expect_suppressed in cases:
        report = build_enterprise_entity_report(message, player_catalog=players)
        actual_team = bool(report.get("primary_team"))
        actual_player = bool(report.get("primary_player"))
        suppressed = bool(report.get("diagnostics", {}).get("player_resolution_suppressed"))
        ok = actual_team == expect_team and actual_player == expect_player and suppressed == expect_suppressed
        passed += int(ok)
        results.append({
            "message": message,
            "passed": ok,
            "team": report.get("primary_team", {}).get("canonical_name") if report.get("primary_team") else None,
            "player": report.get("primary_player", {}).get("canonical_name") if report.get("primary_player") else None,
            "player_status": report.get("player_resolution", {}).get("status"),
        })
    ambiguous = build_enterprise_entity_report("show smith", player_catalog=players)
    ambiguity_ok = ambiguous["player_resolution"]["status"] == ResolutionStatus.AMBIGUOUS.value
    return {
        "status": "ok" if passed == len(cases) and ambiguity_ok else "warning",
        "passed": passed,
        "total": len(cases),
        "ambiguity_test_passed": ambiguity_ok,
        "results": results,
    }


def entity_detection_health() -> dict[str, Any]:
    return {
        "module": MODULE_NAME,
        "path": MODULE_PATH,
        "version": MODULE_VERSION,
        "status": MODULE_STATUS,
        "database_imports": False,
        "warehouse_catalog_adapter": True,
        "boundary_safe_matching": True,
        "id_resolution": True,
        "alias_resolution": True,
        "nickname_resolution": True,
        "ambiguity_reporting": True,
        "team_to_player_suppression": True,
        "static_team_count": len(MLB_TEAM_ALIASES),
    }

# ============================================================
# SECTION 27 - CONFIGURATION
# ============================================================

ENTITY_DETECTION_CONFIGURATION = {
    "team_alias_detection_enabled": True,
    "player_catalog_detection_enabled": True,
    "database_backed_catalogs_supported": True,
    "warehouse_backed_catalogs_supported": True,
    "boundary_safe_matching_enabled": True,
    "fuzzy_correction_enabled": True,
    "ambiguity_detection_enabled": True,
    "team_question_player_suppression_enabled": True,
    "id_resolution_enabled": True,
    "nickname_resolution_enabled": True,
    "minimum_fuzzy_confidence": ENTITY_CONFIDENCE_FUZZY_MINIMUM,
    "ambiguity_margin": ENTITY_AMBIGUITY_MARGIN,
}

# ============================================================
# SECTION 28 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "MODULE_NAME", "MODULE_PATH", "MODULE_VERSION", "ENTITY_DETECTION_VERSION",
    "ENTITY_TYPE_TEAM", "ENTITY_TYPE_PLAYER", "ENTITY_TYPE_SUBJECT", "ENTITY_TYPE_OUTCOME",
    "ENTITY_TYPE_STAT", "ENTITY_TYPE_GAME", "ENTITY_TYPE_UNKNOWN",
    "MLB_TEAM_ALIASES", "MLB_TEAM_IDS", "MLB_TEAM_ABBREVIATIONS",
    "ENTITY_SUBJECT_KEYWORDS", "OUTCOME_ALIASES", "STAT_ALIASES",
    "MatchMethod", "ResolutionStatus", "CatalogSource",
    "CatalogEntity", "EntityCandidate", "EntityResolution", "EntityReport",
    "CatalogNormalizer", "EntityCatalogIndex", "EntityResolver", "WarehouseCatalogAdapter",
    "normalize_entity_text", "tokenize_entity_text", "boundary_contains", "find_boundary_matches",
    "build_static_team_catalog", "build_team_catalog_from_records", "build_player_catalog_from_records",
    "build_enterprise_entity_report", "build_entity_report", "detect_team_entities",
    "detect_primary_team_entity", "detect_player_entities", "detect_primary_player_entity",
    "detect_subject_entities", "detect_outcome_entities", "detect_stat_entities",
    "apply_fuzzy_entity_corrections", "deduplicate_entities", "calculate_alias_confidence",
    "build_ambiguity_prompt", "resolution_candidates", "validate_entity_detection",
    "entity_detection_health", "ENTITY_DETECTION_CONFIGURATION",
]

# ============================================================
# SECTION 29 - LOCAL VALIDATION
# ============================================================

if __name__ == "__main__":
    print(json.dumps(validate_entity_detection(), indent=2, default=str))

Library
/
Sports Predicti.
/
entity_detection.py
# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# PACKAGE: 04_ai/nlp
# FILE: entity_detection.py
# PURPOSE:
# Enterprise entity resolution for MLB teams, players, games,
# outcomes, statistics, aliases, nicknames, IDs, warehouse
# records, ambiguity handling, and downstream chat routing.
# ============================================================
"""
AISP2 enterprise entity detection and resolution engine.

This module converts free-form baseball language into normalized, auditable,
warehouse-compatible entities. It is deliberately independent from Flask,
SQLAlchemy, and any specific persistence layer. Callers may supply dictionaries,
dataclasses, ORM rows, Pydantic models, named tuples, or plain strings.

Primary guarantees
------------------
1. Every message is resolved independently.
2. Team-only questions are never forced into player-search routing.
3. Exact IDs outrank exact names; exact names outrank aliases; aliases outrank
   fuzzy candidates.
4. Matching is token-boundary safe. "as" cannot accidentally resolve Oakland
   Athletics and "sox" will not match inside unrelated words.
5. Ambiguous surnames and abbreviations produce ranked ambiguity results rather
   than silently selecting the wrong entity.
6. Database-backed catalogs are supported through adapters without importing a
   database package here.
7. Existing public functions from the earlier implementation remain available.
"""

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
from difflib import SequenceMatcher
from enum import Enum
from hashlib import sha256
import json
import math
import re
import time
from typing import Any, Final, Protocol, TypeVar
from uuid import uuid4

# ============================================================
# SECTION 02 - MODULE METADATA
# ============================================================

MODULE_NAME: Final[str] = "entity_detection"
MODULE_PATH: Final[str] = "04_ai/nlp/entity_detection.py"
MODULE_VERSION: Final[str] = "4.0.0"
MODULE_STATUS: Final[str] = "enterprise"
ENTITY_DETECTION_VERSION: Final[str] = "phase_10_part_11_enterprise_entity_resolution"

# ============================================================
# SECTION 03 - ENTITY TYPES
# ============================================================

ENTITY_TYPE_TEAM = "team"
ENTITY_TYPE_PLAYER = "player"
ENTITY_TYPE_SUBJECT = "subject"
ENTITY_TYPE_OUTCOME = "outcome"
ENTITY_TYPE_STAT = "stat"
ENTITY_TYPE_GAME = "game"
ENTITY_TYPE_SEASON = "season"
ENTITY_TYPE_DATE = "date"
ENTITY_TYPE_VENUE = "venue"
ENTITY_TYPE_POSITION = "position"
ENTITY_TYPE_UNKNOWN = "unknown"

# ============================================================
# SECTION 04 - CONFIDENCE LEVELS
# ============================================================

ENTITY_CONFIDENCE_ID = 1.00
ENTITY_CONFIDENCE_EXACT = 0.99
ENTITY_CONFIDENCE_ALIAS = 0.94
ENTITY_CONFIDENCE_NICKNAME = 0.91
ENTITY_CONFIDENCE_FULL_NAME = 0.96
ENTITY_CONFIDENCE_LAST_NAME = 0.78
ENTITY_CONFIDENCE_FUZZY_STRONG = 0.88
ENTITY_CONFIDENCE_FUZZY_MINIMUM = 0.74
ENTITY_CONFIDENCE_REVIEW = 0.66
ENTITY_AMBIGUITY_MARGIN = 0.035
MAX_ENTITY_CANDIDATES = 8

# Legacy integer constants retained for compatibility.
ENTITY_CONFIDENCE_STRONG = 90
ENTITY_CONFIDENCE_STANDARD = 82
ENTITY_CONFIDENCE_WEAK = 70

# ============================================================
# SECTION 05 - ENUMERATIONS
# ============================================================

class MatchMethod(str, Enum):
    ID = "id"
    EXACT_NAME = "exact_name"
    ALIAS = "alias"
    NICKNAME = "nickname"
    ABBREVIATION = "abbreviation"
    FULL_NAME = "full_name"
    LAST_NAME = "last_name"
    FIRST_LAST = "first_last"
    FUZZY = "fuzzy"
    CONTEXT = "context"


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"
    SUPPRESSED = "suppressed"


class CatalogSource(str, Enum):
    WAREHOUSE = "warehouse"
    DATABASE = "database"
    STATIC = "static"
    CALLER = "caller"
    CONTEXT = "context"

# ============================================================
# SECTION 06 - EXCEPTIONS
# ============================================================

class EntityDetectionError(RuntimeError):
    """Base exception for entity resolution failures."""


class EntityCatalogError(EntityDetectionError):
    """Raised when an entity catalog cannot be normalized."""


class EntityResolutionError(EntityDetectionError):
    """Raised when strict entity resolution fails."""

# ============================================================
# SECTION 07 - PROTOCOLS AND TYPE ALIASES
# ============================================================

T = TypeVar("T")


class SupportsModelDump(Protocol):
    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...


class SupportsDict(Protocol):
    def dict(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

# ============================================================
# SECTION 08 - MLB TEAM CATALOG
# ============================================================

MLB_TEAM_ALIASES: Final[dict[str, list[str]]] = {
    "Arizona Diamondbacks": ["arizona diamondbacks", "diamondbacks", "d backs", "dbacks", "ari", "arizona"],
    "Atlanta Braves": ["atlanta braves", "braves", "atl", "atlanta"],
    "Baltimore Orioles": ["baltimore orioles", "orioles", "os", "o s", "bal", "baltimore"],
    "Boston Red Sox": ["boston red sox", "red sox", "bos", "boston"],
    "Chicago Cubs": ["chicago cubs", "cubs", "chc", "north siders", "northsiders"],
    "Chicago White Sox": ["chicago white sox", "white sox", "cws", "chisox", "chi sox", "south siders", "southsiders"],
    "Cincinnati Reds": ["cincinnati reds", "reds", "cin", "cincinnati"],
    "Cleveland Guardians": ["cleveland guardians", "guardians", "cle", "cleveland"],
    "Colorado Rockies": ["colorado rockies", "rockies", "col", "colorado"],
    "Detroit Tigers": ["detroit tigers", "tigers", "det", "detroit"],
    "Houston Astros": ["houston astros", "astros", "hou", "houston"],
    "Kansas City Royals": ["kansas city royals", "royals", "kc", "kcr", "kansas city"],
    "Los Angeles Angels": ["los angeles angels", "angels", "la angels", "anaheim", "laa"],
    "Los Angeles Dodgers": ["los angeles dodgers", "dodgers", "la dodgers", "lad"],
    "Miami Marlins": ["miami marlins", "marlins", "mia", "miami"],
    "Milwaukee Brewers": ["milwaukee brewers", "brewers", "mil", "milwaukee"],
    "Minnesota Twins": ["minnesota twins", "twins", "min", "minnesota"],
    "New York Mets": ["new york mets", "mets", "nym", "ny mets"],
    "New York Yankees": ["new york yankees", "yankees", "nyy", "bronx bombers", "new york yanks", "ny yanks", "yanks"],
    "Oakland Athletics": ["oakland athletics", "athletics", "oakland", "oak"],
    "Philadelphia Phillies": ["philadelphia phillies", "phillies", "phils", "phi", "philadelphia"],
    "Pittsburgh Pirates": ["pittsburgh pirates", "pirates", "pit", "pittsburgh", "bucs"],
    "San Diego Padres": ["san diego padres", "padres", "sd", "sdp", "san diego"],
    "San Francisco Giants": ["san francisco giants", "giants", "sf", "sfg", "san francisco"],
    "Seattle Mariners": ["seattle mariners", "mariners", "sea", "seattle"],
    "St. Louis Cardinals": ["st louis cardinals", "saint louis cardinals", "cardinals", "cards", "stl", "st louis", "saint louis"],
    "Tampa Bay Rays": ["tampa bay rays", "rays", "tb", "tbr", "tampa bay", "tampa"],
    "Texas Rangers": ["texas rangers", "rangers", "tex", "texas"],
    "Toronto Blue Jays": ["toronto blue jays", "blue jays", "jays", "tor", "toronto"],
    "Washington Nationals": ["washington nationals", "nationals", "nats", "wsh", "washington"],
}

MLB_TEAM_IDS: Final[dict[str, int]] = {
    "Arizona Diamondbacks": 109, "Atlanta Braves": 144, "Baltimore Orioles": 110,
    "Boston Red Sox": 111, "Chicago Cubs": 112, "Chicago White Sox": 145,
    "Cincinnati Reds": 113, "Cleveland Guardians": 114, "Colorado Rockies": 115,
    "Detroit Tigers": 116, "Houston Astros": 117, "Kansas City Royals": 118,
    "Los Angeles Angels": 108, "Los Angeles Dodgers": 119, "Miami Marlins": 146,
    "Milwaukee Brewers": 158, "Minnesota Twins": 142, "New York Mets": 121,
    "New York Yankees": 147, "Oakland Athletics": 133, "Philadelphia Phillies": 143,
    "Pittsburgh Pirates": 134, "San Diego Padres": 135, "San Francisco Giants": 137,
    "Seattle Mariners": 136, "St. Louis Cardinals": 138, "Tampa Bay Rays": 139,
    "Texas Rangers": 140, "Toronto Blue Jays": 141, "Washington Nationals": 120,
}

MLB_TEAM_ABBREVIATIONS: Final[dict[str, str]] = {
    "Arizona Diamondbacks": "ARI", "Atlanta Braves": "ATL", "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS", "Chicago Cubs": "CHC", "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE", "Colorado Rockies": "COL",
    "Detroit Tigers": "DET", "Houston Astros": "HOU", "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD", "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN", "New York Mets": "NYM",
    "New York Yankees": "NYY", "Oakland Athletics": "OAK", "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT", "San Diego Padres": "SD", "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH",
}

# Ambiguous tokens must never resolve alone without supporting language.
AMBIGUOUS_TEAM_TOKENS: Final[frozenset[str]] = frozenset({
    "as", "a", "sox", "new york", "los angeles", "chicago", "washington",
    "giants", "rangers", "cardinals", "reds", "twins", "angels",
})

TEAM_LANGUAGE_MARKERS: Final[frozenset[str]] = frozenset({
    "team", "teams", "club", "clubs", "franchise", "roster", "lineup",
    "schedule", "record", "standings", "division", "bullpen", "rotation",
    "play", "plays", "game", "games", "mlb", "baseball",
})

PLAYER_LANGUAGE_MARKERS: Final[frozenset[str]] = frozenset({
    "player", "players", "hitter", "batter", "pitcher", "starter", "reliever",
    "closer", "rookie", "prospect", "profile", "stats", "statistics", "ops",
    "average", "era", "whip", "home run", "hit", "walk", "strikeout",
})

# ============================================================
# SECTION 09 - SUBJECT, OUTCOME, AND STAT VOCABULARY
# ============================================================

ENTITY_SUBJECT_KEYWORDS: Final[dict[str, list[str]]] = {
    "team": ["team", "club", "franchise", "organization", "squad"],
    "player": ["player", "batter", "hitter", "pitcher", "starter", "closer", "reliever"],
    "roster": ["roster", "lineup", "active roster", "players on", "who plays for", "who is on"],
    "probability_target": ["highest probability", "best probability", "highest chance", "best chance", "most likely", "best projection"],
    "schedule": ["schedule", "next game", "when do", "when does", "play next", "upcoming game"],
    "standings": ["standings", "record", "wins", "losses", "division rank"],
}

OUTCOME_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "home_run": ("home run", "homer", "homerun", "hr", "dinger", "go yard", "go deep", "long ball"),
    "hit": ("hit", "base hit", "record a hit", "get a hit"),
    "single": ("single", "one bagger"),
    "double": ("double", "two bagger"),
    "triple": ("triple", "three bagger"),
    "walk": ("walk", "base on balls", "bb"),
    "strikeout": ("strikeout", "strike out", "k", "punchout", "whiff"),
    "rbi": ("rbi", "run batted in", "drive in"),
    "run": ("run scored", "score a run"),
    "total_bases": ("total bases", "tb"),
    "stolen_base": ("stolen base", "steal a base", "sb"),
}

STAT_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "batting_average": ("batting average", "average", "avg", "ba"),
    "on_base_percentage": ("on base percentage", "on base", "obp"),
    "slugging_percentage": ("slugging percentage", "slugging", "slg"),
    "ops": ("ops", "on base plus slugging"),
    "home_runs": ("home runs", "homers", "hr"),
    "hits": ("hits", "base hits"),
    "doubles": ("doubles", "2b"),
    "triples": ("triples", "3b"),
    "walks": ("walks", "bb"),
    "strikeouts": ("strikeouts", "ks", "so"),
    "rbi": ("rbi", "runs batted in"),
    "runs": ("runs", "runs scored"),
    "stolen_bases": ("stolen bases", "sb"),
    "era": ("era", "earned run average"),
    "whip": ("whip",),
    "fip": ("fip",),
    "xfip": ("xfip",),
    "war": ("war",),
    "woba": ("woba",),
    "wrc_plus": ("wrc+", "wrc plus"),
    "barrel_rate": ("barrel rate", "barrels"),
    "hard_hit_rate": ("hard hit rate", "hard hit"),
    "exit_velocity": ("exit velocity", "ev"),
    "launch_angle": ("launch angle",),
}

# ============================================================
# SECTION 10 - DATA MODELS
# ============================================================

@dataclass(slots=True)
class CatalogEntity:
    entity_type: str
    canonical_id: str | int | None
    canonical_name: str
    aliases: tuple[str, ...] = ()
    nicknames: tuple[str, ...] = ()
    abbreviation: str | None = None
    team_id: str | int | None = None
    team_name: str | None = None
    position: str | None = None
    active: bool | None = None
    source: str = CatalogSource.CALLER.value
    metadata: dict[str, Any] = field(default_factory=dict)

    def all_names(self) -> tuple[str, ...]:
        values = [self.canonical_name, *self.aliases, *self.nicknames]
        if self.abbreviation:
            values.append(self.abbreviation)
        return tuple(dict.fromkeys(value for value in values if value))


@dataclass(slots=True)
class EntityCandidate:
    entity_type: str
    canonical_id: str | int | None
    canonical_name: str
    matched_text: str
    confidence: float
    match_method: str
    source: str
    start: int | None = None
    end: int | None = None
    team_id: str | int | None = None
    team_name: str | None = None
    position: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EntityResolution:
    entity_type: str
    status: ResolutionStatus
    primary: EntityCandidate | None
    candidates: list[EntityCandidate] = field(default_factory=list)
    query: str = ""
    reason: str = ""
    ambiguity_margin: float | None = None
    suppressed: bool = False

    @property
    def resolved(self) -> bool:
        return self.status == ResolutionStatus.RESOLVED and self.primary is not None

    @property
    def ambiguous(self) -> bool:
        return self.status == ResolutionStatus.AMBIGUOUS

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "status": self.status.value,
            "resolved": self.resolved,
            "ambiguous": self.ambiguous,
            "primary": self.primary.to_dict() if self.primary else None,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "query": self.query,
            "reason": self.reason,
            "ambiguity_margin": self.ambiguity_margin,
            "suppressed": self.suppressed,
        }


@dataclass(slots=True)
class EntityReport:
    request_id: str
    original_message: str
    normalized_message: str
    team_resolution: EntityResolution
    player_resolution: EntityResolution
    outcomes: list[EntityCandidate]
    statistics: list[EntityCandidate]
    subjects: list[EntityCandidate]
    all_entities: list[EntityCandidate]
    corrections: list[dict[str, Any]] = field(default_factory=list)
    processing_time_ms: float = 0.0
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        teams = [item.to_dict() for item in self.team_resolution.candidates]
        players = [item.to_dict() for item in self.player_resolution.candidates]
        subjects = [item.to_dict() for item in self.subjects]
        outcomes = [item.to_dict() for item in self.outcomes]
        statistics = [item.to_dict() for item in self.statistics]
        primary_team = self.team_resolution.primary.to_dict() if self.team_resolution.primary else None
        primary_player = self.player_resolution.primary.to_dict() if self.player_resolution.primary else None
        return {
            "request_id": self.request_id,
            "original_message": self.original_message,
            "message": self.normalized_message,
            "normalized_message": self.normalized_message,
            "teams": teams,
            "players": players,
            "subjects": subjects,
            "outcomes": outcomes,
            "statistics": statistics,
            "entities": [item.to_dict() for item in self.all_entities],
            "primary_team": primary_team,
            "primary_player": primary_player,
            "primary_subject": subjects[0] if subjects else None,
            "primary_outcome": outcomes[0] if outcomes else None,
            "primary_statistic": statistics[0] if statistics else None,
            "team_resolution": self.team_resolution.to_dict(),
            "player_resolution": self.player_resolution.to_dict(),
            "has_team": self.team_resolution.resolved or bool(self.team_resolution.candidates),
            "has_player": self.player_resolution.resolved or bool(self.player_resolution.candidates),
            "has_probability_target": any(item.canonical_name == "probability_target" for item in self.subjects),
            "team_ambiguous": self.team_resolution.ambiguous,
            "player_ambiguous": self.player_resolution.ambiguous,
            "clarification_required": self.team_resolution.ambiguous or self.player_resolution.ambiguous,
            "corrections": self.corrections,
            "processing_time_ms": round(self.processing_time_ms, 3),
            "diagnostics": self.diagnostics,
        }

# ============================================================
# SECTION 11 - GENERIC RECORD NORMALIZATION
# ============================================================

def object_to_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return dict(value.model_dump())
    if hasattr(value, "dict") and callable(value.dict):
        return dict(value.dict())
    if hasattr(value, "_asdict") and callable(value._asdict):
        return dict(value._asdict())
    if hasattr(value, "__table__"):
        try:
            return {column.name: getattr(value, column.name) for column in value.__table__.columns}
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        return {key: item for key, item in vars(value).items() if not key.startswith("_") and not callable(item)}
    if isinstance(value, str):
        return {"name": value}
    raise EntityCatalogError(f"Unsupported catalog record type: {type(value).__name__}")


def records_from_any(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        # Mapping may be name->record or a single record.
        record_markers = {"name", "player_name", "team_name", "id", "player_id", "team_id"}
        if record_markers.intersection(value.keys()):
            return [value]
        output = []
        for key, item in value.items():
            if isinstance(item, Mapping):
                merged = dict(item)
                merged.setdefault("name", key)
                output.append(merged)
            else:
                output.append({"name": key, "value": item})
        return output
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, Iterable):
        return list(value)
    return [value]


def first_present(record: Mapping[str, Any], candidates: Sequence[str], default: Any = None) -> Any:
    for candidate in candidates:
        value = record.get(candidate)
        if value not in (None, ""):
            return value
    return default


def sequence_value(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        chunks = re.split(r"[,;|]", value)
        return tuple(chunk.strip() for chunk in chunks if chunk.strip())
    if isinstance(value, Iterable) and not isinstance(value, (bytes, Mapping)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return (str(value).strip(),)

# ============================================================
# SECTION 12 - TEXT NORMALIZATION AND BOUNDARY MATCHING
# ============================================================

_APOSTROPHE_RE = re.compile(r"[’'`]")
_NON_WORD_RE = re.compile(r"[^a-z0-9+#]+")
_SPACE_RE = re.compile(r"\s+")


def normalize_entity_text(value: str | None) -> str:
    if not value:
        return ""
    text = str(value).lower().strip()
    text = _APOSTROPHE_RE.sub("", text)
    text = text.replace("&", " and ")
    text = _NON_WORD_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def tokenize_entity_text(value: str | None) -> list[str]:
    return normalize_entity_text(value).split()


def phrase_pattern(phrase: str) -> re.Pattern[str]:
    normalized = normalize_entity_text(phrase)
    if not normalized:
        return re.compile(r"(?!x)x")
    parts = [re.escape(part) for part in normalized.split()]
    return re.compile(r"(?<![a-z0-9])" + r"\s+".join(parts) + r"(?![a-z0-9])", re.IGNORECASE)


def find_boundary_matches(message: str, phrase: str) -> list[tuple[int, int, str]]:
    normalized_message = normalize_entity_text(message)
    pattern = phrase_pattern(phrase)
    return [(match.start(), match.end(), match.group(0)) for match in pattern.finditer(normalized_message)]


def boundary_contains(message: str, phrase: str) -> bool:
    return bool(find_boundary_matches(message, phrase))


def token_overlap(left: str, right: str) -> float:
    a = set(tokenize_entity_text(left))
    b = set(tokenize_entity_text(right))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def similarity(left: str, right: str) -> float:
    a = normalize_entity_text(left)
    b = normalize_entity_text(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    seq = SequenceMatcher(None, a, b).ratio()
    overlap = token_overlap(a, b)
    prefix = 1.0 if a.startswith(b) or b.startswith(a) else 0.0
    return max(seq, 0.68 * seq + 0.25 * overlap + 0.07 * prefix)


def canonical_fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()

# ============================================================
# SECTION 13 - CATALOG NORMALIZATION
# ============================================================

class CatalogNormalizer:
    TEAM_NAME_FIELDS = ("team_name", "name", "full_name", "club_name", "canonical_name")
    TEAM_ID_FIELDS = ("team_id", "mlb_team_id", "id", "teamId")
    PLAYER_NAME_FIELDS = ("player_name", "full_name", "name", "display_name", "canonical_name")
    PLAYER_ID_FIELDS = ("player_id", "mlb_player_id", "person_id", "id", "personId")

    def normalize_team(self, value: Any, source: str = CatalogSource.CALLER.value) -> CatalogEntity:
        record = object_to_mapping(value)
        name = str(first_present(record, self.TEAM_NAME_FIELDS, "")).strip()
        if not name:
            raise EntityCatalogError("Team record is missing a name")
        team_id = first_present(record, self.TEAM_ID_FIELDS, MLB_TEAM_IDS.get(name))
        abbreviation = first_present(record, ("abbreviation", "abbr", "team_code", "file_code"), MLB_TEAM_ABBREVIATIONS.get(name))
        aliases = sequence_value(first_present(record, ("aliases", "alias", "alternate_names", "team_aliases"), ()))
        nicknames = sequence_value(first_present(record, ("nicknames", "nickname", "short_name"), ()))
        static_aliases = tuple(MLB_TEAM_ALIASES.get(name, ()))
        merged_aliases = tuple(dict.fromkeys((*aliases, *static_aliases)))
        return CatalogEntity(
            entity_type=ENTITY_TYPE_TEAM,
            canonical_id=team_id,
            canonical_name=name,
            aliases=merged_aliases,
            nicknames=nicknames,
            abbreviation=str(abbreviation).strip() if abbreviation else None,
            source=source,
            metadata={key: item for key, item in record.items() if key not in {"aliases", "nicknames"}},
        )

    def normalize_player(self, value: Any, source: str = CatalogSource.CALLER.value) -> CatalogEntity:
        record = object_to_mapping(value)
        name = str(first_present(record, self.PLAYER_NAME_FIELDS, "")).strip()
        if not name:
            raise EntityCatalogError("Player record is missing a name")
        player_id = first_present(record, self.PLAYER_ID_FIELDS)
        team_id = first_present(record, ("team_id", "current_team_id", "mlb_team_id", "club_id"))
        team_name = first_present(record, ("team_name", "current_team_name", "club_name"))
        aliases = sequence_value(first_present(record, ("aliases", "alias", "alternate_names", "player_aliases"), ()))
        nicknames = sequence_value(first_present(record, ("nicknames", "nickname", "known_as"), ()))
        position = first_present(record, ("position", "position_name", "primary_position", "position_abbreviation"))
        active = first_present(record, ("active", "is_active", "current"))
        return CatalogEntity(
            entity_type=ENTITY_TYPE_PLAYER,
            canonical_id=player_id,
            canonical_name=name,
            aliases=aliases,
            nicknames=nicknames,
            team_id=team_id,
            team_name=str(team_name) if team_name else None,
            position=str(position) if position else None,
            active=bool(active) if active is not None else None,
            source=source,
            metadata={key: item for key, item in record.items() if key not in {"aliases", "nicknames"}},
        )

    def normalize_catalog(self, values: Any, entity_type: str, source: str = CatalogSource.CALLER.value) -> list[CatalogEntity]:
        entities: list[CatalogEntity] = []
        for value in records_from_any(values):
            try:
                entity = self.normalize_team(value, source) if entity_type == ENTITY_TYPE_TEAM else self.normalize_player(value, source)
                entities.append(entity)
            except EntityCatalogError:
                continue
        return self._deduplicate(entities)

    @staticmethod
    def _deduplicate(entities: Sequence[CatalogEntity]) -> list[CatalogEntity]:
        by_key: dict[tuple[str, str], CatalogEntity] = {}
        for entity in entities:
            key = (entity.entity_type, str(entity.canonical_id) if entity.canonical_id is not None else normalize_entity_text(entity.canonical_name))
            if key not in by_key:
                by_key[key] = entity
                continue
            existing = by_key[key]
            existing.aliases = tuple(dict.fromkeys((*existing.aliases, *entity.aliases)))
            existing.nicknames = tuple(dict.fromkeys((*existing.nicknames, *entity.nicknames)))
            existing.metadata.update(entity.metadata)
        return list(by_key.values())

# ============================================================
# SECTION 14 - STATIC TEAM CATALOG BUILDER
# ============================================================

def build_static_team_catalog() -> list[CatalogEntity]:
    normalizer = CatalogNormalizer()
    rows = []
    for name, aliases in MLB_TEAM_ALIASES.items():
        rows.append({
            "team_id": MLB_TEAM_IDS.get(name),
            "team_name": name,
            "abbreviation": MLB_TEAM_ABBREVIATIONS.get(name),
            "aliases": aliases,
        })
    return normalizer.normalize_catalog(rows, ENTITY_TYPE_TEAM, CatalogSource.STATIC.value)

# ============================================================
# SECTION 15 - INDEXES
# ============================================================

class EntityCatalogIndex:
    def __init__(self, entities: Sequence[CatalogEntity]) -> None:
        self.entities = list(entities)
        self.by_id: dict[str, CatalogEntity] = {}
        self.by_exact_name: dict[str, list[CatalogEntity]] = defaultdict(list)
        self.by_alias: dict[str, list[tuple[CatalogEntity, MatchMethod]]] = defaultdict(list)
        self.by_last_name: dict[str, list[CatalogEntity]] = defaultdict(list)
        self._build()

    def _build(self) -> None:
        for entity in self.entities:
            if entity.canonical_id is not None:
                self.by_id[str(entity.canonical_id)] = entity
            canonical = normalize_entity_text(entity.canonical_name)
            self.by_exact_name[canonical].append(entity)
            if entity.entity_type == ENTITY_TYPE_PLAYER:
                parts = canonical.split()
                if parts:
                    self.by_last_name[parts[-1]].append(entity)
            for alias in entity.aliases:
                normalized = normalize_entity_text(alias)
                if normalized:
                    self.by_alias[normalized].append((entity, MatchMethod.ALIAS))
            for nickname in entity.nicknames:
                normalized = normalize_entity_text(nickname)
                if normalized:
                    self.by_alias[normalized].append((entity, MatchMethod.NICKNAME))
            if entity.abbreviation:
                normalized = normalize_entity_text(entity.abbreviation)
                if normalized:
                    self.by_alias[normalized].append((entity, MatchMethod.ABBREVIATION))

    def fingerprint(self) -> str:
        return canonical_fingerprint([
            {
                "type": entity.entity_type,
                "id": entity.canonical_id,
                "name": entity.canonical_name,
                "aliases": entity.aliases,
                "nicknames": entity.nicknames,
                "abbreviation": entity.abbreviation,
            }
            for entity in self.entities
        ])

# ============================================================
# SECTION 16 - MESSAGE SIGNALS
# ============================================================

@dataclass(slots=True)
class MessageSignals:
    tokens: set[str]
    has_team_language: bool
    has_player_language: bool
    explicit_team_list: bool
    explicit_player_list: bool
    explicit_roster: bool
    explicit_schedule: bool
    explicit_prediction: bool
    numeric_ids: list[str]


def analyze_message_signals(message: str) -> MessageSignals:
    normalized = normalize_entity_text(message)
    tokens = set(normalized.split())
    return MessageSignals(
        tokens=tokens,
        has_team_language=bool(tokens & TEAM_LANGUAGE_MARKERS),
        has_player_language=bool(tokens & PLAYER_LANGUAGE_MARKERS),
        explicit_team_list=any(boundary_contains(normalized, phrase) for phrase in ("all teams", "list teams", "show teams", "mlb teams", "every team")),
        explicit_player_list=any(boundary_contains(normalized, phrase) for phrase in ("all players", "list players", "show players", "mlb players", "every player")),
        explicit_roster=any(boundary_contains(normalized, phrase) for phrase in ("roster", "lineup", "who is on", "players on")),
        explicit_schedule=any(boundary_contains(normalized, phrase) for phrase in ("schedule", "next game", "play next", "plays next")),
        explicit_prediction=any(boundary_contains(normalized, phrase) for phrase in ("predict", "probability", "chance", "odds", "projection", "likely")),
        numeric_ids=re.findall(r"\b\d{3,10}\b", normalized),
    )

# ============================================================
# SECTION 17 - ENTITY RESOLVER
# ============================================================

class EntityResolver:
    def __init__(
        self,
        *,
        team_catalog: Any = None,
        player_catalog: Any = None,
        source: str = CatalogSource.CALLER.value,
        fuzzy_threshold: float = ENTITY_CONFIDENCE_FUZZY_MINIMUM,
        ambiguity_margin: float = ENTITY_AMBIGUITY_MARGIN,
        max_candidates: int = MAX_ENTITY_CANDIDATES,
    ) -> None:
        normalizer = CatalogNormalizer()
        supplied_teams = normalizer.normalize_catalog(team_catalog, ENTITY_TYPE_TEAM, source) if team_catalog is not None else []
        static_teams = build_static_team_catalog()
        merged_teams = normalizer._deduplicate([*supplied_teams, *static_teams])
        players = normalizer.normalize_catalog(player_catalog, ENTITY_TYPE_PLAYER, source) if player_catalog is not None else []
        self.team_index = EntityCatalogIndex(merged_teams)
        self.player_index = EntityCatalogIndex(players)
        self.fuzzy_threshold = fuzzy_threshold
        self.ambiguity_margin = ambiguity_margin
        self.max_candidates = max_candidates

    def resolve_team(self, message: str, *, allow_fuzzy: bool = True) -> EntityResolution:
        signals = analyze_message_signals(message)
        # Generic collection requests do not identify one team, and player-only
        # questions must not manufacture a team through fuzzy similarity.
        fuzzy_allowed = (
            allow_fuzzy
            and signals.has_team_language
            and not signals.explicit_team_list
            and not signals.explicit_player_list
        )
        return self._resolve(
            message,
            self.team_index,
            ENTITY_TYPE_TEAM,
            allow_fuzzy=fuzzy_allowed,
        )

    def resolve_player(self, message: str, *, allow_fuzzy: bool = True, suppress_for_team_only: bool = True) -> EntityResolution:
        signals = analyze_message_signals(message)
        if suppress_for_team_only and self._is_team_only_question(signals, message):
            return EntityResolution(
                entity_type=ENTITY_TYPE_PLAYER,
                status=ResolutionStatus.SUPPRESSED,
                primary=None,
                candidates=[],
                query=message,
                reason="Player resolution suppressed because the message is explicitly team-scoped.",
                suppressed=True,
            )
        return self._resolve(message, self.player_index, ENTITY_TYPE_PLAYER, allow_fuzzy=allow_fuzzy)

    @staticmethod
    def _is_team_only_question(signals: MessageSignals, message: str) -> bool:
        if signals.explicit_player_list:
            return False
        if signals.explicit_team_list or signals.explicit_roster or signals.explicit_schedule:
            return True
        if signals.has_team_language and not signals.has_player_language:
            # Prediction language plus a player-like full name should still permit player resolution.
            normalized = normalize_entity_text(message)
            person_pattern = re.search(r"\b[a-z]{2,}\s+[a-z]{2,}\b", normalized)
            return not bool(signals.explicit_prediction and person_pattern)
        return False

    def _resolve(self, message: str, index: EntityCatalogIndex, entity_type: str, *, allow_fuzzy: bool) -> EntityResolution:
        normalized = normalize_entity_text(message)
        candidates: list[EntityCandidate] = []
        signals = analyze_message_signals(message)

        # 17.01 ID matches.
        for numeric_id in signals.numeric_ids:
            entity = index.by_id.get(numeric_id)
            if entity:
                candidates.append(self._candidate(entity, numeric_id, ENTITY_CONFIDENCE_ID, MatchMethod.ID))

        # 17.02 Exact canonical names.
        for canonical, entities in index.by_exact_name.items():
            matches = find_boundary_matches(normalized, canonical)
            for start, end, matched in matches:
                for entity in entities:
                    candidates.append(self._candidate(entity, matched, ENTITY_CONFIDENCE_EXACT, MatchMethod.EXACT_NAME, start, end))

        # 17.03 Aliases and abbreviations.
        for alias, entries in index.by_alias.items():
            if alias in AMBIGUOUS_TEAM_TOKENS and entity_type == ENTITY_TYPE_TEAM and not signals.has_team_language:
                continue
            matches = find_boundary_matches(normalized, alias)
            for start, end, matched in matches:
                for entity, method in entries:
                    base = ENTITY_CONFIDENCE_ALIAS
                    if method == MatchMethod.NICKNAME:
                        base = ENTITY_CONFIDENCE_NICKNAME
                    elif method == MatchMethod.ABBREVIATION:
                        base = 0.93 if len(alias) >= 3 else 0.86
                    candidates.append(self._candidate(entity, matched, base, method, start, end))

        # 17.04 Player surname matching only when meaningful.
        if entity_type == ENTITY_TYPE_PLAYER:
            for surname, entities in index.by_last_name.items():
                if len(surname) < 3 or not boundary_contains(normalized, surname):
                    continue
                for entity in entities:
                    confidence = ENTITY_CONFIDENCE_LAST_NAME
                    candidates.append(self._candidate(entity, surname, confidence, MatchMethod.LAST_NAME))

        # 17.05 Conservative fuzzy fallback.
        if allow_fuzzy and not candidates and index.entities:
            candidates.extend(self._fuzzy_candidates(normalized, index, entity_type))

        candidates = self._dedupe_rank(candidates)
        return self._finalize_resolution(entity_type, message, candidates)

    def _fuzzy_candidates(self, message: str, index: EntityCatalogIndex, entity_type: str) -> list[EntityCandidate]:
        tokens = message.split()
        windows: list[str] = []
        max_window = 4 if entity_type == ENTITY_TYPE_PLAYER else 3
        for size in range(1, min(max_window, len(tokens)) + 1):
            for position in range(0, len(tokens) - size + 1):
                window = " ".join(tokens[position:position + size])
                if len(window) >= 3:
                    windows.append(window)
        results: list[EntityCandidate] = []
        for entity in index.entities:
            best_score = 0.0
            best_text = ""
            for candidate_name in entity.all_names():
                normalized_name = normalize_entity_text(candidate_name)
                for window in windows:
                    score = similarity(window, normalized_name)
                    # Penalize one-token fuzzy player matches to prevent generic words.
                    if entity_type == ENTITY_TYPE_PLAYER and len(window.split()) == 1 and len(normalized_name.split()) > 1:
                        score *= 0.88
                    if score > best_score:
                        best_score = score
                        best_text = window
            if best_score >= self.fuzzy_threshold:
                results.append(self._candidate(entity, best_text, best_score, MatchMethod.FUZZY))
        return sorted(results, key=lambda item: item.confidence, reverse=True)[:self.max_candidates]

    @staticmethod
    def _candidate(
        entity: CatalogEntity,
        matched_text: str,
        confidence: float,
        method: MatchMethod,
        start: int | None = None,
        end: int | None = None,
    ) -> EntityCandidate:
        return EntityCandidate(
            entity_type=entity.entity_type,
            canonical_id=entity.canonical_id,
            canonical_name=entity.canonical_name,
            matched_text=matched_text,
            confidence=round(min(max(confidence, 0.0), 1.0), 4),
            match_method=method.value,
            source=entity.source,
            start=start,
            end=end,
            team_id=entity.team_id,
            team_name=entity.team_name,
            position=entity.position,
            metadata=dict(entity.metadata),
        )

    def _dedupe_rank(self, candidates: Sequence[EntityCandidate]) -> list[EntityCandidate]:
        best: dict[tuple[str, str], EntityCandidate] = {}
        for candidate in candidates:
            key = (candidate.entity_type, str(candidate.canonical_id) if candidate.canonical_id is not None else normalize_entity_text(candidate.canonical_name))
            existing = best.get(key)
            if existing is None or candidate.confidence > existing.confidence:
                best[key] = candidate
        return sorted(best.values(), key=lambda item: (-item.confidence, item.canonical_name))[:self.max_candidates]

    def _finalize_resolution(self, entity_type: str, query: str, candidates: list[EntityCandidate]) -> EntityResolution:
        if not candidates:
            return EntityResolution(entity_type, ResolutionStatus.NOT_FOUND, None, [], query, "No catalog entity matched the message.")
        if len(candidates) == 1:
            return EntityResolution(entity_type, ResolutionStatus.RESOLVED, candidates[0], candidates, query, "Single high-confidence entity resolved.")
        top, second = candidates[0], candidates[1]
        margin = top.confidence - second.confidence
        # Full-name and ID matches are authoritative unless duplicated by catalog corruption.
        authoritative = top.match_method in {MatchMethod.ID.value, MatchMethod.EXACT_NAME.value, MatchMethod.FULL_NAME.value}
        same_confidence = abs(top.confidence - second.confidence) <= self.ambiguity_margin
        same_surname = top.match_method == MatchMethod.LAST_NAME.value and second.match_method == MatchMethod.LAST_NAME.value
        if not authoritative and (same_confidence or same_surname):
            return EntityResolution(
                entity_type=entity_type,
                status=ResolutionStatus.AMBIGUOUS,
                primary=None,
                candidates=candidates,
                query=query,
                reason="Multiple plausible catalog entities matched the message.",
                ambiguity_margin=round(margin, 4),
            )
        return EntityResolution(
            entity_type=entity_type,
            status=ResolutionStatus.RESOLVED,
            primary=top,
            candidates=candidates,
            query=query,
            reason="Top-ranked entity exceeded competing candidates.",
            ambiguity_margin=round(margin, 4),
        )

# ============================================================
# SECTION 18 - VOCABULARY ENTITY DETECTION
# ============================================================

def detect_vocabulary_entities(message: str, vocabulary: Mapping[str, Sequence[str]], entity_type: str) -> list[EntityCandidate]:
    normalized = normalize_entity_text(message)
    candidates: list[EntityCandidate] = []
    for canonical, aliases in vocabulary.items():
        ordered_aliases = sorted(aliases, key=lambda item: len(normalize_entity_text(item)), reverse=True)
        for alias in ordered_aliases:
            matches = find_boundary_matches(normalized, alias)
            if not matches:
                continue
            start, end, matched = matches[0]
            confidence = 0.98 if normalize_entity_text(alias) == normalize_entity_text(canonical) else 0.93
            candidates.append(EntityCandidate(
                entity_type=entity_type,
                canonical_id=None,
                canonical_name=canonical,
                matched_text=matched,
                confidence=confidence,
                match_method=MatchMethod.ALIAS.value,
                source=CatalogSource.STATIC.value,
                start=start,
                end=end,
            ))
            break
    return sorted(candidates, key=lambda item: (-item.confidence, -(len(item.matched_text))))


def detect_subject_entities(message: str) -> list[dict[str, Any]]:
    return [item.to_dict() for item in detect_vocabulary_entities(message, ENTITY_SUBJECT_KEYWORDS, ENTITY_TYPE_SUBJECT)]


def detect_outcome_entities(message: str) -> list[dict[str, Any]]:
    return [item.to_dict() for item in detect_vocabulary_entities(message, OUTCOME_ALIASES, ENTITY_TYPE_OUTCOME)]


def detect_stat_entities(message: str) -> list[dict[str, Any]]:
    return [item.to_dict() for item in detect_vocabulary_entities(message, STAT_ALIASES, ENTITY_TYPE_STAT)]

# ============================================================
# SECTION 19 - PUBLIC ENTERPRISE REPORT BUILDER
# ============================================================

def build_enterprise_entity_report(
    message: str,
    *,
    player_catalog: Any = None,
    team_catalog: Any = None,
    player_profiles: Any = None,
    teams: Any = None,
    allow_fuzzy: bool = True,
    request_id: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    original = str(message or "")
    normalized = normalize_entity_text(original)
    player_catalog = player_catalog if player_catalog is not None else player_profiles
    team_catalog = team_catalog if team_catalog is not None else teams

    resolver = EntityResolver(team_catalog=team_catalog, player_catalog=player_catalog)
    team_resolution = resolver.resolve_team(normalized, allow_fuzzy=allow_fuzzy)
    player_resolution = resolver.resolve_player(normalized, allow_fuzzy=allow_fuzzy)

    outcome_objects = detect_vocabulary_entities(normalized, OUTCOME_ALIASES, ENTITY_TYPE_OUTCOME)
    stat_objects = detect_vocabulary_entities(normalized, STAT_ALIASES, ENTITY_TYPE_STAT)
    subject_objects = detect_vocabulary_entities(normalized, ENTITY_SUBJECT_KEYWORDS, ENTITY_TYPE_SUBJECT)

    all_entities = [
        *team_resolution.candidates,
        *player_resolution.candidates,
        *outcome_objects,
        *stat_objects,
        *subject_objects,
    ]

    report = EntityReport(
        request_id=request_id or str(uuid4()),
        original_message=original,
        normalized_message=normalized,
        team_resolution=team_resolution,
        player_resolution=player_resolution,
        outcomes=outcome_objects,
        statistics=stat_objects,
        subjects=subject_objects,
        all_entities=all_entities,
        processing_time_ms=(time.perf_counter() - started) * 1000.0,
        diagnostics={
            "module_version": MODULE_VERSION,
            "team_catalog_size": len(resolver.team_index.entities),
            "player_catalog_size": len(resolver.player_index.entities),
            "team_catalog_hash": resolver.team_index.fingerprint(),
            "player_catalog_hash": resolver.player_index.fingerprint(),
            "player_resolution_suppressed": player_resolution.suppressed,
            "independent_message_resolution": True,
        },
    )
    return report.to_dict()

# ============================================================
# SECTION 20 - BACKWARD-COMPATIBLE TEAM API
# ============================================================

def detect_team_entities(message: str, team_catalog: Any = None) -> list[dict[str, Any]]:
    report = build_enterprise_entity_report(message, team_catalog=team_catalog, allow_fuzzy=False)
    return report["teams"]


def detect_primary_team_entity(message: str, team_catalog: Any = None) -> dict[str, Any] | None:
    report = build_enterprise_entity_report(message, team_catalog=team_catalog, allow_fuzzy=True)
    return report["primary_team"]

# ============================================================
# SECTION 21 - BACKWARD-COMPATIBLE PLAYER API
# ============================================================

def detect_player_entities(message: str, player_profiles: Any) -> list[dict[str, Any]]:
    report = build_enterprise_entity_report(message, player_catalog=player_profiles, allow_fuzzy=True)
    return report["players"]


def detect_primary_player_entity(message: str, player_profiles: Any) -> dict[str, Any] | None:
    report = build_enterprise_entity_report(message, player_catalog=player_profiles, allow_fuzzy=True)
    return report["primary_player"]

# ============================================================
# SECTION 22 - LEGACY HELPERS
# ============================================================

def calculate_alias_confidence(alias: str) -> int:
    token_count = len(tokenize_entity_text(alias))
    if token_count >= 3:
        return 95
    if token_count == 2:
        return 88
    return 72


def deduplicate_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for entity in entities:
        key = (str(entity.get("entity_type")), str(entity.get("canonical_id") or entity.get("canonical_name")))
        existing = best.get(key)
        if existing is None or float(entity.get("confidence", 0.0)) > float(existing.get("confidence", 0.0)):
            best[key] = entity
    return sorted(best.values(), key=lambda item: float(item.get("confidence", 0.0)), reverse=True)


def build_entity_report(message: str, player_profiles: Any = None, team_catalog: Any = None) -> dict[str, Any]:
    return build_enterprise_entity_report(
        message,
        player_catalog=player_profiles,
        team_catalog=team_catalog,
    )

# ============================================================
# SECTION 23 - FUZZY CORRECTION COMPATIBILITY
# ============================================================

def apply_fuzzy_entity_corrections(message: str, player_profiles: Any = None, team_catalog: Any = None) -> dict[str, Any]:
    report = build_enterprise_entity_report(
        message,
        player_catalog=player_profiles,
        team_catalog=team_catalog,
        allow_fuzzy=True,
    )
    corrections: list[dict[str, Any]] = []
    corrected = str(message or "")
    for resolution_name in ("team_resolution", "player_resolution"):
        resolution = report[resolution_name]
        primary = resolution.get("primary")
        if not primary or primary.get("match_method") != MatchMethod.FUZZY.value:
            continue
        observed = primary.get("matched_text")
        canonical = primary.get("canonical_name")
        if observed and canonical:
            pattern = re.compile(re.escape(str(observed)), re.IGNORECASE)
            corrected = pattern.sub(str(canonical), corrected, count=1)
            corrections.append({
                "entity_type": primary.get("entity_type"),
                "original": observed,
                "corrected": canonical,
                "confidence": primary.get("confidence"),
            })
    return {
        "original_message": message,
        "corrected_message": corrected,
        "corrections": corrections,
        "fuzzy_report": report,
        "has_corrections": bool(corrections),
    }

# ============================================================
# SECTION 24 - DATABASE/Warehouse CATALOG ADAPTERS
# ============================================================

class WarehouseCatalogAdapter:
    """Convert warehouse query results into entity catalogs.

    The adapter intentionally accepts already-fetched records. It does not own a
    database session and therefore cannot leak persistence concerns into NLP.
    """

    def __init__(self, *, source: str = CatalogSource.WAREHOUSE.value) -> None:
        self.source = source
        self.normalizer = CatalogNormalizer()

    def teams(self, records: Any) -> list[CatalogEntity]:
        return self.normalizer.normalize_catalog(records, ENTITY_TYPE_TEAM, self.source)

    def players(self, records: Any) -> list[CatalogEntity]:
        return self.normalizer.normalize_catalog(records, ENTITY_TYPE_PLAYER, self.source)

    def catalogs(self, *, teams: Any, players: Any) -> dict[str, list[CatalogEntity]]:
        return {"teams": self.teams(teams), "players": self.players(players)}


def build_team_catalog_from_records(records: Any, source: str = CatalogSource.WAREHOUSE.value) -> list[CatalogEntity]:
    return CatalogNormalizer().normalize_catalog(records, ENTITY_TYPE_TEAM, source)


def build_player_catalog_from_records(records: Any, source: str = CatalogSource.WAREHOUSE.value) -> list[CatalogEntity]:
    return CatalogNormalizer().normalize_catalog(records, ENTITY_TYPE_PLAYER, source)

# ============================================================
# SECTION 25 - AMBIGUITY HELPERS
# ============================================================

def build_ambiguity_prompt(resolution: Mapping[str, Any], *, limit: int = 5) -> str | None:
    if resolution.get("status") != ResolutionStatus.AMBIGUOUS.value:
        return None
    candidates = resolution.get("candidates", [])[:limit]
    if not candidates:
        return "I found multiple possible matches. Please provide more detail."
    labels = []
    for candidate in candidates:
        label = candidate.get("canonical_name", "Unknown")
        team = candidate.get("team_name")
        position = candidate.get("position")
        details = ", ".join(part for part in (team, position) if part)
        labels.append(f"{label} ({details})" if details else label)
    return "I found multiple matches: " + "; ".join(labels) + ". Which one did you mean?"


def resolution_candidates(report: Mapping[str, Any], entity_type: str) -> list[dict[str, Any]]:
    key = "team_resolution" if entity_type == ENTITY_TYPE_TEAM else "player_resolution"
    return list(report.get(key, {}).get("candidates", []))

# ============================================================
# SECTION 26 - VALIDATION AND HEALTH
# ============================================================

def validate_entity_detection() -> dict[str, Any]:
    players = [
        {"player_id": 682998, "player_name": "Corbin Carroll", "team_id": 109, "team_name": "Arizona Diamondbacks", "position": "CF"},
        {"player_id": 592450, "player_name": "Aaron Judge", "team_id": 147, "team_name": "New York Yankees", "position": "RF", "nicknames": ["The Judge"]},
        {"player_id": 660271, "player_name": "Shohei Ohtani", "team_id": 119, "team_name": "Los Angeles Dodgers", "position": "DH"},
        {"player_id": 100001, "player_name": "Will Smith", "team_id": 119, "team_name": "Los Angeles Dodgers", "position": "C"},
        {"player_id": 100002, "player_name": "John Smith", "team_id": 111, "team_name": "Boston Red Sox", "position": "P"},
    ]
    cases = [
        ("show all MLB teams", False, False, True),
        ("show the Yankees roster", True, False, True),
        ("find Corbin Carroll", False, True, False),
        ("predict Aaron Judge home run", False, True, False),
        ("what is player 682998 ops", False, True, False),
        ("show smith", False, False, False),
    ]
    results = []
    passed = 0
    for message, expect_team, expect_player, expect_suppressed in cases:
        report = build_enterprise_entity_report(message, player_catalog=players)
        actual_team = bool(report.get("primary_team"))
        actual_player = bool(report.get("primary_player"))
        suppressed = bool(report.get("diagnostics", {}).get("player_resolution_suppressed"))
        ok = actual_team == expect_team and actual_player == expect_player and suppressed == expect_suppressed
        passed += int(ok)
        results.append({
            "message": message,
            "passed": ok,
            "team": report.get("primary_team", {}).get("canonical_name") if report.get("primary_team") else None,
            "player": report.get("primary_player", {}).get("canonical_name") if report.get("primary_player") else None,
            "player_status": report.get("player_resolution", {}).get("status"),
        })
    ambiguous = build_enterprise_entity_report("show smith", player_catalog=players)
    ambiguity_ok = ambiguous["player_resolution"]["status"] == ResolutionStatus.AMBIGUOUS.value
    return {
        "status": "ok" if passed == len(cases) and ambiguity_ok else "warning",
        "passed": passed,
        "total": len(cases),
        "ambiguity_test_passed": ambiguity_ok,
        "results": results,
    }


def entity_detection_health() -> dict[str, Any]:
    return {
        "module": MODULE_NAME,
        "path": MODULE_PATH,
        "version": MODULE_VERSION,
        "status": MODULE_STATUS,
        "database_imports": False,
        "warehouse_catalog_adapter": True,
        "boundary_safe_matching": True,
        "id_resolution": True,
        "alias_resolution": True,
        "nickname_resolution": True,
        "ambiguity_reporting": True,
        "team_to_player_suppression": True,
        "static_team_count": len(MLB_TEAM_ALIASES),
    }

# ============================================================
# SECTION 27 - CONFIGURATION
# ============================================================

ENTITY_DETECTION_CONFIGURATION = {
    "team_alias_detection_enabled": True,
    "player_catalog_detection_enabled": True,
    "database_backed_catalogs_supported": True,
    "warehouse_backed_catalogs_supported": True,
    "boundary_safe_matching_enabled": True,
    "fuzzy_correction_enabled": True,
    "ambiguity_detection_enabled": True,
    "team_question_player_suppression_enabled": True,
    "id_resolution_enabled": True,
    "nickname_resolution_enabled": True,
    "minimum_fuzzy_confidence": ENTITY_CONFIDENCE_FUZZY_MINIMUM,
    "ambiguity_margin": ENTITY_AMBIGUITY_MARGIN,
}

# ============================================================
# SECTION 28 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "MODULE_NAME", "MODULE_PATH", "MODULE_VERSION", "ENTITY_DETECTION_VERSION",
    "ENTITY_TYPE_TEAM", "ENTITY_TYPE_PLAYER", "ENTITY_TYPE_SUBJECT", "ENTITY_TYPE_OUTCOME",
    "ENTITY_TYPE_STAT", "ENTITY_TYPE_GAME", "ENTITY_TYPE_UNKNOWN",
    "MLB_TEAM_ALIASES", "MLB_TEAM_IDS", "MLB_TEAM_ABBREVIATIONS",
    "ENTITY_SUBJECT_KEYWORDS", "OUTCOME_ALIASES", "STAT_ALIASES",
    "MatchMethod", "ResolutionStatus", "CatalogSource",
    "CatalogEntity", "EntityCandidate", "EntityResolution", "EntityReport",
    "CatalogNormalizer", "EntityCatalogIndex", "EntityResolver", "WarehouseCatalogAdapter",
    "normalize_entity_text", "tokenize_entity_text", "boundary_contains", "find_boundary_matches",
    "build_static_team_catalog", "build_team_catalog_from_records", "build_player_catalog_from_records",
    "build_enterprise_entity_report", "build_entity_report", "detect_team_entities",
    "detect_primary_team_entity", "detect_player_entities", "detect_primary_player_entity",
    "detect_subject_entities", "detect_outcome_entities", "detect_stat_entities",
    "apply_fuzzy_entity_corrections", "deduplicate_entities", "calculate_alias_confidence",
    "build_ambiguity_prompt", "resolution_candidates", "validate_entity_detection",
    "entity_detection_health", "ENTITY_DETECTION_CONFIGURATION",
]

# ============================================================
# SECTION 29 - LOCAL VALIDATION
# ============================================================

if __name__ == "__main__":
    print(json.dumps(validate_entity_detection(), indent=2, default=str))