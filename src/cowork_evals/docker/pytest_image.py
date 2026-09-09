"""The image pytest runs in: the digest, the build and the check.

The design is [docs/cowork_test.md](../../../docs/cowork_test.md). It is one layer over
the eval image, and `Dockerfile.pytest` beside this file is that layer.

One module per image. [`__init__.py`](__init__.py) owns the image the harness runs in and
this owns the image pytest runs in, and each owns its Dockerfile, its digest, its argument
lists and its check. The command that fixes an absent image is therefore written here for
this image and there for that one.

A `PytestImage` holds frozen configuration and does no work at construction, so
`PytestImage().digest` answers on a machine with no daemon. That is `Docker`'s rule and it
holds here.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from ..config import Config
from . import DATA, DIGEST_LENGTH, Condition, Docker, DockerError, remedy

DOCKERFILE = Path(__file__).parent / "Dockerfile.pytest"
REQUIREMENTS_TEST = DATA / "requirements_test.txt"

# The image tag prefix. There is no `latest`, for the reason in docs/docker.md.
REPOSITORY = "cowork-evals-test"

# The one command that builds this image, as `remedy` in `__init__.py` is the one command
# that builds the base. It names a development script, because `cowork_evals setup
# --docker` is not built. docs/cli.md holds the command that replaces it.
BUILD_REMEDY = "run scripts/cowork_pytest.sh"


def digest_of(*parts: bytes) -> str:
    """Every build input, hashed in order and truncated. `digest` is the one caller.

    Separate from it so a test can vary an input that is a file on disk rather than a
    configuration key, without a patch and without a second implementation of the hash.
    """
    sha = hashlib.sha256()
    for part in parts:
        sha.update(part)
        sha.update(b"\0")
    return sha.hexdigest()[:DIGEST_LENGTH]


class PytestImage:
    """One resolved test image configuration, over one resolved eval image."""

    def __init__(self, config: Config | None = None) -> None:
        """Every setting resolved once, through the `Docker` this image is built over.

        `config` defaults to `cowork_evals.yaml` in the working directory. There is no
        `pytest:` section: this image takes its platform and its base from `docker:`.
        """
        self._config = config if config is not None else Config.load()
        self.docker = Docker(self._config)
        self.platform = self.docker.platform

    # The build arguments, the digest, and the tag over it.

    @property
    def build_args(self) -> dict[str, str]:
        """The one `ARG` the Dockerfile declares, and the only source of its value."""
        return {"BASE_TAG": self.docker.tag}

    @property
    def digest(self) -> str:
        """Every build input, hashed, the base image's digest first.

        A rebuilt base is therefore a different test tag, never a stale hit over an old
        base. The platform is already inside the base digest and is hashed again here, so
        this list is every input on its own terms.
        """
        return digest_of(
            self.docker.digest.encode(),
            DOCKERFILE.read_bytes(),
            REQUIREMENTS_TEST.read_bytes(),
            self.platform.encode(),
        )

    @property
    def tag(self) -> str:
        return f"{REPOSITORY}:{self.digest}"

    # The argument list.

    def build_argv(self, *, no_cache: bool = False) -> list[str]:
        """The build. The context is the package data directory, as the eval image's is.

        No build secret: the base image already carries the extra root CA when the host
        that built it supplied one, and this layer reaches PyPI alone.
        """
        argv = [
            "docker",
            "build",
            "--platform",
            self.platform,
            "-f",
            str(DOCKERFILE),
        ]
        for name, value in self.build_args.items():
            argv += ["--build-arg", f"{name}={value}"]
        argv += ["-t", self.tag]
        if no_cache:
            argv.append("--no-cache")
        argv.append(str(DATA))
        return argv

    # Doing the work.

    def build(self, *, no_cache: bool = False) -> None:
        """Build the image, streaming the output. A non-zero exit raises.

        An absent base image is a failure naming it, never an implicit base build: that
        build takes minutes and belongs to whoever asked for it.
        """
        if not self.docker.image_is_present():
            raise DockerError(f"base image {self.docker.tag} is absent: {remedy(Condition.IMAGE)}")
        completed = subprocess.run(self.build_argv(no_cache=no_cache))
        if completed.returncode != 0:
            raise DockerError(f"docker build failed with exit {completed.returncode}: {self.tag}")

    def image_is_present(self) -> bool:
        completed = subprocess.run(
            ["docker", "image", "inspect", self.tag],
            capture_output=True,
            text=True,
        )
        return completed.returncode == 0

    def check(self) -> list[tuple[Condition, str]]:
        """The unmet conditions, in order, each with the command that fixes it.

        An empty list means ready. It writes nothing and builds nothing.
        `Condition.CREDENTIAL` is never returned: there is no login in this path.
        """
        unmet: list[tuple[Condition, str]] = []
        if not self.docker.daemon_is_reachable():
            unmet.append(
                (Condition.DAEMON, f"docker daemon is not reachable: {remedy(Condition.DAEMON)}")
            )
        # Neither image is readable without a daemon. The base is reported before the
        # layer over it, because building the layer needs it.
        elif not self.docker.image_is_present():
            unmet.append(
                (
                    Condition.IMAGE,
                    f"base image {self.docker.tag} is absent: {remedy(Condition.IMAGE)}",
                )
            )
        elif not self.image_is_present():
            unmet.append((Condition.IMAGE, f"image {self.tag} is absent: {BUILD_REMEDY}"))
        return unmet
