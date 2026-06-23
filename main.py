# ============================================================
# AISP2 BASEBALL
# FILE: main.py
# PURPOSE: FastAPI application entrypoint for template routing,
# static asset mounting, chatbot API, prediction demo API,
# project status endpoints, and system health checks
# ============================================================


# ============================================================
# SECTION 01 - IMPORTS
# ============================================================

from __future__ import annotations

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel


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
# SECTION 08 - CHAT RESPONSE ENGINE
# ============================================================

def build_chat_reply(message: str) -> dict:
    cleaned_message = message.lower().strip()

    if not cleaned_message:
        return {
            "reply": "Ask me about a team, player, matchup, home run probability, hit probability, or baseball trend.",
            "intent": "empty",
        }

    if "judge" in cleaned_message or "home run" in cleaned_message or "hr" in cleaned_message:
        return {
            "reply": (
                "For demo mode, Aaron Judge projects as a high-power outcome candidate. "
                "A future real model would compare recent barrel rate, exit velocity, launch angle, "
                "pitcher matchup, ballpark, weather, and lineup context before estimating home run probability."
            ),
            "intent": "home_run_probability",
        }

    if "ohtani" in cleaned_message:
        return {
            "reply": (
                "Shohei Ohtani is treated as an elite power and contact profile in this demo. "
                "In the full system, AISP2 will evaluate Statcast trends, recent form, handedness splits, "
                "pitcher profile, and park factors."
            ),
            "intent": "player_analysis",
        }

    if "soto" in cleaned_message:
        return {
            "reply": (
                "Juan Soto profiles as an elite plate-discipline hitter. "
                "AISP2 will eventually analyze walk rate, OBP, pitch selection, contact quality, "
                "and matchup context for hit, walk, RBI, and total-base predictions."
            ),
            "intent": "player_analysis",
        }

    if "yankees" in cleaned_message:
        return {
            "reply": (
                "The Yankees are available in demo mode. Once database-backed team routes are connected, "
                "this chat will pull live team data, rosters, player stats, and matchup context."
            ),
            "intent": "team_analysis",
        }

    if "dodgers" in cleaned_message:
        return {
            "reply": (
                "The Dodgers are available in demo mode with Ohtani, Betts, and Freeman. "
                "Future versions will connect real rosters, schedules, splits, and projections."
            ),
            "intent": "team_analysis",
        }

    if "probability" in cleaned_message or "prediction" in cleaned_message or "predict" in cleaned_message:
        return {
            "reply": (
                "AISP2 is being designed around probability cards: estimated probability, confidence, "
                "supporting stats, and a plain-English explanation. The current version is demo-only; "
                "the next major backend step is connecting real teams, players, rosters, and stats."
            ),
            "intent": "prediction_explanation",
        }

    if "team" in cleaned_message or "players" in cleaned_message or "roster" in cleaned_message:
        return {
            "reply": (
                "The platform foundation now supports teams, players, rosters, and season-stat models. "
                "The clean product flow will be: select team, select player, choose outcome, then view a readable probability card."
            ),
            "intent": "platform_status",
        }

    return {
        "reply": (
            "I can help with baseball intelligence questions like home run probability, hit probability, "
            "team comparisons, player trends, matchup analysis, and future model explanations. Right now "
            "I am running in sleek demo mode while the real data pipeline is being connected."
        ),
        "intent": "general",
    }


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