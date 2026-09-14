"""Every shape a check that fails takes."""

from cowork_evals.checks import Result, Run, check


@check
def returns_false(run: Run) -> bool:
    return False


@check
def returns_a_failed_result(run: Run) -> Result:
    return Result(passed=False, explanation="the totals do not add up")


@check
def raises(run: Run) -> None:
    raise ValueError("the workbook has no active sheet")


@check
def asserts(run: Run) -> None:
    assert run.last_message == "SOMETHING ELSE"


@check
def names_a_file_that_is_not_there(run: Run) -> None:
    run.file("absent.txt")


@check
def leaves_the_workspace(run: Run) -> None:
    run.file("../trace.jsonl")


@check
def returns_something_else(run: Run) -> int:
    return 7
