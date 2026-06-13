# Phase 13 Architecture: Pipeline Orchestrator (Full-auto Dev Loop)

> See also: [DESIGN-phase13.md](DESIGN-phase13.md) Part A

## Pipeline State Machine

```
IDEA_RECEIVED → DISCUSSING → DECOMPOSING → EXECUTING → REVIEWING → RELEASING → COMPLETED
                     ↓            ↓           ↓          ↓           ↓
                   FAILED       FAILED      FAILED     FAILED      FAILED
                                                       (retryable) (retryable)
```

- **DISCUSSING**: Bootstrap engine runs discussion; consensus required to proceed
- **DECOMPOSING**: Task generator creates TaskGraph; heuristic fallback on LLM failure
- **EXECUTING**: ParallelExecutionCoordinator runs DAG; failed tasks retried
- **REVIEWING**: Review agent inspects changed files; CHANGES_REQUESTED → back to EXECUTING
- **RELEASING**: Releaser agent creates git tag + release; success → COMPLETED
- **FAILED**: Non-retryable failure; pipeline stops and notifies

## PipelineOrchestrator

Conductor pattern — reuses all existing components, no new engine:

```
PipelineOrchestrator
  ├── storage          → Storage (SQLite)
  ├── hub              → ConnectionManager (WS)
  ├── bootstrap        → BootstrapEngine
  ├── parallel         → ParallelExecutionCoordinator
  └── pipelines        → dict[str, PipelineRun] (in-memory tracking)
```

## Data Models

- **PipelinePhase**: Enum (discussing/decomposing/executing/reviewing/releasing/completed/failed)
- **PipelineRun**: id, project_id, idea, motion_id, graph_id, phase, timestamps, task counts, review_outcome, release_version, error
- **ReviewRequest**: pipeline_id, changed_files, task_results, test_results
- **ReviewResult**: pipeline_id, reviewer_id, outcome (approved/changes_requested), issues, summary
- **ReviewIssue**: file, line, severity (critical/major/minor), description
- **PipelineRetryPolicy**: max_retries=3, retry_delay=30s, retryable_phases={executing,reviewing,releasing}

## API Endpoints

```
POST   /api/v1/pipelines                    # Start pipeline run
GET    /api/v1/pipelines/{id}               # Get pipeline status
GET    /api/v1/pipelines?project_id=X       # List pipelines
POST   /api/v1/pipelines/{id}/cancel        # Cancel running pipeline
POST   /api/v1/pipelines/{id}/retry         # Retry failed pipeline
```

## WebSocket Messages

```
PIPELINE_PHASE_CHANGE  → dashboard  # Phase transition
PIPELINE_TASK_UPDATE   → dashboard  # Task status within pipeline
PIPELINE_COMPLETED     → dashboard  # Pipeline finished
PIPELINE_ERROR         → dashboard  # Non-retryable error
```

## New Files

```
agora/coordinator/
├── pipeline.py              # PipelineOrchestrator (~200 lines)
├── pipeline_models.py       # PipelineRun, PipelinePhase (~100 lines)
├── pipeline_review_models.py # ReviewRequest/Result/Issue (~60 lines)
├── pipeline_router.py       # REST API routes (~80 lines)
├── pipeline_review.py       # Code review phase logic (~120 lines)
└── storage/pipelines.py     # PipelineRun CRUD (~100 lines)
```
