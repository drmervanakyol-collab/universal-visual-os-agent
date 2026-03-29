# Universal Visual OS-Agent Specification

## Goal
Build a Windows-first, Python 3.14-based Universal Visual OS-Agent that is:
- modular
- event-driven
- observe-only by default
- safety-first
- auditable
- recovery-capable
- testable in dry-run and replay modes

## Core Requirements
The system must:
- use normalized coordinates instead of fixed pixel coordinates
- support DPI-aware screen metrics
- separate vision, planning, memory, verification, policy, and action layers
- default to observe_only and dry_run modes
- support checkpoint persistence and recovery through SQLite
- support replay/testing without real OS actions
- include validation and self-debug checks before delivery

## Architecture Layers
1. Perceptual Layer
   - screen capture abstraction
   - frame diff abstraction
   - semantic candidate extraction interfaces

2. Semantic Understanding Layer
   - logical UI tree
   - candidate target model
   - visibility / enabled / occlusion estimates

3. Cognitive / Planning Layer
   - structured decision contract
   - planner abstraction
   - recovery planner abstraction

4. Memory Layer
   - temporal memory
   - layout history
   - failure memory
   - SQLite-backed checkpoints

5. Action Layer
   - action abstraction only at first
   - no real action execution by default
   - explicit feature flag required for any live action

6. Verification & Recovery Layer
   - post-action verification
   - retry / fallback / recovery flow
   - state reconciliation after restart

7. Safety, Policy & Audit Layer
   - allowlist / denylist
   - protected-context detection hooks
   - kill switch
   - pause / resume
   - audit logging

## Non-Goals
The system must not:
- implement anti-bot evasion
- implement stealth behavior
- automate protected contexts such as passwords, payments, security dialogs, or authentication workflows
- use unsafe real actions by default
- claim successful runtime validation without actually executing it

## Modes
The system must support:
- observe_only
- dry_run
- replay_mode
- recovery_mode
- safe_action_mode

Default mode must be `observe_only`.

## Coordinate Rules
- internal coordinates must be normalized in the range 0.0 to 1.0
- conversion helpers must exist for:
  - normalized_to_screen
  - screen_to_normalized
  - bbox_normalized_to_screen
  - dpi_aware_screen_metrics
- multi-monitor and high-DPI setups must be considered

## Persistence Rules
SQLite must be used for:
- task state
- subgoal/checkpoint state
- audit events
- recovery metadata

The system must persist enough state to resume safely after interruption.

## Validation Rules
Before code is presented:
- syntax and import issues must be checked
- interface consistency must be checked
- dry-run or replay validation should be preferred
- actual executed checks must be reported separately from static reasoning
- known risks must be listed honestly

## Initial Deliverables
The first implementation stages should produce:
- project skeleton under `src/`
- config models
- core interfaces and dataclasses
- mode system
- SQLite persistence skeleton
- coordinate helper functions
- policy engine skeleton
- asyncio orchestration skeleton
- tests for pure logic modules

## Implementation Style
- small modules
- clear interfaces
- type hints on public APIs
- safe defaults
- minimal hidden magic
- testable pure functions where possible

## Source of Truth
This file is the implementation specification unless explicitly updated.