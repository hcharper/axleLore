#!/usr/bin/env bash
# upload-release.sh — Upload signed release artefacts to Cloudflare R2.
#
# Usage:
#   ./upload-release.sh <file.img.gz> [file.img.gz.sha256] [file.img.gz.asc]
#
# Environment:
#   R2_BUCKET        — bucket name  (default: axlelore-releases)
#   R2_ENDPOINT_URL  — R2 S3-compat endpoint
#   AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY — R2 credentials
set -euo pipefail

R2_BUCKET="${R2_BUCKET:-axlelore-releases}"
R2_ENDPOINT_URL="${R2_ENDPOINT_URL:?Set R2_ENDPOINT_URL (e.g. https://<account_id>.r2.cloudflarestorage.com)}"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <file> [file.sha256] [file.asc]"
    exit 1
fi

# If only the .img.gz is given, auto-discover .sha256 and .asc siblings
BASE_FILE="$1"
FILES=("$BASE_FILE")
[[ -f "${BASE_FILE}.sha256" ]] && FILES+=("${BASE_FILE}.sha256")
[[ -f "${BASE_FILE}.asc" ]]    && FILES+=("${BASE_FILE}.asc")

# Allow explicit extra args
shift
for extra in "$@"; do
    FILES+=("$extra")
done

echo "Uploading to R2 bucket: ${R2_BUCKET}"
echo ""

for f in "${FILES[@]}"; do
    KEY="$(basename "$f")"
    echo -n "  ${KEY} ($(du -h "$f" | cut -f1))..."
    aws s3 cp "$f" "s3://${R2_BUCKET}/${KEY}" \
        --endpoint-url "$R2_ENDPOINT_URL" \
        --quiet
    echo " done"
done

echo ""
echo "Upload complete.  Files in s3://${R2_BUCKET}/"
echo ""
echo "Generate a presigned download URL (24h expiry):"
echo "  aws s3 presign s3://${R2_BUCKET}/$(basename "$BASE_FILE") \\"
echo "      --endpoint-url ${R2_ENDPOINT_URL} --expires-in 86400"
