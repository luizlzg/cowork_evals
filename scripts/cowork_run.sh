#!/usr/bin/env bash
#
# Run one command under .venv_cowork, the CoWork mirror.
#
#   cowork_run.sh python3 path/to/x.py
#   cowork_run.sh pytest tests/
#
# It puts the mirror first on PATH and sets VIRTUAL_ENV, so a child process that
# calls bare python3 resolves to 3.10, as it does on the VM.
#
# NEVER run `uv run` through this: uv resolves against the project and will use or
# create the 3.14 .venv, ignoring VIRTUAL_ENV. See docs/environments.md.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

case "${1-}" in
  "" | -h | --help) usage ;;
esac

[ -x "$COWORK/bin/python" ] || die ".venv_cowork does not exist. Run scripts/cowork_venv.sh."
[ "$1" != "uv" ] || die "refusing to run uv under the mirror. See docs/environments.md."

export PATH="$COWORK/bin:$PATH"
export VIRTUAL_ENV="$COWORK"
unset PYTHONHOME
exec "$@"
