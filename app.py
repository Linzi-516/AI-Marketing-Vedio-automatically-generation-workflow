"""
AI 广告视频生成工作流 - 图形界面（待重新设计）
运行方式：python app.py

当前状态：前端 UI 已清空，等待重新设计。
后端逻辑请直接运行 main.py 或调用 workflow.run()。
"""

import os
import sys

# 禁用本地地址的代理
os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"
os.environ["no_proxy"] = "localhost,127.0.0.1,::1"

import config
import prompts_config


# ══════════════════════════════════════════════════════════════
#  后端辅助函数（前端重新设计时复用）
#  这些函数将运行时配置写入 config / prompts_config 模块，
#  供前端控件的回调函数调用。
# ══════════════════════════════════════════════════════════════

def apply_api_config(
    qwen_key: str,
    qwen_url: str,
    qwen_model: str,
    jimeng_key: str,
    jimeng_secret: str,
    tts_app_id: str,
    tts_token: str,
    tts_cluster: str,
    tos_region: str,
    tos_bucket: str,
    tos_endpoint: str,
    output_dir: str,
) -> str:
    """将 API 配置写入 config 模块（本次运行生效）。返回操作状态文本。"""
    config.QWEN_API_KEY      = qwen_key.strip()
    config.QWEN_BASE_URL     = qwen_url.strip()
    config.QWEN_MODEL        = qwen_model.strip()
    config.JIMENG_API_KEY    = jimeng_key.strip()
    config.JIMENG_API_SECRET = jimeng_secret.strip()
    config.TTS_APP_ID        = tts_app_id.strip()
    config.TTS_ACCESS_TOKEN  = tts_token.strip()
    config.TTS_CLUSTER       = tts_cluster.strip()
    config.TOS_REGION        = tos_region.strip()
    config.TOS_BUCKET        = tos_bucket.strip()
    config.TOS_ENDPOINT      = tos_endpoint.strip()
    config.OUTPUT_DIR        = output_dir.strip()
    return "API 配置已保存（本次运行生效）"


def apply_params(
    scene_min: int,
    scene_max: int,
    image_width: int,
    image_height: int,
    image_scale: float,
    image_steps: int,
    video_width: int,
    video_height: int,
    omni_resolution: int,
    omni_fast: bool,
    image_count: int,
) -> str:
    """将生成参数写入 config 模块（本次运行生效）。返回操作状态文本。"""
    config.SCENE_MIN_DURATION     = int(scene_min)
    config.SCENE_MAX_DURATION     = int(scene_max)
    config.JIMENG_IMAGE_WIDTH     = int(image_width)
    config.JIMENG_IMAGE_HEIGHT    = int(image_height)
    config.JIMENG_IMAGE_SCALE     = float(image_scale)
    config.JIMENG_IMAGE_STEPS     = int(image_steps)
    config.JIMENG_VIDEO_WIDTH     = int(video_width)
    config.JIMENG_VIDEO_HEIGHT    = int(video_height)
    config.OMNI_OUTPUT_RESOLUTION = int(omni_resolution)
    config.OMNI_FAST_MODE         = bool(omni_fast)
    config.IMAGE_COUNT            = int(image_count)
    return "参数已保存（本次运行生效）"


def apply_prompts(
    story_sys: str,
    story_user: str,
    feat_sys: str,
    feat_user: str,
    voice_sys: str,
    voice_user: str,
    script_sys: str,
    script_user: str,
) -> str:
    """将提示词写入 prompts_config 模块及各节点模块（本次运行生效）。返回操作状态文本。"""
    prompts_config.STORY_MAKER_SYSTEM      = story_sys
    prompts_config.STORY_MAKER_USER        = story_user
    prompts_config.KEY_FEATURE_SYSTEM      = feat_sys
    prompts_config.KEY_FEATURE_USER        = feat_user
    prompts_config.VOICE_TYPE_SYSTEM       = voice_sys
    prompts_config.VOICE_TYPE_USER         = voice_user
    prompts_config.SCRIPT_GENERATOR_SYSTEM = script_sys
    prompts_config.SCRIPT_GENERATOR_USER   = script_user

    import nodes.story_maker as sm
    import nodes.key_feature_extractor as kf
    import nodes.voice_type_generator as vt
    import nodes.script_generator as sg
    sm.SYSTEM_PROMPT        = story_sys
    sm.USER_PROMPT_TEMPLATE = story_user
    kf.SYSTEM_PROMPT        = feat_sys
    kf.USER_PROMPT_TEMPLATE = feat_user
    vt.SYSTEM_PROMPT        = voice_sys
    vt.USER_PROMPT_TEMPLATE = voice_user
    sg.SYSTEM_PROMPT        = script_sys
    sg.USER_PROMPT_TEMPLATE = script_user
    return "提示词已更新（本次运行生效）"


def get_current_config() -> dict:
    """返回当前所有配置项的快照，供前端初始化表单时读取。"""
    return {
        # API
        "qwen_key":       config.QWEN_API_KEY,
        "qwen_url":       config.QWEN_BASE_URL,
        "qwen_model":     config.QWEN_MODEL,
        "jimeng_key":     config.JIMENG_API_KEY,
        "jimeng_secret":  config.JIMENG_API_SECRET,
        "tts_app_id":     config.TTS_APP_ID,
        "tts_token":      config.TTS_ACCESS_TOKEN,
        "tts_cluster":    config.TTS_CLUSTER,
        "tos_region":     config.TOS_REGION,
        "tos_bucket":     config.TOS_BUCKET,
        "tos_endpoint":   config.TOS_ENDPOINT,
        "output_dir":     config.OUTPUT_DIR,
        # 参数
        "scene_min":      config.SCENE_MIN_DURATION,
        "scene_max":      config.SCENE_MAX_DURATION,
        "image_width":    config.JIMENG_IMAGE_WIDTH,
        "image_height":   config.JIMENG_IMAGE_HEIGHT,
        "image_scale":    config.JIMENG_IMAGE_SCALE,
        "image_steps":    config.JIMENG_IMAGE_STEPS,
        "video_width":    config.JIMENG_VIDEO_WIDTH,
        "video_height":   config.JIMENG_VIDEO_HEIGHT,
        "omni_resolution":config.OMNI_OUTPUT_RESOLUTION,
        "omni_fast":      config.OMNI_FAST_MODE,
        "image_count":    config.IMAGE_COUNT,
        "video_engine":   config.VIDEO_ENGINE,
        # 提示词
        "story_sys":      prompts_config.STORY_MAKER_SYSTEM,
        "story_user":     prompts_config.STORY_MAKER_USER,
        "feat_sys":       prompts_config.KEY_FEATURE_SYSTEM,
        "feat_user":      prompts_config.KEY_FEATURE_USER,
        "voice_sys":      prompts_config.VOICE_TYPE_SYSTEM,
        "voice_user":     prompts_config.VOICE_TYPE_USER,
        "script_sys":     prompts_config.SCRIPT_GENERATOR_SYSTEM,
        "script_user":    prompts_config.SCRIPT_GENERATOR_USER,
    }


# ══════════════════════════════════════════════════════════════
#  前端入口（待实现）
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("前端 UI 尚未实现，请运行 python main.py 使用命令行交互模式。")
    sys.exit(0)
