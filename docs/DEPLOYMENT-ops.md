# Operations — Agora Deployment

## 5. Backup and Restore

### Online SQLite Backup

```bash
# Safe backup while coordinator is running
sqlite3 /data/agora.db ".backup /data/backups/agora-$(date +%Y%m%d).db"
```

### Volume Snapshot (Docker)

```bash
docker run --rm -v agora_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/agora-backup-$(date +%Y%m%d).tar.gz -C /data .
```

### Restore from Backup

```bash
docker compose -f docker-compose.prod.yaml down
docker run --rm -v agora_data:/data -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/agora-backup-20260613.tar.gz"
docker compose -f docker-compose.prod.yaml up -d
```

### Cron Backup Job

```cron
# Note: % must be escaped (\%) in crontab; remove backslashes if running in a shell script
0 3 * * * sqlite3 /data/agora.db ".backup /data/backups/agora-$(date +\%Y\%m\%d).db"
0 4 * * * find /data/backups -name "agora-*.db" -mtime +30 -delete
```

## 6. Monitoring

### Health Check

```
GET /api/v1/health → {"status":"healthy","version":"0.13.0",
  "uptime_seconds":12345,"agents_connected":5,"tenants":3,"db_size_mb":12.4}
```

No auth required — for Docker HEALTHCHECK and load balancers.

### Prometheus Metrics

`GET /metrics` — Prometheus text format. Key metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `agora_agents_connected` | Gauge | Connected agents |
| `agora_agents_registered_total` | Counter | Cumulative registrations |
| `agora_discussions_total` | Counter | Discussions by status |
| `agora_discussion_duration_seconds` | Histogram | Duration by method/outcome |
| `agora_votes_total` | Counter | Votes by method/result |
| `agora_tools_calls_total` | Counter | Tool calls by tool/status |
| `agora_ws_messages_total` | Counter | WS messages by direction/type |
| `agora_coordinator_uptime_seconds` | Gauge | Uptime |
| `agora_db_size_bytes` | Gauge | Database file size |

### Log Aggregation

Set `AGORA_LOG_LEVEL=INFO` (or `DEBUG` for troubleshooting).
Logs go to stdout (structured JSON when `DEBUG`).

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Health 503 | Not initialized | Check logs; wait for startup |
| Agents can't connect | `REQUIRE_APPROVAL=true` | Approve via `/api/v1/agents/approve` |
| WS disconnects | Heartbeat timeout | Increase `AGORA_HEARTBEAT_TIMEOUT_SECONDS` |
| 403 on endpoints | `RBAC_ENFORCE=true` | Check role permissions |
| DB locked | Concurrent writes | Ensure single coordinator instance |
| OOM killed | Memory too low | Increase Docker mem limit to 1G+ |

**Debug**: `AGORA_LOG_LEVEL=DEBUG docker compose -f docker-compose.prod.yaml up`
**Reset**: `docker compose -f docker-compose.prod.yaml down -v` (deletes data)
