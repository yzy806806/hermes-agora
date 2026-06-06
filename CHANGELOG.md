# Changelog

All notable changes to this project will be documented in this file.

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