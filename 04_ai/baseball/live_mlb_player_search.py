# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/baseball/live_mlb_player_search.py
# PURPOSE: live MLB player discovery, player lookup,
# player search, fuzzy matching, roster integration,
# and future player intelligence routing
# ============================================================


# ============================================================
# SECTION 01 - IMPORTS
# ============================================================

from typing import Any


# ============================================================
# SECTION 02 - SEARCH NORMALIZATION
# PURPOSE: clean user search text
# ============================================================

def normalize_player_search_text(
    value: str | None,
) -> str:

    if not value:
        return ""

    return (
        str(value)
        .lower()
        .replace(".", "")
        .replace(",", "")
        .replace("'", "")
        .replace('"', "")
        .replace("?", "")
        .replace("!", "")
        .strip()
    )


# ============================================================
# SECTION 03 - PLAYER MATCH SCORING
# PURPOSE: score player similarity
# ============================================================

def calculate_player_match_score(
    search_name: str,
    candidate_name: str,
) -> int:

    search_name = normalize_player_search_text(
        search_name,
    )

    candidate_name = normalize_player_search_text(
        candidate_name,
    )

    if not search_name:
        return 0

    if search_name == candidate_name:
        return 100

    search_tokens = set(
        search_name.split(),
    )

    candidate_tokens = set(
        candidate_name.split(),
    )

    overlap = len(
        search_tokens.intersection(
            candidate_tokens,
        )
    )

    if overlap == 0:
        return 0

    score = int(
        overlap /
        max(
            len(search_tokens),
            len(candidate_tokens),
        ) * 100
    )

    return score


# ============================================================
# SECTION 04 - PLAYER SEARCH
# PURPOSE: search a live MLB player list
# ============================================================

def search_players(
    search_name: str,
    player_pool: list[dict],
    limit: int = 25,
) -> list[dict]:

    results = []

    for player in player_pool:

        full_name = player.get(
            "fullName",
            "",
        )

        score = calculate_player_match_score(
            search_name=search_name,
            candidate_name=full_name,
        )

        if score <= 0:
            continue

        results.append(
            {
                "score": score,
                "player": player,
            }
        )

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results[:limit]


# ============================================================
# SECTION 05 - BEST PLAYER MATCH
# PURPOSE: return highest confidence match
# ============================================================

def get_best_player_match(
    search_name: str,
    player_pool: list[dict],
) -> dict | None:

    matches = search_players(
        search_name=search_name,
        player_pool=player_pool,
        limit=1,
    )

    if not matches:
        return None

    return matches[0]


# ============================================================
# SECTION 06 - PLAYER PROFILE EXTRACTION
# PURPOSE: standardize player output
# ============================================================

def build_player_summary(
    player_record: dict,
) -> dict:

    return {
        "player_id": player_record.get("id"),
        "full_name": player_record.get("fullName"),
        "first_name": player_record.get("firstName"),
        "last_name": player_record.get("lastName"),
        "primary_number": player_record.get(
            "primaryNumber",
        ),
        "active": player_record.get(
            "active",
        ),
        "position": (
            player_record
            .get("primaryPosition", {})
            .get("name")
        ),
    }


# ============================================================
# SECTION 07 - SEARCH REPORT BUILDER
# PURPOSE: diagnostics for chatbot routing
# ============================================================

def build_player_search_report(
    search_name: str,
    player_pool: list[dict],
) -> dict:

    best_match = get_best_player_match(
        search_name=search_name,
        player_pool=player_pool,
    )

    if not best_match:

        return {
            "found": False,
            "search_name": search_name,
            "confidence": 0,
            "player": None,
        }

    return {
        "found": True,
        "search_name": search_name,
        "confidence": best_match["score"],
        "player": build_player_summary(
            best_match["player"],
        ),
    }


# ============================================================
# SECTION 08 - FUTURE PLAYER SEARCH ROADMAP
# ============================================================

"""
08.01 MLB API integration
08.02 Statcast integration
08.03 Fangraphs integration
08.04 Baseball Savant integration
08.05 Nickname recognition
08.06 Fuzzy misspelling recovery
08.07 Multi-player comparison search
08.08 Team roster search
08.09 Position search
08.10 Embedding-based semantic search
08.11 Player similarity engine
08.12 Prospect search
08.13 Historical player search
08.14 Hall of Fame search
08.15 Player trend intelligence
08.16 Live injury status lookup
08.17 Live lineup lookup
08.18 Live game participation lookup
08.19 Vector search integration
08.20 Full baseball knowledge graph integration
"""