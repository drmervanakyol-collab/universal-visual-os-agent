Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement only Phase 7: validation and replay/test harness layer.

Scope:
- add a replay harness for recorded or synthetic event/frame sequences
- add validation report helpers/models
- add deterministic test-mode support where randomness/noise can be disabled
- add reusable test fixtures/helpers for replay_mode and recovery_mode
- add validation utilities for:
  - executed vs static reasoning report separation
  - environment issue reporting
  - safe module / unsafe module summaries
- keep everything pure, testable, and free of live capture or live input
- add focused tests for:
  - replay harness flow
  - deterministic mode behavior
  - validation report formatting/content
  - safe handling of missing replay data
  - recovery-mode replay setup
  - no live execution in validation paths

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