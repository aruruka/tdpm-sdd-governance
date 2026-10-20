# Goal: Build SEO/AEO-Optimized Homepage Hosted Directly on GitHub Pages

## 1. Executive Summary & Objective

- **Target Goal**: Design and deploy a high-performance, single-page landing site and developer workflow showcase directly within this repository (`tdpm-sdd-governance`).
- **Hosting Strategy**: GitHub Pages via GitHub Actions (`.github/workflows/deploy-pages.yml`) under Raymond Yan's personal GitHub account (`aruruka`), with optional custom domain support (`shouneng.website` subdomain).
- **Target Audience**: AI engineers, lead architects, technical directors, and Go/Python/TypeScript engineering teams using Google Antigravity who need rigorous, stage-gated Spec-Driven Development (SDD), BDD, and DDD governance to prevent AI hallucinations and code rot.
- **Governing Skills & Specifications**:
  - `seo-aeo-landing-page-writer` (narrative arc, 25–40 word AEO extraction block, standalone FAQ, pain-first structure)
  - `gh-cli` (GitHub Pages configuration, repository creation under `aruruka`, Actions workflow deployment)
  - `modern-web-guidance` & `a11y-debugging` (semantic HTML5, zero-bloat modern CSS, interactive workflow tabs/accordions, WCAG AA compliance)

---

## 2. Hosting Feasibility & Repository URL Alignment

### 2.1 Hosting Directly Within This Repository
GitHub Pages will be hosted directly from this repository (`https://github.com/aruruka/tdpm-sdd-governance`) using **GitHub Actions (`.github/workflows/deploy-pages.yml`)**:
- Triggers automatically on push to `main`.
- Packages static web assets (e.g., `site/` or `docs/`) and deploys via `actions/upload-pages-artifact` and `actions/deploy-pages@v4`.
- Keeps branch history clean without requiring a separate `gh-pages` branch.

### 2.2 Canonical URLs (`aruruka`)
- **GitHub Account**: `aruruka` (Raymond Yan — `keraymondyan69@gmail.com` / `shouneng.website`)
- **GitHub Repository URL**: `https://github.com/aruruka/tdpm-sdd-governance`
- **GitHub Pages Homepage URL**: `https://aruruka.github.io/tdpm-sdd-governance/` (or custom domain `https://sdd.shouneng.website`)
- **`pyproject.toml` `[project.urls]` (Already Updated)**:
  ```toml
  [project.urls]
  Homepage = "https://aruruka.github.io/tdpm-sdd-governance/"
  Repository = "https://github.com/aruruka/tdpm-sdd-governance"
  ```

---

## 3. SEO & AEO Architecture Specifications (Mandatory Requirements)

The homepage development session MUST strictly adhere to the `seo-aeo-landing-page-writer` specification:

### 3.1 Primary Keyword & Metadata
- **Primary Keyword**: `Spec-Driven Development Antigravity Plugin`
- **Secondary Keywords**: `AI agent governance`, `BDD first development`, `Tactical DDD code generation`, `Go CQRS event sourcing gate`, `phase-lock architecture`
- **Search Intent**: Commercial / Technical evaluation. Engineers looking to make AI coding agents safe, deterministic, and production-grade.

### 3.2 Narrative Arc & Section Sequence (Order is strictly enforced)
1. **Hero Section**:
   - **H1**: Direct outcome statement (e.g., *Eliminate AI Code Rot with Stage-Gated Spec-Driven Development*).
   - **AEO Extraction Blockquote** (strictly 25–40 words, standalone, zero jargon):
     > `tdpm-sdd-governance is an open-source Google Antigravity plugin that enforces stage-gated Spec-Driven Development, preventing AI agent code drift by locking BDD specifications, tactical DDD contracts, and deterministic verification gates before code generation.`
   - **Primary CTA**: `Install Plugin` / `View on GitHub (aruruka/tdpm-sdd-governance)`.
   - **Quick Stat Bar**: *6-Phase SDD Pipeline · Zero Hallucinated APIs · 100% SHA-256 Verified Gates*.
2. **Problem Section (Pain-First, No Product Mention Yet)**:
   - Empathize with autonomous agent failures: jumping straight to database tables and handlers before domain invariants are settled, leaky aggregates, dual-write split-brain bugs, and untested edge cases.
3. **Solution Section**:
   - Introduce `tdpm-sdd-governance`: The Technical Director (`@td-auditor`) & Product Manager (`@pm-planner`) governance pairing orchestrated by `@td-pm` inside Google Antigravity.
4. **Features as Benefits Table**:
   - Explicit mapping: *Feature* $\rightarrow$ *Engineering Outcome*.
   - Phase locks (`.agents/state/phase-lock.json`), Socratic Example Mapping, Panic `SDD_STUB` enforcement, Deterministic Gate CLI (`tdpm-sdd verify-gate`), and Read-Only SDK Verification (`@sdk-architect`).
5. **Social Proof & Architecture Guarantee Stats**:
   - Zero hallucinated Go/Python/TypeScript interfaces, 100% contract compliance, cryptographic SHA-256 audit trails.
6. **Mid-Page CTA**:
   - Fast installation snippet (`git clone https://github.com/aruruka/tdpm-sdd-governance.git` + `uv sync`).
7. **How It Works & Complete `go-cqrs` Developer Process Playbooks** *(See Section 4 below for mandatory deep-dive content)*.
8. **Comparison Table (Honest Evaluation)**:
   - Comparing `tdpm-sdd-governance` vs. *Raw AI Prompts* vs. *Unchecked Autonomous Subagents*.
   - Include honest trade-offs (e.g., requires upfront Socratic BDD discipline before writing production code; raw prompts are faster for throwaway prototypes).
9. **FAQ Section (AEO Optimized)**:
   - Minimum 6 questions, each answer strictly under 50 words and self-contained.
10. **Trust Signals & Compliance**:
    - Open source (`MIT License — Copyright (c) 2026 Raymond Yan (shouneng.website)`), local-first hook execution, zero telemetry leakage, CRLF-normalized SHA-256 lock integrity.
11. **Final CTA & Footer**:
    - Dual CTA: *Star on GitHub* and *Read the Full Documentation*.

---

## 4. Mandatory Deep-Dive Section: Complete `go-cqrs` Process Examples

The homepage MUST feature a prominent, interactive (tabbed or step-by-step) **"Real-World Developer Playbook (`go-cqrs`)"** section covering two complete workflows from start to finish:

---

### Playbook A: Adding a New Feature / Module to `go-cqrs` (Start-to-Finish)

**Scenario**: A developer wants to add a net-new module (e.g., `transfer` for inter-account funds transfers, or `profile` for customer profiles) to an existing `go-cqrs` workspace (`./modern-service`).

#### Step 1: Initial Entrypoint — Which Custom Agent or Slash-Command to Use First?
- **Custom Agent to Invoke First**: Start with **`@td-pm`** (the Principal TD/PM Orchestrator subagent) or trigger the **`/sdd-bdd-architect`** skill.
- **What Happens First**: Register and activate the new module in `.agents/state/phase-lock.json` at **Phase 1** (`P1_STRATEGIC_DDD_AND_CONTEXT_MAP`, since a net-new module skips Phase 0 brownfield legacy triage):
  ```bash
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli add-module \
    --workspace ./modern-service \
    --module transfer \
    --language go \
    --phase 1 \
    --activate
  ```
- The `PreInvocation` hook immediately injects the governance status banner into every turn, and `PreToolUse` physically blocks premature `.go`, `.feature`, `.yaml`, or `.sql` writes.

#### Step 2: Phase 1 — Strategic DDD & Context Mapping (`@pm-planner` + `@td-auditor` | Skill: `/sdd-bdd-architect`)
- **Action**: `@td-pm` routes work to `@pm-planner` and `@td-auditor` to update:
  1. `docs/architecture/boundary-map.md` (Ubiquitous Language Glossary, Subdomain classification: `Core` vs `Supporting`, and Context Map relationships).
  2. `specs/ddd/arch-rules.yaml` (Forbidden cross-boundary Go imports).
  3. `docs/architecture/ARCHITECTURE_BLUEPRINT.md` (Topology diagrams; Go code snippets capped at $\le 15$ lines by `SDD-BLUEPRINT-NO-CODE-DUMP`).
- **Gate `G1` Transition**: Run `tdpm-sdd verify-gate` $\rightarrow$ human approves scorecard via `ask_question` $\rightarrow$ run `tdpm-sdd promote-phase --lock-files "docs/architecture/boundary-map.md" "specs/ddd/arch-rules.yaml"`.

#### Step 3: Phase 2 — Socratic BDD Dialogue & Bridge 2.5b Pattern Gate (`@pm-planner` + `@td-auditor` | Skill: `/sdd-bdd-architect`)
- **Socratic Dialogue (Rounds 1 & 2)**:
  - `@pm-planner` maps Yellow Cards (Domain Rules), Green Cards (Examples), and Red Cards (Edge-Case Questions) in `specs/bdd/example-map.md`.
  - `@pm-planner` interviews the developer via `ask_question` across **at least 2 rounds**, recording each round via `tdpm-sdd record-dialogue`.
- **Bridge 2.5b Pattern Selection**:
  - `@td-auditor` documents the Event Modeling timeline in `specs/bdd/event-modeling-and-pattern-gate.md` and locks the module paradigm (`CQRS_EVENT_SOURCING`, `STATE_BASED_OCC`, or `VERTICAL_SLICE_CRUD`) via:
    ```bash
    uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli select-pattern \
      --workspace ./modern-service \
      --module transfer \
      --paradigm CQRS_EVENT_SOURCING \
      --scope PROCESS_MANAGER_SAGA
    ```
- **Pure Gherkin Specification**:
  - Once `rounds_completed >= 2` and `unresolved_questions == []`, `PreToolUse` unlocks `.feature` authoring.
  - `@pm-planner` writes `specs/features/transfer.feature` strictly in Ubiquitous Language (`Given` events / `When` command / `Then` emitted events or domain errors—zero HTTP status codes, SQL queries, or Kafka topic names allowed).
- **Gate `G2` Transition**: `tdpm-sdd verify-gate` $\rightarrow$ `tdpm-sdd promote-phase --lock-files "specs/bdd/*.md" "specs/features/transfer.feature"`.

#### Step 4: Phase 3 — Tactical DDD Stubs & Ports (`@td-auditor` | Skill: `/sdd-tactical-contract`)
- **Action**: `@td-pm` switches active ownership to **`@td-auditor`**.
- `@td-auditor` translates `transfer.feature` 1:1 into Go domain packages (`internal/transfer/...`):
  - Aggregates with strictly private/unexported fields (no public balance/state getters allowed under `DDD-SEALED-AGGREGATE-GETTER`).
  - Value Objects (`common.Cents` as `int64`—`float64` is blocked by `DDD-FLOAT-CURRENCY`), Commands, Domain Events, Error Sentinels, and Repository/Outbox Port interfaces.
  - Every function and method body MUST be a single-line stub:
    ```go
    panic("SDD_STUB: implementation locked until Phase 5b")
    ```
- **Gate `G3` Transition**: `tdpm-sdd verify-gate` $\rightarrow$ `tdpm-sdd promote-phase --lock-files "specs/ddd/tactical-*.md" "docs/architecture/ARCHITECTURE_BLUEPRINT.md"`.

#### Step 5: Phase 4 — Interface & Storage Contracts (`@td-auditor` + `@pm-planner` | Skill: `/sdd-tactical-contract`)
- **Action**: Go source files are frozen in Phase 4.
  - `@td-auditor` authors OpenAPI 3.1 (`specs/openapi/transfer.v1.yaml`), AsyncAPI 3.0 (`specs/asyncapi/transfer-events.v1.yaml`), and PostgreSQL 16 DDL (`migrations/**/*.sql`).
  - `@pm-planner` authors the pre-implementation acceptance scenarios in `docs/uat/UAT_PLAYBOOK.md`.
- **Gate `G4` Transition**: `tdpm-sdd verify-gate` $\rightarrow$ `tdpm-sdd promote-phase --lock-files "specs/openapi/*.yaml" "specs/asyncapi/*.yaml" "migrations/**/*.sql" "docs/uat/UAT_PLAYBOOK.md"` (advances to Phase `5a_RED_HARNESS`).

#### Step 6: Phase 5 — Red-to-Green Implementation (`@td-auditor` | Skills: `/sdd-cqrs-gate`, `/strict-audit`)
1. **Sub-Phase `5a_RED_HARNESS` (Compile & Fail)**:
   - `PreToolUse` allows writing **only** `*_test.go` files.
   - `@td-auditor` writes domain unit tests and BDD verification harnesses against the Phase 3 stubs.
   - Verify that tests compile cleanly (`go test -c ./...` exits `0`) and fail as expected against `SDD_STUB` panics (`go test ./internal/transfer/...` exits `!= 0`).
   - Run `tdpm-sdd promote-phase --lock-files "internal/transfer/**/*_test.go" "test/verification/*_test.go"` to lock tests and unlock production code (`5b_GREEN_IMPL`).
2. **Sub-Phase `5b_GREEN_IMPL` (Inside-Out Implementation)**:
   - `@td-auditor` replaces `panic("SDD_STUB")` bodies inside-out: Domain Aggregate $\rightarrow$ PostgreSQL Event Store & Transactional Outbox $\rightarrow$ Idempotent Read Projection $\rightarrow$ HTTP Routers.
   - All upstream specs, contracts, and `*_test.go` files remain protected by SHA-256 locks.
   - Promote to `5c_VERIFICATION` via `tdpm-sdd promote-phase --lock-files "internal/transfer/**/*.go"`.
3. **Sub-Phase `5c_VERIFICATION` (Chaos & Benchmark Cutover)**:
   - Execute concurrency/chaos verification suites and update `docs/architecture/CUTOVER_AND_BENCHMARK_REPORT.md`.

#### Step 7: How to Ideally Confirm Feature/Module Development is "Completed" (4-Point Completion Criteria)
A developer knows the feature/module is 100% complete when all four checks pass:
1. **State Ledger Check**: `tdpm-sdd status --workspace ./modern-service` reports `current_phase: 5`, `sub_phase: "5c_VERIFICATION"`, and `gates_passed: ["G1", "G2", "G3", "G4", "G5"]`.
2. **Deterministic Gate Audit**: `tdpm-sdd verify-gate --workspace ./modern-service --module transfer` exits `0` with `"passed": true`, `findings: []`, and zero `"SDD_STUB"` panics remaining.
3. **Go Race & Integration Suite**: `go test -v -race ./internal/transfer/... ./test/verification/...` passes 100% with zero data races.
4. **Independent Read-Only SDK Audit (`@sdk-architect`)**: Delegating to **`@sdk-architect`** (which runs the `run_sdk_verification_pipeline` MCP tool with `focus_area="full_gate"`) confirms 100% SHA-256 cryptographic lock integrity and end-to-end traceability from `transfer.feature` $\rightarrow$ Go domain types $\rightarrow$ OpenAPI/AsyncAPI/SQL $\rightarrow$ passing tests.

---

### Playbook B: Patching / Fixing Bugs in Existing `go-cqrs` Features/Modules

**Scenario**: An existing module (e.g., `account`) is already at Phase 5 (`5c_VERIFICATION`) with all artifacts cryptographically locked by SHA-256 in `.agents/state/phase-lock.json`, and a developer needs to fix a bug.

#### Step 1: Which Slash-Command or Custom Agent to Use?
- **For Diagnosis & Root-Cause Analysis**: Invoke **`@td-auditor`** alongside the **`/systematic-debugging`** and **`/strict-audit`** skills (or ask **`@td-pm`** to coordinate if the bug reveals a missing domain rule in Phase 2 Gherkin).
- **Inspect Current Lock State**:
  ```bash
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli status --workspace ./modern-service
  ```

#### Step 2: Controlled Unlocking & Red-First Bug Patching Workflow
Because the module's tests (`*_test.go`), contracts (`*.yaml`, `*.sql`), and production code (`*.go`) are SHA-256 locked in `phase-lock.json`, `tdpm-sdd-governance` prevents silent, untested hotfixes:

1. **Write the Reproducing Regression Test First (`*_test.go`)**:
   - `@td-auditor` targets `internal/account/cmd/domain/account_test.go` (or `test/verification/bdd_account_test.go`).
   - Because `account_test.go` is in `locked_artifacts`, the `PreToolUse` hook intercepts the edit with a **`force_ask` human checkpoint**:
     > *"CONTRACT / ARTIFACT LOCK PROTECTION: 'internal/account/cmd/domain/account_test.go' is cryptographically locked in module 'account' (Phase 5). Modifying a locked upstream specification or verification test requires explicit human approval."*
   - You approve the edit and verify that `go test ./internal/account/...` **fails** on the new regression test (proving the bug is reproduced).
2. **Apply the Minimal Root-Cause Fix in Production Code (`*.go`)**:
   - `@td-auditor` edits the target production file (e.g., `internal/account/query/infra/postgres_read_repo.go`).
   - You approve the `force_ask` prompt.
   - **Live Guardrails During Patching**: Even during a bug fix, `PreToolUse` runs static AST checks on every edit—preventing the agent from taking shortcuts like exposing a public state getter (`DDD-SEALED-AGGREGATE-GETTER`), using `float64` for money (`DDD-FLOAT-CURRENCY`), or importing write-side packages into read-side projections (`DDD-CROSS-BOUNDARY-IMPORT`).
3. **Re-Seal the Cryptographic SHA-256 Locks**:
   - Once the fix is applied, re-lock the updated test and production files so `verify-gate` records the new canonical SHA-256 hashes (clearing `SDD-LOCK-DRIFT`):
     ```bash
     uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase \
       --workspace ./modern-service \
       --module account \
       --lock-files "internal/account/**/*.go" "test/verification/*_test.go" \
       --force
     ```
   *(Note: If the bug also required updating a locked upstream contract or `.feature` file, include that path in `--lock-files` as well.)*

#### Step 3: How to Verify That the Bug Fix is Effective (4-Step Verification Checklist)
1. **Red $\rightarrow$ Green Regression Proof**: The new regression test in `*_test.go` failed prior to the production edit and now passes consistently under `go test -v -race ./...`.
2. **Deterministic Gate & Lock Drift Verification**:
   ```bash
   uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate \
     --workspace ./modern-service \
     --module account
   ```
   Must return `"passed": true` with `0` `SDD-LOCK-DRIFT` errors and `0` static AST violations.
3. **Contract & Invariant Regression Check (`@sdk-architect`)**:
   Run **`@sdk-architect`** (`run_sdk_verification_pipeline`) to confirm the bug fix did not break OpenAPI 3.1 response schemas, AsyncAPI 3.0 event payloads, or PostgreSQL Double-Barrier idempotency.
4. **Concurrency & Chaos Suite Execution**:
   Run `go test -v -race ./test/verification/...` to confirm that parallel withdrawals, out-of-order event replays, and outbox relay retries still pass without regression.

---

## 5. Technical Implementation Stack for the Homepage

To honor **Ponytail Minimalism** (zero unnecessary dependencies) while delivering an interactive, developer-grade UI:

- **Recommended Approach — Zero-Bloat Static Site (`docs/index.html` or `site/index.html`)**:
  - Semantic HTML5 + modern CSS (CSS Grid/Flexbox, custom properties, dark/light mode, responsive container queries, accessible contrast $\ge 4.5:1$).
  - Interactive vanilla JS tabs/stepper for switching between **Playbook A (Add Feature/Module to `go-cqrs`)** and **Playbook B (Fix/Patch Bugs in `go-cqrs`)**, plus one-click copy buttons for all CLI/agent commands.
  - Embedded JSON-LD (`SoftwareApplication` & `FAQPage` structured data) for maximum AI Answer Engine Optimization (AEO).

---

## 6. Execution Checklist for the Next Session

- [x] **Step 1: Verify GitHub Remote (`aruruka/tdpm-sdd-governance`)**
  - Confirm `git remote -v` points to `https://github.com/aruruka/tdpm-sdd-governance.git` (or create it via `gh repo create aruruka/tdpm-sdd-governance --public --source=. --remote=origin`).
  - Also update badge/clone URLs in `README.md` from `example-org` to `aruruka`.
- [x] **Step 2: Author Full Homepage Copy & Interactive Playbooks**
  - Follow the 11-step `seo-aeo-landing-page-writer` arc.
  - Embed the complete **Playbook A (New Feature/Module in `go-cqrs`)** and **Playbook B (Bug Fixing & Re-Locking in `go-cqrs`)** interactive walkthroughs.
- [x] **Step 3: Build & Validate Static Site Assets**
  - Create semantic HTML/CSS/JS homepage files.
  - Verify responsive layout, keyboard navigation, and WCAG AA contrast.
- [x] **Step 4: Configure GitHub Pages Deployment**
  - Add `.github/workflows/deploy-pages.yml` using `actions/upload-pages-artifact` and `actions/deploy-pages@v4`.
  - Push to `main` and verify live deployment at `https://aruruka.github.io/tdpm-sdd-governance/`.
