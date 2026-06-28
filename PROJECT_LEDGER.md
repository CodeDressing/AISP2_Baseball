# ============================================================
# AISP2 BASEBALL
# MASTER PROJECT LEDGER
# ============================================================

Last Updated: 2026-06-28

Project: AISP2 Baseball  
Repository: https://github.com/CodeDressing/AISP2_Baseball  
Deployment: https://aisp2-baseball.onrender.com  
Primary Goal: Make the existing system work cohesively before creating any new files.

---

# SECTION 01 - CURRENT PROJECT TREE

AISP2_Baseball/
├── main.py
├── requirements.txt
├── PROJECT_LEDGER.md
├── .gitignore
├── aisp2_baseball.db
│
├── 00_raw_data/
│   └── CSV/raw data storage for player, Statcast, roster, team, and schedule imports
│
├── 01_database/
│   ├── __init__.py
│   ├── database.py
│   ├── init_db.py
│   └── models.py
│
├── 02_data_sources/
│   ├── __init__.py
│   └── mlb_stats_api.py
│
├── 03_ingestion/
│   ├── __init__.py
│   ├── team_ingestion.py
│   ├── schedule_ingestion.py
│   └── statcast_warehouse_ingestion.py
│
├── 04_ai/
│   ├── __init__.py
│   ├── probability_engine.py
│   ├── response_generator.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── interaction_memory.py
│   │   ├── learning_engine.py
│   │   └── security_guardrails.py
│   │
│   └── nlp/
│       ├── __init__.py
│       ├── context_builder.py
│       ├── entity_detection.py
│       ├── intent_detection.py
│       ├── nlu_engine.py
│       └── semantic_engine.py
│
├── 05_chat_workspace/
│   ├── components/
│   │   ├── __init__.py
│   │   ├── chat_window.py
│   │   ├── conversation_manager.py
│   │   ├── drag_manager.py
│   │   ├── floating_panel.py
│   │   ├── resize_manager.py
│   │   └── ui_state_manager.py
│   │
│   └── frontend/
│       ├── chat_shell.html
│       ├── chat_workspace.css
│       └── chat_workspace.js
│
├── static/
│   ├── css/
│   │   ├── aisp2.css
│   │   ├── chat.css
│   │   ├── dashboard.css
│   │   ├── mobile.css
│   │   ├── player_explorer.css
│   │   └── prediction.css
│   │
│   └── js/
│       ├── aisp2.js
│       ├── chat.js
│       ├── dashboard.js
│       ├── player_explorer.js
│       └── prediction.js
│
└── templates/
    ├── home.html
    ├── dashboard.html
    ├── player_explorer.html
    ├── prediction_workbench.html
    └── team_explorer.html