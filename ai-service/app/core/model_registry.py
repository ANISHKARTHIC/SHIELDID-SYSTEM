import logging
from typing import Dict, Any
from app.services.providers.insightface_provider import InsightFaceProvider
from app.services.providers.ocr_provider import EasyOCRProvider

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
            
        # Initialize OCR Provider
        self.providers['ocr'] = EasyOCRProvider()
        try:
            self.providers['ocr'].load_model()
        except Exception as e:
            logger.error(f"Failed to load OCR Provider: {e}")
            
        logger.info("Model Registry initialization complete.")

    def get_provider(self, name: str) -> Any:
        return self.providers.get(name)

model_registry = ModelRegistry()
