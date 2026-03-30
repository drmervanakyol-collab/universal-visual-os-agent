------------faz1-----------

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement Phase 2A: geometric layout / region analysis on top of the completed full-desktop capture -> preparation -> state-building -> OCR enrichment pipeline.

Scope:
- do not add live input
- do not add action execution
- do not expand planning or policy
- work only on geometric / region-based layout analysis and semantic region structuring
- keep everything strictly observe-only and read-only

Current architecture to build on:
- full-desktop DXcam capture path
- semantic preparation
- semantic state building
- semantic enrichment
- OCR enrichment outputs
- existing semantic snapshot / layout tree / candidate structures

Goals:
- derive clearer geometric layout regions from the existing semantic snapshot and capture metadata
- introduce region semantics such as header/content/footer/sidebar/modal-like zones where justified
- preserve a consistent layout tree and region hierarchy
- keep all generated candidates non-actionable by default
- improve semantic structure without adding planning or action logic

Required work:
- add region/layout analysis interfaces and implementation
- derive region structures from bounds, frame geometry, metadata, and current semantic scaffold
- integrate region results into semantic snapshot/state outputs cleanly
- preserve explicit safe failure behavior when metadata is incomplete
- do not add third-party runtime dependencies in this phase
- keep the implementation modular and testable

Tests to add/update:
- successful semantic snapshot -> region analysis path
- consistent parent/child layout tree relations after region insertion
- safe handling of incomplete bounds or metadata
- region validity and geometry consistency
- no unhandled exception propagation
- preservation of observe-only semantics

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- include one read-only runtime smoke test if possible
- clearly separate:
  - actually executed checks
  - static reasoning only
  - environment-specific failures

Important:
- this phase is layout/region analysis only
- do not make region-derived candidates actionable
- keep the implementation tightly scoped to geometric region analysis and semantic structuring

--------------faz2-----------

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement Phase 2B: semantic layout enrichment on top of the completed geometric layout / region analysis phase.

Scope:
- do not add live input
- do not add action execution
- do not expand planning or policy
- work only on enriching the current geometric layout regions with stronger semantic interpretation
- keep everything strictly observe-only and read-only

Current architecture to build on:
- full-desktop DXcam capture path
- semantic preparation
- semantic state building
- semantic enrichment
- OCR enrichment
- geometric layout / region analysis outputs
- existing semantic snapshot / layout tree / candidate structures

Goals:
- enrich the current region analysis results with stronger semantic meaning
- improve how header/content/footer/sidebar/modal-like regions are represented in the semantic tree
- use OCR-derived signals and current semantic metadata where useful to refine semantic region meaning
- preserve a consistent layout tree and region hierarchy
- keep all generated candidates non-actionable by default
- improve semantic usefulness without adding planning or action logic

Required work:
- add semantic layout enrichment interfaces and implementation
- refine region roles and metadata using current OCR/semantic signals
- integrate the enriched region semantics into semantic snapshot/state outputs cleanly
- preserve explicit safe failure behavior when region or OCR metadata is incomplete
- do not add third-party runtime dependencies in this phase
- keep the implementation modular and testable

Tests to add/update:
- successful region analysis -> semantic layout enrichment path
- consistent parent/child layout tree relations after semantic enrichment
- safe handling of incomplete region/OCR metadata
- semantic role validity and metadata consistency
- no unhandled exception propagation
- preservation of observe-only semantics

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- include one read-only runtime smoke test if possible
- clearly separate:
  - actually executed checks
  - static reasoning only
  - environment-specific failures

Important:
- this phase is semantic layout enrichment only
- do not make region-derived or OCR-derived candidates actionable
- keep the implementation tightly scoped to semantic layout enrichment