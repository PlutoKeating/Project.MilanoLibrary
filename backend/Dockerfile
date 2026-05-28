FROM python:3.13-slim

WORKDIR /app

# Install ffmpeg for video segmentation and audio extraction
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 10 -r requirements.txt
RUN pip install --no-cache-dir --timeout 120 --retries 10 hf_transfer

COPY app/ ./app/

ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
