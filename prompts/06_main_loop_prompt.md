Read AGENTS.md, docs/SPEC.md, and docs/EXECPLAN.md.

Implement only Phase 6: event-driven main loop skeleton.

Scope:
- add asyncio-based orchestration skeleton
- implement observe -> diff -> semantic rebuild -> policy check -> plan -> verify flow at a skeleton level
- add queue, timeout, cancellation, and retry scaffolding
- support observe_only, dry_run, replay_mode, and recovery_mode in the orchestration layer
- keep everything pure, testable, and free of live capture or live input
- use interfaces/placeholders for perception, planner, verifier, recovery, and action execution
- add focused tests for:
  - loop step ordering
  - mode-specific gating behavior
  - cancellation handling
  - timeout behavior
  - retry / safe abort behavior
  - no live execution in observe_only and dry_run defaults

Requirements:
- Python 3.14 style
- type hints on public interfaces
- small modules
- safe defaults only
- no live OS action
- no live screen capture
- keep OS-facing behavior behind interfaces/placeholders only

Before finishing:
- run the pre-delivery self-debug loop
- fix obvious syntax/import/interface issues
- run compile/import/test validation
- provide a concise validation report
- clearly separate actually executed checks from static reasoning