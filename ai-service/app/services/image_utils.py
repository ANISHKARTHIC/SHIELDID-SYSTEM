import cv2
import numpy as np

def resize_image_for_ai(image_bytes: bytes, max_dim: int = 1600) -> bytes:
    """
    Downscale high-resolution camera photos (e.g. 12MP / 4000x3000, which
    is what ResolutionPreset.high on a modern phone actually captures) to
    max_dim on the longest side. Full-resolution CPU inference (EasyOCR +
    InsightFace, no GPU on the deployed instance) measured at ~80-90s per
    scan; downscaling to a fixed cap brings this down to single-digit
    seconds while keeping enough resolution for licence-text legibility.
    1600px (vs. an earlier 1280px attempt) trades a little of that speedup
    back for extra headroom on fine print (licence number, DOB) since
    accuracy on small text was the reason a prior downscale attempt was
    reverted in favor of full-resolution processing.
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        if len(nparr) == 0:
            return image_bytes
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes

        h, w = img.shape[:2]
        if max(h, w) <= max_dim:
            return image_bytes

        scale = max_dim / float(max(h, w))
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        _, encoded = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 92])
        return encoded.tobytes()
    except Exception:
        return image_bytes
