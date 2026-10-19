---
name: sdd-cqrs-gate
description: >-
  Executes deterministic Gate Verification (Gates G0 through G5), manages Phase 5
  sub-phases (5a Red Test Harness -> 5b Inside-Out Implementation -> 5c Chaos &
  Cutover Verification), and promotes phases with cryptographic SHA-256 locking.
---

# SDD Gatekeeper & Phase Promotion Skill (`G0` -> `G5`)

Use this skill whenever verifying readiness to transition between SDD phases or managing Phase 5 sub-phases (`5a_RED_HARNESS` -> `5b_GREEN_IMPL` -> `5c_VERIFICATION`).

## Step 1: Run Deterministic Gate Verification
Execute the unified Python gate verifier:
```powershell
uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli verify-gate --workspace <workspace_path> --module <module_name>
```
Optionally, delegate to `sdk-architect` (`run_sdk_verification_pipeline`) for a read-only cross-artifact traceability sweep.

## Step 2: Interactive Architect Sign-Off (`ask_question`)
If `verify-gate` returns `"passed": true` (exit code `0`), present the verification summary to the user via Antigravity's `ask_question` tool and ask for approval to lock the current phase's artifacts and advance to the next phase.

## Step 3: Cryptographic Lock & Phase Promotion
Once approved by the user, run `promote-phase` passing the glob patterns of the artifacts completed in the current phase so their SHA-256 hashes are locked into `.agents/state/phase-lock.json`:

- **Promote Gate G1 (Phase 1 -> Phase 2)**:
  ```powershell
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace <workspace> --lock-files "docs/architecture/boundary-map.md" "specs/ddd/arch-rules.yaml"
  ```
- **Promote Gate G2 (Phase 2 -> Phase 3)**:
  ```powershell
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace <workspace> --lock-files "specs/bdd/*.md" "specs/features/*.feature"
  ```
- **Promote Gate G3 (Phase 3 -> Phase 4)**:
  ```powershell
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace <workspace> --lock-files "specs/ddd/tactical-*.md" "docs/architecture/ARCHITECTURE_BLUEPRINT.md"
  ```
- **Promote Gate G4 (Phase 4 -> Phase 5a Red Harness)**:
  ```powershell
  uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace <workspace> --lock-files "specs/openapi/*.yaml" "specs/asyncapi/*.yaml" "migrations/**/*.sql" "docs/uat/UAT_PLAYBOOK.md"
  ```
- **Promote Sub-Gate G5a (`5a_RED_HARNESS` -> `5b_GREEN_IMPL`)**:
  1. Verify `go test -c ./...` exits `0` (tests compile against Phase 3 stubs).
  2. Verify `go test ./internal/<module>/...` exits `!= 0` (proving Red failure on `SDD_STUB`).
  3. Lock test harnesses and unlock production Go implementation:
     ```powershell
     uv run --directory "$PLUGIN_HOME" python -m tdpm_sdd.cli promote-phase --workspace <workspace> --lock-files "test/verification/*_test.go"
     ```
