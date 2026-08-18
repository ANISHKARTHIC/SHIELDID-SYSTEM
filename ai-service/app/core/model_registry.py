import logging
from typing import Any
from app.services.providers.insightface_provider import InsightFaceProvider

logger = logging.getLogger("model_registry")

class ModelRegistry:
    def __init__(self):
        self.providers = {}

    def initialize_models(self):
        """Loads all AI models into memory globally."""
        logger.info("Initializing Model Registry...")

        # Initialize Face Provider
        self.providers['face'] = InsightFaceProvider()
        try:
            self.providers['face'].load_model()
        except Exception as e:
            logger.error(f"Failed to load Face Provider: {e}")

        # Note: OCR is provided via app.services.ocr.factory.get_ocr_provider()
        # (the EasyOCRProvider in app/services/ocr/easy_ocr_provider.py), which
        # lazily loads its own reader on first use. A second EasyOCRProvider
        # class used to be registered here too but was never called by any
        # live endpoint — removed to stop loading EasyOCR into memory twice.

        logger.info("Model Registry initialization complete.")

    def get_provider(self, name: str) -> Any:
        return self.providers.get(name)

model_registry = ModelRegistry()
