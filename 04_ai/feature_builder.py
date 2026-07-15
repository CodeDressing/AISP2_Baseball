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

from collections import Counter, defaultdict, deque, OrderedDict
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from decimal import Decimal, InvalidOperation
from enum import Enum
from hashlib import sha256
import json
import logging
import math
import re
import statistics
from typing import Any, Final, Generic, Protocol, TypeVar, Callable, Iterator

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
MODULE_PATH: Final[str] = "04_ai/feature_builder.py"
MODULE_VERSION: Final[str] = "6.0.0"
MODULE_STATUS: Final[str] = "enterprise_training_ready"
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
# SECTION 28.01 - TRAINING DATASET ENUMERATIONS
# ============================================================

class TargetKind(str, Enum):
    BINARY = "binary"
    COUNT = "count"
    CONTINUOUS = "continuous"
    MULTICLASS = "multiclass"


class DatasetSplitName(str, Enum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"
    HOLDOUT = "holdout"


class SplitStrategy(str, Enum):
    CHRONOLOGICAL = "chronological"
    EXPANDING_WINDOW = "expanding_window"
    ROLLING_ORIGIN = "rolling_origin"
    SEASON_HOLDOUT = "season_holdout"


class ScalingStrategy(str, Enum):
    NONE = "none"
    STANDARD = "standard"
    ROBUST = "robust"
    MIN_MAX = "min_max"


class FeatureSelectionStrategy(str, Enum):
    NONE = "none"
    VARIANCE = "variance"
    CORRELATION = "correlation"
    MISSINGNESS = "missingness"
    COMBINED = "combined"


class DataQualityStatus(str, Enum):
    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class OutcomeFamily(str, Enum):
    PLAYER_BATTING = "player_batting"
    PLAYER_PITCHING = "player_pitching"
    TEAM_GAME = "team_game"
    PLATE_APPEARANCE = "plate_appearance"


# ============================================================
# SECTION 28.02 - OUTCOME TARGET REGISTRY
# ============================================================

@dataclass(frozen=True, slots=True)
class TargetDefinition:
    name: str
    kind: TargetKind
    family: OutcomeFamily
    source_field: str
    threshold: float | None = None
    positive_when: str = "greater_than_or_equal"
    description: str = ""
    minimum_history_rows: int = 1
    include_in_default_training: bool = True

    def derive(self, record: Mapping[str, Any]) -> float | int | str | None:
        raw = record.get(self.source_field)

        if is_missing(raw):
            return None

        if self.kind == TargetKind.BINARY:
            numeric = to_float(raw)

            threshold = (
                self.threshold
                if self.threshold is not None
                else 1.0
            )

            if self.positive_when == "greater_than":
                return float(numeric > threshold)

            if self.positive_when == "equal":
                return float(numeric == threshold)

            return float(
                numeric >= threshold
            )

        if self.kind == TargetKind.COUNT:
            return max(
                0,
                to_int(raw),
            )

        if self.kind == TargetKind.CONTINUOUS:
            return to_float(raw)

        return str(raw)


TARGET_REGISTRY: Final[
    dict[str, TargetDefinition]
] = {
    "target_hit": TargetDefinition(
        name="target_hit",
        kind=TargetKind.BINARY,
        family=OutcomeFamily.PLAYER_BATTING,
        source_field="hits",
        threshold=1.0,
        description=(
            "Player records at least one hit in the game."
        ),
    ),
    "target_single": TargetDefinition(
        name="target_single",
        kind=TargetKind.BINARY,
        family=OutcomeFamily.PLAYER_BATTING,
        source_field="singles",
        threshold=1.0,
        description=(
            "Player records at least one single."
        ),
    ),
    "target_double": TargetDefinition(
        name="target_double",
        kind=TargetKind.BINARY,
        family=OutcomeFamily.PLAYER_BATTING,
        source_field="doubles",
        threshold=1.0,
        description=(
            "Player records at least one double."
        ),
    ),
    "target_triple": TargetDefinition(
        name="target_triple",
        kind=TargetKind.BINARY,
        family=OutcomeFamily.PLAYER_BATTING,
        source_field="triples",
        threshold=1.0,
        description=(
            "Player records at least one triple."
        ),
    ),
    "target_home_run": TargetDefinition(
        name="target_home_run",
        kind=TargetKind.BINARY,
        family=OutcomeFamily.PLAYER_BATTING,
        source_field="home_runs",
        threshold=1.0,
        description=(
            "Player records at least one home run."
        ),
    ),
    "target_walk": TargetDefinition(
        name="target_walk",
        kind=TargetKind.BINARY,
        family=OutcomeFamily.PLAYER_BATTING,
        source_field="walks",
        threshold=1.0,
        description=(
            "Player records at least one walk."
        ),
    ),
    "target_strikeout": TargetDefinition(
        name="target_strikeout",
        kind=TargetKind.BINARY,
        family=OutcomeFamily.PLAYER_BATTING,
        source_field="strikeouts",
        threshold=1.0,
        description=(
            "Player strikes out at least once."
        ),
    ),
    "target_rbi": TargetDefinition(
        name="target_rbi",
        kind=TargetKind.BINARY,
        family=OutcomeFamily.PLAYER_BATTING,
        source_field="rbi",
        threshold=1.0,
        description=(
            "Player records at least one run batted in."
        ),
    ),
    "target_run": TargetDefinition(
        name="target_run",
        kind=TargetKind.BINARY,
        family=OutcomeFamily.PLAYER_BATTING,
        source_field="runs",
        threshold=1.0,
        description=(
            "Player scores at least one run."
        ),
    ),
    "target_total_bases": TargetDefinition(
        name="target_total_bases",
        kind=TargetKind.COUNT,
        family=OutcomeFamily.PLAYER_BATTING,
        source_field="total_bases",
        description=(
            "Player total bases recorded in the game."
        ),
    ),
    "target_hits_count": TargetDefinition(
        name="target_hits_count",
        kind=TargetKind.COUNT,
        family=OutcomeFamily.PLAYER_BATTING,
        source_field="hits",
        description=(
            "Number of hits recorded by the player."
        ),
    ),
    "target_home_runs_count": TargetDefinition(
        name="target_home_runs_count",
        kind=TargetKind.COUNT,
        family=OutcomeFamily.PLAYER_BATTING,
        source_field="home_runs",
        description=(
            "Number of home runs recorded by the player."
        ),
    ),
    "target_pitcher_strikeouts": TargetDefinition(
        name="target_pitcher_strikeouts",
        kind=TargetKind.COUNT,
        family=OutcomeFamily.PLAYER_PITCHING,
        source_field="pitcher_strikeouts",
        description=(
            "Pitcher strikeout count."
        ),
    ),
    "target_pitcher_walks": TargetDefinition(
        name="target_pitcher_walks",
        kind=TargetKind.COUNT,
        family=OutcomeFamily.PLAYER_PITCHING,
        source_field="pitcher_walks",
        description=(
            "Pitcher walks allowed."
        ),
    ),
    "target_pitcher_earned_runs": TargetDefinition(
        name="target_pitcher_earned_runs",
        kind=TargetKind.COUNT,
        family=OutcomeFamily.PLAYER_PITCHING,
        source_field="earned_runs",
        description=(
            "Pitcher earned runs allowed."
        ),
    ),
    "target_team_win": TargetDefinition(
        name="target_team_win",
        kind=TargetKind.BINARY,
        family=OutcomeFamily.TEAM_GAME,
        source_field="team_win",
        threshold=1.0,
        description=(
            "Team wins the game."
        ),
    ),
    "target_team_runs": TargetDefinition(
        name="target_team_runs",
        kind=TargetKind.COUNT,
        family=OutcomeFamily.TEAM_GAME,
        source_field="team_runs",
        description=(
            "Team runs scored."
        ),
    ),
    "target_game_total_runs": TargetDefinition(
        name="target_game_total_runs",
        kind=TargetKind.COUNT,
        family=OutcomeFamily.TEAM_GAME,
        source_field="game_total_runs",
        description=(
            "Combined runs scored by both teams."
        ),
    ),
}


# ============================================================
# SECTION 28.03 - TRAINING CONFIGURATION
# ============================================================

@dataclass(slots=True)
class TrainingDatasetConfig:
    target_names: tuple[str, ...] = (
        "target_hit",
        "target_home_run",
        "target_walk",
        "target_strikeout",
        "target_rbi",
        "target_total_bases",
    )

    split_strategy: SplitStrategy = (
        SplitStrategy.CHRONOLOGICAL
    )

    train_fraction: float = 0.70
    validation_fraction: float = 0.15
    test_fraction: float = 0.15

    minimum_rows: int = 100
    minimum_positive_rows: int = 25
    minimum_negative_rows: int = 25

    entity_field: str = "player_id"
    game_field: str = "game_id"
    timestamp_field: str = "game_date"
    season_field: str = "season"

    holdout_season: int | None = None
    validation_season: int | None = None

    scaling_strategy: ScalingStrategy = (
        ScalingStrategy.STANDARD
    )

    feature_selection_strategy: (
        FeatureSelectionStrategy
    ) = FeatureSelectionStrategy.COMBINED

    variance_threshold: float = 1e-12
    correlation_threshold: float = 0.999
    maximum_missing_fraction: float = 0.98

    include_identifiers_in_matrix: bool = False
    allow_empty_validation: bool = False
    allow_empty_test: bool = False
    require_monotonic_time: bool = True
    require_unique_entity_game_rows: bool = True

    random_seed: int = 42

    artifact_directory: str = (
        "artifacts/training_datasets"
    )

    def validate(self) -> None:
        if not self.target_names:
            raise FeatureConfigurationError(
                "At least one target is required"
            )

        unknown = [
            name
            for name in self.target_names
            if name not in TARGET_REGISTRY
        ]

        if unknown:
            raise FeatureConfigurationError(
                "Unknown targets: "
                + ", ".join(unknown)
            )

        fractions = (
            self.train_fraction
            + self.validation_fraction
            + self.test_fraction
        )

        if abs(fractions - 1.0) > 1e-9:
            raise FeatureConfigurationError(
                "Train, validation, and test fractions "
                "must sum to 1.0"
            )

        if min(
            self.train_fraction,
            self.validation_fraction,
            self.test_fraction,
        ) < 0:
            raise FeatureConfigurationError(
                "Dataset split fractions cannot be negative"
            )

        if self.minimum_rows < 1:
            raise FeatureConfigurationError(
                "minimum_rows must be positive"
            )

        if self.minimum_positive_rows < 0:
            raise FeatureConfigurationError(
                "minimum_positive_rows cannot be negative"
            )

        if self.minimum_negative_rows < 0:
            raise FeatureConfigurationError(
                "minimum_negative_rows cannot be negative"
            )

        if not 0.0 <= self.maximum_missing_fraction <= 1.0:
            raise FeatureConfigurationError(
                "maximum_missing_fraction must be between "
                "zero and one"
            )

        if not 0.0 <= self.correlation_threshold <= 1.0:
            raise FeatureConfigurationError(
                "correlation_threshold must be between zero "
                "and one"
            )


# ============================================================
# SECTION 28.04 - DATASET CONTRACTS
# ============================================================

@dataclass(slots=True)
class DatasetRow:
    features: dict[str, Any]
    labels: dict[str, Any]
    entity_id: Any
    game_id: Any
    timestamp: datetime
    season: int
    source_index: int
    vector_hash: str
    schema_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "features": self.features,
            "labels": self.labels,
            "entity_id": self.entity_id,
            "game_id": self.game_id,
            "timestamp": (
                self.timestamp.isoformat()
            ),
            "season": self.season,
            "source_index": self.source_index,
            "vector_hash": self.vector_hash,
            "schema_hash": self.schema_hash,
        }


@dataclass(slots=True)
class DatasetSplit:
    name: DatasetSplitName
    rows: list[DatasetRow]

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def start_timestamp(self) -> datetime | None:
        if not self.rows:
            return None

        return min(
            row.timestamp
            for row in self.rows
        )

    @property
    def end_timestamp(self) -> datetime | None:
        if not self.rows:
            return None

        return max(
            row.timestamp
            for row in self.rows
        )

    def to_dict(
        self,
        *,
        include_rows: bool = False,
    ) -> dict[str, Any]:
        payload = {
            "name": self.name.value,
            "row_count": self.row_count,
            "start_timestamp": (
                self.start_timestamp.isoformat()
                if self.start_timestamp
                else None
            ),
            "end_timestamp": (
                self.end_timestamp.isoformat()
                if self.end_timestamp
                else None
            ),
        }

        if include_rows:
            payload["rows"] = [
                row.to_dict()
                for row in self.rows
            ]

        return payload


@dataclass(slots=True)
class TargetBalance:
    target_name: str
    target_kind: TargetKind
    row_count: int
    missing_count: int
    positive_count: int | None
    negative_count: int | None
    mean: float | None
    minimum: float | None
    maximum: float | None
    ready: bool
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["target_kind"] = (
            self.target_kind.value
        )
        return payload


@dataclass(slots=True)
class FeatureQualityMetric:
    feature_name: str
    row_count: int
    missing_count: int
    missing_fraction: float
    unique_count: int
    variance: float
    minimum: float | None
    maximum: float | None
    mean: float | None
    standard_deviation: float | None
    constant: bool
    all_missing: bool
    recommended: bool
    exclusion_reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DatasetQualityReport:
    status: DataQualityStatus
    row_count: int
    feature_count: int
    target_count: int

    duplicate_identity_rows: int
    non_monotonic_rows: int
    schema_mismatch_rows: int
    leakage_issue_count: int

    feature_metrics: dict[
        str,
        FeatureQualityMetric,
    ]

    target_balances: dict[
        str,
        TargetBalance,
    ]

    selected_features: list[str]
    excluded_features: dict[
        str,
        list[str],
    ]

    warnings: list[str]
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "row_count": self.row_count,
            "feature_count": self.feature_count,
            "target_count": self.target_count,
            "duplicate_identity_rows": (
                self.duplicate_identity_rows
            ),
            "non_monotonic_rows": (
                self.non_monotonic_rows
            ),
            "schema_mismatch_rows": (
                self.schema_mismatch_rows
            ),
            "leakage_issue_count": (
                self.leakage_issue_count
            ),
            "feature_metrics": {
                name: metric.to_dict()
                for name, metric
                in self.feature_metrics.items()
            },
            "target_balances": {
                name: balance.to_dict()
                for name, balance
                in self.target_balances.items()
            },
            "selected_features": (
                self.selected_features
            ),
            "excluded_features": (
                self.excluded_features
            ),
            "warnings": self.warnings,
            "errors": self.errors,
        }


@dataclass(slots=True)
class TrainingDatasetManifest:
    dataset_id: str
    created_at: datetime
    module_version: str
    config_hash: str
    schema_hash: str
    row_count: int
    feature_names: list[str]
    target_names: list[str]
    split_strategy: SplitStrategy
    split_summary: dict[str, Any]
    quality_status: DataQualityStatus
    source_fingerprint: str
    dataset_fingerprint: str
    temporal_start: datetime | None
    temporal_end: datetime | None
    seasons: list[int]
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "created_at": (
                self.created_at.isoformat()
            ),
            "module_version": (
                self.module_version
            ),
            "config_hash": self.config_hash,
            "schema_hash": self.schema_hash,
            "row_count": self.row_count,
            "feature_names": (
                self.feature_names
            ),
            "target_names": (
                self.target_names
            ),
            "split_strategy": (
                self.split_strategy.value
            ),
            "split_summary": (
                self.split_summary
            ),
            "quality_status": (
                self.quality_status.value
            ),
            "source_fingerprint": (
                self.source_fingerprint
            ),
            "dataset_fingerprint": (
                self.dataset_fingerprint
            ),
            "temporal_start": (
                self.temporal_start.isoformat()
                if self.temporal_start
                else None
            ),
            "temporal_end": (
                self.temporal_end.isoformat()
                if self.temporal_end
                else None
            ),
            "seasons": self.seasons,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class TrainingDataset:
    rows: list[DatasetRow]
    splits: dict[
        DatasetSplitName,
        DatasetSplit,
    ]
    quality: DatasetQualityReport
    manifest: TrainingDatasetManifest
    feature_scaler: "DeterministicFeatureScaler"
    selected_features: list[str]

    def to_dict(
        self,
        *,
        include_rows: bool = False,
    ) -> dict[str, Any]:
        return {
            "manifest": (
                self.manifest.to_dict()
            ),
            "quality": (
                self.quality.to_dict()
            ),
            "splits": {
                name.value: split.to_dict(
                    include_rows=include_rows
                )
                for name, split
                in self.splits.items()
            },
            "selected_features": (
                self.selected_features
            ),
            "feature_scaler": (
                self.feature_scaler.to_dict()
            ),
        }


# ============================================================
# SECTION 28.05 - TARGET DERIVATION ENGINE
# ============================================================

class TargetDeriver:
    def __init__(
        self,
        target_names: Sequence[str],
    ) -> None:
        unknown = [
            name
            for name in target_names
            if name not in TARGET_REGISTRY
        ]

        if unknown:
            raise FeatureConfigurationError(
                "Unknown target definitions: "
                + ", ".join(unknown)
            )

        self.target_names = tuple(
            target_names
        )

    def derive(
        self,
        record: Mapping[str, Any],
    ) -> dict[str, Any]:
        normalized = (
            RecordNormalizer().normalize(
                record
            )
        )

        labels = {}

        for target_name in self.target_names:
            definition = TARGET_REGISTRY[
                target_name
            ]

            value = definition.derive(
                normalized
            )

            if value is not None:
                labels[target_name] = value

        return labels

    def validate_label_set(
        self,
        labels: Mapping[str, Any],
    ) -> list[str]:
        errors = []

        for target_name in self.target_names:
            if target_name not in labels:
                errors.append(
                    f"Missing label {target_name}"
                )

        return errors


# ============================================================
# SECTION 28.06 - DETERMINISTIC FEATURE SCALER
# ============================================================

@dataclass(slots=True)
class ScalingStatistic:
    feature_name: str
    center: float
    scale: float
    minimum: float
    maximum: float
    strategy: ScalingStrategy

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["strategy"] = (
            self.strategy.value
        )
        return payload


class DeterministicFeatureScaler:
    def __init__(
        self,
        strategy: ScalingStrategy = (
            ScalingStrategy.STANDARD
        ),
    ) -> None:
        self.strategy = strategy
        self.statistics_: dict[
            str,
            ScalingStatistic,
        ] = {}
        self.fitted_: bool = False

    def fit(
        self,
        rows: Sequence[
            Mapping[str, Any]
        ],
        feature_names: Sequence[str],
    ) -> "DeterministicFeatureScaler":
        self.statistics_.clear()

        for feature_name in feature_names:
            values = [
                to_float(
                    row.get(feature_name)
                )
                for row in rows
                if not is_missing(
                    row.get(feature_name)
                )
            ]

            if not values:
                values = [0.0]

            minimum = min(values)
            maximum = max(values)

            if (
                self.strategy
                == ScalingStrategy.STANDARD
            ):
                center = mean(values)
                scale = population_std(
                    values,
                    default=1.0,
                )

            elif (
                self.strategy
                == ScalingStrategy.ROBUST
            ):
                center = median(values)

                sorted_values = sorted(values)

                q1_index = int(
                    0.25
                    * (
                        len(sorted_values)
                        - 1
                    )
                )
                q3_index = int(
                    0.75
                    * (
                        len(sorted_values)
                        - 1
                    )
                )

                scale = (
                    sorted_values[q3_index]
                    - sorted_values[q1_index]
                )

            elif (
                self.strategy
                == ScalingStrategy.MIN_MAX
            ):
                center = minimum
                scale = maximum - minimum

            else:
                center = 0.0
                scale = 1.0

            if abs(scale) <= 1e-12:
                scale = 1.0

            self.statistics_[
                feature_name
            ] = ScalingStatistic(
                feature_name=feature_name,
                center=center,
                scale=scale,
                minimum=minimum,
                maximum=maximum,
                strategy=self.strategy,
            )

        self.fitted_ = True

        return self

    def transform_row(
        self,
        row: Mapping[str, Any],
        feature_names: Sequence[str],
    ) -> dict[str, float]:
        if not self.fitted_:
            raise FeatureBuilderError(
                "Feature scaler has not been fitted"
            )

        transformed = {}

        for feature_name in feature_names:
            value = to_float(
                row.get(feature_name)
            )

            statistic = self.statistics_[
                feature_name
            ]

            if (
                self.strategy
                == ScalingStrategy.NONE
            ):
                transformed[
                    feature_name
                ] = value

            else:
                transformed[
                    feature_name
                ] = (
                    value
                    - statistic.center
                ) / statistic.scale

        return transformed

    def transform_rows(
        self,
        rows: Sequence[
            Mapping[str, Any]
        ],
        feature_names: Sequence[str],
    ) -> list[dict[str, float]]:
        return [
            self.transform_row(
                row,
                feature_names,
            )
            for row in rows
        ]

    def fit_transform(
        self,
        rows: Sequence[
            Mapping[str, Any]
        ],
        feature_names: Sequence[str],
    ) -> list[dict[str, float]]:
        self.fit(
            rows,
            feature_names,
        )

        return self.transform_rows(
            rows,
            feature_names,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "fitted": self.fitted_,
            "statistics": {
                name: statistic.to_dict()
                for name, statistic
                in self.statistics_.items()
            },
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "DeterministicFeatureScaler":
        instance = cls(
            ScalingStrategy(
                payload.get(
                    "strategy",
                    ScalingStrategy.NONE.value,
                )
            )
        )

        for name, raw in dict(
            payload.get(
                "statistics",
                {},
            )
        ).items():
            instance.statistics_[
                name
            ] = ScalingStatistic(
                feature_name=name,
                center=to_float(
                    raw.get("center")
                ),
                scale=to_float(
                    raw.get("scale"),
                    1.0,
                ),
                minimum=to_float(
                    raw.get("minimum")
                ),
                maximum=to_float(
                    raw.get("maximum")
                ),
                strategy=ScalingStrategy(
                    raw.get(
                        "strategy",
                        instance.strategy.value,
                    )
                ),
            )

        instance.fitted_ = bool(
            payload.get("fitted")
        )

        return instance


# ============================================================
# SECTION 28.07 - FEATURE QUALITY ANALYZER
# ============================================================

class FeatureQualityAnalyzer:
    def __init__(
        self,
        config: TrainingDatasetConfig,
    ) -> None:
        self.config = config

    def analyze_feature(
        self,
        feature_name: str,
        rows: Sequence[
            Mapping[str, Any]
        ],
    ) -> FeatureQualityMetric:
        raw_values = [
            row.get(feature_name)
            for row in rows
        ]

        missing_count = sum(
            1
            for value in raw_values
            if is_missing(value)
        )

        numeric_values = [
            to_float(value)
            for value in raw_values
            if not is_missing(value)
        ]

        unique_values = {
            canonical_json(value)
            for value in raw_values
            if not is_missing(value)
        }

        row_count = len(rows)

        missing_fraction = safe_divide(
            missing_count,
            row_count,
        )

        variance = (
            population_std(
                numeric_values
            )
            ** 2
            if numeric_values
            else 0.0
        )

        all_missing = (
            missing_count == row_count
        )

        constant = (
            len(unique_values) <= 1
        )

        exclusion_reasons = []

        if all_missing:
            exclusion_reasons.append(
                "all_missing"
            )

        if (
            missing_fraction
            > self.config.maximum_missing_fraction
        ):
            exclusion_reasons.append(
                "excessive_missingness"
            )

        if (
            variance
            <= self.config.variance_threshold
        ):
            exclusion_reasons.append(
                "near_zero_variance"
            )

        if feature_name in IDENTIFIER_FIELDS:
            if (
                not self.config
                .include_identifiers_in_matrix
            ):
                exclusion_reasons.append(
                    "identifier_excluded"
                )

        return FeatureQualityMetric(
            feature_name=feature_name,
            row_count=row_count,
            missing_count=missing_count,
            missing_fraction=(
                missing_fraction
            ),
            unique_count=len(
                unique_values
            ),
            variance=variance,
            minimum=(
                min(numeric_values)
                if numeric_values
                else None
            ),
            maximum=(
                max(numeric_values)
                if numeric_values
                else None
            ),
            mean=(
                mean(numeric_values)
                if numeric_values
                else None
            ),
            standard_deviation=(
                population_std(
                    numeric_values
                )
                if numeric_values
                else None
            ),
            constant=constant,
            all_missing=all_missing,
            recommended=(
                not exclusion_reasons
            ),
            exclusion_reasons=(
                exclusion_reasons
            ),
        )

    def analyze_targets(
        self,
        rows: Sequence[DatasetRow],
    ) -> dict[str, TargetBalance]:
        balances = {}

        for target_name in (
            self.config.target_names
        ):
            definition = TARGET_REGISTRY[
                target_name
            ]

            raw_values = [
                row.labels.get(
                    target_name
                )
                for row in rows
            ]

            missing_count = sum(
                is_missing(value)
                for value in raw_values
            )

            observed = [
                to_float(value)
                for value in raw_values
                if not is_missing(value)
            ]

            warnings = []

            positive_count = None
            negative_count = None

            if (
                definition.kind
                == TargetKind.BINARY
            ):
                positive_count = sum(
                    1
                    for value in observed
                    if value >= 0.5
                )

                negative_count = sum(
                    1
                    for value in observed
                    if value < 0.5
                )

                if (
                    positive_count
                    < self.config
                    .minimum_positive_rows
                ):
                    warnings.append(
                        "insufficient_positive_rows"
                    )

                if (
                    negative_count
                    < self.config
                    .minimum_negative_rows
                ):
                    warnings.append(
                        "insufficient_negative_rows"
                    )

            if not observed:
                warnings.append(
                    "no_observed_target_values"
                )

            balances[target_name] = (
                TargetBalance(
                    target_name=target_name,
                    target_kind=(
                        definition.kind
                    ),
                    row_count=len(
                        raw_values
                    ),
                    missing_count=(
                        missing_count
                    ),
                    positive_count=(
                        positive_count
                    ),
                    negative_count=(
                        negative_count
                    ),
                    mean=(
                        mean(observed)
                        if observed
                        else None
                    ),
                    minimum=(
                        min(observed)
                        if observed
                        else None
                    ),
                    maximum=(
                        max(observed)
                        if observed
                        else None
                    ),
                    ready=not warnings,
                    warnings=warnings,
                )
            )

        return balances


# ============================================================
# SECTION 28.08 - CORRELATION PRUNER
# ============================================================

class CorrelationPruner:
    def __init__(
        self,
        threshold: float = 0.999,
    ) -> None:
        self.threshold = threshold
        self.dropped_: dict[
            str,
            str,
        ] = {}

    @staticmethod
    def _pearson(
        x_values: Sequence[float],
        y_values: Sequence[float],
    ) -> float:
        if (
            len(x_values) != len(y_values)
            or len(x_values) < 2
        ):
            return 0.0

        x_mean = mean(x_values)
        y_mean = mean(y_values)

        numerator = sum(
            (x - x_mean)
            * (y - y_mean)
            for x, y in zip(
                x_values,
                y_values,
            )
        )

        x_scale = math.sqrt(
            sum(
                (x - x_mean) ** 2
                for x in x_values
            )
        )

        y_scale = math.sqrt(
            sum(
                (y - y_mean) ** 2
                for y in y_values
            )
        )

        denominator = (
            x_scale * y_scale
        )

        return safe_divide(
            numerator,
            denominator,
        )

    def select(
        self,
        rows: Sequence[
            Mapping[str, Any]
        ],
        feature_names: Sequence[str],
    ) -> list[str]:
        selected = []

        self.dropped_.clear()

        for feature_name in feature_names:
            current_values = [
                to_float(
                    row.get(feature_name)
                )
                for row in rows
            ]

            correlated_with = None

            for accepted_name in selected:
                accepted_values = [
                    to_float(
                        row.get(
                            accepted_name
                        )
                    )
                    for row in rows
                ]

                correlation = abs(
                    self._pearson(
                        current_values,
                        accepted_values,
                    )
                )

                if (
                    correlation
                    >= self.threshold
                ):
                    correlated_with = (
                        accepted_name
                    )
                    break

            if correlated_with is None:
                selected.append(
                    feature_name
                )

            else:
                self.dropped_[
                    feature_name
                ] = correlated_with

        return selected


# ============================================================
# SECTION 28.09 - CHRONOLOGICAL SPLITTER
# ============================================================

class ChronologicalDatasetSplitter:
    def __init__(
        self,
        config: TrainingDatasetConfig,
    ) -> None:
        self.config = config

    def split(
        self,
        rows: Sequence[DatasetRow],
    ) -> dict[
        DatasetSplitName,
        DatasetSplit,
    ]:
        ordered = sorted(
            rows,
            key=lambda row: (
                row.timestamp,
                str(row.entity_id),
                str(row.game_id),
            ),
        )

        if (
            self.config.split_strategy
            == SplitStrategy.SEASON_HOLDOUT
        ):
            return self._season_holdout(
                ordered
            )

        return self._fractional_split(
            ordered
        )

    def _fractional_split(
        self,
        rows: Sequence[DatasetRow],
    ) -> dict[
        DatasetSplitName,
        DatasetSplit,
    ]:
        row_count = len(rows)

        train_end = int(
            row_count
            * self.config.train_fraction
        )

        validation_end = train_end + int(
            row_count
            * self.config.validation_fraction
        )

        train_rows = list(
            rows[:train_end]
        )

        validation_rows = list(
            rows[
                train_end:validation_end
            ]
        )

        test_rows = list(
            rows[validation_end:]
        )

        return {
            DatasetSplitName.TRAIN: DatasetSplit(
                name=DatasetSplitName.TRAIN,
                rows=train_rows,
            ),
            DatasetSplitName.VALIDATION: DatasetSplit(
                name=DatasetSplitName.VALIDATION,
                rows=validation_rows,
            ),
            DatasetSplitName.TEST: DatasetSplit(
                name=DatasetSplitName.TEST,
                rows=test_rows,
            ),
        }

    def _season_holdout(
        self,
        rows: Sequence[DatasetRow],
    ) -> dict[
        DatasetSplitName,
        DatasetSplit,
    ]:
        seasons = sorted({
            row.season
            for row in rows
        })

        if not seasons:
            return self._fractional_split(
                rows
            )

        test_season = (
            self.config.holdout_season
            if self.config.holdout_season
            is not None
            else seasons[-1]
        )

        validation_season = (
            self.config.validation_season
            if self.config.validation_season
            is not None
            else (
                seasons[-2]
                if len(seasons) >= 2
                else None
            )
        )

        train_rows = [
            row
            for row in rows
            if (
                row.season
                != test_season
                and row.season
                != validation_season
            )
        ]

        validation_rows = [
            row
            for row in rows
            if (
                validation_season
                is not None
                and row.season
                == validation_season
            )
        ]

        test_rows = [
            row
            for row in rows
            if row.season
            == test_season
        ]

        return {
            DatasetSplitName.TRAIN: DatasetSplit(
                name=DatasetSplitName.TRAIN,
                rows=train_rows,
            ),
            DatasetSplitName.VALIDATION: DatasetSplit(
                name=DatasetSplitName.VALIDATION,
                rows=validation_rows,
            ),
            DatasetSplitName.TEST: DatasetSplit(
                name=DatasetSplitName.TEST,
                rows=test_rows,
            ),
        }


# ============================================================
# SECTION 28.10 - WAREHOUSE RECORD ADAPTER
# ============================================================

class WarehouseRecordAdapter:
    """
    Converts database-style player game rows into canonical
    feature-builder records without importing SQLAlchemy models.
    """

    def __init__(
        self,
        normalizer: RecordNormalizer | None = None,
    ) -> None:
        self.normalizer = (
            normalizer
            or RecordNormalizer()
        )

    def adapt_player_game_row(
        self,
        value: Any,
    ) -> dict[str, Any]:
        record = self.normalizer.normalize(
            value
        )

        record.setdefault(
            "game_id",
            first_present(
                record,
                (
                    "game_pk",
                    "mlb_game_id",
                ),
            ),
        )

        record.setdefault(
            "player_id",
            first_present(
                record,
                (
                    "mlb_player_id",
                    "person_id",
                ),
            ),
        )

        record.setdefault(
            "team_id",
            first_present(
                record,
                (
                    "current_team_id",
                    "mlb_team_id",
                ),
            ),
        )

        record.setdefault(
            "game_date",
            first_present(
                record,
                (
                    "official_date",
                    "date",
                ),
            ),
        )

        return record

    def adapt_many(
        self,
        values: Any,
    ) -> list[dict[str, Any]]:
        return [
            self.adapt_player_game_row(
                value
            )
            for value in records_from_any(
                values
            )
        ]

    def group_by_entity(
        self,
        values: Any,
        *,
        entity_field: str = "player_id",
    ) -> dict[Any, list[dict[str, Any]]]:
        groups: dict[
            Any,
            list[dict[str, Any]],
        ] = defaultdict(list)

        for record in self.adapt_many(
            values
        ):
            entity_id = record.get(
                entity_field
            )

            if entity_id is None:
                continue

            groups[entity_id].append(
                record
            )

        for entity_id in groups:
            groups[entity_id].sort(
                key=lambda row: (
                    parse_datetime(
                        row.get("game_date"),
                        datetime.min.replace(
                            tzinfo=UTC
                        ),
                    )
                    or datetime.min.replace(
                        tzinfo=UTC
                    )
                )
            )

        return dict(groups)


# ============================================================
# SECTION 28.11 - TRAINING DATASET BUILDER
# ============================================================

class TrainingDatasetBuilder:
    """
    Converts historical warehouse rows into leakage-safe,
    chronologically split, model-ready datasets.
    """

    def __init__(
        self,
        feature_builder: FeatureBuilder | None = None,
        config: TrainingDatasetConfig | None = None,
        warehouse_adapter: WarehouseRecordAdapter | None = None,
    ) -> None:
        self.config = (
            config
            or TrainingDatasetConfig()
        )

        self.config.validate()

        if feature_builder is None:
            feature_config = (
                FeatureBuilderConfig(
                    mode=FeatureMode.TRAINING,
                    prediction_unit=(
                        PredictionUnit.PLAYER_GAME
                    ),
                    include_labels=True,
                    leakage_policy=(
                        LeakagePolicy.ERROR
                    ),
                    strict=True,
                )
            )

            feature_builder = (
                PlayerFeatureBuilder(
                    feature_config
                )
            )

        self.feature_builder = (
            feature_builder
        )

        self.warehouse_adapter = (
            warehouse_adapter
            or WarehouseRecordAdapter()
        )

        self.target_deriver = (
            TargetDeriver(
                self.config.target_names
            )
        )

        self.quality_analyzer = (
            FeatureQualityAnalyzer(
                self.config
            )
        )

        self.splitter = (
            ChronologicalDatasetSplitter(
                self.config
            )
        )

        self.scaler = (
            DeterministicFeatureScaler(
                self.config.scaling_strategy
            )
        )

    def build(
        self,
        historical_rows: Any,
        *,
        context_rows: Any = None,
        source_metadata: Mapping[
            str,
            Any
        ] | None = None,
    ) -> TrainingDataset:
        adapted_rows = (
            self.warehouse_adapter
            .adapt_many(
                historical_rows
            )
        )

        if (
            len(adapted_rows)
            < self.config.minimum_rows
        ):
            raise FeatureValidationError(
                "Training dataset contains "
                f"{len(adapted_rows)} rows; "
                f"minimum is "
                f"{self.config.minimum_rows}"
            )

        ordered_rows = sorted(
            adapted_rows,
            key=lambda row: (
                parse_datetime(
                    row.get(
                        self.config
                        .timestamp_field
                    ),
                    datetime.min.replace(
                        tzinfo=UTC
                    ),
                )
                or datetime.min.replace(
                    tzinfo=UTC
                ),
                str(
                    row.get(
                        self.config
                        .entity_field
                    )
                ),
                str(
                    row.get(
                        self.config
                        .game_field
                    )
                ),
            ),
        )

        context_lookup = (
            self._context_lookup(
                context_rows
            )
        )

        history_by_entity: dict[
            Any,
            list[dict[str, Any]],
        ] = defaultdict(list)

        dataset_rows: list[
            DatasetRow
        ] = []

        schema_hashes = Counter()

        for source_index, row in enumerate(
            ordered_rows
        ):
            entity_id = row.get(
                self.config.entity_field
            )

            game_id = row.get(
                self.config.game_field
            )

            timestamp = parse_datetime(
                row.get(
                    self.config
                    .timestamp_field
                )
            )

            if timestamp is None:
                continue

            history = list(
                history_by_entity.get(
                    entity_id,
                    [],
                )
            )

            labels = (
                self.target_deriver
                .derive(
                    row
                )
            )

            context = context_lookup.get(
                (
                    game_id,
                    entity_id,
                )
            )

            vector = (
                self.feature_builder.build(
                    current=row,
                    history=history,
                    as_of=timestamp,
                    context=context,
                    labels=labels,
                )
            )

            schema_hashes[
                vector.schema_hash
            ] += 1

            season = to_int(
                row.get(
                    self.config
                    .season_field
                ),
                timestamp.year,
            )

            dataset_rows.append(
                DatasetRow(
                    features=dict(
                        vector.values
                    ),
                    labels=dict(
                        labels
                    ),
                    entity_id=entity_id,
                    game_id=game_id,
                    timestamp=timestamp,
                    season=season,
                    source_index=(
                        source_index
                    ),
                    vector_hash=(
                        vector.vector_hash
                    ),
                    schema_hash=(
                        vector.schema_hash
                    ),
                )
            )

            history_by_entity[
                entity_id
            ].append(row)

        quality = self._quality_report(
            dataset_rows,
            schema_hashes=schema_hashes,
        )

        selected_features = list(
            quality.selected_features
        )

        splits = self.splitter.split(
            dataset_rows
        )

        train_split = splits[
            DatasetSplitName.TRAIN
        ]

        train_feature_rows = [
            row.features
            for row in train_split.rows
        ]

        self.scaler.fit(
            train_feature_rows,
            selected_features,
        )

        schema_hash = fingerprint(
            selected_features
        )

        source_fingerprint = fingerprint(
            adapted_rows
        )

        dataset_fingerprint = fingerprint({
            "rows": [
                row.vector_hash
                for row in dataset_rows
            ],
            "selected_features": (
                selected_features
            ),
            "targets": (
                self.config.target_names
            ),
            "split_strategy": (
                self.config
                .split_strategy.value
            ),
        })

        timestamps = [
            row.timestamp
            for row in dataset_rows
        ]

        manifest = (
            TrainingDatasetManifest(
                dataset_id=str(
                    uuid4()
                ),
                created_at=utc_now(),
                module_version=(
                    MODULE_VERSION
                ),
                config_hash=fingerprint(
                    asdict(self.config)
                ),
                schema_hash=(
                    schema_hash
                ),
                row_count=len(
                    dataset_rows
                ),
                feature_names=(
                    selected_features
                ),
                target_names=list(
                    self.config.target_names
                ),
                split_strategy=(
                    self.config
                    .split_strategy
                ),
                split_summary={
                    name.value: split.to_dict()
                    for name, split
                    in splits.items()
                },
                quality_status=(
                    quality.status
                ),
                source_fingerprint=(
                    source_fingerprint
                ),
                dataset_fingerprint=(
                    dataset_fingerprint
                ),
                temporal_start=(
                    min(timestamps)
                    if timestamps
                    else None
                ),
                temporal_end=(
                    max(timestamps)
                    if timestamps
                    else None
                ),
                seasons=sorted({
                    row.season
                    for row in dataset_rows
                }),
                metadata=dict(
                    source_metadata
                    or {}
                ),
            )
        )

        return TrainingDataset(
            rows=dataset_rows,
            splits=splits,
            quality=quality,
            manifest=manifest,
            feature_scaler=(
                self.scaler
            ),
            selected_features=(
                selected_features
            ),
        )

    def _context_lookup(
        self,
        context_rows: Any,
    ) -> dict[
        tuple[Any, Any],
        dict[str, Any],
    ]:
        if context_rows is None:
            return {}

        normalized = (
            RecordNormalizer()
            .normalize_many(
                context_rows
            )
        )

        return {
            (
                row.get(
                    self.config
                    .game_field
                ),
                row.get(
                    self.config
                    .entity_field
                ),
            ): row
            for row in normalized
        }

    def _quality_report(
        self,
        rows: Sequence[DatasetRow],
        *,
        schema_hashes: Counter,
    ) -> DatasetQualityReport:
        feature_names = sorted({
            name
            for row in rows
            for name in row.features
        })

        feature_metrics = {
            feature_name: (
                self.quality_analyzer
                .analyze_feature(
                    feature_name,
                    [
                        row.features
                        for row in rows
                    ],
                )
            )
            for feature_name in feature_names
        }

        selected_features = [
            name
            for name, metric
            in feature_metrics.items()
            if metric.recommended
        ]

        excluded_features = {
            name: list(
                metric.exclusion_reasons
            )
            for name, metric
            in feature_metrics.items()
            if not metric.recommended
        }

        if (
            self.config
            .feature_selection_strategy
            in {
                FeatureSelectionStrategy.CORRELATION,
                FeatureSelectionStrategy.COMBINED,
            }
        ):
            pruner = CorrelationPruner(
                threshold=(
                    self.config
                    .correlation_threshold
                )
            )

            pruned = pruner.select(
                [
                    row.features
                    for row in rows
                ],
                selected_features,
            )

            for dropped, kept in (
                pruner.dropped_.items()
            ):
                excluded_features.setdefault(
                    dropped,
                    [],
                ).append(
                    "high_correlation_with:"
                    + kept
                )

            selected_features = pruned

        identities = [
            (
                row.entity_id,
                row.game_id,
            )
            for row in rows
        ]

        duplicate_identity_rows = (
            len(identities)
            - len(set(identities))
        )

        non_monotonic_rows = 0

        previous_by_entity = {}

        for row in sorted(
            rows,
            key=lambda item: (
                str(item.entity_id),
                item.timestamp,
            ),
        ):
            previous = previous_by_entity.get(
                row.entity_id
            )

            if (
                previous is not None
                and row.timestamp
                < previous
            ):
                non_monotonic_rows += 1

            previous_by_entity[
                row.entity_id
            ] = row.timestamp

        schema_mismatch_rows = (
            len(rows)
            - max(
                schema_hashes.values(),
                default=0,
            )
        )

        leakage_issue_count = sum(
            1
            for feature_name in feature_names
            if any(
                pattern
                in normalize_name(
                    feature_name
                )
                for pattern
                in LeakageAuditor
                .SUSPICIOUS_PATTERNS
            )
        )

        target_balances = (
            self.quality_analyzer
            .analyze_targets(
                rows
            )
        )

        warnings = []
        errors = []

        if duplicate_identity_rows:
            message = (
                "Duplicate entity/game rows: "
                f"{duplicate_identity_rows}"
            )

            if (
                self.config
                .require_unique_entity_game_rows
            ):
                errors.append(message)
            else:
                warnings.append(message)

        if non_monotonic_rows:
            message = (
                "Non-monotonic entity timelines: "
                f"{non_monotonic_rows}"
            )

            if (
                self.config
                .require_monotonic_time
            ):
                errors.append(message)
            else:
                warnings.append(message)

        if schema_mismatch_rows:
            warnings.append(
                "Schema mismatch rows: "
                f"{schema_mismatch_rows}"
            )

        if leakage_issue_count:
            errors.append(
                "Potential leakage features detected: "
                f"{leakage_issue_count}"
            )

        unready_targets = [
            name
            for name, balance
            in target_balances.items()
            if not balance.ready
        ]

        if unready_targets:
            warnings.append(
                "Targets with insufficient balance: "
                + ", ".join(
                    unready_targets
                )
            )

        if len(rows) < self.config.minimum_rows:
            errors.append(
                "Dataset row count below configured minimum"
            )

        if not selected_features:
            errors.append(
                "No usable features remain after quality filtering"
            )

        status = (
            DataQualityStatus.BLOCKED
            if errors
            else (
                DataQualityStatus.DEGRADED
                if warnings
                else DataQualityStatus.READY
            )
        )

        return DatasetQualityReport(
            status=status,
            row_count=len(rows),
            feature_count=len(
                feature_names
            ),
            target_count=len(
                self.config.target_names
            ),
            duplicate_identity_rows=(
                duplicate_identity_rows
            ),
            non_monotonic_rows=(
                non_monotonic_rows
            ),
            schema_mismatch_rows=(
                schema_mismatch_rows
            ),
            leakage_issue_count=(
                leakage_issue_count
            ),
            feature_metrics=(
                feature_metrics
            ),
            target_balances=(
                target_balances
            ),
            selected_features=(
                selected_features
            ),
            excluded_features=(
                excluded_features
            ),
            warnings=warnings,
            errors=errors,
        )


# ============================================================
# SECTION 28.12 - MODEL MATRIX CONTRACT
# ============================================================

@dataclass(slots=True)
class ModelMatrix:
    features: Any
    labels: dict[str, Any]
    feature_names: list[str]
    row_ids: list[dict[str, Any]]
    split_name: DatasetSplitName
    schema_hash: str
    row_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_names": (
                self.feature_names
            ),
            "row_ids": self.row_ids,
            "split_name": (
                self.split_name.value
            ),
            "schema_hash": (
                self.schema_hash
            ),
            "row_count": self.row_count,
            "label_names": sorted(
                self.labels.keys()
            ),
        }


class ModelMatrixBuilder:
    def build(
        self,
        dataset: TrainingDataset,
        split_name: DatasetSplitName,
        *,
        scaled: bool = True,
    ) -> ModelMatrix:
        split = dataset.splits[
            split_name
        ]

        feature_rows = [
            row.features
            for row in split.rows
        ]

        if scaled:
            feature_rows = (
                dataset.feature_scaler
                .transform_rows(
                    feature_rows,
                    dataset.selected_features,
                )
            )

        matrix, feature_names = (
            feature_matrix(
                [
                    FeatureVector(
                        values={
                            name: row.get(
                                name,
                                0.0,
                            )
                            for name in (
                                dataset
                                .selected_features
                            )
                        },
                        as_of=utc_now(),
                    ).finalize()
                    for row in feature_rows
                ],
                columns=(
                    dataset
                    .selected_features
                ),
            )
        )

        labels = {}

        for target_name in (
            dataset.manifest
            .target_names
        ):
            values = [
                to_float(
                    row.labels.get(
                        target_name
                    )
                )
                for row in split.rows
            ]

            labels[target_name] = (
                np.asarray(
                    values,
                    dtype=float,
                )
                if np is not None
                else values
            )

        row_ids = [
            {
                "entity_id": row.entity_id,
                "game_id": row.game_id,
                "timestamp": (
                    row.timestamp.isoformat()
                ),
                "season": row.season,
            }
            for row in split.rows
        ]

        return ModelMatrix(
            features=matrix,
            labels=labels,
            feature_names=(
                feature_names
            ),
            row_ids=row_ids,
            split_name=split_name,
            schema_hash=(
                dataset.manifest
                .schema_hash
            ),
            row_count=len(
                split.rows
            ),
        )


# ============================================================
# SECTION 28.13 - DATASET ARTIFACT EXPORT
# ============================================================

class TrainingDatasetArtifactWriter:
    def __init__(
        self,
        root_directory: str | Path,
    ) -> None:
        self.root_directory = Path(
            root_directory
        )

    def write(
        self,
        dataset: TrainingDataset,
        *,
        include_rows: bool = False,
    ) -> dict[str, str]:
        dataset_directory = (
            self.root_directory
            / dataset.manifest.dataset_id
        )

        dataset_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        manifest_path = (
            dataset_directory
            / "manifest.json"
        )

        quality_path = (
            dataset_directory
            / "quality_report.json"
        )

        scaler_path = (
            dataset_directory
            / "feature_scaler.json"
        )

        schema_path = (
            dataset_directory
            / "feature_schema.json"
        )

        manifest_path.write_text(
            json.dumps(
                dataset.manifest.to_dict(),
                indent=2,
                sort_keys=True,
                default=str,
            ),
            encoding="utf-8",
        )

        quality_path.write_text(
            json.dumps(
                dataset.quality.to_dict(),
                indent=2,
                sort_keys=True,
                default=str,
            ),
            encoding="utf-8",
        )

        scaler_path.write_text(
            json.dumps(
                dataset.feature_scaler.to_dict(),
                indent=2,
                sort_keys=True,
                default=str,
            ),
            encoding="utf-8",
        )

        schema_path.write_text(
            json.dumps(
                {
                    "schema_hash": (
                        dataset.manifest
                        .schema_hash
                    ),
                    "feature_names": (
                        dataset
                        .selected_features
                    ),
                    "target_names": (
                        dataset.manifest
                        .target_names
                    ),
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        output = {
            "directory": str(
                dataset_directory
            ),
            "manifest": str(
                manifest_path
            ),
            "quality_report": str(
                quality_path
            ),
            "feature_scaler": str(
                scaler_path
            ),
            "feature_schema": str(
                schema_path
            ),
        }

        if include_rows:
            rows_path = (
                dataset_directory
                / "dataset_rows.jsonl"
            )

            with rows_path.open(
                "w",
                encoding="utf-8",
            ) as file:
                for row in dataset.rows:
                    file.write(
                        json.dumps(
                            row.to_dict(),
                            sort_keys=True,
                            default=str,
                        )
                        + "\n"
                    )

            output["rows"] = str(
                rows_path
            )

        return output


# ============================================================
# SECTION 28.14 - WALK-FORWARD FOLD CONTRACT
# ============================================================

@dataclass(slots=True)
class WalkForwardFold:
    fold_index: int
    train_rows: list[DatasetRow]
    validation_rows: list[DatasetRow]
    test_rows: list[DatasetRow]

    train_start: datetime | None
    train_end: datetime | None
    validation_start: datetime | None
    validation_end: datetime | None
    test_start: datetime | None
    test_end: datetime | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "fold_index": self.fold_index,
            "train_count": len(
                self.train_rows
            ),
            "validation_count": len(
                self.validation_rows
            ),
            "test_count": len(
                self.test_rows
            ),
            "train_start": (
                self.train_start.isoformat()
                if self.train_start
                else None
            ),
            "train_end": (
                self.train_end.isoformat()
                if self.train_end
                else None
            ),
            "validation_start": (
                self.validation_start.isoformat()
                if self.validation_start
                else None
            ),
            "validation_end": (
                self.validation_end.isoformat()
                if self.validation_end
                else None
            ),
            "test_start": (
                self.test_start.isoformat()
                if self.test_start
                else None
            ),
            "test_end": (
                self.test_end.isoformat()
                if self.test_end
                else None
            ),
        }


class WalkForwardFoldBuilder:
    def build(
        self,
        rows: Sequence[DatasetRow],
        *,
        minimum_train_rows: int,
        validation_rows: int,
        test_rows: int,
        step_rows: int | None = None,
        expanding: bool = True,
    ) -> list[WalkForwardFold]:
        ordered = sorted(
            rows,
            key=lambda row: (
                row.timestamp,
                str(row.entity_id),
                str(row.game_id),
            ),
        )

        if minimum_train_rows < 1:
            raise FeatureConfigurationError(
                "minimum_train_rows must be positive"
            )

        if validation_rows < 1:
            raise FeatureConfigurationError(
                "validation_rows must be positive"
            )

        if test_rows < 1:
            raise FeatureConfigurationError(
                "test_rows must be positive"
            )

        step_rows = (
            step_rows
            or test_rows
        )

        folds = []

        cursor = minimum_train_rows

        fold_index = 0

        while (
            cursor
            + validation_rows
            + test_rows
            <= len(ordered)
        ):
            if expanding:
                train_slice = ordered[
                    :cursor
                ]

            else:
                train_slice = ordered[
                    max(
                        0,
                        cursor
                        - minimum_train_rows,
                    ):cursor
                ]

            validation_slice = ordered[
                cursor:
                cursor + validation_rows
            ]

            test_slice = ordered[
                cursor + validation_rows:
                cursor + validation_rows
                + test_rows
            ]

            folds.append(
                WalkForwardFold(
                    fold_index=fold_index,
                    train_rows=list(
                        train_slice
                    ),
                    validation_rows=list(
                        validation_slice
                    ),
                    test_rows=list(
                        test_slice
                    ),
                    train_start=(
                        train_slice[0]
                        .timestamp
                        if train_slice
                        else None
                    ),
                    train_end=(
                        train_slice[-1]
                        .timestamp
                        if train_slice
                        else None
                    ),
                    validation_start=(
                        validation_slice[0]
                        .timestamp
                        if validation_slice
                        else None
                    ),
                    validation_end=(
                        validation_slice[-1]
                        .timestamp
                        if validation_slice
                        else None
                    ),
                    test_start=(
                        test_slice[0]
                        .timestamp
                        if test_slice
                        else None
                    ),
                    test_end=(
                        test_slice[-1]
                        .timestamp
                        if test_slice
                        else None
                    ),
                )
            )

            cursor += step_rows
            fold_index += 1

        return folds


# ============================================================
# SECTION 28.15 - FEATURE REGISTRY
# ============================================================

@dataclass(frozen=True, slots=True)
class FeatureRegistryEntry:
    name: str
    group: str
    description: str
    leakage_risk: str
    expected_range: tuple[
        float | None,
        float | None,
    ] = (None, None)
    required_for_training: bool = False


class FeatureRegistry:
    def __init__(self) -> None:
        self._entries: OrderedDict[
            str,
            FeatureRegistryEntry,
        ] = OrderedDict()

    def register(
        self,
        entry: FeatureRegistryEntry,
    ) -> None:
        canonical = normalize_name(
            entry.name
        )

        if not canonical:
            raise FeatureSchemaError(
                "Feature registry name cannot be empty"
            )

        self._entries[
            canonical
        ] = FeatureRegistryEntry(
            name=canonical,
            group=entry.group,
            description=(
                entry.description
            ),
            leakage_risk=(
                entry.leakage_risk
            ),
            expected_range=(
                entry.expected_range
            ),
            required_for_training=(
                entry
                .required_for_training
            ),
        )

    def get(
        self,
        name: str,
    ) -> FeatureRegistryEntry | None:
        return self._entries.get(
            normalize_name(name)
        )

    def entries(
        self,
    ) -> list[FeatureRegistryEntry]:
        return list(
            self._entries.values()
        )

    def validate_features(
        self,
        feature_names: Sequence[str],
    ) -> dict[str, Any]:
        unknown = [
            name
            for name in feature_names
            if normalize_name(name)
            not in self._entries
        ]

        required_missing = [
            entry.name
            for entry in self._entries.values()
            if entry.required_for_training
            and entry.name
            not in {
                normalize_name(name)
                for name in feature_names
            }
        ]

        high_risk = [
            name
            for name in feature_names
            if (
                self.get(name) is not None
                and self.get(name)
                .leakage_risk
                == "high"
            )
        ]

        return {
            "unknown_features": unknown,
            "required_missing": (
                required_missing
            ),
            "high_leakage_risk": (
                high_risk
            ),
            "valid": (
                not required_missing
                and not high_risk
            ),
        }


DEFAULT_FEATURE_REGISTRY = FeatureRegistry()

for registry_entry in (
    FeatureRegistryEntry(
        name="history_game_count",
        group="sample",
        description=(
            "Number of prior games available."
        ),
        leakage_risk="low",
        expected_range=(0.0, None),
        required_for_training=True,
    ),
    FeatureRegistryEntry(
        name="history_plate_appearances",
        group="sample",
        description=(
            "Prior plate appearances."
        ),
        leakage_risk="low",
        expected_range=(0.0, None),
        required_for_training=True,
    ),
    FeatureRegistryEntry(
        name="career_batting_average",
        group="rate",
        description=(
            "Historical batting average."
        ),
        leakage_risk="low",
        expected_range=(0.0, 1.0),
    ),
    FeatureRegistryEntry(
        name="career_home_run_rate",
        group="rate",
        description=(
            "Historical home-run rate."
        ),
        leakage_risk="low",
        expected_range=(0.0, 1.0),
    ),
    FeatureRegistryEntry(
        name="career_walk_rate",
        group="rate",
        description=(
            "Historical walk rate."
        ),
        leakage_risk="low",
        expected_range=(0.0, 1.0),
    ),
    FeatureRegistryEntry(
        name="career_strikeout_rate",
        group="rate",
        description=(
            "Historical strikeout rate."
        ),
        leakage_risk="low",
        expected_range=(0.0, 1.0),
    ),
    FeatureRegistryEntry(
        name="career_ops",
        group="rate",
        description=(
            "Historical on-base plus slugging."
        ),
        leakage_risk="low",
        expected_range=(0.0, 3.0),
    ),
    FeatureRegistryEntry(
        name="context_park_factor",
        group="context",
        description=(
            "Venue offensive park factor."
        ),
        leakage_risk="low",
        expected_range=(0.5, 1.5),
    ),
    FeatureRegistryEntry(
        name="context_rest_days",
        group="context",
        description=(
            "Days of rest before the prediction event."
        ),
        leakage_risk="low",
        expected_range=(0.0, 30.0),
    ),
    FeatureRegistryEntry(
        name="uncertainty_sample_reliability",
        group="uncertainty",
        description=(
            "Sample-size reliability indicator."
        ),
        leakage_risk="low",
        expected_range=(0.0, 1.0),
    ),
):
    DEFAULT_FEATURE_REGISTRY.register(
        registry_entry
    )


# ============================================================
# SECTION 28.16 - TRAINING READINESS REPORT
# ============================================================

def training_readiness_report(
    historical_rows: Any,
    *,
    config: TrainingDatasetConfig | None = None,
) -> dict[str, Any]:
    effective_config = (
        config
        or TrainingDatasetConfig()
    )

    adapted_rows = (
        WarehouseRecordAdapter()
        .adapt_many(
            historical_rows
        )
    )

    row_count = len(
        adapted_rows
    )

    entity_ids = {
        row.get(
            effective_config.entity_field
        )
        for row in adapted_rows
        if row.get(
            effective_config.entity_field
        )
        is not None
    }

    game_ids = {
        row.get(
            effective_config.game_field
        )
        for row in adapted_rows
        if row.get(
            effective_config.game_field
        )
        is not None
    }

    timestamps = [
        parse_datetime(
            row.get(
                effective_config
                .timestamp_field
            )
        )
        for row in adapted_rows
    ]

    valid_timestamps = [
        value
        for value in timestamps
        if value is not None
    ]

    target_deriver = TargetDeriver(
        effective_config.target_names
    )

    target_counts = Counter()

    for row in adapted_rows:
        labels = target_deriver.derive(
            row
        )

        for target_name, value in labels.items():
            if not is_missing(value):
                target_counts[
                    target_name
                ] += 1

    checks = {
        "minimum_rows": (
            row_count
            >= effective_config.minimum_rows
        ),
        "entities_present": (
            len(entity_ids) > 0
        ),
        "games_present": (
            len(game_ids) > 0
        ),
        "timestamps_present": (
            len(valid_timestamps)
            == row_count
        ),
        "all_targets_observed": all(
            target_counts[
                target_name
            ]
            > 0
            for target_name
            in effective_config.target_names
        ),
    }

    passed = sum(
        checks.values()
    )

    return {
        "status": (
            "ready"
            if passed == len(checks)
            else "not_ready"
        ),
        "row_count": row_count,
        "entity_count": len(
            entity_ids
        ),
        "game_count": len(
            game_ids
        ),
        "temporal_start": (
            min(valid_timestamps)
            .isoformat()
            if valid_timestamps
            else None
        ),
        "temporal_end": (
            max(valid_timestamps)
            .isoformat()
            if valid_timestamps
            else None
        ),
        "target_observation_counts": (
            dict(
                target_counts
            )
        ),
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "failed_checks": [
            name
            for name, value
            in checks.items()
            if not value
        ],
    }


# ============================================================
# SECTION 28.17 - ENTERPRISE VALIDATION
# ============================================================

def validate_feature_builder_enterprise(
) -> dict[str, Any]:
    sample_rows = []

    start = datetime(
        2024,
        4,
        1,
        19,
        5,
        tzinfo=UTC,
    )

    for index in range(180):
        sample_rows.append({
            "player_id": (
                index % 12
            )
            + 1,
            "team_id": (
                index % 30
            )
            + 1,
            "game_id": (
                100000 + index
            ),
            "game_date": (
                start
                + timedelta(
                    days=index
                )
            ).isoformat(),
            "season": 2024,
            "plate_appearances": 4,
            "at_bats": 4,
            "hits": index % 3,
            "doubles": (
                1
                if index % 11 == 0
                else 0
            ),
            "triples": (
                1
                if index % 47 == 0
                else 0
            ),
            "home_runs": (
                1
                if index % 17 == 0
                else 0
            ),
            "walks": (
                1
                if index % 7 == 0
                else 0
            ),
            "strikeouts": (
                1
                if index % 2 == 0
                else 0
            ),
            "runs": (
                1
                if index % 4 == 0
                else 0
            ),
            "rbi": (
                1
                if index % 6 == 0
                else 0
            ),
            "home_away": (
                "home"
                if index % 2 == 0
                else "away"
            ),
            "pitcher_throws": (
                "R"
                if index % 3
                else "L"
            ),
        })

    dataset_config = (
        TrainingDatasetConfig(
            minimum_rows=100,
            target_names=(
                "target_hit",
                "target_home_run",
                "target_walk",
                "target_strikeout",
                "target_rbi",
                "target_total_bases",
            ),
        )
    )

    dataset_builder = (
        TrainingDatasetBuilder(
            config=dataset_config
        )
    )

    dataset = dataset_builder.build(
        sample_rows,
        source_metadata={
            "validation_fixture": True,
        },
    )

    matrix_builder = (
        ModelMatrixBuilder()
    )

    train_matrix = (
        matrix_builder.build(
            dataset,
            DatasetSplitName.TRAIN,
        )
    )

    folds = WalkForwardFoldBuilder().build(
        dataset.rows,
        minimum_train_rows=80,
        validation_rows=20,
        test_rows=20,
        step_rows=20,
    )

    checks = {
        "legacy_validation_available": callable(
            validate_feature_builder
        ),
        "feature_builder_available": callable(
            FeatureBuilder
        ),
        "training_dataset_builder_available": callable(
            TrainingDatasetBuilder
        ),
        "target_registry_populated": (
            len(TARGET_REGISTRY) >= 10
        ),
        "dataset_created": (
            len(dataset.rows) > 0
        ),
        "chronological_splits_created": (
            set(dataset.splits)
            == {
                DatasetSplitName.TRAIN,
                DatasetSplitName.VALIDATION,
                DatasetSplitName.TEST,
            }
        ),
        "train_rows_present": (
            dataset.splits[
                DatasetSplitName.TRAIN
            ].row_count
            > 0
        ),
        "validation_rows_present": (
            dataset.splits[
                DatasetSplitName.VALIDATION
            ].row_count
            > 0
        ),
        "test_rows_present": (
            dataset.splits[
                DatasetSplitName.TEST
            ].row_count
            > 0
        ),
        "selected_features_present": (
            len(
                dataset.selected_features
            )
            > 0
        ),
        "scaler_fitted": (
            dataset.feature_scaler
            .fitted_
        ),
        "manifest_created": (
            bool(
                dataset.manifest
                .dataset_id
            )
        ),
        "schema_hash_created": (
            bool(
                dataset.manifest
                .schema_hash
            )
        ),
        "dataset_fingerprint_created": (
            bool(
                dataset.manifest
                .dataset_fingerprint
            )
        ),
        "target_balances_created": (
            len(
                dataset.quality
                .target_balances
            )
            == len(
                dataset_config
                .target_names
            )
        ),
        "model_matrix_created": (
            train_matrix.row_count
            > 0
        ),
        "model_matrix_features_present": (
            len(
                train_matrix
                .feature_names
            )
            > 0
        ),
        "walk_forward_folds_created": (
            len(folds) > 0
        ),
        "training_readiness_available": callable(
            training_readiness_report
        ),
        "artifact_writer_available": callable(
            TrainingDatasetArtifactWriter
        ),
    }

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
        "module": MODULE_NAME,
        "version": MODULE_VERSION,
        "path": MODULE_PATH,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "failed_checks": [
            name
            for name, value
            in checks.items()
            if not value
        ],
        "dataset_summary": (
            dataset.to_dict(
                include_rows=False
            )
        ),
        "train_matrix": (
            train_matrix.to_dict()
        ),
        "walk_forward_fold_count": (
            len(folds)
        ),
    }


# ============================================================
# SECTION 28.18 - ENTERPRISE HEALTH
# ============================================================

def feature_builder_enterprise_health(
) -> dict[str, Any]:
    validation = (
        validate_feature_builder_enterprise()
    )

    return {
        "module": MODULE_NAME,
        "path": MODULE_PATH,
        "version": MODULE_VERSION,
        "status": (
            MODULE_STATUS
            if validation["status"] == "ok"
            else "validation_failed"
        ),
        "capabilities": {
            "single_vector_features": True,
            "batch_features": True,
            "player_game_features": True,
            "batter_pitcher_features": True,
            "team_game_features": True,
            "temporal_leakage_guard": True,
            "warehouse_row_adapter": True,
            "target_registry": True,
            "chronological_splits": True,
            "season_holdout_splits": True,
            "walk_forward_folds": True,
            "feature_quality_analysis": True,
            "target_balance_analysis": True,
            "variance_filtering": True,
            "correlation_pruning": True,
            "deterministic_scaling": True,
            "schema_locking": True,
            "dataset_fingerprints": True,
            "artifact_export": True,
            "model_matrix_generation": True,
            "training_readiness_reporting": True,
        },
        "validation": validation,
        "timestamp": (
            utc_now().isoformat()
        ),
    }


# ============================================================
# SECTION 28.19 - CONVENIENCE TRAINING FUNCTIONS
# ============================================================

def build_training_dataset(
    historical_rows: Any,
    *,
    context_rows: Any = None,
    config: TrainingDatasetConfig | None = None,
    source_metadata: Mapping[
        str,
        Any
    ] | None = None,
) -> TrainingDataset:
    return TrainingDatasetBuilder(
        config=config
    ).build(
        historical_rows,
        context_rows=context_rows,
        source_metadata=source_metadata,
    )


def build_model_matrices(
    dataset: TrainingDataset,
    *,
    scaled: bool = True,
) -> dict[
    DatasetSplitName,
    ModelMatrix,
]:
    builder = ModelMatrixBuilder()

    return {
        split_name: builder.build(
            dataset,
            split_name,
            scaled=scaled,
        )
        for split_name in dataset.splits
    }


def export_training_dataset(
    dataset: TrainingDataset,
    *,
    root_directory: str | Path | None = None,
    include_rows: bool = False,
) -> dict[str, str]:
    root = (
        root_directory
        or TrainingDatasetConfig()
        .artifact_directory
    )

    return (
        TrainingDatasetArtifactWriter(
            root
        ).write(
            dataset,
            include_rows=include_rows,
        )
    )



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

    "TargetKind",
    "DatasetSplitName",
    "SplitStrategy",
    "ScalingStrategy",
    "FeatureSelectionStrategy",
    "DataQualityStatus",
    "OutcomeFamily",

    "TargetDefinition",
    "TARGET_REGISTRY",
    "TrainingDatasetConfig",
    "DatasetRow",
    "DatasetSplit",
    "TargetBalance",
    "FeatureQualityMetric",
    "DatasetQualityReport",
    "TrainingDatasetManifest",
    "TrainingDataset",

    "TargetDeriver",
    "ScalingStatistic",
    "DeterministicFeatureScaler",
    "FeatureQualityAnalyzer",
    "CorrelationPruner",
    "ChronologicalDatasetSplitter",
    "WarehouseRecordAdapter",
    "TrainingDatasetBuilder",

    "ModelMatrix",
    "ModelMatrixBuilder",
    "TrainingDatasetArtifactWriter",

    "WalkForwardFold",
    "WalkForwardFoldBuilder",

    "FeatureRegistryEntry",
    "FeatureRegistry",
    "DEFAULT_FEATURE_REGISTRY",

    "training_readiness_report",
    "validate_feature_builder_enterprise",
    "feature_builder_enterprise_health",
    "build_training_dataset",
    "build_model_matrices",
    "export_training_dataset",
]


# ============================================================
# SECTION 30 - LOCAL VALIDATION ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    report = (
        validate_feature_builder_enterprise()
    )

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

    if report["status"] != "ok":
        raise SystemExit(1)
