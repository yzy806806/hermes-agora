# Phase 13: Pipeline API

> 版本: v0.13.0 | 基础路径: `/api/v1`

## POST /pipelines

启动新的 Pipeline 运行（全自动化开发循环）。

**请求体**:
```json
{
  "idea": "实现用户认证模块",
  "project_id": "agora-project",
  "auto_review": true,
  "auto_release": false
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `idea` | string | 是 | 用户想法/需求描述 |
| `project_id` | string | 是 | 项目 ID |
| `auto_review` | bool | 否 | 自动触发代码审查（默认 true） |
| `auto_release` | bool | 否 | 审查通过后自动发布（默认 false） |

**响应**: `PipelineRun` 对象
```json
{
  "id": "pipe-xxx",
  "project_id": "agora-project",
  "idea": "实现用户认证模块",
  "phase": "discussing",
  "started_at": "2026-06-12T10:00:00Z",
  "completed_at": null,
  "tasks_total": 0,
  "tasks_completed": 0,
  "tasks_failed": 0,
  "review_outcome": null,
  "release_version": null,
  "error": null
}
```

**状态码**:
- `201` — Pipeline 启动成功
- `400` — 参数无效
- `409` — 项目已有运行中的 pipeline

---

## GET /pipelines/{id}

获取 Pipeline 运行状态。

**响应**: `PipelineRun` 对象（同上）

**状态码**:
- `200` — 成功
- `404` — Pipeline 不存在

---

## GET /pipelines

列出 Pipeline 运行。

**查询参数**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `project_id` | string | null | 过滤特定项目 |
| `phase` | string | null | 过滤阶段 |
| `limit` | int | 100 | 返回数量上限 |
| `offset` | int | 0 | 偏移量 |

**响应**:
```json
{
  "pipelines": [...],
  "total": 5,
  "limit": 100,
  "offset": 0
}
```

---

## POST /pipelines/{id}/cancel

取消运行中的 Pipeline。

**响应**: `{\"pipeline_id\": \"pipe-xxx\", \"status\": \"cancelled\"}`

**状态码**:
- `200` — 取消成功
- `404` — Pipeline 不存在
- `409` — Pipeline 已完成，无法取消

---

## POST /pipelines/{id}/retry

重试失败的 Pipeline（从失败阶段重新开始）。

**响应**: `PipelineRun` 对象（phase 重置为失败前的阶段）

**状态码**:
- `200` — 重试启动成功
- `404` — Pipeline 不存在
- `409` — Pipeline 未处于 failed 状态

---

## Pipeline Phase 状态机

```
IDEA_RECEIVED → DISCUSSING → DECOMPOSING → EXECUTING → REVIEWING → RELEASING → COMPLETED
                     ↓              ↓            ↓           ↓            ↓
                   FAILED         FAILED       FAILED      FAILED       FAILED
```

| Phase | 说明 |
|-------|------|
| `discussing` | Bootstrap 引擎运行讨论，达成共识 |
| `decomposing` | 任务生成器创建 TaskGraph |
| `executing` | 并行执行 DAG 中的任务 |
| `reviewing` | 代码审查阶段（可回退至 executing） |
| `releasing` | 发布阶段（git tag + release） |
| `completed` | Pipeline 完成 |
| `failed` | 不可重试的失败 |
