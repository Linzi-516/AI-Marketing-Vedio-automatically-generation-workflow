"""
配置文件 - 所有 API Key 和参数在此统一管理
"""

# ============================================================
# API Keys（填入你的真实 Key）
# ============================================================
QWEN_API_KEY = "your_qwen_api_key_here"
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-plus"  # 可换 qwen-max / qwen-turbo

OPENAI_API_KEY = "your_openai_api_key_here"

JIMENG_API_KEY = "your_jimeng_api_key_here"     # 即梦AI / 火山引擎 API Key
JIMENG_API_SECRET = "your_jimeng_api_secret_here"  # 即梦AI / 火山引擎 API Secret

# ============================================================
# 即梦 / 火山引擎视觉 API 配置
# ============================================================
JIMENG_BASE_URL = "https://visual.volcengineapi.com"

# 智能绘图（文生图 3.0）参数
JIMENG_IMAGE_MODEL = "high_aes_general_v30l"  # 即梦 文生图 3.0（标准版）
JIMENG_IMAGE_WIDTH = 1024
JIMENG_IMAGE_HEIGHT = 1024
JIMENG_IMAGE_SCALE = 3.5      # CFG 引导强度（建议 2.5~5）
JIMENG_IMAGE_STEPS = 25       # 推理步数
JIMENG_IMAGE_USE_LLM = True   # 是否启用大模型优化 Prompt
JIMENG_IMAGE_RETURN_URL = True  # True=返回URL，False=返回Base64

# 视频生成参数
JIMENG_VIDEO_MODEL = "high_aes_general_v30l_zt2i"   # 视频生成3.0 1080P

# 视频生成参数
JIMENG_VIDEO_WIDTH = 1920
JIMENG_VIDEO_HEIGHT = 1080

# ============================================================
# 工作流参数
# ============================================================
# 每段分镜时长范围（秒），由即梦API限制决定
SCENE_MIN_DURATION = 5
SCENE_MAX_DURATION = 15

# 生成图片数量（MVP：1张）
IMAGE_COUNT = 1

# 输出目录
OUTPUT_DIR = "output"
