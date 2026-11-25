FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    EASYOCR_MODULE_PATH=/opt/easyocr
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# CPU-only PyTorch keeps the image ~1.5 GB smaller than the default CUDA wheels
RUN pip install torch==2.15.0 torchvision==0.29.2 --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt
# Bake the OCR weights into the image so the first request is not slow
RUN python -c "import easyocr; easyocr.Reader(['en'], gpu=False, verbose=False)"

COPY app ./app
COPY ml ./ml
COPY scripts ./scripts
COPY artifacts ./artifacts

# Hugging Face Spaces expects 7860; Render sets $PORT
ENV PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
