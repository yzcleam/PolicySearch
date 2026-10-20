#!/usr/bin/env bash
# Thin wrapper so Windows callers can run docker without quoting gymnastics.
exec docker "$@"
