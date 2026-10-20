#!/usr/bin/env bash
set -u

for repo in aparo/opensearch-analysis-ik gaofubao/opensearch-analysis-ik know-no/opensearch-analysis-ik; do
  echo "=== ${repo} ==="
  curl -s --max-time 30 "https://api.github.com/repos/${repo}/releases?per_page=2" \
    | grep -E '"tag_name"|browser_download_url' | head -8
done

echo "=== infinilabs release server ==="
for v in 2.11.0 2.19.0; do
  url="https://release.infinilabs.com/analysis-ik/stable/opensearch-analysis-ik-${v}.zip"
  code=$(curl -sIL --max-time 30 "$url" | grep -E '^HTTP' | tail -1 | tr -d '\r')
  echo "${url} -> ${code}"
done
