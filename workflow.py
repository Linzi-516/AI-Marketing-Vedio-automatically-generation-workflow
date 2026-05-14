"""
主工作流编排
输入产品信息 → 并行执行图像链路 + 脚本链路 → 生成视频片段
"""

import os
import json
import time
import concurrent.futures
from datetime import datetime

import config
from nodes import story_maker, key_feature_extractor, model_generator, script_generator, video_generator


def _save_state(run_dir: str, state: dict):
    """保存工作流中间状态，方便断点续跑"""
    path = os.path.join(run_dir, "state.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _load_state(run_dir: str) -> dict:
    path = os.path.join(run_dir, "state.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def run(
    product_name: str,
    product_offer: str,
    target_audience: str,
    pain_points: str,
    total_duration: int = 30,
    run_id: str = None,
) -> dict:
    """
    执行完整广告视频生成工作流

    Args:
        product_name:     产品名称
        product_offer:    产品功能/Offer
        target_audience:  目标受众描述
        pain_points:      核心痛点
        total_duration:   视频总时长（秒）
        run_id:           本次运行ID（留空自动生成），可传入已有ID实现断点续跑

    Returns:
        state dict，包含各节点输出
    """
    # ── 初始化运行目录 ──────────────────────────────────────────────────
    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(config.OUTPUT_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  AI 广告视频生成工作流 启动")
    print(f"  Run ID : {run_id}")
    print(f"  产品   : {product_name}")
    print(f"  时长   : {total_duration}s")
    print(f"{'='*60}\n")

    state = _load_state(run_dir)

    # ── Step 1: Story Maker ────────────────────────────────────────────
    if "story" not in state:
        result = story_maker.run(
            product_name=product_name,
            product_offer=product_offer,
            target_audience=target_audience,
            pain_points=pain_points,
        )
        state["story"] = result["story"]
        _save_state(run_dir, state)
        print(f"\n[Step 1 完成] 人物小传已生成（{len(state['story'])}字）\n")
    else:
        print("[Step 1 跳过] 已加载缓存的人物小传\n")

    story = state["story"]

    # ── Step 2/3 & Step 4：并行执行图像链路 + 脚本链路 ───────────────
    image_chain_done = "image_paths" in state
    script_chain_done = "scenes" in state

    def image_chain():
        """图像链路：特征提取 → 生图"""
        if image_chain_done:
            print("[图像链路 跳过] 已加载缓存图片")
            return

        # Step 2: Key Feature Extractor
        feat_result = key_feature_extractor.run(story)
        feature_prompt = feat_result["feature_prompt"]
        state["feature_prompt"] = feature_prompt
        _save_state(run_dir, state)
        print(f"\n[Step 2 完成] 人物特征提取完毕\n")

        # Step 3: Model Generator
        img_result = model_generator.run(feature_prompt, output_dir=run_dir)
        state["image_paths"] = img_result["image_paths"]
        state["image_urls"] = img_result["image_urls"]
        _save_state(run_dir, state)
        print(f"\n[Step 3 完成] 人物图片生成完毕\n")

    def script_chain():
        """脚本链路：生成口播脚本 + 分镜"""
        if script_chain_done:
            print("[脚本链路 跳过] 已加载缓存脚本")
            return

        # Step 4: Script Generator
        scr_result = script_generator.run(story, total_duration=total_duration)
        state["full_script"] = scr_result["full_script"]
        state["scenes"] = scr_result["scenes"]
        state["total_scenes"] = scr_result["total_scenes"]
        state["estimated_duration"] = scr_result["estimated_duration"]
        _save_state(run_dir, state)
        print(f"\n[Step 4 完成] 脚本生成完毕（{scr_result['total_scenes']} 段分镜）\n")

    print("[并行执行] 图像链路 + 脚本链路同步启动...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f_image = executor.submit(image_chain)
        f_script = executor.submit(script_chain)
        # 等待两条链路都完成，并捕获异常
        for future in concurrent.futures.as_completed([f_image, f_script]):
            exc = future.exception()
            if exc:
                raise exc

    # ── Step 5: Video Generator ────────────────────────────────────────
    if "video_paths" not in state:
        image_paths = [p for p in state.get("image_paths", []) if p and os.path.exists(p)]
        if not image_paths:
            raise RuntimeError("图片生成失败，无法继续生成视频。请检查 image_paths。")

        vid_result = video_generator.run(
            image_paths=image_paths,
            scenes=state["scenes"],
            output_dir=run_dir,
        )
        state["video_paths"] = vid_result["video_paths"]
        state["video_urls"] = vid_result.get("video_urls", [])
        state["failed_scenes"] = vid_result["failed_scenes"]
        _save_state(run_dir, state)
        print(f"\n[Step 5 完成] 视频片段生成完毕\n")
    else:
        print("[Step 5 跳过] 已加载缓存视频\n")

    # ── 完成汇总 ────────────────────────────────────────────────────────
    valid_videos = [p for p in state.get("video_paths", []) if p]
    print(f"\n{'='*60}")
    print(f"  工作流完成！")
    print(f"  输出目录  : {run_dir}")
    print(f"  人物图片  : {len(state.get('image_paths', []))} 张")
    print(f"  视频分镜  : {state.get('total_scenes', 0)} 段")
    print(f"  成功视频  : {len(valid_videos)} 段")
    if state.get("failed_scenes"):
        print(f"  失败分镜  : {state['failed_scenes']}")
    print(f"{'='*60}\n")

    state["run_id"] = run_id
    state["run_dir"] = run_dir
    return state
