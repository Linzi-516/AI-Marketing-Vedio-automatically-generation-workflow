"""
节点：Model Card Generator（模特模卡图生成）
输入：模特人物原图（1张）+ 姿势剪影参考图（1张）
输出：3张模卡图（模特复刻对应动作，灰底，身材/五官/穿搭保持不变）

调用接口：即梦AI 图片生成4.0（异步）
  提交：POST https://visual.volcengineapi.com?Action=CVSync2AsyncSubmitTask&Version=2022-08-31
  查询：POST https://visual.volcengineapi.com?Action=CVSync2AsyncGetResult&Version=2022-08-31
  req_key：jimeng_t2i_v40
  支持多图输入：同时传入模特原图 + 剪影姿势参考图，通过 prompt 指令生成目标姿势模卡图
"""

import os
import time
import json
import base64
import hmac
import hashlib
import datetime
import requests
import config


# ── 姿势参考图配置 ────────────────────────────────────────────────────────────
# 每个姿势对应：(剪影图路径配置key, prompt描述)
# prompt 用于精确指导：参考第二张图的姿势，保留第一张图的人物特征

POSE_CONFIGS = [
    {
        "silhouette_key": 0,   # 对应 config.MODELCARD_SILHOUETTE_PATHS[0]
        "prompt": (
            "第一张图是人物原图，第二张图是姿势参考剪影。"
            "请让人物完全复刻第二张图中的姿势动作，"
            "保持第一张图人物的五官、发型、穿搭、身材比例完全不变，"
            "背景改为纯灰色，输出为时尚模特展示效果。"
        ),
    },
    {
        "silhouette_key": 1,
        "prompt": (
            "第一张图是人物原图，第二张图是姿势参考剪影。"
            "请让人物完全复刻第二张图中的姿势动作，"
            "保持第一张图人物的五官、发型、穿搭、身材比例完全不变，"
            "背景改为纯灰色，输出为时尚模特展示效果。"
        ),
    },
    {
        "silhouette_key": 2,
        "prompt": (
            "第一张图是人物原图，第二张图是姿势参考剪影。"
            "请让人物完全复刻第二张图中的姿势动作，"
            "保持第一张图人物的五官、发型、穿搭、身材比例完全不变，"
            "背景改为纯灰色，输出为时尚模特展示效果。"
        ),
    },
]


# ── 签名工具 ─────────────────────────────────────────────────────────────────

def _sign_request(method: str, path: str, params: dict, body: str, ak: str, sk: str) -> dict:
    """火山引擎 API 签名"""
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
    canonical_request = "\n".join([
        method, canonical_uri, canonical_querystring,
        canonical_headers, signed_headers, body_hash,
    ])

    credential_scope = f"{date_str}/{region}/{service}/request"
    string_to_sign = "\n".join([
        "HMAC-SHA256", datetime_str, credential_scope,
        hashlib.sha256(canonical_request.encode()).hexdigest(),
    ])

    def _hmac(key, msg):
        return hmac.new(
            key if isinstance(key, bytes) else key.encode(),
            msg.encode(), hashlib.sha256
        ).digest()

    signing_key = _hmac(_hmac(_hmac(_hmac(sk, date_str), region), service), "request")
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    authorization = (
        f"HMAC-SHA256 Credential={ak}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )
    return {**headers, "Authorization": authorization}


def _image_to_base64(image_path: str) -> str:
    """读取本地图片并转为 base64 字符串"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _post(params: dict, payload: dict) -> dict:
    """发送签名请求，返回响应 JSON"""
    body = json.dumps(payload)
    headers = _sign_request(
        "POST", "/", params, body,
        config.JIMENG_API_KEY, config.JIMENG_API_SECRET,
    )
    query = "&".join(f"{k}={v}" for k, v in params.items())
    resp = requests.post(
        f"{config.JIMENG_BASE_URL}?{query}",
        headers=headers, data=body, timeout=60,
    )
    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status_code}，响应体: {resp.text[:500]}")
    return resp.json()


# ── 提交任务 ──────────────────────────────────────────────────────────────────

def _submit_card_task(model_image_path: str, silhouette_path: str, prompt: str) -> str:
    """
    提交图片生成4.0任务，返回 task_id
    传入2张图：第1张=模特原图，第2张=剪影姿势参考图
    """
    model_b64 = _image_to_base64(model_image_path)
    silhouette_b64 = _image_to_base64(silhouette_path)

    payload = {
        "req_key": "jimeng_t2i_v40",
        "binary_data_base64": [model_b64, silhouette_b64],
        "prompt": prompt,
        "scale": 0.6,
        "force_single": True,   # 只输出1张，避免多图计费和超时
        "width": config.JIMENG_MODELCARD_WIDTH,
        "height": config.JIMENG_MODELCARD_HEIGHT,
    }

    params = {"Action": "CVSync2AsyncSubmitTask", "Version": "2022-08-31"}
    result = _post(params, payload)

    if result.get("code") != 10000:
        raise RuntimeError(
            f"提交失败: code={result.get('code')} msg={result.get('message')}"
        )

    task_id = result["data"]["task_id"]
    print(f"[Model Card Generator] 任务已提交 task_id={task_id}")
    return task_id


# ── 轮询任务 ──────────────────────────────────────────────────────────────────

def _poll_card_task(task_id: str, max_wait: int = 300) -> tuple:
    """
    轮询任务状态，返回 (result_type, result_data)
    result_type: "url" | "b64"
    """
    payload = {
        "req_key": "jimeng_t2i_v40",
        "task_id": task_id,
        "req_json": "{\"return_url\":true}",
    }
    params = {"Action": "CVSync2AsyncGetResult", "Version": "2022-08-31"}

    start = time.time()
    time.sleep(5)

    while time.time() - start < max_wait:
        result = _post(params, payload)

        if result.get("code") != 10000:
            raise RuntimeError(
                f"查询失败: code={result.get('code')} msg={result.get('message')}"
            )

        data = result.get("data", {})
        status = data.get("status", "")

        if status == "done":
            # 优先取 image_urls，其次 binary_data_base64
            url_list = data.get("image_urls") or []
            b64_list = data.get("binary_data_base64") or []
            if url_list and url_list[0]:
                return ("url", url_list[0])
            elif b64_list and b64_list[0]:
                return ("b64", b64_list[0])
            else:
                raise RuntimeError(f"任务完成但未返回图片数据: {result}")
        elif status in ("not_found", "expired"):
            raise RuntimeError(f"任务异常，status={status}")
        else:
            elapsed = int(time.time() - start)
            print(f"[Model Card Generator] 等待中 status={status} 已等待{elapsed}s ...")
            time.sleep(10)

    raise TimeoutError(f"模卡图生成超时（{max_wait}s），task_id={task_id}")


# ── 单张模卡生成 ──────────────────────────────────────────────────────────────

def _generate_single_card(
    model_image_path: str,
    silhouette_path: str,
    prompt: str,
    output_path: str,
) -> bool:
    """
    生成一张模卡图并保存到 output_path。
    Returns: True=成功，False=失败
    """
    try:
        task_id = _submit_card_task(model_image_path, silhouette_path, prompt)
        result_type, result_data = _poll_card_task(task_id)

        if result_type == "url":
            img_resp = requests.get(result_data, timeout=60)
            img_resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(img_resp.content)
        else:  # b64
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(result_data))

        return True

    except Exception as e:
        print(f"[Model Card Generator] 生成失败: {e}")
        return False


# ── 主入口 ────────────────────────────────────────────────────────────────────

def run(
    model_image_path: str,
    silhouette_paths: list,
    output_dir: str = None,
) -> dict:
    """
    运行模特模卡图生成节点。
    使用即梦图片生成4.0接口，同时传入模特原图 + 剪影姿势参考图，生成对应姿势模卡图。

    Args:
        model_image_path: 模特人物原图路径（1张）
        silhouette_paths: 姿势剪影参考图路径列表（3张）
        output_dir:       输出目录

    Returns:
        {
            "success": bool,
            "card_paths": list[str|None],
            "failed_indices": list[int],
        }
    """
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(model_image_path):
        raise FileNotFoundError(f"模特原图不存在: {model_image_path}")

    pose_count = len(POSE_CONFIGS)
    print(f"[Model Card Generator] 开始生成模卡图，共 {pose_count} 张姿势...")
    print(f"[Model Card Generator] 模特原图: {model_image_path}")

    card_paths = []
    failed_indices = []

    for idx, pose_cfg in enumerate(POSE_CONFIGS):
        sil_idx = pose_cfg["silhouette_key"]
        silhouette_path = silhouette_paths[sil_idx] if sil_idx < len(silhouette_paths) else None
        prompt = pose_cfg["prompt"]

        if not silhouette_path or not os.path.exists(silhouette_path):
            print(f"[Model Card Generator] 姿势 {idx + 1} 剪影图不存在，跳过: {silhouette_path}")
            failed_indices.append(idx)
            card_paths.append(None)
            continue

        silhouette_name = os.path.basename(silhouette_path)
        print(f"[Model Card Generator] 处理姿势 {idx + 1}/{pose_count}: {silhouette_name}")

        timestamp = int(time.time())
        filename = f"modelcard_{timestamp}_pose{idx}.png"
        output_path = os.path.join(output_dir, filename)

        ok = _generate_single_card(model_image_path, silhouette_path, prompt, output_path)

        if ok:
            card_paths.append(output_path)
            print(f"[Model Card Generator] 姿势 {idx + 1} 模卡图已保存: {output_path}")
        else:
            failed_indices.append(idx)
            card_paths.append(None)
            print(f"[Model Card Generator] 姿势 {idx + 1} 生成失败。")

    success_count = sum(1 for p in card_paths if p is not None)
    print(f"[Model Card Generator] 完成：{success_count}/{pose_count} 张成功。")

    return {
        "success": len(failed_indices) == 0,
        "card_paths": card_paths,
        "failed_indices": failed_indices,
    }
