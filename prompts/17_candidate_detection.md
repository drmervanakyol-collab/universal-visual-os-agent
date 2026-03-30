-------faz1--------

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement Phase 3A: non-actionable candidate generation on top of the completed OCR and layout-enrichment pipeline.

Scope:
- do not add live input
- do not add action execution
- do not expand planning or policy
- work only on generating candidate structures from the current semantic snapshot, OCR enrichment, and layout-enrichment outputs
- keep everything strictly observe-only and read-only

Current architecture to build on:
- full-desktop DXcam capture path
- semantic preparation
- semantic state building
- semantic enrichment
- OCR enrichment
- geometric layout / region analysis
- semantic layout enrichment
- existing semantic snapshot / layout tree / candidate structures

Goals:
- generate richer non-actionable candidates from the existing semantic state
- include likely candidate classes such as:
  - button-like
  - input-like
  - tab-like
  - close-like
  - popup-dismiss-like
  - generic interactive-region-like
- keep all generated candidates explicitly non-actionable by default
- preserve consistent layout tree and region relationships
- improve semantic usefulness without adding planning or action logic

Required work:
- add candidate generation interfaces and implementation
- derive candidate structures from existing OCR, region, and semantic metadata
- attach confidence / heuristic explanation fields where useful
- preserve explicit safe failure behavior when inputs are incomplete
- do not add third-party runtime dependencies in this phase
- keep the implementation modular and testable

Tests to add/update:
- successful semantic snapshot -> non-actionable candidate generation path
- candidate validity and metadata consistency
- safe handling of incomplete OCR/region/semantic metadata
- no unhandled exception propagation
- preservation of observe-only semantics
- explicit verification that generated candidates remain non-actionable

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- include one read-only runtime smoke test if possible
- clearly separate:
  - actually executed checks
  - static reasoning only
  - environment-specific failures

Important:
- this phase is non-actionable candidate generation only
- do not make generated candidates actionable
- do not add click/selection logic
- keep the implementation tightly scoped to candidate generation

---------faz2------

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement Phase 3B: non-actionable candidate scoring.

Scope:
- do not add live input
- do not add action execution
- do not expand planning or policy
- work only on scoring the already generated non-actionable candidates
- keep everything strictly observe-only and read-only

Current pipeline to build on:
- full-desktop DXcam capture
- semantic preparation
- semantic state building
- semantic enrichment
- OCR enrichment
- geometric layout / region analysis
- semantic layout enrichment
- non-actionable candidate generation

Goals:
- assign a confidence/score to each generated candidate
- keep all candidates non-actionable
- provide clear score explanation / contributing factors
- use current OCR, region, layout, and semantic metadata as scoring signals
- improve usefulness without adding planning or action logic

Required work:
- add candidate scoring interfaces and implementation
- score the existing generated candidates
- attach score explanation / contributing factors where useful
- preserve explicit safe failure behavior when metadata is incomplete
- do not add third-party runtime dependencies in this phase
- keep the implementation modular and testable

Tests to add/update:
- successful candidate set -> scored candidate path
- score metadata consistency
- safe handling of incomplete OCR/region/semantic metadata
- no unhandled exception propagation
- preservation of observe-only semantics
- explicit verification that scored candidates remain non-actionable

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- include one read-only runtime smoke test if possible
- clearly separate:
  - actually executed checks
  - static reasoning only
  - environment-specific failures

Important:
- this phase is candidate scoring only
- do not make candidates actionable
- do not add click/selection logic
- keep the implementation tightly scoped to scoring and score explanation