FROM python:3.11-slim

WORKDIR /app

# ✅ ✅ ✅ ADD THIS (FINAL FIX)
RUN apt-get update && apt-get install -y ffmpeg

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# ✅ GUARANTEE static directories exist
RUN mkdir -p /app/ui/assets

ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "uvicorn podpal.main:app --host 0.0.0.0 --port $PORT"]
