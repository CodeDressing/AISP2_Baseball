# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/__init__.py
# PURPOSE: package initializer for semantic analysis,
# NLP, NLU, probability interpretation, embeddings,
# reasoning systems, and future baseball intelligence
# ============================================================


# ============================================================
# SECTION 01 - SEMANTIC ENGINE EXPORTS
# FILE: 04_ai/__init__.py
# PURPOSE: expose semantic interpretation layer
# ============================================================

from .semantic_engine import normalize_text
from .semantic_engine import contains_any_keyword

from .semantic_engine import detect_team
from .semantic_engine import detect_player

from .semantic_engine import detect_outcome
from .semantic_engine import detect_general_intent

from .semantic_engine import interpret_baseball_question


# ============================================================
# SECTION 02 - AI PACKAGE METADATA
# FILE: 04_ai/__init__.py
# PURPOSE: AI subsystem metadata
# ============================================================

AI_PACKAGE_NAME = "AISP2 AI"

AI_PACKAGE_VERSION = "1.0.0"

PRIMARY_ENGINE = "Semantic Engine"


# ============================================================
# SECTION 03 - FUTURE AI MODULE EXPORTS
# FILE: 04_ai/__init__.py
# PURPOSE: future AI architecture ledger
# ============================================================

"""
03.01 intent_detection.py
03.02 entity_detection.py
03.03 probability_interpreter.py
03.04 player_similarity.py
03.05 embeddings.py
03.06 semantic_search.py
03.07 rag_engine.py
03.08 memory_engine.py
03.09 reasoning_engine.py
03.10 explanation_generator.py
"""


# ============================================================
# SECTION 04 - LONG TERM NLP ROADMAP
# FILE: 04_ai/__init__.py
# PURPOSE: semantic evolution path
# ============================================================

"""
Level 1
Keyword Detection

Level 2
Entity Detection

Level 3
Intent Classification

Level 4
Probability Interpretation

Level 5
Semantic Search

Level 6
Embeddings

Level 7
Vector Database Retrieval

Level 8
RAG

Level 9
Reasoning Agents

Level 10
AISP2 Baseball Intelligence System
"""