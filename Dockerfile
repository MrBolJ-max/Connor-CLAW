FROM python:3.12-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create data dirs
RUN mkdir -p data/knowledge_bases data/reports data/logs

# Non-root user
RUN useradd -m -u 1000 synsystems && chown -R synsystems:synsystems /app
USER synsystems

EXPOSE 8000

# Default: run everything (API + Telegram + Scheduler)
CMD ["python", "main.py", "all"]
