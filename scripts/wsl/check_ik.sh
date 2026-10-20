#!/usr/bin/env bash
set -u

for v in 2.11.0 2.19.0 2.20.0 3.0.0; do
  url="https://github.com/infinilabs/analysis-ik/releases/download/v${v}/opensearch-analysis-ik-${v}.zip"
  code=$(curl -sIL --max-time 30 "$url" | grep -E '^HTTP' | tail -1 | tr -d '\r')
  echo "IK ${v}: ${code}"
done

echo "--- recent tags ---"
curl -s --max-time 30 "https://api.github.com/repos/infinilabs/analysis-ik/releases?per_page=8" \
  | grep -E '"tag_name"' | head -8
