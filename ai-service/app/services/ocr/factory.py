import os
from .base import BaseOCR
from .easy_ocr_provider import EasyOCRProvider

def get_ocr_provider() -> BaseOCR:
    provider = os.getenv("OCR_PROVIDER", "easyocr").lower()
    
    if provider == "easyocr":
        return EasyOCRProvider()
    elif provider == "trocr":
        # return TrOCRProvider()
        return EasyOCRProvider()
    elif provider == "paddleocr":
        # return PaddleOCRProvider()
        return EasyOCRProvider()
    else:
        return EasyOCRProvider()
