-----------faz1-------------

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement Phase 4A: semantic delta / state comparison.

Scope:
- do not add live input
- do not add action execution
- do not expand planning or policy
- work only on comparing semantic states/snapshots and producing structured delta outputs
- keep everything strictly observe-only and read-only

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

Goals:
- compare two semantic snapshots/states and produce a structured semantic delta
- identify what changed between states, such as:
  - added/removed layout regions
  - added/removed/changed OCR text regions or text blocks
  - candidate additions/removals/score changes
  - metadata/state changes that matter for later verification
- preserve explicit safe failure behavior when one or both inputs are incomplete
- improve downstream usefulness without adding planning or action logic

Required work:
- add semantic delta interfaces and implementation
- define clean delta result models
- compare snapshots/states in a deterministic, testable way
- include structured change categories and summaries where useful
- keep the implementation modular and testable
- do not add third-party runtime dependencies in this phase

Tests to add/update:
- successful snapshot A -> snapshot B delta path
- safe handling of missing or partial inputs
- added/removed/changed item detection
- deterministic output ordering where useful
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
- this phase is semantic delta/state comparison only
- do not make anything actionable
- do not add click/selection logic
- keep the implementation tightly scoped to semantic delta generation

-------faz2------

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement Phase 4B: goal-oriented verification.

Scope:
- do not add live input
- do not add action execution
- do not expand planning or policy
- work only on verification logic that evaluates whether an expected semantic outcome occurred
- keep everything strictly observe-only and read-only

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

Goals:
- evaluate whether expected semantic outcomes occurred between two semantic states
- support verification cases such as:
  - expected region appeared
  - expected text appeared / disappeared / changed
  - expected candidate appeared / disappeared / changed score
  - expected metadata/state change occurred
- preserve explicit safe failure behavior when one or both inputs are incomplete
- improve downstream usefulness without adding planning or action logic

Required work:
- add verification interfaces and implementation
- define clean verification result models
- use the existing semantic delta layer as the basis for verification
- include structured verification reasons / outcome summaries where useful
- keep the implementation modular and testable
- do not add third-party runtime dependencies in this phase

Tests to add/update:
- successful expected-outcome verification path
- failed expected-outcome verification path
- safe handling of missing or partial inputs
- deterministic verification output where useful
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
- this phase is goal-oriented verification only
- do not make anything actionable
- do not add click/selection logic
- keep the implementation tightly scoped to verification logic built on semantic delta

-----faz3-----

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement Phase 4C: verification explanation and failure taxonomy.

Scope:
- do not add live input
- do not add action execution
- do not expand planning or policy
- work only on explanation, classification, and failure taxonomy for the existing verification layer
- keep everything strictly observe-only and read-only

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

Goals:
- add a structured explanation layer for verification outcomes
- classify verification failures and unknown outcomes into a clear taxonomy
- provide stable reason categories such as:
  - missing_input
  - partial_input
  - expected_change_not_found
  - unexpected_change_detected
  - score_change_not_satisfied
  - metadata_expectation_not_met
  - ambiguous_result
- preserve explicit safe behavior when inputs are incomplete
- improve downstream usefulness without adding planning or action logic

Required work:
- add verification explanation / taxonomy interfaces and implementation
- define clean explanation and taxonomy result models
- enrich existing verification results with structured explanation categories and summaries
- keep the implementation modular and testable
- do not add third-party runtime dependencies in this phase

Tests to add/update:
- successful verification explanation path
- failed verification explanation path
- unknown / partial-input explanation path
- deterministic taxonomy output where useful
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
- this phase is verification explanation and failure taxonomy only
- do not make anything actionable
- do not add click/selection logic
- keep the implementation tightly scoped to explanation and taxonomy on top of existing verification