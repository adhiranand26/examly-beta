"""
Production-grade AI service with smart fallback.
Handles multi-model prioritization, per-provider retry, 
and unique header formats for OpenAI vs Gemini vs Ollama.
"""
import httpx
import json
import logging
import asyncio
import time
from src.protection import get_protected

logger = logging.getLogger(__name__)

VAGUE_PATTERNS = ["i cannot", "i can't", "i'm not sure", "it depends", "not enough information", "unclear", "i don't know"]

class AIService:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self._ollama_healthy = None

    async def process_async(self, img_b64: str, ocr_data: dict) -> dict:
        start_time = time.time()
        api_key = str(self.config_manager.get_api_key()).strip()
        
        # 1. Build prioritized chain (Selected provider FIRST)
        selected_name = self.config_manager.config.ai.provider
        fallback_chain = self.config_manager.config.ai.fallback_chain
        
        # Reorder chain to put selected provider at index 0
        chain = sorted(fallback_chain, key=lambda p: p.name != selected_name)
        
        prompt = self._build_prompt(ocr_data)
        messages = [
            {"role": "system", "content": "You are a JSON-only exam engine. Analyze every option. Pick the best."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}", "detail": "high"}}
            ]}
        ]

        last_error = ""
        for provider in chain:
            if provider.name == "ollama" and not await self._check_ollama_health(provider.url):
                continue

            logger.info(f"Trying AI provider: {provider.name}")
            result = await self._call_with_retry(provider, messages, api_key)
            
            if result and result.get("type") != "error":
                if self._is_valid_answer(result):
                    elapsed = int((time.time() - start_time) * 1000)
                    result.update({"provider": provider.name, "latency_ms": elapsed})
                    return result
                last_error = f"{provider.name}: vague answer"
            else:
                last_error = result.get("explanation", "unknown error")

        return {
            "answer": "All AI providers failed.",
            "confidence": 0.0,
            "type": "error",
            "explanation": f"Last error: {last_error}"
        }

    async def _call_with_retry(self, provider, messages, api_key, max_retries=1):
        err_msg = ""
        for attempt in range(max_retries + 1):
            try:
                # ── Prepare Headers ──
                headers = {"Content-Type": get_protected("content_type")}
                
                if provider.name != "ollama" and api_key:
                    if "gemini" in provider.name.lower():
                        headers["x-goog-api-key"] = api_key
                    else:
                        headers["Authorization"] = f"{get_protected('bearer_prefix')}{api_key}"

                # ── Prepare Payload ──
                payload = {
                    "model": provider.model,
                    "messages": messages,
                    "max_tokens": self.config_manager.config.ai.max_tokens,
                    "temperature": 0.05
                }
                if provider.name == "openai":
                    payload["response_format"] = {"type": "json_object"}

                # ── Execute ──
                timeout = 90.0 if provider.name == "ollama" else 45.0
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(provider.url, json=payload, headers=headers)
                    resp.raise_for_status()
                    content = resp.json()["choices"][0]["message"]["content"].strip()
                    if content.startswith("```"):
                        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                    return json.loads(content)
                    
            except Exception as e:
                err_msg = str(e)
                if attempt < max_retries: await asyncio.sleep(1)
        
        return {"type": "error", "explanation": err_msg}

    def _build_prompt(self, ocr_data):
        text = ocr_data.get("text", "")
        return f"Solve this exam question. Analyze all options. Output JSON ONLY.\nOCR: {text}"

    def _is_valid_answer(self, res):
        ans = str(res.get("answer", "")).lower()
        return bool(ans) and not any(p in ans for p in VAGUE_PATTERNS)

    async def _check_ollama_health(self, url):
        try:
            async with httpx.AsyncClient(timeout=2.0) as c:
                return (await c.get(url.rsplit("/v1/", 1)[0])).status_code == 200
        except: return False
