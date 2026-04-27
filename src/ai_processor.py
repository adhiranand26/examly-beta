"""
AI processing module.
Routes extracted text / images to configurable AI providers.
Supports: Gemini, OpenAI, Mistral, InceptionLabs (mercury-2).
"""

import base64
import json
import re
from pathlib import Path
from typing import Optional

import httpx

from src.config import AIConfig

# ── System prompt ──────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are an expert exam solver. You MUST provide 100% accurate answers.

CRITICAL RULES:
1. You MUST first think step-by-step to solve the problem and wrap ALL your reasoning inside <think>...</think> tags. Double-check your work for 100% accuracy.
2. If an image is provided, trust the image content OVER any extracted OCR text, as the OCR text may contain errors.
3. After your <think> tags, provide ONLY the final exact answer. 
4. Outside of the <think> tags: NO explanations, NO steps, NO code blocks, NO LaTeX formatting.
5. For math, just give the final numerical answer or expression.
6. For multiple choice, just give the correct option letter AND the text (e.g. "A) 42").
7. If none of the options are exactly correct, output the closest option or just output the final calculated mathematical value. DO NOT output 'None' or empty strings.
"""


class AIProcessor:
    """Unified interface to Gemini / OpenAI / Mistral / InceptionLabs APIs."""

    def __init__(self, config: AIConfig) -> None:
        self.config = config
        self._client = httpx.AsyncClient(timeout=120.0)

    async def close(self) -> None:
        await self._client.aclose()

    # ── Public API ─────────────────────────────────────────────────────
    async def process_text(self, text: str) -> str:
        if not self.config.enabled:
            return "[AI disabled]"
        if not self.config.api_key and self.config.provider != "ollama":
            return "[No API key configured]"
        return await self._dispatch(text=text)

    async def process_image(self, image_path: Path, text: Optional[str] = None) -> str:
        if not self.config.enabled:
            return "[AI disabled]"
        if not self.config.api_key and self.config.provider != "ollama":
            return "[No API key configured]"
        return await self._dispatch(text=text, image_path=image_path)

    # ── Router ─────────────────────────────────────────────────────────
    async def _dispatch(self, text: Optional[str] = None,
                        image_path: Optional[Path] = None) -> str:
        try:
            provider = self.config.provider
            if provider == "gemini":
                return await self._call_gemini(text, image_path)
            elif provider == "openai":
                return await self._call_openai_compat(
                    text, image_path,
                    url="https://api.openai.com/v1/chat/completions",
                )
            elif provider == "mistral":
                return await self._call_openai_compat(
                    text, image_path,
                    url="https://api.mistral.ai/v1/chat/completions",
                )
            elif provider == "inceptionlabs":
                return await self._call_openai_compat(
                    text, image_path,
                    url="https://api.inceptionlabs.ai/v1/chat/completions",
                )
            elif provider == "ollama":
                return await self._call_openai_compat(
                    text, image_path,
                    url="http://127.0.0.1:11434/v1/chat/completions",
                )
            else:
                return f"[Unknown provider: {provider}]"
        except Exception as e:
            return f"[AI Error] {type(e).__name__}: {e}"

    # ── Gemini ─────────────────────────────────────────────────────────
    async def _call_gemini(self, text: Optional[str],
                           image_path: Optional[Path]) -> str:
        model = self.config.get_default_model()
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
            f":generateContent?key={self.config.api_key}"
        )

        parts: list = [{"text": SYSTEM_PROMPT}]
        if text:
            parts.append({"text": text})
        if image_path:
            b64 = self._encode_image(image_path)
            parts.append({
                "inline_data": {"mime_type": "image/png", "data": b64}
            })

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "maxOutputTokens": self.config.max_tokens,
                "temperature": 0.3,
            },
        }

        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts_out = candidates[0].get("content", {}).get("parts", [])
            ans = "".join(p.get("text", "") for p in parts_out).strip()
            # Strip out <think> tags
            ans = re.sub(r"<think>.*?</think>", "", ans, flags=re.DOTALL).strip()
            return ans
        return "[No response from Gemini]"

    # ── OpenAI-compatible (OpenAI / Mistral / InceptionLabs) ───────────
    async def _call_openai_compat(self, text: Optional[str],
                                   image_path: Optional[Path],
                                   url: str) -> str:
        model = self.config.get_default_model()

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Determine if we should send the image
        is_vision = False
        if image_path:
            if self.config.provider == "gemini":
                is_vision = True
            elif self.config.provider == "ollama" and any(v in model.lower() for v in ["moondream", "llava", "vision"]):
                is_vision = True

        # Build user message
        if is_vision:
            # Vision-capable providers: send image and prompt
            content = []
            prompt = text if text else "Please solve or answer the question shown in the image."
            content.append({"type": "text", "text": prompt})
            
            b64 = self._encode_image(image_path)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "low"},
            })
            messages.append({"role": "user", "content": content})
        else:
            # Text-only providers (InceptionLabs mercury-2)
            user_text = text or "(no text extracted from screenshot)"
            messages.append({"role": "user", "content": user_text})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": 0.3,
        }

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        resp = await self._client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        ans = data["choices"][0]["message"]["content"].strip()
        
        # Strip out <think> tags
        ans = re.sub(r"<think>.*?</think>", "", ans, flags=re.DOTALL).strip()
        return ans

    # ── Helpers ────────────────────────────────────────────────────────
    @staticmethod
    def _encode_image(path: Path) -> str:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
