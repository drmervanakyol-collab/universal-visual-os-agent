------faz1------

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement Phase 5A: safe action intent scaffolding.

Scope:
- do not add live input
- do not add real action execution
- do not expand planning or policy beyond what is needed for safe action-intent scaffolding
- work only on defining and preparing action-intent structures on top of the completed observe-only pipeline
- keep everything explicitly safety-first

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

Goals:
- define safe action-intent models without performing any real action
- represent things such as:
  - candidate selection intent
  - precondition requirements
  - target validation requirements
  - safety gating requirements
  - intent status / intent reason
- keep all intents non-executing and explicitly dry-run / scaffold only
- preserve observe-only safety while preparing for later dry-run and real safe action phases

Required work:
- add action-intent interfaces and implementation scaffolding
- define clean action-intent result models
- derive action intents only from already exposed/scored candidates and existing semantic metadata
- require explicit safety metadata and target validation fields
- preserve explicit safe failure behavior when candidate or semantic inputs are incomplete
- keep the implementation modular and testable
- do not add third-party runtime dependencies in this phase

Tests to add/update:
- successful candidate -> action-intent scaffold path
- safe handling of incomplete candidate/semantic inputs
- explicit non-executing behavior
- intent metadata consistency
- no unhandled exception propagation
- preservation of observe-only / non-executing semantics

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- include one read-only runtime smoke test if possible
- clearly separate:
  - actually executed checks
  - static reasoning only
  - environment-specific failures

Important:
- this phase is safe action-intent scaffolding only
- do not perform any click, keypress, or real OS action
- do not make anything executable yet
- keep the implementation tightly scoped to action-intent modeling and scaffolding

------faz2-----

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement Phase 5B: dry-run action engine.

Scope:
- do not add live input
- do not add real action execution
- do not expand planning or policy beyond what is needed for dry-run action evaluation
- work only on simulating the handling of the completed action-intent scaffolds
- keep everything strictly safety-first and non-executing

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

Goals:
- simulate how action intents would be processed without performing any real OS action
- produce dry-run results such as:
  - would_execute / would_block / incomplete / rejected
  - blocking reasons
  - missing preconditions
  - failed target validation
  - safety-gate outcomes
- preserve explicit non-executing behavior at all times
- improve downstream usefulness without adding real execution

Required work:
- add dry-run action engine interfaces and implementation
- define clean dry-run result models
- consume existing action-intent scaffolds and evaluate them without executing
- preserve explicit safe failure behavior when intent or semantic inputs are incomplete
- keep the implementation modular and testable
- do not add third-party runtime dependencies in this phase

Tests to add/update:
- successful dry-run evaluation path
- blocked intent path
- incomplete intent path
- target validation failure path
- no unhandled exception propagation
- preservation of non-executing semantics

Validation requirements:
- run the pre-delivery self-debug loop
- run compile/import/test validation
- include one read-only runtime smoke test if possible
- clearly separate:
  - actually executed checks
  - static reasoning only
  - environment-specific failures

Important:
- this phase is dry-run action evaluation only
- do not perform any click, keypress, or real OS action
- do not make anything executable yet
- keep the implementation tightly scoped to dry-run action handling