"""The fixture for the check layer. One check that passes, and one that does not.

The case is the fixture for both halves of the layer at once: a check that reads the file the
run wrote decides on what is inside it, which no grader type can express, and a check that
fails produces the `FAIL` line, the appended grader result and the `checks.jsonl` line an
integration test reads. See ../../../../../README.md.
"""

from cowork_evals.checks import Result, Run, check


@check
def the_file_says_written(run: Run) -> None:
    assert run.file("written.txt").read_text(encoding="utf-8").strip() == "WRITTEN"


@check
def the_file_is_a_workbook(run: Run) -> Result:
    return Result(passed=False, explanation="written.txt is not a workbook")
