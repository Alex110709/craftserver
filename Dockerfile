FROM python:3.11-slim

# Install Java for Minecraft server
RUN apt-get update && \
    apt-get install -y openjdk-17-jre-headless wget curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories
RUN mkdir -p /app/minecraft /app/backups /app/logs

# Copy application code
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# Expose ports
# 8000: Web UI and API
# 25565: Minecraft server
EXPOSE 8000 25565

# Run the application
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
