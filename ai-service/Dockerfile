FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for OpenCV and AI models
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Environment variables for model cache
ENV TRANSFORMERS_CACHE=/app/model_cache
ENV TORCH_HOME=/app/model_cache

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
