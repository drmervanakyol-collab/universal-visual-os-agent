"""Verification exports."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

_EXPORT_MODULES = {
    ".interfaces": (
        "GoalOrientedVerifier",
        "SemanticTransitionVerifier",
        "VerificationExplainer",
        "Verifier",
    ),
    ".models": (
        "CandidateScoreDeltaDirection",
        "ExpectedSemanticChange",
        "ExpectedSemanticOutcome",
        "SemanticOutcomeVerification",
        "SemanticStateTransition",
        "SemanticTransitionExpectation",
        "VerificationExplanation",
        "VerificationExplanationSeverity",
        "VerificationReasonCategory",
        "VerificationResult",
        "VerificationStatus",
        "VerificationTaxonomy",
        "evaluate_semantic_transition",
    ),
    ".explanations": (
        "ObserveOnlyVerificationExplainer",
        "build_explained_verification_result",
    ),
    ".goal_oriented": ("GoalOrientedSemanticVerifier",),
}
_EXPORTS = {
    name: module_name
    for module_name, names in _EXPORT_MODULES.items()
    for name in names
}

__all__ = tuple(name for names in _EXPORT_MODULES.values() for name in names)


def __getattr__(name: str) -> object:
    """Lazily resolve public verification exports to reduce package coupling."""

    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name, __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return a stable view of module globals plus lazy exports."""

    return sorted((*globals(), *__all__))


if TYPE_CHECKING:
    from .explanations import (
        ObserveOnlyVerificationExplainer,
        build_explained_verification_result,
    )
    from .goal_oriented import GoalOrientedSemanticVerifier
    from .interfaces import (
        GoalOrientedVerifier,
        SemanticTransitionVerifier,
        VerificationExplainer,
        Verifier,
    )
    from .models import (
        CandidateScoreDeltaDirection,
        ExpectedSemanticChange,
        ExpectedSemanticOutcome,
        SemanticOutcomeVerification,
        SemanticStateTransition,
        SemanticTransitionExpectation,
        VerificationExplanation,
        VerificationExplanationSeverity,
        VerificationReasonCategory,
        VerificationResult,
        VerificationStatus,
        VerificationTaxonomy,
        evaluate_semantic_transition,
    )
