"""Parameterized static auditors for Go AST, Gherkin BDD, OpenAPI/AsyncAPI contracts, and SHA-256 integrity."""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from .models import ModuleSDDState, WorkspaceGovernanceState, compute_sha256


class AuditFinding(BaseModel):
    """Single deterministic audit finding."""

    severity: str = Field(..., pattern="^(ERROR|WARNING|INFO)$")
    file_path: str
    line: int = 1
    rule_id: str
    message: str


class GateAuditReport(BaseModel):
    """Structured result emitted by verify-gate and strict-audit."""

    passed: bool
    module: str
    phase: int
    sub_phase: str | None = None
    paradigm: str | None = None
    findings: list[AuditFinding] = Field(default_factory=list)
    summary: str


GO_FENCE_RE = re.compile(r"```go\s*\n(.*?)```", re.DOTALL)
GO_FUNC_BLOCK_RE = re.compile(
    r"func\s+(?:\([^)]+\)\s+)?([A-Za-z0-9_]+)\s*\([^)]*\)[^{]*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}",
    re.MULTILINE,
)
GHERKIN_TRANSPORT_LEAK_RE = re.compile(
    r"\b(HTTP\s+\d{3}|status\s+code\s+\d{3}|SELECT\s+|INSERT\s+INTO|UPDATE\s+bank_accounts|pgx\.|KafkaTopic|localhost:\d+)\b",
    re.IGNORECASE,
)


def audit_blueprint_no_code_dump(
    content: str, file_path: str = "docs/architecture/ARCHITECTURE_BLUEPRINT.md"
) -> list[AuditFinding]:
    """Ensures architecture blueprints do not embed concrete Go implementation dumps (>15 lines)."""
    findings: list[AuditFinding] = []
    for match in GO_FENCE_RE.finditer(content):
        block = match.group(1).strip("\n")
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) > 15:
            line_num = content[: match.start()].count("\n") + 1
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path=file_path,
                    line=line_num,
                    rule_id="SDD-BLUEPRINT-NO-CODE-DUMP",
                    message=(
                        f"Go code block contains {len(lines)} non-empty lines (max allowed in blueprint is 15 for "
                        "interface signatures). Concrete implementation bodies are prohibited in Phase 1-3 blueprints."
                    ),
                )
            )
    return findings


def audit_gherkin_purity(content: str, file_path: str) -> list[AuditFinding]:
    """Verifies Gherkin .feature files use Ubiquitous Language without HTTP/SQL/Kafka transport leakage."""
    findings: list[AuditFinding] = []
    if "Feature:" not in content:
        findings.append(
            AuditFinding(
                severity="ERROR",
                file_path=file_path,
                line=1,
                rule_id="BDD-MISSING-FEATURE",
                message="Gherkin file must declare a 'Feature:' header.",
            )
        )
    if not all(kw in content for kw in ("Given ", "When ", "Then ")):
        findings.append(
            AuditFinding(
                severity="ERROR",
                file_path=file_path,
                line=1,
                rule_id="BDD-MISSING-GWT",
                message="Gherkin file must contain declarative 'Given', 'When', and 'Then' behavioral steps.",
            )
        )
    for idx, line in enumerate(content.splitlines(), start=1):
        leak = GHERKIN_TRANSPORT_LEAK_RE.search(line)
        if leak:
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path=file_path,
                    line=idx,
                    rule_id="BDD-TRANSPORT-LEAKAGE",
                    message=(
                        f"Transport/infrastructure term '{leak.group(0)}' leaked into Phase 2 Gherkin spec. "
                        "Write scenarios strictly in domain Ubiquitous Language."
                    ),
                )
            )
    return findings


def audit_go_stub_only(content: str, file_path: str) -> list[AuditFinding]:
    """Verifies that a Phase 3 Go file contains only types, interfaces, or SDD_STUB panic bodies."""
    findings: list[AuditFinding] = []
    for match in GO_FUNC_BLOCK_RE.finditer(content):
        fn_name = match.group(1)
        body = match.group(2).strip()
        # Strip line comments
        code_lines = [
            ln.strip()
            for ln in body.splitlines()
            if ln.strip() and not ln.strip().startswith("//")
        ]
        if not code_lines:
            continue
        if len(code_lines) > 1 or "SDD_STUB" not in code_lines[0]:
            line_num = content[: match.start()].count("\n") + 1
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path=file_path,
                    line=line_num,
                    rule_id="SDD-P3-STUB-ONLY",
                    message=(
                        f"Function '{fn_name}' contains concrete implementation logic in Phase 3. "
                        'All Phase 3 function bodies must be single-line `panic("SDD_STUB: ...")` stubs.'
                    ),
                )
            )
    return findings


def audit_go_cqrs_encapsulation(content: str, file_path: str) -> list[AuditFinding]:
    """Audits Go CQRS/ES files for Candidate B1/B2 aggregate encapsulation and cross-context import rules."""
    findings: list[AuditFinding] = []
    norm = file_path.replace("\\", "/")

    if "/cmd/" in norm and 'query"' in content:
        findings.append(
            AuditFinding(
                severity="ERROR",
                file_path=file_path,
                line=1,
                rule_id="DDD-CROSS-CONTEXT-IMPORT",
                message="Command context package imports Query context package.",
            )
        )
    if "/query/" in norm and 'cmd/' in content:
        findings.append(
            AuditFinding(
                severity="ERROR",
                file_path=file_path,
                line=1,
                rule_id="DDD-CROSS-CONTEXT-IMPORT",
                message="Query context package imports Command context package.",
            )
        )

    if norm.endswith("_aggregate.go"):
        for idx, line in enumerate(content.splitlines(), start=1):
            if re.search(
                r"func\s+\([^)]+\)\s*(GetBalance|Balance|BalanceCents)\s*\(", line
            ):
                findings.append(
                    AuditFinding(
                        severity="ERROR",
                        file_path=file_path,
                        line=idx,
                        rule_id="DDD-SEALED-AGGREGATE-GETTER",
                        message="Aggregate Root exposes a public balance getter, violating Candidate B1 encapsulation.",
                    )
                )
    return findings


def audit_vertical_slice_minimalism(content: str, file_path: str) -> list[AuditFinding]:
    """Enforces Ponytail minimalism when module selected VERTICAL_SLICE_CRUD in Bridge 2.5b."""
    findings: list[AuditFinding] = []
    norm = file_path.replace("\\", "/").lower()
    forbidden_patterns = ("aggregate", "event_store", "outbox_relay", "command_bus")
    for pat in forbidden_patterns:
        if pat in norm:
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path=file_path,
                    line=1,
                    rule_id="PONYTAIL-OVERENGINEERING-BLOCK",
                    message=(
                        f"File '{file_path}' introduces '{pat}' in a module governed by VERTICAL_SLICE_CRUD. "
                        "Supporting CRUD modules must not use Aggregate Roots, Event Sourcing, or Outbox tables."
                    ),
                )
            )
    return findings


def audit_yaml_contract(file_path: Path, rel_path: str) -> list[AuditFinding]:
    """Validates OpenAPI 3.1 and AsyncAPI 3.0 YAML structure and CQRS domain bindings."""
    findings: list[AuditFinding] = []
    try:
        doc = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as exc:
        return [
            AuditFinding(
                severity="ERROR",
                file_path=rel_path,
                line=1,
                rule_id="CONTRACT-YAML-PARSE",
                message=f"Invalid YAML syntax: {exc}",
            )
        ]

    if not isinstance(doc, dict):
        return [
            AuditFinding(
                severity="ERROR",
                file_path=rel_path,
                line=1,
                rule_id="CONTRACT-ROOT-OBJECT",
                message="Contract root must be a YAML mapping.",
            )
        ]

    if "openapi" in rel_path.lower():
        version = str(doc.get("openapi", ""))
        if not version.startswith("3."):
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path=rel_path,
                    line=1,
                    rule_id="OPENAPI-VERSION",
                    message=f"Expected OpenAPI 3.x specification, found '{version}'.",
                )
            )
        if not doc.get("paths"):
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path=rel_path,
                    line=1,
                    rule_id="OPENAPI-PATHS",
                    message="OpenAPI specification must declare non-empty 'paths'.",
                )
            )
    elif "asyncapi" in rel_path.lower():
        version = str(doc.get("asyncapi", ""))
        if not version.startswith(("2.", "3.")):
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path=rel_path,
                    line=1,
                    rule_id="ASYNCAPI-VERSION",
                    message=f"Expected AsyncAPI 2.x/3.x specification, found '{version}'.",
                )
            )
        if not doc.get("channels"):
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path=rel_path,
                    line=1,
                    rule_id="ASYNCAPI-CHANNELS",
                    message="AsyncAPI specification must declare event 'channels'.",
                )
            )
    return findings


def verify_locked_artifacts_integrity(
    workspace_root: Path, mod: ModuleSDDState
) -> list[AuditFinding]:
    """Verifies that all locked upstream artifacts exist and match their recorded SHA-256 digests."""
    findings: list[AuditFinding] = []
    for rel_path, expected_hash in mod.locked_artifacts.items():
        abs_path = workspace_root / rel_path
        if not abs_path.exists():
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path=rel_path,
                    line=1,
                    rule_id="SDD-LOCK-MISSING",
                    message=f"Locked artifact '{rel_path}' is missing from disk.",
                )
            )
            continue
        actual_hash = compute_sha256(abs_path)
        if actual_hash != expected_hash:
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path=rel_path,
                    line=1,
                    rule_id="SDD-LOCK-DRIFT",
                    message=(
                        f"Cryptographic SHA-256 drift detected on locked artifact '{rel_path}': "
                        f"expected {expected_hash[:19]}..., got {actual_hash[:19]}..."
                    ),
                )
            )
    return findings


def run_module_gate_verification(
    workspace_root: Path, state: WorkspaceGovernanceState, module_name: str
) -> GateAuditReport:
    """Runs the comprehensive gate verification suite for the specified module's current phase."""
    mod = state.modules[module_name]
    findings = verify_locked_artifacts_integrity(workspace_root, mod)
    phase = mod.current_phase

    if phase <= 3:
        blueprint = workspace_root / "docs" / "architecture" / "ARCHITECTURE_BLUEPRINT.md"
        if blueprint.exists():
            findings.extend(
                audit_blueprint_no_code_dump(
                    blueprint.read_text(encoding="utf-8", errors="replace")
                )
            )

    if phase >= 1:
        bmap = workspace_root / "docs" / "architecture" / "boundary-map.md"
        if not bmap.exists():
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path="docs/architecture/boundary-map.md",
                    rule_id="G1-MISSING-BOUNDARY-MAP",
                    message="Phase 1 requires 'docs/architecture/boundary-map.md'.",
                )
            )

    if phase == 2:
        if mod.bdd_dialogue.rounds_completed < mod.bdd_dialogue.required_minimum_rounds:
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path=".agents/state/phase-lock.json",
                    rule_id="G2-DIALOGUE-ROUNDS",
                    message=(
                        f"Phase 2 requires >={mod.bdd_dialogue.required_minimum_rounds} Socratic BDD dialogue rounds "
                        f"(completed: {mod.bdd_dialogue.rounds_completed})."
                    ),
                )
            )
        if mod.bdd_dialogue.unresolved_questions:
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path="specs/bdd/example-map.md",
                    rule_id="G2-UNRESOLVED-QUESTIONS",
                    message=f"Unresolved BDD edge-case questions remain: {mod.bdd_dialogue.unresolved_questions}",
                )
            )
        if not mod.bdd_dialogue.pattern_selection_approved or not mod.bdd_dialogue.selected_paradigm:
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path="specs/bdd/event-modeling-and-pattern-gate.md",
                    rule_id="G2-PATTERN-GATE",
                    message="Bridge 2.5b Tactical Pattern Selection Gate has not been approved.",
                )
            )
        features_dir = workspace_root / "specs" / "features"
        feature_files = list(features_dir.glob("*.feature")) if features_dir.exists() else []
        if not feature_files:
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path="specs/features/",
                    rule_id="G2-MISSING-FEATURES",
                    message="Phase 2 requires at least one declarative '.feature' specification.",
                )
            )
        for ff in feature_files:
            rel = ff.relative_to(workspace_root).as_posix()
            findings.extend(
                audit_gherkin_purity(ff.read_text(encoding="utf-8", errors="replace"), rel)
            )

    if phase >= 3 and mod.language == "go":
        mod_dir = workspace_root / "internal" / module_name
        go_files = list(mod_dir.rglob("*.go")) if mod_dir.exists() else []
        if not go_files:
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path=f"internal/{module_name}/",
                    rule_id="G3-MISSING-TACTICAL-FILES",
                    message=f"No Go files found under 'internal/{module_name}/'.",
                )
            )
        for gf in go_files:
            rel = gf.relative_to(workspace_root).as_posix()
            text = gf.read_text(encoding="utf-8", errors="replace")
            if mod.bdd_dialogue.selected_paradigm == "CQRS_EVENT_SOURCING":
                findings.extend(audit_go_cqrs_encapsulation(text, rel))
            elif mod.bdd_dialogue.selected_paradigm == "VERTICAL_SLICE_CRUD":
                findings.extend(audit_vertical_slice_minimalism(text, rel))
            if phase == 3 and not rel.endswith("_test.go"):
                findings.extend(audit_go_stub_only(text, rel))

    if phase == 4:
        openapi_dir = workspace_root / "specs" / "openapi"
        asyncapi_dir = workspace_root / "specs" / "asyncapi"
        yaml_files: list[Path] = []
        if openapi_dir.exists():
            yaml_files.extend(openapi_dir.glob("*.yaml"))
        if asyncapi_dir.exists():
            yaml_files.extend(asyncapi_dir.glob("*.yaml"))
        if not yaml_files:
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    file_path="specs/openapi/",
                    rule_id="G4-MISSING-CONTRACTS",
                    message="Phase 4 requires OpenAPI and/or AsyncAPI YAML specifications.",
                )
            )
        for yf in yaml_files:
            findings.extend(
                audit_yaml_contract(yf, yf.relative_to(workspace_root).as_posix())
            )

    errors = [f for f in findings if f.severity == "ERROR"]
    passed = len(errors) == 0
    summary = (
        f"Gate verification PASSED for module '{module_name}' at Phase {phase} ({mod.phase_name})."
        if passed
        else f"Gate verification FAILED for module '{module_name}' at Phase {phase} with {len(errors)} error(s)."
    )
    return GateAuditReport(
        passed=passed,
        module=module_name,
        phase=phase,
        sub_phase=mod.sub_phase,
        paradigm=mod.bdd_dialogue.selected_paradigm,
        findings=findings,
        summary=summary,
    )
