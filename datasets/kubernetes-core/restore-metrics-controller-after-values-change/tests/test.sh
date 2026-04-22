#!/usr/bin/env bash
set -euo pipefail

mkdir -p /logs/verifier

if /tests/test_controller_service.sh > /logs/verifier/test.log 2>&1; then
  echo "1" > /logs/verifier/reward.txt
else
  echo "0" > /logs/verifier/reward.txt
fi
