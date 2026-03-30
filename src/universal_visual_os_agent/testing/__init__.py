"""Shared replay/recovery fixtures and validation helpers."""

from universal_visual_os_agent.testing.fixtures import (
    build_recovery_mode_config,
    build_recovery_mode_request,
    build_recovery_snapshot,
    build_replay_mode_config,
)
from universal_visual_os_agent.testing.repo_inventory import (
    CleanupRecommendation,
    ObserveOnlyRepoInventoryGenerator,
    ProductionCriticality,
    RepoInventory,
    RepoInventoryBuildResult,
    RepoInventoryRecord,
    RepoInventorySummary,
    RepoPrimaryRole,
)
from universal_visual_os_agent.testing.validation import (
    EnvironmentIssue,
    ModuleSafetySummary,
    ValidationReport,
    make_environment_issue,
    summarize_module_safety,
)

__all__ = [
    "EnvironmentIssue",
    "ModuleSafetySummary",
    "CleanupRecommendation",
    "ObserveOnlyRepoInventoryGenerator",
    "ProductionCriticality",
    "RepoInventory",
    "RepoInventoryBuildResult",
    "RepoInventoryRecord",
    "RepoInventorySummary",
    "RepoPrimaryRole",
    "ValidationReport",
    "build_recovery_mode_config",
    "build_recovery_mode_request",
    "build_recovery_snapshot",
    "build_replay_mode_config",
    "make_environment_issue",
    "summarize_module_safety",
]
