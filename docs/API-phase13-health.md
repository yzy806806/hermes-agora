# Phase 13: Health API

> 版本: v0.13.0 | 基础路径: `/api/v1`

## GET /health

系统健康检查（用于 Docker HEALTHCHECK 和负载均衡器探针）。

**响应**:
```json
{
  "status": "healthy",
  "version": "0.13.0",
  "uptime_seconds": 123456,
  "agents_connected": 5,
  "tenants": 3,
  "db_size_mb": 12.4
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | `healthy` 或 `unhealthy` |
| `version` | string | Coordinator 版本号 |
| `uptime_seconds` | int | 运行时长（秒） |
| `agents_connected` | int | 当前在线 Agent 数 |
| `tenants` | int | 活跃租户数 |
| `db_size_mb` | float | SQLite 数据库大小（MB） |

**状态码**:
- `200` — 系统健康
- `503` — 系统不健康（数据库不可访问等）

**Docker Compose 用法**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```
