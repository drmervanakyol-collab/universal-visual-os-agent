# Project Status

## Completed Phases

- Phase 0: planning, compatibility review, and repo structure definition
- Phase 1: package skeleton, config, modes, logging, and core contracts
- Phase 2: SQLite schema, repositories, checkpoint persistence, and recovery loading primitives
- Phase 3: coordinate transforms, DPI-aware screen metrics, and virtual desktop abstractions
- Phase 4: semantic layout tree, semantic state snapshots, and semantic verification contracts
- Phase 5: policy and safety layer with allowlist/denylist rules, protected-context hooks, pause/resume, and kill switch
- Phase 6: asyncio event-driven main loop skeleton with queue, timeout, cancellation, retry, and mode-aware orchestration
- Phase 7: replay harness, deterministic synthetic sessions, validation report helpers, and reusable replay/recovery test helpers

## Implemented Modules

- `config`: `AgentMode`, `RunConfig`, logging and persistence config models
- `core`, `audit`: shared events, clocks, sinks, and audit record models
- `geometry`: normalized points and bounds, screen metrics, virtual desktop models, transform helpers
- `persistence`: SQLite schema, task/checkpoint/audit repositories, checkpoint service
- `recovery`: recovery snapshots, repository-backed loader, reconciliation contracts
- `semantics`: layout tree nodes, semantic candidates, semantic state snapshots
- `verification`: semantic transition expectations, results, evaluator, verifier contracts
- `policy`: rule models, policy engine, protected-context hook, pause and kill switch abstractions
- `app`: async loop request/result models, adapter interfaces, orchestration skeleton
- `replay`: replay session models, replay providers, harness, synthetic deterministic session builder
- `testing`: validation report helpers and reusable replay/recovery fixtures

## Still-Placeholder Areas

- `integrations/windows`: placeholder package only
- `memory`: placeholder package only
- perception adapters are still interface-only outside replay providers
- planner implementations are still placeholder/test doubles, not goal-driven logic
- action execution remains a contract only; no live executor is implemented
- semantic rebuild from real frames is not implemented
- safe action mode from the spec is not implemented yet

## Current Safety Guarantees

- default runtime mode is `observe_only`
- `RunConfig` rejects live input
- no live screen capture implementation exists in the repo
- policy evaluation can deny or review actions for kill switch, pause state, protected context, deny rules, and incomplete context
- recovery logic is persistence-first and can be exercised with replay/synthetic data
- replay and validation helpers keep execution in pure, deterministic, non-live paths
- validation reporting explicitly separates executed checks from static reasoning

## Current Limitations

- no real Windows capture, UI automation, or input execution
- no production semantic extraction pipeline
- no production planner or recovery planner logic
- no real frame-diff implementation outside replay scaffolding
- no end-to-end persistence/orchestration integration with actual OS state
- no rollout, telemetry, or operational safeguards beyond local skeleton hooks
- no packaging or dependency story yet for optional future Windows integrations

## How To Run Tests

Install test requirements:

```powershell
python -m pip install -r requirements.txt
```

Run tests:

```powershell
python -m pytest -q tests -p no:cacheprovider
```

Optional compile pass:

```powershell
python -m compileall src tests
```
