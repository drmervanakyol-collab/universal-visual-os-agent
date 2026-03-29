Read AGENTS.md, docs/SPEC.md, and docs/EXECPLAN.md.

Implement only Phase 5: policy and safety layer.

Scope:
- add allowlist / denylist models and policy rules
- add protected-context detection interfaces/hooks
- add kill switch abstraction
- add pause / resume state hooks
- add action gating before any future live execution
- keep everything pure, testable, and free of live capture or live input
- add focused tests for:
  - allow / deny decisions
  - protected-context blocking
  - pause / resume gating behavior
  - kill switch behavior
  - safe handling of unknown or partial policy context

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