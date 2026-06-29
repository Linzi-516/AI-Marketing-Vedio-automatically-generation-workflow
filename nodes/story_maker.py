"""
节点1：Story Maker
输入产品信息 → 调用千问 → 输出4模块人物小传
"""

from clients.llm_client import chat_completion
try:
    import prompts_config as _pc
except ImportError:
    _pc = None


SYSTEM_PROMPT = """你是一位拥有10年经验的广告文案专家，擅长将产品信息转化为真实、有温度的用户故事。
你的写作风格：纪实感强、直白扎心、拒绝广告腔、不说教、不夸张。
你的目标是让读者看完故事后心里有一句话："这说的就是我。" """


USER_PROMPT_TEMPLATE = """请根据以下产品信息，为我生成一位目标用户的人物小传。

【产品信息】
- 核心产品：{product_name}
- 功能/Offer：{product_offer}
- 目标受众：{target_audience}
- 核心痛点：{pain_points}

【输出格式要求】
请严格按照以下4个模块输出，每个模块之间空一行，不要添加额外标题或序号以外的内容：

## 模块一：我是谁（生活侧写）
[用100-150字描写这个人的日常生活状态、身份背景、典型场景。要有具体细节，拒绝模糊描述。]

## 模块二：投资者画像
[用50-80字描写这个人的消费能力、决策习惯、对产品类型的态度。直白说明"他/她愿不愿意为此付费，为什么"。]

## 模块三：与产品的故事
[用100-150字描写这个人如何遇见产品、产品如何改变了他/她生活中某个具体细节。要有场景感，不要泛泛而谈。]

## 模块四：原话（用户心声）
[用第一人称写1-3句话，模拟这个用户在向朋友推荐产品时会说的原话。口语化，真实，带一点个人情绪。]
"""


def run(product_name: str, product_offer: str, target_audience: str, pain_points: str) -> dict:
    """
    运行 Story Maker 节点

    Returns:
        {
            "success": bool,
            "story": str,         # 完整人物小传文本
            "raw_response": str   # 原始 LLM 响应
        }
    """
    sys_prompt  = (getattr(_pc, "STORY_MAKER_SYSTEM", None) or SYSTEM_PROMPT) if _pc else SYSTEM_PROMPT
    user_tmpl   = (getattr(_pc, "STORY_MAKER_USER",   None) or USER_PROMPT_TEMPLATE) if _pc else USER_PROMPT_TEMPLATE

    user_message = user_tmpl.format(
        product_name=product_name,
        product_offer=product_offer,
        target_audience=target_audience,
        pain_points=pain_points,
    )

    print("[Story Maker] 正在生成人物小传...")

    story_text = chat_completion(
        system_prompt=sys_prompt,
        user_prompt=user_message,
        temperature=0.8,
    )

    print("[Story Maker] 人物小传生成完成。")
    return {
        "success": True,
        "story": story_text,
        "raw_response": story_text,
    }
