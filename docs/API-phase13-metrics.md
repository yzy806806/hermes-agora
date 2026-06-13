# Phase 13: Metrics History API

> 版本: v0.13.0 | 基础路径: `/api/v1`

## GET /metrics/history

获取指标历史数据（用于 Chart.js 可视化）。

**查询参数**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `metric` | string | 必填 | 指标名称 |
| `range` | string | `7d` | 时间范围 |
| `project_id` | string | null | 过滤特定项目 |

**metric 取值**:
| 值 | 说明 | 图表类型 |
|----|------|----------|
| `agent_activity` | Agent 活跃数时间线 | Line |
| `task_throughput` | 任务完成数/天 | Bar |
| `discussion_outcomes` | 讨论结果分布 | Pie |
| `pipeline_success_rate` | Pipeline 成功率 | Gauge |
| `rate_limit_usage` | TPM 使用率/Agent | Line |

**range 取值**: `1h` | `6h` | `1d` | `7d` | `30d`

**响应**:
```json
{
  "metric": "agent_activity",
  "range": "7d",
  "labels": ["06-06", "06-07", "06-08", "06-09", "06-10", "06-11", "06-12"],
  "datasets": [
    {
      "label": "Active Agents",
      "data": [3, 5, 4, 6, 5, 7, 5]
    }
  ]
}
```

**状态码**:
- `200` — 成功
- `400` — metric 参数无效
