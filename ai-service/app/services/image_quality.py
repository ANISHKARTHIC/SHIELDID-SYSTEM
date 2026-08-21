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

    # 4. Cropping/Rotation Detection
    # Find the largest contour (expected to be the document's outline) and
    # use its bounding box / minimum-area rectangle to flag likely cropping
    # or rotation, rather than discarding the contour once found.
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    is_cropped = False
    rotation = 0
    if contours:
        # Get the largest contour
        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)

        # Two independent cropping signals:
        # - the document's outline touches 2+ image edges within a small
        #   margin (a genuine full-frame photo of a document leaves a
        #   background border on every side; a crop that clips the
        #   document itself pins it flush against the frame boundary)
        # - the outline covers only a small fraction of the frame (the
        #   document wasn't captured at a sensible distance/crop at all)
        margin = 10
        edges_touched = sum([
            x <= margin,
            y <= margin,
            (x + w) >= (width - margin),
            (y + h) >= (height - margin),
        ])
        contour_area_ratio = (w * h) / float(width * height) if width and height else 0
        is_cropped = edges_touched >= 2 or contour_area_ratio < 0.15

        # Rotation angle of the minimum-area bounding rectangle, normalized
        # to [-45, 45] degrees (cv2.minAreaRect reports the rotation of
        # whichever side it labels "width", which can be either the long
        # or short edge of the document depending on orientation).
        (_, _), (rect_w, rect_h), angle = cv2.minAreaRect(c)
        if rect_w < rect_h:
            angle += 90
        if angle > 45:
            angle -= 90
        rotation = round(float(angle), 1)

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
