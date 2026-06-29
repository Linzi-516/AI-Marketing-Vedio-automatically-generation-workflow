"""
节点5-A（Omni模式）：OmniHuman Video Generator
输入人物图片 URL + TTS 音频，输出有声数字人口播视频。
"""

import os
import time

import config
from clients.jimeng_client import download_url, ensure_success, poll_task, post_visual_api


def _resolve_audio_url(audio_path: str) -> str:
    """将本地音频路径转换为 OmniHuman API 可访问的 URL。"""
    if audio_path.startswith("http://") or audio_path.startswith("https://"):
        return audio_path

    upload_base = getattr(config, "AUDIO_UPLOAD_BASE_URL", "").strip()
    if not upload_base:
        raise RuntimeError(
            f"OmniHuman 接口要求音频为公网 URL，但 audio_path 是本地文件: {audio_path}\n"
            "请在 config.py 中配置 AUDIO_UPLOAD_BASE_URL，"
            "或在调用前将音频手动上传到 CDN/OSS/TOS 并传入 URL。"
        )

    uploader = getattr(config, "audio_uploader", None)
    if callable(uploader):
        url = uploader(audio_path)
        print(f"[Omni Generator] 音频已上传: {url}")
        return url

    raise RuntimeError(
        f"AUDIO_UPLOAD_BASE_URL 已配置但未提供 audio_uploader 函数，"
        f"无法自动上传 {audio_path}"
    )


def _submit_omni_task(image_url: str, audio_url: str, prompt: str) -> str:
    """提交 OmniHuman1.5 视频生成任务，返回 task_id。"""
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

    result = post_visual_api("CVSubmitTask", payload)
    data = ensure_success(result, "OmniHuman task submit")
    task_id = data.get("task_id")
    if not task_id:
        raise RuntimeError("OmniHuman task submit did not return task_id.")

    print(f"[Omni Generator] 任务已提交 task_id={task_id}")
    return task_id


def _poll_omni_task(task_id: str, max_wait: int = 600) -> str:
    """轮询任务状态，返回视频 URL。"""
    return poll_task(
        req_key=config.OMNI_VIDEO_MODEL,
        task_id=task_id,
        action="CVGetResult",
        max_wait=max_wait,
        log_prefix="Omni Generator",
    )


def _download_video(url: str, save_path: str) -> bool:
    try:
        download_url(url, save_path, timeout=120)
        return True
    except Exception as e:
        print(f"[Omni Generator] 视频下载失败: {e}")
        return False


def run(
    image_urls: list,
    audio_paths: list,
    scenes: list,
    output_dir: str = None,
) -> dict:
    """
    运行 OmniHuman Video Generator 节点。

    Returns:
        {
            "success": bool,
            "video_paths": list[str|None],
            "video_urls":  list[str|None],
            "failed_scenes": list[int],
        }
    """
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    if not image_urls:
        raise ValueError("至少需要提供 1 个人物图片 URL")

    video_paths = []
    video_urls = []
    failed_scenes = []

    for i, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", i + 1)
        script = scene.get("script", "")
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
            audio_url = _resolve_audio_url(audio_path)

            prompt = (
                "单人口播视频，镜头固定不动，人物表情自然，"
                "不添加字幕，无夸张动作。"
            )
            if script:
                prompt += f"台词内容：{script[:100]}"

            task_id = _submit_omni_task(image_url, audio_url, prompt)
            print("[Omni Generator] 等待视频生成（最长10分钟）...")
            video_url = _poll_omni_task(task_id)

            save_path = os.path.join(output_dir, f"omni_scene_{scene_id:03d}_{int(time.time())}.mp4")

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
