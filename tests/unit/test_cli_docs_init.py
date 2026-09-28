"""The `docs` and `init` verbs: what they print, what they write, and what they refuse.

`main` is the real one and the filesystem it touches is a `tmp_path`, so `init` writes real
files and a second call reads what the first left. Nothing is mocked and nothing is patched.

`init` refusing a package built without its data is not here. Building that condition needs a
patched constant, and `scripts/build.sh` asserts both sources are in the wheel, which is the
guard that matters. The surface is docs/cli.md. See ../README.md.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from cowork_evals import cli, resources
from cowork_evals.cli import OK, USAGE, build_parser, main
from cowork_evals.config import Config


def parse(*argv: str):
    return build_parser().parse_args(list(argv))


# The parse trees.


def test_docs_takes_no_backend_and_an_optional_name() -> None:
    assert parse("docs").name is None
    assert parse("docs", "cli").name == "cli"


def test_init_takes_nothing() -> None:
    assert parse("init").verb == "init"


@pytest.mark.parametrize("argv", [("docs", "--docker"), ("init", "--docker")])
def test_neither_verb_accepts_a_backend(argv: tuple[str, ...]) -> None:
    with pytest.raises(SystemExit) as raised:
        parse(*argv)
    assert raised.value.code == USAGE


# docs.


def test_docs_lists_the_directory_then_every_name(capsys: pytest.CaptureFixture) -> None:
    assert main(["docs"]) == OK
    printed = capsys.readouterr().out.splitlines()
    assert printed[0] == str(resources.docs_dir())
    assert printed[1:] == resources.documents()


def test_docs_prints_one_absolute_path(capsys: pytest.CaptureFixture) -> None:
    assert main(["docs", "eval_format"]) == OK
    printed = capsys.readouterr().out.strip()
    assert Path(printed).is_absolute()
    assert Path(printed).is_file()
    assert Path(printed).name == "eval_format.md"


def test_docs_takes_the_extension_or_leaves_it(capsys: pytest.CaptureFixture) -> None:
    assert main(["docs", "cli"]) == OK
    with_out = capsys.readouterr().out
    assert main(["docs", "cli.md"]) == OK
    assert capsys.readouterr().out == with_out


def test_an_unknown_name_is_a_usage_error_and_lists_the_names(
    capsys: pytest.CaptureFixture,
) -> None:
    assert main(["docs", "no-such-document"]) == USAGE
    printed = capsys.readouterr().err
    assert "no document named 'no-such-document'" in printed
    for name in resources.documents():
        assert name in printed


# init.


def _init_in(path: Path, working_directory: Callable) -> int:
    with working_directory(path):
        return main(["init"])


def test_init_writes_the_config_the_memory_block_and_every_skill(
    tmp_path: Path, working_directory: Callable
) -> None:
    assert _init_in(tmp_path, working_directory) == OK
    assert (tmp_path / resources.CONFIG_NAME).is_file()
    assert (tmp_path / resources.MEMORY_NAME).is_file()
    for _, target in resources.skills():
        assert (tmp_path / target / resources.SKILL_FILE).is_file(), target


def _tree(root: Path) -> dict[Path, bytes]:
    """Every file under a skill directory, bytecode excepted, which `init` does not copy."""
    return {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def test_every_skill_lands_where_claude_code_reads_it(
    tmp_path: Path, working_directory: Callable
) -> None:
    """One directory per skill under `.claude/skills/`, and the copy is the whole directory,
    byte for byte."""
    _init_in(tmp_path, working_directory)
    installed = resources.skills()
    assert len(installed) == 3
    for source, target in installed:
        written = tmp_path / target
        assert written.parent == tmp_path / ".claude" / "skills"
        assert _tree(written) == _tree(source)


def test_a_skill_directory_is_installed_with_every_file_in_it(tmp_path: Path) -> None:
    """A skill's references, scripts and assets travel with its `SKILL.md`."""
    source = tmp_path / "source" / "greeter"
    (source / "references").mkdir(parents=True)
    (source / "scripts").mkdir()
    (source / "SKILL.md").write_text("---\nname: greeter\n---\n")
    (source / "references" / "format.md").write_text("# Format\n")
    (source / "scripts" / "run.py").write_text("print('hi')\n")
    (source / "scripts" / "__pycache__").mkdir()
    (source / "scripts" / "__pycache__" / "run.cpython-310.pyc").write_bytes(b"bytecode")
    target = tmp_path / "consumer" / ".claude" / "skills" / "greeter"

    cli._install(source, target)

    assert not (target / "scripts" / "__pycache__").exists()
    assert set(_tree(target)) == {
        Path("SKILL.md"),
        Path("references/format.md"),
        Path("scripts/run.py"),
    }


def test_the_configuration_it_writes_loads(tmp_path: Path, working_directory: Callable) -> None:
    _init_in(tmp_path, working_directory)
    with working_directory(tmp_path):
        config = Config.load()
    assert config.eval.model
    assert config.docker.platform


def test_a_second_run_changes_nothing(tmp_path: Path, working_directory: Callable) -> None:
    _init_in(tmp_path, working_directory)
    before = {path: path.read_bytes() for path in sorted(tmp_path.rglob("*")) if path.is_file()}
    assert _init_in(tmp_path, working_directory) == OK
    after = {path: path.read_bytes() for path in sorted(tmp_path.rglob("*")) if path.is_file()}
    assert after == before


def test_a_second_run_keeps_the_config_and_the_block_and_replaces_every_skill(
    tmp_path: Path, working_directory: Callable, capsys: pytest.CaptureFixture
) -> None:
    _init_in(tmp_path, working_directory)
    capsys.readouterr()
    _init_in(tmp_path, working_directory)
    printed = capsys.readouterr().out
    assert printed.count("kept") == 2
    assert printed.count("replaced") == len(resources.skills())
    assert "wrote" not in printed


def test_an_upgrade_replaces_a_stale_skill_whole(
    tmp_path: Path, working_directory: Callable
) -> None:
    """A skill written by an older version, edited, and carrying a file the package no longer
    ships, is the shipped skill byte for byte after `init`."""
    _init_in(tmp_path, working_directory)
    for _, target in resources.skills():
        written = tmp_path / target
        (written / resources.SKILL_FILE).write_text("---\nname: stale\n---\n")
        (written / "retired.md").write_text("# Gone from the package\n")
    _init_in(tmp_path, working_directory)
    for source, target in resources.skills():
        assert _tree(tmp_path / target) == _tree(source)


def test_a_skill_target_that_is_a_link_is_replaced_by_the_copy(
    tmp_path: Path, working_directory: Callable
) -> None:
    """The link goes, and what it pointed at is untouched."""
    pointed = tmp_path / "elsewhere"
    pointed.mkdir()
    (pointed / "mine.md").write_text("# Mine\n")
    source, target = resources.skills()[0]
    (tmp_path / target).parent.mkdir(parents=True)
    (tmp_path / target).symlink_to(pointed, target_is_directory=True)
    _init_in(tmp_path, working_directory)
    assert not (tmp_path / target).is_symlink()
    assert _tree(tmp_path / target) == _tree(source)
    assert (pointed / "mine.md").read_text() == "# Mine\n"


def test_an_existing_memory_file_is_appended_to(
    tmp_path: Path, working_directory: Callable
) -> None:
    memory = tmp_path / resources.MEMORY_NAME
    memory.write_text("# My repository\n\nMy own rules.\n")
    _init_in(tmp_path, working_directory)
    written = memory.read_text()
    assert written.startswith("# My repository")
    assert "My own rules." in written
    assert resources.MEMORY_MARKER in written


def test_the_memory_block_is_never_appended_twice(
    tmp_path: Path, working_directory: Callable
) -> None:
    memory = tmp_path / resources.MEMORY_NAME
    memory.write_text("# My repository\n")
    _init_in(tmp_path, working_directory)
    _init_in(tmp_path, working_directory)
    assert memory.read_text().count(resources.MEMORY_MARKER) == 1


def test_an_edited_block_is_still_recognised(tmp_path: Path, working_directory: Callable) -> None:
    """The heading is the marker, so what a consumer wrote under it survives."""
    memory = tmp_path / resources.MEMORY_NAME
    _init_in(tmp_path, working_directory)
    memory.write_text(f"{resources.MEMORY_MARKER}\n\nMy own words.\n")
    _init_in(tmp_path, working_directory)
    assert memory.read_text() == f"{resources.MEMORY_MARKER}\n\nMy own words.\n"


def test_an_existing_config_is_left_exactly_as_it_is(
    tmp_path: Path, working_directory: Callable
) -> None:
    config = tmp_path / resources.CONFIG_NAME
    config.write_text("eval:\n  model: opus\n")
    _init_in(tmp_path, working_directory)
    assert config.read_text() == "eval:\n  model: opus\n"


def test_init_needs_no_backend_and_no_configuration(
    tmp_path: Path, working_directory: Callable
) -> None:
    """It runs in a directory holding nothing, which is where a consumer runs it first."""
    assert not list(tmp_path.iterdir())
    assert _init_in(tmp_path, working_directory) == OK
