# Lightweight, cross-platform container with ffmpeg for MP3 decoding
FROM python:3.11-slim

# Install ffmpeg and libsndfile for audio decoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Default API key (override via environment variable when deploying)
ENV API_KEY=sk_test_123456789

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]