# nodes package
# 视频生成节点：
#   api_generator          → 火山引擎首尾帧 API（需 AK/SK），VIDEO_ENGINE = "api"
#   cli_video_generator    → 即梦 CLI 个人账号（需安装 dreamina 并扫码登录），VIDEO_ENGINE = "cli"
#   omni_video_generator   → OmniHuman1.5 数字人模型（图片URL + TTS音频 → 有声视频），VIDEO_ENGINE = "omni"
# 切换方式：在 config.py 中修改 VIDEO_ENGINE = "api" | "cli" | "omni"
#
# 独立功能节点：
#   key_feature_extractor  → 人物特征提取（小传 → 英文生图提示词）
#   voice_type_generator   → 音色选择（feature_prompt + story → voice_type）
#                            Step 2 完成后立即并行启动（与 model_generator 同步执行）
#                            输出结果在 Step 5 TTS 之前写入 state["voice_type"]
#   model_card_generator   → 模特模卡图生成（模特原图 + 3张剪影 → 3张姿势模卡图）
#   tts_generator          → TTS 音频生成（分镜台词 + 音色代码 → mp3 音频文件）
#                            omni 模式下由 workflow 串行调用；其余模式下并行执行






