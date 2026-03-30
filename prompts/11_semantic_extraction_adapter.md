Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement a new integration phase: semantic extraction adapter for working full-desktop observe-only capture.

Scope:
- do not add live input
- do not add action execution
- do not expand planning or policy
- work only on connecting successful full-desktop capture results into the semantic state pipeline

Goals:
- define a semantic extraction adapter that accepts successful full-desktop capture results from the existing DXcam-backed observe-only capture path
- convert safe successful frame results into semantic extraction input models
- support safe structured failure behavior if capture failed or image payload is unavailable
- prepare semantic state snapshot input in a clean, testable way
- keep everything strictly observe-only and read-only

Required work:
- add adapter interfaces and implementation for semantic extraction input preparation
- connect capture result metadata to semantic state snapshot preparation
- keep OS-specific logic isolated where appropriate
- do not add third-party runtime dependencies unless absolutely necessary; ask first if one is needed

Tests to add/update:
- successful full-desktop capture result -> semantic extraction input path
- safe handling of failed capture results
- safe handling of missing payload/metadata
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
- do not depend on GDI full-desktop capture succeeding
- keep the implementation tightly scoped to semantic extraction preparation only