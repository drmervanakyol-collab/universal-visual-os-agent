Read AGENTS.md, docs/SPEC.md, and docs/EXECPLAN.md.

Implement only Phase 3: coordinate and screen abstraction layer.

Scope:
- add DPI-aware screen metrics models and helpers
- implement normalized_to_screen()
- implement screen_to_normalized()
- implement bbox_normalized_to_screen()
- support multi-monitor-safe abstractions at the model/interface level
- keep everything pure, testable, and free of live capture or live input
- add focused tests for:
  - normalized round-trips
  - high-DPI behavior
  - negative coordinates / virtual desktop cases
  - invalid normalized bounds
  - screen metric validation

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