# Phase 13 Architecture: Multi-tenant Production Deployment

> See also: [DESIGN-phase13.md](DESIGN-phase13.md) Part E

## Deployment Architecture

```
                    ┌──────────────────────┐
                    │  Reverse Proxy       │
                    │  (nginx / Caddy)     │
                    │  TLS termination     │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  Agora Coordinator   │
                    │  (single instance)   │
                    │  Port 8000           │
                    │  ┌────────────────┐  │
                    │  │ global.db      │  │ ← tenant list
                    │  │ /data/tenants/ │  │ ← per-tenant SQLite
                    │  │   {id}/agora.db│  │
                    │  └────────────────┘  │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  Hermes Bridge       │
                    │  (optional)          │
                    │  translates kanban   │
                    │  ↔ Agora WS         │
                    └──────────────────────┘
```

## Docker Compose Production Template

`docker-compose.prod.yaml` provides:
- **coordinator**: `ghcr.io/yzy806806/agora-coordinator:v0.13.0`
  - Health check: `curl -f http://localhost:8000/api/v1/health` (30s interval)
  - Resource limits: 512M memory, 1 CPU
  - Volumes: `agora_data:/data`, read-only config.yaml
  - Required env: `AGORA_RBAC_ENFORCE=true`, `AGORA_REQUIRE_APPROVAL=true`
- **hermes-bridge**: optional, depends on healthy coordinator
  - Profiles to register via `HERMES_PROFILES` env var

## Multi-tenant Configuration

```yaml
# config.yaml — production
coordinator:
  host: "0.0.0.0"
  port: 8000
  db_path: "/data/agora.db"
  tenants_dir: "/data/tenants"
  require_approval: true

rbac:
  enforce: true
  jwt_secret: "${AGORA_JWT_SECRET}"
  token_expiry_hours: 24

tenants:
  default:
    max_agents: 20
    max_concurrent_discussions: 5
    max_tasks_per_agent: 5
```

## Health Check Endpoint

```
GET /api/v1/health
→ {status, version, uptime_seconds, agents_connected, tenants, db_size_mb}
```

## Scaling Considerations

- **Current**: Single-instance with SQLite (sufficient for ~50 agents)
- **Future (Phase 14+)**: Postgres migration for HA, horizontal scaling with message queue
- **Kubernetes**: Overkill at this stage; Docker Compose sufficient

## New Files

```
docker-compose.prod.yaml          # Production deployment template
docs/DEPLOYMENT.md                # Deployment guide (~300 lines)
agora/coordinator/health.py       # Health check endpoint (~40 lines)
```
