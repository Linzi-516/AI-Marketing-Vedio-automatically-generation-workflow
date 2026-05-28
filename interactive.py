"""
交互式用户确认模块 (Interactive Confirmation Module)

设计原则：
  - 所有需要人工干预的节点通过此模块暴露统一接口
  - 后端逻辑与 I/O 完全解耦：默认 CLI 模式直接使用 input()
  - 每个交互点均有明确的返回契约，方便后续按需接入其他 I/O backend

接口约定：
  所有公开函数均接受可选的 io_backend 参数，类型为 IOBackend 子类实例。
  若不传则使用全局默认 backend（默认为 CLIBackend）。

扩展方式：
  1. 实现一个继承 IOBackend 的自定义 backend
  2. 调用 interactive.set_global_backend(...) 或在 workflow.run 中传入 io_backend
  3. workflow.py 中所有 interactive 调用保持不变
"""

import os
import sys
from abc import ABC, abstractmethod
from typing import Optional


# ══════════════════════════════════════════════════════════════
#  I/O Backend 抽象层
# ══════════════════════════════════════════════════════════════

class IOBackend(ABC):
    """I/O 后端抽象基类，自定义交互实现可继承此类。"""

    @abstractmethod
    def display(self, message: str) -> None:
        """向用户展示信息（无需回复）"""

    @abstractmethod
    def prompt(self, message: str, default: str = "") -> str:
        """向用户提问并获取文本回复"""

    @abstractmethod
    def confirm(self, message: str) -> bool:
        """向用户提问是/否，返回 True/False"""


class CLIBackend(IOBackend):
    """命令行 I/O 后端（默认实现）"""

    def display(self, message: str) -> None:
        print(message)

    def prompt(self, message: str, default: str = "") -> str:
        if default:
            user_input = input(f"{message} [默认: {default}]: ").strip()
            return user_input if user_input else default
        return input(f"{message}: ").strip()

    def confirm(self, message: str) -> bool:
        while True:
            answer = input(f"{message} (y/n): ").strip().lower()
            if answer in ("y", "yes", "是", "1"):
                return True
            if answer in ("n", "no", "否", "0"):
                return False
            print("  请输入 y（是）或 n（否）")


# 全局默认 backend
_global_backend: IOBackend = CLIBackend()


def set_global_backend(backend: IOBackend) -> None:
    """替换全局 I/O backend。"""
    global _global_backend
    _global_backend = backend


def _get_backend(backend: Optional[IOBackend]) -> IOBackend:
    return backend if backend is not None else _global_backend


# ══════════════════════════════════════════════════════════════
#  功能 1：生图确认与重生成
# ══════════════════════════════════════════════════════════════

def confirm_images(
    image_paths: list,
    feature_prompt: str,
    run_dir: str,
    backend: Optional[IOBackend] = None,
) -> dict:
    """
    生图完成后，让用户查看结果并决定：
      - 满意 → 继续下一步
      - 不满意 → 可修改 feature_prompt 后重新生成

    Args:
        image_paths:    本次生成的图片本地路径列表
        feature_prompt: 当前使用的生图提示词
        run_dir:        当前运行目录（用于展示路径提示）
        backend:        I/O backend，None 则使用全局默认

    Returns:
        {
            "action": "next" | "regenerate",
            "new_prompt": str | None,   # 若 action=="regenerate" 则为新提示词
        }
    """
    io = _get_backend(backend)
    if hasattr(io, "confirm_images"):
        return io.confirm_images(
            image_paths=image_paths,
            feature_prompt=feature_prompt,
            run_dir=run_dir,
        )

    io.display("\n" + "═" * 60)
    io.display("  【生图完成】请查看以下图片，确认是否满意")
    io.display("═" * 60)

    if image_paths:
        io.display(f"\n  已生成 {len(image_paths)} 张图片，保存位置：")
        for i, p in enumerate(image_paths, 1):
            io.display(f"    [{i}] {p}")
    else:
        io.display("  警告：未能获取到图片路径")

    io.display("\n  当前使用的生图提示词：")
    io.display(f"  {feature_prompt}")
    io.display("")

    satisfied = io.confirm("图片是否满足需求，直接进行下一步？")

    if satisfied:
        return {"action": "next", "new_prompt": None}

    # 不满意 → 询问是否修改提示词
    io.display("\n  当前提示词（可复制后修改）：")
    io.display(f"  {feature_prompt}")
    io.display("")

    modify = io.confirm("是否修改提示词后重新生成？（否则使用原提示词直接重新生成）")

    if modify:
        io.display("\n  请输入新的提示词（英文逗号分隔的描述词）：")
        new_prompt = io.prompt("  新提示词", default=feature_prompt)
        if not new_prompt.strip():
            new_prompt = feature_prompt
    else:
        new_prompt = feature_prompt

    return {"action": "regenerate", "new_prompt": new_prompt}


# ══════════════════════════════════════════════════════════════
#  功能 2：脚本确认与微调
# ══════════════════════════════════════════════════════════════

def confirm_script(
    full_script: str,
    scenes: list,
    backend: Optional[IOBackend] = None,
) -> dict:
    """
    视频生成前，向用户展示完整脚本和分镜列表，允许微调。

    Args:
        full_script: 完整脚本文本
        scenes:      分镜列表，每项为 {"scene_id": int, "duration": int, "script": str}
        backend:     I/O backend

    Returns:
        {
            "action":      "next" | "modify",
            "full_script": str,           # 最终使用的完整脚本（可能被修改）
            "scenes":      list[dict],    # 最终使用的分镜列表（scene 的 script 字段可能被修改）
        }
    """
    io = _get_backend(backend)
    if hasattr(io, "confirm_script"):
        return io.confirm_script(full_script=full_script, scenes=scenes)

    io.display("\n" + "═" * 60)
    io.display("  【脚本生成完成】请审阅以下脚本，确认是否需要微调")
    io.display("═" * 60)

    io.display("\n  ── 完整脚本 ──")
    io.display(full_script)

    io.display("\n  ── 分镜明细 ──")
    for scene in scenes:
        sid = scene.get("scene_id", "?")
        dur = scene.get("duration", "?")
        script = scene.get("script", "")
        io.display(f"  分镜 [{sid}] ({dur}s)：{script}")

    io.display("")
    modify = io.confirm("是否对脚本进行微调？（否则直接使用以上脚本）")

    if not modify:
        return {"action": "next", "full_script": full_script, "scenes": scenes}

    # 微调模式：逐条让用户确认/修改
    io.display("\n  开始逐条微调分镜（直接回车保留原内容）：")
    new_scenes = []
    for scene in scenes:
        sid = scene.get("scene_id", "?")
        dur = scene.get("duration", "?")
        original_script = scene.get("script", "")

        io.display(f"\n  ── 分镜 [{sid}] ({dur}s) ──")
        io.display(f"  原台词：{original_script}")
        new_script = io.prompt("  新台词（回车保留原文）", default=original_script)

        new_scene = dict(scene)
        new_scene["script"] = new_script if new_script.strip() else original_script
        new_scenes.append(new_scene)

    # 重新拼接完整脚本
    new_full_script = "".join(s["script"] for s in new_scenes)

    io.display("\n  ── 更新后的分镜 ──")
    for scene in new_scenes:
        io.display(f"  [{scene['scene_id']}] ({scene['duration']}s)：{scene['script']}")

    return {"action": "modify", "full_script": new_full_script, "scenes": new_scenes}


# ══════════════════════════════════════════════════════════════
#  功能 3：Omni 视频生成 - 每段分镜首帧图片选择
# ══════════════════════════════════════════════════════════════

def select_scene_images(
    scenes: list,
    available_image_paths: list,
    available_image_urls: list,
    backend: Optional[IOBackend] = None,
) -> list:
    """
    让用户为每段分镜选择首帧图片（Omni 引擎专用）。

    设计说明（I/O 解耦）：
      - CLI 模式：展示图片路径列表，用户输入序号或直接粘贴路径/URL
      - 自定义 backend 可将此调用映射为其他图片选择组件，返回格式完全相同
      - 若用户对所有分镜均选相同图片，可输入单个序号快速填充

    Args:
        scenes:                 分镜列表
        available_image_paths:  已生成的图片本地路径列表
        available_image_urls:   已生成的图片公网 URL 列表（与 paths 一一对应）
        backend:                I/O backend

    Returns:
        list[dict]  与 scenes 等长，每项为：
        {
            "scene_id":   int,
            "image_path": str,   # 选中图片的本地路径（用于展示/存档）
            "image_url":  str,   # 选中图片的公网 URL（Omni API 需要）
        }
    """
    io = _get_backend(backend)
    if hasattr(io, "select_scene_images"):
        return io.select_scene_images(
            scenes=scenes,
            available_image_paths=available_image_paths,
            available_image_urls=available_image_urls,
        )

    io.display("\n" + "═" * 60)
    io.display("  【首帧图片选择】为每段分镜选择首帧人物图片")
    io.display("═" * 60)

    # 展示可用图片列表
    io.display("\n  当前可用的人物图片：")
    for i, (p, u) in enumerate(zip(available_image_paths, available_image_urls), 1):
        filename = os.path.basename(p) if p else "(无路径)"
        url_hint = u if u else "（无公网 URL，选择后会要求手动输入）"
        io.display(f"    [{i}] {filename}")
        io.display(f"        本地路径: {p}")
        io.display(f"        公网 URL : {url_hint}")

    io.display("")

    # 询问是否对所有分镜使用同一张图片
    use_same = io.confirm("是否对所有分镜使用同一张图片？")

    if use_same:
        selected_idx = _ask_image_index(
            io, available_image_paths, available_image_urls,
            prompt_text="请选择用于所有分镜的图片（输入序号或直接输入路径/URL）",
            fallback_path=available_image_paths[0] if available_image_paths else "",
            fallback_url=available_image_urls[0] if available_image_urls else "",
        )
        result = []
        for scene in scenes:
            result.append({
                "scene_id": scene.get("scene_id"),
                "image_path": selected_idx["image_path"],
                "image_url": selected_idx["image_url"],
            })
        return result

    # 逐条选择
    result = []
    default_path = available_image_paths[0] if available_image_paths else ""
    default_url = available_image_urls[0] if available_image_urls else ""

    for scene in scenes:
        sid = scene.get("scene_id", "?")
        script_preview = scene.get("script", "")[:30]
        io.display(f"\n  ── 分镜 [{sid}]：{script_preview}... ──")

        selected = _ask_image_index(
            io, available_image_paths, available_image_urls,
            prompt_text=f"  为分镜 [{sid}] 选择首帧图片（序号 / 路径 / URL，回车使用默认[1]）",
            fallback_path=default_path,
            fallback_url=default_url,
        )
        result.append({
            "scene_id": sid,
            "image_path": selected["image_path"],
            "image_url": selected["image_url"],
        })

        # 将本次选择设为后续默认（方便连续输入相同选择时直接回车）
        default_path = selected["image_path"]
        default_url = selected["image_url"]

    io.display("\n  ── 首帧图片分配汇总 ──")
    for item in result:
        fname = os.path.basename(item["image_path"]) if item["image_path"] else "(未知)"
        io.display(f"  分镜 [{item['scene_id']}] → {fname}")

    return result


def _ask_image_index(
    io: IOBackend,
    available_image_paths: list,
    available_image_urls: list,
    prompt_text: str,
    fallback_path: str,
    fallback_url: str,
) -> dict:
    """
    内部辅助：解析用户输入的图片选择。
    用户可输入：
      - 纯数字（序号）→ 使用列表中对应的图片；若该图片无公网 URL，继续追问 URL
      - http/https URL → 直接使用，path 为空字符串
      - 本地路径（包含路径分隔符或以盘符开头）→ 直接使用，继续追问公网 URL
      - 空输入 → 使用 fallback；若 fallback 无 URL，也继续追问
    """
    while True:
        raw = io.prompt(prompt_text, default="").strip()

        # 空输入 → 使用 fallback
        if not raw:
            path = fallback_path
            url = fallback_url
            if not url:
                url = _ask_for_public_url(io, path)
            return {"image_path": path, "image_url": url}

        # 数字序号
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(available_image_paths):
                path = available_image_paths[idx]
                url = available_image_urls[idx] if idx < len(available_image_urls) else ""
                if not url:
                    url = _ask_for_public_url(io, path)
                return {"image_path": path, "image_url": url}
            io.display(f"  序号 {raw} 超出范围（1~{len(available_image_paths)}），请重新输入")
            continue

        # http/https URL → 直接作为公网 URL 使用
        if raw.startswith("http://") or raw.startswith("https://"):
            return {"image_path": "", "image_url": raw}

        # 本地路径
        if os.path.exists(raw):
            url = _ask_for_public_url(io, raw)
            return {"image_path": raw, "image_url": url}

        io.display(f"  输入 '{raw}' 无法识别，请输入序号、本地路径或公网 URL")


def _ask_for_public_url(io: IOBackend, local_path: str) -> str:
    """
    当图片只有本地路径、没有公网 URL 时，提示用户手动输入公网 URL。

    Omni API 要求图片必须为公网可访问的 https:// URL。
    常见做法：
      1. 上传到火山引擎 TOS（桶设为公共读）→ 复制对象 URL
      2. 上传到阿里云 OSS / 腾讯云 COS 等任意对象存储
      3. 上传到图床（如 sm.ms、imgur）获取直链

    接入自定义 I/O 时，此函数可替换为自动上传逻辑。
    """
    filename = os.path.basename(local_path) if local_path else "（未知文件）"
    io.display(f"\n  ⚠  图片 [{filename}] 没有公网 URL。")
    io.display("  OmniHuman API 要求图片必须为公网可访问的 https:// 地址。")
    io.display("  请将该图片上传到 TOS / OSS / 图床等，然后粘贴公网 URL：")
    io.display(f"  （图片本地路径：{local_path}）")

    while True:
        url = io.prompt("  请输入公网 URL（https://...）", default="").strip()
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if url:
            io.display("  输入的不是有效 URL，请确保以 http:// 或 https:// 开头")
        else:
            io.display("  URL 不能为空，请粘贴图片的公网访问地址")
