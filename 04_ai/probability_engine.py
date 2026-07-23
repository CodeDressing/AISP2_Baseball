# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# PHASE 10 PART 1.1
# ENTERPRISE MATHEMATICAL PROBABILITY ENGINE
# FILE: 04_ai/probability_engine.py
# PURPOSE:
# Provide numerically stable, explainable, calibration-ready probability
# mathematics for player, team, matchup, and game projection services.
# ============================================================

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
import logging
import math
import random
import statistics
from typing import Any, Final, TypeVar


# ============================================================
# SECTION 02 - MODULE METADATA AND LOGGING
# ============================================================

ENGINE_NAME: Final[str] = "AISP2 Mathematical Probability Engine"
ENGINE_VERSION: Final[str] = "2.0.0"
ENGINE_PHASE: Final[str] = "Phase 10 Part 1.1"
ENGINE_FILE: Final[str] = "04_ai/probability_engine.py"
ENGINE_STATUS: Final[str] = "enterprise_probability_core_ready"
UTC: Final[timezone] = timezone.utc
LOGGER = logging.getLogger(__name__)


# ============================================================
# SECTION 03 - DOMAIN CONSTANTS
# ============================================================

SUPPORTED_OUTCOMES: Final[frozenset[str]] = frozenset(
    {
        "hit",
        "single",
        "double",
        "triple",
        "home_run",
        "walk",
        "strikeout",
        "rbi",
        "run",
        "total_bases",
        "reach_base",
        "extra_base_hit",
        "team_win",
        "team_runs",
    }
)

PLATE_APPEARANCE_OUTCOMES: Final[tuple[str, ...]] = (
    "single",
    "double",
    "triple",
    "home_run",
    "walk",
    "strikeout",
    "other_out",
)

LEAGUE_PRIORS: Final[dict[str, float]] = {
    "hit": 0.245,
    "single": 0.150,
    "double": 0.045,
    "triple": 0.004,
    "home_run": 0.032,
    "walk": 0.083,
    "strikeout": 0.225,
    "rbi": 0.110,
    "run": 0.115,
    "reach_base": 0.325,
    "extra_base_hit": 0.081,
    "total_bases": 0.325,
    "other_out": 0.461,
    "team_win": 0.500,
    "team_runs": 4.40,
}

OUTCOME_BOUNDS: Final[dict[str, tuple[float, float]]] = {
    "hit": (0.040, 0.500),
    "single": (0.020, 0.360),
    "double": (0.002, 0.160),
    "triple": (0.0002, 0.050),
    "home_run": (0.001, 0.220),
    "walk": (0.010, 0.300),
    "strikeout": (0.025, 0.550),
    "rbi": (0.015, 0.400),
    "run": (0.015, 0.400),
    "reach_base": (0.080, 0.650),
    "extra_base_hit": (0.005, 0.300),
    "total_bases": (0.030, 0.700),
    "other_out": (0.100, 0.850),
    "team_win": (0.010, 0.990),
}

DEFAULT_PRIOR_STRENGTH: Final[float] = 120.0
DEFAULT_CONFIDENCE_LEVEL: Final[float] = 0.95
DEFAULT_EXPECTED_PLATE_APPEARANCES: Final[float] = 4.2
DEFAULT_RANDOM_SEED: Final[int] = 20260714
EPSILON: Final[float] = 1e-12
MAX_EXPONENT: Final[float] = 700.0


# ============================================================
# SECTION 04 - ENUMERATIONS
# ============================================================

class ProbabilityScale(str, Enum):
    DECIMAL = "decimal"
    PERCENT = "percent"
    LOG_ODDS = "log_odds"


class ProbabilityUnit(str, Enum):
    PER_PLATE_APPEARANCE = "per_plate_appearance"
    PER_AT_BAT = "per_at_bat"
    PER_GAME = "per_game"
    TEAM_GAME = "team_game"


class CombinationMethod(str, Enum):
    LOG_ODDS = "log_odds"
    WEIGHTED_AVERAGE = "weighted_average"
    GEOMETRIC = "geometric"
    MULTIPLICATIVE = "multiplicative"


class DistributionKind(str, Enum):
    BERNOULLI = "bernoulli"
    BINOMIAL = "binomial"
    BETA = "beta"
    POISSON = "poisson"
    NEGATIVE_BINOMIAL = "negative_binomial"
    NORMAL = "normal"
    SKELLAM = "skellam"


class ConfidenceBand(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


# ============================================================
# SECTION 05 - EXCEPTIONS
# ============================================================

class ProbabilityEngineError(RuntimeError):
    """Base exception for probability engine failures."""


class ProbabilityValidationError(ProbabilityEngineError):
    """Raised when a probability request contains invalid data."""


class UnsupportedOutcomeError(ProbabilityEngineError):
    """Raised when an outcome is not recognized in strict mode."""


class NumericalStabilityError(ProbabilityEngineError):
    """Raised when a numerical operation cannot produce a finite result."""


# ============================================================
# SECTION 06 - SAFE MATH HELPERS
# ============================================================

Number = int | float | Decimal
T = TypeVar("T")


def is_finite_number(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def to_float(value: Any, default: float = 0.0) -> float:
    if value is None or isinstance(value, bool):
        return float(default)
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return float(default)
    return numeric if math.isfinite(numeric) else float(default)


def safe_divide(
    numerator: float | int | Decimal | None,
    denominator: float | int | Decimal | None,
    default: float = 0.0,
) -> float:
    n = to_float(numerator, default)
    d = to_float(denominator, 0.0)
    if abs(d) <= EPSILON:
        return float(default)
    result = n / d
    return result if math.isfinite(result) else float(default)


def clamp(value: float, minimum: float, maximum: float) -> float:
    if minimum > maximum:
        raise ProbabilityValidationError("minimum cannot exceed maximum")
    numeric = to_float(value, minimum)
    return max(minimum, min(maximum, numeric))


def clamp_probability(value: Any, epsilon: float = EPSILON) -> float:
    return clamp(to_float(value), epsilon, 1.0 - epsilon)


def normalize_rate(value: float | None, fallback: float) -> float:
    if value is None:
        return fallback
    numeric = to_float(value, fallback)
    if numeric > 1.0:
        numeric /= 100.0
    return clamp(numeric, 0.0, 1.0)


def percentage(probability: float, digits: int = 2) -> float:
    return round(clamp(to_float(probability), 0.0, 1.0) * 100.0, digits)


def logistic(value: float) -> float:
    x = clamp(to_float(value), -60.0, 60.0)
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def logit(probability: float) -> float:
    p = clamp_probability(probability)
    return math.log(p / (1.0 - p))


def odds(probability: float) -> float:
    p = clamp_probability(probability)
    return p / (1.0 - p)


def probability_from_odds(odds_value: float) -> float:
    value = max(to_float(odds_value), 0.0)
    return safe_divide(value, 1.0 + value)


def log_sum_exp(values: Sequence[float]) -> float:
    if not values:
        return -math.inf
    maximum = max(values)
    if maximum == -math.inf:
        return -math.inf
    return maximum + math.log(sum(math.exp(value - maximum) for value in values))


def softmax(values: Sequence[float]) -> list[float]:
    if not values:
        return []
    denominator = log_sum_exp(values)
    return [math.exp(value - denominator) for value in values]


def normalize_probabilities(
    probabilities: Mapping[str, float],
    *,
    fallback_uniform: bool = True,
) -> dict[str, float]:
    cleaned = {key: max(to_float(value), 0.0) for key, value in probabilities.items()}
    total = sum(cleaned.values())
    if total <= EPSILON:
        if not fallback_uniform or not cleaned:
            return {key: 0.0 for key in cleaned}
        uniform = 1.0 / len(cleaned)
        return {key: uniform for key in cleaned}
    return {key: value / total for key, value in cleaned.items()}


def geometric_mean(values: Sequence[float], weights: Sequence[float] | None = None) -> float:
    if not values:
        return 0.0
    resolved_weights = list(weights or [1.0] * len(values))
    if len(resolved_weights) != len(values):
        raise ProbabilityValidationError("values and weights must have equal length")
    total_weight = sum(max(weight, 0.0) for weight in resolved_weights)
    if total_weight <= EPSILON:
        return 0.0
    weighted_log = 0.0
    for value, weight in zip(values, resolved_weights):
        weighted_log += max(weight, 0.0) * math.log(max(to_float(value), EPSILON))
    return math.exp(weighted_log / total_weight)


def weighted_mean(
    values: Sequence[float],
    weights: Sequence[float] | None = None,
    default: float = 0.0,
) -> float:
    if not values:
        return default
    resolved_weights = list(weights or [1.0] * len(values))
    if len(values) != len(resolved_weights):
        raise ProbabilityValidationError("values and weights must have equal length")
    denominator = sum(max(weight, 0.0) for weight in resolved_weights)
    if denominator <= EPSILON:
        return default
    numerator = sum(to_float(value) * max(weight, 0.0) for value, weight in zip(values, resolved_weights))
    return numerator / denominator


def safe_power(base: float, exponent: float, default: float = 0.0) -> float:
    try:
        result = math.pow(to_float(base), to_float(exponent))
    except (ValueError, OverflowError):
        return default
    return result if math.isfinite(result) else default


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


# ============================================================
# SECTION 07 - DOMAIN DATA STRUCTURES
# ============================================================

@dataclass(slots=True)
class PlayerFeatureProfile:
    player_name: str
    team_name: str | None = None
    player_id: int | str | None = None
    plate_appearances: int | None = None
    at_bats: int | None = None
    hits: int | None = None
    singles: int | None = None
    doubles: int | None = None
    triples: int | None = None
    home_runs: int | None = None
    walks: int | None = None
    hit_by_pitch: int | None = None
    strikeouts: int | None = None
    rbi: int | None = None
    runs: int | None = None
    total_bases: int | None = None
    batting_average: float | None = None
    on_base_percentage: float | None = None
    slugging_percentage: float | None = None
    ops: float | None = None
    woba: float | None = None
    iso: float | None = None
    babip: float | None = None
    barrel_rate: float | None = None
    hard_hit_rate: float | None = None
    average_exit_velocity: float | None = None
    launch_angle: float | None = None
    sweet_spot_rate: float | None = None
    walk_rate: float | None = None
    strikeout_rate: float | None = None
    expected_batting_average: float | None = None
    expected_slugging_percentage: float | None = None
    expected_woba: float | None = None
    recent_plate_appearances: int | None = None
    recent_hits: int | None = None
    recent_home_runs: int | None = None
    recent_walks: int | None = None
    recent_strikeouts: int | None = None
    projected_plate_appearances: float | None = None
    bats: str | None = None
    position: str | None = None

    def resolved_plate_appearances(self) -> float:
        return max(to_float(self.plate_appearances or self.at_bats), 0.0)

    def resolved_at_bats(self) -> float:
        return max(to_float(self.at_bats or self.plate_appearances), 0.0)

    def derived_singles(self) -> float:
        if self.singles is not None:
            return max(to_float(self.singles), 0.0)
        return max(
            to_float(self.hits)
            - to_float(self.doubles)
            - to_float(self.triples)
            - to_float(self.home_runs),
            0.0,
        )

    def derived_total_bases(self) -> float:
        if self.total_bases is not None:
            return max(to_float(self.total_bases), 0.0)
        return (
            self.derived_singles()
            + 2.0 * to_float(self.doubles)
            + 3.0 * to_float(self.triples)
            + 4.0 * to_float(self.home_runs)
        )


@dataclass(slots=True)
class TeamFeatureProfile:
    team_name: str
    team_id: int | str | None = None
    games_played: int | None = None
    wins: int | None = None
    losses: int | None = None
    runs_scored: int | None = None
    runs_allowed: int | None = None
    runs_per_game: float | None = None
    runs_allowed_per_game: float | None = None
    team_ops: float | None = None
    team_woba: float | None = None
    team_home_run_rate: float | None = None
    team_walk_rate: float | None = None
    team_strikeout_rate: float | None = None
    starting_pitcher_quality: float | None = None
    bullpen_quality_score: float | None = None
    bullpen_fatigue_score: float | None = None
    defense_quality_score: float | None = None
    baserunning_quality_score: float | None = None
    lineup_strength_score: float | None = None
    recent_run_differential: float | None = None
    projected_runs: float | None = None


@dataclass(slots=True)
class GameContextProfile:
    opponent_team: str | None = None
    ballpark: str | None = None
    venue_id: int | str | None = None
    home_game: bool | None = None
    opponent_pitcher: str | None = None
    pitcher_era: float | None = None
    pitcher_whip: float | None = None
    pitcher_fip: float | None = None
    pitcher_xfip: float | None = None
    pitcher_strikeout_rate: float | None = None
    pitcher_walk_rate: float | None = None
    pitcher_home_run_rate: float | None = None
    pitcher_hard_hit_rate_allowed: float | None = None
    pitcher_barrel_rate_allowed: float | None = None
    pitcher_hand: str | None = None
    platoon_advantage: float | None = None
    weather_score: float | None = None
    temperature_f: float | None = None
    humidity_pct: float | None = None
    wind_speed_mph: float | None = None
    wind_out_component: float | None = None
    park_factor: float | None = None
    run_park_factor: float | None = None
    hit_park_factor: float | None = None
    home_run_park_factor: float | None = None
    rest_days: float | None = None
    travel_miles: float | None = None
    timezone_change_hours: float | None = None
    lineup_slot: int | None = None
    expected_plate_appearances: float | None = None
    game_datetime: datetime | str | None = None


@dataclass(slots=True)
class ProbabilityInterval:
    lower: float
    mean: float
    upper: float
    confidence_level: float = DEFAULT_CONFIDENCE_LEVEL
    method: str = "normal_approximation"

    def to_dict(self) -> dict[str, float | str]:
        return {
            "lower": round(self.lower, 8),
            "mean": round(self.mean, 8),
            "upper": round(self.upper, 8),
            "confidence_level": self.confidence_level,
            "method": self.method,
        }


@dataclass(slots=True)
class BetaPosterior:
    alpha: float
    beta: float
    successes: float
    trials: float
    prior_mean: float
    prior_strength: float

    @property
    def mean(self) -> float:
        return safe_divide(self.alpha, self.alpha + self.beta, self.prior_mean)

    @property
    def variance(self) -> float:
        total = self.alpha + self.beta
        return safe_divide(self.alpha * self.beta, total * total * (total + 1.0), 0.0)

    @property
    def standard_deviation(self) -> float:
        return math.sqrt(max(self.variance, 0.0))

    @property
    def effective_sample_size(self) -> float:
        return self.alpha + self.beta

    def interval(self, confidence_level: float = DEFAULT_CONFIDENCE_LEVEL) -> ProbabilityInterval:
        z = normal_quantile(0.5 + confidence_level / 2.0)
        margin = z * self.standard_deviation
        return ProbabilityInterval(
            lower=clamp(self.mean - margin, 0.0, 1.0),
            mean=self.mean,
            upper=clamp(self.mean + margin, 0.0, 1.0),
            confidence_level=confidence_level,
            method="beta_normal_approximation",
        )


@dataclass(slots=True)
class AdjustmentFactor:
    name: str
    factor: float = 1.0
    log_odds_delta: float = 0.0
    weight: float = 1.0
    source: str = ""
    explanation: str = ""
    bounded: bool = True


@dataclass(slots=True)
class ProbabilityEstimate:
    outcome: str
    probability: float
    base_probability: float
    unit: ProbabilityUnit
    interval: ProbabilityInterval
    confidence: float
    confidence_band: ConfidenceBand
    expected_value: float | None = None
    variance: float | None = None
    adjustments: list[AdjustmentFactor] = field(default_factory=list)
    components: dict[str, float] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    model_status: str = ENGINE_STATUS

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": ENGINE_NAME,
            "engine_version": ENGINE_VERSION,
            "phase": ENGINE_PHASE,
            "outcome": self.outcome,
            "probability": percentage(self.probability),
            "probability_decimal": round(self.probability, 8),
            "base_probability": percentage(self.base_probability),
            "base_probability_decimal": round(self.base_probability, 8),
            "unit": self.unit.value,
            "interval": self.interval.to_dict(),
            "confidence": round(self.confidence, 2),
            "confidence_band": self.confidence_band.value,
            "expected_value": None if self.expected_value is None else round(self.expected_value, 8),
            "variance": None if self.variance is None else round(self.variance, 8),
            "adjustments": [asdict(item) for item in self.adjustments],
            "components": {key: round(value, 8) for key, value in self.components.items()},
            "diagnostics": self.diagnostics,
            "warnings": self.warnings,
            "model_status": self.model_status,
        }


@dataclass(slots=True)
class OutcomeDistribution:
    probabilities: dict[str, float]
    expected_total_bases: float
    expected_on_base: float
    entropy: float
    checksum: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "probabilities": {key: round(value, 8) for key, value in self.probabilities.items()},
            "expected_total_bases": round(self.expected_total_bases, 8),
            "expected_on_base": round(self.expected_on_base, 8),
            "entropy": round(self.entropy, 8),
            "checksum": self.checksum,
        }


@dataclass(slots=True)
class TeamWinEstimate:
    home_win_probability: float
    away_win_probability: float
    expected_home_runs: float
    expected_away_runs: float
    expected_run_differential: float
    interval: ProbabilityInterval
    method: str
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "home_win_probability": percentage(self.home_win_probability),
            "home_win_probability_decimal": round(self.home_win_probability, 8),
            "away_win_probability": percentage(self.away_win_probability),
            "away_win_probability_decimal": round(self.away_win_probability, 8),
            "expected_home_runs": round(self.expected_home_runs, 4),
            "expected_away_runs": round(self.expected_away_runs, 4),
            "expected_run_differential": round(self.expected_run_differential, 4),
            "interval": self.interval.to_dict(),
            "method": self.method,
            "diagnostics": self.diagnostics,
        }


# ============================================================
# SECTION 08 - ENGINE CONFIGURATION
# ============================================================

@dataclass(slots=True)
class ProbabilityEngineConfig:
    prior_strength: float = DEFAULT_PRIOR_STRENGTH
    recent_prior_strength: float = 35.0
    recent_weight: float = 0.20
    statcast_weight: float = 0.18
    matchup_weight: float = 0.12
    context_weight: float = 1.0
    default_plate_appearances: float = DEFAULT_EXPECTED_PLATE_APPEARANCES
    confidence_level: float = DEFAULT_CONFIDENCE_LEVEL
    minimum_probability: float = 0.0001
    maximum_probability: float = 0.9999
    strict_outcomes: bool = False
    apply_context: bool = True
    apply_recent_form: bool = True
    apply_statcast: bool = True
    preserve_partition: bool = True
    random_seed: int = DEFAULT_RANDOM_SEED

    def validate(self) -> None:
        if self.prior_strength < 0:
            raise ProbabilityValidationError("prior_strength cannot be negative")
        if self.recent_prior_strength < 0:
            raise ProbabilityValidationError("recent_prior_strength cannot be negative")
        if not 0.0 < self.confidence_level < 1.0:
            raise ProbabilityValidationError("confidence_level must be between zero and one")
        if self.minimum_probability < 0 or self.maximum_probability > 1:
            raise ProbabilityValidationError("probability bounds must fall inside [0, 1]")
        if self.minimum_probability >= self.maximum_probability:
            raise ProbabilityValidationError("minimum_probability must be less than maximum_probability")
        if self.default_plate_appearances <= 0:
            raise ProbabilityValidationError("default_plate_appearances must be positive")


# ============================================================
# SECTION 09 - NORMAL DISTRIBUTION UTILITIES
# ============================================================

def normal_cdf(value: float, mean: float = 0.0, standard_deviation: float = 1.0) -> float:
    if standard_deviation <= 0:
        return float(value >= mean)
    z = (value - mean) / (standard_deviation * math.sqrt(2.0))
    return 0.5 * (1.0 + math.erf(z))


def normal_pdf(value: float, mean: float = 0.0, standard_deviation: float = 1.0) -> float:
    if standard_deviation <= 0:
        return 0.0
    z = (value - mean) / standard_deviation
    return math.exp(-0.5 * z * z) / (standard_deviation * math.sqrt(2.0 * math.pi))


def normal_quantile(probability: float) -> float:
    """Acklam rational approximation for the inverse standard-normal CDF."""
    p = clamp_probability(probability)
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )
    p_low = 0.02425
    p_high = 1.0 - p_low
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q) + 1.0
        )
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r) + 1.0
        )
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
        ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q) + 1.0
    )


# ============================================================
# SECTION 10 - COMBINATORICS AND DISCRETE DISTRIBUTIONS
# ============================================================

def log_factorial(value: int) -> float:
    if value < 0:
        return math.inf
    return math.lgamma(value + 1.0)


def log_combination(n: int, k: int) -> float:
    if k < 0 or n < 0 or k > n:
        return -math.inf
    return log_factorial(n) - log_factorial(k) - log_factorial(n - k)


def bernoulli_pmf(success: int | bool, probability: float) -> float:
    p = clamp_probability(probability)
    return p if bool(success) else 1.0 - p


def binomial_pmf(successes: int, trials: int, probability: float) -> float:
    if trials < 0 or successes < 0 or successes > trials:
        return 0.0
    p = clamp_probability(probability)
    log_probability = (
        log_combination(trials, successes)
        + successes * math.log(p)
        + (trials - successes) * math.log(1.0 - p)
    )
    return math.exp(max(log_probability, -MAX_EXPONENT))


def binomial_cdf(successes: int, trials: int, probability: float) -> float:
    if successes < 0:
        return 0.0
    if successes >= trials:
        return 1.0
    return clamp(sum(binomial_pmf(k, trials, probability) for k in range(successes + 1)), 0.0, 1.0)


def probability_at_least_one(probability: float, opportunities: float) -> float:
    p = clamp(to_float(probability), 0.0, 1.0)
    n = max(to_float(opportunities), 0.0)
    return clamp(1.0 - math.pow(1.0 - p, n), 0.0, 1.0)


def expected_binomial_count(probability: float, opportunities: float) -> float:
    return max(to_float(opportunities), 0.0) * clamp(to_float(probability), 0.0, 1.0)


def binomial_variance(probability: float, opportunities: float) -> float:
    p = clamp(to_float(probability), 0.0, 1.0)
    n = max(to_float(opportunities), 0.0)
    return n * p * (1.0 - p)


def poisson_pmf(count: int, rate: float) -> float:
    if count < 0:
        return 0.0
    lam = max(to_float(rate), 0.0)
    if lam <= EPSILON:
        return 1.0 if count == 0 else 0.0
    log_probability = count * math.log(lam) - lam - log_factorial(count)
    return math.exp(max(log_probability, -MAX_EXPONENT))


def poisson_cdf(count: int, rate: float) -> float:
    if count < 0:
        return 0.0
    return clamp(sum(poisson_pmf(k, rate) for k in range(count + 1)), 0.0, 1.0)


def poisson_survival(count: int, rate: float) -> float:
    return clamp(1.0 - poisson_cdf(count, rate), 0.0, 1.0)


def negative_binomial_pmf(count: int, mean: float, dispersion: float) -> float:
    if count < 0 or mean < 0 or dispersion <= 0:
        return 0.0
    if mean <= EPSILON:
        return 1.0 if count == 0 else 0.0
    r = dispersion
    p = r / (r + mean)
    log_probability = (
        math.lgamma(count + r)
        - math.lgamma(r)
        - math.lgamma(count + 1.0)
        + r * math.log(p)
        + count * math.log(1.0 - p)
    )
    return math.exp(max(log_probability, -MAX_EXPONENT))


# ============================================================
# SECTION 11 - BAYESIAN RATE ESTIMATION
# ============================================================

def beta_prior(prior_mean: float, prior_strength: float) -> tuple[float, float]:
    mean_value = clamp_probability(prior_mean)
    strength = max(to_float(prior_strength), EPSILON)
    return mean_value * strength, (1.0 - mean_value) * strength


def beta_binomial_posterior(
    successes: float,
    trials: float,
    *,
    prior_mean: float,
    prior_strength: float = DEFAULT_PRIOR_STRENGTH,
) -> BetaPosterior:
    resolved_trials = max(to_float(trials), 0.0)
    resolved_successes = clamp(to_float(successes), 0.0, resolved_trials)
    alpha_prior, beta_prior_value = beta_prior(prior_mean, prior_strength)
    return BetaPosterior(
        alpha=alpha_prior + resolved_successes,
        beta=beta_prior_value + resolved_trials - resolved_successes,
        successes=resolved_successes,
        trials=resolved_trials,
        prior_mean=prior_mean,
        prior_strength=prior_strength,
    )


def empirical_bayes_rate(
    successes: float,
    trials: float,
    prior_mean: float,
    prior_strength: float = DEFAULT_PRIOR_STRENGTH,
) -> float:
    return beta_binomial_posterior(
        successes,
        trials,
        prior_mean=prior_mean,
        prior_strength=prior_strength,
    ).mean


def blend_rates(
    rates: Sequence[float],
    weights: Sequence[float] | None = None,
    *,
    method: CombinationMethod = CombinationMethod.LOG_ODDS,
) -> float:
    if not rates:
        raise ProbabilityValidationError("at least one rate is required")
    resolved_weights = list(weights or [1.0] * len(rates))
    if len(resolved_weights) != len(rates):
        raise ProbabilityValidationError("rates and weights must have equal length")
    if method == CombinationMethod.WEIGHTED_AVERAGE:
        return clamp(weighted_mean(rates, resolved_weights), 0.0, 1.0)
    if method == CombinationMethod.GEOMETRIC:
        return clamp(geometric_mean(rates, resolved_weights), 0.0, 1.0)
    if method == CombinationMethod.MULTIPLICATIVE:
        result = 1.0
        for rate in rates:
            result *= clamp_probability(rate)
        return clamp(result, 0.0, 1.0)
    logits = [logit(rate) for rate in rates]
    return logistic(weighted_mean(logits, resolved_weights))


# ============================================================
# SECTION 12 - ENTROPY, INFORMATION, AND SCORING RULES
# ============================================================

def binary_entropy(probability: float) -> float:
    p = clamp_probability(probability)
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def categorical_entropy(probabilities: Iterable[float]) -> float:
    normalized = normalize_probabilities({str(index): value for index, value in enumerate(probabilities)})
    return -sum(value * math.log2(max(value, EPSILON)) for value in normalized.values())


def brier_score(probability: float, observed: int | bool) -> float:
    return (clamp(to_float(probability), 0.0, 1.0) - float(bool(observed))) ** 2


def log_loss(probability: float, observed: int | bool) -> float:
    p = clamp_probability(probability)
    return -math.log(p if bool(observed) else 1.0 - p)


def multiclass_log_loss(probabilities: Mapping[str, float], observed_label: str) -> float:
    normalized = normalize_probabilities(probabilities)
    return -math.log(max(normalized.get(observed_label, 0.0), EPSILON))


# ============================================================
# SECTION 13 - BASE PLAYER RATE CALCULATIONS
# ============================================================

def _rate_bounds(outcome: str) -> tuple[float, float]:
    return OUTCOME_BOUNDS.get(outcome, (0.0001, 0.9999))


def _bounded_outcome_rate(outcome: str, value: float) -> float:
    minimum, maximum = _rate_bounds(outcome)
    return clamp(value, minimum, maximum)


def _posterior_rate(
    outcome: str,
    successes: float,
    trials: float,
    prior_strength: float = DEFAULT_PRIOR_STRENGTH,
) -> float:
    return _bounded_outcome_rate(
        outcome,
        empirical_bayes_rate(
            successes,
            trials,
            LEAGUE_PRIORS.get(outcome, 0.10),
            prior_strength,
        ),
    )


def calculate_hit_rate(player: PlayerFeatureProfile) -> float:
    trials = player.resolved_at_bats()
    if player.hits is not None and trials > 0:
        observed = _posterior_rate("hit", to_float(player.hits), trials)
    elif player.batting_average is not None:
        observed = _bounded_outcome_rate("hit", normalize_rate(player.batting_average, LEAGUE_PRIORS["hit"]))
    else:
        observed = LEAGUE_PRIORS["hit"]
    if player.expected_batting_average is not None:
        observed = blend_rates(
            [observed, normalize_rate(player.expected_batting_average, observed)],
            [0.78, 0.22],
        )
    return _bounded_outcome_rate("hit", observed)


def calculate_single_rate(player: PlayerFeatureProfile) -> float:
    trials = player.resolved_at_bats()
    if trials > 0:
        return _posterior_rate("single", player.derived_singles(), trials)
    return _bounded_outcome_rate(
        "single",
        calculate_hit_rate(player)
        - calculate_double_rate(player)
        - calculate_triple_rate(player)
        - calculate_home_run_rate(player),
    )


def calculate_double_rate(player: PlayerFeatureProfile) -> float:
    return _posterior_rate("double", to_float(player.doubles), player.resolved_at_bats())


def calculate_triple_rate(player: PlayerFeatureProfile) -> float:
    return _posterior_rate("triple", to_float(player.triples), player.resolved_at_bats())


def calculate_home_run_rate(player: PlayerFeatureProfile) -> float:
    trials = player.resolved_plate_appearances()
    base_rate = _posterior_rate("home_run", to_float(player.home_runs), trials)
    statcast_rates: list[float] = [base_rate]
    weights: list[float] = [0.72]
    if player.barrel_rate is not None:
        barrel = normalize_rate(player.barrel_rate, 0.08)
        statcast_rates.append(clamp(barrel * 0.42, 0.002, 0.180))
        weights.append(0.16)
    if player.hard_hit_rate is not None:
        hard_hit = normalize_rate(player.hard_hit_rate, 0.38)
        statcast_rates.append(clamp((hard_hit - 0.20) * 0.13, 0.002, 0.120))
        weights.append(0.07)
    if player.expected_slugging_percentage is not None:
        xslg = normalize_rate(player.expected_slugging_percentage, 0.400)
        statcast_rates.append(clamp((xslg - 0.250) * 0.10, 0.002, 0.150))
        weights.append(0.05)
    return _bounded_outcome_rate(
        "home_run",
        blend_rates(statcast_rates, weights, method=CombinationMethod.WEIGHTED_AVERAGE),
    )


def calculate_walk_rate(player: PlayerFeatureProfile) -> float:
    if player.walk_rate is not None:
        direct = normalize_rate(player.walk_rate, LEAGUE_PRIORS["walk"])
        return _bounded_outcome_rate("walk", direct)
    return _posterior_rate("walk", to_float(player.walks), player.resolved_plate_appearances())


def calculate_strikeout_rate(player: PlayerFeatureProfile) -> float:
    if player.strikeout_rate is not None:
        direct = normalize_rate(player.strikeout_rate, LEAGUE_PRIORS["strikeout"])
        return _bounded_outcome_rate("strikeout", direct)
    return _posterior_rate("strikeout", to_float(player.strikeouts), player.resolved_plate_appearances())


def calculate_rbi_rate(player: PlayerFeatureProfile) -> float:
    return _posterior_rate("rbi", to_float(player.rbi), player.resolved_plate_appearances())


def calculate_run_rate(player: PlayerFeatureProfile) -> float:
    return _posterior_rate("run", to_float(player.runs), player.resolved_plate_appearances())


def calculate_extra_base_rate(player: PlayerFeatureProfile) -> float:
    successes = to_float(player.doubles) + to_float(player.triples) + to_float(player.home_runs)
    return _posterior_rate("extra_base_hit", successes, player.resolved_at_bats())


def calculate_reach_base_rate(player: PlayerFeatureProfile) -> float:
    if player.on_base_percentage is not None:
        return _bounded_outcome_rate(
            "reach_base",
            normalize_rate(player.on_base_percentage, LEAGUE_PRIORS["reach_base"]),
        )
    successes = to_float(player.hits) + to_float(player.walks) + to_float(player.hit_by_pitch)
    return _posterior_rate("reach_base", successes, player.resolved_plate_appearances())


def calculate_total_bases_rate(player: PlayerFeatureProfile) -> float:
    return _bounded_outcome_rate(
        "total_bases",
        safe_divide(player.derived_total_bases(), player.resolved_plate_appearances(), LEAGUE_PRIORS["total_bases"]),
    )


# ============================================================
# SECTION 14 - COHERENT PLATE APPEARANCE DISTRIBUTION
# ============================================================

def build_plate_appearance_distribution(player: PlayerFeatureProfile) -> OutcomeDistribution:
    raw = {
        "single": calculate_single_rate(player),
        "double": calculate_double_rate(player),
        "triple": calculate_triple_rate(player),
        "home_run": calculate_home_run_rate(player),
        "walk": calculate_walk_rate(player),
        "strikeout": calculate_strikeout_rate(player),
    }
    occupied = sum(raw.values())
    raw["other_out"] = max(1.0 - occupied, 0.01)
    normalized = normalize_probabilities(raw)
    expected_total_bases = (
        normalized["single"]
        + 2.0 * normalized["double"]
        + 3.0 * normalized["triple"]
        + 4.0 * normalized["home_run"]
    )
    expected_on_base = (
        normalized["single"]
        + normalized["double"]
        + normalized["triple"]
        + normalized["home_run"]
        + normalized["walk"]
    )
    return OutcomeDistribution(
        probabilities=normalized,
        expected_total_bases=expected_total_bases,
        expected_on_base=expected_on_base,
        entropy=categorical_entropy(normalized.values()),
        checksum=stable_hash(normalized),
    )


# ============================================================
# SECTION 15 - CONTEXT ADJUSTMENT FACTORS
# ============================================================

def calculate_park_adjustment(
    context: GameContextProfile | None,
    outcome: str | None = None,
) -> float:
    if context is None:
        return 1.0
    normalized = normalize_outcome(outcome or "hit")
    if normalized == "home_run" and context.home_run_park_factor is not None:
        value = context.home_run_park_factor
    elif normalized in {"hit", "single", "double", "triple"} and context.hit_park_factor is not None:
        value = context.hit_park_factor
    elif normalized in {"rbi", "run", "team_runs"} and context.run_park_factor is not None:
        value = context.run_park_factor
    else:
        value = context.park_factor
    if value is None:
        return 1.0
    numeric = to_float(value, 1.0)
    if numeric > 10.0:
        numeric /= 100.0
    return clamp(numeric, 0.75, 1.30)


def calculate_pitcher_adjustment(
    outcome: str,
    context: GameContextProfile | None,
) -> float:
    if context is None:
        return 1.0
    normalized = normalize_outcome(outcome)
    deltas: list[float] = []
    weights: list[float] = []
    if context.pitcher_era is not None and normalized in {
        "hit", "single", "double", "triple", "home_run", "rbi", "run", "total_bases"
    }:
        deltas.append(clamp((to_float(context.pitcher_era) - 4.20) * 0.045, -0.22, 0.22))
        weights.append(0.28)
    if context.pitcher_whip is not None and normalized in {"hit", "walk", "rbi", "run", "reach_base"}:
        deltas.append(clamp((to_float(context.pitcher_whip) - 1.28) * 0.24, -0.20, 0.20))
        weights.append(0.24)
    if context.pitcher_strikeout_rate is not None:
        k_rate = normalize_rate(context.pitcher_strikeout_rate, LEAGUE_PRIORS["strikeout"])
        if normalized == "strikeout":
            deltas.append(clamp((k_rate - 0.225) * 1.80, -0.30, 0.30))
            weights.append(0.32)
        elif normalized in {"hit", "home_run", "total_bases"}:
            deltas.append(clamp(-(k_rate - 0.225) * 0.80, -0.16, 0.16))
            weights.append(0.20)
    if context.pitcher_walk_rate is not None and normalized in {"walk", "reach_base", "run"}:
        walk_rate = normalize_rate(context.pitcher_walk_rate, LEAGUE_PRIORS["walk"])
        deltas.append(clamp((walk_rate - 0.083) * 1.50, -0.18, 0.18))
        weights.append(0.20)
    if context.pitcher_home_run_rate is not None and normalized == "home_run":
        home_run_rate = normalize_rate(context.pitcher_home_run_rate, LEAGUE_PRIORS["home_run"])
        deltas.append(clamp((home_run_rate - 0.032) * 3.50, -0.20, 0.20))
        weights.append(0.25)
    if context.pitcher_hard_hit_rate_allowed is not None and normalized in {"hit", "home_run", "total_bases"}:
        hard_hit = normalize_rate(context.pitcher_hard_hit_rate_allowed, 0.38)
        deltas.append(clamp((hard_hit - 0.38) * 0.60, -0.12, 0.12))
        weights.append(0.12)
    if not deltas:
        return 1.0
    delta = weighted_mean(deltas, weights)
    return clamp(math.exp(delta), 0.68, 1.38)


def calculate_team_context_adjustment(
    outcome: str,
    team: TeamFeatureProfile | None,
) -> float:
    if team is None:
        return 1.0
    normalized = normalize_outcome(outcome)
    deltas: list[float] = []
    weights: list[float] = []
    if normalized in {"rbi", "run", "team_runs"} and team.runs_per_game is not None:
        deltas.append(clamp((to_float(team.runs_per_game) - 4.40) * 0.055, -0.20, 0.20))
        weights.append(0.35)
    if normalized in {"hit", "home_run", "total_bases", "rbi", "run"} and team.team_ops is not None:
        deltas.append(clamp((to_float(team.team_ops) - 0.720) * 0.75, -0.16, 0.16))
        weights.append(0.25)
    if normalized in {"rbi", "run", "team_runs"} and team.lineup_strength_score is not None:
        score = to_float(team.lineup_strength_score)
        if score > 1.0:
            score /= 100.0
        deltas.append(clamp((score - 0.50) * 0.35, -0.16, 0.16))
        weights.append(0.25)
    if not deltas:
        return 1.0
    return clamp(math.exp(weighted_mean(deltas, weights)), 0.72, 1.32)


def calculate_home_field_adjustment(context: GameContextProfile | None) -> float:
    if context is None or context.home_game is None:
        return 1.0
    return 1.018 if context.home_game else 0.990


def calculate_weather_adjustment(
    outcome: str,
    context: GameContextProfile | None,
) -> float:
    if context is None:
        return 1.0
    normalized = normalize_outcome(outcome)
    if normalized not in {"hit", "double", "triple", "home_run", "rbi", "run", "total_bases", "team_runs"}:
        return 1.0
    delta = 0.0
    if context.temperature_f is not None:
        delta += clamp((to_float(context.temperature_f) - 72.0) * 0.0018, -0.055, 0.065)
    if context.wind_out_component is not None:
        delta += clamp(to_float(context.wind_out_component) * 0.0040, -0.075, 0.075)
    elif context.wind_speed_mph is not None and context.weather_score is not None:
        delta += clamp(to_float(context.wind_speed_mph) * (to_float(context.weather_score) - 0.5) * 0.003, -0.05, 0.05)
    if context.humidity_pct is not None:
        delta += clamp((to_float(context.humidity_pct) - 55.0) * -0.0004, -0.020, 0.020)
    return clamp(math.exp(delta), 0.85, 1.16)


def calculate_schedule_adjustment(
    outcome: str,
    context: GameContextProfile | None,
) -> float:
    if context is None:
        return 1.0
    normalized = normalize_outcome(outcome)
    if normalized not in SUPPORTED_OUTCOMES:
        return 1.0
    delta = 0.0
    if context.rest_days is not None:
        rest = to_float(context.rest_days)
        if rest <= 0:
            delta -= 0.025
        elif rest >= 2:
            delta += 0.010
    if context.travel_miles is not None:
        delta -= clamp(math.log1p(max(to_float(context.travel_miles), 0.0)) / 450.0, 0.0, 0.025)
    if context.timezone_change_hours is not None:
        delta -= clamp(abs(to_float(context.timezone_change_hours)) * 0.008, 0.0, 0.030)
    return clamp(math.exp(delta), 0.90, 1.08)


def calculate_lineup_adjustment(
    outcome: str,
    context: GameContextProfile | None,
) -> float:
    if context is None or context.lineup_slot is None:
        return 1.0
    slot = int(clamp(to_float(context.lineup_slot), 1.0, 9.0))
    plate_appearance_factors = {
        1: 1.045,
        2: 1.035,
        3: 1.025,
        4: 1.020,
        5: 1.005,
        6: 0.990,
        7: 0.975,
        8: 0.960,
        9: 0.950,
    }
    if normalize_outcome(outcome) in {"rbi"}:
        return {1: 0.96, 2: 0.99, 3: 1.04, 4: 1.07, 5: 1.04, 6: 1.01, 7: 0.98, 8: 0.96, 9: 0.94}[slot]
    return plate_appearance_factors[slot]


def calculate_platoon_adjustment(
    outcome: str,
    context: GameContextProfile | None,
) -> float:
    if context is None or context.platoon_advantage is None:
        return 1.0
    advantage = clamp(to_float(context.platoon_advantage), -1.0, 1.0)
    sensitivity = 0.06 if normalize_outcome(outcome) != "strikeout" else -0.045
    return clamp(math.exp(advantage * sensitivity), 0.90, 1.10)


# ============================================================
# SECTION 16 - RECENT FORM AND STATCAST BLENDING
# ============================================================

def calculate_recent_form_rate(
    outcome: str,
    player: PlayerFeatureProfile,
    *,
    prior_strength: float = 35.0,
) -> float | None:
    trials = max(to_float(player.recent_plate_appearances), 0.0)
    if trials <= 0:
        return None
    normalized = normalize_outcome(outcome)
    success_map = {
        "hit": player.recent_hits,
        "home_run": player.recent_home_runs,
        "walk": player.recent_walks,
        "strikeout": player.recent_strikeouts,
    }
    success_value = success_map.get(normalized)
    if success_value is None:
        return None
    return _posterior_rate(normalized, to_float(success_value), trials, prior_strength)


def calculate_statcast_rate(outcome: str, player: PlayerFeatureProfile) -> float | None:
    normalized = normalize_outcome(outcome)
    estimates: list[float] = []
    weights: list[float] = []
    if normalized == "hit" and player.expected_batting_average is not None:
        estimates.append(normalize_rate(player.expected_batting_average, LEAGUE_PRIORS["hit"]))
        weights.append(0.60)
    if normalized in {"home_run", "extra_base_hit", "total_bases"}:
        if player.barrel_rate is not None:
            estimates.append(clamp(normalize_rate(player.barrel_rate, 0.08) * 0.42, 0.002, 0.20))
            weights.append(0.45)
        if player.hard_hit_rate is not None:
            estimates.append(clamp((normalize_rate(player.hard_hit_rate, 0.38) - 0.18) * 0.16, 0.002, 0.20))
            weights.append(0.25)
        if player.expected_slugging_percentage is not None:
            xslg = normalize_rate(player.expected_slugging_percentage, 0.400)
            if normalized == "home_run":
                estimates.append(clamp((xslg - 0.250) * 0.10, 0.002, 0.18))
            else:
                estimates.append(clamp(xslg, 0.05, 0.80))
            weights.append(0.30)
    if normalized == "reach_base" and player.expected_woba is not None:
        estimates.append(clamp(normalize_rate(player.expected_woba, 0.315), 0.10, 0.60))
        weights.append(1.0)
    if not estimates:
        return None
    return clamp(weighted_mean(estimates, weights), 0.0, 1.0)


# ============================================================
# SECTION 17 - OUTCOME NORMALIZATION AND BASE PROBABILITY API
# ============================================================

def normalize_outcome(outcome: str) -> str:
    normalized = str(outcome or "hit").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "hr": "home_run",
        "homer": "home_run",
        "homerun": "home_run",
        "so": "strikeout",
        "k": "strikeout",
        "bb": "walk",
        "xbh": "extra_base_hit",
        "on_base": "reach_base",
        "total_base": "total_bases",
        "win": "team_win",
        "runs_scored": "team_runs",
    }
    return aliases.get(normalized, normalized)


def calculate_base_probability(outcome: str, player: PlayerFeatureProfile) -> float:
    normalized = normalize_outcome(outcome)
    calculators = {
        "hit": calculate_hit_rate,
        "single": calculate_single_rate,
        "double": calculate_double_rate,
        "triple": calculate_triple_rate,
        "home_run": calculate_home_run_rate,
        "walk": calculate_walk_rate,
        "strikeout": calculate_strikeout_rate,
        "rbi": calculate_rbi_rate,
        "run": calculate_run_rate,
        "reach_base": calculate_reach_base_rate,
        "extra_base_hit": calculate_extra_base_rate,
        "total_bases": calculate_total_bases_rate,
    }
    calculator = calculators.get(normalized)
    if calculator is None:
        return LEAGUE_PRIORS.get(normalized, 0.10)
    return calculator(player)


# ============================================================
# SECTION 18 - LOG-ODDS ADJUSTMENT ENGINE
# ============================================================

def apply_adjustments_log_odds(
    base_probability: float,
    adjustments: Sequence[AdjustmentFactor],
    *,
    minimum: float = 0.0001,
    maximum: float = 0.9999,
) -> float:
    base_logit = logit(base_probability)
    total_delta = 0.0
    for adjustment in adjustments:
        if adjustment.log_odds_delta:
            delta = adjustment.log_odds_delta
        else:
            factor = max(adjustment.factor, EPSILON)
            delta = math.log(factor)
        total_delta += delta * max(adjustment.weight, 0.0)
    return clamp(logistic(base_logit + total_delta), minimum, maximum)


def build_context_adjustments(
    outcome: str,
    team: TeamFeatureProfile | None,
    context: GameContextProfile | None,
) -> list[AdjustmentFactor]:
    factors = [
        AdjustmentFactor(
            name="park",
            factor=calculate_park_adjustment(context, outcome),
            weight=1.0,
            source="park_factor",
            explanation="Outcome-specific ballpark environment.",
        ),
        AdjustmentFactor(
            name="opponent_pitcher",
            factor=calculate_pitcher_adjustment(outcome, context),
            weight=1.0,
            source="pitcher_profile",
            explanation="Opponent pitcher run prevention and contact profile.",
        ),
        AdjustmentFactor(
            name="team_offense",
            factor=calculate_team_context_adjustment(outcome, team),
            weight=0.75,
            source="team_profile",
            explanation="Lineup and team run-production environment.",
        ),
        AdjustmentFactor(
            name="home_field",
            factor=calculate_home_field_adjustment(context),
            weight=0.55,
            source="home_away",
            explanation="Small home or away environment adjustment.",
        ),
        AdjustmentFactor(
            name="weather",
            factor=calculate_weather_adjustment(outcome, context),
            weight=0.70,
            source="weather",
            explanation="Temperature, humidity, and wind effects.",
        ),
        AdjustmentFactor(
            name="schedule",
            factor=calculate_schedule_adjustment(outcome, context),
            weight=0.50,
            source="rest_travel",
            explanation="Rest, travel, and time-zone effects.",
        ),
        AdjustmentFactor(
            name="lineup_slot",
            factor=calculate_lineup_adjustment(outcome, context),
            weight=0.65,
            source="lineup_slot",
            explanation="Expected opportunity and batting-order context.",
        ),
        AdjustmentFactor(
            name="platoon",
            factor=calculate_platoon_adjustment(outcome, context),
            weight=0.70,
            source="platoon_advantage",
            explanation="Batter-pitcher handedness advantage.",
        ),
    ]
    return factors


# ============================================================
# SECTION 19 - CONFIDENCE AND UNCERTAINTY MODEL
# ============================================================

def confidence_band(score: float) -> ConfidenceBand:
    if score >= 85.0:
        return ConfidenceBand.VERY_HIGH
    if score >= 70.0:
        return ConfidenceBand.HIGH
    if score >= 52.0:
        return ConfidenceBand.MODERATE
    return ConfidenceBand.LOW


def calculate_prediction_confidence(
    player: PlayerFeatureProfile,
    team: TeamFeatureProfile | None = None,
    context: GameContextProfile | None = None,
) -> float:
    plate_appearances = player.resolved_plate_appearances()
    sample_score = 1.0 - math.exp(-plate_appearances / 260.0)
    completeness_fields = (
        player.ops,
        player.barrel_rate,
        player.hard_hit_rate,
        player.walk_rate,
        player.strikeout_rate,
        player.expected_batting_average,
        player.expected_slugging_percentage,
    )
    completeness = sum(value is not None for value in completeness_fields) / len(completeness_fields)
    context_fields = () if context is None else (
        context.opponent_pitcher,
        context.pitcher_era,
        context.pitcher_whip,
        context.pitcher_strikeout_rate,
        context.park_factor,
        context.temperature_f,
        context.lineup_slot,
    )
    context_completeness = 0.0 if not context_fields else sum(value is not None for value in context_fields) / len(context_fields)
    team_completeness = 0.0 if team is None else sum(
        value is not None
        for value in (team.runs_per_game, team.team_ops, team.team_woba, team.lineup_strength_score)
    ) / 4.0
    score = 30.0 + 38.0 * sample_score + 14.0 * completeness + 11.0 * context_completeness + 7.0 * team_completeness
    return round(clamp(score, 25.0, 96.0), 2)


def probability_interval_from_effective_sample(
    probability: float,
    effective_sample_size: float,
    confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
) -> ProbabilityInterval:
    p = clamp(to_float(probability), 0.0, 1.0)
    n = max(to_float(effective_sample_size), 1.0)
    z = normal_quantile(0.5 + confidence_level / 2.0)
    denominator = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denominator
    margin = z * math.sqrt(max(p * (1.0 - p) / n + z * z / (4.0 * n * n), 0.0)) / denominator
    return ProbabilityInterval(
        lower=clamp(center - margin, 0.0, 1.0),
        mean=p,
        upper=clamp(center + margin, 0.0, 1.0),
        confidence_level=confidence_level,
        method="wilson_score",
    )


# ============================================================
# SECTION 20 - CORE PLAYER PROBABILITY ESTIMATION
# ============================================================

class ProbabilityEngine:
    """Primary mathematical probability service used by downstream engines."""

    def __init__(self, config: ProbabilityEngineConfig | None = None) -> None:
        self.config = config or ProbabilityEngineConfig()
        self.config.validate()
        self._random = random.Random(self.config.random_seed)

    def estimate_player_outcome(
        self,
        outcome: str,
        player: PlayerFeatureProfile,
        team: TeamFeatureProfile | None = None,
        context: GameContextProfile | None = None,
        *,
        unit: ProbabilityUnit = ProbabilityUnit.PER_PLATE_APPEARANCE,
        opportunities: float | None = None,
    ) -> ProbabilityEstimate:
        normalized = normalize_outcome(outcome)
        if normalized not in SUPPORTED_OUTCOMES:
            if self.config.strict_outcomes:
                raise UnsupportedOutcomeError(f"Unsupported outcome: {outcome}")
            normalized = "hit"

        base_probability = calculate_base_probability(normalized, player)
        component_rates: dict[str, float] = {"career": base_probability}
        blend_values = [base_probability]
        blend_weights = [1.0]

        if self.config.apply_recent_form:
            recent = calculate_recent_form_rate(
                normalized,
                player,
                prior_strength=self.config.recent_prior_strength,
            )
            if recent is not None:
                component_rates["recent"] = recent
                blend_values.append(recent)
                blend_weights.append(self.config.recent_weight)

        if self.config.apply_statcast:
            statcast = calculate_statcast_rate(normalized, player)
            if statcast is not None:
                component_rates["statcast"] = statcast
                blend_values.append(statcast)
                blend_weights.append(self.config.statcast_weight)

        blended_probability = blend_rates(
            blend_values,
            blend_weights,
            method=CombinationMethod.LOG_ODDS,
        )

        adjustments = build_context_adjustments(normalized, team, context) if self.config.apply_context else []
        adjusted_per_opportunity = apply_adjustments_log_odds(
            blended_probability,
            adjustments,
            minimum=self.config.minimum_probability,
            maximum=self.config.maximum_probability,
        )

        resolved_opportunities = self._resolve_opportunities(player, context, opportunities)
        if unit in {ProbabilityUnit.PER_GAME, ProbabilityUnit.TEAM_GAME}:
            final_probability = probability_at_least_one(adjusted_per_opportunity, resolved_opportunities)
            expected_value = expected_binomial_count(adjusted_per_opportunity, resolved_opportunities)
            variance = binomial_variance(adjusted_per_opportunity, resolved_opportunities)
            effective_sample_size = max(player.resolved_plate_appearances() / max(resolved_opportunities, 1.0), 1.0)
        else:
            final_probability = adjusted_per_opportunity
            expected_value = adjusted_per_opportunity
            variance = adjusted_per_opportunity * (1.0 - adjusted_per_opportunity)
            effective_sample_size = max(player.resolved_plate_appearances(), 1.0)

        confidence = calculate_prediction_confidence(player, team, context)
        interval = probability_interval_from_effective_sample(
            final_probability,
            effective_sample_size + self.config.prior_strength,
            self.config.confidence_level,
        )

        warnings: list[str] = []
        if player.resolved_plate_appearances() < 50:
            warnings.append("Small historical sample; league-prior shrinkage is substantial.")
        if context is None:
            warnings.append("No game context was supplied; estimate is context-neutral.")
        if normalized in {"rbi", "run"}:
            warnings.append("RBI and run outcomes depend strongly on lineup and base-state opportunities.")

        return ProbabilityEstimate(
            outcome=normalized,
            probability=final_probability,
            base_probability=base_probability,
            unit=unit,
            interval=interval,
            confidence=confidence,
            confidence_band=confidence_band(confidence),
            expected_value=expected_value,
            variance=variance,
            adjustments=adjustments,
            components={**component_rates, "blended": blended_probability, "adjusted_per_opportunity": adjusted_per_opportunity},
            diagnostics={
                "historical_plate_appearances": player.resolved_plate_appearances(),
                "resolved_opportunities": resolved_opportunities,
                "entropy": binary_entropy(final_probability),
                "effective_sample_size": effective_sample_size,
                "request_checksum": stable_hash(
                    {
                        "outcome": normalized,
                        "player": asdict(player),
                        "team": None if team is None else asdict(team),
                        "context": None if context is None else asdict(context),
                        "unit": unit.value,
                    }
                ),
            },
            warnings=warnings,
        )

    def estimate_all_player_outcomes(
        self,
        player: PlayerFeatureProfile,
        team: TeamFeatureProfile | None = None,
        context: GameContextProfile | None = None,
        *,
        unit: ProbabilityUnit = ProbabilityUnit.PER_GAME,
    ) -> dict[str, ProbabilityEstimate]:
        outcomes = (
            "hit",
            "single",
            "double",
            "triple",
            "home_run",
            "walk",
            "strikeout",
            "rbi",
            "run",
            "extra_base_hit",
            "reach_base",
            "total_bases",
        )
        return {
            outcome: self.estimate_player_outcome(
                outcome,
                player,
                team,
                context,
                unit=unit,
            )
            for outcome in outcomes
        }

    def plate_appearance_distribution(
        self,
        player: PlayerFeatureProfile,
        team: TeamFeatureProfile | None = None,
        context: GameContextProfile | None = None,
    ) -> OutcomeDistribution:
        base_distribution = build_plate_appearance_distribution(player)
        adjusted: dict[str, float] = {}
        for outcome, probability in base_distribution.probabilities.items():
            if outcome == "other_out":
                adjusted[outcome] = probability
                continue
            factors = build_context_adjustments(outcome, team, context) if self.config.apply_context else []
            adjusted[outcome] = apply_adjustments_log_odds(
                probability,
                factors,
                minimum=self.config.minimum_probability,
                maximum=self.config.maximum_probability,
            )
        adjusted["other_out"] = max(1.0 - sum(value for key, value in adjusted.items() if key != "other_out"), 0.01)
        normalized = normalize_probabilities(adjusted)
        expected_total_bases = (
            normalized.get("single", 0.0)
            + 2.0 * normalized.get("double", 0.0)
            + 3.0 * normalized.get("triple", 0.0)
            + 4.0 * normalized.get("home_run", 0.0)
        )
        expected_on_base = sum(normalized.get(key, 0.0) for key in ("single", "double", "triple", "home_run", "walk"))
        return OutcomeDistribution(
            probabilities=normalized,
            expected_total_bases=expected_total_bases,
            expected_on_base=expected_on_base,
            entropy=categorical_entropy(normalized.values()),
            checksum=stable_hash(normalized),
        )

    def estimate_team_win(
        self,
        home_team: TeamFeatureProfile,
        away_team: TeamFeatureProfile,
        *,
        home_context: GameContextProfile | None = None,
        extra_inning_tie_split: float = 0.54,
        maximum_runs: int = 20,
    ) -> TeamWinEstimate:
        home_runs = self.expected_team_runs(home_team, away_team, home_context, is_home=True)
        away_context = GameContextProfile(home_game=False)
        away_runs = self.expected_team_runs(away_team, home_team, away_context, is_home=False)

        home_win = 0.0
        tie_probability = 0.0
        for home_score in range(maximum_runs + 1):
            home_p = poisson_pmf(home_score, home_runs)
            for away_score in range(maximum_runs + 1):
                joint = home_p * poisson_pmf(away_score, away_runs)
                if home_score > away_score:
                    home_win += joint
                elif home_score == away_score:
                    tie_probability += joint
        home_win += tie_probability * clamp(extra_inning_tie_split, 0.0, 1.0)
        home_win = clamp(home_win, 0.01, 0.99)
        interval = probability_interval_from_effective_sample(home_win, 162.0, self.config.confidence_level)
        return TeamWinEstimate(
            home_win_probability=home_win,
            away_win_probability=1.0 - home_win,
            expected_home_runs=home_runs,
            expected_away_runs=away_runs,
            expected_run_differential=home_runs - away_runs,
            interval=interval,
            method="independent_poisson_score_matrix",
            diagnostics={
                "tie_probability_before_extra_innings": tie_probability,
                "maximum_runs_enumerated": maximum_runs,
                "home_offense_strength": self._team_offense_strength(home_team),
                "away_offense_strength": self._team_offense_strength(away_team),
            },
        )

    def expected_team_runs(
        self,
        offense: TeamFeatureProfile,
        defense: TeamFeatureProfile | None = None,
        context: GameContextProfile | None = None,
        *,
        is_home: bool | None = None,
    ) -> float:
        offense_runs = to_float(offense.projected_runs, to_float(offense.runs_per_game, LEAGUE_PRIORS["team_runs"]))
        if defense is not None:
            defense_runs_allowed = to_float(
                defense.runs_allowed_per_game,
                safe_divide(defense.runs_allowed, defense.games_played, LEAGUE_PRIORS["team_runs"]),
            )
        else:
            defense_runs_allowed = LEAGUE_PRIORS["team_runs"]
        baseline = geometric_mean([max(offense_runs, 0.1), max(defense_runs_allowed, 0.1)])
        strength = self._team_offense_strength(offense)
        baseline *= math.exp((strength - 1.0) * 0.18)
        park = calculate_park_adjustment(context, "team_runs")
        weather = calculate_weather_adjustment("team_runs", context)
        home = 1.035 if (is_home if is_home is not None else bool(context and context.home_game)) else 0.985
        if defense is not None:
            pitching = self._team_pitching_factor(defense)
        else:
            pitching = 1.0
        return clamp(baseline * park * weather * home * pitching, 1.2, 10.5)

    @staticmethod
    def _team_offense_strength(team: TeamFeatureProfile) -> float:
        components: list[float] = []
        weights: list[float] = []
        if team.runs_per_game is not None:
            components.append(to_float(team.runs_per_game) / LEAGUE_PRIORS["team_runs"])
            weights.append(0.45)
        if team.team_ops is not None:
            components.append(to_float(team.team_ops) / 0.720)
            weights.append(0.30)
        if team.team_woba is not None:
            components.append(to_float(team.team_woba) / 0.315)
            weights.append(0.25)
        return clamp(weighted_mean(components, weights, 1.0), 0.65, 1.45)

    @staticmethod
    def _team_pitching_factor(team: TeamFeatureProfile) -> float:
        factors: list[float] = []
        weights: list[float] = []
        if team.runs_allowed_per_game is not None:
            factors.append(to_float(team.runs_allowed_per_game) / LEAGUE_PRIORS["team_runs"])
            weights.append(0.50)
        if team.starting_pitcher_quality is not None:
            score = to_float(team.starting_pitcher_quality)
            if score > 1.0:
                score /= 100.0
            factors.append(clamp(1.15 - 0.30 * score, 0.80, 1.20))
            weights.append(0.30)
        if team.bullpen_quality_score is not None:
            score = to_float(team.bullpen_quality_score)
            if score > 1.0:
                score /= 100.0
            factors.append(clamp(1.12 - 0.24 * score, 0.82, 1.18))
            weights.append(0.20)
        return clamp(weighted_mean(factors, weights, 1.0), 0.72, 1.35)

    def _resolve_opportunities(
        self,
        player: PlayerFeatureProfile,
        context: GameContextProfile | None,
        opportunities: float | None,
    ) -> float:
        candidates = (
            opportunities,
            None if context is None else context.expected_plate_appearances,
            player.projected_plate_appearances,
            self.config.default_plate_appearances,
        )
        for candidate in candidates:
            if candidate is not None and to_float(candidate) > 0:
                return clamp(to_float(candidate), 1.0, 7.0)
        return self.config.default_plate_appearances


# ============================================================
# SECTION 21 - LEGACY-COMPATIBLE ADJUSTED PROBABILITY API
# ============================================================

def calculate_adjusted_probability(
    outcome: str,
    player: PlayerFeatureProfile,
    team: TeamFeatureProfile | None = None,
    context: GameContextProfile | None = None,
) -> dict[str, Any]:
    estimate = ProbabilityEngine().estimate_player_outcome(
        outcome,
        player,
        team,
        context,
        unit=ProbabilityUnit.PER_PLATE_APPEARANCE,
    )
    payload = estimate.to_dict()
    payload.update(
        {
            "player": player.player_name,
            "team": player.team_name,
            "adjustments": {
                f"{item.name}_adjustment": round(item.factor, 4)
                for item in estimate.adjustments
            },
            "explanation": build_probability_explanation(
                outcome=estimate.outcome,
                player=player,
                base_probability=estimate.base_probability,
                adjusted_probability=estimate.probability,
                confidence=estimate.confidence,
            ),
            "next_model_layers": [
                "warehouse feature extraction",
                "rolling and exponentially weighted form",
                "pitcher-batter matchup features",
                "context engine integration",
                "probability calibration",
                "Monte Carlo simulation",
                "gradient-boosted model blending",
                "Bayesian live updating",
            ],
        }
    )
    return payload


# ============================================================
# SECTION 22 - EXPLANATION BUILDER
# ============================================================

def build_probability_explanation(
    outcome: str,
    player: PlayerFeatureProfile,
    base_probability: float,
    adjusted_probability: float,
    confidence: float,
) -> list[str]:
    direction = adjusted_probability - base_probability
    if abs(direction) < 0.002:
        context_statement = "Available context produced little material change."
    elif direction > 0:
        context_statement = "Available context increased the estimated probability."
    else:
        context_statement = "Available context reduced the estimated probability."
    return [
        f"Outcome analyzed: {normalize_outcome(outcome).replace('_', ' ')}.",
        f"The player baseline was estimated from {player.player_name}'s observed rates with league-prior shrinkage.",
        f"Base per-opportunity probability: {percentage(base_probability)}%.",
        f"Adjusted per-opportunity probability: {percentage(adjusted_probability)}%.",
        context_statement,
        f"Data confidence score: {round(confidence, 2)}%.",
        "This mathematical probability is calibration-ready and is not a guarantee of the observed result.",
    ]


# ============================================================
# SECTION 23 - PROFILE BUILDERS
# ============================================================

def _mapping_from_any(data: Any) -> dict[str, Any]:
    if data is None:
        return {}
    if isinstance(data, Mapping):
        return dict(data)
    if is_dataclass(data):
        return asdict(data)
    if hasattr(data, "model_dump"):
        return dict(data.model_dump())
    if hasattr(data, "dict") and callable(data.dict):
        return dict(data.dict())
    if hasattr(data, "__dict__"):
        return {key: value for key, value in vars(data).items() if not key.startswith("_")}
    raise ProbabilityValidationError(f"Cannot convert {type(data).__name__} into a profile mapping")


def build_player_profile_from_dict(data: dict[str, Any]) -> PlayerFeatureProfile:
    payload = _mapping_from_any(data)
    allowed = {field_name for field_name in PlayerFeatureProfile.__dataclass_fields__}
    normalized = {key: value for key, value in payload.items() if key in allowed}
    normalized["player_name"] = payload.get("player_name") or payload.get("name") or "Unknown Player"
    normalized.setdefault("team_name", payload.get("team_name") or payload.get("team"))
    return PlayerFeatureProfile(**normalized)


def build_team_profile_from_dict(data: dict[str, Any] | None) -> TeamFeatureProfile | None:
    if not data:
        return None
    payload = _mapping_from_any(data)
    allowed = {field_name for field_name in TeamFeatureProfile.__dataclass_fields__}
    normalized = {key: value for key, value in payload.items() if key in allowed}
    normalized["team_name"] = payload.get("team_name") or payload.get("name") or "Unknown Team"
    return TeamFeatureProfile(**normalized)


def build_game_context_from_dict(data: dict[str, Any] | None) -> GameContextProfile | None:
    if not data:
        return None
    payload = _mapping_from_any(data)
    allowed = {field_name for field_name in GameContextProfile.__dataclass_fields__}
    normalized = {key: value for key, value in payload.items() if key in allowed}
    return GameContextProfile(**normalized)


# ============================================================
# SECTION 24 - PUBLIC PREDICTION FUNCTIONS
# ============================================================

def predict_player_outcome(
    player_data: dict[str, Any],
    outcome: str,
    team_data: dict[str, Any] | None = None,
    game_context: dict[str, Any] | None = None,
    *,
    per_game: bool = False,
    opportunities: float | None = None,
) -> dict[str, Any]:
    player = build_player_profile_from_dict(player_data)
    team = build_team_profile_from_dict(team_data)
    context = build_game_context_from_dict(game_context)
    unit = ProbabilityUnit.PER_GAME if per_game else ProbabilityUnit.PER_PLATE_APPEARANCE
    estimate = ProbabilityEngine().estimate_player_outcome(
        outcome,
        player,
        team,
        context,
        unit=unit,
        opportunities=opportunities,
    )
    payload = estimate.to_dict()
    payload["player"] = player.player_name
    payload["team"] = player.team_name
    payload["explanation"] = build_probability_explanation(
        outcome=estimate.outcome,
        player=player,
        base_probability=estimate.base_probability,
        adjusted_probability=estimate.probability,
        confidence=estimate.confidence,
    )
    return payload


def predict_all_player_outcomes(
    player_data: dict[str, Any],
    team_data: dict[str, Any] | None = None,
    game_context: dict[str, Any] | None = None,
    *,
    per_game: bool = True,
) -> dict[str, Any]:
    player = build_player_profile_from_dict(player_data)
    team = build_team_profile_from_dict(team_data)
    context = build_game_context_from_dict(game_context)
    unit = ProbabilityUnit.PER_GAME if per_game else ProbabilityUnit.PER_PLATE_APPEARANCE
    engine = ProbabilityEngine()
    estimates = engine.estimate_all_player_outcomes(player, team, context, unit=unit)
    return {
        "engine": ENGINE_NAME,
        "engine_version": ENGINE_VERSION,
        "player": player.player_name,
        "team": player.team_name,
        "unit": unit.value,
        "outcomes": {key: estimate.to_dict() for key, estimate in estimates.items()},
        "plate_appearance_distribution": engine.plate_appearance_distribution(player, team, context).to_dict(),
    }


def predict_team_game(
    home_team_data: dict[str, Any],
    away_team_data: dict[str, Any],
    game_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    home = build_team_profile_from_dict(home_team_data)
    away = build_team_profile_from_dict(away_team_data)
    if home is None or away is None:
        raise ProbabilityValidationError("Both home and away team profiles are required")
    context = build_game_context_from_dict(game_context) or GameContextProfile(home_game=True)
    context.home_game = True
    return ProbabilityEngine().estimate_team_win(home, away, home_context=context).to_dict()


# ============================================================
# SECTION 25 - CALIBRATION SUPPORT FUNCTIONS
# ============================================================

def reliability_bins(
    probabilities: Sequence[float],
    observations: Sequence[int | bool],
    *,
    bins: int = 10,
) -> list[dict[str, float | int]]:
    if len(probabilities) != len(observations):
        raise ProbabilityValidationError("probabilities and observations must have equal length")
    if bins <= 0:
        raise ProbabilityValidationError("bins must be positive")
    buckets: list[list[tuple[float, float]]] = [[] for _ in range(bins)]
    for probability, observed in zip(probabilities, observations):
        p = clamp(to_float(probability), 0.0, 1.0)
        index = min(int(p * bins), bins - 1)
        buckets[index].append((p, float(bool(observed))))
    output: list[dict[str, float | int]] = []
    for index, bucket in enumerate(buckets):
        if not bucket:
            output.append(
                {
                    "bin": index,
                    "count": 0,
                    "mean_probability": 0.0,
                    "observed_frequency": 0.0,
                    "absolute_gap": 0.0,
                }
            )
            continue
        mean_probability = statistics.fmean(item[0] for item in bucket)
        observed_frequency = statistics.fmean(item[1] for item in bucket)
        output.append(
            {
                "bin": index,
                "count": len(bucket),
                "mean_probability": mean_probability,
                "observed_frequency": observed_frequency,
                "absolute_gap": abs(mean_probability - observed_frequency),
            }
        )
    return output


def expected_calibration_error(
    probabilities: Sequence[float],
    observations: Sequence[int | bool],
    *,
    bins: int = 10,
) -> float:
    bin_rows = reliability_bins(probabilities, observations, bins=bins)
    total = max(len(probabilities), 1)
    return sum(to_float(row["count"]) / total * to_float(row["absolute_gap"]) for row in bin_rows)


def maximum_calibration_error(
    probabilities: Sequence[float],
    observations: Sequence[int | bool],
    *,
    bins: int = 10,
) -> float:
    rows = reliability_bins(probabilities, observations, bins=bins)
    populated = [to_float(row["absolute_gap"]) for row in rows if to_float(row["count"]) > 0]
    return max(populated, default=0.0)


# ============================================================
# SECTION 26 - MONTE CARLO SUPPORT PRIMITIVES
# ============================================================

def sample_categorical(
    probabilities: Mapping[str, float],
    random_source: random.Random | None = None,
) -> str:
    rng = random_source or random
    normalized = normalize_probabilities(probabilities)
    draw = rng.random()
    cumulative = 0.0
    last_key = next(reversed(normalized))
    for key, probability in normalized.items():
        cumulative += probability
        if draw <= cumulative:
            return key
    return last_key


def sample_binomial(
    trials: int,
    probability: float,
    random_source: random.Random | None = None,
) -> int:
    rng = random_source or random
    p = clamp(to_float(probability), 0.0, 1.0)
    return sum(1 for _ in range(max(trials, 0)) if rng.random() < p)


def sample_poisson(
    rate: float,
    random_source: random.Random | None = None,
) -> int:
    rng = random_source or random
    lam = max(to_float(rate), 0.0)
    if lam <= 30.0:
        threshold = math.exp(-lam)
        product = 1.0
        count = 0
        while product > threshold:
            count += 1
            product *= rng.random()
        return count - 1
    approximation = rng.gauss(lam, math.sqrt(lam))
    return max(int(round(approximation)), 0)


# ============================================================
# SECTION 27 - DIAGNOSTICS AND HEALTH
# ============================================================

def probability_engine_health() -> dict[str, Any]:
    return {
        "engine": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "phase": ENGINE_PHASE,
        "file": ENGINE_FILE,
        "status": ENGINE_STATUS,
        "supported_outcomes": sorted(SUPPORTED_OUTCOMES),
        "supported_units": [item.value for item in ProbabilityUnit],
        "supported_distributions": [item.value for item in DistributionKind],
        "timestamp": datetime.now(UTC).isoformat(),
    }


def validate_probability_engine() -> dict[str, Any]:
    player = PlayerFeatureProfile(
        player_name="Validation Player",
        team_name="Validation Team",
        plate_appearances=500,
        at_bats=445,
        hits=122,
        doubles=26,
        triples=3,
        home_runs=24,
        walks=48,
        strikeouts=118,
        rbi=76,
        runs=71,
        barrel_rate=0.115,
        hard_hit_rate=0.445,
        expected_batting_average=0.268,
        expected_slugging_percentage=0.486,
        projected_plate_appearances=4.3,
    )
    team = TeamFeatureProfile(
        team_name="Validation Team",
        runs_per_game=4.72,
        team_ops=0.744,
        lineup_strength_score=63.0,
    )
    context = GameContextProfile(
        opponent_team="Opponent",
        home_game=True,
        pitcher_era=4.05,
        pitcher_whip=1.24,
        pitcher_strikeout_rate=0.232,
        park_factor=1.03,
        home_run_park_factor=1.07,
        temperature_f=78.0,
        wind_out_component=4.0,
        lineup_slot=3,
        expected_plate_appearances=4.4,
    )
    engine = ProbabilityEngine()
    estimates = engine.estimate_all_player_outcomes(player, team, context)
    distribution = engine.plate_appearance_distribution(player, team, context)
    partition_sum = sum(distribution.probabilities.values())
    failures = []
    for outcome, estimate in estimates.items():
        if not 0.0 <= estimate.probability <= 1.0:
            failures.append(f"{outcome}: probability out of bounds")
        if not estimate.interval.lower <= estimate.interval.mean <= estimate.interval.upper:
            failures.append(f"{outcome}: interval ordering invalid")
    if abs(partition_sum - 1.0) > 1e-9:
        failures.append("plate appearance distribution does not sum to one")
    return {
        "status": "ok" if not failures else "failed",
        "outcome_count": len(estimates),
        "partition_sum": partition_sum,
        "distribution_checksum": distribution.checksum,
        "failures": failures,
    }


# ============================================================
# SECTION 28 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "ENGINE_NAME",
    "ENGINE_VERSION",
    "ENGINE_PHASE",
    "ENGINE_FILE",
    "ENGINE_STATUS",
    "SUPPORTED_OUTCOMES",
    "LEAGUE_PRIORS",
    "ProbabilityScale",
    "ProbabilityUnit",
    "CombinationMethod",
    "DistributionKind",
    "ConfidenceBand",
    "ProbabilityEngineError",
    "ProbabilityValidationError",
    "UnsupportedOutcomeError",
    "NumericalStabilityError",
    "PlayerFeatureProfile",
    "TeamFeatureProfile",
    "GameContextProfile",
    "ProbabilityInterval",
    "BetaPosterior",
    "AdjustmentFactor",
    "ProbabilityEstimate",
    "OutcomeDistribution",
    "TeamWinEstimate",
    "ProbabilityEngineConfig",
    "ProbabilityEngine",
    "safe_divide",
    "clamp",
    "clamp_probability",
    "normalize_rate",
    "percentage",
    "logistic",
    "logit",
    "odds",
    "probability_from_odds",
    "softmax",
    "normalize_probabilities",
    "weighted_mean",
    "geometric_mean",
    "normal_cdf",
    "normal_pdf",
    "normal_quantile",
    "bernoulli_pmf",
    "binomial_pmf",
    "binomial_cdf",
    "probability_at_least_one",
    "expected_binomial_count",
    "binomial_variance",
    "poisson_pmf",
    "poisson_cdf",
    "poisson_survival",
    "negative_binomial_pmf",
    "beta_prior",
    "beta_binomial_posterior",
    "empirical_bayes_rate",
    "blend_rates",
    "binary_entropy",
    "categorical_entropy",
    "brier_score",
    "log_loss",
    "multiclass_log_loss",
    "calculate_hit_rate",
    "calculate_single_rate",
    "calculate_double_rate",
    "calculate_triple_rate",
    "calculate_home_run_rate",
    "calculate_walk_rate",
    "calculate_strikeout_rate",
    "calculate_rbi_rate",
    "calculate_run_rate",
    "calculate_extra_base_rate",
    "calculate_reach_base_rate",
    "calculate_total_bases_rate",
    "build_plate_appearance_distribution",
    "calculate_park_adjustment",
    "calculate_pitcher_adjustment",
    "calculate_team_context_adjustment",
    "calculate_home_field_adjustment",
    "calculate_weather_adjustment",
    "calculate_schedule_adjustment",
    "calculate_lineup_adjustment",
    "calculate_platoon_adjustment",
    "calculate_recent_form_rate",
    "calculate_statcast_rate",
    "normalize_outcome",
    "calculate_base_probability",
    "apply_adjustments_log_odds",
    "build_context_adjustments",
    "calculate_prediction_confidence",
    "probability_interval_from_effective_sample",
    "calculate_adjusted_probability",
    "build_probability_explanation",
    "build_player_profile_from_dict",
    "build_team_profile_from_dict",
    "build_game_context_from_dict",
    "predict_player_outcome",
    "predict_all_player_outcomes",
    "predict_team_game",
    "reliability_bins",
    "expected_calibration_error",
    "maximum_calibration_error",
    "sample_categorical",
    "sample_binomial",
    "sample_poisson",
    "probability_engine_health",
    "validate_probability_engine",
]


# ============================================================
# SECTION 29 - LOCAL EXECUTION TEST
# ============================================================

if __name__ == "__main__":
    validation = validate_probability_engine()
    print(json.dumps(validation, indent=2, sort_keys=True))
    if validation["status"] != "ok":
        raise SystemExit(1)

# ============================================================
# SECTION 90 - PHASE 14 PART 6.0 - MODEL FEEDBACK CALIBRATION HELPERS
# FILE: 04_ai/probability_engine.py
# PURPOSE:
# Convert feedback events into calibration rows and probability
# error summaries for future model correction.
# ============================================================

MODEL_FEEDBACK_CALIBRATION_VERSION = "phase_14_part_6_0_model_feedback_calibration_helpers"


def calculate_feedback_probability_error(
    predicted_probability,
    actual_value,
):
    try:
        predicted = float(predicted_probability)
    except Exception:
        return None

    if predicted > 1.0:
        predicted = predicted / 100.0

    try:
        actual = float(actual_value)
    except Exception:
        if isinstance(actual_value, bool):
            actual = 1.0 if actual_value else 0.0
        else:
            return None

    actual = max(0.0, min(1.0, actual))
    predicted = max(0.0, min(1.0, predicted))

    return round(abs(predicted - actual), 6)


def feedback_event_to_calibration_row(
    feedback_event: dict,
) -> dict:
    feedback_event = dict(feedback_event or {})

    error = feedback_event.get("probability_error")

    if error is None:
        error = calculate_feedback_probability_error(
            feedback_event.get("predicted_probability"),
            feedback_event.get("actual_numeric")
            if feedback_event.get("actual_numeric") is not None
            else feedback_event.get("actual_value"),
        )

    return {
        "calibration_version": MODEL_FEEDBACK_CALIBRATION_VERSION,
        "feedback_event_id": feedback_event.get("id"),
        "prediction_history_id": feedback_event.get("prediction_history_id"),
        "model_name": feedback_event.get("model_name"),
        "model_version": feedback_event.get("model_version"),
        "outcome_key": feedback_event.get("outcome_key"),
        "predicted_probability": feedback_event.get("predicted_probability"),
        "actual_value": feedback_event.get("actual_value"),
        "actual_numeric": feedback_event.get("actual_numeric"),
        "was_correct": feedback_event.get("was_correct"),
        "probability_error": error,
        "training_weight": feedback_event.get("training_weight", 1.0),
        "approved_for_training": bool(feedback_event.get("approved_for_training")),
        "used_for_training": bool(feedback_event.get("used_for_training")),
    }


def build_probability_model_feedback_summary(
    feedback_events: list[dict],
) -> dict:
    events = list(feedback_events or [])
    rows = [
        feedback_event_to_calibration_row(event)
        for event in events
    ]

    error_values = [
        row["probability_error"]
        for row in rows
        if row.get("probability_error") is not None
    ]

    average_error = (
        round(sum(error_values) / len(error_values), 6)
        if error_values
        else None
    )

    return {
        "status": "ready",
        "calibration_version": MODEL_FEEDBACK_CALIBRATION_VERSION,
        "event_count": len(events),
        "scored_event_count": len(error_values),
        "average_probability_error": average_error,
        "rows": rows,
    }


def validate_model_feedback_calibration_helpers() -> dict:
    checks = {
        "error_calculator_available": callable(calculate_feedback_probability_error),
        "calibration_row_builder_available": callable(feedback_event_to_calibration_row),
        "summary_builder_available": callable(build_probability_model_feedback_summary),
        "error_math_valid": calculate_feedback_probability_error(75, 1) == 0.25,
    }

    passed = sum(1 for value in checks.values() if value)

    return {
        "status": "ok" if passed == len(checks) else "degraded",
        "phase": "Phase 14 Part 6.0",
        "calibration_version": MODEL_FEEDBACK_CALIBRATION_VERSION,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
    }


# ============================================================
# SECTION 99 - PHASE 14 PART 7.0 - PRODUCTION TRUTH PROBABILITY POLICY
# FILE: 04_ai/probability_engine.py
# PURPOSE:
# Central probability policy that forbids fabricated probability,
# fabricated confidence, and hidden demo readiness.
# ============================================================

PRODUCTION_TRUTH_PROBABILITY_VERSION = "phase_14_part_7_0_production_truth_probability_policy"

PRODUCTION_TRUTH_STATES = {
    "database_ready": "database_ready",
    "live_api_fallback": "live_api_fallback",
    "warehouse_pending": "warehouse_pending",
    "insufficient_sample": "insufficient_sample",
    "stale_data": "stale_data",
    "missing_statcast": "missing_statcast",
    "prediction_ready": "prediction_ready",
    "prediction_blocked": "prediction_blocked",
}


def build_prediction_blocked_payload(
    *,
    player_name: str,
    outcome_key: str,
    missing_inputs: list[str],
    data_coverage: float = 0.0,
    model_version: str = PRODUCTION_TRUTH_PROBABILITY_VERSION,
) -> dict:
    return {
        "status": PRODUCTION_TRUTH_STATES["prediction_blocked"],
        "player": player_name,
        "outcome_key": outcome_key,
        "predicted_probability": None,
        "confidence": 0.0,
        "data_coverage": data_coverage,
        "model_name": "AISP2 Production Truth Gate",
        "model_version": model_version,
        "missing_inputs": list(dict.fromkeys(missing_inputs or [])),
        "policy": {
            "no_fake_player_stats": True,
            "no_fake_team_stats": True,
            "no_fake_confidence": True,
            "no_fake_warehouse_completeness": True,
        },
    }


def validate_production_truth_probability_policy() -> dict:
    sample = build_prediction_blocked_payload(
        player_name="Example Player",
        outcome_key="home_run",
        missing_inputs=["missing_statcast"],
    )

    checks = {
        "version_present": bool(PRODUCTION_TRUTH_PROBABILITY_VERSION),
        "blocked_payload_has_no_probability": sample["predicted_probability"] is None,
        "blocked_payload_has_zero_confidence": sample["confidence"] == 0.0,
        "policy_forbids_fake_confidence": sample["policy"]["no_fake_confidence"],
        "states_include_prediction_blocked": "prediction_blocked" in PRODUCTION_TRUTH_STATES,
    }

    passed = sum(1 for value in checks.values() if value)

    return {
        "status": "ok" if passed == len(checks) else "degraded",
        "phase": "Phase 14 Part 7.0",
        "probability_policy_version": PRODUCTION_TRUTH_PROBABILITY_VERSION,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "sample_blocked_payload": sample,
    }


# ============================================================
# SECTION 100 - PHASE 16 PART 3E - WORKBENCH FEATURE PACKET PROBABILITY ADAPTER
# FILE: 04_ai/probability_engine.py
# PURPOSE:
# Convert 04_ai/baseball/feature_builder.py feature packets into
# real player-specific Workbench probability outputs.
#
# WHY THIS EXISTS:
# The original probability engine is mathematically strong, but the
# Prediction Workbench needs a stable adapter that consumes:
#
#   feature_packet["rates"]
#   feature_packet["stat_line"]
#   feature_packet["probability_inputs"]
#   feature_packet["technical_profile"]
#
# and produces:
#
#   selected outcome probability
#   all prop probabilities
#   confidence
#   explanation
#   debug proof
#
# CORE MATH:
#   player_specific_rate =
#       observed_rate * sample_weight
#       +
#       league_baseline_rate * (1 - sample_weight)
#
# GAME-LEVEL CONVERSION:
#   If requested, per-opportunity probability is converted to the
#   probability of at least one event across expected opportunities:
#
#   1 - (1 - p) ** opportunities
#
# This section does not claim trained ML/DL calibration. It is the
# correct source-backed statistical baseline layer that future ML/DL
# calibration should consume.
# ============================================================

PHASE_16_PART_3E_PROBABILITY_ADAPTER_VERSION = (
    "phase_16_part_3e_workbench_feature_packet_probability_adapter"
)


PHASE_16_OUTCOME_RATE_MAP = {
    "home_run": {
        "metric": "HR / PA",
        "rate_key": "hr_per_pa",
        "baseline": LEAGUE_PRIORS.get("home_run", 0.032),
        "unit": "per_plate_appearance",
        "minimum": 0.001,
        "maximum": 0.220,
    },
    "hit": {
        "metric": "H / AB",
        "rate_key": "hit_per_ab",
        "baseline": LEAGUE_PRIORS.get("hit", 0.245),
        "unit": "per_at_bat",
        "minimum": 0.040,
        "maximum": 0.500,
    },
    "single": {
        "metric": "1B / AB",
        "rate_key": "single_per_ab",
        "baseline": LEAGUE_PRIORS.get("single", 0.150),
        "unit": "per_at_bat",
        "minimum": 0.020,
        "maximum": 0.360,
    },
    "double": {
        "metric": "2B / AB",
        "rate_key": "double_per_ab",
        "baseline": LEAGUE_PRIORS.get("double", 0.045),
        "unit": "per_at_bat",
        "minimum": 0.002,
        "maximum": 0.160,
    },
    "triple": {
        "metric": "3B / AB",
        "rate_key": "triple_per_ab",
        "baseline": LEAGUE_PRIORS.get("triple", 0.004),
        "unit": "per_at_bat",
        "minimum": 0.0002,
        "maximum": 0.050,
    },
    "walk": {
        "metric": "BB / PA",
        "rate_key": "bb_per_pa",
        "baseline": LEAGUE_PRIORS.get("walk", 0.083),
        "unit": "per_plate_appearance",
        "minimum": 0.010,
        "maximum": 0.300,
    },
    "strikeout": {
        "metric": "K / PA",
        "rate_key": "k_per_pa",
        "baseline": LEAGUE_PRIORS.get("strikeout", 0.225),
        "unit": "per_plate_appearance",
        "minimum": 0.025,
        "maximum": 0.550,
    },
    "rbi": {
        "metric": "RBI / PA",
        "rate_key": "rbi_per_pa",
        "baseline": LEAGUE_PRIORS.get("rbi", 0.110),
        "unit": "per_plate_appearance",
        "minimum": 0.015,
        "maximum": 0.400,
    },
    "run": {
        "metric": "R / PA",
        "rate_key": "run_per_pa",
        "baseline": LEAGUE_PRIORS.get("run", 0.115),
        "unit": "per_plate_appearance",
        "minimum": 0.015,
        "maximum": 0.400,
    },
    "run_scored": {
        "metric": "R / PA",
        "rate_key": "run_per_pa",
        "baseline": LEAGUE_PRIORS.get("run", 0.115),
        "unit": "per_plate_appearance",
        "minimum": 0.015,
        "maximum": 0.400,
    },
    "total_bases": {
        "metric": "TB / AB",
        "rate_key": "tb_per_ab",
        "baseline": LEAGUE_PRIORS.get("total_bases", 0.325),
        "unit": "per_at_bat",
        "minimum": 0.030,
        "maximum": 0.700,
    },
    "extra_base_hit": {
        "metric": "XBH / PA",
        "rate_key": "xbh_per_pa",
        "baseline": LEAGUE_PRIORS.get("extra_base_hit", 0.081),
        "unit": "per_plate_appearance",
        "minimum": 0.005,
        "maximum": 0.300,
    },
    "reach_base": {
        "metric": "TOB / PA",
        "rate_key": "times_on_base_per_pa",
        "baseline": LEAGUE_PRIORS.get("reach_base", 0.325),
        "unit": "per_plate_appearance",
        "minimum": 0.080,
        "maximum": 0.650,
    },
}


def phase16_normalize_workbench_outcome(outcome: Any) -> str:
    text = str(outcome or "home_run").strip().lower()
    text = text.replace("-", "_").replace(" ", "_")

    aliases = {
        "hr": "home_run",
        "homer": "home_run",
        "homerun": "home_run",
        "home_runs": "home_run",
        "hits": "hit",
        "singles": "single",
        "doubles": "double",
        "triples": "triple",
        "walks": "walk",
        "bb": "walk",
        "so": "strikeout",
        "k": "strikeout",
        "ks": "strikeout",
        "strikeouts": "strikeout",
        "runs": "run_scored",
        "run": "run_scored",
        "runs_scored": "run_scored",
        "tb": "total_bases",
        "total_base": "total_bases",
        "xbh": "extra_base_hit",
        "on_base": "reach_base",
    }

    return aliases.get(text, text or "home_run")


def phase16_safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if isinstance(value, Mapping):
        return dict(value)

    if is_dataclass(value):
        return asdict(value)

    if hasattr(value, "model_dump") and callable(value.model_dump):
        return dict(value.model_dump())

    if hasattr(value, "dict") and callable(value.dict):
        return dict(value.dict())

    if hasattr(value, "__dict__"):
        return {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_")
        }

    return {}


def phase16_read_nested(
    payload: Mapping[str, Any],
    path: Sequence[str],
    default: Any = None,
) -> Any:
    current: Any = payload

    for key in path:
        if not isinstance(current, Mapping):
            return default

        if key not in current:
            return default

        current = current.get(key)

    return default if current in (None, "") else current


def phase16_safe_float(value: Any, default: float = 0.0) -> float:
    return to_float(value, default)


def phase16_safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(phase16_safe_float(value, float(default))))
    except Exception:
        return int(default)


def phase16_probability_percent(value: Any, digits: int = 1) -> float:
    return round(clamp(phase16_safe_float(value), 0.0, 1.0) * 100.0, digits)


def phase16_sample_weight(sample_size: int) -> float:
    sample = phase16_safe_int(sample_size)

    if sample >= 600:
        return 0.90

    if sample >= 500:
        return 0.88

    if sample >= 350:
        return 0.82

    if sample >= 150:
        return 0.68

    if sample >= 50:
        return 0.45

    if sample > 0:
        return 0.25

    return 0.0


def phase16_confidence_from_feature_packet(
    feature_packet: Mapping[str, Any],
    *,
    probability_decimal: float,
) -> float:
    sample_size = phase16_safe_int(
        feature_packet.get("sample_size")
        or phase16_read_nested(feature_packet, ("stat_line", "sample_size"))
        or phase16_read_nested(feature_packet, ("probability_inputs", "sample_size"))
    )

    coverage = phase16_safe_float(
        phase16_read_nested(feature_packet, ("probability_inputs", "coverage")),
        0.0,
    )

    source_status = str(
        feature_packet.get("source_status")
        or phase16_read_nested(feature_packet, ("probability_inputs", "source_status"))
        or ""
    ).lower()

    if sample_size <= 0:
        return 12.0

    sample_component = 1.0 - math.exp(-sample_size / 260.0)

    if "database" in source_status:
        source_component = 1.0
    elif "live_mlb" in source_status:
        source_component = 0.82
    elif "request_supplied" in source_status:
        source_component = 0.72
    else:
        source_component = 0.48

    probability_component = 1.0 - binary_entropy(
        clamp(probability_decimal, 0.0001, 0.9999)
    )

    score = (
        28.0
        + 42.0 * sample_component
        + 18.0 * clamp(coverage, 0.0, 1.0)
        + 8.0 * source_component
        + 4.0 * probability_component
    )

    return round(clamp(score, 15.0, 94.0), 1)


def phase16_extract_observed_rate(
    feature_packet: Mapping[str, Any],
    outcome_key: str,
) -> tuple[str, str, float, float, str]:
    rates = phase16_safe_mapping(feature_packet.get("rates"))
    probability_inputs = phase16_safe_mapping(feature_packet.get("probability_inputs"))

    normalized = phase16_normalize_workbench_outcome(outcome_key)
    spec = PHASE_16_OUTCOME_RATE_MAP.get(
        normalized,
        PHASE_16_OUTCOME_RATE_MAP["home_run"],
    )

    metric = str(spec["metric"])
    rate_key = str(spec["rate_key"])
    baseline = phase16_safe_float(spec["baseline"])
    unit = str(spec["unit"])

    observed = phase16_safe_float(rates.get(rate_key), 0.0)

    if observed <= 0.0:
        input_outcome = phase16_normalize_workbench_outcome(
            probability_inputs.get("outcome_key")
        )

        if input_outcome == normalized:
            observed = phase16_safe_float(
                probability_inputs.get("observed_rate"),
                0.0,
            )
            metric = str(probability_inputs.get("primary_metric") or metric)

    return metric, rate_key, observed, baseline, unit


def phase16_player_specific_rate(
    *,
    observed_rate: float,
    baseline_rate: float,
    sample_size: int,
    minimum: float,
    maximum: float,
) -> dict[str, Any]:
    sample_weight = phase16_sample_weight(sample_size)

    if sample_size > 0:
        raw_probability = (
            observed_rate * sample_weight
            + baseline_rate * (1.0 - sample_weight)
        )
        used_no_sample_guard = False
    else:
        raw_probability = baseline_rate * 0.05
        used_no_sample_guard = True

    probability_decimal = clamp(raw_probability, minimum, maximum)

    return {
        "probability_decimal": probability_decimal,
        "sample_weight": sample_weight,
        "used_no_sample_guard": used_no_sample_guard,
        "math_formula": "observed_rate * sample_weight + league_baseline_rate * (1 - sample_weight)",
    }


def phase16_expected_opportunities(
    feature_packet: Mapping[str, Any],
    outcome_key: str,
) -> float:
    stat_line = phase16_safe_mapping(feature_packet.get("stat_line"))
    requested = phase16_safe_mapping(feature_packet.get("requested"))
    raw_payload = phase16_safe_mapping(requested.get("raw_payload"))

    for value in (
        raw_payload.get("expected_plate_appearances"),
        raw_payload.get("projected_plate_appearances"),
        raw_payload.get("opportunities"),
        feature_packet.get("expected_plate_appearances"),
        phase16_read_nested(feature_packet, ("game_context", "expected_plate_appearances")),
    ):
        candidate = phase16_safe_float(value, 0.0)

        if candidate > 0:
            return clamp(candidate, 1.0, 7.0)

    outcome = phase16_normalize_workbench_outcome(outcome_key)

    if outcome in {"hit", "single", "double", "triple", "total_bases"}:
        at_bats = phase16_safe_float(stat_line.get("at_bats"), 0.0)
        plate_appearances = phase16_safe_float(stat_line.get("plate_appearances"), 0.0)

        if plate_appearances > 0 and at_bats > 0:
            at_bat_share = clamp(at_bats / plate_appearances, 0.55, 0.95)
            return round(DEFAULT_EXPECTED_PLATE_APPEARANCES * at_bat_share, 2)

    return DEFAULT_EXPECTED_PLATE_APPEARANCES


def phase16_convert_to_game_probability(
    per_opportunity_probability: float,
    opportunities: float,
) -> float:
    return probability_at_least_one(
        clamp(per_opportunity_probability, 0.0, 1.0),
        clamp(opportunities, 0.0, 7.0),
    )


def build_player_profile_from_feature_packet(
    feature_packet: Mapping[str, Any],
) -> PlayerFeatureProfile:
    packet = phase16_safe_mapping(feature_packet)
    stat_line = phase16_safe_mapping(packet.get("stat_line"))
    rates = phase16_safe_mapping(packet.get("rates"))

    return PlayerFeatureProfile(
        player_name=str(packet.get("player_name") or "Unknown Player"),
        team_name=packet.get("team_name"),
        player_id=packet.get("player_id") or packet.get("mlb_player_id"),
        plate_appearances=phase16_safe_int(stat_line.get("plate_appearances")),
        at_bats=phase16_safe_int(stat_line.get("at_bats")),
        hits=phase16_safe_int(stat_line.get("hits")),
        singles=phase16_safe_int(stat_line.get("singles")),
        doubles=phase16_safe_int(stat_line.get("doubles")),
        triples=phase16_safe_int(stat_line.get("triples")),
        home_runs=phase16_safe_int(stat_line.get("home_runs")),
        walks=phase16_safe_int(stat_line.get("walks")),
        hit_by_pitch=phase16_safe_int(stat_line.get("hit_by_pitch")),
        strikeouts=phase16_safe_int(stat_line.get("strikeouts")),
        rbi=phase16_safe_int(stat_line.get("rbi")),
        runs=phase16_safe_int(stat_line.get("runs")),
        total_bases=phase16_safe_int(stat_line.get("total_bases")),
        batting_average=phase16_safe_float(
            stat_line.get("batting_average") or rates.get("avg"),
            None,
        ),
        on_base_percentage=phase16_safe_float(
            stat_line.get("on_base_percentage") or rates.get("obp"),
            None,
        ),
        slugging_percentage=phase16_safe_float(
            stat_line.get("slugging_percentage") or rates.get("slg"),
            None,
        ),
        ops=phase16_safe_float(
            stat_line.get("ops") or rates.get("ops"),
            None,
        ),
        woba=phase16_safe_float(stat_line.get("woba") or rates.get("woba"), None),
        iso=phase16_safe_float(stat_line.get("isolated_power") or rates.get("iso"), None),
        babip=phase16_safe_float(stat_line.get("babip") or rates.get("babip"), None),
        walk_rate=phase16_safe_float(rates.get("bb_per_pa"), None),
        strikeout_rate=phase16_safe_float(rates.get("k_per_pa"), None),
        projected_plate_appearances=DEFAULT_EXPECTED_PLATE_APPEARANCES,
        bats=phase16_read_nested(packet, ("resolved_player", "bats")),
        position=phase16_read_nested(packet, ("resolved_player", "position")),
    )


def calculate_workbench_probability_from_feature_packet(
    feature_packet: Mapping[str, Any],
    *,
    outcome_key: str | None = None,
    per_game: bool = True,
    opportunities: float | None = None,
) -> dict[str, Any]:
    packet = phase16_safe_mapping(feature_packet)

    selected_outcome = phase16_normalize_workbench_outcome(
        outcome_key
        or packet.get("outcome_key")
        or phase16_read_nested(packet, ("probability_inputs", "outcome_key"))
        or "home_run"
    )

    if selected_outcome == "run":
        selected_outcome = "run_scored"

    spec = PHASE_16_OUTCOME_RATE_MAP.get(
        selected_outcome,
        PHASE_16_OUTCOME_RATE_MAP["home_run"],
    )

    sample_size = phase16_safe_int(
        packet.get("sample_size")
        or phase16_read_nested(packet, ("stat_line", "sample_size"))
        or phase16_read_nested(packet, ("probability_inputs", "sample_size"))
    )

    metric, rate_key, observed_rate, baseline_rate, unit = phase16_extract_observed_rate(
        packet,
        selected_outcome,
    )

    minimum = phase16_safe_float(spec["minimum"])
    maximum = phase16_safe_float(spec["maximum"])

    blended = phase16_player_specific_rate(
        observed_rate=observed_rate,
        baseline_rate=baseline_rate,
        sample_size=sample_size,
        minimum=minimum,
        maximum=maximum,
    )

    per_opportunity_probability = blended["probability_decimal"]

    resolved_opportunities = (
        clamp(phase16_safe_float(opportunities), 1.0, 7.0)
        if opportunities is not None
        else phase16_expected_opportunities(packet, selected_outcome)
    )

    if per_game:
        final_probability = phase16_convert_to_game_probability(
            per_opportunity_probability,
            resolved_opportunities,
        )
        final_unit = "per_game"
    else:
        final_probability = per_opportunity_probability
        final_unit = unit

    confidence = phase16_confidence_from_feature_packet(
        packet,
        probability_decimal=final_probability,
    )

    interval = probability_interval_from_effective_sample(
        final_probability,
        max(sample_size + DEFAULT_PRIOR_STRENGTH, 1.0),
        DEFAULT_CONFIDENCE_LEVEL,
    )

    technical_profile = phase16_safe_mapping(packet.get("technical_profile"))

    no_sample = sample_size <= 0

    warnings: list[str] = []

    if no_sample:
        warnings.append(
            "No usable player hitting sample was available; probability is a no-sample guard."
        )

    if observed_rate <= 0 and sample_size > 0 and selected_outcome != "triple":
        warnings.append(
            f"Observed {metric} was zero or unavailable for this player/outcome."
        )

    source_status = str(
        packet.get("source_status")
        or phase16_read_nested(packet, ("probability_inputs", "source_status"))
        or "unknown"
    )

    player_name = str(packet.get("player_name") or "Unknown Player")
    team_name = str(packet.get("team_name") or "Unknown Team")

    explanation = (
        f"AISP2 calculated {player_name} for {selected_outcome.replace('_', ' ')} "
        f"using {metric}. Observed rate={round(observed_rate * 100.0, 2)}%, "
        f"league baseline={round(baseline_rate * 100.0, 2)}%, "
        f"sample size={sample_size}, sample weight={round(blended['sample_weight'], 3)}. "
        f"The selected probability is player-specific and derived from the feature packet."
    )

    return {
        "status": "ok" if not no_sample else "no_hitting_sample",
        "adapter_version": PHASE_16_PART_3E_PROBABILITY_ADAPTER_VERSION,
        "engine": ENGINE_NAME,
        "engine_version": ENGINE_VERSION,
        "phase": ENGINE_PHASE,
        "player_name": player_name,
        "team_name": team_name,
        "player_id": packet.get("player_id"),
        "mlb_player_id": packet.get("mlb_player_id"),
        "outcome": selected_outcome,
        "outcome_key": selected_outcome,
        "primary_metric": metric,
        "rate_key": rate_key,
        "observed_rate": round(observed_rate, 8),
        "league_baseline_rate": round(baseline_rate, 8),
        "sample_size": sample_size,
        "sample_weight": blended["sample_weight"],
        "source_status": source_status,
        "source_name": packet.get("source_name"),
        "per_opportunity_probability_decimal": round(per_opportunity_probability, 8),
        "per_opportunity_probability": phase16_probability_percent(
            per_opportunity_probability,
            2,
        ),
        "probability_decimal": round(final_probability, 8),
        "probability": phase16_probability_percent(final_probability, 1),
        "probability_percent": phase16_probability_percent(final_probability, 1),
        "confidence": confidence,
        "confidence_band": confidence_band(confidence).value,
        "unit": final_unit,
        "expected_opportunities": round(resolved_opportunities, 3),
        "expected_value": round(per_opportunity_probability * resolved_opportunities, 6),
        "interval": interval.to_dict(),
        "technical_profile": technical_profile,
        "model": "AISP2 Player-Specific Bayesian Shrinkage Adapter",
        "model_status": "player_specific_math_active" if not no_sample else "no_sample_guard",
        "math": {
            "formula": blended["math_formula"],
            "observed_component": round(observed_rate * blended["sample_weight"], 8),
            "baseline_component": round(baseline_rate * (1.0 - blended["sample_weight"]), 8),
            "per_opportunity_probability_decimal": round(per_opportunity_probability, 8),
            "per_game_formula": "1 - (1 - p) ** opportunities" if per_game else None,
            "used_no_sample_guard": blended["used_no_sample_guard"],
        },
        "components": {
            "observed_rate": round(observed_rate, 8),
            "league_baseline_rate": round(baseline_rate, 8),
            "sample_weight": round(blended["sample_weight"], 8),
            "coverage": phase16_read_nested(packet, ("probability_inputs", "coverage"), 0.0),
        },
        "diagnostics": {
            "feature_packet_status": packet.get("status"),
            "feature_packet_valid": packet.get("valid"),
            "feature_packet_source_status": packet.get("source_status"),
            "feature_packet_source_name": packet.get("source_name"),
            "feature_packet_sample_size": packet.get("sample_size"),
            "feature_packet_fingerprint": packet.get("feature_fingerprint"),
            "feature_packet_debug": packet.get("debug", {}),
            "adapter_outcome": selected_outcome,
            "adapter_rate_key": rate_key,
            "adapter_unit": final_unit,
        },
        "warnings": warnings,
        "explanation": explanation,
    }


def build_workbench_prop_probability_library(
    feature_packet: Mapping[str, Any],
    *,
    per_game: bool = True,
) -> dict[str, float]:
    outcomes = (
        "home_run",
        "hit",
        "single",
        "double",
        "triple",
        "walk",
        "strikeout",
        "rbi",
        "run_scored",
        "total_bases",
        "extra_base_hit",
        "reach_base",
    )

    output: dict[str, float] = {}

    for outcome in outcomes:
        estimate = calculate_workbench_probability_from_feature_packet(
            feature_packet,
            outcome_key=outcome,
            per_game=per_game,
        )
        output[outcome] = estimate["probability"]

    return output


def predict_workbench_feature_packet(
    feature_packet: Mapping[str, Any],
    *,
    outcome_key: str | None = None,
    per_game: bool = True,
) -> dict[str, Any]:
    estimate = calculate_workbench_probability_from_feature_packet(
        feature_packet,
        outcome_key=outcome_key,
        per_game=per_game,
    )

    prop_probabilities = build_workbench_prop_probability_library(
        feature_packet,
        per_game=per_game,
    )

    prediction = {
        "estimated_probability": estimate["probability"],
        "probability": estimate["probability"],
        "probability_decimal": estimate["probability_decimal"],
        "confidence": estimate["confidence"],
        "confidence_band": estimate["confidence_band"],
        "model": estimate["model"],
        "model_version": PHASE_16_PART_3E_PROBABILITY_ADAPTER_VERSION,
        "prediction_source": estimate["source_status"],
        "sample_size": estimate["sample_size"],
        "observed_rate": round(estimate["observed_rate"] * 100.0, 2),
        "league_baseline_rate": round(estimate["league_baseline_rate"] * 100.0, 2),
        "sample_weight": estimate["sample_weight"],
        "primary_metric": estimate["primary_metric"],
        "unit": estimate["unit"],
        "expected_opportunities": estimate["expected_opportunities"],
        "expected_value": estimate["expected_value"],
        "tier": (
            "High"
            if estimate["probability"] >= 55
            else "Medium"
            if estimate["probability"] >= 25
            else "Low-Medium"
            if estimate["probability"] >= 8
            else "Low"
        ),
        "risk_profile": (
            "No Hitting Sample"
            if estimate["sample_size"] <= 0
            else estimate["technical_profile"].get("primary_risk", "Normal Baseball Variance")
            if isinstance(estimate["technical_profile"], Mapping)
            else "Normal Baseball Variance"
        ),
        "interval": estimate["interval"],
        "math": estimate["math"],
        "components": estimate["components"],
        "missing_inputs": [],
    }

    return {
        "status": estimate["status"],
        "success": True,
        "adapter_version": PHASE_16_PART_3E_PROBABILITY_ADAPTER_VERSION,
        "engine": estimate["engine"],
        "engine_version": estimate["engine_version"],
        "player_name": estimate["player_name"],
        "team_name": estimate["team_name"],
        "player_id": estimate["player_id"],
        "mlb_player_id": estimate["mlb_player_id"],
        "outcome_key": estimate["outcome_key"],
        "primary_metric": estimate["primary_metric"],
        "probability": estimate["probability"],
        "confidence": estimate["confidence"],
        "sample_size": estimate["sample_size"],
        "source_status": estimate["source_status"],
        "source_name": estimate["source_name"],
        "prediction": prediction,
        "prop_probabilities": prop_probabilities,
        "technical_profile": estimate["technical_profile"],
        "explanation": estimate["explanation"],
        "warnings": estimate["warnings"],
        "diagnostics": estimate["diagnostics"],
        "math": estimate["math"],
    }


def validate_phase_16_part_3e_probability_adapter() -> dict[str, Any]:
    judge_packet = {
        "status": "ok",
        "valid": True,
        "player_id": 592450,
        "mlb_player_id": 592450,
        "player_name": "Aaron Judge",
        "team_name": "New York Yankees",
        "outcome_key": "home_run",
        "sample_size": 704,
        "source_status": "synthetic_validation",
        "source_name": "synthetic_validation_packet",
        "stat_line": {
            "plate_appearances": 704,
            "at_bats": 559,
            "hits": 180,
            "singles": 91,
            "doubles": 36,
            "triples": 1,
            "home_runs": 52,
            "walks": 120,
            "strikeouts": 171,
            "rbi": 131,
            "runs": 128,
            "total_bases": 374,
            "sample_size": 704,
            "ops": 1.159,
        },
        "rates": {
            "hr_per_pa": 52 / 704,
            "hit_per_ab": 180 / 559,
            "single_per_ab": 91 / 559,
            "double_per_ab": 36 / 559,
            "triple_per_ab": 1 / 559,
            "bb_per_pa": 120 / 704,
            "k_per_pa": 171 / 704,
            "rbi_per_pa": 131 / 704,
            "run_per_pa": 128 / 704,
            "tb_per_ab": 374 / 559,
            "xbh_per_pa": 89 / 704,
            "times_on_base_per_pa": 300 / 704,
            "avg": 0.322,
            "obp": 0.458,
            "slg": 0.701,
            "ops": 1.159,
            "iso": 0.379,
        },
        "probability_inputs": {
            "outcome_key": "home_run",
            "coverage": 1.0,
            "sample_size": 704,
            "source_status": "synthetic_validation",
        },
        "technical_profile": {
            "sample_quality": "strong",
            "primary_strength": "Power",
            "primary_risk": "Strikeout Rate",
        },
        "feature_fingerprint": "synthetic_judge_packet",
    }

    contact_packet = {
        **judge_packet,
        "player_id": 123,
        "mlb_player_id": 123,
        "player_name": "Low Power Contact Validation Player",
        "sample_size": 550,
        "stat_line": {
            **judge_packet["stat_line"],
            "plate_appearances": 550,
            "at_bats": 510,
            "hits": 145,
            "singles": 120,
            "doubles": 20,
            "triples": 3,
            "home_runs": 2,
            "walks": 30,
            "strikeouts": 70,
            "rbi": 45,
            "runs": 62,
            "total_bases": 177,
            "sample_size": 550,
            "ops": 0.700,
        },
        "rates": {
            "hr_per_pa": 2 / 550,
            "hit_per_ab": 145 / 510,
            "single_per_ab": 120 / 510,
            "double_per_ab": 20 / 510,
            "triple_per_ab": 3 / 510,
            "bb_per_pa": 30 / 550,
            "k_per_pa": 70 / 550,
            "rbi_per_pa": 45 / 550,
            "run_per_pa": 62 / 550,
            "tb_per_ab": 177 / 510,
            "xbh_per_pa": 25 / 550,
            "times_on_base_per_pa": 175 / 550,
            "avg": 145 / 510,
            "obp": 0.318,
            "slg": 177 / 510,
            "ops": 0.700,
            "iso": 0.063,
        },
        "technical_profile": {
            "sample_quality": "strong",
            "primary_strength": "Contact",
            "primary_risk": "Low Power",
        },
        "feature_fingerprint": "synthetic_contact_packet",
    }

    judge_hr = predict_workbench_feature_packet(
        judge_packet,
        outcome_key="home_run",
        per_game=True,
    )

    contact_hr = predict_workbench_feature_packet(
        contact_packet,
        outcome_key="home_run",
        per_game=True,
    )

    judge_hit = predict_workbench_feature_packet(
        judge_packet,
        outcome_key="hit",
        per_game=True,
    )

    judge_walk = predict_workbench_feature_packet(
        judge_packet,
        outcome_key="walk",
        per_game=True,
    )

    judge_strikeout = predict_workbench_feature_packet(
        judge_packet,
        outcome_key="strikeout",
        per_game=True,
    )

    checks = {
        "adapter_callable": callable(predict_workbench_feature_packet),
        "judge_probability_present": judge_hr["probability"] is not None,
        "contact_probability_present": contact_hr["probability"] is not None,
        "judge_hr_greater_than_contact_hr": judge_hr["probability"] > contact_hr["probability"],
        "judge_hit_differs_from_judge_hr": abs(judge_hit["probability"] - judge_hr["probability"]) > 5.0,
        "walk_differs_from_strikeout": abs(judge_walk["probability"] - judge_strikeout["probability"]) > 5.0,
        "prop_library_present": isinstance(judge_hr.get("prop_probabilities"), dict),
        "math_formula_present": bool(judge_hr.get("math", {}).get("formula")),
        "sample_weight_positive": judge_hr["prediction"]["sample_weight"] > 0,
        "confidence_positive": judge_hr["confidence"] > 0,
    }

    passed = sum(1 for value in checks.values() if value)

    return {
        "status": "ok" if passed == len(checks) else "failed",
        "phase": "Phase 16 Part 3E",
        "adapter_version": PHASE_16_PART_3E_PROBABILITY_ADAPTER_VERSION,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "failed_checks": [
            key
            for key, value in checks.items()
            if not value
        ],
        "sample_results": {
            "judge_home_run_probability": judge_hr["probability"],
            "contact_home_run_probability": contact_hr["probability"],
            "judge_hit_probability": judge_hit["probability"],
            "judge_walk_probability": judge_walk["probability"],
            "judge_strikeout_probability": judge_strikeout["probability"],
            "judge_home_run_math": judge_hr["math"],
            "judge_home_run_prediction": judge_hr["prediction"],
        },
    }


try:
    __all__.extend(
        [
            "PHASE_16_PART_3E_PROBABILITY_ADAPTER_VERSION",
            "PHASE_16_OUTCOME_RATE_MAP",
            "phase16_normalize_workbench_outcome",
            "build_player_profile_from_feature_packet",
            "calculate_workbench_probability_from_feature_packet",
            "build_workbench_prop_probability_library",
            "predict_workbench_feature_packet",
            "validate_phase_16_part_3e_probability_adapter",
        ]
    )
except Exception:
    pass