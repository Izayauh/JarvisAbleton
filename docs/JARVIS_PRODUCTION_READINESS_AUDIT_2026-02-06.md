# JarvisAbleton Production Readiness Audit
Date: 2026-02-06
Author: Codex (static repo audit)

## Scope
This is a static codebase and documentation audit of `C:\Users\isaia\Documents\JarvisAbleton` focused on production readiness: architecture, workflow, usability/UI, schema/data model health, security, reliability, and operations.

I did not run live Ableton-integrated tests in this environment.

## Executive Summary
JarvisAbleton is a technically ambitious local AI assistant for Ableton with real strengths in domain depth and feature breadth, but it is not production-ready yet.

The top blockers are:
1. Credential and secret hygiene issues (critical).
2. Multiple runtime-breaking orchestration defects (critical).
3. Architecture drift and monolithic runtime coupling (high).
4. Inconsistent docs/setup and missing production engineering baseline (high).
5. Schema inconsistency and weak validation across research/chain pipelines (high).

## Current Understanding Of The Software
JarvisAbleton is a local-first Python application that:
1. Accepts voice or text input and sends it to Gemini with tool/function calling (`jarvis_engine.py:62`, `jarvis_engine.py:2472`).
2. Routes commands through an internal multi-agent system (`agent_system.py`, `agents/`).
3. Executes Ableton operations over OSC via a controller layer (`ableton_controls/controller.py`).
4. Supports plugin discovery, chain generation, and research from web/YouTube (`discovery/`, `plugins/`, `research/`).
5. Persists learned state/history/preferences in local JSON files (`context/session_persistence.py:77`).
6. Includes crash-recovery/process automation for Ableton lifecycle (`ableton_controls/process_manager.py`).

## Current Goals (As Documented)
From the project objectives doc, the product goal is to move from basic voice control to an intelligent multi-agent audio engineer:
1. Phase 1 current: voice-controlled assistant.
2. Phase 2 in progress: intelligent audio engineer with research + orchestration.
3. Phase 3/4 future: autonomous production and platform expansion.

Evidence: `docs/PROJECT_OBJECTIVES.md:133`, `docs/PROJECT_OBJECTIVES.md:138`, `docs/PROJECT_OBJECTIVES.md:143`.

## Current Structure
Key structure appears to be:
1. Runtime orchestration and prompts: `jarvis_engine.py` (2570 lines).
2. Tool declarations: `jarvis_tools.py` (1079 lines).
3. OSC control and process management: `ableton_controls/` (`controller.py` is 1630 lines).
4. Agent system: `agent_system.py` + `agents/*`.
5. Research and extraction: `research/*`, `research_bot.py`.
6. Knowledge/persistence: `knowledge/*`, `context/*`, `config/*.json`.
7. Tests/scripts: `tests/` (53 Python files), `scripts/`.

## Workflow (Current Behavior)
Typical command flow appears to be:
1. User input (voice/text) is captured and sent to Gemini.
2. Gemini returns function calls from `ABLETON_TOOLS`.
3. `execute_ableton_function(...)` maps function to controller operations.
4. OSC commands are emitted to AbletonOSC / remote script.
5. Results are logged and sent back to the model.

Evidence: `jarvis_engine.py:2477`, `jarvis_engine.py:2480`, `jarvis_engine.py:504`, `jarvis_engine.py:535`.

## Production Blockers

### Critical

#### PR-001: Plaintext API keys and OAuth client secret are present in workspace
Impact: Immediate credential compromise risk and environment hijack risk.

Evidence:
1. `.env` contains live-looking keys (`.env:1` and subsequent lines).
2. OAuth client secret JSON is present and contains `client_secret` (`client_secret_127051967190-dsp343nhfjp20dsm52vk32hoivgl1k0k.apps.googleusercontent.com.json:1`).

#### PR-002: Ignore policy is insufficient for sensitive local/runtime files
Impact: High probability of accidental secret/data leakage in source distribution.

Evidence:
1. `.gitignore` only contains `venv/` (`.gitignore:1`).
2. README expects `.env.example`, but only `.env` exists in workspace (see mismatch below).

#### PR-003: Workflow coordinator has enum/value mismatches that can break runtime routing
Impact: Complex workflow orchestration can fail at runtime.

Evidence:
1. `IntentType(...)` casts routing strings that do not match enum values (`agents/workflow_coordinator.py:117`, `agents/workflow_coordinator.py:194`, `agents/workflow_coordinator.py:203`).
2. Uses nonexistent `AgentType.RESEARCH` while enum defines `RESEARCHER` (`agents/workflow_coordinator.py:281`, `agents/workflow_coordinator.py:286`, `agents/workflow_coordinator.py:304`, compare `agents/__init__.py`).

#### PR-004: Research execution path contains hard runtime defects
Impact: Research mode can crash or silently fail.

Evidence:
1. Undefined symbol usage: imports only `research_vocal_chain` but calls `research_coordinator.analyze_reference_track(...)` (`jarvis_engine.py:1138`, `jarvis_engine.py:1160`).
2. `research/research_coordinator.py` uses `os.path.basename(...)` without importing `os` (`research/research_coordinator.py:143`, `research/research_coordinator.py:168`; imports shown at `research/research_coordinator.py:8-11`).

### High

#### PR-005: Async/event-loop handling is inconsistent and known to fail
Impact: Deadlocks or runtime errors during live use; unstable behavior in mixed sync/async code.

Evidence:
1. Known anti-pattern comments in production path: "won't work" in running loop (`jarvis_engine.py:1619`, `jarvis_engine.py:1892`).
2. Direct `run_until_complete` calls inside utility paths (`jarvis_engine.py:1895`, `jarvis_engine.py:1956`).
3. Crash recovery runs `run_until_complete` from sync wrapper (`context/crash_recovery.py:270`, `context/crash_recovery.py:283`).
4. Historical runtime failures are visible in log: `asyncio.run() cannot be called from a running event loop` (`logs/jarvis.log:169`, `logs/jarvis.log:221`).

#### PR-006: Documentation drift causes setup failure and operator confusion
Impact: Onboarding friction, support burden, misconfiguration.

Evidence:
1. README references `.env.example` and copy command, but file does not exist in workspace (`README.md:48`, `README.md:51`, `README.md:161`).
2. README says `python test_ableton.py` in root, but file exists in `tests/` (`README.md:133`; file present at `tests/test_ableton.py`).
3. README references `architecture_visualization.html` at repo root (`README.md:162`), actual file is `docs/architecture_visualization.html`.
4. Model/version drift: README says Gemini 2.0 while runtime uses 2.5 IDs (`README.md:3`, `README.md:9`, `jarvis_engine.py:63`, `jarvis_engine.py:64`).
5. Protocol drift: `CLAUDE.md` still mandates `[STATUS: IDLE]` (`CLAUDE.md:54`), while fix docs claim it was removed (`docs/ISSUE_FIXES_SUMMARY.md:14-22`) and runtime prompt now says not to loop (`jarvis_engine.py:2331`).

#### PR-007: Monolithic runtime and heavy import-time side effects
Impact: Hard to test, hard to deploy, fragile startup behavior.

Evidence:
1. Global initialization at import time for env, model client, agent graph, workflow coordinator, crash recovery, and controllers (`jarvis_engine.py:49`, `jarvis_engine.py:62`, `jarvis_engine.py:80-87`, `jarvis_engine.py:91`, `jarvis_engine.py:97`, `jarvis_engine.py:104`).
2. Very large central modules (`jarvis_engine.py`, `jarvis_tools.py`, `ableton_controls/controller.py`).

#### PR-008: Logging strategy may expose sensitive/internal data and produces noisy artifacts
Impact: Security/privacy exposure, noisy operations, difficult debugging.

Evidence:
1. Full tool args/results are logged (`jarvis_engine.py:504`, `jarvis_engine.py:535`, `jarvis_engine.py:2592`, `jarvis_engine.py:2595`).
2. Log includes huge plugin inventories and research details (`logs/jarvis.log:540`, `logs/jarvis.log:347`).

#### PR-009: External URL ingestion lacks strict trust boundaries
Impact: SSRF-like local network probing risk and prompt-injection content ingestion risk.

Evidence:
1. Caller-provided URLs are accepted directly (`research/web_research.py:421`, `research/web_research.py:431`).
2. Arbitrary URL fetch via requests session (`research/web_research.py:318`, `research/web_research.py:320`).

### Medium

#### PR-010: Schema/model contracts are fragmented and weakly validated
Impact: Feature regressions and silent data-shape bugs as system evolves.

Evidence:
1. Research pipeline emits `plugin_name/category/parameters` (`research/research_coordinator.py:48-50`).
2. Chain builder expects `type` and `plugin_name`/`name`, and loosely interprets dicts (`plugins/chain_builder.py:316`, `plugins/chain_builder.py:352`, `plugins/chain_builder.py:354`, `plugins/chain_builder.py:355`).
3. Knowledge cache stores another dict shape (`knowledge/plugin_chain_kb.py:131-138`, `knowledge/plugin_chain_kb.py:500-503`).
4. No typed schema enforcement layer is visible (for example, no active pydantic model usage despite dependency in `requirements.txt`).

#### PR-011: Tests are numerous but mixed with manual/integration scripts; deterministic CI baseline is missing
Impact: Difficult to trust pass/fail as production quality gate.

Evidence:
1. Many tests are print-heavy/manual style (`tests/test_integration.py:12+`, `tests/chain_test_utils.py:159+`).
2. Multiple tests are environment-key gated/skipped (`tests/test_researched_chain_phase2.py:66`, `tests/test_researched_chain_phase2.py:108`, `tests/verify_serper.py:12`).
3. No project-level CI/deploy scaffolding found (`.github` absent, `pyproject.toml` absent, `pytest.ini` absent, `Dockerfile` absent).

#### PR-012: Cross-platform and repo hygiene issues
Impact: Tooling instability and friction.

Evidence:
1. A Windows-reserved filename artifact `nul` exists in root and causes tool errors.
2. Relative path assumptions for config/cache files make execution cwd-sensitive (`ableton_controls/controller.py:60`, `discovery/vst_discovery.py:110`, `macros/macro_builder.py:87`, `knowledge/plugin_chain_kb.py:22`).

#### PR-013: Usability/UI maturity gap
Impact: Suitable for power-user/dev workflows, not yet for broad production users.

Evidence:
1. Primary interaction is terminal/voice loop (`README.md:76-82`, `jarvis_engine.py:2472`, `jarvis_engine.py:2684`).
2. No standalone desktop/web UI app boundary is present in this repository.

## Security-Specific Notes
1. Rotate all keys/secrets immediately and revoke exposed OAuth credentials.
2. Add strict `.gitignore` patterns for `.env`, OAuth secret JSON, logs, caches, local state, screenshots.
3. Add pre-commit secret scanning (for example Gitleaks/Trufflehog) and CI scanning.
4. Restrict URL fetching with allowlist/deny private IP ranges and explicit scheme checks.
5. Redact sensitive values from logs and avoid dumping full command/result payloads by default.

## Architecture And Schema Recommendations
1. Split `jarvis_engine.py` into bounded modules: runtime bootstrap, model gateway, tool dispatcher, orchestration, session state.
2. Replace stringly-typed chain payloads with a single versioned model contract.
3. Introduce schema validation at every boundary (research output, planner output, executor input, persistence write).
4. Move side-effect-heavy initialization behind explicit `main()` startup wiring.
5. Convert undefined/fragile enum references into compile-time-safe mappings and add unit tests for intent routing contracts.

## Usability/UI Recommendations
1. Add a minimal operator UI for status, active session, tool calls, errors, and confirmations.
2. Add guided setup validation (Ableton connection, API keys, ports, remote script health).
3. Provide deterministic error surfaces with remediation steps instead of raw trace messages.
4. Add “safe mode” toggles for destructive operations and multi-step confirmation UX.

## Practical Productionization Roadmap

### Phase A (Immediate, 1-2 weeks)
1. Secret rotation and credential cleanup.
2. Fix critical runtime bugs (workflow coordinator enum mismatch, undefined research symbol, missing `os` import).
3. Align README/setup docs with actual files and commands.
4. Add strict ignore rules and remove runtime artifacts from source distribution.

### Phase B (2-6 weeks)
1. Establish schema contracts and validation layer.
2. Refactor monolith into testable service modules.
3. Stabilize async model (remove nested loop hacks and sync wrappers calling async incorrectly).
4. Introduce structured, redacted logging and telemetry levels.

### Phase C (6-12 weeks)
1. Add CI pipeline with unit/integration split and hardware-gated test jobs.
2. Add packaging/deployment baseline (installer/container where appropriate).
3. Deliver a usable operator UI and onboarding health checks.

## Bottom Line
The software demonstrates strong domain capability and a clear product vision, but production readiness is currently blocked by security hygiene, runtime stability defects, architectural coupling, schema inconsistency, and operator experience gaps.
