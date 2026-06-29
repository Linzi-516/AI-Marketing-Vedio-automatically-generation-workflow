"""
节点5-C：TTS Generator（文字转语音）
输入：分镜列表（含 script 台词）+ 音色代码（voice_type）
输出：每段分镜对应的 mp3 音频文件列表

调用接口：火山引擎语音合成 TTS HTTP 接口
  URL: https://openspeech.bytedance.com/api/v1/tts
  认证: Bearer Token（Access Token）
  返回: JSON，data 字段为 base64 编码的音频数据
"""

import os
import time
import json
import base64
import uuid
import requests
import config

# ── 可用音色参考（中文 AI 广告视频场景精选）────────────────────────────────────
# 使用方法：将 voice_type 值传入 run() 的 voice_type 参数，
#          或在 config.py 中修改 TTS_DEFAULT_VOICE。
#
# 格式：{ "voice_type": ("音色名称", "适用场景", "支持情感") }
VOICE_CATALOG = {
    # ── 广告配音（首选）────────────────────────────────────────────────────────
    "BV401_streaming":    ("促销男声",       "电商活动/热情促销",         ""),
    "BV402_streaming":    ("促销女声",       "电商活动/亲切促销",         ""),
    "BV006_streaming":    ("磁性男声",       "品牌/高端广告",             ""),

    # ── 视频配音（旁白/解说/直播）──────────────────────────────────────────────
    "BV408_streaming":    ("译制片男声",     "品牌故事/成熟厚重",         ""),
    "BV410_streaming":    ("活力解说男",     "快消/运动类",               ""),
    "BV411_streaming":    ("影视解说小帅",   "科技/3C类",                 ""),
    "BV412_streaming":    ("影视解说小美",   "美妆/生活类",               ""),
    "BV437_streaming":    ("解说小帅-多情感","通用解说",                  "happy/sad/angry/scare/hate/surprise"),
    "BV418_streaming":    ("直播一姐",       "直播带货/促销",             ""),
    "BV403_streaming":    ("鸡汤女声",       "品牌情感类/励志",           ""),
    "BV428_streaming":    ("清新文艺女声",   "生活/文创类",               ""),
    "BV142_streaming":    ("沉稳解说男",     "金融/政企/权威类",          ""),
    "BV056_streaming":    ("阳光男声",       "快消/运动/阳光向",          ""),
    "BV005_streaming":    ("活泼女声",       "年轻向/零食/潮品类",        ""),
    "BV158_streaming":    ("智慧老者",       "健康/养生/权威类",          ""),
    "BV157_streaming":    ("慈爱姥姥",       "母婴/家庭/温情类",          ""),
    "BV143_streaming":    ("潇洒青年",       "时尚/潮流类",               ""),

    # ── 通用场景（百搭，含多情感）──────────────────────────────────────────────
    "BV700_V2_streaming": ("灿灿 2.0",       "综合最强/广告通用",
                           "pleased/sorry/annoyed/customer_service/professional/serious/"
                           "happy/sad/angry/scare/hate/surprise/tear/conniving/comfort/"
                           "radio/lovey-dovey/tsundere/charming/yoga/storytelling"),
    "BV700_streaming":    ("灿灿",           "多语种广告（中英日葡西印尼）",
                           "同灿灿2.0，支持language=en/ja/ptbr/esmx/id"),
    "BV701_V2_streaming": ("擎苍 2.0",       "男声通用/旁白沉浸",
                           "happy/sad/angry/scare/hate/surprise/tear/novel_dialog/narrator/narrator_immersive"),
    "BV001_V2_streaming": ("通用女声 2.0",   "自然亲切/百搭",             ""),
    "BV001_streaming":    ("通用女声",       "百搭（含广告风格情感）",
                           "customer_service/happy/sad/angry/scare/hate/surprise/comfort/storytelling/advertising/assistant"),
    "BV002_streaming":    ("通用男声",       "百搭男声",                  ""),
    "BV705_streaming":    ("炀炀",           "自然对话/温暖亲切",
                           "chat/pleased/sorry/annoyed/comfort/storytelling"),

    # ── 有声阅读（故事型/情感型广告旁白）──────────────────────────────────────
    "BV701_streaming":    ("擎苍",           "旁白沉浸感/男声情感",
                           "happy/sad/angry/scare/hate/surprise/tear/novel_dialog/narrator/narrator_immersive"),
    "BV123_streaming":    ("阳光青年",       "青春活力旁白",              "happy/sad/angry/scare/hate/surprise/novel_dialog"),
    "BV107_streaming":    ("霸气青叔",       "中年男声旁白",              "happy/sad/angry/scare/hate/surprise/novel_dialog/narrator"),
    "BV104_streaming":    ("温柔淑女",       "温柔女声旁白",              "happy/sad/angry/scare/hate/surprise/novel_dialog/narrator"),
    "BV102_streaming":    ("儒雅青年",       "儒雅男声旁白",              "happy/sad/angry/scare/hate/surprise/novel_dialog/narrator"),
    "BV100_streaming":    ("质朴青年",       "朴实男声旁白",              "happy/sad/angry/scare/hate/surprise/novel_dialog/narrator"),
    "BV113_streaming":    ("甜宠少御",       "甜美女声旁白",              "happy/sad/angry/scare/hate/surprise/novel_dialog/narrator"),
    "BV115_streaming":    ("古风少御",       "古风/国潮类广告",           "happy/sad/angry/scare/hate/surprise/novel_dialog/narrator"),
    "BV119_streaming":    ("通用赘婿",       "剧情/故事型男声",           "happy/sad/angry/scare/hate/surprise/novel_dialog/narrator"),
    "BV120_streaming":    ("反卷青年",       "轻松/佛系向",               "happy/sad/angry/scare/hate/surprise/novel_dialog"),

    # ── 智能助手（产品介绍/客服型广告）────────────────────────────────────────
    "BV405_streaming":    ("甜美小源",       "产品介绍/客服",             "pleased/sorry/professional/serious"),
    "BV009_streaming":    ("知性女声",       "知性/职场/B端",             "pleased/sorry/professional/serious"),
    "BV007_streaming":    ("亲切女声",       "亲切自然/客服",             ""),
    "BV008_streaming":    ("亲切男声",       "亲切/客服",                 "pleased/sorry/professional/serious"),

    # ── 新闻播报（正式/权威广告）───────────────────────────────────────────────
    "BV011_streaming":    ("新闻女声",       "政企/正式类",               ""),
    "BV012_streaming":    ("新闻男声",       "政企/正式类",               ""),

    # ── 特色/萌系（儿童/动漫/IP类）────────────────────────────────────────────
    "BV051_streaming":    ("奶气萌娃",       "母婴/儿童类",               ""),
    "BV064_streaming":    ("小萝莉",         "动漫/IP/儿童类",            "happy/sad/angry/scare/hate/surprise"),
    "BV406_V2_streaming": ("超自然音色-梓梓 2.0", "高品质自然女声",       ""),
    "BV407_V2_streaming": ("超自然音色-燃燃 2.0", "高品质自然男声",       ""),
}


# ── 核心合成函数 ──────────────────────────────────────────────────────────────

def _synthesize(text: str, voice_type: str) -> bytes:
    """
    调用火山引擎 TTS 接口，将文本合成为 mp3 音频，返回音频字节数据。

    Args:
        text:       待合成的台词文本
        voice_type: 音色代码，如 "BV001_V2_streaming"（通用女声）

    Returns:
        音频字节数据（mp3 格式）

    Raises:
        RuntimeError: 接口返回非 3000 状态码
    """
    req_id = str(uuid.uuid4())

    payload = {
        "app": {
            "appid":   config.TTS_APP_ID,
            "token":   "access_token",   # 固定占位值，实际鉴权靠 Header 中的 Bearer Token
            "cluster": config.TTS_CLUSTER,
        },
        "user": {
            "uid": "workflow_user",
        },
        "audio": {
            "voice_type": voice_type,
            "encoding":   "mp3",
            "speed_ratio":  1.0,    # 语速，1.0 为正常速度
            "volume_ratio": 1.0,    # 音量
            "pitch_ratio":  1.0,    # 音调
        },
        "request": {
            "reqid":     req_id,
            "text":      text,
            "text_type": "plain",
            "operation": "query",   # query = 同步合成
        },
    }

    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer;{config.TTS_ACCESS_TOKEN}",
    }

    resp = requests.post(
        config.TTS_URL,
        headers=headers,
        data=json.dumps(payload),
        timeout=30,
    )
    resp.raise_for_status()

    result = resp.json()
    code = result.get("code")
    if code != 3000:
        raise RuntimeError(
            f"TTS 合成失败: code={code} message={result.get('message', '')} "
            f"reqid={result.get('reqid', '')}"
        )

    audio_b64 = result.get("data", "")
    if not audio_b64:
        raise RuntimeError("TTS 返回成功但 data 字段为空")

    return base64.b64decode(audio_b64)


# ── 主入口 ────────────────────────────────────────────────────────────────────

def run(scenes: list, voice_type: str, output_dir: str = None) -> dict:
    """
    运行 TTS Generator 节点，为每段分镜生成对应的 mp3 音频文件。

    Args:
        scenes:     分镜列表，每项含 scene_id / script 字段
        voice_type: 音色代码（由 script_generator 输出，或使用 config 默认值）
        output_dir: 输出目录

    Returns:
        {
            "success": bool,
            "audio_paths": list[str|None],   # 各分镜音频本地路径，失败为 None
            "failed_indices": list[int],      # 失败的分镜索引（0-based）
        }
    """
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    total = len(scenes)
    print(f"[TTS Generator] 开始生成音频，共 {total} 段，音色：{voice_type}")

    audio_paths = []
    failed_indices = []

    for idx, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", idx + 1)
        text = scene.get("script", "").strip()

        if not text:
            print(f"[TTS Generator] 分镜 {scene_id} 台词为空，跳过。")
            audio_paths.append(None)
            failed_indices.append(idx)
            continue

        print(f"[TTS Generator] 合成分镜 {scene_id}/{total}：{text[:30]}...")

        try:
            audio_bytes = _synthesize(text, voice_type)

            filename = f"audio_{scene_id:03d}_{int(time.time())}.mp3"
            save_path = os.path.join(output_dir, filename)
            with open(save_path, "wb") as f:
                f.write(audio_bytes)

            audio_paths.append(save_path)
            print(f"[TTS Generator] 分镜 {scene_id} 音频已保存: {save_path}")

        except Exception as e:
            print(f"[TTS Generator] 分镜 {scene_id} 合成失败: {e}")
            audio_paths.append(None)
            failed_indices.append(idx)

    success_count = sum(1 for p in audio_paths if p is not None)
    print(f"[TTS Generator] 完成：{success_count}/{total} 段成功。")

    return {
        "success": len(failed_indices) == 0,
        "audio_paths": audio_paths,
        "failed_indices": failed_indices,
    }
