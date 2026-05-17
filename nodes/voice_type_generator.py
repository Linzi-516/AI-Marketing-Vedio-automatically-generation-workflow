"""
节点2.5：Voice Type Generator（音色选择器）
输入：人物视觉特征提示词（feature_prompt）+ 人物小传（story）
输出：最合适的 TTS 音色代码（voice_type）

依赖 Step 2（key_feature_extractor）的输出，与 script_generator 并行执行。
职责：仅做音色决策，不参与脚本创作，确保音色与人物形象保持一致。
"""

from openai import OpenAI
import config


SYSTEM_PROMPT = """你是一位专业的 TTS 音色选择专家。
你的任务是根据广告人物的性别、年龄、气质以及广告产品类型，从给定的音色列表中选择最合适的一个音色。

【决策规则】
优先匹配性别，再匹配年龄段，最后匹配气质/产品类型：

女性音色：
- 女性 + 年轻(20~30岁) + 活力/促销/电商  → BV402_streaming（促销女声）
- 女性 + 年轻(20~30岁) + 美妆/生活/甜美  → BV412_streaming（影视解说小美）
- 女性 + 年轻(20~30岁) + 潮流/零食/休闲  → BV005_streaming（活泼女声）
- 女性 + 成熟(30~45岁) + 知性/职场/B端   → BV009_streaming（知性女声）
- 女性 + 成熟(30~45岁) + 情感/励志/品牌  → BV403_streaming（鸡汤女声）
- 女性 + 成熟(30~45岁) + 文艺/生活/创意  → BV428_streaming（清新文艺女声）
- 女性 + 全年龄 + 情感深度/广告通用       → BV700_V2_streaming（灿灿 2.0）
- 女性 + 直播带货/强促销                  → BV418_streaming（直播一姐）
- 女性 + 母婴/家庭/温情                   → BV157_streaming（慈爱姥姥）
- 女性 + 产品介绍/客服/助手               → BV405_streaming（甜美小源）

男性音色：
- 男性 + 年轻(20~30岁) + 活力/快消/运动  → BV401_streaming（促销男声）
- 男性 + 年轻(20~30岁) + 科技/3C/干练    → BV411_streaming（影视解说小帅）
- 男性 + 年轻(20~30岁) + 阳光/快消/运动  → BV056_streaming（阳光男声）
- 男性 + 成熟(35岁+)  + 品牌/高端/质感   → BV006_streaming（磁性男声）
- 男性 + 成熟(35岁+)  + 故事/品牌/沉浸   → BV408_streaming（译制片男声）
- 男性 + 成熟(40岁+)  + 金融/政企/权威   → BV142_streaming（沉稳解说男）
- 男性 + 健康/养生/权威类                 → BV158_streaming（智慧老者）
- 男性 + 全年龄 + 旁白/情感/通用         → BV701_V2_streaming（擎苍 2.0）

【可选音色列表】
voice_type           | 音色名称        | 适用场景
---------------------|-----------------|----------------------------------
BV402_streaming      | 促销女声        | 电商活动/亲切促销（女）
BV401_streaming      | 促销男声        | 电商活动/热情促销（男）
BV700_V2_streaming   | 灿灿 2.0        | 广告通用/情感深度（女，含多情感）
BV701_V2_streaming   | 擎苍 2.0        | 男声通用/旁白沉浸（男，含多情感）
BV006_streaming      | 磁性男声        | 品牌/高端广告（男）
BV412_streaming      | 影视解说小美    | 美妆/生活类（女）
BV411_streaming      | 影视解说小帅    | 科技/3C类（男）
BV009_streaming      | 知性女声        | 知性/职场/B端（女）
BV403_streaming      | 鸡汤女声        | 品牌情感/励志（女）
BV428_streaming      | 清新文艺女声    | 生活/文创类（女）
BV142_streaming      | 沉稳解说男      | 金融/政企/权威类（男）
BV056_streaming      | 阳光男声        | 快消/运动/阳光向（男）
BV005_streaming      | 活泼女声        | 年轻向/零食/潮品类（女）
BV158_streaming      | 智慧老者        | 健康/养生/权威类（男）
BV157_streaming      | 慈爱姥姥        | 母婴/家庭/温情类（女）
BV408_streaming      | 译制片男声      | 品牌故事/成熟厚重（男）
BV418_streaming      | 直播一姐        | 直播带货/促销（女）
BV405_streaming      | 甜美小源        | 产品介绍/客服（女）

【输出要求】
只输出音色代码（如 BV402_streaming），不要输出任何解释或额外文字。"""


USER_PROMPT_TEMPLATE = """请根据以下信息为广告视频选择最合适的 TTS 音色。

【人物视觉特征（来自生图提示词）】
{feature_prompt}

【人物小传（含产品/场景背景）】
{story}

请结合人物的性别、年龄感、气质以及产品类型，按照决策规则选择最合适的音色，只输出 voice_type 编码。"""


def run(feature_prompt: str, story: str) -> dict:
    """
    运行 Voice Type Generator 节点

    Args:
        feature_prompt: key_feature_extractor 输出的英文视觉特征提示词
        story:          story_maker 输出的人物小传文本

    Returns:
        {
            "success": bool,
            "voice_type": str,   # 音色代码，如 "BV402_streaming"
        }
    """
    client = OpenAI(
        api_key=config.QWEN_API_KEY,
        base_url=config.QWEN_BASE_URL,
    )

    user_message = USER_PROMPT_TEMPLATE.format(
        feature_prompt=feature_prompt,
        story=story,
    )

    print("[Voice Type Generator] 正在根据人物特征选择音色...")

    response = client.chat.completions.create(
        model=config.QWEN_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,   # 低温度，保证输出稳定性
    )

    raw = (response.choices[0].message.content or "").strip()

    # 清理多余内容，只保留音色编码（形如 BV\d+\w*_streaming）
    import re
    match = re.search(r"BV\w+_streaming", raw)
    if match:
        voice_type = match.group(0)
    else:
        # 回退到配置默认值
        voice_type = getattr(config, "TTS_DEFAULT_VOICE", "BV001_V2_streaming")
        print(f"[Voice Type Generator] 警告：未能从输出中提取有效音色代码，回退到默认值：{voice_type}")

    print(f"[Voice Type Generator] 音色选择完成：{voice_type}")
    return {
        "success": True,
        "voice_type": voice_type,
    }
