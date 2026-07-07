from abc import ABC, abstractmethod


class BaseTranslationProvider(ABC):
    """
    Abstract interface for translation operations.
    Supports real-time text translation and batch post-processing translation.
    """

    @abstractmethod
    async def translate_text(
        self, 
        text: str, 
        source_lang: str = "auto", 
        target_lang: str = "ru"
    ) -> str:
        """
        Translates a given text from source_lang to target_lang.
        
        Args:
            text: The original text to translate.
            source_lang: The ISO code of source language (or 'auto').
            target_lang: The target language ISO code (defaults to 'ru').
            
        Returns:
            str: The translated text.
        """
        pass
