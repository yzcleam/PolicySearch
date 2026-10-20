#!/usr/bin/env bash
set -u

echo "== plugin dir =="
docker exec policy-opensearch sh -c 'ls -la /usr/share/opensearch/plugins/opensearch-analysis-ik'

echo "== plugin config =="
docker exec policy-opensearch sh -c 'ls -la /usr/share/opensearch/plugins/opensearch-analysis-ik/config 2>&1'

echo "== opensearch config/analysis-ik =="
docker exec policy-opensearch sh -c 'ls -la /usr/share/opensearch/config/analysis-ik 2>&1'

echo "== IKAnalyzer.cfg.xml =="
docker exec policy-opensearch sh -c 'cat /usr/share/opensearch/plugins/opensearch-analysis-ik/config/IKAnalyzer.cfg.xml 2>&1'

echo "== ik log lines =="
docker logs policy-opensearch 2>&1 | grep -iE "ik|dictionary|analyzer" | tail -20
