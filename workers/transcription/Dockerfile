FROM runpod/base:0.4.0

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y ffmpeg

# Python dependencies
RUN pip install --upgrade pip
RUN pip install boto3 runpod openai-whisper torch

# Copy your handler
COPY handler.py /app/handler.py

# Run handler
CMD ["python3", "-u", "handler.py"]