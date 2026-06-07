# Changelog

All notable changes to this project will be documented in this file.

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