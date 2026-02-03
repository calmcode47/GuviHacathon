FROM python:3.10-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y ffmpeg libsndfile1 curl ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements_production.txt /app/requirements_production.txt
RUN pip install --no-cache-dir -r /app/requirements_production.txt
RUN useradd -m app && chown -R app:app /app
USER app
COPY app /app/app
EXPOSE 8000
ENV FFMPEG_BINARY=/usr/bin/ffmpeg
ENV FFPROBE_BINARY=/usr/bin/ffprobe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD curl -sf http://localhost:8000/health || exit 1
CMD gunicorn -w ${MAX_WORKERS:-4} -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
