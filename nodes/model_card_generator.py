"""
节点：Model Card Generator（模特模卡图生成）
输入模特原图 + 姿势剪影参考图，输出多张姿势模卡图。
"""

import base64
import os
import time

import config
from clients.jimeng_client import (
    download_bytes,
    image_to_base64,
    poll_task,
    submit_async_task,
)


POSE_CONFIGS = [
    {
        "silhouette_key": 0,
        "prompt": (
            "第一张图是人物原图，第二张图是姿势参考剪影。"
            "请让人物完全复刻第二张图中的姿势动作，"
            "保持第一张图人物的五官、发型、穿搭、身材比例完全不变，"
            "背景改为纯灰色，输出为时尚模特展示效果。"
        ),
    },
    {
        "silhouette_key": 1,
        "prompt": (
            "第一张图是人物原图，第二张图是姿势参考剪影。"
            "请让人物完全复刻第二张图中的姿势动作，"
            "保持第一张图人物的五官、发型、穿搭、身材比例完全不变，"
            "背景改为纯灰色，输出为时尚模特展示效果。"
        ),
    },
    {
        "silhouette_key": 2,
        "prompt": (
            "第一张图是人物原图，第二张图是姿势参考剪影。"
            "请让人物完全复刻第二张图中的姿势动作，"
            "保持第一张图人物的五官、发型、穿搭、身材比例完全不变，"
            "背景改为纯灰色，输出为时尚模特展示效果。"
        ),
    },
]


def _submit_card_task(model_image_path: str, silhouette_path: str, prompt: str) -> str:
    """提交图片生成 4.0 任务，返回 task_id。"""
    payload = {
        "req_key": config.JIMENG_MODELCARD_MODEL,
        "binary_data_base64": [
            image_to_base64(model_image_path),
            image_to_base64(silhouette_path),
        ],
        "prompt": prompt,
        "scale": 0.6,
        "force_single": True,
        "width": config.JIMENG_MODELCARD_WIDTH,
        "height": config.JIMENG_MODELCARD_HEIGHT,
    }

    task_id = submit_async_task(payload, operation="模卡图任务提交")
    print(f"[Model Card Generator] 任务已提交 task_id={task_id}")
    return task_id


def _card_result_getter(data: dict) -> str:
    url_list = data.get("image_urls") or []
    b64_list = data.get("binary_data_base64") or []
    if url_list and url_list[0]:
        return f"url:{url_list[0]}"
    if b64_list and b64_list[0]:
        return f"b64:{b64_list[0]}"
    return ""


def _poll_card_task(task_id: str, max_wait: int = 300) -> tuple:
    """轮询任务状态，返回 (result_type, result_data)。"""
    result = poll_task(
        req_key=config.JIMENG_MODELCARD_MODEL,
        task_id=task_id,
        action="CVSync2AsyncGetResult",
        max_wait=max_wait,
        extra_payload={"req_json": "{\"return_url\":true}"},
        result_getter=_card_result_getter,
        log_prefix="Model Card Generator",
    )
    result_type, result_data = result.split(":", 1)
    return result_type, result_data


def _generate_single_card(
    model_image_path: str,
    silhouette_path: str,
    prompt: str,
    output_path: str,
) -> bool:
    """生成单张模卡图并保存到 output_path。"""
    try:
        task_id = _submit_card_task(model_image_path, silhouette_path, prompt)
        result_type, result_data = _poll_card_task(task_id)

        if result_type == "url":
            content = download_bytes(result_data, timeout=60)
        else:
            content = base64.b64decode(result_data)

        with open(output_path, "wb") as f:
            f.write(content)
        return True

    except Exception as e:
        print(f"[Model Card Generator] 生成失败: {e}")
        return False


def run(
    model_image_path: str,
    silhouette_paths: list,
    output_dir: str = None,
) -> dict:
    """
    运行模特模卡图生成节点。

    Returns:
        {
            "success": bool,
            "card_paths": list[str|None],
            "failed_indices": list[int],
        }
    """
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(model_image_path):
        raise FileNotFoundError(f"模特原图不存在: {model_image_path}")

    pose_count = len(POSE_CONFIGS)
    print(f"[Model Card Generator] 开始生成模卡图，共 {pose_count} 张姿势...")
    print(f"[Model Card Generator] 模特原图: {model_image_path}")

    card_paths = []
    failed_indices = []

    for idx, pose_cfg in enumerate(POSE_CONFIGS):
        sil_idx = pose_cfg["silhouette_key"]
        silhouette_path = silhouette_paths[sil_idx] if sil_idx < len(silhouette_paths) else None
        prompt = pose_cfg["prompt"]

        if not silhouette_path or not os.path.exists(silhouette_path):
            print(f"[Model Card Generator] 姿势 {idx + 1} 剪影图不存在，跳过: {silhouette_path}")
            failed_indices.append(idx)
            card_paths.append(None)
            continue

        silhouette_name = os.path.basename(silhouette_path)
        print(f"[Model Card Generator] 处理姿势 {idx + 1}/{pose_count}: {silhouette_name}")

        output_path = os.path.join(output_dir, f"modelcard_{int(time.time())}_pose{idx}.png")
        ok = _generate_single_card(model_image_path, silhouette_path, prompt, output_path)

        if ok:
            card_paths.append(output_path)
            print(f"[Model Card Generator] 姿势 {idx + 1} 模卡图已保存: {output_path}")
        else:
            failed_indices.append(idx)
            card_paths.append(None)
            print(f"[Model Card Generator] 姿势 {idx + 1} 生成失败。")

    success_count = sum(1 for p in card_paths if p is not None)
    print(f"[Model Card Generator] 完成：{success_count}/{pose_count} 张成功。")

    return {
        "success": len(failed_indices) == 0,
        "card_paths": card_paths,
        "failed_indices": failed_indices,
    }
