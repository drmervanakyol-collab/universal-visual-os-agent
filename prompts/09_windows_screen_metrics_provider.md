Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement a new post-skeleton integration phase: Windows screen metrics provider only.

Scope:
- add a Windows-backed screen metrics provider implementation
- keep it strictly observe-only and read-only
- integrate it behind the existing geometry / screen metrics abstractions
- support:
  - primary monitor metrics
  - virtual desktop bounds
  - negative coordinates
  - DPI-aware metrics
  - multi-monitor-safe model output
- keep all OS-specific logic isolated under integrations/windows
- do not add live capture
- do not add live input
- do not add action execution

Requirements:
- Python 3.14 style
- type hints on public interfaces
- small modules
- safe defaults only
- use OS-facing code only for reading screen metrics
- no unsafe shortcuts
- keep interfaces clean and testable

Add focused tests for:
- metric model compatibility
- provider output shape
- safe failure behavior when Windows APIs are unavailable
- virtual desktop / negative coordinate handling at the abstraction level

Before finishing:
- run the pre-delivery self-debug loop
- fix obvious syntax/import/interface issues
- run compile/import/test validation
- provide a concise validation report
- clearly separate actually executed checks from static reasoning
If Windows APIs are unavailable, return a safe structured failure/result instead of throwing unhandled errors.
Do not add third-party runtime dependencies unless absolutely necessary; ask first if one is needed.
