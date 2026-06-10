# Changelog

All notable changes to this project will be documented in this file.

## v0.10.0 (2026-06-11)

### Added
- **Phase 10.1 Parallel Task Execution**: DAG-based dependency resolution (`task_parallel.py`), parallel dispatch engine (`task_parallel_dispatch.py`), event-driven coordination (`task_parallel_events.py`), WebSocket integration (`task_parallel_ws.py`), helper utilities (`task_parallel_helpers.py`)
- **Resource Conflict Detection**: Resource model and conflict detection (`task_resource.py`), compatibility layer (`task_resource_compat.py`), resource usage detection (`task_resource_detect.py`)
- **Task Retry System**: Retry policy engine (`task_retry_policy.py`), retry execution (`task_retry.py`), retry helpers (`task_retry_helpers.py`)
- **Phase 10.2 RBAC**: Role-based access control (`rbac.py`), RBAC middleware (`rbac_middleware.py`), JWT token management (`token_manager.py`), RBAC storage (`storage/rbac.py`), token storage (`storage/tokens.py`)
- **Audit Logging**: Security event audit trail (`audit.py`)
- **Phase 10.3 Plugin Ecosystem**: Plugin manager (`plugin_manager.py`), plugin discovery (`plugin_discovery.py`), plugin sandbox (`plugin_sandbox.py`), plugin extension points (`plugin_extensions.py`), plugin hooks (`plugin_hooks.py`), base plugin class (`plugin.py`)
- **Parallel Execution Storage**: Parallel task storage layer (`storage/parallel.py`)
- **Tests**: 20+ new test files covering parallel execution, resource management, retry, RBAC, tokens, audit, plugins, and integration
- **Design Doc**: Phase 10 architecture document (`docs/DESIGN-phase10.md`)

### Changed
- Coordinator `main.py`, `models.py`, `config.py`, `router.py`, `ws.py`, `ws_endpoint.py`, `ws_handlers.py` updated for Phase 10 features
- Storage layer (`schema.py`, `storage.py`, `agents.py`, `tasks.py`) extended for RBAC, tokens, and parallel execution
- Task execution (`task_exec.py`, `task_assign.py`, `task_models.py`) updated for parallel and retry support
- Input validation (`input_validation.py`) enhanced
- Documentation (`docs/API.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`) updated
- Dockerfile, README.md, pyproject.toml, uv.lock updated
- Test infrastructure (`tests/integration/conftest.py`, `tests/test_phase8_integration.py`) updated

## v0.9.4 (2026-06-10)

### Changed
- **Phase 9.5a Documentation Update**: README, API docs, and ARCHITECTURE updated to reflect v0.9.3 features
- API documentation expanded with Agent register/approve/heartbeat + Rate Limit API endpoints
- Architecture documentation updated with platform independence, task engine, Agent registry, and Rate Limiter architecture
- ROADMAP updated with Phase 9.5a status

## v0.9.3 (2026-06-10)

### Added
- **Phase 9.3 Agent Registration Protocol**: Token-based WebSocket authentication with pending/reserved agent flow (`ws_endpoint.py`, `ws_handlers.py`, `router.py`)
- **Agent Heartbeat + Timeout**: Background heartbeat checker (`agent_heartbeat.py`), timeout detection (`timeout_checker.py`), online tracking
- **Agent Capability Declaration**: Capability model (`capability.py`) and registration in main
- **Agent Storage Updates**: Schema v7 with agent registrations, pending tokens, status tracking (`schema.py`, `agents.py`, `storage.py`)
- **Phase 9.4 API Rate Limiting**: TokenBucket algorithm (`token_rate_limiter.py`), existing rate limiter enhanced (`rate_limiter.py`)
- **Client-Side Rate Limiting**: RateLimitTracker in agent client (`rate_limit.py`, `client.py`)
- **Rate Limit Routing + Flush**: Coordinated rate limit enforcement (`rate_limit_router.py`, `rate_limit_router2.py`, `rate_limit_flush.py`)
- **WS Rate Limit Integration**: Per-connection rate limiting in WebSocket layer (`ws_rate_limit.py`)
- **Tests**: 9 new test files — 6 for Phase 9.3 (models, storage, auth, heartbeat×2, timeout) + 3 for Phase 9.4 (tracker, bucket, limiter) — 62/62 total passing
- **Design Doc**: Phase 9 rate limiting design document (`DESIGN-phase9-rate-limiting.md`)

### Changed
- Agent client `__init__.py` and `client.py` updated for rate limit tracker integration
- Coordinator `main.py`, `models.py`, `config.py`, `config_defaults.yaml` updated for Phase 9.3 + 9.4
- `ws_endpoint.py` and `ws_handlers.py` — major overhaul for auth flow and rate limiting
- Test files `test_main_integration.py`, `test_router.py`, `test_ws.py` updated for new features
- ROADMAP updated with Phase 9.3—9.4 status
- 11 AsyncMock garbage files cleaned from repo root

## v0.9.2 (2026-06-10)

### Added
- **Phase 9.2d Task Execution**: `task_exec.py` handles task execution with result collection, duplicate handler removed
- **Phase 9.2e Task Verification**: New `task_verify/` package (simple_check, auto_check, accept_result, delegate) replacing monolithic `task_verify.py`
- **WebSocket Task Dispatch**: `ws_endpoint.py` updated with task dispatch support
- **New Tests**: `test_accept_result.py`, `test_task_exec_status.py`, `test_task_verify_delegate.py`, `test_ws_task_dispatch.py`

### Changed
- `test_task_verify.py` converted to async, added dependency check tests
- `test_task_exec.py` cleaned up (duplicate tests removed)
- `ws_endpoint.py` imports updated for new task_verify package
- ROADMAP updated with Phase 9.2d-e status
- 10+ AsyncMock garbage files cleaned from repo root

## v0.9.1 (2026-06-10)

### Added
- **Phase 9.2a Task Models + Storage**: Task data models (`task_models.py`) with status, priority, assignments; persistent task storage (`storage/tasks.py`) with schema v6
- **Phase 9.2b Task Generator**: LLM-driven task generation (`task_gen/generator.py`) with heuristic fallback (`task_gen/heuristic.py`), prompts (`task_gen/prompts.py`), and validation (`task_gen/validation.py`)
- **Phase 9.2c Task Assigner**: Capability-based agent matching with round-robin fallback (`task_assign.py`)
- **Task Execution + Verification**: `task_exec.py` for executing tasks, `task_verify.py` for result validation
- **Comprehensive Tests**: 9 test files covering task models, storage, generation (LLM + heuristic), assignment, execution, verification, and message types

### Changed
- Schema version bumped to 6 (task tables)
- Storage layer extended with task CRUD operations
- Coordinator models updated with new task-related fields

## v0.9.0 (2026-06-10)

### Changed
- **Phase 9.1 Platform Independence**: Package restructure from flat `coordinator/` to `agora/coordinator/` namespace
- **Docker image**: Containerized deployment with multi-stage Dockerfile
- **Config overhaul**: Unified configuration system with environment-aware settings
- **Entry points**: New CLI entry points (`agora`, `agora-coordinator`, `agora-agent`) replacing legacy scripts
- **Build system**: Hatchling wheel build targeting `agora` package

### Removed
- Legacy flat module files (`__init__.py`, `cmd_*.py`, `commands.py`) replaced by `agora/` package
- Old `agent_client/` standalone module — now under `agora/agent_client/`

## v0.8.0 (2026-06-09)

### Added
- **Observability (Phase 8.1)**: Metrics, events, and traces infrastructure
  - `coordinator/observability/`: Prometheus metrics exporter, structured event logging, OpenTelemetry-compatible trace context propagation
  - `coordinator/storage/events.py`: Event persistence layer
  - `coordinator/storage/global_store.py`: Cross-tenant shared state store
  - `coordinator/storage/storage_manager.py`: Multi-backend storage orchestration

- **Multi-tenant Infrastructure (Phase 8.2)**: Tenant isolation and management
  - `coordinator/tenant/`: Tenant models, guard (quota/enforcement), manager (lifecycle), router (API endpoints)
  - Lazy tenant initialization via WebSocket path routing

- **Dashboard Frontend (Phase 8.3)**: Real-time monitoring UI
  - `coordinator/dashboard.py`: Dashboard API endpoints (metrics, tenant status, agent health)
  - `coordinator/static/dashboard.html`: Single-page monitoring dashboard
  - `coordinator/static/dashboard.js`: Real-time dashboard updates via WebSocket

- **Integration & Testing (Phase 8.4)**: End-to-end validation
  - `tests/test_observability.py`: Observability pipeline tests
  - `tests/test_multi_tenant.py`: Tenant isolation and lifecycle tests
  - `tests/test_dashboard.py`: Dashboard API and UI tests
  - `tests/test_phase8_integration.py`: Full Phase 8 integration tests
  - `tests/test_ws_tenant_lazy_init.py`: Tenant lazy-init WebSocket tests
  - `docs/DESIGN-phase8.md`: Phase 8 design document

- **Documentation**: Updated API.md, ARCHITECTURE.md, INSPECTION-LOG.md, ROADMAP.md

### Changed
- Rebranded to Agora: independent multi-agent platform
- `coordinator/main.py`: Integrated observability, tenant, and dashboard subsystems
- `coordinator/models.py`: Extended models with tenant/observability fields
- `coordinator/router.py`: New observability, tenant, and dashboard endpoints
- `coordinator/storage/schema.py`: Extended schema for events and tenant tables
- `coordinator/storage/storage.py`: Multi-tenant storage support
- `coordinator/ws.py`: Tenant-aware WebSocket routing
- `coordinator/ws_endpoint.py`: Enhanced with tenant and observability hooks
- `README.md`: Updated feature list and architecture description

### Fixed
- Cleaned up AsyncMock garbage files from project root

## v0.7.0 (2026-06-08)

### Added
- **Integration Test Infrastructure**: E2E integration tests with real WebSocket coordinator
  - `tests/integration/conftest.py`: Shared fixtures (live coordinator, websocket clients)
  - `tests/integration/test_e2e_basic.py`: Basic motion create/discuss/vote flow
  - `tests/integration/test_e2e_multiple.py`: Multi-agent concurrent discussion
  - `tests/integration/test_e2e_reconnect.py`: WebSocket reconnection and state recovery
  - `tests/integration/test_smoke.py`: Quick smoke/healthcheck tests
  - Pytest config with `integration` marker and asyncio auto mode

- **Plugin Hooks**: Hermes plugin lifecycle integration
  - `on_session_start`: Initialize agent connections on session start
  - `on_session_end`: Clean up agent connections on session end
  - `post_tool_call`: Post-process tool call results

- **Docker Production Deployment**: Multi-stage Docker build for production
  - Multi-stage Dockerfile: builder stage → production stage with minimal image
  - `docker-compose.prod.yaml`: Production orchestration with coordinator service
  - CMD simplification for production entrypoint

- **Documentation**:
  - `docs/ARCHITECTURE.md`: Updated architecture documentation
  - `docs/API.md`: API reference documentation
  - `docs/DESIGN-phase7.md`: Phase 7 design document

### Fixed
- Docker test stage configuration and CMD simplification
- Cleaned up AsyncMock garbage files from project root

### Changed
- Updated `pyproject.toml` to v0.7.0
- Updated `plugin.yaml` with hooks metadata
- Updated `README.md` with latest features
- Updated `.dockerignore` for production builds
- Enhanced `__init__.py` with plugin lifecycle hooks
- Enhanced `agent_client/client.py` with reconnection support
- Enhanced `coordinator/storage/agents.py` and `motions.py` storage layer

## v0.6.0 (2026-06-07)

### Added
- **Phase 6 Discussion Quality and Efficiency Enhancement**: Comprehensive quality guard and efficiency improvements
  - `coordinator/quality_guard.py`: Discussion quality monitoring and enforcement
  - `coordinator/quality_guard_models.py`: Data models for quality tracking
  - `coordinator/quality_guard_checks.py`: Quality check implementations
  - `coordinator/quality_scorer.py`: Discussion scoring engine
  - `coordinator/realtime_evaluator.py`: Real-time discussion evaluation
  - `coordinator/consensus_jump.py`: Accelerated consensus detection
  - `coordinator/dynamic_rounds.py`: Adaptive round management
  - `coordinator/model_capabilities.py`: Model capability tracking
  - `coordinator/role_assigner.py`: Dynamic role assignment
  - `coordinator/perspective_ensurer.py`: Perspective diversity enforcement

- **Tests**: 9 new test suites for Phase 6 modules
- **Configuration**: Updated config.py and models.py for new features
- **Documentation**: DESIGN-quality-efficiency.md

### Changed
- Improved assessment.py with quality-aware discussion evaluation
- Enhanced devils_advocate.py with perspective diversity
- Optimized smart_scheduler.py for dynamic round management

## v0.5.0 (2026-06-07)

### Added
- **Phase 5 Fault Tolerance and Security**: Comprehensive system resilience and input protection
  - `coordinator/heartbeat.py`: Agent connection monitoring (PING/PONG)
  - `coordinator/timeout.py`: Discussion timeout handling
  - `coordinator/deadlock_prevention.py`: Circular dependency detection
  - `coordinator/input_validation.py`: Input sanitization and rate limiting

- **Integration**: HeartbeatManager and TimeoutManager startup in coordinator/main.py
- **Configuration**: TimeoutConfig added to coordinator/config.py
- **WebSocket**: Deadlock detection hooks in ws_handlers.py, input validation in ws_endpoint.py

### Changed
- Fixed 24 `datetime.utcnow()` to `datetime.now(timezone.utc)` - resolved DeprecationWarning in Python 3.12+
- Added complete docstrings to 16 functions

### Tests
- Test coverage: 77% → 81%
- All 391 tests passing

---

## v0.4.1 (2026-06-07)

### Added
- **Phase 5 Code Quality Improvements**: Comprehensive code cleanup and test coverage enhancements

### Fixed
- Fixed 24 `datetime.utcnow()` to `datetime.now(timezone.utc)` - resolved DeprecationWarning in Python 3.12+

### Changed
- Added complete docstrings to 16 functions in:
  - `ws_endpoint/` - WebSocket endpoint handlers
  - `ws_handlers/` - WebSocket message handlers  
  - `ws_vote/` - Voting logic handlers
  - `ws_smart/` - Smart discussion handlers

### Tests
- Added 15 new test cases across 3 files
- Test coverage: 77% → 81%
- All 334 tests passing

---

## v0.4.0 (2026-06-07)

### Added
- **Phase 4 Bootstrap - Self-Organizing Development Engine**: New system for AI-driven project development
  - `coordinator/bootstrap/__init__.py`: Bootstrap engine initialization
  - `coordinator/bootstrap/trigger_types.py`: Trigger type definitions (schedule, event, manual)
  - `coordinator/bootstrap/trigger_manager.py`: Trigger management and execution
  - `coordinator/bootstrap/schedule_checker.py`: Schedule-based trigger detection
  - `coordinator/bootstrap/discussion_driver.py`: Trigger discussions from development needs
  - `coordinator/bootstrap/task_generator.py`: Generate tasks from discussion conclusions
  - `coordinator/bootstrap/approval_flow.py`: User approval workflow
  - `coordinator/bootstrap/routes.py`: Bootstrap API routes
  - `coordinator/bootstrap/routes_extra.py`: Extended bootstrap routes
  - `coordinator/bootstrap/bootstrap_schema.py`: Bootstrap data models
  - `coordinator/storage/bootstrap.py`: Bootstrap storage layer
  - `coordinator/storage/bootstrap_approval.py`: Approval storage layer

- **New Tests**: Comprehensive test coverage for Phase 4 features
  - `tests/test_trigger_manager.py`
  - `tests/test_bootstrap_schema.py`
  - `tests/test_discussion_driver.py`
  - `tests/test_task_generator.py`
  - `tests/test_approval_flow.py`
  - `tests/test_bootstrap_engine.py`

- **Documentation**
  - `docs/DESIGN-bootstrap.md`: Bootstrapping system design

### Changed
- Updated `coordinator/main.py` - integrated BootstrapEngine
- Updated `coordinator/storage/schema.py` - SCHEMA_VERSION 3→4, new bootstrap tables
- Updated `coordinator/storage/storage.py` - new bootstrap CRUD methods
- Updated `docs/ROADMAP.md` - Phase 4 marked complete

---

## v0.3.0 (2026-06-06)

### Added
- **Memory and Evolution System**: New memory synchronization and agent evolution
  - `coordinator/memory_sync.py`: Memory synchronization across sessions
  - `coordinator/history_pattern.py`: Historical pattern detection and analysis
  - `coordinator/judgment_tracker.py`: Track and analyze agent judgments
  - `coordinator/judgment_types.py`: Type definitions for judgments
  - `coordinator/conclusion_types.py`: Type definitions for conclusions
  - `coordinator/similar_topic.py`: Similar topic detection
  - `coordinator/curator.py`: Agent evolution and self-improvement
  - `coordinator/storage/judgments.py`: Storage for judgment data

- **New Tests**: Comprehensive test coverage for Phase 3 features
  - `tests/test_memory_sync.py`
  - `tests/test_memory_sync_helpers.py`
  - `tests/test_memory_sync_sync.py`
  - `tests/test_history_pattern.py`
  - `tests/test_history_pattern_strategy.py`
  - `tests/test_judgment_accuracy.py`
  - `tests/test_judgment_leaderboard.py`
  - `tests/test_judgment_tracker.py`
  - `tests/test_similar_topic.py`
  - `tests/test_curator.py`

- **Documentation**: Design documents for Phase 3
  - `docs/DESIGN-memory-evolution.md`: Memory and evolution system design

### Changed
- Updated `coordinator/router.py` - new memory/evolution endpoints
- Updated `coordinator/storage/schema.py` - new judgment tables
- Updated `coordinator/storage/storage.py` - new judgment storage
- Updated `coordinator/ws_vote.py` - voting enhancements
- Updated `tests/conftest.py` - new test fixtures
- Updated `uv.lock` - dependency updates
- Updated `docs/ROADMAP.md` - Phase 3 marked complete

---

## v0.2.0 (2025-06-06)

### Added
- **Smart Discussion**: New discussion management system with smart scheduling
  - `coordinator/assessment.py`: Agent assessment capabilities
  - `coordinator/devils_advocate.py`: Devil's advocate role for discussion
  - `coordinator/focus.py`: Focus management during discussions
  - `coordinator/smart_scheduler.py`: Intelligent discussion scheduling
  - `coordinator/ws_smart.py`: WebSocket endpoint for smart discussion
  - `coordinator/storage/assessments.py`: Storage for discussion assessments

- **Advanced Voting System**: Multiple voting algorithms
  - `coordinator/voting/` (full directory):
    - `approval_voting.py`: Approval voting implementation
    - `multiple_choice.py`: Multiple choice voting
    - `range_voting.py`: Range/score voting
    - `ranked_choice.py`: Ranked choice voting (instant-runoff)
    - `weighted.py`: Weighted voting with weight management
    - `factory.py`: Voting method factory
    - `manager.py`: Voting session management
    - ` weight_manager.py`: Weight calculation for votes
    - `weighted_types.py`: Type definitions for weighted voting

- **New Tests**: Comprehensive test coverage for Phase 2 features
  - `tests/test_assessment.py`
  - `tests/test_devils_advocate.py`
  - `tests/test_focus.py`
  - `tests/test_smart_scheduler.py`
  - `tests/test_vote_factory.py`
  - `tests/test_voting_approval.py`
  - `tests/test_voting_manager.py`
  - `tests/test_voting_multiple_choice.py`
  - `tests/test_voting_range.py`
  - `tests/test_voting_ranked_choice.py`
  - `tests/test_voting_weighted.py`
  - `tests/test_weight_manager.py`

- **Documentation**: Design documents for Phase 2
  - `docs/DESIGN-advanced-voting.md`: Advanced voting system design
  - `docs/DESIGN-smart-discussion.md`: Smart discussion system design
  - `docs/INSPECTION-LOG.md`: Development inspection log

### Changed
- Updated `docs/ROADMAP.md` - Phase 2 marked complete
- Updated `coordinator/models.py`, `coordinator/router.py`, `coordinator/state.py`
- Updated `coordinator/config.py`, `coordinator/ws_endpoint.py`, `coordinator/ws_handlers.py`, `coordinator/ws_vote.py`
- Updated storage: `coordinator/storage/schema.py`, `coordinator/storage/storage.py`, `coordinator/storage/votes.py`

---

## v0.1.0 (2025-06-01)

### Added
- Initial release of Hermes Agora - Multi-Agent Deliberation Framework
- Core discussion and voting infrastructure
- WebSocket-based real-time communication
- SQLite persistence layer
- Agent client for connecting external agents