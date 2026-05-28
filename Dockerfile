FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir \
    runpod \
    boto3 \
    torch \
    openai-whisper

CMD ["python", "-u", "-m", "runpod.serverless"]