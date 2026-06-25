# ============================================================
# AISP2 BASEBALL
# FILE: main.py
# PURPOSE: FastAPI application entrypoint for template routing,
# static asset mounting, chatbot API, prediction demo API,
# project status endpoints, and system health checks
# ============================================================


# ============================================================
# SECTION 01 - IMPORTS
# FILE: main.py
# PURPOSE: safe application imports, numbered directory path
# registration, FastAPI infrastructure, MLB API access,
# semantic engine access, and intent detection access
# ============================================================

from __future__ import annotations


# ============================================================
# SECTION 01.01 - STANDARD LIBRARY IMPORTS
# FILE: main.py
# PURPOSE: core Python utilities and numbered folder support
# ============================================================

import sys
from pathlib import Path
from typing import Any

import requests


# ============================================================
# SECTION 01.02 - PROJECT PATH REGISTRATION
# FILE: main.py
# PURPOSE: make numbered folders importable without using
# invalid Python package names like from 04_ai import ...
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

DATABASE_DIR = PROJECT_ROOT / "01_database"
DATA_SOURCES_DIR = PROJECT_ROOT / "02_data_sources"
INGESTION_DIR = PROJECT_ROOT / "03_ingestion"
AI_DIR = PROJECT_ROOT / "04_ai"

for project_path in [
    PROJECT_ROOT,
    DATABASE_DIR,
    DATA_SOURCES_DIR,
    INGESTION_DIR,
    AI_DIR,
]:
    project_path_string = str(project_path)

    if project_path_string not in sys.path:
        sys.path.insert(0, project_path_string)


# ============================================================
# SECTION 01.03 - FASTAPI IMPORTS
# FILE: main.py
# PURPOSE: web app, request handling, templates, and static files
# ============================================================

from fastapi import FastAPI
from fastapi import Request

from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel


# ============================================================
# SECTION 01.04 - DATABASE IMPORTS
# FILE: main.py
# PURPOSE: safe core database access only
# ============================================================

from database import database_health_check
from database import database_health_details


# ============================================================
# SECTION 01.05 - MLB DATA SOURCE IMPORTS
# FILE: main.py
# PURPOSE: safe MLB Stats API client access
# ============================================================

from mlb_stats_api import MLBStatsAPIClient
from mlb_stats_api import DEFAULT_SEASON


## ============================================================
# SECTION 01.06 - NLP ENGINE IMPORTS
# FILE: main.py
# PURPOSE: connect Natural Language Understanding,
# semantic interpretation, entity recognition,
# context building, and outcome detection
# ============================================================

from nlp.nlu_engine import build_nlu_report

from nlp.semantic_engine import (
    detect_outcome,
    detect_player,
    detect_team,
    interpret_baseball_question,
)

from nlp.entity_detection import (
    MLB_TEAM_ALIASES,
    build_entity_report,
)

from nlp.context_builder import (
    build_baseball_context,
)
# ============================================================
# SECTION 01.07 - NLP INTENT DETECTION IMPORTS
# FILE: main.py
# PURPOSE: connect chat routing to intent classification
# ============================================================

from nlp.intent_detection import INTENT_LIST_TEAMS
from nlp.intent_detection import INTENT_LIST_PLAYERS
from nlp.intent_detection import INTENT_TEAM_INFO
from nlp.intent_detection import INTENT_PLAYER_INFO
from nlp.intent_detection import INTENT_PLAYER_PROBABILITY
from nlp.intent_detection import INTENT_COMPARE_PLAYERS
from nlp.intent_detection import INTENT_COMPARE_TEAMS
from nlp.intent_detection import INTENT_GENERAL_PROBABILITY
from nlp.intent_detection import INTENT_MATCHUP_ANALYSIS
from nlp.intent_detection import INTENT_STAT_REQUEST
from nlp.intent_detection import INTENT_EXPLAIN_MODEL
from nlp.intent_detection import INTENT_HELP
from nlp.intent_detection import INTENT_GENERAL_BASEBALL
from nlp.intent_detection import build_intent_report


# ============================================================
# SECTION 01.08 - AI CORE AND RESPONSE IMPORTS
# FILE: main.py
# PURPOSE: connect security, response generation, and memory
# after 04_ai directory reorganization
# ============================================================

from core.security_guardrails import build_chat_security_report
from core.security_guardrails import build_safe_chat_response

from core.interaction_memory import remember_chat_interaction

from response_generator import generate_response_from_context
# ============================================================
# SECTION 02 - APPLICATION METADATA
# ============================================================

PROJECT_NAME = "AISP2 Baseball"
PROJECT_VERSION = "1.0.0"
PROJECT_PHASE = "1.00 Template Architecture Foundation"
SERVICE_NAME = "aisp2-baseball"
PRIMARY_SPORT = "MLB"

GITHUB_REPOSITORY = "https://github.com/CodeDressing/AISP2_Baseball"
RENDER_SERVICE = "https://aisp2-baseball.onrender.com"

DEVELOPMENT_RULE = "One file or one directory at a time."


# ============================================================
# SECTION 03 - DEMO DATA
# FILE: main.py
# PURPOSE: expanded demo MLB team, player, outcome, and profile
# data for Player Explorer, Prediction Workbench, and chat
# ============================================================

DEMO_TEAMS = {
    "New York Yankees": {
        "abbreviation": "NYY",
        "league": "American League",
        "division": "AL East",
        "ballpark": "Yankee Stadium",
        "players": ["Aaron Judge", "Giancarlo Stanton", "Gerrit Cole"],
    },
    "Boston Red Sox": {
        "abbreviation": "BOS",
        "league": "American League",
        "division": "AL East",
        "ballpark": "Fenway Park",
        "players": ["Rafael Devers", "Jarren Duran", "Garrett Crochet"],
    },
    "Baltimore Orioles": {
        "abbreviation": "BAL",
        "league": "American League",
        "division": "AL East",
        "ballpark": "Oriole Park at Camden Yards",
        "players": ["Gunnar Henderson", "Adley Rutschman", "Grayson Rodriguez"],
    },
    "Cleveland Guardians": {
        "abbreviation": "CLE",
        "league": "American League",
        "division": "AL Central",
        "ballpark": "Progressive Field",
        "players": ["Jose Ramirez", "Steven Kwan", "Tanner Bibee"],
    },
    "Detroit Tigers": {
        "abbreviation": "DET",
        "league": "American League",
        "division": "AL Central",
        "ballpark": "Comerica Park",
        "players": ["Riley Greene", "Tarik Skubal", "Spencer Torkelson"],
    },
    "Houston Astros": {
        "abbreviation": "HOU",
        "league": "American League",
        "division": "AL West",
        "ballpark": "Daikin Park",
        "players": ["Yordan Alvarez", "Jose Altuve", "Framber Valdez"],
    },
    "Texas Rangers": {
        "abbreviation": "TEX",
        "league": "American League",
        "division": "AL West",
        "ballpark": "Globe Life Field",
        "players": ["Corey Seager", "Marcus Semien", "Jacob deGrom"],
    },
    "Seattle Mariners": {
        "abbreviation": "SEA",
        "league": "American League",
        "division": "AL West",
        "ballpark": "T-Mobile Park",
        "players": ["Julio Rodriguez", "Cal Raleigh", "Luis Castillo"],
    },
    "New York Mets": {
        "abbreviation": "NYM",
        "league": "National League",
        "division": "NL East",
        "ballpark": "Citi Field",
        "players": ["Juan Soto", "Francisco Lindor", "Pete Alonso"],
    },
    "Atlanta Braves": {
        "abbreviation": "ATL",
        "league": "National League",
        "division": "NL East",
        "ballpark": "Truist Park",
        "players": ["Ronald Acuna Jr.", "Matt Olson", "Austin Riley"],
    },
    "Philadelphia Phillies": {
        "abbreviation": "PHI",
        "league": "National League",
        "division": "NL East",
        "ballpark": "Citizens Bank Park",
        "players": ["Bryce Harper", "Trea Turner", "Zack Wheeler"],
    },
    "Los Angeles Dodgers": {
        "abbreviation": "LAD",
        "league": "National League",
        "division": "NL West",
        "ballpark": "Dodger Stadium",
        "players": ["Shohei Ohtani", "Mookie Betts", "Freddie Freeman"],
    },
    "San Diego Padres": {
        "abbreviation": "SD",
        "league": "National League",
        "division": "NL West",
        "ballpark": "Petco Park",
        "players": ["Fernando Tatis Jr.", "Manny Machado", "Dylan Cease"],
    },
    "Chicago Cubs": {
        "abbreviation": "CHC",
        "league": "National League",
        "division": "NL Central",
        "ballpark": "Wrigley Field",
        "players": ["Kyle Tucker", "Seiya Suzuki", "Shota Imanaga"],
    },
}


DEMO_OUTCOMES = {
    "home_run": "Hits a Home Run",
    "hit": "Gets at least 1 Hit",
    "rbi": "Records an RBI",
    "total_bases": "Over 1.5 Total Bases",
    "strikeout": "Pitcher Records 6+ Strikeouts",
}


DEMO_PLAYER_PROFILES = {
    "Aaron Judge": {"style": "Elite power hitter", "recent_form": "Strong hard-hit profile", "primary_metric": "Barrel rate", "base_probability": 28, "confidence": 74},
    "Giancarlo Stanton": {"style": "Extreme power hitter", "recent_form": "High variance, high upside", "primary_metric": "Exit velocity", "base_probability": 22, "confidence": 62},
    "Gerrit Cole": {"style": "Ace starting pitcher", "recent_form": "High strikeout profile", "primary_metric": "K rate", "base_probability": 57, "confidence": 75},

    "Rafael Devers": {"style": "Left-handed power bat", "recent_form": "Strong run production profile", "primary_metric": "SLG", "base_probability": 26, "confidence": 71},
    "Jarren Duran": {"style": "Speed and contact profile", "recent_form": "Dynamic table-setter", "primary_metric": "OBP and speed", "base_probability": 59, "confidence": 72},
    "Garrett Crochet": {"style": "Power left-handed starter", "recent_form": "High strikeout arm", "primary_metric": "K rate", "base_probability": 55, "confidence": 74},

    "Gunnar Henderson": {"style": "Young power shortstop", "recent_form": "High-impact offensive profile", "primary_metric": "OPS", "base_probability": 27, "confidence": 73},
    "Adley Rutschman": {"style": "Switch-hitting catcher", "recent_form": "Stable contact and OBP", "primary_metric": "OBP", "base_probability": 60, "confidence": 75},
    "Grayson Rodriguez": {"style": "Power starting pitcher", "recent_form": "Strikeout upside profile", "primary_metric": "Whiff rate", "base_probability": 53, "confidence": 70},

    "Jose Ramirez": {"style": "Switch-hitting run producer", "recent_form": "Elite all-around production", "primary_metric": "OPS and RBI", "base_probability": 62, "confidence": 79},
    "Steven Kwan": {"style": "High-contact hitter", "recent_form": "Strong bat-to-ball profile", "primary_metric": "Contact rate", "base_probability": 67, "confidence": 80},
    "Tanner Bibee": {"style": "Command-oriented starter", "recent_form": "Stable strikeout profile", "primary_metric": "K-BB rate", "base_probability": 51, "confidence": 71},

    "Riley Greene": {"style": "Left-handed impact bat", "recent_form": "Growing power profile", "primary_metric": "Hard-hit rate", "base_probability": 24, "confidence": 68},
    "Tarik Skubal": {"style": "Ace left-handed starter", "recent_form": "Elite strikeout and command profile", "primary_metric": "K rate", "base_probability": 60, "confidence": 82},
    "Spencer Torkelson": {"style": "Power-first corner bat", "recent_form": "Home run upside profile", "primary_metric": "HR rate", "base_probability": 23, "confidence": 66},

    "Yordan Alvarez": {"style": "Elite left-handed slugger", "recent_form": "Premium power profile", "primary_metric": "Exit velocity", "base_probability": 30, "confidence": 78},
    "Jose Altuve": {"style": "Veteran contact-power blend", "recent_form": "Strong top-order production", "primary_metric": "AVG and OPS", "base_probability": 63, "confidence": 76},
    "Framber Valdez": {"style": "Ground-ball left-handed starter", "recent_form": "Run prevention profile", "primary_metric": "Ground-ball rate", "base_probability": 49, "confidence": 70},

    "Corey Seager": {"style": "Elite left-handed shortstop bat", "recent_form": "Strong power and contact blend", "primary_metric": "OPS", "base_probability": 27, "confidence": 75},
    "Marcus Semien": {"style": "Durable run producer", "recent_form": "Stable lineup engine", "primary_metric": "Runs and OPS", "base_probability": 58, "confidence": 73},
    "Jacob deGrom": {"style": "Elite power pitcher", "recent_form": "Ace upside when active", "primary_metric": "K rate", "base_probability": 61, "confidence": 72},

    "Julio Rodriguez": {"style": "Power-speed center fielder", "recent_form": "Dynamic offensive profile", "primary_metric": "OPS and speed", "base_probability": 56, "confidence": 72},
    "Cal Raleigh": {"style": "Switch-hitting power catcher", "recent_form": "Home run upside", "primary_metric": "Barrel rate", "base_probability": 24, "confidence": 67},
    "Luis Castillo": {"style": "Power starting pitcher", "recent_form": "Strong strikeout foundation", "primary_metric": "Whiff rate", "base_probability": 54, "confidence": 73},

    "Juan Soto": {"style": "Elite plate discipline hitter", "recent_form": "Excellent on-base profile", "primary_metric": "OBP and walk rate", "base_probability": 66, "confidence": 81},
    "Francisco Lindor": {"style": "Switch-hitting shortstop star", "recent_form": "Power and speed blend", "primary_metric": "OPS", "base_probability": 57, "confidence": 74},
    "Pete Alonso": {"style": "Power-first slugger", "recent_form": "Strong home run profile", "primary_metric": "HR rate", "base_probability": 24, "confidence": 68},

    "Ronald Acuna Jr.": {"style": "Power-speed superstar", "recent_form": "Dynamic offensive profile", "primary_metric": "OPS and stolen-base threat", "base_probability": 58, "confidence": 73},
    "Matt Olson": {"style": "Left-handed power hitter", "recent_form": "Strong pull-side power", "primary_metric": "Hard-hit rate", "base_probability": 25, "confidence": 70},
    "Austin Riley": {"style": "Middle-order power bat", "recent_form": "Strong contact authority", "primary_metric": "SLG", "base_probability": 23, "confidence": 69},

    "Bryce Harper": {"style": "Elite left-handed run producer", "recent_form": "Strong power and OBP profile", "primary_metric": "OPS", "base_probability": 29, "confidence": 77},
    "Trea Turner": {"style": "Speed and contact shortstop", "recent_form": "Multi-category offensive profile", "primary_metric": "AVG and speed", "base_probability": 62, "confidence": 76},
    "Zack Wheeler": {"style": "Ace right-handed starter", "recent_form": "High command and strikeout profile", "primary_metric": "K-BB rate", "base_probability": 56, "confidence": 80},

    "Shohei Ohtani": {"style": "Elite two-way offensive force", "recent_form": "High-impact contact profile", "primary_metric": "Exit velocity", "base_probability": 31, "confidence": 77},
    "Mookie Betts": {"style": "Contact and power blend", "recent_form": "Stable all-around production", "primary_metric": "OPS", "base_probability": 61, "confidence": 76},
    "Freddie Freeman": {"style": "High-contact run producer", "recent_form": "Reliable hit profile", "primary_metric": "AVG and hard contact", "base_probability": 64, "confidence": 79},

    "Fernando Tatis Jr.": {"style": "Power-speed superstar", "recent_form": "Explosive offensive upside", "primary_metric": "Barrel rate and speed", "base_probability": 27, "confidence": 73},
    "Manny Machado": {"style": "Veteran middle-order bat", "recent_form": "Stable power production", "primary_metric": "SLG", "base_probability": 24, "confidence": 71},
    "Dylan Cease": {"style": "High-strikeout starting pitcher", "recent_form": "Whiff-heavy profile", "primary_metric": "K rate", "base_probability": 58, "confidence": 76},

    "Kyle Tucker": {"style": "Left-handed power and contact star", "recent_form": "Strong all-around hitter", "primary_metric": "OPS", "base_probability": 28, "confidence": 76},
    "Seiya Suzuki": {"style": "Right-handed impact bat", "recent_form": "Power and patience profile", "primary_metric": "Hard-hit rate", "base_probability": 25, "confidence": 70},
    "Shota Imanaga": {"style": "Left-handed starter", "recent_form": "Command and deception profile", "primary_metric": "K-BB rate", "base_probability": 52, "confidence": 72},
}

# ============================================================
# SECTION 04 - REQUEST MODELS
# ============================================================

class ChatRequest(BaseModel):
    message: str


# ============================================================
# SECTION 05 - APPLICATION INITIALIZATION
# ============================================================

app = FastAPI(
    title=PROJECT_NAME,
    version=PROJECT_VERSION,
    description=(
        "AI Sports Intelligence Platform 2 - baseball analytics, "
        "probability, prediction, and AI assistant platform."
    ),
)


# ============================================================
# SECTION 06 - STATIC FILES AND TEMPLATES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

templates = Jinja2Templates(
    directory="templates",
)


# ============================================================
# SECTION 07 - SHARED DEMO HELPERS
# ============================================================

def get_available_players(team_name: str) -> list[str]:
    team = DEMO_TEAMS.get(team_name)

    if not team:
        first_team = next(iter(DEMO_TEAMS.values()))
        return first_team["players"]

    return team["players"]


def normalize_demo_selection(
    team_name: str | None,
    player_name: str | None,
    outcome_key: str | None,
) -> tuple[str, str, str]:
    selected_team = team_name or "New York Yankees"

    if selected_team not in DEMO_TEAMS:
        selected_team = "New York Yankees"

    available_players = get_available_players(
        selected_team,
    )

    selected_player = player_name or available_players[0]

    if selected_player not in available_players:
        selected_player = available_players[0]

    selected_outcome = outcome_key or "home_run"

    if selected_outcome not in DEMO_OUTCOMES:
        selected_outcome = "home_run"

    return selected_team, selected_player, selected_outcome


def build_demo_probability(
    player_name: str,
    outcome_key: str,
) -> dict:
    profile = DEMO_PLAYER_PROFILES.get(
        player_name,
        {
            "style": "Balanced player profile",
            "recent_form": "Stable recent form",
            "primary_metric": "Season production",
            "base_probability": 50,
            "confidence": 65,
        },
    )

    base_probability = profile["base_probability"]

    if outcome_key == "home_run":
        probability = base_probability
    elif outcome_key == "hit":
        probability = min(base_probability + 35, 78)
    elif outcome_key == "rbi":
        probability = min(base_probability + 18, 64)
    elif outcome_key == "total_bases":
        probability = min(base_probability + 23, 69)
    elif outcome_key == "strikeout":
        probability = base_probability
    else:
        probability = base_probability

    return {
        "probability": probability,
        "confidence": profile["confidence"],
        "profile": profile,
    }

# ============================================================
# SECTION 08 - NLU-FIRST CHAT ORCHESTRATION ENGINE
# FILE: main.py
# PURPOSE: route every chat message through security,
# entity detection, Natural Language Understanding, semantic
# interpretation, intent detection, context building, live MLB
# lookup, response generation, and interaction memory
# ============================================================

def build_engine_probability(
    player_name: str,
    outcome_key: str,
) -> dict:
    return build_demo_probability(
        player_name=player_name,
        outcome_key=outcome_key,
    )


def extract_possible_player_search_name(message: str) -> str | None:
    lowered_message = message.lower()

    search_phrases = [
        "search for",
        "look up",
        "find",
        "who is",
        "tell me about",
    ]

    for phrase in search_phrases:
        if phrase in lowered_message:
            possible_name = message[
                lowered_message.find(phrase) + len(phrase):
            ].strip(" ?.!")

            if possible_name:
                return possible_name

    return None


def build_live_team_list_reply() -> str:
    try:
        payload = fetch_mlb_json(
            "/teams?sportId=1&activeStatus=Y"
        )

        teams = [
            team.get("name")
            for team in payload.get("teams", [])
            if team.get("name")
        ]

        teams.sort()

        return (
            f"I currently recognize {len(teams)} active MLB teams:\n\n"
            + "\n".join(f"- {team}" for team in teams)
        )

    except Exception:
        teams = sorted(
            MLB_TEAM_ALIASES.keys(),
        )

        return (
            f"I currently recognize {len(teams)} MLB teams from the AISP2 alias engine:\n\n"
            + "\n".join(f"- {team}" for team in teams)
        )


def build_live_player_search_reply(message: str) -> str:
    search_name = extract_possible_player_search_name(
        message,
    )

    if not search_name:
        return (
            "I can search for players, but I need a player name. "
            "Try: Can I search for Corbin Carroll?"
        )

    try:
        payload = fetch_mlb_json(
            f"/sports/1/players?season={DEFAULT_SEASON}"
        )

        people = payload.get(
            "people",
            [],
        )

        search_tokens = [
            token.lower()
            for token in search_name.split()
            if token
        ]

        matches = []

        for person in people:
            full_name = person.get(
                "fullName",
                "",
            )

            lowered_name = full_name.lower()

            if all(
                token in lowered_name
                for token in search_tokens
            ):
                matches.append(person)

        if not matches:
            return (
                f"I searched the live MLB player list but could not find {search_name}. "
                "Try the full player name or check spelling."
            )

        player = matches[0]

        return (
            f"Yes. I found {player.get('fullName')} in the live MLB player index.\n\n"
            f"Player ID: {player.get('id')}\n"
            f"Primary Number: {player.get('primaryNumber', 'N/A')}\n"
            f"Position: {player.get('primaryPosition', {}).get('name', 'N/A')}\n\n"
            "Next upgrade will connect this live player search directly to team, roster, stats, and probability lookup."
        )

    except Exception:
        return (
            f"I understood that you want to search for {search_name}, but the live MLB player lookup "
            "is not available from the server right now."
        )


def should_use_live_player_search(
    message: str,
    context: dict,
    nlu_report: dict,
) -> bool:
    if context.get("player"):
        return False

    if nlu_report.get("task") in [
        "best_overall_probability",
        "best_team_probability",
        "list_teams",
        "list_players",
    ]:
        return False

    lowered_message = message.lower()

    return any(
        phrase in lowered_message
        for phrase in [
            "search for",
            "look up",
            "find",
            "who is",
            "can i search",
        ]
    )


def build_best_overall_probability_reply(
    outcome_key: str | None,
) -> str:
    selected_outcome = outcome_key or "home_run"

    if selected_outcome not in DEMO_OUTCOMES:
        selected_outcome = "home_run"

    scored_players = []

    for player_name in DEMO_PLAYER_PROFILES.keys():
        prediction = build_engine_probability(
            player_name=player_name,
            outcome_key=selected_outcome,
        )

        scored_players.append(
            {
                "player": player_name,
                "probability": prediction["probability"],
                "confidence": prediction["confidence"],
                "profile": prediction["profile"],
            }
        )

    scored_players.sort(
        key=lambda item: item["probability"],
        reverse=True,
    )

    top_players = scored_players[:5]
    top_player = top_players[0]

    ranking_lines = [
        f"{item['player']}: {item['probability']}% probability, {item['confidence']}% confidence"
        for item in top_players
    ]

    return (
        f"Highest AISP2 probability across loaded players\n\n"
        f"Outcome: {DEMO_OUTCOMES[selected_outcome]}\n\n"
        f"Top Candidate: {top_player['player']}\n"
        f"Estimated Probability: {top_player['probability']}%\n"
        f"Confidence: {top_player['confidence']}%\n\n"
        "Top 5:\n"
        + "\n".join(f"- {line}" for line in ranking_lines)
        + "\n\nThis is currently based on the loaded AISP2 player profile set. "
        "The next upgrade will expand this to live MLB rosters and real statistical features."
    )


def build_chat_reply(message: str) -> dict:
    security_report = build_chat_security_report(
        message,
    )

    cleaned_message = security_report[
        "cleaned_message"
    ]

    if not cleaned_message:
        return {
            "reply": (
                "Ask me about an MLB team, player, roster, matchup, probability, "
                "player search, or prediction."
            ),
            "intent": "empty",
            "security": security_report,
        }

    if security_report["blocked"]:
        return build_safe_chat_response(
            reason=security_report["reason"],
        )

    entity_report = build_entity_report(
        message=cleaned_message,
        player_profiles=DEMO_PLAYER_PROFILES,
    )

    nlu_report = build_nlu_report(
        message=cleaned_message,
        entity_report=entity_report,
    )

    semantic_report = interpret_baseball_question(
        message=cleaned_message,
        teams=DEMO_TEAMS,
        player_profiles=DEMO_PLAYER_PROFILES,
    )

    if nlu_report.get("outcome") and not semantic_report.get("outcome"):
        semantic_report["outcome"] = nlu_report.get("outcome")

    detected_player = (
        semantic_report.get("player")
        or (
            entity_report.get("primary_player", {}) or {}
        ).get("canonical_name")
    )

    detected_team = (
        (
            entity_report.get("primary_team", {}) or {}
        ).get("canonical_name")
        or semantic_report.get("team")
    )

    detected_outcome = (
        nlu_report.get("outcome")
        or semantic_report.get("outcome")
    )

    detected_players = [
        player["canonical_name"]
        for player in entity_report.get("players", [])
    ] or semantic_report.get("players", [])

    detected_teams = [
        team["canonical_name"]
        for team in entity_report.get("teams", [])
    ] or semantic_report.get("teams", [])

    intent_report = build_intent_report(
        message=cleaned_message,
        detected_player=detected_player,
        detected_team=detected_team,
        detected_outcome=detected_outcome,
        detected_players=detected_players,
        detected_teams=detected_teams,
    )

    context = build_baseball_context(
        message=cleaned_message,
        intent_report=intent_report,
        entity_report=entity_report,
        semantic_report=semantic_report,
    )

    if nlu_report.get("task") != "general_baseball_question":
        context["task"] = nlu_report.get("task")

    if nlu_report.get("outcome"):
        context["outcome"] = nlu_report.get("outcome")

    context["nlu"] = nlu_report

    final_intent = intent_report.get(
        "final_intent",
    )

    lowered_message = cleaned_message.lower()

    if (
        nlu_report.get("task") == "list_teams"
        or final_intent == INTENT_LIST_TEAMS
        or "all mlb teams" in lowered_message
        or "how many mlb teams" in lowered_message
        or "normal english list" in lowered_message
    ):
        reply = build_live_team_list_reply()
        context["task"] = "list_teams"

    elif nlu_report.get("task") == "best_overall_probability":
        reply = build_best_overall_probability_reply(
            outcome_key=nlu_report.get("outcome"),
        )
        context["task"] = "best_overall_probability"

    elif should_use_live_player_search(
        cleaned_message,
        context,
        nlu_report,
    ):
        reply = build_live_player_search_reply(
            cleaned_message,
        )
        context["task"] = "live_player_search"

    else:
        reply = generate_response_from_context(
            context=context,
            demo_teams=DEMO_TEAMS,
            player_profiles=DEMO_PLAYER_PROFILES,
            demo_outcomes=DEMO_OUTCOMES,
            build_probability_function=build_engine_probability,
        )

    chat_response = {
        "reply": reply,
        "intent": final_intent,
        "context": context,
        "nlu": nlu_report,
        "semantic": {
            "player": context.get("player"),
            "team": context.get("team"),
            "outcome": context.get("outcome"),
            "players": context.get("players", []),
            "teams": context.get("teams", []),
            "intent_report": intent_report,
            "entity_report": entity_report,
            "semantic_report": semantic_report,
            "nlu_report": nlu_report,
        },
        "security": {
            "blocked": False,
            "message_length": len(cleaned_message),
            "report": security_report,
        },
    }

    memory_status = remember_chat_interaction(
        user_message=cleaned_message,
        chat_response=chat_response,
    )

    chat_response["memory"] = memory_status

    return chat_response
# ============================================================
# SECTION 09 - TEMPLATE ROUTES
# ============================================================

@app.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "project_name": PROJECT_NAME,
            "project_version": PROJECT_VERSION,
            "project_phase": PROJECT_PHASE,
        },
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "project_name": PROJECT_NAME,
            "project_version": PROJECT_VERSION,
            "project_phase": PROJECT_PHASE,
        },
    )


@app.get("/players", response_class=HTMLResponse)
def player_explorer_page(request: Request):
    return templates.TemplateResponse(
        request,
        "player_explorer.html",
        {
            "project_name": PROJECT_NAME,
            "project_version": PROJECT_VERSION,
            "project_phase": PROJECT_PHASE,
        },
    )


@app.get("/tools/prediction", response_class=HTMLResponse)
def prediction_workbench_page(request: Request):
    return templates.TemplateResponse(
        request,
        "prediction_workbench.html",
        {
            "project_name": PROJECT_NAME,
            "project_version": PROJECT_VERSION,
            "project_phase": PROJECT_PHASE,
        },
    )

# ============================================================
# SECTION 10 - CHAT API ENDPOINT
# ============================================================

@app.post("/api/chat")
def chat_api(request: ChatRequest) -> dict:
    return build_chat_reply(
        request.message,
    )


# ============================================================
# SECTION 11 - DEMO PREDICTION API ENDPOINT
# ============================================================

@app.get("/api/demo/prediction")
def demo_prediction_json(
    team: str | None = None,
    player: str | None = None,
    outcome: str | None = None,
) -> dict:
    selected_team, selected_player, selected_outcome = normalize_demo_selection(
        team_name=team,
        player_name=player,
        outcome_key=outcome,
    )

    team_data = DEMO_TEAMS[selected_team]

    prediction = build_demo_probability(
        player_name=selected_player,
        outcome_key=selected_outcome,
    )

    return {
        "mode": "demo",
        "disclaimer": "Illustrative demo only. Not a real betting or wagering prediction.",
        "team": {
            "name": selected_team,
            "abbreviation": team_data["abbreviation"],
            "league": team_data["league"],
            "division": team_data["division"],
            "ballpark": team_data["ballpark"],
        },
        "player": selected_player,
        "outcome": {
            "key": selected_outcome,
            "label": DEMO_OUTCOMES[selected_outcome],
        },
        "prediction": {
            "estimated_probability": prediction["probability"],
            "confidence": prediction["confidence"],
            "model": "AISP Demo Probability Card",
        },
        "supporting_context": {
            "player_style": prediction["profile"]["style"],
            "recent_form": prediction["profile"]["recent_form"],
            "primary_metric": prediction["profile"]["primary_metric"],
        },
        "future_real_sources": [
            "MLB Stats API",
            "Baseball Savant / Statcast",
            "FanGraphs",
            "Baseball Reference",
            "Retrosheet",
            "Lahman Database",
        ],
    }


# ============================================================
# SECTION 12 - SYSTEM ENDPOINTS
# ============================================================

@app.get("/api/root")
def root_json() -> dict:
    return {
        "project": PROJECT_NAME,
        "phase": PROJECT_PHASE,
        "status": "online",
        "version": PROJECT_VERSION,
        "service": SERVICE_NAME,
        "sport": PRIMARY_SPORT,
        "github": GITHUB_REPOSITORY,
        "render": RENDER_SERVICE,
        "homepage": "template-backed chatbot-first interface",
        "routes": [
            "/",
            "/dashboard",
            "/players",
            "/tools/prediction",
            "/api/chat",
            "/api/demo/prediction",
        ],
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "project": PROJECT_NAME,
        "phase": PROJECT_PHASE,
    }


@app.get("/system/info")
def system_info() -> dict:
    return {
        "application": PROJECT_NAME,
        "version": PROJECT_VERSION,
        "phase": PROJECT_PHASE,
        "environment": "development",
        "sport": PRIMARY_SPORT,
        "repository": GITHUB_REPOSITORY,
        "deployment": RENDER_SERVICE,
        "runtime": "FastAPI",
        "deployment_provider": "Render",
        "source_control": "GitHub",
    }


# ============================================================
# SECTION 13 - PROJECT ENDPOINTS
# ============================================================

@app.get("/project/status")
def project_status() -> dict:
    return {
        "project": PROJECT_NAME,
        "status": "ACTIVE DEVELOPMENT",
        "phase": PROJECT_PHASE,
        "homepage": "template-backed chatbot-first interface",
        "deployment": {
            "render": "CONNECTED",
            "url": RENDER_SERVICE,
            "status": "ONLINE",
        },
        "source_control": {
            "github": "CONNECTED",
            "repository": GITHUB_REPOSITORY,
            "branch": "main",
        },
        "foundation": {
            "fastapi_entrypoint": "LIVE",
            "static_assets": "MOUNTED",
            "template_engine": "JINJA2 CONNECTED",
            "database_layer": "CREATED",
            "project_ledger": "CREATED",
            "mlb_stats_api_client": "CREATED",
            "team_ingestion": "CREATED",
            "minimal_chat_homepage": "CREATED",
            "dashboard_template": "CREATED",
            "player_explorer_template": "CREATED",
            "prediction_workbench_template": "CREATED",
        },
        "current_focus": "Template-backed frontend architecture and clean AI product experience",
        "next_target": "Real data-backed team and player tools",
        "development_rule": DEVELOPMENT_RULE,
    }


@app.get("/project/roadmap")
def project_roadmap() -> dict:
    return {
        "current_file": "main.py",
        "current_focus": "Template architecture and route wiring",
        "completed": [
            "GitHub repository",
            "Render deployment",
            "Database layer",
            "Models",
            "MLB Stats API client",
            "Team ingestion engine",
            "Static CSS architecture",
            "Static JS architecture",
            "Home template",
            "Dashboard template",
            "Player explorer template",
            "Prediction workbench template",
            "FastAPI template routing",
        ],
        "next_files": [
            "templates/team_explorer.html",
            "ai_assistant_outline.md",
            "ai_chat_engine.py",
            "04_routes/team_routes.py",
            "04_routes/player_routes.py",
            "06_probability/probability_engine.py",
        ],
    }


@app.get("/project/vision")
def project_vision() -> dict:
    return {
        "vision": "Build the best baseball intelligence platform possible.",
        "product_direction": "Chat-first baseball AI assistant with hidden advanced tools.",
        "core_user_workflow": [
            "Open AISP2",
            "Ask a baseball question",
            "Get readable analysis",
            "Open deeper tools only when needed",
            "Select teams and players",
            "View probabilities and explanations",
        ],
    }


@app.get("/project/data-sources")
def project_data_sources() -> dict:
    return {
        "primary_goal": "Use the best available baseball data sources.",
        "tier_1_sources": [
            "MLB Stats API",
            "Baseball Savant / Statcast",
        ],
        "tier_2_sources": [
            "FanGraphs",
            "Baseball Reference",
        ],
        "historical_sources": [
            "Retrosheet",
            "Lahman Database",
        ],
    }


@app.get("/project/ml-roadmap")
def project_machine_learning_roadmap() -> dict:
    return {
        "supervised_learning_targets": [
            "Hit probability",
            "Home run probability",
            "Strikeout probability",
            "Walk probability",
            "RBI probability",
            "Game winner probability",
        ],
        "future_models": [
            "Logistic Regression",
            "Random Forest",
            "Gradient Boosting",
            "XGBoost",
            "LightGBM",
            "Neural networks",
            "Monte Carlo simulation",
        ],
    }


@app.get("/project/probability-output-design")
def probability_output_design() -> dict:
    return {
        "goal": "Every prediction should be readable, explainable, and useful.",
        "current_demo_endpoint": "/tools/prediction",
        "future_prediction_card": {
            "player": "Aaron Judge",
            "team": "New York Yankees",
            "outcome": "Hits a home run",
            "estimated_probability": "Example: 28%",
            "confidence": "Example: 74%",
            "plain_english_explanation": "Readable model explanation goes here.",
        },
    }


@app.get("/project/files")
def project_files() -> dict:
    return {
        "root": [
            "main.py",
            "requirements.txt",
            "PROJECT_LEDGER.md",
        ],
        "templates": [
            "home.html",
            "dashboard.html",
            "player_explorer.html",
            "prediction_workbench.html",
        ],
        "static/css": [
            "aisp2.css",
            "chat.css",
            "dashboard.css",
            "prediction.css",
        ],
        "static/js": [
            "aisp2.js",
            "chat.js",
            "dashboard.js",
            "prediction.js",
        ],
        "01_database": [
            "database.py",
            "models.py",
            "init_db.py",
        ],
        "02_data_sources": [
            "mlb_stats_api.py",
        ],
        "03_ingestion": [
            "team_ingestion.py",
        ],
        "next_files": [
            "templates/team_explorer.html",
            "ai_assistant_outline.md",
            "ai_chat_engine.py",
        ],
    }


@app.get("/project/next-action")
def project_next_action() -> dict:
    return {
        "current_rule": DEVELOPMENT_RULE,
        "next_action": "Deploy and verify template-backed homepage, dashboard, players page, and prediction workbench",
        "after_that": "Create templates/team_explorer.html",
        "goal": "Keep homepage sleek while advanced tools live behind toolbar links",
    }


# ============================================================
# SECTION 14 - LOCAL STARTUP VALIDATION
# ============================================================

if __name__ == "__main__":
    print("AISP2 Baseball loaded successfully.")
    print("Template-backed frontend architecture initialized.")
    print(f"Project: {PROJECT_NAME}")
    print(f"Version: {PROJECT_VERSION}")
    print(f"Phase: {PROJECT_PHASE}")


# ============================================================
# SECTION 15 - FUTURE APPLICATION ROADMAP
# ============================================================

"""
Future Application Roadmap

Phase 1.01:
    Verify static asset loading on Render.

Phase 1.02:
    Verify template routing on Render.

Phase 1.03:
    Create templates/team_explorer.html.

Phase 1.04:
    Create ai_assistant_outline.md.

Phase 1.05:
    Create ai_chat_engine.py.

Phase 2.00:
    Add real team explorer.

Phase 3.00:
    Add real player explorer.

Phase 4.00:
    Add probability engine.

Phase 5.00:
    Add machine learning models.

Phase 6.00:
    Add simulation engine.

Product Rule:
    Homepage stays minimal.
    Advanced tools stay behind toolbar links.
    Chat becomes the primary interface.
    main.py stays clean and route-focused.
"""

# ============================================================
# SECTION 16 - LIVE MLB DATA API
# FILE: main.py
# PURPOSE: expose all MLB teams and active roster players
# from MLB Stats API for frontend selectors
# ============================================================

MLB_STATS_API_BASE = "https://statsapi.mlb.com/api/v1"


def fetch_mlb_json(path: str) -> dict:
    response = requests.get(
        f"{MLB_STATS_API_BASE}{path}",
        timeout=15,
    )

    response.raise_for_status()

    return response.json()


@app.get("/api/mlb/teams")
def api_mlb_teams() -> dict:
    payload = fetch_mlb_json(
        "/teams?sportId=1&activeStatus=Y"
    )

    teams = []

    for team in payload.get("teams", []):
        teams.append(
            {
                "id": team.get("id"),
                "name": team.get("name"),
                "abbreviation": team.get("abbreviation"),
                "league": team.get("league", {}).get("name"),
                "division": team.get("division", {}).get("name"),
                "venue": team.get("venue", {}).get("name"),
            }
        )

    teams.sort(
        key=lambda item: item["name"] or ""
    )

    return {
        "count": len(teams),
        "teams": teams,
    }


@app.get("/api/mlb/teams/{team_id}/players")
def api_mlb_team_players(team_id: int) -> dict:
    payload = fetch_mlb_json(
        f"/teams/{team_id}/roster?rosterType=active"
    )

    players = []

    for item in payload.get("roster", []):
        person = item.get("person", {})
        position = item.get("position", {})

        players.append(
            {
                "id": person.get("id"),
                "name": person.get("fullName"),
                "position": position.get("name"),
                "position_code": position.get("code"),
                "status": item.get("status", {}).get("description"),
            }
        )

    players.sort(
        key=lambda item: item["name"] or ""
    )

    return {
        "team_id": team_id,
        "count": len(players),
        "players": players,
    }

# ============================================================
# SECTION 17 - CHAT COMPATIBILITY API ROUTES
# FILE: main.py
# PURPOSE: provide simple frontend-friendly routes used by
# static/js/chat.js so homepage chat can display live teams,
# player search results, and warehouse-style summary counts
# ============================================================


@app.get("/admin/database/summary")
def admin_database_summary() -> dict:
    teams_payload = api_mlb_teams()

    team_count = teams_payload.get(
        "count",
        0,
    )

    player_count = 0

    for team in teams_payload.get("teams", []):
        team_id = team.get("id")

        if not team_id:
            continue

        try:
            roster_payload = api_mlb_team_players(
                team_id=team_id,
            )

            player_count += roster_payload.get(
                "count",
                0,
            )

        except Exception:
            continue

    return {
        "mode": "live_mlb_api_compatibility",
        "teams": team_count,
        "players": player_count,
        "games": 0,
        "game_predictions": 0,
        "player_predictions": 0,
        "statcast_events": 0,
        "database_connected": True,
        "source": "MLB Stats API live roster lookup",
        "note": (
            "This is a live compatibility summary for the homepage chat. "
            "Future versions should replace this with warehouse database counts."
        ),
    }


@app.get("/teams")
def teams_compatibility_list() -> list[dict]:
    payload = api_mlb_teams()

    return payload.get(
        "teams",
        [],
    )


@app.get("/players/search")
def players_search_compatibility(
    q: str,
) -> list[dict]:
    clean_query = q.strip().lower()

    if not clean_query:
        return []

    teams_payload = api_mlb_teams()

    results = []

    for team in teams_payload.get("teams", []):
        team_id = team.get("id")

        if not team_id:
            continue

        try:
            roster_payload = api_mlb_team_players(
                team_id=team_id,
            )

        except Exception:
            continue

        for player in roster_payload.get("players", []):
            player_name = (
                player.get("name")
                or ""
            )

            if clean_query not in player_name.lower():
                continue

            results.append(
                {
                    "player_id": player.get("id"),
                    "id": player.get("id"),
                    "name": player_name,
                    "team": team.get("name"),
                    "team_id": team.get("id"),
                    "team_abbreviation": team.get("abbreviation"),
                    "position": player.get("position"),
                    "position_code": player.get("position_code"),
                    "status": player.get("status"),
                    "bats": "N/A",
                    "throws": "N/A",
                    "source": "MLB Stats API active roster",
                }
            )

    results.sort(
        key=lambda item: item.get("name") or ""
    )

    return results[:25]


@app.get("/admin/warehouse/audit")
def admin_warehouse_audit() -> dict:
    summary = admin_database_summary()

    teams = summary.get(
        "teams",
        0,
    )

    players = summary.get(
        "players",
        0,
    )

    warehouse_score = 0

    if teams >= 30:
        warehouse_score += 35

    if players >= 700:
        warehouse_score += 35

    if summary.get("database_connected"):
        warehouse_score += 10

    return {
        "mode": "live_mlb_api_compatibility",
        "status": "partial_live_data_available",
        "warehouse_score": warehouse_score,
        "teams": teams,
        "players": players,
        "games": summary.get("games", 0),
        "roster_entries": players,
        "player_stats": 0,
        "statcast_events": summary.get("statcast_events", 0),
        "ready_for_team_browser": teams > 0,
        "ready_for_player_search": players > 0,
        "ready_for_predictions": False,
        "missing_for_predictions": [
            "local warehouse persistence",
            "player season statistics",
            "game schedule data",
            "Statcast event storage",
            "feature engineering service",
            "POST /predict/player",
            "POST /predict/game",
        ],
    }