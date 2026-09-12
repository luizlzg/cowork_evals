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

from cowork_evals import resources
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
        assert (tmp_path / target).is_file(), target


def test_every_skill_lands_where_claude_code_reads_it(
    tmp_path: Path, working_directory: Callable
) -> None:
    """One directory per skill under `.claude/skills/`, and the copy is byte for byte."""
    _init_in(tmp_path, working_directory)
    installed = resources.skills()
    assert len(installed) == 2
    for source, target in installed:
        written = tmp_path / target
        assert written.parent.parent == tmp_path / ".claude" / "skills"
        assert written.read_text() == source.read_text()


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


def test_a_second_run_reports_every_target_as_kept(
    tmp_path: Path, working_directory: Callable, capsys: pytest.CaptureFixture
) -> None:
    _init_in(tmp_path, working_directory)
    capsys.readouterr()
    _init_in(tmp_path, working_directory)
    printed = capsys.readouterr().out
    assert printed.count("kept") == 2 + len(resources.skills())
    assert "wrote" not in printed


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
