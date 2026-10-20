#!/usr/bin/env bash
set -u
echo "--- latest release assets ---"
curl -s --max-time 30 "https://api.github.com/repos/infinilabs/analysis-ik/releases/latest" \
  | grep -E '"tag_name"|browser_download_url' | head -20

echo "--- repo search ---"
curl -s --max-time 30 "https://api.github.com/search/repositories?q=opensearch+analysis+ik&per_page=5" \
  | grep -E '"full_name"' | head -5
