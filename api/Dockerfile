FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps
RUN apt-get update ; apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    git \
  ; rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
# Install CUDA-enabled nightly PyTorch (CUDA 13.0) then project deps
RUN python -m pip install --upgrade pip \
  ; pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu130 \
  ; pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Create data dirs
RUN mkdir -p /app/data/work /app/data/results /app/logs

EXPOSE 8000
