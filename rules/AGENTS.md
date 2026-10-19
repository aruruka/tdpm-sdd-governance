# TD/PM & Stage-Gated SDD Governance Rules

When operating in any workspace containing `.agents/state/phase-lock.json`, you MUST enforce the **6-Phase BDD-First Spec-Driven Development (SDD) Pipeline** and the **TD/PM Persona Ownership Matrix**:

## 1. Non-Negotiable Artifact Sequence (`P0` -> `P5`)

1. **Phase 0 (`P0_BROWNFIELD_DISCOVERY_AND_TRIAGE` — Owner: `@pm-planner`)**:
   - Audit legacy baselines (`docs/architecture/LEGACY_DEPLOYMENT_REPORT.md`, `ARCHITECTURAL_VERIFICATION_REPORT.md`) and classify every behavior into *Preserve*, *Invert/Remediate*, or *Extend* in `specs/bdd/legacy-parity-triage.md`.
   - Zero `.go`, `.feature`, or `.yaml` contract files may be created in Phase 0.
2. **Phase 1 (`P1_STRATEGIC_DDD_AND_CONTEXT_MAP` — Owner: `@pm-planner` + `@td-auditor`)**:
   - Define the Ubiquitous Language Glossary, Subdomain Classifications (`Core`, `Supporting`, `Generic`), Bounded Contexts, and Context Mapping (`OHS`, `PL`, `SK`, `ACL`) in `docs/architecture/boundary-map.md` and `specs/ddd/arch-rules.yaml`.
   - Architecture blueprints (`docs/architecture/ARCHITECTURE_BLUEPRINT.md`) must NEVER embed concrete Go implementation bodies (>15 lines).
3. **Phase 2 (`P2_ITERATIVE_BDD_AND_PATTERN_GATE` — Owner: `@pm-planner` + `@td-auditor` for Bridge 2.5b)**:
   - Conduct **at least 2 rounds of Socratic Example Mapping dialogue** via `ask_question`, logging Rules, Examples, and Edge-Case Questions in `specs/bdd/example-map.md` and recording each round via `uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli record-dialogue --workspace <workspace>` (or `tdpm-sdd record-dialogue --workspace <workspace>`).
   - Execute **Bridge 2.5a (Event Modeling Timeline)** and **Bridge 2.5b (Tactical Pattern Selection Gate)** in `specs/bdd/event-modeling-and-pattern-gate.md`, locking `CQRS_EVENT_SOURCING`, `STATE_BASED_OCC`, or `VERTICAL_SLICE_CRUD` via `select-pattern`.
   - Author declarative Gherkin specifications (`specs/features/*.feature`) strictly in Ubiquitous Language (`Given` historical events / `When` command / `Then` emitted events, domain errors, or read projections) with zero HTTP/SQL/Kafka transport leakage.
4. **Phase 3 (`P3_TACTICAL_DDD_STUBS_AND_PORTS` — Owner: `@td-auditor`)**:
   - Crystallize Tactical DDD types (Aggregates with private fields, Value Objects, Commands, Domain Events, Queries, Error sentinels, and Repository/Dispatcher interfaces) directly from the locked Phase 2 `.feature` files.
   - All Go function/method bodies in Phase 3 MUST be single-line `panic("SDD_STUB: implementation locked until Phase 5b")` stubs.
5. **Phase 4 (`P4_INTERFACE_AND_STORAGE_CONTRACTS` — Owner: `@td-auditor` + `@pm-planner` for UAT)**:
   - Formalize stabilized Phase 3 Commands, Queries, and Domain Events into OpenAPI 3.1 (`specs/openapi/*.yaml`), AsyncAPI 3.0 (`specs/asyncapi/*.yaml`), PostgreSQL DDL (`migrations/**/*.sql`), and pre-implementation `docs/uat/UAT_PLAYBOOK.md`.
6. **Phase 5 (`P5_IMPLEMENTATION_AND_VERIFICATION` — Owner: `@td-auditor`)**:
   - **Sub-Phase `5a_RED_HARNESS`**: Write `*_test.go` and Godog step definitions against the Phase 3 stubs; verify compilation and Red failure before advancing.
   - **Sub-Phase `5b_GREEN_IMPL`**: Implement production Go code inside-out (Domain -> Write App/Infra -> Read App/Infra -> HTTP Routers) without mutating locked Phase 1–4 artifacts.
   - **Sub-Phase `5c_VERIFICATION`**: Run chaos/concurrency verification suites, benchmarks, and generate `docs/architecture/CUTOVER_AND_BENCHMARK_REPORT.md`.

## 2. Subagent Acceptance Verification

Whenever delegating tasks to `pm-planner`, `td-auditor`, or `sdk-architect`, never accept a completion report on trust alone—always run `uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace <workspace>` (or `tdpm-sdd verify-gate --workspace <workspace>`) and verify on-disk SHA-256 integrity before calling `ask_question` to promote phases.
