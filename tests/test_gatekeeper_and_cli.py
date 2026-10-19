"""End-to-end verification suite for the TD/PM & 6-Phase BDD-First SDD Gatekeeper and CLI."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from tdpm_sdd.auditors import run_module_gate_verification
from tdpm_sdd.cli import (
    build_parser,
    cmd_add_module,
    cmd_init,
    cmd_promote_phase,
    cmd_record_dialogue,
    cmd_select_pattern,
    cmd_status,
    cmd_verify_gate,
)
from tdpm_sdd.gatekeeper import (
    _normalize_rel_path,
    dispatch_hook,
    handle_pre_invocation,
    handle_stop,
)
from tdpm_sdd.models import (
    PHASE_NAMES,
    BDDDialogueState,
    ModuleSDDState,
    WorkspaceGovernanceState,
    compute_sha256,
    load_ledger,
    save_ledger,
)
from tdpm_sdd.sdk_bridge import run_sdk_verification_pipeline


class TestTDPMAndSDDGatekeeper(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp_dir.name).resolve()

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def _write_state(self, mod: ModuleSDDState) -> WorkspaceGovernanceState:
        state = WorkspaceGovernanceState(
            project_name="github.com/example-org/account-platform",
            default_module=mod.module_name,
            active_module=mod.module_name,
            modules={mod.module_name: mod},
        )
        save_ledger(self.ws, state)
        return state

    def _call_pre_tool_use(self, tool_name: str, args: dict) -> dict:
        payload = {
            "workspacePaths": [self.ws.as_posix()],
            "toolCall": {"name": tool_name, "args": args},
        }
        return json.loads(dispatch_hook("pre-tool-use", json.dumps(payload)))

    def test_1_phase1_blocks_go_code_and_contaminated_blueprint(self) -> None:
        mod = ModuleSDDState(
            module_name="transfer",
            current_phase=1,
            phase_name=PHASE_NAMES[1],
            active_owner="pm-planner",
        )
        self._write_state(mod)

        # 1a. Writing Go code in Phase 1 is hard-denied
        res_go = self._call_pre_tool_use(
            "write_to_file",
            {
                "TargetFile": str(self.ws / "internal/transfer/cmd/domain/transfer.go"),
                "CodeContent": "package domain\n",
            },
        )
        self.assertEqual(res_go["decision"], "deny")
        self.assertIn("Phase 1", res_go["reason"])

        # 1b. Writing an ARCHITECTURE_BLUEPRINT.md with >15 lines of Go implementation is hard-denied
        long_go = "\n".join([f"line_{i} := {i}" for i in range(20)])
        res_bp = self._call_pre_tool_use(
            "write_to_file",
            {
                "TargetFile": str(self.ws / "docs/architecture/ARCHITECTURE_BLUEPRINT.md"),
                "CodeContent": f"# Blueprint\n```go\n{long_go}\n```\n",
            },
        )
        self.assertEqual(res_bp["decision"], "deny")
        self.assertIn("BLUEPRINT CONTAMINATION", res_bp["reason"])

    def test_2_phase2_enforces_multi_round_bdd_dialogue_and_blocks_openapi(self) -> None:
        mod = ModuleSDDState(
            module_name="transfer",
            current_phase=2,
            phase_name=PHASE_NAMES[2],
            active_owner="pm-planner",
            bdd_dialogue=BDDDialogueState(
                rounds_completed=1,
                required_minimum_rounds=2,
                unresolved_questions=["What happens on concurrent transfer timeout?"],
            ),
        )
        self._write_state(mod)

        # 2a. Premature .feature authoring with only 1 dialogue round is denied
        res_feat = self._call_pre_tool_use(
            "write_to_file",
            {
                "TargetFile": str(self.ws / "specs/features/transfer.feature"),
                "CodeContent": "Feature: Transfer\n  Scenario: S1\n    Given an account\n    When transfer\n    Then event\n",
            },
        )
        self.assertEqual(res_feat["decision"], "deny")
        self.assertIn("DIALOGUE GATE", res_feat["reason"])

        # 2b. Writing OpenAPI in Phase 2 (before Phase 3 Tactical DDD) is denied
        res_oas = self._call_pre_tool_use(
            "write_to_file",
            {
                "TargetFile": str(self.ws / "specs/openapi/transfer.v1.yaml"),
                "CodeContent": "openapi: 3.1.0\n",
            },
        )
        self.assertEqual(res_oas["decision"], "deny")
        self.assertIn("Phase 3 (Tactical DDD", res_oas["reason"])

        # 2c. Completing round 2 and clearing questions unlocks pure Gherkin, but blocks HTTP transport leakage
        mod.bdd_dialogue.rounds_completed = 2
        mod.bdd_dialogue.unresolved_questions = []
        self._write_state(mod)

        res_leak = self._call_pre_tool_use(
            "write_to_file",
            {
                "TargetFile": str(self.ws / "specs/features/transfer.feature"),
                "CodeContent": "Feature: Transfer\n  Scenario: S1\n    Given an account\n    When POST\n    Then HTTP 200 is returned\n",
            },
        )
        self.assertEqual(res_leak["decision"], "deny")
        self.assertIn("GHERKIN PURITY BLOCK", res_leak["reason"])

        res_clean = self._call_pre_tool_use(
            "write_to_file",
            {
                "TargetFile": str(self.ws / "specs/features/transfer.feature"),
                "CodeContent": "Feature: Transfer\n  Scenario: S1\n    Given account A has 100 dollars\n    When TransferFunds command is dispatched\n    Then FundsTransferredEvent is emitted\n",
            },
        )
        self.assertEqual(res_clean["decision"], "allow")

    def test_3_phase3_enforces_sdd_stubs_and_paradigm_minimalism(self) -> None:
        # 3a. CQRS_EVENT_SOURCING requires SDD_STUB panics and blocks public balance getters
        mod_cqrs = ModuleSDDState(
            module_name="transfer",
            current_phase=3,
            phase_name=PHASE_NAMES[3],
            active_owner="td-auditor",
            bdd_dialogue=BDDDialogueState(
                rounds_completed=2,
                pattern_selection_approved=True,
                selected_paradigm="CQRS_EVENT_SOURCING",
            ),
        )
        self._write_state(mod_cqrs)

        res_impl = self._call_pre_tool_use(
            "write_to_file",
            {
                "TargetFile": str(self.ws / "internal/transfer/cmd/domain/transfer_aggregate.go"),
                "CodeContent": "package domain\nfunc DoTransfer() error {\n  x := 1\n  return nil\n}\n",
            },
        )
        self.assertEqual(res_impl["decision"], "deny")
        self.assertIn("SDD_STUB", res_impl["reason"])

        res_getter = self._call_pre_tool_use(
            "write_to_file",
            {
                "TargetFile": str(self.ws / "internal/transfer/cmd/domain/transfer_aggregate.go"),
                "CodeContent": 'package domain\nfunc (a *Agg) GetBalance() int64 {\n  panic("SDD_STUB")\n}\n',
            },
        )
        self.assertEqual(res_getter["decision"], "deny")
        self.assertIn("Candidate B1", res_getter["reason"])

        res_stub_ok = self._call_pre_tool_use(
            "write_to_file",
            {
                "TargetFile": str(self.ws / "internal/transfer/cmd/domain/transfer_aggregate.go"),
                "CodeContent": 'package domain\nfunc (a *Agg) Transfer(cents int64) error {\n  panic("SDD_STUB: locked until Phase 5b")\n}\n',
            },
        )
        self.assertEqual(res_stub_ok["decision"], "allow")

        # 3b. VERTICAL_SLICE_CRUD blocks Aggregate Root over-engineering
        mod_crud = ModuleSDDState(
            module_name="profile",
            current_phase=3,
            phase_name=PHASE_NAMES[3],
            active_owner="td-auditor",
            bdd_dialogue=BDDDialogueState(
                rounds_completed=2,
                pattern_selection_approved=True,
                selected_paradigm="VERTICAL_SLICE_CRUD",
            ),
        )
        self._write_state(mod_crud)
        res_over = self._call_pre_tool_use(
            "write_to_file",
            {
                "TargetFile": str(self.ws / "internal/profile/domain/profile_aggregate.go"),
                "CodeContent": "package domain\n",
            },
        )
        self.assertEqual(res_over["decision"], "deny")
        self.assertIn("VERTICAL_SLICE_CRUD", res_over["reason"])

    def test_4_phase5a_red_harness_and_locked_artifact_protection(self) -> None:
        bmap = self.ws / "docs/architecture/boundary-map.md"
        bmap.parent.mkdir(parents=True, exist_ok=True)
        bmap.write_text("# Boundary Map\n", encoding="utf-8")

        mod = ModuleSDDState(
            module_name="account",
            current_phase=5,
            phase_name=PHASE_NAMES[5],
            sub_phase="5a_RED_HARNESS",
            active_owner="td-auditor",
            bdd_dialogue=BDDDialogueState(
                rounds_completed=2,
                pattern_selection_approved=True,
                selected_paradigm="CQRS_EVENT_SOURCING",
            ),
            locked_artifacts={"docs/architecture/boundary-map.md": compute_sha256(bmap)},
        )
        self._write_state(mod)

        # 4a. In 5a_RED_HARNESS, writing *_test.go is allowed, but production .go is denied
        res_test = self._call_pre_tool_use(
            "write_to_file",
            {
                "TargetFile": str(self.ws / "internal/account/cmd/domain/account_test.go"),
                "CodeContent": "package domain_test\n",
            },
        )
        self.assertEqual(res_test["decision"], "allow")

        res_prod = self._call_pre_tool_use(
            "write_to_file",
            {
                "TargetFile": str(self.ws / "internal/account/cmd/domain/account_aggregate.go"),
                "CodeContent": "package domain\n",
            },
        )
        self.assertEqual(res_prod["decision"], "deny")
        self.assertIn("5a_RED_HARNESS", res_prod["reason"])

        # 4b. Attempting to mutate locked boundary-map.md triggers force_ask
        res_locked = self._call_pre_tool_use(
            "replace_file_content",
            {
                "TargetFile": str(bmap),
                "ReplacementContent": "# Tampered\n",
            },
        )
        self.assertEqual(res_locked["decision"], "force_ask")
        self.assertIn("LOCK PROTECTION", res_locked["reason"])

        # 4c. Shell bypass via run_command is denied
        res_shell = self._call_pre_tool_use(
            "run_command",
            {"CommandLine": "Set-Content -Path internal/account/foo.go -Value 'package foo'"},
        )
        self.assertEqual(res_shell["decision"], "deny")

    def test_5_sdk_bridge_read_only_verification(self) -> None:
        bmap = self.ws / "docs/architecture/boundary-map.md"
        bmap.parent.mkdir(parents=True, exist_ok=True)
        bmap.write_text("# Boundary Map\n", encoding="utf-8")

        mod = ModuleSDDState(
            module_name="account",
            current_phase=1,
            phase_name=PHASE_NAMES[1],
            active_owner="pm-planner",
            locked_artifacts={"docs/architecture/boundary-map.md": compute_sha256(bmap)},
        )
        self._write_state(mod)

        raw = asyncio.run(
            run_sdk_verification_pipeline(str(self.ws), "account", "full_gate")
        )
        parsed = json.loads(raw)
        self.assertEqual(parsed["status"], "success")
        self.assertTrue(parsed["deterministic_gate_passed"])

    def test_6_phase0_blueprint_no_code_dump_audit_and_gate(self) -> None:
        mod = ModuleSDDState(
            module_name="account",
            current_phase=0,
            phase_name=PHASE_NAMES[0],
            active_owner="pm-planner",
        )
        state = self._write_state(mod)

        bp = self.ws / "docs/architecture/ARCHITECTURE_BLUEPRINT.md"
        bp.parent.mkdir(parents=True, exist_ok=True)
        long_go = "\n".join([f"line_{i} := {i}" for i in range(20)])
        bp.write_text(f"# Blueprint\n```go\n{long_go}\n```\n", encoding="utf-8")

        # verify-gate in Phase 0 must catch SDD-BLUEPRINT-NO-CODE-DUMP
        report = run_module_gate_verification(self.ws, state, "account")
        self.assertFalse(report.passed)
        rule_ids = [f.rule_id for f in report.findings]
        self.assertIn("SDD-BLUEPRINT-NO-CODE-DUMP", rule_ids)

    def test_7_normalize_rel_path_with_relative_paths(self) -> None:
        # Relative path with .. against workspace
        rel = _normalize_rel_path("internal/../internal/account/foo.go", self.ws)
        self.assertEqual(rel, "internal/account/foo.go")

        # Absolute path inside workspace
        abs_p = str(self.ws / "internal/account/bar.go")
        self.assertEqual(_normalize_rel_path(abs_p, self.ws), "internal/account/bar.go")

    def test_8_cli_lifecycle_end_to_end(self) -> None:
        parser = build_parser()

        # 8a. cmd_init
        args = parser.parse_args(["init", "--workspace", str(self.ws), "--phase", "1", "--module", "billing"])
        rc = cmd_init(args)
        self.assertEqual(rc, 0)
        state = load_ledger(self.ws)
        self.assertIsNotNone(state)
        assert state is not None
        self.assertEqual(state.active_module, "billing")
        self.assertEqual(state.modules["billing"].current_phase, 1)

        # 8b. cmd_status
        args_status = parser.parse_args(["status", "--workspace", str(self.ws)])
        self.assertEqual(cmd_status(args_status), 0)

        # 8c. cmd_add_module
        args_add = parser.parse_args(["add-module", "--workspace", str(self.ws), "--module", "inventory", "--phase", "0"])
        self.assertEqual(cmd_add_module(args_add), 0)
        state = load_ledger(self.ws)
        assert state is not None
        self.assertIn("inventory", state.modules)

        # 8d. cmd_record_dialogue
        args_dlg = parser.parse_args([
            "record-dialogue",
            "--workspace", str(self.ws),
            "--module", "billing",
            "--questions", "Q1: Timeout handling?",
        ])
        self.assertEqual(cmd_record_dialogue(args_dlg), 0)
        state = load_ledger(self.ws)
        assert state is not None
        self.assertEqual(state.modules["billing"].bdd_dialogue.rounds_completed, 1)
        self.assertEqual(state.modules["billing"].bdd_dialogue.unresolved_questions, ["Q1: Timeout handling?"])

        # Clear questions
        args_clr = parser.parse_args([
            "record-dialogue",
            "--workspace", str(self.ws),
            "--module", "billing",
            "--clear-questions",
        ])
        self.assertEqual(cmd_record_dialogue(args_clr), 0)
        state = load_ledger(self.ws)
        assert state is not None
        self.assertEqual(state.modules["billing"].bdd_dialogue.rounds_completed, 2)
        self.assertEqual(len(state.modules["billing"].bdd_dialogue.unresolved_questions), 0)

        # 8e. cmd_select_pattern
        args_pat = parser.parse_args([
            "select-pattern",
            "--workspace", str(self.ws),
            "--module", "billing",
            "--paradigm", "CQRS_EVENT_SOURCING",
            "--scope", "SINGLE_AGGREGATE",
        ])
        self.assertEqual(cmd_select_pattern(args_pat), 0)
        state = load_ledger(self.ws)
        assert state is not None
        self.assertTrue(state.modules["billing"].bdd_dialogue.pattern_selection_approved)
        self.assertEqual(state.modules["billing"].bdd_dialogue.selected_paradigm, "CQRS_EVENT_SOURCING")

        # 8f. cmd_verify_gate (Phase 1 fails without boundary-map.md)
        args_vg = parser.parse_args(["verify-gate", "--workspace", str(self.ws), "--module", "billing"])
        self.assertEqual(cmd_verify_gate(args_vg), 2)

        # Create boundary-map.md -> verify-gate passes
        bmap = self.ws / "docs/architecture/boundary-map.md"
        bmap.parent.mkdir(parents=True, exist_ok=True)
        bmap.write_text("# Billing Boundary Map\n", encoding="utf-8")
        self.assertEqual(cmd_verify_gate(args_vg), 0)

        # 8g. cmd_promote_phase -> advances to Phase 2 and locks boundary-map.md
        args_prom = parser.parse_args([
            "promote-phase",
            "--workspace", str(self.ws),
            "--module", "billing",
            "--lock-files", "docs/architecture/boundary-map.md",
        ])
        self.assertEqual(cmd_promote_phase(args_prom), 0)
        state = load_ledger(self.ws)
        assert state is not None
        self.assertEqual(state.modules["billing"].current_phase, 2)
        self.assertIn("docs/architecture/boundary-map.md", state.modules["billing"].locked_artifacts)

    def test_9_cli_missing_module_error_handling(self) -> None:
        parser = build_parser()
        cmd_init(parser.parse_args(["init", "--workspace", str(self.ws), "--phase", "1", "--module", "account"]))

        args_bad = parser.parse_args(["verify-gate", "--workspace", str(self.ws), "--module", "nonexistent"])
        self.assertEqual(cmd_verify_gate(args_bad), 1)

        args_bad_dlg = parser.parse_args(["record-dialogue", "--workspace", str(self.ws), "--module", "nonexistent"])
        self.assertEqual(cmd_record_dialogue(args_bad_dlg), 1)

        args_bad_prom = parser.parse_args(["promote-phase", "--workspace", str(self.ws), "--module", "nonexistent"])
        self.assertEqual(cmd_promote_phase(args_bad_prom), 1)

    def test_10_pre_invocation_and_stop_hooks(self) -> None:
        mod = ModuleSDDState(
            module_name="account",
            current_phase=1,
            phase_name=PHASE_NAMES[1],
            active_owner="pm-planner",
        )
        self._write_state(mod)

        # Pre-invocation hook
        payload = {"workspacePaths": [self.ws.as_posix()]}
        pre_inv = handle_pre_invocation(payload)
        self.assertIn("injectSteps", pre_inv)
        msg = pre_inv["injectSteps"][0]["ephemeralMessage"]
        self.assertIn("TD/PM SDD GOVERNANCE ACTIVE", msg)
        self.assertIn("account", msg)

        # Stop hook
        stop_res = handle_stop(payload)
        self.assertEqual(stop_res["decision"], "allow")


if __name__ == "__main__":
    unittest.main()
