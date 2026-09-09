#!/usr/bin/env bash
#
# Lint Python and shell.
#
#   (no args)  check only, non-zero exit on any finding
#   --fix      apply every fix in place
#
# Runs ruff (lint and format) over Python, and shellcheck plus shfmt over every
# *.sh in the repository outside a dot directory, when they are on PATH.
# tests/unit/test_environments.py selects by the same rule. Markdown is not
# formatted by a tool: see the writing rules in CLAUDE.md.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
need uv

FIX=0
case "${1-}" in
  "") ;;
  --fix) FIX=1 ;;
  -h | --help) usage ;;
  *) die "unknown argument '$1' (expected --fix or none)" ;;
esac

cd "$ROOT"

SHELL_FILES=()
while IFS= read -r file; do
  SHELL_FILES+=("$file")
done < <(find . -name '*.sh' -not -path './.*' | sort)

if [ "$FIX" -eq 1 ]; then
  uv run ruff check --fix .
  uv run ruff format .
  command -v shfmt > /dev/null 2>&1 && shfmt -w -i 2 -ci -sr -bn "${SHELL_FILES[@]}"
else
  uv run ruff check .
  uv run ruff format --check .
  command -v shfmt > /dev/null 2>&1 && shfmt -d -i 2 -ci -sr -bn "${SHELL_FILES[@]}"
fi
command -v shellcheck > /dev/null 2>&1 && shellcheck -x -P scripts "${SHELL_FILES[@]}"

echo "OK: lint clean"
