# shellcheck shell=bash
#
# Shared by every script in this directory. Source it, do not execute it.
#
#   . "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
#
# Sets ROOT to the repository root and VENV / COWORK to the two environments.
# See docs/environments.md.

ROOT="$(cd "$(dirname "${BASH_SOURCE[1]}")/.." && pwd)"
# Read by the scripts that source this file, not here.
# shellcheck disable=SC2034
VENV="$ROOT/.venv"
# shellcheck disable=SC2034
COWORK="$ROOT/.venv_cowork"

die() {
  echo "${0##*/}: $*" >&2
  exit 1
}

need() {
  command -v "$1" > /dev/null 2>&1 || die "$1 is not on PATH"
}

# Print the header comment block of the calling script as its help text.
usage() {
  awk 'NR > 2 { if (/^#/) { sub(/^# ?/, ""); print } else { exit } }' "${BASH_SOURCE[1]}"
  exit 0
}
