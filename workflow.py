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
from nodes import story_maker, key_feature_extractor, model_generator, script_generator, voice_type_generator
from nodes import api_generator, cli_video_generator, model_card_generator, tts_generator, omni_video_generator


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
        """图像链路：特征提取 → [音色选择 + 生图（并行）]"""
        if image_chain_done:
            print("[图像链路 跳过] 已加载缓存图片")
            return

        # Step 2: Key Feature Extractor
        feat_result = key_feature_extractor.run(story)
        feature_prompt = feat_result["feature_prompt"]
        state["feature_prompt"] = feature_prompt
        _save_state(run_dir, state)
        print(f"\n[Step 2 完成] 人物特征提取完毕\n")

        # Step 2.5 & Step 3：音色选择 + 生图 并行
        def voice_type_chain():
            """Step 2.5：根据视觉特征 + 小传选择 TTS 音色"""
            if "voice_type" in state:
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
            """Step 3：生成人物图片"""
            img_result = model_generator.run(feature_prompt, output_dir=run_dir)
            state["image_paths"] = img_result["image_paths"]
            state["image_urls"] = img_result["image_urls"]
            _save_state(run_dir, state)
            print(f"\n[Step 3 完成] 人物图片生成完毕\n")

        print("[并行执行] 音色选择（Step 2.5）+ 生图（Step 3）同步启动...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f_vt    = executor.submit(voice_type_chain)
            f_model = executor.submit(model_gen_chain)
            for future in concurrent.futures.as_completed([f_vt, f_model]):
                exc = future.exception()
                if exc:
                    raise exc

    def script_chain():
        """脚本链路：生成口播脚本 + 分镜"""
        if script_chain_done:
            print("[脚本链路 跳过] 已加载缓存脚本")
            return

        # Step 4: Script Generator（不再负责音色选择）
        scr_result = script_generator.run(story, total_duration=total_duration)
        state["full_script"] = scr_result["full_script"]
        state["scenes"] = scr_result["scenes"]
        state["total_scenes"] = scr_result["total_scenes"]
        state["estimated_duration"] = scr_result["estimated_duration"]
        _save_state(run_dir, state)
        print(f"\n[Step 4 完成] 脚本生成完毕（{scr_result['total_scenes']} 段分镜）\n")

    print("[并行执行] 图像链路（特征提取→音色选择+生图）+ 脚本链路同步启动...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f_image = executor.submit(image_chain)
        f_script = executor.submit(script_chain)
        # 等待两条链路都完成，并捕获异常
        for future in concurrent.futures.as_completed([f_image, f_script]):
            exc = future.exception()
            if exc:
                raise exc

    # ── Step 5: Video Generator + Model Card Generator + TTS ────────────
    engine = config.VIDEO_ENGINE.lower()
    video_done = "video_paths" in state
    card_done  = "card_paths"  in state
    tts_done   = "audio_paths" in state

    def card_chain():
        """模卡图生成链路（所有引擎均并行执行）"""
        if card_done:
            print("[Step 5-B 跳过] 已加载缓存模卡图\n")
            return

        image_paths = [p for p in state.get("image_paths", []) if p and os.path.exists(p)]
        if not image_paths:
            print("[Step 5-B 跳过] 模特图片不存在，跳过模卡图生成")
            return

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
        print(f"\n[Step 5-B 完成] 模卡图生成完毕\n")

    if engine == "omni":
        # ── Omni 模式：TTS → Omni 视频合成（串行），模卡图并行 ──────────
        print("[Step 5] 引擎: OmniHuman1.5（TTS→视频串行，模卡图并行启动）")

        # Step 5-C：TTS 生成（串行，omni 视频合成依赖其结果）
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
            print(f"\n[Step 5-C 完成] TTS 音频生成完毕（{success_count}/{len(state['scenes'])} 段成功）\n")

        # Step 5-A：Omni 视频合成 + 模卡图并行
        def omni_video_chain():
            """OmniHuman 视频生成链路"""
            if video_done:
                print("[Step 5-A 跳过] 已加载缓存视频\n")
                return

            image_urls = [u for u in state.get("image_urls", []) if u]
            if not image_urls:
                raise RuntimeError(
                    "Omni 模式需要图片 URL（image_urls），当前为空。"
                    "请确认 model_generator 已返回 image_urls 并存入 state。"
                )

            audio_paths = state.get("audio_paths", [])

            print(f"[Step 5-A] 使用视频引擎：OmniHuman1.5")
            vid_result = omni_video_generator.run(
                image_urls=image_urls,
                audio_paths=audio_paths,
                scenes=state["scenes"],
                output_dir=run_dir,
            )
            state["video_paths"]  = vid_result["video_paths"]
            state["video_urls"]   = vid_result.get("video_urls", [])
            state["failed_scenes"] = vid_result["failed_scenes"]
            _save_state(run_dir, state)
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
        # ── 非 Omni 模式：视频 + 模卡图 + TTS 三路并行 ─────────────────

        def video_chain():
            """视频生成链路（api / cli）"""
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
            print(f"\n[Step 5-A 完成] 视频片段生成完毕\n")

        def tts_chain():
            """TTS 音频生成链路（非 omni 模式下并行执行）"""
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

    # ── 完成汇总 ────────────────────────────────────────────────────────
    valid_videos = [p for p in state.get("video_paths", []) if p]
    valid_cards  = [p for p in state.get("card_paths",  []) if p]
    valid_audios = [p for p in state.get("audio_paths", []) if p]
    print(f"\n{'='*60}")
    print(f"  工作流完成！")
    print(f"  输出目录  : {run_dir}")
    print(f"  人物图片  : {len(state.get('image_paths', []))} 张")
    print(f"  视频分镜  : {state.get('total_scenes', 0)} 段")
    print(f"  成功视频  : {len(valid_videos)} 段")
    print(f"  TTS 音频  : {len(valid_audios)} 段")
    print(f"  模卡图    : {len(valid_cards)} 张")
    if state.get("failed_scenes"):
        print(f"  失败分镜  : {state['failed_scenes']}")
    if state.get("tts_failed_indices"):
        print(f"  失败TTS   : {state['tts_failed_indices']}")
    if state.get("card_failed_indices"):
        print(f"  失败模卡  : {state['card_failed_indices']}")
    print(f"{'='*60}\n")

    state["run_id"] = run_id
    state["run_dir"] = run_dir
    return state
