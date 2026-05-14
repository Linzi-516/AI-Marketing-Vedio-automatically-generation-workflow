"""
节点3：Model Generator
输入人物特征提示词 → 调用 DALL-E 3 生图 → 下载并保存图片
"""

import os
import time
import httpx
from openai import OpenAI
import config


# 固定风格提示词（写实主义，电影感）
STYLE_PROMPT_PREFIX = (
    "ultra-realistic photography, cinematic, shot on Sony A7R V, 4K resolution, "
    "natural skin texture, subsurface scattering, photojournalism style, "
    "shallow depth of field, professional color grading, real person, "
    "documentary-style portrait, "
)

# 负向提示词（DALL-E 通过 prompt 前缀方式规避）
NEGATIVE_STYLE_SUFFIX = (
    " --no cartoon, anime, 3D render, illustration, digital art, "
    "internet celebrity face, celebrity face, over-beautified, plastic skin, "
    "studio background, fake smile, advertisement pose"
)


def _build_full_prompt(feature_prompt: str) -> str:
    return STYLE_PROMPT_PREFIX + feature_prompt + NEGATIVE_STYLE_SUFFIX


def _download_image(url: str, save_path: str) -> bool:
    """下载图片到本地"""
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.get(url)
            resp.raise_for_status()
            with open(save_path, "wb") as f:
                f.write(resp.content)
        return True
    except Exception as e:
        print(f"[Model Generator] 图片下载失败: {e}")
        return False


def run(feature_prompt: str, output_dir: str = None) -> dict:
    """
    运行 Model Generator 节点

    Returns:
        {
            "success": bool,
            "image_paths": list[str],  # 本地保存的图片路径列表
            "image_urls": list[str],   # 原始 URL 列表（有效期约1小时）
        }
    """
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    full_prompt = _build_full_prompt(feature_prompt)

    print("[Model Generator] 正在生成人物图片...")
    print(f"[Model Generator] Prompt 预览: {full_prompt[:120]}...")

    response = client.images.generate(
        model=config.OPENAI_IMAGE_MODEL,
        prompt=full_prompt,
        size=config.OPENAI_IMAGE_SIZE,
        quality=config.OPENAI_IMAGE_QUALITY,
        n=1,
    )

    image_urls = [item.url for item in response.data]
    image_paths = []

    for i, url in enumerate(image_urls):
        timestamp = int(time.time())
        filename = f"model_{timestamp}_{i}.png"
        save_path = os.path.join(output_dir, filename)
        if _download_image(url, save_path):
            image_paths.append(save_path)
            print(f"[Model Generator] 图片已保存: {save_path}")
        else:
            print(f"[Model Generator] 警告：图片 {i} 下载失败，仅保留 URL")

    print(f"[Model Generator] 图片生成完成，共 {len(image_paths)} 张。")
    return {
        "success": True,
        "image_paths": image_paths,
        "image_urls": image_urls,
    }
