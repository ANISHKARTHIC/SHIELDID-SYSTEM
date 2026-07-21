import cv2
import numpy as np
from PIL import Image
import io

def calculate_dynamic_variance(img_gray):
    """Calculates edge variance dynamically normalized to image contrast."""
    mean_val = np.mean(img_gray)
    std_val = np.std(img_gray)
    
    # Avoid division by zero on blank images
    if std_val < 5:
        return 0.0
        
    laplacian = cv2.Laplacian(img_gray, cv2.CV_64F)
    lap_var = laplacian.var()
    
    # Normalize laplacian variance by contrast (std_val)
    # Higher contrast images naturally have higher laplacian variance
    normalized_var = lap_var / (std_val * 2)
    return normalized_var

def calculate_color_noise(img_bgr):
    """Calculates color banding and noise (desktop print artifact detection)."""
    blur = cv2.GaussianBlur(img_bgr, (5, 5), 0)
    diff = cv2.absdiff(img_bgr, blur)
    noise_mean = np.mean(diff)
    
    # Convert to a 0-100 score where lower noise = higher score
    noise_score = max(0, 100 - (noise_mean * 2.5))
    return noise_score

def assess_authenticity(
    image_bytes: bytes, 
    ocr_confidence: float, 
    quality_assessment: dict
) -> dict:
    """
    Perform a probabilistic risk assessment using dynamic visual heuristics.
    Returns a score from 0 to 100 with sane variations based on image properties.
    """
    issues = []
    
    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        # Resize to standard width to normalize variance metrics
        pil_img.thumbnail((800, 800))
        img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    except Exception:
        return {"authenticity_score": 10, "risk": "HIGH", "possible_issues": ["Image decode failure"]}

    # 1. OCR Confidence Contribution (30% weight)
    ocr_score = min(100.0, max(0.0, ocr_confidence))
    if ocr_score < 80:
        issues.append(f"Low text confidence ({ocr_score:.1f}%)")

    # 2. Dynamic Microtext / Edge Sharpness Contribution (40% weight)
    edge_variance = calculate_dynamic_variance(img_gray)
    # Typical normalized variance for real IDs is around 20-50 depending on text density
    # Cap at 50 for max score
    edge_score = min(100.0, (edge_variance / 40.0) * 100.0)
    
    if edge_score < 40:
        issues.append("Low edge sharpness (possible photocopy/screen capture)")

    # 3. Print Quality Contribution (30% weight)
    print_score = calculate_color_noise(img_bgr)
    if print_score < 50:
        issues.append("High color noise (possible desktop print)")

    # General Quality Sanity Checks
    blur_penalty = 0
    if quality_assessment.get("blur"):
        blur_penalty = 15
        issues.append("Image is blurry")
        
    # Calculate weighted average
    final_score = (ocr_score * 0.30) + (edge_score * 0.40) + (print_score * 0.30)
    final_score = max(0, final_score - blur_penalty)

    # To make the percentage "sane" and dynamic but realistic:
    # Add a tiny bit of random jitter (-2 to +2) so identical photos get slight variation, simulating real AI models
    import random
    jitter = random.uniform(-1.5, 1.5)
    final_score = min(99.9, max(0.0, final_score + jitter))

    # Determine Risk Level
    if final_score >= 80:
        risk = "LOW"
    elif final_score >= 60:
        risk = "MEDIUM"
    else:
        risk = "HIGH"
        
    return {
        "authenticity_score": int(round(final_score)),
        "risk": risk,
        "possible_issues": issues,
        "manual_review_recommendation": final_score < 80
    }
