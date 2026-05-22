# Python FastMCP server
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app folder into /app
COPY ./app /app

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check disabled - MCP endpoint requires specific headers
# HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
#     CMD curl -f http://localhost:8000/mcp || exit 1

# Run server from inside /app
CMD ["python", "fastmcp_server.py"]
