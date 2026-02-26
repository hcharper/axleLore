#!/usr/bin/env bash
# check-update.sh — Check for and apply knowledge-pack updates.
#
# Called by:
#   - rigsherpa-update.timer  (every 6 hours)
#   - NetworkManager dispatcher (on Wi-Fi connect)
#
# Flow:
#   1. Check if device is online
#   2. POST device info → GET update metadata
#   3. If newer version available, download signed .tar.gz
#   4. Verify GPG signature
#   5. Extract atomically into /opt/rigsherpa/data/chromadb/
#   6. Restart rigsherpa.service to reload ChromaDB
#   7. Report success to server
set -euo pipefail

INSTALL_DIR="/opt/rigsherpa"
STATE_DIR="/var/lib/rigsherpa"
DATA_DIR="${INSTALL_DIR}/data"
LOG_TAG="rigsherpa-update"
LOCK_FILE="/tmp/rigsherpa-update.lock"

log()  { logger -t "$LOG_TAG" "$*"; }
warn() { logger -t "$LOG_TAG" -p user.warning "$*"; }

# ── Prevent concurrent runs ──────────────────
exec 200>"$LOCK_FILE"
flock -n 200 || { log "Update already in progress, skipping."; exit 0; }

# ── Read device state ────────────────────────
DEVICE_ID=""
API_TOKEN=""
KB_VERSION="0.0.0"
VEHICLE_TYPE="fzj80"

[[ -f "${STATE_DIR}/device_id" ]]  && DEVICE_ID="$(cat "${STATE_DIR}/device_id")"
[[ -f "${STATE_DIR}/.token" ]]     && API_TOKEN="$(cat "${STATE_DIR}/.token")"

if [[ -f "${INSTALL_DIR}/.env" ]]; then
    VEHICLE_TYPE="$(grep -oP '^DEFAULT_VEHICLE=\K.*' "${INSTALL_DIR}/.env" || echo "fzj80")"
fi
if [[ -f "${DATA_DIR}/manifest.json" ]]; then
    KB_VERSION="$(python3 -c "import json; print(json.load(open('${DATA_DIR}/manifest.json'))['version'])" 2>/dev/null || echo "0.0.0")"
fi

UPDATE_BASE_URL="$(grep -oP '^UPDATE_BASE_URL=\K.*' "${INSTALL_DIR}/.env" 2>/dev/null || echo "https://api.rigsherpa.com")"

# ── Pre-flight: are we online? ───────────────
if ! curl -sf --connect-timeout 5 --max-time 10 "${UPDATE_BASE_URL}/health" >/dev/null 2>&1; then
    log "Update server unreachable. Will retry later."
    exit 0
fi

# ── If we never registered, try now ──────────
if [[ -z "$API_TOKEN" && -n "$DEVICE_ID" ]]; then
    log "No API token found. Attempting registration..."
    /opt/rigsherpa/bin/first-boot.sh 2>/dev/null || true
    [[ -f "${STATE_DIR}/.token" ]] && API_TOKEN="$(cat "${STATE_DIR}/.token")"
fi

# ── Build auth header ────────────────────────
AUTH_HEADER=""
if [[ -n "$API_TOKEN" ]]; then
    AUTH_HEADER="Authorization: Bearer ${API_TOKEN}"
fi

# ── Check for update ─────────────────────────
log "Checking for updates (vehicle=${VEHICLE_TYPE}, kb=${KB_VERSION})..."

CHECK_URL="${UPDATE_BASE_URL}/api/updates/check"
RESPONSE=$(curl -sf \
    -H "Content-Type: application/json" \
    ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
    -d "{\"device_id\":\"${DEVICE_ID}\",\"vehicle_type\":\"${VEHICLE_TYPE}\",\"kb_version\":\"${KB_VERSION}\"}" \
    --connect-timeout 10 \
    --max-time 30 \
    "$CHECK_URL" 2>/dev/null || echo "")

if [[ -z "$RESPONSE" ]]; then
    warn "Failed to check for updates."
    exit 0
fi

# Parse response
UPDATE_AVAILABLE=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('update_available', False))" 2>/dev/null || echo "False")

if [[ "$UPDATE_AVAILABLE" != "True" ]]; then
    log "No update available. Current KB version: ${KB_VERSION}"
    exit 0
fi

NEW_VERSION=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['new_version'])" 2>/dev/null)
DOWNLOAD_URL=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['download_url'])" 2>/dev/null)

log "Update available: ${KB_VERSION} → ${NEW_VERSION}"

# ── Download update ──────────────────────────
TMPDIR=$(mktemp -d /tmp/rigsherpa-update-XXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT

PACK_FILE="${TMPDIR}/knowledge-pack.tar.gz"
PACK_SIG="${TMPDIR}/knowledge-pack.tar.gz.asc"

log "Downloading knowledge pack v${NEW_VERSION}..."
if ! curl -fSL --connect-timeout 15 --max-time 600 -C - \
    ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
    -o "$PACK_FILE" "$DOWNLOAD_URL"; then
    warn "Download failed."
    exit 1
fi

# Download signature
SIG_URL="${DOWNLOAD_URL}.asc"
curl -fsSL --connect-timeout 10 --max-time 30 \
    ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
    -o "$PACK_SIG" "$SIG_URL" 2>/dev/null || true

# ── Verify GPG signature ────────────────────
GPG_PUBKEY="${INSTALL_DIR}/rigsherpa-release.asc"
if [[ -f "$PACK_SIG" && -f "$GPG_PUBKEY" ]]; then
    log "Verifying GPG signature..."
    GNUPGHOME=$(mktemp -d)
    export GNUPGHOME
    gpg --batch --import "$GPG_PUBKEY" 2>/dev/null
    if gpg --batch --verify "$PACK_SIG" "$PACK_FILE" 2>/dev/null; then
        log "Signature verified OK"
    else
        warn "GPG signature verification FAILED. Aborting update."
        rm -rf "$GNUPGHOME"
        exit 1
    fi
    rm -rf "$GNUPGHOME"
else
    warn "No signature file or public key. Skipping verification."
fi

# ── Apply update atomically ──────────────────
log "Applying knowledge pack update..."

STAGING="${DATA_DIR}/chromadb_staging"
rm -rf "$STAGING"
mkdir -p "$STAGING"

tar xzf "$PACK_FILE" -C "$STAGING"

# Validate: must contain a manifest.json
if [[ ! -f "${STAGING}/manifest.json" ]]; then
    # Try one level deep (tarball may have a top-level directory)
    NESTED=$(find "$STAGING" -maxdepth 2 -name manifest.json | head -1)
    if [[ -z "$NESTED" ]]; then
        warn "Downloaded pack is missing manifest.json. Aborting."
        rm -rf "$STAGING"
        exit 1
    fi
    # Move contents up
    NESTED_DIR="$(dirname "$NESTED")"
    mv "$NESTED_DIR"/* "$STAGING/" 2>/dev/null || true
fi

# Atomic swap: old → backup, staging → live
BACKUP="${DATA_DIR}/chromadb_backup"
rm -rf "$BACKUP"

# Stop the service briefly for a clean swap
systemctl stop rigsherpa.service 2>/dev/null || true

if [[ -d "${DATA_DIR}/chromadb" ]]; then
    mv "${DATA_DIR}/chromadb" "$BACKUP"
fi

# Move the chromadb data from staging into place
if [[ -d "${STAGING}/chromadb" ]]; then
    mv "${STAGING}/chromadb" "${DATA_DIR}/chromadb"
else
    # If the pack root IS the chromadb data
    mv "$STAGING" "${DATA_DIR}/chromadb"
fi

# Copy manifest to data root
[[ -f "${STAGING}/manifest.json" ]] && cp "${STAGING}/manifest.json" "${DATA_DIR}/manifest.json" 2>/dev/null || true

# Fix ownership
chown -R rigsherpa:rigsherpa "${DATA_DIR}/chromadb" 2>/dev/null || true

# Restart the service
systemctl start rigsherpa.service

log "Knowledge pack updated to v${NEW_VERSION}"

# Clean up backup (keep one generation)
rm -rf "$BACKUP"

# ── Report success ───────────────────────────
curl -sf -X POST \
    -H "Content-Type: application/json" \
    ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
    -d "{\"device_id\":\"${DEVICE_ID}\",\"vehicle_type\":\"${VEHICLE_TYPE}\",\"kb_version\":\"${NEW_VERSION}\",\"status\":\"success\"}" \
    --connect-timeout 10 \
    --max-time 15 \
    "${UPDATE_BASE_URL}/api/updates/report" 2>/dev/null || true

log "Update complete."
