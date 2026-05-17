"""
节点5-B：CLI Video Generator（即梦 CLI 个人账号版）
输入人物图片 + 分镜脚本 → 调用本地 dreamina CLI → 保存视频片段

前置条件：
  1. 已在本地安装 dreamina CLI（curl -s https://jimeng.jianying.com/cli | bash）
  2. 已通过扫码完成登录（首次运行时 CLI 会弹出二维码）

优点：消耗个人即梦账号积分，无需火山引擎 AK/SK
缺点：需要手动扫码登录，不适合完全无人值守场景
"""

import os
import re
import time
import shutil
import subprocess
import config


def _check_dreamina_installed() -> bool:
    """检查 dreamina CLI 是否已安装"""
    if config.CLI_DREAMINA_PATH != "dreamina" and os.path.exists(config.CLI_DREAMINA_PATH):
        return True
    return shutil.which(config.CLI_DREAMINA_PATH) is not None


def _build_video_prompt(script_text: str) -> str:
    """构建统一的口播视频提示词（全程固定镜头）"""
    return (
        f"制作该人物的单人口播视频，要求整体镜头保持不变，不随意变动，"
        f"不要呈现具体的app内容和任何logo，字幕，只需呈现人物画面，"
        f"人物表情自然，没有夸张的表情，动作，语气，全程的人物形象保持稳定，"
        f"不要在视频中生成字幕，口播台词为：{script_text}"
    )


def _generate_video_cli(image_path: str, scene: dict, output_dir: str) -> str:
    """
    调用 dreamina CLI 生成单个分镜视频

    Args:
        image_path: 人物图片路径（首尾帧相同）
        scene: 分镜信息（含 scene_id / duration / script）
        output_dir: 视频输出目录

    Returns:
        生成的视频本地路径

    Raises:
        RuntimeError: CLI 调用失败时抛出
    """
    scene_id = scene.get("scene_id", 1)
    duration = max(config.SCENE_MIN_DURATION, min(scene.get("duration", 5), config.SCENE_MAX_DURATION))
    # CLI 时长参数：5 或 10
    duration_arg = 5 if duration <= 5 else 10

    script_text = scene.get("script", "")
    prompt = _build_video_prompt(script_text)

    filename = f"scene_{scene_id:03d}_{int(time.time())}.mp4"
    output_path = os.path.join(output_dir, filename)

    # 构建 dreamina 命令
    # 使用首尾帧相同策略：--first-frame 和 --last-frame 均指向同一张图
    cmd = [
        config.CLI_DREAMINA_PATH, "video", "generate",
        "--first-frame", image_path,
        "--last-frame", image_path,
        "--prompt", prompt,
        "--duration", str(duration_arg),
        "--output", output_path,
    ]

    print(f"[CLI Generator] 执行命令: {config.CLI_DREAMINA_PATH} video generate --duration {duration_arg}s ...")
    print(f"[CLI Generator] 台词预览: {script_text[:40]}...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.CLI_VIDEO_TIMEOUT,  # 读取配置的超时时间
            encoding="utf-8",
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"CLI 执行超时（{config.CLI_VIDEO_TIMEOUT}s），分镜 {scene_id}")
    except FileNotFoundError:
        raise RuntimeError(
            "未找到 dreamina 命令。请先安装：在 Git Bash 中运行\n"
            "  curl -s https://jimeng.jianying.com/cli | bash\n"
            "然后重启终端。"
        )

    stdout = result.stdout or ""
    stderr = result.stderr or ""

    if result.returncode != 0:
        raise RuntimeError(
            f"dreamina 命令失败（exit={result.returncode}）\n"
            f"stdout: {stdout[:300]}\n"
            f"stderr: {stderr[:300]}"
        )

    # 优先使用 --output 指定的路径，若 CLI 有其他输出路径则从 stdout 解析
    if os.path.exists(output_path):
        return output_path

    # 尝试从 stdout 中解析实际保存路径（兼容不同版本 CLI）
    path_match = re.search(r"saved\s+(?:to\s+)?['\"]?([^\s'\"]+\.mp4)", stdout, re.IGNORECASE)
    if path_match:
        actual_path = path_match.group(1)
        if os.path.exists(actual_path):
            # 如果 CLI 把文件保存到了别处，移动过来
            os.makedirs(output_dir, exist_ok=True)
            shutil.move(actual_path, output_path)
            return output_path

    raise RuntimeError(
        f"CLI 执行成功但未找到输出视频文件。\n"
        f"预期路径: {output_path}\n"
        f"stdout: {stdout[:300]}"
    )


def run(image_paths: list, scenes: list, output_dir: str = None) -> dict:
    """
    运行 CLI Video Generator 节点（即梦个人账号版）

    Args:
        image_paths: 人物图片路径列表（首尾帧均使用同一张图，循环使用）
        scenes: 分镜列表（来自 Script Generator，每项含 scene_id/duration/script）
        output_dir: 输出目录

    Returns:
        {
            "success": bool,
            "video_paths": list[str],   # 各分镜视频本地路径
            "video_urls": list[str],    # CLI 模式无远程URL，均为 None
            "failed_scenes": list[int], # 失败的分镜 scene_id
        }
    """
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    if not image_paths:
        raise ValueError("至少需要提供1张人物图片")

    # 启动前检查 CLI 是否安装
    if not _check_dreamina_installed():
        raise RuntimeError(
            "未找到 dreamina CLI。请先在 Git Bash 中运行以下命令安装：\n"
            "  curl -s https://jimeng.jianying.com/cli | bash\n"
            "安装完成后重启终端，再重新运行工作流。"
        )

    print(f"[CLI Generator] 使用即梦 CLI（个人账号）生成视频，共 {len(scenes)} 段分镜...")

    video_paths = []
    video_urls = []
    failed_scenes = []

    for i, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", i + 1)
        image_path = image_paths[i % len(image_paths)]

        print(f"\n[CLI Generator] 处理分镜 {scene_id}/{len(scenes)}：{scene.get('script', '')[:30]}...")

        try:
            save_path = _generate_video_cli(image_path, scene, output_dir)
            video_paths.append(save_path)
            video_urls.append(None)  # CLI 模式无远程 URL
            print(f"[CLI Generator] 分镜 {scene_id} 视频已保存: {save_path}")

        except Exception as e:
            print(f"[CLI Generator] 分镜 {scene_id} 生成失败: {e}")
            failed_scenes.append(scene_id)
            video_paths.append(None)
            video_urls.append(None)

    success_count = sum(1 for p in video_paths if p is not None)
    print(f"\n[CLI Generator] 视频生成完成：{success_count}/{len(scenes)} 段成功。")

    return {
        "success": len(failed_scenes) == 0,
        "video_paths": video_paths,
        "video_urls": video_urls,
        "failed_scenes": failed_scenes,
    }
