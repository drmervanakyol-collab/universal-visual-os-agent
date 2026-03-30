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