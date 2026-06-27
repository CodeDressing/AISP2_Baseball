# ============================================================
# AISP2 BASEBALL
# AI SPORTS INTELLIGENCE PLATFORM 2
# MASTER PROJECT LEDGER
# ============================================================


================================================================================
PHASE 8 PART 2
Date: June 27, 2026
Time: 3:10 PM EDT (UTC-04:00)
================================================================================

TITLE
Enterprise MLB Schedule Intelligence Foundation

OBJECTIVE
Begin construction of the enterprise schedule intelligence layer that will
become the foundation for game-specific AI predictions, matchup analysis,
chatbot routing, and downstream live-game ingestion.

COMPLETED
• Expanded database architecture for schedule-driven workflows.
• Added bidirectional Team ↔ Game relationship architecture.
• Prepared ORM structure for Game entity integration.
• Designed Enterprise Schedule Ingestion Engine architecture.
• Established support for monthly and full-season MLB schedule ingestion.
• Standardized game identity using official MLB gamePk identifiers.
• Prepared ingestion workflow for April–September 2026 schedule windows.
• Designed normalization, validation, and database upsert pipeline.
• Established foundation for game-specific chatbot context resolution.

SYSTEM IMPACT
• Team schedule relationships
• Home/Away matchup architecture
• Schedule lookup foundation
• Game-centric prediction workflow
• Official MLB Schedule API integration planning
• AI chatbot schedule awareness

NEXT PHASE
PHASE 8 PART 3
Enterprise Schedule Ingestion Engine
- Implement complete schedule_ingestion.py
- Populate games table from MLB Schedule API
- Validate monthly and full-season synchronization
- Prepare game feed, box score, and player-game statistics ingestion
Last Updated: 2026-06-22

Project Status:
ACTIVE DEVELOPMENT

Primary Developer:
Ryan Michael Schuren

Assistant:
Alfred

Repository:
https://github.com/CodeDressing/AISP2_Baseball

Deployment:
Render

Sport:
Major League Baseball (MLB)

Current Phase:
Phase 1.00 Foundation Build

---

# ============================================================
# SECTION 01 - PROJECT VISION
# ============================================================

AISP2 Baseball is an enterprise-grade baseball intelligence,
analytics, machine learning, simulation, and probability platform.

The objective is to create the most comprehensive baseball
analysis and prediction platform possible.

The platform will combine:

- MLB data
- Statcast data
- Historical data
- Team analytics
- Player analytics
- Machine Learning
- Deep Learning
- Probability Modeling
- Monte Carlo Simulation
- Natural Language Explanations

The system must remain:

- Human Friendly
- Enterprise Scale
- Statistically Advanced
- Expandable
- Source Driven

---

# ============================================================
# SECTION 02 - DEVELOPMENT PRINCIPLES
# ============================================================

AISP2 Development Rules

1. One file at a time.

2. Fully complete a file before moving to the next file.

3. Every file must use enterprise section organization.

4. Every file must contain:
   - Header
   - Numbered Sections
   - Purpose Documentation
   - Future Roadmap

5. Avoid placeholder architecture.

6. Build real functionality.

7. Keep code readable.

8. Scale toward enterprise architecture.

9. GitHub push after meaningful upgrades.

10. Render deployment should remain functional.

---

# ============================================================
# SECTION 03 - CURRENT PROJECT STRUCTURE
# ============================================================

AISP2_Baseball/

    main.py

    requirements.txt

    PROJECT_LEDGER.md

    01_database/

        database.py

        models.py

        init_db.py

---

# ============================================================
# SECTION 04 - COMPLETED MILESTONES
# ============================================================

[COMPLETE]

✓ Local Project Created

✓ Python Environment Created

✓ Git Initialized

✓ GitHub Repository Created

✓ Initial Commit Pushed

✓ Render Service Created

✓ Render Deployment Connected

✓ Enterprise database.py Created

✓ Enterprise models.py Created

✓ Enterprise main.py Created

---

# ============================================================
# SECTION 05 - CURRENT PHASE
# ============================================================

PHASE 1.00

Foundation Infrastructure

Objectives:

- Establish project structure
- Establish database layer
- Establish deployment pipeline
- Establish development standards

Status:

IN PROGRESS

---

# ============================================================
# SECTION 06 - MACHINE LEARNING ROADMAP
# ============================================================

Stanford / DeepLearning.AI Concepts

Completed Courses:

✓ Supervised Machine Learning
✓ Advanced Learning Algorithms
✓ Unsupervised Learning
✓ Recommenders
✓ Reinforcement Learning

AISP2 Implementation Goals

Phase ML-01

Supervised Learning

Models:

- Logistic Regression
- Random Forest
- Gradient Boosting
- XGBoost
- LightGBM

Targets:

- Hit Probability
- Home Run Probability
- Strikeout Probability
- Game Winner Probability

---

Phase ML-02

Unsupervised Learning

Models:

- Clustering
- Similar Player Discovery
- Team Archetype Discovery

Targets:

- Comparable Players
- Team Style Classification
- Prospect Similarity

---

Phase ML-03

Recommendation Systems

Targets:

- Similar Players
- Similar Pitchers
- Similar Hitters

---

Phase ML-04

Advanced Learning Algorithms

Targets:

- Ensemble Systems
- Multi-Model Prediction
- Stacked Models

---

Phase ML-05

Reinforcement Learning

Targets:

- Lineup Optimization
- Bullpen Management
- Strategic Decision Simulation

---

# ============================================================
# SECTION 07 - DATA SOURCE ROADMAP
# ============================================================

Tier 1 Sources

✓ MLB Stats API

Planned:

- Baseball Savant
- FanGraphs
- Baseball Reference
- Retrosheet
- Lahman Database

Goal:

Multiple-source validation and enrichment.

---

# ============================================================
# SECTION 08 - DATABASE ROADMAP
# ============================================================

Current Models

✓ Team

✓ Player

✓ RosterEntry

✓ PlayerSeasonStat

Future Models

- TeamSeasonStat
- Game
- GameLog
- StatcastEvent
- PlayerPrediction
- GamePrediction
- SimulationRun
- ModelRun

---

# ============================================================
# SECTION 09 - USER EXPERIENCE GOALS
# ============================================================

AISP2 must never feel like a database.

Users should see:

Player Name

Not:

player_id

Users should see:

Aaron Judge
HR Probability: 34%

Not:

JSON responses

Every prediction should include:

1. Probability

2. Confidence

3. Supporting Statistics

4. Model Used

5. Data Sources Used

6. Plain-English Explanation

---

# ============================================================
# SECTION 10 - NEXT FILE QUEUE
# ============================================================

Priority Order

1. init_db.py

2. MLB Data Source Layer

3. Team Ingestion Service

4. Player Ingestion Service

5. Statistics Ingestion Service

6. Health Monitoring

7. API Routes

8. Dashboard

---

# ============================================================
# SECTION 11 - LONG TERM END STATE
# ============================================================

AISP2 Baseball becomes:

- Baseball Intelligence Platform
- Statistical Analysis Platform
- Probability Engine
- Machine Learning Platform
- Deep Learning Platform
- Simulation Platform

User Workflow

Select Team
↓
Select Opponent
↓
Select Players
↓
Run Prediction
↓
Run Simulations
↓
Generate Probabilities
↓
Explain Results
↓
Store Results
↓
Improve Models

End Goal:

Best Baseball Intelligence Platform Possible.