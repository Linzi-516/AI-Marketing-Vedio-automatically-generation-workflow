"""
配置文件 - 所有 API Key 和参数在此统一管理
"""

# ============================================================
# API Keys（填入你的真实 Key）
# ============================================================
QWEN_API_KEY = "YOUR_QWEN_API_KEY_HERE"
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-plus"  # 可换 qwen-max / qwen-turbo

OPENAI_API_KEY = "YOUR_OPENAI_API_KEY_HERE"

JIMENG_API_KEY = "YOUR_JIMENG_API_KEY_HERE"     # 即梦AI / 火山引擎 API Key
JIMENG_API_SECRET = "YOUR_JIMENG_API_SECRET_HERE"  # 即梦AI / 火山引擎 API Secret

# ============================================================
# 火山引擎 TTS（语音合成）配置
# 来源：语音技术控制台 → 创建应用 → 语音合成 → 获取 APP_ID / Access Token / ClusterID
# ============================================================
TTS_APP_ID       = "YOUR_TTS_APP_ID_HERE"          # 控制台应用的 APP ID
TTS_ACCESS_TOKEN = "YOUR_TTS_ACCESS_TOKEN_HERE"    # 控制台应用的 Access Token
TTS_CLUSTER      = "volcano_tts"              # 固定值（普通话合成集群）
TTS_URL          = "https://openspeech.bytedance.com/api/v1/tts"

# 默认音色（当 script_generator 未返回 voice_type 时使用）
# ──────────────────────────────────────────────────────────────
# 【广告配音】—— 最贴合 AI 广告视频场景，首选以下音色：
#   BV401_streaming     促销男声（热情促销，电商/活动广告）
#   BV402_streaming     促销女声（亲切促销，电商/活动广告）
#   BV006_streaming     磁性男声（低沉磁性，品牌/高端广告）
#
# 【视频配音】—— 适合旁白、解说、短视频：
#   BV408_streaming     译制片男声（成熟厚重，品牌故事）
#   BV410_streaming     活力解说男（充满活力，快消/运动类）
#   BV411_streaming     影视解说小帅（帅气干练，科技/3C类）
#   BV412_streaming     影视解说小美（甜美活泼，美妆/生活类）
#   BV437_streaming     解说小帅-多情感（支持7种情感，通用解说）
#   BV418_streaming     直播一姐（热情洋溢，直播带货/促销类）
#   BV403_streaming     鸡汤女声（温暖励志，品牌情感类广告）
#   BV428_streaming     清新文艺女声（清新淡雅，生活/文创类）
#   BV142_streaming     沉稳解说男（沉稳大气，金融/政企类）
#   BV056_streaming     阳光男声（阳光开朗，快消/运动类）
#   BV005_streaming     活泼女声（活泼可爱，年轻向/零食类）
#   BV158_streaming     智慧老者（沉稳睿智，健康/养生类）
#   BV157_streaming     慈爱姥姥（温暖慈祥，母婴/家庭类）
#
# 【通用场景】—— 自然亲切，百搭：
#   BV700_V2_streaming  灿灿 2.0（22种情感，综合最强，推荐）
#   BV700_streaming     灿灿（22种情感，支持中英日葡西印尼6语）
#   BV701_V2_streaming  擎苍 2.0（10种情感，男声）
#   BV001_V2_streaming  通用女声 2.0（自然亲切）
#   BV001_streaming     通用女声（12种情感，含广告风格）
#   BV002_streaming     通用男声
#   BV705_streaming     炀炀（自然对话，温暖亲切）
#
# 【有声阅读】—— 适合故事型/情感型广告旁白：
#   BV701_streaming     擎苍（10种情感，旁白沉浸感强）
#   BV123_streaming     阳光青年（7种情感）
#   BV107_streaming     霸气青叔（8种情感）
#   BV104_streaming     温柔淑女（8种情感）
#   BV102_streaming     儒雅青年（8种情感）
#
# 【智能助手】—— 适合产品介绍/客服型广告：
#   BV405_streaming     甜美小源（5种情感/风格，含专业/严肃）
#   BV009_streaming     知性女声（5种情感/风格）
#   BV007_streaming     亲切女声（清晰自然）
#   BV008_streaming     亲切男声（5种情感/风格）
#
# 【新闻播报】—— 适合正式/权威类广告：
#   BV011_streaming     新闻女声
#   BV012_streaming     新闻男声
#
# 【特色/萌系】—— 适合儿童、动漫、IP类广告：
#   BV051_streaming     奶气萌娃
#   BV064_streaming     小萝莉（7种情感）
# ──────────────────────────────────────────────────────────────
TTS_DEFAULT_VOICE = "BV700_V2_streaming"  # 灿灿2.0：22种情感，综合表现最佳，适合广告

# ============================================================
# 即梦 / 火山引擎视觉 API 配置
# ============================================================
JIMENG_BASE_URL = "https://visual.volcengineapi.com"

# 智能绘图（文生图 3.0）参数
JIMENG_IMAGE_MODEL = "high_aes_general_v30l_zt2i"  # 即梦 文生图 3.0（标准版）
JIMENG_IMAGE_WIDTH = 1024
JIMENG_IMAGE_HEIGHT = 1024
JIMENG_IMAGE_SCALE = 3.5      # CFG 引导强度（建议 2.5~5）
JIMENG_IMAGE_STEPS = 25       # 推理步数
JIMENG_IMAGE_USE_LLM = True   # 是否启用大模型优化 Prompt
JIMENG_IMAGE_RETURN_URL = True  # True=返回URL，False=返回Base64

# 模特模卡图生成（图生图，多参考图控制姿势）
JIMENG_MODELCARD_MODEL = "jimeng_t2i_v40"      # 即梦 图片生成 4.0（支持多图输入）
JIMENG_MODELCARD_WIDTH = 1024
JIMENG_MODELCARD_HEIGHT = 1024
JIMENG_MODELCARD_SCALE = 4.0    # CFG 引导强度（越高越贴近提示词，建议 3.5~5）
JIMENG_MODELCARD_STEPS = 30     # 推理步数（图生图可适当多一些）

# 灰底人物姿势参考图（共3张，用于生成模特模卡图）
# 请将3张灰底姿势剪影图的绝对路径填入下方列表
MODELCARD_SILHOUETTE_PATHS = [
    r"C:\path\to\your\正面剪影.png",   # 姿势1（如站姿正面）
    r"C:\path\to\your\侧面剪影.png",   # 姿势2（如站姿侧面）
    r"C:\path\to\your\正面带姿势剪影.png",   # 姿势3（如行走姿势）
]

# 视频生成参数
JIMENG_VIDEO_MODEL = "jimeng_i2v_first_tail_v30_1080"  # 即梦 图生视频3.0 1080P（首尾帧）
JIMENG_VIDEO_WIDTH = 1920
JIMENG_VIDEO_HEIGHT = 1080

# ============================================================
# CLI 引擎配置（仅 VIDEO_ENGINE = "api" 时生效）
# ============================================================
# 本地 dreamina 命令的路径，若已加入系统 PATH 可直接写 "dreamina"
CLI_DREAMINA_PATH = "dreamina"
# 生成单个视频的最大超时时间（秒），默认 600 秒（10分钟）
CLI_VIDEO_TIMEOUT = 600

# ============================================================
# 工作流参数
# ============================================================
# 每段分镜时长范围（秒）
# 即梦API严格限制：只支持 5s（121帧）和 10s（241帧），不允许其他值
SCENE_MIN_DURATION = 5
SCENE_MAX_DURATION = 10

# 视频生成引擎选择：
#   "api"  → 使用火山引擎首尾帧 API（需填写 JIMENG_API_KEY / JIMENG_API_SECRET）
#   "cli"  → 使用本地 dreamina CLI（消耗个人即梦账号积分，需提前安装并扫码登录）
#   "omni" → 使用 OmniHuman1.5 数字人模型（图片+TTS音频 → 有声视频）
#            启用 omni 时，TTS_generator 会自动先于视频生成执行，流程变为：
#            TTS生成 → Omni视频合成（串行），模卡图生成保持并行
VIDEO_ENGINE = "omni"

# ============================================================
# OmniHuman1.5 数字人视频配置（仅 VIDEO_ENGINE = "omni" 时生效）
# ============================================================
OMNI_VIDEO_MODEL       = "jimeng_realman_avatar_picture_omni_v15"  # OmniHuman1.5 req_key
OMNI_OUTPUT_RESOLUTION = 1080    # 输出分辨率，可选 720 / 1080
OMNI_FAST_MODE         = False   # 快速模式（True=降质换速，1080P 建议 False）

# ============================================================
# 火山引擎 TOS（对象存储）配置（omni 模式自动上传音频使用）
# 开通方式：火山引擎控制台 → 对象存储 TOS → 创建桶（选 cn-beijing，公共读）
#   → 获取 Access Key / Secret Key（与 JIMENG 共用同一对 AK/SK 即可）
# ============================================================
TOS_REGION      = "cn-beijing"   # 桶所在地域，与创建时保持一致
TOS_BUCKET      = "your-bucket-name"   # 你创建的桶名称，例如 "my-audio-bucket"
TOS_ENDPOINT    = "tos-cn-beijing.volces.com"   # 地域对应的 Endpoint（cn-beijing 固定此值）
# TOS AK/SK 直接复用 JIMENG 的即可（同一个火山引擎账号）
# TOS_ACCESS_KEY = JIMENG_API_KEY    ← 在下方函数里直接引用，无需重复填写

# 音频上传配置（omni 模式需要将本地 mp3 上传到公网可访问的 URL）
AUDIO_UPLOAD_BASE_URL = f"https://{TOS_BUCKET}.tos-cn-beijing.volces.com"


def audio_uploader(local_path: str) -> str:
    """
    将本地音频文件上传到火山引擎 TOS，返回公网可访问的 HTTPS URL。
    依赖：pip install tos>=2.6.0
    桶需设置为【公共读】，否则链接无法被 Omni 接口访问。
    """
    import os
    import time
    import tos

    client = tos.TosClientV2(
        ak=JIMENG_API_KEY,
        sk=JIMENG_API_SECRET,
        endpoint=TOS_ENDPOINT,
        region=TOS_REGION,
    )

    filename = os.path.basename(local_path)
    object_key = f"audio/{int(time.time())}_{filename}"

    with open(local_path, "rb") as f:
        client.put_object(bucket=TOS_BUCKET, key=object_key, content=f)

    public_url = f"https://{TOS_BUCKET}.{TOS_ENDPOINT}/{object_key}"
    return public_url

# 生成图片数量（1张）
IMAGE_COUNT = 1

# 输出目录
OUTPUT_DIR = r"D:\6031ouput"
