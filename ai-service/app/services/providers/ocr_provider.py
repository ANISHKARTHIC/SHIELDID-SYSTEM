import logging
from typing import Dict, Any
from backend.services.providers.base_providers import BaseOCR

logger = logging.getLogger("ocr_provider")

class EasyOCRProvider(BaseOCR):
    def __init__(self):
        self.reader = None

    def load_model(self) -> None:
        """Loads EasyOCR into memory."""
        try:
            import easyocr
            # Load English language model. Use GPU=False by default for dev compatibility
            self.reader = easyocr.Reader(['en'], gpu=False)
            logger.info("EasyOCR model loaded successfully.")
        except ImportError:
            logger.error("easyocr module not installed. Run `pip install easyocr`")
            raise
        except Exception as e:
            logger.error(f"Failed to load EasyOCR model: {e}")
            raise

    def extract_text(self, image_path: str, regions: Dict[str, dict] = None) -> Dict[str, Any]:
        if not self.reader:
            self.load_model()
            
        # We perform standard OCR on the whole image.
        # In a real enterprise app, we would crop the regions defined in `regions`
        # and run OCR only on those crops for higher accuracy and speed.
        
        try:
            results = self.reader.readtext(image_path)
            extracted_data = {}
            
            # This is a naive mapping. The template engine would actually map
            # coordinate bounds from the `regions` to the bounding boxes here.
            for i, (bbox, text, prob) in enumerate(results):
                extracted_data[f"field_{i}"] = {
                    "text": text,
                    "confidence": float(prob),
                    "bounding_box": [int(x) for point in bbox for x in point] # Flatten
                }
                
            return extracted_data
        except Exception as e:
            logger.error(f"OCR Extraction failed: {e}")
            raise ValueError(f"OCR extraction failed: {e}")
