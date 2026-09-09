#!/usr/bin/env bash
#
# Build .venv, the repository tooling environment.
#
# Run once after cloning. Pass any argument through, so `init.sh --recreate` rebuilds it
# from scratch.
#
# It does not build .venv_cowork. That mirror is 604 MB, nothing in the package reads it,
# and only `cowork_run.sh` uses it. Build it with `cowork_venv.sh` when you need it. See
# docs/environments.md.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

case "${1-}" in
  -h | --help) usage ;;
esac

"$ROOT/scripts/venv.sh" "$@"
