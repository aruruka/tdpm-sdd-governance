"""Deterministic PreToolUse, PreInvocation, and Stop lifecycle hook gatekeeper for Antigravity."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .auditors import (
    audit_blueprint_no_code_dump,
    audit_gherkin_purity,
    audit_go_cqrs_encapsulation,
    audit_go_stub_only,
    audit_vertical_slice_minimalism,
)
from .models import ModuleSDDState, WorkspaceGovernanceState, load_ledger

SHELL_WRITE_BYPASS_RE = re.compile(
    r"(Out-File|Set-Content|Add-Content|New-Item\s+.*\.(go|yaml|yml|feature|sql)|tee\s+.*\.(go|yaml|yml|feature|sql)|touch\s+.*\.(go|yaml|yml|feature|sql)|>\s*[^\s&|]+\.(go|yaml|yml|feature|sql)|phase-lock\.json)",
    re.IGNORECASE,
)


def _extract_workspace_root(payload: dict[str, Any]) -> Path | None:
    paths = payload.get("workspacePaths") or []
    if paths:
        first = str(paths[0]).removeprefix("file:///")
        return Path(first).resolve()
    return None


def _normalize_rel_path(target_file: str, workspace_root: Path) -> str:
    try:
        p = Path(target_file)
        resolved = (p if p.is_absolute() else (workspace_root / p)).resolve()
        return resolved.relative_to(workspace_root.resolve()).as_posix()
    except (ValueError, RuntimeError):
        return target_file.replace("\\", "/")


def _infer_target_module(rel_path: str, state: WorkspaceGovernanceState) -> ModuleSDDState:
    """Maps a relative file path to its owning module in phase-lock.json, defaulting to active_module."""
    parts = rel_path.split("/")
    if len(parts) >= 2 and parts[0] == "internal" and parts[1] in state.modules:
        return state.modules[parts[1]]
    for mod_name, mod_state in state.modules.items():
        if re.search(rf"\b{re.escape(mod_name)}\b", rel_path, re.IGNORECASE):
            return mod_state
    return state.get_active_module()


def handle_pre_invocation(payload: dict[str, Any]) -> dict[str, Any]:
    """Injects an ephemeral phase-governance banner before each model turn if phase-lock.json is present."""
    ws = _extract_workspace_root(payload)
    if not ws:
        return {}
    state = load_ledger(ws)
    if not state:
        return {}
    mod = state.get_active_module()
    sub = f" [{mod.sub_phase}]" if mod.sub_phase else ""
    paradigm = mod.bdd_dialogue.selected_paradigm or "UNSELECTED"
    msg = (
        f"[TD/PM SDD GOVERNANCE ACTIVE | Project: {state.project_name} | Active Module: '{mod.module_name}' | "
        f"Phase: {mod.current_phase} ({mod.phase_name}{sub}) | Owner: @{mod.active_owner} | "
        f"Paradigm: {paradigm} | BDD Rounds: {mod.bdd_dialogue.rounds_completed}/{mod.bdd_dialogue.required_minimum_rounds}]"
    )
    return {"injectSteps": [{"ephemeralMessage": msg}]}


def handle_pre_tool_use(payload: dict[str, Any]) -> dict[str, Any]:
    """Intercepts write_to_file, replace_file_content, and run_command against the unified SDD state ledger."""
    tool_call = payload.get("toolCall") or {}
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args") or {}

    ws = _extract_workspace_root(payload)
    if not ws:
        return {"decision": "allow"}

    # Also check if TargetFile or Cwd belongs to another workspace that has a phase-lock.json
    candidate_roots = [ws]
    target_arg = args.get("TargetFile") or args.get("Cwd")
    if target_arg:
        p = Path(str(target_arg)).resolve()
        for parent in [p] + list(p.parents):
            if (parent / ".agents" / "state" / "phase-lock.json").exists():
                if parent not in candidate_roots:
                    candidate_roots.insert(0, parent)
                break

    active_ws: Path | None = None
    state: WorkspaceGovernanceState | None = None
    for root in candidate_roots:
        loaded = load_ledger(root)
        if loaded is not None:
            active_ws = root
            state = loaded
            break

    if not state or not active_ws:
        return {"decision": "allow"}

    # 1. Intercept shell bypasses on run_command
    if tool_name == "run_command":
        cmd_line = str(args.get("CommandLine", ""))
        # Allow legitimate CLI invocations of tdpm_sdd.cli
        if "tdpm_sdd.cli" in cmd_line or "tdpm-sdd" in cmd_line:
            return {"decision": "allow"}
        if SHELL_WRITE_BYPASS_RE.search(cmd_line):
            return {
                "decision": "deny",
                "reason": (
                    "SDD SECURITY GATE: Direct shell mutation of source/contract files or '.agents/state/phase-lock.json' "
                    "via 'run_command' is prohibited. Use 'write_to_file' / 'replace_file_content' or the official 'tdpm_sdd.cli' commands."
                ),
            }
        return {"decision": "allow"}

    # 2. Intercept file mutations (write_to_file / replace_file_content)
    if tool_name not in ("write_to_file", "replace_file_content"):
        return {"decision": "allow"}

    target_file = str(args.get("TargetFile", ""))
    if not target_file:
        return {"decision": "allow"}

    rel_path = _normalize_rel_path(target_file, active_ws)
    content = str(
        args.get("CodeContent") or args.get("ReplacementContent") or ""
    )

    # Protect direct hand-edits to phase-lock.json unless approved
    if rel_path.endswith(".agents/state/phase-lock.json"):
        return {
            "decision": "force_ask",
            "reason": "Direct edit to '.agents/state/phase-lock.json' detected. Prefer 'uv run python -m tdpm_sdd.cli' state commands.",
        }

    mod = _infer_target_module(rel_path, state)
    phase = mod.current_phase

    # 3. Check if file is already cryptographically locked in any module
    for m_name, m_state in state.modules.items():
        if rel_path in m_state.locked_artifacts:
            return {
                "decision": "force_ask",
                "reason": (
                    f"CONTRACT / ARTIFACT LOCK PROTECTION: '{rel_path}' is cryptographically locked in module '{m_name}' "
                    f"(Phase {m_state.current_phase}). Modifying a locked upstream specification or verification test requires explicit human approval."
                ),
            }

    # 4. Enforce Blueprint No-Code-Dump rule in Phases 0-3
    if rel_path.endswith("ARCHITECTURE_BLUEPRINT.md") and phase <= 3:
        findings = audit_blueprint_no_code_dump(content, rel_path)
        if findings:
            return {
                "decision": "deny",
                "reason": f"SDD BLUEPRINT CONTAMINATION BLOCK: {findings[0].message}",
            }

    # 5. Enforce Phase-Specific Path & Content Rules
    is_gherkin = rel_path.endswith(".feature")
    is_openapi_or_asyncapi = rel_path.startswith(("specs/openapi/", "specs/asyncapi/"))
    is_sql_migration = rel_path.startswith("migrations/") and rel_path.endswith(".sql")
    is_go_file = rel_path.endswith(".go")
    is_go_test = rel_path.endswith("_test.go")

    # Rule A: Gherkin .feature files (Belong to Phase 2 after >=2 dialogue rounds)
    if is_gherkin:
        if phase < 2:
            return {
                "decision": "deny",
                "reason": (
                    f"SDD SEQUENCE BLOCK [Module '{mod.module_name}' is at Phase {phase}]: "
                    "Cannot write Gherkin '.feature' files before Phase 1 (Strategic DDD boundary-map.md) is locked."
                ),
            }
        if phase == 2:
            if (
                mod.bdd_dialogue.rounds_completed
                < mod.bdd_dialogue.required_minimum_rounds
                or len(mod.bdd_dialogue.unresolved_questions) > 0
            ):
                return {
                    "decision": "deny",
                    "reason": (
                        f"SDD PHASE 2 DIALOGUE GATE [Module '{mod.module_name}']: Cannot write final '.feature' files yet "
                        f"(rounds_completed={mod.bdd_dialogue.rounds_completed}/{mod.bdd_dialogue.required_minimum_rounds}, "
                        f"unresolved_questions={len(mod.bdd_dialogue.unresolved_questions)}). "
                        "Complete the Socratic Example Mapping dialogue in 'specs/bdd/example-map.md' first."
                    ),
                }
            findings = audit_gherkin_purity(content, rel_path)
            if findings:
                return {
                    "decision": "deny",
                    "reason": f"SDD GHERKIN PURITY BLOCK: {findings[0].message}",
                }

    # Rule B: OpenAPI, AsyncAPI, and SQL DDL Contracts (Belong to Phase 4, AFTER Phase 2 BDD & Phase 3 Tactical DDD)
    if (is_openapi_or_asyncapi or is_sql_migration) and phase < 4:
        return {
                "decision": "deny",
                "reason": (
                    f"SDD SEQUENCE BLOCK [Module '{mod.module_name}' is at Phase {phase}]: "
                    f"Cannot write interface/storage contract '{rel_path}' before Phase 2 (BDD Scenarios) and "
                    "Phase 3 (Tactical DDD Aggregates, Commands, and Events) are locked. Designing contracts before "
                    "BDD and Tactical DDD causes contract churn!"
                ),
            }

    # Rule C: Go Source & Test Files
    if is_go_file:
        if phase < 3:
            return {
                "decision": "deny",
                "reason": (
                    f"SDD SEQUENCE BLOCK [Module '{mod.module_name}' is at Phase {phase}]: "
                    f"Cannot write Go file '{rel_path}' during Strategic DDD (Phase 1) or BDD Scenarios (Phase 2)."
                ),
            }

        # Check paradigm-specific rules
        if mod.bdd_dialogue.selected_paradigm == "VERTICAL_SLICE_CRUD":
            v_findings = audit_vertical_slice_minimalism(content, rel_path)
            if v_findings:
                return {
                    "decision": "deny",
                    "reason": v_findings[0].message,
                }
        elif mod.bdd_dialogue.selected_paradigm == "CQRS_EVENT_SOURCING":
            c_findings = audit_go_cqrs_encapsulation(content, rel_path)
            if c_findings:
                return {
                    "decision": "deny",
                    "reason": f"SDD TACTICAL DDD VIOLATION: {c_findings[0].message}",
                }

        if phase == 3:
            if is_go_test:
                return {
                    "decision": "deny",
                    "reason": (
                        "SDD PHASE 3 BLOCK: Executable '*_test.go' harnesses belong to Phase 5a (after Phase 4 OpenAPI/AsyncAPI contracts are locked)."
                    ),
                }
            stub_findings = audit_go_stub_only(content, rel_path)
            if stub_findings:
                return {
                    "decision": "deny",
                    "reason": stub_findings[0].message,
                }

        if phase == 4:
            return {
                "decision": "deny",
                "reason": (
                    f"SDD PHASE 4 BLOCK: Phase 4 is strictly for OpenAPI 3.1, AsyncAPI 3.0, SQL DDL, and UAT Playbook authoring. "
                    f"Cannot modify Go file '{rel_path}' in Phase 4."
                ),
            }

        if phase == 5 and mod.sub_phase == "5a_RED_HARNESS" and not is_go_test:
            return {
                "decision": "deny",
                "reason": (
                    f"SDD PHASE 5a RED-HARNESS GATE: Module '{mod.module_name}' is in sub-phase '5a_RED_HARNESS'. "
                    "You may only write '*_test.go' files until the Red-Suite compilation & failure check passes."
                ),
            }

    return {"decision": "allow"}


def handle_stop(payload: dict[str, Any]) -> dict[str, Any]:
    """Allows normal turn stop; can be extended for autonomous gate loops."""
    _ = payload
    return {"decision": "allow"}


def dispatch_hook(event_name: str, stdin_raw: str) -> str:
    """Dispatches a hook event from stdin JSON and returns stdout JSON string."""
    payload = json.loads(stdin_raw) if stdin_raw.strip() else {}
    if event_name == "pre-invocation":
        res = handle_pre_invocation(payload)
    elif event_name == "pre-tool-use":
        res = handle_pre_tool_use(payload)
    elif event_name == "stop":
        res = handle_stop(payload)
    else:
        res = {}
    return json.dumps(res)
