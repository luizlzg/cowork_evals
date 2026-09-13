"""One check, so the directory itself is the only thing wrong with this case."""

from cowork_evals.checks import Run, check


@check
def the_reply_greets(run: Run) -> bool:
    return "hello" in run.last_message.lower()
