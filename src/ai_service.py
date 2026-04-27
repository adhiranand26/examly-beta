"""
Production-grade AI service with multi-model fallback,
per-provider retry with exponential backoff, Ollama health detection,
answer validation, and response quality verification.
"""
import httpx
import json
import logging
import asyncio
import time
from src.protection import get_protected

logger = logging.getLogger(__name__)

# ── Hallucination / Vague Answer Patterns ──
VAGUE_PATTERNS = [
    "i cannot", "i can't", "i'm not sure", "it depends",
    "not enough information", "unclear", "unable to determine",
    "i don't know", "cannot determine", "n/a",
]


class AIService:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self._ollama_healthy = None  # None = unknown, True/False = checked

    async def process_async(self, img_b64: str, ocr_data: dict) -> dict:
        """
        Production AI pipeline:
        1. Build optimized prompt based on OCR quality
        2. Try each provider in fallback chain with per-provider retry
        3. Validate response quality
        4. Return structured result with timing metadata
        """
        start_time = time.time()
        api_key = str(self.config_manager.get_api_key()).strip()

        ocr_text = ocr_data.get("text", "").strip()
        ocr_conf = ocr_data.get("confidence", 0.0)
        ocr_available = ocr_data.get("ocr_available", True)

        prompt = self._build_prompt(ocr_text, ocr_conf, ocr_available)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a JSON-only exam-solving engine with 100% accuracy on MCQs. "
                    "You MUST analyze every option before answering. "
                    "Think step-by-step internally, but output ONLY the JSON object."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}", "detail": "high"},
                    },
                ],
            },
        ]

        # Try fallback chain
        fallback_chain = self.config_manager.config.ai.fallback_chain
        last_error = ""

        for provider in fallback_chain:
            # Skip Ollama if health check failed
            if provider.name == "ollama":
                if not await self._check_ollama_health(provider.url):
                    logger.warning("Ollama not running, skipping.")
                    continue

            result = await self._call_with_retry(provider, messages, api_key)

            if result and result.get("type") != "error":
                # Validate answer quality
                if self._is_valid_answer(result):
                    elapsed = int((time.time() - start_time) * 1000)
                    result["provider"] = provider.name
                    result["latency_ms"] = elapsed
                    logger.info(
                        f"✅ AI response from {provider.name} in {elapsed}ms: "
                        f"answer={result.get('answer')}, conf={result.get('confidence')}"
                    )
                    return result
                else:
                    logger.warning(f"Provider {provider.name} returned vague/invalid answer, trying next...")
                    last_error = f"{provider.name}: vague answer"
                    continue
            else:
                last_error = result.get("explanation", "unknown") if result else "empty response"

        elapsed = int((time.time() - start_time) * 1000)
        logger.error(f"All AI providers failed after {elapsed}ms. Last error: {last_error}")
        return {
            "answer": "All AI providers failed.",
            "confidence": 0.0,
            "type": "error",
            "explanation": last_error,
            "latency_ms": elapsed,
        }

    def _build_prompt(self, ocr_text: str, ocr_conf: float, ocr_available: bool) -> str:
        """Build optimized prompt based on OCR quality."""

        if not ocr_available or (not ocr_text and ocr_conf == 0.0):
            # No OCR — tell AI to read from image directly
            ocr_section = (
                "OCR was NOT available. You MUST read ALL text directly from the image. "
                "Pay extra attention to the question text, options, and any fine print."
            )
        elif ocr_conf < 0.3 or len(ocr_text) < 10:
            # Low quality OCR — tell AI to verify against image
            ocr_section = (
                f"OCR Text (LOW CONFIDENCE — verify against image):\n{ocr_text}\n\n"
                "WARNING: The OCR text above may contain errors. Cross-reference with the image."
            )
        else:
            ocr_section = f"Extracted OCR Text (confidence: {ocr_conf:.0%}):\n{ocr_text}"

        return f"""You are an elite exam-solving AI. Your accuracy must be 100%.

REASONING PROCESS (do this internally, do NOT output it):
1. Read the question carefully from the image and OCR text
2. Identify the question type (MCQ, math, code, descriptive)
3. For MCQ: Analyze EVERY option. Eliminate wrong ones with reasoning. Pick the BEST.
4. For Math: Compute step-by-step. Double-check your arithmetic.
5. For Code: Trace execution line by line.
6. Verify your answer makes sense before responding.

{ocr_section}

OUTPUT FORMAT — respond with ONLY this JSON object (no markdown, no backticks):
{{
  "answer": "The exact answer (e.g. 'A', 'B', '42', 'True', or the full answer text)",
  "confidence": 0.0 to 1.0,
  "type": "mcq" | "descriptive" | "code" | "math",
  "explanation": "Brief 1-line reasoning"
}}"""

    async def _call_with_retry(self, provider, messages: list, api_key: str, max_retries: int = 2) -> dict:
        """Call a provider with retry and exponential backoff."""
        for attempt in range(max_retries + 1):
            try:
                result = await self._call_provider(provider, messages, api_key)
                return result
            except httpx.TimeoutException:
                logger.warning(f"Provider {provider.name} timeout (attempt {attempt + 1}/{max_retries + 1})")
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                logger.warning(f"Provider {provider.name} HTTP {status} (attempt {attempt + 1}/{max_retries + 1})")
                # Don't retry on 401/403 (auth errors)
                if status in (401, 403):
                    return {"answer": f"Auth error ({status})", "confidence": 0.0, "type": "error", "explanation": str(e)}
            except json.JSONDecodeError as e:
                logger.warning(f"Provider {provider.name} invalid JSON (attempt {attempt + 1}/{max_retries + 1}): {e}")
            except Exception as e:
                logger.warning(f"Provider {provider.name} error (attempt {attempt + 1}/{max_retries + 1}): {e}")

            if attempt < max_retries:
                wait = 1.5 ** attempt  # Exponential backoff: 1s, 1.5s
                await asyncio.sleep(wait)

        return {"answer": f"Provider {provider.name} failed after {max_retries + 1} attempts", "confidence": 0.0, "type": "error", "explanation": ""}

    async def _call_provider(self, provider, messages: list, api_key: str) -> dict:
        """Call a single AI provider."""
        payload = {
            "model": provider.model,
            "messages": messages,
            "max_tokens": self.config_manager.config.ai.max_tokens,
            "temperature": 0.05,
        }

        if provider.name != "ollama":
            payload["response_format"] = {"type": "json_object"}

        headers = {"Content-Type": get_protected("content_type")}
        if provider.name != "ollama" and api_key:
            headers["Authorization"] = f"{get_protected('bearer_prefix')}{api_key}"

        # Per-provider timeout: Ollama gets more time (local inference is slower)
        timeout = 90.0 if provider.name == "ollama" else 45.0

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(provider.url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Clean markdown backticks if AI misbehaves
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            parsed = json.loads(content)
            
            # Ensure all required fields exist
            parsed.setdefault("answer", "")
            parsed.setdefault("confidence", 0.0)
            parsed.setdefault("type", "unknown")
            parsed.setdefault("explanation", "")
            
            return parsed

    def _is_valid_answer(self, result: dict) -> bool:
        """Reject hallucinated, vague, or empty answers."""
        answer = str(result.get("answer", "")).strip().lower()

        if not answer:
            return False

        for pattern in VAGUE_PATTERNS:
            if pattern in answer:
                logger.warning(f"Vague answer detected: '{answer}' matches pattern '{pattern}'")
                return False

        return True

    async def _check_ollama_health(self, base_url: str) -> bool:
        """Check if Ollama server is running and responsive."""
        if self._ollama_healthy is not None:
            return self._ollama_healthy

        # Extract base from chat completions URL
        health_url = base_url.rsplit("/v1/", 1)[0]

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(health_url)
                self._ollama_healthy = resp.status_code == 200
                if self._ollama_healthy:
                    logger.info("Ollama health check: OK")
                else:
                    logger.warning(f"Ollama health check: HTTP {resp.status_code}")
        except Exception as e:
            self._ollama_healthy = False
            logger.warning(f"Ollama health check failed: {e}")

        return self._ollama_healthy
