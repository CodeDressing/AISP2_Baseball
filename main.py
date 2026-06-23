# ============================================================
# AISP2 BASEBALL
# PHASE 1.00 PART 8
# ENTERPRISE VISUAL COMMAND CENTER + DEMO PREDICTION WORKBENCH
# FILE: main.py
# PURPOSE: primary FastAPI startup, visual homepage,
# project visibility, roadmap tracking, demo prediction UI,
# probability-card display, health monitoring, and deployment
# verification for AISP2 Baseball
# ============================================================


# ============================================================
# SECTION 01 - IMPORTS
# ============================================================

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


# ============================================================
# SECTION 02 - APPLICATION METADATA
# ============================================================

PROJECT_NAME = "AISP2 Baseball"
PROJECT_VERSION = "1.0.0"
PROJECT_PHASE = "1.00 Foundation"
SERVICE_NAME = "aisp2-baseball"
PRIMARY_SPORT = "MLB"

GITHUB_REPOSITORY = "https://github.com/CodeDressing/AISP2_Baseball"
RENDER_SERVICE = "https://aisp2-baseball.onrender.com"


# ============================================================
# SECTION 03 - PROJECT STATUS CONSTANTS
# ============================================================

COMPLETED_FOUNDATION_ITEMS = [
    "Local PyCharm project created",
    "Python virtual environment created",
    "GitHub repository connected",
    "Render deployment connected",
    "FastAPI entrypoint deployed",
    "Visual homepage created",
    "Project ledger established",
    "Database connection layer created",
    "Database models created",
    "MLB Stats API client started",
    "Demo Prediction Workbench added",
]

CURRENT_OBJECTIVE = (
    "Make AISP2 visually demonstrate the final baseball intelligence "
    "experience before deeper ingestion and model training."
)

NEXT_TARGET = (
    "Verify MLB Stats API client, then build team ingestion so real "
    "MLB teams can replace demo dropdown data."
)

DEVELOPMENT_RULE = "One file or one directory at a time."


# ============================================================
# SECTION 04 - DEMO DATA
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
# SECTION 05 - APPLICATION INITIALIZATION
# ============================================================

app = FastAPI(
    title=PROJECT_NAME,
    version=PROJECT_VERSION,
    description=(
        "AI Sports Intelligence Platform 2 - "
        "Enterprise Baseball Analytics and Prediction Platform"
    ),
)


# ============================================================
# SECTION 06 - SHARED HTML STYLE SYSTEM
# ============================================================

def shared_css() -> str:
    return """
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            min-height: 100vh;
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.35), transparent 30%),
                radial-gradient(circle at top right, rgba(14, 165, 233, 0.22), transparent 28%),
                linear-gradient(180deg, #020617 0%, #0f172a 48%, #111827 100%);
            color: #f8fafc;
            font-family: Inter, Arial, sans-serif;
            padding: 32px;
        }

        .shell {
            max-width: 1320px;
            margin: 0 auto;
        }

        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 28px;
            gap: 16px;
            flex-wrap: wrap;
        }

        .brand {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .kicker {
            color: #38bdf8;
            font-size: 13px;
            font-weight: 900;
            letter-spacing: 0.18em;
            text-transform: uppercase;
        }

        .brand h1 {
            font-size: 42px;
            letter-spacing: -1.2px;
            font-weight: 950;
        }

        .status-pill {
            background: rgba(22, 163, 74, 0.18);
            border: 1px solid rgba(34, 197, 94, 0.45);
            color: #86efac;
            padding: 10px 16px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 900;
            text-transform: uppercase;
        }

        .hero {
            background:
                linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.80)),
                radial-gradient(circle at top right, rgba(56, 189, 248, 0.28), transparent 34%);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 30px;
            padding: 34px;
            box-shadow: 0 30px 90px rgba(0, 0, 0, 0.36);
            margin-bottom: 24px;
        }

        .hero h2 {
            font-size: 30px;
            margin-bottom: 12px;
        }

        .hero p {
            color: #cbd5e1;
            line-height: 1.7;
            font-size: 16px;
            max-width: 1000px;
        }

        .pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 22px;
        }

        .pill {
            background: rgba(15, 23, 42, 0.82);
            border: 1px solid rgba(148, 163, 184, 0.25);
            padding: 8px 13px;
            border-radius: 999px;
            color: #e2e8f0;
            font-size: 13px;
            font-weight: 800;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 18px;
            margin-bottom: 24px;
        }

        .two-col {
            display: grid;
            grid-template-columns: 1.05fr 0.95fr;
            gap: 20px;
            margin-bottom: 24px;
        }

        .three-col {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 18px;
            margin-bottom: 24px;
        }

        .card {
            background: rgba(15, 23, 42, 0.76);
            border: 1px solid rgba(148, 163, 184, 0.20);
            border-radius: 22px;
            padding: 22px;
            box-shadow: 0 18px 55px rgba(0, 0, 0, 0.25);
        }

        .metric-label {
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 12px;
            font-weight: 900;
            margin-bottom: 8px;
        }

        .metric-value {
            font-size: 30px;
            font-weight: 950;
            color: #ffffff;
        }

        .metric-note {
            margin-top: 8px;
            color: #94a3b8;
            font-size: 13px;
            line-height: 1.5;
        }

        .section-title {
            color: #ffffff;
            font-size: 22px;
            font-weight: 950;
            margin-bottom: 14px;
        }

        ul {
            padding-left: 22px;
            color: #cbd5e1;
            line-height: 1.9;
        }

        .timeline {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .step {
            border-left: 3px solid #38bdf8;
            padding: 12px 14px;
            background: rgba(2, 6, 23, 0.32);
            border-radius: 12px;
        }

        .step strong {
            display: block;
            color: #ffffff;
            margin-bottom: 4px;
        }

        .step span {
            color: #94a3b8;
            font-size: 14px;
        }

        .links {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            margin-bottom: 24px;
        }

        a.button, button.button {
            display: block;
            width: 100%;
            text-decoration: none;
            text-align: center;
            padding: 14px 16px;
            border-radius: 16px;
            color: #f8fafc;
            font-weight: 900;
            background: rgba(37, 99, 235, 0.22);
            border: 1px solid rgba(96, 165, 250, 0.38);
            cursor: pointer;
        }

        a.button:hover, button.button:hover {
            background: rgba(37, 99, 235, 0.36);
        }

        .footer {
            color: #64748b;
            text-align: center;
            font-size: 13px;
            padding: 22px 0 8px;
        }

        .warning {
            background: rgba(120, 53, 15, 0.46);
            border: 1px solid rgba(245, 158, 11, 0.44);
            color: #fde68a;
            padding: 14px 18px;
            border-radius: 16px;
            margin-bottom: 22px;
            line-height: 1.6;
            font-size: 14px;
        }

        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 16px;
            margin-bottom: 18px;
        }

        label {
            display: block;
            color: #94a3b8;
            font-size: 12px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 8px;
        }

        select {
            width: 100%;
            background: rgba(2, 6, 23, 0.76);
            color: #f8fafc;
            border: 1px solid rgba(148, 163, 184, 0.32);
            border-radius: 14px;
            padding: 13px 14px;
            font-size: 15px;
            outline: none;
        }

        .prediction-card {
            background:
                linear-gradient(145deg, rgba(8, 47, 73, 0.92), rgba(15, 23, 42, 0.92)),
                radial-gradient(circle at top right, rgba(34, 197, 94, 0.18), transparent 30%);
            border: 1px solid rgba(56, 189, 248, 0.30);
            border-radius: 28px;
            padding: 28px;
            box-shadow: 0 26px 80px rgba(14, 165, 233, 0.16);
        }

        .prediction-title {
            font-size: 28px;
            font-weight: 950;
            margin-bottom: 8px;
        }

        .prediction-subtitle {
            color: #cbd5e1;
            line-height: 1.6;
            margin-bottom: 22px;
        }

        .probability {
            font-size: 72px;
            font-weight: 1000;
            letter-spacing: -2px;
            color: #86efac;
            line-height: 1;
        }

        .confidence {
            font-size: 38px;
            font-weight: 950;
            color: #38bdf8;
        }

        .bar-shell {
            width: 100%;
            height: 14px;
            background: rgba(2, 6, 23, 0.72);
            border-radius: 999px;
            overflow: hidden;
            border: 1px solid rgba(148, 163, 184, 0.18);
            margin-top: 10px;
        }

        .bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #22c55e, #38bdf8);
            border-radius: 999px;
        }

        .stat-list {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-top: 18px;
        }

        .stat-chip {
            background: rgba(15, 23, 42, 0.70);
            border: 1px solid rgba(148, 163, 184, 0.20);
            border-radius: 16px;
            padding: 14px;
        }

        .stat-chip span {
            display: block;
            color: #94a3b8;
            font-size: 12px;
            font-weight: 900;
            text-transform: uppercase;
            margin-bottom: 5px;
        }

        .stat-chip strong {
            color: #ffffff;
            font-size: 16px;
        }

        .small-note {
            color: #94a3b8;
            font-size: 13px;
            line-height: 1.6;
        }

        @media (max-width: 1000px) {
            .grid {
                grid-template-columns: repeat(2, 1fr);
            }

            .two-col, .three-col, .form-grid {
                grid-template-columns: 1fr;
            }

            .links {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 640px) {
            body {
                padding: 18px;
            }

            .brand h1 {
                font-size: 30px;
            }

            .grid {
                grid-template-columns: 1fr;
            }

            .links {
                grid-template-columns: 1fr;
            }

            .probability {
                font-size: 56px;
            }
        }
    </style>
    """


# ============================================================
# SECTION 07 - DEMO PREDICTION HELPERS
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

    confidence = profile["confidence"]

    return {
        "probability": probability,
        "confidence": confidence,
        "profile": profile,
    }


def build_option_tags(
    options: list[str],
    selected_value: str,
) -> str:
    html = ""

    for option in options:
        selected = "selected" if option == selected_value else ""
        html += f"<option value=\"{option}\" {selected}>{option}</option>"

    return html


def build_outcome_option_tags(
    selected_value: str,
) -> str:
    html = ""

    for key, label in DEMO_OUTCOMES.items():
        selected = "selected" if key == selected_value else ""
        html += f"<option value=\"{key}\" {selected}>{label}</option>"

    return html


# ============================================================
# SECTION 08 - ROOT VISUAL COMMAND CENTER
# ============================================================

@app.get("/", response_class=HTMLResponse)
def root() -> str:
    completed_items_html = ""

    for item in COMPLETED_FOUNDATION_ITEMS:
        completed_items_html += f"<li>{item}</li>"

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{PROJECT_NAME} Command Center</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {shared_css()}
</head>

<body>
    <main class="shell">

        <div class="topbar">
            <div class="brand">
                <div class="kicker">AI Sports Intelligence Platform</div>
                <h1>{PROJECT_NAME}</h1>
            </div>

            <div class="status-pill">Online</div>
        </div>

        <section class="hero">
            <h2>Enterprise Baseball Intelligence Command Center</h2>
            <p>
                AISP2 Baseball is being built as a long-term baseball analytics,
                probability, machine learning, simulation, and prediction platform.
                This page now includes the first visible version of the future
                baseball prediction experience.
            </p>

            <div class="pill-row">
                <span class="pill">GitHub Connected</span>
                <span class="pill">Render Connected</span>
                <span class="pill">FastAPI Live</span>
                <span class="pill">Database Layer Started</span>
                <span class="pill">MLB Data Source Layer Started</span>
                <span class="pill">Prediction Demo Added</span>
            </div>
        </section>

        <div class="warning">
            AISP2 is an experimental sports analytics and machine learning platform.
            Demo probabilities are illustrative only until real ingestion and model
            training are connected.
        </div>

        <section class="grid">
            <div class="card">
                <div class="metric-label">Project Phase</div>
                <div class="metric-value">{PROJECT_PHASE}</div>
                <div class="metric-note">Foundation and visibility layer.</div>
            </div>

            <div class="card">
                <div class="metric-label">Deployment</div>
                <div class="metric-value">Live</div>
                <div class="metric-note">Running on Render.</div>
            </div>

            <div class="card">
                <div class="metric-label">Primary Sport</div>
                <div class="metric-value">{PRIMARY_SPORT}</div>
                <div class="metric-note">Major League Baseball first.</div>
            </div>

            <div class="card">
                <div class="metric-label">Visible Product</div>
                <div class="metric-value">Demo</div>
                <div class="metric-note">Prediction Workbench is now available.</div>
            </div>
        </section>

        <section class="two-col">
            <div class="card">
                <div class="section-title">What Has Been Completed</div>
                <ul>
                    {completed_items_html}
                </ul>
            </div>

            <div class="card">
                <div class="section-title">Build Timeline</div>

                <div class="timeline">
                    <div class="step">
                        <strong>Phase 1.00 - Foundation</strong>
                        <span>Project, GitHub, Render, FastAPI, visual command center.</span>
                    </div>

                    <div class="step">
                        <strong>Phase 2.00 - MLB Data Sources</strong>
                        <span>Connect official MLB Stats API and prepare ingestion.</span>
                    </div>

                    <div class="step">
                        <strong>Phase 3.00 - Ingestion</strong>
                        <span>Load teams, players, rosters, schedules, and stats.</span>
                    </div>

                    <div class="step">
                        <strong>Phase 4.00 - Probability Engine</strong>
                        <span>Replace demo cards with real prediction models.</span>
                    </div>
                </div>
            </div>
        </section>

        <section class="two-col">
            <div class="prediction-card">
                <div class="metric-label">First Visible Product Feature</div>
                <div class="prediction-title">Demo Prediction Workbench</div>
                <p class="prediction-subtitle">
                    Select a team, player, and outcome to see the future AISP2
                    probability-card experience. This is the visual target that
                    future ingestion, statistics, and machine learning will power.
                </p>
                <a class="button" href="/demo/prediction">Open Prediction Workbench</a>
            </div>

            <div class="card">
                <div class="section-title">Next Real Backend Target</div>
                <p style="color:#cbd5e1; line-height:1.7;">
                    {NEXT_TARGET}
                </p>

                <br>

                <div class="section-title">Development Rule</div>
                <p style="color:#94a3b8; line-height:1.7;">
                    {DEVELOPMENT_RULE}
                </p>
            </div>
        </section>

        <section class="links">
            <a class="button" href="/demo/prediction">Prediction Demo</a>
            <a class="button" href="/project/status">Project Status</a>
            <a class="button" href="/project/roadmap">Roadmap</a>
            <a class="button" href="/project/data-sources">Data Sources</a>
            <a class="button" href="/project/ml-roadmap">ML Roadmap</a>
            <a class="button" href="/project/probability-output-design">Prediction Design</a>
            <a class="button" href="/project/files">File Inventory</a>
            <a class="button" href="/docs">API Docs</a>
        </section>

        <div class="footer">
            {PROJECT_NAME} · {PROJECT_PHASE} · Version {PROJECT_VERSION} · Built by Ryan with Alfred
        </div>

    </main>
</body>
</html>
"""


# ============================================================
# SECTION 09 - DEMO PREDICTION WORKBENCH
# ============================================================

@app.get("/demo/prediction", response_class=HTMLResponse)
def demo_prediction(
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

    outcome_label = DEMO_OUTCOMES[selected_outcome]

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AISP2 Prediction Workbench</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {shared_css()}
</head>

<body>
    <main class="shell">

        <div class="topbar">
            <div class="brand">
                <div class="kicker">AISP2 Demo Product Experience</div>
                <h1>Prediction Workbench</h1>
            </div>

            <div class="status-pill">Demo Mode</div>
        </div>

        <section class="hero">
            <h2>Select Team · Select Player · Select Outcome</h2>
            <p>
                This page is the first visual version of the future AISP2
                prediction interface. The data is currently demo-only, but the
                layout, user flow, and probability-card design represent the
                experience we are building toward with real MLB ingestion,
                feature engineering, and machine learning.
            </p>

            <div class="pill-row">
                <span class="pill">Human-Friendly UI</span>
                <span class="pill">Probability Card</span>
                <span class="pill">Confidence Score</span>
                <span class="pill">Supporting Stats</span>
                <span class="pill">Plain-English Explanation</span>
            </div>
        </section>

        <div class="warning">
            Demo mode: These probabilities are illustrative placeholders.
            They are not real predictions and should not be used for betting,
            wagering, financial, or professional decisions.
        </div>

        <section class="card">
            <div class="section-title">Prediction Controls</div>

            <form method="get" action="/demo/prediction">
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

                <button class="button" type="submit">
                    Run Demo Prediction
                </button>
            </form>

            <p class="small-note" style="margin-top:14px;">
                Note: In this early demo, changing teams and clicking Run updates
                the player list for that selected team.
            </p>
        </section>

        <br>

        <section class="two-col">
            <div class="prediction-card">
                <div class="metric-label">AISP2 Demo Probability Card</div>
                <div class="prediction-title">{selected_player}</div>
                <p class="prediction-subtitle">
                    {selected_team} · {team_data["abbreviation"]} · {outcome_label}
                </p>

                <div class="three-col">
                    <div>
                        <div class="metric-label">Estimated Probability</div>
                        <div class="probability">{probability}%</div>
                        <div class="bar-shell">
                            <div class="bar-fill" style="width:{probability}%;"></div>
                        </div>
                    </div>

                    <div>
                        <div class="metric-label">Confidence</div>
                        <div class="confidence">{confidence}%</div>
                        <div class="bar-shell">
                            <div class="bar-fill" style="width:{confidence}%;"></div>
                        </div>
                    </div>

                    <div>
                        <div class="metric-label">Model</div>
                        <div class="metric-value">Demo</div>
                        <div class="metric-note">Future: AISP Baseline Probability Engine.</div>
                    </div>
                </div>

                <div class="stat-list">
                    <div class="stat-chip">
                        <span>Player Style</span>
                        <strong>{profile["style"]}</strong>
                    </div>

                    <div class="stat-chip">
                        <span>Recent Form</span>
                        <strong>{profile["recent_form"]}</strong>
                    </div>

                    <div class="stat-chip">
                        <span>Primary Metric</span>
                        <strong>{profile["primary_metric"]}</strong>
                    </div>

                    <div class="stat-chip">
                        <span>Ballpark</span>
                        <strong>{team_data["ballpark"]}</strong>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="section-title">Plain-English Explanation</div>
                <p style="color:#cbd5e1; line-height:1.8;">
                    AISP2 currently projects <strong>{selected_player}</strong>
                    for <strong>{outcome_label}</strong> using demo values based on
                    player archetype, recent form, team context, and a simplified
                    probability profile.
                </p>

                <br>

                <p style="color:#cbd5e1; line-height:1.8;">
                    In the real version, this card will be powered by MLB Stats API,
                    Baseball Savant / Statcast, FanGraphs, rolling trends,
                    matchup context, park factors, and supervised learning models.
                </p>

                <br>

                <div class="section-title">Future Data Sources</div>
                <ul>
                    <li>MLB Stats API</li>
                    <li>Baseball Savant / Statcast</li>
                    <li>FanGraphs</li>
                    <li>Baseball Reference</li>
                    <li>Retrosheet</li>
                    <li>Lahman Database</li>
                </ul>
            </div>
        </section>

        <section class="links">
            <a class="button" href="/">Command Center</a>
            <a class="button" href="/api/demo/prediction?team={selected_team}&player={selected_player}&outcome={selected_outcome}">
                JSON Prediction
            </a>
            <a class="button" href="/project/probability-output-design">Prediction Design</a>
            <a class="button" href="/project/next-action">Next Action</a>
        </section>

        <div class="footer">
            AISP2 Demo Prediction Workbench · Visual Target for Future Real Model Output
        </div>

    </main>
</body>
</html>
"""


# ============================================================
# SECTION 10 - DEMO PREDICTION JSON ENDPOINT
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
# SECTION 11 - ROOT JSON ENDPOINT
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
        "next_best_endpoint": "/demo/prediction",
    }


# ============================================================
# SECTION 12 - HEALTH ENDPOINT
# ============================================================

@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "project": PROJECT_NAME,
        "phase": PROJECT_PHASE,
    }


# ============================================================
# SECTION 13 - SYSTEM INFORMATION
# ============================================================

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
# SECTION 14 - PROJECT STATUS ENDPOINT
# ============================================================

@app.get("/project/status")
def project_status() -> dict:
    return {
        "project": PROJECT_NAME,
        "status": "ACTIVE DEVELOPMENT",
        "phase": PROJECT_PHASE,
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
            "local_project": "CREATED",
            "python_environment": "CREATED",
            "github_repository": "CREATED",
            "render_web_service": "CREATED",
            "fastapi_entrypoint": "LIVE",
            "database_layer": "CREATED",
            "project_ledger": "CREATED",
            "visual_homepage": "CREATED",
            "demo_prediction_workbench": "CREATED",
        },
        "current_focus": "Visible product experience and MLB data source verification",
        "next_target": "Team ingestion from MLB Stats API",
        "development_rule": DEVELOPMENT_RULE,
    }


# ============================================================
# SECTION 15 - PROJECT ROADMAP ENDPOINT
# ============================================================

@app.get("/project/roadmap")
def project_roadmap() -> dict:
    return {
        "completed": [
            "GitHub repository",
            "Render deployment",
            "Visual homepage",
            "Demo Prediction Workbench",
            "requirements.txt",
            "PROJECT_LEDGER.md",
            "01_database/database.py",
            "01_database/models.py",
            "02_data_sources/mlb_stats_api.py",
        ],
        "current_phase": {
            "name": "Phase 1.00 Foundation + Product Visibility",
            "objective": "Create a visible and deployable foundation for AISP2 Baseball",
            "status": "active",
        },
        "next_phase": {
            "name": "Phase 3.00 Ingestion",
            "objective": "Move official MLB data into the AISP2 database",
            "first_file": "03_ingestion/team_ingestion.py",
        },
        "future_phases": [
            "Team ingestion",
            "Roster ingestion",
            "Player ingestion",
            "Player season stat ingestion",
            "Statcast integration",
            "Feature engineering",
            "Probability engine",
            "Machine learning models",
            "Monte Carlo simulation",
            "Human-friendly dashboard",
        ],
    }


# ============================================================
# SECTION 16 - PROJECT VISION ENDPOINT
# ============================================================

@app.get("/project/vision")
def project_vision() -> dict:
    return {
        "vision": "Build the best baseball intelligence platform possible.",
        "mission": (
            "Combine authoritative baseball data, advanced statistics, "
            "machine learning, probability modeling, simulation, and "
            "plain-English explanations into one enterprise-grade platform."
        ),
        "core_user_workflow": [
            "Select team",
            "Select opponent",
            "Select player",
            "Select outcome",
            "Run probability engine",
            "View probability",
            "View confidence",
            "View supporting stats",
            "Read plain-English explanation",
        ],
        "example_outputs": [
            "Aaron Judge home run probability",
            "Juan Soto hit probability",
            "Yankees win probability",
            "Pitcher strikeout probability",
            "Player over/under total bases probability",
        ],
    }


# ============================================================
# SECTION 17 - DATA SOURCE ROADMAP ENDPOINT
# ============================================================

@app.get("/project/data-sources")
def project_data_sources() -> dict:
    return {
        "primary_goal": "Use the best available sources for teams, players, rosters, stats, Statcast, and historical baseball data.",
        "tier_1_sources": [
            {
                "name": "MLB Stats API",
                "status": "active_foundation",
                "purpose": "Official teams, rosters, players, schedules, standings, stats, and games",
            },
            {
                "name": "Baseball Savant / Statcast",
                "status": "planned",
                "purpose": "Pitch-level tracking, batted-ball data, expected stats, launch angle, exit velocity",
            },
        ],
        "tier_2_sources": [
            {
                "name": "FanGraphs",
                "status": "planned",
                "purpose": "Advanced batting, pitching, WAR, leaderboards, projections, and plate discipline metrics",
            },
            {
                "name": "Baseball Reference",
                "status": "planned",
                "purpose": "Historical player, team, game, and season statistics",
            },
        ],
        "historical_sources": [
            {
                "name": "Retrosheet",
                "status": "planned",
                "purpose": "Historical play-by-play and game event archives",
            },
            {
                "name": "Lahman Database",
                "status": "planned",
                "purpose": "Historical baseball database for long-term model training",
            },
        ],
    }


# ============================================================
# SECTION 18 - MACHINE LEARNING ROADMAP ENDPOINT
# ============================================================

@app.get("/project/ml-roadmap")
def project_machine_learning_roadmap() -> dict:
    return {
        "course_concepts_to_apply": [
            "Supervised Machine Learning",
            "Advanced Learning Algorithms",
            "Unsupervised Learning",
            "Recommender Systems",
            "Reinforcement Learning",
        ],
        "supervised_learning_targets": [
            "Hit probability",
            "Home run probability",
            "Strikeout probability",
            "Walk probability",
            "RBI probability",
            "Run scored probability",
            "Game winner probability",
        ],
        "baseline_models": [
            "Logistic Regression",
            "Random Forest",
            "Gradient Boosting",
            "XGBoost",
            "LightGBM",
        ],
        "advanced_models": [
            "Ensemble models",
            "Bayesian models",
            "Time-series models",
            "Neural networks",
        ],
        "unsupervised_learning_targets": [
            "Similar player clustering",
            "Pitcher archetypes",
            "Hitter archetypes",
            "Team style clustering",
        ],
        "recommender_system_targets": [
            "Similar players",
            "Comparable hitters",
            "Comparable pitchers",
            "Comparable team profiles",
        ],
        "reinforcement_learning_targets": [
            "Lineup optimization",
            "Bullpen management simulation",
            "In-game decision strategy",
        ],
    }


# ============================================================
# SECTION 19 - PROBABILITY OUTPUT DESIGN ENDPOINT
# ============================================================

@app.get("/project/probability-output-design")
def probability_output_design() -> dict:
    return {
        "goal": "Every prediction should be readable, explainable, and useful.",
        "current_demo_endpoint": "/demo/prediction",
        "future_prediction_card": {
            "player": "Aaron Judge",
            "team": "New York Yankees",
            "outcome": "Hits a home run",
            "estimated_probability": "Example: 28%",
            "confidence": "Example: 74%",
            "model": "AISP Baseline Probability Engine",
            "data_sources_used": [
                "MLB Stats API",
                "Baseball Savant / Statcast",
                "FanGraphs",
            ],
            "supporting_statistics": [
                "Recent home run rate",
                "Season OPS",
                "Exit velocity trend",
                "Launch angle trend",
                "Opponent pitcher profile",
                "Ballpark factor",
            ],
        },
    }


# ============================================================
# SECTION 20 - FILE INVENTORY ENDPOINT
# ============================================================

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
        "next_directory": "03_ingestion",
        "next_file": "03_ingestion/team_ingestion.py",
    }


# ============================================================
# SECTION 21 - NEXT ACTION ENDPOINT
# ============================================================

@app.get("/project/next-action")
def project_next_action() -> dict:
    return {
        "current_rule": DEVELOPMENT_RULE,
        "next_action": "Verify the demo prediction UI after Render deploy",
        "after_that": "Verify MLB Stats API client locally",
        "then": "Create 03_ingestion/team_ingestion.py",
        "goal": "Load official MLB teams into the AISP2 database",
    }


# ============================================================
# SECTION 22 - LOCAL STARTUP VALIDATION
# ============================================================

if __name__ == "__main__":
    print("AISP2 Baseball loaded successfully.")
    print("FastAPI visual command center initialized.")
    print("Demo Prediction Workbench initialized.")
    print(f"Project: {PROJECT_NAME}")
    print(f"Version: {PROJECT_VERSION}")
    print(f"Phase: {PROJECT_PHASE}")


# ============================================================
# SECTION 23 - FUTURE APPLICATION ROADMAP
# ============================================================

"""
Future API Expansion

Phase 2.00
    Team routes

Phase 2.01
    Player routes

Phase 2.02
    Statistics routes

Phase 2.03
    Roster routes

Phase 3.00
    Feature engineering routes

Phase 4.00
    Probability engine routes

Phase 5.00
    Machine learning routes

Phase 6.00
    Simulation routes

Phase 7.00
    Dashboard integration

Future Human UI

A future dashboard should convert these endpoints into:
    - team selectors
    - player selectors
    - live data status panels
    - database health visuals
    - prediction result cards
    - probability charts
    - confidence explanations
    - model comparison views
"""