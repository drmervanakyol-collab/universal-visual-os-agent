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

Read `AGENTS.md`, `docs/SPEC.md`, and `docs/EXECPLAN.md`.

Implement Phase 6B: observe -> understand -> verify scenario loop.

Scope:
- do not add new live input types
- do not perform real OS actions
- do not expand beyond observe/understand/verify flow
- work only on wiring the completed capture/semantics/verification/scenario-definition layers into a scenario-level loop
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
- dry-run action engine
- minimal safe click prototype
- scenario definition layer

Goals:
- implement a scenario-level loop for:
  - observe
  - understand
  - verify
- allow a scenario definition to be evaluated against the current pipeline without executing real OS actions
- produce structured scenario-run results such as:
  - step started
  - step observed
  - step understood
  - step verified
  - step incomplete
  - step failed
- preserve explicit safe failure behavior when capture/semantic/verification inputs are incomplete
- keep everything modular and testable

Required work:
- add scenario loop interfaces and implementation
- define clean scenario-run result models
- connect existing capture -> semantics -> verification outputs to scenario steps
- support dry-run-only scenario steps
- preserve explicit safety and non-executing semantics
- do not add third-party runtime dependencies in this phase

Tests to add/update:
- successful observe->understand->verify scenario path
- incomplete scenario step path
- failed verification path
- metadata/result consistency
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
- this phase is observe->understand->verify scenario flow only
- do not perform real clicks or keyboard input
- do not broaden into full end-to-end execution yet
- keep the implementation tightly scoped to non-executing scenario loop behavior

-------faz3-------

Implemented Phase 6B as a non-executing scenario runner in loop.py, with the real observe-understand wiring in loop.py. It now runs each scenario step through capture, semantic preparation/state/OCR/layout/candidate scoring/exposure, then verifies the step against a semantic transition without performing any OS action. I also added explicit scenario-run contracts in models.py, models.py, models.py, and models.py, plus the public loop protocol in interfaces.py.

A notable detail is the first-step verification behavior: when there is no prior snapshot, the runner now uses an explicit synthetic empty baseline at loop.py so delta-based appeared / disappeared expectations can resolve deterministically instead of staying unknown. That stays transparent through step metadata, and the whole loop remains observe-only, non-executing, and live_execution_attempted=False.

Focused coverage is in test_scenario_loop.py, test_scenario_loop.py, test_scenario_loop.py, test_scenario_loop.py, test_scenario_loop.py, and test_scenario_loop.py.

Validation:

Actually executed:
python -m compileall src tests
python -m pytest -q tests/test_scenario_loop.py tests/test_scenario_definition.py tests/test_action_intent_scaffolding.py tests/test_dry_run_action_engine.py tests/test_safe_click_prototype.py tests/test_goal_oriented_verification.py -p no:cacheprovider -> 37 passed
Read-only smoke run -> success=True, run_status='completed', signal_status='available', step_final_stage='verified', synthetic_before_snapshot=True, live_execution_attempted=False
Static reasoning only:
I did not wire this scenario runner into the async main-loop/orchestration layer yet.
I kept Phase 6B strictly to observe-understand-verify; it does not execute dry-run actions or real clicks inside the scenario flow.
Environment-specific failures:
None

5 dosya değiştirildi
+1247
-1
Geri Al

__init__.py
interfaces.py
loop.py
models.py
test_scenario_loop.py
