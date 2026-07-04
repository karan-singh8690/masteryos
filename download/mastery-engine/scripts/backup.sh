#!/bin/bash
# Disaster Recovery — Backup Script
# Creates encrypted backups of PostgreSQL, Redis, and configuration.
#
# Task 025-deploy fixes applied:
#   - Flag handling moved to the top (--verify and --restore no longer run a
#     full backup before doing their job).
#   - Redis BGSAVE + LASTSAVE now pass the password via -a flag.
#   - Redis dump file is fetched from inside the container via `docker compose
#     exec ... cp` (works when Redis runs in a Docker volume, not on the host).
#   - .env file is no longer included in the plaintext tar — only in the
#     encrypted archive. A separate `env.backup` is excluded entirely if
#     encryption is disabled, and a warning is printed.
#   - SHA256 checksum emitted alongside every backup for tamper detection.
#   - Exit code is non-zero on failure (so cron / monitoring can detect it).
#
# Usage:
#   ./backup.sh                    # Full backup
#   ./backup.sh --verify           # Verify the latest backup
#   ./backup.sh --restore FILE     # Restore from backup
#
# Schedule via cron: 0 2 * * * /opt/mastery-engine/scripts/backup.sh

set -euo pipefail

# ============================================================
# Argument parsing — handle flags FIRST, before any backup work.
# ============================================================

ACTION="backup"
RESTORE_FILE=""

if [[ $# -ge 1 ]]; then
  case "$1" in
    --verify)
      ACTION="verify"
      ;;
    --restore)
      ACTION="restore"
      RESTORE_FILE="${2:-}"
      if [[ -z "$RESTORE_FILE" ]]; then
        echo "ERROR: --restore requires a backup file argument"
        echo "Usage: $0 --restore <backup_file>"
        exit 2
      fi
      ;;
    -h|--help)
      echo "Usage: $0 [--verify | --restore <backup_file>]"
      echo ""
      echo "  no args         Full backup (default)"
      echo "  --verify        Verify the most recent backup"
      echo "  --restore FILE  Restore from FILE (interactive)"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: $0 [--verify | --restore <backup_file>]"
      exit 2
      ;;
  esac
fi

# ============================================================
# Configuration
# ============================================================

BACKUP_DIR="${BACKUP_DIR:-/opt/mastery-engine/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"

DB_HOST="${DATABASE_HOST:-localhost}"
DB_PORT="${DATABASE_PORT:-5432}"
DB_NAME="${DATABASE_NAME:-mastery_engine}"
DB_USER="${DATABASE_USER:-mastery}"
DB_PASSWORD="${DATABASE_PASSWORD:-}"

REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

# Docker compose project name (used to find the redis container name)
DOCKER_COMPOSE_PROJECT="${DOCKER_COMPOSE_PROJECT:-masteryengine}"
REDIS_CONTAINER="${REDIS_CONTAINER:-${DOCKER_COMPOSE_PROJECT}-redis-1}"

S3_BUCKET="${S3_BACKUP_BUCKET:-}"  # Optional S3 upload
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"  # Optional Slack notification

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="mastery_engine_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# ============================================================
# Functions
# ============================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

notify() {
    local message="$1"
    log "$message"
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -s -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{\"text\": \"🗄️ Backup: $message\"}" || true
    fi
}

error_exit() {
    notify "❌ ERROR: $1"
    exit 1
}

# Build the Redis CLI auth args (empty if no password)
redis_auth_args() {
    if [[ -n "$REDIS_PASSWORD" ]]; then
        echo "-a $REDIS_PASSWORD --no-auth-warning"
    fi
}

# ============================================================
# Pre-flight Checks
# ============================================================

mkdir -p "$BACKUP_DIR" || error_exit "Cannot create backup directory: $BACKUP_DIR"

# ============================================================
# VERIFY mode
# ============================================================

if [[ "$ACTION" == "verify" ]]; then
    LATEST_BACKUP=$(ls -t "${BACKUP_DIR}"/mastery_engine_*.tar.gz* 2>/dev/null | head -1)
    if [ -z "$LATEST_BACKUP" ]; then
        error_exit "No backups found to verify"
    fi

    log "Verifying: $LATEST_BACKUP"

    if [ ! -r "$LATEST_BACKUP" ]; then
        error_exit "Backup file not readable: $LATEST_BACKUP"
    fi

    # Verify SHA256 checksum if it exists
    CHECKSUM_FILE="${LATEST_BACKUP}.sha256"
    if [[ -f "$CHECKSUM_FILE" ]]; then
        log "Verifying SHA256 checksum..."
        (cd "$(dirname "$LATEST_BACKUP")" && sha256sum -c "$(basename "$CHECKSUM_FILE")") > /dev/null 2>&1 \
            || error_exit "Checksum verification failed — backup may be corrupted or tampered with"
        log "✅ Checksum OK"
    else
        log "⚠️  No checksum file found ($(basename "$CHECKSUM_FILE")) — skipping checksum verification"
    fi

    # Verify archive integrity
    log "Verifying archive integrity..."
    if [[ "$LATEST_BACKUP" == *.enc ]]; then
        if [ -z "$ENCRYPTION_KEY" ]; then
            error_exit "Encrypted backup but no BACKUP_ENCRYPTION_KEY set"
        fi
        openssl enc -d -aes-256-cbc -pbkdf2 \
            -in "$LATEST_BACKUP" \
            -pass "pass:${ENCRYPTION_KEY}" | tar tzf - > /dev/null 2>&1 \
            || error_exit "Backup archive is corrupted"
    else
        tar tzf "$LATEST_BACKUP" > /dev/null 2>&1 \
            || error_exit "Backup archive is corrupted"
    fi

    log "✅ Backup verification passed"
    exit 0
fi

# ============================================================
# RESTORE mode
# ============================================================

if [[ "$ACTION" == "restore" ]]; then
    log "⚠️  RESTORE MODE — This will OVERWRITE existing data!"
    log "Backup file: $RESTORE_FILE"

    if [ ! -r "$RESTORE_FILE" ]; then
        error_exit "Backup file not readable: $RESTORE_FILE"
    fi

    read -p "Type 'RESTORE' to confirm: " CONFIRM
    if [ "$CONFIRM" != "RESTORE" ]; then
        log "Restore cancelled"
        exit 0
    fi

    TEMP_DIR=$(mktemp -d)
    log "Extracting backup to $TEMP_DIR..."

    if [[ "$RESTORE_FILE" == *.enc ]]; then
        if [ -z "$ENCRYPTION_KEY" ]; then
            error_exit "Encrypted backup but no BACKUP_ENCRYPTION_KEY set"
        fi
        openssl enc -d -aes-256-cbc -pbkdf2 \
            -in "$RESTORE_FILE" \
            -pass "pass:${ENCRYPTION_KEY}" | \
            tar xzf - -C "$TEMP_DIR"
    else
        tar xzf "$RESTORE_FILE" -C "$TEMP_DIR"
    fi

    BACKUP_DIR_NAME=$(ls "$TEMP_DIR")

    # Restore PostgreSQL
    log "Restoring PostgreSQL..."
    PGPASSWORD="$DB_PASSWORD" pg_restore \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --clean \
        --if-exists \
        --verbose \
        "${TEMP_DIR}/${BACKUP_DIR_NAME}/postgres.dump" 2>&1 \
        || log "⚠️ Some restore warnings (normal — usually 'relation does not exist' on --clean)"

    # Restore Redis
    if [ -f "${TEMP_DIR}/${BACKUP_DIR_NAME}/redis_dump.rdb" ]; then
        log "Restoring Redis..."
        log "  Redis restore is manual — automated restore is unsafe while Redis is running."
        log "  Steps:"
        log "    1. docker compose -f docker-compose.prod.yml stop redis"
        log "    2. docker cp ${TEMP_DIR}/${BACKUP_DIR_NAME}/redis_dump.rdb ${REDIS_CONTAINER}:/data/dump.rdb"
        log "    3. docker compose -f docker-compose.prod.yml start redis"
        log "  Restored file: ${TEMP_DIR}/${BACKUP_DIR_NAME}/redis_dump.rdb"
    fi

    rm -rf "$TEMP_DIR"
    notify "✅ Restore complete from $RESTORE_FILE"
    exit 0
fi

# ============================================================
# BACKUP mode (default)
# ============================================================

log "Starting Mastery Engine backup..."

mkdir -p "$BACKUP_PATH" || error_exit "Cannot create backup path: $BACKUP_PATH"

# ============================================================
# PostgreSQL Backup
# ============================================================

log "Backing up PostgreSQL..."

PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=custom \
    --compress=9 \
    --verbose \
    --file="${BACKUP_PATH}/postgres.dump" 2>&1 || error_exit "PostgreSQL backup failed"

POSTGRES_SIZE=$(du -sh "${BACKUP_PATH}/postgres.dump" | cut -f1)
log "PostgreSQL backup complete: ${POSTGRES_SIZE}"

# ============================================================
# Redis Backup
# ============================================================

log "Backing up Redis..."

# Task 025-deploy fix: pass the password to redis-cli.
REDIS_AUTH="$(redis_auth_args)"

# Trigger Redis BGSAVE (with auth)
if [[ -n "$REDIS_AUTH" ]]; then
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" $REDIS_AUTH BGSAVE > /dev/null 2>&1 || true
else
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" BGSAVE > /dev/null 2>&1 || true
fi

# Wait for BGSAVE to complete (poll LASTSAVE up to 30s)
LASTSAVE_BEFORE=0
if [[ -n "$REDIS_AUTH" ]]; then
    LASTSAVE_BEFORE=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" $REDIS_AUTH LASTSAVE 2>/dev/null || echo "0")
else
    LASTSAVE_BEFORE=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LASTSAVE 2>/dev/null || echo "0")
fi

for i in $(seq 1 30); do
    if [[ -n "$REDIS_AUTH" ]]; then
        LASTSAVE_NOW=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" $REDIS_AUTH LASTSAVE 2>/dev/null || echo "0")
    else
        LASTSAVE_NOW=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LASTSAVE 2>/dev/null || echo "0")
    fi
    if [[ "$LASTSAVE_NOW" != "$LASTSAVE_BEFORE" && "$LASTSAVE_NOW" != "0" ]]; then
        break
    fi
    sleep 1
done

# Task 025-deploy fix: copy dump.rdb from inside the Docker container
# (the host path /var/lib/redis/dump.rdb doesn't exist when Redis runs in a volume).
REDIS_DUMP="${BACKUP_PATH}/redis_dump.rdb"
REDIS_DUMPED=0

# Try docker compose first (production setup)
if command -v docker >/dev/null 2>&1; then
    if docker cp "${REDIS_CONTAINER}:/data/dump.rdb" "$REDIS_DUMP" 2>/dev/null; then
        REDIS_DUMPED=1
        log "  (copied via docker cp from ${REDIS_CONTAINER})"
    fi
fi

# Fallback: host path (for non-Docker deployments)
if [[ "$REDIS_DUMPED" -eq 0 && -f /var/lib/redis/dump.rdb ]]; then
    cp /var/lib/redis/dump.rdb "$REDIS_DUMP"
    REDIS_DUMPED=1
    log "  (copied from host path /var/lib/redis/dump.rdb)"
fi

if [[ "$REDIS_DUMPED" -eq 1 ]]; then
    REDIS_SIZE=$(du -sh "$REDIS_DUMP" | cut -f1)
    log "Redis backup complete: ${REDIS_SIZE}"
else
    log "⚠️  Redis dump file not found — skipping Redis backup (Redis may not be running, or container name differs from ${REDIS_CONTAINER})"
    log "    Set REDIS_CONTAINER env var to override the container name."
fi

# ============================================================
# Configuration Backup
# ============================================================

log "Backing up configuration..."

# Task 025-deploy fix: never include .env in the plaintext tar.
# The .env file contains all secrets (DB passwords, JWT keys, SMTP passwords).
# It is only safe to include when the tar is then encrypted.
#
# Strategy: include .env in the tar ONLY IF encryption is enabled.
# If encryption is disabled, print a warning and skip the .env.

INCLUDE_ENV=0
if [[ -n "$ENCRYPTION_KEY" ]]; then
    INCLUDE_ENV=1
fi

if [[ -f /opt/mastery-engine/.env.production ]]; then
    if [[ "$INCLUDE_ENV" -eq 1 ]]; then
        cp /opt/mastery-engine/.env.production "${BACKUP_PATH}/env.production"
        log "  (env.production included — will be encrypted)"
    else
        log "  ⚠️  .env.production NOT included — set BACKUP_ENCRYPTION_KEY to include it"
    fi
elif [[ -f /opt/mastery-engine/.env ]]; then
    if [[ "$INCLUDE_ENV" -eq 1 ]]; then
        cp /opt/mastery-engine/.env "${BACKUP_PATH}/env.backup"
        log "  (.env included — will be encrypted)"
    else
        log "  ⚠️  .env NOT included — set BACKUP_ENCRYPTION_KEY to include it"
    fi
fi

# Copy Docker Compose files (no secrets, safe to include)
for f in /opt/mastery-engine/docker-compose.yml /opt/mastery-engine/docker-compose.prod.yml; do
    if [[ -f "$f" ]]; then
        cp "$f" "${BACKUP_PATH}/"
    fi
done

# Copy nginx config (no secrets if certs are excluded)
if [ -d /opt/mastery-engine/infrastructure/nginx ]; then
    cp -r /opt/mastery-engine/infrastructure/nginx "${BACKUP_PATH}/nginx"
    # Remove the ssl subdirectory from the backup (certs are sensitive)
    rm -rf "${BACKUP_PATH}/nginx/ssl" 2>/dev/null || true
fi

log "Configuration backup complete"

# ============================================================
# Create Archive
# ============================================================

log "Creating archive..."

cd "$BACKUP_DIR"
tar czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
ARCHIVE_SIZE=$(du -sh "${BACKUP_NAME}.tar.gz" | cut -f1)

# Compute SHA256 checksum of the tarball BEFORE encryption.
log "Computing SHA256 checksum..."
sha256sum "${BACKUP_NAME}.tar.gz" > "${BACKUP_NAME}.tar.gz.sha256"

# Encrypt if key is set
if [ -n "$ENCRYPTION_KEY" ]; then
    log "Encrypting backup..."
    openssl enc -aes-256-cbc \
        -salt \
        -pbkdf2 \
        -in "${BACKUP_NAME}.tar.gz" \
        -out "${BACKUP_NAME}.tar.gz.enc" \
        -pass "pass:${ENCRYPTION_KEY}"
    # Compute checksum of the encrypted file too.
    sha256sum "${BACKUP_NAME}.tar.gz.enc" > "${BACKUP_NAME}.tar.gz.enc.sha256"
    rm "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}.tar.gz.sha256"
    FINAL_FILE="${BACKUP_NAME}.tar.gz.enc"
    FINAL_CHECKSUM="${BACKUP_NAME}.tar.gz.enc.sha256"
    log "Backup encrypted"
else
    FINAL_FILE="${BACKUP_NAME}.tar.gz"
    FINAL_CHECKSUM="${BACKUP_NAME}.tar.gz.sha256"
fi

FINAL_SIZE=$(du -sh "$FINAL_FILE" | cut -f1)

# ============================================================
# Upload to S3 (optional)
# ============================================================

if [ -n "$S3_BUCKET" ]; then
    log "Uploading to S3..."
    aws s3 cp "$FINAL_FILE" "s3://${S3_BUCKET}/backups/" \
        --storage-class STANDARD_IA \
        --no-progress || log "⚠️ S3 upload failed (continuing)"
    aws s3 cp "$FINAL_CHECKSUM" "s3://${S3_BUCKET}/backups/" \
        --storage-class STANDARD_IA \
        --no-progress || log "⚠️ S3 checksum upload failed (continuing)"
    log "S3 upload complete"
fi

# ============================================================
# Cleanup Old Backups
# ============================================================

log "Cleaning up backups older than ${RETENTION_DAYS} days..."

find "$BACKUP_DIR" -name "mastery_engine_*.tar.gz*" -type f -mtime +${RETENTION_DAYS} -delete
find "$BACKUP_DIR" -name "mastery_engine_*.sha256" -type f -mtime +${RETENTION_DAYS} -delete
find "$BACKUP_DIR" -type d -name "mastery_engine_*" -mtime +${RETENTION_DAYS} -exec rm -rf {} \; 2>/dev/null || true

log "Cleaned up old backups"

# Remove the staging directory
rm -rf "$BACKUP_PATH"

# ============================================================
# Summary
# ============================================================

notify "✅ Backup complete: ${FINAL_FILE} (${FINAL_SIZE})"

log ""
log "========================================"
log "Backup Summary"
log "========================================"
log "  Name:     ${FINAL_FILE}"
log "  Size:     ${FINAL_SIZE}"
log "  Path:     ${BACKUP_DIR}/${FINAL_FILE}"
log "  Checksum: ${BACKUP_DIR}/${FINAL_CHECKSUM}"
log "  PostgreSQL: ${POSTGRES_SIZE:-N/A}"
log "  Redis:       ${REDIS_SIZE:-skipped}"
log "  Encrypted:   $([[ -n "$ENCRYPTION_KEY" ]] && echo yes || echo no)"
log "  Retention:   ${RETENTION_DAYS} days"
log "  S3:          ${S3_BUCKET:-not configured}"
log "========================================"
