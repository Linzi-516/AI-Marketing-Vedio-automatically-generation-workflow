"""API-facing workflow backend used to bridge checkpoints to REST calls."""

from __future__ import annotations

import threading
from typing import Any

import interactive


class APICheckpointBackend(interactive.IOBackend):
    """IOBackend that pauses workflow execution at structured checkpoints."""

    def __init__(self, task: Any):
        self.task = task

    def display(self, message: str) -> None:
        self.task.add_log(message)

    def prompt(self, message: str, default: str = "") -> str:
        raise RuntimeError("Generic prompt is not supported by the API backend.")

    def confirm(self, message: str) -> bool:
        raise RuntimeError("Generic confirm is not supported by the API backend.")

    def confirm_images(self, image_paths: list, feature_prompt: str, run_dir: str) -> dict:
        response = self._wait_for_checkpoint(
            checkpoint_type="image_confirm",
            payload={
                "image_paths": image_paths,
                "image_urls": self.task.read_state().get("image_urls", []),
                "feature_prompt": feature_prompt,
                "run_dir": run_dir,
            },
            current_step="image",
        )
        action = response.get("action")
        if action not in ("next", "regenerate"):
            raise ValueError("image_confirm action must be 'next' or 'regenerate'.")
        return {
            "action": action,
            "new_prompt": response.get("new_prompt") if action == "regenerate" else None,
        }

    def confirm_script(self, full_script: str, scenes: list) -> dict:
        response = self._wait_for_checkpoint(
            checkpoint_type="script_confirm",
            payload={
                "full_script": full_script,
                "scenes": scenes,
            },
            current_step="script",
        )
        return {
            "action": "modify",
            "full_script": response.get("full_script", full_script),
            "scenes": response.get("scenes", scenes),
        }

    def select_scene_images(
        self,
        scenes: list,
        available_image_paths: list,
        available_image_urls: list,
    ) -> list:
        response = self._wait_for_checkpoint(
            checkpoint_type="scene_image_select",
            payload={
                "scenes": scenes,
                "available_image_paths": available_image_paths,
                "available_image_urls": available_image_urls,
            },
            current_step="video",
        )
        selections = response.get("scene_image_selections")
        if not isinstance(selections, list):
            raise ValueError("scene_image_select requires scene_image_selections list.")
        return selections

    def _wait_for_checkpoint(self, checkpoint_type: str, payload: dict, current_step: str) -> dict:
        self.task.set_waiting(checkpoint_type, payload, current_step=current_step)
        response = self.task.wait_for_checkpoint_response(checkpoint_type)
        self.task.set_running(current_step=current_step)
        return response
