"""
Central runtime configuration.

This file intentionally keeps variable names stable because workflow.py,
clients/*, and nodes/* import them directly.
"""

import os

from dotenv import load_dotenv


load_dotenv()


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, defaults: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return defaults
    return [item.strip() for item in value.split(";") if item.strip()]


# ============================================================
# 1. LLM configuration
# ============================================================

QWEN_API_KEY = _env("QWEN_API_KEY", "YOUR_QWEN_API_KEY_HERE")
QWEN_BASE_URL = _env("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = _env("QWEN_MODEL", "qwen-plus")  # qwen-max / qwen-turbo are also valid options.

# Reserved for future non-Qwen providers.
OPENAI_API_KEY = _env("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")


# ============================================================
# 2. Jimeng / Volcengine visual API credentials
# ============================================================

JIMENG_Access_Key_ID = _env("JIMENG_Access_Key_ID", "YOUR_JIMENG_ACCESS_KEY_ID_HERE")
JIMENG_SECRET_Acess_Key = _env("JIMENG_SECRET_Acess_Key", "YOUR_JIMENG_SECRET_ACCESS_KEY_HERE")
JIMENG_BASE_URL = _env("JIMENG_BASE_URL", "https://visual.volcengineapi.com")


# ============================================================
# 3. Jimeng image generation settings
# ============================================================

# Text-to-image 3.0 for model/person generation.
JIMENG_IMAGE_MODEL = _env("JIMENG_IMAGE_MODEL", "high_aes_general_v30l_zt2i")
JIMENG_IMAGE_WIDTH = _env_int("JIMENG_IMAGE_WIDTH", 1024)
JIMENG_IMAGE_HEIGHT = _env_int("JIMENG_IMAGE_HEIGHT", 1024)
JIMENG_IMAGE_SCALE = float(_env("JIMENG_IMAGE_SCALE", "3.5"))
JIMENG_IMAGE_STEPS = _env_int("JIMENG_IMAGE_STEPS", 25)
JIMENG_IMAGE_USE_LLM = _env_bool("JIMENG_IMAGE_USE_LLM", True)
JIMENG_IMAGE_RETURN_URL = _env_bool("JIMENG_IMAGE_RETURN_URL", True)

# Number of generated person images.
IMAGE_COUNT = _env_int("IMAGE_COUNT", 1)


# ============================================================
# 4. Jimeng model-card generation settings
# ============================================================

JIMENG_MODELCARD_MODEL = _env("JIMENG_MODELCARD_MODEL", "jimeng_t2i_v40")
JIMENG_MODELCARD_WIDTH = _env_int("JIMENG_MODELCARD_WIDTH", 1024)
JIMENG_MODELCARD_HEIGHT = _env_int("JIMENG_MODELCARD_HEIGHT", 1024)
JIMENG_MODELCARD_SCALE = float(_env("JIMENG_MODELCARD_SCALE", "4.0"))
JIMENG_MODELCARD_STEPS = _env_int("JIMENG_MODELCARD_STEPS", 30)

# Three local silhouette reference images used by Model Card Generator.
MODELCARD_SILHOUETTE_PATHS = _env_list("MODELCARD_SILHOUETTE_PATHS", [
    r"YOUR_PATH_TO_SILHOUETTE_1",
    r"YOUR_PATH_TO_SILHOUETTE_2",
    r"YOUR_PATH_TO_SILHOUETTE_3",
])


# ============================================================
# 5. Jimeng video generation settings
# ============================================================

JIMENG_VIDEO_MODEL = _env("JIMENG_VIDEO_MODEL", "jimeng_i2v_first_tail_v30_1080")
JIMENG_VIDEO_WIDTH = _env_int("JIMENG_VIDEO_WIDTH", 1920)
JIMENG_VIDEO_HEIGHT = _env_int("JIMENG_VIDEO_HEIGHT", 1080)

# Scene duration constraints. Jimeng video API supports only 5s or 10s.
SCENE_MIN_DURATION = _env_int("SCENE_MIN_DURATION", 5)
SCENE_MAX_DURATION = _env_int("SCENE_MAX_DURATION", 10)


# ============================================================
# 6. OmniHuman video settings
# ============================================================

OMNI_VIDEO_MODEL = _env("OMNI_VIDEO_MODEL", "jimeng_realman_avatar_picture_omni_v15")
OMNI_OUTPUT_RESOLUTION = _env_int("OMNI_OUTPUT_RESOLUTION", 1080)  # 720 / 1080
OMNI_FAST_MODE = _env_bool("OMNI_FAST_MODE", False)


# ============================================================
# 7. TTS settings
# ============================================================

TTS_APP_ID = _env("TTS_APP_ID", "YOUR_TTS_APP_ID_HERE")
TTS_ACCESS_TOKEN = _env("TTS_ACCESS_TOKEN", "YOUR_TTS_ACCESS_TOKEN_HERE")
TTS_CLUSTER = _env("TTS_CLUSTER", "volcano_tts")
TTS_URL = _env("TTS_URL", "https://openspeech.bytedance.com/api/v1/tts")

# Recommended default voice for ad-style short videos.
TTS_DEFAULT_VOICE = _env("TTS_DEFAULT_VOICE", "BV700_V2_streaming")


# ============================================================
# 8. TOS object storage settings for Omni audio upload
# ============================================================

TOS_REGION = _env("TOS_REGION", "cn-beijing")
TOS_BUCKET = _env("TOS_BUCKET", "YOUR_TOS_BUCKET_NAME_HERE")
TOS_ENDPOINT = _env("TOS_ENDPOINT", "tos-cn-beijing.volces.com")

# OmniHuman requires audio URLs reachable from the public internet.
AUDIO_UPLOAD_BASE_URL = f"https://{TOS_BUCKET}.tos-cn-beijing.volces.com"


def audio_uploader(local_path: str) -> str:
    """
    Upload local audio to Volcengine TOS and return a public HTTPS URL.

    TODO: move this behavior into clients/tos_client.py. It remains here for
    compatibility because omni_video_generator currently discovers it from
    config.audio_uploader.
    """
    import os
    import time
    import tos

    client = tos.TosClientV2(
        ak=JIMENG_Access_Key_ID,
        sk=JIMENG_SECRET_Acess_Key,
        endpoint=TOS_ENDPOINT,
        region=TOS_REGION,
    )

    filename = os.path.basename(local_path)
    object_key = f"audio/{int(time.time())}_{filename}"

    with open(local_path, "rb") as f:
        client.put_object(bucket=TOS_BUCKET, key=object_key, content=f)

    return f"https://{TOS_BUCKET}.{TOS_ENDPOINT}/{object_key}"


# ============================================================
# 9. Local CLI video engine settings
# ============================================================

CLI_DREAMINA_PATH = _env("CLI_DREAMINA_PATH", "dreamina")
CLI_VIDEO_TIMEOUT = _env_int("CLI_VIDEO_TIMEOUT", 600)


# ============================================================
# 10. Workflow runtime settings
# ============================================================

# "omni": image + TTS audio -> voiced digital-human video.
# "api": Jimeng first/tail-frame API -> silent video + separate TTS audio.
# "cli": local dreamina CLI -> silent video + separate TTS audio.
VIDEO_ENGINE = _env("VIDEO_ENGINE", "omni")

OUTPUT_DIR = _env("OUTPUT_DIR", "YOUR_OUTPUT_DIRECTORY_PATH_HERE")
