"""The container backend: the digest, the argument lists, the build and the check.

The design is [docs/docker.md](../../../docs/docker.md). A `Docker` holds frozen
configuration and does no work at construction, so `Docker().digest` answers on a machine
with no daemon.

Docker is driven through its CLI with `subprocess`, not through `docker-py`, for the
reason in that page. Nothing here names a run directory, writes a symlink, prunes or
decides pass and fail: that is the CLI's, in `plan_cli.md`.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from enum import StrEnum
from pathlib import Path

from ..config import Config
from ..harness import ENABLEMENT_ENV, RunOptions, eval_argv

DOCKERFILE = Path(__file__).parent / "Dockerfile"
DATA = Path(__file__).parent.parent / "data"
REQUIREMENTS = DATA / "requirements.txt"
INSTALLABLE = DATA / "requirements_installable.txt"

# The image tag prefix. There is no `latest`: nothing reads one. docs/docker.md.
REPOSITORY = "cowork-evals"
DIGEST_LENGTH = 12

# The configuration directory this package owns holds these two, and never the developer's
# own ~/.claude. Its path is `docker.login_dir`. docs/docker.md.
CLAUDE_DIR_NAME = ".claude"
STATE_FILE_NAME = ".claude.json"
CREDENTIALS_FILE_NAME = ".credentials.json"

# What makes a directory a plugin root. docs/eval_format.md.
PLUGIN_MANIFEST = Path(".claude-plugin") / "plugin.json"

# Inside the container. The uid the run carries has no passwd entry, so HOME is explicit.
# The Dockerfile creates all four and writes none of them: it takes them as build arguments
# from `build_args`, which is also what the digest hashes.
CONTAINER_HOME = "/tmp/eval-home"
CONTAINER_WORK = "/work"
CONTAINER_PLUGIN = f"{CONTAINER_WORK}/plugin"
CONTAINER_LOGS = f"{CONTAINER_WORK}/logs"

# What the harness leaves behind, and the only thing a backend returns. docs/running_evals.md.
RESULT_NAME = "aggregate-result.json"

# An optional extra root CA, for a host whose network inspects TLS. The host path is
# `docker.extra_ca_file`, and the certificate itself never enters this repository. The
# Dockerfile installs it under this path. docs/docker.md.
#
# The secret id is the one string the Dockerfile still writes for itself. It is not a
# build argument, so `tests/unit/test_docker.py` reads the Dockerfile and asserts the two
# are the same string.
EXTRA_CA_SECRET = "extra_ca"
CONTAINER_EXTRA_CA = "/usr/local/share/ca-certificates/extra_ca.crt"


class Condition(StrEnum):
    """What `Docker.check` reports unmet.

    The condition is what a caller selects on, and the message beside it is for a person to
    read. `scripts/image.sh --check` drops `CREDENTIAL`, so rewording a message changes
    nothing any caller matches.
    """

    DAEMON = "daemon"
    IMAGE = "image"
    CREDENTIAL = "credential"


class DockerError(Exception):
    """A container backend failure, carrying a message and nothing else."""


def plugin_root(target: Path | str) -> Path:
    """The nearest directory at or above `target` holding `.claude-plugin/plugin.json`.

    It is what the read-only mount is rooted at, and what the container-side target is
    relative to.
    """
    resolved = Path(target).resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / PLUGIN_MANIFEST).is_file():
            return candidate
    raise DockerError(f"no {PLUGIN_MANIFEST} at or above {resolved}")


class Docker:
    """One resolved container configuration."""

    def __init__(self, config: Config | None = None) -> None:
        """Every setting resolved once, so a `Docker` is frozen configuration.

        `config` defaults to `cowork_evals.yaml` in the working directory. A configured
        `extra_ca_file` that is not on disk is a host that does not intercept TLS.
        """
        self._config = config if config is not None else Config.load()
        settings = self._config.docker
        self.platform = settings.platform
        self.claude_code_version = settings.claude_code_version
        self.login_dir = settings.login_dir
        self.extra_ca_file: Path | None = (
            settings.extra_ca_file
            if settings.extra_ca_file is not None and settings.extra_ca_file.is_file()
            else None
        )

    # The login this package owns. Both paths are mounted read-write, because the CLI
    # refreshes its token and rewrites its state file on every start.

    @property
    def claude_dir(self) -> Path:
        return self.login_dir / CLAUDE_DIR_NAME

    @property
    def state_file(self) -> Path:
        return self.login_dir / STATE_FILE_NAME

    @property
    def credentials_file(self) -> Path:
        return self.claude_dir / CREDENTIALS_FILE_NAME

    # The build arguments, the digest, and the tag over it.

    @property
    def build_args(self) -> dict[str, str]:
        """Every `ARG` the Dockerfile declares, and the only source of each value.

        The container paths are here rather than in the Dockerfile so that the Python
        constant and the path the image creates cannot differ. The digest hashes this
        mapping, so changing one is a different tag rather than a hit on an image built at
        the old path.
        """
        return {
            "CLAUDE_CODE_VERSION": self.claude_code_version,
            "CONTAINER_HOME": CONTAINER_HOME,
            "CONTAINER_WORK": CONTAINER_WORK,
            "CONTAINER_PLUGIN": CONTAINER_PLUGIN,
            "CONTAINER_LOGS": CONTAINER_LOGS,
            "CONTAINER_EXTRA_CA": CONTAINER_EXTRA_CA,
        }

    @property
    def digest(self) -> str:
        """Every build input, hashed. A changed input is a different tag, never a stale hit."""
        sha = hashlib.sha256()
        for path in (DOCKERFILE, REQUIREMENTS, INSTALLABLE):
            sha.update(path.read_bytes())
            sha.update(b"\0")
        for name, value in self.build_args.items():
            sha.update(f"{name}={value}".encode())
            sha.update(b"\0")
        sha.update(self.platform.encode())
        return sha.hexdigest()[:DIGEST_LENGTH]

    @property
    def tag(self) -> str:
        return f"{REPOSITORY}:{self.digest}"

    # The argument lists.

    def build_argv(self, *, no_cache: bool = False) -> list[str]:
        """The build. The context is the package data directory, two files and nothing else."""
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
        if self.extra_ca_file is not None:
            argv += ["--secret", f"id={EXTRA_CA_SECRET},src={self.extra_ca_file}"]
        if no_cache:
            argv.append("--no-cache")
        argv.append(str(DATA))
        return argv

    def login_argv(self) -> list[str]:
        """The interactive container a developer logs in through once.

        The same two credential mounts as a run, and no plugin and no log mount. The
        caller creates both host paths first: Docker would otherwise create a root-owned
        directory in place of the missing state file.

        `auth login` rather than bare `claude`, which lands in the first-run configuration
        wizard on a fresh configuration directory. This container exists to produce a
        credentials file, and nothing here picks a theme.
        """
        return [
            "docker",
            "run",
            "--rm",
            "-it",
            "--platform",
            self.platform,
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--env",
            f"HOME={CONTAINER_HOME}",
            *self.extra_ca_env_argv(),
            *self.credential_argv(),
            self.tag,
            "claude",
            "auth",
            "login",
            "--claudeai",
        ]

    def run_preamble(self) -> list[str]:
        """One run's container, up to the mounts, the tag and the command.

        The one place the run's platform, uid, home, enablement variable, sandbox options
        and credential mounts are written. `run_argv` adds the two mounts and the harness;
        tests/integration/test_docker.py adds its own mounts and a fixed command, so what
        that tier proves about the sandbox it proves about this list.
        """
        return [
            "docker",
            "run",
            "--rm",
            "--platform",
            self.platform,
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--env",
            f"HOME={CONTAINER_HOME}",
            # The process in the container is the harness itself, with no wrapper to
            # export the enablement variable. docs/plugin_eval.md.
            "--env",
            ENABLEMENT_ENV,
            # Granting Bash turns on the OS sandbox, and bubblewrap needs two things the
            # default container profile denies: unprivileged user namespaces unfiltered,
            # and a /proc it can mount over. docs/docker.md.
            "--security-opt",
            "seccomp=unconfined",
            "--security-opt",
            "systempaths=unconfined",
            *self.extra_ca_env_argv(),
            *self.credential_argv(),
        ]

    def run_argv(
        self, target: Path | str, output_dir: Path | str, options: RunOptions
    ) -> list[str]:
        """One run, as a container. The harness command line is harness.eval_argv.

        The plugin root goes in read-only and the run's log directory read-write. Nothing
        else from the host is mounted, and the harness writes its output into the log
        mount rather than under the plugin. docs/docker.md.
        """
        root = plugin_root(target)
        relative = Path(target).resolve().relative_to(root)
        container_target = CONTAINER_PLUGIN
        if relative != Path("."):
            container_target = f"{CONTAINER_PLUGIN}/{relative.as_posix()}"
        return [
            *self.run_preamble(),
            "-v",
            f"{root}:{CONTAINER_PLUGIN}:ro",
            "-v",
            f"{Path(output_dir).resolve()}:{CONTAINER_LOGS}:rw",
            self.tag,
            *eval_argv(container_target, CONTAINER_LOGS, options),
        ]

    def credential_argv(self) -> list[str]:
        """The one credential route: the login this package owns, mounted. docs/docker.md.

        Read-write, because the CLI refreshes its token and rewrites its state file on
        every start.
        """
        return [
            "-v",
            f"{self.claude_dir}:{CONTAINER_HOME}/{CLAUDE_DIR_NAME}:rw",
            "-v",
            f"{self.state_file}:{CONTAINER_HOME}/{STATE_FILE_NAME}:rw",
        ]

    def extra_ca_env_argv(self) -> list[str]:
        """Node carries its own root store and does not read the system one.

        The image already trusts the extra CA; this is what makes the CLI inside it trust
        the same one, on the host whose build supplied it.
        """
        if self.extra_ca_file is None:
            return []
        return ["--env", f"NODE_EXTRA_CA_CERTS={CONTAINER_EXTRA_CA}"]

    # Doing the work.

    def build(self, *, no_cache: bool = False) -> None:
        """Build the image, streaming the output. A non-zero exit raises."""
        argv = self.build_argv(no_cache=no_cache)
        completed = subprocess.run(argv)
        if completed.returncode != 0:
            raise DockerError(f"docker build failed with exit {completed.returncode}: {self.tag}")

    def login(self) -> None:
        """Run the interactive login, once. A non-zero exit raises.

        The terminal is inherited, so the CLI opens the browser and takes the code in its
        own prompt. Whoever calls this owns a terminal: there is no headless login.
        """
        self.seed_login_dir()
        completed = subprocess.run(self.login_argv())
        if completed.returncode != 0:
            raise DockerError(f"the login exited {completed.returncode}")
        if not self.has_credential():
            raise DockerError(f"the login wrote no {self.credentials_file.name}")

    def seed_login_dir(self) -> None:
        """Create the two login paths, with a state file the CLI will accept.

        An empty `.claude.json` is not an absent one: the CLI reads it, fails to parse it,
        and exits 1 with `JSON Parse error: Unexpected EOF`. Measured 2026-09-08.
        """
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        if not self.state_file.is_file() or self.state_file.stat().st_size == 0:
            self.state_file.write_text("{}")

    def run(
        self,
        target: Path | str,
        output_dir: Path | str,
        options: RunOptions | None = None,
    ) -> Path:
        """Run one container and return the result document it left behind.

        The caller creates `output_dir` first, and owns naming it. A non-zero exit is not
        itself a failure: the harness exits 1 below threshold and 2 on partial results,
        and the gate reads the document either way. No document at all is.
        """
        options = options if options is not None else RunOptions.resolve(self._config)
        output_dir = Path(output_dir).resolve()
        completed = subprocess.run(self.run_argv(target, output_dir, options))
        result = output_dir / RESULT_NAME
        if not result.is_file():
            raise DockerError(
                f"the container left no {RESULT_NAME} in {output_dir}, "
                f"and exited {completed.returncode}"
            )
        return result

    def daemon_is_reachable(self) -> bool:
        try:
            completed = subprocess.run(
                ["docker", "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                text=True,
            )
        except OSError:
            return False
        return completed.returncode == 0

    def image_is_present(self) -> bool:
        completed = subprocess.run(
            ["docker", "image", "inspect", self.tag],
            capture_output=True,
            text=True,
        )
        return completed.returncode == 0

    def has_credential(self) -> bool:
        return self.credentials_file.is_file()

    def check(self) -> list[tuple[Condition, str]]:
        """The unmet conditions, in order, each with the command that fixes it.

        An empty list means ready. It writes nothing and builds nothing.
        """
        unmet: list[tuple[Condition, str]] = []
        if not self.daemon_is_reachable():
            unmet.append(
                (
                    Condition.DAEMON,
                    "docker daemon is not reachable: start Docker Desktop or Rancher Desktop",
                )
            )
        # The image is unreadable without a daemon, so a second line about it would name a
        # condition this run cannot know. The credential is on the host and is read either way.
        elif not self.image_is_present():
            unmet.append(
                (Condition.IMAGE, f"image {self.tag} is absent: run `cowork_evals setup --docker`")
            )
        if not self.has_credential():
            unmet.append(
                (Condition.CREDENTIAL, "no credential: run `cowork_evals setup --docker` to log in")
            )
        return unmet
