"""
节点5-A：API Video Generator（火山引擎版）
输入人物图片 + 分镜脚本 -> 调用即梦图生视频 -> 下载视频片段
"""

import os
import time

import config
from clients.jimeng_client import download_url, image_to_base64, poll_task, submit_async_task


def _build_video_prompt(script_text: str) -> str:
    """构建统一的口播视频提示词。"""
    return (
        f"制作该人物的单人口播视频，要求整体镜头保持不变，不随意变动，"
        f"不要呈现具体的app内容和任何logo、字幕，只需呈现人物画面。"
        f"人物表情自然，没有夸张的表情动作，人物形象全程保持稳定。"
        f"不要在视频中生成字幕，口播台词为：{script_text}"
    )


def _submit_task(image_path: str, scene: dict) -> str:
    """提交图生视频任务，返回 task_id。"""
    duration = max(config.SCENE_MIN_DURATION, min(scene["duration"], config.SCENE_MAX_DURATION))
    frames = 121 if duration <= 5 else 241

    image_b64 = image_to_base64(image_path)
    payload = {
        "req_key": config.JIMENG_VIDEO_MODEL,
        "binary_data_base64": [image_b64, image_b64],
        "prompt": _build_video_prompt(scene.get("script", "")),
        "seed": -1,
        "frames": frames,
    }

    task_id = submit_async_task(payload, operation="即梦视频任务提交")
    print(f"[API Generator] 任务已提交 task_id={task_id}")
    return task_id


def _poll_task(task_id: str, max_wait: int = 600) -> str:
    """轮询任务状态，返回视频 URL。"""
    return poll_task(
        req_key=config.JIMENG_VIDEO_MODEL,
        task_id=task_id,
        action="CVSync2AsyncGetResult",
        max_wait=max_wait,
        log_prefix="API Generator",
    )


def _download_video(url: str, save_path: str) -> bool:
    try:
        download_url(url, save_path, timeout=120)
        return True
    except Exception as e:
        print(f"[API Generator] 视频下载失败: {e}")
        return False


def run(image_paths: list, scenes: list, output_dir: str = None) -> dict:
    """
    运行 API Video Generator 节点。

    Returns:
        {
            "success": bool,
            "video_paths": list[str|None],
            "video_urls": list[str|None],
            "failed_scenes": list[int],
        }
    """
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    if not image_paths:
        raise ValueError("至少需要提供 1 张人物图片")

    video_paths = []
    video_urls = []
    failed_scenes = []

    for i, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", i + 1)
        image_path = image_paths[i % len(image_paths)]

        print(f"[API Generator] 处理分镜 {scene_id}/{len(scenes)}：{scene.get('script', '')[:30]}...")

        try:
            task_id = _submit_task(image_path, scene)

            print("[API Generator] 等待视频生成（最长10分钟）...")
            video_url = _poll_task(task_id)

            save_path = os.path.join(output_dir, f"scene_{scene_id:03d}_{int(time.time())}.mp4")

            if _download_video(video_url, save_path):
                video_paths.append(save_path)
                video_urls.append(video_url)
                print(f"[API Generator] 分镜 {scene_id} 视频已保存: {save_path}")
            else:
                raise RuntimeError("视频下载失败")

        except Exception as e:
            print(f"[API Generator] 分镜 {scene_id} 生成失败: {e}")
            failed_scenes.append(scene_id)
            video_paths.append(None)
            video_urls.append(None)

    success_count = sum(1 for p in video_paths if p is not None)
    print(f"[API Generator] 视频生成完成：{success_count}/{len(scenes)} 段成功。")

    return {
        "success": len(failed_scenes) == 0,
        "video_paths": video_paths,
        "video_urls": video_urls,
        "failed_scenes": failed_scenes,
    }
