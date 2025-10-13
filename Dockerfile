FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for GUI applications (needed for OAuth browser flow)
RUN apt-get update && apt-get install -y \
    gcc \
    xvfb \
    x11-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY gmail_webhook.py .

# Create directories for persistent data
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "gmail_webhook.py"]