import cv2
import numpy as np

def calculate_blur_variance(image: np.ndarray) -> float:
    """Calculates the variance of the Laplacian to estimate blur."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def check_glare(image: np.ndarray) -> bool:
    """Checks if there are significant overly bright regions (glare)."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Threshold for very bright pixels
    _, thresh = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY)
    # Calculate percentage of glare pixels
    glare_percentage = (cv2.countNonZero(thresh) / (image.shape[0] * image.shape[1])) * 100
    return glare_percentage > 2.0 # More than 2% pure white implies glare

def check_resolution(image: np.ndarray) -> bool:
    """Checks if the image resolution is high enough."""
    height, width = image.shape[:2]
    return width >= 800 and height >= 600

def evaluate_image_quality(image_path: str) -> dict:
    """
    Evaluates blur, glare, and resolution of an image.
    Returns scores and suggestions.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    blur_variance = calculate_blur_variance(img)
    has_glare = check_glare(img)
    is_good_resolution = check_resolution(img)

    is_blurry = blur_variance < 100.0 # Threshold for blurry

    overall_quality = 1.0
    suggestions = []

    if is_blurry:
        overall_quality -= 0.4
        suggestions.append("Image is too blurry. Please hold the camera steady and ensure good lighting.")
        
    if has_glare:
        overall_quality -= 0.3
        suggestions.append("Glare detected. Please move away from direct light sources to avoid reflections.")
        
    if not is_good_resolution:
        overall_quality -= 0.2
        suggestions.append("Resolution is too low. Please use a better camera or move closer to the document.")

    return {
        "overall_score": max(0.0, min(1.0, overall_quality)),
        "is_blurry": bool(is_blurry),
        "blur_score": float(blur_variance),
        "has_glare": bool(has_glare),
        "good_resolution": bool(is_good_resolution),
        "suggestions": suggestions,
        "is_acceptable": overall_quality >= 0.7
    }
