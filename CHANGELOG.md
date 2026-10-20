# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Dual MCP Tool Registration**: Canonical `tdpm_run_sdk_verification_pipeline` tool following `{service}_{action}_{resource}` conventions alongside backward-compatible `run_sdk_verification_pipeline`.
- **MCP Tool Annotations & Rich Schema**: Published explicit parameter constraints (`minLength`, `enum`), field descriptions, and MCP execution hints (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`).
- **Flexible Response Formats**: Added `response_format` parameter supporting both machine-readable JSON and human/agent-readable Markdown presentations.
- **Google Cloud Audit Telemetry**: Added `session_id` and UTC timestamps to `AuditResult` payload and implemented structured JSON logging to `stderr`.
- **Transport & Stdio Hygiene**: Ensured stdout is strictly reserved for JSON-RPC 2.0 communication while routing all operational logs to stderr.

## [1.0.0] - 2026-10-20

### Added
- **6-Phase BDD-First SDD Lifecycle Engine**: Full state machine implementing Phase 0 through Phase 5 (`P0_BROWNFIELD_DISCOVERY_AND_TRIAGE` to `P5_IMPLEMENTATION_AND_VERIFICATION`).
- **Cryptographic Gate Verification (`G0`–`G5`)**: Deterministic audit rules and SHA-256 artifact locking via `.agents/state/phase-lock.json`.
- **PreToolUse Gatekeeper**: Real-time interceptor blocking premature code generation, cross-context DDD leaks, sealed aggregate getter pollution, and over-engineering patterns.
- **Socratic Dialogue & Pattern Gate**: Support for multi-round BDD Example Mapping interviews and tactical paradigm locking (`CQRS_EVENT_SOURCING`, `STATE_BASED_OCC`, `VERTICAL_SLICE_CRUD`).
- **Antigravity Agent Personas & Skills**: Integrated agents (`@td-pm`, `@pm-planner`, `@td-auditor`, `@sdk-architect`) and skills (`sdd-bdd-architect`, `sdd-tactical-contract`, `strict-audit`, `sdd-cqrs-gate`).
- **MCP Server (`tdpm-sdk-bridge`)**: Model Context Protocol bridge exposing read-only `run_sdk_verification_pipeline` for deep architectural verification.
- **Multi-Module Support**: Ability to govern multiple distinct modules/services independently within a single workspace ledger.
