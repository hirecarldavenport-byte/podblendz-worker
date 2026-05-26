FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# -------------------------
# System dependencies
# -------------------------
RUN apt-get update && apt-get install -y \
    ffmpeg \
    python3 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# -------------------------
# Python setup
# -------------------------
RUN python3 -m pip install --upgrade pip

# ✅ Install torch WITH CUDA support
RUN pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121

# ✅ Install correct dependencies
RUN pip install \
    runpod \
    boto3 \
    faster-whisper \
    requests

# -------------------------
# App setup
# -------------------------
WORKDIR /app

COPY handler.py /app/handler.py

# -------------------------
# Start worker
# -------------------------
CMD ["python3", "-u", "handler.py"]