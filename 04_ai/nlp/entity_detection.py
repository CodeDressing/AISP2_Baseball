
# ============================================================
# AISP2 BASEBALL
# FILE: 04_ai/entity_detection.py
# PURPOSE: advanced entity detection for MLB teams, players,
# aliases, nicknames, roster language, probability subjects,
# and future fuzzy baseball NLP matching
# ============================================================


# ============================================================
# SECTION 01 - ENTERPRISE MLB ENTITY CONFIGURATION
# FILE: 04_ai/nlp/entity_detection.py
# PURPOSE: recognize MLB teams through official names,
# abbreviations, cities, nicknames, fan language, common
# misspellings, and future alias-learning expansion.
# ============================================================

from __future__ import annotations

# ============================================================
# SECTION 01.01 - ENTITY ENGINE VERSION
# ============================================================

ENTITY_DETECTION_VERSION = "phase_10_part_6_enterprise_entity_detection"


# ============================================================
# SECTION 01.02 - ENTITY TYPES
# ============================================================

ENTITY_TYPE_TEAM = "team"
ENTITY_TYPE_PLAYER = "player"
ENTITY_TYPE_SUBJECT = "subject"
ENTITY_TYPE_OUTCOME = "outcome"
ENTITY_TYPE_STAT = "stat"
ENTITY_TYPE_GAME = "game"
ENTITY_TYPE_UNKNOWN = "unknown"


# ============================================================
# SECTION 01.03 - ENTITY CONFIDENCE THRESHOLDS
# ============================================================

ENTITY_CONFIDENCE_EXACT = 98
ENTITY_CONFIDENCE_STRONG = 90
ENTITY_CONFIDENCE_STANDARD = 82
ENTITY_CONFIDENCE_WEAK = 70
ENTITY_CONFIDENCE_REVIEW = 60


# ============================================================
# SECTION 01.04 - MLB TEAM ALIAS MAP
# ============================================================

MLB_TEAM_ALIASES = {
    "Arizona Diamondbacks": [
        "arizona diamondbacks",
        "diamondbacks",
        "dbacks",
        "d backs",
        "d-backs",
        "ari",
        "arizona",
    ],
    "Atlanta Braves": [
        "atlanta braves",
        "braves",
        "atl",
        "atlanta",
    ],
    "Baltimore Orioles": [
        "baltimore orioles",
        "orioles",
        "o's",
        "os",
        "orioles",
        "bal",
        "baltimore",
    ],
    "Boston Red Sox": [
        "boston red sox",
        "red sox",
        "sox",
        "bos",
        "boston",
    ],
    "Chicago Cubs": [
        "chicago cubs",
        "cubs",
        "chc",
        "north siders",
        "northsiders",
    ],
    "Chicago White Sox": [
        "chicago white sox",
        "white sox",
        "chisox",
        "chi sox",
        "south siders",
        "southsiders",
        "cws",
        "chicago sox",
    ],
    "Cincinnati Reds": [
        "cincinnati reds",
        "reds",
        "cin",
        "cincinnati",
    ],
    "Cleveland Guardians": [
        "cleveland guardians",
        "guardians",
        "cle",
        "cleveland",
    ],
    "Colorado Rockies": [
        "colorado rockies",
        "rockies",
        "col",
        "colorado",
    ],
    "Detroit Tigers": [
        "detroit tigers",
        "tigers",
        "det",
        "detroit",
    ],
    "Houston Astros": [
        "houston astros",
        "astros",
        "hou",
        "houston",
    ],
    "Kansas City Royals": [
        "kansas city royals",
        "royals",
        "kc",
        "kcr",
        "kansas city",
    ],
    "Los Angeles Angels": [
        "los angeles angels",
        "angels",
        "la angels",
        "anaheim angels",
        "anaheim",
        "laa",
    ],
    "Los Angeles Dodgers": [
        "los angeles dodgers",
        "dodgers",
        "la dodgers",
        "lad",
    ],
    "Miami Marlins": [
        "miami marlins",
        "marlins",
        "mia",
        "miami",
    ],
    "Milwaukee Brewers": [
        "milwaukee brewers",
        "brewers",
        "mil",
        "milwaukee",
    ],
    "Minnesota Twins": [
        "minnesota twins",
        "twins",
        "min",
        "minnesota",
    ],
    "New York Mets": [
        "new york mets",
        "mets",
        "nym",
        "ny mets",
    ],
    "New York Yankees": [
        "new york yankees",
        "yankees",
        "nyy",
        "bronx bombers",
        "new york yanks",
        "ny yanks",
        "yanks",
    ],
    "Oakland Athletics": [
        "oakland athletics",
        "athletics",
        "a's",
        "as",
        "oakland",
        "oak",
        "athletics baseball",
    ],
    "Philadelphia Phillies": [
        "philadelphia phillies",
        "phillies",
        "phils",
        "phi",
        "philadelphia",
    ],
    "Pittsburgh Pirates": [
        "pittsburgh pirates",
        "pirates",
        "pit",
        "pittsburgh",
        "bucs",
    ],
    "San Diego Padres": [
        "san diego padres",
        "padres",
        "sd",
        "san diego",
    ],
    "San Francisco Giants": [
        "san francisco giants",
        "giants",
        "sf",
        "sfg",
        "san francisco",
    ],
    "Seattle Mariners": [
        "seattle mariners",
        "mariners",
        "sea",
        "seattle",
        "m's",
        "ms",
    ],
    "St. Louis Cardinals": [
        "st louis cardinals",
        "st. louis cardinals",
        "saint louis cardinals",
        "cardinals",
        "cards",
        "stl",
        "st louis",
        "st. louis",
        "saint louis",
    ],
    "Tampa Bay Rays": [
        "tampa bay rays",
        "rays",
        "tb",
        "tbr",
        "tampa bay",
        "tampa",
    ],
    "Texas Rangers": [
        "texas rangers",
        "rangers",
        "tex",
        "texas",
    ],
    "Toronto Blue Jays": [
        "toronto blue jays",
        "blue jays",
        "jays",
        "tor",
        "toronto",
    ],
    "Washington Nationals": [
        "washington nationals",
        "nationals",
        "nats",
        "wsh",
        "was",
        "washington",
    ],
}


# ============================================================
# SECTION 01.05 - TEAM ABBREVIATION LOOKUP
# ============================================================

MLB_TEAM_ABBREVIATIONS = {
    team_name: aliases[0]
    for team_name, aliases in MLB_TEAM_ALIASES.items()
}


# ============================================================
# SECTION 01.06 - ENTITY DETECTION CONFIGURATION
# ============================================================

ENTITY_DETECTION_CONFIGURATION = {
    "team_alias_detection_enabled": True,
    "player_profile_detection_enabled": True,
    "subject_detection_enabled": True,
    "fuzzy_correction_enabled": True,
    "deduplication_enabled": True,
    "return_primary_entities": True,
    "return_all_entities": True,
    "minimum_confidence": ENTITY_CONFIDENCE_REVIEW,
}

# ============================================================
# SECTION 02 - BASEBALL SUBJECT KEYWORDS
# FILE: 04_ai/entity_detection.py
# PURPOSE: identify what type of entity or target the user
# is asking about
# ============================================================

ENTITY_SUBJECT_KEYWORDS = {
    "team": [
        "team",
        "club",
        "franchise",
        "organization",
        "squad",
    ],
    "player": [
        "player",
        "batter",
        "hitter",
        "pitcher",
        "starter",
        "closer",
        "reliever",
        "someone",
        "anyone",
        "guy",
    ],
    "roster": [
        "roster",
        "lineup",
        "active roster",
        "players on",
        "who plays for",
        "who is on",
    ],
    "probability_target": [
        "highest probability",
        "best probability",
        "highest chance",
        "best chance",
        "most likely",
        "top chance",
        "best projection",
        "highest projected",
    ],
}


# ============================================================
# SECTION 03 - TEXT NORMALIZATION
# FILE: 04_ai/entity_detection.py
# PURPOSE: normalize user text for entity matching
# ============================================================

def normalize_entity_text(value: str | None) -> str:
    if not value:
        return ""

    return (
        str(value)
        .lower()
        .replace("?", " ")
        .replace("!", " ")
        .replace(".", " ")
        .replace(",", " ")
        .replace("'", "")
        .replace('"', "")
        .replace("’", "")
        .replace("-", " ")
        .replace("/", " ")
        .replace("  ", " ")
        .strip()
    )


def tokenize_entity_text(value: str | None) -> list[str]:
    cleaned = normalize_entity_text(value)

    return [
        token
        for token in cleaned.split()
        if token
    ]


# ============================================================
# SECTION 04 - TEAM ENTITY DETECTION
# FILE: 04_ai/entity_detection.py
# PURPOSE: detect one or many MLB teams from user language
# ============================================================

def detect_team_entities(message: str) -> list[dict]:
    cleaned_message = normalize_entity_text(message)
    detected_entities: list[dict] = []

    for team_name, aliases in MLB_TEAM_ALIASES.items():
        for alias in aliases:
            cleaned_alias = normalize_entity_text(alias)

            if cleaned_alias and cleaned_alias in cleaned_message:
                detected_entities.append(
                    {
                        "entity_type": "team",
                        "canonical_name": team_name,
                        "matched_text": alias,
                        "confidence": calculate_alias_confidence(
                            alias,
                        ),
                    }
                )

                break

    return deduplicate_entities(
        detected_entities,
    )


def detect_primary_team_entity(message: str) -> dict | None:
    teams = detect_team_entities(message)

    if not teams:
        return None

    return teams[0]


# ============================================================
# SECTION 05 - PLAYER ENTITY DETECTION
# FILE: 04_ai/entity_detection.py
# PURPOSE: detect one or many players from known player data
# ============================================================

def detect_player_entities(
    message: str,
    player_profiles: dict,
) -> list[dict]:
    cleaned_message = normalize_entity_text(message)
    tokens = tokenize_entity_text(message)
    detected_entities: list[dict] = []

    for player_name in player_profiles.keys():
        cleaned_player = normalize_entity_text(player_name)
        name_parts = cleaned_player.split()

        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[-1] if name_parts else ""

        if cleaned_player in cleaned_message:
            detected_entities.append(
                {
                    "entity_type": "player",
                    "canonical_name": player_name,
                    "matched_text": player_name,
                    "confidence": 95,
                }
            )

            continue

        if last_name and last_name in tokens:
            detected_entities.append(
                {
                    "entity_type": "player",
                    "canonical_name": player_name,
                    "matched_text": last_name,
                    "confidence": 76,
                }
            )

            continue

        if first_name and last_name:
            loose_phrase = f"{first_name} {last_name}"

            if loose_phrase in cleaned_message:
                detected_entities.append(
                    {
                        "entity_type": "player",
                        "canonical_name": player_name,
                        "matched_text": player_name,
                        "confidence": 88,
                    }
                )

    return deduplicate_entities(
        detected_entities,
    )


def detect_primary_player_entity(
    message: str,
    player_profiles: dict,
) -> dict | None:
    players = detect_player_entities(
        message,
        player_profiles,
    )

    if not players:
        return None

    return players[0]


# ============================================================
# SECTION 06 - SUBJECT DETECTION
# FILE: 04_ai/entity_detection.py
# PURPOSE: determine whether the user is asking about a team,
# roster, player, or best probability target
# ============================================================

def detect_subject_entities(message: str) -> list[dict]:
    cleaned_message = normalize_entity_text(message)
    detected_subjects: list[dict] = []

    for subject_type, keywords in ENTITY_SUBJECT_KEYWORDS.items():
        for keyword in keywords:
            cleaned_keyword = normalize_entity_text(keyword)

            if cleaned_keyword in cleaned_message:
                detected_subjects.append(
                    {
                        "entity_type": "subject",
                        "canonical_name": subject_type,
                        "matched_text": keyword,
                        "confidence": calculate_alias_confidence(
                            keyword,
                        ),
                    }
                )

                break

    return deduplicate_entities(
        detected_subjects,
    )


# ============================================================
# SECTION 07 - ENTITY CONFIDENCE HELPERS
# FILE: 04_ai/entity_detection.py
# PURPOSE: score entity matches for future routing decisions
# ============================================================

def calculate_alias_confidence(alias: str) -> int:
    token_count = len(
        tokenize_entity_text(alias),
    )

    if token_count >= 3:
        return 95

    if token_count == 2:
        return 88

    return 72


def deduplicate_entities(entities: list[dict]) -> list[dict]:
    deduped: dict[str, dict] = {}

    for entity in entities:
        key = (
            entity["entity_type"],
            entity["canonical_name"],
        )

        existing = deduped.get(
            str(key),
        )

        if not existing:
            deduped[str(key)] = entity
            continue

        if entity["confidence"] > existing["confidence"]:
            deduped[str(key)] = entity

    return sorted(
        deduped.values(),
        key=lambda item: item["confidence"],
        reverse=True,
    )


# ============================================================
# SECTION 08 - FULL ENTITY REPORT
# FILE: 04_ai/entity_detection.py
# PURPOSE: return complete structured entity diagnostics
# for chat routing, context building, and future learning
# ============================================================

def build_entity_report(
    message: str,
    player_profiles: dict | None = None,
) -> dict:
    player_profiles = player_profiles or {}

    correction_report = apply_fuzzy_entity_corrections(
        message=message,
        player_profiles=player_profiles,
    )

    message = correction_report["corrected_message"]

    team_entities = detect_team_entities(
        message,
    )

    player_entities = detect_player_entities(
        message,
        player_profiles,
    )

    subject_entities = detect_subject_entities(
        message,
    )

    all_entities = [
        *team_entities,
        *player_entities,
        *subject_entities,
    ]

    return {
        "message": message,
        "teams": team_entities,
        "players": player_entities,
        "subjects": subject_entities,
        "entities": all_entities,
        "primary_team": team_entities[0] if team_entities else None,
        "primary_player": player_entities[0] if player_entities else None,
        "primary_subject": subject_entities[0] if subject_entities else None,
        "has_team": bool(team_entities),
        "has_player": bool(player_entities),
        "has_probability_target": any(
            subject["canonical_name"] == "probability_target"
            for subject in subject_entities
        ),
    }


# ============================================================
# SECTION 09 - FUZZY ENTITY CORRECTION
# FILE: 04_ai/nlp/entity_detection.py
# PURPOSE: recover misspelled players, teams, and baseball
# terminology before entity routing while supporting Render
# import behavior
# ============================================================

try:
    from nlp.fuzzy_matching import (
        build_fuzzy_nlp_report,
    )
except ModuleNotFoundError:
    from fuzzy_matching import (
        build_fuzzy_nlp_report,
    )


def apply_fuzzy_entity_corrections(
    message: str,
    player_profiles: dict | None = None,
) -> dict:
    player_profiles = player_profiles or {}

    player_names = sorted(
        player_profiles.keys(),
    )

    team_names = sorted(
        MLB_TEAM_ALIASES.keys(),
    )

    fuzzy_report = build_fuzzy_nlp_report(
        message=message,
        player_names=player_names,
        team_names=team_names,
    )

    corrected_message = message

    corrections = []

    player_match = fuzzy_report.get("player_match")

    if (
        player_match
        and player_match.get("matched")
        and player_match.get("observed_phrase")
        and player_match.get("best_match")
    ):
        corrected_message = corrected_message.replace(
            player_match["observed_phrase"],
            player_match["best_match"],
        )

        corrections.append(
            {
                "entity_type": "player",
                "original": player_match["observed_phrase"],
                "corrected": player_match["best_match"],
                "confidence": player_match["score"],
            }
        )

    team_match = fuzzy_report.get("team_match")

    if (
        team_match
        and team_match.get("matched")
        and team_match.get("observed_phrase")
        and team_match.get("best_match")
    ):
        corrected_message = corrected_message.replace(
            team_match["observed_phrase"],
            team_match["best_match"],
        )

        corrections.append(
            {
                "entity_type": "team",
                "original": team_match["observed_phrase"],
                "corrected": team_match["best_match"],
                "confidence": team_match["score"],
            }
        )

    term_match = fuzzy_report.get("term_match")

    if (
        term_match
        and term_match.get("matched")
        and term_match.get("observed_phrase")
        and term_match.get("canonical_value")
    ):
        corrected_message = corrected_message.replace(
            term_match["observed_phrase"],
            term_match["canonical_value"],
        )

        corrections.append(
            {
                "entity_type": "baseball_term",
                "original": term_match["observed_phrase"],
                "corrected": term_match["canonical_value"],
                "confidence": term_match["score"],
            }
        )

    return {
        "original_message": message,
        "corrected_message": corrected_message,
        "corrections": corrections,
        "fuzzy_report": fuzzy_report,
        "has_corrections": bool(corrections),
    }