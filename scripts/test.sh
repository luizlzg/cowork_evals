#!/usr/bin/env bash
#
# Run the repository test suite under .venv.
#
# Unit tests are the default selection. Integration tests need a real CoWork profile, and
# the live one fires a real CoWork run. Any argument is passed through to pytest.
#
#   test.sh                                  the unit tests
#   test.sh -m integration                   every real-system test, the live run included
#   test.sh -m "integration and not live"    the real-system tests that spend nothing
#   test.sh tests/test_x.py -k name -vv
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
need uv

case "${1-}" in
  -h | --help) usage ;;
esac

exec uv run --project "$ROOT" pytest "$@"
