Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement a new post-skeleton integration phase: observe-only capture adapter only.

Scope:
- add a read-only screen capture adapter
- keep it strictly observe-only
- integrate it behind the existing perception abstractions
- return frame metadata and image payload in a safe adapter/result shape
- support safe failure behavior when capture is unavailable
- keep OS-specific logic isolated under integrations/windows or perception adapters as appropriate
- do not add live input
- do not add action execution
- do not add planning changes

Requirements:
- Python 3.14 style
- type hints on public interfaces
- small modules
- safe defaults only
- ask first if a new third-party runtime dependency is needed
- keep interfaces clean and testable

Add focused tests for:
- provider output shape
- safe unavailable-capture behavior
- frame metadata correctness
- abstraction-level handling of width/height/timestamp fields

Before finishing:
- run the pre-delivery self-debug loop
- fix obvious syntax/import/interface issues
- run compile/import/test validation
- provide a concise validation report
- clearly separate actually executed checks from static reasoning

If capture is unavailable, return a safe structured failure/result instead of throwing unhandled errors.