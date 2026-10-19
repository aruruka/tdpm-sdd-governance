# Troubleshooting & Diagnostic Guide

This guide covers common gate blocks, `PreToolUse` denials, SHA-256 lock drift errors, and diagnostic commands when working with `tdpm-sdd-governance`.

---

## 1. Quick Diagnostic Commands

Before troubleshooting any blocked tool call or failed gate promotion, inspect the workspace state ledger and run the deterministic gate verifier:

```bash
# 1. Inspect the active module, current phase, dialogue counters, and locked hashes
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli status --workspace <workspace>

# 2. Run the static gate audit and view structured findings JSON
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace <workspace> --module <module_name>
```

---

## 2. Resolving Common `PreToolUse` Denials

### 2.1 `SDD PHASE 2 DIALOGUE GATE: Cannot write final '.feature' files yet`

- **Symptom**:
  ```text
  SDD PHASE 2 DIALOGUE GATE [Module 'account']: Cannot write final '.feature' files yet
  (rounds_completed=1/2, unresolved_questions=2). Complete the Socratic Example Mapping
  dialogue in 'specs/bdd/example-map.md' first.
  ```
- **Root Cause**: The agent attempted to create or edit `specs/features/*.feature` during Phase 2 before completing at least 2 rounds of Socratic Example Mapping dialogue with the human user or while `unresolved_questions` is still non-empty.
- **Resolution**:
  1. Update `specs/bdd/example-map.md` with the user's answers from `ask_question`.
  2. Record the completed dialogue round and clear resolved questions:
     ```bash
     uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli record-dialogue \
       --workspace <workspace> \
       --module <module_name> \
       --clear-questions
     ```

---

### 2.2 `SDD GHERKIN PURITY BLOCK` (`BDD-TRANSPORT-LEAKAGE`)

- **Symptom**:
  ```text
  SDD GHERKIN PURITY BLOCK: Transport/infrastructure term 'HTTP 200' leaked into Phase 2
  Gherkin spec. Write scenarios strictly in domain Ubiquitous Language.
  ```
- **Root Cause**: A `.feature` file contains transport or storage implementation details matching `GHERKIN_TRANSPORT_LEAK_RE`:
  - `HTTP <3-digit-code>` or `status code <3-digit-code>`
  - `SELECT `, `INSERT INTO`, or `UPDATE bank_accounts`
  - `pgx.`, `KafkaTopic`, or `localhost:<port>`
- **Resolution**: Rewrite the scenario in pure domain Ubiquitous Language (`Given` domain event history / `When` domain command is dispatched / `Then` domain event is emitted or domain error sentinel is returned). HTTP status code mappings belong to `specs/openapi/*.yaml` in Phase 4.

---

### 2.3 `SDD BLUEPRINT CONTAMINATION BLOCK` (`SDD-BLUEPRINT-NO-CODE-DUMP`)

- **Symptom**:
  ```text
  SDD BLUEPRINT CONTAMINATION BLOCK: Go code block contains 24 non-empty lines (max allowed
  in blueprint is 15 for interface signatures). Concrete implementation bodies are prohibited
  in Phase 1-3 blueprints.
  ```
- **Root Cause**: An edit to `docs/architecture/ARCHITECTURE_BLUEPRINT.md` during Phases `0`–`3` included a ` ```go ` code fence with more than 15 non-empty lines.
- **Resolution**: Replace large code dumps in `ARCHITECTURE_BLUEPRINT.md` with Mermaid sequence/state diagrams, invariant tables, or compact ($\le 15$ lines) port interface signatures.

---

### 2.4 `SDD-P3-STUB-ONLY` in Phase 3

- **Symptom**:
  ```text
  Function 'Withdraw' contains concrete implementation logic in Phase 3. All Phase 3 function
  bodies must be single-line `panic("SDD_STUB: ...")` stubs.
  ```
- **Root Cause**: In Phase 3 (`P3_TACTICAL_DDD_STUBS_AND_PORTS`), `audit_go_stub_only()` checks every Go function and method body in non-test files. Any non-comment body with more than 1 line or lacking the substring `"SDD_STUB"` is blocked.
- **Resolution**: Keep only type declarations, struct fields, interface definitions, and single-line stub bodies in Phase 3:
  ```go
  func (a *AccountAggregate) Withdraw(amount common.Cents) error {
      panic("SDD_STUB: implementation locked until Phase 5b")
  }
  ```

---

### 2.5 `SDD PHASE 5a RED-HARNESS GATE`

- **Symptom**:
  ```text
  SDD PHASE 5a RED-HARNESS GATE: Module 'account' is in sub-phase '5a_RED_HARNESS'.
  You may only write '*_test.go' files until the Red-Suite compilation & failure check passes.
  ```
- **Root Cause**: The module is in Phase 5 sub-phase `5a_RED_HARNESS`, where only `*_test.go` files can be authored.
- **Resolution**:
  1. Finish writing unit/BDD test files (`*_test.go`).
  2. Verify that `go test -c ./...` exits `0` and `go test ./internal/<module>/...` fails (`!= 0`) against the Phase 3 `SDD_STUB` panics.
  3. Promote the module from `5a_RED_HARNESS` to `5b_GREEN_IMPL`:
     ```bash
     uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase \
       --workspace <workspace> \
       --lock-files "internal/<module>/**/*_test.go" "test/verification/*_test.go"
     ```

---

### 2.6 `SDD SECURITY GATE: Direct shell mutation ... via 'run_command' is prohibited`

- **Symptom**:
  ```text
  SDD SECURITY GATE: Direct shell mutation of source/contract files or '.agents/state/phase-lock.json'
  via 'run_command' is prohibited. Use 'write_to_file' / 'replace_file_content' or the official
  'tdpm_sdd.cli' commands.
  ```
- **Root Cause**: An agent attempted to bypass `write_to_file` / `replace_file_content` checks by running shell redirection or PowerShell file-write cmdlets (`Out-File`, `Set-Content`, `Add-Content`, `New-Item`, or `> file.go/yaml/yml/feature/sql`) or touching `phase-lock.json` via `run_command`.
- **Resolution**: Always use Antigravity's native `write_to_file` and `replace_file_content` tools for source/spec edits, and use `uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli` for ledger updates.

---

## 3. Handling Locked Artifacts & SHA-256 Drift (`SDD-LOCK-DRIFT`)

### 3.1 Why `force_ask` Triggers on Locked Artifacts

When an artifact is locked via `promote-phase --lock-files ...`, its workspace-relative POSIX path and normalized SHA-256 digest (`sha256:<hex>`) are recorded in `modules.<module>.locked_artifacts`.

If an agent later calls `write_to_file` or `replace_file_content` on that path, `PreToolUse` returns:

```json
{
  "decision": "force_ask",
  "reason": "CONTRACT / ARTIFACT LOCK PROTECTION: 'specs/features/account.feature' is cryptographically locked in module 'account' (Phase 5). Modifying a locked upstream specification or verification test requires explicit human approval."
}
```

### 3.2 Re-Locking an Artifact After an Approved Human Change

If you explicitly approve an edit to a locked upstream specification (for example, fixing a typo in `boundary-map.md` or updating an OpenAPI description), subsequent runs of `verify-gate` will report `SDD-LOCK-DRIFT`:

```text
Cryptographic SHA-256 drift detected on locked artifact 'docs/architecture/boundary-map.md':
expected sha256:9f2d1e..., got sha256:3b7a4c...
```

To re-synchronize the SHA-256 digest in `.agents/state/phase-lock.json` after an authorized change, run a one-line Python snippet using `tdpm_sdd.models`:

```bash
uv run --directory "$PLUGIN_HOME" python -c '
from pathlib import Path
from tdpm_sdd.models import compute_sha256, load_ledger, save_ledger

ws = Path("./modern-service").resolve()
state = load_ledger(ws)
mod = state.get_active_module()
rel = "docs/architecture/boundary-map.md"
mod.locked_artifacts[rel] = compute_sha256(ws / rel)
save_ledger(ws, state)
print("Updated SHA-256 lock for", rel, "->", mod.locked_artifacts[rel])
'
```

*(Note: `compute_sha256` automatically normalizes `\r\n` to `\n` before hashing so hashes remain identical across Windows, macOS, and Linux.)*

---

## 4. Manual Bypass Policies (`--force`)

In exceptional architectural recovery scenarios where you need to promote a phase despite a non-passing static check, `promote-phase` supports `--force`:

```bash
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase \
  --workspace <workspace> \
  --module <module_name> \
  --force
```

**Governance Policy**:
- Autonomous agents (`@td-pm`, `@pm-planner`, `@td-auditor`) are strictly forbidden by `rules/AGENTS.md` from passing `--force` on their own.
- `--force` may only be executed when explicitly instructed by the human developer.

---

## 5. Multi-Module Routing Edge Cases

- **Symptom**: You added a second module (e.g., `profile`) via `add-module`, but edits to shared files (such as `docs/architecture/ARCHITECTURE_BLUEPRINT.md`) are still evaluated against the first module (`account`).
- **Root Cause**: Files that do not contain a specific module name in their path (`internal/<module>/...` or `\b<module>\b`) fall back to `state.active_module`.
- **Resolution**: Pass `--activate` when running `add-module`, or switch `active_module` when shifting focus between modules:
  ```bash
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli add-module \
    --workspace ./modern-service \
    --module profile \
    --language go \
    --phase 1 \
    --activate
  ```
