-----------faz1------------

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement a new integration sub-phase: OCR/text extraction scaffolding only (Phase 1A).

Scope:
- do not add live input
- do not add action execution
- do not expand planning or policy
- do not add a real OCR runtime backend yet
- work only on OCR/text extraction interfaces, models, and semantic integration scaffolding
- keep everything strictly observe-only and read-only

Goals:
- define OCR/text extraction adapter interfaces
- add clean OCR result models
- add text-region / text-block models
- connect semantic preparation/state-building outputs to OCR-ready input models
- provide safe structured failure behavior when OCR input cannot be prepared
- prepare the pipeline so a real OCR backend can be plugged in later without refactoring the architecture

Required work:
- add OCR interfaces and models
- add OCR request / OCR response / text region structures
- add a pure adapter layer that maps the current semantic preparation/state-building outputs into OCR extraction inputs
- integrate these structures into semantics in a clean and testable way
- do not add third-party runtime dependencies in this phase
- preserve explicit observe-only semantics

Tests to add/update:
- successful semantic input -> OCR input preparation path
- safe handling of failed capture/preparation/state inputs
- safe handling of missing payload/metadata
- text-region / OCR result model validity
- no unhandled exception propagation
- preservation of observe-only semantics

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- clearly separate:
  - actually executed checks
  - static reasoning only
  - environment-specific failures

Important:
- this phase is scaffolding only
- do not add a real OCR backend yet
- keep the implementation tightly scoped to OCR preparation, interfaces, and models only



-----------faz2----------------------------

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement Phase 1B: real OCR backend integration on top of the completed Phase 1A OCR scaffolding.

Scope:
- do not add live input
- do not add action execution
- do not expand planning or policy
- work only on plugging a real OCR backend into the existing OCR/text extraction architecture
- keep everything strictly observe-only and read-only

Current architecture to build on:
- PreparedSemanticTextExtractionAdapter
- TextExtractionRequest
- TextExtractionResponse
- TextExtractionResponseStatus
- TextExtractionBackend
- TextExtractionResult
- SemanticTextBlock
- SemanticTextRegion
- SemanticTextStatus

Goals:
- integrate one real OCR backend behind the existing TextExtractionBackend protocol
- preserve the current adapter architecture so the OCR backend remains swappable
- support OCR extraction from the working full-desktop capture -> semantic preparation -> semantic state-building path
- map OCR output into the existing semantic text models
- preserve structured safe failure behavior
- keep OCR output non-actionable by default

Requirements:
- if a dependency is needed, ask first before adding it
- prefer a Python-native solution that does not require external executables if feasible
- preserve explicit error reporting
- keep interfaces small and testable
- do not silently degrade failures into empty success
- do not convert OCR results into actionable targets
- do not add unrelated image analysis features in this phase

Required work:
- implement one real OCR backend behind TextExtractionBackend
- connect the real OCR backend to the current request/response pipeline
- map backend OCR output into SemanticTextRegion / SemanticTextBlock / TextExtractionResult structures
- preserve placeholder-safe behavior when OCR cannot run
- keep the implementation modular so the OCR backend can be replaced later

Tests to add/update:
- successful OCR backend path on representative synthetic/test input
- safe handling of OCR backend unavailability
- safe handling of empty OCR output
- safe handling of malformed OCR output
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
- this phase is real OCR backend integration only
- do not add executable/tooling dependencies without asking first
- keep the implementation tightly scoped to OCR backend integration

----------faz3------------

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement Phase 1C: OCR enrichment on top of the completed real OCR backend integration.

Scope:
- do not add live input
- do not add action execution
- do not expand planning or policy
- work only on enriching semantic state with real OCR results from the existing OCR pipeline
- keep everything strictly observe-only and read-only

Current architecture to build on:
- PreparedSemanticTextExtractionAdapter
- TextExtractionBackend
- RapidOcrTextExtractionBackend
- TextExtractionRequest
- TextExtractionResponse
- TextExtractionResponseStatus
- TextExtractionResult
- SemanticTextRegion
- SemanticTextBlock
- SemanticTextStatus
- PreparedSemanticStateBuilder and current semantic state outputs

Goals:
- take successful OCR results and enrich semantic state/snapshots with them
- connect OCR text regions and text blocks into the semantic scaffold in a clean, testable way
- preserve non-actionable defaults throughout
- keep structured failure behavior when OCR is unavailable or partial
- improve semantic usefulness without adding planning/action logic

Required work:
- integrate OCR results into semantic snapshot/state structures
- propagate OCR text and region metadata cleanly
- preserve layout tree consistency
- keep OCR-enriched candidates non-actionable by default
- avoid silent failure masking
- do not add unrelated image analysis features in this phase

Tests to add/update:
- successful OCR result -> semantic enrichment path
- safe handling of empty OCR output
- safe handling of partial OCR output
- safe handling of OCR backend failure results
- semantic snapshot consistency after enrichment
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
- this phase is OCR enrichment only
- do not make OCR-derived candidates actionable
- keep the implementation tightly scoped to semantic enrichment from OCR output