---
name: sdd-bdd-architect
description: >-
  Guides Phase 0 Brownfield Parity Triage, Phase 1 Strategic DDD Context Mapping,
  and Phase 2 Multi-Round Socratic BDD Example Mapping, Event Modeling, and
  Bridge 2.5b Tactical Pattern Selection before any Tactical DDD or API contracts are written.
---

# SDD BDD Architect Skill (`P0` -> `P2`)

Use this skill when starting a brownfield rewrite, adding a new feature/module, defining Strategic DDD boundaries, or conducting Socratic BDD Example Mapping dialogues.

## Step 1: Phase 0 Brownfield Parity & Defect Triage (`specs/bdd/legacy-parity-triage.md`)
When modernizing an existing system, classify every legacy behavior into three buckets before writing scenarios:
1. **Bucket 1 — Canonical Wire Parity (Preserve)**: External URIs, HTTP status semantics, and DTO field names that must remain backward-compatible.
2. **Bucket 2 — Architectural & Domain Defects (Invert)**: Known vulnerabilities (e.g., Candidate A Dual-Write Split-Brain, Candidate B1/B2 Overdraft Race, Candidate C Non-Idempotent Replay, Defects D1–D4) that must be inverted into adversarial BDD scenarios.
3. **Bucket 3 — Net-New Capabilities (Extend)**: New business modules or features.

## Step 2: Phase 1 Strategic DDD (`docs/architecture/boundary-map.md` & `specs/ddd/arch-rules.yaml`)
1. Define the **Ubiquitous Language Glossary** separating Command-side terms from Query-side projections.
2. Classify **Subdomains** (`Core`, `Supporting`, `Generic`) and **Bounded Contexts** (`OHS`, `PL`, `SK`, `ACL`).
3. Lock package dependency rules in `specs/ddd/arch-rules.yaml`.

## Step 3: Phase 2 Multi-Round Socratic BDD Dialogue (`specs/bdd/example-map.md`)
The `PreToolUse` hook physically blocks writing `specs/features/*.feature` until `rounds_completed >= 2` and `unresolved_questions == []` in `.agents/state/phase-lock.json`.

1. **Round 1 (Rule & Happy-Path Alignment)**:
   - Write Rules (Yellow Cards), Canonical Examples (Green Cards), and open Edge-Case Questions (Red Cards) into `specs/bdd/example-map.md`.
   - Call `ask_question` to review Round 1 with the user and probe edge cases.
   - Record Round 1:
     ```powershell
     uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli record-dialogue --workspace <workspace> --questions "Q1: ..." "Q2: ..."
     ```
2. **Round 2 (Adversarial Edge-Case & Pattern Selection Interview)**:
   - Probe concurrency collisions (`400` retry vs. `409` fail-fast), out-of-order events (`ErrOutOfOrderEvent`), idempotency, and cross-aggregate Saga vs. single-aggregate boundaries.
   - Walk the user through the **Bridge 2.5b Tactical Pattern Selection Funnel**:
     * `CQRS_EVENT_SOURCING`: Core Subdomain with high read/write asymmetry and mandatory event audit/replay.
     * `STATE_BASED_OCC`: Core/Supporting Subdomain needing immediate Read-Your-Own-Writes ACID with `@Version` OCC.
     * `VERTICAL_SLICE_CRUD`: Supporting Subdomain with 1:1 CRUD symmetry (zero Aggregates/EventStore).
   - Once the user responds via `ask_question`, record Round 2 and lock the pattern:
     ```powershell
     uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli record-dialogue --workspace <workspace> --clear-questions
     uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli select-pattern --workspace <workspace> --paradigm CQRS_EVENT_SOURCING --scope SINGLE_AGGREGATE
     ```
3. **Round 3 (Declarative Gherkin Authoring — `specs/features/*.feature`)**:
   - With `rounds_completed >= 2` and `unresolved_questions == []`, write `specs/features/*.feature` using pure Ubiquitous Language (`Given` past events / `When` command / `Then` emitted events, invariant errors, or read-model projections).
   - Never include HTTP status codes, SQL queries, or Kafka topic names inside `.feature` files.
