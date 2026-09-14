"""Gemini client using the project's configured Gemini gateway."""

from __future__ import annotations

import mimetypes
import os
import pathlib
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any


class GeminiError(RuntimeError):
    """Raised when a Gemini request cannot be completed."""


@dataclass
class GeminiResponse:
    """A completed Gemini response with redacted, audit-friendly metadata."""

    text: str
    model: str
    latency_ms: int
    usage: dict[str, Any] = field(default_factory=dict)
    http_status: int | None = None

    def evidence(self, *, input_sha256: Iterable[str] = ()) -> dict[str, Any]:
        """Return metadata suitable for local evidence logs without credentials."""

        return {
            "provider": "gemini",
            "model": self.model,
            "http_status": self.http_status,
            "latency_ms": self.latency_ms,
            "usage": self.usage,
            "input_sha256": list(input_sha256),
            "response_chars": len(self.text),
        }


def _load_env(path: pathlib.Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _image_bytes(item: Any) -> tuple[bytes, str]:
    if isinstance(item, (bytes, bytearray)):
        return bytes(item), "image/png"
    path = pathlib.Path(item)
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return path.read_bytes(), mime


class GeminiClient:
    """Call Gemini through the configured native SDK endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        *,
        env_path: pathlib.Path | None = None,
        timeout_s: int = 600,
    ) -> None:
        root = pathlib.Path(__file__).resolve().parents[3]
        env = _load_env(env_path or root / ".env")
        self.api_key = api_key or env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
        if not self.api_key:
            raise ValueError("missing GEMINI_API_KEY (.env or environment)")
        self.base_url = (
            base_url or env.get("GEMINI_BASE_URL") or os.environ.get("GEMINI_BASE_URL", "")
        ).rstrip("/")
        if not self.base_url:
            raise ValueError("missing GEMINI_BASE_URL (.env or environment)")
        self.timeout_s = timeout_s
        for key in ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"):
            if env.get(key) and not os.environ.get(key):
                os.environ[key] = env[key]

    def generate(
        self,
        prompt: str,
        *,
        model: str = "gemini-3.8-flash",
        images: Iterable[Any] = (),
        max_output_tokens: int = 2000,
        temperature: float | None = 0.0,
        system_instruction: str | None = None,
        thinking_level: str | None = None,
    ) -> GeminiResponse:
        """Generate text from Gemini with optional inline images."""

        from google import genai
        from google.genai import types

        parts = [types.Part(text=prompt)]
        for image in images:
            data, mime = _image_bytes(image)
            parts.append(types.Part(inline_data=types.Blob(mime_type=mime, data=data)))

        config: dict[str, Any] = {"max_output_tokens": max_output_tokens}
        if temperature is not None:
            config["temperature"] = temperature
        if system_instruction:
            config["system_instruction"] = system_instruction
        if thinking_level:
            config["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)

        started = time.time()
        try:
            client = genai.Client(
                api_key=self.api_key,
                vertexai=True,
                http_options={
                    "base_url": f"{self.base_url}/gemini/",
                    "timeout": self.timeout_s * 1000,
                },
            )
            response = client.models.generate_content(
                model=model,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(**config),
            )
        except Exception as exc:
            raise GeminiError(f"Gemini request failed for {model}: {exc}") from exc

        usage: dict[str, Any] = {}
        metadata = getattr(response, "usage_metadata", None)
        if metadata:
            usage = {
                "prompt_tokens": getattr(metadata, "prompt_token_count", None),
                "completion_tokens": getattr(metadata, "candidates_token_count", None),
                "total_tokens": getattr(metadata, "total_token_count", None),
                "thoughts_tokens": getattr(metadata, "thoughts_token_count", None),
            }
        return GeminiResponse(
            text=(response.text or "").strip(),
            model=model,
            latency_ms=int((time.time() - started) * 1000),
            usage=usage,
            http_status=200,
        )
