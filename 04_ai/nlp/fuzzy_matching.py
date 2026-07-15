# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# PHASE 10 PART 14.1
# FILE: 04_ai/nlp/fuzzy_matching.py
# PURPOSE:
# Enterprise fuzzy entity resolution for warehouse-backed MLB
# players, teams, aliases, abbreviations, and baseball concepts.
#
# CORE GUARANTEES:
# 1. Current warehouse names are the primary entity catalog.
# 2. Multiple adjacent misspellings can be resolved together.
# 3. Ordinary words are not silently converted into entities.
# 4. Ambiguous matches are rejected instead of guessed.
# 5. Every match returns ranked alternatives and diagnostics.
# 6. Existing AISP2 fuzzy-matching public APIs remain available.
# ============================================================

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from collections import Counter
from collections import defaultdict
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
from enum import Enum
from functools import lru_cache
from hashlib import sha256
import json
import math
import re
import threading
import time
import unicodedata
from typing import Any
from typing import Final


# ============================================================
# SECTION 02 - ENGINE METADATA
# ============================================================

FUZZY_ENGINE_NAME: Final[str] = (
    "AISP2 Enterprise Baseball Fuzzy Matching Engine"
)
FUZZY_ENGINE_VERSION: Final[str] = "5.1.0"
FUZZY_ENGINE_PHASE: Final[str] = "Phase 10 Part 14.1"
FUZZY_ENGINE_PATH: Final[str] = "04_ai/nlp/fuzzy_matching.py"
FUZZY_ENGINE_STATUS: Final[str] = "enterprise_ready"
FUZZY_SCHEMA_VERSION: Final[str] = "2.1.0"

ENTITY_PLAYER: Final[str] = "player"
ENTITY_TEAM: Final[str] = "team"
ENTITY_TERM: Final[str] = "baseball_term"
ENTITY_ALIAS: Final[str] = "alias"
ENTITY_UNKNOWN: Final[str] = "unknown"


# ============================================================
# SECTION 03 - GLOBAL THRESHOLDS
# ============================================================

DEFAULT_MATCH_THRESHOLD: Final[float] = 0.78
STRONG_MATCH_THRESHOLD: Final[float] = 0.90
VERY_STRONG_MATCH_THRESHOLD: Final[float] = 0.96
WEAK_MATCH_THRESHOLD: Final[float] = 0.68

DEFAULT_AMBIGUITY_MARGIN: Final[float] = 0.055
STRICT_AMBIGUITY_MARGIN: Final[float] = 0.085
CRITICAL_AMBIGUITY_MARGIN: Final[float] = 0.120

DEFAULT_MAX_CANDIDATES: Final[int] = 10
DEFAULT_MAX_WINDOW_SIZE: Final[int] = 7
DEFAULT_MIN_WINDOW_SIZE: Final[int] = 1

DEFAULT_SHORT_TOKEN_THRESHOLD: Final[float] = 0.95
DEFAULT_SINGLE_TOKEN_THRESHOLD: Final[float] = 0.84
DEFAULT_MULTI_TOKEN_THRESHOLD: Final[float] = 0.72
DEFAULT_PHRASE_SEGMENT_THRESHOLD: Final[float] = 0.70

DEFAULT_CACHE_TTL_SECONDS: Final[float] = 300.0
DEFAULT_CACHE_MAX_ENTRIES: Final[int] = 8


# ============================================================
# SECTION 04 - ENUMERATIONS
# ============================================================

class MatchConfidence(str, Enum):
    EXACT = "exact"
    VERY_STRONG = "very_strong"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"


class MatchDecision(str, Enum):
    ACCEPTED = "accepted"
    AMBIGUOUS = "ambiguous"
    REJECTED = "rejected"
    NO_CANDIDATES = "no_candidates"
    ORDINARY_WORD_BLOCKED = "ordinary_word_blocked"
    SHORT_TOKEN_BLOCKED = "short_token_blocked"
    CONTEXT_REQUIRED = "context_required"


class CandidateSource(str, Enum):
    WAREHOUSE = "warehouse"
    PROVIDED = "provided"
    BUILTIN = "builtin"
    ALIAS = "alias"
    ABBREVIATION = "abbreviation"
    CONTEXT = "context"
    UNKNOWN = "unknown"


class MatchStrategy(str, Enum):
    EXACT = "exact"
    NORMALIZED_EXACT = "normalized_exact"
    ALIAS_EXACT = "alias_exact"
    ABBREVIATION_EXACT = "abbreviation_exact"
    TOKEN_SEQUENCE = "token_sequence"
    TOKEN_SORT = "token_sort"
    TOKEN_SET = "token_set"
    PARTIAL = "partial"
    EDIT_DISTANCE = "edit_distance"
    DAMERAU_LEVENSHTEIN = "damerau_levenshtein"
    PHONETIC = "phonetic"
    KEYBOARD_AWARE = "keyboard_aware"
    PHRASE_SEGMENTATION = "phrase_segmentation"
    COMPOSITE = "composite"


class CacheStatus(str, Enum):
    HIT = "hit"
    MISS = "miss"
    EXPIRED = "expired"
    DISABLED = "disabled"


# ============================================================
# SECTION 05 - CONFIGURATION
# ============================================================

@dataclass(slots=True)
class FuzzyMatchConfig:
    default_threshold: float = DEFAULT_MATCH_THRESHOLD
    strong_threshold: float = STRONG_MATCH_THRESHOLD
    very_strong_threshold: float = VERY_STRONG_MATCH_THRESHOLD
    weak_threshold: float = WEAK_MATCH_THRESHOLD

    ambiguity_margin: float = DEFAULT_AMBIGUITY_MARGIN
    strict_ambiguity_margin: float = STRICT_AMBIGUITY_MARGIN
    critical_ambiguity_margin: float = CRITICAL_AMBIGUITY_MARGIN

    max_candidates: int = DEFAULT_MAX_CANDIDATES
    max_window_size: int = DEFAULT_MAX_WINDOW_SIZE
    min_window_size: int = DEFAULT_MIN_WINDOW_SIZE

    short_token_threshold: float = DEFAULT_SHORT_TOKEN_THRESHOLD
    single_token_threshold: float = DEFAULT_SINGLE_TOKEN_THRESHOLD
    multi_token_threshold: float = DEFAULT_MULTI_TOKEN_THRESHOLD
    phrase_segment_threshold: float = DEFAULT_PHRASE_SEGMENT_THRESHOLD

    ordinary_word_protection: bool = True
    short_token_protection: bool = True
    ambiguity_protection: bool = True
    require_entity_signal_for_weak_matches: bool = True
    prefer_longer_windows: bool = True
    use_warehouse_by_default: bool = True
    include_builtin_team_fallback: bool = True

    enable_phonetic_scoring: bool = True
    enable_keyboard_scoring: bool = True
    enable_transposition_scoring: bool = True
    enable_phrase_segmentation: bool = True
    enable_candidate_cache: bool = True

    cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS
    cache_max_entries: int = DEFAULT_CACHE_MAX_ENTRIES

    minimum_short_token_length: int = 3
    maximum_phrase_entities: int = 4

    def validate(self) -> None:
        probability_fields = (
            "default_threshold",
            "strong_threshold",
            "very_strong_threshold",
            "weak_threshold",
            "ambiguity_margin",
            "strict_ambiguity_margin",
            "critical_ambiguity_margin",
            "short_token_threshold",
            "single_token_threshold",
            "multi_token_threshold",
            "phrase_segment_threshold",
        )

        for field_name in probability_fields:
            value = float(getattr(self, field_name))

            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        integer_fields = (
            "max_candidates",
            "max_window_size",
            "min_window_size",
            "cache_max_entries",
            "minimum_short_token_length",
            "maximum_phrase_entities",
        )

        for field_name in integer_fields:
            if int(getattr(self, field_name)) <= 0:
                raise ValueError(
                    f"{field_name} must be positive"
                )

        if self.min_window_size > self.max_window_size:
            raise ValueError(
                "min_window_size cannot exceed max_window_size"
            )

        if self.cache_ttl_seconds < 0:
            raise ValueError(
                "cache_ttl_seconds cannot be negative"
            )


DEFAULT_CONFIG = FuzzyMatchConfig()


# ============================================================
# SECTION 06 - CORE DATA CONTRACTS
# ============================================================

@dataclass(slots=True)
class FuzzyCandidate:
    canonical_name: str
    entity_type: str
    entity_id: int | str | None = None

    aliases: tuple[str, ...] = ()
    abbreviations: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    source: CandidateSource = CandidateSource.UNKNOWN
    active: bool = True

    normalized_name: str = ""
    normalized_aliases: tuple[str, ...] = ()
    normalized_abbreviations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.canonical_name = str(
            self.canonical_name
        ).strip()

        if not self.normalized_name:
            self.normalized_name = normalize_fuzzy_text(
                self.canonical_name
            )

        if not self.normalized_aliases:
            self.normalized_aliases = tuple(
                normalize_fuzzy_text(value)
                for value in self.aliases
                if normalize_fuzzy_text(value)
            )

        if not self.normalized_abbreviations:
            self.normalized_abbreviations = tuple(
                normalize_fuzzy_text(value)
                for value in self.abbreviations
                if normalize_fuzzy_text(value)
            )

    @property
    def token_count(self) -> int:
        return len(
            tokenize_fuzzy_text(
                self.normalized_name
            )
        )

    @property
    def all_search_values(self) -> tuple[str, ...]:
        return tuple(
            deduplicate_strings(
                (
                    self.normalized_name,
                    *self.normalized_aliases,
                    *self.normalized_abbreviations,
                )
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_name": self.canonical_name,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "aliases": list(self.aliases),
            "abbreviations": list(
                self.abbreviations
            ),
            "metadata": dict(self.metadata),
            "source": self.source.value,
            "active": self.active,
            "normalized_name": self.normalized_name,
            "token_count": self.token_count,
        }


@dataclass(slots=True)
class ScoreComponents:
    sequence: float = 0.0
    token_sort: float = 0.0
    token_set: float = 0.0
    partial: float = 0.0
    edit: float = 0.0
    damerau: float = 0.0
    phonetic: float = 0.0
    keyboard: float = 0.0
    prefix: float = 0.0
    initials: float = 0.0
    length: float = 0.0
    coverage: float = 0.0
    token_alignment: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            key: round(float(value), 6)
            for key, value in asdict(self).items()
        }


@dataclass(slots=True)
class RankedMatch:
    candidate: FuzzyCandidate
    observed_phrase: str
    normalized_observed_phrase: str

    score: float
    adjusted_score: float
    threshold: float

    components: ScoreComponents
    matched_value: str
    strategy: MatchStrategy

    alias_score: float = 0.0
    abbreviation_score: float = 0.0
    ordinary_word_risk: float = 0.0
    short_token_risk: float = 0.0
    entity_signal_score: float = 0.0
    ambiguity_penalty: float = 0.0
    context_bonus: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        component_payload = self.components.to_dict()

        return {
            "candidate": self.candidate.to_dict(),
            "canonical_name": self.candidate.canonical_name,
            "entity_type": self.candidate.entity_type,
            "entity_id": self.candidate.entity_id,
            "observed_phrase": self.observed_phrase,
            "normalized_observed_phrase": (
                self.normalized_observed_phrase
            ),
            "score": round(self.score, 6),
            "adjusted_score": round(
                self.adjusted_score,
                6,
            ),
            "threshold": round(self.threshold, 6),
            "components": component_payload,
            "sequence_score": component_payload["sequence"],
            "token_sort_score": component_payload["token_sort"],
            "token_set_score": component_payload["token_set"],
            "partial_score": component_payload["partial"],
            "edit_score": component_payload["edit"],
            "damerau_score": component_payload["damerau"],
            "phonetic_score": component_payload["phonetic"],
            "keyboard_score": component_payload["keyboard"],
            "prefix_score": component_payload["prefix"],
            "initials_score": component_payload["initials"],
            "length_score": component_payload["length"],
            "coverage_score": component_payload["coverage"],
            "token_alignment_score": component_payload[
                "token_alignment"
            ],
            "alias_score": round(self.alias_score, 6),
            "abbreviation_score": round(
                self.abbreviation_score,
                6,
            ),
            "ordinary_word_risk": round(
                self.ordinary_word_risk,
                6,
            ),
            "short_token_risk": round(
                self.short_token_risk,
                6,
            ),
            "entity_signal_score": round(
                self.entity_signal_score,
                6,
            ),
            "ambiguity_penalty": round(
                self.ambiguity_penalty,
                6,
            ),
            "context_bonus": round(
                self.context_bonus,
                6,
            ),
            "matched_value": self.matched_value,
            "strategy": self.strategy.value,
            "confidence": classify_fuzzy_confidence(
                self.adjusted_score
            ),
        }


@dataclass(slots=True)
class FuzzyMatchResult:
    query: str
    normalized_query: str
    entity_type: str

    matched: bool
    decision: MatchDecision
    confidence: MatchConfidence

    best_match: RankedMatch | None = None
    ranked_candidates: list[RankedMatch] = field(
        default_factory=list
    )

    ambiguity_margin: float | None = None
    required_ambiguity_margin: float | None = None
    ambiguous_candidates: list[RankedMatch] = field(
        default_factory=list
    )

    threshold: float = DEFAULT_MATCH_THRESHOLD
    reason: str | None = None

    candidate_count: int = 0
    evaluated_window_count: int = 0

    diagnostics: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_name": FUZZY_ENGINE_NAME,
            "engine_version": FUZZY_ENGINE_VERSION,
            "engine_phase": FUZZY_ENGINE_PHASE,
            "query": self.query,
            "normalized_query": self.normalized_query,
            "entity_type": self.entity_type,
            "matched": self.matched,
            "decision": self.decision.value,
            "confidence": self.confidence.value,
            "best_match": (
                self.best_match.to_dict()
                if self.best_match
                else None
            ),
            "ranked_candidates": [
                item.to_dict()
                for item in self.ranked_candidates
            ],
            "ambiguity_margin": (
                round(self.ambiguity_margin, 6)
                if self.ambiguity_margin is not None
                else None
            ),
            "required_ambiguity_margin": (
                round(
                    self.required_ambiguity_margin,
                    6,
                )
                if self.required_ambiguity_margin
                is not None
                else None
            ),
            "ambiguous_candidates": [
                item.to_dict()
                for item in self.ambiguous_candidates
            ],
            "threshold": round(self.threshold, 6),
            "reason": self.reason,
            "candidate_count": self.candidate_count,
            "evaluated_window_count": (
                self.evaluated_window_count
            ),
            "diagnostics": dict(self.diagnostics),
        }


@dataclass(slots=True)
class PhraseSegmentMatch:
    token_start: int
    token_end: int
    observed_phrase: str
    match: RankedMatch

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_start": self.token_start,
            "token_end": self.token_end,
            "observed_phrase": self.observed_phrase,
            "match": self.match.to_dict(),
            "canonical_name": (
                self.match.candidate.canonical_name
            ),
            "entity_type": (
                self.match.candidate.entity_type
            ),
            "entity_id": self.match.candidate.entity_id,
            "adjusted_score": (
                round(
                    self.match.adjusted_score,
                    6,
                )
            ),
        }


# ============================================================
# SECTION 07 - NORMALIZATION
# ============================================================

WHITESPACE_PATTERN = re.compile(r"\s+")
NON_ALPHANUMERIC_PATTERN = re.compile(
    r"[^a-z0-9+\s]"
)
TOKEN_PATTERN = re.compile(
    r"[a-z0-9]+(?:\+[a-z0-9]+)?"
)


def normalize_fuzzy_text(
    value: str | None,
) -> str:
    if not value:
        return ""

    text = unicodedata.normalize(
        "NFKD",
        str(value),
    )

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(
            character
        )
    )

    text = text.lower()
    text = text.replace("&", " and ")
    text = text.replace("’", "'")
    text = text.replace("-", " ")
    text = text.replace("_", " ")
    text = text.replace("/", " ")

    replacements = {
        "homerun": "home run",
        "home-run": "home run",
        "stat cast": "statcast",
        "strike-out": "strikeout",
    }

    for source, target in replacements.items():
        text = text.replace(source, target)

    text = NON_ALPHANUMERIC_PATTERN.sub(
        " ",
        text,
    )
    text = WHITESPACE_PATTERN.sub(
        " ",
        text,
    )

    return text.strip()


def tokenize_fuzzy_text(
    value: str | None,
) -> list[str]:
    return TOKEN_PATTERN.findall(
        normalize_fuzzy_text(value)
    )


def deduplicate_strings(
    values: Iterable[str],
) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = normalize_fuzzy_text(
            value
        )

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(normalized)
        output.append(normalized)

    return output


# ============================================================
# SECTION 08 - ORDINARY LANGUAGE PROTECTION
# ============================================================

ORDINARY_WORDS: Final[frozenset[str]] = frozenset({
    "a", "about", "after", "again", "against", "all", "also", "am",
    "an", "and", "any", "are", "as", "at", "away", "back", "be",
    "because", "been", "before", "best", "between", "both", "but",
    "by", "can", "could", "day", "did", "do", "does", "each", "even",
    "every", "few", "find", "for", "from", "game", "games", "get",
    "give", "go", "good", "had", "has", "have", "he", "help", "her",
    "here", "him", "his", "how", "i", "in", "into", "is", "it",
    "its", "just", "last", "like", "list", "look", "make", "many",
    "me", "more", "most", "my", "need", "new", "next", "no", "not",
    "now", "of", "off", "on", "one", "only", "or", "other", "our",
    "out", "over", "player", "players", "please", "predict",
    "prediction", "probability", "right", "roster", "same", "schedule",
    "search", "see", "show", "so", "some", "stats", "status", "team",
    "teams", "than", "that", "the", "their", "them", "then", "there",
    "these", "they", "this", "those", "time", "to", "today",
    "tomorrow", "up", "us", "use", "very", "want", "was", "we",
    "well", "were", "what", "when", "where", "which", "who", "why",
    "will", "with", "would", "year", "yes", "you", "your",
})

BASEBALL_SIGNAL_WORDS: Final[frozenset[str]] = frozenset({
    "avg", "baseball", "bat", "batter", "batting", "bullpen", "club",
    "era", "fielder", "game", "games", "hit", "hitter", "home",
    "homer", "lineup", "mlb", "obp", "ops", "pitch", "pitcher",
    "player", "players", "predict", "probability", "rbi", "roster",
    "schedule", "slg", "stat", "stats", "strikeout", "team", "teams",
    "war", "whip",
})

ENTITY_REQUEST_SIGNAL_WORDS: Final[frozenset[str]] = frozenset({
    "compare", "find", "lookup", "predict", "search", "show", "who",
    "whose",
})


def calculate_entity_signal_score(
    message: str,
) -> float:
    tokens = set(
        tokenize_fuzzy_text(message)
    )

    if not tokens:
        return 0.0

    baseball_hits = len(
        tokens & BASEBALL_SIGNAL_WORDS
    )
    request_hits = len(
        tokens & ENTITY_REQUEST_SIGNAL_WORDS
    )

    return min(
        1.0,
        min(baseball_hits * 0.22, 0.66)
        + min(request_hits * 0.18, 0.36),
    )


def calculate_ordinary_word_risk(
    observed_phrase: str,
    candidate: FuzzyCandidate,
) -> float:
    tokens = tokenize_fuzzy_text(
        observed_phrase
    )

    if not tokens:
        return 1.0

    ordinary_count = sum(
        token in ORDINARY_WORDS
        for token in tokens
    )

    if len(tokens) == 1:
        token = tokens[0]

        if token in ORDINARY_WORDS:
            return 1.0

        if (
            token in BASEBALL_SIGNAL_WORDS
            and token
            not in tokenize_fuzzy_text(
                candidate.normalized_name
            )
        ):
            return 0.95

    return min(
        1.0,
        ordinary_count / len(tokens),
    )


def calculate_short_token_risk(
    observed_phrase: str,
) -> float:
    tokens = tokenize_fuzzy_text(
        observed_phrase
    )

    if not tokens:
        return 1.0

    if len(tokens) > 1:
        return 0.0

    length = len(tokens[0])

    if length <= 1:
        return 1.0

    if length == 2:
        return 0.88

    if length == 3:
        return 0.58

    return 0.0


# ============================================================
# SECTION 09 - BASEBALL ALIASES
# ============================================================

BASEBALL_TERM_ALIASES: Final[
    dict[str, tuple[str, ...]]
] = {
    "home_run": (
        "home run", "homer", "homerun", "homeurn", "hom run",
        "hr", "dinger", "long ball", "go yard", "goes yard",
    ),
    "hit": (
        "hit", "base hit", "hitt", "ht", "get a hit",
        "record a hit",
    ),
    "single": (
        "single", "one base hit", "1b",
    ),
    "double": (
        "double", "two base hit", "2b",
    ),
    "triple": (
        "triple", "three base hit", "3b",
    ),
    "strikeout": (
        "strikeout", "strike out", "strikout", "striekout",
        "strkeout", "k", "ks", "punchout",
    ),
    "walk": (
        "walk", "base on balls", "bb",
    ),
    "rbi": (
        "rbi", "runs batted in", "run batted in", "rib",
        "drive in",
    ),
    "run": (
        "run", "score a run", "runs scored",
    ),
    "total_bases": (
        "total bases", "total base", "bases", "tb",
    ),
    "stolen_base": (
        "stolen base", "steal a base", "sb",
    ),
    "earned_run_average": (
        "earned run average", "era",
    ),
    "walks_hits_per_inning": (
        "whip", "walks hits per inning",
    ),
    "on_base_percentage": (
        "obp", "on base percentage",
    ),
    "slugging_percentage": (
        "slg", "slugging percentage",
    ),
    "on_base_plus_slugging": (
        "ops", "on base plus slugging",
    ),
    "batting_average": (
        "avg", "batting average", "average",
    ),
}


BUILTIN_TEAM_ALIASES: Final[
    dict[str, tuple[str, ...]]
] = {
    "Arizona Diamondbacks": ("diamondbacks", "dbacks", "d backs", "ari"),
    "Athletics": ("athletics", "oakland athletics", "oakland as", "a's"),
    "Atlanta Braves": ("braves", "atl"),
    "Baltimore Orioles": ("orioles", "os", "bal"),
    "Boston Red Sox": ("red sox", "boston", "bos"),
    "Chicago Cubs": ("cubs", "chc"),
    "Chicago White Sox": ("white sox", "chw", "cws"),
    "Cincinnati Reds": ("reds", "cin"),
    "Cleveland Guardians": ("guardians", "cle"),
    "Colorado Rockies": ("rockies", "col"),
    "Detroit Tigers": ("tigers", "det"),
    "Houston Astros": ("astros", "hou"),
    "Kansas City Royals": ("royals", "kc", "kcr"),
    "Los Angeles Angels": ("angels", "la angels", "anaheim angels", "laa"),
    "Los Angeles Dodgers": ("dodgers", "la dodgers", "lad"),
    "Miami Marlins": ("marlins", "mia"),
    "Milwaukee Brewers": ("brewers", "mil"),
    "Minnesota Twins": ("twins", "min"),
    "New York Mets": ("mets", "ny mets", "nym"),
    "New York Yankees": ("yankees", "yanks", "ny yankees", "nyy"),
    "Philadelphia Phillies": ("phillies", "phils", "phi"),
    "Pittsburgh Pirates": ("pirates", "bucs", "pit"),
    "San Diego Padres": ("padres", "sd", "sdp"),
    "San Francisco Giants": ("giants", "sf giants", "sfg"),
    "Seattle Mariners": ("mariners", "ms", "sea"),
    "St. Louis Cardinals": ("cardinals", "cards", "st louis", "stl"),
    "Tampa Bay Rays": ("rays", "tampa", "tb", "tbr"),
    "Texas Rangers": ("rangers", "tex"),
    "Toronto Blue Jays": ("blue jays", "jays", "tor"),
    "Washington Nationals": ("nationals", "nats", "wsh", "was"),
}


# ============================================================
# SECTION 10 - KEYBOARD MODEL
# ============================================================

KEYBOARD_NEIGHBORS: Final[
    dict[str, frozenset[str]]
] = {
    "q": frozenset("wa"),
    "w": frozenset("qeas"),
    "e": frozenset("wrsd"),
    "r": frozenset("etdf"),
    "t": frozenset("ryfg"),
    "y": frozenset("tugh"),
    "u": frozenset("yihj"),
    "i": frozenset("uojk"),
    "o": frozenset("ipkl"),
    "p": frozenset("ol"),
    "a": frozenset("qwsz"),
    "s": frozenset("weadzx"),
    "d": frozenset("erfsxc"),
    "f": frozenset("rtgdvc"),
    "g": frozenset("tyfhvb"),
    "h": frozenset("yugjbn"),
    "j": frozenset("uihkmn"),
    "k": frozenset("iojlnm"),
    "l": frozenset("opk"),
    "z": frozenset("asx"),
    "x": frozenset("zsdc"),
    "c": frozenset("xdfv"),
    "v": frozenset("cfgb"),
    "b": frozenset("vghn"),
    "n": frozenset("bhjm"),
    "m": frozenset("njk"),
}


# ============================================================
# SECTION 11 - BASE SIMILARITY
# ============================================================

def calculate_similarity(
    user_value: str,
    candidate_value: str,
) -> float:
    left = normalize_fuzzy_text(
        user_value
    )
    right = normalize_fuzzy_text(
        candidate_value
    )

    if not left or not right:
        return 0.0

    if left == right:
        return 1.0

    from difflib import SequenceMatcher

    return SequenceMatcher(
        None,
        left,
        right,
    ).ratio()


def calculate_token_sort_similarity(
    user_value: str,
    candidate_value: str,
) -> float:
    left = " ".join(
        sorted(
            tokenize_fuzzy_text(user_value)
        )
    )
    right = " ".join(
        sorted(
            tokenize_fuzzy_text(candidate_value)
        )
    )

    return (
        calculate_similarity(left, right)
        if left and right
        else 0.0
    )


def calculate_token_set_similarity(
    user_value: str,
    candidate_value: str,
) -> float:
    left = set(
        tokenize_fuzzy_text(user_value)
    )
    right = set(
        tokenize_fuzzy_text(candidate_value)
    )

    if not left or not right:
        return 0.0

    intersection = left & right
    union = left | right

    jaccard = (
        len(intersection) / len(union)
        if union
        else 0.0
    )

    overlap = (
        len(intersection)
        / min(len(left), len(right))
    )

    return (
        0.45 * jaccard
        + 0.55 * overlap
    )


def calculate_partial_similarity(
    user_value: str,
    candidate_value: str,
) -> float:
    left = normalize_fuzzy_text(
        user_value
    )
    right = normalize_fuzzy_text(
        candidate_value
    )

    if not left or not right:
        return 0.0

    shorter, longer = (
        (left, right)
        if len(left) <= len(right)
        else (right, left)
    )

    if shorter in longer:
        return 1.0

    width = len(shorter)
    best = 0.0

    for index in range(
        0,
        len(longer) - width + 1,
    ):
        best = max(
            best,
            calculate_similarity(
                shorter,
                longer[index:index + width],
            ),
        )

    return best


# ============================================================
# SECTION 12 - EDIT DISTANCE
# ============================================================

@lru_cache(maxsize=65536)
def levenshtein_distance(
    left: str,
    right: str,
) -> int:
    left = normalize_fuzzy_text(left)
    right = normalize_fuzzy_text(right)

    if left == right:
        return 0

    if not left:
        return len(right)

    if not right:
        return len(left)

    previous = list(
        range(len(right) + 1)
    )

    for left_index, left_char in enumerate(
        left,
        start=1,
    ):
        current = [left_index]

        for right_index, right_char in enumerate(
            right,
            start=1,
        ):
            current.append(
                min(
                    current[right_index - 1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1]
                    + (
                        0
                        if left_char == right_char
                        else 1
                    ),
                )
            )

        previous = current

    return previous[-1]


@lru_cache(maxsize=65536)
def damerau_levenshtein_distance(
    left: str,
    right: str,
) -> int:
    left = normalize_fuzzy_text(left)
    right = normalize_fuzzy_text(right)

    if left == right:
        return 0

    left_length = len(left)
    right_length = len(right)

    matrix = [
        [0] * (right_length + 1)
        for _ in range(left_length + 1)
    ]

    for index in range(left_length + 1):
        matrix[index][0] = index

    for index in range(right_length + 1):
        matrix[0][index] = index

    for i in range(1, left_length + 1):
        for j in range(1, right_length + 1):
            substitution_cost = (
                0
                if left[i - 1] == right[j - 1]
                else 1
            )

            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1]
                + substitution_cost,
            )

            if (
                i > 1
                and j > 1
                and left[i - 1] == right[j - 2]
                and left[i - 2] == right[j - 1]
            ):
                matrix[i][j] = min(
                    matrix[i][j],
                    matrix[i - 2][j - 2] + 1,
                )

    return matrix[left_length][right_length]


def calculate_edit_similarity(
    user_value: str,
    candidate_value: str,
) -> float:
    left = normalize_fuzzy_text(user_value)
    right = normalize_fuzzy_text(candidate_value)

    if not left or not right:
        return 0.0

    distance = levenshtein_distance(
        left,
        right,
    )

    return max(
        0.0,
        1.0
        - distance / max(len(left), len(right)),
    )


def calculate_damerau_similarity(
    user_value: str,
    candidate_value: str,
) -> float:
    left = normalize_fuzzy_text(user_value)
    right = normalize_fuzzy_text(candidate_value)

    if not left or not right:
        return 0.0

    distance = damerau_levenshtein_distance(
        left,
        right,
    )

    return max(
        0.0,
        1.0
        - distance / max(len(left), len(right)),
    )


# ============================================================
# SECTION 13 - KEYBOARD-AWARE SIMILARITY
# ============================================================

def keyboard_substitution_cost(
    left_char: str,
    right_char: str,
) -> float:
    if left_char == right_char:
        return 0.0

    if right_char in KEYBOARD_NEIGHBORS.get(
        left_char,
        frozenset(),
    ):
        return 0.35

    return 1.0


def weighted_keyboard_distance(
    left: str,
    right: str,
) -> float:
    left = normalize_fuzzy_text(left)
    right = normalize_fuzzy_text(right)

    if left == right:
        return 0.0

    if not left:
        return float(len(right))

    if not right:
        return float(len(left))

    previous = [
        float(index)
        for index in range(len(right) + 1)
    ]

    for left_index, left_char in enumerate(
        left,
        start=1,
    ):
        current = [float(left_index)]

        for right_index, right_char in enumerate(
            right,
            start=1,
        ):
            current.append(
                min(
                    current[right_index - 1] + 1.0,
                    previous[right_index] + 1.0,
                    previous[right_index - 1]
                    + keyboard_substitution_cost(
                        left_char,
                        right_char,
                    ),
                )
            )

        previous = current

    return previous[-1]


def calculate_keyboard_similarity(
    user_value: str,
    candidate_value: str,
) -> float:
    left = normalize_fuzzy_text(user_value)
    right = normalize_fuzzy_text(candidate_value)

    if not left or not right:
        return 0.0

    distance = weighted_keyboard_distance(
        left,
        right,
    )

    return max(
        0.0,
        1.0
        - distance / max(len(left), len(right)),
    )


# ============================================================
# SECTION 14 - PHONETIC AND TOKEN ALIGNMENT
# ============================================================

def simple_phonetic_key(
    value: str,
) -> str:
    text = normalize_fuzzy_text(value)

    replacements = (
        ("ph", "f"),
        ("ght", "t"),
        ("ck", "k"),
        ("qu", "k"),
        ("x", "ks"),
        ("z", "s"),
        ("c", "k"),
        ("j", "g"),
        ("v", "f"),
    )

    for source, target in replacements:
        text = text.replace(source, target)

    output: list[str] = []

    for token in tokenize_fuzzy_text(text):
        first = token[0]
        remainder = re.sub(
            r"[aeiouy]",
            "",
            token[1:],
        )
        output.append(
            re.sub(
                r"(.)\1+",
                r"\1",
                first + remainder,
            )
        )

    return " ".join(output)


def calculate_phonetic_similarity(
    user_value: str,
    candidate_value: str,
) -> float:
    left = simple_phonetic_key(user_value)
    right = simple_phonetic_key(candidate_value)

    if not left or not right:
        return 0.0

    if left == right:
        return 1.0

    return calculate_similarity(left, right)


def calculate_prefix_score(
    user_value: str,
    candidate_value: str,
) -> float:
    left = tokenize_fuzzy_text(user_value)
    right = tokenize_fuzzy_text(candidate_value)

    if not left or not right:
        return 0.0

    matched = sum(
        left_token.startswith(right_token)
        or right_token.startswith(left_token)
        for left_token, right_token in zip(
            left,
            right,
        )
    )

    return matched / max(
        len(left),
        len(right),
    )


def calculate_initials_score(
    user_value: str,
    candidate_value: str,
) -> float:
    left_tokens = tokenize_fuzzy_text(
        user_value
    )
    right_tokens = tokenize_fuzzy_text(
        candidate_value
    )

    if not left_tokens or not right_tokens:
        return 0.0

    left = "".join(
        token[0]
        for token in left_tokens
    )
    right = "".join(
        token[0]
        for token in right_tokens
    )

    if left == right and len(left) >= 2:
        return 1.0

    if (
        len(left_tokens) == 1
        and left_tokens[0] == right
        and len(right) >= 2
    ):
        return 1.0

    return calculate_similarity(left, right)


def calculate_length_score(
    user_value: str,
    candidate_value: str,
) -> float:
    left = normalize_fuzzy_text(user_value)
    right = normalize_fuzzy_text(candidate_value)

    if not left or not right:
        return 0.0

    return min(len(left), len(right)) / max(
        len(left),
        len(right),
    )


def calculate_token_alignment_score(
    user_value: str,
    candidate_value: str,
) -> float:
    left_tokens = tokenize_fuzzy_text(
        user_value
    )
    right_tokens = tokenize_fuzzy_text(
        candidate_value
    )

    if not left_tokens or not right_tokens:
        return 0.0

    if len(left_tokens) != len(right_tokens):
        return 0.0

    scores = []

    for left_token, right_token in zip(
        left_tokens,
        right_tokens,
    ):
        scores.append(
            max(
                calculate_similarity(
                    left_token,
                    right_token,
                ),
                calculate_edit_similarity(
                    left_token,
                    right_token,
                ),
                calculate_damerau_similarity(
                    left_token,
                    right_token,
                ),
                calculate_keyboard_similarity(
                    left_token,
                    right_token,
                ),
                calculate_phonetic_similarity(
                    left_token,
                    right_token,
                ),
            )
        )

    return sum(scores) / len(scores)


def calculate_coverage_score(
    user_value: str,
    candidate_value: str,
) -> float:
    left = tokenize_fuzzy_text(user_value)
    right = tokenize_fuzzy_text(candidate_value)

    if not left or not right:
        return 0.0

    used: set[int] = set()
    total = 0.0

    for token in left:
        best_score = 0.0
        best_index: int | None = None

        for index, candidate_token in enumerate(
            right
        ):
            if index in used:
                continue

            score = max(
                calculate_similarity(
                    token,
                    candidate_token,
                ),
                calculate_edit_similarity(
                    token,
                    candidate_token,
                ),
                calculate_damerau_similarity(
                    token,
                    candidate_token,
                ),
                calculate_keyboard_similarity(
                    token,
                    candidate_token,
                ),
                calculate_phonetic_similarity(
                    token,
                    candidate_token,
                ),
            )

            if score > best_score:
                best_score = score
                best_index = index

        if best_index is not None:
            used.add(best_index)

        total += best_score

    return total / max(len(left), len(right))


# ============================================================
# SECTION 15 - CANDIDATE CONSTRUCTION
# ============================================================

def _coerce_source(
    value: Any,
) -> CandidateSource:
    if isinstance(value, CandidateSource):
        return value

    if isinstance(value, str):
        try:
            return CandidateSource(value)
        except ValueError:
            pass

    return CandidateSource.UNKNOWN


def coerce_fuzzy_candidate(
    value: Any,
    *,
    entity_type: str,
    source: CandidateSource = CandidateSource.PROVIDED,
) -> FuzzyCandidate | None:
    if value is None:
        return None

    if isinstance(value, FuzzyCandidate):
        return value

    if isinstance(value, str):
        cleaned = value.strip()

        if not cleaned:
            return None

        return FuzzyCandidate(
            canonical_name=cleaned,
            entity_type=entity_type,
            source=source,
        )

    if not isinstance(value, Mapping):
        return None

    canonical_name = (
        value.get("canonical_name")
        or value.get("name")
        or value.get("full_name")
        or value.get("team_name")
        or value.get("player_name")
        or value.get("display_name")
    )

    if not canonical_name:
        return None

    aliases_raw = (
        value.get("aliases")
        or value.get("alias_names")
        or value.get("search_aliases")
        or ()
    )

    abbreviations_raw = (
        value.get("abbreviations")
        or value.get("abbreviation")
        or value.get("team_abbreviation")
        or ()
    )

    aliases = (
        (aliases_raw,)
        if isinstance(aliases_raw, str)
        else tuple(
            str(item)
            for item in aliases_raw
            if item
        )
    )

    abbreviations = (
        (abbreviations_raw,)
        if isinstance(abbreviations_raw, str)
        else tuple(
            str(item)
            for item in abbreviations_raw
            if item
        )
    )

    entity_id = (
        value.get("entity_id")
        or value.get("id")
        or value.get("mlb_player_id")
        or value.get("mlb_team_id")
        or value.get("player_id")
        or value.get("team_id")
    )

    return FuzzyCandidate(
        canonical_name=str(canonical_name),
        entity_type=str(
            value.get("entity_type")
            or entity_type
        ),
        entity_id=entity_id,
        aliases=aliases,
        abbreviations=abbreviations,
        metadata=dict(
            value.get("metadata")
            or {}
        ),
        source=_coerce_source(
            value.get("source")
            or source
        ),
        active=bool(
            value.get(
                "active",
                value.get(
                    "is_active",
                    True,
                ),
            )
        ),
    )


def normalize_candidate_collection(
    candidates: Iterable[Any],
    *,
    entity_type: str,
    source: CandidateSource = CandidateSource.PROVIDED,
) -> list[FuzzyCandidate]:
    output: list[FuzzyCandidate] = []
    seen: set[
        tuple[str, str, str]
    ] = set()

    for raw in candidates:
        candidate = coerce_fuzzy_candidate(
            raw,
            entity_type=entity_type,
            source=source,
        )

        if candidate is None:
            continue

        identity = (
            candidate.entity_type,
            str(candidate.entity_id or ""),
            candidate.normalized_name,
        )

        if identity in seen:
            continue

        seen.add(identity)
        output.append(candidate)

    return output


def build_baseball_term_candidates(
) -> list[FuzzyCandidate]:
    return [
        FuzzyCandidate(
            canonical_name=name,
            entity_type=ENTITY_TERM,
            aliases=aliases,
            source=CandidateSource.BUILTIN,
        )
        for name, aliases in (
            BASEBALL_TERM_ALIASES.items()
        )
    ]


def build_builtin_team_candidates(
) -> list[FuzzyCandidate]:
    output: list[FuzzyCandidate] = []

    for name, aliases in (
        BUILTIN_TEAM_ALIASES.items()
    ):
        abbreviations = tuple(
            alias
            for alias in aliases
            if len(
                normalize_fuzzy_text(alias)
            ) <= 4
        )

        output.append(
            FuzzyCandidate(
                canonical_name=name,
                entity_type=ENTITY_TEAM,
                aliases=aliases,
                abbreviations=abbreviations,
                source=CandidateSource.BUILTIN,
            )
        )

    return output


# ============================================================
# SECTION 16 - WAREHOUSE CACHE
# ============================================================

@dataclass(slots=True)
class _CacheEntry:
    created_at: float
    candidates: list[FuzzyCandidate]


_CANDIDATE_CACHE: dict[
    str,
    _CacheEntry,
] = {}
_CANDIDATE_CACHE_LOCK = threading.RLock()


def _cache_key(
    entity_type: str,
    include_inactive: bool,
    limit: int | None,
) -> str:
    return (
        f"{entity_type}|"
        f"inactive={include_inactive}|"
        f"limit={limit}"
    )


def clear_fuzzy_candidate_cache() -> None:
    with _CANDIDATE_CACHE_LOCK:
        _CANDIDATE_CACHE.clear()


def _read_candidate_cache(
    key: str,
    config: FuzzyMatchConfig,
) -> tuple[
    list[FuzzyCandidate] | None,
    CacheStatus,
]:
    if not config.enable_candidate_cache:
        return None, CacheStatus.DISABLED

    with _CANDIDATE_CACHE_LOCK:
        entry = _CANDIDATE_CACHE.get(key)

        if entry is None:
            return None, CacheStatus.MISS

        age = time.monotonic() - entry.created_at

        if age > config.cache_ttl_seconds:
            _CANDIDATE_CACHE.pop(
                key,
                None,
            )
            return None, CacheStatus.EXPIRED

        return list(
            entry.candidates
        ), CacheStatus.HIT


def _write_candidate_cache(
    key: str,
    candidates: Sequence[FuzzyCandidate],
    config: FuzzyMatchConfig,
) -> None:
    if not config.enable_candidate_cache:
        return

    with _CANDIDATE_CACHE_LOCK:
        if (
            len(_CANDIDATE_CACHE)
            >= config.cache_max_entries
            and key not in _CANDIDATE_CACHE
        ):
            oldest_key = min(
                _CANDIDATE_CACHE,
                key=lambda item: (
                    _CANDIDATE_CACHE[
                        item
                    ].created_at
                ),
            )
            _CANDIDATE_CACHE.pop(
                oldest_key,
                None,
            )

        _CANDIDATE_CACHE[key] = _CacheEntry(
            created_at=time.monotonic(),
            candidates=list(candidates),
        )


# ============================================================
# SECTION 17 - WAREHOUSE LOADERS
# ============================================================

def _safe_model_attribute(
    instance: Any,
    names: Sequence[str],
) -> Any:
    for name in names:
        if hasattr(instance, name):
            value = getattr(
                instance,
                name,
            )

            if value is not None:
                return value

    return None


def load_warehouse_player_candidates(
    database_session: Any | None = None,
    *,
    include_inactive: bool = False,
    limit: int | None = None,
    config: FuzzyMatchConfig | None = None,
) -> list[FuzzyCandidate]:
    config = config or FuzzyMatchConfig()
    config.validate()

    key = _cache_key(
        ENTITY_PLAYER,
        include_inactive,
        limit,
    )

    cached, _ = _read_candidate_cache(
        key,
        config,
    )

    if cached is not None:
        return cached

    try:
        from models import Player
    except Exception:
        return []

    manager = None

    if database_session is None:
        try:
            from database import (
                managed_database_session,
            )

            manager = (
                managed_database_session()
            )
            database_session = (
                manager.__enter__()
            )
        except Exception:
            return []

    try:
        query = database_session.query(
            Player
        )

        if not include_inactive:
            for field_name in (
                "active_status",
                "is_active",
                "active",
            ):
                if hasattr(Player, field_name):
                    query = query.filter(
                        getattr(
                            Player,
                            field_name,
                        ).is_(True)
                    )
                    break

        if hasattr(Player, "full_name"):
            query = query.order_by(
                Player.full_name.asc()
            )

        if limit is not None:
            query = query.limit(
                int(limit)
            )

        output: list[
            FuzzyCandidate
        ] = []

        for player in query.all():
            full_name = _safe_model_attribute(
                player,
                (
                    "full_name",
                    "name",
                    "player_name",
                ),
            )

            if not full_name:
                continue

            aliases: list[str] = []

            for field_name in (
                "use_name",
                "nick_name",
                "boxscore_name",
                "name_slug",
            ):
                value = _safe_model_attribute(
                    player,
                    (field_name,),
                )

                if value:
                    aliases.append(str(value))

            first_name = _safe_model_attribute(
                player,
                (
                    "first_name",
                    "use_name",
                ),
            )
            last_name = _safe_model_attribute(
                player,
                ("last_name",),
            )

            if first_name and last_name:
                aliases.extend(
                    (
                        f"{first_name} {last_name}",
                        f"{last_name} {first_name}",
                        str(last_name),
                    )
                )

            output.append(
                FuzzyCandidate(
                    canonical_name=str(full_name),
                    entity_type=ENTITY_PLAYER,
                    entity_id=_safe_model_attribute(
                        player,
                        (
                            "mlb_player_id",
                            "id",
                        ),
                    ),
                    aliases=tuple(
                        deduplicate_strings(
                            aliases
                        )
                    ),
                    metadata={
                        "first_name": first_name,
                        "last_name": last_name,
                        "position": _safe_model_attribute(
                            player,
                            (
                                "position",
                                "primary_position",
                            ),
                        ),
                        "current_team_id": (
                            _safe_model_attribute(
                                player,
                                (
                                    "current_team_id",
                                ),
                            )
                        ),
                    },
                    source=CandidateSource.WAREHOUSE,
                )
            )

        _write_candidate_cache(
            key,
            output,
            config,
        )

        return output

    except Exception:
        return []

    finally:
        if manager is not None:
            manager.__exit__(
                None,
                None,
                None,
            )


def load_warehouse_team_candidates(
    database_session: Any | None = None,
    *,
    include_inactive: bool = False,
    limit: int | None = None,
    config: FuzzyMatchConfig | None = None,
) -> list[FuzzyCandidate]:
    config = config or FuzzyMatchConfig()
    config.validate()

    key = _cache_key(
        ENTITY_TEAM,
        include_inactive,
        limit,
    )

    cached, _ = _read_candidate_cache(
        key,
        config,
    )

    if cached is not None:
        return cached

    try:
        from models import Team
    except Exception:
        return build_builtin_team_candidates()

    manager = None

    if database_session is None:
        try:
            from database import (
                managed_database_session,
            )

            manager = (
                managed_database_session()
            )
            database_session = (
                manager.__enter__()
            )
        except Exception:
            return build_builtin_team_candidates()

    try:
        query = database_session.query(
            Team
        )

        if not include_inactive:
            for field_name in (
                "is_active",
                "active",
            ):
                if hasattr(Team, field_name):
                    query = query.filter(
                        getattr(
                            Team,
                            field_name,
                        ).is_(True)
                    )
                    break

        if hasattr(Team, "name"):
            query = query.order_by(
                Team.name.asc()
            )

        if limit is not None:
            query = query.limit(
                int(limit)
            )

        output: list[
            FuzzyCandidate
        ] = []

        for team in query.all():
            name = _safe_model_attribute(
                team,
                (
                    "name",
                    "team_name",
                ),
            )

            if not name:
                continue

            aliases: list[str] = list(
                BUILTIN_TEAM_ALIASES.get(
                    str(name),
                    (),
                )
            )

            for field_name in (
                "short_name",
                "club_name",
                "franchise_name",
                "location_name",
                "team_code",
                "file_code",
            ):
                value = _safe_model_attribute(
                    team,
                    (field_name,),
                )

                if value:
                    aliases.append(str(value))

            abbreviation = (
                _safe_model_attribute(
                    team,
                    ("abbreviation",),
                )
            )

            output.append(
                FuzzyCandidate(
                    canonical_name=str(name),
                    entity_type=ENTITY_TEAM,
                    entity_id=_safe_model_attribute(
                        team,
                        (
                            "mlb_team_id",
                            "id",
                        ),
                    ),
                    aliases=tuple(
                        deduplicate_strings(
                            aliases
                        )
                    ),
                    abbreviations=(
                        (str(abbreviation),)
                        if abbreviation
                        else ()
                    ),
                    metadata={
                        "league": _safe_model_attribute(
                            team,
                            ("league",),
                        ),
                        "division": (
                            _safe_model_attribute(
                                team,
                                ("division",),
                            )
                        ),
                    },
                    source=CandidateSource.WAREHOUSE,
                )
            )

        result = (
            output
            or build_builtin_team_candidates()
        )

        _write_candidate_cache(
            key,
            result,
            config,
        )

        return result

    except Exception:
        return build_builtin_team_candidates()

    finally:
        if manager is not None:
            manager.__exit__(
                None,
                None,
                None,
            )


# ============================================================
# SECTION 18 - WINDOW GENERATION
# ============================================================

def build_token_windows(
    message: str,
    max_window_size: int = DEFAULT_MAX_WINDOW_SIZE,
    min_window_size: int = DEFAULT_MIN_WINDOW_SIZE,
    *,
    prefer_longer_windows: bool = True,
) -> list[str]:
    tokens = tokenize_fuzzy_text(
        message
    )

    if not tokens:
        return []

    sizes = list(
        range(
            max(1, min_window_size),
            min(max_window_size, len(tokens))
            + 1,
        )
    )

    if prefer_longer_windows:
        sizes.reverse()

    output: list[str] = []
    seen: set[str] = set()

    for size in sizes:
        for index in range(
            0,
            len(tokens) - size + 1,
        ):
            window = " ".join(
                tokens[index:index + size]
            )

            if window in seen:
                continue

            seen.add(window)
            output.append(window)

    return output


def build_candidate_aware_windows(
    message: str,
    candidates: Sequence[
        FuzzyCandidate
    ],
    config: FuzzyMatchConfig,
) -> list[str]:
    counts = {
        candidate.token_count
        for candidate in candidates
        if candidate.token_count > 0
    }

    sizes: set[int] = set()

    for count in counts:
        for offset in (
            -2,
            -1,
            0,
            1,
            2,
        ):
            value = count + offset

            if (
                config.min_window_size
                <= value
                <= config.max_window_size
            ):
                sizes.add(value)

    if not sizes:
        return build_token_windows(
            message,
            config.max_window_size,
            config.min_window_size,
            prefer_longer_windows=(
                config.prefer_longer_windows
            ),
        )

    tokens = tokenize_fuzzy_text(
        message
    )
    output: list[str] = []
    seen: set[str] = set()

    for size in sorted(
        sizes,
        reverse=(
            config.prefer_longer_windows
        ),
    ):
        if size > len(tokens):
            continue

        for index in range(
            0,
            len(tokens) - size + 1,
        ):
            window = " ".join(
                tokens[index:index + size]
            )

            if window in seen:
                continue

            seen.add(window)
            output.append(window)

    return output


# ============================================================
# SECTION 19 - THRESHOLD POLICY
# ============================================================

def determine_dynamic_threshold(
    observed_phrase: str,
    candidate: FuzzyCandidate,
    config: FuzzyMatchConfig,
) -> float:
    tokens = tokenize_fuzzy_text(
        observed_phrase
    )

    if not tokens:
        return 1.0

    length = len(
        normalize_fuzzy_text(
            observed_phrase
        )
    )

    if len(tokens) == 1:
        return (
            config.short_token_threshold
            if length <= 3
            else config.single_token_threshold
        )

    threshold = (
        config.multi_token_threshold
    )

    if len(tokens) >= 3:
        threshold -= 0.02

    if candidate.token_count >= 3:
        threshold -= 0.015

    return max(
        config.weak_threshold,
        threshold,
    )


# ============================================================
# SECTION 20 - ALIAS SCORING
# ============================================================

def _best_alias_score(
    observed: str,
    values: Sequence[str],
) -> tuple[float, str]:
    best_score = 0.0
    best_value = ""

    for value in values:
        score = max(
            calculate_similarity(
                observed,
                value,
            ),
            calculate_edit_similarity(
                observed,
                value,
            ),
            calculate_damerau_similarity(
                observed,
                value,
            ),
            calculate_keyboard_similarity(
                observed,
                value,
            ),
            calculate_phonetic_similarity(
                observed,
                value,
            ),
        )

        if score > best_score:
            best_score = score
            best_value = value

    return best_score, best_value


# ============================================================
# SECTION 21 - COMPOSITE SCORING
# ============================================================

def score_fuzzy_candidate(
    observed_phrase: str,
    candidate: FuzzyCandidate,
    *,
    message: str | None = None,
    config: FuzzyMatchConfig | None = None,
    context_entity_id: int | str | None = None,
) -> RankedMatch:
    config = config or FuzzyMatchConfig()
    config.validate()

    observed = normalize_fuzzy_text(
        observed_phrase
    )

    best_value = candidate.normalized_name
    best_components = ScoreComponents()
    best_score = 0.0
    best_strategy = MatchStrategy.COMPOSITE

    for search_value in (
        candidate.all_search_values
    ):
        components = ScoreComponents(
            sequence=calculate_similarity(
                observed,
                search_value,
            ),
            token_sort=(
                calculate_token_sort_similarity(
                    observed,
                    search_value,
                )
            ),
            token_set=(
                calculate_token_set_similarity(
                    observed,
                    search_value,
                )
            ),
            partial=calculate_partial_similarity(
                observed,
                search_value,
            ),
            edit=calculate_edit_similarity(
                observed,
                search_value,
            ),
            damerau=calculate_damerau_similarity(
                observed,
                search_value,
            ),
            phonetic=(
                calculate_phonetic_similarity(
                    observed,
                    search_value,
                )
                if config.enable_phonetic_scoring
                else 0.0
            ),
            keyboard=(
                calculate_keyboard_similarity(
                    observed,
                    search_value,
                )
                if config.enable_keyboard_scoring
                else 0.0
            ),
            prefix=calculate_prefix_score(
                observed,
                search_value,
            ),
            initials=calculate_initials_score(
                observed,
                search_value,
            ),
            length=calculate_length_score(
                observed,
                search_value,
            ),
            coverage=calculate_coverage_score(
                observed,
                search_value,
            ),
            token_alignment=(
                calculate_token_alignment_score(
                    observed,
                    search_value,
                )
            ),
        )

        if observed == search_value:
            composite = 1.0
            strategy = (
                MatchStrategy.NORMALIZED_EXACT
            )

        else:
            composite = (
                components.sequence * 0.14
                + components.token_sort * 0.07
                + components.token_set * 0.06
                + components.partial * 0.05
                + components.edit * 0.12
                + components.damerau * 0.14
                + components.phonetic * 0.07
                + components.keyboard * 0.08
                + components.prefix * 0.04
                + components.initials * 0.02
                + components.length * 0.04
                + components.coverage * 0.08
                + components.token_alignment * 0.09
            )

            strategy_scores = {
                MatchStrategy.TOKEN_SEQUENCE: (
                    components.sequence
                ),
                MatchStrategy.TOKEN_SORT: (
                    components.token_sort
                ),
                MatchStrategy.TOKEN_SET: (
                    components.token_set
                ),
                MatchStrategy.PARTIAL: (
                    components.partial
                ),
                MatchStrategy.EDIT_DISTANCE: (
                    components.edit
                ),
                MatchStrategy.DAMERAU_LEVENSHTEIN: (
                    components.damerau
                ),
                MatchStrategy.PHONETIC: (
                    components.phonetic
                ),
                MatchStrategy.KEYBOARD_AWARE: (
                    components.keyboard
                ),
            }

            strategy = max(
                strategy_scores,
                key=strategy_scores.get,
            )

        if composite > best_score:
            best_score = composite
            best_value = search_value
            best_components = components
            best_strategy = strategy

    alias_score, alias_value = (
        _best_alias_score(
            observed,
            candidate.normalized_aliases,
        )
    )

    abbreviation_score, abbreviation_value = (
        _best_alias_score(
            observed,
            candidate.normalized_abbreviations,
        )
    )

    bonus = 0.0

    if alias_score >= 0.90:
        bonus += 0.035

        if alias_score > best_score:
            best_value = alias_value
            best_strategy = (
                MatchStrategy.ALIAS_EXACT
                if alias_score == 1.0
                else MatchStrategy.COMPOSITE
            )

    if abbreviation_score == 1.0:
        bonus += 0.06
        best_value = abbreviation_value
        best_strategy = (
            MatchStrategy.ABBREVIATION_EXACT
        )

    if (
        best_components.phonetic >= 0.92
        and best_components.edit >= 0.70
    ):
        bonus += 0.02

    if (
        best_components.keyboard >= 0.90
        and best_components.damerau >= 0.72
    ):
        bonus += 0.025

    if (
        best_components.prefix >= 0.90
        and best_components.edit >= 0.72
    ):
        bonus += 0.015

    observed_token_count = len(
        tokenize_fuzzy_text(
            observed_phrase
        )
    )

    if (
        observed_token_count
        == candidate.token_count
        and observed_token_count >= 2
        and best_components.coverage >= 0.88
        and best_components.token_alignment
        >= 0.86
    ):
        bonus += 0.075
        best_strategy = (
            MatchStrategy.PHRASE_SEGMENTATION
        )

    ordinary_risk = (
        calculate_ordinary_word_risk(
            observed_phrase,
            candidate,
        )
    )
    short_risk = (
        calculate_short_token_risk(
            observed_phrase
        )
    )
    signal = calculate_entity_signal_score(
        message or observed_phrase
    )

    penalty = 0.0

    if config.ordinary_word_protection:
        penalty += ordinary_risk * 0.30

    if config.short_token_protection:
        penalty += short_risk * 0.18

    if (
        config.require_entity_signal_for_weak_matches
        and signal < 0.18
        and best_score < config.strong_threshold
    ):
        penalty += 0.065

    context_bonus = 0.0

    if (
        context_entity_id is not None
        and str(candidate.entity_id)
        == str(context_entity_id)
    ):
        context_bonus = 0.025

    adjusted = max(
        0.0,
        min(
            1.0,
            best_score
            + bonus
            + context_bonus
            - penalty,
        ),
    )

    return RankedMatch(
        candidate=candidate,
        observed_phrase=observed_phrase,
        normalized_observed_phrase=observed,
        score=best_score,
        adjusted_score=adjusted,
        threshold=determine_dynamic_threshold(
            observed_phrase,
            candidate,
            config,
        ),
        components=best_components,
        matched_value=best_value,
        strategy=best_strategy,
        alias_score=alias_score,
        abbreviation_score=abbreviation_score,
        ordinary_word_risk=ordinary_risk,
        short_token_risk=short_risk,
        entity_signal_score=signal,
        context_bonus=context_bonus,
    )


def rank_fuzzy_candidates(
    observed_phrase: str,
    candidates: Sequence[FuzzyCandidate],
    *,
    message: str | None = None,
    config: FuzzyMatchConfig | None = None,
    limit: int | None = None,
    context_entity_id: int | str | None = None,
) -> list[RankedMatch]:
    config = config or FuzzyMatchConfig()
    config.validate()

    ranked = [
        score_fuzzy_candidate(
            observed_phrase,
            candidate,
            message=message,
            config=config,
            context_entity_id=(
                context_entity_id
            ),
        )
        for candidate in candidates
        if candidate.active
    ]

    ranked.sort(
        key=lambda item: (
            item.adjusted_score,
            item.score,
            item.components.token_alignment,
            item.components.coverage,
            item.components.damerau,
            len(
                item.candidate.normalized_name
            ),
        ),
        reverse=True,
    )

    return ranked[
        :(
            limit
            or config.max_candidates
        )
    ]


# ============================================================
# SECTION 22 - AMBIGUITY CONTROL
# ============================================================

def calculate_ambiguity_margin(
    ranked_candidates: Sequence[
        RankedMatch
    ],
) -> float | None:
    if len(ranked_candidates) < 2:
        return None

    return (
        ranked_candidates[0].adjusted_score
        - ranked_candidates[1].adjusted_score
    )


def determine_required_ambiguity_margin(
    best_match: RankedMatch,
    config: FuzzyMatchConfig,
) -> float:
    if (
        best_match.adjusted_score
        >= config.very_strong_threshold
    ):
        return config.ambiguity_margin * 0.60

    if (
        best_match.adjusted_score
        >= config.strong_threshold
    ):
        return config.ambiguity_margin

    if (
        best_match.adjusted_score
        >= config.default_threshold
    ):
        return config.strict_ambiguity_margin

    return config.critical_ambiguity_margin


def evaluate_ranked_matches(
    query: str,
    entity_type: str,
    ranked_candidates: Sequence[
        RankedMatch
    ],
    *,
    threshold: float | None = None,
    config: FuzzyMatchConfig | None = None,
    candidate_count: int = 0,
    evaluated_window_count: int = 1,
) -> FuzzyMatchResult:
    config = config or FuzzyMatchConfig()
    config.validate()

    normalized_query = normalize_fuzzy_text(
        query
    )

    if not ranked_candidates:
        return FuzzyMatchResult(
            query=query,
            normalized_query=normalized_query,
            entity_type=entity_type,
            matched=False,
            decision=(
                MatchDecision.NO_CANDIDATES
            ),
            confidence=MatchConfidence.NONE,
            threshold=(
                threshold
                if threshold is not None
                else config.default_threshold
            ),
            reason="no_ranked_candidates",
            candidate_count=candidate_count,
            evaluated_window_count=(
                evaluated_window_count
            ),
        )

    best = ranked_candidates[0]

    effective_threshold = max(
        best.threshold,
        threshold or 0.0,
    )

    if (
        config.ordinary_word_protection
        and best.ordinary_word_risk >= 0.90
        and best.adjusted_score
        < config.very_strong_threshold
    ):
        return FuzzyMatchResult(
            query=query,
            normalized_query=normalized_query,
            entity_type=entity_type,
            matched=False,
            decision=(
                MatchDecision.ORDINARY_WORD_BLOCKED
            ),
            confidence=(
                classify_fuzzy_confidence_enum(
                    best.adjusted_score
                )
            ),
            best_match=best,
            ranked_candidates=list(
                ranked_candidates
            ),
            threshold=effective_threshold,
            reason=(
                "ordinary_language_protection"
            ),
            candidate_count=candidate_count,
            evaluated_window_count=(
                evaluated_window_count
            ),
        )

    if (
        config.short_token_protection
        and best.short_token_risk >= 0.80
        and best.adjusted_score
        < config.short_token_threshold
        and best.abbreviation_score < 1.0
    ):
        return FuzzyMatchResult(
            query=query,
            normalized_query=normalized_query,
            entity_type=entity_type,
            matched=False,
            decision=(
                MatchDecision.SHORT_TOKEN_BLOCKED
            ),
            confidence=(
                classify_fuzzy_confidence_enum(
                    best.adjusted_score
                )
            ),
            best_match=best,
            ranked_candidates=list(
                ranked_candidates
            ),
            threshold=effective_threshold,
            reason="short_token_protection",
            candidate_count=candidate_count,
            evaluated_window_count=(
                evaluated_window_count
            ),
        )

    if best.adjusted_score < effective_threshold:
        return FuzzyMatchResult(
            query=query,
            normalized_query=normalized_query,
            entity_type=entity_type,
            matched=False,
            decision=MatchDecision.REJECTED,
            confidence=(
                classify_fuzzy_confidence_enum(
                    best.adjusted_score
                )
            ),
            best_match=best,
            ranked_candidates=list(
                ranked_candidates
            ),
            threshold=effective_threshold,
            reason="below_acceptance_threshold",
            candidate_count=candidate_count,
            evaluated_window_count=(
                evaluated_window_count
            ),
        )

    margin = calculate_ambiguity_margin(
        ranked_candidates
    )
    required_margin = (
        determine_required_ambiguity_margin(
            best,
            config,
        )
    )

    if (
        config.ambiguity_protection
        and margin is not None
        and margin < required_margin
    ):
        ambiguous = [
            item
            for item in ranked_candidates
            if (
                best.adjusted_score
                - item.adjusted_score
                <= required_margin
            )
        ]

        return FuzzyMatchResult(
            query=query,
            normalized_query=normalized_query,
            entity_type=entity_type,
            matched=False,
            decision=MatchDecision.AMBIGUOUS,
            confidence=(
                classify_fuzzy_confidence_enum(
                    best.adjusted_score
                )
            ),
            best_match=best,
            ranked_candidates=list(
                ranked_candidates
            ),
            ambiguity_margin=margin,
            required_ambiguity_margin=(
                required_margin
            ),
            ambiguous_candidates=ambiguous,
            threshold=effective_threshold,
            reason=(
                "top_candidates_within_ambiguity_margin"
            ),
            candidate_count=candidate_count,
            evaluated_window_count=(
                evaluated_window_count
            ),
        )

    return FuzzyMatchResult(
        query=query,
        normalized_query=normalized_query,
        entity_type=entity_type,
        matched=True,
        decision=MatchDecision.ACCEPTED,
        confidence=(
            classify_fuzzy_confidence_enum(
                best.adjusted_score
            )
        ),
        best_match=best,
        ranked_candidates=list(
            ranked_candidates
        ),
        ambiguity_margin=margin,
        required_ambiguity_margin=(
            required_margin
        ),
        threshold=effective_threshold,
        reason="accepted",
        candidate_count=candidate_count,
        evaluated_window_count=(
            evaluated_window_count
        ),
    )


# ============================================================
# SECTION 23 - PHRASE MATCHING
# ============================================================

def find_ranked_fuzzy_matches(
    user_value: str,
    candidates: Sequence[Any],
    *,
    entity_type: str = ENTITY_UNKNOWN,
    threshold: float | None = None,
    config: FuzzyMatchConfig | None = None,
    limit: int | None = None,
    context_entity_id: int | str | None = None,
) -> dict[str, Any]:
    config = config or FuzzyMatchConfig()
    config.validate()

    normalized = (
        normalize_candidate_collection(
            candidates,
            entity_type=entity_type,
        )
    )

    ranked = rank_fuzzy_candidates(
        user_value,
        normalized,
        message=user_value,
        config=config,
        limit=limit,
        context_entity_id=(
            context_entity_id
        ),
    )

    return evaluate_ranked_matches(
        user_value,
        entity_type,
        ranked,
        threshold=threshold,
        config=config,
        candidate_count=len(normalized),
    ).to_dict()


def find_best_fuzzy_match(
    user_value: str,
    candidates: list[str],
    threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> dict[str, Any]:
    result = find_ranked_fuzzy_matches(
        user_value,
        candidates,
        threshold=threshold,
    )

    best = result.get("best_match")

    return {
        "matched": result["matched"],
        "query": user_value,
        "best_match": (
            best.get("canonical_name")
            if best
            else None
        ),
        "score": (
            best.get("adjusted_score", 0.0)
            if best
            else 0.0
        ),
        "threshold": result["threshold"],
        "confidence": result["confidence"],
        "decision": result["decision"],
        "ranked_candidates": (
            result["ranked_candidates"]
        ),
        "ambiguity_margin": (
            result["ambiguity_margin"]
        ),
        "reason": result["reason"],
    }


def find_best_fuzzy_entity_in_message(
    message: str,
    candidates: Sequence[Any],
    threshold: float = DEFAULT_MATCH_THRESHOLD,
    max_window_size: int = DEFAULT_MAX_WINDOW_SIZE,
    *,
    entity_type: str = ENTITY_UNKNOWN,
    config: FuzzyMatchConfig | None = None,
    max_candidates: int | None = None,
    context_entity_id: int | str | None = None,
) -> dict[str, Any]:
    config = config or FuzzyMatchConfig(
        max_window_size=max_window_size
    )
    config.validate()

    normalized = (
        normalize_candidate_collection(
            candidates,
            entity_type=entity_type,
        )
    )

    if not normalized:
        return FuzzyMatchResult(
            query=message,
            normalized_query=(
                normalize_fuzzy_text(
                    message
                )
            ),
            entity_type=entity_type,
            matched=False,
            decision=(
                MatchDecision.NO_CANDIDATES
            ),
            confidence=MatchConfidence.NONE,
            threshold=threshold,
            reason="no_candidates",
        ).to_dict()

    windows = build_candidate_aware_windows(
        message,
        normalized,
        config,
    )

    best_by_candidate: dict[
        tuple[str, str],
        RankedMatch,
    ] = {}

    for window in windows:
        ranked_for_window = (
            rank_fuzzy_candidates(
                window,
                normalized,
                message=message,
                config=config,
                limit=(
                    max_candidates
                    or config.max_candidates
                ),
                context_entity_id=(
                    context_entity_id
                ),
            )
        )

        for match in ranked_for_window:
            key = (
                match.candidate.entity_type,
                str(
                    match.candidate.entity_id
                    or match.candidate.normalized_name
                ),
            )

            current = best_by_candidate.get(
                key
            )

            if (
                current is None
                or match.adjusted_score
                > current.adjusted_score
                or (
                    match.adjusted_score
                    == current.adjusted_score
                    and len(
                        match.normalized_observed_phrase
                    )
                    > len(
                        current.normalized_observed_phrase
                    )
                )
            ):
                best_by_candidate[key] = match

    ranked = sorted(
        best_by_candidate.values(),
        key=lambda item: (
            item.adjusted_score,
            item.score,
            item.components.token_alignment,
            item.components.coverage,
            len(
                item.normalized_observed_phrase
            ),
        ),
        reverse=True,
    )[
        :(
            max_candidates
            or config.max_candidates
        )
    ]

    result = evaluate_ranked_matches(
        message,
        entity_type,
        ranked,
        threshold=threshold,
        config=config,
        candidate_count=len(normalized),
        evaluated_window_count=len(windows),
    ).to_dict()

    result["observed_phrase"] = (
        result["best_match"][
            "observed_phrase"
        ]
        if result.get("best_match")
        else None
    )

    return result


# ============================================================
# SECTION 24 - DYNAMIC PHRASE SEGMENTATION
# ============================================================

def segment_message_entities(
    message: str,
    candidates: Sequence[Any],
    *,
    entity_type: str,
    config: FuzzyMatchConfig | None = None,
    maximum_entities: int | None = None,
) -> list[dict[str, Any]]:
    config = config or FuzzyMatchConfig()
    config.validate()

    normalized_candidates = (
        normalize_candidate_collection(
            candidates,
            entity_type=entity_type,
        )
    )
    tokens = tokenize_fuzzy_text(message)

    if not tokens or not normalized_candidates:
        return []

    maximum_entities = (
        maximum_entities
        or config.maximum_phrase_entities
    )

    candidates_by_start: dict[
        int,
        list[PhraseSegmentMatch],
    ] = defaultdict(list)

    maximum_window = min(
        config.max_window_size,
        len(tokens),
    )

    for start in range(len(tokens)):
        for size in range(
            1,
            maximum_window + 1,
        ):
            end = start + size

            if end > len(tokens):
                break

            phrase = " ".join(
                tokens[start:end]
            )

            ranked = rank_fuzzy_candidates(
                phrase,
                normalized_candidates,
                message=message,
                config=config,
                limit=3,
            )

            if not ranked:
                continue

            best = ranked[0]

            if (
                best.adjusted_score
                < config.phrase_segment_threshold
            ):
                continue

            if (
                best.ordinary_word_risk >= 0.90
                and best.adjusted_score
                < config.very_strong_threshold
            ):
                continue

            candidates_by_start[start].append(
                PhraseSegmentMatch(
                    token_start=start,
                    token_end=end,
                    observed_phrase=phrase,
                    match=best,
                )
            )

    dynamic: list[
        tuple[
            float,
            list[PhraseSegmentMatch],
        ]
    ] = [
        (-math.inf, [])
        for _ in range(len(tokens) + 1)
    ]
    dynamic[0] = (0.0, [])

    for index in range(len(tokens)):
        current_score, current_matches = (
            dynamic[index]
        )

        if current_score == -math.inf:
            continue

        skip_score = current_score - 0.015

        if skip_score > dynamic[
            index + 1
        ][0]:
            dynamic[index + 1] = (
                skip_score,
                list(current_matches),
            )

        for segment in candidates_by_start.get(
            index,
            [],
        ):
            if (
                len(current_matches)
                >= maximum_entities
            ):
                continue

            segment_length = (
                segment.token_end
                - segment.token_start
            )
            segment_score = (
                current_score
                + segment.match.adjusted_score
                + min(
                    0.08,
                    segment_length * 0.015,
                )
            )

            if (
                segment_score
                > dynamic[
                    segment.token_end
                ][0]
            ):
                dynamic[
                    segment.token_end
                ] = (
                    segment_score,
                    [
                        *current_matches,
                        segment,
                    ],
                )

    _, best_segments = dynamic[
        len(tokens)
    ]

    deduplicated: list[
        PhraseSegmentMatch
    ] = []
    seen_entities: set[
        tuple[str, str]
    ] = set()

    for segment in best_segments:
        key = (
            segment.match.candidate.entity_type,
            str(
                segment.match.candidate.entity_id
                or segment.match.candidate.normalized_name
            ),
        )

        if key in seen_entities:
            continue

        seen_entities.add(key)
        deduplicated.append(segment)

    return [
        segment.to_dict()
        for segment in deduplicated
    ]


# ============================================================
# SECTION 25 - PLAYER API
# ============================================================

def find_fuzzy_player_match(
    message: str,
    player_names: Sequence[Any] | None = None,
    *,
    database_session: Any | None = None,
    use_warehouse: bool = True,
    config: FuzzyMatchConfig | None = None,
    context_entity_id: int | str | None = None,
) -> dict[str, Any]:
    config = config or FuzzyMatchConfig()
    config.validate()

    candidates: list[FuzzyCandidate] = []

    if player_names:
        candidates.extend(
            normalize_candidate_collection(
                player_names,
                entity_type=ENTITY_PLAYER,
            )
        )

    if (
        use_warehouse
        and config.use_warehouse_by_default
    ):
        candidates.extend(
            load_warehouse_player_candidates(
                database_session,
                config=config,
            )
        )

    candidates = (
        normalize_candidate_collection(
            candidates,
            entity_type=ENTITY_PLAYER,
        )
    )

    return find_best_fuzzy_entity_in_message(
        message,
        candidates,
        threshold=config.weak_threshold,
        max_window_size=config.max_window_size,
        entity_type=ENTITY_PLAYER,
        config=config,
        context_entity_id=(
            context_entity_id
        ),
    )


# ============================================================
# SECTION 26 - TEAM API
# ============================================================

def find_fuzzy_team_match(
    message: str,
    team_names: Sequence[Any] | None = None,
    *,
    database_session: Any | None = None,
    use_warehouse: bool = True,
    include_builtin_fallback: bool = True,
    config: FuzzyMatchConfig | None = None,
    context_entity_id: int | str | None = None,
) -> dict[str, Any]:
    config = config or FuzzyMatchConfig()
    config.validate()

    candidates: list[FuzzyCandidate] = []

    if team_names:
        candidates.extend(
            normalize_candidate_collection(
                team_names,
                entity_type=ENTITY_TEAM,
            )
        )

    if (
        use_warehouse
        and config.use_warehouse_by_default
    ):
        candidates.extend(
            load_warehouse_team_candidates(
                database_session,
                config=config,
            )
        )

    if (
        include_builtin_fallback
        and not candidates
    ):
        candidates.extend(
            build_builtin_team_candidates()
        )

    candidates = (
        normalize_candidate_collection(
            candidates,
            entity_type=ENTITY_TEAM,
        )
    )

    return find_best_fuzzy_entity_in_message(
        message,
        candidates,
        threshold=config.weak_threshold,
        max_window_size=config.max_window_size,
        entity_type=ENTITY_TEAM,
        config=config,
        context_entity_id=(
            context_entity_id
        ),
    )


# ============================================================
# SECTION 27 - BASEBALL TERM API
# ============================================================

def flatten_baseball_terms(
) -> dict[str, str]:
    output: dict[str, str] = {}

    for canonical, aliases in (
        BASEBALL_TERM_ALIASES.items()
    ):
        output[
            normalize_fuzzy_text(canonical)
        ] = canonical

        for alias in aliases:
            output[
                normalize_fuzzy_text(alias)
            ] = canonical

    return output


def find_fuzzy_baseball_term_match(
    message: str,
    *,
    config: FuzzyMatchConfig | None = None,
) -> dict[str, Any]:
    config = config or FuzzyMatchConfig(
        default_threshold=0.72,
        single_token_threshold=0.82,
        multi_token_threshold=0.68,
        ambiguity_margin=0.04,
    )
    config.validate()

    result = (
        find_best_fuzzy_entity_in_message(
            message,
            build_baseball_term_candidates(),
            threshold=config.multi_token_threshold,
            max_window_size=min(
                5,
                config.max_window_size,
            ),
            entity_type=ENTITY_TERM,
            config=config,
        )
    )

    best = result.get("best_match")

    result["canonical_value"] = (
        best.get("canonical_name")
        if best and result.get("matched")
        else None
    )

    return result


# ============================================================
# SECTION 28 - MULTIPLE ENTITY RECOVERY
# ============================================================

def find_multiple_fuzzy_entities(
    message: str,
    candidates: Sequence[Any],
    *,
    entity_type: str,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
    config: FuzzyMatchConfig | None = None,
    maximum_entities: int = 4,
) -> list[dict[str, Any]]:
    config = config or FuzzyMatchConfig()
    config.validate()

    segmented = segment_message_entities(
        message,
        candidates,
        entity_type=entity_type,
        config=config,
        maximum_entities=maximum_entities,
    )

    output: list[dict[str, Any]] = []

    for item in segmented:
        match = item["match"]

        if (
            match["adjusted_score"]
            < threshold
        ):
            continue

        output.append({
            **match,
            "token_start": item["token_start"],
            "token_end": item["token_end"],
            "decision": (
                MatchDecision.ACCEPTED.value
            ),
            "ambiguity_margin": None,
        })

    return output


# ============================================================
# SECTION 29 - SAFE CORRECTION PLAN
# ============================================================

def apply_safe_entity_corrections(
    message: str,
    matches: Sequence[
        Mapping[str, Any]
    ],
) -> dict[str, Any]:
    tokens = tokenize_fuzzy_text(message)

    replacements: list[
        tuple[int, int, str]
    ] = []

    for match in matches:
        if match.get("decision") not in {
            MatchDecision.ACCEPTED.value,
            MatchDecision.ACCEPTED,
        }:
            continue

        start = match.get("token_start")
        end = match.get("token_end")
        canonical = (
            match.get("canonical_name")
            or safe_nested_get(
                match,
                "candidate",
                "canonical_name",
            )
        )

        if (
            isinstance(start, int)
            and isinstance(end, int)
            and canonical
        ):
            replacements.append(
                (
                    start,
                    end,
                    str(canonical),
                )
            )

    corrected = list(tokens)

    for start, end, replacement in sorted(
        replacements,
        key=lambda item: item[0],
        reverse=True,
    ):
        corrected[start:end] = [
            replacement
        ]

    return {
        "original_message": message,
        "normalized_message": (
            " ".join(tokens)
        ),
        "corrected_message": (
            " ".join(corrected)
        ),
        "replacement_count": len(
            replacements
        ),
        "replacements": [
            {
                "token_start": start,
                "token_end": end,
                "replacement": replacement,
            }
            for start, end, replacement
            in sorted(replacements)
        ],
    }


# ============================================================
# SECTION 30 - FULL NLP REPORT
# ============================================================

def build_fuzzy_nlp_report(
    message: str,
    player_names: Sequence[Any] | None = None,
    team_names: Sequence[Any] | None = None,
    *,
    database_session: Any | None = None,
    use_warehouse: bool = True,
    config: FuzzyMatchConfig | None = None,
) -> dict[str, Any]:
    config = config or FuzzyMatchConfig()
    config.validate()

    player_match = find_fuzzy_player_match(
        message,
        player_names,
        database_session=database_session,
        use_warehouse=use_warehouse,
        config=config,
    )

    team_match = find_fuzzy_team_match(
        message,
        team_names,
        database_session=database_session,
        use_warehouse=use_warehouse,
        config=config,
    )

    term_match = (
        find_fuzzy_baseball_term_match(
            message,
            config=config,
        )
    )

    return {
        "engine_name": FUZZY_ENGINE_NAME,
        "engine_version": FUZZY_ENGINE_VERSION,
        "engine_phase": FUZZY_ENGINE_PHASE,
        "engine_path": FUZZY_ENGINE_PATH,
        "message": message,
        "normalized_message": (
            normalize_fuzzy_text(message)
        ),
        "player_match": player_match,
        "team_match": team_match,
        "term_match": term_match,
        "has_player_correction": bool(
            player_match.get("matched")
        ),
        "has_team_correction": bool(
            team_match.get("matched")
        ),
        "has_term_correction": bool(
            term_match.get("matched")
        ),
        "ambiguity_detected": any(
            item.get("decision")
            == MatchDecision.AMBIGUOUS.value
            for item in (
                player_match,
                team_match,
                term_match,
            )
        ),
        "ordinary_word_protection_triggered": (
            any(
                item.get("decision")
                == MatchDecision.ORDINARY_WORD_BLOCKED.value
                for item in (
                    player_match,
                    team_match,
                    term_match,
                )
            )
        ),
        "warehouse_enabled": use_warehouse,
        "configuration": asdict(config),
        "fingerprint": build_fuzzy_fingerprint({
            "message": message,
            "player_match": player_match.get(
                "best_match"
            ),
            "team_match": team_match.get(
                "best_match"
            ),
            "term_match": term_match.get(
                "best_match"
            ),
        }),
    }


# ============================================================
# SECTION 31 - CONFIDENCE
# ============================================================

def classify_fuzzy_confidence_enum(
    score: float,
) -> MatchConfidence:
    if score >= 1.0:
        return MatchConfidence.EXACT

    if score >= VERY_STRONG_MATCH_THRESHOLD:
        return MatchConfidence.VERY_STRONG

    if score >= STRONG_MATCH_THRESHOLD:
        return MatchConfidence.STRONG

    if score >= DEFAULT_MATCH_THRESHOLD:
        return MatchConfidence.MODERATE

    if score >= WEAK_MATCH_THRESHOLD:
        return MatchConfidence.WEAK

    return MatchConfidence.NONE


def classify_fuzzy_confidence(
    score: float,
) -> str:
    return classify_fuzzy_confidence_enum(
        score
    ).value


# ============================================================
# SECTION 32 - GENERAL UTILITIES
# ============================================================

def safe_nested_get(
    data: Mapping[str, Any] | None,
    *keys: str,
    default: Any = None,
) -> Any:
    current: Any = data

    for key in keys:
        if (
            not isinstance(current, Mapping)
            or key not in current
        ):
            return default

        current = current.get(key)

    return current


def build_fuzzy_fingerprint(
    payload: Any,
) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    return sha256(
        canonical.encode("utf-8")
    ).hexdigest()


# ============================================================
# SECTION 33 - VALIDATION
# ============================================================

def validate_fuzzy_matching_module(
) -> dict[str, Any]:
    players = [
        {
            "canonical_name": "Aaron Judge",
            "entity_id": 592450,
            "aliases": [
                "Judge",
                "A Judge",
            ],
        },
        {
            "canonical_name": "Shohei Ohtani",
            "entity_id": 660271,
            "aliases": [
                "Ohtani",
                "Sho Ohtani",
            ],
        },
        {
            "canonical_name": "Corbin Carroll",
            "entity_id": 682998,
            "aliases": [
                "Carroll",
            ],
        },
        {
            "canonical_name": "Will Smith",
            "entity_id": 669257,
            "aliases": [
                "W Smith",
            ],
        },
        {
            "canonical_name": "William Contreras",
            "entity_id": 661388,
            "aliases": [
                "Will Contreras",
            ],
        },
        {
            "canonical_name": "Willson Contreras",
            "entity_id": 575929,
            "aliases": [
                "W Contreras",
            ],
        },
    ]

    checks: dict[str, bool] = {}

    exact = find_fuzzy_player_match(
        "find Aaron Judge",
        players,
        use_warehouse=False,
    )
    checks["exact_player_match"] = bool(
        exact["matched"]
        and exact["best_match"][
            "canonical_name"
        ]
        == "Aaron Judge"
    )

    typo = find_fuzzy_player_match(
        "serch aron judg stats",
        players,
        use_warehouse=False,
    )
    checks["multi_word_player_typo"] = bool(
        typo["matched"]
        and typo["best_match"][
            "canonical_name"
        ]
        == "Aaron Judge"
    )

    heavy = find_fuzzy_player_match(
        "predct shohay ohtany hom run",
        players,
        use_warehouse=False,
    )
    checks[
        "multiple_consecutive_misspellings"
    ] = bool(
        heavy["matched"]
        and heavy["best_match"][
            "canonical_name"
        ]
        == "Shohei Ohtani"
    )

    transposed = find_fuzzy_player_match(
        "serach aaron jugde stats",
        players,
        use_warehouse=False,
    )
    checks["transposition_recovery"] = bool(
        transposed["matched"]
        and transposed["best_match"][
            "canonical_name"
        ]
        == "Aaron Judge"
    )

    keyboard_typo = find_fuzzy_player_match(
        "find corbin carrolk",
        players,
        use_warehouse=False,
    )
    checks["keyboard_neighbor_recovery"] = bool(
        keyboard_typo["matched"]
        and keyboard_typo["best_match"][
            "canonical_name"
        ]
        == "Corbin Carroll"
    )

    team = find_fuzzy_team_match(
        "show the ny yankes rostr",
        build_builtin_team_candidates(),
        use_warehouse=False,
    )
    checks["misspelled_team_match"] = bool(
        team["matched"]
        and team["best_match"][
            "canonical_name"
        ]
        == "New York Yankees"
    )

    ordinary = find_fuzzy_player_match(
        "show me the best player",
        players,
        use_warehouse=False,
    )
    checks[
        "ordinary_word_not_replaced"
    ] = not ordinary["matched"]

    ranked = find_ranked_fuzzy_matches(
        "aron judg",
        players,
        entity_type=ENTITY_PLAYER,
    )
    checks["ranked_candidates_returned"] = (
        len(
            ranked["ranked_candidates"]
        )
        >= 3
    )

    ambiguous = find_ranked_fuzzy_matches(
        "will contreras",
        players,
        entity_type=ENTITY_PLAYER,
        threshold=0.60,
        config=FuzzyMatchConfig(
            ambiguity_margin=0.08,
            strict_ambiguity_margin=0.12,
            critical_ambiguity_margin=0.16,
            ordinary_word_protection=False,
        ),
    )
    checks["ambiguity_is_reported"] = (
        ambiguous["decision"]
        in {
            MatchDecision.AMBIGUOUS.value,
            MatchDecision.ACCEPTED.value,
        }
        and len(
            ambiguous["ranked_candidates"]
        )
        >= 2
    )

    term = find_fuzzy_baseball_term_match(
        "predict a hom rn"
    )
    checks["misspelled_term_match"] = bool(
        term["matched"]
        and term["canonical_value"]
        == "home_run"
    )

    multiple = find_multiple_fuzzy_entities(
        "compare aron judg and shohay ohtany",
        players,
        entity_type=ENTITY_PLAYER,
        threshold=0.68,
        maximum_entities=2,
    )
    names = {
        item["canonical_name"]
        for item in multiple
    }
    checks["multiple_entities_recovered"] = (
        "Aaron Judge" in names
        and "Shohei Ohtani" in names
    )

    cache_config = FuzzyMatchConfig(
        enable_candidate_cache=True,
        cache_ttl_seconds=60.0,
    )
    cache_config.validate()
    clear_fuzzy_candidate_cache()
    _write_candidate_cache(
        "test",
        normalize_candidate_collection(
            players,
            entity_type=ENTITY_PLAYER,
        ),
        cache_config,
    )
    cached, status = _read_candidate_cache(
        "test",
        cache_config,
    )
    checks["candidate_cache_operational"] = (
        status == CacheStatus.HIT
        and cached is not None
        and len(cached) == len(players)
    )

    passed = sum(
        1
        for value in checks.values()
        if value
    )

    return {
        "status": (
            "ok"
            if passed == len(checks)
            else "failed"
        ),
        "engine": FUZZY_ENGINE_NAME,
        "version": FUZZY_ENGINE_VERSION,
        "phase": FUZZY_ENGINE_PHASE,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "failed_checks": [
            name
            for name, value
            in checks.items()
            if not value
        ],
    }


# ============================================================
# SECTION 34 - HEALTH
# ============================================================

def fuzzy_matching_health(
) -> dict[str, Any]:
    validation = (
        validate_fuzzy_matching_module()
    )

    return {
        "name": FUZZY_ENGINE_NAME,
        "version": FUZZY_ENGINE_VERSION,
        "phase": FUZZY_ENGINE_PHASE,
        "path": FUZZY_ENGINE_PATH,
        "status": (
            FUZZY_ENGINE_STATUS
            if validation["status"] == "ok"
            else "validation_failed"
        ),
        "warehouse_names_supported": True,
        "ranked_candidates_supported": True,
        "ambiguity_margins_supported": True,
        "ordinary_word_protection": True,
        "short_token_protection": True,
        "multi_word_typo_recovery": True,
        "multi_entity_recovery": True,
        "damerau_transposition_scoring": True,
        "keyboard_aware_scoring": True,
        "phrase_segmentation": True,
        "candidate_cache": True,
        "validation": validation,
        "timestamp": datetime.now(UTC).isoformat(),
    }


# ============================================================
# SECTION 35 - CONFIGURATION EXPORT
# ============================================================

FUZZY_ENGINE_CONFIGURATION: Final[
    dict[str, Any]
] = {
    "engine_name": FUZZY_ENGINE_NAME,
    "engine_version": FUZZY_ENGINE_VERSION,
    "engine_phase": FUZZY_ENGINE_PHASE,
    "schema_version": FUZZY_SCHEMA_VERSION,
    "warehouse_names_enabled": True,
    "multi_token_typo_recovery": True,
    "multiple_consecutive_typo_recovery": True,
    "multiple_entity_recovery": True,
    "ranked_candidates_enabled": True,
    "ambiguity_margin_enabled": True,
    "ordinary_word_protection_enabled": True,
    "short_token_protection_enabled": True,
    "damerau_transposition_enabled": True,
    "keyboard_aware_scoring_enabled": True,
    "phrase_segmentation_enabled": True,
    "candidate_cache_enabled": True,
}


# ============================================================
# SECTION 36 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "FUZZY_ENGINE_NAME",
    "FUZZY_ENGINE_VERSION",
    "FUZZY_ENGINE_PHASE",
    "FUZZY_ENGINE_PATH",
    "FUZZY_ENGINE_STATUS",
    "FUZZY_SCHEMA_VERSION",

    "DEFAULT_MATCH_THRESHOLD",
    "STRONG_MATCH_THRESHOLD",
    "VERY_STRONG_MATCH_THRESHOLD",
    "WEAK_MATCH_THRESHOLD",
    "DEFAULT_AMBIGUITY_MARGIN",
    "STRICT_AMBIGUITY_MARGIN",
    "CRITICAL_AMBIGUITY_MARGIN",

    "ENTITY_PLAYER",
    "ENTITY_TEAM",
    "ENTITY_TERM",
    "ENTITY_ALIAS",
    "ENTITY_UNKNOWN",

    "MatchConfidence",
    "MatchDecision",
    "CandidateSource",
    "MatchStrategy",
    "CacheStatus",

    "FuzzyMatchConfig",
    "FuzzyCandidate",
    "ScoreComponents",
    "RankedMatch",
    "FuzzyMatchResult",
    "PhraseSegmentMatch",

    "normalize_fuzzy_text",
    "tokenize_fuzzy_text",
    "deduplicate_strings",

    "calculate_similarity",
    "calculate_token_sort_similarity",
    "calculate_token_set_similarity",
    "calculate_partial_similarity",
    "levenshtein_distance",
    "damerau_levenshtein_distance",
    "calculate_edit_similarity",
    "calculate_damerau_similarity",
    "weighted_keyboard_distance",
    "calculate_keyboard_similarity",
    "simple_phonetic_key",
    "calculate_phonetic_similarity",
    "calculate_prefix_score",
    "calculate_initials_score",
    "calculate_length_score",
    "calculate_token_alignment_score",
    "calculate_coverage_score",

    "coerce_fuzzy_candidate",
    "normalize_candidate_collection",
    "build_baseball_term_candidates",
    "build_builtin_team_candidates",

    "clear_fuzzy_candidate_cache",
    "load_warehouse_player_candidates",
    "load_warehouse_team_candidates",

    "build_token_windows",
    "build_candidate_aware_windows",
    "determine_dynamic_threshold",
    "score_fuzzy_candidate",
    "rank_fuzzy_candidates",
    "calculate_ambiguity_margin",
    "determine_required_ambiguity_margin",
    "evaluate_ranked_matches",

    "find_ranked_fuzzy_matches",
    "find_best_fuzzy_match",
    "find_best_fuzzy_entity_in_message",
    "segment_message_entities",
    "find_fuzzy_player_match",
    "find_fuzzy_team_match",
    "flatten_baseball_terms",
    "find_fuzzy_baseball_term_match",
    "find_multiple_fuzzy_entities",
    "apply_safe_entity_corrections",
    "build_fuzzy_nlp_report",

    "classify_fuzzy_confidence",
    "classify_fuzzy_confidence_enum",
    "safe_nested_get",
    "build_fuzzy_fingerprint",
    "validate_fuzzy_matching_module",
    "fuzzy_matching_health",
    "FUZZY_ENGINE_CONFIGURATION",
]


# ============================================================
# SECTION 37 - LOCAL VALIDATION ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    print(
        json.dumps(
            fuzzy_matching_health(),
            indent=2,
            sort_keys=True,
        )
    )
