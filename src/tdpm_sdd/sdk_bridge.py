"""Read-Only Google Antigravity SDK MCP Bridge with strict PreToolUse isolation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef, attr-defined]
    except (ImportError, AttributeError):
        FastMCP = Any  # type: ignore[assignment, misc]
from pydantic import BaseModel, Field, ValidationError

from .auditors import run_module_gate_verification
from .models import load_ledger

mcp = FastMCP("tdpm-sdk-bridge")

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
STRICT_AUDIT_SKILL_PATH = PLUGIN_ROOT / "skills" / "strict-audit"
ALLOWED_SDK_READ_TOOLS = frozenset(
    {"view_file", "code_search", "check_file_metrics", "run_deterministic_gate_check"}
)


class SDKVerificationRequest(BaseModel):
    """Validated parameters for run_sdk_verification_pipeline."""

    workspace_dir: str = Field(..., min_length=1, description="Absolute path to the target workspace")
    module_name: str = Field(default="account", min_length=1)
    focus_area: Literal["traceability", "encapsulation", "contracts", "full_gate"] = Field(
        default="full_gate"
    )


class AuditResult(BaseModel):
    """Structured read-only audit payload returned to the host Antigravity session."""

    status: Literal["success", "error"]
    workspace_dir: str
    module_name: str
    phase: int
    selected_paradigm: str | None
    deterministic_gate_passed: bool
    deterministic_findings: list[dict]
    sdk_semantic_report: str
    tokens_used: int = 0


@mcp.tool()
async def run_sdk_verification_pipeline(
    workspace_dir: str,
    module_name: str = "account",
    focus_area: str = "full_gate",
) -> str:
    """Executes deterministic static checks + an isolated READ-ONLY Google Antigravity SDK verification sweep.

    Guarantees that nested SDK agents NEVER execute write_to_file, replace_file_content, or run_command,
    preserving 100% of file mutations for the host Antigravity session's PreToolUse hook.
    """
    try:
        req = SDKVerificationRequest(
            workspace_dir=workspace_dir,
            module_name=module_name,
            focus_area=focus_area,  # type: ignore[arg-type]
        )
    except ValidationError as exc:
        return AuditResult(
            status="error",
            workspace_dir=workspace_dir,
            module_name=module_name,
            phase=-1,
            selected_paradigm=None,
            deterministic_gate_passed=False,
            deterministic_findings=[],
            sdk_semantic_report=f"Invalid verification request: {exc}",
        ).model_dump_json(indent=2)

    ws_path = Path(req.workspace_dir).resolve()
    state = load_ledger(ws_path)
    if not state or req.module_name not in state.modules:
        return AuditResult(
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
        ).model_dump_json(indent=2)

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

    return AuditResult(
        status="success",
        workspace_dir=str(ws_path),
        module_name=req.module_name,
        phase=mod.current_phase,
        selected_paradigm=mod.bdd_dialogue.selected_paradigm,
        deterministic_gate_passed=gate_report.passed,
        deterministic_findings=[f.model_dump() for f in gate_report.findings],
        sdk_semantic_report=sdk_report_text,
        tokens_used=tokens_used,
    ).model_dump_json(indent=2)


if __name__ == "__main__":
    mcp.run()
