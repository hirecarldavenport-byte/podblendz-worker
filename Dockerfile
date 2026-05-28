FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir \
    runpod \
    boto3 \
    openai-whisper

CMD ["python", "workers/handler.py"]
