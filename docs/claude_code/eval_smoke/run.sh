#!/usr/bin/env bash
# Run the demo eval suite in this directory.
#   ./run.sh                       all cases
#   ./run.sh --case "capital-*"    one case or a glob
set -euo pipefail

export CLAUDE_CODE_WALNUT_SPIRE=1 # plugin eval is early access

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec claude plugin eval "$HERE" \
  --model sonnet \
  --judge-model haiku \
  --ablation none \
  --max-cost-usd 3 \
  --no-publish \
  --no-scaffold \
  "$@"
