# Frontend Dockerfile — Mastery Engine
# Multi-stage build for production.
#
# Stages:
#   deps     — install npm dependencies (npm ci for reproducibility)
#   builder  — compile the Next.js standalone bundle
#   runtime  — slim runtime with curl for healthchecks

# ================================
# Stage 1: Dependencies
# ================================
FROM node:20-alpine AS deps

WORKDIR /app

# Install curl + wget for healthchecks in the runtime stage (carried via COPY).
# Also needed because alpine doesn't ship curl by default.
RUN apk add --no-cache curl wget

COPY package.json ./
# package-lock.json MUST exist for `npm ci` (reproducible installs).
# We fail the build if it's missing rather than silently falling back to `npm install`.
COPY package-lock.json* ./
RUN if [ ! -f package-lock.json ]; then \
      echo "ERROR: package-lock.json not found. Run 'npm install' locally first."; \
      exit 1; \
    fi && \
    npm ci

# ================================
# Stage 2: Builder
# ================================
FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ================================
# Stage 3: Runtime
# ================================
FROM node:20-alpine AS runtime

WORKDIR /app

# Install curl for docker-compose healthchecks.
# (alpine doesn't ship curl by default, and compose's healthcheck uses `curl -f`.)
RUN apk add --no-cache curl wget

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Health check — uses curl (installed above) for parity with docker-compose healthchecks
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=30s \
    CMD curl -sf http://localhost:3000/api/v1/health || exit 1

CMD ["node", "server.js"]
