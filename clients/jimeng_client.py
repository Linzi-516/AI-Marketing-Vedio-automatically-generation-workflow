"""Shared client helpers for Jimeng / Volcengine visual APIs."""

import base64
import json
import time
from typing import Callable

import requests

import config
from utils.signing import sign_volcengine_request


class JimengClientError(RuntimeError):
    """Raised when a Jimeng API call fails."""


def image_to_base64(image_path: str) -> str:
    """Read a local image file and return a base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def post_visual_api(
    action: str,
    payload: dict,
    timeout: int = 60,
    path: str = "/",
    version: str = "2022-08-31",
) -> dict:
    """Send a signed POST request to the Volcengine visual API."""
    params = {"Action": action, "Version": version}
    body = json.dumps(payload)
    headers = sign_volcengine_request(
        "POST",
        path,
        params,
        body,
        config.JIMENG_Access_Key_ID,
        config.JIMENG_SECRET_Acess_Key,
    )
    query = "&".join(f"{k}={v}" for k, v in params.items())
    resp = requests.post(
        f"{config.JIMENG_BASE_URL}?{query}",
        headers=headers,
        data=body,
        timeout=timeout,
    )
    if not resp.ok:
        raise JimengClientError(f"HTTP {resp.status_code}, response: {resp.text[:500]}")
    return resp.json()


def ensure_success(result: dict, operation: str) -> dict:
    """Validate the common Jimeng response code and return data."""
    if result.get("code") != 10000:
        raise JimengClientError(
            f"{operation} failed: code={result.get('code')} msg={result.get('message')}"
        )
    return result.get("data", {})


def submit_async_task(payload: dict, operation: str = "Jimeng task") -> str:
    """Submit a CVSync2AsyncSubmitTask request and return task_id."""
    result = post_visual_api("CVSync2AsyncSubmitTask", payload)
    data = ensure_success(result, operation)
    task_id = data.get("task_id")
    if not task_id:
        raise JimengClientError(f"{operation} did not return task_id.")
    return task_id


def poll_task(
    req_key: str,
    task_id: str,
    action: str,
    max_wait: int = 600,
    interval: int = 10,
    initial_delay: int = 5,
    extra_payload: dict | None = None,
    result_getter: Callable[[dict], str] | None = None,
    log_prefix: str = "Jimeng",
) -> str:
    """Poll an async task until done and return a URL or encoded result."""
    payload = {"req_key": req_key, "task_id": task_id}
    if extra_payload:
        payload.update(extra_payload)

    start = time.time()
    if initial_delay:
        time.sleep(initial_delay)

    while time.time() - start < max_wait:
        last_err = None
        for _ in range(3):
            try:
                result = post_visual_api(action, payload, timeout=30)
                last_err = None
                break
            except Exception as exc:
                last_err = exc
                time.sleep(3)
        if last_err:
            raise last_err

        data = ensure_success(result, f"{log_prefix} query")
        status = data.get("status", "")

        if status == "done":
            if result_getter:
                value = result_getter(data)
            else:
                value = data.get("video_url", "")
            if not value:
                raise JimengClientError(f"{log_prefix} task done but result is empty.")
            return value
        if status in ("not_found", "expired"):
            raise JimengClientError(f"{log_prefix} task abnormal: status={status}")

        elapsed = int(time.time() - start)
        print(f"[{log_prefix}] waiting: status={status} elapsed={elapsed}s task_id={task_id[:8]}...")
        time.sleep(interval)

    raise TimeoutError(f"{log_prefix} task timed out after {max_wait}s, task_id={task_id}")


def download_url(url: str, save_path: str, timeout: int = 120) -> None:
    """Download a URL to a local file path."""
    resp = requests.get(url, timeout=timeout, stream=True)
    resp.raise_for_status()
    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


def download_bytes(url: str, timeout: int = 60) -> bytes:
    """Download a URL and return bytes."""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content
