import httpx
from app.core.config import settings
from app.core.interfaces.translation import BaseTranslationProvider


class DeepLTranslationProvider(BaseTranslationProvider):
    """
    Implementation of BaseTranslationProvider using DeepL Translator API.
    """

    def __init__(self):
        self.api_key = settings.DEEPL_API_KEY
        # DeepL API endpoint changes based on the key type (:fx is free)
        if self.api_key.endswith(":fx"):
            self.base_url = "https://api-free.deepl.com/v2/translate"
        else:
            self.base_url = "https://api.deepl.com/v2/translate"

    async def translate_text(
        self, 
        text: str, 
        source_lang: str = "auto", 
        target_lang: str = "ru"
    ) -> str:
        if not text.strip():
            return ""
        
        # DeepL expects ISO language codes (e.g. 'EN' or 'RU')
        # Map auto to None
        source = None if source_lang.lower() == "auto" else source_lang.upper()
        target = target_lang.upper()

        headers = {"Authorization": f"DeepL-Auth-Key {self.api_key}"}
        data = {
            "text": [text],
            "target_lang": target
        }
        if source:
            data["source_lang"] = source

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(self.base_url, headers=headers, json=data)
            
            if response.status_code != 200:
                # Log or raise exception
                raise Exception(f"DeepL API error: {response.status_code} - {response.text}")
                
            result = response.json()
            return result["translations"][0]["text"]
class GoogleTranslationProvider(BaseTranslationProvider):
    """
    Mock implementation of BaseTranslationProvider for Google fallback.
    """
    async def translate_text(self, text: str, source_lang: str = "auto", target_lang: str = "ru") -> str:
        return f"[Google Translate: {text}]"
