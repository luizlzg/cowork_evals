"""Every shape a check that passes takes. Input on disk, read by the real discovery."""

from helpers import shout

from cowork_evals.checks import Result, Run, check


@check
def the_file_says_written(run: Run) -> None:
    assert run.file("written.txt").read_text(encoding="utf-8").strip() == "WRITTEN"


@check
def the_sibling_is_importable(run: Run) -> bool:
    return shout("written") == "WRITTEN"


@check
def the_last_message_is_read(run: Run) -> Result:
    return Result(passed="WRITTEN" in run.last_message, explanation="the reply says WRITTEN")


@check
def the_scratch_is_writable(run: Run) -> None:
    (run.scratch / f"note-{run.index}.txt").write_text(str(run.index), encoding="utf-8")


def not_a_check(run: Run) -> None:
    """Undecorated, so it is not discovered and never runs."""
    raise AssertionError("an undecorated function was run")
