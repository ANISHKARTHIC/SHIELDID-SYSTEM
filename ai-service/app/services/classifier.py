import cv2
import numpy as np

def detect_face(image_bytes: bytes):
    """Uses InsightFace to detect if a face is present in the image and extract its embedding."""
    try:
        from app.core.model_registry import model_registry
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        if len(nparr) == 0:
            return False, None
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return False, None
            
        face_provider = model_registry.providers.get('face')
        if face_provider and face_provider.app:
            faces = face_provider.app.get(img)
            if len(faces) > 0:
                embedding = None
                if hasattr(faces[0], "embedding") and faces[0].embedding is not None:
                    embedding = faces[0].embedding.tolist()
                return True, embedding
            return False, None

        # Model not loaded: we cannot confirm a face is present, so fail
        # closed. This gates "does this document have a face photo on it" —
        # failing open here would mean any environment where InsightFace
        # fails to initialize (missing GPU/CUDA lib, OOM, corrupt model
        # cache) silently accepts every image as a valid ID document with
        # no face check at all, for the lifetime of that failure.
        import logging
        logging.getLogger("classifier").error("Face provider not loaded; failing closed (no face detected)")
        return False, None
    except Exception as e:
        import logging
        logging.getLogger("classifier").error(f"Error detecting face with InsightFace: {e}")
        return False, None # Fail closed: an error here means we can't confirm a face is present

def classify_document_real(image_bytes: bytes) -> dict:
    """
    Step 1 Pipeline: Classify the document.
    Must return whether it's a valid ID document or not.
    """
    has_face, face_embedding = detect_face(image_bytes)
    
    if not has_face:
        return {
            "is_valid": False,
            "document_type": "unknown",
            "reason": "No face detected on the document. Please upload a valid ID."
        }
        
    result = {
        "is_valid": True,
        "document_type": "driving_licence_or_passport",
        "reason": "Valid face photo found on document."
    }
    if face_embedding is not None:
        result["face_embedding"] = face_embedding
    return result

