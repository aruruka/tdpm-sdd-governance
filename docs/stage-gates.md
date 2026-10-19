# Stage-Gates & Lifecycle Reference (`P0` $\rightarrow$ `P5`)

`tdpm-sdd-governance` models software delivery as a deterministic, 6-phase finite state machine backed by `<workspace>/.agents/state/phase-lock.json`. Every phase has an explicit **Active Owner Persona**, **Allowed/Blocked File Mutations**, **Static Audit Rules**, and a **Cryptographic Promotion Gate (`G0`–`G5`)**.

---

## 1. End-to-End State Machine Overview

```text
+---------------------------------------------------------------------------------------------------+
|                             P0: P0_BROWNFIELD_DISCOVERY_AND_TRIAGE                                |
|  Owner: @pm-planner  |  Skill: sdd-bdd-architect                                                  |
|  Outputs: docs/architecture/LEGACY_DEPLOYMENT_REPORT.md, ARCHITECTURAL_VERIFICATION_REPORT.md,    |
|           specs/bdd/legacy-parity-triage.md                                                       |
|  Blocked: *.feature, *.go, specs/openapi/*.yaml, specs/asyncapi/*.yaml, migrations/*.sql          |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                         [ Gate G0 Promotion ]
                                                  v
+---------------------------------------------------------------------------------------------------+
|                             P1: P1_STRATEGIC_DDD_AND_CONTEXT_MAP                                  |
|  Owner: @pm-planner + @td-auditor  |  Skill: sdd-bdd-architect                                    |
|  Outputs: docs/architecture/boundary-map.md, specs/ddd/arch-rules.yaml, ARCHITECTURE_BLUEPRINT.md |
|  Guard:   ARCHITECTURE_BLUEPRINT.md Go code blocks must be <= 15 non-empty lines                  |
|  Blocked: *.feature, *.go, specs/openapi/*.yaml, specs/asyncapi/*.yaml, migrations/*.sql          |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                           [ Gate G1: verify-gate + promote-phase (SHA-256) ]
                                                  v
+---------------------------------------------------------------------------------------------------+
|                             P2: P2_ITERATIVE_BDD_AND_PATTERN_GATE                                 |
|  Owner: @pm-planner (BDD) + @td-auditor (Bridge 2.5b)  |  Skill: sdd-bdd-architect                |
|  Step 2a: >= 2 Socratic Dialogue rounds via ask_question (`record-dialogue`) in example-map.md    |
|  Step 2b: Bridge 2.5a/2.5b Pattern Gate (`select-pattern`: CQRS_EVENT_SOURCING | STATE_BASED_OCC  |
|           | VERTICAL_SLICE_CRUD) in specs/bdd/event-modeling-and-pattern-gate.md                  |
|  Step 2c: Author pure Gherkin `specs/features/*.feature` (unlocked only after Step 2a clears Qs)  |
|  Blocked: *.go, specs/openapi/*.yaml, specs/asyncapi/*.yaml, migrations/*.sql                     |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                           [ Gate G2: verify-gate + promote-phase (SHA-256) ]
                                                  v
+---------------------------------------------------------------------------------------------------+
|                             P3: P3_TACTICAL_DDD_STUBS_AND_PORTS                                   |
|  Owner: @td-auditor  |  Skill: sdd-tactical-contract, strict-audit                                |
|  Outputs: specs/ddd/tactical-model-spec.md, internal/<module>/**/*.go (non-test files only)       |
|  Guards:  - Every Go function body MUST be single-line `panic("SDD_STUB: ...")`                   |
|           - CQRS_EVENT_SOURCING: zero public balance getters (`GetBalance`, `Balance`, etc.)      |
|           - VERTICAL_SLICE_CRUD: zero `aggregate`, `event_store`, `outbox_relay`, `command_bus`   |
|  Blocked: *_test.go, specs/openapi/*.yaml, specs/asyncapi/*.yaml, migrations/*.sql                |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                           [ Gate G3: verify-gate + promote-phase (SHA-256) ]
                                                  v
+---------------------------------------------------------------------------------------------------+
|                             P4: P4_INTERFACE_AND_STORAGE_CONTRACTS                                |
|  Owner: @td-auditor (Contracts) + @pm-planner (UAT)  |  Skill: sdd-tactical-contract              |
|  Outputs: specs/openapi/*.yaml (3.x), specs/asyncapi/*.yaml (2.x/3.x), migrations/**/*.sql,       |
|           docs/uat/UAT_PLAYBOOK.md                                                                |
|  Blocked: All *.go files (both production and *_test.go)                                          |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                           [ Gate G4: verify-gate + promote-phase (SHA-256) ]
                                                  v
+---------------------------------------------------------------------------------------------------+
|                             P5: P5_IMPLEMENTATION_AND_VERIFICATION                                |
|  Owner: @td-auditor  |  Skills: sdd-cqrs-gate, strict-audit                                       |
|                                                                                                   |
|  +-- Sub-Phase 5a: 5a_RED_HARNESS -------------------------------------------------------------+  |
|  |   Allowed: *_test.go ONLY (production *.go remains blocked!)                                |  |
|  |   Gate G5a: `go test -c ./...` == 0 AND `go test ./internal/<module>/...` != 0 (Red fail)   |  |
|  +----------------------------------------------+----------------------------------------------+  |
|                                                 | [ promote-phase locks *_test.go ]               |
|                                                 v                                                 |
|  +-- Sub-Phase 5b: 5b_GREEN_IMPL --------------------------------------------------------------+  |
|  |   Allowed: Production *.go implementation (Domain -> Write App/Infra -> Read -> Routers)    |  |
|  |   Guard:   Locked Phase 1-5a specs, contracts, and *_test.go cannot be mutated              |  |
|  +----------------------------------------------+----------------------------------------------+  |
|                                                 | [ promote-phase advances to 5c ]                |
|                                                 v                                                 |
|  +-- Sub-Phase 5c: 5c_VERIFICATION ------------------------------------------------------------+  |
|  |   Outputs: Concurrency/Chaos verification & docs/architecture/CUTOVER_AND_BENCHMARK_REPORT.md| |
|  +---------------------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Human vs. Autonomous Agent Responsibility Matrix

| Lifecycle Stage | Human Developer / Architect Responsibilities | Autonomous Agent (`@td-pm`, `@pm-planner`, `@td-auditor`, `@sdk-architect`) Responsibilities |
| :--- | :--- | :--- |
| **Phase 0 (`P0`)** | Confirm which legacy quirks are mandatory wire-level parity vs. bugs to remediate. | Inspect legacy code/deployment reports; categorize behaviors into Buckets 1, 2, and 3 in `specs/bdd/legacy-parity-triage.md`. |
| **Phase 1 (`P1`)** | Review Bounded Context boundaries and Ubiquitous Language terminology. | Draft `docs/architecture/boundary-map.md`, `specs/ddd/arch-rules.yaml`, and high-level `ARCHITECTURE_BLUEPRINT.md`. |
| **Phase 2 (`P2`)** | Answer $\ge 2$ rounds of Socratic Example Mapping questions (`ask_question`) and approve Bridge 2.5b Pattern Selection. | Formulate Yellow/Green/Red cards in `specs/bdd/example-map.md`, log dialogue rounds via CLI, run Bridge 2.5b funnel, and author pure `.feature` files. |
| **Phase 3 (`P3`)** | Review Tactical DDD Aggregate boundaries, Value Objects, and Port interfaces. | Generate 1:1 BDD-derived Go types with `panic("SDD_STUB: ...")` bodies and verify `go build ./...`. |
| **Phase 4 (`P4`)** | Review external REST/Event schemas, SQL DDL indexes/constraints, and UAT acceptance criteria. | Generate OpenAPI 3.1, AsyncAPI 3.0, PostgreSQL DDL migrations, and `docs/uat/UAT_PLAYBOOK.md`. |
| **Phase 5 (`P5`)** | Authorize transitions from `5a_RED_HARNESS` $\rightarrow$ `5b_GREEN_IMPL` $\rightarrow$ `5c_VERIFICATION`. | Write failing tests (`5a`), implement inside-out production logic (`5b`), run chaos/benchmark suites (`5c`), and verify zero lock drift. |

---

## 3. Detailed Phase Specifications & Gate Criteria

### Phase 0: `P0_BROWNFIELD_DISCOVERY_AND_TRIAGE`

- **Phase Index**: `0`
- **Default Active Owner**: `pm-planner`
- **Primary Skill**: `sdd-bdd-architect`
- **Purpose**: Prevent blind translation of legacy bugs into a modern architecture during a brownfield rewrite.
- **Inputs**:
  - Legacy codebase or deployment/verification baselines (`docs/architecture/LEGACY_DEPLOYMENT_REPORT.md`, `docs/architecture/ARCHITECTURAL_VERIFICATION_REPORT.md`)
- **Required Outputs**:
  - `specs/bdd/legacy-parity-triage.md` classifying every legacy behavior into:
    1. **Bucket 1 — Canonical Wire Parity (Preserve)**: External URIs, HTTP status semantics, and DTO field names that must remain backward-compatible.
    2. **Bucket 2 — Architectural & Domain Defects (Invert/Remediate)**: Known race conditions, dual-write split-brains, or floating-point rounding bugs that must be inverted into adversarial BDD scenarios.
    3. **Bucket 3 — Net-New Capabilities (Extend)**: Net-new business modules or endpoints.
- **`PreToolUse` Enforcement**:
  - Denies writing `.feature` files (`SDD SEQUENCE BLOCK`).
  - Denies writing `.go` files (`SDD SEQUENCE BLOCK`).
  - Denies writing `specs/openapi/*`, `specs/asyncapi/*`, or `migrations/*.sql` (`SDD SEQUENCE BLOCK`).
  - Denies Go code blocks $> 15$ non-empty lines in `ARCHITECTURE_BLUEPRINT.md` (`SDD-BLUEPRINT-NO-CODE-DUMP`).
- **Promotion Command (`G0` $\rightarrow$ `P1`)**:
  ```bash
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace <workspace>
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace <workspace> \
    --lock-files "specs/bdd/legacy-parity-triage.md"
  ```

---

### Phase 1: `P1_STRATEGIC_DDD_AND_CONTEXT_MAP`

- **Phase Index**: `1`
- **Default Active Owner**: `pm-planner` (co-owned with `td-auditor` for topology/DAG rules)
- **Primary Skill**: `sdd-bdd-architect`
- **Purpose**: Establish the Ubiquitous Language Glossary, Subdomain classifications, and Bounded Context integration boundaries before writing behavioral scenarios.
- **Required Outputs**:
  - `docs/architecture/boundary-map.md`:
    - Ubiquitous Language Glossary (explicitly separating Command-side verbs/nouns from Query-side read projections)
    - Subdomain classifications (`Core`, `Supporting`, `Generic`)
    - Context Mapping integration relationships (`OHS` Open Host Service, `PL` Published Language, `SK` Shared Kernel, `ACL` Anti-Corruption Layer)
  - `specs/ddd/arch-rules.yaml`: Package dependency DAG and context isolation rules.
  - `docs/architecture/ARCHITECTURE_BLUEPRINT.md` *(optional in P1, audited if present)*: High-level Mermaid diagrams, state tables, and invariants.
- **Deterministic Gate Checks (`G1`)**:
  - `G1-MISSING-BOUNDARY-MAP`: `docs/architecture/boundary-map.md` must exist on disk.
  - `SDD-BLUEPRINT-NO-CODE-DUMP`: Any ` ```go ... ``` ` block in `docs/architecture/ARCHITECTURE_BLUEPRINT.md` must have $\le 15$ non-empty lines.
- **Promotion Command (`G1` $\rightarrow$ `P2`)**:
  ```bash
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace <workspace>
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace <workspace> \
    --lock-files "docs/architecture/boundary-map.md" "specs/ddd/arch-rules.yaml"
  ```

---

### Phase 2: `P2_ITERATIVE_BDD_AND_PATTERN_GATE`

- **Phase Index**: `2`
- **Default Active Owner**: `pm-planner` (BDD scenarios) + `td-auditor` (Bridge 2.5b Pattern Gate)
- **Primary Skill**: `sdd-bdd-architect`
- **Purpose**: Force edge cases, concurrency collisions, and failure modes out into the open through multi-round Socratic dialogue with the human user, select the right-sized tactical architecture pattern, and author pure Gherkin specifications.
- **Three-Step Execution Protocol**:
  1. **Socratic Example Mapping ($\ge 2$ Rounds in `specs/bdd/example-map.md`)**:
     - **Round 1**: Draft Rules (Yellow Cards), Canonical Happy-Path Examples (Green Cards), and open Edge-Case Questions (Red Cards). Present to the user via `ask_question`, then record Round 1:
       ```bash
       uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli record-dialogue \
         --workspace <workspace> \
         --questions "Q1: Should concurrent version conflicts retry or fail fast?" "Q2: How are out-of-order events handled?"
       ```
     - **Round 2**: Probe adversarial edge cases (concurrency, idempotency, replay isolation) and walk the user through the Bridge 2.5b Pattern Selection Funnel via `ask_question`. Once answered, clear open questions:
       ```bash
       uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli record-dialogue \
         --workspace <workspace> \
         --clear-questions
       ```
  2. **Bridge 2.5a (Event Modeling Timeline) & Bridge 2.5b (Tactical Pattern Selection Gate)**:
     - Document the timeline and 4-Question Decision Funnel in `specs/bdd/event-modeling-and-pattern-gate.md`.
     - Lock the selected paradigm (`CQRS_EVENT_SOURCING`, `STATE_BASED_OCC`, or `VERTICAL_SLICE_CRUD`) and coordination scope (`SINGLE_AGGREGATE`, `PROCESS_MANAGER_SAGA`, or `CRUD_DIRECT`) in `.agents/state/phase-lock.json`:
       ```bash
       uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli select-pattern \
         --workspace <workspace> \
         --paradigm CQRS_EVENT_SOURCING \
         --scope SINGLE_AGGREGATE
       ```
  3. **Declarative Gherkin Authoring (`specs/features/*.feature`)**:
     - Once `rounds_completed >= required_minimum_rounds` (default `2`) and `unresolved_questions == []`, the `PreToolUse` gatekeeper unlocks writing `specs/features/*.feature`.
- **Deterministic Gate Checks (`G2`)**:
  - `G2-DIALOGUE-ROUNDS`: `bdd_dialogue.rounds_completed >= bdd_dialogue.required_minimum_rounds` (default `2`).
  - `G2-UNRESOLVED-QUESTIONS`: `bdd_dialogue.unresolved_questions` must be empty (`[]`).
  - `G2-PATTERN-GATE`: `bdd_dialogue.pattern_selection_approved == True` and `selected_paradigm` is set.
  - `G2-MISSING-FEATURES`: At least one `specs/features/*.feature` file must exist.
  - `BDD-MISSING-FEATURE`: Every `.feature` file must contain a `Feature:` header.
  - `BDD-MISSING-GWT`: Every `.feature` file must contain `Given `, `When `, and `Then ` steps.
  - `BDD-TRANSPORT-LEAKAGE`: Zero occurrences of transport/infrastructure terms matching:
    `\b(HTTP\s+\d{3}|status\s+code\s+\d{3}|SELECT\s+|INSERT\s+INTO|UPDATE\s+bank_accounts|pgx\.|KafkaTopic|localhost:\d+)\b`
- **Promotion Command (`G2` $\rightarrow$ `P3`)**:
  ```bash
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace <workspace>
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace <workspace> \
    --lock-files "specs/bdd/*.md" "specs/features/*.feature"
  ```

---

### Phase 3: `P3_TACTICAL_DDD_STUBS_AND_PORTS`

- **Phase Index**: `3`
- **Default Active Owner**: `td-auditor`
- **Primary Skills**: `sdd-tactical-contract`, `strict-audit`
- **Purpose**: Crystallize compile-checked domain types, Aggregates, Value Objects, Commands, Events, Queries, Error sentinels, and Port interfaces directly from the locked Phase 2 `.feature` files—before writing external wire schemas or implementation code.
- **Required Outputs**:
  - `specs/ddd/tactical-model-spec.md`
  - `docs/architecture/ARCHITECTURE_BLUEPRINT.md` (with Go blocks $\le 15$ lines)
  - `internal/<module>/**/*.go` compile-only stub files:
    - Every `When` step $\rightarrow$ Command struct (`internal/<module>/cmd/app/commands.go`)
    - Every `Given` / `Then` event step $\rightarrow$ Domain Event struct (`internal/<module>/common/events.go`)
    - Every `Then` rejection step $\rightarrow$ Domain Error sentinel (`internal/<module>/cmd/domain/errors.go`)
    - All Go functions/methods must have a single-line body containing `SDD_STUB`:
      ```go
      panic("SDD_STUB: implementation locked until Phase 5b")
      ```
- **Deterministic Gate Checks (`G3`)**:
  - `G3-MISSING-TACTICAL-FILES`: At least one `.go` file must exist under `internal/<module>/` (when `language == "go"`).
  - `SDD-P3-STUB-ONLY`: Every non-empty Go function/method body in non-test files must be a single line containing `"SDD_STUB"`.
  - **Paradigm-Specific Checks**:
    - If `selected_paradigm == "CQRS_EVENT_SOURCING"`:
      - `DDD-CROSS-CONTEXT-IMPORT`: `/cmd/` packages must never import `query` packages, and `/query/` packages must never import `cmd/` packages.
      - `DDD-SEALED-AGGREGATE-GETTER`: Files ending in `_aggregate.go` must never declare public balance getters (`GetBalance`, `Balance`, `BalanceCents`).
    - If `selected_paradigm == "VERTICAL_SLICE_CRUD"`:
      - `PONYTAIL-OVERENGINEERING-BLOCK`: File paths must not contain `aggregate`, `event_store`, `outbox_relay`, or `command_bus`.
- **`PreToolUse` Enforcement**:
  - Blocks `*_test.go` files (`SDD PHASE 3 BLOCK: Executable '*_test.go' harnesses belong to Phase 5a`).
  - Blocks `specs/openapi/*`, `specs/asyncapi/*`, and `migrations/*.sql` (`SDD SEQUENCE BLOCK`).
- **Promotion Command (`G3` $\rightarrow$ `P4`)**:
  ```bash
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace <workspace>
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace <workspace> \
    --lock-files "specs/ddd/tactical-*.md" "docs/architecture/ARCHITECTURE_BLUEPRINT.md"
  ```
  *(Note: Do **not** pass `internal/<module>/**/*.go` to `--lock-files` at Gate G3, because Phase 5b will replace the `panic("SDD_STUB")` bodies with production implementations.)*

---

### Phase 4: `P4_INTERFACE_AND_STORAGE_CONTRACTS`

- **Phase Index**: `4`
- **Default Active Owner**: `td-auditor` (OpenAPI/AsyncAPI/DDL) + `pm-planner` (`UAT_PLAYBOOK.md`)
- **Primary Skill**: `sdd-tactical-contract`
- **Purpose**: Formalize the stabilized Phase 3 Commands, Queries, and Domain Events into external REST, event-stream, and database schemas, and author the pre-implementation UAT Playbook.
- **Required Outputs**:
  - `specs/openapi/*.yaml`: OpenAPI `3.x` specification with non-empty `paths`.
  - `specs/asyncapi/*.yaml`: AsyncAPI `2.x` or `3.x` specification with non-empty `channels`.
  - `migrations/**/*.sql`: PostgreSQL DDL migrations (e.g., `UNIQUE (aggregate_id, version)` on `event_store` and `processed_events`, partial index `WHERE published_at IS NULL` on `event_outbox`).
  - `docs/uat/UAT_PLAYBOOK.md`: Executable Product Manager UAT specification derived from Phase 2 `.feature` scenarios and Phase 4 OpenAPI/AsyncAPI contracts.
- **Deterministic Gate Checks (`G4`)**:
  - `G4-MISSING-CONTRACTS`: At least one YAML contract must exist in `specs/openapi/` or `specs/asyncapi/`.
  - `CONTRACT-YAML-PARSE` / `CONTRACT-ROOT-OBJECT`: All contract files must be valid YAML mappings.
  - `OPENAPI-VERSION` / `OPENAPI-PATHS`: OpenAPI files must specify `openapi: 3.x` and declare non-empty `paths`.
  - `ASYNCAPI-VERSION` / `ASYNCAPI-CHANNELS`: AsyncAPI files must specify `asyncapi: 2.x` or `3.x` and declare non-empty `channels`.
- **`PreToolUse` Enforcement**:
  - Blocks all `.go` file edits (`SDD PHASE 4 BLOCK: Phase 4 is strictly for OpenAPI 3.1, AsyncAPI 3.0, SQL DDL, and UAT Playbook authoring`).
- **Promotion Command (`G4` $\rightarrow$ `P5a`)**:
  ```bash
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace <workspace>
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace <workspace> \
    --lock-files "specs/openapi/*.yaml" "specs/asyncapi/*.yaml" "migrations/**/*.sql" "docs/uat/UAT_PLAYBOOK.md"
  ```

---

### Phase 5: `P5_IMPLEMENTATION_AND_VERIFICATION` (`5a` $\rightarrow$ `5b` $\rightarrow$ `5c`)

- **Phase Index**: `5`
- **Default Active Owner**: `td-auditor`
- **Primary Skills**: `sdd-cqrs-gate`, `strict-audit`
- **Purpose**: Execute strict Red-Green-Verify TDD/BDD implementation against the locked Phase 1–4 specifications.

#### Sub-Phase `5a_RED_HARNESS`

- **`PreToolUse` Enforcement**:
  - Allows writing `*_test.go` files.
  - **Denies** modifying any non-test `.go` file (`SDD PHASE 5a RED-HARNESS GATE: You may only write '*_test.go' files until the Red-Suite compilation & failure check passes`).
- **Exit Criteria (Sub-Gate `G5a`)**:
  1. Test binaries compile cleanly against Phase 3 stubs (`go test -c ./...` exits `0`).
  2. Running the tests fails (`go test ./internal/<module>/...` exits `!= 0` due to `panic("SDD_STUB")`).
- **Promotion Command (`5a_RED_HARNESS` $\rightarrow$ `5b_GREEN_IMPL`)**:
  ```bash
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace <workspace>
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace <workspace> \
    --lock-files "test/verification/*_test.go" "internal/<module>/**/*_test.go"
  ```

#### Sub-Phase `5b_GREEN_IMPL`

- **`PreToolUse` Enforcement**:
  - Unlocks production `.go` files so `@td-auditor` can replace `panic("SDD_STUB")` bodies inside-out:
    1. Domain (`*_aggregate.go`, value objects, invariants)
    2. Write Application & Infrastructure (Transactional Outbox + Event Store `pgx.Tx`)
    3. Read Application & Infrastructure (Double-Barrier Idempotent SQL Projection + Kafka Consumer)
    4. HTTP Command & Query Routers
  - Enforces paradigm checks (`DDD-SEALED-AGGREGATE-GETTER`, `DDD-CROSS-CONTEXT-IMPORT`, `PONYTAIL-OVERENGINEERING-BLOCK`) on every write.
  - Protects all locked Phase 1–4 artifacts and Phase 5a `*_test.go` files via `CONTRACT / ARTIFACT LOCK PROTECTION` (`force_ask`).
- **Promotion Command (`5b_GREEN_IMPL` $\rightarrow$ `5c_VERIFICATION`)**:
  ```bash
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace <workspace>
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace <workspace> \
    --lock-files "internal/<module>/**/*.go"
  ```

#### Sub-Phase `5c_VERIFICATION`

- **Activities**:
  - Run full unit, integration, Testcontainers, and Toxiproxy chaos verification suites.
  - Run `@sdk-architect` (`run_sdk_verification_pipeline`) with `focus_area="full_gate"`.
  - Generate `docs/architecture/CUTOVER_AND_BENCHMARK_REPORT.md`.
- **Final Verification Check (`G5`)**:
  ```bash
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace <workspace>
  ```

---

## 4. Static Audit Rule ID Reference

| Rule ID | Enforced By | Phase(s) | Condition Triggered |
| :--- | :--- | :--- | :--- |
| `SDD-BLUEPRINT-NO-CODE-DUMP` | `PreToolUse` & `verify-gate` | `P0`–`P3` | `ARCHITECTURE_BLUEPRINT.md` contains a ` ```go ` fenced block with $> 15$ non-empty lines. |
| `G1-MISSING-BOUNDARY-MAP` | `verify-gate` | `P1`–`P5` | `docs/architecture/boundary-map.md` does not exist on disk. |
| `G2-DIALOGUE-ROUNDS` | `PreToolUse` & `verify-gate` | `P2` | `rounds_completed < required_minimum_rounds` (default `2`). |
| `G2-UNRESOLVED-QUESTIONS` | `PreToolUse` & `verify-gate` | `P2` | `unresolved_questions` list in `phase-lock.json` is non-empty. |
| `G2-PATTERN-GATE` | `verify-gate` | `P2` | `pattern_selection_approved` is `false` or `selected_paradigm` is `null`. |
| `G2-MISSING-FEATURES` | `verify-gate` | `P2` | No `*.feature` files found in `specs/features/`. |
| `BDD-MISSING-FEATURE` | `PreToolUse` & `verify-gate` | `P2` | `.feature` file is missing a `Feature:` header. |
| `BDD-MISSING-GWT` | `PreToolUse` & `verify-gate` | `P2` | `.feature` file is missing `Given `, `When `, or `Then ` keywords. |
| `BDD-TRANSPORT-LEAKAGE` | `PreToolUse` & `verify-gate` | `P2` | `.feature` file contains HTTP codes, SQL statements, `pgx.`, `KafkaTopic`, or `localhost:<port>`. |
| `G3-MISSING-TACTICAL-FILES` | `verify-gate` | `P3`–`P5` | No `.go` files found under `internal/<module>/` (when `language == "go"`). |
| `SDD-P3-STUB-ONLY` | `PreToolUse` & `verify-gate` | `P3` | Non-test Go function body has $> 1$ code line or lacks `"SDD_STUB"`. |
| `DDD-CROSS-CONTEXT-IMPORT` | `PreToolUse` & `verify-gate` | `P3`–`P5` | Go file in `/cmd/` imports `query"` or Go file in `/query/` imports `cmd/` (`CQRS_EVENT_SOURCING`). |
| `DDD-SEALED-AGGREGATE-GETTER` | `PreToolUse` & `verify-gate` | `P3`–`P5` | `*_aggregate.go` defines `GetBalance()`, `Balance()`, or `BalanceCents()` (`CQRS_EVENT_SOURCING`). |
| `PONYTAIL-OVERENGINEERING-BLOCK` | `PreToolUse` & `verify-gate` | `P3`–`P5` | File path contains `aggregate`, `event_store`, `outbox_relay`, or `command_bus` under `VERTICAL_SLICE_CRUD`. |
| `G4-MISSING-CONTRACTS` | `verify-gate` | `P4` | No `.yaml` files found in `specs/openapi/` or `specs/asyncapi/`. |
| `CONTRACT-YAML-PARSE` | `verify-gate` | `P4` | YAML syntax error in OpenAPI or AsyncAPI file. |
| `CONTRACT-ROOT-OBJECT` | `verify-gate` | `P4` | YAML root element is not a dictionary/mapping. |
| `OPENAPI-VERSION` / `OPENAPI-PATHS` | `verify-gate` | `P4` | OpenAPI file is not version `3.x` or has empty `paths`. |
| `ASYNCAPI-VERSION` / `ASYNCAPI-CHANNELS` | `verify-gate` | `P4` | AsyncAPI file is not version `2.x`/`3.x` or has empty `channels`. |
| `SDD-LOCK-MISSING` | `verify-gate` | `P0`–`P5` | A file recorded in `locked_artifacts` is missing from disk. |
| `SDD-LOCK-DRIFT` | `verify-gate` | `P0`–`P5` | On-disk CRLF-normalized SHA-256 digest does not match `locked_artifacts` in `phase-lock.json`. |
