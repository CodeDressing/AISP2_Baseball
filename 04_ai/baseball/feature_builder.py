# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# PACKAGE: 04_prediction_engine
# FILE: feature_builder.py
# ============================================================
"""
Enterprise-grade feature engineering for baseball prediction models.

This module converts raw player, team, game, roster, Statcast, schedule,
venue, weather, and market-style context into deterministic model-ready
feature vectors.

Design goals
------------
1. Prevent temporal leakage by enforcing an explicit as-of timestamp.
2. Support training and inference through the same transformation path.
3. Accept dictionaries, dataclasses, ORM objects, named tuples, and pandas
   DataFrames without hard-coding a single persistence implementation.
4. Produce stable, ordered, serializable features with lineage metadata.
5. Support player, matchup, team-game, and plate-appearance prediction.
6. Remain importable when optional numerical dependencies are unavailable.
7. Provide validation, imputation, clipping, categorical encoding, rolling
   windows, exponentially weighted form, opponent splits, park context,
   rest/travel context, and uncertainty indicators.
8. Expose a compact public API while retaining enterprise diagnostics.

This file intentionally contains no model fitting. Its responsibility is
feature construction only. Model training, probability calibration, model
selection, registry management, and serving belong in separate modules.
"""

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from collections import Counter, defaultdict, deque
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from hashlib import sha256
import json
import logging
import math
import re
import statistics
from typing import Any, Final, Generic, Protocol, TypeVar

# ============================================================
# SECTION 02 - OPTIONAL DEPENDENCIES
# ============================================================

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    np = None  # type: ignore

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pd = None  # type: ignore


# ============================================================
# SECTION 03 - MODULE METADATA
# ============================================================

MODULE_NAME: Final[str] = "feature_builder"
MODULE_PATH: Final[str] = "04_prediction_engine/feature_builder.py"
MODULE_VERSION: Final[str] = "3.0.0"
MODULE_STATUS: Final[str] = "enterprise"
MODULE_AUTHOR: Final[str] = "Ryan M. Schuren"
MODULE_ASSISTANT: Final[str] = "Alfred"
UTC: Final[timezone] = timezone.utc

LOGGER = logging.getLogger(__name__)


# ============================================================
# SECTION 04 - TYPE ALIASES AND PROTOCOLS
# ============================================================

Number = int | float | Decimal
Record = Mapping[str, Any]
MutableRecord = MutableMapping[str, Any]
T = TypeVar("T")


class SupportsModelDump(Protocol):
    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Pydantic-compatible serialization protocol."""


class SupportsDict(Protocol):
    def dict(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Legacy Pydantic-compatible serialization protocol."""


# ============================================================
# SECTION 05 - EXCEPTIONS
# ============================================================

class FeatureBuilderError(RuntimeError):
    """Base exception for feature construction failures."""


class FeatureConfigurationError(FeatureBuilderError):
    """Raised when feature configuration is invalid."""


class FeatureValidationError(FeatureBuilderError):
    """Raised when input or output feature validation fails."""


class TemporalLeakageError(FeatureBuilderError):
    """Raised when a record violates the as-of cutoff."""


class FeatureSchemaError(FeatureBuilderError):
    """Raised when a required schema element cannot be resolved."""


# ============================================================
# SECTION 06 - ENUMERATIONS
# ============================================================

class FeatureMode(str, Enum):
    TRAINING = "training"
    INFERENCE = "inference"
    BACKTEST = "backtest"


class PredictionUnit(str, Enum):
    PLAYER_GAME = "player_game"
    BATTER_PITCHER = "batter_pitcher"
    TEAM_GAME = "team_game"
    PLATE_APPEARANCE = "plate_appearance"


class MissingValueStrategy(str, Enum):
    ZERO = "zero"
    MEAN = "mean"
    MEDIAN = "median"
    CONSTANT = "constant"
    PRESERVE = "preserve"


class UnknownCategoryStrategy(str, Enum):
    HASH = "hash"
    ZERO = "zero"
    ERROR = "error"


class LeakagePolicy(str, Enum):
    ERROR = "error"
    DROP = "drop"
    WARN = "warn"


class FeatureSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


# ============================================================
# SECTION 07 - CORE CONSTANTS
# ============================================================

DEFAULT_ROLLING_WINDOWS: Final[tuple[int, ...]] = (3, 5, 10, 15, 30)
DEFAULT_EWM_HALFLIVES: Final[tuple[float, ...]] = (3.0, 7.0, 14.0)
DEFAULT_MIN_HISTORY: Final[int] = 1
DEFAULT_PRIOR_WEIGHT: Final[float] = 25.0
DEFAULT_HASH_BUCKETS: Final[int] = 128
DEFAULT_FLOAT_PRECISION: Final[int] = 10
DEFAULT_CLIP_ZSCORE: Final[float] = 8.0

IDENTIFIER_FIELDS: Final[frozenset[str]] = frozenset({
    "id", "game_id", "player_id", "batter_id", "pitcher_id", "team_id",
    "opponent_id", "home_team_id", "away_team_id", "venue_id", "season",
})

TIMESTAMP_CANDIDATES: Final[tuple[str, ...]] = (
    "event_timestamp", "game_datetime", "game_date", "date", "timestamp",
    "occurred_at", "created_at", "updated_at",
)

PLAYER_ID_CANDIDATES: Final[tuple[str, ...]] = (
    "player_id", "mlb_player_id", "person_id", "batter_id", "pitcher_id", "id",
)

TEAM_ID_CANDIDATES: Final[tuple[str, ...]] = (
    "team_id", "mlb_team_id", "current_team_id", "club_id",
)

GAME_ID_CANDIDATES: Final[tuple[str, ...]] = (
    "game_id", "game_pk", "mlb_game_id", "id",
)

DEFAULT_RATE_SPECS: Final[dict[str, tuple[str, str]]] = {
    "batting_average": ("hits", "at_bats"),
    "on_base_percentage": ("times_on_base", "plate_appearances"),
    "slugging_percentage": ("total_bases", "at_bats"),
    "home_run_rate": ("home_runs", "plate_appearances"),
    "walk_rate": ("walks", "plate_appearances"),
    "strikeout_rate": ("strikeouts", "plate_appearances"),
    "extra_base_hit_rate": ("extra_base_hits", "plate_appearances"),
    "rbi_rate": ("rbi", "plate_appearances"),
    "run_rate": ("runs", "plate_appearances"),
    "stolen_base_rate": ("stolen_bases", "times_on_base"),
    "pitcher_strikeout_rate": ("pitcher_strikeouts", "batters_faced"),
    "pitcher_walk_rate": ("pitcher_walks", "batters_faced"),
    "pitcher_home_run_rate": ("pitcher_home_runs", "batters_faced"),
    "whip_component_rate": ("walks_hits_allowed", "innings_pitched"),
    "earned_run_rate_component": ("earned_runs", "innings_pitched"),
}

DEFAULT_COUNTING_FIELDS: Final[tuple[str, ...]] = (
    "plate_appearances", "at_bats", "hits", "singles", "doubles", "triples",
    "home_runs", "walks", "intentional_walks", "hit_by_pitch", "strikeouts",
    "runs", "rbi", "stolen_bases", "caught_stealing", "sacrifice_flies",
    "total_bases", "extra_base_hits", "times_on_base", "games_started",
    "innings_pitched", "batters_faced", "pitcher_strikeouts", "pitcher_walks",
    "pitcher_home_runs", "earned_runs", "runs_allowed", "hits_allowed",
    "walks_hits_allowed", "pitches", "strikes", "swinging_strikes",
    "ground_balls", "fly_balls", "line_drives", "popups", "hard_hit_events",
    "barrels", "batted_ball_events", "wins", "losses", "team_runs",
    "team_runs_allowed", "team_hits", "team_home_runs", "team_walks",
    "team_strikeouts", "errors",
)

DEFAULT_CONTEXT_NUMERIC_FIELDS: Final[tuple[str, ...]] = (
    "temperature_f", "humidity_pct", "wind_speed_mph", "wind_out_component",
    "air_density", "altitude_ft", "park_factor", "run_park_factor",
    "hr_park_factor", "hit_park_factor", "travel_miles", "rest_days",
    "timezone_change_hours", "lineup_slot", "days_since_last_game",
    "days_since_last_start", "pitch_count_last_game", "season_progress",
)

DEFAULT_CATEGORICAL_FIELDS: Final[tuple[str, ...]] = (
    "player_bats", "player_throws", "pitcher_throws", "batter_side",
    "home_away", "venue_name", "roof_type", "surface", "weather_condition",
    "day_night", "position", "division", "league", "opponent_division",
)

DEFAULT_LABEL_FIELDS: Final[tuple[str, ...]] = (
    "target_hit", "target_single", "target_double", "target_triple",
    "target_home_run", "target_walk", "target_strikeout", "target_rbi",
    "target_run", "target_total_bases", "target_fantasy_points",
    "target_team_win", "target_team_runs",
)


# ============================================================
# SECTION 08 - UTILITY FUNCTIONS
# ============================================================

def utc_now() -> datetime:
    return datetime.now(UTC)


def safe_divide(
    numerator: Any,
    denominator: Any,
    *,
    default: float = 0.0,
    epsilon: float = 1e-12,
) -> float:
    n = to_float(numerator, default=default)
    d = to_float(denominator, default=0.0)
    if not math.isfinite(n) or not math.isfinite(d) or abs(d) <= epsilon:
        return default
    value = n / d
    return value if math.isfinite(value) else default


def clamp(value: Any, minimum: float, maximum: float, default: float = 0.0) -> float:
    numeric = to_float(value, default=default)
    return min(max(numeric, minimum), maximum)


def sigmoid(value: Any) -> float:
    x = clamp(value, -60.0, 60.0)
    return 1.0 / (1.0 + math.exp(-x))


def log1p_safe(value: Any) -> float:
    numeric = max(to_float(value), 0.0)
    return math.log1p(numeric)


def signed_log1p(value: Any) -> float:
    numeric = to_float(value)
    return math.copysign(math.log1p(abs(numeric)), numeric)


def to_float(value: Any, default: float = 0.0) -> float:
    if value is None or isinstance(value, bool):
        return float(default)
    if isinstance(value, (int, float, Decimal)):
        try:
            numeric = float(value)
            return numeric if math.isfinite(numeric) else float(default)
        except (TypeError, ValueError, OverflowError):
            return float(default)
    if isinstance(value, str):
        stripped = value.strip().replace(",", "")
        if not stripped:
            return float(default)
        if stripped.endswith("%"):
            stripped = stripped[:-1]
            try:
                return float(stripped) / 100.0
            except ValueError:
                return float(default)
        try:
            numeric = float(Decimal(stripped))
            return numeric if math.isfinite(numeric) else float(default)
        except (InvalidOperation, ValueError, OverflowError):
            return float(default)
    return float(default)


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(to_float(value, default=float(default))))
    except (TypeError, ValueError, OverflowError):
        return default


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if pd is not None:
        try:
            missing = pd.isna(value)
            if isinstance(missing, bool):
                return missing
        except Exception:
            pass
    return False


def normalize_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def stable_hash(value: Any, buckets: int = DEFAULT_HASH_BUCKETS) -> int:
    if buckets <= 0:
        raise ValueError("buckets must be positive")
    digest = sha256(str(value).encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % buckets


def parse_datetime(value: Any, default: datetime | None = None) -> datetime | None:
    if value is None:
        return default
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=UTC)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=UTC)
        except (ValueError, OSError, OverflowError):
            return default
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        normalized = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
        for fmt in (
            "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y",
            "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M",
        ):
            try:
                return datetime.strptime(text, fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
    return default


def get_nested(record: Mapping[str, Any], path: str, default: Any = None) -> Any:
    current: Any = record
    for part in path.split("."):
        if isinstance(current, Mapping):
            current = current.get(part, default)
        else:
            current = getattr(current, part, default)
        if current is default:
            return default
    return current


def first_present(record: Mapping[str, Any], candidates: Sequence[str], default: Any = None) -> Any:
    for key in candidates:
        value = get_nested(record, key, None)
        if not is_missing(value):
            return value
    return default


def object_to_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump"):
        return dict(value.model_dump())
    if hasattr(value, "dict") and callable(value.dict):
        return dict(value.dict())
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    if hasattr(value, "__table__"):
        result: dict[str, Any] = {}
        try:
            for column in value.__table__.columns:
                result[column.name] = getattr(value, column.name)
            return result
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        return {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_") and not callable(item)
        }
    raise FeatureSchemaError(f"Cannot convert {type(value).__name__} to mapping")


def records_from_any(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if pd is not None and isinstance(data, pd.DataFrame):
        return [dict(row) for row in data.to_dict(orient="records")]
    if isinstance(data, Mapping):
        return [dict(data)]
    if isinstance(data, (str, bytes)):
        raise FeatureSchemaError("String input is not a valid record collection")
    if isinstance(data, Iterable):
        return [object_to_mapping(item) for item in data]
    return [object_to_mapping(data)]


def canonical_json(value: Any) -> str:
    def serializer(item: Any) -> Any:
        if isinstance(item, (datetime, date)):
            return item.isoformat()
        if isinstance(item, Decimal):
            return float(item)
        if isinstance(item, Enum):
            return item.value
        if is_dataclass(item):
            return asdict(item)
        if np is not None and isinstance(item, np.generic):
            return item.item()
        raise TypeError(f"Unsupported type: {type(item).__name__}")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=serializer)


def fingerprint(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def mean(values: Iterable[Any], default: float = 0.0) -> float:
    numeric = [to_float(v) for v in values if not is_missing(v)]
    return statistics.fmean(numeric) if numeric else default


def median(values: Iterable[Any], default: float = 0.0) -> float:
    numeric = [to_float(v) for v in values if not is_missing(v)]
    return float(statistics.median(numeric)) if numeric else default


def population_std(values: Iterable[Any], default: float = 0.0) -> float:
    numeric = [to_float(v) for v in values if not is_missing(v)]
    return float(statistics.pstdev(numeric)) if len(numeric) > 1 else default


def weighted_mean(values: Sequence[float], weights: Sequence[float], default: float = 0.0) -> float:
    if len(values) != len(weights) or not values:
        return default
    total_weight = sum(max(w, 0.0) for w in weights)
    if total_weight <= 0:
        return default
    return sum(v * max(w, 0.0) for v, w in zip(values, weights)) / total_weight


def days_between(later: datetime | None, earlier: datetime | None, default: float = 0.0) -> float:
    if later is None or earlier is None:
        return default
    return (later - earlier).total_seconds() / 86400.0


# ============================================================
# SECTION 09 - CONFIGURATION DATA MODELS
# ============================================================

@dataclass(frozen=True, slots=True)
class FeatureColumnSpec:
    name: str
    dtype: str = "float"
    default: Any = 0.0
    minimum: float | None = None
    maximum: float | None = None
    required: bool = False
    description: str = ""
    source: str = ""
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RateFeatureSpec:
    name: str
    numerator: str
    denominator: str
    prior_mean: float = 0.0
    prior_weight: float = DEFAULT_PRIOR_WEIGHT
    minimum: float = 0.0
    maximum: float = 1.0


@dataclass(frozen=True, slots=True)
class RollingFeatureSpec:
    source_field: str
    windows: tuple[int, ...] = DEFAULT_ROLLING_WINDOWS
    operations: tuple[str, ...] = ("sum", "mean", "std", "min", "max", "trend")
    min_periods: int = 1


@dataclass(frozen=True, slots=True)
class CategoricalFeatureSpec:
    source_field: str
    output_prefix: str | None = None
    known_values: tuple[str, ...] = ()
    hash_buckets: int = DEFAULT_HASH_BUCKETS
    strategy: UnknownCategoryStrategy = UnknownCategoryStrategy.HASH


@dataclass(slots=True)
class FeatureBuilderConfig:
    mode: FeatureMode = FeatureMode.INFERENCE
    prediction_unit: PredictionUnit = PredictionUnit.PLAYER_GAME
    rolling_windows: tuple[int, ...] = DEFAULT_ROLLING_WINDOWS
    ewm_halflives: tuple[float, ...] = DEFAULT_EWM_HALFLIVES
    minimum_history: int = DEFAULT_MIN_HISTORY
    prior_weight: float = DEFAULT_PRIOR_WEIGHT
    missing_strategy: MissingValueStrategy = MissingValueStrategy.ZERO
    missing_constant: float = 0.0
    unknown_category_strategy: UnknownCategoryStrategy = UnknownCategoryStrategy.HASH
    categorical_hash_buckets: int = DEFAULT_HASH_BUCKETS
    leakage_policy: LeakagePolicy = LeakagePolicy.ERROR
    strict: bool = False
    include_identifiers: bool = True
    include_missing_indicators: bool = True
    include_lineage: bool = True
    include_labels: bool = False
    include_raw_counts: bool = True
    include_rates: bool = True
    include_rolling: bool = True
    include_ewm: bool = True
    include_trends: bool = True
    include_interactions: bool = True
    include_context: bool = True
    include_uncertainty: bool = True
    float_precision: int = DEFAULT_FLOAT_PRECISION
    clip_zscore: float = DEFAULT_CLIP_ZSCORE
    counting_fields: tuple[str, ...] = DEFAULT_COUNTING_FIELDS
    context_numeric_fields: tuple[str, ...] = DEFAULT_CONTEXT_NUMERIC_FIELDS
    categorical_fields: tuple[str, ...] = DEFAULT_CATEGORICAL_FIELDS
    label_fields: tuple[str, ...] = DEFAULT_LABEL_FIELDS
    rate_specs: dict[str, tuple[str, str]] = field(
        default_factory=lambda: dict(DEFAULT_RATE_SPECS)
    )

    def validate(self) -> None:
        if not self.rolling_windows or any(w <= 0 for w in self.rolling_windows):
            raise FeatureConfigurationError("rolling_windows must contain positive integers")
        if any(h <= 0 for h in self.ewm_halflives):
            raise FeatureConfigurationError("ewm_halflives must be positive")
        if self.minimum_history < 0:
            raise FeatureConfigurationError("minimum_history cannot be negative")
        if self.prior_weight < 0:
            raise FeatureConfigurationError("prior_weight cannot be negative")
        if self.categorical_hash_buckets <= 0:
            raise FeatureConfigurationError("categorical_hash_buckets must be positive")
        if self.float_precision < 0:
            raise FeatureConfigurationError("float_precision cannot be negative")


# ============================================================
# SECTION 10 - RESULT AND DIAGNOSTIC DATA MODELS
# ============================================================

@dataclass(slots=True)
class FeatureIssue:
    code: str
    message: str
    severity: FeatureSeverity = FeatureSeverity.WARNING
    field_name: str | None = None
    record_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FeatureLineage:
    feature_name: str
    source_fields: tuple[str, ...]
    operation: str
    as_of: datetime
    history_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FeatureVector:
    values: dict[str, Any]
    as_of: datetime
    entity_id: str | int | None = None
    game_id: str | int | None = None
    prediction_unit: PredictionUnit = PredictionUnit.PLAYER_GAME
    labels: dict[str, Any] = field(default_factory=dict)
    lineage: dict[str, FeatureLineage] = field(default_factory=dict)
    issues: list[FeatureIssue] = field(default_factory=list)
    schema_hash: str = ""
    vector_hash: str = ""

    def finalize(self) -> "FeatureVector":
        self.values = dict(sorted(self.values.items()))
        self.labels = dict(sorted(self.labels.items()))
        self.schema_hash = fingerprint(list(self.values.keys()))
        self.vector_hash = fingerprint({
            "values": self.values,
            "labels": self.labels,
            "as_of": self.as_of,
            "entity_id": self.entity_id,
            "game_id": self.game_id,
            "prediction_unit": self.prediction_unit.value,
        })
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "values": self.values,
            "as_of": self.as_of.isoformat(),
            "entity_id": self.entity_id,
            "game_id": self.game_id,
            "prediction_unit": self.prediction_unit.value,
            "labels": self.labels,
            "lineage": {
                key: {
                    "feature_name": item.feature_name,
                    "source_fields": list(item.source_fields),
                    "operation": item.operation,
                    "as_of": item.as_of.isoformat(),
                    "history_count": item.history_count,
                    "metadata": item.metadata,
                }
                for key, item in self.lineage.items()
            },
            "issues": [asdict(issue) for issue in self.issues],
            "schema_hash": self.schema_hash,
            "vector_hash": self.vector_hash,
        }


@dataclass(slots=True)
class FeatureBatch:
    vectors: list[FeatureVector]
    created_at: datetime = field(default_factory=utc_now)
    config_hash: str = ""
    schema_hash: str = ""
    issues: list[FeatureIssue] = field(default_factory=list)

    def finalize(self) -> "FeatureBatch":
        for vector in self.vectors:
            vector.finalize()
        schemas = sorted({vector.schema_hash for vector in self.vectors})
        self.schema_hash = fingerprint(schemas)
        return self

    def rows(self, include_labels: bool = True) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for vector in self.vectors:
            row = dict(vector.values)
            if include_labels:
                row.update(vector.labels)
            rows.append(row)
        return rows

    def to_dataframe(self) -> Any:
        if pd is None:
            raise FeatureBuilderError("pandas is not installed")
        return pd.DataFrame(self.rows())


# ============================================================
# SECTION 11 - FEATURE MANIFEST
# ============================================================

@dataclass(slots=True)
class FeatureManifest:
    module_version: str
    created_at: datetime
    prediction_unit: PredictionUnit
    mode: FeatureMode
    feature_names: list[str]
    label_names: list[str]
    schema_hash: str
    config_hash: str
    descriptions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_version": self.module_version,
            "created_at": self.created_at.isoformat(),
            "prediction_unit": self.prediction_unit.value,
            "mode": self.mode.value,
            "feature_names": self.feature_names,
            "label_names": self.label_names,
            "schema_hash": self.schema_hash,
            "config_hash": self.config_hash,
            "descriptions": self.descriptions,
        }


# ============================================================
# SECTION 12 - RECORD NORMALIZATION
# ============================================================

class RecordNormalizer:
    """Normalize heterogeneous baseball records into canonical dictionaries."""

    FIELD_ALIASES: Final[dict[str, tuple[str, ...]]] = {
        "game_id": ("game_id", "game_pk", "gamePk", "mlb_game_id"),
        "player_id": ("player_id", "person_id", "personId", "mlb_player_id"),
        "team_id": ("team_id", "teamId", "mlb_team_id", "club_id"),
        "opponent_id": ("opponent_id", "opponentId", "opposing_team_id"),
        "venue_id": ("venue_id", "venueId", "ballpark_id"),
        "game_date": ("game_date", "gameDate", "date", "official_date"),
        "plate_appearances": ("plate_appearances", "pa", "PA"),
        "at_bats": ("at_bats", "ab", "AB"),
        "hits": ("hits", "h", "H"),
        "doubles": ("doubles", "2b", "2B"),
        "triples": ("triples", "3b", "3B"),
        "home_runs": ("home_runs", "hr", "HR"),
        "walks": ("walks", "bb", "BB", "base_on_balls"),
        "strikeouts": ("strikeouts", "so", "SO", "k"),
        "runs": ("runs", "r", "R"),
        "rbi": ("rbi", "RBI"),
        "stolen_bases": ("stolen_bases", "sb", "SB"),
        "caught_stealing": ("caught_stealing", "cs", "CS"),
        "innings_pitched": ("innings_pitched", "ip", "IP"),
        "earned_runs": ("earned_runs", "er", "ER"),
        "hits_allowed": ("hits_allowed", "ha", "H_allowed"),
        "pitcher_walks": ("pitcher_walks", "bb_allowed", "BB_allowed"),
        "pitcher_strikeouts": ("pitcher_strikeouts", "so_pitching", "K_pitching"),
        "batters_faced": ("batters_faced", "bf", "BF"),
    }

    def __init__(self, aliases: Mapping[str, Sequence[str]] | None = None) -> None:
        self.aliases = {
            key: tuple(values)
            for key, values in (aliases or self.FIELD_ALIASES).items()
        }

    def normalize(self, value: Any) -> dict[str, Any]:
        raw = object_to_mapping(value)
        normalized = {normalize_name(key): item for key, item in raw.items()}

        for canonical, aliases in self.aliases.items():
            if canonical in normalized and not is_missing(normalized[canonical]):
                continue
            for alias in aliases:
                alias_key = normalize_name(alias)
                if alias_key in normalized and not is_missing(normalized[alias_key]):
                    normalized[canonical] = normalized[alias_key]
                    break

        self._derive_baseball_counts(normalized)
        return normalized

    def normalize_many(self, values: Any) -> list[dict[str, Any]]:
        return [self.normalize(item) for item in records_from_any(values)]

    @staticmethod
    def _derive_baseball_counts(record: MutableRecord) -> None:
        hits = to_float(record.get("hits"))
        doubles = to_float(record.get("doubles"))
        triples = to_float(record.get("triples"))
        home_runs = to_float(record.get("home_runs"))

        record.setdefault("singles", max(hits - doubles - triples - home_runs, 0.0))
        record.setdefault("extra_base_hits", max(doubles + triples + home_runs, 0.0))
        record.setdefault(
            "total_bases",
            max(record["singles"] + 2 * doubles + 3 * triples + 4 * home_runs, 0.0),
        )

        walks = to_float(record.get("walks"))
        hbp = to_float(record.get("hit_by_pitch"))
        record.setdefault("times_on_base", max(hits + walks + hbp, 0.0))

        record.setdefault(
            "walks_hits_allowed",
            max(to_float(record.get("hits_allowed")) + to_float(record.get("pitcher_walks")), 0.0),
        )

        if is_missing(record.get("plate_appearances")):
            at_bats = to_float(record.get("at_bats"))
            sacrifice_flies = to_float(record.get("sacrifice_flies"))
            record["plate_appearances"] = max(at_bats + walks + hbp + sacrifice_flies, 0.0)


# ============================================================
# SECTION 13 - TEMPORAL SAFETY
# ============================================================

class TemporalGuard:
    def __init__(
        self,
        *,
        policy: LeakagePolicy = LeakagePolicy.ERROR,
        timestamp_candidates: Sequence[str] = TIMESTAMP_CANDIDATES,
    ) -> None:
        self.policy = policy
        self.timestamp_candidates = tuple(timestamp_candidates)

    def timestamp(self, record: Mapping[str, Any]) -> datetime | None:
        return parse_datetime(first_present(record, self.timestamp_candidates))

    def filter(
        self,
        records: Sequence[dict[str, Any]],
        as_of: datetime,
    ) -> tuple[list[dict[str, Any]], list[FeatureIssue]]:
        safe: list[dict[str, Any]] = []
        issues: list[FeatureIssue] = []

        for record in records:
            timestamp = self.timestamp(record)
            if timestamp is None or timestamp < as_of:
                safe.append(record)
                continue

            issue = FeatureIssue(
                code="temporal_leakage",
                message=f"Record timestamp {timestamp.isoformat()} is not earlier than as_of",
                severity=FeatureSeverity.ERROR,
                record_id=str(first_present(record, GAME_ID_CANDIDATES, "")),
                details={"timestamp": timestamp.isoformat(), "as_of": as_of.isoformat()},
            )
            issues.append(issue)

            if self.policy == LeakagePolicy.ERROR:
                raise TemporalLeakageError(issue.message)
            if self.policy == LeakagePolicy.WARN:
                LOGGER.warning(issue.message)
            # DROP and WARN both exclude the record.

        return safe, issues


# ============================================================
# SECTION 14 - HISTORY INDEX
# ============================================================

class HistoryIndex:
    """In-memory temporal index optimized for repeated feature builds."""

    def __init__(
        self,
        records: Sequence[dict[str, Any]],
        *,
        entity_fields: Sequence[str] = PLAYER_ID_CANDIDATES,
        timestamp_fields: Sequence[str] = TIMESTAMP_CANDIDATES,
    ) -> None:
        self.entity_fields = tuple(entity_fields)
        self.timestamp_fields = tuple(timestamp_fields)
        self._records: dict[Any, list[dict[str, Any]]] = defaultdict(list)

        for record in records:
            entity_id = first_present(record, self.entity_fields)
            if entity_id is not None:
                self._records[entity_id].append(record)

        for entity_id in self._records:
            self._records[entity_id].sort(
                key=lambda item: parse_datetime(
                    first_present(item, self.timestamp_fields),
                    datetime.min.replace(tzinfo=UTC),
                )
            )

    def get(
        self,
        entity_id: Any,
        *,
        before: datetime,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        records = self._records.get(entity_id, [])
        eligible = [
            item for item in records
            if (
                parse_datetime(first_present(item, self.timestamp_fields)) is None
                or parse_datetime(first_present(item, self.timestamp_fields)) < before
            )
        ]
        return eligible[-limit:] if limit else eligible

    def entities(self) -> list[Any]:
        return list(self._records.keys())


# ============================================================
# SECTION 15 - NUMERICAL TRANSFORMATIONS
# ============================================================

class NumericalTransformer:
    @staticmethod
    def aggregate(values: Sequence[Any], operation: str) -> float:
        numeric = [to_float(value) for value in values if not is_missing(value)]
        if not numeric:
            return 0.0
        if operation == "sum":
            return float(sum(numeric))
        if operation == "mean":
            return mean(numeric)
        if operation == "median":
            return median(numeric)
        if operation == "std":
            return population_std(numeric)
        if operation == "min":
            return float(min(numeric))
        if operation == "max":
            return float(max(numeric))
        if operation == "last":
            return float(numeric[-1])
        if operation == "trend":
            return NumericalTransformer.linear_trend(numeric)
        raise FeatureConfigurationError(f"Unsupported aggregation operation: {operation}")

    @staticmethod
    def linear_trend(values: Sequence[Any]) -> float:
        y = [to_float(value) for value in values if not is_missing(value)]
        n = len(y)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2.0
        y_mean = mean(y)
        numerator = sum((index - x_mean) * (value - y_mean) for index, value in enumerate(y))
        denominator = sum((index - x_mean) ** 2 for index in range(n))
        return safe_divide(numerator, denominator)

    @staticmethod
    def ewm(values: Sequence[Any], halflife: float) -> float:
        numeric = [to_float(value) for value in values if not is_missing(value)]
        if not numeric:
            return 0.0
        alpha = 1.0 - math.exp(math.log(0.5) / halflife)
        result = numeric[0]
        for value in numeric[1:]:
            result = alpha * value + (1.0 - alpha) * result
        return float(result)

    @staticmethod
    def shrink_rate(
        numerator: Any,
        denominator: Any,
        *,
        prior_mean: float,
        prior_weight: float,
    ) -> float:
        n = max(to_float(numerator), 0.0)
        d = max(to_float(denominator), 0.0)
        return safe_divide(n + prior_mean * prior_weight, d + prior_weight, default=prior_mean)

    @staticmethod
    def robust_zscore(value: Any, population: Sequence[Any]) -> float:
        numeric = [to_float(item) for item in population if not is_missing(item)]
        if len(numeric) < 3:
            return 0.0
        center = median(numeric)
        absolute_deviations = [abs(item - center) for item in numeric]
        mad = median(absolute_deviations)
        if mad <= 1e-12:
            return 0.0
        return 0.67448975 * (to_float(value) - center) / mad


# ============================================================
# SECTION 16 - CATEGORICAL ENCODER
# ============================================================

class StableCategoricalEncoder:
    """Stateless deterministic encoder suitable for online inference."""

    def __init__(
        self,
        *,
        buckets: int = DEFAULT_HASH_BUCKETS,
        unknown_strategy: UnknownCategoryStrategy = UnknownCategoryStrategy.HASH,
    ) -> None:
        self.buckets = buckets
        self.unknown_strategy = unknown_strategy

    def encode_scalar(
        self,
        field_name: str,
        value: Any,
        known_values: Sequence[str] = (),
    ) -> dict[str, float]:
        normalized = normalize_name(value) or "missing"
        prefix = normalize_name(field_name)

        if known_values:
            normalized_known = {normalize_name(item) for item in known_values}
            if normalized in normalized_known:
                return {f"{prefix}__{normalized}": 1.0}
            if self.unknown_strategy == UnknownCategoryStrategy.ERROR:
                raise FeatureValidationError(
                    f"Unknown category {value!r} for field {field_name!r}"
                )
            if self.unknown_strategy == UnknownCategoryStrategy.ZERO:
                return {f"{prefix}__unknown": 0.0}

        bucket = stable_hash(f"{prefix}:{normalized}", self.buckets)
        return {
            f"{prefix}__hash": float(bucket),
            f"{prefix}__present": 0.0 if normalized == "missing" else 1.0,
        }


# ============================================================
# SECTION 17 - IMPUTATION
# ============================================================

class FeatureImputer:
    def __init__(
        self,
        strategy: MissingValueStrategy,
        constant: float = 0.0,
    ) -> None:
        self.strategy = strategy
        self.constant = constant
        self.statistics_: dict[str, float] = {}

    def fit(self, rows: Sequence[Mapping[str, Any]]) -> "FeatureImputer":
        columns: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            for key, value in row.items():
                if not is_missing(value) and isinstance(value, (int, float, Decimal)):
                    columns[key].append(to_float(value))

        for key, values in columns.items():
            if self.strategy == MissingValueStrategy.MEAN:
                self.statistics_[key] = mean(values)
            elif self.strategy == MissingValueStrategy.MEDIAN:
                self.statistics_[key] = median(values)
        return self

    def transform(self, row: Mapping[str, Any]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in row.items():
            if not is_missing(value):
                output[key] = value
                continue
            if self.strategy == MissingValueStrategy.PRESERVE:
                output[key] = value
            elif self.strategy == MissingValueStrategy.CONSTANT:
                output[key] = self.constant
            elif self.strategy in (MissingValueStrategy.MEAN, MissingValueStrategy.MEDIAN):
                output[key] = self.statistics_.get(key, self.constant)
            else:
                output[key] = 0.0
        return output


# ============================================================
# SECTION 18 - FEATURE VALIDATOR
# ============================================================

class FeatureValidator:
    def __init__(self, *, strict: bool = False) -> None:
        self.strict = strict

    def validate_vector(self, vector: FeatureVector) -> list[FeatureIssue]:
        issues: list[FeatureIssue] = []
        for key, value in vector.values.items():
            if not key or key != normalize_name(key):
                issues.append(FeatureIssue(
                    code="invalid_feature_name",
                    message=f"Feature name is not canonical: {key!r}",
                    severity=FeatureSeverity.ERROR,
                    field_name=key,
                ))

            if isinstance(value, float) and not math.isfinite(value):
                issues.append(FeatureIssue(
                    code="non_finite_value",
                    message=f"Feature {key!r} contains non-finite value",
                    severity=FeatureSeverity.ERROR,
                    field_name=key,
                ))

            if isinstance(value, (list, dict, set, tuple)):
                issues.append(FeatureIssue(
                    code="non_scalar_value",
                    message=f"Feature {key!r} is not scalar",
                    severity=FeatureSeverity.ERROR,
                    field_name=key,
                ))

        if self.strict and any(issue.severity == FeatureSeverity.ERROR for issue in issues):
            raise FeatureValidationError(
                "; ".join(issue.message for issue in issues if issue.severity == FeatureSeverity.ERROR)
            )
        return issues

    def validate_batch_schema(self, vectors: Sequence[FeatureVector]) -> list[FeatureIssue]:
        if not vectors:
            return []
        reference = set(vectors[0].values)
        issues: list[FeatureIssue] = []
        for index, vector in enumerate(vectors[1:], start=1):
            current = set(vector.values)
            if current != reference:
                issues.append(FeatureIssue(
                    code="schema_mismatch",
                    message=f"Vector {index} does not match the reference schema",
                    severity=FeatureSeverity.ERROR,
                    details={
                        "missing": sorted(reference - current),
                        "extra": sorted(current - reference),
                    },
                ))
        if self.strict and issues:
            raise FeatureValidationError(issues[0].message)
        return issues


# ============================================================
# SECTION 19 - FEATURE BUILDER
# ============================================================

class FeatureBuilder:
    """
    Central enterprise feature construction service.

    The builder is intentionally stateless with respect to learned model
    parameters. Any state stored here is limited to configuration and fitted
    imputation statistics.
    """

    def __init__(
        self,
        config: FeatureBuilderConfig | None = None,
        *,
        normalizer: RecordNormalizer | None = None,
        validator: FeatureValidator | None = None,
    ) -> None:
        self.config = config or FeatureBuilderConfig()
        self.config.validate()
        self.normalizer = normalizer or RecordNormalizer()
        self.validator = validator or FeatureValidator(strict=self.config.strict)
        self.temporal_guard = TemporalGuard(policy=self.config.leakage_policy)
        self.encoder = StableCategoricalEncoder(
            buckets=self.config.categorical_hash_buckets,
            unknown_strategy=self.config.unknown_category_strategy,
        )
        self.imputer = FeatureImputer(
            strategy=self.config.missing_strategy,
            constant=self.config.missing_constant,
        )

    # --------------------------------------------------------
    # SECTION 19.01 - PRIMARY SINGLE-VECTOR API
    # --------------------------------------------------------

    def build(
        self,
        *,
        current: Any,
        history: Any = None,
        as_of: datetime | date | str | None = None,
        opponent_history: Any = None,
        team_history: Any = None,
        context: Any = None,
        labels: Any = None,
    ) -> FeatureVector:
        current_record = self.normalizer.normalize(current)
        history_records = self.normalizer.normalize_many(history)
        opponent_records = self.normalizer.normalize_many(opponent_history)
        team_records = self.normalizer.normalize_many(team_history)
        context_record = self.normalizer.normalize(context) if context is not None else {}

        resolved_as_of = self._resolve_as_of(as_of, current_record)
        history_records, temporal_issues = self.temporal_guard.filter(
            history_records,
            resolved_as_of,
        )
        opponent_records, opponent_temporal_issues = self.temporal_guard.filter(
            opponent_records,
            resolved_as_of,
        )
        team_records, team_temporal_issues = self.temporal_guard.filter(
            team_records,
            resolved_as_of,
        )

        features: dict[str, Any] = {}
        lineage: dict[str, FeatureLineage] = {}

        if self.config.include_identifiers:
            self._add_identifiers(features, current_record, resolved_as_of)

        self._add_calendar_features(features, current_record, resolved_as_of)
        self._add_sample_features(features, history_records)
        self._add_current_numeric_features(features, current_record, lineage, resolved_as_of)

        if self.config.include_rates:
            self._add_rate_features(features, history_records, lineage, resolved_as_of)

        if self.config.include_rolling:
            self._add_rolling_features(features, history_records, lineage, resolved_as_of)

        if self.config.include_ewm:
            self._add_ewm_features(features, history_records, lineage, resolved_as_of)

        if self.config.include_context:
            self._add_context_features(features, current_record, context_record, lineage, resolved_as_of)

        self._add_split_features(features, history_records, current_record, lineage, resolved_as_of)
        self._add_opponent_features(features, opponent_records, lineage, resolved_as_of)
        self._add_team_features(features, team_records, lineage, resolved_as_of)

        if self.config.include_interactions:
            self._add_interaction_features(features)

        if self.config.include_uncertainty:
            self._add_uncertainty_features(features, history_records)

        if self.config.include_missing_indicators:
            self._add_missing_indicators(features)

        features = self._sanitize_features(features)

        label_values: dict[str, Any] = {}
        if self.config.include_labels or self.config.mode == FeatureMode.TRAINING:
            label_record = self.normalizer.normalize(labels) if labels is not None else current_record
            label_values = self._extract_labels(label_record)

        vector = FeatureVector(
            values=features,
            as_of=resolved_as_of,
            entity_id=first_present(current_record, PLAYER_ID_CANDIDATES),
            game_id=first_present(current_record, GAME_ID_CANDIDATES),
            prediction_unit=self.config.prediction_unit,
            labels=label_values,
            lineage=lineage if self.config.include_lineage else {},
            issues=temporal_issues + opponent_temporal_issues + team_temporal_issues,
        )
        vector.issues.extend(self.validator.validate_vector(vector))
        return vector.finalize()

    # --------------------------------------------------------
    # SECTION 19.02 - BATCH API
    # --------------------------------------------------------

    def build_batch(
        self,
        rows: Any,
        *,
        history: Any = None,
        as_of_field: str = "game_date",
        entity_field: str = "player_id",
        context_rows: Any = None,
        labels_rows: Any = None,
    ) -> FeatureBatch:
        current_rows = self.normalizer.normalize_many(rows)
        all_history = self.normalizer.normalize_many(history)
        contexts = self.normalizer.normalize_many(context_rows)
        labels = self.normalizer.normalize_many(labels_rows)

        context_lookup = self._lookup_by_identity(contexts)
        label_lookup = self._lookup_by_identity(labels)
        history_index = HistoryIndex(all_history, entity_fields=(entity_field, *PLAYER_ID_CANDIDATES))

        vectors: list[FeatureVector] = []
        for row in current_rows:
            entity_id = first_present(row, (entity_field, *PLAYER_ID_CANDIDATES))
            as_of = parse_datetime(row.get(as_of_field)) or self._resolve_as_of(None, row)
            identity_key = self._identity_key(row)

            vector = self.build(
                current=row,
                history=history_index.get(entity_id, before=as_of) if entity_id is not None else [],
                as_of=as_of,
                context=context_lookup.get(identity_key),
                labels=label_lookup.get(identity_key),
            )
            vectors.append(vector)

        batch = FeatureBatch(
            vectors=vectors,
            config_hash=self.config_hash(),
        )
        batch.issues.extend(self.validator.validate_batch_schema(vectors))
        return batch.finalize()

    # --------------------------------------------------------
    # SECTION 19.03 - DATAFRAME API
    # --------------------------------------------------------

    def build_dataframe(self, *args: Any, **kwargs: Any) -> Any:
        batch = self.build_batch(*args, **kwargs)
        return batch.to_dataframe()

    # --------------------------------------------------------
    # SECTION 19.04 - FITTED IMPUTATION API
    # --------------------------------------------------------

    def fit_imputer(self, rows: Sequence[Mapping[str, Any]]) -> "FeatureBuilder":
        self.imputer.fit(rows)
        return self

    # --------------------------------------------------------
    # SECTION 19.05 - IDENTIFIER FEATURES
    # --------------------------------------------------------

    def _add_identifiers(
        self,
        features: MutableRecord,
        record: Mapping[str, Any],
        as_of: datetime,
    ) -> None:
        for canonical, candidates in (
            ("player_id", PLAYER_ID_CANDIDATES),
            ("team_id", TEAM_ID_CANDIDATES),
            ("game_id", GAME_ID_CANDIDATES),
            ("opponent_id", ("opponent_id", "opposing_team_id")),
            ("venue_id", ("venue_id", "ballpark_id")),
        ):
            value = first_present(record, candidates)
            if value is not None:
                features[canonical] = value

        features["as_of_epoch"] = as_of.timestamp()
        features["season"] = to_int(record.get("season"), as_of.year)

    # --------------------------------------------------------
    # SECTION 19.06 - CALENDAR FEATURES
    # --------------------------------------------------------

    def _add_calendar_features(
        self,
        features: MutableRecord,
        record: Mapping[str, Any],
        as_of: datetime,
    ) -> None:
        game_time = parse_datetime(
            first_present(record, ("game_datetime", "game_date", "date")),
            as_of,
        ) or as_of

        day_of_year = game_time.timetuple().tm_yday
        features.update({
            "calendar_year": float(game_time.year),
            "calendar_month": float(game_time.month),
            "calendar_day": float(game_time.day),
            "calendar_day_of_week": float(game_time.weekday()),
            "calendar_day_of_year": float(day_of_year),
            "calendar_hour": float(game_time.hour),
            "calendar_is_weekend": float(game_time.weekday() >= 5),
            "calendar_month_sin": math.sin(2 * math.pi * game_time.month / 12.0),
            "calendar_month_cos": math.cos(2 * math.pi * game_time.month / 12.0),
            "calendar_day_sin": math.sin(2 * math.pi * day_of_year / 366.0),
            "calendar_day_cos": math.cos(2 * math.pi * day_of_year / 366.0),
            "season_progress": clamp((day_of_year - 80) / 210.0, 0.0, 1.0),
        })

    # --------------------------------------------------------
    # SECTION 19.07 - SAMPLE FEATURES
    # --------------------------------------------------------

    def _add_sample_features(
        self,
        features: MutableRecord,
        history: Sequence[Mapping[str, Any]],
    ) -> None:
        features["history_game_count"] = float(len(history))
        features["history_log_count"] = log1p_safe(len(history))
        features["history_sufficient"] = float(len(history) >= self.config.minimum_history)

        plate_appearances = sum(to_float(item.get("plate_appearances")) for item in history)
        features["history_plate_appearances"] = plate_appearances
        features["history_plate_appearances_log"] = log1p_safe(plate_appearances)

    # --------------------------------------------------------
    # SECTION 19.08 - CURRENT NUMERIC FEATURES
    # --------------------------------------------------------

    def _add_current_numeric_features(
        self,
        features: MutableRecord,
        record: Mapping[str, Any],
        lineage: MutableMapping[str, FeatureLineage],
        as_of: datetime,
    ) -> None:
        if not self.config.include_raw_counts:
            return

        for field_name in self.config.counting_fields:
            if field_name not in record:
                continue
            feature_name = f"current_{field_name}"
            features[feature_name] = to_float(record.get(field_name))
            lineage[feature_name] = FeatureLineage(
                feature_name=feature_name,
                source_fields=(field_name,),
                operation="identity",
                as_of=as_of,
                history_count=0,
            )

    # --------------------------------------------------------
    # SECTION 19.09 - RATE FEATURES
    # --------------------------------------------------------

    def _add_rate_features(
        self,
        features: MutableRecord,
        history: Sequence[Mapping[str, Any]],
        lineage: MutableMapping[str, FeatureLineage],
        as_of: datetime,
    ) -> None:
        totals = self._totals(history)

        for feature_name, (numerator, denominator) in self.config.rate_specs.items():
            numerator_value = totals.get(numerator, 0.0)
            denominator_value = totals.get(denominator, 0.0)
            raw_rate = safe_divide(numerator_value, denominator_value)
            smoothed_rate = NumericalTransformer.shrink_rate(
                numerator_value,
                denominator_value,
                prior_mean=raw_rate if denominator_value > 0 else 0.0,
                prior_weight=self.config.prior_weight,
            )
            output_name = f"career_{feature_name}"
            features[output_name] = raw_rate
            features[f"{output_name}_smoothed"] = smoothed_rate
            lineage[output_name] = FeatureLineage(
                feature_name=output_name,
                source_fields=(numerator, denominator),
                operation="sum_ratio",
                as_of=as_of,
                history_count=len(history),
            )

        hits = totals.get("hits", 0.0)
        walks = totals.get("walks", 0.0)
        hbp = totals.get("hit_by_pitch", 0.0)
        sacrifice_flies = totals.get("sacrifice_flies", 0.0)
        at_bats = totals.get("at_bats", 0.0)
        total_bases = totals.get("total_bases", 0.0)

        features["career_obp"] = safe_divide(
            hits + walks + hbp,
            at_bats + walks + hbp + sacrifice_flies,
        )
        features["career_slg"] = safe_divide(total_bases, at_bats)
        features["career_ops"] = features["career_obp"] + features["career_slg"]
        features["career_iso"] = features["career_slg"] - safe_divide(hits, at_bats)
        features["career_babip"] = safe_divide(
            hits - totals.get("home_runs", 0.0),
            at_bats - totals.get("strikeouts", 0.0)
            - totals.get("home_runs", 0.0) + sacrifice_flies,
        )

        innings = totals.get("innings_pitched", 0.0)
        features["career_era"] = 9.0 * safe_divide(totals.get("earned_runs", 0.0), innings)
        features["career_whip"] = safe_divide(totals.get("walks_hits_allowed", 0.0), innings)
        features["career_k_per_9"] = 9.0 * safe_divide(totals.get("pitcher_strikeouts", 0.0), innings)
        features["career_bb_per_9"] = 9.0 * safe_divide(totals.get("pitcher_walks", 0.0), innings)
        features["career_hr_per_9"] = 9.0 * safe_divide(totals.get("pitcher_home_runs", 0.0), innings)

    # --------------------------------------------------------
    # SECTION 19.10 - ROLLING FEATURES
    # --------------------------------------------------------

    def _add_rolling_features(
        self,
        features: MutableRecord,
        history: Sequence[Mapping[str, Any]],
        lineage: MutableMapping[str, FeatureLineage],
        as_of: datetime,
    ) -> None:
        for window in self.config.rolling_windows:
            window_records = history[-window:]
            for field_name in self.config.counting_fields:
                values = [item.get(field_name) for item in window_records if field_name in item]
                if not values:
                    continue

                for operation in ("sum", "mean", "std"):
                    output_name = f"{field_name}_last_{window}_{operation}"
                    features[output_name] = NumericalTransformer.aggregate(values, operation)
                    lineage[output_name] = FeatureLineage(
                        feature_name=output_name,
                        source_fields=(field_name,),
                        operation=f"rolling_{operation}",
                        as_of=as_of,
                        history_count=len(window_records),
                        metadata={"window": window},
                    )

                if self.config.include_trends:
                    output_name = f"{field_name}_last_{window}_trend"
                    features[output_name] = NumericalTransformer.linear_trend(values)
                    lineage[output_name] = FeatureLineage(
                        feature_name=output_name,
                        source_fields=(field_name,),
                        operation="rolling_linear_trend",
                        as_of=as_of,
                        history_count=len(window_records),
                        metadata={"window": window},
                    )

            self._add_window_rates(features, window_records, window)

    def _add_window_rates(
        self,
        features: MutableRecord,
        records: Sequence[Mapping[str, Any]],
        window: int,
    ) -> None:
        totals = self._totals(records)
        for feature_name, (numerator, denominator) in self.config.rate_specs.items():
            features[f"{feature_name}_last_{window}"] = safe_divide(
                totals.get(numerator),
                totals.get(denominator),
            )

    # --------------------------------------------------------
    # SECTION 19.11 - EWM FEATURES
    # --------------------------------------------------------

    def _add_ewm_features(
        self,
        features: MutableRecord,
        history: Sequence[Mapping[str, Any]],
        lineage: MutableMapping[str, FeatureLineage],
        as_of: datetime,
    ) -> None:
        for halflife in self.config.ewm_halflives:
            token = str(halflife).replace(".", "_")
            for field_name in self.config.counting_fields:
                values = [item.get(field_name) for item in history if field_name in item]
                if not values:
                    continue
                output_name = f"{field_name}_ewm_hl_{token}"
                features[output_name] = NumericalTransformer.ewm(values, halflife)
                lineage[output_name] = FeatureLineage(
                    feature_name=output_name,
                    source_fields=(field_name,),
                    operation="ewm",
                    as_of=as_of,
                    history_count=len(values),
                    metadata={"halflife": halflife},
                )

    # --------------------------------------------------------
    # SECTION 19.12 - CONTEXT FEATURES
    # --------------------------------------------------------

    def _add_context_features(
        self,
        features: MutableRecord,
        current: Mapping[str, Any],
        context: Mapping[str, Any],
        lineage: MutableMapping[str, FeatureLineage],
        as_of: datetime,
    ) -> None:
        merged = dict(current)
        merged.update(context)

        for field_name in self.config.context_numeric_fields:
            value = merged.get(field_name)
            if is_missing(value):
                continue
            feature_name = f"context_{field_name}"
            features[feature_name] = to_float(value)
            lineage[feature_name] = FeatureLineage(
                feature_name=feature_name,
                source_fields=(field_name,),
                operation="context_identity",
                as_of=as_of,
                history_count=0,
            )

        for field_name in self.config.categorical_fields:
            if field_name in merged:
                features.update(self.encoder.encode_scalar(field_name, merged.get(field_name)))

        home_away = normalize_name(merged.get("home_away"))
        features["context_is_home"] = float(home_away in {"home", "h"})
        features["context_is_away"] = float(home_away in {"away", "a"})

        day_night = normalize_name(merged.get("day_night"))
        features["context_is_day_game"] = float(day_night == "day")
        features["context_is_night_game"] = float(day_night == "night")

        wind = to_float(merged.get("wind_speed_mph"))
        wind_direction = to_float(merged.get("wind_direction_degrees"))
        if wind and wind_direction:
            radians = math.radians(wind_direction)
            features["context_wind_x"] = wind * math.cos(radians)
            features["context_wind_y"] = wind * math.sin(radians)

    # --------------------------------------------------------
    # SECTION 19.13 - SPLIT FEATURES
    # --------------------------------------------------------

    def _add_split_features(
        self,
        features: MutableRecord,
        history: Sequence[Mapping[str, Any]],
        current: Mapping[str, Any],
        lineage: MutableMapping[str, FeatureLineage],
        as_of: datetime,
    ) -> None:
        split_definitions = {
            "home": lambda row: normalize_name(row.get("home_away")) in {"home", "h"},
            "away": lambda row: normalize_name(row.get("home_away")) in {"away", "a"},
            "vs_lhp": lambda row: normalize_name(row.get("pitcher_throws")) in {"l", "left"},
            "vs_rhp": lambda row: normalize_name(row.get("pitcher_throws")) in {"r", "right"},
            "day": lambda row: normalize_name(row.get("day_night")) == "day",
            "night": lambda row: normalize_name(row.get("day_night")) == "night",
        }

        for split_name, predicate in split_definitions.items():
            records = [item for item in history if predicate(item)]
            if not records:
                features[f"split_{split_name}_games"] = 0.0
                continue
            totals = self._totals(records)
            features[f"split_{split_name}_games"] = float(len(records))
            features[f"split_{split_name}_avg"] = safe_divide(
                totals.get("hits"), totals.get("at_bats")
            )
            features[f"split_{split_name}_obp"] = safe_divide(
                totals.get("hits", 0.0) + totals.get("walks", 0.0) + totals.get("hit_by_pitch", 0.0),
                totals.get("at_bats", 0.0) + totals.get("walks", 0.0)
                + totals.get("hit_by_pitch", 0.0) + totals.get("sacrifice_flies", 0.0),
            )
            features[f"split_{split_name}_hr_rate"] = safe_divide(
                totals.get("home_runs"), totals.get("plate_appearances")
            )
            features[f"split_{split_name}_k_rate"] = safe_divide(
                totals.get("strikeouts"), totals.get("plate_appearances")
            )

        current_pitcher_side = normalize_name(current.get("pitcher_throws"))
        if current_pitcher_side in {"l", "left"}:
            features["active_hand_split_avg"] = features.get("split_vs_lhp_avg", 0.0)
            features["active_hand_split_hr_rate"] = features.get("split_vs_lhp_hr_rate", 0.0)
        elif current_pitcher_side in {"r", "right"}:
            features["active_hand_split_avg"] = features.get("split_vs_rhp_avg", 0.0)
            features["active_hand_split_hr_rate"] = features.get("split_vs_rhp_hr_rate", 0.0)

    # --------------------------------------------------------
    # SECTION 19.14 - OPPONENT FEATURES
    # --------------------------------------------------------

    def _add_opponent_features(
        self,
        features: MutableRecord,
        history: Sequence[Mapping[str, Any]],
        lineage: MutableMapping[str, FeatureLineage],
        as_of: datetime,
    ) -> None:
        features["opponent_history_count"] = float(len(history))
        if not history:
            return

        totals = self._totals(history)
        features["opponent_avg"] = safe_divide(totals.get("hits"), totals.get("at_bats"))
        features["opponent_hr_rate"] = safe_divide(
            totals.get("home_runs"), totals.get("plate_appearances")
        )
        features["opponent_k_rate"] = safe_divide(
            totals.get("strikeouts"), totals.get("plate_appearances")
        )
        features["opponent_walk_rate"] = safe_divide(
            totals.get("walks"), totals.get("plate_appearances")
        )
        features["opponent_runs_per_game"] = safe_divide(totals.get("runs"), len(history))

    # --------------------------------------------------------
    # SECTION 19.15 - TEAM FEATURES
    # --------------------------------------------------------

    def _add_team_features(
        self,
        features: MutableRecord,
        history: Sequence[Mapping[str, Any]],
        lineage: MutableMapping[str, FeatureLineage],
        as_of: datetime,
    ) -> None:
        features["team_history_count"] = float(len(history))
        if not history:
            return

        totals = self._totals(history)
        games = max(len(history), 1)
        features["team_runs_per_game"] = safe_divide(totals.get("team_runs", totals.get("runs")), games)
        features["team_runs_allowed_per_game"] = safe_divide(
            totals.get("team_runs_allowed", totals.get("runs_allowed")), games
        )
        features["team_run_differential_per_game"] = (
            features["team_runs_per_game"] - features["team_runs_allowed_per_game"]
        )
        wins = totals.get("wins", 0.0)
        losses = totals.get("losses", 0.0)
        features["team_win_percentage"] = safe_divide(wins, wins + losses, default=0.5)
        features["team_pythagorean_expectation"] = safe_divide(
            features["team_runs_per_game"] ** 1.83,
            features["team_runs_per_game"] ** 1.83
            + features["team_runs_allowed_per_game"] ** 1.83,
            default=0.5,
        )

    # --------------------------------------------------------
    # SECTION 19.16 - INTERACTION FEATURES
    # --------------------------------------------------------

    def _add_interaction_features(self, features: MutableRecord) -> None:
        features["interaction_ops_park"] = (
            to_float(features.get("career_ops"))
            * to_float(features.get("context_park_factor"), 1.0)
        )
        features["interaction_hr_rate_hr_park"] = (
            to_float(features.get("career_home_run_rate"))
            * to_float(features.get("context_hr_park_factor"), 1.0)
        )
        features["interaction_rest_form"] = (
            to_float(features.get("context_rest_days"))
            * to_float(features.get("hits_ewm_hl_3_0"))
        )
        features["interaction_travel_fatigue"] = (
            log1p_safe(features.get("context_travel_miles"))
            * max(0.0, 2.0 - to_float(features.get("context_rest_days")))
        )
        features["interaction_platoon_advantage"] = self._platoon_advantage(features)
        features["interaction_form_delta_hits"] = (
            to_float(features.get("hits_last_5_mean"))
            - to_float(features.get("hits_last_30_mean"))
        )
        features["interaction_form_delta_hr"] = (
            to_float(features.get("home_runs_last_5_mean"))
            - to_float(features.get("home_runs_last_30_mean"))
        )
        features["interaction_offense_vs_opponent"] = (
            to_float(features.get("career_ops"))
            - to_float(features.get("opponent_k_rate"))
            + to_float(features.get("opponent_walk_rate"))
        )

    @staticmethod
    def _platoon_advantage(features: Mapping[str, Any]) -> float:
        batter_left = to_float(features.get("batter_side__hash")) == to_float(
            stable_hash("batter_side:left")
        )
        pitcher_left = to_float(features.get("pitcher_throws__hash")) == to_float(
            stable_hash("pitcher_throws:left")
        )
        if batter_left and not pitcher_left:
            return 1.0
        if not batter_left and pitcher_left:
            return 1.0
        return 0.0

    # --------------------------------------------------------
    # SECTION 19.17 - UNCERTAINTY FEATURES
    # --------------------------------------------------------

    def _add_uncertainty_features(
        self,
        features: MutableRecord,
        history: Sequence[Mapping[str, Any]],
    ) -> None:
        games = len(history)
        plate_appearances = sum(to_float(item.get("plate_appearances")) for item in history)
        sample_reliability = 1.0 - math.exp(-plate_appearances / 100.0)
        features["uncertainty_sample_reliability"] = clamp(sample_reliability, 0.0, 1.0)
        features["uncertainty_small_sample"] = float(plate_appearances < 50)
        features["uncertainty_no_history"] = float(games == 0)

        hit_values = [to_float(item.get("hits")) for item in history]
        hr_values = [to_float(item.get("home_runs")) for item in history]
        features["uncertainty_hits_volatility"] = population_std(hit_values)
        features["uncertainty_hr_volatility"] = population_std(hr_values)
        features["uncertainty_completeness"] = self._completeness_score(history)

    # --------------------------------------------------------
    # SECTION 19.18 - MISSINGNESS FEATURES
    # --------------------------------------------------------

    def _add_missing_indicators(self, features: MutableRecord) -> None:
        original = list(features.items())
        missing_count = 0
        for key, value in original:
            missing = float(is_missing(value))
            if missing:
                missing_count += 1
            features[f"missing_{key}"] = missing
        features["missing_total"] = float(missing_count)
        features["missing_fraction"] = safe_divide(missing_count, len(original))

    # --------------------------------------------------------
    # SECTION 19.19 - LABEL EXTRACTION
    # --------------------------------------------------------

    def _extract_labels(self, record: Mapping[str, Any]) -> dict[str, Any]:
        labels: dict[str, Any] = {}
        for field_name in self.config.label_fields:
            if field_name in record and not is_missing(record[field_name]):
                labels[field_name] = to_float(record[field_name])

        if "target_hit" not in labels and "hits" in record:
            labels["target_hit"] = float(to_float(record.get("hits")) > 0)
        if "target_home_run" not in labels and "home_runs" in record:
            labels["target_home_run"] = float(to_float(record.get("home_runs")) > 0)
        if "target_single" not in labels and "singles" in record:
            labels["target_single"] = float(to_float(record.get("singles")) > 0)
        if "target_double" not in labels and "doubles" in record:
            labels["target_double"] = float(to_float(record.get("doubles")) > 0)
        if "target_triple" not in labels and "triples" in record:
            labels["target_triple"] = float(to_float(record.get("triples")) > 0)
        if "target_total_bases" not in labels and "total_bases" in record:
            labels["target_total_bases"] = to_float(record.get("total_bases"))
        return labels

    # --------------------------------------------------------
    # SECTION 19.20 - SANITIZATION
    # --------------------------------------------------------

    def _sanitize_features(self, features: Mapping[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for raw_name, raw_value in features.items():
            name = normalize_name(raw_name)
            value = raw_value

            if is_missing(value):
                if self.config.missing_strategy == MissingValueStrategy.PRESERVE:
                    sanitized[name] = None
                else:
                    sanitized[name] = self.config.missing_constant
                continue

            if isinstance(value, bool):
                sanitized[name] = float(value)
            elif isinstance(value, (int, float, Decimal)):
                numeric = to_float(value)
                numeric = clamp(
                    numeric,
                    -10 ** self.config.clip_zscore,
                    10 ** self.config.clip_zscore,
                )
                sanitized[name] = round(numeric, self.config.float_precision)
            elif isinstance(value, (datetime, date)):
                sanitized[name] = value.isoformat()
            elif isinstance(value, Enum):
                sanitized[name] = value.value
            else:
                sanitized[name] = str(value)

        return self.imputer.transform(sanitized)

    # --------------------------------------------------------
    # SECTION 19.21 - HELPERS
    # --------------------------------------------------------

    @staticmethod
    def _totals(records: Sequence[Mapping[str, Any]]) -> dict[str, float]:
        totals: dict[str, float] = defaultdict(float)
        for record in records:
            for key, value in record.items():
                if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
                    totals[key] += to_float(value)
        return dict(totals)

    @staticmethod
    def _completeness_score(records: Sequence[Mapping[str, Any]]) -> float:
        if not records:
            return 0.0
        fields = set().union(*(record.keys() for record in records))
        if not fields:
            return 0.0
        observed = sum(
            1 for record in records for field_name in fields
            if not is_missing(record.get(field_name))
        )
        return safe_divide(observed, len(records) * len(fields))

    @staticmethod
    def _resolve_as_of(
        value: datetime | date | str | None,
        current: Mapping[str, Any],
    ) -> datetime:
        parsed = parse_datetime(value)
        if parsed is not None:
            return parsed
        inferred = parse_datetime(first_present(current, TIMESTAMP_CANDIDATES))
        return inferred or utc_now()

    @staticmethod
    def _identity_key(record: Mapping[str, Any]) -> tuple[Any, Any]:
        return (
            first_present(record, GAME_ID_CANDIDATES),
            first_present(record, PLAYER_ID_CANDIDATES),
        )

    def _lookup_by_identity(
        self,
        records: Sequence[Mapping[str, Any]],
    ) -> dict[tuple[Any, Any], Mapping[str, Any]]:
        return {self._identity_key(record): record for record in records}

    def config_hash(self) -> str:
        return fingerprint(asdict(self.config))

    def manifest(self, vectors: Sequence[FeatureVector]) -> FeatureManifest:
        feature_names = sorted({name for vector in vectors for name in vector.values})
        label_names = sorted({name for vector in vectors for name in vector.labels})
        return FeatureManifest(
            module_version=MODULE_VERSION,
            created_at=utc_now(),
            prediction_unit=self.config.prediction_unit,
            mode=self.config.mode,
            feature_names=feature_names,
            label_names=label_names,
            schema_hash=fingerprint(feature_names),
            config_hash=self.config_hash(),
        )


# ============================================================
# SECTION 20 - SPECIALIZED PLAYER FEATURE BUILDER
# ============================================================

class PlayerFeatureBuilder(FeatureBuilder):
    """Convenience builder for player-game projection features."""

    def __init__(self, config: FeatureBuilderConfig | None = None) -> None:
        effective = config or FeatureBuilderConfig(
            prediction_unit=PredictionUnit.PLAYER_GAME
        )
        super().__init__(effective)


# ============================================================
# SECTION 21 - SPECIALIZED MATCHUP FEATURE BUILDER
# ============================================================

class MatchupFeatureBuilder(FeatureBuilder):
    """Build batter-versus-pitcher matchup features."""

    def build_matchup(
        self,
        *,
        batter: Any,
        pitcher: Any,
        batter_history: Any = None,
        pitcher_history: Any = None,
        matchup_history: Any = None,
        as_of: datetime | date | str | None = None,
        context: Any = None,
        labels: Any = None,
    ) -> FeatureVector:
        batter_record = self.normalizer.normalize(batter)
        pitcher_record = self.normalizer.normalize(pitcher)
        merged = dict(batter_record)

        for key, value in pitcher_record.items():
            merged[f"pitcher_{key}" if not key.startswith("pitcher_") else key] = value

        vector = self.build(
            current=merged,
            history=batter_history,
            opponent_history=pitcher_history,
            as_of=as_of,
            context=context,
            labels=labels,
        )

        matchup_records = self.normalizer.normalize_many(matchup_history)
        matchup_records, issues = self.temporal_guard.filter(matchup_records, vector.as_of)
        totals = self._totals(matchup_records)

        vector.values.update({
            "matchup_plate_appearances": totals.get("plate_appearances", 0.0),
            "matchup_hits": totals.get("hits", 0.0),
            "matchup_home_runs": totals.get("home_runs", 0.0),
            "matchup_walks": totals.get("walks", 0.0),
            "matchup_strikeouts": totals.get("strikeouts", 0.0),
            "matchup_average": safe_divide(totals.get("hits"), totals.get("at_bats")),
            "matchup_home_run_rate": safe_divide(
                totals.get("home_runs"), totals.get("plate_appearances")
            ),
            "matchup_walk_rate": safe_divide(
                totals.get("walks"), totals.get("plate_appearances")
            ),
            "matchup_strikeout_rate": safe_divide(
                totals.get("strikeouts"), totals.get("plate_appearances")
            ),
        })
        vector.issues.extend(issues)
        vector.prediction_unit = PredictionUnit.BATTER_PITCHER
        vector.values = self._sanitize_features(vector.values)
        vector.issues.extend(self.validator.validate_vector(vector))
        return vector.finalize()


# ============================================================
# SECTION 22 - SPECIALIZED TEAM FEATURE BUILDER
# ============================================================

class TeamFeatureBuilder(FeatureBuilder):
    """Build team-game run and win probability features."""

    def __init__(self, config: FeatureBuilderConfig | None = None) -> None:
        effective = config or FeatureBuilderConfig(
            prediction_unit=PredictionUnit.TEAM_GAME
        )
        super().__init__(effective)

    def build_team_game(
        self,
        *,
        team: Any,
        opponent: Any,
        team_history: Any,
        opponent_history: Any,
        as_of: datetime | date | str | None = None,
        context: Any = None,
        labels: Any = None,
    ) -> FeatureVector:
        team_record = self.normalizer.normalize(team)
        opponent_record = self.normalizer.normalize(opponent)

        merged = dict(team_record)
        for key, value in opponent_record.items():
            merged[f"opponent_{key}"] = value

        return self.build(
            current=merged,
            history=team_history,
            opponent_history=opponent_history,
            team_history=team_history,
            as_of=as_of,
            context=context,
            labels=labels,
        )


# ============================================================
# SECTION 23 - FEATURE MATRIX UTILITIES
# ============================================================

def align_feature_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    fill_value: float = 0.0,
    ordered_columns: Sequence[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    columns = list(ordered_columns or sorted({key for row in rows for key in row}))
    aligned = [
        {column: row.get(column, fill_value) for column in columns}
        for row in rows
    ]
    return aligned, columns


def feature_matrix(
    vectors: Sequence[FeatureVector],
    *,
    columns: Sequence[str] | None = None,
) -> tuple[Any, list[str]]:
    rows, ordered = align_feature_rows(
        [vector.values for vector in vectors],
        ordered_columns=columns,
    )
    if np is None:
        return [[to_float(row[column]) for column in ordered] for row in rows], ordered
    matrix = np.asarray(
        [[to_float(row[column]) for column in ordered] for row in rows],
        dtype=float,
    )
    return matrix, ordered


def label_matrix(
    vectors: Sequence[FeatureVector],
    label_names: Sequence[str],
) -> Any:
    rows = [
        [to_float(vector.labels.get(name)) for name in label_names]
        for vector in vectors
    ]
    return np.asarray(rows, dtype=float) if np is not None else rows


# ============================================================
# SECTION 24 - LEAKAGE AUDITOR
# ============================================================

@dataclass(slots=True)
class LeakageAuditReport:
    safe: bool
    future_record_count: int
    suspicious_feature_names: list[str]
    issues: list[FeatureIssue]


class LeakageAuditor:
    SUSPICIOUS_PATTERNS: Final[tuple[str, ...]] = (
        "final_", "result_", "actual_", "postgame_", "post_game_",
        "target_", "winner", "game_result", "final_score",
    )

    def audit(
        self,
        *,
        records: Any,
        as_of: datetime,
        feature_names: Sequence[str] = (),
    ) -> LeakageAuditReport:
        normalized = RecordNormalizer().normalize_many(records)
        future_count = 0
        issues: list[FeatureIssue] = []

        for record in normalized:
            timestamp = parse_datetime(first_present(record, TIMESTAMP_CANDIDATES))
            if timestamp is not None and timestamp >= as_of:
                future_count += 1
                issues.append(FeatureIssue(
                    code="future_record",
                    message="Record is not temporally prior to prediction timestamp",
                    severity=FeatureSeverity.ERROR,
                    details={
                        "record_timestamp": timestamp.isoformat(),
                        "as_of": as_of.isoformat(),
                    },
                ))

        suspicious = [
            name for name in feature_names
            if any(pattern in normalize_name(name) for pattern in self.SUSPICIOUS_PATTERNS)
        ]
        for name in suspicious:
            issues.append(FeatureIssue(
                code="suspicious_feature_name",
                message=f"Potential target leakage feature detected: {name}",
                severity=FeatureSeverity.WARNING,
                field_name=name,
            ))

        return LeakageAuditReport(
            safe=future_count == 0 and not suspicious,
            future_record_count=future_count,
            suspicious_feature_names=suspicious,
            issues=issues,
        )


# ============================================================
# SECTION 25 - FEATURE DRIFT PROFILE
# ============================================================

@dataclass(slots=True)
class FeatureDistribution:
    count: int
    missing: int
    mean: float
    std: float
    minimum: float
    maximum: float
    median: float


def profile_feature_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, FeatureDistribution]:
    columns = sorted({key for row in rows for key in row})
    output: dict[str, FeatureDistribution] = {}

    for column in columns:
        raw_values = [row.get(column) for row in rows]
        missing = sum(is_missing(value) for value in raw_values)
        values = [
            to_float(value)
            for value in raw_values
            if not is_missing(value) and isinstance(value, (int, float, Decimal))
        ]
        if not values:
            continue
        output[column] = FeatureDistribution(
            count=len(values),
            missing=missing,
            mean=mean(values),
            std=population_std(values),
            minimum=min(values),
            maximum=max(values),
            median=median(values),
        )
    return output


def population_stability_index(
    expected: Sequence[Any],
    actual: Sequence[Any],
    *,
    bins: int = 10,
    epsilon: float = 1e-6,
) -> float:
    expected_values = sorted(to_float(value) for value in expected if not is_missing(value))
    actual_values = [to_float(value) for value in actual if not is_missing(value)]
    if len(expected_values) < bins or not actual_values:
        return 0.0

    boundaries = []
    for index in range(1, bins):
        position = min(int(index * len(expected_values) / bins), len(expected_values) - 1)
        boundaries.append(expected_values[position])

    def bucket_counts(values: Sequence[float]) -> list[int]:
        counts = [0] * bins
        for value in values:
            bucket = 0
            while bucket < len(boundaries) and value > boundaries[bucket]:
                bucket += 1
            counts[bucket] += 1
        return counts

    expected_counts = bucket_counts(expected_values)
    actual_counts = bucket_counts(actual_values)

    psi = 0.0
    for expected_count, actual_count in zip(expected_counts, actual_counts):
        expected_pct = max(expected_count / len(expected_values), epsilon)
        actual_pct = max(actual_count / len(actual_values), epsilon)
        psi += (actual_pct - expected_pct) * math.log(actual_pct / expected_pct)
    return float(psi)


# ============================================================
# SECTION 26 - SERIALIZATION
# ============================================================

def save_manifest(manifest: FeatureManifest, path: str) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(manifest.to_dict(), file, indent=2, sort_keys=True)


def load_manifest(path: str) -> FeatureManifest:
    with open(path, "r", encoding="utf-8") as file:
        payload = json.load(file)
    return FeatureManifest(
        module_version=payload["module_version"],
        created_at=parse_datetime(payload["created_at"]) or utc_now(),
        prediction_unit=PredictionUnit(payload["prediction_unit"]),
        mode=FeatureMode(payload["mode"]),
        feature_names=list(payload["feature_names"]),
        label_names=list(payload["label_names"]),
        schema_hash=payload["schema_hash"],
        config_hash=payload["config_hash"],
        descriptions=dict(payload.get("descriptions", {})),
    )


# ============================================================
# SECTION 27 - HEALTH AND DIAGNOSTICS
# ============================================================

def feature_builder_health() -> dict[str, Any]:
    return {
        "module": MODULE_NAME,
        "path": MODULE_PATH,
        "version": MODULE_VERSION,
        "status": MODULE_STATUS,
        "python_ready": True,
        "numpy_available": np is not None,
        "pandas_available": pd is not None,
        "supported_modes": [item.value for item in FeatureMode],
        "supported_prediction_units": [item.value for item in PredictionUnit],
        "default_rolling_windows": list(DEFAULT_ROLLING_WINDOWS),
        "default_ewm_halflives": list(DEFAULT_EWM_HALFLIVES),
        "timestamp": utc_now().isoformat(),
    }


def validate_feature_builder() -> dict[str, Any]:
    sample_current = {
        "player_id": 1,
        "team_id": 147,
        "game_id": 999,
        "game_date": "2026-07-01T19:05:00Z",
        "pitcher_throws": "R",
        "home_away": "home",
    }
    sample_history = [
        {
            "player_id": 1,
            "game_id": index,
            "game_date": f"2026-06-{index:02d}T19:05:00Z",
            "plate_appearances": 4,
            "at_bats": 4,
            "hits": index % 3,
            "home_runs": 1 if index in {3, 7} else 0,
            "walks": 0,
            "strikeouts": 1,
        }
        for index in range(1, 11)
    ]
    builder = FeatureBuilder()
    vector = builder.build(
        current=sample_current,
        history=sample_history,
        as_of="2026-07-01T19:05:00Z",
        context={"temperature_f": 82, "park_factor": 1.03},
    )
    return {
        "status": "ok",
        "feature_count": len(vector.values),
        "schema_hash": vector.schema_hash,
        "vector_hash": vector.vector_hash,
        "issue_count": len(vector.issues),
    }


# ============================================================
# SECTION 28 - PUBLIC FACTORY FUNCTIONS
# ============================================================

def create_feature_builder(
    *,
    mode: FeatureMode | str = FeatureMode.INFERENCE,
    prediction_unit: PredictionUnit | str = PredictionUnit.PLAYER_GAME,
    strict: bool = False,
    include_labels: bool = False,
    **overrides: Any,
) -> FeatureBuilder:
    resolved_mode = mode if isinstance(mode, FeatureMode) else FeatureMode(mode)
    resolved_unit = (
        prediction_unit
        if isinstance(prediction_unit, PredictionUnit)
        else PredictionUnit(prediction_unit)
    )
    config = FeatureBuilderConfig(
        mode=resolved_mode,
        prediction_unit=resolved_unit,
        strict=strict,
        include_labels=include_labels,
        **overrides,
    )
    if resolved_unit == PredictionUnit.BATTER_PITCHER:
        return MatchupFeatureBuilder(config)
    if resolved_unit == PredictionUnit.TEAM_GAME:
        return TeamFeatureBuilder(config)
    return PlayerFeatureBuilder(config)


def build_feature_vector(
    current: Any,
    history: Any = None,
    *,
    as_of: datetime | date | str | None = None,
    context: Any = None,
    config: FeatureBuilderConfig | None = None,
) -> FeatureVector:
    return FeatureBuilder(config).build(
        current=current,
        history=history,
        as_of=as_of,
        context=context,
    )


def build_feature_rows(
    rows: Any,
    *,
    history: Any = None,
    config: FeatureBuilderConfig | None = None,
) -> list[dict[str, Any]]:
    batch = FeatureBuilder(config).build_batch(rows, history=history)
    return batch.rows()


# ============================================================
# SECTION 29 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "MODULE_NAME",
    "MODULE_PATH",
    "MODULE_VERSION",
    "FeatureBuilderError",
    "FeatureConfigurationError",
    "FeatureValidationError",
    "TemporalLeakageError",
    "FeatureSchemaError",
    "FeatureMode",
    "PredictionUnit",
    "MissingValueStrategy",
    "UnknownCategoryStrategy",
    "LeakagePolicy",
    "FeatureSeverity",
    "FeatureColumnSpec",
    "RateFeatureSpec",
    "RollingFeatureSpec",
    "CategoricalFeatureSpec",
    "FeatureBuilderConfig",
    "FeatureIssue",
    "FeatureLineage",
    "FeatureVector",
    "FeatureBatch",
    "FeatureManifest",
    "RecordNormalizer",
    "TemporalGuard",
    "HistoryIndex",
    "NumericalTransformer",
    "StableCategoricalEncoder",
    "FeatureImputer",
    "FeatureValidator",
    "FeatureBuilder",
    "PlayerFeatureBuilder",
    "MatchupFeatureBuilder",
    "TeamFeatureBuilder",
    "LeakageAuditReport",
    "LeakageAuditor",
    "FeatureDistribution",
    "align_feature_rows",
    "feature_matrix",
    "label_matrix",
    "profile_feature_rows",
    "population_stability_index",
    "save_manifest",
    "load_manifest",
    "feature_builder_health",
    "validate_feature_builder",
    "create_feature_builder",
    "build_feature_vector",
    "build_feature_rows",
    "safe_divide",
    "stable_hash",
    "parse_datetime",
    "records_from_any",
    "fingerprint",
]
