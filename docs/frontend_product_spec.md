# 内部工具前端产品规格

## 1. 产品定位与基调

本前端定位为内部 AIGC 工作流控制台，用于创建、监控、确认和查看广告视频生成任务。

设计基调：

- 白灰风格，避免商业化和营销型视觉。
- 信息密度适中，优先保证状态清晰、操作明确。
- 以任务流转为核心，用户始终知道当前任务执行到哪一步、是否需要人工操作。
- 页面采用后台工具布局：左侧导航，右侧内容区。

状态颜色：

| 状态 | 颜色 | 含义 |
|---|---|---|
| 未执行 | 灰色 | 步骤尚未开始 |
| 执行中 | 黄色 | 系统正在生成 |
| 等待确认 | 蓝色 | 需要用户操作 Checkpoint |
| 完成 | 绿色 | 步骤已完成 |
| 失败 | 红色 | 步骤或任务失败 |

颜色使用原则：

- 不使用大面积高饱和色块。
- 优先使用状态标签、左边框、浅色背景、图标提示。
- 失败状态需要展示明确错误信息。

## 2. 全局页面结构

整体布局：

```text
┌───────────────────────────────┐
│ 左侧导航 │ 右侧页面内容        │
│         │                     │
│ 配置状态 │ 当前页面标题        │
│ 新建任务 │ 具体页面内容        │
│ 任务列表 │                     │
│ 任务详情 │                     │
└───────────────────────────────┘
```

左侧导航：

- 配置状态
- 新建任务
- 任务列表
- 任务详情

任务详情页中，左侧导航下方可展示最近任务列表：

- run_id
- 任务状态
- 点击后进入对应任务详情

右侧内容区：

- 背景为浅灰。
- 内容区域使用白色分区。
- 分区边框使用浅灰。
- 不使用营销型 Hero、装饰插画、强渐变。

## 3. 页面规格

### 3.1 配置状态页

用户首次进入工具时默认看到配置状态页。

第一版只做只读展示，不提供 API Key 写入能力。

展示内容：

- 当前视频引擎：`video_engine`
- 当前千问模型：`qwen_model`
- 当前即梦生图模型：`jimeng_image_model`
- 当前 OmniHuman 模型：`omni_video_model`
- 输出目录：`output_dir`
- 分镜最小时长：`scene_min_duration`
- 分镜最大时长：`scene_max_duration`

数据来源：

- `GET /api/config`

配置完整性提示：

- 第一版不展示 API Key 明文。
- 如后端未来提供脱敏配置完整性字段，可显示“已配置 / 未配置”。
- 当前版本只展示非敏感配置。

### 3.2 新建任务页

用于创建新的广告视频生成任务。

表单字段：

- 产品名称 `product_name`
- 产品功能 / Offer `product_offer`
- 目标受众 `target_audience`
- 核心痛点 `pain_points`
- 视频总时长 `total_duration`
- 可选 run_id `run_id`

主要操作：

- 创建任务
- 清空表单

提交接口：

- `POST /api/runs`

提交成功后：

- 跳转到任务详情页。
- 使用返回的 `run_id` 加载任务状态。

### 3.3 任务列表页

用于查看和进入历史任务。

第一版后端暂未提供任务列表接口，因此前端可先用本地最近任务缓存，或后续等待新增接口。

建议展示字段：

- run_id
- 产品名称
- 状态
- 当前步骤
- 最近更新时间
- 操作：打开详情

后续建议新增接口：

- `GET /api/runs`

### 3.4 任务详情页

任务详情页是核心页面。

顶部摘要区展示：

- 产品名称
- run_id
- 任务状态
- 当前步骤
- 视频引擎
- 刷新按钮
- 复制 run_id

数据来源：

- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/artifacts`
- 当 `status=waiting_user` 时调用 `GET /api/runs/{run_id}/checkpoint`

## 4. 任务详情步骤区域

任务详情页按用户理解工作流的方式分为 8 个区域。

### 4.1 产品输入

展示创建任务时输入的信息：

- 产品名称
- 产品功能 / Offer
- 目标受众
- 核心痛点
- 目标时长

第一版只读，不允许在任务详情中修改产品输入。

### 4.2 用户画像 / 人物小传

展示内容：

- `story`

作用：

- 让用户理解后续人物图片、脚本和音色生成的依据。

第一版只读，不设置 Checkpoint。

### 4.3 人物视觉与音色

展示内容：

- `feature_prompt`
- `voice_type`

建议布局：

- 左侧：人物视觉描述
- 右侧：音色代码和说明

第一版只读。

### 4.4 人物图片

对应 Checkpoint：

- `image_confirm`

展示内容：

- 人物图片缩略图
- 图片本地路径
- 图片公网 URL 状态
- 当前生图提示词 `feature_prompt`

等待确认时展示操作：

- 满意，继续
- 修改 prompt 重绘

提交接口：

- `POST /api/runs/{run_id}/checkpoint`

提交示例：

```json
{
  "type": "image_confirm",
  "action": "next"
}
```

重绘示例：

```json
{
  "type": "image_confirm",
  "action": "regenerate",
  "new_prompt": "updated prompt"
}
```

### 4.5 口播脚本与分镜

对应 Checkpoint：

- `script_confirm`

展示内容：

- 完整脚本 `full_script`
- 分镜表格 `scenes`

分镜表格字段：

- scene_id
- duration
- script

等待确认时允许编辑：

- 完整脚本
- 每段分镜台词

提交接口：

- `POST /api/runs/{run_id}/checkpoint`

提交示例：

```json
{
  "type": "script_confirm",
  "full_script": "final script",
  "scenes": []
}
```

### 4.6 TTS 音频

展示内容：

- 每段音频路径
- 每段音频播放器
- 失败音频索引 `tts_failed_indices`

状态：

- 未生成时灰色。
- 生成中黄色。
- 生成完成绿色。
- 部分失败时红色提示失败索引。

### 4.7 首帧分配

仅 Omni 模式需要。

对应 Checkpoint：

- `scene_image_select`

展示内容：

- 左侧：分镜卡片列表
- 右侧：人物图片池
- 每个分镜当前绑定的首帧图片
- 图片公网 URL 状态

核心交互：

- 用户拖拽人物图片到对应分镜卡片。
- 支持“全部使用这张图”。
- 支持每个分镜下拉选择图片。
- 支持手动填写公网 URL。

提交接口：

- `POST /api/runs/{run_id}/checkpoint`

提交示例：

```json
{
  "type": "scene_image_select",
  "scene_image_selections": [
    {
      "scene_id": 1,
      "image_path": "local path",
      "image_url": "https://..."
    }
  ]
}
```

### 4.8 视频与模卡产物

展示内容：

- 视频播放器列表
- 视频文件路径
- 视频 URL
- 模卡图画廊
- 模卡图文件路径
- 失败分镜 `failed_scenes`
- 失败模卡索引 `card_failed_indices`

建议拆成两个子区域：

- 视频结果
- 模卡图结果

第一版至少支持：

- 预览视频
- 预览模卡图
- 复制文件路径

## 5. 状态与交互规则

任务状态来自：

- `GET /api/runs/{run_id}`

状态映射：

| API status | 前端含义 |
|---|---|
| queued | 已创建，等待后台线程启动 |
| running | 系统执行中 |
| waiting_user | 等待用户 Checkpoint 操作 |
| completed | 工作流完成 |
| failed | 工作流失败 |

当任务状态为 `waiting_user`：

1. 前端调用 `GET /api/runs/{run_id}/checkpoint`。
2. 根据 `type` 激活对应步骤区域。
3. 用户提交确认后，调用 `POST /api/runs/{run_id}/checkpoint`。
4. 提交成功后继续轮询任务状态。

轮询建议：

- running：每 2-5 秒轮询一次。
- waiting_user：停止频繁轮询，仅保留手动刷新。
- completed / failed：停止轮询。

## 6. MVP 范围

第一版必须包含：

- 左侧导航 + 右侧内容区。
- 配置状态页。
- 新建任务页。
- 任务详情页。
- 任务状态轮询。
- 三个 Checkpoint 的交互。
- 产物预览。

第一版暂不包含：

- 用户登录与权限。
- API Key 前端写入。
- 多用户隔离。
- WebSocket 实时日志。
- 在线删除任务。
- 云端文件管理。

