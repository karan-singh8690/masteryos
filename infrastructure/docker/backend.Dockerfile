# Backend Dockerfile — Mastery Engine
# Multi-stage build for smaller production images.
#
# Stages:
#   builder-deps  — install build tooling + compile Python deps (cached layer)
#   builder-dev   — same as builder-deps but also installs dev deps (for tests / lint)
#   runtime       — slim runtime with only prod deps + curl for healthchecks

# ================================
# Stage 1: Builder (production deps only)
# ================================
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install PRODUCTION dependencies only (no [dev] extras).
# Dev dependencies are installed in the dev stage below.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# ================================
# Stage 1b: Dev builder (used by CI / lint / test images)
# ================================
FROM builder AS builder-dev

RUN pip install --no-cache-dir -e ".[dev]"

# ================================
# Stage 2: Runtime
# ================================
FROM python:3.13-slim AS runtime

WORKDIR /app

# Install runtime dependencies:
#   - libpq5: PostgreSQL client library (asyncpg)
#   - curl:   required by docker-compose healthchecks (`curl -f http://.../health/ready`)
#   - wget:   fallback for images without curl (used by some exporters)
#   - ca-certificates: required for HTTPS calls to SMTP / Sentry / AI providers
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder (production deps only)
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r mastery && useradd -r -g mastery mastery
USER mastery

# Expose port
EXPOSE 8000

# Health check — uses curl (installed above) for parity with docker-compose healthchecks
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=30s \
    CMD curl -sf http://localhost:8000/api/v1/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
