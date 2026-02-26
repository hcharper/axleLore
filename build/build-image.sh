#!/usr/bin/env bash
# build-image.sh — Build a flashable RigSherpa SD-card image for a vehicle.
#
# Usage:
#   ./build-image.sh <vehicle_type>         # e.g. ./build-image.sh fzj80
#   VEHICLE_TYPE=fzj80 ./build-image.sh     # alternative
#
# Requires: Docker
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

# Restore CustomPiOS framework config before Docker build (may have been overwritten
# by a previous build's distribution config). The Docker image must contain the
# original framework config script, not our distribution variables.
git -C "$CUSTOMPIOS_DIR" checkout -- src/config

# Build the Docker image from clean CustomPiOS source
echo ""
echo "Building cross-compilation Docker image..."
docker build --tag custompios_builder "$CUSTOMPIOS_DIR/src"

echo ""
echo "Building image (this may take 30-60 minutes)..."
echo ""

pushd "$CUSTOMPIOS_DIR/src" > /dev/null

# Copy our module into the CustomPiOS workspace (not symlink — Docker needs real files)
rm -rf modules/rigsherpa
cp -r "$SCRIPT_DIR/modules/rigsherpa" modules/rigsherpa

# Create the distribution config (separate from the framework config in the Docker image)
cat > config <<BUILDCFG
export MODULES="base(rigsherpa)"
export BASE_ARCH="arm64"
export BASE_BOARD="raspberrypiarm64"
export BASE_IMAGE_ENLARGEROOT=12000
BUILDCFG

# Run the build inside a privileged Docker container (no sudo needed)
# /distro = our distribution (config, modules, workspace output)
# /CustomPiOS = the framework (preserved in the Docker image with original config)
docker run --rm --privileged \
    -v "$(pwd):/distro" \
    -e DIST_PATH=/distro \
    -e CUSTOM_PI_OS_PATH=/CustomPiOS \
    -e BASE_BOARD=raspberrypiarm64 \
    -e LOG=no \
    -e VEHICLE_TYPE="$VEHICLE_TYPE" \
    -e VEHICLE_NAME="$VEHICLE_NAME" \
    -e RIGSHERPA_VERSION="$RIGSHERPA_VERSION" \
    -e OLLAMA_MODEL="${OLLAMA_MODEL:-}" \
    -e OLLAMA_FALLBACK_MODEL="${OLLAMA_FALLBACK_MODEL:-}" \
    -e PULL_FALLBACK="${PULL_FALLBACK:-}" \
    -e EMBEDDING_MODEL="${EMBEDDING_MODEL:-}" \
    -e WIFI_CONNECT_VERSION="${WIFI_CONNECT_VERSION:-}" \
    custompios_builder \
    bash -c '
        set -ex
        export BASE_IMAGE_PATH=${DIST_PATH}/image-${BASE_BOARD}
        mkdir -p "${BASE_IMAGE_PATH}"
        ${CUSTOM_PI_OS_PATH}/custompios_core/base_image_downloader.py
        bash -x ${CUSTOM_PI_OS_PATH}/build_custom_os
        chmod -R a+rX ${DIST_PATH}/workspace/
    '

popd > /dev/null

# ── collect output ───────────────────────────
TIMESTAMP="$(date +%Y%m%d)"
OUTPUT_NAME="rigsherpa-${VEHICLE_TYPE}-${RIGSHERPA_VERSION}-${TIMESTAMP}"

# CustomPiOS places images in src/workspace/
BUILT_IMAGE=$(find "$CUSTOMPIOS_DIR/src/workspace/" -name '*.img' -type f 2>/dev/null | head -1)
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
