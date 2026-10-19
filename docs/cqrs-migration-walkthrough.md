# End-to-End Walkthrough: Migrating a Legacy Service to Event-Driven CQRS

This tutorial demonstrates how `tdpm-sdd-governance` governs a realistic brownfield architectural rewrite: migrating a synchronous, defect-prone legacy account service (`legacy-service/`) into an event-sourced Go + PostgreSQL 16 + Kafka CQRS service (`modern-service/`), alongside a supporting CRUD profile module.

---

## Scenario Overview

Suppose your team is replacing `legacy-service/` (a synchronous monolithic banking service) with `modern-service/`. An initial audit of `legacy-service/` uncovered three critical architectural defects:

1. **Candidate A (Dual-Write Split-Brain)**: The legacy service updates the SQL table and publishes to Kafka in two separate non-transactional steps, dropping events when the broker times out.
2. **Candidate B1/B2 (Overdraft Race & Leaky Aggregate State)**: The legacy service reads `account.getBalance()` in the application layer and performs an unguarded `UPDATE`, allowing concurrent withdrawals to overdraw the account.
3. **Candidate C / Defect D1 & D2 (Non-Idempotent Read Replay & Floating-Point Drift)**: Duplicate Kafka deliveries double-credit the read projection, and `float64` arithmetic introduces sub-cent rounding errors.

Below is the exact phase-by-phase workflow executed by you (the Architect) and the plugin's subagents (`@td-pm`, `@pm-planner`, `@td-auditor`, and `@sdk-architect`).

---

## Phase 0: Brownfield Discovery & Defect Triage (`P0`)

### 1. Initialize the Workspace at Phase 0

```bash
export PLUGIN_HOME="$HOME/.gemini/config/plugins/tdpm-sdd-governance"

uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli init \
  --workspace ./modern-service \
  --project-name "github.com/acme-financial/account-platform" \
  --module "account" \
  --language go \
  --phase 0
```

At this point, `current_phase` is `0` (`P0_BROWNFIELD_DISCOVERY_AND_TRIAGE`) and `active_owner` is `@pm-planner`. If an agent attempts to write any `.go`, `.feature`, `.yaml`, or `.sql` file now, `PreToolUse` immediately blocks the call.

### 2. Delegate Triage to `@pm-planner`

`@pm-planner` activates the `sdd-bdd-architect` skill, inspects the baseline reports (`docs/architecture/LEGACY_DEPLOYMENT_REPORT.md` and `docs/architecture/ARCHITECTURAL_VERIFICATION_REPORT.md`), and writes `specs/bdd/legacy-parity-triage.md`:

```markdown
# Brownfield Parity & Defect Triage (`account`)

## Bucket 1 — Canonical Wire Parity (Preserve)
- Preserve `POST /api/v1/accounts` request/response JSON field names (`holder_name`, `initial_balance`).
- Preserve `POST /api/v1/accounts/{id}/withdraw` and `GET /api/v1/accounts/{id}` URIs.

## Bucket 2 — Architectural & Domain Defects (Invert into Adversarial BDD Scenarios)
- **Candidate A (Dual-Write Split-Brain)**: Invert into atomic Transactional Outbox requirement.
- **Candidate B1/B2 (Overdraft Race)**: Seal Aggregate state; ban public balance getters; enforce `UNIQUE (aggregate_id, version)` optimistic concurrency control.
- **Candidate C & Defect D1 (Non-Idempotent Replay)**: Enforce Double-Barrier Read Idempotency (`processed_events` deduplication + `last_version = version - 1` sequence check).
- **Defect D2 (Floating-Point Currency)**: Replace internal `float64` with `int64` minor units (`common.Cents`).

## Bucket 3 — Net-New Capabilities (Extend)
- Add idempotent command deduplication and dead-letter outbox relay metrics.
```

### 3. Verify & Promote Gate `G0` $\rightarrow$ Phase 1

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace ./modern-service
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace ./modern-service \
  --lock-files "specs/bdd/legacy-parity-triage.md"
```

---

## Phase 1: Strategic DDD & Context Map (`P1`)

### 1. Define Ubiquitous Language & Bounded Contexts

`@pm-planner` and `@td-auditor` collaborate to author:
1. `docs/architecture/boundary-map.md`:
   - **Ubiquitous Language Glossary**: Separates Command-side concepts (`OpenAccount`, `WithdrawFunds`, `AccountAggregate`, `Cents`) from Query-side concepts (`AccountProjection`, `GetAccountByID`).
   - **Subdomain Classification**: Classifies `account` as a **Core Subdomain** and `profile` as a **Supporting Subdomain**.
   - **Context Map**: Declares `cmd` (Write Context) and `query` (Read Context) connected strictly via an asynchronous Published Language (`PL`) event stream (`cqrs.Envelope`) with zero cross-context Go imports.
2. `specs/ddd/arch-rules.yaml`: Declares package dependency constraints.
3. `docs/architecture/ARCHITECTURE_BLUEPRINT.md`: Documents the Hexagonal topology using Mermaid diagrams and state tables.

> **Guardrail in Action**: If `@td-auditor` tries to paste a 25-line Go implementation snippet into `docs/architecture/ARCHITECTURE_BLUEPRINT.md`, the `PreToolUse` hook denies the write with `SDD-BLUEPRINT-NO-CODE-DUMP` (maximum allowed is 15 non-empty lines for interface signatures).

### 2. Verify & Promote Gate `G1` $\rightarrow$ Phase 2

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace ./modern-service
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace ./modern-service \
  --lock-files "docs/architecture/boundary-map.md" "specs/ddd/arch-rules.yaml"
```

---

## Phase 2: Socratic BDD Dialogue & Bridge 2.5b Pattern Gate (`P2`)

In Phase 2, `PreToolUse` physically blocks creating `specs/features/*.feature` until at least 2 Socratic dialogue rounds are recorded and all open edge-case questions are cleared.

### 1. Socratic Dialogue Round 1 (Rules, Happy Paths, and Red Question Cards)

`@pm-planner` creates `specs/bdd/example-map.md` containing Yellow Cards (Domain Rules), Green Cards (Examples), and Red Cards (Open Edge-Case Questions), then invokes `ask_question` to interview you.

`@pm-planner` records Round 1 in the state ledger:

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli record-dialogue \
  --workspace ./modern-service \
  --questions \
    "Q1: When two concurrent WithdrawFunds commands collide on version N, should the command handler retry automatically or return a concurrency conflict?" \
    "Q2: How should the read projection behave if event version 3 arrives before version 2?"
```

### 2. Socratic Dialogue Round 2 & Bridge 2.5b Pattern Selection

You respond via `ask_question`:
- **Q1 Decision**: Fail fast on command-side optimistic concurrency conflict so the caller controls idempotency/retries.
- **Q2 Decision**: Reject out-of-order events (`ErrOutOfOrderEvent`) via Barrier 2 (`WHERE id = $3 AND last_version = $2 - 1`) so the consumer retries in sequence.
- **Bridge 2.5b Pattern Decision**: Select `CQRS_EVENT_SOURCING` with `SINGLE_AGGREGATE` scope for `account`.

`@pm-planner` and `@td-auditor` update `specs/bdd/example-map.md` and `specs/bdd/event-modeling-and-pattern-gate.md`, then record Round 2 and lock the pattern:

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli record-dialogue \
  --workspace ./modern-service \
  --clear-questions

uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli select-pattern \
  --workspace ./modern-service \
  --paradigm CQRS_EVENT_SOURCING \
  --scope SINGLE_AGGREGATE
```

### 3. Author Declarative Gherkin (`specs/features/account.feature`)

With `rounds_completed == 2` and `unresolved_questions == []`, `@pm-planner` writes `specs/features/account.feature` in pure Ubiquitous Language:

```gherkin
Feature: Bank Account Lifecycle and Overdraft Prevention

  Scenario: Withdraw funds within available balance
    Given an opened account "acc-100" with initial balance of 10000 cents at version 1
    When the WithdrawFunds command is dispatched for account "acc-100" with 4000 cents at expected version 1
    Then the FundsWithdrawnEvent is emitted for account "acc-100" with amount 4000 cents at version 2

  Scenario: Reject withdrawal exceeding available balance (Candidate B1/B2 Inversion)
    Given an opened account "acc-100" with initial balance of 3000 cents at version 1
    When the WithdrawFunds command is dispatched for account "acc-100" with 5000 cents at expected version 1
    Then the command is rejected with domain error ErrInsufficientFunds
```

> **Guardrail in Action**: If a scenario includes `Then HTTP 400 is returned` or `INSERT INTO bank_accounts`, `PreToolUse` denies the write with `BDD-TRANSPORT-LEAKAGE`.

### 4. Verify & Promote Gate `G2` $\rightarrow$ Phase 3

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace ./modern-service
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace ./modern-service \
  --lock-files "specs/bdd/*.md" "specs/features/*.feature"
```

---

## Phase 3: Tactical DDD Stubs & Ports (`P3`)

Now `@td-auditor` takes ownership (`active_owner: "td-auditor"`), activates `sdd-tactical-contract`, and derives the Go domain model 1:1 from `specs/features/account.feature`.

### 1. Author Compile-Only `SDD_STUB` Go Files

`@td-auditor` creates `internal/account/cmd/domain/account_aggregate.go`:

```go
package domain

import "github.com/acme-financial/account-platform/internal/account/common"

type AccountAggregate struct {
	id           string
	balanceCents common.Cents
	active       bool
	version      int64
}

func NewAccountAggregate(id string) *AccountAggregate {
	panic("SDD_STUB: implementation locked until Phase 5b")
}

func (a *AccountAggregate) Withdraw(amount common.Cents) (common.FundsWithdrawnEvent, error) {
	panic("SDD_STUB: implementation locked until Phase 5b")
}
```

> **Guardrails in Action**:
> - If `@td-auditor` writes `func (a *AccountAggregate) GetBalance() common.Cents`, `PreToolUse` denies it with `DDD-SEALED-AGGREGATE-GETTER` (Candidate B1 encapsulation).
> - If `@td-auditor` writes real implementation logic instead of `panic("SDD_STUB: ...")`, `PreToolUse` denies it with `SDD-P3-STUB-ONLY`.
> - If `@td-auditor` tries to write `account_test.go` in Phase 3, `PreToolUse` denies it (`Executable '*_test.go' harnesses belong to Phase 5a`).
> - If you also added a `profile` module governed by `VERTICAL_SLICE_CRUD`, attempting to create `internal/profile/domain/profile_aggregate.go` is denied with `PONYTAIL-OVERENGINEERING-BLOCK`.

### 2. Verify & Promote Gate `G3` $\rightarrow$ Phase 4

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace ./modern-service
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace ./modern-service \
  --lock-files "specs/ddd/tactical-*.md" "docs/architecture/ARCHITECTURE_BLUEPRINT.md"
```

---

## Phase 4: Interface & Storage Contracts (`P4`)

In Phase 4, all `.go` files are frozen. `@td-auditor` and `@pm-planner` formalize external contracts from the stabilized Phase 3 types:

1. **OpenAPI 3.1 (`specs/openapi/account.v1.yaml`)**: Maps `OpenAccountCommand`, `WithdrawFundsCommand`, and `GetAccountQuery` to REST endpoints and maps `ErrInsufficientFunds` / `ErrConcurrencyConflict` to deterministic HTTP status codes.
2. **AsyncAPI 3.0 (`specs/asyncapi/account-events.v1.yaml`)**: Defines the `bank-account-events` channel, partition key (`aggregate_id`), and event payload schemas.
3. **PostgreSQL 16 DDL (`migrations/write/001_event_store.sql` & `migrations/read/001_projections.sql`)**:
   - Write store: `event_store` with `UNIQUE (aggregate_id, version)` and `event_outbox` with partial index `WHERE published_at IS NULL`.
   - Read store: `processed_events` with `PRIMARY KEY (aggregate_id, version)` and `bank_accounts` using `BIGINT` minor units.
4. **Pre-Implementation UAT Playbook (`docs/uat/UAT_PLAYBOOK.md`)**: Authored by `@pm-planner`.

### Verify & Promote Gate `G4` $\rightarrow$ Phase 5 (`5a_RED_HARNESS`)

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace ./modern-service
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace ./modern-service \
  --lock-files "specs/openapi/*.yaml" "specs/asyncapi/*.yaml" "migrations/**/*.sql" "docs/uat/UAT_PLAYBOOK.md"
```

---

## Phase 5: Red-Green-Verify Implementation (`P5`)

### Sub-Phase `5a_RED_HARNESS`: Compile & Fail Against Stubs

In `5a_RED_HARNESS`, `PreToolUse` allows writing `*_test.go` files while keeping production `.go` files locked.

1. `@td-auditor` writes domain unit tests (`internal/account/cmd/domain/account_test.go`) and BDD acceptance harnesses (`test/verification/bdd_account_test.go`).
2. Verify test compilation and Red failure against `SDD_STUB`:
   ```bash
   go test -c ./...                        # Must exit 0 (compiles cleanly)
   go test ./internal/account/...          # Must exit != 0 (panics on SDD_STUB)
   ```
3. Lock the test harnesses and promote to `5b_GREEN_IMPL`:
   ```bash
   uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace ./modern-service \
     --lock-files "internal/account/**/*_test.go" "test/verification/*_test.go"
   ```

### Sub-Phase `5b_GREEN_IMPL`: Inside-Out Production Implementation

Now `PreToolUse` unlocks non-test `.go` files while protecting all locked specifications, contracts, and `*_test.go` files with SHA-256 lock checks.

`@td-auditor` replaces `panic("SDD_STUB")` bodies inside-out:
1. **Domain Layer**: `AccountAggregate` command methods and event `Apply` state transitions using `common.Cents` (`int64`).
2. **Write Infrastructure**: `PostgresEventStore.SaveEvents` appending to `event_store` and `event_outbox` inside a single `pgx.Tx`.
3. **Read Infrastructure**: `PostgresReadRepository.ProjectEvent` enforcing Barrier 1 (`INSERT INTO processed_events ... ON CONFLICT DO NOTHING`) and Barrier 2 (`UPDATE bank_accounts ... WHERE id = $3 AND last_version = $2 - 1`).
4. **HTTP Routers**: Wiring OpenAPI-compliant handlers.

Once all tests pass (`go test -race ./...`), promote to `5c_VERIFICATION`:

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace ./modern-service
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace ./modern-service \
  --lock-files "internal/account/**/*.go"
```

### Sub-Phase `5c_VERIFICATION`: Chaos Testing, Deep SDK Audit & Cutover Report

1. `@td-auditor` executes Testcontainers + Toxiproxy network partition tests and benchmark suites, publishing `docs/architecture/CUTOVER_AND_BENCHMARK_REPORT.md`.
2. `@td-pm` delegates a final read-only audit to `@sdk-architect` (`run_sdk_verification_pipeline` with `focus_area="full_gate"`), verifying 100% SHA-256 lock integrity across all Phase 0–5 artifacts.
