"""The test image's digest and its argument lists. docs/cowork_test.md.

Nothing here starts a container or reaches a daemon. A function that starts one is
covered in tests/integration/test_pytest_image.py.
"""

from __future__ import annotations

import re

from cowork_evals.config import Config, DockerSection
from cowork_evals.docker import DATA, Condition
from cowork_evals.docker.pytest_image import (
    DOCKERFILE,
    REQUIREMENTS_TEST,
    PytestImage,
    digest_of,
)


def build_arg(argv: list[str], flag: str) -> str:
    """The value that follows `flag`. Fails the test when the flag is absent."""
    return argv[argv.index(flag) + 1]


def image(**values) -> PytestImage:
    """A test image over one written `docker:` section. There is no other route in."""
    return PytestImage(Config(docker=DockerSection(**values)))


# The digest, and the tag over it.


def test_the_digest_is_twelve_hex_characters():
    assert re.fullmatch(r"[0-9a-f]{12}", image().digest)


def test_the_digest_is_stable_across_instances():
    first = image(claude_code_version="2.1.259")
    second = image(claude_code_version="2.1.259")
    assert first.digest == second.digest


def test_a_rebuilt_base_is_a_different_test_tag():
    """The base digest is the first thing hashed, so a stale hit over an old base is not
    reachable."""
    older = image(claude_code_version="2.1.259")
    newer = image(claude_code_version="2.1.260")
    assert older.docker.digest != newer.docker.digest
    assert older.digest != newer.digest


def test_the_platform_is_in_the_digest():
    arm = image(platform="linux/arm64", claude_code_version="2.1.259")
    amd = image(platform="linux/amd64", claude_code_version="2.1.259")
    assert arm.digest != amd.digest


def test_the_digest_hashes_the_base_the_dockerfile_the_pinned_list_and_the_platform():
    """Which four inputs go in, and in what order. The hash itself is the next test."""
    configured = image()
    assert configured.digest == digest_of(
        configured.docker.digest.encode(),
        DOCKERFILE.read_bytes(),
        REQUIREMENTS_TEST.read_bytes(),
        configured.platform.encode(),
    )


def test_changing_any_one_of_the_four_changes_the_digest():
    """The two that are files on disk are unreachable through a `docker:` section."""
    four = (b"base", b"dockerfile", b"pins", b"linux/arm64")
    unchanged = digest_of(*four)
    for position in range(len(four)):
        edited = list(four)
        edited[position] = b"edited"
        assert digest_of(*edited) != unchanged


def test_the_test_digest_is_not_the_base_digest():
    configured = image()
    assert configured.digest != configured.docker.digest


def test_the_tag_names_the_digest_and_its_own_repository():
    configured = image()
    assert configured.tag == f"cowork-evals-test:{configured.digest}"
    assert not configured.tag.startswith("cowork-evals:")


def test_there_is_no_latest():
    assert "latest" not in image().tag


# The build argument list.


def test_build_argv_names_the_pytest_dockerfile_and_the_data_context():
    argv = image().build_argv()
    assert argv[:2] == ["docker", "build"]
    assert build_arg(argv, "-f") == str(DOCKERFILE)
    assert argv[-1] == str(DATA), "the context is the package data directory, and comes last"


def test_build_argv_carries_the_platform_the_tag_and_the_base_tag():
    configured = image(claude_code_version="2.1.259")
    argv = configured.build_argv()
    assert build_arg(argv, "--platform") == "linux/arm64"
    assert build_arg(argv, "--build-arg") == f"BASE_TAG={configured.docker.tag}"
    assert build_arg(argv, "-t") == configured.tag


def test_build_argv_carries_one_tag_and_one_build_argument():
    argv = image().build_argv()
    assert argv.count("-t") == 1
    assert argv.count("--build-arg") == 1


def test_build_argv_carries_no_build_secret(tmp_path):
    """The base image already holds the extra root CA, and this layer reaches PyPI alone."""
    ca = tmp_path / "root_ca.pem"
    ca.write_text("-----BEGIN CERTIFICATE-----\n")
    assert "--secret" not in image(extra_ca_file=ca).build_argv()


def test_no_cache_is_off_unless_asked():
    assert "--no-cache" not in image().build_argv()
    assert "--no-cache" in image().build_argv(no_cache=True)


# The Dockerfile itself.


def test_the_dockerfile_takes_its_base_from_the_build_argument():
    """A literal base tag here is an image built against a base nothing resolved."""
    text = DOCKERFILE.read_text()
    assert "ARG BASE_TAG" in text
    assert "FROM ${BASE_TAG}" in text
    assert "FROM cowork-evals" not in text


def test_the_dockerfile_installs_the_pinned_list_with_no_deps():
    text = DOCKERFILE.read_text()
    assert "--no-deps" in text
    assert "-r /tmp/requirements_test.txt" in text
    assert text.count("python3 -m pip install") == 1, "one install layer, and one only"


# The check.


def test_check_never_returns_the_credential_condition():
    """There is no login in this path, so nothing here can want one.

    It reads the daemon and the two image tags, whatever this machine's state is, and
    starts no container.
    """
    conditions = [condition for condition, _ in image().check()]
    assert Condition.CREDENTIAL not in conditions
    assert set(conditions) <= {Condition.DAEMON, Condition.IMAGE}
