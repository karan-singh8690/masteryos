#!/usr/bin/env bash
# Generate a self-signed SSL certificate for PostgreSQL (inter-container TLS).
#
# Postgres 13+ supports `ssl=on` with a self-signed cert — sufficient for
# traffic that never leaves the Docker private network. For public exposure
# (not recommended), use a CA-signed cert.
#
# Usage:
#   ./scripts/generate-postgres-ssl.sh
#
# Output:
#   infrastructure/postgres/ssl/postgres.pem       (cert)
#   infrastructure/postgres/ssl/postgres-key.pem   (private key, chmod 600)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SSL_DIR="${PROJECT_ROOT}/infrastructure/postgres/ssl"

mkdir -p "${SSL_DIR}"

if [[ -f "${SSL_DIR}/postgres.pem" && -f "${SSL_DIR}/postgres-key.pem" ]]; then
  echo "✓ PostgreSQL SSL certs already exist at ${SSL_DIR}/"
  echo "  To regenerate, delete them first: rm ${SSL_DIR}/postgres*.pem"
  exit 0
fi

echo "→ Generating PostgreSQL self-signed SSL certificate (3650 days)..."

openssl req -new -x509 -days 3650 -nodes \
  -out "${SSL_DIR}/postgres.pem" \
  -keyout "${SSL_DIR}/postgres-key.pem" \
  -subj "/CN=postgres/O=Mastery Engine/C=US" \
  -addext "subjectAltName=DNS:postgres,DNS:localhost,IP:127.0.0.1" 2>/dev/null

# Postgres requires the key file to be 0600 or it refuses to start.
chmod 600 "${SSL_DIR}/postgres-key.pem"
chmod 644 "${SSL_DIR}/postgres.pem"

echo "✓ Generated:"
echo "    ${SSL_DIR}/postgres.pem"
echo "    ${SSL_DIR}/postgres-key.pem"
echo ""
echo "These files are mounted read-only into the postgres container at:"
echo "    /etc/ssl/certs/postgres.pem"
echo "    /etc/ssl/private/postgres-key.pem"
