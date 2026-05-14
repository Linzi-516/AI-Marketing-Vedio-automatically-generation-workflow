"""
节点5：Video Generator
输入人物图片 + 分镜脚本 → 调用即梦AI 3.0 图生视频（首帧）→ 下载视频片段

接口文档：即梦AI-视频生成3.0 1080P-图生视频-首帧
  提交：POST https://visual.volcengineapi.com?Action=CVSync2AsyncSubmitTask&Version=2022-08-31
  查询：POST https://visual.volcengineapi.com?Action=CVSync2AsyncGetResult&Version=2022-08-31
  req_key：jimeng_i2v_first_v30_1080
"""

import os
import time
import json
import hmac
import hashlib
import datetime
import base64
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
    火山引擎 API 签名
    Region: cn-north-1，Service: cv
    """
    now = datetime.datetime.utcnow()
    date_str = now.strftime("%Y%m%d")
    datetime_str = now.strftime("%Y%m%dT%H%M%SZ")

    service = "cv"
    region = "cn-north-1"

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

    credential_scope = f"{date_str}/{region}/{service}/request"
    string_to_sign = "\n".join([
        "HMAC-SHA256",
        datetime_str,
        credential_scope,
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
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _submit_task(image_path: str, scene: dict) -> str:
    """
    提交图生视频任务，返回 task_id
    Action: CVSync2AsyncSubmitTask
    """
    duration = max(config.SCENE_MIN_DURATION, min(scene["duration"], config.SCENE_MAX_DURATION))
    # frames: 5s=121, 10s=241（仅支持这两个值）
    frames = 121 if duration <= 5 else 241

    script_text = scene.get("script", "")
    visual_note = scene.get("visual_note", "")
    video_prompt = VIDEO_PROMPT_PREFIX + f"dialogue: \"{script_text}\", {visual_note}"

    image_b64 = _image_to_base64(image_path)

    payload = {
        "req_key": config.JIMENG_VIDEO_MODEL,
        "binary_data_base64": [image_b64],
        "prompt": video_prompt,
        "seed": -1,
        "frames": frames,
    }
    body = json.dumps(payload)

    params = {"Action": "CVSync2AsyncSubmitTask", "Version": "2022-08-31"}
    headers = _sign_request(
        "POST", "/", params, body,
        config.JIMENG_API_KEY, config.JIMENG_API_SECRET
    )
    query = "&".join(f"{k}={v}" for k, v in params.items())
    resp = requests.post(
        f"{config.JIMENG_BASE_URL}?{query}",
        headers=headers, data=body, timeout=60
    )
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 10000:
        raise RuntimeError(f"即梦AI提交失败: code={result.get('code')} msg={result.get('message')}")

    task_id = result["data"]["task_id"]
    print(f"[Video Generator] 任务已提交 task_id={task_id}")
    return task_id


def _poll_task(task_id: str, max_wait: int = 600) -> str:
    """
    轮询任务状态，返回视频 URL
    Action: CVSync2AsyncGetResult
    status: in_queue / generating / done / not_found / expired
    """
    payload = {
        "req_key": config.JIMENG_VIDEO_MODEL,
        "task_id": task_id,
    }
    body = json.dumps(payload)
    params = {"Action": "CVSync2AsyncGetResult", "Version": "2022-08-31"}

    start = time.time()
    interval = 10  # 每10秒轮询一次
    time.sleep(5)  # 提交后稍等再开始轮询

    while time.time() - start < max_wait:
        # 带重试的轮询请求（网络抖动时重试3次）
        last_err = None
        for attempt in range(3):
            try:
                headers = _sign_request(
                    "POST", "/", params, body,
                    config.JIMENG_API_KEY, config.JIMENG_API_SECRET
                )
                query = "&".join(f"{k}={v}" for k, v in params.items())
                resp = requests.post(
                    f"{config.JIMENG_BASE_URL}?{query}",
                    headers=headers, data=body, timeout=30
                )
                resp.raise_for_status()
                last_err = None
                break
            except Exception as e:
                last_err = e
                time.sleep(3)
        if last_err:
            raise last_err
        result = resp.json()

        if result.get("code") != 10000:
            raise RuntimeError(f"即梦AI查询失败: code={result.get('code')} msg={result.get('message')}")

        data = result.get("data", {})
        status = data.get("status", "")

        if status == "done":
            video_url = data.get("video_url", "")
            if not video_url:
                raise RuntimeError("任务完成但 video_url 为空")
            return video_url
        elif status in ("not_found", "expired"):
            raise RuntimeError(f"任务异常，status={status}")
        else:
            elapsed = int(time.time() - start)
            print(f"[Video Generator] 等待中 status={status} 已等待{elapsed}s task_id={task_id[:8]}...")
            time.sleep(interval)

    raise TimeoutError(f"视频生成超时（{max_wait}s），task_id={task_id}")


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
        image_path = image_paths[i % len(image_paths)]

        print(f"[Video Generator] 处理分镜 {scene_id}/{len(scenes)}：{scene.get('script', '')[:30]}...")

        try:
            # 1. 提交任务
            task_id = _submit_task(image_path, scene)

            # 2. 轮询结果
            print(f"[Video Generator] 等待视频生成（最长10分钟）...")
            video_url = _poll_task(task_id)

            # 3. 下载视频
            filename = f"scene_{scene_id:03d}_{int(time.time())}.mp4"
            save_path = os.path.join(output_dir, filename)

            if _download_video(video_url, save_path):
                video_paths.append(save_path)
                video_urls.append(video_url)
                print(f"[Video Generator] 分镜 {scene_id} 视频已保存: {save_path}")
            else:
                raise RuntimeError("视频下载失败")

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
