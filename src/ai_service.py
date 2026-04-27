"""
Robust Multi-Model Fallback AI Service
- Intelligent provider re-prioritization
- Provider-specific header management
- Async health checks (Ollama/API keys)
- Fuzzy JSON extraction
- Deep debug logging
"""
import httpx
import json
import logging
import asyncio
import time
import re
from src.protection import get_protected

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, config_manager):
        self.config_manager = config_manager

    async def process_async(self, img_b64: str, ocr_data: dict) -> dict:
        """
        Orchestrates a robust fallback chain. Tries each valid provider 
        until one succeeds or the chain is exhausted.
        """
        start_time = time.time()
        api_key = str(self.config_manager.get_api_key()).strip()
        
        # 1. Prepare prioritization (Selected provider first)
        selected_name = self.config_manager.config.ai.provider
        full_chain = self.config_manager.config.ai.fallback_chain
        
        # Reorder: Selected -> others
        chain = sorted(full_chain, key=lambda p: p.name != selected_name)
        
        prompt = (
            "You are an exam-solving engine. Analyze the image and OCR text. "
            "Output ONLY a JSON object. No explanation outside JSON.\n"
            f"OCR Context: {ocr_data.get('text', '')}"
        )
        
        messages = [
            {"role": "system", "content": "You are a professional exam assistant. Respond ONLY with JSON."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}", "detail": "high"}}
            ]}
        ]

        last_error = "No providers attempted."
        
        # 2. Iterate through fallback chain
        for provider in chain:
            # --- Health Check: Skip if Key Missing ---
            if provider.name != "ollama" and not api_key:
                logger.warning(f"[AI] Skipping {provider.name}: No API key provided.")
                last_error = "API Key missing in settings."
                continue
                
            # --- Health Check: Skip if Ollama Offline ---
            if provider.name == "ollama":
                if not await self._is_ollama_online(provider.url):
                    logger.warning(f"[AI] Skipping {provider.name}: Server unreachable.")
                    last_error = "Ollama is not running locally."
                    continue

            # 3. Attempt API Call
            try:
                logger.info(f"[AI] Attempting {provider.name}...")
                
                result = await self._call_provider_with_retry(provider, messages, api_key)
                
                if result:
                    total_time = int((time.time() - start_time) * 1000)
                    result.update({"provider": provider.name, "latency_ms": total_time})
                    logger.info(f"[AI] Success with {provider.name} in {total_time}ms")
                    return result

            except Exception as e:
                last_error = str(e)
                logger.error(f"[AI] Provider {provider.name} failed: {last_error}")
                continue

        # 4. Final Failure State
        logger.critical(f"[AI] All providers in chain failed. Last error: {last_error}")
        return {
            "answer": "All AI providers failed.",
            "confidence": 0.0,
            "type": "error",
            "explanation": f"Check API key or internet. (Last Error: {last_error})"
        }

    async def _call_provider_with_retry(self, provider, messages, api_key):
        """Internal call logic with a single retry on timeout."""
        for attempt in [1, 2]:
            try:
                # Build Headers
                headers = {"Content-Type": get_protected("content_type")}
                if provider.name != "ollama" and api_key:
                    if "gemini" in provider.name.lower():
                        headers["x-goog-api-key"] = api_key
                    else:
                        headers["Authorization"] = f"{get_protected('bearer_prefix')}{api_key}"

                # Build Payload
                payload = {
                    "model": provider.model,
                    "messages": messages,
                    "temperature": 0.05,
                    "max_tokens": self.config_manager.config.ai.max_tokens
                }
                if provider.name == "openai":
                    payload["response_format"] = {"type": "json_object"}

                # Request
                timeout = httpx.Timeout(90.0 if provider.name == "ollama" else 45.0, connect=5.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(provider.url, json=payload, headers=headers)
                    
                    if resp.status_code != 200:
                        logger.error(f"[AI] {provider.name} HTTP {resp.status_code}: {resp.text[:100]}")
                        resp.raise_for_status()

                    raw_content = resp.json()["choices"][0]["message"]["content"].strip()
                    return self._fuzzy_json_parse(raw_content)

            except (httpx.TimeoutException, httpx.ReadTimeout) as e:
                if attempt == 1:
                    logger.warning(f"[AI] {provider.name} timed out, retrying...")
                    continue
                raise e
            except Exception as e:
                raise e
        return None

    def _fuzzy_json_parse(self, text: str) -> dict:
        """Extracts JSON even if the AI adds conversational text."""
        # Try direct parse first
        try:
            return json.loads(text)
        except:
            pass

        # Try to find anything between { and }
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        # Last resort: Strip markdown tags
        clean = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean)
        except Exception as e:
            logger.error(f"[AI] Failed to parse fuzzy JSON: {text[:100]}")
            raise ValueError(f"AI returned invalid JSON format: {str(e)}")

    async def _is_ollama_online(self, url: str) -> bool:
        """Rapid health check for Ollama (<2s)."""
        base = url.rsplit("/v1/", 1)[0]
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(base)
                return resp.status_code == 200
        except:
            return False
