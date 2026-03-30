# Next Steps

Archived planning snapshot. Active documentation entry points live in `docs/README.md`.

## Moving From Skeleton To Safe Integrations

- Finalize the safety contract for `safe_action_mode`, including explicit enable flags, operator confirmation boundaries, and failure downgrade behavior.
- Implement Windows-first perception adapters behind existing protocols:
  - DPI-aware screen metrics provider
  - screen capture provider
  - frame diff implementation
- Define a stable recorded replay format on disk so replay sessions can be loaded from files instead of only synthetic/in-memory data.
- Implement semantic rebuild logic that converts observed frames into `SemanticStateSnapshot` objects while preserving deterministic replay coverage.
- Add planner and recovery-planner implementations that consume semantic state and recovery snapshots through the existing contracts.
- Add a simulated action executor first, then only consider live execution behind strict config gating and policy approval.
- Expand protected-context detection from static hooks to real detectors for passwords, payments, authentication flows, and security dialogs.
- Integrate persistence and orchestration end-to-end so task state, checkpoints, audit events, and recovery decisions are emitted during real loop execution.
- Add migration/versioning policy for SQLite schema evolution before any non-trivial state is stored across releases.
- Add integration-test layers that keep live execution disabled by default:
  - replay-based end-to-end loop tests
  - recovery restart tests
  - policy-blocking integration tests
  - Windows adapter dry-run validation

## Non-Negotiables For Real Integrations

- keep live input disabled by default
- preserve kill switch, pause/resume, audit logging, and protected-context blocking in every live path
- keep OS-specific code behind protocol boundaries
- keep replay and deterministic validation as the primary test path
- do not add stealth, anti-bot, or protected-context automation
