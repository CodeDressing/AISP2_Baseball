# ============================================================
# AISP2 BASEBALL
# PHASE 1.00 PART 7
# ENTERPRISE VISUAL COMMAND CENTER
# FILE: main.py
# PURPOSE: primary FastAPI startup, visual homepage,
# project visibility, roadmap tracking, health monitoring,
# data-source roadmap, ML roadmap, and deployment verification
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
    "Project ledger established",
    "Database connection layer created",
    "Database models created",
    "MLB Stats API client started",
]

CURRENT_OBJECTIVE = "Make AISP2 visibly track progress before deeper ingestion."

NEXT_TARGET = "Complete MLB Stats API client verification, then build team ingestion."

DEVELOPMENT_RULE = "One file or one directory at a time."


# ============================================================
# SECTION 04 - APPLICATION INITIALIZATION
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
# SECTION 05 - ROOT VISUAL COMMAND CENTER
# ============================================================

@app.get("/", response_class=HTMLResponse)
def root() -> str:
    """
    Visual homepage.

    This replaces the raw JSON root page with a human-friendly
    project command center so progress is visible on every deploy.
    """

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

    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            min-height: 100vh;
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.35), transparent 30%),
                radial-gradient(circle at top right, rgba(14, 165, 233, 0.22), transparent 28%),
                linear-gradient(180deg, #020617 0%, #0f172a 48%, #111827 100%);
            color: #f8fafc;
            font-family: Inter, Arial, sans-serif;
            padding: 32px;
        }}

        .shell {{
            max-width: 1280px;
            margin: 0 auto;
        }}

        .topbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 28px;
            gap: 16px;
            flex-wrap: wrap;
        }}

        .brand {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}

        .kicker {{
            color: #38bdf8;
            font-size: 13px;
            font-weight: 900;
            letter-spacing: 0.18em;
            text-transform: uppercase;
        }}

        .brand h1 {{
            font-size: 42px;
            letter-spacing: -1.2px;
            font-weight: 950;
        }}

        .status-pill {{
            background: rgba(22, 163, 74, 0.18);
            border: 1px solid rgba(34, 197, 94, 0.45);
            color: #86efac;
            padding: 10px 16px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 900;
            text-transform: uppercase;
        }}

        .hero {{
            background:
                linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.80)),
                radial-gradient(circle at top right, rgba(56, 189, 248, 0.28), transparent 34%);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 30px;
            padding: 34px;
            box-shadow: 0 30px 90px rgba(0, 0, 0, 0.36);
            margin-bottom: 24px;
        }}

        .hero h2 {{
            font-size: 30px;
            margin-bottom: 12px;
        }}

        .hero p {{
            color: #cbd5e1;
            line-height: 1.7;
            font-size: 16px;
            max-width: 960px;
        }}

        .pill-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 22px;
        }}

        .pill {{
            background: rgba(15, 23, 42, 0.82);
            border: 1px solid rgba(148, 163, 184, 0.25);
            padding: 8px 13px;
            border-radius: 999px;
            color: #e2e8f0;
            font-size: 13px;
            font-weight: 800;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 18px;
            margin-bottom: 24px;
        }}

        .card {{
            background: rgba(15, 23, 42, 0.76);
            border: 1px solid rgba(148, 163, 184, 0.20);
            border-radius: 22px;
            padding: 22px;
            box-shadow: 0 18px 55px rgba(0, 0, 0, 0.25);
        }}

        .metric-label {{
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 12px;
            font-weight: 900;
            margin-bottom: 8px;
        }}

        .metric-value {{
            font-size: 30px;
            font-weight: 950;
            color: #ffffff;
        }}

        .metric-note {{
            margin-top: 8px;
            color: #94a3b8;
            font-size: 13px;
            line-height: 1.5;
        }}

        .two-col {{
            display: grid;
            grid-template-columns: 1.2fr 0.8fr;
            gap: 20px;
            margin-bottom: 24px;
        }}

        .section-title {{
            color: #ffffff;
            font-size: 22px;
            font-weight: 950;
            margin-bottom: 14px;
        }}

        ul {{
            padding-left: 22px;
            color: #cbd5e1;
            line-height: 1.9;
        }}

        .timeline {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .step {{
            border-left: 3px solid #38bdf8;
            padding: 12px 14px;
            background: rgba(2, 6, 23, 0.32);
            border-radius: 12px;
        }}

        .step strong {{
            display: block;
            color: #ffffff;
            margin-bottom: 4px;
        }}

        .step span {{
            color: #94a3b8;
            font-size: 14px;
        }}

        .links {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            margin-bottom: 24px;
        }}

        a.button {{
            display: block;
            text-decoration: none;
            text-align: center;
            padding: 14px 16px;
            border-radius: 16px;
            color: #f8fafc;
            font-weight: 900;
            background: rgba(37, 99, 235, 0.22);
            border: 1px solid rgba(96, 165, 250, 0.38);
        }}

        a.button:hover {{
            background: rgba(37, 99, 235, 0.36);
        }}

        .footer {{
            color: #64748b;
            text-align: center;
            font-size: 13px;
            padding: 22px 0 8px;
        }}

        .warning {{
            background: rgba(120, 53, 15, 0.46);
            border: 1px solid rgba(245, 158, 11, 0.44);
            color: #fde68a;
            padding: 14px 18px;
            border-radius: 16px;
            margin-bottom: 22px;
            line-height: 1.6;
            font-size: 14px;
        }}

        @media (max-width: 1000px) {{
            .grid {{
                grid-template-columns: repeat(2, 1fr);
            }}

            .two-col {{
                grid-template-columns: 1fr;
            }}

            .links {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}

        @media (max-width: 640px) {{
            body {{
                padding: 18px;
            }}

            .brand h1 {{
                font-size: 30px;
            }}

            .grid {{
                grid-template-columns: 1fr;
            }}

            .links {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>

<body>
    <main class="shell">

        <div class="topbar">
            <div class="brand">
                <div class="kicker">AI Sports Intelligence Platform</div>
                <h1>{PROJECT_NAME}</h1>
            </div>

            <div class="status-pill">
                Online
            </div>
        </div>

        <section class="hero">
            <h2>Enterprise Baseball Intelligence Command Center</h2>
            <p>
                AISP2 Baseball is being built as a long-term baseball analytics,
                probability, machine learning, simulation, and prediction platform.
                This homepage tracks visible progress as the system grows from
                foundation infrastructure into real MLB data acquisition,
                feature engineering, probability modeling, and advanced prediction tools.
            </p>

            <div class="pill-row">
                <span class="pill">GitHub Connected</span>
                <span class="pill">Render Connected</span>
                <span class="pill">FastAPI Live</span>
                <span class="pill">Database Layer Started</span>
                <span class="pill">MLB Data Source Layer Started</span>
            </div>
        </section>

        <div class="warning">
            AISP2 is an experimental sports analytics and machine learning platform.
            It is not financial advice, gambling advice, legal advice, or a guarantee
            of sports outcomes.
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
                <div class="metric-label">Next Target</div>
                <div class="metric-value">Teams</div>
                <div class="metric-note">Load official MLB teams into database.</div>
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
                        <span>Project, GitHub, Render, FastAPI, database foundation.</span>
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
                        <span>Build readable prediction outputs and confidence scores.</span>
                    </div>
                </div>
            </div>
        </section>

        <section class="two-col">
            <div class="card">
                <div class="section-title">Current Objective</div>
                <p style="color:#cbd5e1; line-height:1.7;">
                    {CURRENT_OBJECTIVE}
                </p>

                <br>

                <div class="section-title">Next Target</div>
                <p style="color:#cbd5e1; line-height:1.7;">
                    {NEXT_TARGET}
                </p>
            </div>

            <div class="card">
                <div class="section-title">Development Rule</div>
                <p style="color:#cbd5e1; line-height:1.7;">
                    {DEVELOPMENT_RULE}
                </p>

                <br>

                <p style="color:#94a3b8; line-height:1.7;">
                    Every file should be organized with enterprise headers,
                    numbered sections, clear responsibility, verification,
                    and future roadmap notes.
                </p>
            </div>
        </section>

        <section class="links">
            <a class="button" href="/project/status">Project Status</a>
            <a class="button" href="/project/roadmap">Roadmap</a>
            <a class="button" href="/project/data-sources">Data Sources</a>
            <a class="button" href="/project/ml-roadmap">ML Roadmap</a>
            <a class="button" href="/project/probability-output-design">Prediction Design</a>
            <a class="button" href="/project/files">File Inventory</a>
            <a class="button" href="/project/next-action">Next Action</a>
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
# SECTION 06 - ROOT JSON ENDPOINT
# ============================================================

@app.get("/api/root")
def root_json() -> dict:
    """
    JSON version of the root endpoint.

    The homepage is now visual HTML, so this endpoint preserves
    the original deployment-verification JSON response.
    """

    return {
        "project": PROJECT_NAME,
        "phase": PROJECT_PHASE,
        "status": "online",
        "version": PROJECT_VERSION,
        "service": SERVICE_NAME,
        "sport": PRIMARY_SPORT,
        "github": GITHUB_REPOSITORY,
        "render": RENDER_SERVICE,
        "next_best_endpoint": "/project/status",
    }


# ============================================================
# SECTION 07 - HEALTH ENDPOINT
# ============================================================

@app.get("/health")
def health() -> dict:
    """
    Simple service health endpoint.

    Future versions will include:
        - database checks
        - data source checks
        - ingestion status
        - prediction engine status
        - model readiness status
    """

    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "project": PROJECT_NAME,
        "phase": PROJECT_PHASE,
    }


# ============================================================
# SECTION 08 - SYSTEM INFORMATION
# ============================================================

@app.get("/system/info")
def system_info() -> dict:
    """
    Basic system metadata.
    """

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
# SECTION 09 - PROJECT STATUS ENDPOINT
# ============================================================

@app.get("/project/status")
def project_status() -> dict:
    """
    Human-readable project status endpoint.
    """

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
        },
        "current_focus": "Project visibility, database foundation, and MLB data source verification",
        "next_target": "Team ingestion from MLB Stats API",
        "development_rule": DEVELOPMENT_RULE,
    }


# ============================================================
# SECTION 10 - PROJECT ROADMAP ENDPOINT
# ============================================================

@app.get("/project/roadmap")
def project_roadmap() -> dict:
    """
    Project roadmap endpoint.
    """

    return {
        "completed": [
            {
                "item": "GitHub repository",
                "status": "complete",
                "purpose": "Source control and deployment pipeline",
            },
            {
                "item": "Render deployment",
                "status": "complete",
                "purpose": "Live web service deployment",
            },
            {
                "item": "main.py",
                "status": "complete",
                "purpose": "Visual command center and FastAPI application entry point",
            },
            {
                "item": "requirements.txt",
                "status": "complete",
                "purpose": "Python dependency management",
            },
            {
                "item": "PROJECT_LEDGER.md",
                "status": "complete",
                "purpose": "Master project tracking ledger",
            },
            {
                "item": "01_database/database.py",
                "status": "complete",
                "purpose": "SQLAlchemy database connection layer",
            },
            {
                "item": "01_database/models.py",
                "status": "complete",
                "purpose": "Team, player, roster, and stat models",
            },
            {
                "item": "01_database/init_db.py",
                "status": "in progress",
                "purpose": "Database initialization engine",
            },
            {
                "item": "02_data_sources/mlb_stats_api.py",
                "status": "in progress",
                "purpose": "Official MLB Stats API client",
            },
        ],
        "current_phase": {
            "name": "Phase 1.00 Foundation",
            "objective": "Create a clean, visible, deployable foundation for AISP2 Baseball",
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
# SECTION 11 - PROJECT VISION ENDPOINT
# ============================================================

@app.get("/project/vision")
def project_vision() -> dict:
    """
    Project vision endpoint.
    """

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
        "user_experience_goal": (
            "The platform should feel like a friendly baseball analyst, "
            "not a database or raw JSON system."
        ),
    }


# ============================================================
# SECTION 12 - DATA SOURCE ROADMAP ENDPOINT
# ============================================================

@app.get("/project/data-sources")
def project_data_sources() -> dict:
    """
    Data source roadmap endpoint.
    """

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
        "future_context_sources": [
            "Weather",
            "Ballpark factors",
            "Injuries",
            "Transactions",
            "Lineups",
            "Travel context",
            "Rest days",
        ],
    }


# ============================================================
# SECTION 13 - MACHINE LEARNING ROADMAP ENDPOINT
# ============================================================

@app.get("/project/ml-roadmap")
def project_machine_learning_roadmap() -> dict:
    """
    Machine learning roadmap endpoint.
    """

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
# SECTION 14 - PROBABILITY OUTPUT DESIGN ENDPOINT
# ============================================================

@app.get("/project/probability-output-design")
def probability_output_design() -> dict:
    """
    Describes the future human-friendly probability result format.
    """

    return {
        "goal": "Every prediction should be readable, explainable, and useful.",
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
            "plain_english_explanation": (
                "Judge projects well because his recent power metrics, "
                "hard-hit rate, and matchup profile support elevated "
                "home run probability."
            ),
        },
    }


# ============================================================
# SECTION 15 - FILE INVENTORY ENDPOINT
# ============================================================

@app.get("/project/files")
def project_files() -> dict:
    """
    Tracks current known project files.
    """

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
# SECTION 16 - NEXT ACTION ENDPOINT
# ============================================================

@app.get("/project/next-action")
def project_next_action() -> dict:
    """
    Shows the next planned build action.
    """

    return {
        "current_rule": DEVELOPMENT_RULE,
        "next_action": "Verify MLB Stats API client locally",
        "after_that": "Create 03_ingestion directory",
        "first_ingestion_file": "03_ingestion/team_ingestion.py",
        "goal": "Load official MLB teams into the AISP2 database",
    }


# ============================================================
# SECTION 17 - LOCAL STARTUP VALIDATION
# ============================================================

if __name__ == "__main__":
    print("AISP2 Baseball loaded successfully.")
    print("FastAPI visual command center initialized.")
    print(f"Project: {PROJECT_NAME}")
    print(f"Version: {PROJECT_VERSION}")
    print(f"Phase: {PROJECT_PHASE}")


# ============================================================
# SECTION 18 - FUTURE APPLICATION ROADMAP
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

Future Command Center Expansion

/project/status
/project/roadmap
/project/vision
/project/data-sources
/project/ml-roadmap
/project/probability-output-design
/project/files
/project/next-action

Future Human UI

A future dashboard should convert these endpoints into:
    - progress cards
    - project status panels
    - data source readiness indicators
    - model readiness indicators
    - database health visuals
    - prediction result cards
"""