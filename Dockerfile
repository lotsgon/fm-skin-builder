# Dockerfile for fm-skin-builder
# This runs the catalogue builder in a Linux environment where UnityPy works correctly
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including build tools for UnityPy and Cairo for cairosvg
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    gcc \
    g++ \
    libcairo2 \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Install the package in development mode
RUN pip install -e .

# Create directories for input/output
RUN mkdir -p /bundles /output

# Set entrypoint to run the catalogue command
ENTRYPOINT ["python", "-m", "fm_skin_builder.cli.main", "catalogue"]
