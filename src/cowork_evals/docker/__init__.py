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
from pathlib import Path

from ..env import setting
from ..harness import RunOptions, eval_argv

DOCKERFILE = Path(__file__).parent / "Dockerfile"
DATA = Path(__file__).parent.parent / "data"
REQUIREMENTS = DATA / "requirements.txt"
INSTALLABLE = DATA / "requirements_installable.txt"

# The image tag prefix. There is no `latest`: nothing reads one. docs/docker.md.
REPOSITORY = "cowork-evals"
DIGEST_LENGTH = 12

# The configuration directory this package owns, and the CLI state file beside it. Never
# the developer's own ~/.claude. docs/docker.md.
DEFAULT_LOGIN_DIR = Path("~/.cache/cowork_evals/claude")
CLAUDE_DIR_NAME = ".claude"
STATE_FILE_NAME = ".claude.json"
CREDENTIALS_FILE_NAME = ".credentials.json"

# What makes a directory a plugin root. docs/eval_format.md.
PLUGIN_MANIFEST = Path(".claude-plugin") / "plugin.json"

# Inside the container. The uid the run carries has no passwd entry, so HOME is explicit.
CONTAINER_HOME = "/tmp/eval-home"
CONTAINER_PLUGIN = "/work/plugin"
CONTAINER_LOGS = "/work/logs"

# What the harness leaves behind, and the only thing a backend returns. docs/running_evals.md.
RESULT_NAME = "aggregate-result.json"

# An optional extra root CA, for a host whose network inspects TLS. The host path comes
# from SSL_CERT_FILE, which such a host already sets for its own tooling, and never from
# this repository. The Dockerfile installs it under this path. docs/docker.md.
EXTRA_CA_SECRET = "extra_ca"
CONTAINER_EXTRA_CA = "/usr/local/share/ca-certificates/extra_ca.crt"


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

    def __init__(
        self,
        *,
        platform: str | None = None,
        claude_code_version: str | None = None,
        login_dir: Path | str | None = None,
    ) -> None:
        self.platform = platform if platform is not None else setting("EVAL_PLATFORM")
        self.claude_code_version = (
            claude_code_version
            if claude_code_version is not None
            else setting("CLAUDE_CODE_VERSION")
        )
        self.login_dir = (
            Path(login_dir).expanduser() if login_dir else DEFAULT_LOGIN_DIR.expanduser()
        )

    @property
    def extra_ca_file(self) -> Path | None:
        """The host's extra root CA, or None on a network that does not inspect TLS."""
        value = setting("SSL_CERT_FILE")
        if not value:
            return None
        path = Path(value).expanduser()
        return path if path.is_file() else None

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

    # The digest, and the tag over it.

    @property
    def digest(self) -> str:
        """Every build input, hashed. A changed input is a different tag, never a stale hit."""
        sha = hashlib.sha256()
        for path in (DOCKERFILE, REQUIREMENTS, INSTALLABLE):
            sha.update(path.read_bytes())
            sha.update(b"\0")
        sha.update(self.claude_code_version.encode())
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
            "--build-arg",
            f"CLAUDE_CODE_VERSION={self.claude_code_version}",
            "-t",
            self.tag,
        ]
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
            *self._credential_mount_argv(),
            self.tag,
            "claude",
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
            f"CLAUDE_CODE_WALNUT_SPIRE={setting('CLAUDE_CODE_WALNUT_SPIRE')}",
            # Granting Bash turns on the OS sandbox, and bubblewrap needs unprivileged
            # user namespaces unfiltered. docs/docker.md.
            "--security-opt",
            "seccomp=unconfined",
            *self.extra_ca_env_argv(),
            *self.credential_argv(),
            "-v",
            f"{root}:{CONTAINER_PLUGIN}:ro",
            "-v",
            f"{Path(output_dir).resolve()}:{CONTAINER_LOGS}:rw",
            self.tag,
            *eval_argv(container_target, CONTAINER_LOGS, options),
        ]

    def credential_argv(self) -> list[str]:
        """The key wins when both routes are available. docs/docker.md.

        The key is passed by name, never by value: the value reaches the container through
        this process's own environment, so it is in no argument list and in no log.
        """
        if setting("ANTHROPIC_API_KEY"):
            return ["--env", "ANTHROPIC_API_KEY"]
        return self._credential_mount_argv()

    def extra_ca_env_argv(self) -> list[str]:
        """Node carries its own root store and does not read the system one.

        The image already trusts the extra CA; this is what makes the CLI inside it trust
        the same one, on the host whose build supplied it.
        """
        if self.extra_ca_file is None:
            return []
        return ["--env", f"NODE_EXTRA_CA_CERTS={CONTAINER_EXTRA_CA}"]

    def _credential_mount_argv(self) -> list[str]:
        return [
            "-v",
            f"{self.claude_dir}:{CONTAINER_HOME}/{CLAUDE_DIR_NAME}:rw",
            "-v",
            f"{self.state_file}:{CONTAINER_HOME}/{STATE_FILE_NAME}:rw",
        ]

    # Doing the work.

    def build(self, *, no_cache: bool = False) -> None:
        """Build the image, streaming the output. A non-zero exit raises."""
        argv = self.build_argv(no_cache=no_cache)
        completed = subprocess.run(argv)
        if completed.returncode != 0:
            raise DockerError(f"docker build failed with exit {completed.returncode}: {self.tag}")

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
        options = options if options is not None else RunOptions.resolve()
        output_dir = Path(output_dir).resolve()
        completed = subprocess.run(
            self.run_argv(target, output_dir, options),
            env=self.child_environment(),
        )
        result = output_dir / RESULT_NAME
        if not result.is_file():
            raise DockerError(
                f"the container left no {RESULT_NAME} in {output_dir}, "
                f"and exited {completed.returncode}"
            )
        return result

    def child_environment(self) -> dict[str, str]:
        """This process's environment, plus the key when it came from `.env`.

        `run_argv` passes ANTHROPIC_API_KEY by name, so the value has to be in the
        environment of the `docker` process rather than in its arguments.
        """
        environment = dict(os.environ)
        key = setting("ANTHROPIC_API_KEY")
        if key:
            environment["ANTHROPIC_API_KEY"] = key
        return environment

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
        return bool(setting("ANTHROPIC_API_KEY")) or self.credentials_file.is_file()

    def check(self) -> list[str]:
        """The unmet conditions, in order, each with the command that fixes it.

        An empty list means ready. It writes nothing and builds nothing.
        """
        unmet: list[str] = []
        if not self.daemon_is_reachable():
            unmet.append("docker daemon is not reachable: start Docker Desktop or Rancher Desktop")
        # The image is unreadable without a daemon, so a second line about it would name a
        # condition this run cannot know. The credential is on the host and is read either way.
        elif not self.image_is_present():
            unmet.append(f"image {self.tag} is absent: run `cowork_evals setup --docker`")
        if not self.has_credential():
            unmet.append(
                "no credential: set ANTHROPIC_API_KEY, "
                "or run `cowork_evals setup --docker` to log in"
            )
        return unmet
