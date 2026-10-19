# Getting Started with `tdpm-sdd-governance`

This guide walks you through installing the `tdpm-sdd-governance` plugin, configuring its MCP verification bridge, initializing a governed project workspace, and verifying that the `PreToolUse` gatekeeper and agent personas are active.

---

## 1. Prerequisites

Ensure the following tools are installed on your workstation:

- **Python**: `>= 3.11` (required by `pyproject.toml`)
- **`uv`**: Fast Python package and environment manager (`>= 0.4.0`)
- **Google Antigravity IDE / CLI**: Host environment supporting `plugin.json`, `hooks.json`, subagents, and MCP servers
- **Target Language Toolchain** (project-dependent):
  - Go (`>= 1.23` recommended for `language: "go"` workspaces)
  - Python (`>= 3.11` with Pydantic v2 for `language: "python"` workspaces)
  - TypeScript / Node.js (with Zod for `language: "typescript"` workspaces)

---

## 2. Installation

### Step 2.1: Clone into Your Antigravity Plugins Directory

Clone the repository into your Antigravity plugins directory. Throughout this documentation, `$PLUGIN_HOME` refers to the root directory of this plugin:

- **Linux / macOS / WSL**: `~/.gemini/config/plugins/tdpm-sdd-governance`
- **Windows (PowerShell)**: `$HOME\.gemini\config\plugins\tdpm-sdd-governance`

```bash
# Linux / macOS / WSL
export PLUGIN_HOME="$HOME/.gemini/config/plugins/tdpm-sdd-governance"
git clone https://github.com/your-org/tdpm-sdd-governance.git "$PLUGIN_HOME"

# Synchronize the isolated virtual environment (.venv) from uv.lock
uv --directory "$PLUGIN_HOME" sync
```

```powershell
# Windows PowerShell
$env:PLUGIN_HOME = "$HOME\.gemini\config\plugins\tdpm-sdd-governance"
git clone https://github.com/your-org/tdpm-sdd-governance.git $env:PLUGIN_HOME
uv --directory $env:PLUGIN_HOME sync
```

### Step 2.2: Configure `mcp_config.json`

The plugin includes an MCP server (`tdpm-sdk-bridge`) that exposes the read-only `run_sdk_verification_pipeline` tool. Update `mcp_config.json` in `$PLUGIN_HOME` so the `--directory` argument points to your installed `$PLUGIN_HOME` path:

```json
{
  "mcpServers": {
    "tdpm-sdk-bridge": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/.gemini/config/plugins/tdpm-sdd-governance",
        "run",
        "python",
        "-m",
        "tdpm_sdd.sdk_bridge"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### Step 2.3: Verify the Plugin Installation

Run the included unit test suite and CLI help command to confirm that `pydantic`, `pyyaml`, and `mcp` are properly installed and the `tdpm-sdd` entrypoint works:

```bash
uv run --directory "$PLUGIN_HOME" python -m unittest discover -s tests -v
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli --help
```

Expected test output:

```text
test_1_phase1_blocks_go_code_and_contaminated_blueprint ... ok
test_2_phase2_enforces_multi_round_bdd_dialogue_and_blocks_openapi ... ok
test_3_phase3_enforces_sdd_stubs_and_paradigm_minimalism ... ok
test_4_phase5a_red_harness_and_locked_artifact_protection ... ok
test_5_sdk_bridge_read_only_verification ... ok
----------------------------------------------------------------------
Ran 5 tests in 0.08s

OK
```

---

## 3. Target Workspace Directory Layout

When `tdpm-sdd-governance` governs a project workspace (e.g., `modern-service/`), it expects and enforces a deterministic artifact hierarchy across Phases `P0` through `P5`:

```text
modern-service/
├── .agents/
│   └── state/
│       └── phase-lock.json                          # Unified Pydantic v2 state ledger & SHA-256 locks
├── docs/
│   ├── architecture/
│   │   ├── LEGACY_DEPLOYMENT_REPORT.md              # [P0] Legacy runtime baseline report (brownfield)
│   │   ├── ARCHITECTURAL_VERIFICATION_REPORT.md     # [P0] Legacy defect & parity audit
│   │   ├── boundary-map.md                          # [P1] Ubiquitous Language, Subdomains & Context Map
│   │   ├── ARCHITECTURE_BLUEPRINT.md                # [P1-P3] Diagrams & invariants (Go blocks <=15 lines)
│   │   └── CUTOVER_AND_BENCHMARK_REPORT.md          # [P5c] Final chaos & benchmark verification report
│   └── uat/
│       └── UAT_PLAYBOOK.md                          # [P4] Pre-implementation executable UAT playbook
├── specs/
│   ├── ddd/
│   │   ├── arch-rules.yaml                          # [P1] Bounded Context & package dependency DAG rules
│   │   └── tactical-model-spec.md                   # [P3] Tactical DDD Aggregate, VO, Command/Event spec
│   ├── bdd/
│   │   ├── legacy-parity-triage.md                  # [P0] Bucket 1 (Preserve), Bucket 2 (Invert), Bucket 3 (Extend)
│   │   ├── example-map.md                           # [P2] Yellow (Rule), Green (Example), Red (Question) cards
│   │   └── event-modeling-and-pattern-gate.md       # [P2] Bridge 2.5a Timeline & Bridge 2.5b Pattern Gate
│   ├── features/
│   │   └── <module>.feature                         # [P2] Pure declarative Gherkin scenarios
│   ├── openapi/
│   │   └── <module>.v1.yaml                         # [P4] OpenAPI 3.1 synchronous REST contracts
│   └── asyncapi/
│       └── <module>-events.v1.yaml                  # [P4] AsyncAPI 3.0 event stream contracts
├── migrations/
│   ├── write/
│   │   └── 001_event_store_and_outbox.sql           # [P4] Write-side DDL (e.g. UNIQUE(aggregate_id, version))
│   └── read/
│       └── 001_projections_and_processed_events.sql # [P4] Read-side projection & idempotency DDL
├── internal/
│   ├── cqrs/                                        # Shared CQRS/Event Store/Outbox primitives
│   └── <module>/                                    # Module-scoped implementation (Go layout)
│       ├── common/                                  # Value Objects (e.g. Cents) & Domain Event structs
│       ├── cmd/
│       │   ├── domain/                              # Aggregate Roots (*_aggregate.go) & domain errors
│       │   ├── app/                                 # Command structs & Command handlers
│       │   └── infra/                               # Write-side repositories & HTTP command routers
│       └── query/
│           ├── domain/                              # Read projection models
│           ├── app/                                 # Query structs & Query handlers
│           └── infra/                               # Read-side repositories, consumers & HTTP query routers
└── test/
    └── verification/                                # [P5a/P5c] Cross-cutting BDD & chaos verification suites
```

> **Note on Non-Opt-In Workspaces**: If a workspace does **not** contain `.agents/state/phase-lock.json`, the `PreInvocation` and `PreToolUse` hooks immediately return `{}` / `{"decision": "allow"}`, leaving non-governed repositories completely unaffected.

---

## 4. Initializing a Workspace

You can initialize `.agents/state/phase-lock.json` in three common modes using `tdpm_sdd.cli init`:

### Mode A: Brownfield Migration (Start at Phase 0)

Use `--phase 0` when migrating or rewriting an existing service (`legacy-service/` $\rightarrow$ `modern-service/`) so `@pm-planner` begins with legacy behavior triage:

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli init \
  --workspace ./modern-service \
  --project-name "github.com/acme-corp/order-service" \
  --module "order" \
  --language go \
  --phase 0
```

### Mode B: Greenfield Feature / Module (Start at Phase 1)

Use `--phase 1` when starting a net-new bounded context with no legacy baseline to triage:

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli init \
  --workspace ./modern-service \
  --project-name "github.com/acme-corp/order-service" \
  --module "payment" \
  --language go \
  --phase 1
```

### Mode C: Baseline & Lock an Already-Completed Workspace (Phase 5 + `--lock-existing`)

If you are onboarding an existing repository that already satisfies the SDD architecture and want to lock its specifications, migrations, and verification tests against future regressions:

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli init \
  --workspace ./modern-service \
  --project-name "github.com/acme-corp/account-platform" \
  --module "account" \
  --language go \
  --phase 5 \
  --paradigm CQRS_EVENT_SOURCING \
  --lock-existing
```

When `--lock-existing` is passed, `init` computes normalized SHA-256 hashes for all matching files in:
- `docs/architecture/*.md`
- `docs/uat/*.md`
- `migrations/**/*.sql`
- `internal/<module>/**/*.go`
- `internal/cqrs/**/*.go`
- `test/verification/*.go`

---

## 5. Verifying Plugin Activation

Once `.agents/state/phase-lock.json` exists in your workspace, verify the three governance layers:

### 5.1 Verify `PreInvocation` Context Injection

Simulate an Antigravity `PreInvocation` hook event to confirm the ephemeral governance banner is injected before each agent turn:

```bash
echo '{"workspacePaths": ["./modern-service"]}' | \
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli hook pre-invocation
```

Expected output:

```json
{
  "injectSteps": [
    {
      "ephemeralMessage": "[TD/PM SDD GOVERNANCE ACTIVE | Project: github.com/acme-corp/order-service | Active Module: 'order' | Phase: 0 (P0_BROWNFIELD_DISCOVERY_AND_TRIAGE) | Owner: @pm-planner | Paradigm: UNSELECTED | BDD Rounds: 0/2]"
    }
  ]
}
```

### 5.2 Verify `PreToolUse` Out-of-Phase Protection

Simulate an attempt to write a Go file while the workspace is still in Phase 0:

```bash
echo '{
  "workspacePaths": ["./modern-service"],
  "toolCall": {
    "name": "write_to_file",
    "args": {
      "TargetFile": "./modern-service/internal/order/cmd/domain/order.go",
      "CodeContent": "package domain\n"
    }
  }
}' | uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli hook pre-tool-use
```

Expected output:

```json
{
  "decision": "deny",
  "reason": "SDD SEQUENCE BLOCK [Module 'order' is at Phase 0]: Cannot write Go file 'internal/order/cmd/domain/order.go' during Strategic DDD (Phase 1) or BDD Scenarios (Phase 2)."
}
```

### 5.3 Verify Interactive Agent Prompts

In the Antigravity chat session opened on `modern-service/`, run any of the suggested prompts defined in `plugin.json`:

- *"Check the current SDD phase lock status and module readiness"*
- *"Start Phase 1 Strategic DDD and Phase 2 Socratic BDD dialogue for a new module"*
- *"Run the TD/PM Gate Verification audit on the active module"*

---

## Next Steps

- Review **[Stage-Gates & Lifecycle Reference](stage-gates.md)** for a complete breakdown of every phase (`P0`–`P5`), gate check (`G0`–`G5`), and static audit rule.
- Walk through a full brownfield rewrite in **[CQRS Migration Walkthrough](cqrs-migration-walkthrough.md)**.
