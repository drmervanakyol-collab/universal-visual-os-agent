from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"


def _run_import_probe(module_name: str, *, statements: str = "") -> set[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{SRC_PATH}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(SRC_PATH)
    )
    command = (
        "import importlib, json, sys\n"
        f"importlib.import_module({module_name!r})\n"
        f"{statements}\n"
        "print(json.dumps(sorted("
        "name for name in sys.modules "
        "if name.startswith('universal_visual_os_agent')"
        ")))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", command],
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        env=env,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return set(json.loads(result.stdout))


def test_actions_interfaces_import_remains_isolated() -> None:
    loaded_modules = _run_import_probe("universal_visual_os_agent.actions.interfaces")

    assert "universal_visual_os_agent.actions.interfaces" in loaded_modules
    assert "universal_visual_os_agent.actions.dry_run" not in loaded_modules
    assert "universal_visual_os_agent.actions.safe_click" not in loaded_modules
    assert "universal_visual_os_agent.actions.scaffolding" not in loaded_modules


def test_semantics_interfaces_import_remains_isolated() -> None:
    loaded_modules = _run_import_probe("universal_visual_os_agent.semantics.interfaces")

    assert "universal_visual_os_agent.semantics.interfaces" in loaded_modules
    assert "universal_visual_os_agent.semantics.building" not in loaded_modules
    assert "universal_visual_os_agent.semantics.candidate_exposure" not in loaded_modules
    assert "universal_visual_os_agent.semantics.candidate_generation" not in loaded_modules
    assert "universal_visual_os_agent.semantics.candidate_scoring" not in loaded_modules
    assert "universal_visual_os_agent.semantics.ocr" not in loaded_modules
    assert "universal_visual_os_agent.semantics.semantic_delta" not in loaded_modules


def test_verification_interfaces_import_remains_isolated() -> None:
    loaded_modules = _run_import_probe("universal_visual_os_agent.verification.interfaces")

    assert "universal_visual_os_agent.verification.interfaces" in loaded_modules
    assert "universal_visual_os_agent.verification.explanations" not in loaded_modules
    assert "universal_visual_os_agent.verification.goal_oriented" not in loaded_modules
    assert "universal_visual_os_agent.verification.models" not in loaded_modules


def test_windows_integration_facade_import_remains_isolated() -> None:
    loaded_modules = _run_import_probe("universal_visual_os_agent.integrations.windows")

    assert "universal_visual_os_agent.integrations.windows" in loaded_modules
    assert "universal_visual_os_agent.integrations.windows.capture" not in loaded_modules
    assert "universal_visual_os_agent.integrations.windows.capture_backends" not in loaded_modules
    assert "universal_visual_os_agent.integrations.windows.capture_models" not in loaded_modules
    assert "universal_visual_os_agent.integrations.windows.click" not in loaded_modules
    assert "universal_visual_os_agent.integrations.windows.dxcam_capture_diagnostic" not in loaded_modules


def test_scenarios_facade_import_remains_isolated() -> None:
    loaded_modules = _run_import_probe("universal_visual_os_agent.scenarios")

    assert "universal_visual_os_agent.scenarios" in loaded_modules
    assert "universal_visual_os_agent.scenarios.action_flow" not in loaded_modules
    assert "universal_visual_os_agent.scenarios.definition" not in loaded_modules
    assert "universal_visual_os_agent.scenarios.loop" not in loaded_modules
    assert "universal_visual_os_agent.scenarios.models" not in loaded_modules
    assert "universal_visual_os_agent.scenarios.state_machine" not in loaded_modules


def test_ai_architecture_facade_import_remains_isolated() -> None:
    loaded_modules = _run_import_probe("universal_visual_os_agent.ai_architecture")

    assert "universal_visual_os_agent.ai_architecture" in loaded_modules
    assert "universal_visual_os_agent.ai_architecture.arbitration" not in loaded_modules
    assert "universal_visual_os_agent.ai_architecture.cloud_planner" not in loaded_modules
    assert "universal_visual_os_agent.ai_architecture.contracts" not in loaded_modules
    assert "universal_visual_os_agent.ai_architecture.local_visual_resolver" not in loaded_modules
    assert "universal_visual_os_agent.ai_architecture.ontology" not in loaded_modules


def test_semantics_models_compatibility_surface_remains_isolated() -> None:
    loaded_modules = _run_import_probe("universal_visual_os_agent.semantics.models")

    assert "universal_visual_os_agent.semantics.models" in loaded_modules
    assert "universal_visual_os_agent.semantics.building" not in loaded_modules
    assert "universal_visual_os_agent.semantics.candidate_exposure" not in loaded_modules
    assert "universal_visual_os_agent.semantics.candidate_generation" not in loaded_modules
    assert "universal_visual_os_agent.semantics.candidate_scoring" not in loaded_modules
    assert "universal_visual_os_agent.semantics.ocr" not in loaded_modules
    assert "universal_visual_os_agent.semantics.semantic_delta" not in loaded_modules


def test_action_result_model_modules_remain_separate_from_engines() -> None:
    loaded_modules = _run_import_probe("universal_visual_os_agent.actions.dry_run_models")
    loaded_modules.update(
        _run_import_probe("universal_visual_os_agent.actions.scaffolding_models")
    )

    assert "universal_visual_os_agent.actions.dry_run_models" in loaded_modules
    assert "universal_visual_os_agent.actions.scaffolding_models" in loaded_modules
    assert "universal_visual_os_agent.actions.dry_run" not in loaded_modules
    assert "universal_visual_os_agent.actions.scaffolding" not in loaded_modules


def test_action_compatibility_reexports_still_resolve_from_engine_modules() -> None:
    loaded_modules = _run_import_probe(
        "universal_visual_os_agent.actions.dry_run",
        statements=(
            "from universal_visual_os_agent.actions.dry_run import DryRunActionEvaluation\n"
            "from universal_visual_os_agent.actions.scaffolding import ActionIntentScaffoldView\n"
            "assert DryRunActionEvaluation.__name__ == 'DryRunActionEvaluation'\n"
            "assert ActionIntentScaffoldView.__name__ == 'ActionIntentScaffoldView'\n"
        ),
    )

    assert "universal_visual_os_agent.actions.dry_run" in loaded_modules
    assert "universal_visual_os_agent.actions.scaffolding" in loaded_modules
    assert "universal_visual_os_agent.actions.dry_run_models" in loaded_modules
    assert "universal_visual_os_agent.actions.scaffolding_models" in loaded_modules


def test_lazy_package_reexports_still_resolve() -> None:
    loaded_modules = _run_import_probe(
        "universal_visual_os_agent.semantics",
        statements=(
            "from universal_visual_os_agent.actions import SafeClickPrototypeExecutor\n"
            "from universal_visual_os_agent.semantics import SemanticStateSnapshot\n"
            "from universal_visual_os_agent.verification import GoalOrientedSemanticVerifier\n"
            "assert SafeClickPrototypeExecutor.__name__ == 'SafeClickPrototypeExecutor'\n"
            "assert SemanticStateSnapshot.__name__ == 'SemanticStateSnapshot'\n"
            "assert GoalOrientedSemanticVerifier.__name__ == 'GoalOrientedSemanticVerifier'\n"
        ),
    )

    assert "universal_visual_os_agent.actions.safe_click" in loaded_modules
    assert "universal_visual_os_agent.semantics.state" in loaded_modules
    assert "universal_visual_os_agent.verification.goal_oriented" in loaded_modules


def test_revision_facade_lazy_reexports_still_resolve() -> None:
    loaded_modules = _run_import_probe(
        "universal_visual_os_agent.ai_architecture",
        statements=(
            "from universal_visual_os_agent.ai_architecture import ObserveOnlyLocalVisualResolverScaffolder\n"
            "from universal_visual_os_agent.integrations.windows import WindowsCaptureRuntimeMode\n"
            "from universal_visual_os_agent.scenarios import ScenarioFlowState\n"
            "from universal_visual_os_agent.semantics.models import SemanticStateSnapshot\n"
            "assert ObserveOnlyLocalVisualResolverScaffolder.__name__ == 'ObserveOnlyLocalVisualResolverScaffolder'\n"
            "assert WindowsCaptureRuntimeMode.__name__ == 'WindowsCaptureRuntimeMode'\n"
            "assert ScenarioFlowState.__name__ == 'ScenarioFlowState'\n"
            "assert SemanticStateSnapshot.__name__ == 'SemanticStateSnapshot'\n"
        ),
    )

    assert "universal_visual_os_agent.ai_architecture.local_visual_resolver" in loaded_modules
    assert "universal_visual_os_agent.integrations.windows.capture_models" in loaded_modules
    assert "universal_visual_os_agent.scenarios.state_machine" in loaded_modules
    assert "universal_visual_os_agent.semantics.state" in loaded_modules
