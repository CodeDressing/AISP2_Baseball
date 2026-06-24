# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/intent_detection.py
# PURPOSE: advanced intent detection layer for AI chat
# understanding, semantic routing, probability requests,
# comparisons, team/player lookup, and future NLP expansion
# ============================================================


# ============================================================
# SECTION 01 - INTENT CONSTANTS
# FILE: 04_ai/intent_detection.py
# PURPOSE: define supported user intent categories
# ============================================================

INTENT_LIST_TEAMS = "list_teams"
INTENT_LIST_PLAYERS = "list_players"
INTENT_TEAM_INFO = "team_info"
INTENT_PLAYER_INFO = "player_info"
INTENT_PLAYER_PROBABILITY = "player_probability"
INTENT_COMPARE_PLAYERS = "compare_players"
INTENT_COMPARE_TEAMS = "compare_teams"
INTENT_GENERAL_PROBABILITY = "general_probability"
INTENT_MATCHUP_ANALYSIS = "matchup_analysis"
INTENT_STAT_REQUEST = "stat_request"
INTENT_EXPLAIN_MODEL = "explain_model"
INTENT_HELP = "help"
INTENT_GENERAL_BASEBALL = "general_baseball_question"


# ============================================================
# SECTION 02 - INTENT KEYWORD MAP
# FILE: 04_ai/intent_detection.py
# PURPOSE: expanded natural language phrase map for teams,
# players, rosters, matchups, probabilities, predictions,
# comparisons, stats, explanations, and help routing
# ============================================================

INTENT_KEYWORDS = {
    INTENT_LIST_TEAMS: [
        "what teams",
        "which teams",
        "what teams do you know",
        "which teams do you know",
        "what teams do you have",
        "which teams do you have",
        "teams do you",
        "teams available",
        "available teams",
        "access to teams",
        "list teams",
        "show teams",
        "show me teams",
        "all teams",
        "every team",
        "mlb teams",
        "baseball teams",
        "team database",
        "teams in your database",
        "teams loaded",
        "loaded teams",
        "what clubs",
        "which clubs",
        "show clubs",
        "list clubs",
        "organizations available",
        "mlb organizations",
        "franchises",
        "team list",
        "club list",
    ],

    INTENT_LIST_PLAYERS: [
        "what players",
        "which players",
        "what players do you know",
        "which players do you know",
        "what players do you have",
        "which players do you have",
        "players do you",
        "players available",
        "available players",
        "access to players",
        "list players",
        "show players",
        "show me players",
        "all players",
        "every player",
        "mlb players",
        "baseball players",
        "player database",
        "players in your database",
        "players loaded",
        "loaded players",
        "show roster",
        "show me the roster",
        "who is on the roster",
        "who is on this team",
        "team roster",
        "active roster",
        "40 man roster",
        "lineup players",
        "player list",
        "roster list",
    ],

    INTENT_COMPARE_PLAYERS: [
        "compare",
        "compare players",
        "player comparison",
        "versus",
        "vs",
        "v ",
        "better player",
        "who is better",
        "which player is better",
        "who is more likely",
        "who has a better chance",
        "who has the better chance",
        "who has more upside",
        "who has higher upside",
        "who is safer",
        "who is riskier",
        "who should i pick",
        "which player should i pick",
        "judge or ohtani",
        "harper or soto",
        "between",
        "head to head",
        "side by side",
        "rank these players",
        "rank players",
        "best player",
        "top player",
        "higher probability",
        "higher chance",
        "better projection",
    ],

    INTENT_COMPARE_TEAMS: [
        "compare teams",
        "team comparison",
        "which team",
        "which team is better",
        "better team",
        "who wins",
        "who will win",
        "winner",
        "game winner",
        "moneyline",
        "team matchup",
        "matchup between",
        "head to head teams",
        "rank teams",
        "best team",
        "top team",
        "stronger team",
        "weaker team",
        "team edge",
        "which club",
        "division comparison",
    ],

    INTENT_PLAYER_PROBABILITY: [
        "probability",
        "chance",
        "chances",
        "odds",
        "projection",
        "project",
        "predict",
        "prediction",
        "likely",
        "how likely",
        "what are the chances",
        "what is the chance",
        "what's the chance",
        "will he",
        "can he",
        "does he",
        "is he going to",
        "is he likely to",
        "projected to",
        "probable",
        "expected to",
        "expectation",
        "estimate",
        "estimated",
        "forecast",
        "forecasted",
        "model",
        "model says",
        "probability model",
        "prediction model",
        "give me a probability",
        "give me odds",
        "give me a projection",
        "run a prediction",
        "calculate prediction",
        "calculate probability",
        "what do you think happens",
        "what happens here",
        "best bet",
        "edge",
        "lean",
        "pick",
        "prop",
        "player prop",
        "sportsbook",
        "over under",
        "over/under",
        "o/u",
    ],

    INTENT_MATCHUP_ANALYSIS: [
        "matchup",
        "match up",
        "against",
        "facing",
        "faces",
        "vs pitcher",
        "versus pitcher",
        "batter vs pitcher",
        "bvp",
        "pitcher matchup",
        "batter matchup",
        "handedness",
        "splits",
        "lefty",
        "righty",
        "left handed",
        "right handed",
        "left handed pitcher",
        "right handed pitcher",
        "same handed",
        "opposite handed",
        "platoon",
        "park factor",
        "ballpark",
        "stadium",
        "weather",
        "wind",
        "temperature",
        "roof",
        "bullpen",
        "starter",
        "starting pitcher",
        "lineup spot",
        "batting order",
        "leadoff",
        "cleanup",
        "cleanup hitter",
    ],

    INTENT_STAT_REQUEST: [
        "stats",
        "statistics",
        "numbers",
        "data",
        "season stats",
        "career stats",
        "game log",
        "recent games",
        "last game",
        "last 5",
        "last five",
        "last 7",
        "last seven",
        "last 10",
        "last ten",
        "last 15",
        "last fifteen",
        "last 30",
        "last thirty",
        "average",
        "batting average",
        "avg",
        "obp",
        "on base",
        "on base percentage",
        "slugging",
        "slg",
        "ops",
        "woba",
        "wrc",
        "wrc+",
        "war",
        "era",
        "whip",
        "fip",
        "xfip",
        "strikeouts",
        "k rate",
        "walk rate",
        "bb rate",
        "home runs",
        "hr",
        "rbi",
        "runs",
        "hits",
        "doubles",
        "triples",
        "total bases",
        "stolen bases",
        "sb",
        "barrel",
        "barrel rate",
        "hard hit",
        "hard hit rate",
        "exit velocity",
        "launch angle",
        "xslg",
        "xba",
        "xwoba",
        "chase rate",
        "whiff rate",
        "contact rate",
    ],

    INTENT_EXPLAIN_MODEL: [
        "why",
        "explain",
        "explain why",
        "reason",
        "reasoning",
        "rationale",
        "how did you get",
        "how did you calculate",
        "how did you determine",
        "what supports",
        "supporting data",
        "supporting metrics",
        "confidence",
        "confidence score",
        "why confidence",
        "why probability",
        "why that probability",
        "why that prediction",
        "what factors",
        "which factors",
        "important factors",
        "key factors",
        "model explanation",
        "explain the model",
        "how does the model work",
        "why is it high",
        "why is it low",
        "risk",
        "risk profile",
        "what is the risk",
    ],

    INTENT_TEAM_INFO: [
        "team",
        "roster",
        "lineup",
        "club",
        "organization",
        "franchise",
        "division",
        "league",
        "american league",
        "national league",
        "al east",
        "al central",
        "al west",
        "nl east",
        "nl central",
        "nl west",
        "team profile",
        "team info",
        "team information",
        "team analysis",
        "team overview",
        "team strength",
        "team weakness",
        "offense",
        "defense",
        "bullpen",
        "rotation",
        "starting rotation",
        "batting order",
        "depth chart",
    ],

    INTENT_PLAYER_INFO: [
        "player",
        "profile",
        "player profile",
        "scouting",
        "scouting report",
        "analyze",
        "analysis",
        "tell me about",
        "who is",
        "what kind of player",
        "player type",
        "hitter type",
        "pitcher type",
        "power hitter",
        "contact hitter",
        "slugger",
        "ace",
        "starter",
        "closer",
        "reliever",
        "prospect",
        "rookie",
        "veteran",
        "injury",
        "health",
        "form",
        "recent form",
        "trend",
        "trending",
        "hot",
        "cold",
        "slump",
        "streak",
    ],

    INTENT_HELP: [
        "help",
        "what can you do",
        "how do i use",
        "how should i use",
        "commands",
        "examples",
        "sample questions",
        "what should i ask",
        "what can i ask",
        "how does this work",
        "guide me",
        "instructions",
        "features",
        "capabilities",
        "what are your capabilities",
        "show me what you can do",
    ],
}
# ============================================================
# SECTION 03 - INTENT PRIORITY
# FILE: 04_ai/intent_detection.py
# PURPOSE: resolve conflicts when multiple intents match
# ============================================================

INTENT_PRIORITY = [
    INTENT_HELP,
    INTENT_COMPARE_PLAYERS,
    INTENT_COMPARE_TEAMS,
    INTENT_PLAYER_PROBABILITY,
    INTENT_MATCHUP_ANALYSIS,
    INTENT_STAT_REQUEST,
    INTENT_LIST_TEAMS,
    INTENT_LIST_PLAYERS,
    INTENT_TEAM_INFO,
    INTENT_PLAYER_INFO,
    INTENT_EXPLAIN_MODEL,
    INTENT_GENERAL_PROBABILITY,
    INTENT_GENERAL_BASEBALL,
]


# ============================================================
# SECTION 04 - NORMALIZATION HELPERS
# FILE: 04_ai/intent_detection.py
# PURPOSE: clean text and prepare user language
# ============================================================

def normalize_intent_text(value: str | None) -> str:
    if not value:
        return ""

    return (
        value.lower()
        .replace("?", " ")
        .replace("!", " ")
        .replace(".", " ")
        .replace(",", " ")
        .replace("'", "")
        .replace('"', "")
        .replace("’", "")
        .replace("-", " ")
        .strip()
    )


def tokenize_intent_text(value: str | None) -> list[str]:
    cleaned = normalize_intent_text(value)

    return [
        token
        for token in cleaned.split()
        if token
    ]


def phrase_exists(
    message: str,
    phrases: list[str],
) -> bool:
    cleaned_message = normalize_intent_text(message)

    return any(
        phrase in cleaned_message
        for phrase in phrases
    )


# ============================================================
# SECTION 05 - MATCH SCORING
# FILE: 04_ai/intent_detection.py
# PURPOSE: score each possible intent from keyword evidence
# ============================================================

def score_intent_match(
    message: str,
    phrases: list[str],
) -> int:
    cleaned_message = normalize_intent_text(message)
    score = 0

    for phrase in phrases:
        if phrase in cleaned_message:
            score += max(
                1,
                len(phrase.split()),
            )

    return score


def score_all_intents(message: str) -> dict[str, int]:
    scores: dict[str, int] = {}

    for intent_name, phrases in INTENT_KEYWORDS.items():
        scores[intent_name] = score_intent_match(
            message=message,
            phrases=phrases,
        )

    return scores


# ============================================================
# SECTION 06 - PRIMARY INTENT DETECTION
# FILE: 04_ai/intent_detection.py
# PURPOSE: classify the user's highest-level intent
# ============================================================

def detect_primary_intent(message: str) -> str:
    scores = score_all_intents(message)

    best_intent = INTENT_GENERAL_BASEBALL
    best_score = 0

    for intent_name in INTENT_PRIORITY:
        intent_score = scores.get(
            intent_name,
            0,
        )

        if intent_score > best_score:
            best_intent = intent_name
            best_score = intent_score

    return best_intent


def detect_possible_intents(message: str) -> list[str]:
    scores = score_all_intents(message)

    matched_intents = [
        intent_name
        for intent_name, score in scores.items()
        if score > 0
    ]

    matched_intents.sort(
        key=lambda intent_name: INTENT_PRIORITY.index(intent_name)
        if intent_name in INTENT_PRIORITY
        else 999
    )

    return matched_intents


# ============================================================
# SECTION 07 - ENTITY-AWARE INTENT UPGRADE
# FILE: 04_ai/intent_detection.py
# PURPOSE: improve intent using detected players, teams,
# outcomes, and comparison language
# ============================================================

def upgrade_intent_with_entities(
    base_intent: str,
    detected_player: str | None = None,
    detected_team: str | None = None,
    detected_outcome: str | None = None,
    detected_players: list[str] | None = None,
    detected_teams: list[str] | None = None,
) -> str:
    player_count = len(detected_players or [])
    team_count = len(detected_teams or [])

    if player_count >= 2:
        return INTENT_COMPARE_PLAYERS

    if team_count >= 2:
        return INTENT_COMPARE_TEAMS

    if detected_player and detected_outcome:
        return INTENT_PLAYER_PROBABILITY

    if detected_player and base_intent in [
        INTENT_PLAYER_PROBABILITY,
        INTENT_GENERAL_PROBABILITY,
    ]:
        return INTENT_PLAYER_PROBABILITY

    if detected_team and base_intent == INTENT_MATCHUP_ANALYSIS:
        return INTENT_MATCHUP_ANALYSIS

    if detected_player and base_intent == INTENT_STAT_REQUEST:
        return INTENT_STAT_REQUEST

    if detected_player:
        return INTENT_PLAYER_INFO

    if detected_team:
        return INTENT_TEAM_INFO

    return base_intent


# ============================================================
# SECTION 08 - QUESTION TYPE DETECTION
# FILE: 04_ai/intent_detection.py
# PURPOSE: identify how the user is asking the question
# ============================================================

def detect_question_type(message: str) -> str:
    cleaned = normalize_intent_text(message)

    if cleaned.startswith("what"):
        return "what_question"

    if cleaned.startswith("who"):
        return "who_question"

    if cleaned.startswith("which"):
        return "which_question"

    if cleaned.startswith("why"):
        return "why_question"

    if cleaned.startswith("how"):
        return "how_question"

    if cleaned.startswith("can") or cleaned.startswith("will"):
        return "probability_question"

    return "statement_or_command"


# ============================================================
# SECTION 09 - CONFIDENCE SCORING
# FILE: 04_ai/intent_detection.py
# PURPOSE: produce simple confidence score for routing
# ============================================================

def calculate_intent_confidence(
    message: str,
    final_intent: str,
    detected_player: str | None = None,
    detected_team: str | None = None,
    detected_outcome: str | None = None,
) -> int:
    scores = score_all_intents(message)
    score = scores.get(
        final_intent,
        0,
    )

    confidence = 35

    if score > 0:
        confidence += min(
            score * 10,
            35,
        )

    if detected_player:
        confidence += 12

    if detected_team:
        confidence += 8

    if detected_outcome:
        confidence += 10

    return min(
        confidence,
        95,
    )


# ============================================================
# SECTION 10 - INTENT REPORT BUILDER
# FILE: 04_ai/intent_detection.py
# PURPOSE: return full intent diagnostics for the chat engine
# ============================================================

def build_intent_report(
    message: str,
    detected_player: str | None = None,
    detected_team: str | None = None,
    detected_outcome: str | None = None,
    detected_players: list[str] | None = None,
    detected_teams: list[str] | None = None,
) -> dict:
    base_intent = detect_primary_intent(message)

    final_intent = upgrade_intent_with_entities(
        base_intent=base_intent,
        detected_player=detected_player,
        detected_team=detected_team,
        detected_outcome=detected_outcome,
        detected_players=detected_players,
        detected_teams=detected_teams,
    )

    confidence = calculate_intent_confidence(
        message=message,
        final_intent=final_intent,
        detected_player=detected_player,
        detected_team=detected_team,
        detected_outcome=detected_outcome,
    )

    return {
        "message": message,
        "question_type": detect_question_type(message),
        "base_intent": base_intent,
        "final_intent": final_intent,
        "possible_intents": detect_possible_intents(message),
        "intent_scores": score_all_intents(message),
        "confidence": confidence,
        "detected_player": detected_player,
        "detected_team": detected_team,
        "detected_outcome": detected_outcome,
        "detected_players": detected_players or [],
        "detected_teams": detected_teams or [],
    }


# ============================================================
# SECTION 11 - FUTURE INTENT DETECTION ROADMAP
# FILE: 04_ai/intent_detection.py
# PURPOSE: future NLP and semantic intent expansion ledger
# ============================================================

"""
11.01 Add fuzzy phrase matching.
11.02 Add misspelling tolerance.
11.03 Add confidence calibration.
11.04 Add multi-turn follow-up routing.
11.05 Add conversation context memory.
11.06 Add player/team alias maps.
11.07 Add embedding-based intent classification.
11.08 Add transformer-based NLU classification.
11.09 Add baseball ontology matching.
11.10 Add multi-agent routing.
"""