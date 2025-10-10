FROM python:3.10-slim-bullseye

ARG GITHUB_TOKEN
ENV GOPRIVATE=github.com/STM-GLOBAL/*

WORKDIR /app

RUN apt-get update && apt-get install -y \
    espeak \
    espeak-data \
    libespeak1 \
    libespeak-dev \
    ffmpeg \
    wget \
    alsa-utils \
    pulseaudio \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    poppler-utils \
    libmagic1 \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN git config --global url."https://${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"

RUN wget https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -O /app/global-bundle.pem

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--workers", "1"]