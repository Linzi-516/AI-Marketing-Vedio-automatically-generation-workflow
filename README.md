# AI 自动化广告视频生成工作流

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
┌────────┐   ┌──────────────┐
│Key Feat│   │Script        │
│Extract │   │Generator     │  千问 → 口播脚本 + 分镜
└───┬────┘   └──────┬───────┘
    │               │
    ▼               │
┌────────────┐      │
│Model       │      │
│Generator   │  DALL-E 3 → 人物图片
└───┬────────┘      │
    │               │
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │Video Generator│  即梦AI 3.0 → 多段视频片段
    └───────────────┘
```

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置 API Key
编辑 `config.py`，填入：
- `QWEN_API_KEY`：[阿里云百炼平台](https://bailian.console.aliyun.com/) 获取
- `OPENAI_API_KEY`：[OpenAI Platform](https://platform.openai.com/) 获取
- `JIMENG_API_KEY` / `JIMENG_API_SECRET`：[火山引擎即梦AI](https://console.volcengine.com/cv) 获取

### 3. 修改产品信息
编辑 `main.py` 中的 `PRODUCT_INPUT` 字典：
```python
PRODUCT_INPUT = {
    "product_name": "你的产品名",
    "product_offer": "产品功能/卖点",
    "target_audience": "目标用户描述",
    "pain_points": "核心痛点",
    "total_duration": 30,  # 视频总时长（秒）
}
```

### 4. 运行
```bash
python main.py
```

## 输出结构

```
output/
└── 20260513_120000/        # 本次运行目录（自动以时间命名）
    ├── state.json          # 工作流状态（支持断点续跑）
    ├── model_xxxx.png      # 生成的人物图片
    ├── scene_001_xxxx.mp4  # 第1段视频
    ├── scene_002_xxxx.mp4  # 第2段视频
    └── ...
```

## 断点续跑

工作流每步完成后自动保存 `state.json`。若中途失败，直接在代码中传入 `run_id` 即可从断点继续：

```python
workflow.run(**PRODUCT_INPUT, run_id="20260513_120000")
```

## 节点说明

| 节点 | 文件 | 模型 | 说明 |
|------|------|------|------|
| Story Maker | `nodes/story_maker.py` | 千问 | 生成4模块人物小传 |
| Key Feature Extractor | `nodes/key_feature_extractor.py` | 千问 | 提取可视化人物特征 |
| Model Generator | `nodes/model_generator.py` | DALL-E 3 | 生成写实人物图片 |
| Script Generator | `nodes/script_generator.py` | 千问 | 生成口播脚本+分镜 |
| Video Generator | `nodes/video_generator.py` | 即梦AI 3.0 | 图生视频各分镜片段 |

## 后续扩展规划

- [ ] 图形化界面（Web UI）
- [ ] 多人物/多图片生成与筛选
- [ ] 双人对话/剧情脚本类型
- [ ] 自动视频剪辑拼接（FFmpeg）
- [ ] 指定人物姿势/首尾帧
