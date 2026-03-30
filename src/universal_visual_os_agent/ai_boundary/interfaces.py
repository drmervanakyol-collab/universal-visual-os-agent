"""Interfaces for structured AI-boundary validation."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.ai_boundary.models import (
    AiBoundaryValidationContext,
    CloudPlannerContract,
    LocalVisualResolverContract,
    PlannerContractValidationResult,
    ResolverContractValidationResult,
)


class PlannerBoundaryValidator(Protocol):
    """Validate structured cloud-planner output before downstream use."""

    def validate_planner_contract(
        self,
        contract: CloudPlannerContract,
        *,
        context: AiBoundaryValidationContext,
    ) -> PlannerContractValidationResult:
        """Validate one planner contract against current semantic and safety context."""


class ResolverBoundaryValidator(Protocol):
    """Validate structured local visual resolver output before downstream use."""

    def validate_resolver_contract(
        self,
        contract: LocalVisualResolverContract,
        *,
        context: AiBoundaryValidationContext,
    ) -> ResolverContractValidationResult:
        """Validate one resolver contract against current semantic and safety context."""
