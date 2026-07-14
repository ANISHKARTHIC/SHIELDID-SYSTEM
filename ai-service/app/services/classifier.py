import cv2
import numpy as np

def detect_face(image_bytes: bytes) -> bool:
    """Uses OpenCV Haar Cascades to detect if a face is present in the image."""
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Load the pre-trained Haar cascade for frontal face
        # In a real environment, you'd use a more robust model like RetinaFace or MTCNN
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        faces = face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(30, 30)
        )
        
        return len(faces) > 0
    except Exception as e:
        import logging
        logging.getLogger("classifier").error(f"Error detecting face: {e}")
        return False

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
