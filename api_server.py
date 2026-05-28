"""FastAPI entrypoint for the internal workflow tool."""

from __future__ import annotations

import importlib
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import config
from task_manager import task_manager


app = FastAPI(title="AI Ad Video Workflow API", version="0.1.0")


class CreateRunRequest(BaseModel):
    product_name: str
    product_offer: str
    target_audience: str
    pain_points: str
    total_duration: int = Field(default=30, ge=1)
    run_id: str | None = None


class CheckpointSubmitRequest(BaseModel):
    type: str
    action: str | None = None
    new_prompt: str | None = None
    full_script: str | None = None
    scenes: list[dict[str, Any]] | None = None
    scene_image_selections: list[dict[str, Any]] | None = None


@app.post("/api/runs")
def create_run(request: CreateRunRequest):
    _reload_runtime_config()
    try:
        task = task_manager.create_run(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {
        "run_id": task.run_id,
        "status": "queued",
    }


@app.get("/api/runs")
def list_runs():
    return {
        "runs": task_manager.list_runs(),
    }


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    try:
        task = task_manager.get_or_restore_task(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found.")
    return task.snapshot()


@app.get("/api/runs/{run_id}/checkpoint")
def get_checkpoint(run_id: str):
    try:
        task = task_manager.get_or_restore_task(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found.")
    if task.status != "waiting_user" or not task.pending_checkpoint:
        raise HTTPException(status_code=404, detail="Run is not waiting for a checkpoint.")
    return task.pending_checkpoint


@app.post("/api/runs/{run_id}/checkpoint")
def submit_checkpoint(run_id: str, request: CheckpointSubmitRequest):
    try:
        task = task_manager.submit_checkpoint(run_id, request.model_dump(exclude_none=True))
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "run_id": task.run_id,
        "status": "running",
    }


@app.get("/api/runs/{run_id}/artifacts")
def get_artifacts(run_id: str):
    try:
        task = task_manager.get_or_restore_task(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found.")
    state = task.read_state()
    return {
        "run_id": run_id,
        "run_dir": task.run_dir,
        "images": _compact_paths(state.get("image_paths", []), run_id),
        "audios": _compact_paths(state.get("audio_paths", []), run_id),
        "videos": _compact_paths(state.get("video_paths", []), run_id),
        "model_cards": _compact_paths(state.get("card_paths", []), run_id),
        "request": task.request,
        "state": state,
    }


@app.get("/api/runs/{run_id}/files/{filename}")
def get_run_file(run_id: str, filename: str):
    try:
        task = task_manager.get_or_restore_task(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found.")
    safe_name = os.path.basename(filename)
    file_path = os.path.abspath(os.path.join(task.run_dir, safe_name))
    run_dir = os.path.abspath(task.run_dir)
    if not file_path.startswith(run_dir + os.sep) or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(file_path)


@app.get("/api/config")
def get_config():
    _reload_runtime_config()
    return {
        "video_engine": config.VIDEO_ENGINE,
        "qwen_model": config.QWEN_MODEL,
        "jimeng_image_model": config.JIMENG_IMAGE_MODEL,
        "omni_video_model": config.OMNI_VIDEO_MODEL,
        "output_dir": _safe_display_value(config.OUTPUT_DIR),
        "scene_min_duration": config.SCENE_MIN_DURATION,
        "scene_max_duration": config.SCENE_MAX_DURATION,
    }


@app.get("/api/config/status")
def get_config_status():
    _reload_runtime_config()
    items = [
        _config_item("QWEN_API_KEY", "千问 API Key", config.QWEN_API_KEY, ["story", "feature", "script", "voice"]),
        _config_item("JIMENG_Access_Key_ID", "火山引擎 Access Key ID", config.JIMENG_Access_Key_ID, ["image", "video", "model_card", "tos"]),
        _config_item("JIMENG_SECRET_Acess_Key", "火山引擎 Secret Access Key", config.JIMENG_SECRET_Acess_Key, ["image", "video", "model_card", "tos"]),
        _config_item("TTS_APP_ID", "TTS App ID", config.TTS_APP_ID, ["tts", "omni_video"]),
        _config_item("TTS_ACCESS_TOKEN", "TTS Access Token", config.TTS_ACCESS_TOKEN, ["tts", "omni_video"]),
        _config_item("TOS_BUCKET", "TOS 存储桶", config.TOS_BUCKET, ["omni_video"]),
        _path_item("OUTPUT_DIR", "输出目录", config.OUTPUT_DIR, ["artifacts"]),
        _silhouette_item("MODELCARD_SILHOUETTE_PATHS", "模卡图剪影路径", config.MODELCARD_SILHOUETTE_PATHS, ["model_card"]),
    ]
    return {
        "overall_status": "ready" if all(item["configured"] for item in items) else "incomplete",
        "items": items,
    }


def _compact_paths(paths: list, run_id: str) -> list[dict[str, Any]]:
    result = []
    for path in paths or []:
        if not path:
            continue
        name = os.path.basename(path)
        result.append({
            "path": path,
            "name": name,
            "exists": os.path.exists(path),
            "url": f"/api/runs/{run_id}/files/{name}",
        })
    return result


def _reload_runtime_config() -> None:
    importlib.reload(config)


def _config_item(key: str, label: str, value: Any, required_for: list[str]) -> dict[str, Any]:
    configured = _is_configured_value(value)
    return {
        "key": key,
        "label": label,
        "configured": configured,
        "required_for": required_for,
        "message": "已配置" if configured else "未配置或仍为占位值",
    }


def _path_item(key: str, label: str, value: Any, required_for: list[str]) -> dict[str, Any]:
    configured = _is_configured_value(value)
    exists = os.path.isdir(value) if configured else False
    if not configured:
        message = "未配置或仍为占位值"
    elif exists:
        message = "目录已存在"
    else:
        message = "已配置，目录将在运行时创建或需手动确认"
    return {
        "key": key,
        "label": label,
        "configured": configured,
        "required_for": required_for,
        "message": message,
    }


def _silhouette_item(key: str, label: str, values: list[str], required_for: list[str]) -> dict[str, Any]:
    configured_paths = [path for path in values if _is_configured_value(path)]
    existing_count = sum(1 for path in configured_paths if os.path.exists(path))
    configured = len(configured_paths) == len(values) and existing_count == len(values)
    if configured:
        message = f"已配置 {existing_count}/{len(values)} 个文件"
    elif configured_paths:
        message = f"已填写 {len(configured_paths)}/{len(values)} 个路径，存在 {existing_count}/{len(values)} 个文件"
    else:
        message = "未配置或仍为示例路径"
    return {
        "key": key,
        "label": label,
        "configured": configured,
        "required_for": required_for,
        "message": message,
    }


def _is_configured_value(value: Any) -> bool:
    if value is None:
        return False
    if not isinstance(value, str):
        return bool(value)
    stripped = value.strip()
    if not stripped:
        return False
    lowered = stripped.lower()
    placeholders = [
        "your_",
        "your-",
        "your ",
        "c:\\path\\to\\",
        "c:/path/to/",
    ]
    return not any(lowered.startswith(prefix) for prefix in placeholders)


def _safe_display_value(value: str) -> str:
    return "<configured>" if _is_configured_value(value) else value
