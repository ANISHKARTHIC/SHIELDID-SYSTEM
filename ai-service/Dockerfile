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
#
# INSIGHTFACE_MODEL_PACK/INSIGHTFACE_DET_SIZE are build args so the image
# can be built either as the full-power variant (buffalo_l/640, the
# default — for a real instance) or the low-memory demo variant
# (buffalo_s/320, ~160MB vs ~600MB, fits a t3.micro free-tier box
# alongside EasyOCR+torch):
#   docker build --build-arg INSIGHTFACE_MODEL_PACK=buffalo_s \
#                --build-arg INSIGHTFACE_DET_SIZE=320 ai-service/
ARG INSIGHTFACE_MODEL_PACK=buffalo_l
ARG INSIGHTFACE_DET_SIZE=640
ENV INSIGHTFACE_MODEL_ROOT=/app/model_cache/insightface
ENV EASYOCR_MODEL_DIR=/app/model_cache/easyocr
ENV INSIGHTFACE_MODEL_PACK=${INSIGHTFACE_MODEL_PACK}
ENV INSIGHTFACE_DET_SIZE=${INSIGHTFACE_DET_SIZE}
RUN python -c "from app.services.providers.insightface_provider import InsightFaceProvider; from app.services.ocr.easy_ocr_provider import EasyOCRProvider; InsightFaceProvider().load_model(); EasyOCRProvider()._get_reader(); print('Model warm-up complete.')"

RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=10 \
    CMD curl -f http://localhost:8001/docs || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
