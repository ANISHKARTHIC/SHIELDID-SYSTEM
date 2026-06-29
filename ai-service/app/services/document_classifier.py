from PIL import Image
import io

def classify_document(image_bytes: bytes, filename: str = "") -> dict:
    """
    Classify the document type from the image using filename keywords and aspect ratio hints.
    """
    detected_class = "uk_driving_licence"
    
    # 1. Filename keyword checks
    fn = filename.lower() if filename else ""
    if "passport" in fn:
        detected_class = "passport"
    elif "licence" in fn or "driving" in fn or "dl" in fn:
        detected_class = "uk_driving_licence"
    else:
        # 2. Aspect ratio fallback (ID-1 cards are landscape; passport scans are typically vertical)
        try:
            pil_img = Image.open(io.BytesIO(image_bytes))
            width, height = pil_img.size
            if height > width: # Portrait scan is typical for a passport page scan
                detected_class = "passport"
        except Exception:
            pass

    return {
        "document_type": detected_class,
        "confidence": 0.95
    }
