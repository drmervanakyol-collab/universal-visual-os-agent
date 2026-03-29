Read AGENTS.md, docs/SPEC.md, and docs/EXECPLAN.md.

Implement only Phase 4 locally in this repository.

Scope:
- add semantic layout tree models
- add semantic candidate and semantic state snapshot models
- add verification contracts for semantic-state transitions
- update semantic and verification exports
- add focused tests in tests/test_semantic_state_pipeline.py

Requirements:
- keep the scope limited to Phase 4 only
- no live capture
- no live input
- no OS-facing implementation
- Python 3.14
- run compile/import/test validation
- clearly separate actually executed checks from static reasoning

Before finishing:
- run the pre-delivery self-debug loop
- fix obvious syntax/import/interface issues
- provide a concise validation report