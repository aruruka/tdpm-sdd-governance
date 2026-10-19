---
name: strict-audit
description: >-
  Stack- and paradigm-parameterized architectural audit skill. Dynamically adapts
  verification rules based on the module's language (go, python, typescript) and
  selected tactical paradigm (CQRS_EVENT_SOURCING, STATE_BASED_OCC, VERTICAL_SLICE_CRUD)
  in .agents/state/phase-lock.json.
---

# Parameterized Strict Architectural Audit (`strict-audit`)

Always read `<workspace>/.agents/state/phase-lock.json` first to determine the target module's `(language, selected_paradigm, current_phase)` before evaluating files. Return all findings in deterministic `file_path:line` order.

## 1. Go Stack (`language == "go"`)

### Paradigm A: `CQRS_EVENT_SOURCING` (Core Subdomain)
1. **Sealed Aggregate Encapsulation (Candidate B1/B2)**:
   - Aggregate structs (`internal/<module>/cmd/domain/*_aggregate.go`) must keep mutable state fields (`balanceCents`, `active`) unexported with **zero public balance getters** (`Balance()`, `GetBalance()`, `BalanceCents()`).
   - Command handlers (`internal/<module>/cmd/app/*.go`) must contain zero domain invariant branching.
2. **Zero Cross-Context Coupling**:
   - `internal/<module>/cmd/...` must never import `internal/<module>/query/...`, and vice versa.
3. **Transactional Outbox Atomicity (Candidate A)**:
   - `SaveEvents` in `internal/<module>/cmd/infra/postgres_store.go` must append to `event_store` and `event_outbox` inside a single `pgx.Tx` and enforce `UNIQUE (aggregate_id, version)` (`SQLSTATE 23505` -> `cqrs.ErrConcurrencyConflict`).
4. **Double-Barrier Read Idempotency (Candidate C & Defect D1)**:
   - `ProjectEvent` in `internal/<module>/query/infra/postgres_repo.go` must execute inside a single `pgx.Tx` enforcing Barrier 1 (`INSERT INTO processed_events ... ON CONFLICT (aggregate_id, version) DO NOTHING`) and Barrier 2 (`WHERE id = $3 AND last_version = $2 - 1`).
5. **Fixed-Point Monetary Core (Defect D2)**:
   - Internal domain and SQL schemas must use `int64` minor units (`common.Cents` / `BIGINT`), converting to `float64` only at JSON DTO serialization boundaries.
6. **Contract & Phase Compliance**:
   - In Phase 3, all non-test functions must be `panic("SDD_STUB: ...")`.
   - In Phases 4–5, HTTP routes and Kafka event structs must match `specs/openapi/*.yaml` and `specs/asyncapi/*.yaml` 1:1.

### Paradigm B: `STATE_BASED_OCC` (Core / Supporting Subdomain without Event Sourcing)
1. Verify relational updates enforce optimistic locking (`WHERE id = $1 AND version = $2`).
2. Flag any unnecessary `event_store` or replay machinery as scope creep.

### Paradigm C: `VERTICAL_SLICE_CRUD` (Supporting Subdomain — Ponytail Minimalism)
1. **Anti-Over-Engineering Gate**: Flag any Aggregate Root (`*_aggregate.go`), Mediator/CommandBus wrapper, or `event_outbox` table as a `PONYTAIL-OVERENGINEERING-BLOCK` error.
2. Verify direct, parameterized SQL queries (`pgx`) and clean request validation at the HTTP handler boundary.

## 2. Python & TypeScript Stacks (`language in ("python", "typescript")`)
1. Verify all external API and MCP tool boundaries parse inputs via strict **Pydantic v2** (`ConfigDict(extra="forbid")`) or **Zod** schemas.
2. Flag any bare `try/except:` blocks, unparameterized SQL string interpolation, or mutable default arguments.
