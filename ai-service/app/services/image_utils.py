import cv2
import numpy as np

def resize_image_for_ai(image_bytes: bytes, max_dim: int = 1024) -> bytes:
    """
    Downscale high-resolution camera photos (e.g. 12MP / 4000x3000, which
    is what ResolutionPreset.high on a modern phone actually captures) to
    max_dim on the longest side.

    On `main` (t3.micro, 1GB RAM), 1024px is a memory-safety requirement,
    not just a speed tunable: this cuts PyTorch/EasyOCR memory allocation
    from ~700MB+ down to ~35MB, which is the difference between fitting in
    1GB and getting OOM-killed by the kernel. It also cuts full-resolution
    CPU inference time from ~80-90s down to a few seconds. The `high-power`
    branch (real RAM headroom, speed/accuracy tradeoff only) uses a higher
    1600px cap instead — don't raise this default here without re-checking
    memory headroom on a t3.micro first.
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

        _, encoded = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return encoded.tobytes()
    except Exception:
        return image_bytes
