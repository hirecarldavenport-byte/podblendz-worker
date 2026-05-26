FROM runpod/pytorch:3.10-2.0.1-cuda11.8-runtime

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y ffmpeg

# Install Python deps
RUN pip install --upgrade pip
RUN pip install boto3 runpod openai-whisper

# Copy your handler
COPY handler.py /app/handler.py

# Run the worker
CMD ["python", "-u", "handler.py"]