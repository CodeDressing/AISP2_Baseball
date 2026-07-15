# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# PHASE 10 PART 16.0
# FILE: 04_ai/nlp/__init__.py
# PURPOSE:
# Single authoritative public API and orchestration gateway for
# the complete AISP2 Baseball NLP subsystem.
#
# ARCHITECTURAL CONTRACT:
# 1. nlu_engine.py is the primary router.
# 2. semantic_engine.py is fallback-only.
# 3. This module exposes one orchestration function.
# 4. External callers should import from nlp, not internals.
# 5. Internal module failures are isolated and diagnosed.
# 6. Accepted primary routes are never silently replaced.
# ============================================================

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from collections import Counter
from collections import defaultdict
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import MutableMapping
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
from enum import Enum
from functools import lru_cache
from hashlib import sha256
import importlib
import inspect
import json
import logging
import threading
import time
import traceback
from types import ModuleType
from typing import Any
from typing import Final


# ============================================================
# SECTION 02 - PACKAGE METADATA
# ============================================================

NLP_PACKAGE_NAME: Final[str] = "AISP2 Enterprise Baseball NLP"
NLP_PACKAGE_VERSION: Final[str] = "7.0.0"
NLP_PACKAGE_PHASE: Final[str] = "Phase 10 Part 16.0"
NLP_PACKAGE_PATH: Final[str] = "04_ai/nlp/__init__.py"
NLP_PACKAGE_STATUS: Final[str] = "enterprise_ready"
NLP_SCHEMA_VERSION: Final[str] = "4.0.0"

PRIMARY_ROUTER_MODULE: Final[str] = "nlu_engine"
SEMANTIC_FALLBACK_MODULE: Final[str] = "semantic_engine"

AUTHORITATIVE_ORCHESTRATION_FUNCTION: Final[str] = (
    "orchestrate_nlp"
)

NLP_PUBLIC_API_CONTRACT: Final[str] = (
    "single_gateway"
)


# ============================================================
# SECTION 03 - LOGGING
# ============================================================

LOGGER = logging.getLogger(
    "aisp2.nlp"
)


# ============================================================
# SECTION 04 - ENUMERATIONS
# ============================================================

class NLPExecutionStatus(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class NLPRouterRole(str, Enum):
    PRIMARY = "primary"
    FALLBACK = "fallback"
    SUPPORT = "support"


class NLPStage(str, Enum):
    INPUT = "input"
    CONTEXT = "context"
    PRIMARY_ROUTER = "primary_router"
    ENTITY_SUPPORT = "entity_support"
    FUZZY_SUPPORT = "fuzzy_support"
    SEMANTIC_FALLBACK = "semantic_fallback"
    MERGE = "merge"
    VALIDATION = "validation"
    OUTPUT = "output"


class NLPFallbackReason(str, Enum):
    NONE = "none"
    NO_PRIMARY_RESULT = "no_primary_result"
    PRIMARY_FAILED = "primary_failed"
    PRIMARY_UNRESOLVED = "primary_unresolved"
    PRIMARY_LOW_CONFIDENCE = "primary_low_confidence"
    PRIMARY_AMBIGUOUS = "primary_ambiguous"
    MISSING_REQUIRED_ENTITY = "missing_required_entity"
    EXPLICIT_REQUEST = "explicit_request"


class NLPDiagnosticSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NLPModuleName(str, Enum):
    NLU_ENGINE = "nlu_engine"
    INTENT_DETECTION = "intent_detection"
    ENTITY_DETECTION = "entity_detection"
    CONTEXT_BUILDER = "context_builder"
    FUZZY_MATCHING = "fuzzy_matching"
    SEMANTIC_ENGINE = "semantic_engine"


# ============================================================
# SECTION 05 - CONFIGURATION
# ============================================================

@dataclass(slots=True)
class NLPOrchestrationConfig:
    primary_confidence_threshold: float = 0.78
    fallback_confidence_threshold: float = 0.62
    unresolved_confidence_threshold: float = 0.40

    enable_context: bool = True
    enable_entity_support: bool = True
    enable_fuzzy_support: bool = True
    enable_semantic_fallback: bool = True

    preserve_primary_intent: bool = True
    preserve_primary_entities: bool = True
    allow_semantic_override: bool = False

    strict_primary_router: bool = True
    tolerate_support_module_failures: bool = True
    include_diagnostics: bool = True
    include_stage_timings: bool = True
    include_raw_module_results: bool = False
    include_audit_record: bool = True

    maximum_diagnostics: int = 100
    maximum_candidates: int = 10

    def validate(self) -> None:
        for field_name in (
            "primary_confidence_threshold",
            "fallback_confidence_threshold",
            "unresolved_confidence_threshold",
        ):
            value = float(
                getattr(self, field_name)
            )

            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        if self.allow_semantic_override:
            raise ValueError(
                "semantic fallback may not override the primary router"
            )

        if self.maximum_diagnostics <= 0:
            raise ValueError(
                "maximum_diagnostics must be positive"
            )

        if self.maximum_candidates <= 0:
            raise ValueError(
                "maximum_candidates must be positive"
            )


DEFAULT_NLP_CONFIG = NLPOrchestrationConfig()


# ============================================================
# SECTION 06 - DIAGNOSTIC CONTRACTS
# ============================================================

@dataclass(slots=True)
class NLPDiagnostic:
    stage: NLPStage
    severity: NLPDiagnosticSeverity
    code: str
    message: str
    module: str | None = None
    exception_type: str | None = None
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "module": self.module,
            "exception_type": self.exception_type,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class NLPStageTiming:
    stage: NLPStage
    duration_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "duration_ms": round(
                float(self.duration_ms),
                6,
            ),
        }


@dataclass(slots=True)
class NLPModuleState:
    module_name: str
    imported: bool
    role: NLPRouterRole
    version: str | None = None
    phase: str | None = None
    validation_status: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# SECTION 07 - PRIMARY ROUTE CONTRACT
# ============================================================

@dataclass(slots=True)
class PrimaryRoute:
    intent: str | None = None
    confidence: float = 0.0
    accepted: bool = False
    unresolved: bool = False
    ambiguous: bool = False

    player: str | None = None
    team: str | None = None
    outcome: str | None = None

    players: list[str] = field(
        default_factory=list
    )
    teams: list[str] = field(
        default_factory=list
    )
    outcomes: list[str] = field(
        default_factory=list
    )

    missing_required_entities: list[str] = field(
        default_factory=list
    )

    raw: dict[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any] | None,
    ) -> "PrimaryRoute":
        if not payload:
            return cls()

        confidence = coerce_confidence(
            payload.get("confidence", 0.0)
        )

        intent = (
            payload.get("intent")
            or payload.get("route")
            or payload.get("intent_name")
            or payload.get("primary_intent")
        )

        accepted = bool(
            payload.get("accepted")
            or payload.get("matched")
            or payload.get("route_accepted")
            or payload.get("status") in {
                "ok",
                "accepted",
                "resolved",
            }
        )

        unresolved = bool(
            payload.get("unresolved")
            or payload.get("needs_fallback")
            or payload.get("status") in {
                "unknown",
                "unresolved",
                "no_match",
            }
        )

        ambiguous = bool(
            payload.get("ambiguous")
            or payload.get("decision")
            == "ambiguous"
        )

        return cls(
            intent=(
                str(intent)
                if intent is not None
                else None
            ),
            confidence=confidence,
            accepted=accepted,
            unresolved=unresolved,
            ambiguous=ambiguous,
            player=_first_string(
                payload,
                (
                    "player",
                    "player_name",
                    "resolved_player",
                ),
            ),
            team=_first_string(
                payload,
                (
                    "team",
                    "team_name",
                    "resolved_team",
                ),
            ),
            outcome=_first_string(
                payload,
                (
                    "outcome",
                    "stat",
                    "target_outcome",
                ),
            ),
            players=_coerce_string_list(
                payload.get("players")
            ),
            teams=_coerce_string_list(
                payload.get("teams")
            ),
            outcomes=_coerce_string_list(
                payload.get("outcomes")
            ),
            missing_required_entities=(
                _coerce_string_list(
                    payload.get(
                        "missing_required_entities"
                    )
                    or payload.get(
                        "missing_entities"
                    )
                )
            ),
            raw=dict(payload),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "confidence": round(
                float(self.confidence),
                6,
            ),
            "accepted": self.accepted,
            "unresolved": self.unresolved,
            "ambiguous": self.ambiguous,
            "player": self.player,
            "team": self.team,
            "outcome": self.outcome,
            "players": list(self.players),
            "teams": list(self.teams),
            "outcomes": list(self.outcomes),
            "missing_required_entities": list(
                self.missing_required_entities
            ),
            "raw": dict(self.raw),
        }


# ============================================================
# SECTION 08 - ORCHESTRATION RESULT
# ============================================================

@dataclass(slots=True)
class NLPOrchestrationResult:
    message: str
    normalized_message: str

    status: NLPExecutionStatus
    intent: str | None
    confidence: float

    primary_route: PrimaryRoute
    fallback_used: bool
    fallback_reason: NLPFallbackReason

    player: str | None = None
    team: str | None = None
    outcome: str | None = None

    players: list[str] = field(
        default_factory=list
    )
    teams: list[str] = field(
        default_factory=list
    )
    outcomes: list[str] = field(
        default_factory=list
    )

    context: dict[str, Any] = field(
        default_factory=dict
    )
    semantic_fallback: dict[str, Any] | None = None
    fuzzy_support: dict[str, Any] | None = None
    entity_support: dict[str, Any] | None = None

    clarification_required: bool = False
    clarification_question: str | None = None

    diagnostics: list[NLPDiagnostic] = field(
        default_factory=list
    )
    timings: list[NLPStageTiming] = field(
        default_factory=list
    )

    module_states: list[NLPModuleState] = field(
        default_factory=list
    )

    raw_results: dict[str, Any] = field(
        default_factory=dict
    )
    audit: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_name": NLP_PACKAGE_NAME,
            "package_version": NLP_PACKAGE_VERSION,
            "package_phase": NLP_PACKAGE_PHASE,
            "orchestration_function": (
                AUTHORITATIVE_ORCHESTRATION_FUNCTION
            ),
            "message": self.message,
            "normalized_message": (
                self.normalized_message
            ),
            "status": self.status.value,
            "intent": self.intent,
            "confidence": round(
                float(self.confidence),
                6,
            ),
            "primary_route": (
                self.primary_route.to_dict()
            ),
            "fallback_used": self.fallback_used,
            "fallback_reason": (
                self.fallback_reason.value
            ),
            "player": self.player,
            "team": self.team,
            "outcome": self.outcome,
            "players": list(self.players),
            "teams": list(self.teams),
            "outcomes": list(self.outcomes),
            "context": dict(self.context),
            "semantic_fallback": (
                dict(self.semantic_fallback)
                if self.semantic_fallback
                else None
            ),
            "fuzzy_support": (
                dict(self.fuzzy_support)
                if self.fuzzy_support
                else None
            ),
            "entity_support": (
                dict(self.entity_support)
                if self.entity_support
                else None
            ),
            "clarification_required": (
                self.clarification_required
            ),
            "clarification_question": (
                self.clarification_question
            ),
            "diagnostics": [
                item.to_dict()
                for item in self.diagnostics
            ],
            "timings": [
                item.to_dict()
                for item in self.timings
            ],
            "module_states": [
                item.to_dict()
                for item in self.module_states
            ],
            "raw_results": dict(
                self.raw_results
            ),
            "audit": dict(self.audit),
        }


# ============================================================
# SECTION 09 - GENERAL UTILITIES
# ============================================================

def coerce_confidence(
    value: Any,
) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0

    if confidence > 1.0:
        confidence = confidence / 100.0

    return max(
        0.0,
        min(1.0, confidence),
    )


def _coerce_string_list(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        return [value] if value.strip() else []

    if isinstance(value, Iterable):
        output = []

        for item in value:
            if item is None:
                continue

            text = str(item).strip()

            if text:
                output.append(text)

        return unique_strings(output)

    return []


def _first_string(
    payload: Mapping[str, Any],
    keys: Sequence[str],
) -> str | None:
    for key in keys:
        value = payload.get(key)

        if isinstance(value, str):
            value = value.strip()

            if value:
                return value

    return None


def unique_strings(
    values: Iterable[Any],
) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()

    for value in values:
        if value is None:
            continue

        text = str(value).strip()

        if not text:
            continue

        key = text.casefold()

        if key in seen:
            continue

        seen.add(key)
        output.append(text)

    return output


def safe_mapping_get(
    payload: Mapping[str, Any] | None,
    *keys: str,
    default: Any = None,
) -> Any:
    current: Any = payload

    for key in keys:
        if (
            not isinstance(current, Mapping)
            or key not in current
        ):
            return default

        current = current.get(key)

    return current


def normalize_message(
    message: str | None,
) -> str:
    text = str(message or "")
    return " ".join(
        text.strip().split()
    )


def fingerprint_payload(
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
# SECTION 10 - MODULE REGISTRY
# ============================================================

@dataclass(slots=True)
class ModuleDescriptor:
    name: NLPModuleName
    role: NLPRouterRole
    required: bool
    import_candidates: tuple[str, ...]
    validation_functions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name.value,
            "role": self.role.value,
            "required": self.required,
            "import_candidates": list(
                self.import_candidates
            ),
            "validation_functions": list(
                self.validation_functions
            ),
        }


MODULE_REGISTRY: Final[
    tuple[ModuleDescriptor, ...]
] = (
    ModuleDescriptor(
        name=NLPModuleName.NLU_ENGINE,
        role=NLPRouterRole.PRIMARY,
        required=True,
        import_candidates=(
            ".nlu_engine",
            "nlp.nlu_engine",
            "nlu_engine",
        ),
        validation_functions=(
            "validate_nlu_engine_module",
            "validate_nlu_engine",
        ),
    ),
    ModuleDescriptor(
        name=NLPModuleName.INTENT_DETECTION,
        role=NLPRouterRole.SUPPORT,
        required=False,
        import_candidates=(
            ".intent_detection",
            "nlp.intent_detection",
            "intent_detection",
        ),
        validation_functions=(
            "validate_intent_detection_module",
        ),
    ),
    ModuleDescriptor(
        name=NLPModuleName.ENTITY_DETECTION,
        role=NLPRouterRole.SUPPORT,
        required=False,
        import_candidates=(
            ".entity_detection",
            "nlp.entity_detection",
            "entity_detection",
        ),
        validation_functions=(
            "validate_entity_detection_module",
        ),
    ),
    ModuleDescriptor(
        name=NLPModuleName.CONTEXT_BUILDER,
        role=NLPRouterRole.SUPPORT,
        required=False,
        import_candidates=(
            ".context_builder",
            "nlp.context_builder",
            "context_builder",
        ),
        validation_functions=(
            "validate_context_builder_module",
        ),
    ),
    ModuleDescriptor(
        name=NLPModuleName.FUZZY_MATCHING,
        role=NLPRouterRole.SUPPORT,
        required=False,
        import_candidates=(
            ".fuzzy_matching",
            "nlp.fuzzy_matching",
            "fuzzy_matching",
        ),
        validation_functions=(
            "validate_fuzzy_matching_module",
        ),
    ),
    ModuleDescriptor(
        name=NLPModuleName.SEMANTIC_ENGINE,
        role=NLPRouterRole.FALLBACK,
        required=False,
        import_candidates=(
            ".semantic_engine",
            "nlp.semantic_engine",
            "semantic_engine",
        ),
        validation_functions=(
            "validate_semantic_engine_module",
        ),
    ),
)


# ============================================================
# SECTION 11 - MODULE LOADING
# ============================================================

_MODULE_CACHE: dict[
    str,
    ModuleType | None,
] = {}
_MODULE_CACHE_LOCK = threading.RLock()


def clear_nlp_module_cache() -> None:
    with _MODULE_CACHE_LOCK:
        _MODULE_CACHE.clear()


def _import_module_candidate(
    candidate: str,
) -> ModuleType:
    if candidate.startswith("."):
        return importlib.import_module(
            candidate,
            package=__name__,
        )

    return importlib.import_module(
        candidate
    )


def load_nlp_module(
    descriptor: ModuleDescriptor,
    *,
    force_reload: bool = False,
) -> ModuleType | None:
    cache_key = descriptor.name.value

    with _MODULE_CACHE_LOCK:
        if (
            not force_reload
            and cache_key in _MODULE_CACHE
        ):
            return _MODULE_CACHE[cache_key]

    imported: ModuleType | None = None

    for candidate in descriptor.import_candidates:
        try:
            imported = _import_module_candidate(
                candidate
            )
            break
        except Exception:
            continue

    with _MODULE_CACHE_LOCK:
        _MODULE_CACHE[cache_key] = imported

    return imported


def get_module_descriptor(
    module_name: NLPModuleName | str,
) -> ModuleDescriptor | None:
    key = (
        module_name.value
        if isinstance(module_name, NLPModuleName)
        else str(module_name)
    )

    for descriptor in MODULE_REGISTRY:
        if descriptor.name.value == key:
            return descriptor

    return None


# ============================================================
# SECTION 12 - FUNCTION RESOLUTION
# ============================================================

def resolve_callable(
    module: ModuleType | None,
    names: Sequence[str],
) -> Callable[..., Any] | None:
    if module is None:
        return None

    for name in names:
        value = getattr(
            module,
            name,
            None,
        )

        if callable(value):
            return value

    return None


def call_with_supported_arguments(
    function: Callable[..., Any],
    **kwargs: Any,
) -> Any:
    signature = inspect.signature(
        function
    )

    accepts_kwargs = any(
        parameter.kind
        == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )

    if accepts_kwargs:
        return function(**kwargs)

    supported = {
        key: value
        for key, value in kwargs.items()
        if key in signature.parameters
    }

    return function(**supported)


# ============================================================
# SECTION 13 - MODULE STATE INSPECTION
# ============================================================

def inspect_module_state(
    descriptor: ModuleDescriptor,
    module: ModuleType | None,
) -> NLPModuleState:
    if module is None:
        return NLPModuleState(
            module_name=descriptor.name.value,
            imported=False,
            role=descriptor.role,
            error="module_not_available",
        )

    version = None
    phase = None

    for attribute_name in (
        "NLU_ENGINE_VERSION",
        "FUZZY_ENGINE_VERSION",
        "SEMANTIC_ENGINE_VERSION",
        "CONTEXT_ENGINE_VERSION",
        "INTENT_ENGINE_VERSION",
        "ENTITY_ENGINE_VERSION",
        "__version__",
    ):
        value = getattr(
            module,
            attribute_name,
            None,
        )

        if value:
            version = str(value)
            break

    for attribute_name in (
        "NLU_ENGINE_PHASE",
        "FUZZY_ENGINE_PHASE",
        "SEMANTIC_ENGINE_PHASE",
        "CONTEXT_ENGINE_PHASE",
        "INTENT_ENGINE_PHASE",
        "ENTITY_ENGINE_PHASE",
    ):
        value = getattr(
            module,
            attribute_name,
            None,
        )

        if value:
            phase = str(value)
            break

    validation_status = None

    for function_name in (
        descriptor.validation_functions
    ):
        function = getattr(
            module,
            function_name,
            None,
        )

        if callable(function):
            try:
                result = function()

                if isinstance(result, Mapping):
                    validation_status = str(
                        result.get(
                            "status",
                            "unknown",
                        )
                    )
                else:
                    validation_status = "unknown"

            except Exception as error:
                validation_status = "failed"
                return NLPModuleState(
                    module_name=descriptor.name.value,
                    imported=True,
                    role=descriptor.role,
                    version=version,
                    phase=phase,
                    validation_status=validation_status,
                    error=str(error),
                )

            break

    return NLPModuleState(
        module_name=descriptor.name.value,
        imported=True,
        role=descriptor.role,
        version=version,
        phase=phase,
        validation_status=validation_status,
    )


def inspect_all_module_states(
) -> list[NLPModuleState]:
    output = []

    for descriptor in MODULE_REGISTRY:
        module = load_nlp_module(
            descriptor
        )

        output.append(
            inspect_module_state(
                descriptor,
                module,
            )
        )

    return output


# ============================================================
# SECTION 14 - TIMING CONTEXT
# ============================================================

class StageTimer:
    def __init__(
        self,
        stage: NLPStage,
        timings: list[NLPStageTiming],
    ) -> None:
        self.stage = stage
        self.timings = timings
        self.started_at = 0.0

    def __enter__(
        self,
    ) -> "StageTimer":
        self.started_at = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        exc_traceback: Any,
    ) -> None:
        duration_ms = (
            time.perf_counter()
            - self.started_at
        ) * 1000.0

        self.timings.append(
            NLPStageTiming(
                stage=self.stage,
                duration_ms=duration_ms,
            )
        )


# ============================================================
# SECTION 15 - ERROR CAPTURE
# ============================================================

def diagnostic_from_exception(
    *,
    stage: NLPStage,
    code: str,
    message: str,
    module: str | None,
    error: BaseException,
) -> NLPDiagnostic:
    return NLPDiagnostic(
        stage=stage,
        severity=NLPDiagnosticSeverity.ERROR,
        code=code,
        message=message,
        module=module,
        exception_type=type(error).__name__,
        metadata={
            "exception": str(error),
            "traceback": "".join(
                traceback.format_exception(
                    type(error),
                    error,
                    error.__traceback__,
                )
            ),
        },
    )


# ============================================================
# SECTION 16 - CONTEXT SUPPORT
# ============================================================

def build_context_support(
    message: str,
    *,
    context: Mapping[str, Any] | None,
    conversation_id: str | None,
    user_id: str | None,
    module: ModuleType | None,
) -> dict[str, Any]:
    if module is None:
        return dict(context or {})

    function = resolve_callable(
        module,
        (
            "build_context",
            "build_conversation_context",
            "resolve_context",
            "build_context_report",
            "process_context",
        ),
    )

    if function is None:
        return dict(context or {})

    result = call_with_supported_arguments(
        function,
        message=message,
        context=dict(context or {}),
        conversation_id=conversation_id,
        user_id=user_id,
    )

    if isinstance(result, Mapping):
        return dict(result)

    return dict(context or {})


# ============================================================
# SECTION 17 - PRIMARY NLU ROUTER
# ============================================================

PRIMARY_ROUTER_FUNCTION_CANDIDATES: Final[
    tuple[str, ...]
] = (
    "process_nlu",
    "analyze_message",
    "understand_message",
    "route_message",
    "process_message",
    "process_query",
    "handle_message",
    "interpret_message",
    "run_nlu",
    "orchestrate_nlu",
)


def execute_primary_router(
    message: str,
    *,
    context: Mapping[str, Any] | None,
    teams: Any,
    player_profiles: Any,
    database_session: Any,
    conversation_id: str | None,
    user_id: str | None,
    module: ModuleType | None,
) -> dict[str, Any]:
    if module is None:
        raise RuntimeError(
            "primary nlu_engine module is unavailable"
        )

    function = resolve_callable(
        module,
        PRIMARY_ROUTER_FUNCTION_CANDIDATES,
    )

    if function is None:
        raise RuntimeError(
            "nlu_engine exposes no recognized primary routing function"
        )

    result = call_with_supported_arguments(
        function,
        message=message,
        query=message,
        text=message,
        context=dict(context or {}),
        teams=teams,
        player_profiles=player_profiles,
        database_session=database_session,
        conversation_id=conversation_id,
        user_id=user_id,
    )

    if isinstance(result, Mapping):
        return dict(result)

    if hasattr(result, "to_dict"):
        converted = result.to_dict()

        if isinstance(converted, Mapping):
            return dict(converted)

    raise TypeError(
        "primary router returned an unsupported result type"
    )


# ============================================================
# SECTION 18 - ENTITY SUPPORT
# ============================================================

def execute_entity_support(
    message: str,
    *,
    teams: Any,
    player_profiles: Any,
    database_session: Any,
    module: ModuleType | None,
) -> dict[str, Any]:
    if module is None:
        return {}

    function = resolve_callable(
        module,
        (
            "detect_entities",
            "extract_entities",
            "build_entity_report",
            "analyze_entities",
            "resolve_entities",
        ),
    )

    if function is None:
        return {}

    result = call_with_supported_arguments(
        function,
        message=message,
        text=message,
        teams=teams,
        player_profiles=player_profiles,
        database_session=database_session,
    )

    if isinstance(result, Mapping):
        return dict(result)

    return {}


# ============================================================
# SECTION 19 - FUZZY SUPPORT
# ============================================================

def execute_fuzzy_support(
    message: str,
    *,
    teams: Any,
    player_profiles: Any,
    database_session: Any,
    module: ModuleType | None,
) -> dict[str, Any]:
    if module is None:
        return {}

    function = resolve_callable(
        module,
        (
            "build_fuzzy_nlp_report",
            "build_fuzzy_report",
            "analyze_fuzzy_message",
        ),
    )

    if function is None:
        return {}

    player_names = (
        list(player_profiles.keys())
        if isinstance(player_profiles, Mapping)
        else player_profiles
    )

    team_names = (
        list(teams.keys())
        if isinstance(teams, Mapping)
        else teams
    )

    result = call_with_supported_arguments(
        function,
        message=message,
        player_names=player_names,
        team_names=team_names,
        database_session=database_session,
        use_warehouse=True,
    )

    if isinstance(result, Mapping):
        return dict(result)

    return {}


# ============================================================
# SECTION 20 - SEMANTIC FALLBACK
# ============================================================

def execute_semantic_fallback(
    message: str,
    *,
    primary_route: Mapping[str, Any],
    context: Mapping[str, Any] | None,
    teams: Any,
    player_profiles: Any,
    database_session: Any,
    module: ModuleType | None,
) -> dict[str, Any]:
    if module is None:
        return {}

    function = resolve_callable(
        module,
        (
            "build_semantic_fallback_envelope",
            "analyze_semantic_fallback",
            "interpret_baseball_question",
        ),
    )

    if function is None:
        return {}

    result = call_with_supported_arguments(
        function,
        message=message,
        primary_route=primary_route,
        context=dict(context or {}),
        teams=teams,
        player_profiles=player_profiles,
        database_session=database_session,
    )

    if isinstance(result, Mapping):
        return dict(result)

    return {}


# ============================================================
# SECTION 21 - FALLBACK POLICY
# ============================================================

def determine_fallback_reason(
    primary: PrimaryRoute,
    *,
    primary_failed: bool,
    explicit_fallback: bool,
    config: NLPOrchestrationConfig,
) -> NLPFallbackReason:
    if explicit_fallback:
        return NLPFallbackReason.EXPLICIT_REQUEST

    if primary_failed:
        return NLPFallbackReason.PRIMARY_FAILED

    if not primary.raw:
        return NLPFallbackReason.NO_PRIMARY_RESULT

    if primary.ambiguous:
        return NLPFallbackReason.PRIMARY_AMBIGUOUS

    if primary.missing_required_entities:
        return NLPFallbackReason.MISSING_REQUIRED_ENTITY

    if primary.unresolved:
        return NLPFallbackReason.PRIMARY_UNRESOLVED

    if (
        primary.confidence
        < config.fallback_confidence_threshold
    ):
        return NLPFallbackReason.PRIMARY_LOW_CONFIDENCE

    return NLPFallbackReason.NONE


def should_use_semantic_fallback(
    primary: PrimaryRoute,
    *,
    primary_failed: bool,
    explicit_fallback: bool,
    config: NLPOrchestrationConfig,
) -> bool:
    if not config.enable_semantic_fallback:
        return False

    reason = determine_fallback_reason(
        primary,
        primary_failed=primary_failed,
        explicit_fallback=explicit_fallback,
        config=config,
    )

    return reason != NLPFallbackReason.NONE


# ============================================================
# SECTION 22 - ENTITY MERGE POLICY
# ============================================================

def _extract_entity_values(
    payload: Mapping[str, Any] | None,
    singular: str,
    plural: str,
) -> tuple[str | None, list[str]]:
    if not payload:
        return None, []

    singular_value = payload.get(singular)

    singular_text = (
        str(singular_value).strip()
        if singular_value is not None
        and str(singular_value).strip()
        else None
    )

    plural_values = _coerce_string_list(
        payload.get(plural)
    )

    if singular_text:
        plural_values = unique_strings(
            [
                singular_text,
                *plural_values,
            ]
        )

    return singular_text, plural_values


def merge_entities(
    primary: PrimaryRoute,
    *,
    entity_support: Mapping[str, Any] | None,
    fuzzy_support: Mapping[str, Any] | None,
    semantic_fallback: Mapping[str, Any] | None,
    preserve_primary: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for singular, plural in (
        ("player", "players"),
        ("team", "teams"),
        ("outcome", "outcomes"),
    ):
        primary_singular = getattr(
            primary,
            singular,
        )
        primary_plural = list(
            getattr(primary, plural)
        )

        support_singular, support_plural = (
            _extract_entity_values(
                entity_support,
                singular,
                plural,
            )
        )

        fuzzy_singular = None
        fuzzy_plural: list[str] = []

        if fuzzy_support:
            match_payload = fuzzy_support.get(
                f"{singular}_match"
            )

            if isinstance(match_payload, Mapping):
                best_match = match_payload.get(
                    "best_match"
                )

                if isinstance(best_match, Mapping):
                    fuzzy_singular = (
                        best_match.get(
                            "canonical_name"
                        )
                    )

                elif isinstance(best_match, str):
                    fuzzy_singular = best_match

                if fuzzy_singular:
                    fuzzy_plural.append(
                        str(fuzzy_singular)
                    )

        semantic_singular, semantic_plural = (
            _extract_entity_values(
                semantic_fallback,
                singular,
                plural,
            )
        )

        merged_plural = unique_strings(
            [
                *primary_plural,
                primary_singular,
                *support_plural,
                support_singular,
                *fuzzy_plural,
                fuzzy_singular,
                *semantic_plural,
                semantic_singular,
            ]
        )

        if preserve_primary and primary_singular:
            merged_singular = primary_singular

        else:
            merged_singular = (
                primary_singular
                or support_singular
                or fuzzy_singular
                or semantic_singular
                or (
                    merged_plural[0]
                    if merged_plural
                    else None
                )
            )

        result[singular] = merged_singular
        result[plural] = merged_plural

    return result


# ============================================================
# SECTION 23 - INTENT MERGE POLICY
# ============================================================

def merge_intent(
    primary: PrimaryRoute,
    semantic_fallback: Mapping[str, Any] | None,
    *,
    preserve_primary: bool,
) -> tuple[str | None, float]:
    semantic_intent = (
        semantic_fallback.get(
            "recommended_intent"
        )
        if semantic_fallback
        else None
    )
    semantic_confidence = coerce_confidence(
        semantic_fallback.get(
            "recommended_confidence",
            0.0,
        )
        if semantic_fallback
        else 0.0
    )

    if preserve_primary and primary.intent:
        return (
            primary.intent,
            primary.confidence,
        )

    if primary.intent:
        return (
            primary.intent,
            primary.confidence,
        )

    if semantic_intent:
        return (
            str(semantic_intent),
            semantic_confidence,
        )

    return None, primary.confidence


# ============================================================
# SECTION 24 - CLARIFICATION MERGE
# ============================================================

def merge_clarification(
    primary_payload: Mapping[str, Any],
    semantic_fallback: Mapping[str, Any] | None,
) -> tuple[bool, str | None]:
    primary_required = bool(
        primary_payload.get(
            "clarification_required"
        )
    )
    primary_question = (
        primary_payload.get(
            "clarification_question"
        )
    )

    semantic_required = bool(
        semantic_fallback.get(
            "clarification_required"
        )
        if semantic_fallback
        else False
    )
    semantic_question = (
        semantic_fallback.get(
            "clarification_question"
        )
        if semantic_fallback
        else None
    )

    if primary_required:
        return (
            True,
            str(primary_question)
            if primary_question
            else None,
        )

    if semantic_required:
        return (
            True,
            str(semantic_question)
            if semantic_question
            else None,
        )

    return False, None


# ============================================================
# SECTION 25 - AUDIT RECORD
# ============================================================

def build_nlp_audit_record(
    result: NLPOrchestrationResult,
) -> dict[str, Any]:
    stable_payload = {
        "message": result.message,
        "intent": result.intent,
        "confidence": result.confidence,
        "fallback_used": result.fallback_used,
        "fallback_reason": (
            result.fallback_reason.value
        ),
        "player": result.player,
        "team": result.team,
        "outcome": result.outcome,
        "players": result.players,
        "teams": result.teams,
        "outcomes": result.outcomes,
        "clarification_required": (
            result.clarification_required
        ),
    }

    return {
        "package": NLP_PACKAGE_NAME,
        "version": NLP_PACKAGE_VERSION,
        "phase": NLP_PACKAGE_PHASE,
        "function": (
            AUTHORITATIVE_ORCHESTRATION_FUNCTION
        ),
        "primary_router": PRIMARY_ROUTER_MODULE,
        "semantic_fallback": (
            SEMANTIC_FALLBACK_MODULE
        ),
        "semantic_override_allowed": False,
        "fingerprint": fingerprint_payload(
            stable_payload
        ),
        "created_at": datetime.now(
            UTC
        ).isoformat(),
        "stable_payload": stable_payload,
    }


# ============================================================
# SECTION 26 - AUTHORITATIVE ORCHESTRATION FUNCTION
# ============================================================

def orchestrate_nlp(
    message: str,
    *,
    context: Mapping[str, Any] | None = None,
    teams: Any = None,
    player_profiles: Any = None,
    database_session: Any = None,
    conversation_id: str | None = None,
    user_id: str | None = None,
    explicit_semantic_fallback: bool = False,
    config: NLPOrchestrationConfig | None = None,
) -> dict[str, Any]:
    config = config or NLPOrchestrationConfig()
    config.validate()

    normalized_message = normalize_message(
        message
    )

    diagnostics: list[
        NLPDiagnostic
    ] = []
    timings: list[
        NLPStageTiming
    ] = []
    raw_results: dict[
        str,
        Any,
    ] = {}

    if not normalized_message:
        diagnostics.append(
            NLPDiagnostic(
                stage=NLPStage.INPUT,
                severity=(
                    NLPDiagnosticSeverity.WARNING
                ),
                code="empty_message",
                message=(
                    "NLP orchestration received an empty message"
                ),
            )
        )

        empty_result = NLPOrchestrationResult(
            message=str(message or ""),
            normalized_message="",
            status=NLPExecutionStatus.FAILED,
            intent=None,
            confidence=0.0,
            primary_route=PrimaryRoute(),
            fallback_used=False,
            fallback_reason=(
                NLPFallbackReason.NONE
            ),
            diagnostics=diagnostics,
            timings=timings,
            module_states=(
                inspect_all_module_states()
            ),
        )

        if config.include_audit_record:
            empty_result.audit = (
                build_nlp_audit_record(
                    empty_result
                )
            )

        return empty_result.to_dict()

    module_map: dict[
        NLPModuleName,
        ModuleType | None,
    ] = {}

    module_states: list[
        NLPModuleState
    ] = []

    for descriptor in MODULE_REGISTRY:
        module = load_nlp_module(
            descriptor
        )
        module_map[
            descriptor.name
        ] = module
        module_states.append(
            inspect_module_state(
                descriptor,
                module,
            )
        )

    if (
        module_map[
            NLPModuleName.NLU_ENGINE
        ]
        is None
        and config.strict_primary_router
    ):
        diagnostics.append(
            NLPDiagnostic(
                stage=NLPStage.PRIMARY_ROUTER,
                severity=(
                    NLPDiagnosticSeverity.CRITICAL
                ),
                code=(
                    "primary_router_unavailable"
                ),
                message=(
                    "nlu_engine.py is required but unavailable"
                ),
                module=PRIMARY_ROUTER_MODULE,
            )
        )

    resolved_context = dict(
        context or {}
    )

    if config.enable_context:
        with StageTimer(
            NLPStage.CONTEXT,
            timings,
        ):
            try:
                resolved_context = (
                    build_context_support(
                        normalized_message,
                        context=context,
                        conversation_id=(
                            conversation_id
                        ),
                        user_id=user_id,
                        module=module_map[
                            NLPModuleName.CONTEXT_BUILDER
                        ],
                    )
                )

            except Exception as error:
                diagnostics.append(
                    diagnostic_from_exception(
                        stage=NLPStage.CONTEXT,
                        code=(
                            "context_support_failed"
                        ),
                        message=(
                            "Context support failed; original context retained"
                        ),
                        module=(
                            NLPModuleName.CONTEXT_BUILDER.value
                        ),
                        error=error,
                    )
                )

    primary_payload: dict[
        str,
        Any,
    ] = {}
    primary_failed = False

    with StageTimer(
        NLPStage.PRIMARY_ROUTER,
        timings,
    ):
        try:
            primary_payload = (
                execute_primary_router(
                    normalized_message,
                    context=resolved_context,
                    teams=teams,
                    player_profiles=(
                        player_profiles
                    ),
                    database_session=(
                        database_session
                    ),
                    conversation_id=(
                        conversation_id
                    ),
                    user_id=user_id,
                    module=module_map[
                        NLPModuleName.NLU_ENGINE
                    ],
                )
            )

        except Exception as error:
            primary_failed = True

            diagnostics.append(
                diagnostic_from_exception(
                    stage=(
                        NLPStage.PRIMARY_ROUTER
                    ),
                    code=(
                        "primary_router_failed"
                    ),
                    message=(
                        "Primary NLU router failed"
                    ),
                    module=(
                        NLPModuleName.NLU_ENGINE.value
                    ),
                    error=error,
                )
            )

    raw_results[
        "primary_router"
    ] = dict(primary_payload)

    primary_route = PrimaryRoute.from_mapping(
        primary_payload
    )

    entity_support: dict[
        str,
        Any,
    ] = {}

    if config.enable_entity_support:
        with StageTimer(
            NLPStage.ENTITY_SUPPORT,
            timings,
        ):
            try:
                entity_support = (
                    execute_entity_support(
                        normalized_message,
                        teams=teams,
                        player_profiles=(
                            player_profiles
                        ),
                        database_session=(
                            database_session
                        ),
                        module=module_map[
                            NLPModuleName.ENTITY_DETECTION
                        ],
                    )
                )

            except Exception as error:
                diagnostics.append(
                    diagnostic_from_exception(
                        stage=(
                            NLPStage.ENTITY_SUPPORT
                        ),
                        code=(
                            "entity_support_failed"
                        ),
                        message=(
                            "Entity support module failed"
                        ),
                        module=(
                            NLPModuleName.ENTITY_DETECTION.value
                        ),
                        error=error,
                    )
                )

    raw_results[
        "entity_support"
    ] = dict(entity_support)

    fuzzy_support: dict[
        str,
        Any,
    ] = {}

    if config.enable_fuzzy_support:
        with StageTimer(
            NLPStage.FUZZY_SUPPORT,
            timings,
        ):
            try:
                fuzzy_support = (
                    execute_fuzzy_support(
                        normalized_message,
                        teams=teams,
                        player_profiles=(
                            player_profiles
                        ),
                        database_session=(
                            database_session
                        ),
                        module=module_map[
                            NLPModuleName.FUZZY_MATCHING
                        ],
                    )
                )

            except Exception as error:
                diagnostics.append(
                    diagnostic_from_exception(
                        stage=(
                            NLPStage.FUZZY_SUPPORT
                        ),
                        code=(
                            "fuzzy_support_failed"
                        ),
                        message=(
                            "Fuzzy support module failed"
                        ),
                        module=(
                            NLPModuleName.FUZZY_MATCHING.value
                        ),
                        error=error,
                    )
                )

    raw_results[
        "fuzzy_support"
    ] = dict(fuzzy_support)

    fallback_reason = (
        determine_fallback_reason(
            primary_route,
            primary_failed=primary_failed,
            explicit_fallback=(
                explicit_semantic_fallback
            ),
            config=config,
        )
    )

    semantic_fallback: dict[
        str,
        Any,
    ] = {}

    fallback_used = (
        should_use_semantic_fallback(
            primary_route,
            primary_failed=primary_failed,
            explicit_fallback=(
                explicit_semantic_fallback
            ),
            config=config,
        )
    )

    if fallback_used:
        with StageTimer(
            NLPStage.SEMANTIC_FALLBACK,
            timings,
        ):
            try:
                semantic_fallback = (
                    execute_semantic_fallback(
                        normalized_message,
                        primary_route=(
                            primary_payload
                        ),
                        context=resolved_context,
                        teams=teams,
                        player_profiles=(
                            player_profiles
                        ),
                        database_session=(
                            database_session
                        ),
                        module=module_map[
                            NLPModuleName.SEMANTIC_ENGINE
                        ],
                    )
                )

            except Exception as error:
                diagnostics.append(
                    diagnostic_from_exception(
                        stage=(
                            NLPStage.SEMANTIC_FALLBACK
                        ),
                        code=(
                            "semantic_fallback_failed"
                        ),
                        message=(
                            "Semantic fallback failed"
                        ),
                        module=(
                            NLPModuleName.SEMANTIC_ENGINE.value
                        ),
                        error=error,
                    )
                )

    raw_results[
        "semantic_fallback"
    ] = dict(semantic_fallback)

    with StageTimer(
        NLPStage.MERGE,
        timings,
    ):
        merged_entities = merge_entities(
            primary_route,
            entity_support=entity_support,
            fuzzy_support=fuzzy_support,
            semantic_fallback=(
                semantic_fallback
            ),
            preserve_primary=(
                config.preserve_primary_entities
            ),
        )

        merged_intent, merged_confidence = (
            merge_intent(
                primary_route,
                semantic_fallback,
                preserve_primary=(
                    config.preserve_primary_intent
                ),
            )
        )

        clarification_required, clarification_question = (
            merge_clarification(
                primary_payload,
                semantic_fallback,
            )
        )

    if (
        primary_route.intent
        and semantic_fallback.get(
            "recommended_intent"
        )
        and primary_route.intent
        != semantic_fallback.get(
            "recommended_intent"
        )
    ):
        diagnostics.append(
            NLPDiagnostic(
                stage=NLPStage.MERGE,
                severity=(
                    NLPDiagnosticSeverity.INFO
                ),
                code=(
                    "semantic_intent_conflict_preserved_primary"
                ),
                message=(
                    "Semantic fallback recommended a different intent; primary intent was preserved"
                ),
                module=(
                    NLPModuleName.SEMANTIC_ENGINE.value
                ),
                metadata={
                    "primary_intent": (
                        primary_route.intent
                    ),
                    "semantic_intent": (
                        semantic_fallback.get(
                            "recommended_intent"
                        )
                    ),
                },
            )
        )

    if primary_failed and not semantic_fallback:
        status = NLPExecutionStatus.FAILED

    elif primary_failed:
        status = NLPExecutionStatus.PARTIAL

    elif diagnostics and any(
        diagnostic.severity
        in {
            NLPDiagnosticSeverity.ERROR,
            NLPDiagnosticSeverity.CRITICAL,
        }
        for diagnostic in diagnostics
    ):
        status = NLPExecutionStatus.PARTIAL

    else:
        status = NLPExecutionStatus.OK

    result = NLPOrchestrationResult(
        message=str(message),
        normalized_message=normalized_message,
        status=status,
        intent=merged_intent,
        confidence=merged_confidence,
        primary_route=primary_route,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        player=merged_entities["player"],
        team=merged_entities["team"],
        outcome=merged_entities["outcome"],
        players=merged_entities["players"],
        teams=merged_entities["teams"],
        outcomes=merged_entities["outcomes"],
        context=resolved_context,
        semantic_fallback=(
            semantic_fallback
            if semantic_fallback
            else None
        ),
        fuzzy_support=(
            fuzzy_support
            if fuzzy_support
            else None
        ),
        entity_support=(
            entity_support
            if entity_support
            else None
        ),
        clarification_required=(
            clarification_required
        ),
        clarification_question=(
            clarification_question
        ),
        diagnostics=diagnostics[
            :config.maximum_diagnostics
        ],
        timings=(
            timings
            if config.include_stage_timings
            else []
        ),
        module_states=module_states,
        raw_results=(
            raw_results
            if config.include_raw_module_results
            else {}
        ),
    )

    if config.include_audit_record:
        result.audit = build_nlp_audit_record(
            result
        )

    return result.to_dict()


# ============================================================
# SECTION 27 - AUTHORITATIVE ALIAS
# ============================================================

process_nlp = orchestrate_nlp


# ============================================================
# SECTION 28 - BACKWARD-COMPATIBILITY WRAPPERS
# ============================================================

def process_message(
    message: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return orchestrate_nlp(
        message,
        **kwargs,
    )


def process_query(
    query: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return orchestrate_nlp(
        query,
        **kwargs,
    )


def analyze_message(
    message: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return orchestrate_nlp(
        message,
        **kwargs,
    )


def understand_message(
    message: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return orchestrate_nlp(
        message,
        **kwargs,
    )


# ============================================================
# SECTION 29 - HEALTH REPORT
# ============================================================

def nlp_package_health(
) -> dict[str, Any]:
    validation = (
        validate_nlp_package()
    )

    module_states = (
        inspect_all_module_states()
    )

    primary_available = any(
        state.module_name
        == NLPModuleName.NLU_ENGINE.value
        and state.imported
        for state in module_states
    )

    semantic_available = any(
        state.module_name
        == NLPModuleName.SEMANTIC_ENGINE.value
        and state.imported
        for state in module_states
    )

    return {
        "name": NLP_PACKAGE_NAME,
        "version": NLP_PACKAGE_VERSION,
        "phase": NLP_PACKAGE_PHASE,
        "path": NLP_PACKAGE_PATH,
        "status": (
            NLP_PACKAGE_STATUS
            if validation["status"] == "ok"
            else "validation_failed"
        ),
        "schema_version": NLP_SCHEMA_VERSION,
        "public_api_contract": (
            NLP_PUBLIC_API_CONTRACT
        ),
        "authoritative_function": (
            AUTHORITATIVE_ORCHESTRATION_FUNCTION
        ),
        "primary_router": (
            PRIMARY_ROUTER_MODULE
        ),
        "primary_router_available": (
            primary_available
        ),
        "semantic_fallback": (
            SEMANTIC_FALLBACK_MODULE
        ),
        "semantic_fallback_available": (
            semantic_available
        ),
        "semantic_override_allowed": False,
        "module_states": [
            state.to_dict()
            for state in module_states
        ],
        "validation": validation,
        "timestamp": datetime.now(
            UTC
        ).isoformat(),
    }


# ============================================================
# SECTION 30 - TEST MODULE BUILDERS
# ============================================================

def _build_test_primary_module(
    result: Mapping[str, Any],
) -> ModuleType:
    module = ModuleType(
        "_test_nlu_engine"
    )

    def process_nlu(
        message: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return dict(result)

    module.process_nlu = process_nlu
    module.NLU_ENGINE_VERSION = "test"
    module.NLU_ENGINE_PHASE = "test"

    return module


def _build_test_semantic_module(
    result: Mapping[str, Any],
) -> ModuleType:
    module = ModuleType(
        "_test_semantic_engine"
    )

    def analyze_semantic_fallback(
        message: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return dict(result)

    module.analyze_semantic_fallback = (
        analyze_semantic_fallback
    )
    module.SEMANTIC_ENGINE_VERSION = "test"
    module.SEMANTIC_ENGINE_PHASE = "test"

    return module


# ============================================================
# SECTION 31 - INTERNAL ORCHESTRATION TEST HARNESS
# ============================================================

def _run_orchestration_with_modules(
    message: str,
    *,
    primary_module: ModuleType | None,
    semantic_module: ModuleType | None,
    config: NLPOrchestrationConfig | None = None,
) -> dict[str, Any]:
    config = config or NLPOrchestrationConfig()

    original_cache = dict(
        _MODULE_CACHE
    )

    try:
        _MODULE_CACHE[
            NLPModuleName.NLU_ENGINE.value
        ] = primary_module
        _MODULE_CACHE[
            NLPModuleName.SEMANTIC_ENGINE.value
        ] = semantic_module
        _MODULE_CACHE[
            NLPModuleName.CONTEXT_BUILDER.value
        ] = None
        _MODULE_CACHE[
            NLPModuleName.ENTITY_DETECTION.value
        ] = None
        _MODULE_CACHE[
            NLPModuleName.FUZZY_MATCHING.value
        ] = None
        _MODULE_CACHE[
            NLPModuleName.INTENT_DETECTION.value
        ] = None

        return orchestrate_nlp(
            message,
            config=config,
        )

    finally:
        _MODULE_CACHE.clear()
        _MODULE_CACHE.update(
            original_cache
        )


# ============================================================
# SECTION 32 - PACKAGE VALIDATION
# ============================================================

def validate_nlp_package(
) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    accepted_primary_module = (
        _build_test_primary_module({
            "intent": "player_stats",
            "confidence": 0.95,
            "accepted": True,
            "player": "Aaron Judge",
            "players": [
                "Aaron Judge",
            ],
        })
    )

    conflicting_semantic_module = (
        _build_test_semantic_module({
            "recommended_intent": "roster",
            "recommended_confidence": 0.99,
            "team": "New York Yankees",
            "teams": [
                "New York Yankees",
            ],
            "status": "fallback_recommendation",
        })
    )

    accepted_result = (
        _run_orchestration_with_modules(
            "show Aaron Judge stats",
            primary_module=(
                accepted_primary_module
            ),
            semantic_module=(
                conflicting_semantic_module
            ),
        )
    )

    checks[
        "accepted_primary_intent_preserved"
    ] = (
        accepted_result["intent"]
        == "player_stats"
    )

    checks[
        "accepted_primary_skips_fallback"
    ] = (
        accepted_result[
            "fallback_used"
        ]
        is False
    )

    checks[
        "primary_player_preserved"
    ] = (
        accepted_result["player"]
        == "Aaron Judge"
    )

    unresolved_primary_module = (
        _build_test_primary_module({
            "intent": None,
            "confidence": 0.20,
            "accepted": False,
            "unresolved": True,
        })
    )

    fallback_semantic_module = (
        _build_test_semantic_module({
            "recommended_intent": (
                "player_probability"
            ),
            "recommended_confidence": 0.88,
            "player": "Aaron Judge",
            "players": [
                "Aaron Judge",
            ],
            "outcome": "home_run",
            "outcomes": [
                "home_run",
            ],
            "status": (
                "fallback_recommendation"
            ),
            "clarification_required": False,
        })
    )

    unresolved_result = (
        _run_orchestration_with_modules(
            "what is Aaron Judge home run probability",
            primary_module=(
                unresolved_primary_module
            ),
            semantic_module=(
                fallback_semantic_module
            ),
        )
    )

    checks[
        "unresolved_primary_uses_fallback"
    ] = (
        unresolved_result[
            "fallback_used"
        ]
        is True
    )

    checks[
        "fallback_intent_used_when_primary_missing"
    ] = (
        unresolved_result["intent"]
        == "player_probability"
    )

    checks[
        "fallback_player_recovered"
    ] = (
        unresolved_result["player"]
        == "Aaron Judge"
    )

    checks[
        "fallback_outcome_recovered"
    ] = (
        unresolved_result["outcome"]
        == "home_run"
    )

    low_confidence_primary_module = (
        _build_test_primary_module({
            "intent": "custom_primary_route",
            "confidence": 0.30,
            "accepted": False,
        })
    )

    low_confidence_result = (
        _run_orchestration_with_modules(
            "show Yankees roster",
            primary_module=(
                low_confidence_primary_module
            ),
            semantic_module=(
                conflicting_semantic_module
            ),
        )
    )

    checks[
        "low_confidence_primary_intent_still_preserved"
    ] = (
        low_confidence_result["intent"]
        == "custom_primary_route"
    )

    checks[
        "semantic_override_disabled"
    ] = (
        NLPOrchestrationConfig().allow_semantic_override
        is False
    )

    checks[
        "override_configuration_rejected"
    ] = False

    try:
        NLPOrchestrationConfig(
            allow_semantic_override=True
        ).validate()
    except ValueError:
        checks[
            "override_configuration_rejected"
        ] = True

    checks[
        "single_authoritative_function_named"
    ] = (
        AUTHORITATIVE_ORCHESTRATION_FUNCTION
        == "orchestrate_nlp"
    )

    checks[
        "process_nlp_alias_points_to_orchestrator"
    ] = (
        process_nlp is orchestrate_nlp
    )

    checks[
        "module_registry_primary_unique"
    ] = (
        sum(
            descriptor.role
            == NLPRouterRole.PRIMARY
            for descriptor in MODULE_REGISTRY
        )
        == 1
    )

    checks[
        "module_registry_fallback_unique"
    ] = (
        sum(
            descriptor.role
            == NLPRouterRole.FALLBACK
            for descriptor in MODULE_REGISTRY
        )
        == 1
    )

    checks[
        "primary_module_is_nlu_engine"
    ] = (
        next(
            descriptor
            for descriptor in MODULE_REGISTRY
            if descriptor.role
            == NLPRouterRole.PRIMARY
        ).name
        == NLPModuleName.NLU_ENGINE
    )

    checks[
        "fallback_module_is_semantic_engine"
    ] = (
        next(
            descriptor
            for descriptor in MODULE_REGISTRY
            if descriptor.role
            == NLPRouterRole.FALLBACK
        ).name
        == NLPModuleName.SEMANTIC_ENGINE
    )

    checks[
        "empty_message_is_rejected"
    ] = (
        orchestrate_nlp(
            "",
            config=NLPOrchestrationConfig(
                strict_primary_router=False
            ),
        )["status"]
        == NLPExecutionStatus.FAILED.value
    )

    checks[
        "audit_fingerprint_created"
    ] = bool(
        unresolved_result.get(
            "audit",
            {}
        ).get("fingerprint")
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
        "package": NLP_PACKAGE_NAME,
        "version": NLP_PACKAGE_VERSION,
        "phase": NLP_PACKAGE_PHASE,
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
# SECTION 33 - API MANIFEST
# ============================================================

def get_nlp_public_api_manifest(
) -> dict[str, Any]:
    return {
        "package": NLP_PACKAGE_NAME,
        "version": NLP_PACKAGE_VERSION,
        "phase": NLP_PACKAGE_PHASE,
        "contract": NLP_PUBLIC_API_CONTRACT,
        "authoritative_function": (
            AUTHORITATIVE_ORCHESTRATION_FUNCTION
        ),
        "primary_router": (
            PRIMARY_ROUTER_MODULE
        ),
        "semantic_fallback": (
            SEMANTIC_FALLBACK_MODULE
        ),
        "semantic_override_allowed": False,
        "public_functions": [
            "orchestrate_nlp",
            "process_nlp",
            "process_message",
            "process_query",
            "analyze_message",
            "understand_message",
            "nlp_package_health",
            "validate_nlp_package",
            "get_nlp_public_api_manifest",
        ],
        "module_registry": [
            descriptor.to_dict()
            for descriptor in MODULE_REGISTRY
        ],
    }


# ============================================================
# SECTION 34 - PACKAGE CONFIGURATION EXPORT
# ============================================================

NLP_PACKAGE_CONFIGURATION: Final[
    dict[str, Any]
] = {
    "package_name": NLP_PACKAGE_NAME,
    "package_version": NLP_PACKAGE_VERSION,
    "package_phase": NLP_PACKAGE_PHASE,
    "schema_version": NLP_SCHEMA_VERSION,
    "public_api_contract": (
        NLP_PUBLIC_API_CONTRACT
    ),
    "authoritative_function": (
        AUTHORITATIVE_ORCHESTRATION_FUNCTION
    ),
    "primary_router": (
        PRIMARY_ROUTER_MODULE
    ),
    "semantic_fallback": (
        SEMANTIC_FALLBACK_MODULE
    ),
    "semantic_override_allowed": False,
    "single_gateway_enabled": True,
    "context_support_enabled": True,
    "entity_support_enabled": True,
    "fuzzy_support_enabled": True,
    "semantic_fallback_enabled": True,
    "audit_enabled": True,
    "diagnostics_enabled": True,
    "stage_timings_enabled": True,
}


# ============================================================
# SECTION 35 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "NLP_PACKAGE_NAME",
    "NLP_PACKAGE_VERSION",
    "NLP_PACKAGE_PHASE",
    "NLP_PACKAGE_PATH",
    "NLP_PACKAGE_STATUS",
    "NLP_SCHEMA_VERSION",
    "PRIMARY_ROUTER_MODULE",
    "SEMANTIC_FALLBACK_MODULE",
    "AUTHORITATIVE_ORCHESTRATION_FUNCTION",
    "NLP_PUBLIC_API_CONTRACT",

    "NLPExecutionStatus",
    "NLPRouterRole",
    "NLPStage",
    "NLPFallbackReason",
    "NLPDiagnosticSeverity",
    "NLPModuleName",

    "NLPOrchestrationConfig",
    "NLPDiagnostic",
    "NLPStageTiming",
    "NLPModuleState",
    "PrimaryRoute",
    "NLPOrchestrationResult",
    "ModuleDescriptor",

    "MODULE_REGISTRY",
    "NLP_PACKAGE_CONFIGURATION",

    "coerce_confidence",
    "unique_strings",
    "safe_mapping_get",
    "normalize_message",
    "fingerprint_payload",

    "clear_nlp_module_cache",
    "load_nlp_module",
    "get_module_descriptor",
    "resolve_callable",
    "call_with_supported_arguments",
    "inspect_module_state",
    "inspect_all_module_states",

    "build_context_support",
    "execute_primary_router",
    "execute_entity_support",
    "execute_fuzzy_support",
    "execute_semantic_fallback",
    "determine_fallback_reason",
    "should_use_semantic_fallback",
    "merge_entities",
    "merge_intent",
    "merge_clarification",
    "build_nlp_audit_record",

    "orchestrate_nlp",
    "process_nlp",
    "process_message",
    "process_query",
    "analyze_message",
    "understand_message",

    "nlp_package_health",
    "validate_nlp_package",
    "get_nlp_public_api_manifest",
]


# ============================================================
# SECTION 36 - LOCAL VALIDATION ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    print(
        json.dumps(
            nlp_package_health(),
            indent=2,
            sort_keys=True,
        )
    )
