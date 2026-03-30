# Universal Visual OS-Agent

Windows-first, Python 3.14, safety-first visual OS-agent skeleton built from [docs/spec.md](docs/spec.md) and [docs/execplan.md](docs/execplan.md).

## Current State

This repository is no longer just a blank scaffold. Phases 1 through 7 of the current execution plan have been implemented as safe, testable skeletons:

- configuration and mode system
- core contracts and dataclasses
- SQLite persistence and recovery loading skeleton
- normalized coordinate and multi-monitor-safe geometry helpers
- semantic layout and verification models
- policy and safety gating
- asyncio event-driven loop skeleton
- replay harness and validation/reporting helpers

The project is still intentionally non-live by default. There is no real screen capture, no real OS input execution, and no Windows integration logic beyond placeholders and interfaces.

## Implemented Architecture

Under `src/universal_visual_os_agent/` the current implementation includes:

- `config/`: safe runtime config and supported modes
- `core/`, `audit/`: shared event and audit contracts
- `geometry/`: normalized coordinates, DPI-aware metrics, and virtual desktop abstractions
- `persistence/`, `recovery/`: SQLite schema, repositories, checkpoint service, recovery loading
- `semantics/`, `verification/`: semantic layout/state models and semantic transition verification contracts
- `policy/`: allowlist/denylist rules, protected-context hooks, pause/resume, kill switch, action gating
- `app/`: async orchestration skeleton with queue, timeout, retry, and cancellation scaffolding
- `replay/`, `testing/`: replay harness, deterministic synthetic sessions, validation report helpers, reusable test fixtures

Still placeholder or interface-only areas:

- `integrations/windows/`
- `memory/`
- live perception/capture adapters
- real planner implementations
- real action execution

## Safety Defaults

- `observe_only` remains the default mode
- live input is rejected by `RunConfig`
- policy gating runs before any future live execution path
- protected contexts, pause state, and kill switch can deny execution
- replay and validation paths do not attempt live execution
- tests prefer replay, dry-run, and synthetic data over unsafe runtime behavior

## Dependencies

Current repo state is intentionally small:

- runtime dependencies in `pyproject.toml`: none
- test dependency in `requirements.txt`: `pytest`

That matches the current implementation, which is stdlib-first and keeps optional future integrations out of the base package.

## Running Tests

Install the test dependency:

```powershell
python -m pip install -r requirements.txt
```

Run the test suite:

```powershell
python -m pytest -q tests -p no:cacheprovider
```

Optional self-check:

```powershell
python -m compileall src tests
```

## Project Docs

- [docs/README.md](docs/README.md): active docs index and archive guide
- [docs/spec.md](docs/spec.md): source-of-truth requirements
- [docs/execplan.md](docs/execplan.md): phased implementation plan
- [docs/VALIDATION_REPORT_TEMPLATE.md](docs/VALIDATION_REPORT_TEMPLATE.md): report template for future delivery passes
- [docs/archive/PROJECT_STATUS.md](docs/archive/PROJECT_STATUS.md): archived implementation snapshot
- [docs/archive/NEXT_STEPS.md](docs/archive/NEXT_STEPS.md): archived planning snapshot
