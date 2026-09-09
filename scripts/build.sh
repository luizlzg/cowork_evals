#!/usr/bin/env bash
#
# Build the distribution, and prove the built wheel is complete.
#
#   (no args)  build sdist and wheel into dist/, then verify both
#
# The wheel carries files that are not Python: the two Dockerfiles and the three
# requirements files, which the package reads at run time from beside its own modules. A
# packaging change that drops one of them breaks `setup --docker` on a machine with no
# checkout, and nothing else here catches it. The verification below installs the wheel
# into a throwaway environment and runs the command out of it.
#
# Publishing to an index is a separate act and is not done here. See docs/library.md.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
need uv

case "${1-}" in
  "") ;;
  -h | --help) usage ;;
  *) die "unknown argument '$1' (expected none)" ;;
esac

cd "$ROOT"
rm -rf dist
uv build --out-dir dist

WHEEL="$(echo dist/*.whl)"
SDIST="$(echo dist/*.tar.gz)"
[ -f "$WHEEL" ] || die "no wheel in dist/"
[ -f "$SDIST" ] || die "no sdist in dist/"

# Each listing is read once. `grep -q` closes the pipe on its first hit, and under
# `pipefail` that reports the producer as failed.
WHEEL_FILES="$(unzip -Z1 "$WHEEL")"
SDIST_FILES="$(tar tzf "$SDIST")"

# What ships beside the modules. docs/library.md holds the table.
for member in \
  cowork_evals/data/requirements.txt \
  cowork_evals/data/requirements_installable.txt \
  cowork_evals/data/requirements_test.txt \
  cowork_evals/docker/Dockerfile \
  cowork_evals/docker/Dockerfile.pytest; do
  grep -qx "$member" <<< "$WHEEL_FILES" || die "$member is missing from the wheel"
done

# No development directory ships. The sdist include list in pyproject.toml is the rule.
for directory in scripts docs tests plans plugins; do
  if grep -q "/$directory/" <<< "$SDIST_FILES"; then
    die "$directory/ is in the sdist"
  fi
done

BUILD_VENV="$(mktemp -d)"
trap 'rm -rf "$BUILD_VENV"' EXIT
uv venv --python 3.14 "$BUILD_VENV/venv" > /dev/null
VIRTUAL_ENV="$BUILD_VENV/venv" uv pip install --quiet "$WHEEL"
"$BUILD_VENV/venv/bin/cowork_evals" --version

echo "OK: $WHEEL and $SDIST"
