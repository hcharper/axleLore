#!/usr/bin/env bash
# build_pack.sh — Build a distributable knowledge pack for a vehicle.
#
# Usage:
#   ./build_pack.sh <vehicle_type> [version]
#   ./build_pack.sh fzj80 1.0.0
#
# Prerequisites:
#   - ChromaDB must already be populated via the ingestion pipeline
#     (scrapers → chunker → builder.add_chunks)
#   - The project venv must have sentence-transformers installed
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

VEHICLE_TYPE="${1:?Usage: $0 <vehicle_type> [version]}"
VERSION="${2:-1.0.0}"

CHROMADB_DIR="${ROOT_DIR}/data/chromadb"
OUTPUT_DIR="${ROOT_DIR}/data/knowledge_packs/${VEHICLE_TYPE}"
OUTPUT_FILE="${OUTPUT_DIR}/${VEHICLE_TYPE}-knowledge-pack-v${VERSION}.tar.gz"

# Activate venv
if [[ -f "${ROOT_DIR}/.venv/bin/activate" ]]; then
    source "${ROOT_DIR}/.venv/bin/activate"
fi

export PYTHONPATH="${ROOT_DIR}/src:${ROOT_DIR}"

echo "=========================================="
echo "  Knowledge Pack Builder"
echo "  Vehicle: ${VEHICLE_TYPE}"
echo "  Version: ${VERSION}"
echo "=========================================="

# Check that there's data
if [[ ! -d "$CHROMADB_DIR" ]]; then
    echo "Error: ChromaDB directory not found at $CHROMADB_DIR"
    echo "  Run the ingestion pipeline first."
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo ""
echo "Exporting knowledge pack..."
python3 -c "
import sys
from pathlib import Path
from tools.kb_builder.builder import KnowledgeBaseBuilder

builder = KnowledgeBaseBuilder(Path('${CHROMADB_DIR}'))

stats = builder.get_stats('${VEHICLE_TYPE}')
print(f'  Collections: {len(stats[\"collections\"])}')
print(f'  Total chunks: {stats[\"total_chunks\"]}')

if stats['total_chunks'] == 0:
    print()
    print('WARNING: No chunks found. The pack will be empty.')
    print('  Run the ingestion pipeline first to populate ChromaDB.')
    print()

builder.export('${VEHICLE_TYPE}', Path('${OUTPUT_FILE}'), version='${VERSION}')
"

echo ""
echo "Knowledge pack exported:"
echo "  ${OUTPUT_FILE}"
echo "  Size: $(du -h "$OUTPUT_FILE" | cut -f1)"

# Also copy the manifest out for easy inspection
MANIFEST="${OUTPUT_DIR}/manifest.json"
tar xzf "$OUTPUT_FILE" --include="*/manifest.json" -O > "$MANIFEST" 2>/dev/null || true
if [[ -s "$MANIFEST" ]]; then
    echo ""
    echo "Manifest:"
    cat "$MANIFEST"
fi

# Copy chromadb data for the image build
echo ""
echo "Extracting chromadb data for image builder..."
rm -rf "${OUTPUT_DIR}/chromadb"
tar xzf "$OUTPUT_FILE" -C "$OUTPUT_DIR"
# The tarball extracts as <vehicle_type>/chromadb/ and <vehicle_type>/manifest.json
if [[ -d "${OUTPUT_DIR}/${VEHICLE_TYPE}/chromadb" ]]; then
    mv "${OUTPUT_DIR}/${VEHICLE_TYPE}/chromadb" "${OUTPUT_DIR}/chromadb"
    mv "${OUTPUT_DIR}/${VEHICLE_TYPE}/manifest.json" "${OUTPUT_DIR}/manifest.json" 2>/dev/null || true
    rm -rf "${OUTPUT_DIR}/${VEHICLE_TYPE}"
fi

echo ""
echo "Ready for image build:"
echo "  ChromaDB: ${OUTPUT_DIR}/chromadb/"
echo "  Manifest: ${OUTPUT_DIR}/manifest.json"
echo ""
echo "Next: cd build && ./build-image.sh ${VEHICLE_TYPE}"
