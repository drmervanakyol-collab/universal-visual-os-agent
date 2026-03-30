Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement a new integration phase: semantic state building pipeline on top of the working full-desktop capture preparation path.

Scope:
- do not add live input
- do not add action execution
- do not expand planning or policy
- work only on building semantic state objects from the existing semantic extraction preparation inputs

Goals:
- take the existing SemanticExtractionInput / preparation path and build semantic state outputs from it
- construct semantic layout/state models in a clean, testable pipeline
- support:
  - semantic layout tree creation
  - semantic candidate node creation
  - semantic snapshot construction
  - safe handling of incomplete or missing metadata/payload
- keep everything strictly observe-only and read-only

Required work:
- add interfaces and implementation for semantic state building
- transform prepared semantic extraction input into semantic state / layout outputs
- preserve structured safe failure behavior
- keep the implementation pure and testable
- do not add third-party runtime dependencies unless absolutely necessary; ask first if one is needed

Tests to add/update:
- successful semantic preparation input -> semantic state output path
- safe handling of failed / partial preparation inputs
- semantic layout tree consistency
- semantic candidate validity
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
- use the working DXcam full-desktop capture + semantic preparation path as the primary integration target
- keep the implementation tightly scoped to semantic state building only