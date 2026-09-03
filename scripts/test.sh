#!/usr/bin/env bash
#
# Run the repository test suite under .venv.
#
# Any argument is passed through to pytest.
#
#   test.sh
#   test.sh tests/test_x.py -k name -vv
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
need uv

case "${1-}" in
  -h | --help) usage ;;
esac

exec uv run --project "$ROOT" pytest "$@"
