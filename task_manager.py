"""In-memory task manager for the internal REST API."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import config
import workflow
from api_backend import APICheckpointBackend


TERMINAL_STATUSES = {"completed", "failed"}


@dataclass
class RunTask:
    run_id: str
    request: dict
    status: str = "queued"
    current_step: str | None = None
    pending_checkpoint: dict | None = None
    error: str | None = None
    result: dict | None = None
    logs: list[str] = field(default_factory=list)
    _condition: threading.Condition = field(default_factory=threading.Condition)
    _checkpoint_response: dict | None = None

    @property
    def run_dir(self) -> str:
        return os.path.join(config.OUTPUT_DIR, self.run_id)

    def add_log(self, message: str) -> None:
        with self._condition:
            self.logs.append(message)

    def set_running(self, current_step: str | None = None) -> None:
        with self._condition:
            if self.status not in TERMINAL_STATUSES:
                self.status = "running"
            if current_step:
                self.current_step = current_step
            self.pending_checkpoint = None
            self._checkpoint_response = None
            self._condition.notify_all()

    def set_waiting(self, checkpoint_type: str, payload: dict, current_step: str | None = None) -> None:
        with self._condition:
            self.status = "waiting_user"
            self.current_step = current_step
            self.pending_checkpoint = {
                "type": checkpoint_type,
                "payload": payload,
            }
            self._checkpoint_response = None
            self._condition.notify_all()

    def submit_checkpoint_response(self, checkpoint_type: str, response: dict) -> None:
        with self._condition:
            if self.status != "waiting_user" or not self.pending_checkpoint:
                raise ValueError("Run is not waiting for a checkpoint.")
            if self.pending_checkpoint.get("type") != checkpoint_type:
                raise ValueError(
                    f"Checkpoint type mismatch: expected {self.pending_checkpoint.get('type')}, got {checkpoint_type}."
                )
            self._checkpoint_response = response
            self._condition.notify_all()

    def wait_for_checkpoint_response(self, checkpoint_type: str) -> dict:
        with self._condition:
            while self._checkpoint_response is None and self.status not in TERMINAL_STATUSES:
                self._condition.wait()
            if self.status in TERMINAL_STATUSES and self._checkpoint_response is None:
                raise RuntimeError("Run ended before checkpoint response was submitted.")
            response = self._checkpoint_response or {}
            if response.get("type") != checkpoint_type:
                raise ValueError(f"Expected checkpoint response type {checkpoint_type}.")
            return response

    def mark_completed(self, result: dict) -> None:
        with self._condition:
            self.status = "completed"
            self.current_step = "completed"
            self.pending_checkpoint = None
            self.result = result
            self._condition.notify_all()

    def mark_failed(self, exc: Exception) -> None:
        with self._condition:
            self.status = "failed"
            self.error = str(exc)
            self.pending_checkpoint = None
            self._condition.notify_all()

    def read_state(self) -> dict:
        state_path = os.path.join(self.run_dir, "state.json")
        if not os.path.exists(state_path):
            return {}
        with open(state_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)

    def snapshot(self) -> dict:
        state = self.read_state()
        with self._condition:
            return {
                "run_id": self.run_id,
                "status": self.status,
                "current_step": self.current_step or infer_current_step(state, self.pending_checkpoint),
                "pending_checkpoint": self.pending_checkpoint["type"] if self.pending_checkpoint else None,
                "progress": build_progress(state),
                "error": self.error,
                "request": self.request,
            }


class TaskManager:
    def __init__(self):
        self._tasks: dict[str, RunTask] = {}
        self._lock = threading.Lock()

    def create_run(self, payload: dict) -> RunTask:
        run_id = payload.get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S")
        with self._lock:
            existing = self._tasks.get(run_id)
            if existing and existing.status not in TERMINAL_STATUSES:
                raise ValueError(f"Run {run_id} is already active.")
            task = RunTask(run_id=run_id, request={**payload, "run_id": run_id})
            self._tasks[run_id] = task

        thread = threading.Thread(target=self._run_workflow, args=(task,), daemon=True)
        thread.start()
        return task

    def get_task(self, run_id: str) -> RunTask | None:
        with self._lock:
            return self._tasks.get(run_id)

    def get_or_restore_task(self, run_id: str) -> RunTask:
        task = self.get_task(run_id)
        if task:
            return task
        run_dir = os.path.join(config.OUTPUT_DIR, run_id)
        if not os.path.exists(run_dir):
            raise KeyError(run_id)
        state = read_run_state(run_dir)
        request = state.get("_request") or {"run_id": run_id}
        status = "completed" if "video_paths" in state else "failed"
        restored = RunTask(
            run_id=run_id,
            request={**request, "run_id": run_id},
            status=status,
            current_step=infer_current_step(state),
            error=None if status == "completed" else "Run exists on disk but is not active.",
        )
        with self._lock:
            self._tasks[run_id] = restored
        return restored

    def list_runs(self) -> list[dict]:
        run_ids = set()
        with self._lock:
            run_ids.update(self._tasks.keys())

        if os.path.exists(config.OUTPUT_DIR):
            for name in os.listdir(config.OUTPUT_DIR):
                run_dir = os.path.join(config.OUTPUT_DIR, name)
                state_path = os.path.join(run_dir, "state.json")
                if os.path.isdir(run_dir) and os.path.exists(state_path):
                    run_ids.add(name)

        runs = []
        for run_id in run_ids:
            try:
                runs.append(self.get_or_restore_task(run_id).snapshot())
            except (KeyError, json.JSONDecodeError, OSError):
                continue
        return sorted(runs, key=lambda item: item["run_id"], reverse=True)

    def submit_checkpoint(self, run_id: str, response: dict) -> RunTask:
        task = self.get_or_restore_task(run_id)
        checkpoint_type = response.get("type")
        if not checkpoint_type:
            raise ValueError("Checkpoint response requires type.")
        task.submit_checkpoint_response(checkpoint_type, response)
        return task

    def _run_workflow(self, task: RunTask) -> None:
        task.set_running(current_step="story")
        backend = APICheckpointBackend(task)
        try:
            result = workflow.run(
                product_name=task.request["product_name"],
                product_offer=task.request["product_offer"],
                target_audience=task.request["target_audience"],
                pain_points=task.request["pain_points"],
                total_duration=int(task.request.get("total_duration") or 30),
                run_id=task.run_id,
                io_backend=backend,
            )
            task.mark_completed(result)
        except Exception as exc:
            task.mark_failed(exc)


def build_progress(state: dict) -> dict:
    completed_steps = []
    step_keys = [
        ("story", "story"),
        ("feature", "feature_prompt"),
        ("image", "image_paths"),
        ("voice", "voice_type"),
        ("script", "scenes"),
        ("tts", "audio_paths"),
        ("scene_image_select", "scene_image_selections"),
        ("video", "video_paths"),
        ("model_card", "card_paths"),
    ]
    for step, key in step_keys:
        if key in state:
            completed_steps.append(step)
    return {
        "completed_steps": completed_steps,
        "total_scenes": state.get("total_scenes", len(state.get("scenes", [])) if state else 0),
    }


def infer_current_step(state: dict, pending_checkpoint: dict | None = None) -> str | None:
    if pending_checkpoint:
        checkpoint_type = pending_checkpoint.get("type")
        if checkpoint_type == "image_confirm":
            return "image"
        if checkpoint_type == "script_confirm":
            return "script"
        if checkpoint_type == "scene_image_select":
            return "video"
    if not state:
        return "queued"
    if "video_paths" in state:
        return "completed"
    if "audio_paths" in state:
        return "video"
    if "scenes" in state:
        return "script"
    if "image_paths" in state:
        return "image"
    if "story" in state:
        return "story"
    return "queued"


def read_run_state(run_dir: str) -> dict:
    state_path = os.path.join(run_dir, "state.json")
    if not os.path.exists(state_path):
        return {}
    with open(state_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


task_manager = TaskManager()
