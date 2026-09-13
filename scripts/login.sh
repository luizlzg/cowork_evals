#!/usr/bin/env bash
#
# Log in to Claude Code once, in a container, for the login this package owns.
#
# The image carries the CLI. This starts one interactive container with the two login
# paths mounted, and the CLI opens a browser and takes the code in its own prompt. It is
# the `login` route, and there is no API key route. A host on `docker.credential: bedrock`
# needs no login and this script has nothing to do there. See docs/docker.md.
#
#   (no args)     log in, or report the login already there
#   --check       report whether a login is present, no writes
#   --force       log in again over a login that is already there
#
# It needs a terminal and a browser. Run it before the integration tier: those tests read
# the credential and never create one.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
need uv
need docker

case "${1-}" in
  "") FORCE="False" ;;
  --force) FORCE="True" ;;
  --check)
    exec uv run --project "$ROOT" python3 -c '
import sys

from cowork_evals.docker import Condition, Docker, remedy

docker = Docker()
if not docker.has_credential():
    print(f"FAIL: no login: {remedy(Condition.CREDENTIAL)}", file=sys.stderr)
    sys.exit(1)
print(f"OK: logged in at {docker.credentials_file}")
'
    ;;
  -h | --help) usage ;;
  *) die "unknown argument '$1' (expected --check, --force or none)" ;;
esac

# The login is an OAuth flow: the CLI opens a browser and reads a code back. Without a
# terminal `docker run -it` refuses, so refuse first and say why.
[ -t 0 ] || die "no terminal: run scripts/login.sh from a shell, not from a pipe or an agent"

exec uv run --project "$ROOT" python3 -c "
import sys

from cowork_evals.docker import Docker, DockerError

docker = Docker()
if docker.has_credential() and not $FORCE:
    print(f'current: logged in at {docker.credentials_file}')
    sys.exit(0)
try:
    docker.login()
except DockerError as error:
    print(f'FAIL: {error}', file=sys.stderr)
    sys.exit(1)
print(f'OK: logged in at {docker.credentials_file}')
"
