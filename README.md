# TD/PM & Stage-Gated SDD Governance (`tdpm-sdd-governance`)

[![CI](https://github.com/example-org/tdpm-sdd-governance/actions/workflows/ci.yml/badge.svg)](https://github.com/example-org/tdpm-sdd-governance/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Pydantic v2](https://img.shields.io/badge/pydantic-v2-e92063.svg)](https://docs.pydantic.dev/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

> **Deterministic 6-Phase BDD-First Spec-Driven Development (SDD) & Technical Director / Product Manager (TD/PM) Governance Plugin for Google Antigravity.**

`tdpm-sdd-governance` enforces a causal, stage-gated software engineering lifecycle (`P0` $\rightarrow$ `P5`) inside Google Antigravity workspaces. It combines specialized **Product Manager (`@pm-planner`)** and **Technical Director (`@td-auditor`)** personas with a deterministic **`PreToolUse` lifecycle hook gatekeeper**, **cryptographic SHA-256 artifact locking**, and a strictly read-only **Google Antigravity SDK verification bridge (`tdpm-sdk-bridge`)**.

---

## Why `tdpm-sdd-governance`?

Autonomous coding agents frequently jump straight to writing production code or database schemas before domain invariants, concurrency policies, and failure modes are settled—causing contract churn, leaky abstractions, and untested edge cases.

`tdpm-sdd-governance` physically prevents premature implementation at the tool-execution layer:

1. **Causal Phase Ordering (`P0` $\rightarrow$ `P5`)**: Agents cannot author Gherkin `.feature` files before Strategic DDD boundaries are locked (`P1`), cannot write Go domain types before completing $\ge 2$ rounds of Socratic BDD Example Mapping (`P2`), cannot write OpenAPI/AsyncAPI/SQL contracts before Tactical DDD types stabilize (`P3`), and cannot write production code before the Red test suite compiles and fails against `SDD_STUB` panics (`P5a`).
2. **Productive Persona Tension**: Separates behavioral discovery (`@pm-planner`) from architectural enforcement (`@td-auditor`), orchestrated by `@td-pm` and independently audited by `@sdk-architect`.
3. **Paradigm-Aware Static Auditing**: Evaluates each module against its locked tactical paradigm (`CQRS_EVENT_SOURCING`, `STATE_BASED_OCC`, or `VERTICAL_SLICE_CRUD`), enforcing strict aggregate encapsulation on event-sourced cores while blocking over-engineered ceremony on CRUD modules.
4. **Cryptographic Immutability**: Upstream specifications (`boundary-map.md`, `*.feature`, `*.yaml`, `*_test.go`) are locked by normalized SHA-256 digests in `.agents/state/phase-lock.json` upon phase promotion.

---

## Architecture & Responsibility Split

```text
+-----------------------------------------------------------------------------------+
|                        HUMAN DEVELOPER / ARCHITECT                                |
|  - Answers Socratic BDD Example Mapping prompts (Rounds 1 & 2 via ask_question)   |
|  - Approves Bridge 2.5b Tactical Pattern Selection (CQRS/ES vs OCC vs CRUD)       |
|  - Reviews Gate Audit Reports (G0-G5) and authorizes promote-phase transitions    |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                     @td-pm (Principal Orchestrator Subagent)                      |
|  Inspects .agents/state/phase-lock.json -> Routes work by active phase & owner    |
+------------------+------------------------------+---------------------------------+
                   |                              |
      Phases 0, 1, 2, 4 (UAT)        Bridge 2.5b, Phases 3, 4 (Contracts), 5
                   v                              v
+----------------------------------+   +--------------------------------------------+
| @pm-planner (Product Manager)    |   | @td-auditor (Technical Director)           |
| Skill: sdd-bdd-architect         |   | Skills: sdd-tactical-contract,             |
| - P0: legacy-parity-triage.md    |   |         strict-audit, sdd-cqrs-gate        |
| - P1: Ubiquitous Language        |   | - P1: Context Map & arch-rules.yaml        |
| - P2: >=2 Socratic BDD rounds &  |   | - P2.5b: Pattern Selection Gate            |
|       pure Gherkin .feature      |   | - P3: Tactical DDD SDD_STUB types          |
| - P4: docs/uat/UAT_PLAYBOOK.md   |   | - P4: OpenAPI 3.1, AsyncAPI 3.0, SQL DDL   |
+----------------------------------+   | - P5: 5a Red -> 5b Green -> 5c Verification|
                                       +--------------------------------------------+
                                                          |
                                                          v
+-----------------------------------------------------------------------------------+
|              DETERMINISTIC ENFORCEMENT & ISOLATED VERIFICATION LAYER              |
|  1. hooks.json (PreInvocation / PreToolUse / Stop -> tdpm_sdd.cli hook)           |
|     - Blocks out-of-phase writes, shell bypasses, & locked artifact tampering     |
|  2. @sdk-architect + tdpm-sdk-bridge MCP Server (run_sdk_verification_pipeline)   |
|     - Read-only AST/Contract/SHA-256 verifier + optional Google Antigravity SDK   |
+-----------------------------------------------------------------------------------+
```

---

## Enforced 6-Phase Lifecycle (`P0` $\rightarrow$ `P5`)

| Phase | Canonical State Identifier | Active Owner | Required Artifacts & Gate Criteria | Gate ID |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | `P0_BROWNFIELD_DISCOVERY_AND_TRIAGE` | `@pm-planner` | Audit legacy baselines (`docs/architecture/LEGACY_DEPLOYMENT_REPORT.md`, `ARCHITECTURAL_VERIFICATION_REPORT.md`) and classify behaviors into *Preserve*, *Invert/Remediate*, or *Extend* in `specs/bdd/legacy-parity-triage.md`. Zero `.go`, `.feature`, or `.yaml` files allowed. | `G0` |
| **Phase 1** | `P1_STRATEGIC_DDD_AND_CONTEXT_MAP` | `@pm-planner` + `@td-auditor` | Author Ubiquitous Language Glossary, Subdomain classifications (`Core`, `Supporting`, `Generic`), and Context Map (`OHS`, `PL`, `SK`, `ACL`) in `docs/architecture/boundary-map.md` and `specs/ddd/arch-rules.yaml`. Blueprint code blocks $\le 15$ lines. | `G1` |
| **Phase 2** | `P2_ITERATIVE_BDD_AND_PATTERN_GATE` | `@pm-planner` + `@td-auditor` | Conduct $\ge 2$ Socratic dialogue rounds (`specs/bdd/example-map.md`), clear all `unresolved_questions`, lock Bridge 2.5b paradigm (`specs/bdd/event-modeling-and-pattern-gate.md`), and author pure Gherkin `specs/features/*.feature` (zero HTTP/SQL/Kafka leakage). | `G2` |
| **Phase 3** | `P3_TACTICAL_DDD_STUBS_AND_PORTS` | `@td-auditor` | Derive Aggregates, Value Objects, Commands, Events, Queries, Errors, and Ports 1:1 from Phase 2 `.feature` files under `internal/<module>/**/*.go`. All function bodies must be single-line `panic("SDD_STUB: ...")`. Zero `*_test.go` files allowed. | `G3` |
| **Phase 4** | `P4_INTERFACE_AND_STORAGE_CONTRACTS` | `@td-auditor` + `@pm-planner` | Formalize Phase 3 types into OpenAPI 3.1 (`specs/openapi/*.yaml`), AsyncAPI 3.0 (`specs/asyncapi/*.yaml`), SQL DDL (`migrations/**/*.sql`), and `docs/uat/UAT_PLAYBOOK.md`. Source `.go` files are frozen. | `G4` |
| **Phase 5a** | `P5_IMPLEMENTATION_AND_VERIFICATION` (`5a_RED_HARNESS`) | `@td-auditor` | Author executable unit/BDD test harnesses (`*_test.go`). Production `.go` files remain locked at `SDD_STUB`. Tests must compile (`go test -c ./...` exits `0`) and fail against stubs (`go test ./...` exits `!= 0`). | `G5a` |
| **Phase 5b** | `P5_IMPLEMENTATION_AND_VERIFICATION` (`5b_GREEN_IMPL`) | `@td-auditor` | Implement production code inside-out (Domain $\rightarrow$ Write App/Infra $\rightarrow$ Read App/Infra $\rightarrow$ HTTP Routers) without mutating SHA-256 locked Phase 1–5a artifacts. | `G5b` |
| **Phase 5c** | `P5_IMPLEMENTATION_AND_VERIFICATION` (`5c_VERIFICATION`) | `@td-auditor` | Execute concurrency/chaos verification suites, performance benchmarks, and publish `docs/architecture/CUTOVER_AND_BENCHMARK_REPORT.md`. | `G5` |

---

## Repository Structure

```text
tdpm-sdd-governance/
├── .github/
│   └── workflows/
│       └── ci.yml                           # GitHub Actions CI matrix (Ubuntu & Windows)
├── LICENSE                                  # MIT License (2026 Antigravity Authors)
├── CONTRIBUTING.md                          # Contribution guidelines & developer setup
├── CODE_OF_CONDUCT.md                       # Contributor Covenant v2.1
├── SECURITY.md                              # Vulnerability reporting policy
├── CHANGELOG.md                             # Keep a Changelog release notes
├── plugin.json                              # Antigravity plugin manifest (v1.0.0)
├── hooks.json                               # PreInvocation, PreToolUse, and Stop lifecycle hooks
├── mcp_config.json                          # tdpm-sdk-bridge MCP server definition
├── pyproject.toml                           # Python >=3.11 package & `tdpm-sdd` CLI entrypoint
├── rules/
│   └── AGENTS.md                            # Global workspace governance rules & persona matrix
├── agents/
│   ├── td-pm.md                             # @td-pm orchestrator subagent definition
│   ├── product-manager.md                   # @pm-planner Product Manager subagent definition
│   ├── tech-director.md                     # @td-auditor Technical Director subagent definition
│   └── sdk-architect.md                     # @sdk-architect read-only SDK verification subagent
├── skills/
│   ├── sdd-bdd-architect/SKILL.md           # P0 -> P2 Socratic BDD & Pattern Selection workflow
│   ├── sdd-tactical-contract/SKILL.md       # P3 -> P4 Tactical DDD stubs & OpenAPI/AsyncAPI/DDL
│   ├── sdd-cqrs-gate/SKILL.md               # G0 -> G5 gate verification & SHA-256 promotion
│   └── strict-audit/SKILL.md                # Stack & paradigm-parameterized static audit rules
├── src/tdpm_sdd/
│   ├── py.typed                             # PEP 561 typing marker
│   ├── models.py                            # Pydantic v2 state ledger models & CRLF-safe SHA-256
│   ├── cli.py                               # `tdpm-sdd` / `python -m tdpm_sdd.cli` commands
│   ├── gatekeeper.py                        # Hook dispatcher & PreToolUse policy engine
│   ├── auditors.py                          # AST, Gherkin, YAML contract, and lock-drift auditors
│   └── sdk_bridge.py                        # FastMCP server (`run_sdk_verification_pipeline`)
├── tests/
│   └── test_gatekeeper_and_cli.py           # End-to-end unit & integration test suite
└── docs/
    ├── getting-started.md                   # Installation, workspace init, and verification guide
    ├── stage-gates.md                       # Complete state-machine & gate rule reference
    ├── configuration.md                     # Ledger schema, hook tuning, and MCP environment docs
    ├── cqrs-migration-walkthrough.md        # End-to-end brownfield monolith -> CQRS/ES tutorial
    └── troubleshooting.md                   # Common blocks, drift resolution, and diagnostics
```

---

## Quick Start

### 1. Install Prerequisites & Plugin Dependencies

Requires **Python 3.11+** and **[`uv`](https://docs.astral.sh/uv/)**:

**Linux / macOS / WSL:**
```bash
export PLUGIN_HOME="$HOME/.gemini/config/plugins/tdpm-sdd-governance"
git clone https://github.com/example-org/tdpm-sdd-governance.git "$PLUGIN_HOME"
uv --directory "$PLUGIN_HOME" sync
```

**Windows (PowerShell):**
```powershell
$env:PLUGIN_HOME = "$HOME\.gemini\config\plugins\tdpm-sdd-governance"
git clone https://github.com/example-org/tdpm-sdd-governance.git $env:PLUGIN_HOME
uv --directory $env:PLUGIN_HOME sync
```

### 2. Initialize Governance in Your Target Workspace

Bootstrap `.agents/state/phase-lock.json` at Phase 0 (brownfield migration) or Phase 1 (greenfield module):

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli init \
  --workspace ./modern-service \
  --project-name "github.com/example-org/account-platform" \
  --module "account" \
  --language go \
  --phase 0 \
  --paradigm CQRS_EVENT_SOURCING
```

*(Alternatively, if installed globally or in your environment, invoke `tdpm-sdd init --workspace ./modern-service ...` directly.)*

### 3. Inspect Ledger & Verify Active Gate

```bash
# View full Pydantic v2 state ledger JSON
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli status --workspace ./modern-service

# Run deterministic gate verification for the active module
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace ./modern-service
```

---

## Documentation Suite

- **[Getting Started Guide](docs/getting-started.md)**: Step-by-step installation, path configuration, workspace layout, and test suite execution.
- **[Stage-Gates & Lifecycle Reference](docs/stage-gates.md)**: Exhaustive state-machine reference covering Phases `P0`–`P5`, `PreToolUse` blocking rules, static audit rule IDs, and SHA-256 artifact locks.
- **[Configuration Reference](docs/configuration.md)**: Complete schema reference for `.agents/state/phase-lock.json`, `hooks.json`, `mcp_config.json`, CLI flags, and optional Google Antigravity SDK environment variables.
- **[CQRS Migration Walkthrough](docs/cqrs-migration-walkthrough.md)**: End-to-end tutorial migrating a legacy synchronous service (`legacy-service/`) to an event-sourced Go + PostgreSQL 16 CQRS service (`modern-service/`) across all 6 phases.
- **[Troubleshooting & Diagnostics](docs/troubleshooting.md)**: Resolving `PreToolUse` denials, `force_ask` prompts, SHA-256 lock drift, dialogue gates, and shell bypass blocks.

---

## Running the Plugin Verification Suite

Run the built-in unit test suite to verify hook interception, Gherkin purity checks, `SDD_STUB` enforcement, and the read-only MCP bridge:

```bash
uv run --directory "$PLUGIN_HOME" python -m unittest discover -s tests -v
```

---

## License

MIT License. Copyright (c) 2026 Antigravity Authors & Contributors. See [LICENSE](LICENSE) for details.
