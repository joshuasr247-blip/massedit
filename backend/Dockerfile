FROM python:3.12-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Create storage dirs
RUN mkdir -p /data/clips /data/thumbnails /data/outputs

ENV MASSEDIT_STORAGE_PATH=/data
ENV PORT=8000

EXPOSE 8000

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
