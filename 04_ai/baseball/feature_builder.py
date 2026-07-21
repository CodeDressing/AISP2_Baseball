# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# FILE: 04_ai/baseball/feature_builder.py
# PHASE: Phase 16 Part 3A
# PURPOSE:
#   Live player-specific baseball feature builder for the
#   Prediction Workbench.
#
# CORE RESPONSIBILITY:
#   selected player/team/outcome
#   -> resolve player
#   -> resolve team
#   -> find best season stat row
#   -> derive player-specific technical rates
#   -> return one stable feature packet for probability_engine.py
#
# IMPORTANT:
#   This file is intentionally focused on live prediction feature
#   construction. It is not a model trainer. Training dataset builders
#   can exist elsewhere, but the Workbench needs a deterministic,
#   source-backed player feature packet first.
# ============================================================

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any, Final, Iterable, Mapping, MutableMapping, Sequence
import difflib
import json
import logging
import math
import re
import sys
import urllib.parse
import urllib.request


# ============================================================
# SECTION 02 - MODULE METADATA
# ============================================================

MODULE_NAME: Final[str] = "baseball_live_feature_builder"
MODULE_PATH: Final[str] = "04_ai/baseball/feature_builder.py"
MODULE_VERSION: Final[str] = "16.3A.0"
MODULE_PHASE: Final[str] = "Phase 16 Part 3A"
MODULE_STATUS: Final[str] = "live_player_prediction_feature_ready"
MODULE_ASSISTANT: Final[str] = "Alfred"
UTC: Final[timezone] = timezone.utc

LOGGER = logging.getLogger(__name__)


# ============================================================
# SECTION 03 - PATH BOOTSTRAP
# ============================================================

_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parents[2] if len(_THIS_FILE.parents) >= 3 else Path.cwd()
_DATABASE_DIR = _PROJECT_ROOT / "01_database"

for _candidate_path in (_PROJECT_ROOT, _DATABASE_DIR):
    _candidate_text = str(_candidate_path)
    if _candidate_text not in sys.path:
        sys.path.insert(0, _candidate_text)


# ============================================================
# SECTION 04 - OPTIONAL DATABASE IMPORTS
# ============================================================

_DATABASE_IMPORT_ERROR: str | None = None
_MODELS_IMPORT_ERROR: str | None = None

try:
    import database as _database_module  # type: ignore
except Exception as exc:  # pragma: no cover
    _database_module = None  # type: ignore
    _DATABASE_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

try:
    import models as _models_module  # type: ignore
except Exception as exc:  # pragma: no cover
    _models_module = None  # type: ignore
    _MODELS_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


# ============================================================
# SECTION 05 - EXCEPTIONS
# ============================================================

class FeatureBuilderError(RuntimeError):
    """Base exception for live feature construction failures."""


class PlayerResolutionError(FeatureBuilderError):
    """Raised when the selected player cannot be resolved."""


class StatResolutionError(FeatureBuilderError):
    """Raised when player stat resolution fails unexpectedly."""


class FeatureSchemaError(FeatureBuilderError):
    """Raised when expected schema objects are unavailable."""


# ============================================================
# SECTION 06 - ENUMERATIONS
# ============================================================

class FeatureSourceStatus(str, Enum):
    DATABASE_PLAYER_SEASON_STATS = "database_player_season_stats"
    LIVE_MLB_STATS_API = "live_mlb_stats_api"
    REQUEST_SUPPLIED_STAT_LINE = "request_supplied_stat_line"
    NO_HITTING_SAMPLE = "no_hitting_sample"
    PLAYER_NOT_RESOLVED = "player_not_resolved"
    DATABASE_UNAVAILABLE = "database_unavailable"
    ERROR = "error"


class SampleQuality(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NO_SAMPLE = "no_sample"


class PredictionFamily(str, Enum):
    HITTER = "hitter"
    PITCHER = "pitcher"
    TEAM = "team"
    UNKNOWN = "unknown"


# ============================================================
# SECTION 07 - CONSTANTS
# ============================================================

PLAYER_NAME_FIELDS: Final[tuple[str, ...]] = (
    "player_name",
    "full_name",
    "name",
    "display_name",
    "selected_player",
)

PLAYER_ID_FIELDS: Final[tuple[str, ...]] = (
    "player_id",
    "mlb_player_id",
    "selected_player_id",
    "person_id",
    "id",
)

TEAM_NAME_FIELDS: Final[tuple[str, ...]] = (
    "team_name",
    "selected_team",
    "current_team_name",
    "club_name",
)

TEAM_ID_FIELDS: Final[tuple[str, ...]] = (
    "team_id",
    "mlb_team_id",
    "selected_team_id",
    "current_team_id",
)

OUTCOME_FIELDS: Final[tuple[str, ...]] = (
    "outcome_key",
    "outcome",
    "selected_outcome",
    "prediction_type",
)

COUNT_FIELDS: Final[tuple[str, ...]] = (
    "games_played",
    "plate_appearances",
    "at_bats",
    "runs",
    "hits",
    "singles",
    "doubles",
    "triples",
    "home_runs",
    "rbi",
    "walks",
    "intentional_walks",
    "hit_by_pitch",
    "sacrifice_flies",
    "strikeouts",
    "stolen_bases",
    "caught_stealing",
)

RATE_FIELDS: Final[tuple[str, ...]] = (
    "batting_average",
    "on_base_percentage",
    "slugging_percentage",
    "ops",
    "isolated_power",
    "babip",
    "walk_rate",
    "strikeout_rate",
    "home_run_rate",
    "woba",
    "wrc_plus",
)

PREDICTION_OUTCOME_ALIASES: Final[dict[str, str]] = {
    "home_run": "home_run",
    "home runs": "home_run",
    "hr": "home_run",
    "homer": "home_run",
    "hit": "hit",
    "hits": "hit",
    "single": "single",
    "double": "double",
    "triple": "triple",
    "walk": "walk",
    "bb": "walk",
    "strikeout": "strikeout",
    "k": "strikeout",
    "rbi": "rbi",
    "run": "run_scored",
    "runs": "run_scored",
    "run_scored": "run_scored",
    "total_bases": "total_bases",
    "tb": "total_bases",
}

OUTCOME_FAMILY: Final[dict[str, PredictionFamily]] = {
    "home_run": PredictionFamily.HITTER,
    "hit": PredictionFamily.HITTER,
    "single": PredictionFamily.HITTER,
    "double": PredictionFamily.HITTER,
    "triple": PredictionFamily.HITTER,
    "walk": PredictionFamily.HITTER,
    "strikeout": PredictionFamily.HITTER,
    "rbi": PredictionFamily.HITTER,
    "run_scored": PredictionFamily.HITTER,
    "total_bases": PredictionFamily.HITTER,
}

LEAGUE_BASELINE_RATES: Final[dict[str, float]] = {
    "home_run": 0.032,
    "hit": 0.245,
    "single": 0.150,
    "double": 0.045,
    "triple": 0.004,
    "walk": 0.086,
    "strikeout": 0.220,
    "rbi": 0.135,
    "run_scored": 0.150,
    "total_bases": 0.360,
}

NO_SAMPLE_FALLBACK_PROBABILITY: Final[dict[str, float]] = {
    "home_run": 0.002,
    "hit": 0.050,
    "single": 0.035,
    "double": 0.008,
    "triple": 0.001,
    "walk": 0.020,
    "strikeout": 0.220,
    "rbi": 0.020,
    "run_scored": 0.020,
    "total_bases": 0.080,
}

TECHNICAL_RATE_KEYS: Final[tuple[str, ...]] = (
    "hr_per_pa",
    "hit_per_ab",
    "single_per_ab",
    "double_per_ab",
    "triple_per_ab",
    "bb_per_pa",
    "k_per_pa",
    "rbi_per_pa",
    "run_per_pa",
    "tb_per_ab",
    "xbh_per_pa",
    "times_on_base_per_pa",
)


# ============================================================
# SECTION 08 - LOW-LEVEL UTILITY FUNCTIONS
# ============================================================

def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def normalize_name_for_match(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def to_float(value: Any, default: float = 0.0) -> float:
    if value is None or isinstance(value, bool):
        return float(default)

    if isinstance(value, (int, float, Decimal)):
        try:
            numeric = float(value)
            return numeric if math.isfinite(numeric) else float(default)
        except Exception:
            return float(default)

    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if not cleaned:
            return float(default)
        if cleaned.endswith("%"):
            cleaned = cleaned[:-1]
            try:
                return float(cleaned) / 100.0
            except Exception:
                return float(default)
        try:
            numeric = float(Decimal(cleaned))
            return numeric if math.isfinite(numeric) else float(default)
        except (InvalidOperation, ValueError, OverflowError):
            return float(default)

    return float(default)


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(to_float(value, float(default))))
    except Exception:
        return default


def safe_divide(
    numerator: Any,
    denominator: Any,
    *,
    default: float = 0.0,
    epsilon: float = 1e-12,
) -> float:
    n = to_float(numerator)
    d = to_float(denominator)
    if not math.isfinite(n) or not math.isfinite(d) or abs(d) <= epsilon:
        return float(default)
    result = n / d
    return result if math.isfinite(result) else float(default)


def clamp(value: Any, minimum: float, maximum: float, default: float = 0.0) -> float:
    numeric = to_float(value, default)
    return min(max(numeric, minimum), maximum)


def pct(value: Any, digits: int = 1) -> float:
    return round(to_float(value) * 100.0, digits)


def object_to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if isinstance(value, Mapping):
        return dict(value)

    if is_dataclass(value):
        return asdict(value)

    if hasattr(value, "__table__"):
        output: dict[str, Any] = {}
        try:
            for column in value.__table__.columns:
                output[column.name] = getattr(value, column.name)
            return output
        except Exception:
            pass

    if hasattr(value, "__dict__"):
        return {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_")
        }

    return {}


def first_present(
    payload: Mapping[str, Any],
    names: Sequence[str],
    default: Any = None,
) -> Any:
    for name in names:
        if name in payload and payload.get(name) not in (None, ""):
            return payload.get(name)

    normalized_payload = {
        normalize_key(key): value
        for key, value in payload.items()
    }

    for name in names:
        key = normalize_key(name)
        if key in normalized_payload and normalized_payload.get(key) not in (None, ""):
            return normalized_payload.get(key)

    return default


def parse_outcome(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "home_run"

    normalized = normalize_key(raw).replace("_", " ")
    compact = normalize_key(raw)

    if raw in PREDICTION_OUTCOME_ALIASES:
        return PREDICTION_OUTCOME_ALIASES[raw]

    if normalized in PREDICTION_OUTCOME_ALIASES:
        return PREDICTION_OUTCOME_ALIASES[normalized]

    if compact in PREDICTION_OUTCOME_ALIASES:
        return PREDICTION_OUTCOME_ALIASES[compact]

    return compact or "home_run"


def stable_fingerprint(value: Any) -> str:
    def serializer(item: Any) -> Any:
        if isinstance(item, (datetime, date)):
            return item.isoformat()
        if isinstance(item, Decimal):
            return float(item)
        if isinstance(item, Enum):
            return item.value
        if is_dataclass(item):
            return asdict(item)
        raise TypeError(f"Unsupported type: {type(item).__name__}")

    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=serializer,
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=UTC)
        except Exception:
            return None

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None

        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except Exception:
            pass

        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(text, fmt).replace(tzinfo=UTC)
            except Exception:
                continue

    return None


def model_has_column(model_class: Any, column_name: str) -> bool:
    try:
        return column_name in model_class.__mapper__.columns.keys()
    except Exception:
        return False


def model_has_relationship(model_class: Any, relationship_name: str) -> bool:
    try:
        return relationship_name in model_class.__mapper__.relationships.keys()
    except Exception:
        return False


def read_attr(value: Any, names: Sequence[str] | str, default: Any = None) -> Any:
    candidates = (names,) if isinstance(names, str) else tuple(names)

    if isinstance(value, Mapping):
        for name in candidates:
            if name in value and value.get(name) not in (None, ""):
                return value.get(name)
        normalized = {normalize_key(k): v for k, v in value.items()}
        for name in candidates:
            key = normalize_key(name)
            if key in normalized and normalized.get(key) not in (None, ""):
                return normalized.get(key)

    for name in candidates:
        try:
            item = getattr(value, name)
            if item not in (None, ""):
                return item
        except Exception:
            continue

    return default


# ============================================================
# SECTION 09 - DATA CONTRACTS
# ============================================================

@dataclass(slots=True)
class SelectedPredictionRequest:
    player_id: int | None = None
    player_name: str | None = None
    team_id: int | None = None
    team_name: str | None = None
    outcome_key: str = "home_run"
    season: int | None = None
    game_id: int | None = None
    game_date: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Any) -> "SelectedPredictionRequest":
        data = object_to_dict(payload)

        player_id_raw = first_present(data, PLAYER_ID_FIELDS)
        team_id_raw = first_present(data, TEAM_ID_FIELDS)

        outcome_key = parse_outcome(
            first_present(data, OUTCOME_FIELDS, "home_run")
        )

        season_raw = first_present(data, ("season", "selected_season"))

        return cls(
            player_id=to_int(player_id_raw, 0) or None,
            player_name=normalize_text(first_present(data, PLAYER_NAME_FIELDS, "")) or None,
            team_id=to_int(team_id_raw, 0) or None,
            team_name=normalize_text(first_present(data, TEAM_NAME_FIELDS, "")) or None,
            outcome_key=outcome_key,
            season=to_int(season_raw, 0) or None,
            game_id=to_int(first_present(data, ("game_id", "game_pk"), 0), 0) or None,
            game_date=normalize_text(first_present(data, ("game_date", "date", "official_date"), "")) or None,
            raw_payload=data,
        )


@dataclass(slots=True)
class ResolvedPlayer:
    resolved: bool
    source: str
    internal_player_id: int | None = None
    mlb_player_id: int | None = None
    full_name: str | None = None
    current_team_id: int | None = None
    current_team_name: str | None = None
    position: str | None = None
    position_code: str | None = None
    position_abbreviation: str | None = None
    bats: str | None = None
    throws: str | None = None
    active_status: str | None = None
    match_score: float | None = None
    warnings: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ResolvedTeam:
    resolved: bool
    source: str
    internal_team_id: int | None = None
    mlb_team_id: int | None = None
    name: str | None = None
    abbreviation: str | None = None
    warnings: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PlayerSeasonStatLine:
    found: bool
    source_status: FeatureSourceStatus
    source_name: str
    season: int | None = None
    stat_group: str = "hitting"
    team_id: int | None = None
    team_name: str | None = None
    games_played: int = 0
    plate_appearances: int = 0
    at_bats: int = 0
    runs: int = 0
    hits: int = 0
    singles: int = 0
    doubles: int = 0
    triples: int = 0
    home_runs: int = 0
    rbi: int = 0
    walks: int = 0
    intentional_walks: int = 0
    hit_by_pitch: int = 0
    sacrifice_flies: int = 0
    strikeouts: int = 0
    stolen_bases: int = 0
    caught_stealing: int = 0
    batting_average: float = 0.0
    on_base_percentage: float = 0.0
    slugging_percentage: float = 0.0
    ops: float = 0.0
    isolated_power: float = 0.0
    babip: float = 0.0
    walk_rate: float = 0.0
    strikeout_rate: float = 0.0
    home_run_rate: float = 0.0
    woba: float = 0.0
    wrc_plus: float = 0.0
    total_bases: int = 0
    extra_base_hits: int = 0
    times_on_base: int = 0
    sample_size: int = 0
    source_updated_at: str | None = None
    warnings: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_status"] = self.source_status.value
        return payload


@dataclass(slots=True)
class PlayerTechnicalProfile:
    sample_quality: SampleQuality
    hitter_role: str
    power_profile: str
    contact_profile: str
    discipline_profile: str
    strikeout_profile: str
    run_production_profile: str
    speed_profile: str
    ops_tier: str
    primary_strength: str
    primary_risk: str
    model_guidance: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["sample_quality"] = self.sample_quality.value
        return payload


@dataclass(slots=True)
class PlayerFeaturePacket:
    status: str
    valid: bool
    phase: str
    module_version: str
    requested: SelectedPredictionRequest
    resolved_player: ResolvedPlayer
    resolved_team: ResolvedTeam
    stat_line: PlayerSeasonStatLine
    rates: dict[str, float]
    probability_inputs: dict[str, Any]
    technical_profile: PlayerTechnicalProfile
    missing_features: list[str]
    debug: dict[str, Any]
    created_at: str
    feature_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "valid": self.valid,
            "phase": self.phase,
            "module_version": self.module_version,
            "requested": asdict(self.requested),
            "resolved_player": asdict(self.resolved_player),
            "resolved_team": asdict(self.resolved_team),
            "stat_line": self.stat_line.to_dict(),
            "rates": self.rates,
            "probability_inputs": self.probability_inputs,
            "technical_profile": self.technical_profile.to_dict(),
            "missing_features": self.missing_features,
            "debug": self.debug,
            "created_at": self.created_at,
            "feature_fingerprint": self.feature_fingerprint,

            # Workbench-friendly aliases.
            "player_id": self.resolved_player.internal_player_id,
            "mlb_player_id": self.resolved_player.mlb_player_id,
            "player_name": self.resolved_player.full_name or self.requested.player_name,
            "team_id": self.resolved_team.internal_team_id or self.resolved_player.current_team_id,
            "team_name": self.resolved_team.name or self.resolved_player.current_team_name or self.requested.team_name,
            "outcome_key": self.requested.outcome_key,
            "sample_size": self.stat_line.sample_size,
            "source_status": self.stat_line.source_status.value,
            "source_name": self.stat_line.source_name,
            "has_hitting_sample": self.stat_line.sample_size > 0,
            "primary_metric": self.probability_inputs.get("primary_metric"),
            "observed_rate": self.probability_inputs.get("observed_rate"),
            "league_baseline_rate": self.probability_inputs.get("league_baseline_rate"),
        }


# ============================================================
# SECTION 10 - DATABASE SESSION HELPERS
# ============================================================

@contextmanager
def managed_feature_session(existing_session: Any = None):
    if existing_session is not None:
        yield existing_session
        return

    if _database_module is None:
        yield None
        return

    if hasattr(_database_module, "managed_database_session"):
        try:
            with _database_module.managed_database_session() as session:
                yield session
            return
        except TypeError:
            pass
        except Exception as exc:
            LOGGER.warning("managed_database_session failed: %s", exc)

    session = None

    try:
        if hasattr(_database_module, "create_database_session"):
            session = _database_module.create_database_session()
        elif hasattr(_database_module, "SessionLocal"):
            session = _database_module.SessionLocal()

        yield session
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                pass


def get_model_class(name: str) -> Any:
    if _models_module is None:
        return None
    return getattr(_models_module, name, None)


# ============================================================
# SECTION 11 - REQUEST-SUPPLIED STAT LINE SUPPORT
# ============================================================

def stat_line_from_payload(
    request: SelectedPredictionRequest,
) -> PlayerSeasonStatLine | None:
    payload = request.raw_payload

    if not payload:
        return None

    direct_keys = {
        "plate_appearances",
        "at_bats",
        "hits",
        "home_runs",
        "walks",
        "strikeouts",
        "rbi",
        "runs",
    }

    if not any(key in payload for key in direct_keys):
        nested = payload.get("stat_line") or payload.get("stats") or payload.get("player_stats")
        if isinstance(nested, Mapping):
            payload = dict(nested)
        else:
            return None

    line = normalize_stat_mapping(
        payload,
        source_status=FeatureSourceStatus.REQUEST_SUPPLIED_STAT_LINE,
        source_name="request_supplied_stat_line",
    )

    if line.sample_size <= 0:
        return None

    return line


# ============================================================
# SECTION 12 - STAT NORMALIZATION
# ============================================================

def normalize_stat_mapping(
    value: Mapping[str, Any],
    *,
    source_status: FeatureSourceStatus,
    source_name: str,
) -> PlayerSeasonStatLine:
    row = dict(value)

    def pick(*names: str, default: Any = 0) -> Any:
        return first_present(row, names, default)

    hits = to_int(pick("hits", "h"))
    doubles = to_int(pick("doubles", "double", "2b", "two_b"))
    triples = to_int(pick("triples", "triple", "3b", "three_b"))
    home_runs = to_int(pick("home_runs", "homeRuns", "hr"))
    singles = to_int(pick("singles", "single"), -1)

    if singles < 0:
        singles = max(0, hits - doubles - triples - home_runs)

    total_bases = to_int(pick("total_bases", "totalBases", "tb"), -1)
    if total_bases < 0:
        total_bases = singles + (2 * doubles) + (3 * triples) + (4 * home_runs)

    walks = to_int(pick("walks", "baseOnBalls", "bb"))
    hit_by_pitch = to_int(pick("hit_by_pitch", "hitByPitch", "hbp"))
    plate_appearances = to_int(pick("plate_appearances", "plateAppearances", "pa"))
    at_bats = to_int(pick("at_bats", "atBats", "ab"))

    if plate_appearances <= 0 and at_bats > 0:
        plate_appearances = at_bats + walks + hit_by_pitch + to_int(
            pick("sacrifice_flies", "sacFlies", "sf")
        )

    batting_average = to_float(pick("batting_average", "avg", default=0.0))
    on_base_percentage = to_float(pick("on_base_percentage", "obp", default=0.0))
    slugging_percentage = to_float(pick("slugging_percentage", "slg", default=0.0))
    ops = to_float(pick("ops", default=0.0))

    if batting_average <= 0 and at_bats > 0:
        batting_average = safe_divide(hits, at_bats)

    sacrifice_flies = to_int(pick("sacrifice_flies", "sacFlies", "sf"))

    if on_base_percentage <= 0:
        on_base_percentage = safe_divide(
            hits + walks + hit_by_pitch,
            at_bats + walks + hit_by_pitch + sacrifice_flies,
        )

    if slugging_percentage <= 0:
        slugging_percentage = safe_divide(total_bases, at_bats)

    if ops <= 0:
        ops = on_base_percentage + slugging_percentage

    strikeouts = to_int(pick("strikeouts", "strikeOuts", "so", "k"))
    runs = to_int(pick("runs", "r"))
    rbi = to_int(pick("rbi", "runsBattedIn"))
    intentional_walks = to_int(pick("intentional_walks", "intentionalWalks", "ibb"))

    line = PlayerSeasonStatLine(
        found=True,
        source_status=source_status,
        source_name=source_name,
        season=to_int(pick("season"), 0) or None,
        stat_group=str(pick("stat_group", "group", default="hitting") or "hitting"),
        team_id=to_int(pick("team_id", "teamId"), 0) or None,
        team_name=normalize_text(pick("team_name", "teamName", default="")) or None,
        games_played=to_int(pick("games_played", "gamesPlayed", "games")),
        plate_appearances=plate_appearances,
        at_bats=at_bats,
        runs=runs,
        hits=hits,
        singles=singles,
        doubles=doubles,
        triples=triples,
        home_runs=home_runs,
        rbi=rbi,
        walks=walks,
        intentional_walks=intentional_walks,
        hit_by_pitch=hit_by_pitch,
        sacrifice_flies=sacrifice_flies,
        strikeouts=strikeouts,
        stolen_bases=to_int(pick("stolen_bases", "stolenBases", "sb")),
        caught_stealing=to_int(pick("caught_stealing", "caughtStealing", "cs")),
        batting_average=batting_average,
        on_base_percentage=on_base_percentage,
        slugging_percentage=slugging_percentage,
        ops=ops,
        isolated_power=to_float(pick("isolated_power", "iso", default=slugging_percentage - batting_average)),
        babip=to_float(pick("babip", default=0.0)),
        walk_rate=to_float(pick("walk_rate", default=safe_divide(walks, plate_appearances))),
        strikeout_rate=to_float(pick("strikeout_rate", default=safe_divide(strikeouts, plate_appearances))),
        home_run_rate=to_float(pick("home_run_rate", default=safe_divide(home_runs, plate_appearances))),
        woba=to_float(pick("woba", "wOBA", default=0.0)),
        wrc_plus=to_float(pick("wrc_plus", "wRC+", "wrcPlus", default=0.0)),
        total_bases=total_bases,
        extra_base_hits=max(0, doubles + triples + home_runs),
        times_on_base=max(0, hits + walks + hit_by_pitch),
        sample_size=max(plate_appearances, at_bats),
        source_updated_at=str(pick("source_updated_at", "updated_at", default="")) or None,
        raw=row,
    )

    if line.sample_size <= 0:
        line.found = False
        line.source_status = FeatureSourceStatus.NO_HITTING_SAMPLE
        line.warnings.append("Stat line exists but has no usable PA or AB sample.")

    return line


def stat_line_from_orm_row(
    row: Any,
    *,
    source_name: str = "database_player_season_stats",
) -> PlayerSeasonStatLine:
    return normalize_stat_mapping(
        object_to_dict(row),
        source_status=FeatureSourceStatus.DATABASE_PLAYER_SEASON_STATS,
        source_name=source_name,
    )


def no_sample_stat_line(
    *,
    source_name: str,
    warning: str,
) -> PlayerSeasonStatLine:
    return PlayerSeasonStatLine(
        found=False,
        source_status=FeatureSourceStatus.NO_HITTING_SAMPLE,
        source_name=source_name,
        warnings=[warning],
    )


# ============================================================
# SECTION 13 - TEAM RESOLUTION
# ============================================================

def resolve_team(
    request: SelectedPredictionRequest,
    *,
    session: Any = None,
) -> ResolvedTeam:
    Team = get_model_class("Team")

    if session is None or Team is None:
        return ResolvedTeam(
            resolved=False,
            source="unavailable",
            name=request.team_name,
            internal_team_id=request.team_id,
            warnings=["Team model or database session unavailable."],
        )

    try:
        query = session.query(Team)

        candidates: list[Any] = []

        if request.team_id:
            for column_name in ("id", "mlb_team_id"):
                if model_has_column(Team, column_name):
                    item = query.filter(getattr(Team, column_name) == request.team_id).first()
                    if item is not None:
                        candidates.append(item)

        if request.team_name:
            name = request.team_name
            for column_name in ("name", "team_name", "abbreviation"):
                if model_has_column(Team, column_name):
                    item = query.filter(getattr(Team, column_name) == name).first()
                    if item is not None:
                        candidates.append(item)

            if not candidates and model_has_column(Team, "name"):
                normalized_target = normalize_name_for_match(name)
                all_teams = query.limit(100).all()
                scored: list[tuple[float, Any]] = []
                for team in all_teams:
                    candidate_name = normalize_name_for_match(read_attr(team, ("name", "abbreviation"), ""))
                    score = difflib.SequenceMatcher(None, normalized_target, candidate_name).ratio()
                    scored.append((score, team))
                scored.sort(key=lambda pair: pair[0], reverse=True)
                if scored and scored[0][0] >= 0.72:
                    candidates.append(scored[0][1])

        if not candidates:
            return ResolvedTeam(
                resolved=False,
                source="not_found",
                name=request.team_name,
                internal_team_id=request.team_id,
                warnings=["No matching team row found."],
            )

        team = candidates[0]
        raw = object_to_dict(team)

        return ResolvedTeam(
            resolved=True,
            source="database",
            internal_team_id=to_int(read_attr(team, "id"), 0) or None,
            mlb_team_id=to_int(read_attr(team, "mlb_team_id"), 0) or None,
            name=normalize_text(read_attr(team, ("name", "team_name"), request.team_name)),
            abbreviation=normalize_text(read_attr(team, ("abbreviation", "abbr"), "")) or None,
            raw=raw,
        )

    except Exception as exc:
        return ResolvedTeam(
            resolved=False,
            source="error",
            name=request.team_name,
            internal_team_id=request.team_id,
            warnings=[f"{type(exc).__name__}: {exc}"],
        )


# ============================================================
# SECTION 14 - PLAYER RESOLUTION
# ============================================================

def resolve_player(
    request: SelectedPredictionRequest,
    *,
    session: Any = None,
    resolved_team: ResolvedTeam | None = None,
) -> ResolvedPlayer:
    Player = get_model_class("Player")

    if session is None or Player is None:
        return ResolvedPlayer(
            resolved=False,
            source="unavailable",
            internal_player_id=request.player_id,
            full_name=request.player_name,
            warnings=["Player model or database session unavailable."],
        )

    warnings: list[str] = []
    candidates: list[tuple[float, str, Any]] = []

    try:
        query = session.query(Player)

        if request.player_id:
            if model_has_column(Player, "mlb_player_id") and request.player_id >= 100000:
                player = query.filter(Player.mlb_player_id == request.player_id).first()
                if player is not None:
                    candidates.append((1.0, "database_mlb_player_id", player))

            if model_has_column(Player, "id"):
                player = query.filter(Player.id == request.player_id).first()
                if player is not None:
                    candidates.append((0.98, "database_internal_player_id", player))

            if model_has_column(Player, "mlb_player_id"):
                player = query.filter(Player.mlb_player_id == request.player_id).first()
                if player is not None:
                    candidates.append((0.97, "database_mlb_player_id_secondary", player))

        if request.player_name:
            exact_name = request.player_name

            for column_name in ("full_name", "name", "use_name"):
                if model_has_column(Player, column_name):
                    player = query.filter(getattr(Player, column_name) == exact_name).first()
                    if player is not None:
                        candidates.append((0.94, f"database_exact_{column_name}", player))

            normalized_target = normalize_name_for_match(request.player_name)

            if not candidates and model_has_column(Player, "full_name"):
                possible_rows = query.limit(5000).all()
                scored: list[tuple[float, str, Any]] = []

                for player in possible_rows:
                    candidate_names = [
                        read_attr(player, "full_name", ""),
                        read_attr(player, "use_name", ""),
                        read_attr(player, "last_name", ""),
                    ]
                    best = 0.0
                    for candidate_name in candidate_names:
                        candidate_norm = normalize_name_for_match(candidate_name)
                        if not candidate_norm:
                            continue
                        score = difflib.SequenceMatcher(None, normalized_target, candidate_norm).ratio()
                        if normalized_target and normalized_target in candidate_norm:
                            score = max(score, 0.90)
                        best = max(best, score)
                    if best >= 0.72:
                        scored.append((best, "database_fuzzy_name", player))

                scored.sort(key=lambda item: item[0], reverse=True)
                candidates.extend(scored[:5])

        if not candidates:
            return ResolvedPlayer(
                resolved=False,
                source="not_found",
                internal_player_id=request.player_id,
                full_name=request.player_name,
                warnings=["No matching player row found from request payload."],
            )

        candidates.sort(key=lambda item: item[0], reverse=True)

        if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < 0.03:
            warnings.append(
                "Player resolution was close between multiple candidates; using highest score."
            )

        score, source, player = candidates[0]
        raw = object_to_dict(player)

        current_team_id = to_int(
            read_attr(player, ("current_team_id", "team_id"), 0),
            0,
        ) or None

        current_team_name = None
        try:
            if hasattr(player, "team") and player.team is not None:
                current_team_name = normalize_text(
                    read_attr(player.team, ("name", "team_name"), "")
                ) or None
        except Exception:
            current_team_name = None

        if current_team_name is None and resolved_team and resolved_team.resolved:
            if current_team_id is None or current_team_id == resolved_team.internal_team_id:
                current_team_name = resolved_team.name

        return ResolvedPlayer(
            resolved=True,
            source=source,
            internal_player_id=to_int(read_attr(player, "id"), 0) or None,
            mlb_player_id=to_int(read_attr(player, "mlb_player_id"), 0) or None,
            full_name=normalize_text(read_attr(player, "full_name", request.player_name)),
            current_team_id=current_team_id,
            current_team_name=current_team_name,
            position=normalize_text(read_attr(player, "position", "")) or None,
            position_code=normalize_text(read_attr(player, "position_code", "")) or None,
            position_abbreviation=normalize_text(read_attr(player, "position_abbreviation", "")) or None,
            bats=normalize_text(read_attr(player, "bats", "")) or None,
            throws=normalize_text(read_attr(player, "throws", "")) or None,
            active_status=normalize_text(read_attr(player, "active_status", "")) or None,
            match_score=round(score, 4),
            warnings=warnings,
            raw=raw,
        )

    except Exception as exc:
        return ResolvedPlayer(
            resolved=False,
            source="error",
            internal_player_id=request.player_id,
            full_name=request.player_name,
            warnings=[f"{type(exc).__name__}: {exc}"],
        )


# ============================================================
# SECTION 15 - DATABASE STAT RESOLUTION
# ============================================================

def find_database_season_stat_line(
    resolved_player: ResolvedPlayer,
    request: SelectedPredictionRequest,
    *,
    session: Any = None,
) -> PlayerSeasonStatLine:
    PlayerSeasonStat = get_model_class("PlayerSeasonStat")

    if session is None or PlayerSeasonStat is None:
        return no_sample_stat_line(
            source_name="database_unavailable",
            warning="PlayerSeasonStat model or database session unavailable.",
        )

    if not resolved_player.resolved or not resolved_player.internal_player_id:
        return no_sample_stat_line(
            source_name="player_not_resolved",
            warning="Player was not resolved to an internal database id.",
        )

    try:
        query = session.query(PlayerSeasonStat)

        if not model_has_column(PlayerSeasonStat, "player_id"):
            return no_sample_stat_line(
                source_name="player_season_stats_missing_player_id",
                warning="PlayerSeasonStat is missing player_id column.",
            )

        query = query.filter(PlayerSeasonStat.player_id == resolved_player.internal_player_id)

        rows = query.all()

        if not rows:
            return no_sample_stat_line(
                source_name="database_no_player_season_stat_rows",
                warning="No PlayerSeasonStat rows found for resolved player.",
            )

        filtered_rows = []

        for row in rows:
            stat_group = str(read_attr(row, "stat_group", "hitting") or "hitting").lower()
            if "hit" not in stat_group and stat_group not in {"batting", "hitting", ""}:
                continue

            if request.season:
                season = to_int(read_attr(row, "season"), 0)
                if season != request.season:
                    continue

            filtered_rows.append(row)

        if not filtered_rows:
            filtered_rows = rows

        def row_score(row: Any) -> tuple[int, int, int]:
            season = to_int(read_attr(row, "season"), 0)
            pa = to_int(read_attr(row, "plate_appearances"), 0)
            ab = to_int(read_attr(row, "at_bats"), 0)
            return (season, max(pa, ab), to_int(read_attr(row, "games_played"), 0))

        filtered_rows.sort(key=row_score, reverse=True)

        best_row = filtered_rows[0]
        line = stat_line_from_orm_row(best_row)

        if line.sample_size <= 0:
            line.found = False
            line.source_status = FeatureSourceStatus.NO_HITTING_SAMPLE
            line.source_name = "database_stat_row_without_hitting_sample"
            line.warnings.append(
                "A PlayerSeasonStat row exists, but PA/AB/H/HR values do not form a usable hitting sample."
            )

        return line

    except Exception as exc:
        return PlayerSeasonStatLine(
            found=False,
            source_status=FeatureSourceStatus.ERROR,
            source_name="database_stat_resolution_error",
            warnings=[f"{type(exc).__name__}: {exc}"],
        )


# ============================================================
# SECTION 16 - LIVE MLB API FALLBACK
# ============================================================

def http_json(url: str, timeout: float = 12.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AISP2-Baseball/16.3A",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read().decode("utf-8", errors="replace")
        return json.loads(payload)


def current_candidate_seasons() -> list[int]:
    year = utc_now().year
    return [year, year - 1, year - 2]


def search_mlb_player_id_by_name(player_name: str) -> int | None:
    name = normalize_text(player_name)
    if not name:
        return None

    url = (
        "https://statsapi.mlb.com/api/v1/people/search?"
        + urllib.parse.urlencode({"names": name})
    )

    try:
        data = http_json(url)
        people = data.get("people") or []
        if people:
            return to_int(people[0].get("id"), 0) or None
    except Exception:
        return None

    return None


def fetch_live_mlb_hitting_stat_line(
    resolved_player: ResolvedPlayer,
    request: SelectedPredictionRequest,
) -> PlayerSeasonStatLine:
    mlb_player_id = resolved_player.mlb_player_id

    if not mlb_player_id and request.player_id and request.player_id >= 100000:
        mlb_player_id = request.player_id

    if not mlb_player_id and request.player_name:
        mlb_player_id = search_mlb_player_id_by_name(request.player_name)

    if not mlb_player_id:
        return no_sample_stat_line(
            source_name="mlb_stats_api_no_player_id",
            warning="No MLB player id available for live MLB Stats API fallback.",
        )

    seasons = [request.season] if request.season else current_candidate_seasons()
    seasons = [season for season in seasons if season]

    warnings: list[str] = []

    for season in seasons:
        url = (
            f"https://statsapi.mlb.com/api/v1/people/{mlb_player_id}/stats?"
            + urllib.parse.urlencode(
                {
                    "stats": "season",
                    "group": "hitting",
                    "season": str(season),
                }
            )
        )

        try:
            data = http_json(url)
        except Exception as exc:
            warnings.append(f"{season}: {type(exc).__name__}: {exc}")
            continue

        stats_blocks = data.get("stats") or []

        for block in stats_blocks:
            splits = block.get("splits") or []
            for split in splits:
                stat = dict(split.get("stat") or {})
                if not stat:
                    continue

                stat["season"] = season
                stat["team_name"] = (split.get("team") or {}).get("name")
                stat["team_id"] = (split.get("team") or {}).get("id")

                line = normalize_stat_mapping(
                    stat,
                    source_status=FeatureSourceStatus.LIVE_MLB_STATS_API,
                    source_name=f"live_mlb_stats_api_hitting_{season}",
                )

                line.raw = {
                    "mlb_player_id": mlb_player_id,
                    "season": season,
                    "split": split,
                    "url": url,
                }

                if warnings:
                    line.warnings.extend(warnings)

                if line.sample_size > 0:
                    return line

    return no_sample_stat_line(
        source_name="mlb_stats_api_no_hitting_sample",
        warning=(
            "MLB Stats API fallback was checked, but no usable season hitting sample was found."
        ),
    )


# ============================================================
# SECTION 17 - RATE ENGINE
# ============================================================

def calculate_rates(stat_line: PlayerSeasonStatLine) -> dict[str, float]:
    pa = stat_line.plate_appearances
    ab = stat_line.at_bats

    rates = {
        "hr_per_pa": safe_divide(stat_line.home_runs, pa),
        "hit_per_ab": safe_divide(stat_line.hits, ab),
        "single_per_ab": safe_divide(stat_line.singles, ab),
        "double_per_ab": safe_divide(stat_line.doubles, ab),
        "triple_per_ab": safe_divide(stat_line.triples, ab),
        "bb_per_pa": safe_divide(stat_line.walks, pa),
        "k_per_pa": safe_divide(stat_line.strikeouts, pa),
        "rbi_per_pa": safe_divide(stat_line.rbi, pa),
        "run_per_pa": safe_divide(stat_line.runs, pa),
        "tb_per_ab": safe_divide(stat_line.total_bases, ab),
        "xbh_per_pa": safe_divide(stat_line.extra_base_hits, pa),
        "times_on_base_per_pa": safe_divide(stat_line.times_on_base, pa),
        "avg": stat_line.batting_average,
        "obp": stat_line.on_base_percentage,
        "slg": stat_line.slugging_percentage,
        "ops": stat_line.ops,
        "iso": stat_line.isolated_power,
        "babip": stat_line.babip,
        "woba": stat_line.woba,
        "wrc_plus": stat_line.wrc_plus,
    }

    return {
        key: round(value, 6)
        for key, value in rates.items()
    }


def observed_rate_for_outcome(
    outcome_key: str,
    stat_line: PlayerSeasonStatLine,
    rates: Mapping[str, float],
) -> tuple[str, float]:
    outcome = parse_outcome(outcome_key)

    if outcome == "home_run":
        return "HR / PA", to_float(rates.get("hr_per_pa"))

    if outcome == "hit":
        return "H / AB", to_float(rates.get("hit_per_ab"))

    if outcome == "single":
        return "1B / AB", to_float(rates.get("single_per_ab"))

    if outcome == "double":
        return "2B / AB", to_float(rates.get("double_per_ab"))

    if outcome == "triple":
        return "3B / AB", to_float(rates.get("triple_per_ab"))

    if outcome == "walk":
        return "BB / PA", to_float(rates.get("bb_per_pa"))

    if outcome == "strikeout":
        return "K / PA", to_float(rates.get("k_per_pa"))

    if outcome == "rbi":
        return "RBI / PA", to_float(rates.get("rbi_per_pa"))

    if outcome == "run_scored":
        return "R / PA", to_float(rates.get("run_per_pa"))

    if outcome == "total_bases":
        return "TB / AB", to_float(rates.get("tb_per_ab"))

    return "HR / PA", to_float(rates.get("hr_per_pa"))


# ============================================================
# SECTION 18 - TECHNICAL PROFILE ENGINE
# ============================================================

def sample_quality_from_size(sample_size: int) -> SampleQuality:
    if sample_size >= 350:
        return SampleQuality.STRONG
    if sample_size >= 150:
        return SampleQuality.MODERATE
    if sample_size >= 25:
        return SampleQuality.WEAK
    return SampleQuality.NO_SAMPLE


def tier_by_thresholds(
    value: float,
    thresholds: Sequence[tuple[float, str]],
    default: str,
) -> str:
    for threshold, label in thresholds:
        if value >= threshold:
            return label
    return default


def build_technical_profile(
    stat_line: PlayerSeasonStatLine,
    rates: Mapping[str, float],
    outcome_key: str,
) -> PlayerTechnicalProfile:
    sample_quality = sample_quality_from_size(stat_line.sample_size)

    warnings: list[str] = []

    if sample_quality == SampleQuality.NO_SAMPLE:
        return PlayerTechnicalProfile(
            sample_quality=sample_quality,
            hitter_role="No hitting sample",
            power_profile="No batting sample",
            contact_profile="No batting sample",
            discipline_profile="No batting sample",
            strikeout_profile="No batting sample",
            run_production_profile="No batting sample",
            speed_profile="No batting sample",
            ops_tier="No batting sample",
            primary_strength="Unavailable",
            primary_risk="No usable hitting sample",
            model_guidance=(
                "Do not treat this player as a league-average hitter. "
                "The selected player has no usable PA/AB sample for this prop."
            ),
            warnings=["No usable hitting sample was found."],
        )

    hr_rate = to_float(rates.get("hr_per_pa"))
    hit_rate = to_float(rates.get("hit_per_ab"))
    walk_rate = to_float(rates.get("bb_per_pa"))
    strikeout_rate = to_float(rates.get("k_per_pa"))
    rbi_rate = to_float(rates.get("rbi_per_pa"))
    run_rate = to_float(rates.get("run_per_pa"))
    tb_rate = to_float(rates.get("tb_per_ab"))
    ops = to_float(rates.get("ops"))
    iso = to_float(rates.get("iso"))

    power_profile = tier_by_thresholds(
        max(hr_rate, iso / 5.0),
        (
            (0.065, "Elite power profile"),
            (0.045, "Strong power profile"),
            (0.030, "Average power profile"),
            (0.018, "Limited power profile"),
        ),
        "Low power profile",
    )

    contact_profile = tier_by_thresholds(
        hit_rate,
        (
            (0.300, "Elite contact profile"),
            (0.270, "Strong contact profile"),
            (0.245, "Average contact profile"),
            (0.220, "Below-average contact profile"),
        ),
        "Low contact profile",
    )

    discipline_profile = tier_by_thresholds(
        walk_rate,
        (
            (0.140, "Elite plate discipline"),
            (0.105, "Strong plate discipline"),
            (0.080, "Average plate discipline"),
            (0.055, "Aggressive/low-walk profile"),
        ),
        "Very low walk profile",
    )

    if strikeout_rate >= 0.320:
        strikeout_profile = "High strikeout risk"
    elif strikeout_rate >= 0.250:
        strikeout_profile = "Elevated strikeout risk"
    elif strikeout_rate >= 0.180:
        strikeout_profile = "Average strikeout profile"
    else:
        strikeout_profile = "Low strikeout profile"

    production_value = max(rbi_rate, run_rate)
    run_production_profile = tier_by_thresholds(
        production_value,
        (
            (0.185, "Elite run-production profile"),
            (0.150, "Strong run-production profile"),
            (0.115, "Average run-production profile"),
            (0.080, "Limited run-production profile"),
        ),
        "Low run-production profile",
    )

    speed_profile = tier_by_thresholds(
        safe_divide(stat_line.stolen_bases, max(stat_line.times_on_base, 1)),
        (
            (0.090, "Aggressive stolen-base profile"),
            (0.045, "Moderate stolen-base profile"),
            (0.015, "Limited stolen-base profile"),
        ),
        "Minimal stolen-base profile",
    )

    ops_tier = tier_by_thresholds(
        ops,
        (
            (0.950, "Elite OPS tier"),
            (0.850, "Strong OPS tier"),
            (0.740, "Average OPS tier"),
            (0.650, "Below-average OPS tier"),
        ),
        "Low OPS tier",
    )

    strengths = {
        "power": hr_rate / max(LEAGUE_BASELINE_RATES["home_run"], 0.0001),
        "contact": hit_rate / max(LEAGUE_BASELINE_RATES["hit"], 0.0001),
        "discipline": walk_rate / max(LEAGUE_BASELINE_RATES["walk"], 0.0001),
        "run_production": production_value / max(LEAGUE_BASELINE_RATES["rbi"], 0.0001),
        "total_bases": tb_rate / max(LEAGUE_BASELINE_RATES["total_bases"], 0.0001),
    }

    primary_strength = max(strengths.items(), key=lambda item: item[1])[0].replace("_", " ").title()

    risks = {
        "small sample": 1.0 if sample_quality == SampleQuality.WEAK else 0.0,
        "strikeout rate": strikeout_rate / 0.22,
        "low contact": 0.245 / max(hit_rate, 0.001),
        "low power": 0.032 / max(hr_rate, 0.001),
    }

    primary_risk = max(risks.items(), key=lambda item: item[1])[0].title()

    if sample_quality == SampleQuality.WEAK:
        warnings.append("Weak sample: probability engine must apply heavier baseline shrinkage.")

    model_guidance = (
        f"Use {sample_quality.value} sample weighting. "
        f"Primary observed strength: {primary_strength}. "
        f"Primary risk signal: {primary_risk}. "
        f"Do not use league fallback unless sample_size is zero."
    )

    return PlayerTechnicalProfile(
        sample_quality=sample_quality,
        hitter_role="Hitter sample available",
        power_profile=power_profile,
        contact_profile=contact_profile,
        discipline_profile=discipline_profile,
        strikeout_profile=strikeout_profile,
        run_production_profile=run_production_profile,
        speed_profile=speed_profile,
        ops_tier=ops_tier,
        primary_strength=primary_strength,
        primary_risk=primary_risk,
        model_guidance=model_guidance,
        warnings=warnings,
    )


# ============================================================
# SECTION 19 - PROBABILITY INPUT CONTRACT
# ============================================================

def build_probability_inputs(
    request: SelectedPredictionRequest,
    stat_line: PlayerSeasonStatLine,
    rates: Mapping[str, float],
    profile: PlayerTechnicalProfile,
) -> dict[str, Any]:
    outcome = parse_outcome(request.outcome_key)
    primary_metric, observed_rate = observed_rate_for_outcome(outcome, stat_line, rates)

    baseline = LEAGUE_BASELINE_RATES.get(outcome, LEAGUE_BASELINE_RATES["home_run"])
    no_sample_fallback = NO_SAMPLE_FALLBACK_PROBABILITY.get(
        outcome,
        NO_SAMPLE_FALLBACK_PROBABILITY["home_run"],
    )

    sample_size = stat_line.sample_size

    if sample_size >= 350:
        sample_weight = 0.82
    elif sample_size >= 150:
        sample_weight = 0.68
    elif sample_size >= 50:
        sample_weight = 0.45
    elif sample_size > 0:
        sample_weight = 0.25
    else:
        sample_weight = 0.0

    if sample_size > 0:
        feature_probability_seed = (
            observed_rate * sample_weight
            + baseline * (1.0 - sample_weight)
        )
    else:
        feature_probability_seed = no_sample_fallback

    coverage = 0.0
    required = ["plate_appearances", "at_bats", "hits", "home_runs", "walks", "strikeouts", "ops"]
    observed = 0
    for key in required:
        if to_float(read_attr(stat_line, key, 0), 0.0) > 0:
            observed += 1
    coverage = safe_divide(observed, len(required))

    return {
        "outcome_key": outcome,
        "outcome_family": OUTCOME_FAMILY.get(outcome, PredictionFamily.UNKNOWN).value,
        "primary_metric": primary_metric,
        "observed_rate": round(observed_rate, 6),
        "league_baseline_rate": round(baseline, 6),
        "no_sample_fallback_rate": round(no_sample_fallback, 6),
        "sample_weight": round(sample_weight, 4),
        "feature_probability_seed": round(feature_probability_seed, 6),
        "sample_size": sample_size,
        "sample_quality": profile.sample_quality.value,
        "coverage": round(coverage, 4),
        "has_hitting_sample": sample_size > 0,
        "requires_no_sample_fallback": sample_size <= 0,
        "source_status": stat_line.source_status.value,
        "source_name": stat_line.source_name,
    }


# ============================================================
# SECTION 20 - MISSING FEATURE REPORT
# ============================================================

def missing_features_for_packet(
    stat_line: PlayerSeasonStatLine,
    rates: Mapping[str, float],
) -> list[str]:
    missing: list[str] = []

    if stat_line.sample_size <= 0:
        missing.extend(["plate_appearances", "at_bats", "hitting_sample"])

    for key in ("hits", "home_runs", "walks", "strikeouts"):
        if to_float(read_attr(stat_line, key, 0), 0.0) <= 0:
            missing.append(key)

    for key in ("avg", "obp", "slg", "ops"):
        if to_float(rates.get(key), 0.0) <= 0:
            missing.append(key)

    return sorted(set(missing))


# ============================================================
# SECTION 21 - MAIN LIVE FEATURE BUILDER
# ============================================================

def build_player_prediction_features(
    payload: Any,
    *,
    db_session: Any = None,
    allow_live_mlb_fallback: bool = True,
) -> dict[str, Any]:
    request = SelectedPredictionRequest.from_payload(payload)

    debug: dict[str, Any] = {
        "module": MODULE_NAME,
        "module_path": MODULE_PATH,
        "module_version": MODULE_VERSION,
        "database_import_error": _DATABASE_IMPORT_ERROR,
        "models_import_error": _MODELS_IMPORT_ERROR,
        "raw_payload_keys": sorted(object_to_dict(payload).keys()),
    }

    with managed_feature_session(db_session) as session:
        resolved_team = resolve_team(request, session=session)
        resolved_player = resolve_player(
            request,
            session=session,
            resolved_team=resolved_team,
        )

        stat_line = stat_line_from_payload(request)

        if stat_line is None:
            stat_line = find_database_season_stat_line(
                resolved_player,
                request,
                session=session,
            )

        if (
            stat_line.sample_size <= 0
            and allow_live_mlb_fallback
            and resolved_player.resolved
        ):
            live_line = fetch_live_mlb_hitting_stat_line(
                resolved_player,
                request,
            )
            if live_line.sample_size > 0:
                stat_line = live_line
            else:
                stat_line.warnings.extend(live_line.warnings)
                stat_line.source_name = live_line.source_name
                stat_line.source_status = live_line.source_status

    if stat_line.sample_size <= 0:
        rates = {key: 0.0 for key in TECHNICAL_RATE_KEYS}
        rates.update(
            {
                "avg": 0.0,
                "obp": 0.0,
                "slg": 0.0,
                "ops": 0.0,
                "iso": 0.0,
                "babip": 0.0,
                "woba": 0.0,
                "wrc_plus": 0.0,
            }
        )
    else:
        rates = calculate_rates(stat_line)

    technical_profile = build_technical_profile(
        stat_line,
        rates,
        request.outcome_key,
    )

    probability_inputs = build_probability_inputs(
        request,
        stat_line,
        rates,
        technical_profile,
    )

    missing_features = missing_features_for_packet(
        stat_line,
        rates,
    )

    valid = bool(
        resolved_player.resolved
        and stat_line.sample_size > 0
        and probability_inputs.get("observed_rate") is not None
    )

    status = "ok" if valid else "no_hitting_sample"

    if not resolved_player.resolved:
        status = "player_not_resolved"

    packet_payload_for_hash = {
        "request": asdict(request),
        "resolved_player": asdict(resolved_player),
        "resolved_team": asdict(resolved_team),
        "stat_line": stat_line.to_dict(),
        "rates": rates,
        "probability_inputs": probability_inputs,
        "technical_profile": technical_profile.to_dict(),
        "missing_features": missing_features,
    }

    packet = PlayerFeaturePacket(
        status=status,
        valid=valid,
        phase=MODULE_PHASE,
        module_version=MODULE_VERSION,
        requested=request,
        resolved_player=resolved_player,
        resolved_team=resolved_team,
        stat_line=stat_line,
        rates=rates,
        probability_inputs=probability_inputs,
        technical_profile=technical_profile,
        missing_features=missing_features,
        debug=debug,
        created_at=utc_now().isoformat(),
        feature_fingerprint=stable_fingerprint(packet_payload_for_hash),
    )

    return packet.to_dict()


def build_workbench_player_features(
    payload: Any,
    *,
    db_session: Any = None,
) -> dict[str, Any]:
    return build_player_prediction_features(
        payload,
        db_session=db_session,
        allow_live_mlb_fallback=True,
    )


def build_live_player_feature_packet(
    *,
    player_id: int | None = None,
    player_name: str | None = None,
    team_id: int | None = None,
    team_name: str | None = None,
    outcome_key: str = "home_run",
    season: int | None = None,
    db_session: Any = None,
) -> dict[str, Any]:
    return build_player_prediction_features(
        {
            "player_id": player_id,
            "player_name": player_name,
            "team_id": team_id,
            "team_name": team_name,
            "outcome_key": outcome_key,
            "season": season,
        },
        db_session=db_session,
        allow_live_mlb_fallback=True,
    )


# ============================================================
# SECTION 22 - LEGACY COMPATIBILITY CLASSES
# ============================================================

@dataclass(slots=True)
class FeatureVector:
    values: dict[str, Any]
    as_of: datetime = field(default_factory=utc_now)
    entity_id: str | int | None = None
    game_id: str | int | None = None
    labels: dict[str, Any] = field(default_factory=dict)
    schema_hash: str = ""
    vector_hash: str = ""

    def finalize(self) -> "FeatureVector":
        self.values = dict(sorted(self.values.items()))
        self.schema_hash = stable_fingerprint(list(self.values.keys()))
        self.vector_hash = stable_fingerprint(
            {
                "values": self.values,
                "labels": self.labels,
                "as_of": self.as_of,
                "entity_id": self.entity_id,
                "game_id": self.game_id,
            }
        )
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "values": self.values,
            "as_of": self.as_of.isoformat(),
            "entity_id": self.entity_id,
            "game_id": self.game_id,
            "labels": self.labels,
            "schema_hash": self.schema_hash,
            "vector_hash": self.vector_hash,
        }


class FeatureBuilder:
    """
    Compatibility wrapper.

    Older code can still call FeatureBuilder().build(current=..., history=...).
    New Workbench code should call build_player_prediction_features().
    """

    def build(
        self,
        *,
        current: Any,
        history: Any = None,
        as_of: Any = None,
        context: Any = None,
        labels: Any = None,
        **_: Any,
    ) -> FeatureVector:
        current_record = object_to_dict(current)
        values: dict[str, Any] = {}

        normalized_current = normalize_stat_mapping(
            current_record,
            source_status=FeatureSourceStatus.REQUEST_SUPPLIED_STAT_LINE,
            source_name="legacy_current_record",
        )

        rates = calculate_rates(normalized_current)

        values.update(
            {
                "player_id": first_present(current_record, PLAYER_ID_FIELDS),
                "team_id": first_present(current_record, TEAM_ID_FIELDS),
                "season": first_present(current_record, ("season",), utc_now().year),
                "sample_size": normalized_current.sample_size,
                **rates,
            }
        )

        return FeatureVector(
            values=values,
            as_of=parse_datetime(as_of) or utc_now(),
            entity_id=values.get("player_id"),
            labels=object_to_dict(labels),
        ).finalize()


class PlayerFeatureBuilder(FeatureBuilder):
    """Compatibility alias for older imports."""


class MatchupFeatureBuilder(FeatureBuilder):
    """Compatibility alias for older imports."""


class TeamFeatureBuilder(FeatureBuilder):
    """Compatibility alias for older imports."""


def build_feature_vector(
    current: Any,
    history: Any = None,
    *,
    as_of: Any = None,
    context: Any = None,
    **kwargs: Any,
) -> FeatureVector:
    return FeatureBuilder().build(
        current=current,
        history=history,
        as_of=as_of,
        context=context,
        **kwargs,
    )


def build_feature_rows(
    rows: Any,
    *,
    history: Any = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    if rows is None:
        return []

    if isinstance(rows, Mapping):
        row_iterable = [rows]
    elif isinstance(rows, Iterable) and not isinstance(rows, (str, bytes)):
        row_iterable = list(rows)
    else:
        row_iterable = [rows]

    return [
        build_feature_vector(row, history=history, **kwargs).values
        for row in row_iterable
    ]


# ============================================================
# SECTION 23 - HEALTH AND VALIDATION
# ============================================================

def feature_builder_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "module": MODULE_NAME,
        "path": MODULE_PATH,
        "version": MODULE_VERSION,
        "phase": MODULE_PHASE,
        "module_status": MODULE_STATUS,
        "database_imported": _database_module is not None,
        "models_imported": _models_module is not None,
        "database_import_error": _DATABASE_IMPORT_ERROR,
        "models_import_error": _MODELS_IMPORT_ERROR,
        "capabilities": {
            "live_player_resolution": True,
            "team_resolution": True,
            "database_player_season_stats": True,
            "live_mlb_stats_api_fallback": True,
            "player_specific_rates": True,
            "technical_profile": True,
            "probability_input_contract": True,
            "workbench_debug_payload": True,
            "legacy_feature_vector_wrapper": True,
        },
        "supported_outcomes": sorted(PREDICTION_OUTCOME_ALIASES.values()),
        "checked_at": utc_now().isoformat(),
    }


def validate_feature_builder() -> dict[str, Any]:
    synthetic_payload = {
        "player_id": 592450,
        "player_name": "Aaron Judge",
        "team_name": "New York Yankees",
        "outcome_key": "home_run",
        "stat_line": {
            "season": 2026,
            "plate_appearances": 704,
            "at_bats": 559,
            "hits": 180,
            "doubles": 36,
            "triples": 1,
            "home_runs": 52,
            "walks": 120,
            "strikeouts": 171,
            "runs": 128,
            "rbi": 131,
            "avg": 0.322,
            "obp": 0.458,
            "slg": 0.701,
            "ops": 1.159,
        },
    }

    packet = build_player_prediction_features(
        synthetic_payload,
        db_session=None,
        allow_live_mlb_fallback=False,
    )

    checks = {
        "health_ok": feature_builder_health()["status"] == "ok",
        "packet_created": isinstance(packet, dict),
        "sample_size_positive": to_int(packet.get("sample_size"), 0) > 0,
        "hr_rate_positive": to_float(packet.get("rates", {}).get("hr_per_pa")) > 0,
        "primary_metric_present": bool(packet.get("primary_metric")),
        "probability_seed_present": packet.get("probability_inputs", {}).get("feature_probability_seed") is not None,
        "technical_profile_present": bool(packet.get("technical_profile")),
        "source_status_present": bool(packet.get("source_status")),
        "legacy_vector_available": isinstance(
            build_feature_vector(synthetic_payload["stat_line"]).to_dict(),
            dict,
        ),
    }

    passed = sum(1 for value in checks.values() if value)

    return {
        "status": "ok" if passed == len(checks) else "failed",
        "phase": MODULE_PHASE,
        "module": MODULE_NAME,
        "version": MODULE_VERSION,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "failed_checks": [
            name
            for name, value in checks.items()
            if not value
        ],
        "synthetic_packet_summary": {
            "player_name": packet.get("player_name"),
            "sample_size": packet.get("sample_size"),
            "source_status": packet.get("source_status"),
            "primary_metric": packet.get("primary_metric"),
            "observed_rate": packet.get("observed_rate"),
            "feature_probability_seed": packet.get("probability_inputs", {}).get("feature_probability_seed"),
            "power_profile": packet.get("technical_profile", {}).get("power_profile"),
        },
    }


def validate_feature_builder_enterprise() -> dict[str, Any]:
    return validate_feature_builder()


def feature_builder_enterprise_health() -> dict[str, Any]:
    validation = validate_feature_builder()
    health = feature_builder_health()
    return {
        **health,
        "validation": validation,
        "status": "ok" if validation.get("status") == "ok" else "validation_failed",
    }


# ============================================================
# SECTION 24 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "MODULE_NAME",
    "MODULE_PATH",
    "MODULE_VERSION",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "FeatureBuilderError",
    "PlayerResolutionError",
    "StatResolutionError",
    "FeatureSchemaError",
    "FeatureSourceStatus",
    "SampleQuality",
    "PredictionFamily",
    "SelectedPredictionRequest",
    "ResolvedPlayer",
    "ResolvedTeam",
    "PlayerSeasonStatLine",
    "PlayerTechnicalProfile",
    "PlayerFeaturePacket",
    "FeatureVector",
    "FeatureBuilder",
    "PlayerFeatureBuilder",
    "MatchupFeatureBuilder",
    "TeamFeatureBuilder",
    "build_player_prediction_features",
    "build_workbench_player_features",
    "build_live_player_feature_packet",
    "build_feature_vector",
    "build_feature_rows",
    "feature_builder_health",
    "validate_feature_builder",
    "validate_feature_builder_enterprise",
    "feature_builder_enterprise_health",
    "safe_divide",
    "to_float",
    "to_int",
    "parse_outcome",
    "calculate_rates",
    "build_probability_inputs",
]


# ============================================================
# SECTION 25 - LOCAL VALIDATION ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    report = validate_feature_builder()
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    if report.get("status") != "ok":
        raise SystemExit(1)