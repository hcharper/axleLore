#!/usr/bin/env bash
# build-image.sh — Build a flashable RigSherpa SD-card image for a vehicle.
#
# Usage:
#   ./build-image.sh <vehicle_type>         # e.g. ./build-image.sh fzj80
#   VEHICLE_TYPE=fzj80 ./build-image.sh     # alternative
#
# Requires: Docker (or a Debian/Ubuntu host with qemu-user-static)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# ── resolve vehicle type ─────────────────────
VEHICLE_TYPE="${1:-${VEHICLE_TYPE:-}}"
if [[ -z "$VEHICLE_TYPE" ]]; then
    echo "Usage: $0 <vehicle_type>"
    echo "Available vehicles:"
    for f in "$SCRIPT_DIR/config/"*.conf; do
        [[ "$(basename "$f")" == "base.conf" ]] && continue
        basename "$f" .conf
    done
    exit 1
fi

VEHICLE_CONF="$SCRIPT_DIR/config/${VEHICLE_TYPE}.conf"
if [[ ! -f "$VEHICLE_CONF" ]]; then
    echo "Error: No build config found at $VEHICLE_CONF"
    exit 1
fi

# ── load configuration ───────────────────────
# shellcheck source=config/base.conf
source "$SCRIPT_DIR/config/base.conf"
# shellcheck source=config/fzj80.conf
source "$VEHICLE_CONF"

echo "=========================================="
echo "  RigSherpa Image Builder"
echo "  Vehicle: ${VEHICLE_NAME} (${VEHICLE_TYPE})"
echo "  Version: ${RIGSHERPA_VERSION}"
echo "=========================================="

# ── pre-flight checks ────────────────────────
KNOWLEDGE_PACK="${ROOT_DIR}/data/knowledge_packs/${VEHICLE_TYPE}"
if [[ ! -d "$KNOWLEDGE_PACK/chromadb" ]]; then
    echo "WARNING: Knowledge pack not found at $KNOWLEDGE_PACK"
    echo "  Run:  tools/kb_builder/build_pack.sh ${VEHICLE_TYPE}"
    echo "  Continuing without knowledge data (empty ChromaDB)."
fi

VEHICLE_YAML="${ROOT_DIR}/config/vehicles/${VEHICLE_TYPE}.yaml"
if [[ ! -f "$VEHICLE_YAML" ]]; then
    echo "Error: Vehicle config not found at $VEHICLE_YAML"
    exit 1
fi

VEHICLE_KEYWORDS="${ROOT_DIR}/config/vehicles/${VEHICLE_TYPE}_keywords.yaml"
if [[ ! -f "$VEHICLE_KEYWORDS" ]]; then
    echo "WARNING: Keyword routing config not found at $VEHICLE_KEYWORDS"
    echo "  Default routing will be used."
fi

# ── prepare filesystem layer ─────────────────
# CustomPiOS copies everything under modules/rigsherpa/filesystem/
# into the image root filesystem verbatim.
FS_DIR="$SCRIPT_DIR/modules/rigsherpa/filesystem"
rm -rf "$FS_DIR"
mkdir -p "$FS_DIR/opt/rigsherpa"

echo "Copying application source..."
# Copy app code, configs, bins (exclude dev/build artefacts)
rsync -a --exclude='.venv' --exclude='.git' --exclude='__pycache__' \
    --exclude='*.pyc' --exclude='build/' --exclude='data/' \
    --exclude='.env' --exclude='node_modules' \
    "$ROOT_DIR/" "$FS_DIR/opt/rigsherpa/"

echo "Copying vehicle config..."
mkdir -p "$FS_DIR/opt/rigsherpa/config/vehicles"
cp "$VEHICLE_YAML" "$FS_DIR/opt/rigsherpa/config/vehicles/"
[[ -f "$VEHICLE_KEYWORDS" ]] && cp "$VEHICLE_KEYWORDS" "$FS_DIR/opt/rigsherpa/config/vehicles/"

echo "Copying knowledge pack..."
mkdir -p "$FS_DIR/opt/rigsherpa/data"
if [[ -d "$KNOWLEDGE_PACK/chromadb" ]]; then
    cp -r "$KNOWLEDGE_PACK/chromadb" "$FS_DIR/opt/rigsherpa/data/chromadb"
fi
if [[ -f "$KNOWLEDGE_PACK/manifest.json" ]]; then
    cp "$KNOWLEDGE_PACK/manifest.json" "$FS_DIR/opt/rigsherpa/data/"
fi

# Copy GPG public key for update verification
if [[ -n "${GPG_KEY_ID:-}" ]]; then
    gpg --export --armor "$GPG_KEY_ID" > "$FS_DIR/opt/rigsherpa/rigsherpa-release.asc"
fi

# ── build with CustomPiOS ────────────────────
CUSTOMPIOS_DIR="$SCRIPT_DIR/CustomPiOS"
if [[ ! -d "$CUSTOMPIOS_DIR" ]]; then
    echo "Cloning CustomPiOS..."
    git clone --depth 1 https://github.com/guysoft/CustomPiOS.git "$CUSTOMPIOS_DIR"
fi

# Export variables the chroot_script needs
export VEHICLE_TYPE VEHICLE_NAME RIGSHERPA_VERSION
export OLLAMA_MODEL OLLAMA_FALLBACK_MODEL PULL_FALLBACK
export EMBEDDING_MODEL
export WIFI_CONNECT_VERSION

OUTPUT_DIR="$SCRIPT_DIR/output"
mkdir -p "$OUTPUT_DIR"

# Build using Docker (cross-compile arm64 on x86_64)
echo ""
echo "Building image (this may take 30-60 minutes)..."
echo ""

pushd "$CUSTOMPIOS_DIR/src" > /dev/null

# Link our module into the CustomPiOS workspace
ln -sfn "$SCRIPT_DIR/modules/rigsherpa" modules/rigsherpa

# Create the build config
cat > config <<BUILDCFG
export MODULES="base(rigsherpa)"
export BASE_ARCH="arm64"
BUILDCFG

sudo bash -x build
popd > /dev/null

# ── collect output ───────────────────────────
TIMESTAMP="$(date +%Y%m%d)"
OUTPUT_NAME="rigsherpa-${VEHICLE_TYPE}-${RIGSHERPA_VERSION}-${TIMESTAMP}"

# CustomPiOS places images in src/workspace/
BUILT_IMAGE=$(find "$CUSTOMPIOS_DIR/src/workspace/" -name '*.img' -type f | head -1)
if [[ -z "$BUILT_IMAGE" ]]; then
    echo "Error: No image found after build."
    exit 1
fi

echo "Compressing image..."
gzip -c "$BUILT_IMAGE" > "$OUTPUT_DIR/${OUTPUT_NAME}.img.gz"

echo ""
echo "=========================================="
echo "  Build complete!"
echo "  Image: $OUTPUT_DIR/${OUTPUT_NAME}.img.gz"
echo "  Size:  $(du -h "$OUTPUT_DIR/${OUTPUT_NAME}.img.gz" | cut -f1)"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Sign:   ./sign-release.sh $OUTPUT_DIR/${OUTPUT_NAME}.img.gz"
echo "  2. Upload: ./upload-release.sh $OUTPUT_DIR/${OUTPUT_NAME}*"

# Cleanup the filesystem layer (it can be large)
rm -rf "$FS_DIR"
