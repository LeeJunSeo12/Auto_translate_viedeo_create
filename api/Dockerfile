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
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Create data dirs
RUN mkdir -p /app/data/work /app/data/results /app/logs

EXPOSE 8000
