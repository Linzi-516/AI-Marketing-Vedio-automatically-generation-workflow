"""
节点5-A（Omni模式）：OmniHuman Video Generator
输入：人物图片（URL）+ TTS 音频（本地路径）+ 分镜脚本（prompt）
输出：与分镜数量相同的有声 mp4 视频文件列表

调用接口：即梦 OmniHuman1.5（数字人模型）
  提交：POST https://visual.volcengineapi.com?Action=CVSubmitTask&Version=2022-08-31
  查询：POST https://visual.volcengineapi.com?Action=CVGetResult&Version=2022-08-31
  req_key：jimeng_realman_avatar_picture_omni_v15

流程：
  1. 将本地音频上传至可公网访问的临时存储，获取音频 URL（借用火山引擎 TOS 或用户自行提供 CDN）
     → 本节点采用简化方案：直接使用 file:// base64 data URI 不可行，
       因此提供两种模式：
         a. audio_url 模式：外部传入已公网可访问的音频 URL（推荐）
         b. 本地上传模式：自动将 mp3 上传至火山引擎 ImageX/TOS（需额外配置，暂不实现）
     当前实现：调用方需将音频先上传并传入 audio_url，或 workflow 负责上传。
     为降低集成复杂度，本节点同时支持：
       - audio_path（本地文件路径）→ 自动读取并以 base64 data URI 方式处理（不推荐，接口不一定支持）
       - audio_url（http/https URL）→ 直接使用（推荐）

注意：
  - 每段音频时长必须 < 60s，建议 < 15s
  - 图片必须为可公网访问的 URL
  - 视频 URL 有效期仅 1 小时，需及时下载
"""

import os
import time
import json
import hmac
import hashlib
import datetime
import requests
import config


# ── 火山引擎签名（与 api_generator 相同）────────────────────────────────────

def _sign_request(method: str, path: str, params: dict, body: str, ak: str, sk: str) -> dict:
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


def _post(params: dict, payload: dict) -> dict:
    """封装签名 + POST 请求"""
    body = json.dumps(payload)
    headers = _sign_request(
        "POST", "/", params, body,
        config.JIMENG_API_KEY, config.JIMENG_API_SECRET
    )
    query = "&".join(f"{k}={v}" for k, v in params.items())
    resp = requests.post(
        f"{config.JIMENG_BASE_URL}?{query}",
        headers=headers, data=body, timeout=60
    )
    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status_code}，响应体: {resp.text[:500]}")
    return resp.json()


# ── 音频 URL 解析 ──────────────────────────────────────────────────────────────

def _resolve_audio_url(audio_path: str) -> str:
    """
    将本地音频路径转换为可用于 API 的 URL。

    优先级：
      1. 如果 audio_path 本身已是 http/https URL，直接返回
      2. 如果是本地文件，检查 config.AUDIO_UPLOAD_BASE_URL 是否配置：
           - 若配置了，尝试将文件上传（调用 config 提供的上传函数）
           - 若未配置，抛出 RuntimeError 提示用户配置

    当前实现支持以下上传后端（在 config.py 中配置 AUDIO_UPLOAD_BASE_URL）：
      - 留空：抛出 RuntimeError，要求用户手动提供 URL
    """
    if audio_path.startswith("http://") or audio_path.startswith("https://"):
        return audio_path

    # 本地文件 → 上传
    upload_base = getattr(config, "AUDIO_UPLOAD_BASE_URL", "").strip()
    if not upload_base:
        raise RuntimeError(
            f"OmniHuman 接口要求音频为公网 URL，但 audio_path 是本地文件: {audio_path}\n"
            "请在 config.py 中配置 AUDIO_UPLOAD_BASE_URL，"
            "或在调用前将音频手动上传到 CDN/OSS/TOS 并传入 URL。"
        )

    # 调用用户配置的上传函数（config.audio_uploader）
    uploader = getattr(config, "audio_uploader", None)
    if callable(uploader):
        url = uploader(audio_path)
        print(f"[Omni Generator] 音频已上传: {url}")
        return url

    raise RuntimeError(
        f"AUDIO_UPLOAD_BASE_URL 已配置但未提供 audio_uploader 函数，"
        f"无法自动上传 {audio_path}"
    )


# ── 提交任务 ──────────────────────────────────────────────────────────────────

def _submit_omni_task(image_url: str, audio_url: str, prompt: str) -> str:
    """
    提交 OmniHuman1.5 视频生成任务，返回 task_id
    Action: CVSubmitTask
    """
    payload = {
        "req_key": config.OMNI_VIDEO_MODEL,
        "image_url": image_url,
        "audio_url": audio_url,
        "seed": -1,
        "output_resolution": config.OMNI_OUTPUT_RESOLUTION,
        "pe_fast_mode": config.OMNI_FAST_MODE,
    }
    if prompt:
        payload["prompt"] = prompt

    params = {"Action": "CVSubmitTask", "Version": "2022-08-31"}
    result = _post(params, payload)

    if result.get("code") != 10000:
        raise RuntimeError(
            f"OmniHuman 提交失败: code={result.get('code')} msg={result.get('message')}"
        )

    task_id = result["data"]["task_id"]
    print(f"[Omni Generator] 任务已提交 task_id={task_id}")
    return task_id


# ── 轮询任务 ──────────────────────────────────────────────────────────────────

def _poll_omni_task(task_id: str, max_wait: int = 600) -> str:
    """
    轮询任务状态，返回视频 URL
    status: processing / in_queue / generating / done / not_found / expired
    """
    payload = {
        "req_key": config.OMNI_VIDEO_MODEL,
        "task_id": task_id,
    }
    params = {"Action": "CVGetResult", "Version": "2022-08-31"}

    start = time.time()
    interval = 10
    time.sleep(5)

    while time.time() - start < max_wait:
        last_err = None
        for attempt in range(3):
            try:
                result = _post(params, payload)
                last_err = None
                break
            except Exception as e:
                last_err = e
                time.sleep(3)
        if last_err:
            raise last_err

        if result.get("code") != 10000:
            raise RuntimeError(
                f"OmniHuman 查询失败: code={result.get('code')} msg={result.get('message')}"
            )

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
            print(f"[Omni Generator] 等待中 status={status} 已等待{elapsed}s task_id={task_id[:8]}...")
            time.sleep(interval)

    raise TimeoutError(f"OmniHuman 视频生成超时（{max_wait}s），task_id={task_id}")


# ── 下载视频 ──────────────────────────────────────────────────────────────────

def _download_video(url: str, save_path: str) -> bool:
    try:
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"[Omni Generator] 视频下载失败: {e}")
        return False


# ── 主入口 ────────────────────────────────────────────────────────────────────

def run(
    image_urls: list,
    audio_paths: list,
    scenes: list,
    output_dir: str = None,
) -> dict:
    """
    运行 OmniHuman Video Generator 节点。
    每段分镜对应一张图片 + 一段 TTS 音频 → 生成一段有声视频。

    Args:
        image_urls:   人物图片 URL 列表（公网可访问）。若列表长度 < 分镜数，循环使用。
        audio_paths:  TTS 音频本地路径或 URL 列表（与 scenes 一一对应）。
        scenes:       分镜列表（来自 Script Generator，每项含 scene_id / script）。
        output_dir:   输出目录。

    Returns:
        {
            "success": bool,
            "video_paths": list[str|None],   # 各分镜视频本地路径
            "video_urls":  list[str|None],   # 各分镜视频原始 URL（有效期1小时）
            "failed_scenes": list[int],       # 失败的分镜 scene_id
        }
    """
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    if not image_urls:
        raise ValueError("至少需要提供1个人物图片 URL")

    video_paths = []
    video_urls = []
    failed_scenes = []

    for i, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", i + 1)
        script = scene.get("script", "")

        # 获取本段对应的图片 URL 和音频
        image_url = image_urls[i % len(image_urls)]
        audio_path = audio_paths[i] if i < len(audio_paths) else None

        if not audio_path:
            print(f"[Omni Generator] 分镜 {scene_id} 无对应音频，跳过。")
            failed_scenes.append(scene_id)
            video_paths.append(None)
            video_urls.append(None)
            continue

        print(f"[Omni Generator] 处理分镜 {scene_id}/{len(scenes)}: {script[:30]}...")

        try:
            # 解析音频 URL（本地文件需上传）
            audio_url = _resolve_audio_url(audio_path)

            # 构建 prompt：引导人物做口播动作
            prompt = (
                f"单人口播视频，镜头固定不动，人物表情自然，"
                f"不添加字幕，无夸张动作。"
            )
            if script:
                prompt += f"台词内容：{script[:100]}"

            # 提交并等待
            task_id = _submit_omni_task(image_url, audio_url, prompt)
            print(f"[Omni Generator] 等待视频生成（最长10分钟）...")
            video_url = _poll_omni_task(task_id)

            # 下载视频
            filename = f"omni_scene_{scene_id:03d}_{int(time.time())}.mp4"
            save_path = os.path.join(output_dir, filename)

            if _download_video(video_url, save_path):
                video_paths.append(save_path)
                video_urls.append(video_url)
                print(f"[Omni Generator] 分镜 {scene_id} 视频已保存: {save_path}")
            else:
                raise RuntimeError("视频下载失败")

        except Exception as e:
            print(f"[Omni Generator] 分镜 {scene_id} 生成失败: {e}")
            failed_scenes.append(scene_id)
            video_paths.append(None)
            video_urls.append(None)

    success_count = sum(1 for p in video_paths if p is not None)
    print(f"[Omni Generator] 视频生成完成：{success_count}/{len(scenes)} 段成功。")

    return {
        "success": len(failed_scenes) == 0,
        "video_paths": video_paths,
        "video_urls": video_urls,
        "failed_scenes": failed_scenes,
    }
