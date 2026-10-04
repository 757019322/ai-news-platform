# ── Stage 1: builder ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime MySQL client lib only
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy backend source + frontend (served by FastAPI at /)
COPY backend/ .
COPY frontend/ ./frontend/

# Non-root user for security; faiss_index dir is the persisted volume
RUN useradd -m appuser && mkdir -p /app/faiss_index && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Wait for MySQL then start (healthcheck handles ordering via depends_on)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
