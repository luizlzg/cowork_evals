"""One check and one helper beside it. A valid checks directory is no violation."""

from helpers import greeting

from cowork_evals.checks import Run, check


@check
def the_reply_greets_alex(run: Run) -> bool:
    return greeting() in run.last_message
