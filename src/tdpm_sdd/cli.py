"""Unified CLI for TD/PM & SDD Governance hooks, state transitions, and gate verification."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from .auditors import run_module_gate_verification
from .gatekeeper import dispatch_hook
from .models import (
    PHASE_NAMES,
    PHASE_OWNERS,
    ADRRecord,
    BDDDialogueState,
    ModuleSDDState,
    WorkspaceGovernanceState,
    compute_sha256,
    load_ledger,
    save_ledger,
)


def cmd_hook(args: argparse.Namespace) -> int:
    stdin_raw = sys.stdin.read()
    out = dispatch_hook(args.event, stdin_raw)
    sys.stdout.write(out + "\n")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    ws = Path(args.workspace).resolve()
    existing = load_ledger(ws)
    if existing and not args.force:
        print(f"Ledger already exists at {ws / '.agents/state/phase-lock.json'}. Use --force to overwrite.")
        return 1

    phase = args.phase
    mod_state = ModuleSDDState(
        module_name=args.module,
        language=args.language,
        current_phase=phase,
        phase_name=PHASE_NAMES[phase],
        sub_phase="5c_VERIFICATION" if phase == 5 else None,
        active_owner=PHASE_OWNERS[phase],
        gates_passed=[f"G{i}" for i in range(phase)],
        bdd_dialogue=BDDDialogueState(
            rounds_completed=2 if phase >= 3 else 0,
            required_minimum_rounds=2,
            unresolved_questions=[],
            pattern_selection_approved=phase >= 3,
            selected_paradigm=args.paradigm if phase >= 3 else None,
        ),
    )

    if args.lock_existing:
        lock_patterns = [
            "docs/architecture/*.md",
            "docs/uat/*.md",
            "migrations/**/*.sql",
            f"internal/{args.module}/**/*.go",
            "internal/cqrs/**/*.go",
            "test/verification/*.go",
        ]
        for pat in lock_patterns:
            for fp in sorted(ws.glob(pat)):
                if fp.is_file():
                    rel = fp.relative_to(ws).as_posix()
                    mod_state.locked_artifacts[rel] = compute_sha256(fp)

    state = WorkspaceGovernanceState(
        project_name=args.project_name,
        default_module=args.module,
        active_module=args.module,
        adrs=[
            ADRRecord(
                adr_id="ADR-001",
                title="Go 1.23+ & PostgreSQL 16 Consolidated Event Store + Outbox Architecture",
                status="accepted",
                artifact_path="docs/architecture/ARCHITECTURE_BLUEPRINT.md",
                decided_by="td-auditor",
            )
        ],
        modules={args.module: mod_state},
    )
    out_path = save_ledger(ws, state)
    print(f"Initialized unified TD/PM SDD state ledger at: {out_path}")
    print(f"Locked {len(mod_state.locked_artifacts)} existing artifacts for module '{args.module}'.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ws = Path(args.workspace).resolve()
    state = load_ledger(ws)
    if not state:
        print(f"No phase-lock.json found in {ws}")
        return 1
    print(state.model_dump_json(indent=2))
    return 0


def cmd_add_module(args: argparse.Namespace) -> int:
    ws = Path(args.workspace).resolve()
    state = load_ledger(ws)
    if not state:
        print(f"No phase-lock.json found in {ws}. Run 'init' first.")
        return 1
    state.modules[args.module] = ModuleSDDState(
        module_name=args.module,
        language=args.language,
        current_phase=args.phase,
        phase_name=PHASE_NAMES[args.phase],
        active_owner=PHASE_OWNERS[args.phase],
    )
    if args.activate:
        state.active_module = args.module
    save_ledger(ws, state)
    print(f"Added module '{args.module}' at Phase {args.phase} ({PHASE_NAMES[args.phase]}).")
    return 0


def cmd_record_dialogue(args: argparse.Namespace) -> int:
    ws = Path(args.workspace).resolve()
    state = load_ledger(ws)
    if not state:
        return 1
    mod_name = args.module or state.active_module
    if mod_name not in state.modules:
        print(f"Error: Module '{mod_name}' not found. Available modules: {list(state.modules.keys())}")
        return 1
    mod = state.modules[mod_name]
    mod.bdd_dialogue.rounds_completed += 1
    if args.clear_questions:
        mod.bdd_dialogue.unresolved_questions = []
    elif args.questions is not None:
        mod.bdd_dialogue.unresolved_questions = [q for q in args.questions if q.strip()]
    mod.updated_at = datetime.now(UTC).isoformat()
    save_ledger(ws, state)
    print(
        f"Recorded BDD dialogue round #{mod.bdd_dialogue.rounds_completed} for '{mod_name}' "
        f"(unresolved_questions={len(mod.bdd_dialogue.unresolved_questions)})."
    )
    return 0


def cmd_select_pattern(args: argparse.Namespace) -> int:
    ws = Path(args.workspace).resolve()
    state = load_ledger(ws)
    if not state:
        return 1
    mod_name = args.module or state.active_module
    if mod_name not in state.modules:
        print(f"Error: Module '{mod_name}' not found. Available modules: {list(state.modules.keys())}")
        return 1
    mod = state.modules[mod_name]
    mod.bdd_dialogue.selected_paradigm = args.paradigm
    mod.bdd_dialogue.coordination_scope = args.scope
    mod.bdd_dialogue.pattern_selection_approved = True
    mod.updated_at = datetime.now(UTC).isoformat()
    save_ledger(ws, state)
    print(f"Bridge 2.5b Pattern Gate locked for '{mod_name}': {args.paradigm} ({args.scope}).")
    return 0


def cmd_verify_gate(args: argparse.Namespace) -> int:
    ws = Path(args.workspace).resolve()
    state = load_ledger(ws)
    if not state:
        print(f"No phase-lock.json found in {ws}")
        return 1
    mod_name = args.module or state.active_module
    if mod_name not in state.modules:
        print(f"Error: Module '{mod_name}' not found. Available modules: {list(state.modules.keys())}")
        return 1
    report = run_module_gate_verification(ws, state, mod_name)
    print(report.model_dump_json(indent=2))
    return 0 if report.passed else 2


def cmd_promote_phase(args: argparse.Namespace) -> int:
    ws = Path(args.workspace).resolve()
    state = load_ledger(ws)
    if not state:
        return 1
    mod_name = args.module or state.active_module
    if mod_name not in state.modules:
        print(f"Error: Module '{mod_name}' not found. Available modules: {list(state.modules.keys())}")
        return 1
    mod = state.modules[mod_name]
    report = run_module_gate_verification(ws, state, mod_name)
    if not report.passed and not args.force:
        print("Cannot promote phase: Gate verification failed!")
        print(report.model_dump_json(indent=2))
        return 2

    # Lock current phase artifacts by SHA-256 before advancing
    for rel_pat in args.lock_files or []:
        for fp in sorted(ws.glob(rel_pat)):
            if fp.is_file():
                rel = fp.relative_to(ws).as_posix()
                mod.locked_artifacts[rel] = compute_sha256(fp)

    gate_id = f"G{mod.current_phase}"
    if gate_id not in mod.gates_passed:
        mod.gates_passed.append(gate_id)

    if mod.current_phase < 5:
        mod.current_phase += 1
        mod.phase_name = PHASE_NAMES[mod.current_phase]
        mod.active_owner = PHASE_OWNERS[mod.current_phase]
        if mod.current_phase == 5:
            mod.sub_phase = "5a_RED_HARNESS"
    elif mod.current_phase == 5:
        if mod.sub_phase == "5a_RED_HARNESS":
            mod.sub_phase = "5b_GREEN_IMPL"
        elif mod.sub_phase == "5b_GREEN_IMPL":
            mod.sub_phase = "5c_VERIFICATION"

    mod.updated_at = datetime.now(UTC).isoformat()
    save_ledger(ws, state)
    print(
        f"Promoted module '{mod_name}' to Phase {mod.current_phase} "
        f"({mod.phase_name}, sub_phase={mod.sub_phase}, owner=@{mod.active_owner})."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tdpm-sdd", description="TD/PM & SDD Governance CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_hook = sub.add_parser("hook", help="Execute Antigravity lifecycle hook")
    p_hook.add_argument("event", choices=["pre-invocation", "pre-tool-use", "stop"])
    p_hook.set_defaults(func=cmd_hook)

    p_init = sub.add_parser("init", help="Initialize .agents/state/phase-lock.json in a workspace")
    p_init.add_argument("--workspace", default=".")
    p_init.add_argument("--project-name", default="github.com/example-org/account-platform")
    p_init.add_argument("--module", default="account")
    p_init.add_argument("--language", choices=["go", "python", "typescript"], default="go")
    p_init.add_argument("--phase", type=int, choices=[0, 1, 2, 3, 4, 5], default=5)
    p_init.add_argument(
        "--paradigm",
        choices=["CQRS_EVENT_SOURCING", "STATE_BASED_OCC", "VERTICAL_SLICE_CRUD"],
        default="CQRS_EVENT_SOURCING",
    )
    p_init.add_argument("--lock-existing", action="store_true")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_status = sub.add_parser("status", help="Display current SDD state ledger")
    p_status.add_argument("--workspace", default=".")
    p_status.set_defaults(func=cmd_status)

    p_add = sub.add_parser("add-module", help="Register a new feature/module in the state ledger")
    p_add.add_argument("--workspace", default=".")
    p_add.add_argument("--module", required=True)
    p_add.add_argument("--language", choices=["go", "python", "typescript"], default="go")
    p_add.add_argument("--phase", type=int, choices=[0, 1, 2, 3, 4, 5], default=1)
    p_add.add_argument("--activate", action="store_true")
    p_add.set_defaults(func=cmd_add_module)

    p_diag = sub.add_parser("record-dialogue", help="Record a completed Socratic BDD dialogue round")
    p_diag.add_argument("--workspace", default=".")
    p_diag.add_argument("--module", default=None)
    p_diag.add_argument("--clear-questions", action="store_true")
    p_diag.add_argument("--questions", nargs="*", default=None)
    p_diag.set_defaults(func=cmd_record_dialogue)

    p_pat = sub.add_parser("select-pattern", help="Lock Bridge 2.5b Tactical Pattern Selection Gate")
    p_pat.add_argument("--workspace", default=".")
    p_pat.add_argument("--module", default=None)
    p_pat.add_argument(
        "--paradigm",
        required=True,
        choices=["CQRS_EVENT_SOURCING", "STATE_BASED_OCC", "VERTICAL_SLICE_CRUD"],
    )
    p_pat.add_argument(
        "--scope",
        default="SINGLE_AGGREGATE",
        choices=["SINGLE_AGGREGATE", "PROCESS_MANAGER_SAGA", "CRUD_DIRECT"],
    )
    p_pat.set_defaults(func=cmd_select_pattern)

    p_ver = sub.add_parser("verify-gate", help="Verify current phase gate criteria")
    p_ver.add_argument("--workspace", default=".")
    p_ver.add_argument("--module", default=None)
    p_ver.set_defaults(func=cmd_verify_gate)

    p_prom = sub.add_parser("promote-phase", help="Lock artifacts by SHA-256 and advance to next phase")
    p_prom.add_argument("--workspace", default=".")
    p_prom.add_argument("--module", default=None)
    p_prom.add_argument("--lock-files", nargs="*", default=[])
    p_prom.add_argument("--force", action="store_true")
    p_prom.set_defaults(func=cmd_promote_phase)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
