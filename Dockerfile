# Use an official Python runtime as a parent image
FROM python:3.12.3-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create a non-root user for security
RUN groupadd -r weatherflow && useradd -r -g weatherflow weatherflow

# Set the working directory
WORKDIR /app/weatherflow-collector

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt ./

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY *.py ./

# Create necessary directories
RUN mkdir -p logs api_data_saver export cache && \
    chown -R weatherflow:weatherflow /app/weatherflow-collector

# Switch to non-root user
USER weatherflow

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8080/health', timeout=5)" || exit 1

# Expose ports
EXPOSE 6789 50222/udp

# Run the application
CMD ["python3", "src/weatherflow-collector.py"]
