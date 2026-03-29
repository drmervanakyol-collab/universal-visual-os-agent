# EXECPLAN.md

## Objective
Implement the Universal Visual OS-Agent incrementally from `docs/SPEC.md`.

## Phase 0 - Planning and compatibility
- Inventory Python 3.14 package risks
- Produce compatibility matrix
- Propose fallback packages where needed
- Define initial repo structure

## Phase 1 - Core skeleton
- Create package layout under `src/`
- Define config, models, interfaces, logging, modes
- Add observe_only and dry_run foundations

## Phase 2 - State, memory, and recovery
- SQLite schemas
- checkpoint manager
- task/subgoal persistence
- recovery state reconciliation

## Phase 3 - Coordinate and screen abstractions
- DPI-aware metrics
- normalized coordinate transforms
- multi-monitor-safe abstractions

## Phase 4 - Semantic state pipeline
- layout tree models
- candidate target contract
- verification contract

## Phase 5 - Policy and safety
- policy engine
- allowlist/denylist
- protected-context detection interfaces
- kill switch / pause / resume

## Phase 6 - Event-driven main loop
- asyncio orchestration
- queue/cancellation/timeouts
- dry-run execution flow

## Phase 7 - Validation
- replay harness
- unit tests
- validation report template

## Constraints
- No full live-action agent by default
- No stealth/evasion logic
- Prefer modular and testable code
- Record all assumptions