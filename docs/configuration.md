# Configuration & CLI Reference

This document specifies all configuration files, Pydantic v2 state schemas, CLI subcommands, lifecycle hook configurations, and MCP environment settings used by `tdpm-sdd-governance`.

---

## 1. Unified State Ledger Schema (`.agents/state/phase-lock.json`)

The single source of truth for workspace governance is stored at `<workspace>/.agents/state/phase-lock.json`. It is strictly validated by Pydantic v2 (`ConfigDict(extra="forbid")`) in [`src/tdpm_sdd/models.py`](../src/tdpm_sdd/models.py).

### 1.1 Example `phase-lock.json`

```json
{
  "schema_version": "2.0",
  "project_name": "github.com/acme-corp/ledger-platform",
  "default_module": "account",
  "active_module": "account",
  "adrs": [
    {
      "adr_id": "ADR-001",
      "title": "Go 1.23+ & PostgreSQL 16 Consolidated Event Store + Outbox Architecture",
      "status": "accepted",
      "artifact_path": "docs/architecture/ARCHITECTURE_BLUEPRINT.md",
      "decided_by": "td-auditor",
      "created_at": "2026-10-19T10:00:00+00:00"
    }
  ],
  "backlog": [
    {
      "item_id": "BL-001",
      "module": "notification",
      "title": "Webhook Notification Delivery Slice",
      "priority": "P1",
      "status": "planned"
    }
  ],
  "modules": {
    "account": {
      "module_name": "account",
      "language": "go",
      "current_phase": 2,
      "phase_name": "P2_ITERATIVE_BDD_AND_PATTERN_GATE",
      "sub_phase": null,
      "active_owner": "pm-planner",
      "gates_passed": [
        "G0",
        "G1"
      ],
      "bdd_dialogue": {
        "rounds_completed": 2,
        "required_minimum_rounds": 2,
        "unresolved_questions": [],
        "pattern_selection_approved": true,
        "selected_paradigm": "CQRS_EVENT_SOURCING",
        "coordination_scope": "SINGLE_AGGREGATE"
      },
      "locked_artifacts": {
        "specs/bdd/legacy-parity-triage.md": "sha256:4a8b9c...",
        "docs/architecture/boundary-map.md": "sha256:9f2d1e...",
        "specs/ddd/arch-rules.yaml": "sha256:7c3e5a..."
      },
      "updated_at": "2026-10-19T10:15:00+00:00"
    }
  }
}
```

### 1.2 Root Model: `WorkspaceGovernanceState`

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `schema_version` | `str` | `"2.0"` | Ledger schema version identifier. |
| `project_name` | `str` | *(required)* | Canonical repository or module identifier (e.g., `"github.com/acme-corp/ledger-platform"`). |
| `default_module` | `str` | `"account"` | Fallback module name when initializing the workspace. |
| `active_module` | `str` | `"account"` | Key in `modules` currently targeted by default CLI commands and `PreInvocation` banners. |
| `adrs` | `list[ADRRecord]` | `[]` | Architecture Decision Records tracked in the workspace. |
| `backlog` | `list[BacklogItem]` | `[]` | Product roadmap / backlog items managed by `@pm-planner`. |
| `modules` | `dict[str, ModuleSDDState]` | `{}` | Map of module name to its `ModuleSDDState` configuration. |

### 1.3 Module Model: `ModuleSDDState`

| Field | Type | Default | Allowed Values / Constraints |
| :--- | :--- | :--- | :--- |
| `module_name` | `str` | *(required)* | Non-empty module identifier (maps to `internal/<module_name>/`). |
| `language` | `SupportedLanguage` | `"go"` | `"go"`, `"python"`, `"typescript"` |
| `current_phase` | `int` | `0` | Integer `0` through `5`. |
| `phase_name` | `str` | `"P0_BROWNFIELD_DISCOVERY_AND_TRIAGE"` | Canonical phase name from `PHASE_NAMES`. |
| `sub_phase` | `Phase5SubPhase \| null` | `null` | `"5a_RED_HARNESS"`, `"5b_GREEN_IMPL"`, `"5c_VERIFICATION"`, or `null` (when `current_phase < 5`). |
| `active_owner` | `AgentPersona` | `"pm-planner"` | `"td-pm"`, `"pm-planner"`, `"td-auditor"`, `"sdk-architect"` |
| `gates_passed` | `list[str]` | `[]` | List of completed gate IDs (e.g., `["G0", "G1", "G2"]`). |
| `bdd_dialogue` | `BDDDialogueState` | `BDDDialogueState()` | Nested Socratic BDD and Bridge 2.5b Pattern Gate state. |
| `locked_artifacts` | `dict[str, str]` | `{}` | Map of workspace-relative POSIX path to `"sha256:<hex>"` digest. |
| `updated_at` | `str` | UTC ISO-8601 | Timestamp of last state mutation. |

### 1.4 Dialogue & Pattern Gate Model: `BDDDialogueState`

| Field | Type | Default | Allowed Values / Description |
| :--- | :--- | :--- | :--- |
| `rounds_completed` | `int` | `0` | Number of completed Socratic BDD dialogue rounds (`>= 0`). |
| `required_minimum_rounds` | `int` | `2` | Minimum dialogue rounds required before `.feature` authoring (`>= 1`). |
| `unresolved_questions` | `list[str]` | `[]` | Open Red Question Cards from `specs/bdd/example-map.md`. Must be `[]` to unlock `.feature` authoring and pass Gate `G2`. |
| `pattern_selection_approved` | `bool` | `false` | Set to `true` when `select-pattern` locks Bridge 2.5b. |
| `selected_paradigm` | `TacticalParadigm \| null` | `null` | `"CQRS_EVENT_SOURCING"`, `"STATE_BASED_OCC"`, `"VERTICAL_SLICE_CRUD"`, or `null`. |
| `coordination_scope` | `Literal` | `"SINGLE_AGGREGATE"` | `"SINGLE_AGGREGATE"`, `"PROCESS_MANAGER_SAGA"`, or `"CRUD_DIRECT"`. |

---

## 2. CLI Reference (`tdpm-sdd` / `python -m tdpm_sdd.cli`)

All state mutations should be executed via the CLI rather than hand-editing `.agents/state/phase-lock.json` (direct edits to `phase-lock.json` via `write_to_file` or `replace_file_content` trigger a `force_ask` prompt, and shell redirection to `phase-lock.json` is hard-denied).

Invoke the CLI via `uv`:

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli <subcommand> [options]
```

### 2.1 `init` — Initialize Workspace Ledger

Creates `.agents/state/phase-lock.json` in the target workspace.

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli init \
  --workspace <path> \
  --project-name <name> \
  --module <module_name> \
  --language {go,python,typescript} \
  --phase {0,1,2,3,4,5} \
  --paradigm {CQRS_EVENT_SOURCING,STATE_BASED_OCC,VERTICAL_SLICE_CRUD} \
  [--lock-existing] \
  [--force]
```

- `--workspace`: Target workspace root directory (default: `"."`).
- `--project-name`: Project identifier (default: `"github.com/example-org/account-platform"`).
- `--module`: Initial module name (default: `"account"`).
- `--language`: Target stack (`go`, `python`, `typescript`; default: `"go"`).
- `--phase`: Starting phase `0`–`5` (default: `5`).Note: When initializing at `--phase 5`, `sub_phase` is initialized to `"5c_VERIFICATION"`, `rounds_completed` is set to `2`, and `pattern_selection_approved` is set to `True`. When initializing at `--phase 0`, `1`, or `2`, `selected_paradigm` starts as `None` until `select-pattern` is run in Phase 2.
- `--paradigm`: Tactical paradigm applied if `--phase >= 3` (default: `"CQRS_EVENT_SOURCING"`).
- `--lock-existing`: Computes and locks SHA-256 hashes for existing architecture docs, UAT docs, SQL migrations, module Go files, and verification tests.
- `--force`: Overwrite an existing `.agents/state/phase-lock.json` file (exits with code `1` if file exists and `--force` is omitted).

### 2.2 `status` — Inspect Current Ledger

Prints the formatted JSON representation of `.agents/state/phase-lock.json`.

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli status --workspace <path>
```

- Exit code `0` if ledger exists; `1` if missing.

### 2.3 `add-module` — Register an Additional Bounded Context / Module

Adds a new module to an existing `phase-lock.json` ledger so multi-module repositories can govern each bounded context independently (e.g., `account` on `CQRS_EVENT_SOURCING` at Phase 5 while `profile` starts at Phase 1).

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli add-module \
  --workspace <path> \
  --module <new_module_name> \
  [--language {go,python,typescript}] \
  [--phase {0,1,2,3,4,5}] \
  [--activate]
```

- `--module`: *(required)* Name of the new module.
- `--language`: Language stack (default: `"go"`).
- `--phase`: Initial phase for the new module (default: `1`).
- `--activate`: Immediately set `active_module` to this new module.

### 2.4 `record-dialogue` — Record a Socratic BDD Dialogue Round

Increments `bdd_dialogue.rounds_completed` by `1` and updates or clears `unresolved_questions`.

```bash
# Record Round 1 with open Red Question Cards
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli record-dialogue \
  --workspace <path> \
  [--module <module_name>] \
  --questions "Q1: ..." "Q2: ..."

# Record Round 2 and clear all resolved questions
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli record-dialogue \
  --workspace <path> \
  [--module <module_name>] \
  --clear-questions
```

### 2.5 `select-pattern` — Lock Bridge 2.5b Tactical Pattern Gate

Sets `selected_paradigm`, `coordination_scope`, and `pattern_selection_approved = True` for the target module.

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli select-pattern \
  --workspace <path> \
  [--module <module_name>] \
  --paradigm {CQRS_EVENT_SOURCING,STATE_BASED_OCC,VERTICAL_SLICE_CRUD} \
  [--scope {SINGLE_AGGREGATE,PROCESS_MANAGER_SAGA,CRUD_DIRECT}]
```

### 2.6 `verify-gate` — Run Deterministic Gate Auditor

Executes `run_module_gate_verification` for the target module's current phase and prints a structured `GateAuditReport` JSON payload.

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate \
  --workspace <path> \
  [--module <module_name>]
```

- Exit code `0` when `passed == true` (zero `ERROR` findings).
- Exit code `2` when `passed == false`.
- Exit code `1` when `phase-lock.json` is missing.

### 2.7 `promote-phase` — Lock Artifacts by SHA-256 and Advance Phase

Runs `verify-gate`, computes normalized SHA-256 hashes for all files matching `--lock-files` globs, records the passed gate (`G0`–`G5`), and advances the module's phase or Phase 5 sub-phase (`5a_RED_HARNESS` $\rightarrow$ `5b_GREEN_IMPL` $\rightarrow$ `5c_VERIFICATION`).

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase \
  --workspace <path> \
  [--module <module_name>] \
  [--lock-files <glob1> <glob2> ...] \
  [--force]
```

- Refuses to advance and exits with code `2` if `verify-gate` fails, unless `--force` is explicitly provided.

### 2.8 `hook` — Internal Antigravity Lifecycle Hook Entrypoint

Invoked automatically by Antigravity via `hooks.json`. Reads JSON from `stdin` and writes the hook decision JSON to `stdout`:

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli hook {pre-invocation,pre-tool-use,stop}
```

---

## 3. Lifecycle Hook Configuration (`hooks.json`)

[`hooks.json`](../hooks.json) registers three lifecycle hooks under `"tdpm-sdd-gatekeeper"`:

```json
{
  "tdpm-sdd-gatekeeper": {
    "enabled": true,
    "PreInvocation": [
      {
        "type": "command",
        "command": "uv run python -m tdpm_sdd.cli hook pre-invocation",
        "timeout": 10
      }
    ],
    "PreToolUse": [
      {
        "matcher": "write_to_file|replace_file_content|run_command",
        "hooks": [
          {
            "type": "command",
            "command": "uv run python -m tdpm_sdd.cli hook pre-tool-use",
            "timeout": 15
          }
        ]
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "uv run python -m tdpm_sdd.cli hook stop",
        "timeout": 10
      }
    ]
  }
}
```

### Multi-Module Path Resolution in `PreToolUse`

When a workspace contains multiple modules in `phase-lock.json`, `_infer_target_module()` in [`src/tdpm_sdd/gatekeeper.py`](../src/tdpm_sdd/gatekeeper.py) resolves which module owns a target file in the following priority order:
1. **Explicit Internal Path**: `internal/<module_name>/...` where `<module_name>` is a key in `state.modules`.
2. **Word-Boundary Match**: Any relative path containing `\b<module_name>\b` (e.g., `specs/features/transfer.feature` maps to module `transfer`).
3. **Active Module Fallback**: Falls back to `state.active_module`.

---

## 4. MCP Verification Bridge (`mcp_config.json` & `sdk_bridge.py`)

The `tdpm-sdk-bridge` FastMCP server exposes one tool to `@sdk-architect` and the host agent:

### Tool: `run_sdk_verification_pipeline`

- **Parameters**:
  - `workspace_dir` (`str`, required): Absolute path to the target governed workspace.
  - `module_name` (`str`, default `"account"`): Target module name in `phase-lock.json`.
  - `focus_area` (`Literal["traceability", "encapsulation", "contracts", "full_gate"]`, default `"full_gate"`): Audit scope.

### Execution Modes & Environment Variables

`run_sdk_verification_pipeline` always executes the deterministic zero-token Python AST, Gherkin, YAML Contract, and SHA-256 verification suite first. If the `google-antigravity` Python SDK is installed in the environment and credentials are provided, it additionally launches a strictly read-only nested `Agent` (restricted to `view_file`, `code_search`, `check_file_metrics`, and `run_deterministic_gate_check` via `@hooks.pre_tool_call_decide` and `policy.deny_all()`):

| Environment Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `PYTHONUNBUFFERED` | Recommended | `"1"` | Ensures unbuffered stdio communication for the FastMCP server. |
| `GEMINI_API_KEY` | Optional | *unset* | Enables nested read-only Google Antigravity SDK semantic audits via Gemini API. |
| `GOOGLE_CLOUD_PROJECT` | Optional | *unset* | Enables nested read-only Google Antigravity SDK semantic audits via Vertex AI. |
| `GOOGLE_CLOUD_LOCATION` | Optional | `"us-central1"` | Vertex AI region when `GOOGLE_CLOUD_PROJECT` is set. |

When neither `GEMINI_API_KEY` nor `GOOGLE_CLOUD_PROJECT` is set (or when `google-antigravity` is not installed), `run_sdk_verification_pipeline` completes in **zero-token deterministic mode**, returning full AST, Gherkin, Contract, and SHA-256 findings without external API calls.
