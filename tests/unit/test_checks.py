"""The check layer over hand-written case trees and hand-written run directories.

The case tree and the collected run are under tests/data/checks/. The run directory is
copied into `tmp_path` before anything runs, because a check writes `scratch/` and the layer
writes `checks.jsonl` beside the three collected names, and a fixture directory is read and
never written. The discovery, the loader and the execution are the real ones, and every
expected value is a literal. No model, and no judge. See ../README.md.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from cowork_evals import checks
from cowork_evals.cases import read
from cowork_evals.checks import Check, CheckError, Result, Run

DATA = Path(__file__).resolve().parent.parent / "data" / "checks"
PLUGIN = DATA / "plugin"
CASES = PLUGIN / "evals" / "plugin"


@pytest.fixture
def collected(tmp_path: Path) -> Path:
    """One collected run directory, copied out of the fixture tree so it can be written."""
    directory = tmp_path / "traces" / "checked" / "run-1"
    shutil.copytree(DATA / "run", directory)
    return directory


def one_run(collected: Path, case: str = "checked", index: int = 1) -> Run:
    return checks.build_run(collected, CASES / case, index, "haiku")


# Discovery.


def test_a_check_is_named_for_its_file_and_its_function() -> None:
    found = checks.discover(CASES / "checked")
    assert [one.name for one in found] == [
        "assertions.the_file_says_written",
        "assertions.the_sibling_is_importable",
        "assertions.the_last_message_is_read",
        "assertions.the_scratch_is_writable",
    ]


def test_the_order_is_path_order_then_definition_order() -> None:
    found = checks.discover(CASES / "failing")
    assert [one.name.split(".")[1] for one in found] == [
        "returns_false",
        "returns_a_failed_result",
        "raises",
        "asserts",
        "names_a_file_that_is_not_there",
        "leaves_the_workspace",
        "returns_something_else",
    ]


def test_an_undecorated_function_is_not_a_check() -> None:
    assert "assertions.not_a_check" not in {one.name for one in checks.discover(CASES / "checked")}


def test_a_file_with_no_decorated_function_yields_nothing() -> None:
    assert checks.discover(CASES / "noted") == ()


def test_a_case_with_no_checks_directory_yields_nothing() -> None:
    assert checks.discover(DATA) == ()


def test_a_file_that_will_not_import_is_one_failed_check_named_for_the_file() -> None:
    found = checks.discover(CASES / "broken")
    assert len(found) == 1
    assert found[0].name == "unimportable"
    assert found[0].function is None
    assert found[0].error is not None
    assert "unimportable.py could not be imported: RuntimeError" in found[0].error
    assert "openpyxl is not installed" in found[0].error


def test_the_checks_directory_is_on_sys_path_only_while_the_files_load() -> None:
    before = list(sys.path)
    found = checks.discover(CASES / "checked")
    assert sys.path == before
    assert found  # the sibling import resolved while the directory was on the path


def test_a_sibling_a_check_file_imported_is_not_left_in_sys_modules() -> None:
    checks.discover(CASES / "checked")
    assert "helpers" not in sys.modules
    assert not [name for name in sys.modules if name.startswith("cowork_evals_check_")]


def test_two_cases_holding_one_file_name_get_two_module_names() -> None:
    first = checks._module_name(CASES / "checked" / "checks" / "helpers.py")
    second = checks._module_name(CASES / "noted" / "checks" / "helpers.py")
    assert first != second
    assert first.endswith("_helpers") and second.endswith("_helpers")


def test_a_duplicate_name_within_one_case_is_reported() -> None:
    path = CASES / "checked" / "checks" / "assertions.py"
    one = Check(name="assertions.same", path=path, function=lambda run: None)
    assert checks.duplicate_names((one, one)) == ["assertions.same"]
    assert checks.duplicate_names((one,)) == []


def test_the_case_reader_carries_the_check_files_in_path_order() -> None:
    case = read(CASES / "checked")
    assert [path.name for path in case.checks] == ["assertions.py", "helpers.py"]
    assert read(CASES / "broken").checks == (CASES / "broken" / "checks" / "unimportable.py",)


# The run a check reads.


def test_the_run_carries_what_the_collector_left(collected: Path) -> None:
    run = one_run(collected)
    assert run.workspace == collected / "workspace"
    assert run.trace == collected / "trace.jsonl"
    assert run.last_message == "WRITTEN\n"
    assert run.run_dir == collected
    assert run.case_dir == CASES / "checked"
    assert run.index == 1
    assert run.judge_model == "haiku"


def test_the_scratch_is_created_before_the_first_check(collected: Path) -> None:
    assert not (collected / "scratch").exists()
    run = one_run(collected)
    assert run.scratch == collected / "scratch"
    assert run.scratch.is_dir()


def test_the_scratch_is_shared_by_every_check_of_one_run(collected: Path) -> None:
    for one in checks.discover(CASES / "checked"):
        checks.execute(one, one_run(collected))
    assert [path.name for path in sorted((collected / "scratch").iterdir())] == ["note-1.txt"]


def test_a_run_with_no_last_message_reads_as_empty(collected: Path) -> None:
    (collected / "last_message.txt").unlink()
    assert one_run(collected).last_message == ""


def test_file_resolves_under_the_workspace(collected: Path) -> None:
    assert one_run(collected).file("written.txt") == collected / "workspace" / "written.txt"


def test_a_name_that_is_not_there_raises(collected: Path) -> None:
    with pytest.raises(CheckError) as raised:
        one_run(collected).file("absent.txt")
    assert str(raised.value) == "absent.txt is not in the workspace"


def test_a_name_that_leaves_the_workspace_raises(collected: Path) -> None:
    with pytest.raises(CheckError) as raised:
        one_run(collected).file("../trace.jsonl")
    assert str(raised.value) == "../trace.jsonl resolves outside the workspace"


# The judge over paths. Nothing here starts a process: the two refusals return before one.


def test_a_judge_call_naming_no_path_is_a_failed_check(collected: Path) -> None:
    result = one_run(collected).judge("Every slide carries a title.")
    assert result.passed is False
    assert result.explanation == checks.NO_PATHS


def test_a_judge_call_naming_a_path_that_is_not_there_is_a_failed_check(collected: Path) -> None:
    result = one_run(collected).judge("Every slide carries a title.", "scratch/deck.png")
    assert result.passed is False
    assert result.explanation == "scratch/deck.png is not there, so it cannot be judged"


# Execution.


def outcomes(case: str, collected: Path) -> dict[str, Any]:
    return {
        one.name.split(".")[-1]: checks.execute(one, one_run(collected, case))
        for one in checks.discover(CASES / case)
    }


def test_every_passing_shape_passes(collected: Path) -> None:
    found = outcomes("checked", collected)
    assert [one.passed for one in found.values()] == [True, True, True, True]
    assert found["the_file_says_written"].explanation == "the check raised nothing"
    assert found["the_sibling_is_importable"].explanation == "the check returned True"
    assert found["the_last_message_is_read"].explanation == "the reply says WRITTEN"


def test_every_failing_shape_fails(collected: Path) -> None:
    found = outcomes("failing", collected)
    assert [one.passed for one in found.values()] == [False] * 7
    assert found["returns_false"].explanation == "the check returned False"
    assert found["returns_a_failed_result"].explanation == "the totals do not add up"
    assert found["raises"].explanation == "ValueError: the workbook has no active sheet"
    assert (
        found["names_a_file_that_is_not_there"].explanation == "absent.txt is not in the workspace"
    )
    assert (
        found["leaves_the_workspace"].explanation == "../trace.jsonl resolves outside the workspace"
    )
    assert found["returns_something_else"].explanation == (
        "the check returned int, and a check returns None, a bool or a Result"
    )


def test_an_exception_carries_its_traceback_and_a_check_error_does_not(collected: Path) -> None:
    found = outcomes("failing", collected)
    assert "ValueError: the workbook has no active sheet" in found["raises"].traceback
    assert "failures.py" in found["raises"].traceback
    assert found["names_a_file_that_is_not_there"].traceback is None


def test_a_failed_assert_carries_the_assertion(collected: Path) -> None:
    found = outcomes("failing", collected)
    assert found["asserts"].explanation.startswith("AssertionError")
    assert "assert run.last_message" in found["asserts"].traceback


def test_a_file_that_will_not_import_is_a_failed_check(collected: Path) -> None:
    one = checks.discover(CASES / "broken")[0]
    outcome = checks.execute(one, one_run(collected, "broken"))
    assert outcome.name == "unimportable"
    assert outcome.passed is False
    assert "could not be imported" in outcome.explanation


def test_nothing_raises_out_of_the_module(collected: Path) -> None:
    for case in ("checked", "failing", "broken"):
        for one in checks.discover(CASES / case):
            assert checks.execute(one, one_run(collected, case)).duration_seconds >= 0


def test_a_skip_is_a_failed_unscored_check() -> None:
    one = Check(name="assertions.x", path=Path("x.py"), function=lambda run: None)
    outcome = checks.skipped(one, checks.NO_ARTEFACTS)
    assert outcome.passed is False
    assert outcome.skipped is True
    assert outcome.skip_reason == checks.NO_ARTEFACTS
    assert checks.grader_result(outcome)["scored"] is False


def test_a_result_carries_two_fields_and_nothing_else() -> None:
    assert [field for field in Result.__dataclass_fields__] == ["passed", "explanation"]
    assert Result(passed=True).explanation == ""


def test_the_line_one_check_writes(collected: Path) -> None:
    found = outcomes("failing", collected)
    line = json.loads(json.dumps(found["returns_false"].document()))
    assert line["name"] == "failures.returns_false"
    assert line["passed"] is False
    assert line["explanation"] == "the check returned False"
    assert line["durationSeconds"] >= 0
    assert "traceback" not in line
    assert "judge" not in line
