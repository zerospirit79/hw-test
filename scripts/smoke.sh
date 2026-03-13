#!/usr/bin/env bash
set -euo pipefail
./scripts/pc-test --help >/dev/null
./scripts/pc-test diag --json >/dev/null
./scripts/pc-test collect --out ./.tmp-logs --json >/dev/null
./scripts/pc-test smart --json >/dev/null || true
./scripts/pc-test sensors --json >/dev/null || true
rm -rf ./.tmp-logs ./.tmp-logs.tar.gz
echo "SMOKE: OK"
