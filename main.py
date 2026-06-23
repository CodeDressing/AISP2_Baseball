# ============================================================
# AISP2 BASEBALL
# PHASE 1.00 PART 9
# MINIMAL AI CHATBOT HOMEPAGE
# FILE: main.py
# PURPOSE: FastAPI startup, sleek chatbot-first homepage,
# lightweight baseball AI assistant demo, hidden tool routes,
# health checks, and project visibility endpoints
# ============================================================


# ============================================================
# SECTION 01 - IMPORTS
# ============================================================

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


# ============================================================
# SECTION 02 - APPLICATION METADATA
# ============================================================

PROJECT_NAME = "AISP2 Baseball"
PROJECT_VERSION = "1.0.0"
PROJECT_PHASE = "1.00 Chat Interface Foundation"
SERVICE_NAME = "aisp2-baseball"
PRIMARY_SPORT = "MLB"

GITHUB_REPOSITORY = "https://github.com/CodeDressing/AISP2_Baseball"
RENDER_SERVICE = "https://aisp2-baseball.onrender.com"

DEVELOPMENT_RULE = "One file or one directory at a time."


# ============================================================
# SECTION 03 - DEMO DATA
# ============================================================

DEMO_TEAMS = {
    "New York Yankees": {
        "abbreviation": "NYY",
        "league": "American League",
        "division": "AL East",
        "ballpark": "Yankee Stadium",
        "players": [
            "Aaron Judge",
            "Giancarlo Stanton",
            "Gerrit Cole",
        ],
    },
    "Los Angeles Dodgers": {
        "abbreviation": "LAD",
        "league": "National League",
        "division": "NL West",
        "ballpark": "Dodger Stadium",
        "players": [
            "Shohei Ohtani",
            "Mookie Betts",
            "Freddie Freeman",
        ],
    },
    "New York Mets": {
        "abbreviation": "NYM",
        "league": "National League",
        "division": "NL East",
        "ballpark": "Citi Field",
        "players": [
            "Juan Soto",
            "Francisco Lindor",
            "Pete Alonso",
        ],
    },
    "Atlanta Braves": {
        "abbreviation": "ATL",
        "league": "National League",
        "division": "NL East",
        "ballpark": "Truist Park",
        "players": [
            "Ronald Acuna Jr.",
            "Matt Olson",
            "Austin Riley",
        ],
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
    "Aaron Judge": {
        "style": "Elite power hitter",
        "recent_form": "Strong hard-hit profile",
        "primary_metric": "Barrel rate",
        "base_probability": 28,
        "confidence": 74,
    },
    "Shohei Ohtani": {
        "style": "Elite two-way offensive force",
        "recent_form": "High-impact contact profile",
        "primary_metric": "Exit velocity",
        "base_probability": 31,
        "confidence": 77,
    },
    "Juan Soto": {
        "style": "Elite plate discipline hitter",
        "recent_form": "Excellent on-base profile",
        "primary_metric": "OBP and walk rate",
        "base_probability": 66,
        "confidence": 81,
    },
    "Mookie Betts": {
        "style": "Contact and power blend",
        "recent_form": "Stable all-around production",
        "primary_metric": "OPS",
        "base_probability": 61,
        "confidence": 76,
    },
    "Freddie Freeman": {
        "style": "High-contact run producer",
        "recent_form": "Reliable hit profile",
        "primary_metric": "AVG and hard contact",
        "base_probability": 64,
        "confidence": 79,
    },
    "Pete Alonso": {
        "style": "Power-first slugger",
        "recent_form": "Strong home run profile",
        "primary_metric": "HR rate",
        "base_probability": 24,
        "confidence": 68,
    },
    "Ronald Acuna Jr.": {
        "style": "Power-speed superstar",
        "recent_form": "Dynamic offensive profile",
        "primary_metric": "OPS and stolen-base threat",
        "base_probability": 58,
        "confidence": 73,
    },
    "Matt Olson": {
        "style": "Left-handed power hitter",
        "recent_form": "Strong pull-side power",
        "primary_metric": "Hard-hit rate",
        "base_probability": 25,
        "confidence": 70,
    },
    "Austin Riley": {
        "style": "Middle-order power bat",
        "recent_form": "Strong contact authority",
        "primary_metric": "SLG",
        "base_probability": 23,
        "confidence": 69,
    },
    "Giancarlo Stanton": {
        "style": "Extreme power hitter",
        "recent_form": "High variance, high upside",
        "primary_metric": "Exit velocity",
        "base_probability": 22,
        "confidence": 62,
    },
    "Gerrit Cole": {
        "style": "Ace starting pitcher",
        "recent_form": "High strikeout profile",
        "primary_metric": "K rate",
        "base_probability": 57,
        "confidence": 75,
    },
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
        "AI Sports Intelligence Platform 2 - "
        "Baseball analytics, probability, prediction, and AI assistant platform."
    ),
)


# ============================================================
# SECTION 06 - SHARED HELPERS
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
        selected_team
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


def build_option_tags(
    options: list[str],
    selected_value: str,
) -> str:
    html = ""

    for option in options:
        selected = "selected" if option == selected_value else ""
        html += f'<option value="{option}" {selected}>{option}</option>'

    return html


def build_outcome_option_tags(
    selected_value: str,
) -> str:
    html = ""

    for key, label in DEMO_OUTCOMES.items():
        selected = "selected" if key == selected_value else ""
        html += f'<option value="{key}" {selected}>{label}</option>'

    return html


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
                "The Yankees are available in demo mode. "
                "Once database-backed team routes are connected, this chat will pull live team data, "
                "rosters, player stats, and matchup context."
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
            "I can help with baseball intelligence questions like: "
            "home run probability, hit probability, team comparisons, player trends, matchup analysis, "
            "and future model explanations. Right now I am running in sleek demo mode while the real data pipeline is being connected."
        ),
        "intent": "general",
    }


# ============================================================
# SECTION 07 - HOMEPAGE CSS
# ============================================================

def homepage_css() -> str:
    return """
    <style>
        :root {
            --bg-main: #05070b;
            --bg-panel: rgba(12, 18, 31, 0.72);
            --bg-panel-strong: rgba(12, 18, 31, 0.92);
            --border-soft: rgba(255, 255, 255, 0.08);
            --border-bright: rgba(148, 163, 184, 0.22);
            --text-main: #f8fafc;
            --text-muted: #cbd5e1;
            --text-soft: #94a3b8;
            --blue: #38bdf8;
            --blue-strong: #2563eb;
            --green: #22c55e;
            --gold: #d6b46d;
            --shadow-xl: 0 40px 120px rgba(0, 0, 0, 0.58);
            --radius-xl: 34px;
            --radius-lg: 24px;
            --radius-md: 16px;
            --font-main: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        * {
            box-sizing: border-box;
        }

        html {
            scroll-behavior: smooth;
        }

        body {
            margin: 0;
            min-height: 100vh;
            color: var(--text-main);
            font-family: var(--font-main);
            background:
                radial-gradient(circle at 18% 10%, rgba(56, 189, 248, 0.18), transparent 30%),
                radial-gradient(circle at 82% 18%, rgba(34, 197, 94, 0.10), transparent 26%),
                radial-gradient(circle at 50% 100%, rgba(37, 99, 235, 0.16), transparent 36%),
                linear-gradient(135deg, #020617 0%, #05070b 44%, #0b1120 100%);
            overflow-x: hidden;
        }

        body::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background-image:
                linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
            background-size: 64px 64px;
            mask-image: radial-gradient(circle at center, black, transparent 72%);
            z-index: -1;
        }

        a {
            color: inherit;
            text-decoration: none;
        }

        .app-shell {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .topbar {
            position: sticky;
            top: 0;
            z-index: 20;
            height: 72px;
            padding: 0 clamp(18px, 4vw, 56px);
            display: flex;
            align-items: center;
            justify-content: space-between;
            backdrop-filter: blur(22px);
            background: rgba(2, 6, 23, 0.56);
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }

        .brand-mark {
            display: flex;
            align-items: center;
            gap: 12px;
            font-weight: 900;
            letter-spacing: -0.04em;
        }

        .brand-icon {
            width: 34px;
            height: 34px;
            display: grid;
            place-items: center;
            border-radius: 12px;
            background:
                linear-gradient(135deg, rgba(56, 189, 248, 0.24), rgba(34, 197, 94, 0.14));
            border: 1px solid rgba(255, 255, 255, 0.10);
            box-shadow: 0 18px 46px rgba(56, 189, 248, 0.12);
        }

        .nav-links {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .nav-links a {
            color: var(--text-soft);
            font-size: 13px;
            font-weight: 800;
            padding: 10px 12px;
            border-radius: 999px;
            transition: 0.2s ease;
        }

        .nav-links a:hover {
            color: white;
            background: rgba(255, 255, 255, 0.06);
        }

        .hero {
            flex: 1;
            width: min(1120px, calc(100% - 32px));
            margin: 0 auto;
            padding:
                clamp(48px, 8vw, 96px)
                0
                clamp(32px, 6vw, 72px);
            display: grid;
            place-items: center;
        }

        .center-stack {
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
        }

        .eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 20px;
            padding: 9px 14px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.045);
            border: 1px solid rgba(255, 255, 255, 0.08);
            color: var(--text-muted);
            font-size: 12px;
            font-weight: 900;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }

        .pulse {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--green);
            box-shadow: 0 0 0 7px rgba(34, 197, 94, 0.12);
        }

        h1 {
            max-width: 920px;
            margin: 0;
            font-size: clamp(3.4rem, 9vw, 7.8rem);
            line-height: 0.88;
            letter-spacing: -0.09em;
            font-weight: 1000;
            background:
                linear-gradient(135deg, #ffffff 0%, #dbeafe 42%, #7dd3fc 72%, #86efac 100%);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }

        .subtitle {
            width: min(780px, 100%);
            margin: 28px auto 34px;
            color: var(--text-muted);
            font-size: clamp(1.05rem, 2.3vw, 1.42rem);
            line-height: 1.75;
        }

        .chat-panel {
            width: min(920px, 100%);
            border-radius: var(--radius-xl);
            background:
                linear-gradient(180deg, rgba(15, 23, 42, 0.78), rgba(8, 13, 24, 0.92));
            border: 1px solid rgba(255, 255, 255, 0.10);
            box-shadow: var(--shadow-xl);
            overflow: hidden;
            text-align: left;
        }

        .chat-header {
            min-height: 64px;
            padding: 18px 22px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.07);
            background: rgba(255, 255, 255, 0.025);
        }

        .chat-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .assistant-avatar {
            width: 38px;
            height: 38px;
            display: grid;
            place-items: center;
            border-radius: 14px;
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.30), rgba(34, 197, 94, 0.16));
            border: 1px solid rgba(255, 255, 255, 0.10);
        }

        .chat-title strong {
            display: block;
            font-size: 15px;
        }

        .chat-title span {
            display: block;
            margin-top: 2px;
            color: var(--text-soft);
            font-size: 12px;
        }

        .mode-pill {
            padding: 8px 11px;
            border-radius: 999px;
            background: rgba(34, 197, 94, 0.10);
            border: 1px solid rgba(34, 197, 94, 0.22);
            color: #bbf7d0;
            font-size: 11px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        .messages {
            height: clamp(260px, 42vh, 420px);
            padding: 22px;
            overflow-y: auto;
        }

        .message {
            max-width: 82%;
            margin-bottom: 14px;
            padding: 14px 16px;
            border-radius: 18px;
            line-height: 1.62;
            font-size: 14px;
        }

        .bot {
            margin-right: auto;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.07);
            color: var(--text-muted);
        }

        .user {
            margin-left: auto;
            background: linear-gradient(135deg, rgba(37, 99, 235, 0.92), rgba(14, 165, 233, 0.78));
            color: white;
        }

        .suggestions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            padding: 0 22px 20px;
        }

        .suggestion {
            border: 1px solid rgba(255, 255, 255, 0.09);
            background: rgba(255, 255, 255, 0.045);
            color: var(--text-muted);
            border-radius: 999px;
            padding: 10px 13px;
            font-size: 12px;
            font-weight: 800;
            cursor: pointer;
            transition: 0.2s ease;
        }

        .suggestion:hover {
            color: white;
            transform: translateY(-1px);
            border-color: rgba(56, 189, 248, 0.28);
            background: rgba(56, 189, 248, 0.10);
        }

        .input-area {
            display: flex;
            gap: 12px;
            padding: 18px;
            border-top: 1px solid rgba(255, 255, 255, 0.07);
            background: rgba(2, 6, 23, 0.54);
        }

        .input-area input {
            flex: 1;
            min-height: 54px;
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 999px;
            outline: none;
            background: rgba(255, 255, 255, 0.055);
            color: white;
            padding: 0 18px;
            font-size: 15px;
        }

        .input-area input::placeholder {
            color: #64748b;
        }

        .send-button {
            min-width: 112px;
            min-height: 54px;
            border: none;
            border-radius: 999px;
            cursor: pointer;
            color: #020617;
            font-size: 14px;
            font-weight: 950;
            background: linear-gradient(135deg, #7dd3fc, #86efac);
            box-shadow: 0 18px 42px rgba(56, 189, 248, 0.16);
            transition: 0.2s ease;
        }

        .send-button:hover {
            transform: translateY(-1px);
            box-shadow: 0 22px 52px rgba(56, 189, 248, 0.22);
        }

        .quiet-row {
            width: min(920px, 100%);
            margin-top: 18px;
            display: flex;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        .quiet-link {
            color: var(--text-soft);
            font-size: 12px;
            font-weight: 800;
            padding: 9px 12px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.035);
            border: 1px solid rgba(255, 255, 255, 0.055);
        }

        .quiet-link:hover {
            color: white;
            background: rgba(255, 255, 255, 0.065);
        }

        .disclaimer {
            width: min(820px, 100%);
            margin: 20px auto 0;
            color: #64748b;
            font-size: 12px;
            line-height: 1.6;
            text-align: center;
        }

        @media (max-width: 760px) {
            .topbar {
                height: auto;
                padding: 16px 18px;
                align-items: flex-start;
                gap: 12px;
                flex-direction: column;
            }

            .nav-links {
                width: 100%;
                overflow-x: auto;
                padding-bottom: 2px;
            }

            .hero {
                width: min(100% - 24px, 1120px);
                padding-top: 40px;
            }

            .chat-header {
                align-items: flex-start;
                flex-direction: column;
            }

            .message {
                max-width: 94%;
            }

            .input-area {
                flex-direction: column;
            }

            .send-button {
                width: 100%;
            }
        }
    </style>
    """


# ============================================================
# SECTION 08 - MINIMAL CHATBOT HOMEPAGE
# ============================================================

@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{PROJECT_NAME} | Baseball Intelligence Chat</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {homepage_css()}
</head>

<body>
    <div class="app-shell">

        <header class="topbar">
            <a class="brand-mark" href="/">
                <span class="brand-icon">⚾</span>
                <span>AISP2</span>
            </a>

            <nav class="nav-links" aria-label="Primary navigation">
                <a href="/tools/prediction">Predictions</a>
                <a href="/project/status">Status</a>
                <a href="/project/data-sources">Sources</a>
                <a href="/project/ml-roadmap">Models</a>
                <a href="/docs">API</a>
            </nav>
        </header>

        <main class="hero">
            <section class="center-stack">

                <div class="eyebrow">
                    <span class="pulse"></span>
                    Baseball Intelligence Engine
                </div>

                <h1>AISP2</h1>

                <p class="subtitle">
                    Ask about players, teams, matchups, probabilities, props,
                    Statcast trends, projections, and future model explanations.
                </p>

                <section class="chat-panel" aria-label="AISP2 chat assistant">

                    <div class="chat-header">
                        <div class="chat-title">
                            <div class="assistant-avatar">AI</div>
                            <div>
                                <strong>AISP2 Analyst</strong>
                                <span>Minimal demo mode · real data pipeline coming online</span>
                            </div>
                        </div>

                        <div class="mode-pill">Online</div>
                    </div>

                    <div class="messages" id="messages">
                        <div class="message bot">
                            Welcome to AISP2. Ask me about a player, team, matchup,
                            home run probability, hit probability, roster trend, or future projection.
                        </div>
                    </div>

                    <div class="suggestions">
                        <button class="suggestion" data-prompt="What is Aaron Judge's home run outlook?">
                            Judge HR outlook
                        </button>

                        <button class="suggestion" data-prompt="Compare Shohei Ohtani and Juan Soto.">
                            Ohtani vs Soto
                        </button>

                        <button class="suggestion" data-prompt="How will AISP2 calculate win probability?">
                            Win probability
                        </button>

                        <button class="suggestion" data-prompt="Show me how player prop predictions will work.">
                            Prop predictions
                        </button>
                    </div>

                    <form class="input-area" id="chat-form">
                        <input
                            id="chat-input"
                            type="text"
                            placeholder="Ask AISP2 anything about baseball..."
                            autocomplete="off"
                            maxlength="900"
                        >

                        <button class="send-button" type="submit">
                            Ask
                        </button>
                    </form>

                </section>

                <div class="quiet-row">
                    <a class="quiet-link" href="/tools/prediction">Open prediction demo</a>
                    <a class="quiet-link" href="/project/roadmap">View roadmap</a>
                    <a class="quiet-link" href="/project/files">File inventory</a>
                    <a class="quiet-link" href="/health">Health</a>
                </div>

                <p class="disclaimer">
                    Demo assistant only. AISP2 is an experimental sports analytics platform.
                    It is not gambling advice, financial advice, or a guarantee of outcomes.
                </p>

            </section>
        </main>

    </div>

    <script>
        const form = document.getElementById("chat-form");
        const input = document.getElementById("chat-input");
        const messages = document.getElementById("messages");
        const suggestions = document.querySelectorAll(".suggestion");

        function appendMessage(text, type) {{
            const node = document.createElement("div");
            node.className = "message " + type;
            node.innerText = text;
            messages.appendChild(node);
            messages.scrollTop = messages.scrollHeight;
            return node;
        }}

        async function sendMessage(text) {{
            const cleanText = text.trim();

            if (!cleanText) {{
                return;
            }}

            appendMessage(cleanText, "user");
            input.value = "";

            const loadingNode = appendMessage("Thinking...", "bot");

            try {{
                const response = await fetch("/api/chat", {{
                    method: "POST",
                    headers: {{
                        "Content-Type": "application/json"
                    }},
                    body: JSON.stringify({{
                        message: cleanText
                    }})
                }});

                const payload = await response.json();

                loadingNode.innerText = payload.reply || "I am ready for your next baseball question.";

            }} catch (error) {{
                loadingNode.innerText = "AISP2 is having trouble responding right now. The interface is online, but the assistant backend needs attention.";
            }}
        }}

        form.addEventListener("submit", function(event) {{
            event.preventDefault();
            sendMessage(input.value);
        }});

        suggestions.forEach(function(button) {{
            button.addEventListener("click", function() {{
                sendMessage(button.dataset.prompt);
            }});
        }});

        setTimeout(function() {{
            input.focus();
        }}, 300);
    </script>
</body>
</html>
"""


# ============================================================
# SECTION 09 - CHAT API ENDPOINT
# ============================================================

@app.post("/api/chat")
def chat_api(request: ChatRequest) -> dict:
    return build_chat_reply(
        request.message,
    )


# ============================================================
# SECTION 10 - PREDICTION TOOL PAGE
# ============================================================

@app.get("/tools/prediction", response_class=HTMLResponse)
def prediction_tool(
    team: str | None = None,
    player: str | None = None,
    outcome: str | None = None,
) -> str:
    selected_team, selected_player, selected_outcome = normalize_demo_selection(
        team_name=team,
        player_name=player,
        outcome_key=outcome,
    )

    team_data = DEMO_TEAMS[selected_team]
    available_players = get_available_players(selected_team)

    prediction = build_demo_probability(
        player_name=selected_player,
        outcome_key=selected_outcome,
    )

    probability = prediction["probability"]
    confidence = prediction["confidence"]
    profile = prediction["profile"]
    outcome_label = DEMO_OUTCOMES[selected_outcome]

    team_options = build_option_tags(
        options=list(DEMO_TEAMS.keys()),
        selected_value=selected_team,
    )

    player_options = build_option_tags(
        options=available_players,
        selected_value=selected_player,
    )

    outcome_options = build_outcome_option_tags(
        selected_value=selected_outcome,
    )

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AISP2 Prediction Demo</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {homepage_css()}
    <style>
        .tool-wrap {{
            width: min(1100px, calc(100% - 32px));
            margin: 0 auto;
            padding: 54px 0;
        }}

        .tool-card {{
            padding: 26px;
            border-radius: 28px;
            background: rgba(15, 23, 42, 0.76);
            border: 1px solid rgba(255, 255, 255, 0.09);
            box-shadow: var(--shadow-xl);
        }}

        .tool-title {{
            font-size: clamp(2rem, 5vw, 4rem);
            letter-spacing: -0.07em;
            margin: 0 0 12px;
        }}

        .tool-subtitle {{
            color: var(--text-muted);
            line-height: 1.7;
            margin-bottom: 24px;
        }}

        .form-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
            margin-bottom: 16px;
        }}

        label {{
            display: block;
            color: var(--text-soft);
            font-size: 12px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 0.10em;
            margin-bottom: 8px;
        }}

        select {{
            width: 100%;
            min-height: 52px;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.10);
            background: rgba(2, 6, 23, 0.72);
            color: white;
            padding: 0 14px;
            font-size: 15px;
        }}

        .result {{
            margin-top: 22px;
            padding: 26px;
            border-radius: 26px;
            background:
                linear-gradient(145deg, rgba(8, 47, 73, 0.88), rgba(15, 23, 42, 0.92));
            border: 1px solid rgba(56, 189, 248, 0.24);
        }}

        .big-number {{
            font-size: clamp(4rem, 10vw, 7rem);
            line-height: 0.9;
            font-weight: 1000;
            letter-spacing: -0.08em;
            color: #86efac;
        }}

        .result-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 18px;
            margin-top: 22px;
        }}

        .mini {{
            padding: 16px;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.07);
        }}

        .mini span {{
            display: block;
            color: var(--text-soft);
            font-size: 12px;
            font-weight: 900;
            text-transform: uppercase;
            margin-bottom: 7px;
        }}

        .mini strong {{
            color: white;
        }}

        @media (max-width: 760px) {{
            .form-grid, .result-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>

<body>
    <header class="topbar">
        <a class="brand-mark" href="/">
            <span class="brand-icon">⚾</span>
            <span>AISP2</span>
        </a>

        <nav class="nav-links">
            <a href="/">Chat</a>
            <a href="/project/status">Status</a>
            <a href="/docs">API</a>
        </nav>
    </header>

    <main class="tool-wrap">
        <section class="tool-card">
            <p class="eyebrow">
                <span class="pulse"></span>
                Demo Prediction Tool
            </p>

            <h1 class="tool-title">Prediction Workbench</h1>

            <p class="tool-subtitle">
                A clean hidden tool page for early probability-card testing.
                The homepage stays minimal and chat-first.
            </p>

            <form method="get" action="/tools/prediction">
                <div class="form-grid">
                    <div>
                        <label>Team</label>
                        <select name="team">
                            {team_options}
                        </select>
                    </div>

                    <div>
                        <label>Player</label>
                        <select name="player">
                            {player_options}
                        </select>
                    </div>

                    <div>
                        <label>Outcome</label>
                        <select name="outcome">
                            {outcome_options}
                        </select>
                    </div>
                </div>

                <button class="send-button" type="submit">
                    Run Demo Prediction
                </button>
            </form>

            <section class="result">
                <p class="eyebrow">
                    {selected_team} · {team_data["abbreviation"]} · {outcome_label}
                </p>

                <h2 style="margin:0 0 18px; font-size:2rem;">
                    {selected_player}
                </h2>

                <div class="big-number">
                    {probability}%
                </div>

                <p style="color:var(--text-muted); line-height:1.8; margin-top:18px;">
                    Demo probability with {confidence}% confidence.
                    Future versions will use live data, Statcast trends, matchup context,
                    park factors, and machine learning models.
                </p>

                <div class="result-grid">
                    <div class="mini">
                        <span>Player Style</span>
                        <strong>{profile["style"]}</strong>
                    </div>

                    <div class="mini">
                        <span>Recent Form</span>
                        <strong>{profile["recent_form"]}</strong>
                    </div>

                    <div class="mini">
                        <span>Primary Metric</span>
                        <strong>{profile["primary_metric"]}</strong>
                    </div>

                    <div class="mini">
                        <span>Ballpark</span>
                        <strong>{team_data["ballpark"]}</strong>
                    </div>
                </div>
            </section>
        </section>
    </main>
</body>
</html>
"""


# ============================================================
# SECTION 11 - DEMO PREDICTION JSON ENDPOINT
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
        "homepage": "minimal chatbot-first interface",
        "next_best_endpoint": "/",
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
        "homepage": "minimal chatbot-first interface",
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
            "database_layer": "CREATED",
            "project_ledger": "CREATED",
            "mlb_stats_api_client": "CREATED",
            "team_ingestion": "CREATED",
            "minimal_chat_homepage": "CREATED",
        },
        "current_focus": "Chat-first homepage and clean AI product experience",
        "next_target": "Real data-backed team and player tools",
        "development_rule": DEVELOPMENT_RULE,
    }


@app.get("/project/roadmap")
def project_roadmap() -> dict:
    return {
        "current_file": "main.py",
        "current_focus": "Minimal chatbot-first homepage",
        "completed": [
            "GitHub repository",
            "Render deployment",
            "Database layer",
            "Models",
            "MLB Stats API client",
            "Team ingestion engine",
            "Minimal chatbot homepage",
            "Prediction demo tool",
        ],
        "next_files": [
            "static/aisp2.css",
            "static/aisp2.js",
            "ai_assistant_outline.md",
            "ai_chat_engine.py",
            "team_explorer.py",
            "player_explorer.py",
            "probability_engine.py",
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
            "Select teams and players later",
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
            "static/aisp2.css",
            "static/aisp2.js",
            "ai_assistant_outline.md",
        ],
    }


@app.get("/project/next-action")
def project_next_action() -> dict:
    return {
        "current_rule": DEVELOPMENT_RULE,
        "next_action": "Deploy and review minimal chatbot homepage",
        "after_that": "Move inline CSS and JS into static files",
        "goal": "Keep homepage sleek while advanced tools live behind toolbar links",
    }


# ============================================================
# SECTION 14 - LOCAL STARTUP VALIDATION
# ============================================================

if __name__ == "__main__":
    print("AISP2 Baseball loaded successfully.")
    print("Minimal chatbot-first homepage initialized.")
    print(f"Project: {PROJECT_NAME}")
    print(f"Version: {PROJECT_VERSION}")
    print(f"Phase: {PROJECT_PHASE}")


# ============================================================
# SECTION 15 - FUTURE APPLICATION ROADMAP
# ============================================================

"""
Future Application Roadmap

Phase 1.01:
    Extract homepage CSS into static/aisp2.css.

Phase 1.02:
    Extract homepage JavaScript into static/aisp2.js.

Phase 1.03:
    Create ai_assistant_outline.md.

Phase 1.04:
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
"""