FROM python:3.12-slim

WORKDIR /app

# System dependencies for OpenCV / onnxruntime / insightface
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu

COPY . .

# Bake model weights into the image at build time so the container has no
# first-boot download/internet dependency in production.
ENV INSIGHTFACE_MODEL_ROOT=/app/model_cache/insightface
ENV EASYOCR_MODEL_DIR=/app/model_cache/easyocr
RUN python -c "from app.services.providers.insightface_provider import InsightFaceProvider; from app.services.ocr.easy_ocr_provider import EasyOCRProvider; InsightFaceProvider().load_model(); EasyOCRProvider()._get_reader(); print('Model warm-up complete.')"

RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=10 \
    CMD curl -f http://localhost:8001/docs || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
