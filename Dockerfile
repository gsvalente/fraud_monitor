# Telegram Fraud Monitor - Docker Container
# Multi-stage build for optimized image size

# Stage 1: Base system with dependencies
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies including Tesseract OCR
RUN apt-get update && apt-get install -y \
    # Essential system packages
    curl \
    wget \
    git \
    # Tesseract OCR and language packs
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-spa \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    # Image processing libraries for OpenCV
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    libgtk-3-0 \
    # Additional libraries for image processing
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libopenjp2-7-dev \
    # Clean up to reduce image size
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Verify Tesseract installation
RUN tesseract --version && tesseract --list-langs

# Stage 2: Python dependencies
FROM base as dependencies

# Create app directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Final application image
FROM dependencies as final

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create necessary directories
RUN mkdir -p /app/downloads/images \
    && mkdir -p /app/config \
    && mkdir -p /app/data \
    && mkdir -p /app/logs

# Copy application code
COPY . .

# Copy configuration files
COPY config/ ./config/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Set proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set working directory
WORKDIR /app

# Create volume mount points for persistent data
VOLUME ["/app/data", "/app/downloads", "/app/logs"]

# Environment variables for container
ENV PYTHONPATH=/app \
    TESSERACT_PATH=tesseract \
    DATABASE_PATH=/app/data/fraud_monitor.db \
    LOG_FILE=/app/logs/fraud_detection.log

# Health check to ensure the application is running properly
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.path.append('/app'); from src.database.simplified_database import SimplifiedDatabaseManager; print('Health check passed')" || exit 1

# Expose port (if needed for future web interface)
EXPOSE 8000

# Default command - can be overridden
CMD ["python", "main.py"]