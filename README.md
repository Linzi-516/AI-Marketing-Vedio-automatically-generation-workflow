# AI 自动化广告视频生成工作流

输入产品信息，自动完成：人物小传 → 特征提取 → 人物生图 → 口播脚本 → TTS 配音 → 视频生成 + 模特模卡图生成。

---

## 整体架构

```
产品信息输入
     │
     ▼
┌─────────────────┐
│  Story Maker    │  千问 → 4模块人物小传
└────────┬────────┘
         │
    ┌────┴─────┐  并行执行
    │          │
    ▼          ▼
┌──────────────────────┐  ┌────────────────┐
│  Key Feature         │  │Script Generator│  千问 → 口播脚本 + 分镜
│  Extractor           │  └───────┬────────┘
└────┬─────────────────┘          │
     │                            │
  ┌──┴───────────┐                │
  │  并行执行    │                │
  ▼              ▼                │
┌────────────┐  ┌──────────────┐  │
│   Model    │  │ Voice Type   │  │
│ Generator  │  │  Generator   │  │
│即梦文生图  │  │千问→TTS音色  │  │
│ 3.0 生图   │  └──────┬───────┘  │
└──────┬─────┘         │          │
       └───────┬────────┘         │
               └─────────┬────────┘
                          │
         ┌────────────────┴──────────────────┐
         │                                   │
         ▼（omni 模式：串行）                ▼（并行）
┌────────────────┐                  ┌──────────────────────┐
│  TTS Generator │                  │  Model Card Generator │
│ 火山引擎语音   │                  │  即梦图生图 4.0       │
│  合成 → mp3   │                  │  原图+3张剪影→模卡图  │
└───────┬────────┘                  └──────────────────────┘
        │
        ▼
┌─────────────────────┐
│  OmniHuman Video    │
│    Generator        │
│ 图片URL + 音频URL   │
│  → 有声数字人视频   │
└─────────────────────┘
```

> **omni 模式**（推荐）：TTS 先于视频生成串行执行，生成有声数字人口播视频；模卡图与视频生成并行执行。
>
> **api / cli 模式**：视频生成、模卡图生成、TTS 三路并行，输出哑视频（无声）+ 独立音频。

---

## V4 版本主要更新特性

- **全新 Gradio 图形化界面 (Web UI)**：实现了全功能的图形化控制台。
    - **深色侧边栏导航**：采用专业设计语言，左侧竖向导航栏集成 Logo 区与功能菜单。
    - **五大功能模块**：API 配置（卡片式）、产品信息输入、详细参数配置、引擎运行控制、提示词在线编辑。
    - **可视化交互 Checkpoints**：
        - **生图确认**：实时预览人物图，支持修改提示词重绘。
        - **脚本微调**：内置表格编辑器，可直接修改分镜台词。
        - **首帧分配**：Omni 模式专用，支持为分镜灵活指定图片序号。
    - **实时日志终端**：UI 内部嵌虚拟终端，同步输出后台运行日志，支持运行状态实时刷新。
- **UI 与工作流深度解耦**：通过 `GradioBackend` 类适配 `interactive` 抽象接口，实现同一套逻辑在 CLI 和 Web UI 下的无缝切换。

---

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动图形化界面（推荐）
```bash
python app.py
```
程序启动后会自动在浏览器打开 `http://127.0.0.1:7860`。

### 3. 配置 API Key 及路径
您可以在 Web UI 的 **"⚙️ API 配置"** 页面直接填入并保存配置，或手动编辑 `config.py`：

| 配置项 | 说明 | 获取地址 |
|--------|------|----------|
| `QWEN_API_KEY` | 阿里云千问 API Key | [阿里云百炼平台](https://bailian.console.aliyun.com/) |
| `JIMENG_API_KEY` | 火山引擎 Access Key ID | [火山引擎控制台 IAM](https://console.volcengine.com/iam/keymanage) |
| `JIMENG_API_SECRET` | 火山引擎 Secret Access Key | 同上 |
| `TTS_APP_ID` | 语音合成应用的 APP ID | [语音技术控制台 → 应用管理](https://console.volcengine.com/speech/app) |
| `TTS_ACCESS_TOKEN` | 语音合成应用的 Access Token | 同上（点击应用名称进入详情页获取） |
| `TOS_BUCKET` | 火山引擎 TOS 存储桶名称 | [对象存储 TOS 控制台](https://console.volcengine.com/tos)（需设为公共读） |
| `OUTPUT_DIR` | 本地输出目录（绝对路径） | 自定义 |
| `MODELCARD_SILHOUETTE_PATHS` | 3张灰底姿势剪影图路径列表 | 本地准备 |

**模特模卡图剪影配置示例：**
```python
MODELCARD_SILHOUETTE_PATHS = [
    r"C:\silhouettes\pose_front.png",   # 姿势1（站姿正面）
    r"C:\silhouettes\pose_side.png",    # 姿势2（站姿侧面）
    r"C:\silhouettes\pose_walk.png",    # 姿势3（行走姿势）
]
```

### 3. 选择视频生成引擎

在 `config.py` 中设置 `VIDEO_ENGINE`：

| 值 | 引擎 | 说明 |
|----|------|------|
| `"omni"` | OmniHuman1.5（默认推荐） | 数字人口播，图片+音频→有声视频；需配置 TTS 和 TOS |
| `"api"` | 火山引擎首尾帧 API | 生成哑视频（无声），按量计费，无需登录 |
| `"cli"` | 即梦 CLI 个人账号 | 生成哑视频（无声），消耗个人积分，需提前安装并扫码登录 |

**omni 模式额外前置配置：**
1. 在[语音技术控制台](https://console.volcengine.com/speech/app)创建应用，挂载"大模型语音合成"能力，获取 `TTS_APP_ID` 和 `TTS_ACCESS_TOKEN`。
2. 在[对象存储 TOS 控制台](https://console.volcengine.com/tos)创建存储桶（地域选 `cn-beijing`，设为**公共读**），填入 `TOS_BUCKET`。TOS 的 AK/SK 直接复用 `JIMENG_API_KEY` / `JIMENG_API_SECRET`（同一火山引擎账号）。

**CLI 引擎前置步骤（仅 `cli` 模式需要）：**
```bash
# 1. 安装 dreamina CLI（在 Git Bash 中执行）
curl -s https://jimeng.jianying.com/cli | bash

# 2. 重启终端后，手动运行一次登录（终端会显示二维码，扫码完成授权）
dreamina login

# 3. 登录成功后，再运行工作流，后续无需重复扫码
```

### 4. 填写产品信息

编辑 `main.py` 中的 `PRODUCT_INPUT`：
```python
PRODUCT_INPUT = {
    "product_name": "你的产品名",
    "product_offer": "产品功能/卖点",
    "target_audience": "目标用户描述",
    "pain_points": "核心痛点",
    "total_duration": 30,  # 视频总时长（秒）
}
```

### 5. 运行与续跑
```bash
# 启动全新任务
python main.py

# 启动旧任务
#main.py 中修改run_id="xxxx"
```

---

## 核心文件结构

```text
├── config.py              # 统一的配置中心（API Key、路径、参数脱敏管理）
├── prompts_config.py      # 统一提示词管理模块（V2新增，集中管理所有LLM提示词）
├── interactive.py         # 统一交互确认模块（V2新增，处理CLI与UI人工干预）
├── main.py                # 命令行执行入口
├── app.py                 # 图形界面入口（预留）
├── workflow.py            # 工作流主控制器
└── nodes/                 # 各个执行节点逻辑
    ├── story_maker.py
    ├── key_feature_extractor.py
    ├── script_generator.py
    └── ...
```

---

## 输出结构

```
output/
└── 20260513_120000/              # 本次运行目录（自动以时间命名）
    ├── state.json                # 工作流状态（支持断点续跑）
    ├── model_xxxx.png            # 生成的人物图片（Model Generator 输出）
    ├── modelcard_xxxx_pose1.png  # 模卡图 - 姿势1
    ├── modelcard_xxxx_pose2.png  # 模卡图 - 姿势2
    ├── modelcard_xxxx_pose3.png  # 模卡图 - 姿势3
    ├── audio_001_xxxx.mp3        # 第1段 TTS 音频（omni / api / cli 模式均生成）
    ├── audio_002_xxxx.mp3        # 第2段 TTS 音频
    ├── omni_scene_001_xxxx.mp4   # 第1段有声数字人视频（omni 模式）
    ├── omni_scene_002_xxxx.mp4   # 第2段有声数字人视频（omni 模式）
    └── ...
```

> api / cli 模式下视频文件名为 `scene_001_xxxx.mp4`。

---

## 断点续跑与交互式确认

工作流每步完成后自动保存 `state.json`。中途遇到交互式确认点（如确认脚本、确认图片、补全图片公网URL）或程序报错退出时，可通过传入对应的 `run_id` 恢复进度：

```bash
python main.py -r 20260513_120000
```
或在代码中调用：
```python
workflow.run(**PRODUCT_INPUT, run_id="20260513_120000")
```

各步骤独立判断缓存状态，已完成的步骤自动跳过，节省时间与费用。

> **自动检测失效保护（V2新增）**：若在 Omni 模式下由于网络问题或 `image_url` 为空导致数字人生成失败，系统会自动重置对应的检查点（Checkpoint 3），重新运行后会暂停并提示你手动输入缺失的公网 HTTPS 图片链接，补全后即可直接进入视频生成，无需重头跑。

---

## 节点说明

| 步骤 | 节点 | 文件 | 模型/服务 | 说明 |
|------|------|------|-----------|------|
| Step 1 | Story Maker | `nodes/story_maker.py` | 千问 | 生成4模块人物小传 |
| Step 2 | Key Feature Extractor | `nodes/key_feature_extractor.py` | 千问 | 提取可视化人物特征（英文提示词） |
| Step 2.5 | Voice Type Generator | `nodes/voice_type_generator.py` | 千问 | 根据人物特征+小传智能选择 TTS 音色（与 Step 3 并行） |
| Step 3 | Model Generator | `nodes/model_generator.py` | 即梦AI 文生图 3.0 | 生成写实人物图片，返回本地路径+公网 URL |
| Step 4 | Script Generator | `nodes/script_generator.py` | 千问 | 生成口播脚本+分镜（与图像链路并行） |
| Step 5-C | TTS Generator | `nodes/tts_generator.py` | 火山引擎大模型语音合成 | 按分镜生成 mp3 音频；omni 模式下串行先于视频执行 |
| Step 5-A | Omni Video Generator | `nodes/omni_video_generator.py` | 即梦 OmniHuman1.5 | 图片URL + 音频URL → 有声数字人口播视频（omni 模式） |
| Step 5-A | API Video Generator | `nodes/api_generator.py` | 即梦AI 图生视频 3.0（首尾帧） | 生成哑视频（api 模式） |
| Step 5-A | CLI Video Generator | `nodes/cli_video_generator.py` | dreamina CLI（个人账号） | 生成哑视频（cli 模式） |
| Step 5-B | Model Card Generator | `nodes/model_card_generator.py` | 即梦AI 图片生成 4.0 | 模特原图 + 3张剪影 → 3张姿势模卡图（与视频生成并行） |

---

## 主要配置项速查

```python
# config.py

# ── 视频引擎 ──────────────────────────────────────────────
VIDEO_ENGINE = "omni"          # "omni"（推荐）/ "api" / "cli"

# ── 千问 LLM ──────────────────────────────────────────────
QWEN_API_KEY  = "..."
QWEN_MODEL    = "qwen-plus"    # 可换 qwen-max / qwen-turbo

# ── 即梦 / 火山引擎视觉 API ───────────────────────────────
JIMENG_API_KEY    = "..."      # 火山引擎 Access Key ID
JIMENG_API_SECRET = "..."      # 火山引擎 Secret Access Key

# ── 火山引擎 TTS（大模型语音合成）────────────────────────
TTS_APP_ID       = "..."       # 语音技术控制台应用的 APP ID
TTS_ACCESS_TOKEN = "..."       # 语音技术控制台应用的 Access Token
TTS_CLUSTER      = "volcano_tts"
TTS_DEFAULT_VOICE = "BV700_V2_streaming"  # 灿灿2.0（默认音色）

# ── 火山引擎 TOS（对象存储，omni 模式上传音频用）─────────
TOS_REGION   = "cn-beijing"
TOS_BUCKET   = "your-bucket"   # 需设为公共读
TOS_ENDPOINT = "tos-cn-beijing.volces.com"

# ── OmniHuman1.5 参数（仅 omni 模式）─────────────────────
OMNI_VIDEO_MODEL       = "jimeng_realman_avatar_picture_omni_v15"
OMNI_OUTPUT_RESOLUTION = 1080  # 可选 720 / 1080
OMNI_FAST_MODE         = False

# ── 视频时长限制（api / cli 模式）────────────────────────
SCENE_MIN_DURATION = 5         # 即梦API仅支持 5s / 10s
SCENE_MAX_DURATION = 10

# ── 模卡图剪影路径 ────────────────────────────────────────
MODELCARD_SILHOUETTE_PATHS = [
    r"姿势图1路径",
    r"姿势图2路径",
    r"姿势图3路径",
]

# ── 输出目录 ──────────────────────────────────────────────
OUTPUT_DIR = r"输出目录绝对路径"
```

---

## 后续扩展规划

- [ ] 图形化界面（Web UI）
- [ ] 多人物/多图片生成与筛选
- [ ] 双人对话/剧情脚本类型
- [ ] 自动视频剪辑拼接（FFmpeg）
- [ ] omni 模式支持多图片轮换（不同分镜使用不同人物角度）
- [ ] 支持自定义模特模卡图尺寸与姿势数量
- [ ] 模卡图批量导出（品牌物料包）
