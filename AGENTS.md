# AGENTS.md

## Repository mission
Build a safe, modular, testable Windows-first Universal Visual OS-Agent from `docs/SPEC.md`.

## Required reading before any change
- Read `docs/SPEC.md`
- Read `docs/EXECPLAN.md` if it exists
- Do not start coding until you have summarized the relevant scope

## Working style
- Prefer plan-first for complex tasks
- Keep changes small and phase-based
- Do not implement the whole system in one pass
- Default to observe-only and dry-run behavior
- Never add stealth, evasion, anti-bot, or protected-context automation

## Source of truth
- Architecture and requirements live in `docs/SPEC.md`
- If code conflicts with spec, follow spec unless the spec is technically impossible; in that case, document the conflict before changing code

## Coding standards
- Python 3.14 syntax only
- Full type hints on public interfaces
- Small modules, no giant files
- Prefer dataclasses / protocols / clear interfaces
- Separate pure logic from OS integration
- Avoid hard-coded coordinates, timings, and magic numbers

## Safety rules
- No real input execution by default
- Real actions must stay behind explicit config flags
- Respect policy engine and protected-context detection
- Always preserve kill switch, pause/resume, and audit logging hooks

## Validation rules
Before presenting code:
1. Run a self-check pass
2. Identify syntax/import/interface issues
3. Fix obvious errors first
4. Report what was actually validated vs only reasoned about
5. Never claim runtime success without actually running tests

## Testing expectations
- Add or update tests when adding non-trivial logic
- Prioritize:
  - coordinate transforms
  - state models
  - checkpoint persistence
  - planner contracts
  - verification logic
- Prefer replay/dry-run tests over unsafe live-action tests

## Done when
A task is done only when:
- requested code is implemented
- related tests or validation artifacts are added/updated
- assumptions and risks are documented
- no contradiction with `docs/SPEC.md` remains unexplained