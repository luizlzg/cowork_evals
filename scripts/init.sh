#!/usr/bin/env bash
#
# Build both environments: .venv and .venv_cowork.
#
# Run once after cloning. Pass any argument through to both builders, so
# `init.sh --recreate` rebuilds both from scratch. See docs/environments.md.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

case "${1-}" in
  -h | --help) usage ;;
esac

"$ROOT/scripts/venv.sh" "$@"
"$ROOT/scripts/cowork_venv.sh" "$@"
