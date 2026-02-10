#!/usr/bin/env bash
# sign-release.sh — GPG-sign and checksum a release artefact.
#
# Usage:
#   ./sign-release.sh <file>
#   GPG_KEY_ID=ABC123 ./sign-release.sh axlelore-fzj80-0.2.0.img.gz
set -euo pipefail

FILE="${1:?Usage: $0 <file>}"

if [[ ! -f "$FILE" ]]; then
    echo "Error: File not found: $FILE"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config/base.conf"

GPG_KEY_ID="${GPG_KEY_ID:-}"

echo "Generating SHA256 checksum..."
sha256sum "$FILE" > "${FILE}.sha256"
echo "  → ${FILE}.sha256"

echo "Generating GPG signature..."
if [[ -n "$GPG_KEY_ID" ]]; then
    gpg --detach-sign --armor --default-key "$GPG_KEY_ID" -o "${FILE}.asc" "$FILE"
else
    gpg --detach-sign --armor -o "${FILE}.asc" "$FILE"
fi
echo "  → ${FILE}.asc"

echo ""
echo "Release artefacts:"
ls -lh "$FILE" "${FILE}.sha256" "${FILE}.asc"
echo ""
echo "Verification commands for buyers:"
echo "  sha256sum -c ${FILE##*/}.sha256"
echo "  gpg --verify ${FILE##*/}.asc ${FILE##*/}"
