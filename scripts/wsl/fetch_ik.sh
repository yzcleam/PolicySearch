#!/usr/bin/env bash
set -euo pipefail

DEST="/mnt/e/PolicySearcher/deploy/opensearch"
mkdir -p "$DEST"
cd "$DEST"

echo "--- downloading IK 2.19.3 ---"
curl -sSL --max-time 300 -o opensearch-analysis-ik-2.19.3.zip \
  "https://github.com/aparo/opensearch-analysis-ik/releases/download/2.19.3/opensearch-analysis-ik.zip"

ls -lh opensearch-analysis-ik-2.19.3.zip
echo "--- zip contents ---"
unzip -l opensearch-analysis-ik-2.19.3.zip | head -15
echo "--- descriptor ---"
unzip -p opensearch-analysis-ik-2.19.3.zip '*/plugin-descriptor.properties' 2>/dev/null \
  || unzip -p opensearch-analysis-ik-2.19.3.zip 'plugin-descriptor.properties'
