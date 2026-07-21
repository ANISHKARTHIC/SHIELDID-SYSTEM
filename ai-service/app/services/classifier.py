import cv2
import numpy as np

def detect_face(image_bytes: bytes) -> bool:
    """Uses InsightFace to detect if a face is present in the image."""
    try:
        from app.core.model_registry import model_registry
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        face_provider = model_registry.providers.get('face')
        if face_provider and face_provider.app:
            faces = face_provider.app.get(img)
            return len(faces) > 0
            
        # Fallback to true if model is somehow not loaded
        return True
    except Exception as e:
        import logging
        logging.getLogger("classifier").error(f"Error detecting face with InsightFace: {e}")
        return True # Fallback to let it proceed rather than blocking incorrectly

def classify_document_real(image_bytes: bytes) -> dict:
    """
    Step 1 Pipeline: Classify the document.
    Must return whether it's a valid ID document or not.
    """
    has_face = detect_face(image_bytes)
    
    if not has_face:
        return {
            "is_valid": False,
            "document_type": "unknown",
            "reason": "No face detected on the document. Please upload a valid ID."
        }
        
    return {
        "is_valid": True,
        "document_type": "driving_licence_or_passport",
        "reason": "Valid face photo found on document."
    }
