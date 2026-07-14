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

before comit n push; ==> Running 'uvicorn main:app --host 0.0.0.0 --port $PORT'
Traceback (most recent call last):
  File "/opt/render/project/src/.venv/bin/uvicorn", line 7, in <module>
    sys.exit(main())
             ~~~~^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/click/core.py", line 1569, in __call__
    return self.main(*args, **kwargs)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/click/core.py", line 1490, in main
    rv = self.invoke(ctx)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/click/core.py", line 1353, in invoke
    return ctx.invoke(self.callback, **ctx.params)
           ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/click/core.py", line 907, in invoke
    return callback(*args, **kwargs)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/uvicorn/main.py", line 440, in main
    run(
    ~~~^
        app,
        ^^^^
    ...<48 lines>...
        reset_contextvars=reset_contextvars,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/uvicorn/main.py", line 609, in run
    config.load_app()
    ~~~~~~~~~~~~~~~^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/uvicorn/config.py", line 427, in load_app
    return import_from_string(self.app)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/uvicorn/importer.py", line 19, in import_from_string
    module = importlib.import_module(module_str)
  File "/opt/render/project/python/Python-3.14.3/lib/python3.14/importlib/__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1398, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1342, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 938, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 759, in exec_module
  File "<frozen importlib._bootstrap>", line 491, in _call_with_frames_removed
  File "/opt/render/project/src/main.py", line 105, in <module>
    from nlp.nlu_engine import build_nlu_report
  File "/opt/render/project/src/04_ai/nlp/nlu_engine.py", line 7
    ↓
    ^
SyntaxError: invalid character '↓' (U+2193)
==> Exited with status 1
==> Common ways to troubleshoot your deploy: https://render.com/docs/troubleshooting-deploys
==> Running 'uvicorn main:app --host 0.0.0.0 --port $PORT'
Worked for 22s

The Render failure is a syntax error in the deployed copy of 04_ai/nlp/nlu_engine.py:

Line 7: ↓
SyntaxError: invalid character '↓'

That arrow was pasted into the Python file as executable text rather than inside a comment or docstring. FastAPI never reached startup.

Use this corrected Render-safe replacement:

nlu_engine_render_safe.py

Replace:

04_ai/nlp/nlu_engine.py

with the downloaded file.

Verification completed
Python compilation passed
build_nlu_report imports correctly
understand_baseball_message imports correctly
Internal NLU validation passed
12 of 12 tests passed
Smart punctuation and the stray arrow were removed from executable source

Then run locally before committing:

python -m py_compile 04_ai/nlp/nlu_engine.py

Then test the import:

python -c "import sys; sys.path.insert(0, '04_ai'); from nlp.nlu_engine import build_nlu_report, understand_baseball_message; print('NLU import passed')"

Expected result:

NLU import passed

Then commit both corrected NLP files:

git add 04_ai/nlp/nlu_engine.py
git add 04_ai/nlp/entity_detection.py
git commit -m "Phase 10 Part 11.1 - Fix NLU Render Syntax and Add Enterprise Entity Resolution - July 14 2026"
git push

Do not commit until both local commands pass.

Library
/
Sports Predicti.
/
nlu_engine_render_safe.py
# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# PACKAGE: 04_ai/nlp
# FILE: nlu_engine.py
# PURPOSE:
# Enterprise Natural Language Understanding orchestration for
# independent baseball-question classification, entity-aware
# routing, multi-turn follow-up resolution, diagnostics, and
# stable downstream chat-service contracts.
# ============================================================
"""
AISP2 enterprise Natural Language Understanding engine.

This module is the primary orchestration layer for baseball chat requests.
It intentionally contains no SQLAlchemy models, database table declarations,
HTTP routes, Flask objects, model training, or response rendering.

Responsibilities
----------------
1. Normalize one incoming user message into a stable text contract.
2. Reclassify every message independently from previous intent state.
3. Coordinate entity, intent, fuzzy, semantic, and context helpers.
4. Use conversation context only to resolve incomplete follow-ups.
5. Ensure a newly named player, team, game, stat, or outcome overrides old
   conversation context.
6. Detect ambiguity and missing information before backend routing.
7. Produce deterministic, serializable reports for the chat service.
8. Remain importable when sibling NLP modules are temporarily unavailable.

The orchestration rule is strict:

    CURRENT MESSAGE MEANING > EXPLICIT CURRENT ENTITIES > FOLLOW-UP CONTEXT
    > FALLBACK HEURISTICS > PREVIOUS INTENT

Previous intent is diagnostic only. It never locks or forces the next user
message into the previous request type.
"""

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, date, datetime, timedelta
from enum import Enum
from hashlib import sha256
import json
import logging
import math
import re
import unicodedata
from typing import Any, Final, Protocol
from uuid import uuid4

LOGGER = logging.getLogger(__name__)


# ============================================================
# SECTION 02 - MODULE METADATA
# ============================================================

NLU_ENGINE_NAME: Final[str] = "AISP2 Enterprise Baseball NLU Engine"
NLU_ENGINE_VERSION: Final[str] = "4.0.0"
NLU_ENGINE_PHASE: Final[str] = "Phase 10 Part 10.0"
NLU_ENGINE_PATH: Final[str] = "04_ai/nlp/nlu_engine.py"
NLU_ENGINE_STATUS: Final[str] = "enterprise_ready"


# ============================================================
# SECTION 03 - OPTIONAL SIBLING ENGINE IMPORTS
# ============================================================

# The package can run in both package-import and direct-script contexts.
try:  # pragma: no cover - import path depends on runtime packaging
    from .entity_detection import build_entity_report as _external_entity_report
except Exception:  # pragma: no cover
    try:
        from entity_detection import build_entity_report as _external_entity_report
    except Exception:
        _external_entity_report = None

try:  # pragma: no cover
    from .intent_detection import build_intent_report as _external_intent_report
except Exception:  # pragma: no cover
    try:
        from intent_detection import build_intent_report as _external_intent_report
    except Exception:
        _external_intent_report = None

try:  # pragma: no cover
    from .semantic_engine import interpret_baseball_question as _external_semantic_report
except Exception:  # pragma: no cover
    try:
        from semantic_engine import interpret_baseball_question as _external_semantic_report
    except Exception:
        _external_semantic_report = None

try:  # pragma: no cover
    from .context_builder import build_baseball_context as _external_context_report
except Exception:  # pragma: no cover
    try:
        from context_builder import build_baseball_context as _external_context_report
    except Exception:
        _external_context_report = None

try:  # pragma: no cover
    from .fuzzy_matching import build_fuzzy_nlp_report as _external_fuzzy_report
except Exception:  # pragma: no cover
    try:
        from fuzzy_matching import build_fuzzy_nlp_report as _external_fuzzy_report
    except Exception:
        _external_fuzzy_report = None


# ============================================================
# SECTION 04 - PUBLIC TASK CONSTANTS
# ============================================================

NLU_TASK_GENERAL = "general_baseball_question"
NLU_TASK_GREETING = "greeting"
NLU_TASK_HELP = "help"
NLU_TASK_LIST_TEAMS = "list_teams"
NLU_TASK_LIST_PLAYERS = "list_players"
NLU_TASK_TEAM_LOOKUP = "team_lookup"
NLU_TASK_TEAM_STATS = "team_stats"
NLU_TASK_TEAM_ROSTER = "team_roster"
NLU_TASK_TEAM_SCHEDULE = "team_schedule"
NLU_TASK_TEAM_PREDICTION = "team_prediction"
NLU_TASK_PLAYER_LOOKUP = "player_lookup"
NLU_TASK_PLAYER_STATS = "player_stats"
NLU_TASK_PLAYER_GAME_LOG = "player_game_log"
NLU_TASK_PLAYER_SPLITS = "player_splits"
NLU_TASK_PLAYER_PROBABILITY = "player_probability"
NLU_TASK_COMPARE_PLAYERS = "compare_players"
NLU_TASK_COMPARE_TEAMS = "compare_teams"
NLU_TASK_MATCHUP_ANALYSIS = "matchup_analysis"
NLU_TASK_GAME_LOOKUP = "game_lookup"
NLU_TASK_GAME_PREDICTION = "game_prediction"
NLU_TASK_STANDINGS = "standings"
NLU_TASK_LEAGUE_LEADERS = "league_leaders"
NLU_TASK_DATABASE_STATUS = "database_status"
NLU_TASK_WAREHOUSE_STATUS = "warehouse_status"
NLU_TASK_DATA_FRESHNESS = "data_freshness"
NLU_TASK_MODEL_STATUS = "model_status"
NLU_TASK_EXPLAIN_MODEL = "explain_model"
NLU_TASK_CLARIFICATION = "clarification_required"
NLU_TASK_UNSUPPORTED = "unsupported"
NLU_TASK_BEST_TEAM_PROBABILITY = "best_team_probability"
NLU_TASK_BEST_OVERALL_PROBABILITY = "best_overall_probability"
NLU_TASK_ROSTER_LOOKUP = NLU_TASK_TEAM_ROSTER

SUPPORTED_TASKS: Final[tuple[str, ...]] = (
    NLU_TASK_GENERAL,
    NLU_TASK_GREETING,
    NLU_TASK_HELP,
    NLU_TASK_LIST_TEAMS,
    NLU_TASK_LIST_PLAYERS,
    NLU_TASK_TEAM_LOOKUP,
    NLU_TASK_TEAM_STATS,
    NLU_TASK_TEAM_ROSTER,
    NLU_TASK_TEAM_SCHEDULE,
    NLU_TASK_TEAM_PREDICTION,
    NLU_TASK_PLAYER_LOOKUP,
    NLU_TASK_PLAYER_STATS,
    NLU_TASK_PLAYER_GAME_LOG,
    NLU_TASK_PLAYER_SPLITS,
    NLU_TASK_PLAYER_PROBABILITY,
    NLU_TASK_COMPARE_PLAYERS,
    NLU_TASK_COMPARE_TEAMS,
    NLU_TASK_MATCHUP_ANALYSIS,
    NLU_TASK_GAME_LOOKUP,
    NLU_TASK_GAME_PREDICTION,
    NLU_TASK_STANDINGS,
    NLU_TASK_LEAGUE_LEADERS,
    NLU_TASK_DATABASE_STATUS,
    NLU_TASK_WAREHOUSE_STATUS,
    NLU_TASK_DATA_FRESHNESS,
    NLU_TASK_MODEL_STATUS,
    NLU_TASK_EXPLAIN_MODEL,
    NLU_TASK_CLARIFICATION,
    NLU_TASK_UNSUPPORTED,
    NLU_TASK_BEST_TEAM_PROBABILITY,
    NLU_TASK_BEST_OVERALL_PROBABILITY,
)


# ============================================================
# SECTION 05 - PUBLIC SCOPE CONSTANTS
# ============================================================

NLU_SCOPE_UNKNOWN = "unknown"
NLU_SCOPE_ALL_PLAYERS = "all_players"
NLU_SCOPE_TEAM_PLAYERS = "team_players"
NLU_SCOPE_SINGLE_PLAYER = "single_player"
NLU_SCOPE_MULTIPLE_PLAYERS = "multiple_players"
NLU_SCOPE_ALL_TEAMS = "all_teams"
NLU_SCOPE_TEAM = "team"
NLU_SCOPE_MULTIPLE_TEAMS = "multiple_teams"
NLU_SCOPE_GAME = "game"
NLU_SCOPE_LEAGUE = "league"
NLU_SCOPE_SYSTEM = "system"

SUPPORTED_SCOPES: Final[tuple[str, ...]] = (
    NLU_SCOPE_UNKNOWN,
    NLU_SCOPE_ALL_PLAYERS,
    NLU_SCOPE_TEAM_PLAYERS,
    NLU_SCOPE_SINGLE_PLAYER,
    NLU_SCOPE_MULTIPLE_PLAYERS,
    NLU_SCOPE_ALL_TEAMS,
    NLU_SCOPE_TEAM,
    NLU_SCOPE_MULTIPLE_TEAMS,
    NLU_SCOPE_GAME,
    NLU_SCOPE_LEAGUE,
    NLU_SCOPE_SYSTEM,
)


# ============================================================
# SECTION 06 - ENTITY, STAT, OUTCOME, AND TIME CONSTANTS
# ============================================================

ENTITY_PLAYER = "player"
ENTITY_TEAM = "team"
ENTITY_GAME = "game"
ENTITY_STATISTIC = "statistic"
ENTITY_OUTCOME = "outcome"
ENTITY_DATE = "date"
ENTITY_SEASON = "season"
ENTITY_VENUE = "venue"
ENTITY_POSITION = "position"
ENTITY_OPPONENT = "opponent"
ENTITY_PITCHER = "pitcher"
ENTITY_BATTER = "batter"
ENTITY_LIMIT = "limit"

SUPPORTED_OUTCOMES: Final[tuple[str, ...]] = (
    "hit",
    "single",
    "double",
    "triple",
    "home_run",
    "walk",
    "strikeout",
    "rbi",
    "run",
    "stolen_base",
    "total_bases",
    "team_win",
    "team_runs",
)

SUPPORTED_STATISTICS: Final[tuple[str, ...]] = (
    "batting_average",
    "on_base_percentage",
    "slugging_percentage",
    "ops",
    "home_runs",
    "hits",
    "singles",
    "doubles",
    "triples",
    "walks",
    "strikeouts",
    "rbi",
    "runs",
    "stolen_bases",
    "total_bases",
    "plate_appearances",
    "at_bats",
    "woba",
    "wrc_plus",
    "war",
    "era",
    "whip",
    "fip",
    "xfip",
    "strikeout_rate",
    "walk_rate",
    "barrel_rate",
    "hard_hit_rate",
    "exit_velocity",
    "launch_angle",
    "xba",
    "xslg",
    "xwoba",
    "chase_rate",
    "whiff_rate",
    "contact_rate",
    "wins",
    "losses",
    "win_percentage",
    "runs_per_game",
    "runs_allowed_per_game",
)


# ============================================================
# SECTION 07 - ENUMERATIONS
# ============================================================

class ConfidenceBand(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class EntitySource(str, Enum):
    CURRENT_EXACT = "current_exact"
    CURRENT_ALIAS = "current_alias"
    CURRENT_FUZZY = "current_fuzzy"
    CURRENT_HEURISTIC = "current_heuristic"
    CONVERSATION_CONTEXT = "conversation_context"
    EXTERNAL_ENGINE = "external_engine"
    UNKNOWN = "unknown"


class ClarificationReason(str, Enum):
    NONE = "none"
    EMPTY_MESSAGE = "empty_message"
    MISSING_PLAYER = "missing_player"
    MISSING_TEAM = "missing_team"
    MISSING_OUTCOME = "missing_outcome"
    MISSING_STATISTIC = "missing_statistic"
    AMBIGUOUS_PLAYER = "ambiguous_player"
    AMBIGUOUS_TEAM = "ambiguous_team"
    AMBIGUOUS_INTENT = "ambiguous_intent"
    UNSUPPORTED_REQUEST = "unsupported_request"


# ============================================================
# SECTION 08 - CORE DATA CONTRACTS
# ============================================================

@dataclass(slots=True)
class NormalizedMessage:
    request_id: str
    original: str
    normalized: str
    tokens: list[str]
    token_set: set[str]
    question_type: str
    is_empty: bool
    corrections: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "original": self.original,
            "normalized": self.normalized,
            "tokens": self.tokens,
            "question_type": self.question_type,
            "is_empty": self.is_empty,
            "corrections": self.corrections,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(slots=True)
class ResolvedEntity:
    entity_type: str
    canonical_name: str | None = None
    entity_id: int | str | None = None
    matched_text: str | None = None
    confidence: float = 0.0
    source: EntitySource = EntitySource.UNKNOWN
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "canonical_name": self.canonical_name,
            "entity_id": self.entity_id,
            "matched_text": self.matched_text,
            "confidence": round(float(self.confidence), 4),
            "source": self.source.value,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class ConversationContext:
    last_player_id: int | str | None = None
    last_player_name: str | None = None
    last_team_id: int | str | None = None
    last_team_name: str | None = None
    last_game_id: int | str | None = None
    last_game_label: str | None = None
    last_statistic: str | None = None
    last_outcome: str | None = None
    last_intent: str | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_any(cls, value: Any) -> "ConversationContext":
        if value is None:
            return cls()
        if isinstance(value, cls):
            return value
        if is_dataclass(value):
            value = asdict(value)
        if isinstance(value, Mapping):
            return cls(
                last_player_id=value.get("last_player_id"),
                last_player_name=value.get("last_player_name"),
                last_team_id=value.get("last_team_id"),
                last_team_name=value.get("last_team_name"),
                last_game_id=value.get("last_game_id"),
                last_game_label=value.get("last_game_label"),
                last_statistic=value.get("last_statistic"),
                last_outcome=value.get("last_outcome"),
                last_intent=value.get("last_intent"),
                updated_at=parse_datetime(value.get("updated_at")),
                metadata=dict(value.get("metadata") or {}),
            )
        return cls()

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_player_id": self.last_player_id,
            "last_player_name": self.last_player_name,
            "last_team_id": self.last_team_id,
            "last_team_name": self.last_team_name,
            "last_game_id": self.last_game_id,
            "last_game_label": self.last_game_label,
            "last_statistic": self.last_statistic,
            "last_outcome": self.last_outcome,
            "last_intent": self.last_intent,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class IntentCandidate:
    intent: str
    score: float
    evidence: list[str] = field(default_factory=list)
    negative_evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "score": round(float(self.score), 4),
            "evidence": self.evidence,
            "negative_evidence": self.negative_evidence,
        }


@dataclass(slots=True)
class NLUReport:
    request_id: str
    original_message: str
    normalized_message: str
    intent: str
    scope: str
    confidence: float
    confidence_band: ConfidenceBand
    routing_target: str
    entities: dict[str, Any]
    intent_candidates: list[IntentCandidate]
    context_used: bool
    context_resolution: dict[str, Any]
    clarification_required: bool
    clarification_reason: ClarificationReason
    clarification_prompt: str | None
    missing: dict[str, bool]
    diagnostics: dict[str, Any]
    next_context: ConversationContext
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "original_message": self.original_message,
            "normalized_message": self.normalized_message,
            "intent": self.intent,
            "task": self.intent,
            "scope": self.scope,
            "confidence": round(float(self.confidence), 4),
            "confidence_percent": round(float(self.confidence) * 100.0, 2),
            "confidence_band": self.confidence_band.value,
            "routing_target": self.routing_target,
            "entities": self.entities,
            "intent_candidates": [item.to_dict() for item in self.intent_candidates],
            "context_used": self.context_used,
            "context_resolution": self.context_resolution,
            "clarification_required": self.clarification_required,
            "clarification_reason": self.clarification_reason.value,
            "clarification_prompt": self.clarification_prompt,
            "missing": self.missing,
            "routing_ready": not self.clarification_required,
            "diagnostics": self.diagnostics,
            "next_context": self.next_context.to_dict(),
            "created_at": self.created_at.isoformat(),
            "engine": {
                "name": NLU_ENGINE_NAME,
                "version": NLU_ENGINE_VERSION,
                "phase": NLU_ENGINE_PHASE,
                "path": NLU_ENGINE_PATH,
            },
        }


# ============================================================
# SECTION 09 - CONFIGURATION
# ============================================================

@dataclass(slots=True)
class NLUConfig:
    enable_external_entity_engine: bool = True
    enable_external_intent_engine: bool = True
    enable_external_semantic_engine: bool = True
    enable_external_context_engine: bool = True
    enable_external_fuzzy_engine: bool = True
    allow_context_pronoun_resolution: bool = True
    allow_context_ellipsis_resolution: bool = True
    context_max_age_hours: float = 24.0
    minimum_confidence: float = 0.35
    clarification_confidence: float = 0.52
    ambiguity_margin: float = 0.08
    fuzzy_threshold: float = 0.78
    max_catalog_candidates: int = 8
    strict: bool = False

    def validate(self) -> None:
        for field_name in (
            "minimum_confidence",
            "clarification_confidence",
            "ambiguity_margin",
            "fuzzy_threshold",
        ):
            value = float(getattr(self, field_name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1")
        if self.context_max_age_hours < 0:
            raise ValueError("context_max_age_hours cannot be negative")
        if self.max_catalog_candidates <= 0:
            raise ValueError("max_catalog_candidates must be positive")


DEFAULT_CONFIG = NLUConfig()


# ============================================================
# SECTION 10 - NORMALIZATION TABLES
# ============================================================

DIRECT_TOKEN_REPLACEMENTS: Final[dict[str, str]] = {
    "whos": "who is",
    "whats": "what is",
    "wheres": "where is",
    "hows": "how is",
    "cant": "cannot",
    "wont": "will not",
    "dont": "do not",
    "doesnt": "does not",
    "isnt": "is not",
    "arent": "are not",
    "im": "i am",
    "ive": "i have",
    "probablity": "probability",
    "probalility": "probability",
    "prediciton": "prediction",
    "predicitons": "predictions",
    "projecton": "projection",
    "basebal": "baseball",
    "baseabll": "baseball",
    "rostor": "roster",
    "likley": "likely",
    "homerun": "home run",
    "homeurn": "home run",
    "strikout": "strikeout",
    "striekout": "strikeout",
    "ribbies": "rbi",
    "ribbie": "rbi",
    "dingers": "home run",
    "dinger": "home run",
    "punchouts": "strikeouts",
    "punchout": "strikeout",
}

PHRASE_REPLACEMENTS: Final[dict[str, str]] = {
    "home runn": "home run",
    "home-run": "home run",
    "stat cast": "statcast",
    "runs batted in": "rbi",
    "run batted in": "rbi",
    "base knock": "hit",
    "long ball": "home run",
    "go yard": "hit a home run",
    "goes yard": "hits a home run",
    "to homer": "to hit a home run",
    "hit bomb": "hit a home run",
    "hit a bomb": "hit a home run",
    "get a hit": "record a hit",
    "gets a hit": "records a hit",
    "strike out": "strikeout",
    "total base": "total bases",
    "best shot": "highest probability",
    "top shot": "highest probability",
    "best bet": "highest probability",
    "highest chance": "highest probability",
    "best chance": "highest probability",
    "top chance": "highest probability",
    "highest odds": "highest probability",
    "best odds": "highest probability",
    "most probable": "most likely",
}

OUTCOME_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "home_run": ("home run", "homer", "hr", "dinger", "go deep", "go yard"),
    "hit": ("record a hit", "base hit", "hit"),
    "single": ("single", "one bagger"),
    "double": ("double", "two bagger", "two base hit"),
    "triple": ("triple", "three bagger", "three base hit"),
    "walk": ("walk", "base on balls", "bb"),
    "strikeout": ("strikeout", "strikeouts", "k", "ks", "whiff", "punchout"),
    "rbi": ("rbi", "drive in", "knock in"),
    "run": ("run scored", "score a run", "scores a run"),
    "stolen_base": ("stolen base", "steal a base", "sb"),
    "total_bases": ("total bases", "tb"),
    "team_win": ("win", "winner", "moneyline"),
    "team_runs": ("team runs", "runs scored", "run total"),
}

STAT_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "batting_average": ("batting average", "average", "avg", "ba"),
    "on_base_percentage": ("on base percentage", "on base", "obp"),
    "slugging_percentage": ("slugging percentage", "slugging", "slg"),
    "ops": ("ops",),
    "home_runs": ("home runs", "homers", "hr total"),
    "hits": ("hits", "hit total"),
    "singles": ("singles",),
    "doubles": ("doubles",),
    "triples": ("triples",),
    "walks": ("walks", "bb total"),
    "strikeouts": ("strikeouts", "k total", "ks"),
    "rbi": ("rbi",),
    "runs": ("runs",),
    "stolen_bases": ("stolen bases", "sb total"),
    "total_bases": ("total bases", "tb"),
    "plate_appearances": ("plate appearances", "pa"),
    "at_bats": ("at bats", "ab"),
    "woba": ("woba",),
    "wrc_plus": ("wrc+", "wrc plus", "wrc"),
    "war": ("war",),
    "era": ("era",),
    "whip": ("whip",),
    "fip": ("fip",),
    "xfip": ("xfip",),
    "strikeout_rate": ("strikeout rate", "k rate", "k percentage"),
    "walk_rate": ("walk rate", "bb rate", "walk percentage"),
    "barrel_rate": ("barrel rate", "barrels"),
    "hard_hit_rate": ("hard hit rate", "hard hit"),
    "exit_velocity": ("exit velocity", "ev"),
    "launch_angle": ("launch angle",),
    "xba": ("xba", "expected batting average"),
    "xslg": ("xslg", "expected slugging"),
    "xwoba": ("xwoba", "expected woba"),
    "chase_rate": ("chase rate",),
    "whiff_rate": ("whiff rate",),
    "contact_rate": ("contact rate",),
    "wins": ("wins",),
    "losses": ("losses",),
    "win_percentage": ("win percentage", "winning percentage", "record"),
    "runs_per_game": ("runs per game", "rpg"),
    "runs_allowed_per_game": ("runs allowed per game",),
}

PRONOUN_PLAYER_PHRASES: Final[tuple[str, ...]] = (
    "he", "him", "his", "that player", "the player", "this player",
    "that hitter", "that pitcher", "the hitter", "the pitcher",
)

PRONOUN_TEAM_PHRASES: Final[tuple[str, ...]] = (
    "they", "them", "their", "that team", "the team", "this team",
    "that club", "the club",
)

RESET_CONTEXT_PHRASES: Final[tuple[str, ...]] = (
    "new question", "forget that", "clear context", "start over", "reset chat",
)


# ============================================================
# SECTION 11 - INTENT RULES
# ============================================================

@dataclass(frozen=True, slots=True)
class IntentRule:
    intent: str
    routing_target: str
    phrases: tuple[str, ...] = ()
    required_any: tuple[str, ...] = ()
    negative_phrases: tuple[str, ...] = ()
    base_weight: float = 0.0
    phrase_weight: float = 1.0
    entity_bonus: tuple[str, ...] = ()
    priority: int = 100


INTENT_RULES: Final[tuple[IntentRule, ...]] = (
    IntentRule(
        NLU_TASK_DATABASE_STATUS,
        "database_status_handler",
        phrases=("database status", "is the database connected", "database connected", "database health"),
        required_any=("database", "db"),
        base_weight=2.0,
        priority=1,
    ),
    IntentRule(
        NLU_TASK_WAREHOUSE_STATUS,
        "warehouse_status_handler",
        phrases=("warehouse status", "ingestion status", "data warehouse", "rows loaded"),
        required_any=("warehouse", "ingestion", "loaded"),
        base_weight=1.8,
        priority=2,
    ),
    IntentRule(
        NLU_TASK_DATA_FRESHNESS,
        "data_freshness_handler",
        phrases=("how fresh is the data", "latest ingestion", "last updated", "data freshness", "stale data"),
        required_any=("fresh", "updated", "latest", "stale"),
        base_weight=1.8,
        priority=3,
    ),
    IntentRule(
        NLU_TASK_MODEL_STATUS,
        "model_status_handler",
        phrases=("model status", "prediction engine status", "is the model ready"),
        required_any=("model", "engine"),
        base_weight=1.5,
        priority=4,
    ),
    IntentRule(
        NLU_TASK_EXPLAIN_MODEL,
        "explainability_handler",
        phrases=("explain the model", "how does the model work", "why that prediction", "why that probability", "what factors"),
        required_any=("why", "explain", "factors", "reasoning"),
        base_weight=1.3,
        priority=5,
    ),
    IntentRule(
        NLU_TASK_HELP,
        "help_handler",
        phrases=("what can you do", "how do i use", "sample questions", "show me what you can do", "help"),
        base_weight=1.3,
        priority=6,
    ),
    IntentRule(
        NLU_TASK_LIST_TEAMS,
        "list_teams_handler",
        phrases=("list teams", "show all teams", "all mlb teams", "every mlb team", "what teams", "which teams", "team list"),
        required_any=("teams", "clubs", "franchises"),
        negative_phrases=("team stats", "team roster", "team schedule"),
        base_weight=1.5,
        priority=10,
    ),
    IntentRule(
        NLU_TASK_LIST_PLAYERS,
        "list_players_handler",
        phrases=("list players", "show all players", "all mlb players", "what players", "which players", "player list"),
        required_any=("players",),
        negative_phrases=("player stats", "player prediction"),
        base_weight=1.5,
        priority=11,
    ),
    IntentRule(
        NLU_TASK_COMPARE_PLAYERS,
        "compare_players_handler",
        phrases=("compare players", "who is better", "which player is better", "between", "versus", " vs "),
        entity_bonus=(ENTITY_PLAYER,),
        base_weight=1.2,
        priority=12,
    ),
    IntentRule(
        NLU_TASK_COMPARE_TEAMS,
        "compare_teams_handler",
        phrases=("compare teams", "which team is better", "team comparison", "who wins", "team matchup"),
        entity_bonus=(ENTITY_TEAM,),
        base_weight=1.2,
        priority=13,
    ),
    IntentRule(
        NLU_TASK_GAME_PREDICTION,
        "game_prediction_handler",
        phrases=("predict the game", "game prediction", "who will win", "win probability", "game odds"),
        required_any=("predict", "prediction", "probability", "win", "odds"),
        base_weight=1.5,
        priority=14,
    ),
    IntentRule(
        NLU_TASK_TEAM_PREDICTION,
        "team_prediction_handler",
        phrases=("team prediction", "team win probability", "chances to win", "will the team win"),
        required_any=("predict", "probability", "chance", "win"),
        entity_bonus=(ENTITY_TEAM,),
        base_weight=1.4,
        priority=15,
    ),
    IntentRule(
        NLU_TASK_PLAYER_PROBABILITY,
        "player_prediction_handler",
        phrases=("predict", "probability", "what are the chances", "how likely", "will he", "will she", "projection", "player prop"),
        required_any=("predict", "probability", "chance", "likely", "projection", "odds", "will"),
        entity_bonus=(ENTITY_PLAYER, ENTITY_OUTCOME),
        base_weight=1.4,
        priority=16,
    ),
    IntentRule(
        NLU_TASK_MATCHUP_ANALYSIS,
        "matchup_analysis_handler",
        phrases=("matchup", "batter vs pitcher", "against", "facing", "splits versus", "park factor", "weather impact"),
        required_any=("matchup", "against", "facing", "versus", " vs "),
        base_weight=1.2,
        priority=17,
    ),
    IntentRule(
        NLU_TASK_TEAM_ROSTER,
        "team_roster_handler",
        phrases=("team roster", "show roster", "who is on", "who plays for", "active roster", "40 man roster", "lineup"),
        required_any=("roster", "lineup", "players on"),
        entity_bonus=(ENTITY_TEAM,),
        base_weight=1.4,
        priority=20,
    ),
    IntentRule(
        NLU_TASK_TEAM_SCHEDULE,
        "team_schedule_handler",
        phrases=("team schedule", "when do", "next game", "upcoming games", "who do they play", "schedule"),
        required_any=("schedule", "next game", "when", "upcoming"),
        entity_bonus=(ENTITY_TEAM,),
        base_weight=1.3,
        priority=21,
    ),
    IntentRule(
        NLU_TASK_PLAYER_GAME_LOG,
        "player_game_log_handler",
        phrases=("game log", "recent games", "last game", "last five games", "last 5", "last ten games", "last 10"),
        required_any=("game log", "recent", "last game", "last 5", "last 10"),
        entity_bonus=(ENTITY_PLAYER,),
        base_weight=1.3,
        priority=22,
    ),
    IntentRule(
        NLU_TASK_PLAYER_SPLITS,
        "player_splits_handler",
        phrases=("splits", "against lefties", "against righties", "home away splits", "platoon split"),
        required_any=("splits", "lefties", "righties", "home away"),
        entity_bonus=(ENTITY_PLAYER,),
        base_weight=1.3,
        priority=23,
    ),
    IntentRule(
        NLU_TASK_PLAYER_STATS,
        "player_stats_handler",
        phrases=("player stats", "season stats", "career stats", "what is his", "what is her", "stats for"),
        required_any=("stats", "statistics", "average", "ops", "era", "whip", "home runs", "hits", "rbi"),
        entity_bonus=(ENTITY_PLAYER, ENTITY_STATISTIC),
        base_weight=1.2,
        priority=24,
    ),
    IntentRule(
        NLU_TASK_TEAM_STATS,
        "team_stats_handler",
        phrases=("team stats", "team record", "what is their record", "runs per game", "team statistics"),
        required_any=("stats", "record", "runs per game", "win percentage"),
        entity_bonus=(ENTITY_TEAM, ENTITY_STATISTIC),
        base_weight=1.2,
        priority=25,
    ),
    IntentRule(
        NLU_TASK_STANDINGS,
        "standings_handler",
        phrases=("standings", "division standings", "league standings", "who is in first"),
        required_any=("standings", "first place", "division leader"),
        base_weight=1.3,
        priority=26,
    ),
    IntentRule(
        NLU_TASK_LEAGUE_LEADERS,
        "league_leaders_handler",
        phrases=("league leaders", "who leads", "home run leaders", "batting leaders", "top players"),
        required_any=("leaders", "who leads", "top"),
        base_weight=1.2,
        priority=27,
    ),
    IntentRule(
        NLU_TASK_GAME_LOOKUP,
        "game_lookup_handler",
        phrases=("game today", "games today", "tonights games", "game status", "score of"),
        required_any=("game", "games", "score"),
        base_weight=1.0,
        priority=28,
    ),
    IntentRule(
        NLU_TASK_PLAYER_LOOKUP,
        "player_lookup_handler",
        phrases=("find player", "show player", "tell me about", "who is"),
        entity_bonus=(ENTITY_PLAYER,),
        base_weight=0.8,
        priority=30,
    ),
    IntentRule(
        NLU_TASK_TEAM_LOOKUP,
        "team_lookup_handler",
        phrases=("show team", "tell me about the team", "team info", "team overview"),
        entity_bonus=(ENTITY_TEAM,),
        base_weight=0.8,
        priority=31,
    ),
    IntentRule(
        NLU_TASK_GREETING,
        "greeting_handler",
        phrases=("hello", "hi", "hey", "good morning", "good afternoon", "good evening"),
        base_weight=0.8,
        priority=90,
    ),
    IntentRule(
        NLU_TASK_GENERAL,
        "general_baseball_handler",
        base_weight=0.1,
        priority=999,
    ),
)

RULE_BY_INTENT: Final[dict[str, IntentRule]] = {rule.intent: rule for rule in INTENT_RULES}


# ============================================================
# SECTION 12 - ROUTING MAP
# ============================================================

ROUTING_TARGETS: Final[dict[str, str]] = {
    rule.intent: rule.routing_target for rule in INTENT_RULES
}
ROUTING_TARGETS.update({
    NLU_TASK_CLARIFICATION: "clarification_handler",
    NLU_TASK_UNSUPPORTED: "unsupported_handler",
    NLU_TASK_BEST_TEAM_PROBABILITY: "best_team_probability_handler",
    NLU_TASK_BEST_OVERALL_PROBABILITY: "best_overall_probability_handler",
})


# ============================================================
# SECTION 13 - GENERAL HELPERS
# ============================================================

def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    if isinstance(value, str):
        text = value.strip().replace("Z", "+00:00")
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))


def canonical_json(value: Any) -> str:
    def serializer(item: Any) -> Any:
        if isinstance(item, datetime):
            return item.isoformat()
        if isinstance(item, Enum):
            return item.value
        if is_dataclass(item):
            return asdict(item)
        if isinstance(item, set):
            return sorted(item)
        raise TypeError(type(item).__name__)

    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=serializer)


def fingerprint(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize_catalog_record(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump"):
        return dict(value.model_dump())
    if hasattr(value, "dict") and callable(value.dict):
        return dict(value.dict())
    if hasattr(value, "__dict__"):
        return {
            key: item for key, item in vars(value).items()
            if not key.startswith("_") and not callable(item)
        }
    return {"name": str(value)}


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def phrase_pattern(phrase: str) -> re.Pattern[str]:
    escaped = re.escape(phrase.strip())
    escaped = escaped.replace(r"\ ", r"\s+")
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)


def contains_phrase(message: str, phrase: str) -> bool:
    if not phrase:
        return False
    return bool(phrase_pattern(phrase).search(message))


def contains_any(message: str, phrases: Iterable[str]) -> bool:
    return any(contains_phrase(message, phrase) for phrase in phrases)


def token_overlap(left: str, right: str) -> float:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def confidence_band(value: float) -> ConfidenceBand:
    value = clamp(value)
    if value >= 0.90:
        return ConfidenceBand.VERY_HIGH
    if value >= 0.75:
        return ConfidenceBand.HIGH
    if value >= 0.55:
        return ConfidenceBand.MODERATE
    if value > 0:
        return ConfidenceBand.LOW
    return ConfidenceBand.NONE


# ============================================================
# SECTION 14 - MESSAGE NORMALIZATION
# ============================================================

def _replace_phrases(text: str, replacements: Mapping[str, str]) -> tuple[str, list[dict[str, Any]]]:
    corrections: list[dict[str, Any]] = []
    output = text
    for source in sorted(replacements, key=len, reverse=True):
        target = replacements[source]
        pattern = phrase_pattern(source)
        if pattern.search(output):
            output = pattern.sub(target, output)
            corrections.append({"source": source, "target": target, "type": "phrase"})
    return output, corrections


def normalize_nlu_text(value: str | None) -> str:
    if value is None:
        return ""
    text = strip_accents(str(value)).lower().strip()
    text = text.replace("'", "'").replace("`", "'")
    text = re.sub(r"[^a-z0-9+.%'\-/\s]", " ", text)
    text = text.replace("/", " ").replace("_", " ")
    text, _ = _replace_phrases(text, PHRASE_REPLACEMENTS)
    tokens: list[str] = []
    for raw_token in collapse_spaces(text).split():
        token = raw_token.strip(".,!?;:\"'()[]{}")
        replacement = DIRECT_TOKEN_REPLACEMENTS.get(token)
        if replacement:
            tokens.extend(replacement.split())
        elif token:
            tokens.append(token)
    normalized = collapse_spaces(" ".join(tokens))
    normalized, _ = _replace_phrases(normalized, PHRASE_REPLACEMENTS)
    return collapse_spaces(normalized)


def detect_nlu_question_type(message: str) -> str:
    cleaned = normalize_nlu_text(message)
    if cleaned.startswith("who"):
        return "who_question"
    if cleaned.startswith("what"):
        return "what_question"
    if cleaned.startswith("which"):
        return "which_question"
    if cleaned.startswith("when"):
        return "when_question"
    if cleaned.startswith("where"):
        return "where_question"
    if cleaned.startswith("why"):
        return "why_question"
    if cleaned.startswith("how many") or cleaned.startswith("how much"):
        return "quantity_question"
    if cleaned.startswith("how"):
        return "how_question"
    if cleaned.startswith(("can", "will", "does", "is", "are", "should")):
        return "yes_no_or_probability_question"
    return "statement_or_command"


def build_normalized_message(message: str | None, request_id: str | None = None) -> NormalizedMessage:
    original = "" if message is None else str(message)
    request_id = request_id or str(uuid4())
    normalized = normalize_nlu_text(original)
    corrections: list[dict[str, Any]] = []

    raw_lower = strip_accents(original).lower()
    for source, target in PHRASE_REPLACEMENTS.items():
        if contains_phrase(raw_lower, source):
            corrections.append({"source": source, "target": target, "type": "phrase"})
    for token in collapse_spaces(raw_lower).split():
        cleaned_token = token.strip(".,!?;:\"'()[]{}")
        if cleaned_token in DIRECT_TOKEN_REPLACEMENTS:
            corrections.append({
                "source": cleaned_token,
                "target": DIRECT_TOKEN_REPLACEMENTS[cleaned_token],
                "type": "token",
            })

    tokens = normalized.split() if normalized else []
    return NormalizedMessage(
        request_id=request_id,
        original=original,
        normalized=normalized,
        tokens=tokens,
        token_set=set(tokens),
        question_type=detect_nlu_question_type(normalized),
        is_empty=not bool(normalized),
        corrections=corrections,
    )


def build_language_normalization_report(original_message: str) -> dict[str, Any]:
    normalized = build_normalized_message(original_message)
    return {
        "original_message": normalized.original,
        "normalized_message": normalized.normalized,
        "changed": normalize_nlu_text(normalized.original) != normalized.original.strip().lower(),
        "corrections": normalized.corrections,
        "question_type": normalized.question_type,
        "engine": NLU_ENGINE_NAME,
        "engine_version": NLU_ENGINE_VERSION,
    }


def nlu_contains_any(message: str, phrases: Sequence[str]) -> bool:
    normalized = normalize_nlu_text(message)
    return contains_any(normalized, [normalize_nlu_text(item) for item in phrases])


# ============================================================
# SECTION 15 - CATALOG NORMALIZATION
# ============================================================

def _catalog_items(catalog: Any) -> list[dict[str, Any]]:
    if catalog is None:
        return []
    if isinstance(catalog, Mapping):
        items: list[dict[str, Any]] = []
        for key, value in catalog.items():
            record = normalize_catalog_record(value)
            record.setdefault("name", str(key))
            items.append(record)
        return items
    if isinstance(catalog, (str, bytes)):
        return [{"name": str(catalog)}]
    if isinstance(catalog, Iterable):
        return [normalize_catalog_record(item) for item in catalog]
    return [normalize_catalog_record(catalog)]


def normalize_player_catalog(catalog: Any) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for record in _catalog_items(catalog):
        name = (
            record.get("full_name")
            or record.get("player_name")
            or record.get("name")
            or record.get("display_name")
        )
        if not name:
            continue
        aliases = record.get("aliases") or record.get("nicknames") or []
        if isinstance(aliases, str):
            aliases = [aliases]
        output.append({
            "id": record.get("player_id") or record.get("mlb_id") or record.get("id"),
            "name": str(name),
            "normalized_name": normalize_nlu_text(str(name)),
            "aliases": [normalize_nlu_text(str(alias)) for alias in aliases if alias],
            "team_id": record.get("team_id"),
            "team_name": record.get("team_name") or record.get("team"),
            "position": record.get("position") or record.get("primary_position"),
            "raw": record,
        })
    return output


def normalize_team_catalog(catalog: Any) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for record in _catalog_items(catalog):
        name = record.get("team_name") or record.get("name") or record.get("full_name")
        if not name:
            continue
        aliases = record.get("aliases") or []
        if isinstance(aliases, str):
            aliases = [aliases]
        abbreviation = record.get("abbreviation") or record.get("abbr") or record.get("team_code")
        city = record.get("city") or record.get("location_name")
        nickname = record.get("nickname") or record.get("club_name")
        candidate_aliases = list(aliases)
        candidate_aliases.extend(item for item in (abbreviation, city, nickname) if item)
        output.append({
            "id": record.get("team_id") or record.get("mlb_id") or record.get("id"),
            "name": str(name),
            "normalized_name": normalize_nlu_text(str(name)),
            "aliases": [normalize_nlu_text(str(alias)) for alias in candidate_aliases if alias],
            "abbreviation": abbreviation,
            "raw": record,
        })
    return output


# ============================================================
# SECTION 16 - BUILT-IN MLB TEAM CATALOG
# ============================================================

BUILTIN_MLB_TEAMS: Final[tuple[tuple[str, str, tuple[str, ...]], ...]] = (
    ("Arizona Diamondbacks", "ARI", ("diamondbacks", "dbacks", "d backs", "arizona")),
    ("Atlanta Braves", "ATL", ("braves", "atlanta")),
    ("Baltimore Orioles", "BAL", ("orioles", "os", "o's", "baltimore")),
    ("Boston Red Sox", "BOS", ("red sox", "sox", "boston")),
    ("Chicago Cubs", "CHC", ("cubs", "north siders")),
    ("Chicago White Sox", "CWS", ("white sox", "chisox", "south siders")),
    ("Cincinnati Reds", "CIN", ("reds", "cincinnati")),
    ("Cleveland Guardians", "CLE", ("guardians", "cleveland")),
    ("Colorado Rockies", "COL", ("rockies", "colorado")),
    ("Detroit Tigers", "DET", ("tigers", "detroit")),
    ("Houston Astros", "HOU", ("astros", "houston")),
    ("Kansas City Royals", "KC", ("royals", "kansas city", "kcr")),
    ("Los Angeles Angels", "LAA", ("angels", "la angels", "anaheim")),
    ("Los Angeles Dodgers", "LAD", ("dodgers", "la dodgers")),
    ("Miami Marlins", "MIA", ("marlins", "miami")),
    ("Milwaukee Brewers", "MIL", ("brewers", "milwaukee")),
    ("Minnesota Twins", "MIN", ("twins", "minnesota")),
    ("New York Mets", "NYM", ("mets", "ny mets")),
    ("New York Yankees", "NYY", ("yankees", "yanks", "bronx bombers", "ny yanks")),
    ("Athletics", "ATH", ("athletics", "as", "a's", "oakland athletics")),
    ("Philadelphia Phillies", "PHI", ("phillies", "phils", "philadelphia")),
    ("Pittsburgh Pirates", "PIT", ("pirates", "bucs", "pittsburgh")),
    ("San Diego Padres", "SD", ("padres", "san diego")),
    ("San Francisco Giants", "SF", ("giants", "san francisco", "sfg")),
    ("Seattle Mariners", "SEA", ("mariners", "seattle", "ms", "m's")),
    ("St. Louis Cardinals", "STL", ("cardinals", "cards", "st louis", "saint louis")),
    ("Tampa Bay Rays", "TB", ("rays", "tampa bay", "tampa", "tbr")),
    ("Texas Rangers", "TEX", ("rangers", "texas")),
    ("Toronto Blue Jays", "TOR", ("blue jays", "jays", "toronto")),
    ("Washington Nationals", "WSH", ("nationals", "nats", "washington")),
)


def builtin_team_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": None,
            "name": name,
            "normalized_name": normalize_nlu_text(name),
            "aliases": [normalize_nlu_text(alias) for alias in aliases] + [abbreviation.lower()],
            "abbreviation": abbreviation,
            "raw": {},
        }
        for name, abbreviation, aliases in BUILTIN_MLB_TEAMS
    ]


# ============================================================
# SECTION 17 - ENTITY MATCHING
# ============================================================

def _exact_catalog_matches(
    normalized_message: str,
    catalog: Sequence[Mapping[str, Any]],
    entity_type: str,
) -> list[ResolvedEntity]:
    matches: list[ResolvedEntity] = []
    for record in catalog:
        canonical = str(record.get("name") or "")
        normalized_name = str(record.get("normalized_name") or normalize_nlu_text(canonical))
        aliases = [str(alias) for alias in record.get("aliases") or []]
        candidates = [(normalized_name, EntitySource.CURRENT_EXACT, 0.99)]
        candidates.extend((alias, EntitySource.CURRENT_ALIAS, 0.93) for alias in aliases)
        best: ResolvedEntity | None = None
        for candidate, source, confidence in candidates:
            if candidate and contains_phrase(normalized_message, candidate):
                entity = ResolvedEntity(
                    entity_type=entity_type,
                    canonical_name=canonical,
                    entity_id=record.get("id"),
                    matched_text=candidate,
                    confidence=confidence,
                    source=source,
                    metadata={
                        "team_id": record.get("team_id"),
                        "team_name": record.get("team_name"),
                        "position": record.get("position"),
                        "abbreviation": record.get("abbreviation"),
                    },
                )
                if best is None or entity.confidence > best.confidence:
                    best = entity
        if best is not None:
            matches.append(best)
    matches.sort(key=lambda item: (item.confidence, len(item.matched_text or "")), reverse=True)
    return matches


def _candidate_name_phrases(message: NormalizedMessage, max_tokens: int = 4) -> list[str]:
    stop_words = {
        "show", "find", "search", "tell", "about", "predict", "probability", "chance",
        "stats", "statistics", "team", "player", "mlb", "baseball", "what", "who",
        "is", "are", "the", "a", "an", "for", "of", "on", "in", "please", "me",
    }
    tokens = [token for token in message.tokens if token not in stop_words]
    phrases: list[str] = []
    for size in range(min(max_tokens, len(tokens)), 0, -1):
        for index in range(0, len(tokens) - size + 1):
            phrase = " ".join(tokens[index:index + size])
            if phrase and phrase not in phrases:
                phrases.append(phrase)
    return phrases


def _sequence_similarity(left: str, right: str) -> float:
    # Local implementation avoids hard dependency on fuzzy_matching.py.
    from difflib import SequenceMatcher
    if not left or not right:
        return 0.0
    exact = SequenceMatcher(None, left, right).ratio()
    overlap = token_overlap(left, right)
    prefix = 1.0 if left.startswith(right) or right.startswith(left) else 0.0
    return 0.68 * exact + 0.24 * overlap + 0.08 * prefix


def _fuzzy_catalog_matches(
    message: NormalizedMessage,
    catalog: Sequence[Mapping[str, Any]],
    entity_type: str,
    threshold: float,
    limit: int,
) -> list[ResolvedEntity]:
    phrases = _candidate_name_phrases(message)
    scored: list[ResolvedEntity] = []
    for record in catalog:
        canonical = str(record.get("name") or "")
        candidate_values = [str(record.get("normalized_name") or normalize_nlu_text(canonical))]
        candidate_values.extend(str(alias) for alias in record.get("aliases") or [])
        best_score = 0.0
        best_phrase: str | None = None
        best_candidate: str | None = None
        for observed in phrases:
            for candidate in candidate_values:
                score = _sequence_similarity(observed, candidate)
                if score > best_score:
                    best_score = score
                    best_phrase = observed
                    best_candidate = candidate
        if best_score >= threshold:
            scored.append(ResolvedEntity(
                entity_type=entity_type,
                canonical_name=canonical,
                entity_id=record.get("id"),
                matched_text=best_phrase,
                confidence=best_score,
                source=EntitySource.CURRENT_FUZZY,
                metadata={
                    "matched_candidate": best_candidate,
                    "team_id": record.get("team_id"),
                    "team_name": record.get("team_name"),
                    "position": record.get("position"),
                    "abbreviation": record.get("abbreviation"),
                },
            ))
    scored.sort(key=lambda item: item.confidence, reverse=True)
    return scored[:limit]


def detect_statistic(message: str) -> ResolvedEntity | None:
    normalized = normalize_nlu_text(message)
    matches: list[tuple[int, str, str]] = []
    for statistic, aliases in STAT_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_nlu_text(alias)
            if contains_phrase(normalized, normalized_alias):
                matches.append((len(normalized_alias.split()), statistic, normalized_alias))
    if not matches:
        return None
    matches.sort(reverse=True)
    _, statistic, matched = matches[0]
    return ResolvedEntity(
        entity_type=ENTITY_STATISTIC,
        canonical_name=statistic,
        matched_text=matched,
        confidence=0.96,
        source=EntitySource.CURRENT_ALIAS,
    )


def detect_nlu_outcome(message: str) -> str | None:
    entity = detect_outcome_entity(message)
    return entity.canonical_name if entity else None


def detect_outcome_entity(message: str) -> ResolvedEntity | None:
    normalized = normalize_nlu_text(message)
    matches: list[tuple[int, str, str]] = []
    for outcome, aliases in OUTCOME_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_nlu_text(alias)
            if contains_phrase(normalized, normalized_alias):
                matches.append((len(normalized_alias.split()), outcome, normalized_alias))
    if not matches:
        return None
    matches.sort(reverse=True)
    _, outcome, matched = matches[0]
    return ResolvedEntity(
        entity_type=ENTITY_OUTCOME,
        canonical_name=outcome,
        matched_text=matched,
        confidence=0.96,
        source=EntitySource.CURRENT_ALIAS,
    )


def detect_season(message: str) -> ResolvedEntity | None:
    normalized = normalize_nlu_text(message)
    match = re.search(r"\b(19\d{2}|20\d{2})\b", normalized)
    if not match:
        return None
    return ResolvedEntity(
        entity_type=ENTITY_SEASON,
        canonical_name=match.group(1),
        entity_id=int(match.group(1)),
        matched_text=match.group(1),
        confidence=0.99,
        source=EntitySource.CURRENT_EXACT,
    )


def detect_limit(message: str) -> ResolvedEntity | None:
    normalized = normalize_nlu_text(message)
    patterns = (
        r"\blast\s+(\d{1,3})\b",
        r"\btop\s+(\d{1,3})\b",
        r"\bshow\s+(\d{1,3})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            value = max(1, min(int(match.group(1)), 200))
            return ResolvedEntity(
                entity_type=ENTITY_LIMIT,
                canonical_name=str(value),
                entity_id=value,
                matched_text=match.group(0),
                confidence=0.98,
                source=EntitySource.CURRENT_EXACT,
            )
    word_numbers = {
        "five": 5, "ten": 10, "fifteen": 15, "twenty": 20, "thirty": 30,
    }
    for word, value in word_numbers.items():
        if contains_phrase(normalized, f"last {word}"):
            return ResolvedEntity(
                entity_type=ENTITY_LIMIT,
                canonical_name=str(value),
                entity_id=value,
                matched_text=f"last {word}",
                confidence=0.95,
                source=EntitySource.CURRENT_ALIAS,
            )
    return None


def detect_relative_date(message: str, now: datetime | None = None) -> ResolvedEntity | None:
    now = now or utc_now()
    normalized = normalize_nlu_text(message)
    date_value: date | None = None
    matched: str | None = None
    if contains_phrase(normalized, "today") or contains_phrase(normalized, "tonight"):
        date_value, matched = now.date(), "today" if "today" in normalized else "tonight"
    elif contains_phrase(normalized, "tomorrow"):
        date_value, matched = (now + timedelta(days=1)).date(), "tomorrow"
    elif contains_phrase(normalized, "yesterday"):
        date_value, matched = (now - timedelta(days=1)).date(), "yesterday"
    if date_value is None:
        return None
    return ResolvedEntity(
        entity_type=ENTITY_DATE,
        canonical_name=date_value.isoformat(),
        matched_text=matched,
        confidence=0.98,
        source=EntitySource.CURRENT_ALIAS,
    )


# ============================================================
# SECTION 18 - CONTEXT RESOLUTION
# ============================================================

def context_is_fresh(context: ConversationContext, config: NLUConfig) -> bool:
    if context.updated_at is None:
        return True
    age = utc_now() - context.updated_at
    return age.total_seconds() <= config.context_max_age_hours * 3600.0


def message_requests_context_reset(message: str) -> bool:
    return contains_any(normalize_nlu_text(message), RESET_CONTEXT_PHRASES)


def _has_player_pronoun(message: str) -> bool:
    normalized = normalize_nlu_text(message)
    return contains_any(normalized, PRONOUN_PLAYER_PHRASES)


def _has_team_pronoun(message: str) -> bool:
    normalized = normalize_nlu_text(message)
    return contains_any(normalized, PRONOUN_TEAM_PHRASES)


def resolve_context_entities(
    message: NormalizedMessage,
    explicit_players: list[ResolvedEntity],
    explicit_teams: list[ResolvedEntity],
    statistic: ResolvedEntity | None,
    outcome: ResolvedEntity | None,
    context: ConversationContext,
    config: NLUConfig,
) -> tuple[list[ResolvedEntity], list[ResolvedEntity], ResolvedEntity | None, ResolvedEntity | None, dict[str, Any]]:
    resolution = {
        "used": False,
        "player_from_context": False,
        "team_from_context": False,
        "statistic_from_context": False,
        "outcome_from_context": False,
        "reset": False,
        "reasons": [],
    }

    if message_requests_context_reset(message.normalized):
        resolution["reset"] = True
        resolution["reasons"].append("explicit_context_reset")
        return explicit_players, explicit_teams, statistic, outcome, resolution

    if not context_is_fresh(context, config):
        resolution["reasons"].append("context_expired")
        return explicit_players, explicit_teams, statistic, outcome, resolution

    players = list(explicit_players)
    teams = list(explicit_teams)

    # Explicit current entities always win. Context is only used when absent.
    if (
        not players
        and config.allow_context_pronoun_resolution
        and context.last_player_name
        and _has_player_pronoun(message.normalized)
    ):
        players.append(ResolvedEntity(
            entity_type=ENTITY_PLAYER,
            canonical_name=context.last_player_name,
            entity_id=context.last_player_id,
            matched_text="conversation pronoun",
            confidence=0.88,
            source=EntitySource.CONVERSATION_CONTEXT,
        ))
        resolution["used"] = True
        resolution["player_from_context"] = True
        resolution["reasons"].append("player_pronoun_resolved")

    if (
        not teams
        and config.allow_context_pronoun_resolution
        and context.last_team_name
        and _has_team_pronoun(message.normalized)
    ):
        teams.append(ResolvedEntity(
            entity_type=ENTITY_TEAM,
            canonical_name=context.last_team_name,
            entity_id=context.last_team_id,
            matched_text="conversation pronoun",
            confidence=0.86,
            source=EntitySource.CONVERSATION_CONTEXT,
        ))
        resolution["used"] = True
        resolution["team_from_context"] = True
        resolution["reasons"].append("team_pronoun_resolved")

    # Elliptical follow-ups such as "what about home runs" may reuse only the
    # subject entity, never the prior intent itself.
    elliptical = message.question_type in {
        "what_question", "how_question", "quantity_question",
        "yes_no_or_probability_question",
    } or message.normalized.startswith(("and ", "also ", "what about ", "how about "))

    if config.allow_context_ellipsis_resolution and elliptical:
        if not players and not teams and context.last_player_name and (statistic or outcome):
            players.append(ResolvedEntity(
                entity_type=ENTITY_PLAYER,
                canonical_name=context.last_player_name,
                entity_id=context.last_player_id,
                matched_text="elliptical follow-up",
                confidence=0.80,
                source=EntitySource.CONVERSATION_CONTEXT,
            ))
            resolution["used"] = True
            resolution["player_from_context"] = True
            resolution["reasons"].append("player_ellipsis_resolved")
        elif not players and not teams and context.last_team_name and statistic:
            teams.append(ResolvedEntity(
                entity_type=ENTITY_TEAM,
                canonical_name=context.last_team_name,
                entity_id=context.last_team_id,
                matched_text="elliptical follow-up",
                confidence=0.78,
                source=EntitySource.CONVERSATION_CONTEXT,
            ))
            resolution["used"] = True
            resolution["team_from_context"] = True
            resolution["reasons"].append("team_ellipsis_resolved")

    if statistic is None and resolution["used"] and context.last_statistic and contains_any(
        message.normalized, ("that stat", "same stat", "it", "that number")
    ):
        statistic = ResolvedEntity(
            entity_type=ENTITY_STATISTIC,
            canonical_name=context.last_statistic,
            matched_text="conversation statistic",
            confidence=0.75,
            source=EntitySource.CONVERSATION_CONTEXT,
        )
        resolution["statistic_from_context"] = True
        resolution["reasons"].append("statistic_pronoun_resolved")

    if outcome is None and resolution["used"] and context.last_outcome and contains_any(
        message.normalized, ("that outcome", "same outcome", "do it again", "again")
    ):
        outcome = ResolvedEntity(
            entity_type=ENTITY_OUTCOME,
            canonical_name=context.last_outcome,
            matched_text="conversation outcome",
            confidence=0.72,
            source=EntitySource.CONVERSATION_CONTEXT,
        )
        resolution["outcome_from_context"] = True
        resolution["reasons"].append("outcome_ellipsis_resolved")

    return players, teams, statistic, outcome, resolution


# ============================================================
# SECTION 19 - INTENT SCORING
# ============================================================

def _entity_presence(
    players: Sequence[ResolvedEntity],
    teams: Sequence[ResolvedEntity],
    statistic: ResolvedEntity | None,
    outcome: ResolvedEntity | None,
    game_present: bool,
) -> set[str]:
    present: set[str] = set()
    if players:
        present.add(ENTITY_PLAYER)
    if teams:
        present.add(ENTITY_TEAM)
    if statistic:
        present.add(ENTITY_STATISTIC)
    if outcome:
        present.add(ENTITY_OUTCOME)
    if game_present:
        present.add(ENTITY_GAME)
    return present


def score_intent_rules(
    message: NormalizedMessage,
    players: Sequence[ResolvedEntity],
    teams: Sequence[ResolvedEntity],
    statistic: ResolvedEntity | None,
    outcome: ResolvedEntity | None,
    game_present: bool,
) -> list[IntentCandidate]:
    entity_presence = _entity_presence(players, teams, statistic, outcome, game_present)
    candidates: list[IntentCandidate] = []

    for rule in INTENT_RULES:
        score = rule.base_weight
        evidence: list[str] = []
        negative: list[str] = []

        for phrase in rule.phrases:
            normalized_phrase = normalize_nlu_text(phrase)
            if normalized_phrase and contains_phrase(message.normalized, normalized_phrase):
                token_weight = max(1.0, min(3.5, len(normalized_phrase.split()) * 0.65))
                score += rule.phrase_weight * token_weight
                evidence.append(f"phrase:{normalized_phrase}")

        for required in rule.required_any:
            normalized_required = normalize_nlu_text(required)
            if normalized_required and contains_phrase(message.normalized, normalized_required):
                score += 0.75
                evidence.append(f"required:{normalized_required}")

        for entity_type in rule.entity_bonus:
            if entity_type in entity_presence:
                score += 1.2
                evidence.append(f"entity:{entity_type}")

        for phrase in rule.negative_phrases:
            normalized_phrase = normalize_nlu_text(phrase)
            if normalized_phrase and contains_phrase(message.normalized, normalized_phrase):
                score -= 1.5
                negative.append(f"negative:{normalized_phrase}")

        # Structural bonuses and guards.
        if rule.intent == NLU_TASK_COMPARE_PLAYERS and len(players) >= 2:
            score += 3.5
            evidence.append("structure:multiple_players")
        if rule.intent == NLU_TASK_COMPARE_TEAMS and len(teams) >= 2:
            score += 3.5
            evidence.append("structure:multiple_teams")
        if rule.intent == NLU_TASK_PLAYER_PROBABILITY and players and outcome:
            score += 3.0
            evidence.append("structure:player_plus_outcome")
        if rule.intent == NLU_TASK_PLAYER_STATS and players and statistic:
            score += 3.0
            evidence.append("structure:player_plus_statistic")
        if rule.intent == NLU_TASK_TEAM_STATS and teams and statistic:
            score += 3.0
            evidence.append("structure:team_plus_statistic")
        if rule.intent == NLU_TASK_TEAM_ROSTER and teams and contains_any(message.normalized, ("roster", "lineup", "who is on", "who plays for")):
            score += 3.0
            evidence.append("structure:team_plus_roster_language")
        if rule.intent == NLU_TASK_TEAM_SCHEDULE and teams and contains_any(message.normalized, ("schedule", "next game", "when do", "upcoming")):
            score += 3.0
            evidence.append("structure:team_plus_schedule_language")
        if rule.intent == NLU_TASK_PLAYER_LOOKUP and len(players) == 1 and not statistic and not outcome:
            score += 1.8
            evidence.append("structure:single_player_lookup")
        if rule.intent == NLU_TASK_TEAM_LOOKUP and len(teams) == 1 and not statistic and not outcome:
            score += 1.8
            evidence.append("structure:single_team_lookup")
        if rule.intent == NLU_TASK_GAME_PREDICTION and len(teams) >= 2 and contains_any(message.normalized, ("win", "predict", "probability")):
            score += 3.2
            evidence.append("structure:two_team_game_prediction")
        if rule.intent == NLU_TASK_GAME_LOOKUP and game_present:
            score += 1.5
            evidence.append("structure:game_language")

        # Do not let generic player probability swallow simple stat questions.
        if rule.intent == NLU_TASK_PLAYER_PROBABILITY and statistic and not contains_any(
            message.normalized, ("predict", "probability", "chance", "likely", "odds", "will")
        ):
            score -= 2.5
            negative.append("guard:stat_without_prediction_language")

        # Team-list questions must not become player search merely because the
        # word "players" appears in explanatory text.
        if rule.intent in {NLU_TASK_PLAYER_LOOKUP, NLU_TASK_LIST_PLAYERS} and contains_any(
            message.normalized, ("all teams", "mlb teams", "team list", "list teams")
        ):
            score -= 3.0
            negative.append("guard:explicit_team_list")

        candidates.append(IntentCandidate(rule.intent, score, evidence, negative))

    candidates.sort(key=lambda item: (item.score, -RULE_BY_INTENT.get(item.intent, IntentRule(item.intent, "", priority=999)).priority), reverse=True)
    return candidates


def _normalize_candidate_confidence(candidates: Sequence[IntentCandidate]) -> float:
    if not candidates:
        return 0.0
    top = candidates[0].score
    second = candidates[1].score if len(candidates) > 1 else 0.0
    if top <= 0:
        return 0.0
    margin = max(top - second, 0.0)
    magnitude = 1.0 - math.exp(-max(top, 0.0) / 5.0)
    separation = 1.0 - math.exp(-margin / 2.5)
    return clamp(0.55 * magnitude + 0.45 * separation)


def _select_intent(candidates: Sequence[IntentCandidate]) -> tuple[str, float]:
    if not candidates:
        return NLU_TASK_GENERAL, 0.0
    selected = candidates[0]
    return selected.intent, _normalize_candidate_confidence(candidates)


# ============================================================
# SECTION 20 - SCOPE DETECTION
# ============================================================

def detect_entity_scope(
    message: str,
    entity_report: Mapping[str, Any] | None = None,
    *,
    players: Sequence[ResolvedEntity] | None = None,
    teams: Sequence[ResolvedEntity] | None = None,
    intent: str | None = None,
) -> str:
    entity_report = entity_report or {}
    players = list(players or [])
    teams = list(teams or [])

    if not players:
        for item in entity_report.get("players", []) or []:
            players.append(ResolvedEntity(
                entity_type=ENTITY_PLAYER,
                canonical_name=item.get("canonical_name") or item.get("name"),
            ))
    if not teams:
        for item in entity_report.get("teams", []) or []:
            teams.append(ResolvedEntity(
                entity_type=ENTITY_TEAM,
                canonical_name=item.get("canonical_name") or item.get("name"),
            ))

    normalized = normalize_nlu_text(message)
    if intent in {NLU_TASK_DATABASE_STATUS, NLU_TASK_WAREHOUSE_STATUS, NLU_TASK_MODEL_STATUS, NLU_TASK_DATA_FRESHNESS}:
        return NLU_SCOPE_SYSTEM
    if len(players) >= 2:
        return NLU_SCOPE_MULTIPLE_PLAYERS
    if len(teams) >= 2:
        return NLU_SCOPE_MULTIPLE_TEAMS
    if players:
        return NLU_SCOPE_SINGLE_PLAYER
    if teams:
        if intent == NLU_TASK_TEAM_ROSTER:
            return NLU_SCOPE_TEAM_PLAYERS
        return NLU_SCOPE_TEAM
    if intent in {NLU_TASK_LIST_PLAYERS, NLU_TASK_BEST_OVERALL_PROBABILITY, NLU_TASK_LEAGUE_LEADERS}:
        return NLU_SCOPE_ALL_PLAYERS
    if intent in {NLU_TASK_LIST_TEAMS, NLU_TASK_STANDINGS}:
        return NLU_SCOPE_ALL_TEAMS
    if intent in {NLU_TASK_GAME_LOOKUP, NLU_TASK_GAME_PREDICTION} or contains_any(normalized, ("game", "games", "matchup")):
        return NLU_SCOPE_GAME
    if contains_any(normalized, ("mlb", "league", "baseball")):
        return NLU_SCOPE_LEAGUE
    return NLU_SCOPE_UNKNOWN


# ============================================================
# SECTION 21 - MISSING INFORMATION AND CLARIFICATION
# ============================================================

def detect_missing_information(
    task: str,
    entity_report: Mapping[str, Any] | None = None,
    outcome: str | None = None,
    *,
    players: Sequence[ResolvedEntity] | None = None,
    teams: Sequence[ResolvedEntity] | None = None,
    statistic: ResolvedEntity | None = None,
) -> dict[str, bool]:
    entity_report = entity_report or {}
    players = list(players or [])
    teams = list(teams or [])
    has_player = bool(players) or bool(entity_report.get("has_player"))
    has_team = bool(teams) or bool(entity_report.get("has_team"))
    return {
        "missing_player": task in {
            NLU_TASK_PLAYER_LOOKUP,
            NLU_TASK_PLAYER_STATS,
            NLU_TASK_PLAYER_GAME_LOG,
            NLU_TASK_PLAYER_SPLITS,
            NLU_TASK_PLAYER_PROBABILITY,
        } and not has_player,
        "missing_team": task in {
            NLU_TASK_TEAM_LOOKUP,
            NLU_TASK_TEAM_STATS,
            NLU_TASK_TEAM_ROSTER,
            NLU_TASK_TEAM_SCHEDULE,
            NLU_TASK_TEAM_PREDICTION,
            NLU_TASK_BEST_TEAM_PROBABILITY,
        } and not has_team,
        "missing_outcome": task in {
            NLU_TASK_PLAYER_PROBABILITY,
            NLU_TASK_BEST_TEAM_PROBABILITY,
            NLU_TASK_BEST_OVERALL_PROBABILITY,
        } and not outcome,
        "missing_statistic": task in {NLU_TASK_PLAYER_STATS, NLU_TASK_TEAM_STATS} and statistic is None,
    }


def determine_clarification(
    message: NormalizedMessage,
    intent: str,
    confidence: float,
    candidates: Sequence[IntentCandidate],
    players: Sequence[ResolvedEntity],
    teams: Sequence[ResolvedEntity],
    missing: Mapping[str, bool],
    config: NLUConfig,
) -> tuple[bool, ClarificationReason, str | None]:
    if message.is_empty:
        return True, ClarificationReason.EMPTY_MESSAGE, "Please enter a baseball question."

    if len(players) >= 2 and intent not in {NLU_TASK_COMPARE_PLAYERS}:
        top = players[0].confidence
        second = players[1].confidence
        if abs(top - second) <= config.ambiguity_margin:
            names = ", ".join(item.canonical_name or "Unknown" for item in players[:4])
            return True, ClarificationReason.AMBIGUOUS_PLAYER, f"I found multiple possible players: {names}. Which one did you mean?"

    if len(teams) >= 2 and intent not in {NLU_TASK_COMPARE_TEAMS, NLU_TASK_GAME_PREDICTION}:
        top = teams[0].confidence
        second = teams[1].confidence
        if abs(top - second) <= config.ambiguity_margin:
            names = ", ".join(item.canonical_name or "Unknown" for item in teams[:4])
            return True, ClarificationReason.AMBIGUOUS_TEAM, f"I found multiple possible teams: {names}. Which one did you mean?"

    if missing.get("missing_player"):
        return True, ClarificationReason.MISSING_PLAYER, "Which player would you like me to analyze?"
    if missing.get("missing_team"):
        return True, ClarificationReason.MISSING_TEAM, "Which MLB team would you like me to use?"
    if missing.get("missing_outcome"):
        return True, ClarificationReason.MISSING_OUTCOME, "Which outcome should I project: hit, home run, walk, strikeout, RBI, run, or total bases?"
    if missing.get("missing_statistic"):
        return True, ClarificationReason.MISSING_STATISTIC, "Which statistic would you like: AVG, OBP, SLG, OPS, home runs, hits, ERA, WHIP, or another metric?"

    if len(candidates) >= 2:
        margin = candidates[0].score - candidates[1].score
        if confidence < config.clarification_confidence and margin <= config.ambiguity_margin:
            return True, ClarificationReason.AMBIGUOUS_INTENT, "I can help with player stats, team information, schedules, rosters, or predictions. Which did you mean?"

    if intent == NLU_TASK_UNSUPPORTED:
        return True, ClarificationReason.UNSUPPORTED_REQUEST, "I could not map that request to a supported baseball action."

    return False, ClarificationReason.NONE, None


# ============================================================
# SECTION 22 - EXTERNAL ENGINE COORDINATION
# ============================================================

def _safe_external_entity_report(message: str, players: Sequence[Mapping[str, Any]], config: NLUConfig) -> dict[str, Any]:
    if not config.enable_external_entity_engine or _external_entity_report is None:
        return {}
    try:
        player_profiles = {str(item.get("name")): item for item in players if item.get("name")}
        result = _external_entity_report(message, player_profiles=player_profiles)
        return dict(result or {})
    except Exception as exc:
        LOGGER.debug("External entity engine failed: %s", exc)
        return {"error": str(exc)}


def _safe_external_fuzzy_report(message: str, players: Sequence[Mapping[str, Any]], teams: Sequence[Mapping[str, Any]], config: NLUConfig) -> dict[str, Any]:
    if not config.enable_external_fuzzy_engine or _external_fuzzy_report is None:
        return {}
    try:
        result = _external_fuzzy_report(
            message=message,
            player_names=[str(item.get("name")) for item in players if item.get("name")],
            team_names=[str(item.get("name")) for item in teams if item.get("name")],
        )
        return dict(result or {})
    except Exception as exc:
        LOGGER.debug("External fuzzy engine failed: %s", exc)
        return {"error": str(exc)}


def _safe_external_semantic_report(message: str, players: Sequence[Mapping[str, Any]], teams: Sequence[Mapping[str, Any]], config: NLUConfig) -> dict[str, Any]:
    if not config.enable_external_semantic_engine or _external_semantic_report is None:
        return {}
    try:
        player_profiles = {str(item.get("name")): item for item in players if item.get("name")}
        team_profiles = {
            str(item.get("name")): {
                "abbreviation": item.get("abbreviation"),
                **dict(item.get("raw") or {}),
            }
            for item in teams if item.get("name")
        }
        result = _external_semantic_report(message, team_profiles, player_profiles)
        return dict(result or {})
    except Exception as exc:
        LOGGER.debug("External semantic engine failed: %s", exc)
        return {"error": str(exc)}


def _safe_external_intent_report(
    message: str,
    players: Sequence[ResolvedEntity],
    teams: Sequence[ResolvedEntity],
    outcome: ResolvedEntity | None,
    config: NLUConfig,
) -> dict[str, Any]:
    if not config.enable_external_intent_engine or _external_intent_report is None:
        return {}
    try:
        result = _external_intent_report(
            message=message,
            detected_player=players[0].canonical_name if players else None,
            detected_team=teams[0].canonical_name if teams else None,
            detected_outcome=outcome.canonical_name if outcome else None,
            detected_players=[item.canonical_name for item in players if item.canonical_name],
            detected_teams=[item.canonical_name for item in teams if item.canonical_name],
        )
        return dict(result or {})
    except Exception as exc:
        LOGGER.debug("External intent engine failed: %s", exc)
        return {"error": str(exc)}


# ============================================================
# SECTION 23 - CONTEXT UPDATE POLICY
# ============================================================

def build_next_context(
    previous: ConversationContext,
    intent: str,
    players: Sequence[ResolvedEntity],
    teams: Sequence[ResolvedEntity],
    statistic: ResolvedEntity | None,
    outcome: ResolvedEntity | None,
    clarification_required: bool,
    reset: bool,
) -> ConversationContext:
    if reset:
        previous = ConversationContext()

    # Never save an unresolved or failed parse as authoritative context.
    if clarification_required:
        return previous

    next_context = ConversationContext.from_any(previous.to_dict())
    if players:
        next_context.last_player_id = players[0].entity_id
        next_context.last_player_name = players[0].canonical_name
        # A newly named player changes the active subject; stale game context
        # may no longer apply.
        if players[0].source != EntitySource.CONVERSATION_CONTEXT:
            next_context.last_game_id = None
            next_context.last_game_label = None
    if teams:
        next_context.last_team_id = teams[0].entity_id
        next_context.last_team_name = teams[0].canonical_name
    if statistic:
        next_context.last_statistic = statistic.canonical_name
    if outcome:
        next_context.last_outcome = outcome.canonical_name
    next_context.last_intent = intent
    next_context.updated_at = utc_now()
    return next_context


# ============================================================
# SECTION 24 - PRIMARY ENTERPRISE NLU ENGINE
# ============================================================

class BaseballNLUEngine:
    """Primary stateless-per-request NLU orchestration service."""

    def __init__(self, config: NLUConfig | None = None) -> None:
        self.config = config or NLUConfig()
        self.config.validate()

    def understand(
        self,
        message: str | None,
        *,
        player_catalog: Any = None,
        team_catalog: Any = None,
        conversation_context: Any = None,
        request_id: str | None = None,
    ) -> NLUReport:
        started = utc_now()
        normalized_message = build_normalized_message(message, request_id=request_id)
        context = ConversationContext.from_any(conversation_context)

        players_catalog = normalize_player_catalog(player_catalog)
        teams_catalog = normalize_team_catalog(team_catalog)
        if not teams_catalog:
            teams_catalog = builtin_team_catalog()

        # Every request starts from the current message. No previous intent is
        # passed into scoring or classification.
        exact_players = _exact_catalog_matches(normalized_message.normalized, players_catalog, ENTITY_PLAYER)
        exact_teams = _exact_catalog_matches(normalized_message.normalized, teams_catalog, ENTITY_TEAM)

        players = exact_players
        teams = exact_teams

        if not players and players_catalog:
            players = _fuzzy_catalog_matches(
                normalized_message,
                players_catalog,
                ENTITY_PLAYER,
                self.config.fuzzy_threshold,
                self.config.max_catalog_candidates,
            )
        if not teams:
            teams = _fuzzy_catalog_matches(
                normalized_message,
                teams_catalog,
                ENTITY_TEAM,
                self.config.fuzzy_threshold,
                self.config.max_catalog_candidates,
            )

        statistic = detect_statistic(normalized_message.normalized)
        outcome = detect_outcome_entity(normalized_message.normalized)
        season = detect_season(normalized_message.normalized)
        limit = detect_limit(normalized_message.normalized)
        relative_date = detect_relative_date(normalized_message.normalized)

        players, teams, statistic, outcome, context_resolution = resolve_context_entities(
            normalized_message,
            players,
            teams,
            statistic,
            outcome,
            context,
            self.config,
        )

        game_present = contains_any(
            normalized_message.normalized,
            ("game", "games", "matchup", "score", "today", "tonight", "tomorrow"),
        )

        candidates = score_intent_rules(
            normalized_message,
            players,
            teams,
            statistic,
            outcome,
            game_present,
        )
        intent, confidence = _select_intent(candidates)

        # Deterministic post-selection rules handle structures that are clearer
        # than generic phrase scores.
        if len(players) >= 2 and contains_any(normalized_message.normalized, ("compare", "versus", "vs", "between", "better")):
            intent = NLU_TASK_COMPARE_PLAYERS
            confidence = max(confidence, 0.94)
        elif len(teams) >= 2 and contains_any(normalized_message.normalized, ("compare", "versus", "vs", "who wins", "predict", "probability")):
            intent = NLU_TASK_GAME_PREDICTION if contains_any(normalized_message.normalized, ("who wins", "predict", "probability")) else NLU_TASK_COMPARE_TEAMS
            confidence = max(confidence, 0.93)
        elif players and outcome and contains_any(normalized_message.normalized, ("predict", "probability", "chance", "likely", "will", "odds", "projection")):
            intent = NLU_TASK_PLAYER_PROBABILITY
            confidence = max(confidence, 0.94)
        elif players and statistic and not contains_any(normalized_message.normalized, ("predict", "probability", "chance", "likely", "will", "odds")):
            intent = NLU_TASK_PLAYER_STATS
            confidence = max(confidence, 0.91)
        elif teams and statistic and not contains_any(normalized_message.normalized, ("predict", "probability", "chance", "likely", "will", "odds")):
            intent = NLU_TASK_TEAM_STATS
            confidence = max(confidence, 0.90)
        elif players and intent == NLU_TASK_GENERAL:
            intent = NLU_TASK_PLAYER_LOOKUP
            confidence = max(confidence, 0.78)
        elif teams and intent == NLU_TASK_GENERAL:
            intent = NLU_TASK_TEAM_LOOKUP
            confidence = max(confidence, 0.76)

        scope = detect_entity_scope(
            normalized_message.normalized,
            players=players,
            teams=teams,
            intent=intent,
        )

        missing = detect_missing_information(
            intent,
            outcome=outcome.canonical_name if outcome else None,
            players=players,
            teams=teams,
            statistic=statistic,
        )

        clarification_required, clarification_reason, clarification_prompt = determine_clarification(
            normalized_message,
            intent,
            confidence,
            candidates,
            players,
            teams,
            missing,
            self.config,
        )

        if clarification_required:
            routing_target = ROUTING_TARGETS[NLU_TASK_CLARIFICATION]
        else:
            routing_target = ROUTING_TARGETS.get(intent, "general_baseball_handler")

        external_entity = _safe_external_entity_report(normalized_message.normalized, players_catalog, self.config)
        external_fuzzy = _safe_external_fuzzy_report(normalized_message.normalized, players_catalog, teams_catalog, self.config)
        external_semantic = _safe_external_semantic_report(normalized_message.normalized, players_catalog, teams_catalog, self.config)
        external_intent = _safe_external_intent_report(normalized_message.normalized, players, teams, outcome, self.config)

        next_context = build_next_context(
            context,
            intent,
            players,
            teams,
            statistic,
            outcome,
            clarification_required,
            bool(context_resolution.get("reset")),
        )

        entities_payload = {
            "player": players[0].to_dict() if players else None,
            "players": [item.to_dict() for item in players],
            "team": teams[0].to_dict() if teams else None,
            "teams": [item.to_dict() for item in teams],
            "statistic": statistic.to_dict() if statistic else None,
            "outcome": outcome.to_dict() if outcome else None,
            "season": season.to_dict() if season else None,
            "date": relative_date.to_dict() if relative_date else None,
            "limit": limit.to_dict() if limit else None,
        }

        elapsed_ms = (utc_now() - started).total_seconds() * 1000.0
        diagnostics = {
            "classification_policy": "current_message_first",
            "previous_intent_used_for_classification": False,
            "previous_intent": context.last_intent,
            "normalized_message": normalized_message.to_dict(),
            "catalog_counts": {
                "players": len(players_catalog),
                "teams": len(teams_catalog),
            },
            "candidate_count": len(candidates),
            "top_candidate_margin": round(
                candidates[0].score - candidates[1].score if len(candidates) > 1 else candidates[0].score if candidates else 0.0,
                4,
            ),
            "external_engines": {
                "entity": external_entity,
                "fuzzy": external_fuzzy,
                "semantic": external_semantic,
                "intent": external_intent,
            },
            "processing_time_ms": round(elapsed_ms, 3),
            "request_fingerprint": fingerprint({
                "message": normalized_message.normalized,
                "players": [item.canonical_name for item in players],
                "teams": [item.canonical_name for item in teams],
                "statistic": statistic.canonical_name if statistic else None,
                "outcome": outcome.canonical_name if outcome else None,
                "intent": intent,
            }),
        }

        return NLUReport(
            request_id=normalized_message.request_id,
            original_message=normalized_message.original,
            normalized_message=normalized_message.normalized,
            intent=intent,
            scope=scope,
            confidence=confidence,
            confidence_band=confidence_band(confidence),
            routing_target=routing_target,
            entities=entities_payload,
            intent_candidates=candidates[:10],
            context_used=bool(context_resolution.get("used")),
            context_resolution=context_resolution,
            clarification_required=clarification_required,
            clarification_reason=clarification_reason,
            clarification_prompt=clarification_prompt,
            missing=missing,
            diagnostics=diagnostics,
            next_context=next_context,
        )


# ============================================================
# SECTION 25 - PRIMARY PUBLIC FUNCTION
# ============================================================

def understand_baseball_message(
    message: str | None,
    *,
    player_catalog: Any = None,
    team_catalog: Any = None,
    conversation_context: Any = None,
    request_id: str | None = None,
    config: NLUConfig | None = None,
) -> dict[str, Any]:
    """Understand one message through a completely fresh classification cycle."""
    engine = BaseballNLUEngine(config=config)
    return engine.understand(
        message,
        player_catalog=player_catalog,
        team_catalog=team_catalog,
        conversation_context=conversation_context,
        request_id=request_id,
    ).to_dict()


# ============================================================
# SECTION 26 - BACKWARD-COMPATIBLE NLU REPORT API
# ============================================================

def build_nlu_report(
    message: str,
    entity_report: dict | None = None,
    *,
    player_catalog: Any = None,
    team_catalog: Any = None,
    conversation_context: Any = None,
) -> dict[str, Any]:
    """
    Backward-compatible report function.

    The legacy entity_report argument is accepted but never treated as the
    authoritative classifier. It may supplement catalogs when possible.
    """
    if entity_report:
        if player_catalog is None:
            player_catalog = [
                {
                    "name": item.get("canonical_name") or item.get("name"),
                    "id": item.get("entity_id") or item.get("id"),
                }
                for item in entity_report.get("players", []) or []
            ]
        if team_catalog is None:
            team_catalog = [
                {
                    "name": item.get("canonical_name") or item.get("name"),
                    "id": item.get("entity_id") or item.get("id"),
                }
                for item in entity_report.get("teams", []) or []
            ]
    return understand_baseball_message(
        message,
        player_catalog=player_catalog,
        team_catalog=team_catalog,
        conversation_context=conversation_context,
    )


def classify_nlu_task(
    message: str,
    entity_report: dict | None = None,
) -> str:
    return build_nlu_report(message, entity_report=entity_report)["intent"]


def detect_best_probability_goal(message: str) -> bool:
    normalized = normalize_nlu_text(message)
    return contains_any(normalized, (
        "highest probability",
        "best probability",
        "most likely",
        "who has the highest",
        "who is most likely",
    ))


def detect_list_goal(message: str) -> str | None:
    normalized = normalize_nlu_text(message)
    if contains_any(normalized, ("list teams", "show all teams", "all mlb teams", "what teams")):
        return NLU_TASK_LIST_TEAMS
    if contains_any(normalized, ("list players", "show all players", "all mlb players", "what players")):
        return NLU_TASK_LIST_PLAYERS
    return None


def detect_help_goal(message: str) -> bool:
    return contains_any(normalize_nlu_text(message), ("help", "what can you do", "how do i use", "sample questions"))


def detect_comparison_goal(message: str) -> str | None:
    normalized = normalize_nlu_text(message)
    if contains_any(normalized, ("compare", "versus", "vs", "who is better", "between")):
        return NLU_TASK_COMPARE_PLAYERS
    return None


def calculate_nlu_confidence(
    task: str,
    scope: str,
    outcome: str | None,
    entity_report: dict | None = None,
) -> int:
    confidence = 35
    if task != NLU_TASK_GENERAL:
        confidence += 25
    if scope != NLU_SCOPE_UNKNOWN:
        confidence += 15
    if outcome:
        confidence += 15
    entity_report = entity_report or {}
    if entity_report.get("has_team"):
        confidence += 10
    if entity_report.get("has_player"):
        confidence += 10
    return min(confidence, 96)


# ============================================================
# SECTION 27 - BATCH API
# ============================================================

def understand_message_batch(
    messages: Iterable[str],
    *,
    player_catalog: Any = None,
    team_catalog: Any = None,
    conversation_context: Any = None,
    config: NLUConfig | None = None,
) -> list[dict[str, Any]]:
    engine = BaseballNLUEngine(config=config)
    context = ConversationContext.from_any(conversation_context)
    reports: list[dict[str, Any]] = []
    for message in messages:
        report = engine.understand(
            message,
            player_catalog=player_catalog,
            team_catalog=team_catalog,
            conversation_context=context,
        )
        reports.append(report.to_dict())
        context = report.next_context
    return reports


# ============================================================
# SECTION 28 - VALIDATION TEST CASES
# ============================================================

VALIDATION_PLAYER_CATALOG: Final[list[dict[str, Any]]] = [
    {"id": 682998, "name": "Corbin Carroll", "team_name": "Arizona Diamondbacks", "position": "OF"},
    {"id": 592450, "name": "Aaron Judge", "team_name": "New York Yankees", "position": "OF"},
    {"id": 660271, "name": "Shohei Ohtani", "team_name": "Los Angeles Dodgers", "position": "DH"},
    {"id": 665742, "name": "Juan Soto", "team_name": "New York Mets", "position": "OF"},
]

VALIDATION_TEAM_CATALOG: Final[list[dict[str, Any]]] = [
    {"id": 109, "name": "Arizona Diamondbacks", "abbreviation": "ARI", "aliases": ["dbacks"]},
    {"id": 147, "name": "New York Yankees", "abbreviation": "NYY", "aliases": ["yankees", "yanks"]},
    {"id": 119, "name": "Los Angeles Dodgers", "abbreviation": "LAD", "aliases": ["dodgers"]},
    {"id": 121, "name": "New York Mets", "abbreviation": "NYM", "aliases": ["mets"]},
]


def validate_nlu_engine() -> dict[str, Any]:
    engine = BaseballNLUEngine(NLUConfig(
        enable_external_entity_engine=False,
        enable_external_intent_engine=False,
        enable_external_semantic_engine=False,
        enable_external_context_engine=False,
        enable_external_fuzzy_engine=False,
    ))

    cases = [
        ("show all mlb teams", NLU_TASK_LIST_TEAMS),
        ("find Corbin Carroll", NLU_TASK_PLAYER_LOOKUP),
        ("what is Corbin Carroll's OPS", NLU_TASK_PLAYER_STATS),
        ("predict Aaron Judge home run", NLU_TASK_PLAYER_PROBABILITY),
        ("show the Yankees roster", NLU_TASK_TEAM_ROSTER),
        ("when do the Mets play next", NLU_TASK_TEAM_SCHEDULE),
        ("is the database connected", NLU_TASK_DATABASE_STATUS),
        ("compare Aaron Judge and Shohei Ohtani", NLU_TASK_COMPARE_PLAYERS),
    ]

    results: list[dict[str, Any]] = []
    passed = 0
    for message, expected in cases:
        report = engine.understand(
            message,
            player_catalog=VALIDATION_PLAYER_CATALOG,
            team_catalog=VALIDATION_TEAM_CATALOG,
        )
        ok = report.intent == expected
        passed += int(ok)
        results.append({
            "message": message,
            "expected": expected,
            "actual": report.intent,
            "passed": ok,
            "confidence": report.confidence,
        })

    # Multi-turn subject switching test. Previous player must never override a
    # newly named player or a team question.
    first = engine.understand(
        "show Corbin Carroll",
        player_catalog=VALIDATION_PLAYER_CATALOG,
        team_catalog=VALIDATION_TEAM_CATALOG,
    )
    follow_up = engine.understand(
        "what is his OPS",
        player_catalog=VALIDATION_PLAYER_CATALOG,
        team_catalog=VALIDATION_TEAM_CATALOG,
        conversation_context=first.next_context,
    )
    switched = engine.understand(
        "predict Aaron Judge home run",
        player_catalog=VALIDATION_PLAYER_CATALOG,
        team_catalog=VALIDATION_TEAM_CATALOG,
        conversation_context=follow_up.next_context,
    )
    team_switch = engine.understand(
        "show all MLB teams",
        player_catalog=VALIDATION_PLAYER_CATALOG,
        team_catalog=VALIDATION_TEAM_CATALOG,
        conversation_context=switched.next_context,
    )

    context_tests = {
        "pronoun_resolved": (
            follow_up.entities["player"] is not None
            and follow_up.entities["player"]["canonical_name"] == "Corbin Carroll"
            and follow_up.intent == NLU_TASK_PLAYER_STATS
        ),
        "new_player_overrides_context": (
            switched.entities["player"] is not None
            and switched.entities["player"]["canonical_name"] == "Aaron Judge"
            and switched.intent == NLU_TASK_PLAYER_PROBABILITY
        ),
        "team_list_ignores_previous_player": team_switch.intent == NLU_TASK_LIST_TEAMS,
        "previous_intent_not_used": team_switch.diagnostics["previous_intent_used_for_classification"] is False,
    }

    total = len(cases) + len(context_tests)
    total_passed = passed + sum(bool(value) for value in context_tests.values())
    return {
        "status": "ok" if total_passed == total else "failed",
        "engine": NLU_ENGINE_NAME,
        "version": NLU_ENGINE_VERSION,
        "passed": total_passed,
        "total": total,
        "cases": results,
        "context_tests": context_tests,
    }


# ============================================================
# SECTION 29 - HEALTH REPORT
# ============================================================

def nlu_engine_health() -> dict[str, Any]:
    validation = validate_nlu_engine()
    return {
        "name": NLU_ENGINE_NAME,
        "version": NLU_ENGINE_VERSION,
        "phase": NLU_ENGINE_PHASE,
        "path": NLU_ENGINE_PATH,
        "status": NLU_ENGINE_STATUS if validation["status"] == "ok" else "validation_failed",
        "sqlalchemy_dependency": False,
        "database_model_code_present": False,
        "all_task_constants_defined": True,
        "independent_message_reclassification": True,
        "context_is_followup_only": True,
        "supported_tasks": list(SUPPORTED_TASKS),
        "supported_scopes": list(SUPPORTED_SCOPES),
        "external_engines_available": {
            "entity": _external_entity_report is not None,
            "intent": _external_intent_report is not None,
            "semantic": _external_semantic_report is not None,
            "context": _external_context_report is not None,
            "fuzzy": _external_fuzzy_report is not None,
        },
        "validation": validation,
        "timestamp": utc_now().isoformat(),
    }


# ============================================================
# SECTION 30 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "NLU_ENGINE_NAME",
    "NLU_ENGINE_VERSION",
    "NLU_ENGINE_PHASE",
    "NLU_ENGINE_PATH",
    "NLU_ENGINE_STATUS",
    "NLU_TASK_GENERAL",
    "NLU_TASK_GREETING",
    "NLU_TASK_HELP",
    "NLU_TASK_LIST_TEAMS",
    "NLU_TASK_LIST_PLAYERS",
    "NLU_TASK_TEAM_LOOKUP",
    "NLU_TASK_TEAM_STATS",
    "NLU_TASK_TEAM_ROSTER",
    "NLU_TASK_TEAM_SCHEDULE",
    "NLU_TASK_TEAM_PREDICTION",
    "NLU_TASK_PLAYER_LOOKUP",
    "NLU_TASK_PLAYER_STATS",
    "NLU_TASK_PLAYER_GAME_LOG",
    "NLU_TASK_PLAYER_SPLITS",
    "NLU_TASK_PLAYER_PROBABILITY",
    "NLU_TASK_COMPARE_PLAYERS",
    "NLU_TASK_COMPARE_TEAMS",
    "NLU_TASK_MATCHUP_ANALYSIS",
    "NLU_TASK_GAME_LOOKUP",
    "NLU_TASK_GAME_PREDICTION",
    "NLU_TASK_STANDINGS",
    "NLU_TASK_LEAGUE_LEADERS",
    "NLU_TASK_DATABASE_STATUS",
    "NLU_TASK_WAREHOUSE_STATUS",
    "NLU_TASK_DATA_FRESHNESS",
    "NLU_TASK_MODEL_STATUS",
    "NLU_TASK_EXPLAIN_MODEL",
    "NLU_TASK_CLARIFICATION",
    "NLU_TASK_UNSUPPORTED",
    "NLU_TASK_BEST_TEAM_PROBABILITY",
    "NLU_TASK_BEST_OVERALL_PROBABILITY",
    "NLU_TASK_ROSTER_LOOKUP",
    "NLU_SCOPE_UNKNOWN",
    "NLU_SCOPE_ALL_PLAYERS",
    "NLU_SCOPE_TEAM_PLAYERS",
    "NLU_SCOPE_SINGLE_PLAYER",
    "NLU_SCOPE_MULTIPLE_PLAYERS",
    "NLU_SCOPE_ALL_TEAMS",
    "NLU_SCOPE_TEAM",
    "NLU_SCOPE_MULTIPLE_TEAMS",
    "NLU_SCOPE_GAME",
    "NLU_SCOPE_LEAGUE",
    "NLU_SCOPE_SYSTEM",
    "ConfidenceBand",
    "EntitySource",
    "ClarificationReason",
    "NormalizedMessage",
    "ResolvedEntity",
    "ConversationContext",
    "IntentCandidate",
    "NLUReport",
    "NLUConfig",
    "BaseballNLUEngine",
    "normalize_nlu_text",
    "detect_nlu_question_type",
    "build_normalized_message",
    "build_language_normalization_report",
    "nlu_contains_any",
    "normalize_player_catalog",
    "normalize_team_catalog",
    "detect_statistic",
    "detect_nlu_outcome",
    "detect_outcome_entity",
    "detect_season",
    "detect_limit",
    "detect_relative_date",
    "detect_entity_scope",
    "detect_missing_information",
    "detect_best_probability_goal",
    "detect_list_goal",
    "detect_help_goal",
    "detect_comparison_goal",
    "calculate_nlu_confidence",
    "classify_nlu_task",
    "understand_baseball_message",
    "build_nlu_report",
    "understand_message_batch",
    "validate_nlu_engine",
    "nlu_engine_health",
]


# ============================================================
# SECTION 31 - LOCAL VALIDATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    print(json.dumps(nlu_engine_health(), indent=2, sort_keys=True))

Library
/
Sports Predicti.
/
nlu_engine_render_safe.py
# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# PACKAGE: 04_ai/nlp
# FILE: nlu_engine.py
# PURPOSE:
# Enterprise Natural Language Understanding orchestration for
# independent baseball-question classification, entity-aware
# routing, multi-turn follow-up resolution, diagnostics, and
# stable downstream chat-service contracts.
# ============================================================
"""
AISP2 enterprise Natural Language Understanding engine.

This module is the primary orchestration layer for baseball chat requests.
It intentionally contains no SQLAlchemy models, database table declarations,
HTTP routes, Flask objects, model training, or response rendering.

Responsibilities
----------------
1. Normalize one incoming user message into a stable text contract.
2. Reclassify every message independently from previous intent state.
3. Coordinate entity, intent, fuzzy, semantic, and context helpers.
4. Use conversation context only to resolve incomplete follow-ups.
5. Ensure a newly named player, team, game, stat, or outcome overrides old
   conversation context.
6. Detect ambiguity and missing information before backend routing.
7. Produce deterministic, serializable reports for the chat service.
8. Remain importable when sibling NLP modules are temporarily unavailable.

The orchestration rule is strict:

    CURRENT MESSAGE MEANING > EXPLICIT CURRENT ENTITIES > FOLLOW-UP CONTEXT
    > FALLBACK HEURISTICS > PREVIOUS INTENT

Previous intent is diagnostic only. It never locks or forces the next user
message into the previous request type.
"""

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, date, datetime, timedelta
from enum import Enum
from hashlib import sha256
import json
import logging
import math
import re
import unicodedata
from typing import Any, Final, Protocol
from uuid import uuid4

LOGGER = logging.getLogger(__name__)


# ============================================================
# SECTION 02 - MODULE METADATA
# ============================================================

NLU_ENGINE_NAME: Final[str] = "AISP2 Enterprise Baseball NLU Engine"
NLU_ENGINE_VERSION: Final[str] = "4.0.0"
NLU_ENGINE_PHASE: Final[str] = "Phase 10 Part 10.0"
NLU_ENGINE_PATH: Final[str] = "04_ai/nlp/nlu_engine.py"
NLU_ENGINE_STATUS: Final[str] = "enterprise_ready"


# ============================================================
# SECTION 03 - OPTIONAL SIBLING ENGINE IMPORTS
# ============================================================

# The package can run in both package-import and direct-script contexts.
try:  # pragma: no cover - import path depends on runtime packaging
    from .entity_detection import build_entity_report as _external_entity_report
except Exception:  # pragma: no cover
    try:
        from entity_detection import build_entity_report as _external_entity_report
    except Exception:
        _external_entity_report = None

try:  # pragma: no cover
    from .intent_detection import build_intent_report as _external_intent_report
except Exception:  # pragma: no cover
    try:
        from intent_detection import build_intent_report as _external_intent_report
    except Exception:
        _external_intent_report = None

try:  # pragma: no cover
    from .semantic_engine import interpret_baseball_question as _external_semantic_report
except Exception:  # pragma: no cover
    try:
        from semantic_engine import interpret_baseball_question as _external_semantic_report
    except Exception:
        _external_semantic_report = None

try:  # pragma: no cover
    from .context_builder import build_baseball_context as _external_context_report
except Exception:  # pragma: no cover
    try:
        from context_builder import build_baseball_context as _external_context_report
    except Exception:
        _external_context_report = None

try:  # pragma: no cover
    from .fuzzy_matching import build_fuzzy_nlp_report as _external_fuzzy_report
except Exception:  # pragma: no cover
    try:
        from fuzzy_matching import build_fuzzy_nlp_report as _external_fuzzy_report
    except Exception:
        _external_fuzzy_report = None


# ============================================================
# SECTION 04 - PUBLIC TASK CONSTANTS
# ============================================================

NLU_TASK_GENERAL = "general_baseball_question"
NLU_TASK_GREETING = "greeting"
NLU_TASK_HELP = "help"
NLU_TASK_LIST_TEAMS = "list_teams"
NLU_TASK_LIST_PLAYERS = "list_players"
NLU_TASK_TEAM_LOOKUP = "team_lookup"
NLU_TASK_TEAM_STATS = "team_stats"
NLU_TASK_TEAM_ROSTER = "team_roster"
NLU_TASK_TEAM_SCHEDULE = "team_schedule"
NLU_TASK_TEAM_PREDICTION = "team_prediction"
NLU_TASK_PLAYER_LOOKUP = "player_lookup"
NLU_TASK_PLAYER_STATS = "player_stats"
NLU_TASK_PLAYER_GAME_LOG = "player_game_log"
NLU_TASK_PLAYER_SPLITS = "player_splits"
NLU_TASK_PLAYER_PROBABILITY = "player_probability"
NLU_TASK_COMPARE_PLAYERS = "compare_players"
NLU_TASK_COMPARE_TEAMS = "compare_teams"
NLU_TASK_MATCHUP_ANALYSIS = "matchup_analysis"
NLU_TASK_GAME_LOOKUP = "game_lookup"
NLU_TASK_GAME_PREDICTION = "game_prediction"
NLU_TASK_STANDINGS = "standings"
NLU_TASK_LEAGUE_LEADERS = "league_leaders"
NLU_TASK_DATABASE_STATUS = "database_status"
NLU_TASK_WAREHOUSE_STATUS = "warehouse_status"
NLU_TASK_DATA_FRESHNESS = "data_freshness"
NLU_TASK_MODEL_STATUS = "model_status"
NLU_TASK_EXPLAIN_MODEL = "explain_model"
NLU_TASK_CLARIFICATION = "clarification_required"
NLU_TASK_UNSUPPORTED = "unsupported"
NLU_TASK_BEST_TEAM_PROBABILITY = "best_team_probability"
NLU_TASK_BEST_OVERALL_PROBABILITY = "best_overall_probability"
NLU_TASK_ROSTER_LOOKUP = NLU_TASK_TEAM_ROSTER

SUPPORTED_TASKS: Final[tuple[str, ...]] = (
    NLU_TASK_GENERAL,
    NLU_TASK_GREETING,
    NLU_TASK_HELP,
    NLU_TASK_LIST_TEAMS,
    NLU_TASK_LIST_PLAYERS,
    NLU_TASK_TEAM_LOOKUP,
    NLU_TASK_TEAM_STATS,
    NLU_TASK_TEAM_ROSTER,
    NLU_TASK_TEAM_SCHEDULE,
    NLU_TASK_TEAM_PREDICTION,
    NLU_TASK_PLAYER_LOOKUP,
    NLU_TASK_PLAYER_STATS,
    NLU_TASK_PLAYER_GAME_LOG,
    NLU_TASK_PLAYER_SPLITS,
    NLU_TASK_PLAYER_PROBABILITY,
    NLU_TASK_COMPARE_PLAYERS,
    NLU_TASK_COMPARE_TEAMS,
    NLU_TASK_MATCHUP_ANALYSIS,
    NLU_TASK_GAME_LOOKUP,
    NLU_TASK_GAME_PREDICTION,
    NLU_TASK_STANDINGS,
    NLU_TASK_LEAGUE_LEADERS,
    NLU_TASK_DATABASE_STATUS,
    NLU_TASK_WAREHOUSE_STATUS,
    NLU_TASK_DATA_FRESHNESS,
    NLU_TASK_MODEL_STATUS,
    NLU_TASK_EXPLAIN_MODEL,
    NLU_TASK_CLARIFICATION,
    NLU_TASK_UNSUPPORTED,
    NLU_TASK_BEST_TEAM_PROBABILITY,
    NLU_TASK_BEST_OVERALL_PROBABILITY,
)


# ============================================================
# SECTION 05 - PUBLIC SCOPE CONSTANTS
# ============================================================

NLU_SCOPE_UNKNOWN = "unknown"
NLU_SCOPE_ALL_PLAYERS = "all_players"
NLU_SCOPE_TEAM_PLAYERS = "team_players"
NLU_SCOPE_SINGLE_PLAYER = "single_player"
NLU_SCOPE_MULTIPLE_PLAYERS = "multiple_players"
NLU_SCOPE_ALL_TEAMS = "all_teams"
NLU_SCOPE_TEAM = "team"
NLU_SCOPE_MULTIPLE_TEAMS = "multiple_teams"
NLU_SCOPE_GAME = "game"
NLU_SCOPE_LEAGUE = "league"
NLU_SCOPE_SYSTEM = "system"

SUPPORTED_SCOPES: Final[tuple[str, ...]] = (
    NLU_SCOPE_UNKNOWN,
    NLU_SCOPE_ALL_PLAYERS,
    NLU_SCOPE_TEAM_PLAYERS,
    NLU_SCOPE_SINGLE_PLAYER,
    NLU_SCOPE_MULTIPLE_PLAYERS,
    NLU_SCOPE_ALL_TEAMS,
    NLU_SCOPE_TEAM,
    NLU_SCOPE_MULTIPLE_TEAMS,
    NLU_SCOPE_GAME,
    NLU_SCOPE_LEAGUE,
    NLU_SCOPE_SYSTEM,
)


# ============================================================
# SECTION 06 - ENTITY, STAT, OUTCOME, AND TIME CONSTANTS
# ============================================================

ENTITY_PLAYER = "player"
ENTITY_TEAM = "team"
ENTITY_GAME = "game"
ENTITY_STATISTIC = "statistic"
ENTITY_OUTCOME = "outcome"
ENTITY_DATE = "date"
ENTITY_SEASON = "season"
ENTITY_VENUE = "venue"
ENTITY_POSITION = "position"
ENTITY_OPPONENT = "opponent"
ENTITY_PITCHER = "pitcher"
ENTITY_BATTER = "batter"
ENTITY_LIMIT = "limit"

SUPPORTED_OUTCOMES: Final[tuple[str, ...]] = (
    "hit",
    "single",
    "double",
    "triple",
    "home_run",
    "walk",
    "strikeout",
    "rbi",
    "run",
    "stolen_base",
    "total_bases",
    "team_win",
    "team_runs",
)

SUPPORTED_STATISTICS: Final[tuple[str, ...]] = (
    "batting_average",
    "on_base_percentage",
    "slugging_percentage",
    "ops",
    "home_runs",
    "hits",
    "singles",
    "doubles",
    "triples",
    "walks",
    "strikeouts",
    "rbi",
    "runs",
    "stolen_bases",
    "total_bases",
    "plate_appearances",
    "at_bats",
    "woba",
    "wrc_plus",
    "war",
    "era",
    "whip",
    "fip",
    "xfip",
    "strikeout_rate",
    "walk_rate",
    "barrel_rate",
    "hard_hit_rate",
    "exit_velocity",
    "launch_angle",
    "xba",
    "xslg",
    "xwoba",
    "chase_rate",
    "whiff_rate",
    "contact_rate",
    "wins",
    "losses",
    "win_percentage",
    "runs_per_game",
    "runs_allowed_per_game",
)


# ============================================================
# SECTION 07 - ENUMERATIONS
# ============================================================

class ConfidenceBand(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class EntitySource(str, Enum):
    CURRENT_EXACT = "current_exact"
    CURRENT_ALIAS = "current_alias"
    CURRENT_FUZZY = "current_fuzzy"
    CURRENT_HEURISTIC = "current_heuristic"
    CONVERSATION_CONTEXT = "conversation_context"
    EXTERNAL_ENGINE = "external_engine"
    UNKNOWN = "unknown"


class ClarificationReason(str, Enum):
    NONE = "none"
    EMPTY_MESSAGE = "empty_message"
    MISSING_PLAYER = "missing_player"
    MISSING_TEAM = "missing_team"
    MISSING_OUTCOME = "missing_outcome"
    MISSING_STATISTIC = "missing_statistic"
    AMBIGUOUS_PLAYER = "ambiguous_player"
    AMBIGUOUS_TEAM = "ambiguous_team"
    AMBIGUOUS_INTENT = "ambiguous_intent"
    UNSUPPORTED_REQUEST = "unsupported_request"


# ============================================================
# SECTION 08 - CORE DATA CONTRACTS
# ============================================================

@dataclass(slots=True)
class NormalizedMessage:
    request_id: str
    original: str
    normalized: str
    tokens: list[str]
    token_set: set[str]
    question_type: str
    is_empty: bool
    corrections: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "original": self.original,
            "normalized": self.normalized,
            "tokens": self.tokens,
            "question_type": self.question_type,
            "is_empty": self.is_empty,
            "corrections": self.corrections,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(slots=True)
class ResolvedEntity:
    entity_type: str
    canonical_name: str | None = None
    entity_id: int | str | None = None
    matched_text: str | None = None
    confidence: float = 0.0
    source: EntitySource = EntitySource.UNKNOWN
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "canonical_name": self.canonical_name,
            "entity_id": self.entity_id,
            "matched_text": self.matched_text,
            "confidence": round(float(self.confidence), 4),
            "source": self.source.value,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class ConversationContext:
    last_player_id: int | str | None = None
    last_player_name: str | None = None
    last_team_id: int | str | None = None
    last_team_name: str | None = None
    last_game_id: int | str | None = None
    last_game_label: str | None = None
    last_statistic: str | None = None
    last_outcome: str | None = None
    last_intent: str | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_any(cls, value: Any) -> "ConversationContext":
        if value is None:
            return cls()
        if isinstance(value, cls):
            return value
        if is_dataclass(value):
            value = asdict(value)
        if isinstance(value, Mapping):
            return cls(
                last_player_id=value.get("last_player_id"),
                last_player_name=value.get("last_player_name"),
                last_team_id=value.get("last_team_id"),
                last_team_name=value.get("last_team_name"),
                last_game_id=value.get("last_game_id"),
                last_game_label=value.get("last_game_label"),
                last_statistic=value.get("last_statistic"),
                last_outcome=value.get("last_outcome"),
                last_intent=value.get("last_intent"),
                updated_at=parse_datetime(value.get("updated_at")),
                metadata=dict(value.get("metadata") or {}),
            )
        return cls()

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_player_id": self.last_player_id,
            "last_player_name": self.last_player_name,
            "last_team_id": self.last_team_id,
            "last_team_name": self.last_team_name,
            "last_game_id": self.last_game_id,
            "last_game_label": self.last_game_label,
            "last_statistic": self.last_statistic,
            "last_outcome": self.last_outcome,
            "last_intent": self.last_intent,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class IntentCandidate:
    intent: str
    score: float
    evidence: list[str] = field(default_factory=list)
    negative_evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "score": round(float(self.score), 4),
            "evidence": self.evidence,
            "negative_evidence": self.negative_evidence,
        }


@dataclass(slots=True)
class NLUReport:
    request_id: str
    original_message: str
    normalized_message: str
    intent: str
    scope: str
    confidence: float
    confidence_band: ConfidenceBand
    routing_target: str
    entities: dict[str, Any]
    intent_candidates: list[IntentCandidate]
    context_used: bool
    context_resolution: dict[str, Any]
    clarification_required: bool
    clarification_reason: ClarificationReason
    clarification_prompt: str | None
    missing: dict[str, bool]
    diagnostics: dict[str, Any]
    next_context: ConversationContext
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "original_message": self.original_message,
            "normalized_message": self.normalized_message,
            "intent": self.intent,
            "task": self.intent,
            "scope": self.scope,
            "confidence": round(float(self.confidence), 4),
            "confidence_percent": round(float(self.confidence) * 100.0, 2),
            "confidence_band": self.confidence_band.value,
            "routing_target": self.routing_target,
            "entities": self.entities,
            "intent_candidates": [item.to_dict() for item in self.intent_candidates],
            "context_used": self.context_used,
            "context_resolution": self.context_resolution,
            "clarification_required": self.clarification_required,
            "clarification_reason": self.clarification_reason.value,
            "clarification_prompt": self.clarification_prompt,
            "missing": self.missing,
            "routing_ready": not self.clarification_required,
            "diagnostics": self.diagnostics,
            "next_context": self.next_context.to_dict(),
            "created_at": self.created_at.isoformat(),
            "engine": {
                "name": NLU_ENGINE_NAME,
                "version": NLU_ENGINE_VERSION,
                "phase": NLU_ENGINE_PHASE,
                "path": NLU_ENGINE_PATH,
            },
        }


# ============================================================
# SECTION 09 - CONFIGURATION
# ============================================================

@dataclass(slots=True)
class NLUConfig:
    enable_external_entity_engine: bool = True
    enable_external_intent_engine: bool = True
    enable_external_semantic_engine: bool = True
    enable_external_context_engine: bool = True
    enable_external_fuzzy_engine: bool = True
    allow_context_pronoun_resolution: bool = True
    allow_context_ellipsis_resolution: bool = True
    context_max_age_hours: float = 24.0
    minimum_confidence: float = 0.35
    clarification_confidence: float = 0.52
    ambiguity_margin: float = 0.08
    fuzzy_threshold: float = 0.78
    max_catalog_candidates: int = 8
    strict: bool = False

    def validate(self) -> None:
        for field_name in (
            "minimum_confidence",
            "clarification_confidence",
            "ambiguity_margin",
            "fuzzy_threshold",
        ):
            value = float(getattr(self, field_name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1")
        if self.context_max_age_hours < 0:
            raise ValueError("context_max_age_hours cannot be negative")
        if self.max_catalog_candidates <= 0:
            raise ValueError("max_catalog_candidates must be positive")


DEFAULT_CONFIG = NLUConfig()


# ============================================================
# SECTION 10 - NORMALIZATION TABLES
# ============================================================

DIRECT_TOKEN_REPLACEMENTS: Final[dict[str, str]] = {
    "whos": "who is",
    "whats": "what is",
    "wheres": "where is",
    "hows": "how is",
    "cant": "cannot",
    "wont": "will not",
    "dont": "do not",
    "doesnt": "does not",
    "isnt": "is not",
    "arent": "are not",
    "im": "i am",
    "ive": "i have",
    "probablity": "probability",
    "probalility": "probability",
    "prediciton": "prediction",
    "predicitons": "predictions",
    "projecton": "projection",
    "basebal": "baseball",
    "baseabll": "baseball",
    "rostor": "roster",
    "likley": "likely",
    "homerun": "home run",
    "homeurn": "home run",
    "strikout": "strikeout",
    "striekout": "strikeout",
    "ribbies": "rbi",
    "ribbie": "rbi",
    "dingers": "home run",
    "dinger": "home run",
    "punchouts": "strikeouts",
    "punchout": "strikeout",
}

PHRASE_REPLACEMENTS: Final[dict[str, str]] = {
    "home runn": "home run",
    "home-run": "home run",
    "stat cast": "statcast",
    "runs batted in": "rbi",
    "run batted in": "rbi",
    "base knock": "hit",
    "long ball": "home run",
    "go yard": "hit a home run",
    "goes yard": "hits a home run",
    "to homer": "to hit a home run",
    "hit bomb": "hit a home run",
    "hit a bomb": "hit a home run",
    "get a hit": "record a hit",
    "gets a hit": "records a hit",
    "strike out": "strikeout",
    "total base": "total bases",
    "best shot": "highest probability",
    "top shot": "highest probability",
    "best bet": "highest probability",
    "highest chance": "highest probability",
    "best chance": "highest probability",
    "top chance": "highest probability",
    "highest odds": "highest probability",
    "best odds": "highest probability",
    "most probable": "most likely",
}

OUTCOME_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "home_run": ("home run", "homer", "hr", "dinger", "go deep", "go yard"),
    "hit": ("record a hit", "base hit", "hit"),
    "single": ("single", "one bagger"),
    "double": ("double", "two bagger", "two base hit"),
    "triple": ("triple", "three bagger", "three base hit"),
    "walk": ("walk", "base on balls", "bb"),
    "strikeout": ("strikeout", "strikeouts", "k", "ks", "whiff", "punchout"),
    "rbi": ("rbi", "drive in", "knock in"),
    "run": ("run scored", "score a run", "scores a run"),
    "stolen_base": ("stolen base", "steal a base", "sb"),
    "total_bases": ("total bases", "tb"),
    "team_win": ("win", "winner", "moneyline"),
    "team_runs": ("team runs", "runs scored", "run total"),
}

STAT_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "batting_average": ("batting average", "average", "avg", "ba"),
    "on_base_percentage": ("on base percentage", "on base", "obp"),
    "slugging_percentage": ("slugging percentage", "slugging", "slg"),
    "ops": ("ops",),
    "home_runs": ("home runs", "homers", "hr total"),
    "hits": ("hits", "hit total"),
    "singles": ("singles",),
    "doubles": ("doubles",),
    "triples": ("triples",),
    "walks": ("walks", "bb total"),
    "strikeouts": ("strikeouts", "k total", "ks"),
    "rbi": ("rbi",),
    "runs": ("runs",),
    "stolen_bases": ("stolen bases", "sb total"),
    "total_bases": ("total bases", "tb"),
    "plate_appearances": ("plate appearances", "pa"),
    "at_bats": ("at bats", "ab"),
    "woba": ("woba",),
    "wrc_plus": ("wrc+", "wrc plus", "wrc"),
    "war": ("war",),
    "era": ("era",),
    "whip": ("whip",),
    "fip": ("fip",),
    "xfip": ("xfip",),
    "strikeout_rate": ("strikeout rate", "k rate", "k percentage"),
    "walk_rate": ("walk rate", "bb rate", "walk percentage"),
    "barrel_rate": ("barrel rate", "barrels"),
    "hard_hit_rate": ("hard hit rate", "hard hit"),
    "exit_velocity": ("exit velocity", "ev"),
    "launch_angle": ("launch angle",),
    "xba": ("xba", "expected batting average"),
    "xslg": ("xslg", "expected slugging"),
    "xwoba": ("xwoba", "expected woba"),
    "chase_rate": ("chase rate",),
    "whiff_rate": ("whiff rate",),
    "contact_rate": ("contact rate",),
    "wins": ("wins",),
    "losses": ("losses",),
    "win_percentage": ("win percentage", "winning percentage", "record"),
    "runs_per_game": ("runs per game", "rpg"),
    "runs_allowed_per_game": ("runs allowed per game",),
}

PRONOUN_PLAYER_PHRASES: Final[tuple[str, ...]] = (
    "he", "him", "his", "that player", "the player", "this player",
    "that hitter", "that pitcher", "the hitter", "the pitcher",
)

PRONOUN_TEAM_PHRASES: Final[tuple[str, ...]] = (
    "they", "them", "their", "that team", "the team", "this team",
    "that club", "the club",
)

RESET_CONTEXT_PHRASES: Final[tuple[str, ...]] = (
    "new question", "forget that", "clear context", "start over", "reset chat",
)


# ============================================================
# SECTION 11 - INTENT RULES
# ============================================================

@dataclass(frozen=True, slots=True)
class IntentRule:
    intent: str
    routing_target: str
    phrases: tuple[str, ...] = ()
    required_any: tuple[str, ...] = ()
    negative_phrases: tuple[str, ...] = ()
    base_weight: float = 0.0
    phrase_weight: float = 1.0
    entity_bonus: tuple[str, ...] = ()
    priority: int = 100


INTENT_RULES: Final[tuple[IntentRule, ...]] = (
    IntentRule(
        NLU_TASK_DATABASE_STATUS,
        "database_status_handler",
        phrases=("database status", "is the database connected", "database connected", "database health"),
        required_any=("database", "db"),
        base_weight=2.0,
        priority=1,
    ),
    IntentRule(
        NLU_TASK_WAREHOUSE_STATUS,
        "warehouse_status_handler",
        phrases=("warehouse status", "ingestion status", "data warehouse", "rows loaded"),
        required_any=("warehouse", "ingestion", "loaded"),
        base_weight=1.8,
        priority=2,
    ),
    IntentRule(
        NLU_TASK_DATA_FRESHNESS,
        "data_freshness_handler",
        phrases=("how fresh is the data", "latest ingestion", "last updated", "data freshness", "stale data"),
        required_any=("fresh", "updated", "latest", "stale"),
        base_weight=1.8,
        priority=3,
    ),
    IntentRule(
        NLU_TASK_MODEL_STATUS,
        "model_status_handler",
        phrases=("model status", "prediction engine status", "is the model ready"),
        required_any=("model", "engine"),
        base_weight=1.5,
        priority=4,
    ),
    IntentRule(
        NLU_TASK_EXPLAIN_MODEL,
        "explainability_handler",
        phrases=("explain the model", "how does the model work", "why that prediction", "why that probability", "what factors"),
        required_any=("why", "explain", "factors", "reasoning"),
        base_weight=1.3,
        priority=5,
    ),
    IntentRule(
        NLU_TASK_HELP,
        "help_handler",
        phrases=("what can you do", "how do i use", "sample questions", "show me what you can do", "help"),
        base_weight=1.3,
        priority=6,
    ),
    IntentRule(
        NLU_TASK_LIST_TEAMS,
        "list_teams_handler",
        phrases=("list teams", "show all teams", "all mlb teams", "every mlb team", "what teams", "which teams", "team list"),
        required_any=("teams", "clubs", "franchises"),
        negative_phrases=("team stats", "team roster", "team schedule"),
        base_weight=1.5,
        priority=10,
    ),
    IntentRule(
        NLU_TASK_LIST_PLAYERS,
        "list_players_handler",
        phrases=("list players", "show all players", "all mlb players", "what players", "which players", "player list"),
        required_any=("players",),
        negative_phrases=("player stats", "player prediction"),
        base_weight=1.5,
        priority=11,
    ),
    IntentRule(
        NLU_TASK_COMPARE_PLAYERS,
        "compare_players_handler",
        phrases=("compare players", "who is better", "which player is better", "between", "versus", " vs "),
        entity_bonus=(ENTITY_PLAYER,),
        base_weight=1.2,
        priority=12,
    ),
    IntentRule(
        NLU_TASK_COMPARE_TEAMS,
        "compare_teams_handler",
        phrases=("compare teams", "which team is better", "team comparison", "who wins", "team matchup"),
        entity_bonus=(ENTITY_TEAM,),
        base_weight=1.2,
        priority=13,
    ),
    IntentRule(
        NLU_TASK_GAME_PREDICTION,
        "game_prediction_handler",
        phrases=("predict the game", "game prediction", "who will win", "win probability", "game odds"),
        required_any=("predict", "prediction", "probability", "win", "odds"),
        base_weight=1.5,
        priority=14,
    ),
    IntentRule(
        NLU_TASK_TEAM_PREDICTION,
        "team_prediction_handler",
        phrases=("team prediction", "team win probability", "chances to win", "will the team win"),
        required_any=("predict", "probability", "chance", "win"),
        entity_bonus=(ENTITY_TEAM,),
        base_weight=1.4,
        priority=15,
    ),
    IntentRule(
        NLU_TASK_PLAYER_PROBABILITY,
        "player_prediction_handler",
        phrases=("predict", "probability", "what are the chances", "how likely", "will he", "will she", "projection", "player prop"),
        required_any=("predict", "probability", "chance", "likely", "projection", "odds", "will"),
        entity_bonus=(ENTITY_PLAYER, ENTITY_OUTCOME),
        base_weight=1.4,
        priority=16,
    ),
    IntentRule(
        NLU_TASK_MATCHUP_ANALYSIS,
        "matchup_analysis_handler",
        phrases=("matchup", "batter vs pitcher", "against", "facing", "splits versus", "park factor", "weather impact"),
        required_any=("matchup", "against", "facing", "versus", " vs "),
        base_weight=1.2,
        priority=17,
    ),
    IntentRule(
        NLU_TASK_TEAM_ROSTER,
        "team_roster_handler",
        phrases=("team roster", "show roster", "who is on", "who plays for", "active roster", "40 man roster", "lineup"),
        required_any=("roster", "lineup", "players on"),
        entity_bonus=(ENTITY_TEAM,),
        base_weight=1.4,
        priority=20,
    ),
    IntentRule(
        NLU_TASK_TEAM_SCHEDULE,
        "team_schedule_handler",
        phrases=("team schedule", "when do", "next game", "upcoming games", "who do they play", "schedule"),
        required_any=("schedule", "next game", "when", "upcoming"),
        entity_bonus=(ENTITY_TEAM,),
        base_weight=1.3,
        priority=21,
    ),
    IntentRule(
        NLU_TASK_PLAYER_GAME_LOG,
        "player_game_log_handler",
        phrases=("game log", "recent games", "last game", "last five games", "last 5", "last ten games", "last 10"),
        required_any=("game log", "recent", "last game", "last 5", "last 10"),
        entity_bonus=(ENTITY_PLAYER,),
        base_weight=1.3,
        priority=22,
    ),
    IntentRule(
        NLU_TASK_PLAYER_SPLITS,
        "player_splits_handler",
        phrases=("splits", "against lefties", "against righties", "home away splits", "platoon split"),
        required_any=("splits", "lefties", "righties", "home away"),
        entity_bonus=(ENTITY_PLAYER,),
        base_weight=1.3,
        priority=23,
    ),
    IntentRule(
        NLU_TASK_PLAYER_STATS,
        "player_stats_handler",
        phrases=("player stats", "season stats", "career stats", "what is his", "what is her", "stats for"),
        required_any=("stats", "statistics", "average", "ops", "era", "whip", "home runs", "hits", "rbi"),
        entity_bonus=(ENTITY_PLAYER, ENTITY_STATISTIC),
        base_weight=1.2,
        priority=24,
    ),
    IntentRule(
        NLU_TASK_TEAM_STATS,
        "team_stats_handler",
        phrases=("team stats", "team record", "what is their record", "runs per game", "team statistics"),
        required_any=("stats", "record", "runs per game", "win percentage"),
        entity_bonus=(ENTITY_TEAM, ENTITY_STATISTIC),
        base_weight=1.2,
        priority=25,
    ),
    IntentRule(
        NLU_TASK_STANDINGS,
        "standings_handler",
        phrases=("standings", "division standings", "league standings", "who is in first"),
        required_any=("standings", "first place", "division leader"),
        base_weight=1.3,
        priority=26,
    ),
    IntentRule(
        NLU_TASK_LEAGUE_LEADERS,
        "league_leaders_handler",
        phrases=("league leaders", "who leads", "home run leaders", "batting leaders", "top players"),
        required_any=("leaders", "who leads", "top"),
        base_weight=1.2,
        priority=27,
    ),
    IntentRule(
        NLU_TASK_GAME_LOOKUP,
        "game_lookup_handler",
        phrases=("game today", "games today", "tonights games", "game status", "score of"),
        required_any=("game", "games", "score"),
        base_weight=1.0,
        priority=28,
    ),
    IntentRule(
        NLU_TASK_PLAYER_LOOKUP,
        "player_lookup_handler",
        phrases=("find player", "show player", "tell me about", "who is"),
        entity_bonus=(ENTITY_PLAYER,),
        base_weight=0.8,
        priority=30,
    ),
    IntentRule(
        NLU_TASK_TEAM_LOOKUP,
        "team_lookup_handler",
        phrases=("show team", "tell me about the team", "team info", "team overview"),
        entity_bonus=(ENTITY_TEAM,),
        base_weight=0.8,
        priority=31,
    ),
    IntentRule(
        NLU_TASK_GREETING,
        "greeting_handler",
        phrases=("hello", "hi", "hey", "good morning", "good afternoon", "good evening"),
        base_weight=0.8,
        priority=90,
    ),
    IntentRule(
        NLU_TASK_GENERAL,
        "general_baseball_handler",
        base_weight=0.1,
        priority=999,
    ),
)

RULE_BY_INTENT: Final[dict[str, IntentRule]] = {rule.intent: rule for rule in INTENT_RULES}


# ============================================================
# SECTION 12 - ROUTING MAP
# ============================================================

ROUTING_TARGETS: Final[dict[str, str]] = {
    rule.intent: rule.routing_target for rule in INTENT_RULES
}
ROUTING_TARGETS.update({
    NLU_TASK_CLARIFICATION: "clarification_handler",
    NLU_TASK_UNSUPPORTED: "unsupported_handler",
    NLU_TASK_BEST_TEAM_PROBABILITY: "best_team_probability_handler",
    NLU_TASK_BEST_OVERALL_PROBABILITY: "best_overall_probability_handler",
})


# ============================================================
# SECTION 13 - GENERAL HELPERS
# ============================================================

def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    if isinstance(value, str):
        text = value.strip().replace("Z", "+00:00")
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))


def canonical_json(value: Any) -> str:
    def serializer(item: Any) -> Any:
        if isinstance(item, datetime):
            return item.isoformat()
        if isinstance(item, Enum):
            return item.value
        if is_dataclass(item):
            return asdict(item)
        if isinstance(item, set):
            return sorted(item)
        raise TypeError(type(item).__name__)

    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=serializer)


def fingerprint(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize_catalog_record(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump"):
        return dict(value.model_dump())
    if hasattr(value, "dict") and callable(value.dict):
        return dict(value.dict())
    if hasattr(value, "__dict__"):
        return {
            key: item for key, item in vars(value).items()
            if not key.startswith("_") and not callable(item)
        }
    return {"name": str(value)}


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def phrase_pattern(phrase: str) -> re.Pattern[str]:
    escaped = re.escape(phrase.strip())
    escaped = escaped.replace(r"\ ", r"\s+")
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)


def contains_phrase(message: str, phrase: str) -> bool:
    if not phrase:
        return False
    return bool(phrase_pattern(phrase).search(message))


def contains_any(message: str, phrases: Iterable[str]) -> bool:
    return any(contains_phrase(message, phrase) for phrase in phrases)


def token_overlap(left: str, right: str) -> float:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def confidence_band(value: float) -> ConfidenceBand:
    value = clamp(value)
    if value >= 0.90:
        return ConfidenceBand.VERY_HIGH
    if value >= 0.75:
        return ConfidenceBand.HIGH
    if value >= 0.55:
        return ConfidenceBand.MODERATE
    if value > 0:
        return ConfidenceBand.LOW
    return ConfidenceBand.NONE


# ============================================================
# SECTION 14 - MESSAGE NORMALIZATION
# ============================================================

def _replace_phrases(text: str, replacements: Mapping[str, str]) -> tuple[str, list[dict[str, Any]]]:
    corrections: list[dict[str, Any]] = []
    output = text
    for source in sorted(replacements, key=len, reverse=True):
        target = replacements[source]
        pattern = phrase_pattern(source)
        if pattern.search(output):
            output = pattern.sub(target, output)
            corrections.append({"source": source, "target": target, "type": "phrase"})
    return output, corrections


def normalize_nlu_text(value: str | None) -> str:
    if value is None:
        return ""
    text = strip_accents(str(value)).lower().strip()
    text = text.replace("'", "'").replace("`", "'")
    text = re.sub(r"[^a-z0-9+.%'\-/\s]", " ", text)
    text = text.replace("/", " ").replace("_", " ")
    text, _ = _replace_phrases(text, PHRASE_REPLACEMENTS)
    tokens: list[str] = []
    for raw_token in collapse_spaces(text).split():
        token = raw_token.strip(".,!?;:\"'()[]{}")
        replacement = DIRECT_TOKEN_REPLACEMENTS.get(token)
        if replacement:
            tokens.extend(replacement.split())
        elif token:
            tokens.append(token)
    normalized = collapse_spaces(" ".join(tokens))
    normalized, _ = _replace_phrases(normalized, PHRASE_REPLACEMENTS)
    return collapse_spaces(normalized)


def detect_nlu_question_type(message: str) -> str:
    cleaned = normalize_nlu_text(message)
    if cleaned.startswith("who"):
        return "who_question"
    if cleaned.startswith("what"):
        return "what_question"
    if cleaned.startswith("which"):
        return "which_question"
    if cleaned.startswith("when"):
        return "when_question"
    if cleaned.startswith("where"):
        return "where_question"
    if cleaned.startswith("why"):
        return "why_question"
    if cleaned.startswith("how many") or cleaned.startswith("how much"):
        return "quantity_question"
    if cleaned.startswith("how"):
        return "how_question"
    if cleaned.startswith(("can", "will", "does", "is", "are", "should")):
        return "yes_no_or_probability_question"
    return "statement_or_command"


def build_normalized_message(message: str | None, request_id: str | None = None) -> NormalizedMessage:
    original = "" if message is None else str(message)
    request_id = request_id or str(uuid4())
    normalized = normalize_nlu_text(original)
    corrections: list[dict[str, Any]] = []

    raw_lower = strip_accents(original).lower()
    for source, target in PHRASE_REPLACEMENTS.items():
        if contains_phrase(raw_lower, source):
            corrections.append({"source": source, "target": target, "type": "phrase"})
    for token in collapse_spaces(raw_lower).split():
        cleaned_token = token.strip(".,!?;:\"'()[]{}")
        if cleaned_token in DIRECT_TOKEN_REPLACEMENTS:
            corrections.append({
                "source": cleaned_token,
                "target": DIRECT_TOKEN_REPLACEMENTS[cleaned_token],
                "type": "token",
            })

    tokens = normalized.split() if normalized else []
    return NormalizedMessage(
        request_id=request_id,
        original=original,
        normalized=normalized,
        tokens=tokens,
        token_set=set(tokens),
        question_type=detect_nlu_question_type(normalized),
        is_empty=not bool(normalized),
        corrections=corrections,
    )


def build_language_normalization_report(original_message: str) -> dict[str, Any]:
    normalized = build_normalized_message(original_message)
    return {
        "original_message": normalized.original,
        "normalized_message": normalized.normalized,
        "changed": normalize_nlu_text(normalized.original) != normalized.original.strip().lower(),
        "corrections": normalized.corrections,
        "question_type": normalized.question_type,
        "engine": NLU_ENGINE_NAME,
        "engine_version": NLU_ENGINE_VERSION,
    }


def nlu_contains_any(message: str, phrases: Sequence[str]) -> bool:
    normalized = normalize_nlu_text(message)
    return contains_any(normalized, [normalize_nlu_text(item) for item in phrases])


# ============================================================
# SECTION 15 - CATALOG NORMALIZATION
# ============================================================

def _catalog_items(catalog: Any) -> list[dict[str, Any]]:
    if catalog is None:
        return []
    if isinstance(catalog, Mapping):
        items: list[dict[str, Any]] = []
        for key, value in catalog.items():
            record = normalize_catalog_record(value)
            record.setdefault("name", str(key))
            items.append(record)
        return items
    if isinstance(catalog, (str, bytes)):
        return [{"name": str(catalog)}]
    if isinstance(catalog, Iterable):
        return [normalize_catalog_record(item) for item in catalog]
    return [normalize_catalog_record(catalog)]


def normalize_player_catalog(catalog: Any) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for record in _catalog_items(catalog):
        name = (
            record.get("full_name")
            or record.get("player_name")
            or record.get("name")
            or record.get("display_name")
        )
        if not name:
            continue
        aliases = record.get("aliases") or record.get("nicknames") or []
        if isinstance(aliases, str):
            aliases = [aliases]
        output.append({
            "id": record.get("player_id") or record.get("mlb_id") or record.get("id"),
            "name": str(name),
            "normalized_name": normalize_nlu_text(str(name)),
            "aliases": [normalize_nlu_text(str(alias)) for alias in aliases if alias],
            "team_id": record.get("team_id"),
            "team_name": record.get("team_name") or record.get("team"),
            "position": record.get("position") or record.get("primary_position"),
            "raw": record,
        })
    return output


def normalize_team_catalog(catalog: Any) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for record in _catalog_items(catalog):
        name = record.get("team_name") or record.get("name") or record.get("full_name")
        if not name:
            continue
        aliases = record.get("aliases") or []
        if isinstance(aliases, str):
            aliases = [aliases]
        abbreviation = record.get("abbreviation") or record.get("abbr") or record.get("team_code")
        city = record.get("city") or record.get("location_name")
        nickname = record.get("nickname") or record.get("club_name")
        candidate_aliases = list(aliases)
        candidate_aliases.extend(item for item in (abbreviation, city, nickname) if item)
        output.append({
            "id": record.get("team_id") or record.get("mlb_id") or record.get("id"),
            "name": str(name),
            "normalized_name": normalize_nlu_text(str(name)),
            "aliases": [normalize_nlu_text(str(alias)) for alias in candidate_aliases if alias],
            "abbreviation": abbreviation,
            "raw": record,
        })
    return output


# ============================================================
# SECTION 16 - BUILT-IN MLB TEAM CATALOG
# ============================================================

BUILTIN_MLB_TEAMS: Final[tuple[tuple[str, str, tuple[str, ...]], ...]] = (
    ("Arizona Diamondbacks", "ARI", ("diamondbacks", "dbacks", "d backs", "arizona")),
    ("Atlanta Braves", "ATL", ("braves", "atlanta")),
    ("Baltimore Orioles", "BAL", ("orioles", "os", "o's", "baltimore")),
    ("Boston Red Sox", "BOS", ("red sox", "sox", "boston")),
    ("Chicago Cubs", "CHC", ("cubs", "north siders")),
    ("Chicago White Sox", "CWS", ("white sox", "chisox", "south siders")),
    ("Cincinnati Reds", "CIN", ("reds", "cincinnati")),
    ("Cleveland Guardians", "CLE", ("guardians", "cleveland")),
    ("Colorado Rockies", "COL", ("rockies", "colorado")),
    ("Detroit Tigers", "DET", ("tigers", "detroit")),
    ("Houston Astros", "HOU", ("astros", "houston")),
    ("Kansas City Royals", "KC", ("royals", "kansas city", "kcr")),
    ("Los Angeles Angels", "LAA", ("angels", "la angels", "anaheim")),
    ("Los Angeles Dodgers", "LAD", ("dodgers", "la dodgers")),
    ("Miami Marlins", "MIA", ("marlins", "miami")),
    ("Milwaukee Brewers", "MIL", ("brewers", "milwaukee")),
    ("Minnesota Twins", "MIN", ("twins", "minnesota")),
    ("New York Mets", "NYM", ("mets", "ny mets")),
    ("New York Yankees", "NYY", ("yankees", "yanks", "bronx bombers", "ny yanks")),
    ("Athletics", "ATH", ("athletics", "as", "a's", "oakland athletics")),
    ("Philadelphia Phillies", "PHI", ("phillies", "phils", "philadelphia")),
    ("Pittsburgh Pirates", "PIT", ("pirates", "bucs", "pittsburgh")),
    ("San Diego Padres", "SD", ("padres", "san diego")),
    ("San Francisco Giants", "SF", ("giants", "san francisco", "sfg")),
    ("Seattle Mariners", "SEA", ("mariners", "seattle", "ms", "m's")),
    ("St. Louis Cardinals", "STL", ("cardinals", "cards", "st louis", "saint louis")),
    ("Tampa Bay Rays", "TB", ("rays", "tampa bay", "tampa", "tbr")),
    ("Texas Rangers", "TEX", ("rangers", "texas")),
    ("Toronto Blue Jays", "TOR", ("blue jays", "jays", "toronto")),
    ("Washington Nationals", "WSH", ("nationals", "nats", "washington")),
)


def builtin_team_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": None,
            "name": name,
            "normalized_name": normalize_nlu_text(name),
            "aliases": [normalize_nlu_text(alias) for alias in aliases] + [abbreviation.lower()],
            "abbreviation": abbreviation,
            "raw": {},
        }
        for name, abbreviation, aliases in BUILTIN_MLB_TEAMS
    ]


# ============================================================
# SECTION 17 - ENTITY MATCHING
# ============================================================

def _exact_catalog_matches(
    normalized_message: str,
    catalog: Sequence[Mapping[str, Any]],
    entity_type: str,
) -> list[ResolvedEntity]:
    matches: list[ResolvedEntity] = []
    for record in catalog:
        canonical = str(record.get("name") or "")
        normalized_name = str(record.get("normalized_name") or normalize_nlu_text(canonical))
        aliases = [str(alias) for alias in record.get("aliases") or []]
        candidates = [(normalized_name, EntitySource.CURRENT_EXACT, 0.99)]
        candidates.extend((alias, EntitySource.CURRENT_ALIAS, 0.93) for alias in aliases)
        best: ResolvedEntity | None = None
        for candidate, source, confidence in candidates:
            if candidate and contains_phrase(normalized_message, candidate):
                entity = ResolvedEntity(
                    entity_type=entity_type,
                    canonical_name=canonical,
                    entity_id=record.get("id"),
                    matched_text=candidate,
                    confidence=confidence,
                    source=source,
                    metadata={
                        "team_id": record.get("team_id"),
                        "team_name": record.get("team_name"),
                        "position": record.get("position"),
                        "abbreviation": record.get("abbreviation"),
                    },
                )
                if best is None or entity.confidence > best.confidence:
                    best = entity
        if best is not None:
            matches.append(best)
    matches.sort(key=lambda item: (item.confidence, len(item.matched_text or "")), reverse=True)
    return matches


def _candidate_name_phrases(message: NormalizedMessage, max_tokens: int = 4) -> list[str]:
    stop_words = {
        "show", "find", "search", "tell", "about", "predict", "probability", "chance",
        "stats", "statistics", "team", "player", "mlb", "baseball", "what", "who",
        "is", "are", "the", "a", "an", "for", "of", "on", "in", "please", "me",
    }
    tokens = [token for token in message.tokens if token not in stop_words]
    phrases: list[str] = []
    for size in range(min(max_tokens, len(tokens)), 0, -1):
        for index in range(0, len(tokens) - size + 1):
            phrase = " ".join(tokens[index:index + size])
            if phrase and phrase not in phrases:
                phrases.append(phrase)
    return phrases


def _sequence_similarity(left: str, right: str) -> float:
    # Local implementation avoids hard dependency on fuzzy_matching.py.
    from difflib import SequenceMatcher
    if not left or not right:
        return 0.0
    exact = SequenceMatcher(None, left, right).ratio()
    overlap = token_overlap(left, right)
    prefix = 1.0 if left.startswith(right) or right.startswith(left) else 0.0
    return 0.68 * exact + 0.24 * overlap + 0.08 * prefix


def _fuzzy_catalog_matches(
    message: NormalizedMessage,
    catalog: Sequence[Mapping[str, Any]],
    entity_type: str,
    threshold: float,
    limit: int,
) -> list[ResolvedEntity]:
    phrases = _candidate_name_phrases(message)
    scored: list[ResolvedEntity] = []
    for record in catalog:
        canonical = str(record.get("name") or "")
        candidate_values = [str(record.get("normalized_name") or normalize_nlu_text(canonical))]
        candidate_values.extend(str(alias) for alias in record.get("aliases") or [])
        best_score = 0.0
        best_phrase: str | None = None
        best_candidate: str | None = None
        for observed in phrases:
            for candidate in candidate_values:
                score = _sequence_similarity(observed, candidate)
                if score > best_score:
                    best_score = score
                    best_phrase = observed
                    best_candidate = candidate
        if best_score >= threshold:
            scored.append(ResolvedEntity(
                entity_type=entity_type,
                canonical_name=canonical,
                entity_id=record.get("id"),
                matched_text=best_phrase,
                confidence=best_score,
                source=EntitySource.CURRENT_FUZZY,
                metadata={
                    "matched_candidate": best_candidate,
                    "team_id": record.get("team_id"),
                    "team_name": record.get("team_name"),
                    "position": record.get("position"),
                    "abbreviation": record.get("abbreviation"),
                },
            ))
    scored.sort(key=lambda item: item.confidence, reverse=True)
    return scored[:limit]


def detect_statistic(message: str) -> ResolvedEntity | None:
    normalized = normalize_nlu_text(message)
    matches: list[tuple[int, str, str]] = []
    for statistic, aliases in STAT_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_nlu_text(alias)
            if contains_phrase(normalized, normalized_alias):
                matches.append((len(normalized_alias.split()), statistic, normalized_alias))
    if not matches:
        return None
    matches.sort(reverse=True)
    _, statistic, matched = matches[0]
    return ResolvedEntity(
        entity_type=ENTITY_STATISTIC,
        canonical_name=statistic,
        matched_text=matched,
        confidence=0.96,
        source=EntitySource.CURRENT_ALIAS,
    )


def detect_nlu_outcome(message: str) -> str | None:
    entity = detect_outcome_entity(message)
    return entity.canonical_name if entity else None


def detect_outcome_entity(message: str) -> ResolvedEntity | None:
    normalized = normalize_nlu_text(message)
    matches: list[tuple[int, str, str]] = []
    for outcome, aliases in OUTCOME_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_nlu_text(alias)
            if contains_phrase(normalized, normalized_alias):
                matches.append((len(normalized_alias.split()), outcome, normalized_alias))
    if not matches:
        return None
    matches.sort(reverse=True)
    _, outcome, matched = matches[0]
    return ResolvedEntity(
        entity_type=ENTITY_OUTCOME,
        canonical_name=outcome,
        matched_text=matched,
        confidence=0.96,
        source=EntitySource.CURRENT_ALIAS,
    )


def detect_season(message: str) -> ResolvedEntity | None:
    normalized = normalize_nlu_text(message)
    match = re.search(r"\b(19\d{2}|20\d{2})\b", normalized)
    if not match:
        return None
    return ResolvedEntity(
        entity_type=ENTITY_SEASON,
        canonical_name=match.group(1),
        entity_id=int(match.group(1)),
        matched_text=match.group(1),
        confidence=0.99,
        source=EntitySource.CURRENT_EXACT,
    )


def detect_limit(message: str) -> ResolvedEntity | None:
    normalized = normalize_nlu_text(message)
    patterns = (
        r"\blast\s+(\d{1,3})\b",
        r"\btop\s+(\d{1,3})\b",
        r"\bshow\s+(\d{1,3})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            value = max(1, min(int(match.group(1)), 200))
            return ResolvedEntity(
                entity_type=ENTITY_LIMIT,
                canonical_name=str(value),
                entity_id=value,
                matched_text=match.group(0),
                confidence=0.98,
                source=EntitySource.CURRENT_EXACT,
            )
    word_numbers = {
        "five": 5, "ten": 10, "fifteen": 15, "twenty": 20, "thirty": 30,
    }
    for word, value in word_numbers.items():
        if contains_phrase(normalized, f"last {word}"):
            return ResolvedEntity(
                entity_type=ENTITY_LIMIT,
                canonical_name=str(value),
                entity_id=value,
                matched_text=f"last {word}",
                confidence=0.95,
                source=EntitySource.CURRENT_ALIAS,
            )
    return None


def detect_relative_date(message: str, now: datetime | None = None) -> ResolvedEntity | None:
    now = now or utc_now()
    normalized = normalize_nlu_text(message)
    date_value: date | None = None
    matched: str | None = None
    if contains_phrase(normalized, "today") or contains_phrase(normalized, "tonight"):
        date_value, matched = now.date(), "today" if "today" in normalized else "tonight"
    elif contains_phrase(normalized, "tomorrow"):
        date_value, matched = (now + timedelta(days=1)).date(), "tomorrow"
    elif contains_phrase(normalized, "yesterday"):
        date_value, matched = (now - timedelta(days=1)).date(), "yesterday"
    if date_value is None:
        return None
    return ResolvedEntity(
        entity_type=ENTITY_DATE,
        canonical_name=date_value.isoformat(),
        matched_text=matched,
        confidence=0.98,
        source=EntitySource.CURRENT_ALIAS,
    )


# ============================================================
# SECTION 18 - CONTEXT RESOLUTION
# ============================================================

def context_is_fresh(context: ConversationContext, config: NLUConfig) -> bool:
    if context.updated_at is None:
        return True
    age = utc_now() - context.updated_at
    return age.total_seconds() <= config.context_max_age_hours * 3600.0


def message_requests_context_reset(message: str) -> bool:
    return contains_any(normalize_nlu_text(message), RESET_CONTEXT_PHRASES)


def _has_player_pronoun(message: str) -> bool:
    normalized = normalize_nlu_text(message)
    return contains_any(normalized, PRONOUN_PLAYER_PHRASES)


def _has_team_pronoun(message: str) -> bool:
    normalized = normalize_nlu_text(message)
    return contains_any(normalized, PRONOUN_TEAM_PHRASES)


def resolve_context_entities(
    message: NormalizedMessage,
    explicit_players: list[ResolvedEntity],
    explicit_teams: list[ResolvedEntity],
    statistic: ResolvedEntity | None,
    outcome: ResolvedEntity | None,
    context: ConversationContext,
    config: NLUConfig,
) -> tuple[list[ResolvedEntity], list[ResolvedEntity], ResolvedEntity | None, ResolvedEntity | None, dict[str, Any]]:
    resolution = {
        "used": False,
        "player_from_context": False,
        "team_from_context": False,
        "statistic_from_context": False,
        "outcome_from_context": False,
        "reset": False,
        "reasons": [],
    }

    if message_requests_context_reset(message.normalized):
        resolution["reset"] = True
        resolution["reasons"].append("explicit_context_reset")
        return explicit_players, explicit_teams, statistic, outcome, resolution

    if not context_is_fresh(context, config):
        resolution["reasons"].append("context_expired")
        return explicit_players, explicit_teams, statistic, outcome, resolution

    players = list(explicit_players)
    teams = list(explicit_teams)

    # Explicit current entities always win. Context is only used when absent.
    if (
        not players
        and config.allow_context_pronoun_resolution
        and context.last_player_name
        and _has_player_pronoun(message.normalized)
    ):
        players.append(ResolvedEntity(
            entity_type=ENTITY_PLAYER,
            canonical_name=context.last_player_name,
            entity_id=context.last_player_id,
            matched_text="conversation pronoun",
            confidence=0.88,
            source=EntitySource.CONVERSATION_CONTEXT,
        ))
        resolution["used"] = True
        resolution["player_from_context"] = True
        resolution["reasons"].append("player_pronoun_resolved")

    if (
        not teams
        and config.allow_context_pronoun_resolution
        and context.last_team_name
        and _has_team_pronoun(message.normalized)
    ):
        teams.append(ResolvedEntity(
            entity_type=ENTITY_TEAM,
            canonical_name=context.last_team_name,
            entity_id=context.last_team_id,
            matched_text="conversation pronoun",
            confidence=0.86,
            source=EntitySource.CONVERSATION_CONTEXT,
        ))
        resolution["used"] = True
        resolution["team_from_context"] = True
        resolution["reasons"].append("team_pronoun_resolved")

    # Elliptical follow-ups such as "what about home runs" may reuse only the
    # subject entity, never the prior intent itself.
    elliptical = message.question_type in {
        "what_question", "how_question", "quantity_question",
        "yes_no_or_probability_question",
    } or message.normalized.startswith(("and ", "also ", "what about ", "how about "))

    if config.allow_context_ellipsis_resolution and elliptical:
        if not players and not teams and context.last_player_name and (statistic or outcome):
            players.append(ResolvedEntity(
                entity_type=ENTITY_PLAYER,
                canonical_name=context.last_player_name,
                entity_id=context.last_player_id,
                matched_text="elliptical follow-up",
                confidence=0.80,
                source=EntitySource.CONVERSATION_CONTEXT,
            ))
            resolution["used"] = True
            resolution["player_from_context"] = True
            resolution["reasons"].append("player_ellipsis_resolved")
        elif not players and not teams and context.last_team_name and statistic:
            teams.append(ResolvedEntity(
                entity_type=ENTITY_TEAM,
                canonical_name=context.last_team_name,
                entity_id=context.last_team_id,
                matched_text="elliptical follow-up",
                confidence=0.78,
                source=EntitySource.CONVERSATION_CONTEXT,
            ))
            resolution["used"] = True
            resolution["team_from_context"] = True
            resolution["reasons"].append("team_ellipsis_resolved")

    if statistic is None and resolution["used"] and context.last_statistic and contains_any(
        message.normalized, ("that stat", "same stat", "it", "that number")
    ):
        statistic = ResolvedEntity(
            entity_type=ENTITY_STATISTIC,
            canonical_name=context.last_statistic,
            matched_text="conversation statistic",
            confidence=0.75,
            source=EntitySource.CONVERSATION_CONTEXT,
        )
        resolution["statistic_from_context"] = True
        resolution["reasons"].append("statistic_pronoun_resolved")

    if outcome is None and resolution["used"] and context.last_outcome and contains_any(
        message.normalized, ("that outcome", "same outcome", "do it again", "again")
    ):
        outcome = ResolvedEntity(
            entity_type=ENTITY_OUTCOME,
            canonical_name=context.last_outcome,
            matched_text="conversation outcome",
            confidence=0.72,
            source=EntitySource.CONVERSATION_CONTEXT,
        )
        resolution["outcome_from_context"] = True
        resolution["reasons"].append("outcome_ellipsis_resolved")

    return players, teams, statistic, outcome, resolution


# ============================================================
# SECTION 19 - INTENT SCORING
# ============================================================

def _entity_presence(
    players: Sequence[ResolvedEntity],
    teams: Sequence[ResolvedEntity],
    statistic: ResolvedEntity | None,
    outcome: ResolvedEntity | None,
    game_present: bool,
) -> set[str]:
    present: set[str] = set()
    if players:
        present.add(ENTITY_PLAYER)
    if teams:
        present.add(ENTITY_TEAM)
    if statistic:
        present.add(ENTITY_STATISTIC)
    if outcome:
        present.add(ENTITY_OUTCOME)
    if game_present:
        present.add(ENTITY_GAME)
    return present


def score_intent_rules(
    message: NormalizedMessage,
    players: Sequence[ResolvedEntity],
    teams: Sequence[ResolvedEntity],
    statistic: ResolvedEntity | None,
    outcome: ResolvedEntity | None,
    game_present: bool,
) -> list[IntentCandidate]:
    entity_presence = _entity_presence(players, teams, statistic, outcome, game_present)
    candidates: list[IntentCandidate] = []

    for rule in INTENT_RULES:
        score = rule.base_weight
        evidence: list[str] = []
        negative: list[str] = []

        for phrase in rule.phrases:
            normalized_phrase = normalize_nlu_text(phrase)
            if normalized_phrase and contains_phrase(message.normalized, normalized_phrase):
                token_weight = max(1.0, min(3.5, len(normalized_phrase.split()) * 0.65))
                score += rule.phrase_weight * token_weight
                evidence.append(f"phrase:{normalized_phrase}")

        for required in rule.required_any:
            normalized_required = normalize_nlu_text(required)
            if normalized_required and contains_phrase(message.normalized, normalized_required):
                score += 0.75
                evidence.append(f"required:{normalized_required}")

        for entity_type in rule.entity_bonus:
            if entity_type in entity_presence:
                score += 1.2
                evidence.append(f"entity:{entity_type}")

        for phrase in rule.negative_phrases:
            normalized_phrase = normalize_nlu_text(phrase)
            if normalized_phrase and contains_phrase(message.normalized, normalized_phrase):
                score -= 1.5
                negative.append(f"negative:{normalized_phrase}")

        # Structural bonuses and guards.
        if rule.intent == NLU_TASK_COMPARE_PLAYERS and len(players) >= 2:
            score += 3.5
            evidence.append("structure:multiple_players")
        if rule.intent == NLU_TASK_COMPARE_TEAMS and len(teams) >= 2:
            score += 3.5
            evidence.append("structure:multiple_teams")
        if rule.intent == NLU_TASK_PLAYER_PROBABILITY and players and outcome:
            score += 3.0
            evidence.append("structure:player_plus_outcome")
        if rule.intent == NLU_TASK_PLAYER_STATS and players and statistic:
            score += 3.0
            evidence.append("structure:player_plus_statistic")
        if rule.intent == NLU_TASK_TEAM_STATS and teams and statistic:
            score += 3.0
            evidence.append("structure:team_plus_statistic")
        if rule.intent == NLU_TASK_TEAM_ROSTER and teams and contains_any(message.normalized, ("roster", "lineup", "who is on", "who plays for")):
            score += 3.0
            evidence.append("structure:team_plus_roster_language")
        if rule.intent == NLU_TASK_TEAM_SCHEDULE and teams and contains_any(message.normalized, ("schedule", "next game", "when do", "upcoming")):
            score += 3.0
            evidence.append("structure:team_plus_schedule_language")
        if rule.intent == NLU_TASK_PLAYER_LOOKUP and len(players) == 1 and not statistic and not outcome:
            score += 1.8
            evidence.append("structure:single_player_lookup")
        if rule.intent == NLU_TASK_TEAM_LOOKUP and len(teams) == 1 and not statistic and not outcome:
            score += 1.8
            evidence.append("structure:single_team_lookup")
        if rule.intent == NLU_TASK_GAME_PREDICTION and len(teams) >= 2 and contains_any(message.normalized, ("win", "predict", "probability")):
            score += 3.2
            evidence.append("structure:two_team_game_prediction")
        if rule.intent == NLU_TASK_GAME_LOOKUP and game_present:
            score += 1.5
            evidence.append("structure:game_language")

        # Do not let generic player probability swallow simple stat questions.
        if rule.intent == NLU_TASK_PLAYER_PROBABILITY and statistic and not contains_any(
            message.normalized, ("predict", "probability", "chance", "likely", "odds", "will")
        ):
            score -= 2.5
            negative.append("guard:stat_without_prediction_language")

        # Team-list questions must not become player search merely because the
        # word "players" appears in explanatory text.
        if rule.intent in {NLU_TASK_PLAYER_LOOKUP, NLU_TASK_LIST_PLAYERS} and contains_any(
            message.normalized, ("all teams", "mlb teams", "team list", "list teams")
        ):
            score -= 3.0
            negative.append("guard:explicit_team_list")

        candidates.append(IntentCandidate(rule.intent, score, evidence, negative))

    candidates.sort(key=lambda item: (item.score, -RULE_BY_INTENT.get(item.intent, IntentRule(item.intent, "", priority=999)).priority), reverse=True)
    return candidates


def _normalize_candidate_confidence(candidates: Sequence[IntentCandidate]) -> float:
    if not candidates:
        return 0.0
    top = candidates[0].score
    second = candidates[1].score if len(candidates) > 1 else 0.0
    if top <= 0:
        return 0.0
    margin = max(top - second, 0.0)
    magnitude = 1.0 - math.exp(-max(top, 0.0) / 5.0)
    separation = 1.0 - math.exp(-margin / 2.5)
    return clamp(0.55 * magnitude + 0.45 * separation)


def _select_intent(candidates: Sequence[IntentCandidate]) -> tuple[str, float]:
    if not candidates:
        return NLU_TASK_GENERAL, 0.0
    selected = candidates[0]
    return selected.intent, _normalize_candidate_confidence(candidates)


# ============================================================
# SECTION 20 - SCOPE DETECTION
# ============================================================

def detect_entity_scope(
    message: str,
    entity_report: Mapping[str, Any] | None = None,
    *,
    players: Sequence[ResolvedEntity] | None = None,
    teams: Sequence[ResolvedEntity] | None = None,
    intent: str | None = None,
) -> str:
    entity_report = entity_report or {}
    players = list(players or [])
    teams = list(teams or [])

    if not players:
        for item in entity_report.get("players", []) or []:
            players.append(ResolvedEntity(
                entity_type=ENTITY_PLAYER,
                canonical_name=item.get("canonical_name") or item.get("name"),
            ))
    if not teams:
        for item in entity_report.get("teams", []) or []:
            teams.append(ResolvedEntity(
                entity_type=ENTITY_TEAM,
                canonical_name=item.get("canonical_name") or item.get("name"),
            ))

    normalized = normalize_nlu_text(message)
    if intent in {NLU_TASK_DATABASE_STATUS, NLU_TASK_WAREHOUSE_STATUS, NLU_TASK_MODEL_STATUS, NLU_TASK_DATA_FRESHNESS}:
        return NLU_SCOPE_SYSTEM
    if len(players) >= 2:
        return NLU_SCOPE_MULTIPLE_PLAYERS
    if len(teams) >= 2:
        return NLU_SCOPE_MULTIPLE_TEAMS
    if players:
        return NLU_SCOPE_SINGLE_PLAYER
    if teams:
        if intent == NLU_TASK_TEAM_ROSTER:
            return NLU_SCOPE_TEAM_PLAYERS
        return NLU_SCOPE_TEAM
    if intent in {NLU_TASK_LIST_PLAYERS, NLU_TASK_BEST_OVERALL_PROBABILITY, NLU_TASK_LEAGUE_LEADERS}:
        return NLU_SCOPE_ALL_PLAYERS
    if intent in {NLU_TASK_LIST_TEAMS, NLU_TASK_STANDINGS}:
        return NLU_SCOPE_ALL_TEAMS
    if intent in {NLU_TASK_GAME_LOOKUP, NLU_TASK_GAME_PREDICTION} or contains_any(normalized, ("game", "games", "matchup")):
        return NLU_SCOPE_GAME
    if contains_any(normalized, ("mlb", "league", "baseball")):
        return NLU_SCOPE_LEAGUE
    return NLU_SCOPE_UNKNOWN


# ============================================================
# SECTION 21 - MISSING INFORMATION AND CLARIFICATION
# ============================================================

def detect_missing_information(
    task: str,
    entity_report: Mapping[str, Any] | None = None,
    outcome: str | None = None,
    *,
    players: Sequence[ResolvedEntity] | None = None,
    teams: Sequence[ResolvedEntity] | None = None,
    statistic: ResolvedEntity | None = None,
) -> dict[str, bool]:
    entity_report = entity_report or {}
    players = list(players or [])
    teams = list(teams or [])
    has_player = bool(players) or bool(entity_report.get("has_player"))
    has_team = bool(teams) or bool(entity_report.get("has_team"))
    return {
        "missing_player": task in {
            NLU_TASK_PLAYER_LOOKUP,
            NLU_TASK_PLAYER_STATS,
            NLU_TASK_PLAYER_GAME_LOG,
            NLU_TASK_PLAYER_SPLITS,
            NLU_TASK_PLAYER_PROBABILITY,
        } and not has_player,
        "missing_team": task in {
            NLU_TASK_TEAM_LOOKUP,
            NLU_TASK_TEAM_STATS,
            NLU_TASK_TEAM_ROSTER,
            NLU_TASK_TEAM_SCHEDULE,
            NLU_TASK_TEAM_PREDICTION,
            NLU_TASK_BEST_TEAM_PROBABILITY,
        } and not has_team,
        "missing_outcome": task in {
            NLU_TASK_PLAYER_PROBABILITY,
            NLU_TASK_BEST_TEAM_PROBABILITY,
            NLU_TASK_BEST_OVERALL_PROBABILITY,
        } and not outcome,
        "missing_statistic": task in {NLU_TASK_PLAYER_STATS, NLU_TASK_TEAM_STATS} and statistic is None,
    }


def determine_clarification(
    message: NormalizedMessage,
    intent: str,
    confidence: float,
    candidates: Sequence[IntentCandidate],
    players: Sequence[ResolvedEntity],
    teams: Sequence[ResolvedEntity],
    missing: Mapping[str, bool],
    config: NLUConfig,
) -> tuple[bool, ClarificationReason, str | None]:
    if message.is_empty:
        return True, ClarificationReason.EMPTY_MESSAGE, "Please enter a baseball question."

    if len(players) >= 2 and intent not in {NLU_TASK_COMPARE_PLAYERS}:
        top = players[0].confidence
        second = players[1].confidence
        if abs(top - second) <= config.ambiguity_margin:
            names = ", ".join(item.canonical_name or "Unknown" for item in players[:4])
            return True, ClarificationReason.AMBIGUOUS_PLAYER, f"I found multiple possible players: {names}. Which one did you mean?"

    if len(teams) >= 2 and intent not in {NLU_TASK_COMPARE_TEAMS, NLU_TASK_GAME_PREDICTION}:
        top = teams[0].confidence
        second = teams[1].confidence
        if abs(top - second) <= config.ambiguity_margin:
            names = ", ".join(item.canonical_name or "Unknown" for item in teams[:4])
            return True, ClarificationReason.AMBIGUOUS_TEAM, f"I found multiple possible teams: {names}. Which one did you mean?"

    if missing.get("missing_player"):
        return True, ClarificationReason.MISSING_PLAYER, "Which player would you like me to analyze?"
    if missing.get("missing_team"):
        return True, ClarificationReason.MISSING_TEAM, "Which MLB team would you like me to use?"
    if missing.get("missing_outcome"):
        return True, ClarificationReason.MISSING_OUTCOME, "Which outcome should I project: hit, home run, walk, strikeout, RBI, run, or total bases?"
    if missing.get("missing_statistic"):
        return True, ClarificationReason.MISSING_STATISTIC, "Which statistic would you like: AVG, OBP, SLG, OPS, home runs, hits, ERA, WHIP, or another metric?"

    if len(candidates) >= 2:
        margin = candidates[0].score - candidates[1].score
        if confidence < config.clarification_confidence and margin <= config.ambiguity_margin:
            return True, ClarificationReason.AMBIGUOUS_INTENT, "I can help with player stats, team information, schedules, rosters, or predictions. Which did you mean?"

    if intent == NLU_TASK_UNSUPPORTED:
        return True, ClarificationReason.UNSUPPORTED_REQUEST, "I could not map that request to a supported baseball action."

    return False, ClarificationReason.NONE, None


# ============================================================
# SECTION 22 - EXTERNAL ENGINE COORDINATION
# ============================================================

def _safe_external_entity_report(message: str, players: Sequence[Mapping[str, Any]], config: NLUConfig) -> dict[str, Any]:
    if not config.enable_external_entity_engine or _external_entity_report is None:
        return {}
    try:
        player_profiles = {str(item.get("name")): item for item in players if item.get("name")}
        result = _external_entity_report(message, player_profiles=player_profiles)
        return dict(result or {})
    except Exception as exc:
        LOGGER.debug("External entity engine failed: %s", exc)
        return {"error": str(exc)}


def _safe_external_fuzzy_report(message: str, players: Sequence[Mapping[str, Any]], teams: Sequence[Mapping[str, Any]], config: NLUConfig) -> dict[str, Any]:
    if not config.enable_external_fuzzy_engine or _external_fuzzy_report is None:
        return {}
    try:
        result = _external_fuzzy_report(
            message=message,
            player_names=[str(item.get("name")) for item in players if item.get("name")],
            team_names=[str(item.get("name")) for item in teams if item.get("name")],
        )
        return dict(result or {})
    except Exception as exc:
        LOGGER.debug("External fuzzy engine failed: %s", exc)
        return {"error": str(exc)}


def _safe_external_semantic_report(message: str, players: Sequence[Mapping[str, Any]], teams: Sequence[Mapping[str, Any]], config: NLUConfig) -> dict[str, Any]:
    if not config.enable_external_semantic_engine or _external_semantic_report is None:
        return {}
    try:
        player_profiles = {str(item.get("name")): item for item in players if item.get("name")}
        team_profiles = {
            str(item.get("name")): {
                "abbreviation": item.get("abbreviation"),
                **dict(item.get("raw") or {}),
            }
            for item in teams if item.get("name")
        }
        result = _external_semantic_report(message, team_profiles, player_profiles)
        return dict(result or {})
    except Exception as exc:
        LOGGER.debug("External semantic engine failed: %s", exc)
        return {"error": str(exc)}


def _safe_external_intent_report(
    message: str,
    players: Sequence[ResolvedEntity],
    teams: Sequence[ResolvedEntity],
    outcome: ResolvedEntity | None,
    config: NLUConfig,
) -> dict[str, Any]:
    if not config.enable_external_intent_engine or _external_intent_report is None:
        return {}
    try:
        result = _external_intent_report(
            message=message,
            detected_player=players[0].canonical_name if players else None,
            detected_team=teams[0].canonical_name if teams else None,
            detected_outcome=outcome.canonical_name if outcome else None,
            detected_players=[item.canonical_name for item in players if item.canonical_name],
            detected_teams=[item.canonical_name for item in teams if item.canonical_name],
        )
        return dict(result or {})
    except Exception as exc:
        LOGGER.debug("External intent engine failed: %s", exc)
        return {"error": str(exc)}


# ============================================================
# SECTION 23 - CONTEXT UPDATE POLICY
# ============================================================

def build_next_context(
    previous: ConversationContext,
    intent: str,
    players: Sequence[ResolvedEntity],
    teams: Sequence[ResolvedEntity],
    statistic: ResolvedEntity | None,
    outcome: ResolvedEntity | None,
    clarification_required: bool,
    reset: bool,
) -> ConversationContext:
    if reset:
        previous = ConversationContext()

    # Never save an unresolved or failed parse as authoritative context.
    if clarification_required:
        return previous

    next_context = ConversationContext.from_any(previous.to_dict())
    if players:
        next_context.last_player_id = players[0].entity_id
        next_context.last_player_name = players[0].canonical_name
        # A newly named player changes the active subject; stale game context
        # may no longer apply.
        if players[0].source != EntitySource.CONVERSATION_CONTEXT:
            next_context.last_game_id = None
            next_context.last_game_label = None
    if teams:
        next_context.last_team_id = teams[0].entity_id
        next_context.last_team_name = teams[0].canonical_name
    if statistic:
        next_context.last_statistic = statistic.canonical_name
    if outcome:
        next_context.last_outcome = outcome.canonical_name
    next_context.last_intent = intent
    next_context.updated_at = utc_now()
    return next_context


# ============================================================
# SECTION 24 - PRIMARY ENTERPRISE NLU ENGINE
# ============================================================

class BaseballNLUEngine:
    """Primary stateless-per-request NLU orchestration service."""

    def __init__(self, config: NLUConfig | None = None) -> None:
        self.config = config or NLUConfig()
        self.config.validate()

    def understand(
        self,
        message: str | None,
        *,
        player_catalog: Any = None,
        team_catalog: Any = None,
        conversation_context: Any = None,
        request_id: str | None = None,
    ) -> NLUReport:
        started = utc_now()
        normalized_message = build_normalized_message(message, request_id=request_id)
        context = ConversationContext.from_any(conversation_context)

        players_catalog = normalize_player_catalog(player_catalog)
        teams_catalog = normalize_team_catalog(team_catalog)
        if not teams_catalog:
            teams_catalog = builtin_team_catalog()

        # Every request starts from the current message. No previous intent is
        # passed into scoring or classification.
        exact_players = _exact_catalog_matches(normalized_message.normalized, players_catalog, ENTITY_PLAYER)
        exact_teams = _exact_catalog_matches(normalized_message.normalized, teams_catalog, ENTITY_TEAM)

        players = exact_players
        teams = exact_teams

        if not players and players_catalog:
            players = _fuzzy_catalog_matches(
                normalized_message,
                players_catalog,
                ENTITY_PLAYER,
                self.config.fuzzy_threshold,
                self.config.max_catalog_candidates,
            )
        if not teams:
            teams = _fuzzy_catalog_matches(
                normalized_message,
                teams_catalog,
                ENTITY_TEAM,
                self.config.fuzzy_threshold,
                self.config.max_catalog_candidates,
            )

        statistic = detect_statistic(normalized_message.normalized)
        outcome = detect_outcome_entity(normalized_message.normalized)
        season = detect_season(normalized_message.normalized)
        limit = detect_limit(normalized_message.normalized)
        relative_date = detect_relative_date(normalized_message.normalized)

        players, teams, statistic, outcome, context_resolution = resolve_context_entities(
            normalized_message,
            players,
            teams,
            statistic,
            outcome,
            context,
            self.config,
        )

        game_present = contains_any(
            normalized_message.normalized,
            ("game", "games", "matchup", "score", "today", "tonight", "tomorrow"),
        )

        candidates = score_intent_rules(
            normalized_message,
            players,
            teams,
            statistic,
            outcome,
            game_present,
        )
        intent, confidence = _select_intent(candidates)

        # Deterministic post-selection rules handle structures that are clearer
        # than generic phrase scores.
        if len(players) >= 2 and contains_any(normalized_message.normalized, ("compare", "versus", "vs", "between", "better")):
            intent = NLU_TASK_COMPARE_PLAYERS
            confidence = max(confidence, 0.94)
        elif len(teams) >= 2 and contains_any(normalized_message.normalized, ("compare", "versus", "vs", "who wins", "predict", "probability")):
            intent = NLU_TASK_GAME_PREDICTION if contains_any(normalized_message.normalized, ("who wins", "predict", "probability")) else NLU_TASK_COMPARE_TEAMS
            confidence = max(confidence, 0.93)
        elif players and outcome and contains_any(normalized_message.normalized, ("predict", "probability", "chance", "likely", "will", "odds", "projection")):
            intent = NLU_TASK_PLAYER_PROBABILITY
            confidence = max(confidence, 0.94)
        elif players and statistic and not contains_any(normalized_message.normalized, ("predict", "probability", "chance", "likely", "will", "odds")):
            intent = NLU_TASK_PLAYER_STATS
            confidence = max(confidence, 0.91)
        elif teams and statistic and not contains_any(normalized_message.normalized, ("predict", "probability", "chance", "likely", "will", "odds")):
            intent = NLU_TASK_TEAM_STATS
            confidence = max(confidence, 0.90)
        elif players and intent == NLU_TASK_GENERAL:
            intent = NLU_TASK_PLAYER_LOOKUP
            confidence = max(confidence, 0.78)
        elif teams and intent == NLU_TASK_GENERAL:
            intent = NLU_TASK_TEAM_LOOKUP
            confidence = max(confidence, 0.76)

        scope = detect_entity_scope(
            normalized_message.normalized,
            players=players,
            teams=teams,
            intent=intent,
        )

        missing = detect_missing_information(
            intent,
            outcome=outcome.canonical_name if outcome else None,
            players=players,
            teams=teams,
            statistic=statistic,
        )

        clarification_required, clarification_reason, clarification_prompt = determine_clarification(
            normalized_message,
            intent,
            confidence,
            candidates,
            players,
            teams,
            missing,
            self.config,
        )

        if clarification_required:
            routing_target = ROUTING_TARGETS[NLU_TASK_CLARIFICATION]
        else:
            routing_target = ROUTING_TARGETS.get(intent, "general_baseball_handler")

        external_entity = _safe_external_entity_report(normalized_message.normalized, players_catalog, self.config)
        external_fuzzy = _safe_external_fuzzy_report(normalized_message.normalized, players_catalog, teams_catalog, self.config)
        external_semantic = _safe_external_semantic_report(normalized_message.normalized, players_catalog, teams_catalog, self.config)
        external_intent = _safe_external_intent_report(normalized_message.normalized, players, teams, outcome, self.config)

        next_context = build_next_context(
            context,
            intent,
            players,
            teams,
            statistic,
            outcome,
            clarification_required,
            bool(context_resolution.get("reset")),
        )

        entities_payload = {
            "player": players[0].to_dict() if players else None,
            "players": [item.to_dict() for item in players],
            "team": teams[0].to_dict() if teams else None,
            "teams": [item.to_dict() for item in teams],
            "statistic": statistic.to_dict() if statistic else None,
            "outcome": outcome.to_dict() if outcome else None,
            "season": season.to_dict() if season else None,
            "date": relative_date.to_dict() if relative_date else None,
            "limit": limit.to_dict() if limit else None,
        }

        elapsed_ms = (utc_now() - started).total_seconds() * 1000.0
        diagnostics = {
            "classification_policy": "current_message_first",
            "previous_intent_used_for_classification": False,
            "previous_intent": context.last_intent,
            "normalized_message": normalized_message.to_dict(),
            "catalog_counts": {
                "players": len(players_catalog),
                "teams": len(teams_catalog),
            },
            "candidate_count": len(candidates),
            "top_candidate_margin": round(
                candidates[0].score - candidates[1].score if len(candidates) > 1 else candidates[0].score if candidates else 0.0,
                4,
            ),
            "external_engines": {
                "entity": external_entity,
                "fuzzy": external_fuzzy,
                "semantic": external_semantic,
                "intent": external_intent,
            },
            "processing_time_ms": round(elapsed_ms, 3),
            "request_fingerprint": fingerprint({
                "message": normalized_message.normalized,
                "players": [item.canonical_name for item in players],
                "teams": [item.canonical_name for item in teams],
                "statistic": statistic.canonical_name if statistic else None,
                "outcome": outcome.canonical_name if outcome else None,
                "intent": intent,
            }),
        }

        return NLUReport(
            request_id=normalized_message.request_id,
            original_message=normalized_message.original,
            normalized_message=normalized_message.normalized,
            intent=intent,
            scope=scope,
            confidence=confidence,
            confidence_band=confidence_band(confidence),
            routing_target=routing_target,
            entities=entities_payload,
            intent_candidates=candidates[:10],
            context_used=bool(context_resolution.get("used")),
            context_resolution=context_resolution,
            clarification_required=clarification_required,
            clarification_reason=clarification_reason,
            clarification_prompt=clarification_prompt,
            missing=missing,
            diagnostics=diagnostics,
            next_context=next_context,
        )


# ============================================================
# SECTION 25 - PRIMARY PUBLIC FUNCTION
# ============================================================

def understand_baseball_message(
    message: str | None,
    *,
    player_catalog: Any = None,
    team_catalog: Any = None,
    conversation_context: Any = None,
    request_id: str | None = None,
    config: NLUConfig | None = None,
) -> dict[str, Any]:
    """Understand one message through a completely fresh classification cycle."""
    engine = BaseballNLUEngine(config=config)
    return engine.understand(
        message,
        player_catalog=player_catalog,
        team_catalog=team_catalog,
        conversation_context=conversation_context,
        request_id=request_id,
    ).to_dict()


# ============================================================
# SECTION 26 - BACKWARD-COMPATIBLE NLU REPORT API
# ============================================================

def build_nlu_report(
    message: str,
    entity_report: dict | None = None,
    *,
    player_catalog: Any = None,
    team_catalog: Any = None,
    conversation_context: Any = None,
) -> dict[str, Any]:
    """
    Backward-compatible report function.

    The legacy entity_report argument is accepted but never treated as the
    authoritative classifier. It may supplement catalogs when possible.
    """
    if entity_report:
        if player_catalog is None:
            player_catalog = [
                {
                    "name": item.get("canonical_name") or item.get("name"),
                    "id": item.get("entity_id") or item.get("id"),
                }
                for item in entity_report.get("players", []) or []
            ]
        if team_catalog is None:
            team_catalog = [
                {
                    "name": item.get("canonical_name") or item.get("name"),
                    "id": item.get("entity_id") or item.get("id"),
                }
                for item in entity_report.get("teams", []) or []
            ]
    return understand_baseball_message(
        message,
        player_catalog=player_catalog,
        team_catalog=team_catalog,
        conversation_context=conversation_context,
    )


def classify_nlu_task(
    message: str,
    entity_report: dict | None = None,
) -> str:
    return build_nlu_report(message, entity_report=entity_report)["intent"]


def detect_best_probability_goal(message: str) -> bool:
    normalized = normalize_nlu_text(message)
    return contains_any(normalized, (
        "highest probability",
        "best probability",
        "most likely",
        "who has the highest",
        "who is most likely",
    ))


def detect_list_goal(message: str) -> str | None:
    normalized = normalize_nlu_text(message)
    if contains_any(normalized, ("list teams", "show all teams", "all mlb teams", "what teams")):
        return NLU_TASK_LIST_TEAMS
    if contains_any(normalized, ("list players", "show all players", "all mlb players", "what players")):
        return NLU_TASK_LIST_PLAYERS
    return None


def detect_help_goal(message: str) -> bool:
    return contains_any(normalize_nlu_text(message), ("help", "what can you do", "how do i use", "sample questions"))


def detect_comparison_goal(message: str) -> str | None:
    normalized = normalize_nlu_text(message)
    if contains_any(normalized, ("compare", "versus", "vs", "who is better", "between")):
        return NLU_TASK_COMPARE_PLAYERS
    return None


def calculate_nlu_confidence(
    task: str,
    scope: str,
    outcome: str | None,
    entity_report: dict | None = None,
) -> int:
    confidence = 35
    if task != NLU_TASK_GENERAL:
        confidence += 25
    if scope != NLU_SCOPE_UNKNOWN:
        confidence += 15
    if outcome:
        confidence += 15
    entity_report = entity_report or {}
    if entity_report.get("has_team"):
        confidence += 10
    if entity_report.get("has_player"):
        confidence += 10
    return min(confidence, 96)


# ============================================================
# SECTION 27 - BATCH API
# ============================================================

def understand_message_batch(
    messages: Iterable[str],
    *,
    player_catalog: Any = None,
    team_catalog: Any = None,
    conversation_context: Any = None,
    config: NLUConfig | None = None,
) -> list[dict[str, Any]]:
    engine = BaseballNLUEngine(config=config)
    context = ConversationContext.from_any(conversation_context)
    reports: list[dict[str, Any]] = []
    for message in messages:
        report = engine.understand(
            message,
            player_catalog=player_catalog,
            team_catalog=team_catalog,
            conversation_context=context,
        )
        reports.append(report.to_dict())
        context = report.next_context
    return reports


# ============================================================
# SECTION 28 - VALIDATION TEST CASES
# ============================================================

VALIDATION_PLAYER_CATALOG: Final[list[dict[str, Any]]] = [
    {"id": 682998, "name": "Corbin Carroll", "team_name": "Arizona Diamondbacks", "position": "OF"},
    {"id": 592450, "name": "Aaron Judge", "team_name": "New York Yankees", "position": "OF"},
    {"id": 660271, "name": "Shohei Ohtani", "team_name": "Los Angeles Dodgers", "position": "DH"},
    {"id": 665742, "name": "Juan Soto", "team_name": "New York Mets", "position": "OF"},
]

VALIDATION_TEAM_CATALOG: Final[list[dict[str, Any]]] = [
    {"id": 109, "name": "Arizona Diamondbacks", "abbreviation": "ARI", "aliases": ["dbacks"]},
    {"id": 147, "name": "New York Yankees", "abbreviation": "NYY", "aliases": ["yankees", "yanks"]},
    {"id": 119, "name": "Los Angeles Dodgers", "abbreviation": "LAD", "aliases": ["dodgers"]},
    {"id": 121, "name": "New York Mets", "abbreviation": "NYM", "aliases": ["mets"]},
]


def validate_nlu_engine() -> dict[str, Any]:
    engine = BaseballNLUEngine(NLUConfig(
        enable_external_entity_engine=False,
        enable_external_intent_engine=False,
        enable_external_semantic_engine=False,
        enable_external_context_engine=False,
        enable_external_fuzzy_engine=False,
    ))

    cases = [
        ("show all mlb teams", NLU_TASK_LIST_TEAMS),
        ("find Corbin Carroll", NLU_TASK_PLAYER_LOOKUP),
        ("what is Corbin Carroll's OPS", NLU_TASK_PLAYER_STATS),
        ("predict Aaron Judge home run", NLU_TASK_PLAYER_PROBABILITY),
        ("show the Yankees roster", NLU_TASK_TEAM_ROSTER),
        ("when do the Mets play next", NLU_TASK_TEAM_SCHEDULE),
        ("is the database connected", NLU_TASK_DATABASE_STATUS),
        ("compare Aaron Judge and Shohei Ohtani", NLU_TASK_COMPARE_PLAYERS),
    ]

    results: list[dict[str, Any]] = []
    passed = 0
    for message, expected in cases:
        report = engine.understand(
            message,
            player_catalog=VALIDATION_PLAYER_CATALOG,
            team_catalog=VALIDATION_TEAM_CATALOG,
        )
        ok = report.intent == expected
        passed += int(ok)
        results.append({
            "message": message,
            "expected": expected,
            "actual": report.intent,
            "passed": ok,
            "confidence": report.confidence,
        })

    # Multi-turn subject switching test. Previous player must never override a
    # newly named player or a team question.
    first = engine.understand(
        "show Corbin Carroll",
        player_catalog=VALIDATION_PLAYER_CATALOG,
        team_catalog=VALIDATION_TEAM_CATALOG,
    )
    follow_up = engine.understand(
        "what is his OPS",
        player_catalog=VALIDATION_PLAYER_CATALOG,
        team_catalog=VALIDATION_TEAM_CATALOG,
        conversation_context=first.next_context,
    )
    switched = engine.understand(
        "predict Aaron Judge home run",
        player_catalog=VALIDATION_PLAYER_CATALOG,
        team_catalog=VALIDATION_TEAM_CATALOG,
        conversation_context=follow_up.next_context,
    )
    team_switch = engine.understand(
        "show all MLB teams",
        player_catalog=VALIDATION_PLAYER_CATALOG,
        team_catalog=VALIDATION_TEAM_CATALOG,
        conversation_context=switched.next_context,
    )

    context_tests = {
        "pronoun_resolved": (
            follow_up.entities["player"] is not None
            and follow_up.entities["player"]["canonical_name"] == "Corbin Carroll"
            and follow_up.intent == NLU_TASK_PLAYER_STATS
        ),
        "new_player_overrides_context": (
            switched.entities["player"] is not None
            and switched.entities["player"]["canonical_name"] == "Aaron Judge"
            and switched.intent == NLU_TASK_PLAYER_PROBABILITY
        ),
        "team_list_ignores_previous_player": team_switch.intent == NLU_TASK_LIST_TEAMS,
        "previous_intent_not_used": team_switch.diagnostics["previous_intent_used_for_classification"] is False,
    }

    total = len(cases) + len(context_tests)
    total_passed = passed + sum(bool(value) for value in context_tests.values())
    return {
        "status": "ok" if total_passed == total else "failed",
        "engine": NLU_ENGINE_NAME,
        "version": NLU_ENGINE_VERSION,
        "passed": total_passed,
        "total": total,
        "cases": results,
        "context_tests": context_tests,
    }


# ============================================================
# SECTION 29 - HEALTH REPORT
# ============================================================

def nlu_engine_health() -> dict[str, Any]:
    validation = validate_nlu_engine()
    return {
        "name": NLU_ENGINE_NAME,
        "version": NLU_ENGINE_VERSION,
        "phase": NLU_ENGINE_PHASE,
        "path": NLU_ENGINE_PATH,
        "status": NLU_ENGINE_STATUS if validation["status"] == "ok" else "validation_failed",
        "sqlalchemy_dependency": False,
        "database_model_code_present": False,
        "all_task_constants_defined": True,
        "independent_message_reclassification": True,
        "context_is_followup_only": True,
        "supported_tasks": list(SUPPORTED_TASKS),
        "supported_scopes": list(SUPPORTED_SCOPES),
        "external_engines_available": {
            "entity": _external_entity_report is not None,
            "intent": _external_intent_report is not None,
            "semantic": _external_semantic_report is not None,
            "context": _external_context_report is not None,
            "fuzzy": _external_fuzzy_report is not None,
        },
        "validation": validation,
        "timestamp": utc_now().isoformat(),
    }


# ============================================================
# SECTION 30 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "NLU_ENGINE_NAME",
    "NLU_ENGINE_VERSION",
    "NLU_ENGINE_PHASE",
    "NLU_ENGINE_PATH",
    "NLU_ENGINE_STATUS",
    "NLU_TASK_GENERAL",
    "NLU_TASK_GREETING",
    "NLU_TASK_HELP",
    "NLU_TASK_LIST_TEAMS",
    "NLU_TASK_LIST_PLAYERS",
    "NLU_TASK_TEAM_LOOKUP",
    "NLU_TASK_TEAM_STATS",
    "NLU_TASK_TEAM_ROSTER",
    "NLU_TASK_TEAM_SCHEDULE",
    "NLU_TASK_TEAM_PREDICTION",
    "NLU_TASK_PLAYER_LOOKUP",
    "NLU_TASK_PLAYER_STATS",
    "NLU_TASK_PLAYER_GAME_LOG",
    "NLU_TASK_PLAYER_SPLITS",
    "NLU_TASK_PLAYER_PROBABILITY",
    "NLU_TASK_COMPARE_PLAYERS",
    "NLU_TASK_COMPARE_TEAMS",
    "NLU_TASK_MATCHUP_ANALYSIS",
    "NLU_TASK_GAME_LOOKUP",
    "NLU_TASK_GAME_PREDICTION",
    "NLU_TASK_STANDINGS",
    "NLU_TASK_LEAGUE_LEADERS",
    "NLU_TASK_DATABASE_STATUS",
    "NLU_TASK_WAREHOUSE_STATUS",
    "NLU_TASK_DATA_FRESHNESS",
    "NLU_TASK_MODEL_STATUS",
    "NLU_TASK_EXPLAIN_MODEL",
    "NLU_TASK_CLARIFICATION",
    "NLU_TASK_UNSUPPORTED",
    "NLU_TASK_BEST_TEAM_PROBABILITY",
    "NLU_TASK_BEST_OVERALL_PROBABILITY",
    "NLU_TASK_ROSTER_LOOKUP",
    "NLU_SCOPE_UNKNOWN",
    "NLU_SCOPE_ALL_PLAYERS",
    "NLU_SCOPE_TEAM_PLAYERS",
    "NLU_SCOPE_SINGLE_PLAYER",
    "NLU_SCOPE_MULTIPLE_PLAYERS",
    "NLU_SCOPE_ALL_TEAMS",
    "NLU_SCOPE_TEAM",
    "NLU_SCOPE_MULTIPLE_TEAMS",
    "NLU_SCOPE_GAME",
    "NLU_SCOPE_LEAGUE",
    "NLU_SCOPE_SYSTEM",
    "ConfidenceBand",
    "EntitySource",
    "ClarificationReason",
    "NormalizedMessage",
    "ResolvedEntity",
    "ConversationContext",
    "IntentCandidate",
    "NLUReport",
    "NLUConfig",
    "BaseballNLUEngine",
    "normalize_nlu_text",
    "detect_nlu_question_type",
    "build_normalized_message",
    "build_language_normalization_report",
    "nlu_contains_any",
    "normalize_player_catalog",
    "normalize_team_catalog",
    "detect_statistic",
    "detect_nlu_outcome",
    "detect_outcome_entity",
    "detect_season",
    "detect_limit",
    "detect_relative_date",
    "detect_entity_scope",
    "detect_missing_information",
    "detect_best_probability_goal",
    "detect_list_goal",
    "detect_help_goal",
    "detect_comparison_goal",
    "calculate_nlu_confidence",
    "classify_nlu_task",
    "understand_baseball_message",
    "build_nlu_report",
    "understand_message_batch",
    "validate_nlu_engine",
    "nlu_engine_health",
]


# ============================================================
# SECTION 31 - LOCAL VALIDATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    print(json.dumps(nlu_engine_health(), indent=2, sort_keys=True))