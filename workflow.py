"""
主工作流编排（交互式版本）
输入产品信息 → 并行执行图像链路 + 脚本链路 → 【用户确认图片】→ 【用户确认脚本 + 选择首帧】→ 生成视频片段

交互点说明：
  checkpoint_1 - 生图完成后：用户查看图片，可重新生成（支持修改提示词）
  checkpoint_2 - 视频生成前：用户审阅脚本，可微调各分镜台词
  checkpoint_3 - Omni视频前：用户为每段分镜选择首帧图片

非 omni 引擎：仅包含 checkpoint_1 / checkpoint_2，视频生成时自动按 image_paths 顺序分配。
"""

import os
import json
import time
import concurrent.futures
from datetime import datetime

import config
import interactive
from nodes import story_maker, key_feature_extractor, model_generator, script_generator, voice_type_generator
from nodes import api_generator, cli_video_generator, model_card_generator, tts_generator, omni_video_generator


# ── 状态持久化 ─────────────────────────────────────────────────────────────────

def _save_state(run_dir: str, state: dict):
    """保存工作流中间状态，方便断点续跑"""
    path = os.path.join(run_dir, "state.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _load_state(run_dir: str) -> dict:
    path = os.path.join(run_dir, "state.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {}


def _valid_paths(paths: list) -> list:
    return [p for p in paths or [] if p and os.path.exists(p)]


def _raise_if_failed(result: dict, failed_key: str, label: str):
    failed = result.get(failed_key, [])
    if failed:
        raise RuntimeError(f"{label} 失败，失败索引/分镜: {failed}")


# ── 子链路：并行图像链路（特征提取 → 音色+生图） ──────────────────────────────

def _run_image_chain(state: dict, run_dir: str):
    """
    图像链路：Step 2 特征提取 → Step 2.5 音色选择 & Step 3 生图（并行）
    直接修改 state 并持久化。
    """
    story = state["story"]

    # Step 2: Key Feature Extractor
    if "feature_prompt" not in state:
        feat_result = key_feature_extractor.run(story)
        state["feature_prompt"] = feat_result["feature_prompt"]
        _save_state(run_dir, state)
        print(f"\n[Step 2 完成] 人物特征提取完毕\n")
    else:
        print("[Step 2 跳过] 已加载缓存特征提示词\n")

    feature_prompt = state["feature_prompt"]

    # Step 2.5 & Step 3：音色选择 + 生图 并行
    voice_done = "voice_type" in state
    image_done = "image_paths" in state

    def voice_type_chain():
        if voice_done:
            print("[Step 2.5 跳过] 已加载缓存音色\n")
            return
        vt_result = voice_type_generator.run(
            feature_prompt=feature_prompt,
            story=story,
        )
        state["voice_type"] = vt_result["voice_type"]
        _save_state(run_dir, state)
        print(f"\n[Step 2.5 完成] 音色选择完毕：{vt_result['voice_type']}\n")

    def model_gen_chain():
        if image_done:
            print("[Step 3 跳过] 已加载缓存图片\n")
            return
        img_result = model_generator.run(feature_prompt, output_dir=run_dir)
        state["image_paths"] = img_result["image_paths"]
        state["image_urls"] = img_result["image_urls"]
        _save_state(run_dir, state)
        print(f"\n[Step 3 完成] 人物图片生成完毕\n")

    if not voice_done or not image_done:
        print("[并行执行] 音色选择（Step 2.5）+ 生图（Step 3）同步启动...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f_vt    = executor.submit(voice_type_chain)
            f_model = executor.submit(model_gen_chain)
            for future in concurrent.futures.as_completed([f_vt, f_model]):
                exc = future.exception()
                if exc:
                    raise exc


# ── 子链路：脚本链路 ───────────────────────────────────────────────────────────

def _run_script_chain(state: dict, run_dir: str, total_duration: int):
    """脚本链路：Step 4 生成口播脚本 + 分镜"""
    if "scenes" in state:
        print("[脚本链路 跳过] 已加载缓存脚本")
        return

    scr_result = script_generator.run(state["story"], total_duration=total_duration)
    state["full_script"] = scr_result["full_script"]
    state["scenes"] = scr_result["scenes"]
    state["total_scenes"] = scr_result["total_scenes"]
    state["estimated_duration"] = scr_result["estimated_duration"]
    _save_state(run_dir, state)
    print(f"\n[Step 4 完成] 脚本生成完毕（{scr_result['total_scenes']} 段分镜）\n")


# ══════════════════════════════════════════════════════════════════════════════
#  主流程入口
# ══════════════════════════════════════════════════════════════════════════════

def run(
    product_name: str,
    product_offer: str,
    target_audience: str,
    pain_points: str,
    total_duration: int = 30,
    run_id: str = None,
    io_backend: interactive.IOBackend = None,
) -> dict:
    """
    执行完整广告视频生成工作流（交互式版本）

    Args:
        product_name:     产品名称
        product_offer:    产品功能/Offer
        target_audience:  目标受众描述
        pain_points:      核心痛点
        total_duration:   视频总时长（秒）
        run_id:           本次运行ID（留空自动生成），可传入已有ID实现断点续跑
        io_backend:       I/O 后端实例，None 则使用全局默认（CLIBackend）
                          可传入自定义 IOBackend 实现

    Returns:
        state dict，包含各节点输出
    """
    # ── 初始化运行目录 ─────────────────────────────────────────────────────────
    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(config.OUTPUT_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    io = interactive._get_backend(io_backend)

    io.display(f"\n{'='*60}")
    io.display(f"  AI 广告视频生成工作流 启动（交互式模式）")
    io.display(f"  Run ID : {run_id}")
    io.display(f"  产品   : {product_name}")
    io.display(f"  时长   : {total_duration}s")
    io.display(f"{'='*60}\n")

    state = _load_state(run_dir)
    state.setdefault("_request", {
        "run_id": run_id,
        "product_name": product_name,
        "product_offer": product_offer,
        "target_audience": target_audience,
        "pain_points": pain_points,
        "total_duration": total_duration,
    })
    _save_state(run_dir, state)

    # ── Step 1: Story Maker ────────────────────────────────────────────────────
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

    # ── Step 2/2.5/3 & Step 4：并行执行图像链路 + 脚本链路 ────────────────────
    image_chain_done = "image_paths" in state
    script_chain_done = "scenes" in state

    if not image_chain_done or not script_chain_done:
        print("[并行执行] 图像链路（特征提取→音色选择+生图）+ 脚本链路同步启动...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f_image = executor.submit(_run_image_chain, state, run_dir)
            f_script = executor.submit(_run_script_chain, state, run_dir, total_duration)
            for future in concurrent.futures.as_completed([f_image, f_script]):
                exc = future.exception()
                if exc:
                    raise exc
    else:
        print("[Step 2-4 跳过] 已加载缓存的图片与脚本\n")

    # ══════════════════════════════════════════════════════════════════════════
    #  CHECKPOINT 1：生图确认
    #  用户查看图片，决定是否满意。不满意可修改提示词后重新生成（循环直到满意）
    # ══════════════════════════════════════════════════════════════════════════
    if not state.get("_image_confirmed", False):
        while True:
            confirm_result = interactive.confirm_images(
                image_paths=state.get("image_paths", []),
                feature_prompt=state.get("feature_prompt", ""),
                run_dir=run_dir,
                backend=io_backend,
            )

            if confirm_result["action"] == "next":
                state["_image_confirmed"] = True
                _save_state(run_dir, state)
                io.display("\n[Checkpoint 1 ✓] 图片已确认，进入下一步\n")
                break

            # 重新生成
            new_prompt = confirm_result["new_prompt"]
            io.display(f"\n[重新生图] 使用提示词：{new_prompt[:80]}...")
            state["feature_prompt"] = new_prompt

            # 清除旧图片（保留 voice_type，不需要重新选音色）
            state.pop("image_paths", None)
            state.pop("image_urls", None)
            _save_state(run_dir, state)

            img_result = model_generator.run(new_prompt, output_dir=run_dir)
            state["image_paths"] = img_result["image_paths"]
            state["image_urls"] = img_result["image_urls"]
            _save_state(run_dir, state)
            io.display(f"\n[重新生图完成] 共 {len(state['image_paths'])} 张图片\n")
    else:
        print("[Checkpoint 1 跳过] 图片确认已记录\n")

    # ══════════════════════════════════════════════════════════════════════════
    #  CHECKPOINT 2：脚本确认与微调
    #  仅在进入视频生成前（Step 5）触发一次
    # ══════════════════════════════════════════════════════════════════════════
    if not state.get("_script_confirmed", False):
        script_result = interactive.confirm_script(
            full_script=state.get("full_script", ""),
            scenes=state.get("scenes", []),
            backend=io_backend,
        )
        state["full_script"] = script_result["full_script"]
        state["scenes"] = script_result["scenes"]
        state["total_scenes"] = len(script_result["scenes"])
        state["_script_confirmed"] = True
        _save_state(run_dir, state)
        io.display("\n[Checkpoint 2 ✓] 脚本已确认，进入视频生成\n")
    else:
        print("[Checkpoint 2 跳过] 脚本确认已记录\n")

    # ── Step 5: 视频生成（+ 模卡图 + TTS） ────────────────────────────────────
    engine = config.VIDEO_ENGINE.lower()
    video_done = "video_paths" in state
    card_done  = "card_paths"  in state
    tts_done   = bool(_valid_paths(state.get("audio_paths", [])))

    def card_chain():
        """模卡图生成链路（所有引擎均并行执行）"""
        if card_done:
            print("[Step 5-B 跳过] 已加载缓存模卡图\n")
            return

        image_paths = [p for p in state.get("image_paths", []) if p and os.path.exists(p)]
        if not image_paths:
            raise RuntimeError("模特图片不存在，无法继续生成模卡图。请检查 image_paths。")

        model_image_path = image_paths[0]
        silhouette_paths = config.MODELCARD_SILHOUETTE_PATHS

        print(f"[Step 5-B] 开始生成模特模卡图（3张姿势）...")
        card_result = model_card_generator.run(
            model_image_path=model_image_path,
            silhouette_paths=silhouette_paths,
            output_dir=run_dir,
        )
        state["card_paths"] = card_result["card_paths"]
        state["card_failed_indices"] = card_result["failed_indices"]
        _save_state(run_dir, state)
        _raise_if_failed(card_result, "failed_indices", "模卡图生成")
        print(f"\n[Step 5-B 完成] 模卡图生成完毕\n")

    if engine == "omni":
        # ── Omni 模式：TTS → Checkpoint 3 → Omni 视频合成（串行），模卡图并行 ──

        print("[Step 5] 引擎: OmniHuman1.5（TTS→视频串行，模卡图并行启动）")

        # Step 5-C：TTS 生成
        if tts_done:
            print("[Step 5-C 跳过] 已加载缓存音频\n")
        else:
            voice_type = state.get("voice_type", config.TTS_DEFAULT_VOICE)
            print(f"[Step 5-C] 开始生成 TTS 音频（音色：{voice_type}）...")
            tts_result = tts_generator.run(
                scenes=state["scenes"],
                voice_type=voice_type,
                output_dir=run_dir,
            )
            state["audio_paths"]        = tts_result["audio_paths"]
            state["tts_failed_indices"] = tts_result["failed_indices"]
            _save_state(run_dir, state)
            success_count = sum(1 for p in tts_result["audio_paths"] if p)
            _raise_if_failed(tts_result, "failed_indices", "TTS 音频生成")
            print(f"\n[Step 5-C 完成] TTS 音频生成完毕（{success_count}/{len(state['scenes'])} 段成功）\n")

        # ══════════════════════════════════════════════════════════════════════
        #  CHECKPOINT 3（Omni 专用）：每段分镜首帧图片选择
        #  用户为每段分镜独立指定首帧人物图片
        #  CLI 模式：输入序号/路径/URL；自定义 I/O 可替换为拖拽/点击选择
        # ══════════════════════════════════════════════════════════════════════
        if not state.get("_scene_images_confirmed", False):
            scene_image_selections = interactive.select_scene_images(
                scenes=state["scenes"],
                available_image_paths=state.get("image_paths", []),
                available_image_urls=state.get("image_urls", []),
                backend=io_backend,
            )
            # 将选择结果持久化（列表顺序与 scenes 对应）
            state["scene_image_selections"] = scene_image_selections
            state["_scene_images_confirmed"] = True
            _save_state(run_dir, state)
            io.display("\n[Checkpoint 3 ✓] 首帧图片分配已确认，开始生成视频\n")
        else:
            scene_image_selections = state.get("scene_image_selections", [])
            # 断点续跑保护：检查已保存的选择中是否存在空 URL，若有则重新触发选择
            missing_url = any(not sel.get("image_url") for sel in scene_image_selections)
            if missing_url:
                io.display(
                    "\n[Checkpoint 3 ⚠] 检测到已保存的首帧图片分配中存在缺失的公网 URL，"
                    "需重新确认。\n"
                )
                state.pop("_scene_images_confirmed", None)
                state.pop("scene_image_selections", None)
                _save_state(run_dir, state)
                scene_image_selections = interactive.select_scene_images(
                    scenes=state["scenes"],
                    available_image_paths=state.get("image_paths", []),
                    available_image_urls=state.get("image_urls", []),
                    backend=io_backend,
                )
                state["scene_image_selections"] = scene_image_selections
                state["_scene_images_confirmed"] = True
                _save_state(run_dir, state)
                io.display("\n[Checkpoint 3 ✓] 首帧图片分配已重新确认，开始生成视频\n")
            else:
                print("[Checkpoint 3 跳过] 首帧图片分配已记录\n")

        # 从 scene_image_selections 中提取有序的 image_url 列表传给 omni
        ordered_image_urls = [
            sel.get("image_url") or ""
            for sel in scene_image_selections
        ]

        # Step 5-A：Omni 视频合成 + 模卡图并行
        def omni_video_chain():
            if video_done:
                print("[Step 5-A 跳过] 已加载缓存视频\n")
                return

            if not ordered_image_urls or all(not u for u in ordered_image_urls):
                raise RuntimeError(
                    "Omni 模式需要图片公网 URL（image_urls），当前全部为空。\n"
                    "请确认已在 Checkpoint 3 中为每段分镜选择了包含公网 URL 的图片。"
                )

            audio_paths = state.get("audio_paths", [])

            print(f"[Step 5-A] 使用视频引擎：OmniHuman1.5")
            vid_result = omni_video_generator.run(
                image_urls=ordered_image_urls,
                audio_paths=audio_paths,
                scenes=state["scenes"],
                output_dir=run_dir,
            )
            state["video_paths"]   = vid_result["video_paths"]
            state["video_urls"]    = vid_result.get("video_urls", [])
            state["failed_scenes"] = vid_result["failed_scenes"]
            _save_state(run_dir, state)
            _raise_if_failed(vid_result, "failed_scenes", "Omni 视频生成")
            print(f"\n[Step 5-A 完成] Omni 视频片段生成完毕\n")

        print("[并行执行] OmniHuman 视频生成 + 模卡图生成同步启动...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f_video = executor.submit(omni_video_chain)
            f_card  = executor.submit(card_chain)
            for future in concurrent.futures.as_completed([f_video, f_card]):
                exc = future.exception()
                if exc:
                    raise exc

    else:
        # ── 非 Omni 模式：视频 + 模卡图 + TTS 三路并行 ────────────────────────

        def video_chain():
            if video_done:
                print("[Step 5-A 跳过] 已加载缓存视频\n")
                return

            image_paths = [p for p in state.get("image_paths", []) if p and os.path.exists(p)]
            if not image_paths:
                raise RuntimeError("图片生成失败，无法继续生成视频。请检查 image_paths。")

            if engine == "cli":
                print(f"[Step 5-A] 使用视频引擎：CLI（dreamina 个人账号）")
                vid_result = cli_video_generator.run(
                    image_paths=image_paths,
                    scenes=state["scenes"],
                    output_dir=run_dir,
                )
            else:
                print(f"[Step 5-A] 使用视频引擎：API（火山引擎首尾帧）")
                vid_result = api_generator.run(
                    image_paths=image_paths,
                    scenes=state["scenes"],
                    output_dir=run_dir,
                )

            state["video_paths"]   = vid_result["video_paths"]
            state["video_urls"]    = vid_result.get("video_urls", [])
            state["failed_scenes"] = vid_result["failed_scenes"]
            _save_state(run_dir, state)
            _raise_if_failed(vid_result, "failed_scenes", "视频生成")
            print(f"\n[Step 5-A 完成] 视频片段生成完毕\n")

        def tts_chain():
            if tts_done:
                print("[Step 5-C 跳过] 已加载缓存音频\n")
                return

            voice_type = state.get("voice_type", config.TTS_DEFAULT_VOICE)
            print(f"[Step 5-C] 开始生成 TTS 音频（音色：{voice_type}）...")
            tts_result = tts_generator.run(
                scenes=state["scenes"],
                voice_type=voice_type,
                output_dir=run_dir,
            )
            state["audio_paths"]        = tts_result["audio_paths"]
            state["tts_failed_indices"] = tts_result["failed_indices"]
            _save_state(run_dir, state)
            success_count = sum(1 for p in tts_result["audio_paths"] if p)
            _raise_if_failed(tts_result, "failed_indices", "TTS 音频生成")
            print(f"\n[Step 5-C 完成] TTS 音频生成完毕（{success_count}/{len(state['scenes'])} 段成功）\n")

        print("[并行执行] 视频生成 + 模卡图生成 + TTS 音频同步启动...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            f_video = executor.submit(video_chain)
            f_card  = executor.submit(card_chain)
            f_tts   = executor.submit(tts_chain)
            for future in concurrent.futures.as_completed([f_video, f_card, f_tts]):
                exc = future.exception()
                if exc:
                    raise exc

    # ── 完成汇总 ───────────────────────────────────────────────────────────────
    valid_videos = [p for p in state.get("video_paths", []) if p]
    valid_cards  = [p for p in state.get("card_paths",  []) if p]
    valid_audios = [p for p in state.get("audio_paths", []) if p]

    io.display(f"\n{'='*60}")
    io.display(f"  工作流完成！")
    io.display(f"  输出目录  : {run_dir}")
    io.display(f"  人物图片  : {len(state.get('image_paths', []))} 张")
    io.display(f"  视频分镜  : {state.get('total_scenes', 0)} 段")
    io.display(f"  成功视频  : {len(valid_videos)} 段")
    io.display(f"  TTS 音频  : {len(valid_audios)} 段")
    io.display(f"  模卡图    : {len(valid_cards)} 张")
    if state.get("failed_scenes"):
        io.display(f"  失败分镜  : {state['failed_scenes']}")
    if state.get("tts_failed_indices"):
        io.display(f"  失败TTS   : {state['tts_failed_indices']}")
    if state.get("card_failed_indices"):
        io.display(f"  失败模卡  : {state['card_failed_indices']}")
    io.display(f"{'='*60}\n")

    state["run_id"]  = run_id
    state["run_dir"] = run_dir
    return state
