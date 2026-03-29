Read AGENTS.md, docs/SPEC.md, and docs/EXECPLAN.md.

Implement only Phase 2: state, memory, and recovery persistence skeleton.

Scope:
- add SQLite schema for tasks, checkpoints, and audit events
- add persistence models and repository interfaces
- add checkpoint writer/reader
- add recovery snapshot loading primitives
- add state reconciliation interfaces only
- keep everything safe, dry-run friendly, and free of live OS actions
- add focused tests for checkpoint persistence and recovery loading

Requirements:
- Python 3.14 style
- type hints on public interfaces
- small modules
- safe defaults only
- do not implement live capture
- do not implement live input
- do not add unsafe shortcuts
- keep OS-facing behavior behind interfaces/placeholders only

Suggested deliverables:
- SQLite schema module(s)
- repository interfaces and concrete SQLite repositories
- checkpoint persistence service
- recovery state model(s)
- state reconciliation contract(s)
- tests for:
  - writing a checkpoint
  - reading the latest checkpoint
  - loading recovery state
  - handling missing checkpoint data safely
  - audit event persistence basics

Before finishing:
- run the pre-delivery self-debug loop
- fix obvious syntax/import/interface issues
- run compile/import/test validation
- provide a concise validation report
- clearly separate actually executed checks from static reasoning

Important:
- If you need to install a test dependency, ask first
- If you encounter an environment-only issue, explain it clearly and do not present it as a code defect
- Keep the implementation tightly scoped to Phase 2 only