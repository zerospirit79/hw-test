#!/usr/bin/env bash
set -euo pipefail
./scripts/pc-test --help >/dev/null
./scripts/pc-test diag --json >/dev/null
./scripts/pc-test collect --out ./.tmp-logs --json >/dev/null
rm -rf ./.tmp-logs ./.tmp-logs.tar.gz
echo "SMOKE: OK"
