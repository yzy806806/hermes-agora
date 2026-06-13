# Scaling — Agora Deployment

## 7. Single-Instance Limits

The coordinator is designed for **single-instance** deployment with SQLite.
Practical limits for a single coordinator:

| Dimension | Limit | Notes |
|-----------|-------|-------|
| Concurrent agents | ~50 | WS connection overhead; increase RAM |
| Active discussions | ~20 | Depends on round complexity |
| Tasks in DAG | ~200 | Memory-bound; verify with load test |
| Database size | ~10 GB | SQLite handles this; backup gets slow |
| API throughput | ~1000 req/s | FastAPI + uvicorn on 1 CPU |

## File Descriptors

Each WebSocket connection uses one file descriptor. On Linux, the default
limit (1024) may be insufficient for 50+ agents. Raise it:

```bash
# Temporary (current session)
ulimit -n 65535

# Permanent — add to /etc/security/limits.conf
* soft nofile 65535
* hard nofile 65535
```

For Docker, add to `docker-compose.prod.yaml`:

```yaml
services:
  coordinator:
    ulimits:
      nofile:
        soft: 65535
        hard: 65535
```

## Future: Postgres Migration

SQLite limits the coordinator to a single process. For high-availability
or horizontal scaling, a future phase will migrate to PostgreSQL:

- **Phase 14+**: Postgres backend with asyncpg driver
- **Architecture**: N coordinators behind a load balancer, shared Postgres
- **Migration path**: `db_path` → `database_url` in config.yaml
- **Current workaround**: If you need HA now, run one coordinator and use
  a reverse proxy health check to failover to a standby (cold standby
  with shared volume).

## Horizontal Scaling (Not Yet Supported)

Multi-coordinator deployment requires:
1. Shared database (Postgres)
2. Message bus for WS fan-out (Redis Pub/Sub or NATS)
3. Sticky sessions for WS connections

These are **not implemented** in Phase 13. Do not run multiple coordinator
instances against the same SQLite database — it will corrupt data.
