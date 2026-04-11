FROM python:3.11-slim

WORKDIR /app

# Install system deps for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server/ server/
COPY cli/ cli/
COPY data/ data/
COPY run_server.py run_cli.py ./

# Expose the API port
EXPOSE 8000

# Default: run the server
CMD ["python", "run_server.py"]
