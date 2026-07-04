#!/usr/bin/env bash
# Provision TLS certificates for Nginx.
#
# Two modes:
#   1. Self-signed (for staging / internal / pre-DNS testing):
#        ./scripts/generate-nginx-ssl.sh --self-signed
#
#   2. Let's Encrypt via certbot (production):
#        ./scripts/generate-nginx-ssl.sh --letsencrypt app.masteryengine.com
#
# The script writes certs to infrastructure/nginx/ssl/ which is bind-mounted
# read-only into the nginx container.
#
# Required for both modes:
#   - infrastructure/nginx/ssl/ directory (created by this script)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SSL_DIR="${PROJECT_ROOT}/infrastructure/nginx/ssl"
NGINX_CONF="${PROJECT_ROOT}/infrastructure/nginx/nginx.conf"

mkdir -p "${SSL_DIR}"

usage() {
  echo "Usage: $0 [--self-signed | --letsencrypt DOMAIN [ALT_DOMAIN...]]"
  echo ""
  echo "Examples:"
  echo "  $0 --self-signed"
  echo "  $0 --letsencrypt app.masteryengine.com"
  echo "  $0 --letsencrypt app.masteryengine.com api.masteryengine.com"
  exit 1
}

if [[ $# -lt 1 ]]; then
  usage
fi

MODE="$1"
shift

generate_self_signed() {
  echo "→ Generating self-signed TLS certificate (365 days)..."
  echo "  WARNING: Self-signed certs are NOT trusted by browsers."
  echo "  Use --letsencrypt for production."

  openssl req -new -x509 -days 365 -nodes \
    -out "${SSL_DIR}/fullchain.pem" \
    -keyout "${SSL_DIR}/privkey.pem" \
    -subj "/CN=localhost/O=Mastery Engine/C=US" \
    -addext "subjectAltName=DNS:localhost,DNS:app.masteryengine.com,DNS:api.masteryengine.com,IP:127.0.0.1" 2>/dev/null

  chmod 600 "${SSL_DIR}/privkey.pem"
  chmod 644 "${SSL_DIR}/fullchain.pem"

  echo "✓ Generated self-signed certs:"
  echo "    ${SSL_DIR}/fullchain.pem"
  echo "    ${SSL_DIR}/privkey.pem"
}

generate_letsencrypt() {
  if [[ $# -lt 1 ]]; then
    echo "ERROR: --letsencrypt requires at least one domain."
    usage
  fi

  local primary_domain="$1"
  shift
  local alt_domains=("$@")

  # Verify certbot is installed
  if ! command -v certbot >/dev/null 2>&1; then
    echo "ERROR: certbot is not installed."
    echo "  Install with: sudo apt install -y certbot"
    exit 1
  fi

  # Build certbot args
  local certbot_args=(
    certonly
    --non-interactive
    --agree-tos
    --email "admin@${primary_domain#*.}"
    --standalone
    -d "${primary_domain}"
  )
  for alt in "${alt_domains[@]}"; do
    certbot_args+=( -d "${alt}" )
  done

  echo "→ Requesting Let's Encrypt certificate for: ${primary_domain} ${alt_domains[*]:-}"
  echo "  (Port 80 must be free — stop nginx first if running.)"

  sudo certbot "${certbot_args[@]}"

  # Locate the live cert directory
  local live_dir="/etc/letsencrypt/live/${primary_domain}"
  if [[ ! -f "${live_dir}/fullchain.pem" ]]; then
    echo "ERROR: certbot completed but ${live_dir}/fullchain.pem not found."
    exit 1
  fi

  # Copy certs to the nginx ssl directory
  sudo cp "${live_dir}/fullchain.pem" "${SSL_DIR}/fullchain.pem"
  sudo cp "${live_dir}/privkey.pem"  "${SSL_DIR}/privkey.pem"

  # Fix ownership (deployer should be the user running docker compose)
  local current_user
  current_user="$(id -un)"
  sudo chown "${current_user}:${current_user}" "${SSL_DIR}/fullchain.pem" "${SSL_DIR}/privkey.pem"
  sudo chmod 600 "${SSL_DIR}/privkey.pem"
  sudo chmod 644 "${SSL_DIR}/fullchain.pem"

  echo "✓ Installed Let's Encrypt certs:"
  echo "    ${SSL_DIR}/fullchain.pem"
  echo "    ${SSL_DIR}/privkey.pem"
  echo ""
  echo "Auto-renewal:"
  echo "  Certbot installs a systemd timer automatically. Verify with:"
  echo "    sudo systemctl list-timers | grep certbot"
  echo ""
  echo "  After renewal, reload nginx:"
  echo "    docker compose -f docker-compose.prod.yml exec nginx nginx -s reload"
  echo ""
  echo "  Or add this crontab entry (root):"
  echo "    0 3 * * * certbot renew --quiet --post-hook \"docker compose -f ${PROJECT_ROOT}/docker-compose.prod.yml exec nginx nginx -s reload\""
}

case "${MODE}" in
  --self-signed)
    generate_self_signed
    ;;
  --letsencrypt)
    generate_letsencrypt "$@"
    ;;
  -h|--help)
    usage
    ;;
  *)
    echo "Unknown mode: ${MODE}"
    usage
    ;;
esac

# Verify the nginx.conf references match
if [[ -f "${NGINX_CONF}" ]]; then
  if grep -q "/etc/nginx/ssl/fullchain.pem" "${NGINX_CONF}" && \
     grep -q "/etc/nginx/ssl/privkey.pem" "${NGINX_CONF}"; then
    echo "✓ nginx.conf references match the generated file paths."
  else
    echo "⚠️  WARNING: nginx.conf does not reference /etc/nginx/ssl/{fullchain,privkey}.pem"
    echo "    Verify the ssl_certificate paths in ${NGINX_CONF}"
  fi
fi
