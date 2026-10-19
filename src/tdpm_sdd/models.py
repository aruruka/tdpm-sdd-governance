"""Unified Pydantic v2 State Ledger Models consolidating .tdpm/state.json and .agents/state/phase-lock.json."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import IntEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SDDPhase(IntEnum):
    """6-Phase Spec-Driven Development (SDD) causal sequence."""

    P0_BROWNFIELD_TRIAGE = 0
    P1_STRATEGIC_DDD = 1
    P2_ITERATIVE_BDD_AND_BRIDGE = 2
    P3_TACTICAL_DDD = 3
    P4_INTERFACE_CONTRACTS = 4
    P5_IMPLEMENTATION_AND_HARNESS = 5


PHASE_NAMES: dict[int, str] = {
    0: "P0_BROWNFIELD_DISCOVERY_AND_TRIAGE",
    1: "P1_STRATEGIC_DDD_AND_CONTEXT_MAP",
    2: "P2_ITERATIVE_BDD_AND_PATTERN_GATE",
    3: "P3_TACTICAL_DDD_STUBS_AND_PORTS",
    4: "P4_INTERFACE_AND_STORAGE_CONTRACTS",
    5: "P5_IMPLEMENTATION_AND_VERIFICATION",
}

PHASE_OWNERS: dict[int, Literal["pm-planner", "td-auditor"]] = {
    0: "pm-planner",
    1: "pm-planner",
    2: "pm-planner",
    3: "td-auditor",
    4: "td-auditor",
    5: "td-auditor",
}

SupportedLanguage = Literal["go", "python", "typescript"]
TacticalParadigm = Literal[
    "CQRS_EVENT_SOURCING",
    "STATE_BASED_OCC",
    "VERTICAL_SLICE_CRUD",
]
Phase5SubPhase = Literal[
    "5a_RED_HARNESS",
    "5b_GREEN_IMPL",
    "5c_VERIFICATION",
]
AgentPersona = Literal["td-pm", "pm-planner", "td-auditor", "sdk-architect"]


class ADRRecord(BaseModel):
    """Architecture Decision Record tracked in the unified TD/PM ledger."""

    model_config = ConfigDict(extra="forbid")

    adr_id: str = Field(..., min_length=1, description="Identifier such as ADR-001")
    title: str = Field(..., min_length=1)
    status: Literal["proposed", "accepted", "superseded"] = "accepted"
    artifact_path: str = Field(..., min_length=1)
    decided_by: AgentPersona = "td-auditor"
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )


class BacklogItem(BaseModel):
    """Product roadmap / post-V1 iteration backlog item managed by pm-planner."""

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(..., min_length=1)
    module: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    priority: Literal["P0", "P1", "P2"] = "P1"
    status: Literal["planned", "in_progress", "completed"] = "planned"


class BDDDialogueState(BaseModel):
    """Tracks multi-round Socratic Example Mapping & Bridge 2.5 Pattern Selection."""

    model_config = ConfigDict(extra="forbid")

    rounds_completed: int = Field(default=0, ge=0)
    required_minimum_rounds: int = Field(default=2, ge=1)
    unresolved_questions: list[str] = Field(default_factory=list)
    pattern_selection_approved: bool = False
    selected_paradigm: TacticalParadigm | None = None
    coordination_scope: Literal["SINGLE_AGGREGATE", "PROCESS_MANAGER_SAGA", "CRUD_DIRECT"] = (
        "SINGLE_AGGREGATE"
    )


class ModuleSDDState(BaseModel):
    """Per-module SDD lifecycle state, persona ownership, and cryptographic artifact locks."""

    model_config = ConfigDict(extra="forbid")

    module_name: str = Field(..., min_length=1)
    language: SupportedLanguage = "go"
    current_phase: int = Field(default=0, ge=0, le=5)
    phase_name: str = Field(default=PHASE_NAMES[0])
    sub_phase: Phase5SubPhase | None = None
    active_owner: AgentPersona = "pm-planner"
    gates_passed: list[str] = Field(default_factory=list)
    bdd_dialogue: BDDDialogueState = Field(default_factory=BDDDialogueState)
    locked_artifacts: dict[str, str] = Field(
        default_factory=dict,
        description="Map of workspace-relative forward-slash path to sha256:<hex>",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )


class WorkspaceGovernanceState(BaseModel):
    """Unified root ledger stored at <workspace>/.agents/state/phase-lock.json."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "2.0"
    project_name: str = Field(..., min_length=1)
    default_module: str = Field(default="account")
    active_module: str = Field(default="account")
    adrs: list[ADRRecord] = Field(default_factory=list)
    backlog: list[BacklogItem] = Field(default_factory=list)
    modules: dict[str, ModuleSDDState] = Field(default_factory=dict)

    def get_active_module(self) -> ModuleSDDState:
        if self.active_module not in self.modules:
            raise KeyError(
                f"Active module '{self.active_module}' not found in modules: {list(self.modules.keys())}"
            )
        return self.modules[self.active_module]


def compute_sha256(file_path: Path) -> str:
    """Computes 'sha256:<hex>' digest of a file normalizing CRLF to LF for cross-OS determinism."""
    raw = file_path.read_bytes().replace(b"\r\n", b"\n")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def resolve_ledger_path(workspace_root: Path) -> Path:
    """Returns canonical ledger path <workspace>/.agents/state/phase-lock.json."""
    return workspace_root / ".agents" / "state" / "phase-lock.json"


def load_ledger(workspace_root: Path) -> WorkspaceGovernanceState | None:
    """Loads and validates the unified Pydantic v2 state ledger if it exists."""
    path = resolve_ledger_path(workspace_root)
    if not path.exists():
        return None
    return WorkspaceGovernanceState.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def save_ledger(workspace_root: Path, state: WorkspaceGovernanceState) -> Path:
    """Atomically writes the Pydantic-validated state ledger to disk."""
    path = resolve_ledger_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path
