import cv2
import numpy as np
from PIL import Image
import io

def check_hologram_glare(img_hsv) -> bool:
    """Check for specular highlights typical of polycarbonate holograms."""
    # V channel for brightness, S channel for saturation
    v_channel = img_hsv[:,:,2]
    s_channel = img_hsv[:,:,1]
    # Relaxed for standard photos without direct flash
    glare_mask = (v_channel > 180) & (s_channel < 60)
    return np.sum(glare_mask) > 10  # Just a tiny specular spot is enough to pass

def check_microtext_sharpness(img_gray) -> float:
    """Analyze high-frequency details using Laplacian variance to simulate microtext legibility."""
    laplacian_var = cv2.Laplacian(img_gray, cv2.CV_64F).var()
    return laplacian_var

def check_print_quality(img_bgr) -> bool:
    """Check for lithographic vs desktop printing by analyzing color banding/noise."""
    # Desktop printers often have higher noise/dithering in uniform areas
    blur = cv2.GaussianBlur(img_bgr, (5, 5), 0)
    diff = cv2.absdiff(img_bgr, blur)
    noise_level = np.mean(diff)
    # Relaxed to 20.0 to account for smartphone camera JPEG compression artifacts
    return noise_level < 20.0 # Lower noise = higher quality lithographic

def assess_authenticity(
    image_bytes: bytes, 
    ocr_confidence: float, 
    quality_assessment: dict
) -> dict:
    """
    Perform a confidence-based risk assessment using advanced visual heuristics.
    Evaluates criteria from the Genuine/Fake classification matrix.
    """
    score = 100
    issues = []
    risk = "LOW"
    
    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    except Exception:
        return {"authenticity_score": 0, "risk": "HIGH", "possible_issues": ["Image decode failure"]}

    # 1. OCR Confidence
    if ocr_confidence < 90:
        score -= (90 - ocr_confidence) * 1.5
        issues.append(f"Low Text Legibility ({ocr_confidence:.1f}%)")
        
    # 2. Material & Holograms (Specular Highlight Check)
    has_glare = check_hologram_glare(img_hsv)
    if not has_glare:
        score -= 10
        issues.append("Material: Lacks polycarbonate/holographic reflection (appears flat/PVC)")

    # 3. Microtext & Text Texture
    microtext_var = check_microtext_sharpness(img_gray)
    if microtext_var < 50:
        score -= 10
        issues.append("Microtext: Blurry dots or fuzzy lines detected (Lacks laser-engraved sharpness)")

    # 4. Print Quality (Lithographic vs Desktop)
    is_lithographic = check_print_quality(img_bgr)
    if not is_lithographic:
        score -= 10
        issues.append("Print Quality: Muddy colors or visible banding (Possible desktop printer replica)")

    # 5. General Quality Sanity Checks
    if quality_assessment.get("blur"):
        score -= 10
        issues.append("Overall Image Blur detected")
        
    # UV and Watermark are visually assumed missing if lighting is standard
    # We won't penalize for UV unless in a UV scanner, but we can list it as unchecked.

    # Determine Risk Level
    if score >= 85:
        risk = "LOW"
    elif score >= 65:
        risk = "MEDIUM"
    else:
        risk = "HIGH"
        
    return {
        "authenticity_score": int(round(max(0, score))),
        "risk": risk,
        "possible_issues": issues
    }
