# Configuration — Agora Deployment

## Environment Variables

All env vars use the `AGORA_` prefix. Priority: CLI > env > config.yaml > defaults.

| Variable | Default | Description |
|----------|---------|-------------|
| `AGORA_HOST` | `0.0.0.0` | Listen address |
| `AGORA_PORT` | `8765` | Listen port (default 8765; set to 8000 in Docker) |
| `AGORA_DB_PATH` | `~/.agora/data/agora.db` | SQLite database path |
| `AGORA_LOG_LEVEL` | `INFO` | Log level: DEBUG, INFO, WARNING, ERROR |
| `AGORA_REQUIRE_APPROVAL` | `false` | Require admin approval for agent registration |
| `AGORA_RBAC_ENFORCE` | `false` | Enable RBAC permission checks |
| `AGORA_JWT_SECRET` | `""` | Secret for JWT signing (required in prod!) |
| `AGORA_ADMIN_TOKEN` | `""` | Token for admin API access |
| `AGORA_CORS_ORIGINS` | `["*"]` | Allowed CORS origins (JSON list) |
| `AGORA_DASHBOARD_USERS` | `""` | `user:hash,user2:hash2` for dashboard auth |
| `AGORA_HEARTBEAT_INTERVAL_SECONDS` | `30` | Agent heartbeat interval |
| `AGORA_HEARTBEAT_TIMEOUT_SECONDS` | `120` | Agent heartbeat timeout |

## config.yaml Example

```yaml
coordinator:
  host: "0.0.0.0"
  port: 8765
  db_path: "/data/agora.db"
  require_approval: true

rbac:
  enforce: true
  jwt_secret: "${AGORA_JWT_SECRET}"

tenants:
  default:
    max_agents: 20
    max_concurrent_discussions: 5
```

## Tenant Management

### Create a Tenant

```bash
curl -X POST http://localhost:8000/api/v1/tenants \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"acme-corp","name":"Acme Corp",
       "config":{"max_agents":50,"max_concurrent_discussions":10}}'
```

### List Tenants

```bash
curl http://localhost:8000/api/v1/tenants
```

### Tenant Config Options

| Option | Default | Description |
|--------|---------|-------------|
| `max_agents` | 10 | Max concurrent agents |
| `max_concurrent_discussions` | 3 | Max simultaneous discussions |
| `default_voting_method` | `simple_majority` | Voting method |
| `allow_custom_voting_methods` | `true` | Allow per-discussion overrides |
| `quality_threshold` | 0.6 | Discussion quality floor |
| `discussion_timeout_seconds` | 3600 | Auto-close after inactivity |
| `auto_close_inactive_seconds` | 86400 | Auto-close stale discussions |

### Data Isolation

Each tenant gets its own SQLite database under the configured
`AGORA_DB_PATH` directory (`/data/tenants/{tenant_id}/tenant.db`).
The `default` tenant uses the main `agora.db`. Deleting a tenant
soft-deletes its record; the database file is retained for audit.
