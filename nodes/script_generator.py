"""
节点4：Script Generator
输入人物小传 + 视频总时长 → 调用千问 → 输出口播脚本 + 分镜列表

注意：音色选择已移至独立的 voice_type_generator 节点（Step 2.5），
      该节点基于 key_feature_extractor 的视觉特征进行音色决策，与本节点并行执行。
"""

import json
import re
import config
from clients.llm_client import chat_completion
try:
    import prompts_config as _pc
except ImportError:
    _pc = None


SYSTEM_PROMPT = """你是一位专业的短视频口播广告脚本创作者，擅长为真人出镜广告写单人口播脚本。
你的脚本特点：
1. 语言口语化、自然流畅，像真人说话，不像广告词
2. 情感真实，先共情再解决方案，不强行推销
3. 节奏感强，知道哪里停顿、哪里加速
4. 画面保持高稳定性，人物始终正对镜头说话，无需画面切换或场景变动"""


USER_PROMPT_TEMPLATE = """请根据以下人物小传，为我创作一段单人口播广告脚本，并划分分镜。

【人物小传】
{story}

【视频参数】
- 视频总时长：{total_duration}秒
- 每段分镜时长：只能是 {min_duration} 秒或 {max_duration} 秒（由视频生成API严格限制，不能取其他值）

【脚本要求】
1. 用第一人称，模拟真实用户分享体验
2. 结构：开场共情（痛点）→ 转折（遇见产品）→ 效果展示 → 情感收尾/行动号召
3. 语言口语化，带真实情绪，避免"我强烈推荐"等广告腔
4. 总字数与时长匹配（中文口播约3-4字/秒）
5. 每段分镜的 duration 只能取 {min_duration} 或 {max_duration}，不允许其他值

【输出格式】
请严格按照以下 JSON 格式输出，不要添加任何额外文字：

```json
{{
  "full_script": "完整脚本文本（纯文字，无分镜标记）",
  "scenes": [
    {{
      "scene_id": 1,
      "duration": {min_duration},
      "script": "这段分镜的口播台词"
    }},
    {{
      "scene_id": 2,
      "duration": {max_duration},
      "script": "这段分镜的口播台词"
    }}
  ],
  "total_scenes": 3,
  "estimated_duration": 25
}}
```
"""


def _extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON"""
    # 尝试提取 ```json ... ``` 代码块
    match = re.search(r"```json\s*([\s\S]+?)\s*```", text)
    if match:
        json_str = match.group(1)
    else:
        # 尝试直接找到 { ... } 的最外层
        match = re.search(r"\{[\s\S]+\}", text)
        if match:
            json_str = match.group(0)
        else:
            raise ValueError("无法从 LLM 输出中提取 JSON")

    return json.loads(json_str)


def run(story: str, total_duration: int = 30) -> dict:
    """
    运行 Script Generator 节点

    Args:
        story: 人物小传文本
        total_duration: 视频总时长（秒），默认30秒

    Returns:
        {
            "success": bool,
            "full_script": str,      # 完整脚本
            "scenes": list[dict],    # 分镜列表，每项含 scene_id/duration/script
            "total_scenes": int,
            "estimated_duration": int,
        }
    """
    sys_prompt = (getattr(_pc, "SCRIPT_GENERATOR_SYSTEM", None) or SYSTEM_PROMPT) if _pc else SYSTEM_PROMPT
    user_tmpl  = (getattr(_pc, "SCRIPT_GENERATOR_USER",   None) or USER_PROMPT_TEMPLATE) if _pc else USER_PROMPT_TEMPLATE

    user_message = user_tmpl.format(
        story=story,
        total_duration=total_duration,
        min_duration=config.SCENE_MIN_DURATION,
        max_duration=config.SCENE_MAX_DURATION,
    )

    print(f"[Script Generator] 正在生成口播脚本（目标时长 {total_duration}s）...")

    raw_text = chat_completion(
        system_prompt=sys_prompt,
        user_prompt=user_message,
        temperature=0.7,
    )

    script_data = _extract_json(raw_text)

    print(f"[Script Generator] 脚本生成完成，共 {script_data.get('total_scenes', len(script_data.get('scenes', [])))} 个分镜。")
    return {
        "success": True,
        "full_script": script_data.get("full_script", ""),
        "scenes": script_data.get("scenes", []),
        "total_scenes": script_data.get("total_scenes", len(script_data.get("scenes", []))),
        "estimated_duration": script_data.get("estimated_duration", total_duration),
    }
