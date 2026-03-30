------faz1-----

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement Phase 6A: scenario definition layer.

Scope:
- do not add new live input types
- do not expand real execution beyond the existing narrow safe click prototype
- do not expand planning or policy beyond what is needed for scenario definition
- work only on defining reusable scenario structures on top of the completed observe-only and safe-action pipeline
- keep everything safety-first

Current pipeline to build on:
- full-desktop DXcam capture
- semantic preparation
- semantic state building
- semantic enrichment
- OCR enrichment
- geometric layout / region analysis
- semantic layout enrichment
- candidate generation
- candidate scoring
- safe candidate exposure
- semantic delta / state comparison
- goal-oriented verification
- verification explanation / taxonomy
- safe action-intent scaffolding
- dry-run action engine
- minimal safe click prototype

Goals:
- define a reusable scenario layer for small agent tasks
- represent things such as:
  - scenario identity
  - scenario steps
  - expected semantic outcomes
  - candidate selection constraints
  - safety requirements
  - dry-run vs real-execution eligibility
  - scenario status / scenario result
- keep scenario definitions explicit, structured, and testable
- improve orchestration readiness without adding broad new execution behavior

Required work:
- add scenario definition interfaces and implementation scaffolding
- define clean scenario models and result models
- support scenario step definitions that can reference existing verification and action-intent structures
- preserve explicit safe failure behavior when required scenario inputs are incomplete
- keep the implementation modular and testable
- do not add third-party runtime dependencies in this phase

Tests to add/update:
- successful scenario definition / parse / validation path
- safe handling of incomplete scenario definitions
- scenario metadata consistency
- no unhandled exception propagation
- preservation of observe-only / safety-first semantics
- explicit handling of dry-run-only vs real-click-eligible scenario flags

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- include one read-only runtime smoke test if possible
- clearly separate:
  - actually executed checks
  - static reasoning only
  - environment-specific failures

Important:
- this phase is scenario definition only
- do not broaden into full end-to-end execution yet
- do not add keyboard input or text entry
- keep the implementation tightly scoped to scenario modeling and scaffolding

------faz2----

