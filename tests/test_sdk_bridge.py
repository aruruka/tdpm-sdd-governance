"""Comprehensive verification suite for tdpm-sdk-bridge MCP Server.

Validates:
1. MCP Protocol & mcp-builder compliance (tool listing, annotations, dual registration, schema generation).
2. Dual response format support (JSON and Markdown).
3. Google Cloud audit telemetry and stdio hygiene (stderr JSON logging, zero stdout contamination).
4. Backward compatibility with existing callers.
"""

from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

from tdpm_sdd.models import (
    PHASE_NAMES,
    ModuleSDDState,
    WorkspaceGovernanceState,
    compute_sha256,
    save_ledger,
)
from tdpm_sdd.sdk_bridge import (
    AuditResult,
    format_audit_result_markdown,
    mcp,
    run_sdk_verification_pipeline,
    tdpm_run_sdk_verification_pipeline,
)


class TestSDKSBridgeMCP(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp_dir.name).resolve()

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def _init_sample_workspace(self) -> None:
        bmap = self.ws / "docs/architecture/boundary-map.md"
        bmap.parent.mkdir(parents=True, exist_ok=True)
        bmap.write_text("# Account Boundary Map\n", encoding="utf-8")

        mod = ModuleSDDState(
            module_name="account",
            current_phase=1,
            phase_name=PHASE_NAMES[1],
            active_owner="pm-planner",
            locked_artifacts={"docs/architecture/boundary-map.md": compute_sha256(bmap)},
        )
        state = WorkspaceGovernanceState(
            project_name="github.com/example-org/account-platform",
            default_module="account",
            active_module="account",
            modules={"account": mod},
        )
        save_ledger(self.ws, state)

    def test_1_mcp_tools_registration_and_annotations(self) -> None:
        """Verify both tools are registered with full MCP annotations and rich schemas."""
        tools = asyncio.run(mcp.list_tools())
        tool_names = {t.name for t in tools}
        self.assertIn("tdpm_run_sdk_verification_pipeline", tool_names)
        self.assertIn("run_sdk_verification_pipeline", tool_names)

        for t in tools:
            if t.name in ("tdpm_run_sdk_verification_pipeline", "run_sdk_verification_pipeline"):
                # Annotations check
                self.assertIsNotNone(t.annotations)
                self.assertTrue(t.annotations.read_only_hint)
                self.assertFalse(t.annotations.destructive_hint)
                self.assertTrue(t.annotations.idempotent_hint)
                self.assertFalse(t.annotations.open_world_hint)

                # Schema properties check
                props = t.input_schema.get("properties", {})
                self.assertIn("workspace_dir", props)
                self.assertIn("module_name", props)
                self.assertIn("focus_area", props)
                self.assertIn("session_id", props)
                self.assertIn("response_format", props)

                # Workspace dir must be required
                req = t.input_schema.get("required", [])
                self.assertIn("workspace_dir", req)

    def test_2_canonical_tool_json_execution_and_gcp_audit(self) -> None:
        """Verify tdpm_run_sdk_verification_pipeline returns valid JSON with GCP audit fields."""
        self._init_sample_workspace()

        stderr_capture = io.StringIO()
        stdout_capture = io.StringIO()
        old_stderr, old_stdout = sys.stderr, sys.stdout
        try:
            sys.stderr, sys.stdout = stderr_capture, stdout_capture
            raw = asyncio.run(
                tdpm_run_sdk_verification_pipeline(
                    workspace_dir=str(self.ws),
                    module_name="account",
                    focus_area="full_gate",
                    session_id="session-xyz-987",
                    response_format="json",
                )
            )
        finally:
            sys.stderr, sys.stdout = old_stderr, old_stdout

        # Stdout must remain completely empty to preserve stdio JSON-RPC transport integrity
        self.assertEqual(stdout_capture.getvalue(), "")

        # Stderr must contain GCP structured JSON log lines
        err_lines = [ln.strip() for ln in stderr_capture.getvalue().splitlines() if ln.strip()]
        self.assertGreater(len(err_lines), 0)
        first_log = json.loads(err_lines[0])
        self.assertIn("severity", first_log)
        self.assertIn("time", first_log)
        self.assertEqual(first_log.get("logging.googleapis.com/labels", {}).get("session_id"), "session-xyz-987")

        # Response payload check
        data = json.loads(raw)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["module_name"], "account")
        self.assertTrue(data["deterministic_gate_passed"])
        self.assertEqual(data["session_id"], "session-xyz-987")
        self.assertIn("timestamp_utc", data)

    def test_3_markdown_response_format(self) -> None:
        """Verify markdown response format adheres to mcp-builder presentation standards."""
        self._init_sample_workspace()

        md_output = asyncio.run(
            tdpm_run_sdk_verification_pipeline(
                workspace_dir=str(self.ws),
                module_name="account",
                focus_area="full_gate",
                session_id="sess-md-1",
                response_format="markdown",
            )
        )

        self.assertIn("# SDD Gate & SDK Verification Report: account", md_output)
        self.assertIn("- **Status**: `SUCCESS`", md_output)
        self.assertIn("- **Session ID**: `sess-md-1`", md_output)
        self.assertIn("## Deterministic Findings", md_output)
        self.assertIn("## SDK Semantic Report", md_output)

    def test_4_backward_compatible_alias_positional_call(self) -> None:
        """Verify run_sdk_verification_pipeline works seamlessly with legacy positional args."""
        self._init_sample_workspace()

        raw = asyncio.run(
            run_sdk_verification_pipeline(str(self.ws), "account", "full_gate")
        )
        data = json.loads(raw)
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["deterministic_gate_passed"])
        self.assertIsNone(data["session_id"])

    def test_5_missing_module_error_handling(self) -> None:
        """Verify structured error payload is returned when target module is absent."""
        self._init_sample_workspace()

        raw = asyncio.run(
            tdpm_run_sdk_verification_pipeline(
                workspace_dir=str(self.ws),
                module_name="nonexistent_module",
                session_id="err-sess",
            )
        )
        data = json.loads(raw)
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["phase"], -1)
        self.assertFalse(data["deterministic_gate_passed"])
        self.assertIn("not found", data["sdk_semantic_report"])
        self.assertEqual(data["session_id"], "err-sess")

    def test_6_invalid_workspace_validation(self) -> None:
        """Verify Pydantic validation catches empty or invalid workspace_dir."""
        raw = asyncio.run(
            tdpm_run_sdk_verification_pipeline(
                workspace_dir="",
                module_name="account",
            )
        )
        data = json.loads(raw)
        self.assertEqual(data["status"], "error")
        self.assertIn("Invalid verification request", data["sdk_semantic_report"])


if __name__ == "__main__":
    unittest.main()
