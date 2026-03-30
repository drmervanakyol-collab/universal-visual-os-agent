Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement a new integration phase: OCR/text extraction adapter on top of the working full-desktop capture -> semantic preparation -> semantic state-building path.

Scope:
- do not add live input
- do not add action execution
- do not expand planning or policy
- work only on extracting text/OCR-ready semantic signals from the existing observe-only pipeline
- keep everything strictly observe-only and read-only

Goals:
- define an OCR/text extraction adapter interface
- add a clean text extraction result model
- connect successful full-desktop semantic preparation/state inputs to text extraction inputs
- support structured safe failure behavior when capture/preparation/state input is unavailable
- enrich semantic state with text-region or OCR-result placeholders/results in a clean, testable way
- keep the implementation modular so a future OCR backend can be swapped in safely

Required work:
- add OCR/text extraction interfaces and implementation scaffolding
- add a pure, testable adapter layer that transforms image/payload/state inputs into OCR extraction requests/results
- if a real OCR backend is needed, ask first before adding a dependency
- do not require external executables or non-Python runtime tools unless explicitly approved
- preserve explicit error reporting and observe-only semantics

Tests to add/update:
- successful prepared input -> OCR extraction adapter path
- safe handling of failed capture/preparation/state inputs
- safe handling of missing payload/metadata
- semantic state enrichment with text results/placeholders
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
- use the working DXcam full-desktop capture path as the primary integration target
- keep the implementation tightly scoped to OCR/text extraction only
- do not silently turn semantic candidates into actionable targets
- if a dependency is needed for real OCR, stop and ask first