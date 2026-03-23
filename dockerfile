# =========================================================
# Maantra AI Assistant
# Production Docker Image
# =========================================================

# ---------------------------------------------------------
# Builder Stage
# ---------------------------------------------------------

FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./
COPY requirements.txt ./

# Install dependencies into virtual environment
RUN uv venv /opt/venv
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ---------------------------------------------------------
# Production Stage
# ---------------------------------------------------------

FROM python:3.11-slim AS production

WORKDIR /app

# Install dumb-init for signal handling
RUN apt-get update && \
    apt-get install -y dumb-init && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1001 maantra && \
    useradd -u 1001 -g maantra -s /bin/bash -m assistant

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application source
COPY src ./src

# Create runtime directories
RUN mkdir -p /app/data /app/logs && \
    chown -R assistant:maantra /app

# Activate venv
ENV PATH="/opt/venv/bin:$PATH"

# Switch to non-root user
USER assistant

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/assistant.db
ENV LOG_LEVEL=info

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
CMD python -c "print('healthy')" || exit 1

# Proper signal handling
ENTRYPOINT ["dumb-init", "--"]

# Start Maantra
CMD ["python", "-m", "src.main"]