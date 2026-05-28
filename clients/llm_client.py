"""
Unified LLM client wrapper.

Nodes keep prompt construction and business parsing locally, while this module
owns the OpenAI-compatible chat call details for Qwen/DashScope.
"""

from openai import OpenAI

import config


class LLMClientError(RuntimeError):
    """Raised when an LLM call returns an invalid response."""


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    model: str | None = None,
) -> str:
    """Run a chat completion and return stripped text from the first choice."""
    client = OpenAI(
        api_key=config.QWEN_API_KEY,
        base_url=config.QWEN_BASE_URL,
    )

    response = client.chat.completions.create(
        model=model or config.QWEN_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )

    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError) as exc:
        raise LLMClientError("LLM response did not contain a valid message.") from exc

    if not content:
        raise LLMClientError("LLM response content is empty.")

    return content.strip()
