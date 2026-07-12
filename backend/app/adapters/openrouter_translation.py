import httpx
import time
from app.core.config import settings
from app.core.interfaces.translation import BaseTranslationProvider


class OpenRouterTranslationProvider(BaseTranslationProvider):
    """
    Implementation of BaseTranslationProvider using OpenRouter API.
    Provides async, low-latency translation using a lightweight LLM.
    """

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_TRANSLATION_MODEL
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def translate_text(
        self, 
        text: str, 
        source_lang: str = "auto", 
        target_lang: str = "ru"
    ) -> str:
        if not text.strip():
            return ""

        print(f"Translation provider: OpenRouterTranslationProvider")
        print(f"Model: {self.model}")
        print(f"Source language: {source_lang}")
        print(f"Target language: {target_lang}")

        # Construct the system message specifying strict translation constraints
        system_prompt = (
            f"You are a professional real-time translator translating to target language '{target_lang}'.\n"
            "Translate text exactly.\n"
            "If the input is already in the target language, return it unchanged.\n"
            "Do not summarize.\n"
            "Do not explain.\n"
            "Do not improve grammar.\n"
            "Do not answer questions.\n"
            "Do not continue sentences.\n"
            "Keep speaker meaning unchanged.\n"
            "Return ONLY translated text.\n"
            "Nothing else."
        )

        user_message = f"Text: {text}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 128
        }

        start_time = time.time()
        try:
            response = await self.client.post(self.base_url, headers=headers, json=payload)
            
            if response.status_code != 200:
                raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")
                
            result = response.json()
            translated_text = result["choices"][0]["message"]["content"].strip()
            
            # Strip potential markdown code block backticks if LLM mistakenly added them
            if translated_text.startswith("```") and translated_text.endswith("```"):
                lines = translated_text.splitlines()
                if len(lines) >= 3:
                    translated_text = "\n".join(lines[1:-1]).strip()

            duration_ms = int((time.time() - start_time) * 1000)
            print(f"Translation completed in {duration_ms} ms")
            return translated_text
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            print(f"Translation failed after {duration_ms} ms: {e}")
            raise
