from __future__ import annotations

from pathlib import Path

from universal_visual_os_agent.testing.repo_inventory import (
    CleanupRecommendation,
    ObserveOnlyRepoInventoryGenerator,
    ProductionCriticality,
    RepoPrimaryRole,
)


class _ExplodingRepoInventoryGenerator(ObserveOnlyRepoInventoryGenerator):
    def _collect_file_paths(self, repo_root):
        del repo_root
        raise RuntimeError("repo inventory exploded")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_repo_inventory_classifies_roles_and_cleanup_targets_deterministically(tmp_path: Path) -> None:
    _write_text(
        tmp_path / "src/universal_visual_os_agent/semantics/candidate_generation.py",
        "from universal_visual_os_agent.geometry.models import NormalizedBBox\n\nVALUE = 1\n",
    )
    _write_text(
        tmp_path / "src/universal_visual_os_agent/integrations/windows/foreground_capture_diagnostic.py",
        "VALUE = 2\n",
    )
    _write_text(
        tmp_path / "src/universal_visual_os_agent/ai_boundary/models.py",
        "VALUE = 3\n",
    )
    _write_text(tmp_path / "tests/test_semantics.py", "def test_placeholder():\n    assert True\n")
    _write_text(tmp_path / "docs/PROJECT_STATUS.md", "# status\n")

    result = ObserveOnlyRepoInventoryGenerator().build(tmp_path)

    assert result.success is True
    assert result.inventory is not None
    records = {record.path: record for record in result.inventory.records}
    assert tuple(records) == tuple(sorted(records))
    assert (
        records["src/universal_visual_os_agent/semantics/candidate_generation.py"].primary_role
        is RepoPrimaryRole.semantics
    )
    assert (
        records["src/universal_visual_os_agent/semantics/candidate_generation.py"].production_criticality
        is ProductionCriticality.critical
    )
    assert (
        records[
            "src/universal_visual_os_agent/integrations/windows/foreground_capture_diagnostic.py"
        ].cleanup_recommendation
        is CleanupRecommendation.retain_as_diagnostic_only
    )
    assert records["tests/test_semantics.py"].primary_role is RepoPrimaryRole.test_only
    assert records["tests/test_semantics.py"].cleanup_recommendation is CleanupRecommendation.retain_as_test_only
    assert records["docs/PROJECT_STATUS.md"].archive_candidate is True
    assert records["docs/PROJECT_STATUS.md"].cleanup_recommendation is CleanupRecommendation.review_for_archive


def test_repo_inventory_detects_python_cycle_risk(tmp_path: Path) -> None:
    _write_text(
        tmp_path / "src/universal_visual_os_agent/foo.py",
        "from universal_visual_os_agent import bar\n",
    )
    _write_text(
        tmp_path / "src/universal_visual_os_agent/bar.py",
        "from universal_visual_os_agent import foo\n",
    )

    result = ObserveOnlyRepoInventoryGenerator().build(tmp_path)

    assert result.success is True
    assert result.inventory is not None
    records = {record.path: record for record in result.inventory.records}
    assert "cycle_member" in records["src/universal_visual_os_agent/foo.py"].coupling_risk_notes
    assert "cycle_member" in records["src/universal_visual_os_agent/bar.py"].coupling_risk_notes
    assert (
        records["src/universal_visual_os_agent/foo.py"].cleanup_recommendation
        is CleanupRecommendation.review_for_cycle_isolation
    )
    assert set(result.inventory.summary.cycle_risk_paths) == {
        "src/universal_visual_os_agent/foo.py",
        "src/universal_visual_os_agent/bar.py",
    }


def test_repo_inventory_writes_markdown_and_json_artifacts(tmp_path: Path) -> None:
    _write_text(tmp_path / "README.md", "# repo\n")

    generator = ObserveOnlyRepoInventoryGenerator()
    result = generator.build(tmp_path)

    assert result.success is True
    assert result.inventory is not None
    markdown_path, json_path = generator.write_artifacts(
        result.inventory,
        docs_dir=tmp_path / "docs",
    )

    assert markdown_path.name == "REPO_INVENTORY.md"
    assert json_path.name == "REPO_INVENTORY.json"
    assert markdown_path.read_text(encoding="utf-8").startswith("# Repo Inventory")
    assert '"schema_version": "repo_inventory_v1"' in json_path.read_text(encoding="utf-8")


def test_repo_inventory_does_not_propagate_unhandled_exceptions() -> None:
    result = _ExplodingRepoInventoryGenerator().build(Path("C:/placeholder"))

    assert result.success is False
    assert result.error_code == "repo_inventory_generation_exception"
    assert result.error_message == "repo inventory exploded"
