#!/usr/bin/env bash
#
# Build and verify .venv_cowork, the CoWork image mirror.
#
# Python 3.10 plus docs/data/requirements_installable.txt: the interpreter and the
# wheels a CoWork session provides, minus the nine pins that cannot install off the
# VM. Code that must behave like a session runs here, never under the repo .venv.
#
# It reproduces the interpreter and the wheels only. Ubuntu 22.04, aarch64,
# LibreOffice, ImageMagick, pandoc and tesseract are not reproduced, so rendering
# and OCR behaviour still diverges from a session. See docs/environments.md.
#
#   (no args)     create if absent, sync, exit 0 when already correct
#   --recreate    delete and rebuild from scratch
#   --check       verify only, no writes, non-zero exit on drift
#
# Shell, not Python: it runs before and independently of the repo environment.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
need uv

PY="$COWORK/bin/python"
REQUIREMENTS="$ROOT/docs/data/requirements_installable.txt"
PYTHON_VERSION="3.10"

# Not on the CoWork image. Installed so pytest can collect and run tests under the
# mirror. Code under test must not import one of these: it would pass here and fail
# in a session.
TEST_ONLY_DIRECT=(pytest pytest-timeout)
TEST_ONLY_ALL="pytest pytest-timeout pluggy iniconfig exceptiongroup tomli"

MODE="sync"
case "${1-}" in
  "") ;;
  --recreate) MODE="recreate" ;;
  --check) MODE="check" ;;
  -h | --help) usage ;;
  *) die "unknown argument '$1' (expected --recreate, --check or none)" ;;
esac

# Lower-case the distribution name and fold _ and . to -, per PEP 503. Versions are
# left alone. Lines without a == pin are dropped.
normalize_pins() {
  awk -F'==' 'NF == 2 { name = tolower($1); gsub(/[_.]/, "-", name); print name "==" $2 }'
}

fail() {
  echo "FAIL: $*" >&2
  DRIFT=1
}

verify() {
  DRIFT=0

  if [ ! -x "$PY" ]; then
    fail "$COWORK does not exist. Run scripts/cowork_venv.sh."
    return 1
  fi

  local actual_version
  actual_version="$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
  if [ "$actual_version" != "$PYTHON_VERSION" ]; then
    fail "interpreter is $actual_version, expected $PYTHON_VERSION"
  fi

  local expected actual missing extra absent
  expected="$(normalize_pins < "$REQUIREMENTS" | sort -u)"
  actual="$(uv pip freeze --python "$PY" | normalize_pins | sort -u)"

  missing="$(comm -23 <(echo "$expected") <(echo "$actual"))"
  if [ -n "$missing" ]; then
    fail "$(echo "$missing" | wc -l | tr -d ' ') pins missing or at the wrong version:"
    echo "$missing" | sed 's/^/  /' >&2
  fi

  # An extra is anything installed that is neither a pin nor a test-only package, at
  # any version.
  extra="$(
    comm -13 <(echo "$expected") <(echo "$actual") \
      | cut -d= -f1 \
      | grep -vxF -e "${TEST_ONLY_ALL// /$'\n'}" || true
  )"
  if [ -n "$extra" ]; then
    fail "$(echo "$extra" | wc -l | tr -d ' ') packages installed that are on neither list:"
    echo "$extra" | sed 's/^/  /' >&2
  fi

  # Without this a package added to TEST_ONLY_DIRECT is never installed: it is not a
  # pin, so it cannot be missing, and it is on TEST_ONLY_ALL, so it is not an extra.
  absent="$(
    printf '%s\n' "${TEST_ONLY_DIRECT[@]}" \
      | grep -vxF -e "$(echo "$actual" | cut -d= -f1)" || true
  )"
  if [ -n "$absent" ]; then
    fail "$(echo "$absent" | wc -l | tr -d ' ') test-only packages not installed:"
    echo "$absent" | sed 's/^/  /' >&2
  fi

  [ "$DRIFT" -eq 0 ]
}

build() {
  if [ "$MODE" = "recreate" ]; then
    rm -rf "$COWORK"
  fi
  # --no-project: the venv is standalone, so the root requires-python == 3.14 does
  # not apply to it.
  uv venv --no-project --allow-existing --python "$PYTHON_VERSION" "$COWORK"
  uv pip sync --python "$PY" "$REQUIREMENTS"
  uv pip install --python "$PY" "${TEST_ONLY_DIRECT[@]}"
}

case "$MODE" in
  check)
    if verify; then
      echo "OK: .venv_cowork matches Python $PYTHON_VERSION + $(grep -c '==' "$REQUIREMENTS") pins"
      exit 0
    fi
    exit 1
    ;;
  sync)
    if verify 2> /dev/null; then
      echo "OK: .venv_cowork already correct"
      exit 0
    fi
    build
    ;;
  recreate)
    build
    ;;
esac

verify
echo "OK: .venv_cowork matches Python $PYTHON_VERSION + $(grep -c '==' "$REQUIREMENTS") pins"
