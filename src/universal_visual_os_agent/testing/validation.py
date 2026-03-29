"""Validation report helpers and formatting utilities."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True, kw_only=True)
class EnvironmentIssue:
    """An environment-only issue encountered during validation."""

    summary: str
    details: str | None = None
    blocking: bool = False


@dataclass(slots=True, frozen=True, kw_only=True)
class ModuleSafetySummary:
    """Safe and unsafe module summaries for validation reporting."""

    safe_modules: tuple[str, ...] = ()
    unsafe_modules: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True, kw_only=True)
class ValidationReport:
    """Structured validation report with explicit executed/static separation."""

    task: str
    files_changed: tuple[str, ...] = ()
    executed_checks: tuple[str, ...] = ()
    static_reasoning_only: tuple[str, ...] = ()
    fixed_issues: tuple[str, ...] = ()
    remaining_risks: tuple[str, ...] = ()
    simulated: tuple[str, ...] = ()
    actually_executed: tuple[str, ...] = ()
    recommended_next_tests: tuple[str, ...] = ()
    environment_issues: tuple[EnvironmentIssue, ...] = ()
    module_summary: ModuleSafetySummary = field(default_factory=ModuleSafetySummary)

    def to_markdown(self) -> str:
        """Render the report using the repository template shape."""

        lines = [
            "# Validation Report",
            "",
            "## Task",
            self.task,
            "",
            "## Files Changed",
            *_format_items(self.files_changed),
            "",
            "## Executed Checks",
            *_format_items(self.executed_checks),
            "",
            "## Static Reasoning Only",
            *_format_items(self.static_reasoning_only),
            "",
            "## Environment Issues",
            *_format_environment_issues(self.environment_issues),
            "",
            "## Fixed Issues",
            *_format_items(self.fixed_issues),
            "",
            "## Remaining Risks",
            *_format_items(self.remaining_risks),
            "",
            "## Simulated vs Actually Executed",
            "- Simulated:",
            *_indent_items(self.simulated),
            "- Actually executed:",
            *_indent_items(self.actually_executed),
            "",
            "## Recommended Next Tests",
            *_format_items(self.recommended_next_tests),
            "",
            "## Safe / Unsafe Modules",
            "- Safe:",
            *_indent_items(self.module_summary.safe_modules),
            "- Unsafe / not yet validated:",
            *_indent_items(self.module_summary.unsafe_modules),
        ]
        return "\n".join(lines)


def make_environment_issue(summary: str, *, details: str | None = None, blocking: bool = False) -> EnvironmentIssue:
    """Build an environment issue entry."""

    return EnvironmentIssue(summary=summary, details=details, blocking=blocking)


def summarize_module_safety(
    *,
    safe_modules: tuple[str, ...] = (),
    unsafe_modules: tuple[str, ...] = (),
) -> ModuleSafetySummary:
    """Build a module safety summary."""

    return ModuleSafetySummary(
        safe_modules=safe_modules,
        unsafe_modules=unsafe_modules,
    )


def _format_items(items: tuple[str, ...]) -> tuple[str, ...]:
    if not items:
        return ("- None",)
    return tuple(f"- {item}" for item in items)


def _indent_items(items: tuple[str, ...]) -> tuple[str, ...]:
    if not items:
        return ("  - None",)
    return tuple(f"  - {item}" for item in items)


def _format_environment_issues(items: tuple[EnvironmentIssue, ...]) -> tuple[str, ...]:
    if not items:
        return ("- None",)
    lines: list[str] = []
    for issue in items:
        suffix = " (blocking)" if issue.blocking else ""
        lines.append(f"- {issue.summary}{suffix}")
        if issue.details:
            lines.append(f"  - {issue.details}")
    return tuple(lines)
