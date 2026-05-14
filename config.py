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
OPENAI_IMAGE_MODEL = "dall-e-3"
OPENAI_IMAGE_SIZE = "1024x1024"
OPENAI_IMAGE_QUALITY = "hd"

JIMENG_API_KEY = "your_jimeng_api_key_here"     # 即梦AI API Key
JIMENG_API_SECRET = "your_jimeng_api_secret_here"  # 即梦AI API Secret

# ============================================================
# 即梦 AI 接口配置
# ============================================================
JIMENG_BASE_URL = "https://visual.volcengineapi.com"
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
