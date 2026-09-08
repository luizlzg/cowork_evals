"""The container backend's digest and its argument lists. docs/docker.md.

Nothing here starts a container or reaches a daemon. A function that starts one is
covered in tests/integration/test_docker.py.
"""

from __future__ import annotations

import os
import re

import pytest

from cowork_evals.docker import (
    CONTAINER_EXTRA_CA,
    CONTAINER_HOME,
    DATA,
    DOCKERFILE,
    Docker,
    DockerError,
    plugin_root,
)
from cowork_evals.harness import RunOptions


def build_arg(argv: list[str], flag: str) -> str:
    """The value that follows `flag`. Fails the test when the flag is absent."""
    return argv[argv.index(flag) + 1]


# The digest, and the tag over it.


def test_the_digest_is_twelve_hex_characters():
    assert re.fullmatch(r"[0-9a-f]{12}", Docker(platform="linux/arm64").digest)


def test_the_digest_is_stable_across_instances():
    first = Docker(platform="linux/arm64", claude_code_version="2.1.259")
    second = Docker(platform="linux/arm64", claude_code_version="2.1.259")
    assert first.digest == second.digest


def test_the_platform_is_in_the_digest():
    """Without it an arm64 and an amd64 image share one tag."""
    arm = Docker(platform="linux/arm64", claude_code_version="2.1.259")
    amd = Docker(platform="linux/amd64", claude_code_version="2.1.259")
    assert arm.digest != amd.digest


def test_the_claude_code_version_is_in_the_digest():
    older = Docker(platform="linux/arm64", claude_code_version="2.1.259")
    newer = Docker(platform="linux/arm64", claude_code_version="2.1.260")
    assert older.digest != newer.digest


def test_the_tag_names_the_digest():
    docker = Docker(platform="linux/arm64")
    assert docker.tag == f"cowork-evals:{docker.digest}"


# The settings behind the configuration.


def test_the_platform_and_the_version_resolve_through_env(environment, working_directory, tmp_path):
    """Both fall back to the value docs/docker.md records."""
    with environment(EVAL_PLATFORM=None, CLAUDE_CODE_VERSION=None), working_directory(tmp_path):
        docker = Docker()
    assert docker.platform == "linux/arm64"
    assert docker.claude_code_version == "2.1.259"


def test_an_explicit_value_beats_the_setting(environment):
    with environment(EVAL_PLATFORM="linux/amd64"):
        assert Docker(platform="linux/arm64").platform == "linux/arm64"


def test_the_login_dir_defaults_under_the_cache(environment):
    docker = Docker(platform="linux/arm64")
    assert docker.login_dir == (docker.login_dir.home() / ".cache/cowork_evals/claude")
    assert docker.claude_dir == docker.login_dir / ".claude"
    assert docker.state_file == docker.login_dir / ".claude.json"
    assert docker.credentials_file == docker.claude_dir / ".credentials.json"


# The build argument list.


def test_build_argv_names_the_dockerfile_and_the_data_context():
    argv = Docker(platform="linux/arm64").build_argv()
    assert argv[:2] == ["docker", "build"]
    assert build_arg(argv, "-f") == str(DOCKERFILE)
    assert argv[-1] == str(DATA), "the context is the package data directory, and comes last"


def test_build_argv_carries_the_platform_the_tag_and_the_build_argument():
    docker = Docker(platform="linux/arm64", claude_code_version="2.1.259")
    argv = docker.build_argv()
    assert build_arg(argv, "--platform") == "linux/arm64"
    assert build_arg(argv, "--build-arg") == "CLAUDE_CODE_VERSION=2.1.259"
    assert build_arg(argv, "-t") == docker.tag


def test_build_argv_carries_one_tag_and_no_latest():
    argv = Docker(platform="linux/arm64").build_argv()
    assert argv.count("-t") == 1
    assert "cowork-evals:latest" not in argv


def test_no_cache_is_off_unless_asked():
    assert "--no-cache" not in Docker(platform="linux/arm64").build_argv()
    assert "--no-cache" in Docker(platform="linux/arm64").build_argv(no_cache=True)


def test_the_extra_ca_is_a_build_secret_when_the_host_has_one(environment, tmp_path):
    ca = tmp_path / "root_ca.pem"
    ca.write_text("-----BEGIN CERTIFICATE-----\n")
    with environment(SSL_CERT_FILE=str(ca)):
        argv = Docker(platform="linux/arm64").build_argv()
    assert build_arg(argv, "--secret") == f"id=extra_ca,src={ca}"


def test_there_is_no_extra_ca_when_the_host_sets_none(environment):
    with environment(SSL_CERT_FILE=None):
        assert "--secret" not in Docker(platform="linux/arm64").build_argv()


def test_an_ssl_cert_file_naming_a_missing_file_is_no_extra_ca(environment, tmp_path):
    with environment(SSL_CERT_FILE=str(tmp_path / "absent.pem")):
        assert Docker(platform="linux/arm64").extra_ca_file is None


# The login argument list.


def test_login_argv_mounts_the_two_credential_paths_read_write(environment):
    with environment(SSL_CERT_FILE=None):
        docker = Docker(platform="linux/arm64")
        argv = docker.login_argv()
    mounts = [argv[i + 1] for i, value in enumerate(argv) if value == "-v"]
    assert mounts == [
        f"{docker.claude_dir}:{CONTAINER_HOME}/.claude:rw",
        f"{docker.state_file}:{CONTAINER_HOME}/.claude.json:rw",
    ]


def test_login_argv_mounts_no_plugin_and_no_log_directory(environment):
    with environment(SSL_CERT_FILE=None):
        argv = Docker(platform="linux/arm64").login_argv()
    assert "/work/plugin" not in " ".join(argv)
    assert "/work/logs" not in " ".join(argv)


def test_login_argv_is_interactive_and_goes_straight_to_the_login(environment):
    """Bare `claude` lands in the first-run wizard on a fresh configuration directory."""
    with environment(SSL_CERT_FILE=None):
        docker = Docker(platform="linux/arm64")
        argv = docker.login_argv()
    assert argv[:4] == ["docker", "run", "--rm", "-it"]
    assert argv[-5:] == [docker.tag, "claude", "auth", "login", "--claudeai"]
    assert build_arg(argv, "--user") == f"{os.getuid()}:{os.getgid()}"
    assert f"HOME={CONTAINER_HOME}" in argv


def test_login_argv_points_node_at_the_extra_ca_when_the_host_has_one(environment, tmp_path):
    ca = tmp_path / "root_ca.pem"
    ca.write_text("-----BEGIN CERTIFICATE-----\n")
    with environment(SSL_CERT_FILE=str(ca)):
        argv = Docker(platform="linux/arm64").login_argv()
    assert f"NODE_EXTRA_CA_CERTS={CONTAINER_EXTRA_CA}" in argv


# The plugin root.


def test_the_plugin_root_is_the_nearest_manifest_above_the_target(tmp_path):
    root = tmp_path / "marketplace" / "smoke"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text("{}")
    case = root / "evals" / "plugin" / "python-version"
    case.mkdir(parents=True)
    assert plugin_root(case) == root.resolve()
    assert plugin_root(root) == root.resolve(), "the root itself is a target the CLI accepts"


def test_a_target_under_no_plugin_raises(tmp_path):
    with pytest.raises(DockerError):
        plugin_root(tmp_path)


# The run argument list.


@pytest.fixture
def plugin(tmp_path):
    """A plugin root with one case under it, on disk. Nothing here starts a container."""
    root = tmp_path / "smoke"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text("{}")
    (root / "evals" / "plugin" / "python-version").mkdir(parents=True)
    return root


def run_options() -> RunOptions:
    return RunOptions(model="sonnet", judge_model="haiku", max_cost_usd="5", allow_tools=("Bash",))


def test_run_argv_mounts_the_plugin_read_only_and_the_logs_read_write(
    environment, plugin, tmp_path
):
    logs = tmp_path / "logs"
    logs.mkdir()
    with environment(SSL_CERT_FILE=None):
        argv = Docker(platform="linux/arm64").run_argv(plugin, logs, run_options())
    mounts = [argv[i + 1] for i, value in enumerate(argv) if value == "-v"]
    assert mounts[-2:] == [
        f"{plugin.resolve()}:/work/plugin:ro",
        f"{logs.resolve()}:/work/logs:rw",
    ]


def test_run_argv_carries_the_uid_the_home_and_the_sandbox_option(environment, plugin, tmp_path):
    with environment(SSL_CERT_FILE=None, CLAUDE_CODE_WALNUT_SPIRE=None):
        argv = Docker(platform="linux/arm64").run_argv(plugin, tmp_path, run_options())
    assert argv[:3] == ["docker", "run", "--rm"]
    assert build_arg(argv, "--platform") == "linux/arm64"
    assert build_arg(argv, "--user") == f"{os.getuid()}:{os.getgid()}"
    assert f"HOME={CONTAINER_HOME}" in argv
    assert build_arg(argv, "--security-opt") == "seccomp=unconfined"
    assert "CLAUDE_CODE_WALNUT_SPIRE=1" in argv


def test_the_container_side_target_is_relative_to_the_plugin_root(environment, plugin, tmp_path):
    case = plugin / "evals" / "plugin" / "python-version"
    with environment(SSL_CERT_FILE=None):
        argv = Docker(platform="linux/arm64").run_argv(case, tmp_path, run_options())
    assert "/work/plugin/evals/plugin/python-version" in argv


def test_the_plugin_root_itself_is_the_mount_point(environment, plugin, tmp_path):
    with environment(SSL_CERT_FILE=None):
        argv = Docker(platform="linux/arm64").run_argv(plugin, tmp_path, run_options())
    assert "/work/plugin" in argv


def test_the_output_dir_is_the_log_mount(environment, plugin, tmp_path):
    with environment(SSL_CERT_FILE=None):
        argv = Docker(platform="linux/arm64").run_argv(plugin, tmp_path, run_options())
    assert build_arg(argv, "--output-dir") == "/work/logs"
    assert build_arg(argv, "--debug-file") == "/work/logs/debug.txt"


def test_the_two_login_paths_are_mounted_read_write(
    environment, working_directory, plugin, tmp_path
):
    """The one credential route. docs/docker.md."""
    logs = tmp_path / "logs"
    logs.mkdir()
    with environment(SSL_CERT_FILE=None), working_directory(tmp_path):
        docker = Docker(platform="linux/arm64")
        argv = docker.run_argv(plugin, logs, run_options())
    mounts = [argv[i + 1] for i, value in enumerate(argv) if value == "-v"]
    assert mounts == [
        f"{docker.claude_dir}:{CONTAINER_HOME}/.claude:rw",
        f"{docker.state_file}:{CONTAINER_HOME}/.claude.json:rw",
        f"{plugin.resolve()}:/work/plugin:ro",
        f"{logs.resolve()}:/work/logs:rw",
    ]


def test_run_argv_ends_with_the_tag_and_the_harness_command(environment, plugin, tmp_path):
    with environment(SSL_CERT_FILE=None):
        docker = Docker(platform="linux/arm64")
        argv = docker.run_argv(plugin, tmp_path, run_options())
    image = argv.index(docker.tag)
    assert argv[image + 1 : image + 4] == ["claude", "--debug-file", "/work/logs/debug.txt"]
    assert "--no-publish" in argv[image:]


def test_run_argv_mounts_nothing_else_from_the_host(environment, plugin, tmp_path):
    """The two login paths, the plugin and the logs. Nothing else."""
    with environment(SSL_CERT_FILE=None):
        argv = Docker(platform="linux/arm64").run_argv(plugin, tmp_path, run_options())
    assert argv.count("-v") == 4


def test_seed_login_dir_writes_a_state_file_the_cli_will_accept(environment, tmp_path):
    """An empty `.claude.json` is not an absent one: the CLI exits 1 on it."""
    with environment(SSL_CERT_FILE=None):
        docker = Docker(platform="linux/arm64", login_dir=tmp_path / "login")
    docker.seed_login_dir()
    assert docker.claude_dir.is_dir()
    assert docker.state_file.read_text() == "{}"


def test_seed_login_dir_replaces_an_empty_state_file(environment, tmp_path):
    with environment(SSL_CERT_FILE=None):
        docker = Docker(platform="linux/arm64", login_dir=tmp_path / "login")
    docker.claude_dir.mkdir(parents=True)
    docker.state_file.write_text("")
    docker.seed_login_dir()
    assert docker.state_file.read_text() == "{}"


def test_seed_login_dir_keeps_a_state_file_the_cli_already_wrote(environment, tmp_path):
    with environment(SSL_CERT_FILE=None):
        docker = Docker(platform="linux/arm64", login_dir=tmp_path / "login")
    docker.claude_dir.mkdir(parents=True)
    docker.state_file.write_text('{"kept": true}')
    docker.seed_login_dir()
    assert docker.state_file.read_text() == '{"kept": true}'
