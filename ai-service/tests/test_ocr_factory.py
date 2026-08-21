import unittest
from app.services.ocr.factory import get_ocr_provider, _providers
from app.services.ocr.easy_ocr_provider import EasyOCRProvider


class TestOCRProviderFactory(unittest.TestCase):
    def setUp(self):
        # Isolate each test from whatever previous tests (or module import
        # order) have already populated into the singleton cache.
        _providers.clear()

    def test_returns_same_instance_across_calls(self):
        # Regression: get_ocr_provider() used to construct a brand-new
        # EasyOCRProvider() on every call — since EasyOCRProvider caches
        # its loaded reader on `self.reader` after first use, a fresh
        # instance per call meant that cache never actually applied, and
        # every single /ocr request re-loaded the full EasyOCR model from
        # disk from scratch. Callers must get back the same instance so
        # the reader is genuinely loaded once and reused.
        provider1 = get_ocr_provider()
        provider2 = get_ocr_provider()
        self.assertIs(provider1, provider2)

    def test_returns_easyocr_provider(self):
        provider = get_ocr_provider()
        self.assertIsInstance(provider, EasyOCRProvider)


if __name__ == "__main__":
    unittest.main()
