"""Deterministic repository inventory generation for hygiene and cleanup planning."""

from __future__ import annotations

import ast
import json
from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Mapping, Self


REPO_INVENTORY_SCHEMA_VERSION = "repo_inventory_v1"


class RepoPrimaryRole(StrEnum):
    """Primary role classification for one repository file."""

    core = "core"
    runtime = "runtime"
    diagnostic = "diagnostic"
    test_only = "test_only"
    ai_contracts = "ai_contracts"
    semantics = "semantics"
    actions = "actions"
    scenario = "scenario"
    docs = "docs"
    support = "support"


class ProductionCriticality(StrEnum):
    """Production relevance for current repository flow."""

    critical = "critical"
    supporting = "supporting"
    non_production = "non_production"


class CleanupRecommendation(StrEnum):
    """Conservative next-step cleanup recommendation."""

    keep = "keep"
    review_for_split = "review_for_split"
    review_for_archive = "review_for_archive"
    review_for_cycle_isolation = "review_for_cycle_isolation"
    retain_as_diagnostic_only = "retain_as_diagnostic_only"
    retain_as_test_only = "retain_as_test_only"
    review_runtime_boundary = "review_runtime_boundary"


@dataclass(slots=True, frozen=True, kw_only=True)
class RepoInventoryRecord:
    """One structured repository inventory record."""

    path: str
    primary_role: RepoPrimaryRole
    secondary_role: str | None
    production_criticality: ProductionCriticality
    cleanup_recommendation: CleanupRecommendation
    diagnostic_candidate: bool = False
    archive_candidate: bool = False
    legacy_candidate: bool = False
    line_count: int | None = None
    internal_import_count: int = 0
    cross_package_import_count: int = 0
    coupling_risk_notes: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("path must not be empty.")
        if self.line_count is not None and self.line_count < 0:
            raise ValueError("line_count must not be negative.")
        if self.internal_import_count < 0 or self.cross_package_import_count < 0:
            raise ValueError("Import counts must not be negative.")


@dataclass(slots=True, frozen=True, kw_only=True)
class RepoInventorySummary:
    """Deterministic summary for the current inventory build."""

    total_file_count: int
    primary_role_counts: Mapping[str, int]
    production_criticality_counts: Mapping[str, int]
    cleanup_recommendation_counts: Mapping[str, int]
    diagnostic_candidate_paths: tuple[str, ...] = ()
    archive_candidate_paths: tuple[str, ...] = ()
    cycle_risk_paths: tuple[str, ...] = ()
    oversized_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.total_file_count < 0:
            raise ValueError("total_file_count must not be negative.")


@dataclass(slots=True, frozen=True, kw_only=True)
class RepoInventory:
    """Structured repository inventory and render helpers."""

    generator_name: str
    repo_root: str
    schema_version: str = REPO_INVENTORY_SCHEMA_VERSION
    records: tuple[RepoInventoryRecord, ...] = ()
    summary: RepoInventorySummary = field(
        default_factory=lambda: RepoInventorySummary(
            total_file_count=0,
            primary_role_counts={},
            production_criticality_counts={},
            cleanup_recommendation_counts={},
        )
    )

    def to_json(self) -> str:
        """Render the inventory to stable JSON."""

        payload = {
            "generator_name": self.generator_name,
            "repo_root": self.repo_root,
            "schema_version": self.schema_version,
            "summary": {
                "total_file_count": self.summary.total_file_count,
                "primary_role_counts": dict(self.summary.primary_role_counts),
                "production_criticality_counts": dict(self.summary.production_criticality_counts),
                "cleanup_recommendation_counts": dict(self.summary.cleanup_recommendation_counts),
                "diagnostic_candidate_paths": self.summary.diagnostic_candidate_paths,
                "archive_candidate_paths": self.summary.archive_candidate_paths,
                "cycle_risk_paths": self.summary.cycle_risk_paths,
                "oversized_paths": self.summary.oversized_paths,
            },
            "records": [
                {
                    "path": record.path,
                    "primary_role": record.primary_role.value,
                    "secondary_role": record.secondary_role,
                    "production_criticality": record.production_criticality.value,
                    "cleanup_recommendation": record.cleanup_recommendation.value,
                    "diagnostic_candidate": record.diagnostic_candidate,
                    "archive_candidate": record.archive_candidate,
                    "legacy_candidate": record.legacy_candidate,
                    "line_count": record.line_count,
                    "internal_import_count": record.internal_import_count,
                    "cross_package_import_count": record.cross_package_import_count,
                    "coupling_risk_notes": record.coupling_risk_notes,
                    "metadata": dict(record.metadata),
                }
                for record in self.records
            ],
        }
        return json.dumps(payload, indent=2, sort_keys=True)

    def to_markdown(self) -> str:
        """Render a review-friendly markdown summary with prioritized cleanup targets."""

        priority_records = tuple(
            record
            for record in self.records
            if record.cleanup_recommendation is not CleanupRecommendation.keep
        )
        code_cleanup_records = tuple(
            record
            for record in priority_records
            if not record.path.startswith((".tmp_test_artifacts/", "tests/"))
            and record.cleanup_recommendation is not CleanupRecommendation.retain_as_test_only
        )
        critical_records = tuple(
            record
            for record in self.records
            if record.production_criticality is ProductionCriticality.critical
        )
        lines = [
            "# Repo Inventory",
            "",
            f"- Generator: `{self.generator_name}`",
            f"- Schema: `{self.schema_version}`",
            f"- Repo root: `{self.repo_root}`",
            f"- Total files: `{self.summary.total_file_count}`",
            "",
            "## Summary Counts",
            "",
            "### Primary Role",
            *_mapping_lines(self.summary.primary_role_counts),
            "",
            "### Production Criticality",
            *_mapping_lines(self.summary.production_criticality_counts),
            "",
            "### Cleanup Recommendation",
            *_mapping_lines(self.summary.cleanup_recommendation_counts),
            "",
            "## Code Hygiene Hotspots",
            "",
            *_record_table(code_cleanup_records),
            "",
            "## Archive / Temp Candidates",
            "",
            *_record_table(
                record for record in priority_records if record.archive_candidate
            ),
            "",
            "## Production-Critical Files",
            "",
            *_record_table(critical_records),
            "",
            "## Full Inventory",
            "",
            *_record_table(self.records),
        ]
        return "\n".join(lines)


@dataclass(slots=True, frozen=True, kw_only=True)
class RepoInventoryBuildResult:
    """Failure-safe repo-inventory generation result."""

    generator_name: str
    success: bool
    inventory: RepoInventory | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.generator_name:
            raise ValueError("generator_name must not be empty.")
        if self.success and self.inventory is None:
            raise ValueError("Successful inventory results must include inventory.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed inventory results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful inventory results must not include error details.")
        if not self.success and self.inventory is not None:
            raise ValueError("Failed inventory results must not include inventory.")

    @classmethod
    def ok(
        cls,
        *,
        generator_name: str,
        inventory: RepoInventory,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            generator_name=generator_name,
            success=True,
            inventory=inventory,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        generator_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            generator_name=generator_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class _PythonModuleStats:
    module_name: str
    line_count: int
    internal_import_count: int
    cross_package_import_count: int
    in_cycle: bool = False


class ObserveOnlyRepoInventoryGenerator:
    """Generate a deterministic repository inventory for later hygiene work."""

    generator_name = "ObserveOnlyRepoInventoryGenerator"

    def build(self, repo_root: Path) -> RepoInventoryBuildResult:
        try:
            normalized_root = repo_root.resolve()
            file_paths = tuple(self._collect_file_paths(normalized_root))
            module_stats = self._build_python_module_stats(normalized_root)
            records = tuple(
                self._classify_file(
                    normalized_root,
                    file_path,
                    module_stats=module_stats,
                )
                for file_path in file_paths
            )
            inventory = RepoInventory(
                generator_name=self.generator_name,
                repo_root=normalized_root.as_posix(),
                records=records,
                summary=_build_summary(records),
            )
        except Exception as exc:  # noqa: BLE001 - inventory generation must remain failure-safe
            return RepoInventoryBuildResult.failure(
                generator_name=self.generator_name,
                error_code="repo_inventory_generation_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return RepoInventoryBuildResult.ok(
            generator_name=self.generator_name,
            inventory=inventory,
            details={
                "record_count": len(records),
                "cycle_risk_count": len(inventory.summary.cycle_risk_paths),
                "archive_candidate_count": len(inventory.summary.archive_candidate_paths),
            },
        )

    def write_artifacts(
        self,
        inventory: RepoInventory,
        *,
        docs_dir: Path,
    ) -> tuple[Path, Path]:
        """Write deterministic markdown and JSON inventory artifacts."""

        docs_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = docs_dir / "REPO_INVENTORY.md"
        json_path = docs_dir / "REPO_INVENTORY.json"
        markdown_path.write_text(inventory.to_markdown(), encoding="utf-8")
        json_path.write_text(inventory.to_json(), encoding="utf-8")
        return markdown_path, json_path

    def _collect_file_paths(self, repo_root: Path) -> Iterable[Path]:
        ignored_dirs = {".git", "__pycache__", ".pytest_cache", ".mypy_cache"}
        for path in sorted(repo_root.rglob("*"), key=lambda item: item.as_posix()):
            if not path.is_file():
                continue
            if any(part in ignored_dirs for part in path.parts):
                continue
            yield path

    def _build_python_module_stats(self, repo_root: Path) -> Mapping[str, _PythonModuleStats]:
        src_root = repo_root / "src"
        if not src_root.exists():
            return {}
        python_files = tuple(
            path
            for path in self._collect_file_paths(repo_root)
            if path.suffix == ".py" and src_root in path.parents
        )
        module_names = {
            _module_name_from_path(path, src_root): path
            for path in python_files
        }
        import_graph = _build_import_graph(module_names)
        cycle_members = _cycle_members(import_graph)
        stats: dict[str, _PythonModuleStats] = {}
        for module_name, path in module_names.items():
            source_text = path.read_text(encoding="utf-8", errors="ignore")
            line_count = source_text.count("\n") + (0 if source_text == "" else 1)
            imported_modules = tuple(import_graph.get(module_name, ()))
            cross_packages = {
                _top_level_project_package(imported_module)
                for imported_module in imported_modules
                if imported_module != module_name
            }
            stats[path.relative_to(repo_root).as_posix()] = _PythonModuleStats(
                module_name=module_name,
                line_count=line_count,
                internal_import_count=len(imported_modules),
                cross_package_import_count=len(cross_packages),
                in_cycle=module_name in cycle_members,
            )
        return stats

    def _classify_file(
        self,
        repo_root: Path,
        file_path: Path,
        *,
        module_stats: Mapping[str, _PythonModuleStats],
    ) -> RepoInventoryRecord:
        relative_path = file_path.relative_to(repo_root).as_posix()
        primary_role, secondary_role = _classify_roles(relative_path)
        diagnostic_candidate = _is_diagnostic_candidate(relative_path)
        archive_candidate = _is_archive_candidate(relative_path)
        legacy_candidate = _is_legacy_candidate(relative_path)
        production_criticality = _production_criticality(relative_path, primary_role, diagnostic_candidate)
        stats = module_stats.get(relative_path)
        coupling_risk_notes = _coupling_risk_notes(relative_path, stats)
        cleanup_recommendation = _cleanup_recommendation(
            primary_role=primary_role,
            diagnostic_candidate=diagnostic_candidate,
            archive_candidate=archive_candidate,
            coupling_risk_notes=coupling_risk_notes,
        )
        return RepoInventoryRecord(
            path=relative_path,
            primary_role=primary_role,
            secondary_role=secondary_role,
            production_criticality=production_criticality,
            cleanup_recommendation=cleanup_recommendation,
            diagnostic_candidate=diagnostic_candidate,
            archive_candidate=archive_candidate,
            legacy_candidate=legacy_candidate,
            line_count=None if stats is None else stats.line_count,
            internal_import_count=0 if stats is None else stats.internal_import_count,
            cross_package_import_count=0 if stats is None else stats.cross_package_import_count,
            coupling_risk_notes=coupling_risk_notes,
            metadata={
                "python_module_name": None if stats is None else stats.module_name,
                "in_cycle": False if stats is None else stats.in_cycle,
            },
        )


def _classify_roles(path: str) -> tuple[RepoPrimaryRole, str | None]:
    if path.startswith("tests/"):
        return RepoPrimaryRole.test_only, "pytest_suite"
    if path.startswith("docs/"):
        if path.lower().endswith(("project_status.md", "next_steps.md")):
            return RepoPrimaryRole.docs, "status_doc"
        if path.lower().endswith(("spec.md", "execplan.md")):
            return RepoPrimaryRole.docs, "source_of_truth"
        return RepoPrimaryRole.docs, "support_doc"
    if path.startswith("src/universal_visual_os_agent/integrations/windows/"):
        if _is_diagnostic_candidate(path):
            return RepoPrimaryRole.diagnostic, "windows_capture_diagnostic"
        if path.endswith("click.py"):
            return RepoPrimaryRole.runtime, "windows_click_runtime"
        return RepoPrimaryRole.runtime, "windows_capture_runtime"
    if path.startswith("src/universal_visual_os_agent/semantics/"):
        return RepoPrimaryRole.semantics, _secondary_role_from_name(path)
    if path.startswith("src/universal_visual_os_agent/actions/"):
        return RepoPrimaryRole.actions, _secondary_role_from_name(path)
    if path.startswith("src/universal_visual_os_agent/scenarios/"):
        return RepoPrimaryRole.scenario, _secondary_role_from_name(path)
    if path.startswith("src/universal_visual_os_agent/ai_boundary/"):
        return RepoPrimaryRole.ai_contracts, "boundary_validation"
    if path.startswith("src/universal_visual_os_agent/ai_architecture/"):
        return RepoPrimaryRole.ai_contracts, "planner_resolver_scaffolding"
    if path.startswith("src/universal_visual_os_agent/testing/"):
        return RepoPrimaryRole.support, "inventory_or_validation_support"
    if path.startswith("src/universal_visual_os_agent/"):
        return RepoPrimaryRole.core, _secondary_role_from_package(path)
    if path.startswith(".github/"):
        return RepoPrimaryRole.support, "github_metadata"
    if path.startswith("data/"):
        return RepoPrimaryRole.support, "data_artifact"
    if path.startswith(".tmp_test_artifacts/"):
        return RepoPrimaryRole.support, "temporary_artifact"
    return RepoPrimaryRole.support, None


def _secondary_role_from_package(path: str) -> str | None:
    package_name = path.split("/")[2] if path.count("/") >= 2 else None
    return {
        "app": "orchestration",
        "audit": "audit",
        "config": "configuration",
        "core": "event_core",
        "geometry": "geometry",
        "memory": "memory_placeholder",
        "perception": "perception",
        "persistence": "persistence",
        "planning": "planning_contracts",
        "policy": "policy",
        "recovery": "recovery",
        "replay": "replay",
        "verification": "verification",
    }.get(package_name)


def _secondary_role_from_name(path: str) -> str | None:
    lower_path = path.lower()
    if "candidate_" in lower_path:
        return "candidate_pipeline"
    if "ocr" in lower_path:
        return "ocr_pipeline"
    if "layout" in lower_path:
        return "layout_pipeline"
    if "delta" in lower_path:
        return "state_delta"
    if "state_machine" in lower_path:
        return "state_machine"
    if "action_flow" in lower_path:
        return "scenario_action_flow"
    if "loop" in lower_path:
        return "scenario_loop"
    if "safe_click" in lower_path:
        return "safe_click"
    if "dry_run" in lower_path:
        return "dry_run"
    return None


def _is_diagnostic_candidate(path: str) -> bool:
    lower_path = path.lower()
    return "diagnostic" in lower_path or "gdi" in lower_path or "printwindow" in lower_path


def _is_archive_candidate(path: str) -> bool:
    lower_path = path.lower()
    return lower_path.startswith(".tmp_test_artifacts/") or lower_path.endswith(
        ("project_status.md", "next_steps.md")
    )


def _is_legacy_candidate(path: str) -> bool:
    lower_path = path.lower()
    return "legacy" in lower_path


def _production_criticality(
    path: str,
    primary_role: RepoPrimaryRole,
    diagnostic_candidate: bool,
) -> ProductionCriticality:
    if primary_role in {RepoPrimaryRole.docs, RepoPrimaryRole.test_only}:
        return ProductionCriticality.non_production
    if diagnostic_candidate:
        return ProductionCriticality.non_production
    if path.startswith("src/universal_visual_os_agent/integrations/windows/"):
        return ProductionCriticality.critical
    if path.startswith("src/universal_visual_os_agent/semantics/"):
        return ProductionCriticality.critical
    if path.startswith("src/universal_visual_os_agent/config/"):
        return ProductionCriticality.critical
    if path.startswith("src/universal_visual_os_agent/geometry/"):
        return ProductionCriticality.critical
    if path.startswith("src/universal_visual_os_agent/perception/"):
        return ProductionCriticality.critical
    if path.startswith("src/universal_visual_os_agent/app/"):
        return ProductionCriticality.supporting
    if path.startswith("src/universal_visual_os_agent/"):
        return ProductionCriticality.supporting
    return ProductionCriticality.non_production


def _coupling_risk_notes(
    path: str,
    stats: _PythonModuleStats | None,
) -> tuple[str, ...]:
    notes: list[str] = []
    if stats is None:
        return ()
    if stats.in_cycle:
        notes.append("cycle_member")
    if stats.line_count >= 250:
        notes.append("oversized_module")
    if stats.internal_import_count >= 8:
        notes.append(f"high_internal_import_count:{stats.internal_import_count}")
    if stats.cross_package_import_count >= 4:
        notes.append(f"high_cross_package_import_count:{stats.cross_package_import_count}")
    if path.endswith("__init__.py") and stats.internal_import_count >= 4:
        notes.append("facade_reexport_surface")
    return tuple(notes)


def _cleanup_recommendation(
    *,
    primary_role: RepoPrimaryRole,
    diagnostic_candidate: bool,
    archive_candidate: bool,
    coupling_risk_notes: tuple[str, ...],
) -> CleanupRecommendation:
    if primary_role is RepoPrimaryRole.test_only:
        return CleanupRecommendation.retain_as_test_only
    if diagnostic_candidate:
        return CleanupRecommendation.retain_as_diagnostic_only
    if archive_candidate:
        return CleanupRecommendation.review_for_archive
    if "cycle_member" in coupling_risk_notes:
        return CleanupRecommendation.review_for_cycle_isolation
    if "oversized_module" in coupling_risk_notes:
        return CleanupRecommendation.review_for_split
    if primary_role is RepoPrimaryRole.runtime and any(
        note.startswith("high_cross_package_import_count") for note in coupling_risk_notes
    ):
        return CleanupRecommendation.review_runtime_boundary
    return CleanupRecommendation.keep


def _build_summary(records: tuple[RepoInventoryRecord, ...]) -> RepoInventorySummary:
    primary_role_counts = Counter(record.primary_role.value for record in records)
    production_criticality_counts = Counter(
        record.production_criticality.value for record in records
    )
    cleanup_recommendation_counts = Counter(
        record.cleanup_recommendation.value for record in records
    )
    return RepoInventorySummary(
        total_file_count=len(records),
        primary_role_counts=dict(sorted(primary_role_counts.items())),
        production_criticality_counts=dict(sorted(production_criticality_counts.items())),
        cleanup_recommendation_counts=dict(sorted(cleanup_recommendation_counts.items())),
        diagnostic_candidate_paths=tuple(
            record.path for record in records if record.diagnostic_candidate
        ),
        archive_candidate_paths=tuple(
            record.path for record in records if record.archive_candidate
        ),
        cycle_risk_paths=tuple(
            record.path for record in records if "cycle_member" in record.coupling_risk_notes
        ),
        oversized_paths=tuple(
            record.path for record in records if "oversized_module" in record.coupling_risk_notes
        ),
    )


def _build_import_graph(module_names: Mapping[str, Path]) -> Mapping[str, tuple[str, ...]]:
    known_modules = set(module_names)
    graph: dict[str, tuple[str, ...]] = {}
    for module_name, path in module_names.items():
        source_text = path.read_text(encoding="utf-8", errors="ignore")
        imported_modules = tuple(
            sorted(
                {
                    resolved_module
                    for imported_module in _parse_project_imports(module_name, path, source_text)
                    if (resolved_module := _resolve_known_module(imported_module, known_modules))
                    is not None
                }
            )
        )
        graph[module_name] = imported_modules
    return graph


def _parse_project_imports(
    module_name: str,
    path: Path,
    source_text: str,
) -> tuple[str, ...]:
    tree = ast.parse(source_text or "\n", filename=str(path))
    imports: set[str] = set()
    is_init = path.name == "__init__.py"
    current_package = module_name if is_init else module_name.rsplit(".", 1)[0]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("universal_visual_os_agent"):
                    imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module and node.module.startswith("universal_visual_os_agent"):
                    imports.add(node.module)
                    for alias in node.names:
                        imports.add(f"{node.module}.{alias.name}")
                continue
            base_parts = current_package.split(".")
            parent_parts = base_parts[: len(base_parts) - (node.level - 1)]
            if node.module:
                imports.add(".".join(parent_parts + node.module.split(".")))
                continue
            for alias in node.names:
                imports.add(".".join(parent_parts + [alias.name]))
    return tuple(sorted(imports))


def _resolve_known_module(imported_module: str, known_modules: set[str]) -> str | None:
    candidate = imported_module
    while candidate:
        if candidate in known_modules:
            return candidate
        if "." not in candidate:
            return None
        candidate = candidate.rsplit(".", 1)[0]
    return None


def _module_name_from_path(path: Path, src_root: Path) -> str:
    relative_parts = path.relative_to(src_root).with_suffix("").parts
    if relative_parts[-1] == "__init__":
        return ".".join(relative_parts[:-1])
    return ".".join(relative_parts)


def _top_level_project_package(module_name: str) -> str:
    parts = module_name.split(".")
    return parts[1] if len(parts) > 1 else parts[0]


def _cycle_members(graph: Mapping[str, tuple[str, ...]]) -> set[str]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    cycle_members: set[str] = set()

    def strong_connect(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for neighbor in graph.get(node, ()):
            if neighbor not in indices:
                strong_connect(neighbor)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
            elif neighbor in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[neighbor])

        if lowlinks[node] != indices[node]:
            return
        component: list[str] = []
        while stack:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node:
                break
        if len(component) > 1:
            cycle_members.update(component)

    for node in sorted(graph):
        if node not in indices:
            strong_connect(node)
    return cycle_members


def _mapping_lines(mapping: Mapping[str, int]) -> tuple[str, ...]:
    if not mapping:
        return ("- None",)
    return tuple(f"- `{key}`: {value}" for key, value in sorted(mapping.items()))


def _record_table(records: Iterable[RepoInventoryRecord]) -> tuple[str, ...]:
    record_tuple = tuple(records)
    if not record_tuple:
        return ("- None",)
    lines = [
        "| Path | Primary Role | Criticality | Cleanup | Flags | Risk Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for record in record_tuple:
        flags = ",".join(
            flag
            for flag, enabled in (
                ("diagnostic", record.diagnostic_candidate),
                ("archive", record.archive_candidate),
                ("legacy", record.legacy_candidate),
            )
            if enabled
        ) or "-"
        risk_notes = ", ".join(record.coupling_risk_notes) or "-"
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{record.path}`",
                    record.primary_role.value,
                    record.production_criticality.value,
                    record.cleanup_recommendation.value,
                    flags,
                    risk_notes,
                )
            )
            + " |"
        )
    return tuple(lines)
