"""The container backend's digest and its argument lists. docs/docker.md.

Nothing here starts a container or reaches a daemon. A function that starts one is
covered in tests/integration/test_docker.py.
"""

from __future__ import annotations

import os
import re

from cowork_evals.docker import CONTAINER_EXTRA_CA, CONTAINER_HOME, DATA, DOCKERFILE, Docker


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


def test_login_argv_is_interactive_and_runs_the_cli(environment):
    with environment(SSL_CERT_FILE=None):
        docker = Docker(platform="linux/arm64")
        argv = docker.login_argv()
    assert argv[:4] == ["docker", "run", "--rm", "-it"]
    assert argv[-2:] == [docker.tag, "claude"]
    assert build_arg(argv, "--user") == f"{os.getuid()}:{os.getgid()}"
    assert f"HOME={CONTAINER_HOME}" in argv


def test_login_argv_points_node_at_the_extra_ca_when_the_host_has_one(environment, tmp_path):
    ca = tmp_path / "root_ca.pem"
    ca.write_text("-----BEGIN CERTIFICATE-----\n")
    with environment(SSL_CERT_FILE=str(ca)):
        argv = Docker(platform="linux/arm64").login_argv()
    assert f"NODE_EXTRA_CA_CERTS={CONTAINER_EXTRA_CA}" in argv
