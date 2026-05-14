"""
节点5：Video Generator
输入人物图片 + 分镜脚本 → 调用即梦AI 3.0 图生视频 → 下载视频片段
"""

import os
import time
import json
import hmac
import hashlib
import datetime
import requests
import config


# 固定口播视频提示词前缀
VIDEO_PROMPT_PREFIX = (
    "single person talking-head video, fixed camera angle, "
    "no app screen or product display, "
    "natural facial expressions, subtle gestures only, "
    "stable consistent character appearance throughout, "
    "no subtitles, no logo, no text overlay, "
    "clean background, cinematic portrait style, "
)


def _sign_request(method: str, path: str, params: dict, body: str, ak: str, sk: str) -> dict:
    """
    火山引擎 API 签名（即梦AI使用火山引擎SDK）
    参考：https://www.volcengine.com/docs/6369/65
    """
    now = datetime.datetime.utcnow()
    date_str = now.strftime("%Y%m%d")
    datetime_str = now.strftime("%Y%m%dT%H%M%SZ")

    service = "cv"
    region = "cn-north-1"

    # canonical request
    canonical_uri = path
    canonical_querystring = "&".join(
        f"{k}={v}" for k, v in sorted(params.items())
    )
    headers = {
        "content-type": "application/json",
        "host": "visual.volcengineapi.com",
        "x-date": datetime_str,
    }
    canonical_headers = "".join(
        f"{k}:{v}\n" for k, v in sorted(headers.items())
    )
    signed_headers = ";".join(sorted(headers.keys()))

    body_hash = hashlib.sha256(body.encode()).hexdigest()
    canonical_request = "\n".join([
        method,
        canonical_uri,
        canonical_querystring,
        canonical_headers,
        signed_headers,
        body_hash,
    ])

    # string to sign
    credential_scope = f"{date_str}/{region}/{service}/request"
    string_to_sign = "\n".join([
        "HMAC-SHA256",
        datetime_str,
        credential_scope,
        hashlib.sha256(canonical_request.encode()).hexdigest(),
    ])

    # signing key
    def _hmac(key, msg):
        return hmac.new(key if isinstance(key, bytes) else key.encode(),
                        msg.encode(), hashlib.sha256).digest()

    signing_key = _hmac(_hmac(_hmac(_hmac(sk, date_str), region), service), "request")
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    authorization = (
        f"HMAC-SHA256 Credential={ak}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )

    return {
        **headers,
        "Authorization": authorization,
    }


def _image_to_base64(image_path: str) -> str:
    import base64
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _submit_video_task(image_path: str, scene: dict) -> str:
    """
    提交即梦 AI 图生视频任务，返回 task_id
    """
    duration = max(config.SCENE_MIN_DURATION, min(scene["duration"], config.SCENE_MAX_DURATION))
    script_text = scene.get("script", "")
    visual_note = scene.get("visual_note", "")

    # 组合视频 prompt
    video_prompt = VIDEO_PROMPT_PREFIX + f"dialogue: \"{script_text}\", {visual_note}"

    image_b64 = _image_to_base64(image_path)

    payload = {
        "req_key": config.JIMENG_VIDEO_MODEL,
        "prompt": video_prompt,
        "image_urls": [],
        "binary_data_base64": [image_b64],
        "duration": duration,
        "width": config.JIMENG_VIDEO_WIDTH,
        "height": config.JIMENG_VIDEO_HEIGHT,
    }
    body = json.dumps(payload)

    path = "/"
    params = {
        "Action": "CVProcess",
        "Version": "2022-08-31",
    }

    headers = _sign_request(
        "POST", path, params, body,
        config.JIMENG_API_KEY, config.JIMENG_API_SECRET
    )

    url = config.JIMENG_BASE_URL
    query = "&".join(f"{k}={v}" for k, v in params.items())
    resp = requests.post(f"{url}?{query}", headers=headers, data=body, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 10000:
        raise RuntimeError(f"即梦AI提交失败: {result}")

    task_id = result["data"]["task_id"]
    return task_id


def _poll_video_task(task_id: str, max_wait: int = 300) -> str:
    """
    轮询即梦AI任务状态，返回视频 URL
    """
    path = "/"
    params = {
        "Action": "CVProcess",
        "Version": "2022-08-31",
    }

    payload = {"task_id": task_id}
    body = json.dumps(payload)

    start = time.time()
    while time.time() - start < max_wait:
        headers = _sign_request(
            "GET", path, params, "",
            config.JIMENG_API_KEY, config.JIMENG_API_SECRET
        )
        query = "&".join(f"{k}={v}" for k, v in params.items())
        resp = requests.get(
            f"{config.JIMENG_BASE_URL}?{query}&task_id={task_id}",
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()
        result = resp.json()

        status = result.get("data", {}).get("status")
        if status == "done":
            return result["data"]["videos"][0]["url"]
        elif status in ("failed", "error"):
            raise RuntimeError(f"即梦AI视频生成失败: {result}")

        print(f"[Video Generator] 等待视频生成（task_id={task_id[:8]}...）状态: {status}")
        time.sleep(5)

    raise TimeoutError(f"即梦AI任务超时（{max_wait}s）: {task_id}")


def _download_video(url: str, save_path: str) -> bool:
    try:
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"[Video Generator] 视频下载失败: {e}")
        return False


def run(image_paths: list, scenes: list, output_dir: str = None) -> dict:
    """
    运行 Video Generator 节点

    Args:
        image_paths: 人物图片路径列表（至少1张，循环使用）
        scenes: 分镜列表（来自 Script Generator）
        output_dir: 输出目录

    Returns:
        {
            "success": bool,
            "video_paths": list[str],   # 各分镜视频本地路径
            "video_urls": list[str],    # 各分镜视频原始URL
            "failed_scenes": list[int], # 失败的分镜 scene_id
        }
    """
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    if not image_paths:
        raise ValueError("至少需要提供1张人物图片")

    video_paths = []
    video_urls = []
    failed_scenes = []

    for i, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", i + 1)
        # 循环使用图片（多张图片轮流）
        image_path = image_paths[i % len(image_paths)]

        print(f"[Video Generator] 处理分镜 {scene_id}/{len(scenes)}：{scene.get('script', '')[:30]}...")

        try:
            task_id = _submit_video_task(image_path, scene)
            print(f"[Video Generator] 分镜 {scene_id} 已提交，task_id={task_id[:8]}...")

            video_url = _poll_video_task(task_id)
            video_urls.append(video_url)

            filename = f"scene_{scene_id:03d}_{int(time.time())}.mp4"
            save_path = os.path.join(output_dir, filename)
            if _download_video(video_url, save_path):
                video_paths.append(save_path)
                print(f"[Video Generator] 分镜 {scene_id} 视频已保存: {save_path}")
            else:
                video_paths.append(None)

        except Exception as e:
            print(f"[Video Generator] 分镜 {scene_id} 生成失败: {e}")
            failed_scenes.append(scene_id)
            video_paths.append(None)
            video_urls.append(None)

    success_count = sum(1 for p in video_paths if p is not None)
    print(f"[Video Generator] 视频生成完成：{success_count}/{len(scenes)} 段成功。")

    return {
        "success": len(failed_scenes) == 0,
        "video_paths": video_paths,
        "video_urls": video_urls,
        "failed_scenes": failed_scenes,
    }
