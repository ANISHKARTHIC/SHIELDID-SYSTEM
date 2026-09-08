import cv2
import numpy as np

def order_points(pts: np.ndarray) -> np.ndarray:
    """Orders coordinates as [top-left, top-right, bottom-right, bottom-left]."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Applies perspective transform to flatten the document rectangle."""
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = max(int(heightA), int(heightB))

    if maxWidth <= 0 or maxHeight <= 0:
        return image

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

    # Standard ID cards / licences are landscape; normalize if vertical
    if warped.shape[0] > warped.shape[1] * 1.18:
        warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)

    return warped


def crop_and_deskew_document(img: np.ndarray) -> np.ndarray:
    """
    Detects and crops an ID document from the surrounding background scene
    (desk, hands, bedding, etc.) before downscaling.

    1. If a 4-point quadrilateral matching document dimensions is detected,
       flattens/deskews with perspective transform.
    2. If a clean bounding box is detected, crops with a small safety margin.
    3. If the image is already cropped (document fills frame) or no distinct
       document is isolated, leaves the original image intact.
    """
    if img is None or img.size == 0:
        return img

    H, W = img.shape[:2]
    total_area = H * W
    if total_area < 10000:
        return img

    target_h = 600
    scale = target_h / float(H) if H > target_h else 1.0
    if scale < 1.0:
        scaled_w = int(W * scale)
        small = cv2.resize(img, (scaled_w, target_h), interpolation=cv2.INTER_AREA)
    else:
        small = img
        scale = 1.0

    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(blurred, 40, 140)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return img

    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    small_total_area = small.shape[0] * small.shape[1]

    for c in contours:
        c_area = cv2.contourArea(c)
        area_ratio = c_area / float(small_total_area)

        # If already tightly framed/cropped (> 88%), do not crop further
        if area_ratio > 0.88:
            return img

        if area_ratio < 0.12:
            continue

        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.025 * peri, True)

        if len(approx) == 4 and cv2.isContourConvex(approx):
            pts = approx.reshape(4, 2).astype("float32")
            orig_pts = pts / scale
            warped = four_point_transform(img, orig_pts)
            wh_ratio = max(warped.shape[1], warped.shape[0]) / float(max(1, min(warped.shape[1], warped.shape[0])))
            if 1.15 <= wh_ratio <= 2.3:
                return warped

        x, y, w, h = cv2.boundingRect(c)
        box_area = (w * h) / float(small_total_area)
        aspect = max(w, h) / float(max(1, min(w, h)))
        if 0.15 <= box_area <= 0.88 and 1.15 <= aspect <= 2.3:
            orig_x = int(x / scale)
            orig_y = int(y / scale)
            orig_w = int(w / scale)
            orig_h = int(h / scale)

            pad_x = int(orig_w * 0.03)
            pad_y = int(orig_h * 0.03)

            x1 = max(0, orig_x - pad_x)
            y1 = max(0, orig_y - pad_y)
            x2 = min(W, orig_x + orig_w + pad_x)
            y2 = min(H, orig_y + orig_h + pad_y)

            cropped = img[y1:y2, x1:x2]
            if cropped.shape[0] > cropped.shape[1] * 1.18:
                cropped = cv2.rotate(cropped, cv2.ROTATE_90_CLOCKWISE)
            return cropped

    return img


def resize_image_for_ai(image_bytes: bytes, max_dim: int = 1024) -> bytes:
    """
    Crops the document from any surrounding background, then downscales to
    max_dim on the longest side.

    Cropping before downscaling preserves crucial high-frequency details:
    a card inside a 12MP photo previously shrank to ~350px when the whole
    photo was downscaled, making fine text unreadable. Now the card itself
    is isolated first and occupies up to max_dim pixels.
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        if len(nparr) == 0:
            return image_bytes
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes

        # First crop document from scene if present
        img = crop_and_deskew_document(img)

        h, w = img.shape[:2]
        if max(h, w) <= max_dim:
            _, encoded = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            return encoded.tobytes()

        scale = max_dim / float(max(h, w))
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        _, encoded = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return encoded.tobytes()
    except Exception:
        return image_bytes


def enhance_image_for_ocr(img: np.ndarray) -> np.ndarray:
    """
    Enhance document image for OCR by:
    1. Upscaling if the document resolution is too low (< 600px on min dimension)
    2. Applying subtle unsharp masking to sharpen character boundaries
    3. Applying CLAHE on luminance channel to equalize lighting and boost text contrast
    """
    if img is None or img.size == 0:
        return img

    try:
        h, w = img.shape[:2]
        min_dim = min(h, w)
        if min_dim < 600:
            scale = max(1.5, 800.0 / float(max(min_dim, 1)))
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

        gaussian = cv2.GaussianBlur(img, (0, 0), 1.5)
        sharpened = cv2.addWeighted(img, 1.3, gaussian, -0.3, 0)

        lab = cv2.cvtColor(sharpened, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        enhanced = cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2RGB)
        return enhanced
    except Exception:
        return img
