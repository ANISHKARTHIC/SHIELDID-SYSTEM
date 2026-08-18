import os
import sys
import io
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from starlette.datastructures import UploadFile

# Add ai-service root to sys.path
ai_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ai_root not in sys.path:
    sys.path.insert(0, ai_root)

def create_test_image_bytes(width=600, height=400, color=(200, 200, 200), text="TEST ID"):
    """Generates a valid test image byte stream with some texture."""
    img = Image.new("RGB", (width, height), color=color)
    pixels = np.array(img)
    noise = np.random.randint(0, 50, (height, width, 3), dtype=np.uint8)
    noisy_img = Image.fromarray(np.clip(pixels + noise, 0, 255).astype(np.uint8))

    buf = io.BytesIO()
    noisy_img.save(buf, format="JPEG")
    return buf.getvalue()

def create_text_image_bytes(lines, width=856, height=540, color=(240, 240, 235)):
    """
    Generates a real image with actual rendered, OCR-readable text lines —
    used to test content-based document classification, which needs genuine
    text in the image rather than filename hints or noise.
    """
    img = Image.new("RGB", (width, height), color=color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/liberation-sans/LiberationSans-Regular.ttf", 24
        )
    except Exception:
        font = ImageFont.load_default()
    y = 30
    for line in lines:
        draw.text((30, y), line, fill=(10, 10, 10), font=font)
        y += 40
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()

def create_upload_file(filename: str, content_bytes: bytes, content_type: str = "image/jpeg") -> UploadFile:
    """Helper to construct FastAPI/Starlette UploadFile."""
    file_obj = io.BytesIO(content_bytes)
    return UploadFile(filename=filename, file=file_obj, headers={"content-type": content_type})
