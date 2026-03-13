#!/usr/bin/env bash
set -euo pipefail
./scripts/hw-test --help >/dev/null
./scripts/hw-test diag --json >/dev/null
./scripts/hw-test collect --out ./.tmp-logs --json >/dev/null
./scripts/hw-test smart --json >/dev/null || true
./scripts/hw-test sensors --json >/dev/null || true
rm -rf ./.tmp-logs ./.tmp-logs.tar.gz
echo "SMOKE: OK"
