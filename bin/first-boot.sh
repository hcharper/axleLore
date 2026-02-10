#!/usr/bin/env bash
# first-boot.sh — Runs once on the very first boot of an AxleLore device.
#
# Handles:
#   1. Filesystem expansion (Pi OS usually does this, but we ensure it)
#   2. Unique hostname generation from Pi serial
#   3. Device registration with the update server
#   4. Mark Wi-Fi as configured (wifi-connect will have already run)
#   5. Mark provisioning as complete so this never runs again
#
# Called by: axlelore-firstboot.service (systemd oneshot)
# Guard:    ConditionPathExists=!/var/lib/axlelore/.provisioned
set -euo pipefail

INSTALL_DIR="/opt/axlelore"
STATE_DIR="/var/lib/axlelore"
LOG_TAG="axlelore-firstboot"

log() { logger -t "$LOG_TAG" "$*"; echo "[first-boot] $*"; }

# ──────────────────────────────────────────────
# 1. Expand filesystem (idempotent)
# ──────────────────────────────────────────────
log "Ensuring filesystem is expanded..."
if command -v raspi-config &>/dev/null; then
    raspi-config nonint do_expand_rootfs 2>/dev/null || true
fi

# ──────────────────────────────────────────────
# 2. Generate unique hostname from Pi serial
# ──────────────────────────────────────────────
PI_SERIAL="unknown"
if [[ -f /proc/device-tree/serial-number ]]; then
    PI_SERIAL="$(tr -d '\0' < /proc/device-tree/serial-number)"
fi

SHORT_SERIAL="${PI_SERIAL: -6}"
NEW_HOSTNAME="axlelore-${SHORT_SERIAL}"
log "Setting hostname to ${NEW_HOSTNAME}"
hostnamectl set-hostname "$NEW_HOSTNAME" 2>/dev/null || {
    echo "$NEW_HOSTNAME" > /etc/hostname
    sed -i "s/127\.0\.1\.1.*/127.0.1.1\t${NEW_HOSTNAME}/" /etc/hosts
}

# ──────────────────────────────────────────────
# 3. Generate device identity
# ──────────────────────────────────────────────
DEVICE_ID="${PI_SERIAL}"
mkdir -p "$STATE_DIR"
echo "$DEVICE_ID" > "${STATE_DIR}/device_id"
log "Device ID: ${DEVICE_ID}"

# Read software & knowledge-pack versions
SOFTWARE_VERSION="unknown"
KB_VERSION="unknown"
VEHICLE_TYPE="unknown"

if [[ -f "${INSTALL_DIR}/.env" ]]; then
    VEHICLE_TYPE="$(grep -oP '^DEFAULT_VEHICLE=\K.*' "${INSTALL_DIR}/.env" || echo "unknown")"
fi
if [[ -f "${INSTALL_DIR}/pyproject.toml" ]]; then
    SOFTWARE_VERSION="$(grep -oP '^version\s*=\s*"\K[^"]+' "${INSTALL_DIR}/pyproject.toml" || echo "unknown")"
fi
if [[ -f "${INSTALL_DIR}/data/manifest.json" ]]; then
    KB_VERSION="$(python3 -c "import json; print(json.load(open('${INSTALL_DIR}/data/manifest.json'))['version'])" 2>/dev/null || echo "unknown")"
fi

# ──────────────────────────────────────────────
# 4. Register with update server (best-effort)
# ──────────────────────────────────────────────
UPDATE_BASE_URL="$(grep -oP '^UPDATE_BASE_URL=\K.*' "${INSTALL_DIR}/.env" 2>/dev/null || echo "https://api.axlelore.com")"

log "Attempting device registration..."
REGISTRATION_PAYLOAD=$(cat <<JSON
{
    "device_id": "${DEVICE_ID}",
    "hostname": "${NEW_HOSTNAME}",
    "vehicle_type": "${VEHICLE_TYPE}",
    "software_version": "${SOFTWARE_VERSION}",
    "kb_version": "${KB_VERSION}",
    "hardware": "$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0' || echo 'unknown')"
}
JSON
)

RESPONSE=$(curl -sf -X POST \
    -H "Content-Type: application/json" \
    -d "$REGISTRATION_PAYLOAD" \
    "${UPDATE_BASE_URL}/api/devices/register" \
    --connect-timeout 10 \
    --max-time 30 2>/dev/null || echo "FAILED")

if [[ "$RESPONSE" != "FAILED" ]]; then
    # Extract and store API token
    TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || echo "")
    if [[ -n "$TOKEN" ]]; then
        echo "$TOKEN" > "${STATE_DIR}/.token"
        chmod 600 "${STATE_DIR}/.token"
        log "Device registered successfully"
    else
        log "Registration response did not contain a token"
    fi
else
    log "Device registration failed (no network?). Will retry on next update check."
fi

# ──────────────────────────────────────────────
# 5. Mark Wi-Fi as configured
# ──────────────────────────────────────────────
# If we got this far, networking is up (either wifi-connect ran, or ethernet).
# Stop the wifi-connect service and prevent future runs.
touch "${STATE_DIR}/.wifi-configured"
systemctl stop axlelore-wifi-setup.service 2>/dev/null || true
systemctl disable axlelore-wifi-setup.service 2>/dev/null || true

# ──────────────────────────────────────────────
# 6. Mark provisioning as complete
# ──────────────────────────────────────────────
touch "${STATE_DIR}/.provisioned"
log "First-boot provisioning complete"

# Ensure the main axlelore service starts
systemctl start axlelore.service 2>/dev/null || true
