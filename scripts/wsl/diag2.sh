#!/usr/bin/env bash
set -u
echo "== ps =="
docker ps -a --format '{{.Names}} | {{.Status}} | {{.Ports}}'
echo "== inspect =="
for c in policy-postgres policy-opensearch; do
  docker inspect -f '{{.Name}} status={{.State.Status}} exit={{.State.ExitCode}} restarts={{.RestartCount}} started={{.State.StartedAt}}' "$c" 2>&1
done
echo "== postgres logs =="
docker logs --tail 20 policy-postgres 2>&1
echo "== opensearch logs =="
docker logs --tail 20 policy-opensearch 2>&1
echo "== uptime =="
uptime
