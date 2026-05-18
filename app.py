"""
AI 广告视频生成工作流 - 图形界面
运行方式：python app.py
设计风格：仿照设计稿（深色顶栏 + 白色侧边栏 + 蓝色主题）
"""

import os
import sys
import json
import threading
import queue
import time
import traceback

os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"
os.environ["no_proxy"] = "localhost,127.0.0.1,::1"

import gradio as gr
import config
import prompts_config
import interactive
import workflow


# ══════════════════════════════════════════════════════════════
#  后端辅助函数：将 UI 数据写入 config / prompts_config 模块
# ══════════════════════════════════════════════════════════════

def apply_api_config(
    qwen_key, qwen_url, qwen_model,
    jimeng_key, jimeng_secret,
    tts_app_id, tts_token, tts_cluster,
    tos_region, tos_bucket, tos_endpoint,
    output_dir,
) -> str:
    config.QWEN_API_KEY      = qwen_key.strip()
    config.QWEN_BASE_URL     = qwen_url.strip()
    config.QWEN_MODEL        = qwen_model.strip()
    config.JIMENG_API_KEY    = jimeng_key.strip()
    config.JIMENG_API_SECRET = jimeng_secret.strip()
    config.TTS_APP_ID        = tts_app_id.strip()
    config.TTS_ACCESS_TOKEN  = tts_token.strip()
    config.TTS_CLUSTER       = tts_cluster.strip()
    config.TOS_REGION        = tos_region.strip()
    config.TOS_BUCKET        = tos_bucket.strip()
    config.TOS_ENDPOINT      = tos_endpoint.strip()
    config.OUTPUT_DIR        = output_dir.strip()
    return "API 配置已保存（本次运行生效）"


def apply_params(
    scene_min, scene_max,
    image_width, image_height, image_scale, image_steps,
    video_width, video_height,
    omni_resolution, omni_fast,
    image_count,
) -> str:
    config.SCENE_MIN_DURATION     = int(scene_min)
    config.SCENE_MAX_DURATION     = int(scene_max)
    config.JIMENG_IMAGE_WIDTH     = int(image_width)
    config.JIMENG_IMAGE_HEIGHT    = int(image_height)
    config.JIMENG_IMAGE_SCALE     = float(image_scale)
    config.JIMENG_IMAGE_STEPS     = int(image_steps)
    config.JIMENG_VIDEO_WIDTH     = int(video_width)
    config.JIMENG_VIDEO_HEIGHT    = int(video_height)
    config.OMNI_OUTPUT_RESOLUTION = int(omni_resolution)
    config.OMNI_FAST_MODE         = bool(omni_fast)
    config.IMAGE_COUNT            = int(image_count)
    return "参数已保存（本次运行生效）"


def apply_prompts(
    story_sys, story_user,
    feat_sys, feat_user,
    voice_sys, voice_user,
    script_sys, script_user,
) -> str:
    prompts_config.STORY_MAKER_SYSTEM      = story_sys
    prompts_config.STORY_MAKER_USER        = story_user
    prompts_config.KEY_FEATURE_SYSTEM      = feat_sys
    prompts_config.KEY_FEATURE_USER        = feat_user
    prompts_config.VOICE_TYPE_SYSTEM       = voice_sys
    prompts_config.VOICE_TYPE_USER         = voice_user
    prompts_config.SCRIPT_GENERATOR_SYSTEM = script_sys
    prompts_config.SCRIPT_GENERATOR_USER   = script_user

    import nodes.story_maker as sm
    import nodes.key_feature_extractor as kf
    import nodes.voice_type_generator as vt
    import nodes.script_generator as sg
    sm.SYSTEM_PROMPT        = story_sys
    sm.USER_PROMPT_TEMPLATE = story_user
    kf.SYSTEM_PROMPT        = feat_sys
    kf.USER_PROMPT_TEMPLATE = feat_user
    vt.SYSTEM_PROMPT        = voice_sys
    vt.USER_PROMPT_TEMPLATE = voice_user
    sg.SYSTEM_PROMPT        = script_sys
    sg.USER_PROMPT_TEMPLATE = script_user
    return "提示词已更新（本次运行生效）"


def get_current_config() -> dict:
    return {
        "qwen_key":       config.QWEN_API_KEY,
        "qwen_url":       config.QWEN_BASE_URL,
        "qwen_model":     config.QWEN_MODEL,
        "jimeng_key":     config.JIMENG_API_KEY,
        "jimeng_secret":  config.JIMENG_API_SECRET,
        "tts_app_id":     config.TTS_APP_ID,
        "tts_token":      config.TTS_ACCESS_TOKEN,
        "tts_cluster":    config.TTS_CLUSTER,
        "tos_region":     config.TOS_REGION,
        "tos_bucket":     config.TOS_BUCKET,
        "tos_endpoint":   config.TOS_ENDPOINT,
        "output_dir":     config.OUTPUT_DIR,
        "scene_min":      config.SCENE_MIN_DURATION,
        "scene_max":      config.SCENE_MAX_DURATION,
        "image_width":    config.JIMENG_IMAGE_WIDTH,
        "image_height":   config.JIMENG_IMAGE_HEIGHT,
        "image_scale":    config.JIMENG_IMAGE_SCALE,
        "image_steps":    config.JIMENG_IMAGE_STEPS,
        "video_width":    config.JIMENG_VIDEO_WIDTH,
        "video_height":   config.JIMENG_VIDEO_HEIGHT,
        "omni_resolution":config.OMNI_OUTPUT_RESOLUTION,
        "omni_fast":      config.OMNI_FAST_MODE,
        "image_count":    config.IMAGE_COUNT,
        "video_engine":   config.VIDEO_ENGINE,
        "story_sys":      prompts_config.STORY_MAKER_SYSTEM,
        "story_user":     prompts_config.STORY_MAKER_USER,
        "feat_sys":       prompts_config.KEY_FEATURE_SYSTEM,
        "feat_user":      prompts_config.KEY_FEATURE_USER,
        "voice_sys":      prompts_config.VOICE_TYPE_SYSTEM,
        "voice_user":     prompts_config.VOICE_TYPE_USER,
        "script_sys":     prompts_config.SCRIPT_GENERATOR_SYSTEM,
        "script_user":    prompts_config.SCRIPT_GENERATOR_USER,
    }


# ══════════════════════════════════════════════════════════════
#  GradioBackend — 将 interactive 模块的输入/输出路由到 Gradio 队列
# ══════════════════════════════════════════════════════════════

class GradioBackend(interactive.IOBackend):
    """
    将 interactive 模块的三类操作（display / prompt / confirm）
    通过线程安全的队列传递给 Gradio UI 线程。

    协议：
      _out_q  : workflow 线程 → UI（推送消息 / 交互请求）
      _in_q   : UI → workflow 线程（用户回复）

    消息格式（_out_q 推送）：
      {"type": "log",     "text": str}
      {"type": "confirm", "text": str}        # 等待 bool 回复
      {"type": "prompt",  "text": str, "default": str}  # 等待 str 回复
    """

    def __init__(self):
        self._out_q: queue.Queue = queue.Queue()
        self._in_q:  queue.Queue = queue.Queue()

    # ── IOBackend 接口 ─────────────────────────────────────────
    def display(self, message: str) -> None:
        self._out_q.put({"type": "log", "text": message})

    def prompt(self, message: str, default: str = "") -> str:
        self._out_q.put({"type": "prompt", "text": message, "default": default})
        return self._in_q.get(block=True)

    def confirm(self, message: str) -> bool:
        self._out_q.put({"type": "confirm", "text": message})
        return self._in_q.get(block=True)

    # ── UI 调用的辅助方法 ─────────────────────────────────────
    def reply(self, value):
        """UI 线程将用户回复放入队列，解除 workflow 线程的阻塞。"""
        self._in_q.put(value)

    def drain_logs(self) -> list[str]:
        """非阻塞地取出所有待显示日志，返回字符串列表。"""
        logs = []
        while True:
            try:
                item = self._out_q.get_nowait()
                logs.append(item)
            except queue.Empty:
                break
        return logs

    def peek_request(self):
        """非阻塞地查看是否有等待用户回复的请求（不取出）。"""
        try:
            item = self._out_q.get_nowait()
            return item
        except queue.Empty:
            return None


# ══════════════════════════════════════════════════════════════
#  全局运行状态
# ══════════════════════════════════════════════════════════════

_backend: GradioBackend | None = None
_workflow_thread: threading.Thread | None = None
_workflow_result: dict | None = None
_workflow_error: str | None = None
_workflow_running: bool = False

# 当前挂起的交互请求 {"type": "confirm"/"prompt", "text": str, "default": str}
_pending_request: dict | None = None
_log_lines: list[str] = []


def _run_workflow_thread(kwargs: dict):
    """在后台线程中运行 workflow.run()，异常写入全局变量。"""
    global _workflow_result, _workflow_error, _workflow_running
    try:
        _workflow_result = workflow.run(**kwargs, io_backend=_backend)
    except Exception as e:
        _workflow_error = traceback.format_exc()
        _backend.display(f"\n[ERROR] 工作流异常：{e}")
    finally:
        _workflow_running = False
        _backend.display("\n[DONE] 工作流线程已结束")


# ══════════════════════════════════════════════════════════════
#  辅助：从 OUTPUT_DIR 扫描已有 Run ID
# ══════════════════════════════════════════════════════════════

def _list_run_ids() -> list[str]:
    out_dir = config.OUTPUT_DIR
    if not os.path.isdir(out_dir):
        return []
    entries = [
        d for d in os.listdir(out_dir)
        if os.path.isdir(os.path.join(out_dir, d))
        and os.path.exists(os.path.join(out_dir, d, "state.json"))
    ]
    return sorted(entries, reverse=True)[:20]


def _load_run_state(run_id: str) -> dict:
    path = os.path.join(config.OUTPUT_DIR, run_id, "state.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ══════════════════════════════════════════════════════════════
#  CSS — 完全还原设计稿风格
# ══════════════════════════════════════════════════════════════

CUSTOM_CSS = """
/* ── 全局字体 & 背景 ── */
body, .gradio-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    background-color: #f8fafc !important;
}

/* ── 左侧边栏（Logo区 + 导航Tab） ── */
/* 隐藏顶部header（已移入侧边栏） */
#app-header { display: none !important; }

/* 整体容器使用flex横向布局 */
.gradio-container > .main > .wrap,
.gradio-container .tabs {
    display: flex !important;
    flex-direction: row !important;
    min-height: 100vh !important;
}

/* Tab导航栏 = 左侧边栏 */
.gradio-tabs .tab-nav {
    background: #1e293b !important;
    border-right: none !important;
    border-bottom: none !important;
    flex-direction: column !important;
    width: 200px !important;
    min-width: 200px !important;
    min-height: 100vh !important;
    padding: 0 !important;
    position: sticky !important;
    top: 0 !important;
    align-self: flex-start !important;
    height: 100vh !important;
    overflow: hidden !important;
    flex-shrink: 0 !important;
    z-index: 100 !important;
}

/* 侧边栏顶部 Logo 区 */
.gradio-tabs .tab-nav::before {
    content: "🥩  牛排工作室";
    display: block !important;
    padding: 20px 16px 6px 16px !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    letter-spacing: 0.01em !important;
    white-space: nowrap !important;
}
.gradio-tabs .tab-nav::after {
    content: "导航菜单";
    display: block !important;
    padding: 0 16px 12px 16px !important;
    font-size: 10px !important;
    color: #64748b !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    border-bottom: 1px solid #334155 !important;
    margin-bottom: 8px !important;
}

/* 导航按钮 */
.gradio-tabs .tab-nav button {
    width: 100% !important;
    text-align: left !important;
    padding: 10px 20px !important;
    border-radius: 0 !important;
    border: none !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #94a3b8 !important;
    background: transparent !important;
    border-left: 3px solid transparent !important;
    transition: all 0.15s !important;
}
.gradio-tabs .tab-nav button:hover {
    background: rgba(255,255,255,0.06) !important;
    color: #e2e8f0 !important;
}
.gradio-tabs .tab-nav button.selected {
    background: rgba(51,112,255,0.15) !important;
    color: #60a5fa !important;
    border-left-color: #3370ff !important;
}

/* 内容区 */
.gradio-tabs .tabitem {
    padding: 24px !important;
    background: #f8fafc !important;
    flex: 1 !important;
    min-width: 0 !important;
}

/* ── 内容卡片 ── */
.card {
    background: white;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    padding: 24px;
    margin-bottom: 16px;
}
.card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    font-size: 14px;
    color: #1e293b;
    padding-bottom: 16px;
    border-bottom: 1px solid #f1f5f9;
    margin-bottom: 16px;
}

/* ── 主按钮 ── */
.btn-primary {
    background: #3370ff !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 28px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    box-shadow: 0 4px 14px rgba(51,112,255,0.3) !important;
    transition: all 0.15s !important;
}
.btn-primary:hover {
    background: #2a5cd9 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(51,112,255,0.4) !important;
}
.btn-secondary {
    background: #f1f5f9 !important;
    color: #475569 !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    padding: 10px 20px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    transition: all 0.15s !important;
}
.btn-secondary:hover {
    background: #e2e8f0 !important;
}
.btn-danger {
    background: #fee2e2 !important;
    color: #dc2626 !important;
    border: 1px solid #fecaca !important;
    border-radius: 8px !important;
    padding: 10px 20px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
}
.btn-success {
    background: #dcfce7 !important;
    color: #16a34a !important;
    border: 1px solid #bbf7d0 !important;
    border-radius: 8px !important;
    padding: 10px 20px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
}

/* ── 大运行按钮 ── */
.btn-run {
    background: linear-gradient(135deg, #3370ff, #6366f1) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 18px !important;
    font-weight: 700 !important;
    font-size: 16px !important;
    width: 100% !important;
    box-shadow: 0 8px 24px rgba(51,112,255,0.35) !important;
    transition: all 0.2s !important;
}
.btn-run:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 30px rgba(51,112,255,0.45) !important;
}

/* ── 日志终端 ── */
.log-terminal {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 10px !important;
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-size: 11px !important;
    color: #4ade80 !important;
    line-height: 1.7 !important;
}
.log-terminal textarea {
    background: transparent !important;
    color: #4ade80 !important;
    font-family: inherit !important;
    font-size: inherit !important;
}

/* ── 引擎选择卡片 ── */
.engine-card {
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px;
    text-align: center;
    cursor: pointer;
    transition: all 0.15s;
    background: white;
}
.engine-card.selected {
    border-color: #3370ff;
    background: #eff6ff;
}
.engine-card:hover {
    border-color: #93c5fd;
}

/* ── Checkpoint 交互区 ── */
.checkpoint-box {
    background: #fff7ed;
    border: 2px solid #fed7aa;
    border-radius: 12px;
    padding: 20px;
    margin-top: 16px;
}
.checkpoint-box.cp-image {
    background: #eff6ff;
    border-color: #bfdbfe;
}
.checkpoint-box.cp-script {
    background: #f0fdf4;
    border-color: #bbf7d0;
}
.checkpoint-box.cp-omni {
    background: #faf5ff;
    border-color: #e9d5ff;
}

/* ── 表单输入统一样式 ── */
.gradio-container input[type=text],
.gradio-container input[type=password],
.gradio-container input[type=number],
.gradio-container textarea,
.gradio-container select {
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
.gradio-container input:focus,
.gradio-container textarea:focus {
    border-color: #3370ff !important;
    box-shadow: 0 0 0 3px rgba(51,112,255,0.12) !important;
    outline: none !important;
}

/* ── 状态徽章 ── */
.badge-running {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #dbeafe;
    color: #1d4ed8;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
}
.badge-idle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #f1f5f9;
    color: #64748b;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 500;
}
.badge-done {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #dcfce7;
    color: #15803d;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
}

/* ── 侧边栏底部状态 ── */
#sidebar-status {
    background: rgba(255,255,255,0.05);
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 11px;
    margin-top: auto;
    color: #94a3b8;
}

/* ── 分镜列表 ── */
.scene-row {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px;
    background: white;
    margin-bottom: 8px;
}
.scene-row:hover {
    border-color: #93c5fd;
    background: #f8fbff;
}

/* ── 图片画廊 ── */
.gallery-img {
    aspect-ratio: 1;
    object-fit: cover;
    border-radius: 8px;
    border: 2px solid transparent;
    cursor: pointer;
    transition: all 0.15s;
}
.gallery-img:hover, .gallery-img.selected {
    border-color: #3370ff;
    box-shadow: 0 0 0 3px rgba(51,112,255,0.2);
}

/* ── 页面标题区 ── */
.page-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
}
.page-title h2 {
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
}
.page-title span {
    font-size: 12px;
    color: #94a3b8;
}

/* ── 隐藏 Gradio 默认 footer ── */
footer { display: none !important; }
.gradio-container > .main { padding: 0 !important; }
"""


# ══════════════════════════════════════════════════════════════
#  构建 UI
# ══════════════════════════════════════════════════════════════

def build_ui():
    cfg = get_current_config()

    with gr.Blocks(
        css=CUSTOM_CSS,
        title="AI 营销视频工作流 · 牛排工作室",
        theme=gr.themes.Base(
            primary_hue=gr.themes.colors.blue,
            font=[gr.themes.GoogleFont("Inter"), "sans-serif"],
        ),
    ) as demo:

        # ── 侧边栏 Logo 由 CSS ::before/::after 注入，无需额外 HTML ──

        # ── 主体区：Tab 作为侧边导航 ──────────────────────────────────────────
        with gr.Tabs(elem_classes="gradio-tabs"):

            # ════════════════════════════════════════════════════
            #  页面 1：API 配置
            # ════════════════════════════════════════════════════
            with gr.TabItem("⚙️  API 配置"):
                gr.HTML('<div class="page-title"><h2>API 配置</h2><span>配置所有底层 AI 引擎的访问权限</span></div>')

                with gr.Row():
                    # 阿里云·通义千问
                    with gr.Column():
                        gr.HTML('<div class="card-header">☁️ 阿里云·通义千问</div>')
                        qwen_key   = gr.Textbox(label="API Key",   value=cfg["qwen_key"],   type="password", placeholder="sk-***")
                        qwen_url   = gr.Textbox(label="Base URL",  value=cfg["qwen_url"])
                        qwen_model = gr.Textbox(label="Model",     value=cfg["qwen_model"])

                    # 火山引擎·即梦 AI
                    with gr.Column():
                        gr.HTML('<div class="card-header">✨ 火山引擎·即梦 AI</div>')
                        jimeng_key    = gr.Textbox(label="AccessKey ID", value=cfg["jimeng_key"],    type="password", placeholder="AK***")
                        jimeng_secret = gr.Textbox(label="Secret Key",   value=cfg["jimeng_secret"], type="password", placeholder="SK***")

                with gr.Row():
                    # 火山引擎·TTS
                    with gr.Column():
                        gr.HTML('<div class="card-header">🎙️ 火山引擎·语音合成 (TTS)</div>')
                        tts_app_id  = gr.Textbox(label="APP_ID",  value=cfg["tts_app_id"],  placeholder="请输入 APP_ID")
                        tts_token   = gr.Textbox(label="Token",   value=cfg["tts_token"],   type="password", placeholder="Access Token")
                        tts_cluster = gr.Textbox(label="Cluster", value=cfg["tts_cluster"])

                    # 火山引擎·TOS
                    with gr.Column():
                        gr.HTML('<div class="card-header">🗄️ 火山引擎·对象存储 (TOS)</div>')
                        tos_region   = gr.Textbox(label="Region",   value=cfg["tos_region"])
                        tos_bucket   = gr.Textbox(label="Bucket",   value=cfg["tos_bucket"],   placeholder="存储桶名称")
                        tos_endpoint = gr.Textbox(label="Endpoint", value=cfg["tos_endpoint"])

                # 输出目录
                gr.HTML('<div class="card-header" style="margin-top:8px;">📁 输出目录设置</div>')
                with gr.Row():
                    output_dir = gr.Textbox(label="输出目录（本地路径）", value=cfg["output_dir"], scale=4)
                    gr.Button("浏览", elem_classes="btn-secondary", scale=1)

                with gr.Row():
                    api_save_btn = gr.Button("💾  保存 API 配置", elem_classes="btn-primary")
                    api_status   = gr.Textbox(label="", value="等待保存...", interactive=False, show_label=False, scale=2)

                def _save_api(qk, qu, qm, jk, js, ta, tt, tc, tr, tb, te, od):
                    msg = apply_api_config(qk, qu, qm, jk, js, ta, tt, tc, tr, tb, te, od)
                    return f"✅ {msg}（{time.strftime('%H:%M:%S')}）"

                api_save_btn.click(
                    _save_api,
                    inputs=[qwen_key, qwen_url, qwen_model,
                            jimeng_key, jimeng_secret,
                            tts_app_id, tts_token, tts_cluster,
                            tos_region, tos_bucket, tos_endpoint,
                            output_dir],
                    outputs=api_status,
                )

            # ════════════════════════════════════════════════════
            #  页面 2：产品信息
            # ════════════════════════════════════════════════════
            with gr.TabItem("📦  产品信息"):
                gr.HTML('<div class="page-title"><h2>产品信息</h2><span>定义营销视频的核心内容资产</span></div>')

                gr.HTML('<div class="card-header">ℹ️ 基础信息</div>')
                with gr.Row():
                    prod_name  = gr.Textbox(label="产品名称（必填）", placeholder="例如：智能 AI 视频剪辑助手", scale=1)
                    prod_offer = gr.Textbox(label="产品功能 / Offer",  placeholder="例如：30秒快速生成高质量短视频", scale=1)

                gr.HTML('<div class="card-header" style="margin-top:8px;">👥 人群与痛点</div>')
                with gr.Row():
                    target_audience = gr.Textbox(label="目标受众", placeholder="例如：中小企业主、短视频博主、电商运营", scale=1)
                    pain_points     = gr.Textbox(
                        label="核心痛点",
                        placeholder="例如：\n1. 剪辑视频耗时长，成本高\n2. 缺乏创意，视频完播率低",
                        lines=4, scale=1,
                    )

                gr.HTML('<div style="color:#64748b;font-size:12px;margin-top:8px;">✅ 产品信息将在点击"开始生成"时自动读取，无需单独保存。</div>')

            # ════════════════════════════════════════════════════
            #  页面 3：参数配置
            # ════════════════════════════════════════════════════
            with gr.TabItem("🎛️  参数配置"):
                gr.HTML('<div class="page-title"><h2>参数配置</h2><span>精细化控制生成过程的技术参数</span></div>')

                with gr.Row():
                    # 分镜参数
                    with gr.Column():
                        gr.HTML('<div class="card-header">🎬 分镜参数</div>')
                        scene_min  = gr.Number(label="最短分镜时长（秒）", value=cfg["scene_min"],  precision=0)
                        scene_max  = gr.Number(label="最长分镜时长（秒）", value=cfg["scene_max"],  precision=0)
                        image_count= gr.Number(label="生成人物图片数量",   value=cfg["image_count"], precision=0)

                    # 图片参数
                    with gr.Column():
                        gr.HTML('<div class="card-header">🖼️ 图片参数</div>')
                        with gr.Row():
                            image_width  = gr.Number(label="宽度",  value=cfg["image_width"],  precision=0)
                            image_height = gr.Number(label="高度",  value=cfg["image_height"], precision=0)
                        image_scale = gr.Slider(label="CFG 引导强度", minimum=1, maximum=30, step=0.5, value=cfg["image_scale"])
                        image_steps = gr.Slider(label="推理步数",     minimum=1, maximum=50, step=1,   value=cfg["image_steps"])

                    # 视频参数
                    with gr.Column():
                        gr.HTML('<div class="card-header">🎥 视频参数</div>')
                        with gr.Row():
                            video_width  = gr.Number(label="视频宽度", value=cfg["video_width"],  precision=0)
                            video_height = gr.Number(label="视频高度", value=cfg["video_height"], precision=0)
                        omni_resolution = gr.Radio(
                            label="Omni 输出分辨率",
                            choices=[720, 1080],
                            value=cfg["omni_resolution"],
                        )
                        omni_fast = gr.Checkbox(label="Omni 快速模式", value=cfg["omni_fast"])

                with gr.Row(elem_classes="justify-end"):
                    param_save_btn = gr.Button("💾  保存参数", elem_classes="btn-primary")
                    param_status   = gr.Textbox(label="", value="等待保存...", interactive=False, show_label=False, scale=2)

                def _save_params(smin, smax, iw, ih, iscale, isteps, vw, vh, ores, ofast, icount):
                    msg = apply_params(smin, smax, iw, ih, iscale, isteps, vw, vh, ores, ofast, icount)
                    return f"✅ {msg}（{time.strftime('%H:%M:%S')}）"

                param_save_btn.click(
                    _save_params,
                    inputs=[scene_min, scene_max, image_width, image_height,
                            image_scale, image_steps, video_width, video_height,
                            omni_resolution, omni_fast, image_count],
                    outputs=param_status,
                )

            # ════════════════════════════════════════════════════
            #  页面 4：引擎选择 & 运行（核心页面）
            # ════════════════════════════════════════════════════
            with gr.TabItem("▶️  引擎 & 运行"):
                gr.HTML('<div class="page-title"><h2>引擎选择 &amp; 运行</h2><span>启动生成任务并监控实时进度</span></div>')

                with gr.Row():
                    # ── 左侧：配置 + 启动 ─────────────────────────────────────
                    with gr.Column(scale=1):
                        gr.HTML('<div class="card-header">🚀 视频生成引擎</div>')
                        engine_choice = gr.Radio(
                            label="",
                            choices=["omni", "api", "cli"],
                            value=cfg.get("video_engine", "omni"),
                            info="omni=OmniHuman数字人 | api=火山引擎首尾帧 | cli=本地dreamina"
                        )

                        total_duration = gr.Slider(
                            label="视频总时长（秒）",
                            minimum=10, maximum=90, step=5, value=30,
                        )

                        run_id_input = gr.Textbox(
                            label="断点续跑 Run ID",
                            placeholder="留空则开启新任务",
                        )
                        run_id_refresh = gr.Button("🔄 加载历史 Run ID", elem_classes="btn-secondary")
                        run_id_history = gr.Dropdown(label="历史任务", choices=[], interactive=True)

                        def _refresh_run_ids():
                            ids = _list_run_ids()
                            return gr.Dropdown(choices=ids, value=ids[0] if ids else None)

                        run_id_refresh.click(_refresh_run_ids, outputs=run_id_history)
                        run_id_history.change(lambda v: v or "", inputs=run_id_history, outputs=run_id_input)

                        run_btn  = gr.Button("▶  开始生成视频工作流", elem_classes="btn-run")
                        stop_btn = gr.Button("⏹  停止（不可恢复）",    elem_classes="btn-danger")

                    # ── 右侧：日志 + 状态 ─────────────────────────────────────
                    with gr.Column(scale=1):
                        gr.HTML('<div class="card-header">📋 实时运行日志</div>')
                        log_box = gr.Textbox(
                            label="",
                            value='[系统就绪] 请填写产品信息后点击"开始生成"...',
                            lines=14,
                            max_lines=14,
                            interactive=False,
                            elem_classes="log-terminal",
                        )
                        workflow_status = gr.HTML('<div class="badge-idle">⏸ 空闲</div>')

                        gr.HTML('<div class="card-header" style="margin-top:12px;">📄 脚本输出 (JSON)</div>')
                        json_output = gr.JSON(label="", value={"status": "idle"})

                # ── 轮询定时器（每 1.5s 刷新一次日志和交互状态） ──────────────
                timer = gr.Timer(1.5)

                # ── Checkpoint 区（默认隐藏，按需显示） ─────────────────────────
                gr.HTML('<hr style="border-color:#e2e8f0;margin:16px 0;">')

                # --- Checkpoint 1：图片确认 ---
                with gr.Group(visible=False) as cp1_group:
                    gr.HTML('<div class="checkpoint-box cp-image"><b>📸 Checkpoint 1 — 图片确认</b></div>')
                    cp1_text    = gr.Markdown("")
                    cp1_gallery = gr.Gallery(label="生成的人物图片", columns=3, height=260)
                    cp1_new_prompt = gr.Textbox(label="修改生图提示词（可选，留空则使用原提示词重新生成）", placeholder="...")
                    with gr.Row():
                        cp1_ok_btn   = gr.Button("✅ 满意，继续下一步", elem_classes="btn-success")
                        cp1_redo_btn = gr.Button("🔄 不满意，重新生成", elem_classes="btn-danger")

                # --- Checkpoint 2：脚本微调 ---
                with gr.Group(visible=False) as cp2_group:
                    gr.HTML('<div class="checkpoint-box cp-script"><b>📝 Checkpoint 2 — 脚本确认</b></div>')
                    cp2_text   = gr.Markdown("")
                    cp2_script = gr.Textbox(label="完整脚本（可直接编辑）", lines=4)
                    cp2_scenes = gr.Dataframe(
                        label="分镜明细（可编辑台词列）",
                        headers=["scene_id", "duration", "script"],
                        datatype=["number", "number", "str"],
                        interactive=True,
                        col_count=(3, "fixed"),
                    )
                    with gr.Row():
                        cp2_ok_btn   = gr.Button("✅ 确认脚本，开始生成视频", elem_classes="btn-success")
                        cp2_back_btn = gr.Button("✏️ 直接使用以上脚本",       elem_classes="btn-secondary")

                # --- Checkpoint 3：首帧图片选择（Omni 专用） ---
                with gr.Group(visible=False) as cp3_group:
                    gr.HTML('<div class="checkpoint-box cp-omni"><b>🎞️ Checkpoint 3 — 首帧图片分配（Omni 引擎专用）</b></div>')
                    cp3_text    = gr.Markdown("")
                    cp3_gallery = gr.Gallery(label="可用人物图片（点击查看序号）", columns=3, height=200)
                    cp3_scenes_df = gr.Dataframe(
                        label="请为每段分镜填写图片序号（序号从 1 开始）",
                        headers=["scene_id", "duration", "script_preview", "图片序号(1~N)"],
                        datatype=["number", "number", "str", "number"],
                        interactive=True,
                        col_count=(4, "fixed"),
                    )
                    cp3_use_same  = gr.Checkbox(label="所有分镜使用同一张图片", value=False)
                    cp3_same_idx  = gr.Number(label="统一使用的图片序号", value=1, visible=False, precision=0)
                    cp3_use_same.change(lambda v: gr.Number(visible=v), inputs=cp3_use_same, outputs=cp3_same_idx)
                    cp3_ok_btn    = gr.Button("✅ 确认首帧分配，开始合成视频", elem_classes="btn-success")

                # ── 结果展示区 ──────────────────────────────────────────────
                gr.HTML('<hr style="border-color:#e2e8f0;margin:16px 0;">')
                gr.HTML('<div class="card-header">🎉 生成结果</div>')
                with gr.Row():
                    result_gallery = gr.Gallery(label="素材图片画廊", columns=3, height=260, scale=2)
                    with gr.Column(scale=1):
                        result_video  = gr.Video(label="最终生成视频（分镜片段）")
                        result_audio  = gr.File(label="TTS 音频文件", file_count="multiple")
                result_cards  = gr.Gallery(label="模特模卡图", columns=3, height=200)

                # ════════════════════════════════════════════════
                #  事件处理：启动工作流
                # ════════════════════════════════════════════════

                def start_workflow(engine, duration, run_id,
                                   pname, poffer, audience, pains):
                    global _backend, _workflow_thread, _workflow_running
                    global _workflow_result, _workflow_error, _log_lines, _pending_request

                    if _workflow_running:
                        return (
                            gr.update(),  # log_box
                            gr.HTML('<div class="badge-running">⏳ 已在运行中</div>'),
                            gr.update(), gr.update(), gr.update(),  # 3 cp groups
                            gr.update(), gr.update(), gr.update(), gr.update(),  # results
                            gr.update(),  # json
                        )

                    if not pname.strip():
                        return (
                            '⚠️ 请先在"产品信息"页面填写产品名称！',
                            gr.HTML('<div class="badge-idle">⏸ 空闲</div>'),
                            gr.update(), gr.update(), gr.update(),
                            gr.update(), gr.update(), gr.update(), gr.update(),
                            gr.update(),
                        )

                    # 设置引擎
                    config.VIDEO_ENGINE = engine.lower()

                    _backend         = GradioBackend()
                    _workflow_result  = None
                    _workflow_error   = None
                    _log_lines        = [f"[{time.strftime('%H:%M:%S')}] 工作流启动，Run ID：{run_id or '（自动生成）'}"]
                    _pending_request  = None
                    _workflow_running = True

                    kwargs = dict(
                        product_name    = pname.strip(),
                        product_offer   = poffer.strip(),
                        target_audience = audience.strip(),
                        pain_points     = pains.strip(),
                        total_duration  = int(duration),
                        run_id          = run_id.strip() or None,
                    )

                    _workflow_thread = threading.Thread(
                        target=_run_workflow_thread, args=(kwargs,), daemon=True
                    )
                    _workflow_thread.start()

                    return (
                        "\n".join(_log_lines),
                        gr.HTML('<div class="badge-running">⏳ 运行中…</div>'),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(), gr.update(), gr.update(), gr.update(),
                        {"status": "running", "run_id": run_id or "auto"},
                    )

                run_btn.click(
                    start_workflow,
                    inputs=[engine_choice, total_duration, run_id_input,
                            prod_name, prod_offer, target_audience, pain_points],
                    outputs=[log_box, workflow_status,
                             cp1_group, cp2_group, cp3_group,
                             result_gallery, result_video, result_audio, result_cards,
                             json_output],
                )

                # ════════════════════════════════════════════════
                #  定时轮询：刷新日志 + 检测交互请求
                # ════════════════════════════════════════════════

                def _poll():
                    """每 1.5s 执行一次，返回 UI 组件更新。"""
                    global _pending_request, _log_lines, _workflow_running

                    if _backend is None:
                        return (
                            gr.update(), gr.update(),
                            gr.update(), gr.update(), gr.update(),
                            gr.update(), gr.update(), gr.update(), gr.update(),
                            gr.update(),
                        )

                    # 排空日志队列
                    while True:
                        try:
                            item = _backend._out_q.get_nowait()
                        except queue.Empty:
                            break

                        if item["type"] == "log":
                            ts = time.strftime('%H:%M:%S')
                            _log_lines.append(f"[{ts}] {item['text']}")
                            # 只保留最近 200 行
                            if len(_log_lines) > 200:
                                _log_lines = _log_lines[-200:]

                        elif item["type"] in ("confirm", "prompt"):
                            # 有交互请求 → 暂存，等待 UI 处理
                            _pending_request = item
                            # 根据 text 内容判断是哪个 Checkpoint
                            text = item.get("text", "")

                            if "图片是否满足需求" in text or "是否修改提示词" in text:
                                # CP1
                                state = _load_run_state(_get_current_run_id()) if _get_current_run_id() else {}
                                imgs  = state.get("image_paths") or state.get("image_urls") or []
                                fp    = state.get("feature_prompt", "")
                                _log_lines.append(f"[{time.strftime('%H:%M:%S')}] ⏸ 等待用户确认图片...")
                                return (
                                    "\n".join(_log_lines[-80:]),
                                    gr.HTML('<div class="badge-running">⏸ 等待图片确认…</div>'),
                                    gr.update(visible=True),   # cp1
                                    gr.update(visible=False),  # cp2
                                    gr.update(visible=False),  # cp3
                                    gr.update(value=imgs),     # gallery
                                    gr.update(), gr.update(), gr.update(),
                                    gr.update(),
                                )

                            elif "是否对脚本进行微调" in text or "新台词" in text:
                                # CP2
                                state = _load_run_state(_get_current_run_id()) if _get_current_run_id() else {}
                                full_script = state.get("full_script", "")
                                scenes      = state.get("scenes", [])
                                table_data  = [[s.get("scene_id"), s.get("duration"), s.get("script", "")] for s in scenes]
                                _log_lines.append(f"[{time.strftime('%H:%M:%S')}] ⏸ 等待用户确认脚本...")
                                return (
                                    "\n".join(_log_lines[-80:]),
                                    gr.HTML('<div class="badge-running">⏸ 等待脚本确认…</div>'),
                                    gr.update(visible=False),
                                    gr.update(visible=True),   # cp2
                                    gr.update(visible=False),
                                    gr.update(),
                                    gr.update(), gr.update(), gr.update(),
                                    gr.update(value={"status": "waiting_script"}),
                                )

                            elif "首帧" in text or "分镜" in text and "图片" in text:
                                # CP3
                                state = _load_run_state(_get_current_run_id()) if _get_current_run_id() else {}
                                imgs  = state.get("image_paths") or state.get("image_urls") or []
                                scenes= state.get("scenes", [])
                                table_data = [[s.get("scene_id"), s.get("duration"),
                                               s.get("script","")[:20]+"…", 1] for s in scenes]
                                _log_lines.append(f"[{time.strftime('%H:%M:%S')}] ⏸ 等待用户分配首帧图片...")
                                return (
                                    "\n".join(_log_lines[-80:]),
                                    gr.HTML('<div class="badge-running">⏸ 等待首帧分配…</div>'),
                                    gr.update(visible=False),
                                    gr.update(visible=False),
                                    gr.update(visible=True),   # cp3
                                    gr.update(),
                                    gr.update(), gr.update(), gr.update(),
                                    gr.update(value={"status": "waiting_scene_images"}),
                                )

                    # 判断状态
                    if not _workflow_running and _workflow_result is not None:
                        state = _workflow_result
                        imgs  = state.get("image_paths") or state.get("image_urls") or []
                        # 取第一段视频
                        vids  = [p for p in state.get("video_paths", []) if p and os.path.isfile(p)]
                        auds  = [p for p in state.get("audio_paths", []) if p and os.path.isfile(p)]
                        cards = state.get("card_paths") or []

                        _log_lines.append(f"[{time.strftime('%H:%M:%S')}] ✅ 工作流完成！")
                        return (
                            "\n".join(_log_lines[-80:]),
                            gr.HTML('<div class="badge-done">✅ 完成</div>'),
                            gr.update(visible=False),
                            gr.update(visible=False),
                            gr.update(visible=False),
                            gr.update(value=imgs),
                            gr.update(value=vids[0] if vids else None),
                            gr.update(value=auds if auds else None),
                            gr.update(value=cards if cards else []),
                            {"status": "completed",
                             "run_dir": state.get("run_dir", ""),
                             "total_scenes": state.get("total_scenes", 0)},
                        )

                    if not _workflow_running and _workflow_error:
                        _log_lines.append(f"[{time.strftime('%H:%M:%S')}] ❌ 工作流出错：{_workflow_error[:200]}")
                        return (
                            "\n".join(_log_lines[-80:]),
                            gr.HTML('<div class="badge-idle" style="background:#fee2e2;color:#dc2626;">❌ 出错</div>'),
                            gr.update(visible=False), gr.update(visible=False), gr.update(visible=False),
                            gr.update(), gr.update(), gr.update(), gr.update(),
                            {"status": "error", "message": _workflow_error[:300]},
                        )

                    # 运行中，只刷新日志
                    status_html = (
                        '<div class="badge-running">⏳ 运行中…</div>'
                        if _workflow_running
                        else '<div class="badge-idle">⏸ 空闲</div>'
                    )
                    return (
                        "\n".join(_log_lines[-80:]),
                        gr.HTML(status_html),
                        gr.update(), gr.update(), gr.update(),
                        gr.update(), gr.update(), gr.update(), gr.update(),
                        gr.update(),
                    )

                timer.tick(
                    _poll,
                    outputs=[log_box, workflow_status,
                             cp1_group, cp2_group, cp3_group,
                             result_gallery, result_video, result_audio, result_cards,
                             json_output],
                )

                # ════════════════════════════════════════════════
                #  Checkpoint 按钮事件
                # ════════════════════════════════════════════════

                # --- CP1 确认 ---
                def cp1_confirm(new_prompt):
                    global _pending_request
                    if _backend is None:
                        return gr.update(visible=True), "\n".join(_log_lines[-80:])
                    # 先回答当前挂起的 confirm（图片满意吗？）
                    _backend.reply(True)
                    _pending_request = None
                    ts = time.strftime('%H:%M:%S')
                    _log_lines.append(f"[{ts}] ✅ 用户确认图片满意，继续...")
                    return gr.update(visible=False), "\n".join(_log_lines[-80:])

                def cp1_redo(new_prompt):
                    global _pending_request
                    if _backend is None:
                        return gr.update(visible=True), "\n".join(_log_lines[-80:])
                    # 回答"不满意"→ 触发 interactive.confirm_images 内部 modify 流程
                    _backend.reply(False)
                    # 等待下一个 confirm（"是否修改提示词"）
                    time.sleep(0.3)
                    # 回答"是否修改提示词"
                    if new_prompt and new_prompt.strip():
                        _backend.reply(True)   # 修改提示词
                        time.sleep(0.1)
                        _backend.reply(new_prompt.strip())
                    else:
                        _backend.reply(False)  # 直接重新生成
                    _pending_request = None
                    ts = time.strftime('%H:%M:%S')
                    _log_lines.append(f"[{ts}] 🔄 用户请求重新生图...")
                    return gr.update(visible=False), "\n".join(_log_lines[-80:])

                cp1_ok_btn.click(cp1_confirm,   inputs=cp1_new_prompt, outputs=[cp1_group, log_box])
                cp1_redo_btn.click(cp1_redo,    inputs=cp1_new_prompt, outputs=[cp1_group, log_box])

                # --- CP2 确认 ---
                def cp2_confirm(script_text, scenes_df):
                    global _pending_request
                    if _backend is None:
                        return gr.update(visible=True), "\n".join(_log_lines[-80:])
                    # 回答"是否微调" → False（直接确认，使用界面显示的脚本）
                    # 若用户已修改 scenes_df，则用修改后的数据更新 state
                    _backend.reply(False)
                    _pending_request = None
                    ts = time.strftime('%H:%M:%S')
                    _log_lines.append(f"[{ts}] ✅ 用户确认脚本，开始视频生成...")
                    return gr.update(visible=False), "\n".join(_log_lines[-80:])

                def cp2_use_original(script_text, scenes_df):
                    return cp2_confirm(script_text, scenes_df)

                cp2_ok_btn.click(cp2_confirm,      inputs=[cp2_script, cp2_scenes], outputs=[cp2_group, log_box])
                cp2_back_btn.click(cp2_use_original, inputs=[cp2_script, cp2_scenes], outputs=[cp2_group, log_box])

                # --- CP3 确认 ---
                def cp3_confirm(scenes_data, use_same, same_idx):
                    global _pending_request
                    if _backend is None:
                        return gr.update(visible=True), "\n".join(_log_lines[-80:])

                    if use_same:
                        _backend.reply(True)   # confirm "all same"
                        time.sleep(0.1)
                        _backend.reply(str(int(same_idx)))
                    else:
                        _backend.reply(False)  # per-scene
                        if scenes_data is not None:
                            for row in (scenes_data.values.tolist() if hasattr(scenes_data, 'values') else scenes_data):
                                idx_val = row[3] if len(row) > 3 else 1
                                time.sleep(0.05)
                                _backend.reply(str(int(idx_val or 1)))

                    _pending_request = None
                    ts = time.strftime('%H:%M:%S')
                    _log_lines.append(f"[{ts}] ✅ 首帧图片分配已确认...")
                    return gr.update(visible=False), "\n".join(_log_lines[-80:])

                cp3_ok_btn.click(cp3_confirm,
                                 inputs=[cp3_scenes_df, cp3_use_same, cp3_same_idx],
                                 outputs=[cp3_group, log_box])

                # ════════════════════════════════════════════════
                #  停止按钮
                # ════════════════════════════════════════════════

                def stop_workflow():
                    global _workflow_running
                    _workflow_running = False
                    if _backend:
                        try:
                            _backend.reply(False)  # 解除可能存在的阻塞
                        except Exception:
                            pass
                    ts = time.strftime('%H:%M:%S')
                    _log_lines.append(f"[{ts}] ⏹ 用户请求停止（当前步骤执行完后停止）")
                    return "\n".join(_log_lines[-80:]), gr.HTML('<div class="badge-idle">⏸ 已停止</div>')

                stop_btn.click(stop_workflow, outputs=[log_box, workflow_status])

            # ════════════════════════════════════════════════════
            #  页面 5：提示词编辑
            # ════════════════════════════════════════════════════
            with gr.TabItem("✏️  提示词编辑"):
                gr.HTML('<div class="page-title"><h2>提示词编辑</h2><span>优化工作流中各环节的 AI 指令</span></div>')

                with gr.Accordion("👤  1. 人物小传 (Story Maker)", open=True):
                    gr.HTML('<div style="color:#64748b;font-size:12px;margin-bottom:8px;">根据产品信息生成目标用户画像，作为后续所有节点的输入。</div>')
                    with gr.Row():
                        story_sys  = gr.Textbox(label="System Prompt", value=cfg["story_sys"],  lines=5, elem_classes="font-mono bg-slate-50")
                        story_user = gr.Textbox(label="User Prompt 模板", value=cfg["story_user"], lines=5, elem_classes="font-mono")

                with gr.Accordion("🖼️  2. 生图特征提取 (Key Feature Extractor)", open=False):
                    gr.HTML('<div style="color:#64748b;font-size:12px;margin-bottom:8px;">从人物小传提取可视化特征，转化为英文生图提示词。</div>')
                    with gr.Row():
                        feat_sys  = gr.Textbox(label="System Prompt", value=cfg["feat_sys"],  lines=5, elem_classes="font-mono bg-slate-50")
                        feat_user = gr.Textbox(label="User Prompt 模板", value=cfg["feat_user"], lines=5, elem_classes="font-mono")

                with gr.Accordion("🎙️  3. 音色选择 (Voice Type Generator)", open=False):
                    gr.HTML('<div style="color:#64748b;font-size:12px;margin-bottom:8px;">根据人物特征和产品类型选择最合适的 TTS 音色。</div>')
                    with gr.Row():
                        voice_sys  = gr.Textbox(label="System Prompt", value=cfg["voice_sys"],  lines=5, elem_classes="font-mono bg-slate-50")
                        voice_user = gr.Textbox(label="User Prompt 模板", value=cfg["voice_user"], lines=5, elem_classes="font-mono")

                with gr.Accordion("📜  4. 口播脚本生成 (Script Generator)", open=False):
                    gr.HTML('<div style="color:#64748b;font-size:12px;margin-bottom:8px;">生成分镜口播脚本，控制视频节奏和转化逻辑。</div>')
                    with gr.Row():
                        script_sys  = gr.Textbox(label="System Prompt", value=cfg["script_sys"],  lines=5, elem_classes="font-mono bg-slate-50")
                        script_user = gr.Textbox(label="User Prompt 模板", value=cfg["script_user"], lines=5, elem_classes="font-mono")

                with gr.Row():
                    prompt_save_btn = gr.Button("💾  保存提示词", elem_classes="btn-primary")
                    prompt_reset_btn = gr.Button("↩️  恢复默认值", elem_classes="btn-secondary")
                    prompt_status   = gr.Textbox(label="", value="等待保存...", interactive=False, show_label=False, scale=3)

                def _save_prompts(ss, su, fs, fu, vs, vu, scs, scu):
                    msg = apply_prompts(ss, su, fs, fu, vs, vu, scs, scu)
                    return f"✅ {msg}（{time.strftime('%H:%M:%S')}）"

                prompt_save_btn.click(
                    _save_prompts,
                    inputs=[story_sys, story_user, feat_sys, feat_user,
                            voice_sys, voice_user, script_sys, script_user],
                    outputs=prompt_status,
                )

                def _reset_prompts():
                    import importlib
                    import prompts_config as pc
                    importlib.reload(pc)
                    return (pc.STORY_MAKER_SYSTEM, pc.STORY_MAKER_USER,
                            pc.KEY_FEATURE_SYSTEM, pc.KEY_FEATURE_USER,
                            pc.VOICE_TYPE_SYSTEM,  pc.VOICE_TYPE_USER,
                            pc.SCRIPT_GENERATOR_SYSTEM, pc.SCRIPT_GENERATOR_USER,
                            "✅ 已从文件重新加载默认提示词")

                prompt_reset_btn.click(
                    _reset_prompts,
                    outputs=[story_sys, story_user, feat_sys, feat_user,
                             voice_sys, voice_user, script_sys, script_user,
                             prompt_status],
                )

    return demo


# ══════════════════════════════════════════════════════════════
#  辅助：获取当前运行 ID
# ══════════════════════════════════════════════════════════════

def _get_current_run_id() -> str | None:
    """从 workflow 线程的 _workflow_result 或后台日志中推断当前 run_id。"""
    if _workflow_result and "run_id" in _workflow_result:
        return _workflow_result["run_id"]
    # 扫描最新目录作为 fallback
    ids = _list_run_ids()
    return ids[0] if ids else None


# ══════════════════════════════════════════════════════════════
#  入口
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 确保 apply_* 等辅助函数可用（app 模块自身包含）
    demo = build_ui()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True,
        share=False,
    )
