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

--------BitBlt failed hatası teşhisi için-----------

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

-----------tam çözülmedi----

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement a focused read-only capture backend strategy improvement for the existing Windows observe-only capture layer.

Scope:
- do not add live input
- do not add action execution
- do not expand planning or semantic extraction
- work only on the observe-only capture stack and its abstractions

Goals:
- keep the current GDI/BitBlt capture path as one backend
- introduce a backend strategy abstraction so multiple read-only capture backends can be selected safely
- add capability detection / backend selection logic
- preserve structured failure behavior and diagnostics
- prefer safe, explicit backend reporting over silent fallback

Required work:
- define a capture backend abstraction and backend selection result
- keep the existing GDI backend
- investigate and implement, if feasible within current repo constraints, one additional read-only Windows capture backend path
- if a full alternate backend is not feasible, still implement:
  - backend strategy abstraction
  - capability detection hooks
  - structured “why this backend is unavailable” reporting
- isolate all OS-specific logic under integrations/windows
- do not add third-party runtime dependencies unless absolutely necessary; ask first if one is needed

Preferred backend candidates:
- a safer alternate Windows read-only backend for display/window capture
- if only window-level capture is feasible in this pass, keep that clearly separated from full desktop capture

Tests to add/update:
- backend selection behavior
- capability detection output
- structured unavailable-backend reporting
- safe fallback ordering
- no unhandled exception propagation
- preservation of observe-only semantics

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- include one read-only runtime smoke test if possible
- clearly separate:
  - actually executed checks
  - environment-specific failures
  - static reasoning only

Important:
- If the existing GDI backend still fails in this environment, do not hide that fact.
- If an alternate backend cannot be fully implemented safely in this pass, say so clearly and leave the code in a cleaner backend-strategy state.
- Keep the implementation tightly scoped to capture backend strategy and safe diagnostics only.

-----alt yapı düzeldi ama sorun çözülmedi----

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement a focused live-validation and hardening pass for the existing read-only PrintWindow foreground-window capture backend only.

Scope:
- do not add live input
- do not add action execution
- do not expand planning or semantic extraction
- work only on the existing PrintWindow foreground-window capture path and its diagnostics/tests

Goals:
- validate whether the existing PrintWindow foreground-window backend can successfully capture in this environment
- improve its structured diagnostics and stage reporting
- clearly distinguish:
  - unsupported target
  - no foreground window
  - inaccessible window handle
  - PrintWindow failure
  - bitmap/readback failure
  - environment/session limitations
- keep everything strictly read-only and observe-only

Required work:
- add or improve runtime smoke validation for foreground_window capture
- improve structured failure/result details for the PrintWindow path
- add any small hardening needed for:
  - invalid hwnd
  - minimized/invisible/unsupported windows
  - foreground window changes during capture
- preserve safe structured failure behavior
- do not add third-party runtime dependencies unless absolutely necessary; ask first if one is needed

Tests to add/update:
- foreground-window backend selection behavior
- unsupported target handling
- no-foreground-window behavior
- structured diagnostic output shape
- no unhandled exception propagation
- safe behavior when PrintWindow returns failure

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- include one read-only runtime smoke test for foreground_window capture if possible
- clearly separate:
  - actually executed checks
  - environment-specific failures
  - static reasoning only

Important:
- If live PrintWindow capture still fails in this environment, do not hide that fact.
- If it succeeds, report the exact target type and success path clearly.
- Keep the implementation tightly scoped to the existing PrintWindow foreground-window backend only.

-------tanı için script oluşturma -------

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement a small local diagnostic utility for interactive Windows foreground-window capture validation only.

Scope:
- do not add live input
- do not add action execution
- do not expand planning, semantics, or replay
- work only on a small manual diagnostic entry point for the existing observe-only capture stack

Goals:
- add a simple local diagnostic script or module that can be run manually by the user
- check and print:
  - whether a foreground window handle is detected
  - basic foreground window metadata if available
  - whether the PrintWindow backend can capture that foreground window
  - structured success/failure details
- optionally save a diagnostic image only if capture succeeds
- keep everything strictly read-only and observe-only

Requirements:
- Python 3.14 style
- type hints where appropriate
- small, isolated implementation
- no third-party runtime dependencies unless absolutely necessary; ask first if one is needed
- no live input
- no action execution

Tests:
- add focused tests for the diagnostic result shape and safe failure behavior
- do not over-expand scope

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- clearly separate actually executed checks from static reasoning

Important:
- the utility must be intended for manual local execution by the user in an interactive desktop session
- if capture succeeds, report that clearly
- if no foreground window is visible, report that clearly
- keep the implementation tightly scoped to diagnostics only

------full erkran için farklı çözüm ------

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement a focused new integration phase for full-desktop read-only capture using a modern Windows backend, with Desktop Duplication as the primary target.

Scope:
- do not add live input
- do not add action execution
- do not expand planning, semantics, or policy
- work only on full-desktop observe-only capture capability
- keep all OS-specific logic isolated under `integrations/windows`

Primary goal:
- add a new read-only full-desktop capture backend strategy centered on Windows Desktop Duplication feasibility and implementation

Required goals:
- investigate and implement, if feasible in the current repo constraints, a read-only Desktop Duplication backend for full desktop capture
- if full implementation is not feasible in this pass, still add:
  - backend abstraction support
  - capability detection
  - structured backend availability reporting
  - clear diagnostic output explaining why Desktop Duplication is unavailable or incomplete
- preserve the existing observe-only safety model
- do not remove the existing GDI or PrintWindow paths; keep them as fallbacks or separate strategies

Functional requirements:
- target full desktop / virtual desktop capture, not only foreground window capture
- support multi-monitor-safe abstractions where possible
- return structured success/failure results
- preserve image payload + frame metadata behavior
- report structured diagnostics including:
  - selected backend
  - available backends
  - capability detection results
  - failing stage
  - environment/session limitations
  - whether fallback paths were attempted

Safety requirements:
- strictly read-only and observe-only
- no live input
- no action execution
- no unsafe shortcuts
- no silent fallback that hides backend failure reasons
- if a backend is unavailable, return safe structured failure instead of throwing unhandled exceptions

Implementation constraints:
- Python 3.14 style
- type hints on public interfaces
- keep modules small
- keep interfaces clean and testable
- do not add third-party runtime dependencies unless absolutely necessary; ask first if one is needed
- if Desktop Duplication requires a substantial low-level dependency or cannot be safely implemented directly in this pass, say so clearly and leave the code in a cleaner backend-strategy state

Tests to add/update:
- backend capability detection behavior
- backend selection behavior for full-desktop capture requests
- structured unavailable-backend reporting
- safe failure behavior for incomplete or unsupported Desktop Duplication paths
- no unhandled exception propagation
- preservation of observe-only semantics
- abstraction-level validation for virtual desktop output shape

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- include one read-only runtime smoke test if possible
- clearly separate:
  - actually executed checks
  - environment-specific failures
  - static reasoning only

Important:
- If Desktop Duplication cannot be fully implemented safely in this pass, do not fake completeness.
- If the current environment does not allow successful live full-desktop capture validation, say so clearly.
- If another modern read-only full-desktop Windows backend is more feasible within current repo constraints, explain that explicitly and compare it against Desktop Duplication.
- Keep the implementation tightly scoped to full-desktop capture backend strategy and diagnostics only.

-----yine olmadı dxcam eklemeyi deneyecek-------

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement a focused new integration phase for working full-desktop observe-only capture using DXcam as the primary backend.

Scope:
- do not add live input
- do not add action execution
- do not expand planning, semantics, or policy
- work only on full-desktop observe-only capture capability
- keep all OS-specific logic isolated under `integrations/windows`

Goals:
- add a new DXcam-backed full-desktop capture backend
- keep the existing GDI backend as a fallback
- keep PrintWindow separate for foreground-window capture only
- preserve structured success/failure results
- preserve backend selection and diagnostics
- prefer DXcam for full-desktop capture requests when available

Requirements:
- ask for approval before adding the dependency if needed
- integrate DXcam behind the existing capture backend abstraction
- support full-desktop / virtual-desktop capture requests
- keep everything strictly read-only and observe-only
- report:
  - selected backend
  - available backends
  - backend unavailability reasons
  - environment/session limitations
  - fallback behavior
- no silent fallback that hides failure causes

Tests to add/update:
- DXcam backend availability detection
- backend selection behavior for full-desktop requests
- structured failure behavior when DXcam is unavailable
- safe fallback to GDI if DXcam is unavailable or fails
- no unhandled exception propagation
- preservation of observe-only semantics

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- include one read-only runtime smoke test for full-desktop capture if possible
- clearly separate:
  - actually executed checks
  - environment-specific failures
  - static reasoning only

Important:
- If DXcam integration succeeds, use it as the primary full-desktop backend.
- If DXcam cannot be added safely, say so clearly and stop rather than faking completeness.
- Keep the implementation tightly scoped to full-desktop capture backend integration only.

------dxcam güncellemesi-----

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement a focused diagnostic-only pass for the existing DXcam full-desktop capture backend.

Scope:
- do not add live input
- do not add action execution
- do not add new capture backends
- do not expand planning, semantics, or policy
- work only on diagnosing why the current DXcam backend returns COMError / access denied in this environment

Goals:
- add a small manual local diagnostic utility for DXcam
- report structured details about:
  - process/session context
  - whether the process appears interactive
  - current desktop/session accessibility
  - backend initialization stage
  - exact failure stage and HRESULT
  - output selection details
  - monitor/output metadata
- keep everything strictly read-only and diagnostic-only
- do not hide environment-specific failures

Requirements:
- Python 3.14 style
- type hints where appropriate
- small, isolated implementation
- no new third-party dependency
- no live input
- no action execution

Tests:
- add focused tests for diagnostic result shape and safe failure behavior
- do not over-expand scope

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- clearly separate:
  - actually executed checks
  - environment-specific failures
  - static reasoning only

Important:
- the utility must be intended for manual local execution by the user in an interactive desktop session
- if DXcam initialization fails, report the exact HRESULT and stage clearly
- keep the implementation tightly scoped to diagnostics only

-------ful desktop utility ------

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement a small manual full-desktop DXcam capture diagnostic utility only.

Scope:
- do not add live input
- do not add action execution
- do not expand planning, semantics, or policy
- work only on a manual local diagnostic entry point for the existing DXcam full-desktop observe-only capture path

Goals:
- add a simple local diagnostic script or module that can be run manually by the user
- check and print:
  - whether the DXcam backend initializes successfully
  - whether a real full-desktop frame can be acquired
  - frame width/height and metadata if successful
  - structured success/failure details if unsuccessful
- optionally save a diagnostic image only if capture succeeds
- keep everything strictly read-only and observe-only

Requirements:
- Python 3.14 style
- type hints where appropriate
- small, isolated implementation
- no third-party runtime dependencies beyond the already approved DXcam
- no live input
- no action execution

Tests:
- add focused tests for diagnostic result shape and safe failure behavior
- do not over-expand scope

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- clearly separate actually executed checks from static reasoning

Important:
- the utility must be intended for manual local execution by the user in an interactive desktop session
- if real frame capture succeeds, report that clearly
- if image saving is supported, save only on success
- keep the implementation tightly scoped to diagnostics only