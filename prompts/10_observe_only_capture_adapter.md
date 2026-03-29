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

--------BitBlt failed hatası teşhisi için 

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement a focused diagnostics and hardening pass for the existing Windows observe-only capture adapter only.

Scope:
- do not add new architecture layers
- do not add live input
- do not add action execution
- do not expand planning or semantic extraction
- work only on the existing Windows observe-only capture implementation and its tests

Goals:
- diagnose why live Win32 screen-copy currently fails with structured error_code='windows_api_error' and BitBlt failure
- improve diagnostics so failures are easier to distinguish and debug
- keep the adapter strictly read-only and observe-only
- preserve structured failure behavior instead of throwing unhandled exceptions
- if possible, make the capture path more robust without introducing unsafe behavior

Required changes:
- improve error classification around the Windows capture path
- include more structured failure details where safe and useful:
  - failing API stage
  - Win32 error code if available
  - whether metrics lookup succeeded
  - whether DC/bitmap creation succeeded
  - whether virtual desktop bounds were valid
- add a conservative fallback strategy only if it remains read-only and safe
- keep all OS-specific logic isolated under `integrations/windows`
- do not add third-party runtime dependencies unless absolutely necessary; ask first if one is needed

Tests to add/update:
- safe failure behavior for each major capture stage
- structured diagnostic output shape
- fallback behavior if a primary capture path fails
- no unhandled exception propagation
- abstraction-level behavior for invalid bounds / metrics failures

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- include one read-only runtime smoke test if possible
- clearly separate:
  - actually executed checks
  - environment-specific failures
  - static reasoning only

Important:
- If capture still fails in this environment, do not hide that fact.
- If the issue appears environment-specific, say so clearly and explain why.
- Keep the implementation tightly scoped to diagnostics and hardening of the existing capture adapter only.