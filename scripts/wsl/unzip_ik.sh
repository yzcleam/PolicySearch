#!/usr/bin/env bash
set -euo pipefail
cd /mnt/e/PolicySearcher/deploy/opensearch
rm -rf ik-config
unzip -o -q opensearch-analysis-ik-2.19.3.zip 'config/*' -d ik-config
echo "== files =="
find ik-config -type f | sort
echo "== cfg =="
cat ik-config/config/IKAnalyzer.cfg.xml
