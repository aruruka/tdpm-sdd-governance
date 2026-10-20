"""Read-Only Google Antigravity SDK MCP Bridge with strict PreToolUse isolation.

Conforms to:
1. Google Cloud Agent Security & Least Privilege Standards (read-only enforcement, zero stdout leakage, GCP structured logging).
2. MCP Specification & mcp-builder Standards (JSON-RPC 2.0, dual-format output, rich parameter schemas, standard tool annotations).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef, attr-defined]
    except (ImportError, AttributeError):
        FastMCP = Any  # type: ignore[assignment, misc]

try:
    from mcp.types import ToolAnnotations
except ImportError:
    ToolAnnotations = Any  # type: ignore[assignment, misc]

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .auditors import run_module_gate_verification
from .models import load_ledger

SERVER_NAME = "tdpm-sdk-bridge"
mcp = FastMCP(SERVER_NAME)

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
STRICT_AUDIT_SKILL_PATH = PLUGIN_ROOT / "skills" / "strict-audit"
ALLOWED_SDK_READ_TOOLS = frozenset(
    {"view_file", "code_search", "check_file_metrics", "run_deterministic_gate_check"}
)

TOOL_ANNOTATIONS = ToolAnnotations(
    title="Execute Read-Only SDD Gate & SDK Verification",
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)


def log_gcp_audit(
    severity: str,
    message: str,
    session_id: str | None = None,
    **extra: Any,
) -> None:
    """Emits a Google Cloud structured log entry exclusively to sys.stderr.

    Guarantees that stdio JSON-RPC protocol streams (stdout) remain 100% uncorrupted,
    while complying with Google Cloud Agent audit logging standards.
    """
    entry: dict[str, Any] = {
        "severity": severity,
        "time": datetime.now(UTC).isoformat(),
        "message": message,
    }
    if session_id:
        entry["logging.googleapis.com/labels"] = {"session_id": session_id}
    if extra:
        entry["audit_context"] = extra
    sys.stderr.write(json.dumps(entry, ensure_ascii=False) + "\n")
    sys.stderr.flush()


class SDKVerificationRequest(BaseModel):
    """Validated input parameters for the SDD SDK verification pipeline."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    workspace_dir: str = Field(
        ...,
        min_length=1,
        description="Absolute filesystem path to the target workspace root.",
    )
    module_name: str = Field(
        default="account",
        min_length=1,
        description="Target BDD module name defined in .agents/state/phase-lock.json.",
    )
    focus_area: Literal["traceability", "encapsulation", "contracts", "full_gate"] = Field(
        default="full_gate",
        description="Specific verification focus area for the sweep.",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional host session or user ID for Google Cloud audit compliance.",
    )
    response_format: Literal["json", "markdown"] = Field(
        default="json",
        description="Output format: 'json' for programmatic parsers or 'markdown' for agent/human inspection.",
    )


class AuditResult(BaseModel):
    """Structured read-only audit payload returned to the host Antigravity session."""

    model_config = ConfigDict(str_strip_whitespace=True)

    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 UTC timestamp of audit execution.",
    )
    session_id: str | None = Field(
        default=None,
        description="Host session or user ID for Google Cloud audit compliance.",
    )
    status: Literal["success", "error"]
    workspace_dir: str
    module_name: str
    phase: int
    selected_paradigm: str | None
    deterministic_gate_passed: bool
    deterministic_findings: list[dict[str, Any]]
    sdk_semantic_report: str
    tokens_used: int = 0


def format_audit_result_markdown(result: AuditResult) -> str:
    """Formats an AuditResult into human/agent-readable Markdown per mcp-builder standards."""
    status_icon = "PASSED" if result.deterministic_gate_passed else "FAILED"
    lines = [
        f"# SDD Gate & SDK Verification Report: {result.module_name}",
        f"- **Status**: `{result.status.upper()}` (Gate: **{status_icon}**)",
        f"- **Phase**: `Phase {result.phase}`",
        f"- **Paradigm**: `{result.selected_paradigm or 'Not Selected'}`",
        f"- **Workspace**: `{result.workspace_dir}`",
        f"- **Timestamp (UTC)**: `{result.timestamp_utc}`",
    ]
    if result.session_id:
        lines.append(f"- **Session ID**: `{result.session_id}`")
    if result.tokens_used > 0:
        lines.append(f"- **Tokens Used**: `{result.tokens_used}`")

    lines.append("\n## Deterministic Findings")
    if not result.deterministic_findings:
        lines.append("No gate violations detected. All phase-lock artifacts and invariants verified.")
    else:
        lines.append("| Severity | Rule ID | File | Line | Message |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for f in result.deterministic_findings:
            sev = f.get("severity", "INFO")
            rule = f.get("rule_id", "N/A")
            fp = f.get("file_path", "")
            ln = f.get("line", 0)
            msg = str(f.get("message", "")).replace("\n", " ")
            lines.append(f"| `{sev}` | `{rule}` | `{fp}` | {ln} | {msg} |")

    lines.append("\n## SDK Semantic Report")
    lines.append(result.sdk_semantic_report)
    return "\n".join(lines)


async def execute_verification_pipeline(
    workspace_dir: str,
    module_name: str = "account",
    focus_area: Literal["traceability", "encapsulation", "contracts", "full_gate"] = "full_gate",
    session_id: str | None = None,
    response_format: Literal["json", "markdown"] = "json",
) -> str:
    """Core verification engine executing static AST checks and isolated read-only SDK sweeps."""
    try:
        req = SDKVerificationRequest(
            workspace_dir=workspace_dir,
            module_name=module_name,
            focus_area=focus_area,
            session_id=session_id,
            response_format=response_format,
        )
    except ValidationError as exc:
        log_gcp_audit(
            severity="WARNING",
            message=f"Validation failed for verification request: {exc}",
            session_id=session_id,
            workspace_dir=workspace_dir,
            module_name=module_name,
        )
        err_res = AuditResult(
            status="error",
            workspace_dir=workspace_dir,
            module_name=module_name,
            phase=-1,
            selected_paradigm=None,
            deterministic_gate_passed=False,
            deterministic_findings=[],
            sdk_semantic_report=f"Invalid verification request: {exc}",
            session_id=session_id,
        )
        if response_format == "markdown":
            return format_audit_result_markdown(err_res)
        return err_res.model_dump_json(indent=2)

    ws_path = Path(req.workspace_dir).resolve()
    log_gcp_audit(
        severity="INFO",
        message=f"Initiating SDD verification pipeline for module '{req.module_name}'",
        session_id=req.session_id,
        workspace_dir=str(ws_path),
        module_name=req.module_name,
        focus_area=req.focus_area,
    )

    state = load_ledger(ws_path)
    if not state or req.module_name not in state.modules:
        log_gcp_audit(
            severity="ERROR",
            message=f"Module '{req.module_name}' not found in state ledger",
            session_id=req.session_id,
            workspace_dir=str(ws_path),
            module_name=req.module_name,
        )
        err_res = AuditResult(
            status="error",
            workspace_dir=str(ws_path),
            module_name=req.module_name,
            phase=-1,
            selected_paradigm=None,
            deterministic_gate_passed=False,
            deterministic_findings=[],
            sdk_semantic_report=(
                f"Module '{req.module_name}' not found in '{ws_path / '.agents/state/phase-lock.json'}'."
            ),
            session_id=req.session_id,
        )
        if req.response_format == "markdown":
            return format_audit_result_markdown(err_res)
        return err_res.model_dump_json(indent=2)

    mod = state.modules[req.module_name]
    gate_report = run_module_gate_verification(ws_path, state, req.module_name)

    # Attempt optional deep semantic check via google.antigravity SDK if installed and API key / Vertex configured
    sdk_report_text = gate_report.summary
    tokens_used = 0
    try:
        from google.antigravity import Agent, LocalAgentConfig, types  # type: ignore[import-not-found]
        from google.antigravity.hooks import hooks, policy  # type: ignore[import-not-found]

        @hooks.pre_tool_call_decide
        async def enforce_read_only_sdk_hook(data: types.ToolCall) -> types.HookResult:
            """Hard programmatic block preventing any nested SDK write or command execution."""
            if data.name not in ALLOWED_SDK_READ_TOOLS:
                return types.HookResult(allow=False)
            return types.HookResult(allow=True)

        def check_file_metrics(file_path: str) -> str:
            """Read-only helper tool exposed to the SDK agent."""
            resolved = (ws_path / file_path).resolve()
            if not str(resolved).startswith(str(ws_path)) or not resolved.is_file():
                return f"Error: '{file_path}' is outside workspace or not a file."
            lines = len(resolved.read_text(encoding="utf-8", errors="replace").splitlines())
            return f"{file_path}: {lines} lines"

        reviewer_subagent = types.SubagentConfig(
            name="static_scanner",
            description="Read-only boundary and contract traceability scanner.",
            system_instructions=(
                f"Inspect module '{req.module_name}' (language={mod.language}, "
                f"paradigm={mod.bdd_dialogue.selected_paradigm}) strictly in read-only mode."
            ),
            tools=[check_file_metrics],
            capabilities=types.SubagentCapabilities(
                enabled_tools=types.BuiltinTools.read_only(),
            ),
        )

        config = LocalAgentConfig(
            vertex=bool(os.environ.get("GOOGLE_CLOUD_PROJECT")),
            project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
            api_key=os.environ.get("GEMINI_API_KEY"),
            workspaces=[str(ws_path)],
            skills_paths=[str(STRICT_AUDIT_SKILL_PATH)] if STRICT_AUDIT_SKILL_PATH.exists() else [],
            tools=[check_file_metrics],
            subagents=[reviewer_subagent],
            hooks=[enforce_read_only_sdk_hook],
            capabilities=types.CapabilitiesConfig(
                enabled_tools=types.BuiltinTools.read_only(),
                enable_subagents=True,
                max_subagent_depth=2,
                allowed_subagents=["static_scanner"],
            ),
            policies=[
                policy.deny_all(),
                policy.allow("view_file"),
                policy.allow("code_search"),
                policy.workspace_only([str(ws_path)]),
            ],
        )

        if config.api_key or config.vertex:
            async with Agent(config) as sdk_agent:
                resp = await sdk_agent.chat(
                    f"Audit module '{req.module_name}' at Phase {mod.current_phase} ({mod.phase_name}) "
                    f"with paradigm '{mod.bdd_dialogue.selected_paradigm}' and focus '{req.focus_area}'. "
                    "Use the strict-audit skill and return findings in deterministic file:line order."
                )
                sdk_report_text = await resp.text()
                tokens_used = (
                    resp.usage_metadata.total_token_count if resp.usage_metadata else 0
                )
        else:
            sdk_report_text = (
                f"{gate_report.summary} (Note: GEMINI_API_KEY/GOOGLE_CLOUD_PROJECT not set; "
                "completed deterministic AST & SHA-256 verification without nested LLM token burn.)"
            )
    except ImportError:
        sdk_report_text = (
            f"{gate_report.summary} (Executed zero-token deterministic Python AST/Contract verification; "
            "install 'google-antigravity' package to enable optional nested LLM sweeps.)"
        )
    except Exception as exc:  # noqa: BLE001
        sdk_report_text = f"{gate_report.summary} | SDK runtime note: {type(exc).__name__}: {exc}"

    result = AuditResult(
        status="success",
        workspace_dir=str(ws_path),
        module_name=req.module_name,
        phase=mod.current_phase,
        selected_paradigm=mod.bdd_dialogue.selected_paradigm,
        deterministic_gate_passed=gate_report.passed,
        deterministic_findings=[f.model_dump() for f in gate_report.findings],
        sdk_semantic_report=sdk_report_text,
        tokens_used=tokens_used,
        session_id=req.session_id,
    )

    log_gcp_audit(
        severity="INFO",
        message=f"Completed SDD verification pipeline for module '{req.module_name}' (passed={gate_report.passed})",
        session_id=req.session_id,
        workspace_dir=str(ws_path),
        module_name=req.module_name,
        gate_passed=gate_report.passed,
        findings_count=len(gate_report.findings),
        tokens_used=tokens_used,
    )

    if req.response_format == "markdown":
        return format_audit_result_markdown(result)
    return result.model_dump_json(indent=2)


@mcp.tool(
    name="tdpm_run_sdk_verification_pipeline",
    annotations=TOOL_ANNOTATIONS,
)
async def tdpm_run_sdk_verification_pipeline(
    workspace_dir: Annotated[
        str,
        Field(..., min_length=1, description="Absolute filesystem path to the target workspace root."),
    ],
    module_name: Annotated[
        str,
        Field(default="account", min_length=1, description="Target BDD module name defined in .agents/state/phase-lock.json."),
    ] = "account",
    focus_area: Annotated[
        Literal["traceability", "encapsulation", "contracts", "full_gate"],
        Field(default="full_gate", description="Specific verification focus area for the sweep."),
    ] = "full_gate",
    session_id: Annotated[
        str | None,
        Field(default=None, description="Optional host session or user ID for Google Cloud audit compliance."),
    ] = None,
    response_format: Annotated[
        Literal["json", "markdown"],
        Field(default="json", description="Output format: 'json' for programmatic parsers or 'markdown' for agent/human inspection."),
    ] = "json",
) -> str:
    """Canonical SDD Verification Pipeline conforming to MCP builder naming standards.

    Executes deterministic static checks + an isolated READ-ONLY Google Antigravity SDK verification sweep.
    Guarantees that nested SDK agents NEVER execute write_to_file, replace_file_content, or run_command,
    preserving 100% of file mutations for the host Antigravity session's PreToolUse hook.
    """
    return await execute_verification_pipeline(
        workspace_dir=workspace_dir,
        module_name=module_name,
        focus_area=focus_area,
        session_id=session_id,
        response_format=response_format,
    )


@mcp.tool(
    name="run_sdk_verification_pipeline",
    annotations=TOOL_ANNOTATIONS,
)
async def run_sdk_verification_pipeline(
    workspace_dir: Annotated[
        str,
        Field(..., min_length=1, description="Absolute filesystem path to the target workspace root."),
    ],
    module_name: Annotated[
        str,
        Field(default="account", min_length=1, description="Target BDD module name defined in .agents/state/phase-lock.json."),
    ] = "account",
    focus_area: Annotated[
        Literal["traceability", "encapsulation", "contracts", "full_gate"],
        Field(default="full_gate", description="Specific verification focus area for the sweep."),
    ] = "full_gate",
    session_id: Annotated[
        str | None,
        Field(default=None, description="Optional host session or user ID for Google Cloud audit compliance."),
    ] = None,
    response_format: Annotated[
        Literal["json", "markdown"],
        Field(default="json", description="Output format: 'json' for programmatic parsers or 'markdown' for agent/human inspection."),
    ] = "json",
) -> str:
    """Backward-compatible alias for the SDD Verification Pipeline.

    Executes deterministic static checks + an isolated READ-ONLY Google Antigravity SDK verification sweep.
    Guarantees that nested SDK agents NEVER execute write_to_file, replace_file_content, or run_command,
    preserving 100% of file mutations for the host Antigravity session's PreToolUse hook.
    """
    return await execute_verification_pipeline(
        workspace_dir=workspace_dir,
        module_name=module_name,
        focus_area=focus_area,
        session_id=session_id,
        response_format=response_format,
    )


if __name__ == "__main__":
    mcp.run()
