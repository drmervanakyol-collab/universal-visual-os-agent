# Universal Visual OS-Agent

Windows-first, Python 3.14 tabanlı, güvenli, modüler ve test edilebilir bir görsel OS-agent iskeleti.

## Current project status
This repository is in the architecture and scaffolding phase.

## Safety defaults
- observe_only by default
- no real live input by default
- dry_run and replay-first validation
- protected contexts must not be automated

## Source of truth
- `docs/SPEC.md`
- `docs/EXECPLAN.md`
- `AGENTS.md`

## Initial development workflow
1. plan first
2. build small modules
3. validate before delivery
4. prefer dry-run and replay over live actions

## Planned implementation phases
See `docs/EXECPLAN.md`.

## Notes
This repository is intended for safe, auditable desktop automation and accessibility-oriented experimentation.