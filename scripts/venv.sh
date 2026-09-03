#!/usr/bin/env bash
#
# Build or update .venv, the repository tooling environment.
#
# Python 3.14 plus the dev dependency group in pyproject.toml. Never runs on a
# CoWork VM, so it is unconstrained. See docs/environments.md.
#
#   (no args)   sync .venv from pyproject.toml
#   --recreate  delete and rebuild from scratch
#   --check     verify the lock is current, no writes
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
need uv

case "${1-}" in
  "") uv sync --project "$ROOT" --all-groups ;;
  --recreate)
    rm -rf "$VENV"
    uv sync --project "$ROOT" --all-groups
    ;;
  --check) uv sync --project "$ROOT" --all-groups --locked ;;
  -h | --help) usage ;;
  *) die "unknown argument '$1' (expected --recreate, --check or none)" ;;
esac

echo "OK: .venv at $("$VENV/bin/python" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
