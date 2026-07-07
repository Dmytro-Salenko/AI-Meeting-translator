from app.core.config import settings
from app.core.interfaces.storage import BaseStorageProvider
from app.core.interfaces.translation import BaseTranslationProvider
from app.core.interfaces.summary import BaseSummaryProvider

# Concrete adapter imports
from app.adapters.s3_storage import S3StorageProvider
from app.adapters.deepl_translation import DeepLTranslationProvider, GoogleTranslationProvider
from app.adapters.openrouter_summary import OpenRouterSummaryProvider, MockSummaryProvider

# In-memory singletons for efficiency
_storage_provider: BaseStorageProvider = None
_translation_provider: BaseTranslationProvider = None
_summary_provider: BaseSummaryProvider = None


def get_storage_provider() -> BaseStorageProvider:
    global _storage_provider
    if _storage_provider is None:
        if settings.STORAGE_PROVIDER == "r2":
            _storage_provider = S3StorageProvider()
        else:
            # Fallback to in-memory/mock mock-up defined in meeting_stream
            from app.routers.meeting_stream import MockStorageProvider
            _storage_provider = MockStorageProvider()
    return _storage_provider


def get_translation_provider() -> BaseTranslationProvider:
    global _translation_provider
    if _translation_provider is None:
        if settings.TRANSLATION_PROVIDER == "deepl":
            _translation_provider = DeepLTranslationProvider()
        elif settings.TRANSLATION_PROVIDER == "google":
            _translation_provider = GoogleTranslationProvider()
        else:
            from app.routers.meeting_stream import MockTranslationProvider
            _translation_provider = MockTranslationProvider()
    return _translation_provider


def get_summary_provider() -> BaseSummaryProvider:
    global _summary_provider
    if _summary_provider is None:
        if settings.SUMMARY_PROVIDER == "openrouter":
            _summary_provider = OpenRouterSummaryProvider()
        else:
            _summary_provider = MockSummaryProvider()
    return _summary_provider
