"""
节点2：Key Feature Extractor
输入人物小传 → 调用千问 → 输出结构化生图提示词
"""

from openai import OpenAI
import config
try:
    import prompts_config as _pc
except ImportError:
    _pc = None


SYSTEM_PROMPT = """你是一位专业的AI生图提示词工程师，擅长从文字描述中提取可视化人物特征，
并将其转化为精准、高质量的英文生图提示词。你的提示词需要：
1. 聚焦可视化元素（年龄感、面部特征、体型、穿着、气质、所处环境）
2. 使用生图模型能理解的专业描述词汇
3. 避免主观判断和情感描述，只保留视觉可呈现的内容"""


USER_PROMPT_TEMPLATE = """请阅读以下人物小传，提取人物的可视化特征，并转化为英文生图提示词。

【人物小传】
{story}

【提取要求】
请从故事中推断并提取以下维度的视觉特征，如故事未明确提及某维度，请根据人物整体气质合理推断：

1. 年龄感（如：mid-30s woman, late 20s man）
2. 面部特征（如：slightly tired eyes, natural makeup, warm smile）
3. 体型与姿态（如：average build, slightly slouched posture）
4. 穿着风格（如：casual office wear, white shirt, simple jewelry）
5. 整体气质（如：approachable, hardworking, slightly stressed but hopeful）
6. 所处环境（如：home kitchen, modern apartment, morning light）

【输出格式】
直接输出一段英文提示词，各特征用逗号分隔，不要添加任何解释或前缀。
示例格式：mid-30s Asian woman, natural makeup, slightly tired eyes, casual home clothes, warm approachable expression, standing in a modern kitchen, morning soft light
"""


def run(story: str) -> dict:
    """
    运行 Key Feature Extractor 节点

    Returns:
        {
            "success": bool,
            "feature_prompt": str,  # 英文人物特征提示词
        }
    """
    client = OpenAI(
        api_key=config.QWEN_API_KEY,
        base_url=config.QWEN_BASE_URL,
    )

    sys_prompt = (getattr(_pc, "KEY_FEATURE_SYSTEM", None) or SYSTEM_PROMPT) if _pc else SYSTEM_PROMPT
    user_tmpl  = (getattr(_pc, "KEY_FEATURE_USER",   None) or USER_PROMPT_TEMPLATE) if _pc else USER_PROMPT_TEMPLATE

    user_message = user_tmpl.format(story=story)

    print("[Key Feature Extractor] 正在提取人物视觉特征...")

    response = client.chat.completions.create(
        model=config.QWEN_MODEL,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.3,
    )

    feature_prompt = response.choices[0].message.content.strip()

    print(f"[Key Feature Extractor] 特征提取完成：{feature_prompt[:80]}...")
    return {
        "success": True,
        "feature_prompt": feature_prompt,
    }
