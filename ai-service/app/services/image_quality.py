import cv2
import numpy as np

from PIL import Image
import io

def assess_image_quality(image_bytes: bytes) -> dict:
    """
    Assess the quality of an uploaded image document.
    """
    try:
        # Decodes WEBP, PNG, JPEG, etc. natively via Pillow
        pil_img = Image.open(io.BytesIO(image_bytes))
        pil_img = pil_img.convert("RGB")
        img = np.array(pil_img)
        # Convert RGB to BGR for OpenCV functions below
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    except Exception as e:
        raise ValueError(f"Invalid image format or corrupted data: {e}")

    height, width, _ = img.shape
    
    # 1. Resolution Check
    resolution = height * width
    is_low_res = resolution < 300000 # Example threshold

    # 2. Blur Detection (Variance of Laplacian)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    is_blurred = laplacian_var < 100 # Threshold

    # 3. Brightness/Lighting Detection
    brightness = np.mean(gray)
    lighting = "good"
    if brightness < 50:
        lighting = "under_exposed"
    elif brightness > 210:
        lighting = "over_exposed"

    # 4. Cropping/Rotation Detection (Mocked for now)
    # Proper cropping detection requires document contours detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    is_cropped = False
    rotation = 0
    if contours:
        # Get the largest contour
        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        # If the largest contour touches the image boundaries heavily, it might be cropped
        if x < 10 or y < 10 or (x+w) > (width - 10) or (y+h) > (height - 10):
            # Very rudimentary check
            pass

    # Calculate overall score based on penalties
    score = 100
    if is_blurred: score -= 30
    if lighting != "good": score -= 20
    if is_low_res: score -= 20

    return {
        "quality_score": max(0, score),
        "blur": bool(is_blurred),
        "lighting": lighting,
        "cropped": bool(is_cropped),
        "rotation": rotation
    }
