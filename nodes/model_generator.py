"""
节点3：Model Generator
输入人物特征提示词 → 调用火山引擎（智能绘图）API 生图 → 下载/保存图片
"""

import os
import time
import json
import base64
import hmac
import hashlib
import datetime
import requests
import httpx
import config


# 固定风格提示词（写实主义，电影感）
STYLE_PROMPT_PREFIX = (
    "ultra-realistic photography, cinematic, shot on Sony A7R V, 4K resolution, "
    "natural skin texture, subsurface scattering, photojournalism style, "
    "shallow depth of field, professional color grading, real person, "
    "documentary-style portrait, "
)

# 负向提示词
NEGATIVE_STYLE_SUFFIX = (
    "cartoon, anime, 3D render, illustration, digital art, "
    "internet celebrity face, celebrity face, over-beautified, plastic skin, "
    "studio background, fake smile, advertisement pose"
)

def _sign_request(method: str, path: str, params: dict, body: str, ak: str, sk: str) -> dict:
    """
    火山引擎 API 签名
    """
    now = datetime.datetime.utcnow()
    date_str = now.strftime("%Y%m%d")
    datetime_str = now.strftime("%Y%m%dT%H%M%SZ")

    service = "cv"
    region = "cn-north-1"

    canonical_uri = path
    canonical_querystring = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    headers = {
        "content-type": "application/json",
        "host": "visual.volcengineapi.com",
        "x-date": datetime_str,
    }
    canonical_headers = "".join(f"{k}:{v}\n" for k, v in sorted(headers.items()))
    signed_headers = ";".join(sorted(headers.keys()))
    body_hash = hashlib.sha256(body.encode()).hexdigest()
    canonical_request = "\n".join([method, canonical_uri, canonical_querystring, canonical_headers, signed_headers, body_hash])

    credential_scope = f"{date_str}/{region}/{service}/request"
    string_to_sign = "\n".join(["HMAC-SHA256", datetime_str, credential_scope, hashlib.sha256(canonical_request.encode()).hexdigest()])

    def _hmac(key, msg):
        return hmac.new(key if isinstance(key, bytes) else key.encode(), msg.encode(), hashlib.sha256).digest()

    signing_key = _hmac(_hmac(_hmac(_hmac(sk, date_str), region), service), "request")
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    authorization = f"HMAC-SHA256 Credential={ak}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
    return {**headers, "Authorization": authorization}

def _build_full_prompt(feature_prompt: str) -> str:
    return STYLE_PROMPT_PREFIX + feature_prompt

def run(feature_prompt: str, output_dir: str = None) -> dict:
    """
    运行 Model Generator 节点 (火山引擎版本)

    Returns:
        {
            "success": bool,
            "image_paths": list[str],  # 本地保存的图片路径列表
        }
    """
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    full_prompt = _build_full_prompt(feature_prompt)

    print("[Model Generator] 正在调用火山引擎智能绘图 API 生成人物图片...")
    print(f"[Model Generator] Prompt 预览: {full_prompt[:120]}...")

    payload = {
        "req_key": config.JIMENG_IMAGE_MODEL,
        "prompt": full_prompt,
        "negative_prompt": NEGATIVE_STYLE_SUFFIX,
        "width": config.JIMENG_IMAGE_WIDTH,
        "height": config.JIMENG_IMAGE_HEIGHT,
    }
    body = json.dumps(payload)

    path = "/"
    params = {
        "Action": "CVProcess",
        "Version": "2022-08-31",
    }

    headers = _sign_request("POST", path, params, body, config.JIMENG_API_KEY, config.JIMENG_API_SECRET)
    
    url = config.JIMENG_BASE_URL
    query = "&".join(f"{k}={v}" for k, v in params.items())
    
    try:
        resp = requests.post(f"{url}?{query}", headers=headers, data=body, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        
        if result.get("code") != 10000:
            raise RuntimeError(f"火山引擎生成失败: {result}")
        
        image_paths = []
        # CVProcess 通常通过 base64 返回图像内容
        b64_images = result.get("data", {}).get("binary_data_base64", [])
        image_urls = result.get("data", {}).get("image_urls", [])

        if not b64_images and not image_urls:
            raise RuntimeError(f"火山引擎返回数据异常，未获取到图片数据: {result}")

        for i in range(max(len(b64_images), len(image_urls))):
            timestamp = int(time.time())
            filename = f"model_{timestamp}_{i}.png"
            save_path = os.path.join(output_dir, filename)

            if i < len(b64_images) and b64_images[i]:
                with open(save_path, "wb") as f:
                    f.write(base64.b64decode(b64_images[i]))
                image_paths.append(save_path)
                print(f"[Model Generator] 图片已保存 (Base64): {save_path}")
            elif i < len(image_urls) and image_urls[i]:
                # 备用方案，通过 URL 下载
                with httpx.Client(timeout=60) as client:
                    img_resp = client.get(image_urls[i])
                    img_resp.raise_for_status()
                    with open(save_path, "wb") as f:
                        f.write(img_resp.content)
                image_paths.append(save_path)
                print(f"[Model Generator] 图片已下载 (URL): {save_path}")

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
