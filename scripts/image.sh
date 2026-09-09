#!/usr/bin/env bash
#
# Build and verify the container image, cowork-evals:<digest>.
#
# It is scripts/cowork_venv.sh for the image: Ubuntu 22.04 with the interpreter, the
# wheels, the document tooling and the fonts a CoWork session provides. The digest
# covers every build input, so a changed input is a different tag. See docs/docker.md.
#
#   (no args)     build the image for docker.platform
#   --check       verify the current digest is present, no writes
#   --recreate    build with --no-cache
#
# Run it before the integration tier: those tests need the image and never build it.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
need uv
need docker

case "${1-}" in
  "") NO_CACHE="False" ;;
  --recreate) NO_CACHE="True" ;;
  --check) NO_CACHE="" ;;
  -h | --help) usage ;;
  *) die "unknown argument '$1' (expected --check, --recreate or none)" ;;
esac

if [ "${1-}" = "--check" ]; then
  # The credential is not a property of the image, so --check does not read it.
  exec uv run --project "$ROOT" python3 -c '
import sys

from cowork_evals.docker import Docker

docker = Docker()
unmet = [line for line in docker.check() if not line.startswith("no credential")]
for line in unmet:
    print(f"FAIL: {line}", file=sys.stderr)
if unmet:
    sys.exit(1)
print(f"OK: {docker.tag} is present")
'
fi

exec uv run --project "$ROOT" python3 -c "
from cowork_evals.docker import Docker

docker = Docker()
print(f'building {docker.tag} for {docker.platform}')
docker.build(no_cache=$NO_CACHE)
print(f'OK: {docker.tag}')
"
