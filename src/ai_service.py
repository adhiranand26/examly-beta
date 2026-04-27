import httpx
import json
import logging

class AIService:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        
    async def process_async(self, img_b64: str, ocr_data: dict) -> dict:
        """
        Structured JSON response using advanced prompting and strictly validated output.
        """
        api_key = self.config_manager.get_api_key()
        if not api_key:
            return {"answer": "No API key configured.", "confidence": 0.0, "type": "error"}

        prompt = f"""
You are an expert exam solver. You must return your analysis strictly as a JSON object matching this schema:
{{
  "answer": "The final exact answer (e.g. 'A', '42', 'The mitochondria')",
  "confidence": 0.0 to 1.0 (float),
  "type": "mcq" | "descriptive" | "code" | "math"
}}
DO NOT include markdown formatting, backticks, or <think> tags. ONLY JSON.

Extracted OCR Text:
{ocr_data.get('text', '')}
        """

        payload = {
            "model": self.config_manager.config.ai.model,
            "messages": [
                {"role": "system", "content": "You are a JSON-only response engine."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}", "detail": "low"}}
                    ]
                }
            ],
            "max_tokens": self.config_manager.config.ai.max_tokens,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        # Compatible with OpenAI format endpoints
        url = "https://api.openai.com/v1/chat/completions"
        if self.config_manager.config.ai.provider == "inceptionlabs":
             url = "https://api.inceptionlabs.ai/v1/chat/completions"
             
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                return json.loads(content)
            except Exception as e:
                logging.error(f"AI Service Error: {e}")
                return {"answer": f"API Error: {str(e)}", "confidence": 0.0, "type": "error"}
