---
name: sdd-tactical-contract
description: >-
  Guides Phase 3 Tactical DDD Modeling (Aggregates, Value Objects, Commands, Events,
  Ports, and Go SDD_STUB signatures) and Phase 4 Interface & Storage Contracts
  (OpenAPI 3.1, AsyncAPI 3.0, PostgreSQL DDL, and pre-implementation UAT Playbooks).
---

# SDD Tactical & Contract Skill (`P3` -> `P4`)

Use this skill after Gate G2 (`specs/features/*.feature` and Bridge 2.5b Pattern Selection) is locked.

## Phase 3: Tactical DDD Modeling (`P3_TACTICAL_DDD_STUBS_AND_PORTS`)

1. **1:1 Derivation from BDD Scenarios**:
   - Every `When` step in `specs/features/*.feature` maps to a **Command** struct (`internal/<module>/cmd/app/commands.go`).
   - Every `Given` / `Then` event step maps to a **Domain Event** struct (`internal/<module>/common/events.go`).
   - Every `Then` rejection step maps to a typed **Domain Error** sentinel (`internal/<module>/cmd/domain/errors.go`).
   - Monetary or precision quantities map to immutable **Value Objects** (e.g., `common.Cents` as `int64` minor units).
2. **Blueprint Contamination Guard**:
   - In `docs/architecture/ARCHITECTURE_BLUEPRINT.md`, include Mermaid diagrams, state tables, and mathematical proofs only. Any fenced ```go block over 15 lines will be blocked by the `PreToolUse` gatekeeper.
3. **Compile-Only `SDD_STUB` Signatures**:
   - If `selected_paradigm == "CQRS_EVENT_SOURCING"`, declare `AccountAggregate` with unexported fields (`balanceCents`, `active`) and **zero public balance getters**.
   - Every function or method body in `internal/**/*.go` during Phase 3 MUST be:
     ```go
     panic("SDD_STUB: implementation locked until Phase 5b")
     ```
   - Verify compilation via `go build ./...` before requesting Gate G3 promotion.

## Phase 4: Interface & Storage Contracts (`P4_INTERFACE_AND_STORAGE_CONTRACTS`)

Once Phase 3 Commands, Queries, Domain Events, and Errors are locked by Gate G3:
1. **OpenAPI 3.1 (`specs/openapi/*.yaml`)**:
   - Wrap stabilized Command and Query DTOs into synchronous REST endpoints, mapping Phase 3 domain errors to deterministic HTTP status codes (`400 Bad Request`, `409 Conflict`).
2. **AsyncAPI 3.0 (`specs/asyncapi/*.yaml`)**:
   - Formalize the Kafka channel (`bank-account-events`), partition key (`aggregate_id`), `cqrs.Envelope` event wrapper reference, and JSON Schemas for each Phase 3 Domain Event.
3. **PostgreSQL DDL (`migrations/write/*.sql` & `migrations/read/*.sql`)**:
   - Enforce `UNIQUE (aggregate_id, version)` on `event_store` and `processed_events`, partial index `WHERE published_at IS NULL` on `event_outbox`, and `BIGINT` minor units on `bank_accounts`.
4. **Pre-Implementation UAT Specification (`docs/uat/UAT_PLAYBOOK.md`)**:
   - Author the UAT Playbook directly from the locked OpenAPI + `.feature` contracts prior to Phase 5 implementation.
