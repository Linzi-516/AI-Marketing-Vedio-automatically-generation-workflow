# 配置状态检测规划

## 目标

配置页第一版只做“状态检测”，不做 API Key 明文展示和写入。前端只需要知道每项配置是否已填写、是否仍是占位值、当前会影响哪些能力。

这样做有两个好处：

- 避免把 Key、Secret、Token 暴露给浏览器。
- 用户能在创建任务前知道缺少哪些依赖配置。

## 推荐接口

```http
GET /api/config/status
```

返回示例：

```json
{
  "overall_status": "incomplete",
  "items": [
    {
      "key": "QWEN_API_KEY",
      "label": "千问 API Key",
      "configured": false,
      "required_for": ["story", "feature", "script", "voice"],
      "message": "未配置或仍为占位值"
    },
    {
      "key": "JIMENG_Access_Key_ID",
      "label": "火山引擎 Access Key ID",
      "configured": true,
      "required_for": ["image", "video", "model_card", "tos"],
      "message": "已配置"
    }
  ]
}
```

## 检测规则

后端只判断配置值是否存在、是否明显仍是占位值，不返回原始值。

建议认为以下值是未配置：

- 空字符串
- `None`
- 以 `YOUR_` 开头的占位值
- `your-bucket-name`
- 示例路径，如 `C:\path\to\...`

## 配置项分组

| 分组 | 配置项 | 影响能力 |
|------|--------|----------|
| LLM | `QWEN_API_KEY` | 人物小传、特征提取、脚本生成、音色选择 |
| 即梦/火山视觉 | `JIMENG_Access_Key_ID`, `JIMENG_SECRET_Acess_Key` | 生图、视频、模卡图、TOS 上传 |
| TTS | `TTS_APP_ID`, `TTS_ACCESS_TOKEN` | 语音合成 |
| TOS | `TOS_BUCKET`, `TOS_ENDPOINT`, `TOS_REGION` | Omni 模式音频公网 URL |
| 模卡图 | `MODELCARD_SILHOUETTE_PATHS` | 模卡图生成 |
| 输出 | `OUTPUT_DIR` | 任务产物保存 |

## 前端展示建议

配置页展示成一组状态行：

- 左侧：配置名称和影响能力
- 中间：状态徽标，`已配置` / `未配置` / `需检查`
- 右侧：简短提示，例如“缺少 TTS Token，Omni 视频无法继续”

不要在页面上展示明文 Key。未来如果要支持写入，也建议做成“保存后立即脱敏”的单独接口。

## 后续可实施步骤

1. 后端新增 `GET /api/config/status`。
2. 前端 `ConfigPage` 从该接口读取状态。
3. 新建任务页根据状态做轻量提醒，但第一版不强制拦截。
4. 等内部使用稳定后，再评估是否增加配置写入接口。
