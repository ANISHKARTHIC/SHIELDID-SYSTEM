import os
from .base import BaseOCR
from .easy_ocr_provider import EasyOCRProvider

# EasyOCRProvider caches its loaded reader on `self.reader` after first use
# (see easy_ocr_provider.py), but that cache is only useful if the same
# instance is reused across requests. get_ocr_provider() previously
# constructed a brand-new EasyOCRProvider() on every single call, which
# meant the "lazy load, cache after first use" design never actually
# applied — every /ocr request re-loaded the full EasyOCR model from disk
# from scratch, not just the first request after container startup. This
# was the dominant cost in OCR being slow, well beyond image resolution.
# Module-level singletons per provider type fix this: the reader is now
# genuinely loaded once and reused for the lifetime of the process.
_providers: dict[str, BaseOCR] = {}

def get_ocr_provider() -> BaseOCR:
    provider = os.getenv("OCR_PROVIDER", "easyocr").lower()

    if provider not in _providers:
        # trocr/paddleocr aren't implemented yet — fall through to
        # EasyOCRProvider for all provider values, same as before.
        _providers[provider] = EasyOCRProvider()

    return _providers[provider]
