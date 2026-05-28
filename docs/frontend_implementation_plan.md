# 前端实现规划

## 1. 技术栈建议

第一版前端定位为内部工具，建议采用：

- React
- Vite
- TypeScript
- 原生 CSS / CSS Modules
- `@dnd-kit/core` 用于首帧拖拽

不建议第一版引入复杂状态管理库。任务状态、Checkpoint、产物数据可通过 hooks 和局部 state 管理。

## 2. 文件大小与复杂度约束

为了避免前端代码过重，必须遵守：

- 页面文件只负责布局、路由级数据调度和组件组合。
- 复杂交互放入组件。
- 轮询、Checkpoint、Artifacts 等数据逻辑放入 hooks。
- API 请求单独封装。
- 类型定义单独维护。

建议文件大小目标：

| 类型 | 建议行数 |
|---|---|
| 页面文件 | 150-300 行 |
| 普通组件 | 80-200 行 |
| 复杂组件 | 300-400 行以内 |
| API client | 100-200 行 |
| 类型文件 | 可集中维护，但不混入页面 |

重点防止以下文件膨胀：

- `RunDetailPage.tsx`
- `SceneImageAssignSection.tsx`
- `ScriptCheckpointSection.tsx`

如果组件超过 400 行，应继续拆分子组件。

## 3. 推荐目录结构

```text
frontend/
├── package.json
├── index.html
├── vite.config.ts
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── api/
    │   └── workflowApi.ts
    ├── hooks/
    │   ├── useRunPolling.ts
    │   ├── useCheckpoint.ts
    │   └── useArtifacts.ts
    ├── pages/
    │   ├── ConfigPage.tsx
    │   ├── CreateRunPage.tsx
    │   ├── RunListPage.tsx
    │   └── RunDetailPage.tsx
    ├── components/
    │   ├── layout/
    │   │   ├── AppShell.tsx
    │   │   ├── Sidebar.tsx
    │   │   └── PageHeader.tsx
    │   ├── common/
    │   │   ├── Button.tsx
    │   │   ├── StatusBadge.tsx
    │   │   ├── SectionCard.tsx
    │   │   └── EmptyState.tsx
    │   └── run-detail/
    │       ├── RunSummary.tsx
    │       ├── StepStatusBar.tsx
    │       ├── ProductInputSection.tsx
    │       ├── StorySection.tsx
    │       ├── FeatureVoiceSection.tsx
    │       ├── ImageCheckpointSection.tsx
    │       ├── ScriptCheckpointSection.tsx
    │       ├── AudioSection.tsx
    │       ├── SceneImageAssignSection.tsx
    │       └── ArtifactSection.tsx
    ├── types/
    │   └── workflow.ts
    └── styles/
        ├── global.css
        └── tokens.css
```

## 4. 页面职责

### 4.1 `ConfigPage`

职责：

- 调用 `GET /api/config`。
- 展示只读配置。
- 不提供 API Key 写入。
- 不展示任何敏感字段。

### 4.2 `CreateRunPage`

职责：

- 渲染新建任务表单。
- 调用 `POST /api/runs`。
- 创建成功后跳转到 `RunDetailPage`。

表单字段：

- 产品名称
- 产品功能 / Offer
- 目标受众
- 核心痛点
- 视频总时长
- 可选 run_id

### 4.3 `RunListPage`

职责：

- 第一版可展示本地最近任务。
- 后续如后端新增 `GET /api/runs`，再切换为服务端任务列表。

### 4.4 `RunDetailPage`

职责：

- 读取 `run_id`。
- 使用 hooks 获取 run 状态、checkpoint、artifacts。
- 渲染顶部摘要、步骤状态条和 8 个步骤区块。
- 不直接写复杂编辑、拖拽、音频播放器逻辑。

`RunDetailPage` 不应直接包含：

- 脚本表格编辑细节。
- 图片拖拽细节。
- 音频播放器列表细节。
- 产物卡片渲染细节。

## 5. API Client 设计

文件：

```text
frontend/src/api/workflowApi.ts
```

导出函数：

```ts
getConfig(): Promise<RuntimeConfig>
createRun(input: CreateRunInput): Promise<CreateRunResponse>
getRun(runId: string): Promise<RunStatus>
getCheckpoint(runId: string): Promise<Checkpoint | null>
submitCheckpoint(runId: string, payload: CheckpointSubmit): Promise<{ run_id: string; status: string }>
getArtifacts(runId: string): Promise<ArtifactsResponse>
```

API base URL：

- 第一版使用相对路径 `/api`。
- 如前后端分离部署，可通过 `VITE_API_BASE_URL` 配置。

## 6. Hooks 设计

### 6.1 `useRunPolling`

职责：

- 根据 run_id 调用 `getRun`。
- 根据任务状态控制轮询。

轮询策略：

- `queued` / `running`：每 2-5 秒轮询。
- `waiting_user`：停止自动轮询，等待用户操作。
- `completed` / `failed`：停止轮询。

返回：

```ts
{
  run,
  loading,
  error,
  refresh,
}
```

### 6.2 `useCheckpoint`

职责：

- 当 run 状态为 `waiting_user` 时读取 checkpoint。
- 提供 `submit` 方法。
- 提交成功后触发 run 状态刷新。

### 6.3 `useArtifacts`

职责：

- 调用 `GET /api/runs/{run_id}/artifacts`。
- 在 run 状态变化或用户手动刷新时更新产物。

## 7. 任务详情组件拆分

### 7.1 `RunSummary`

展示：

- 产品名称
- run_id
- 当前状态
- 当前步骤
- 刷新按钮
- 复制 run_id

### 7.2 `StepStatusBar`

展示步骤：

```text
产品输入 → 人物小传 → 人物图片 → 脚本 → 音频 → 首帧 → 视频 → 完成
```

根据 run 状态和 artifacts/state 推导每一步颜色。

### 7.3 `ImageCheckpointSection`

展示：

- 图片缩略图
- 图片路径
- 图片 URL 状态
- 当前 prompt

等待确认时显示：

- 满意继续
- 修改 prompt 重绘

提交：

- `image_confirm`

### 7.4 `ScriptCheckpointSection`

展示：

- 完整脚本 textarea
- 分镜表格

等待确认时允许编辑：

- `full_script`
- 每个 scene 的 `script`

提交：

- `script_confirm`

拆分建议：

- 如果表格编辑逻辑变复杂，拆出 `SceneScriptTable.tsx`。

### 7.5 `SceneImageAssignSection`

展示：

- 人物图片池
- 分镜卡片列表
- 当前首帧绑定关系

交互：

- 拖拽图片到分镜卡片。
- 下拉选择图片作为兜底。
- “全部使用这张图”。
- 手动填写公网 URL。

提交：

- `scene_image_select`

拆分建议：

- `ImagePool.tsx`
- `SceneImageDropCard.tsx`
- `ManualImageUrlInput.tsx`

### 7.6 `ArtifactSection`

展示：

- 视频播放器列表
- 模卡图画廊
- 文件路径复制
- 失败信息

## 8. 类型设计

文件：

```text
frontend/src/types/workflow.ts
```

核心类型：

```ts
type RunStatusValue = 'queued' | 'running' | 'waiting_user' | 'completed' | 'failed'

type CheckpointType = 'image_confirm' | 'script_confirm' | 'scene_image_select'

interface RunStatus {
  run_id: string
  status: RunStatusValue
  current_step: string | null
  pending_checkpoint: CheckpointType | null
  progress: {
    completed_steps: string[]
    total_scenes: number
  }
  error: string | null
}
```

第一版类型应贴合后端当前 API，不额外发明复杂前端状态模型。

## 9. 实现顺序

建议按以下顺序实现：

1. 搭建 Vite + React + TypeScript 项目。
2. 建立全局布局：`AppShell`、`Sidebar`、`PageHeader`。
3. 实现 `workflowApi.ts` 和基础类型。
4. 实现配置状态页。
5. 实现新建任务页。
6. 实现任务详情页基础轮询。
7. 实现图片确认 Checkpoint。
8. 实现脚本确认 Checkpoint。
9. 实现首帧分配 Checkpoint。
10. 实现产物预览。

## 10. 暂不实现

第一版暂不实现：

- 登录权限。
- API Key 写入。
- WebSocket。
- 多用户任务隔离。
- 云端文件管理。
- 复杂任务搜索筛选。
- 节点级重跑按钮。

