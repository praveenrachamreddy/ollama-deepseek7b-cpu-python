# Use the official Ollama image as base
FROM ollama/ollama:latest

# Install curl, CPU optimization tools, and Python dependencies
RUN apt-get update && apt-get install -y \
    curl \
    cpu-checker \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Set environment variables for CPU optimization
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_MODELS=/root/.ollama/models
ENV GOGC=1000
ENV MALLOC_ARENA_MAX=2

# Create a startup script with CPU optimizations
RUN echo '#!/bin/bash\n\
\n\
# Get number of CPU cores\n\
CPU_CORES=$(nproc)\n\
THREADS=$((CPU_CORES - 1))\n\
\n\
# Start Ollama server in background\n\
ollama serve &\n\
\n\
# Wait for Ollama server to be ready\n\
max_attempts=30\n\
attempt=0\n\
echo "Waiting for Ollama server to start..."\n\
\n\
while ! curl -s http://localhost:11434/api/version >/dev/null; do\n\
    attempt=$((attempt + 1))\n\
    if [ $attempt -eq $max_attempts ]; then\n\
        echo "Timeout waiting for Ollama server"\n\
        exit 1\n\
    fi\n\
    sleep 1\n\
done\n\
\n\
echo "Ollama server is ready. Pulling model..."\n\
\n\
# Configure model parameters for CPU optimization\n\
cat <<EOF > /app/model.json\n\
{\n\
  "context_length": 2048,\n\
  "num_gpu": 0,\n\
  "num_thread": $THREADS,\n\
  "batch_size": 1,\n\
  "seed": 42\n\
}\n\
EOF\n\
\n\
# Pull the DeepSeek 7B model\n\
if ! ollama pull deepseek-r1:7b; then\n\
    echo "Failed to pull model"\n\
    exit 1\n\
fi\n\
\n\
echo "Model pulled successfully. Starting model..."\n\
\n\
# Run the model with CPU optimization parameters\n\
ollama run deepseek-r1:7b \n\
#ollama run deepseek-r1:7b --model /app/model.json &\n\
\n\
# Keep container running\n\
tail -f /dev/null' > /app/start.sh && \
    chmod +x /app/start.sh

# Expose the Ollama API port
EXPOSE 11434

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:11434/api/version || exit 1

# Install Python Flask and requests
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Add the Python application code
COPY app.py /app/app.py

# Set the startup script as the entry point
ENTRYPOINT ["/app/start.sh"]

# Expose the Flask application port
EXPOSE 8080
