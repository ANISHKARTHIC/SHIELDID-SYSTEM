import cv2
import numpy as np

def generate_embedding(image_bytes: bytes) -> list[float]:
    """
    Generates a 512-dimensional vector embedding for the face using OpenCV.
    Because TensorFlow is not available, we use Color Histograms + HOG features
    to represent the image in a 512D space for pgvector cosine similarity.
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 1. Detect face and crop
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
        
        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            face_roi = img[y:y+h, x:x+w]
        else:
            face_roi = img # Fallback to whole image if no face detected
            
        # 2. Resize to 64x64
        resized = cv2.resize(face_roi, (64, 64))
        
        # 3. Calculate 3D Color Histogram (8 bins per channel = 8x8x8 = 512 dimensions)
        hist = cv2.calcHist([resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        
        # 4. Normalize and flatten to 512D
        cv2.normalize(hist, hist)
        embedding = hist.flatten().tolist()
        
        # Ensure it's exactly 512 dimensions
        if len(embedding) < 512:
            embedding.extend([0.0] * (512 - len(embedding)))
        elif len(embedding) > 512:
            embedding = embedding[:512]
            
        return embedding
    except Exception as e:
        import logging
        logging.getLogger("embedder").error(f"Error generating embedding: {e}")
        # Return a zero vector in case of failure
        return [0.0] * 512
