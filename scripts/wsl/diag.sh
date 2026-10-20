#!/usr/bin/env bash
set -u
echo "== systemd =="
systemctl is-active docker
systemctl status docker --no-pager -n 15 2>&1 | tail -15

echo "== docker info =="
docker info 2>&1 | head -15

echo "== containers =="
docker ps -a 2>&1
