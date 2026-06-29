"""
节点3：Model Generator
输入人物特征提示词 -> 调用火山引擎即梦文生图 3.0 API 生图 -> 下载/保存图片
"""

import base64
import os
import time

import config
from clients.jimeng_client import download_bytes, post_visual_api


STYLE_PROMPT_PREFIX = (
    "ultra-realistic photography, cinematic, shot on Sony A7R V, 4K resolution, "
    "natural skin texture, subsurface scattering, photojournalism style, "
    "shallow depth of field, professional color grading, real person, "
    "documentary-style portrait, "
)

NEGATIVE_STYLE_SUFFIX = (
    "cartoon, anime, 3D render, illustration, digital art, "
    "internet celebrity face, celebrity face, over-beautified, plastic skin, "
    "studio background, fake smile, advertisement pose"
)


def _build_full_prompt(feature_prompt: str) -> str:
    return STYLE_PROMPT_PREFIX + feature_prompt


def run(feature_prompt: str, output_dir: str = None) -> dict:
    """
    运行 Model Generator 节点。

    Returns:
        {
            "success": bool,
            "image_paths": list[str],
            "image_urls": list[str],
        }
    """
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    full_prompt = _build_full_prompt(feature_prompt)

    print("[Model Generator] 正在调用即梦文生图 3.0 API 生成人物图片...")
    print(f"[Model Generator] Prompt 预览: {full_prompt[:120]}...")

    payload = {
        "req_key": config.JIMENG_IMAGE_MODEL,
        "prompt": full_prompt,
        "negative_prompt": NEGATIVE_STYLE_SUFFIX,
        "width": config.JIMENG_IMAGE_WIDTH,
        "height": config.JIMENG_IMAGE_HEIGHT,
        "scale": config.JIMENG_IMAGE_SCALE,
        "ddim_steps": config.JIMENG_IMAGE_STEPS,
        "use_pre_llm": config.JIMENG_IMAGE_USE_LLM,
        "return_url": config.JIMENG_IMAGE_RETURN_URL,
        "seed": -1,
    }

    try:
        result = post_visual_api("CVProcess", payload, timeout=60)

        if result.get("code") != 10000:
            raise RuntimeError(f"即梦生图失败: {result}")

        image_paths = []
        data = result.get("data", {})
        b64_images = data.get("binary_data_base64", [])
        image_urls = data.get("image_urls", [])

        if not b64_images and not image_urls:
            raise RuntimeError(f"即梦返回数据异常，未获取到图片数据: {result}")

        for i in range(max(len(b64_images), len(image_urls))):
            timestamp = int(time.time())
            save_path = os.path.join(output_dir, f"model_{timestamp}_{i}.png")

            if i < len(b64_images) and b64_images[i]:
                with open(save_path, "wb") as f:
                    f.write(base64.b64decode(b64_images[i]))
                image_paths.append(save_path)
                print(f"[Model Generator] 图片已保存(Base64): {save_path}")
            elif i < len(image_urls) and image_urls[i]:
                with open(save_path, "wb") as f:
                    f.write(download_bytes(image_urls[i], timeout=60))
                image_paths.append(save_path)
                print(f"[Model Generator] 图片已下载(URL): {save_path}")

        print(f"[Model Generator] 图片生成完成，共 {len(image_paths)} 张。")
        return {
            "success": True,
            "image_paths": image_paths,
            "image_urls": image_urls,
        }
    except Exception as e:
        print(f"[Model Generator] 生成失败异常: {e}")
        return {
            "success": False,
            "image_paths": [],
            "image_urls": [],
        }
