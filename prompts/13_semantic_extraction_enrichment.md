Read AGENTS.md, docs/SPEC.md, and docs/EXECPLAN.md.

Implement a new integration phase: semantic extraction enrichment layer on top of the working full-desktop capture -> preparation -> state-building path.

Scope:
- do not add live input
- do not add action execution
- do not expand planning or policy
- work only on enriching semantic state construction from the existing preparation/state-building pipeline
- keep everything strictly observe-only and read-only

Goals:
- extend the current semantic state builder so it produces a richer semantic scaffold from successful full-desktop preparation inputs
- preserve safe structured failure behavior
- keep the implementation pure and testable
- prepare the pipeline for future OCR / detection / layout analysis, without adding those heavy integrations yet

Required work:
- enrich semantic layout/state outputs with clearer capture-surface semantics
- add region/block-style intermediate semantic structures if useful
- preserve consistent layout tree construction
- preserve non-actionable defaults unless explicitly justified
- keep metadata propagation clean and explicit
- do not add third-party runtime dependencies unless absolutely necessary; ask first if one is needed

Tests to add/update:
- successful preparation input -> enriched semantic state path
- consistency of layout tree / parent-child relations
- safe handling of missing payload or incomplete metadata
- candidate validity and non-actionable defaults
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
- use the working DXcam full-desktop capture + semantic preparation + state-building path as the primary integration target
- keep the implementation tightly scoped to semantic enrichment only
- do not silently convert observe-only semantic scaffolds into actionable candidates