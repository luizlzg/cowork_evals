#!/usr/bin/env bash
#
# Probe the container image and compare it against the CoWork image inventory.
#
# One probe runs inside the container, bind-mounted read-only, and the comparison runs
# on the host. Nothing is installed into the image. What fails and what is only
# printed is the delta table in docs/docker.md.
#
#   (no args)     probe and compare, writing the document to a temporary file
#   <path>        the same, keeping the probe document at <path>
#
# It needs the image built: run scripts/image.sh first.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
need uv
need docker

case "${1-}" in
  -h | --help) usage ;;
esac

read -r TAG PLATFORM PROBE <<< "$(
  uv run --project "$ROOT" python3 -c '
from cowork_evals.docker import Docker, probe

docker = Docker()
print(docker.tag, docker.platform, probe.__file__)
'
)"

OUT="${1-}"
if [ -z "$OUT" ]; then
  OUT="$(mktemp -t cowork_evals_probe)"
  trap 'rm -f "$OUT"' EXIT
fi

docker run --rm \
  --platform "$PLATFORM" \
  -v "$PROBE:/tmp/probe.py:ro" \
  "$TAG" python3 /tmp/probe.py > "$OUT"

uv run --project "$ROOT" python3 -m cowork_evals.docker.parity "$OUT"
