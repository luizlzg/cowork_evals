# Consent

## Summary

Driving CoWork takes the keyboard: the driver activates the desktop application and sends
keystrokes to the frontmost window. A modal dialog exists to warn whoever is at the machine
first, and it works. Almost nothing shows it.

`CoWork._consented` reads a module flag and refuses with code 2 when it is unset. Showing the
dialog is the caller's job, and only `cli._ask` and `cli._each_plugin` do it. Every other caller
either calls `cowork.consent` itself or sets `cowork.consent: none`. The integration tier took
the second route, so on 2026-09-13 a `pytest -m integration` run activated CoWork and typed with
no warning while the developer was working in another window.

Two changes fix it, because two different things take the keyboard. The driver asks instead of
checking, which covers every caller of the driver. The integration tier asks once before any of
its tests run, which covers the three tests that call `osascript` themselves and never reach the
driver at all. After both, `cowork.consent: none` is the only way to fire without a warning.

## Change 1: the driver asks

`CoWork._consented` (`cowork.py:243`) becomes one call to `cowork.consent(self._config)`.

That function already does the whole job: it returns at once under `consent: none` or when this
process has already asked, shows the dialog otherwise, sets the flag, and raises code 2 on
Cancel. The step number stays 2a and the code stays 2, so the failure taxonomy is unchanged.

`cli._ask` and `cli._each_plugin` keep their up-front call, because asking once before a sweep
beats asking at the first submission. They stop being the only thing that asks.

This is the fix a consumer gets. It is not enough for this repository's own tests, which is
change 2.

## Change 2: the integration tier asks

Three tests in `tests/integration/test_cowork.py` take the keyboard without going through the
driver, so no change to the driver can cover them:

| Test                                                      | Takes the keyboard by        | `live` |
| ----------------------------------------------------------- | ------------------------------ | ------ |
| `test_focus_frontmost_names_this_machines_frontmost_process` | `activate("Finder")`         | no     |
| `test_focus_the_guard_refuses_with_code_9_when_cowork_is_not_frontmost` | `activate("Finder")` | no    |
| `test_focus_a_primed_composer_is_cleared_before_the_prompt`  | `activate` then `keystroke "CONTAMINATION"`, before it calls the driver | yes |

Two of them are not `live`, so `-m "integration and not live"` steals focus today and this plan
must not claim otherwise.

`tests/integration/conftest.py` gains a session-scoped autouse fixture that calls
`cowork.consent` once, with `cowork.consent` forced to `dialog`. Autouse, so a new test cannot
forget it, which is the class of bug this plan exists to close. Session-scoped, so one run asks
once and the driver's own ask is then a no-op.

It asks on every integration run, including a Docker-only one that would take no keyboard.
Gating on a marker was rejected: a marker is something a new test can omit, and the two tests
above show that happening is not hypothetical. One dialog per run is the cheaper mistake.

It needs no CoWork profile. `cowork.consent` reads `consent` and `consent_timeout` and nothing
else, so a machine with no profile configured still gets the dialog, which is correct:
`activate("Finder")` needs no profile either.

Cancel raises code 2 from the fixture, so every integration test errors. That is the right
outcome: the developer said no to the keyboard, so the tier cannot run.

## What else has to change

| Thing                                                      | Do                                              |
| ---------------------------------------------------------- | ------------------------------------------------- |
| `CONSENT_DIALOG`, imported at `cowork.py:23`, read only by the deleted condition | drop the import, or lint fails |
| `tests/integration/conftest.py`, the `unattended` fixture, sets `consent: none` | set `consent: dialog`, rename it `attended`. Five tests use it |
| `tests/unit/test_cowork.py:529`, `driver.run` under `consent: dialog` | delete the test |

The fixture forces `dialog` rather than copying the machine's value, so a developer whose own
file carries `none` is still warned by a test run.

That unit test is deleted rather than adapted. The obvious adaptation, the same submission under
`consent: none`, is worse: consent passes, the driver proceeds to `_clear`, and `osascript`
activates CoWork for real from the unit tier. The rule that follows is that a unit test may call
`_consented` and may never call `run` or `submit`.

Nothing else in the unit tier is affected. The other two sites that reach the firing path are
`test_cowork.py:507`, which refuses at the prompt cap before consent, and `test_cowork.py:522`,
which already carries `consent: none`. `test_cli.py`'s ceiling test reaches `cli._each_plugin`
on the CoWork backend and already sets `consent: none` too.

## Testing

A dialog cannot be asserted without a person, so the assertion is its effect: a submission that
succeeds under `consent: dialog` proves the driver asked, because the old code would have raised
code 2. That belongs in the integration tier and is added to `test_a_live_run_returns_the_marker`,
which already makes one live submission, so it costs no extra VM boot.

It asserts the flag is set after the submission and not that it was clear before: the autouse
fixture has already asked by then, which is the point of change 2.

No new unit test. After the deletion the unit tier cannot assert anything more about consent
without showing a dialog or activating the application, and both are out of bounds there.

Never mock and never skip, per `CLAUDE.md` and `tests/README.md`. Neither needs lifting:
`consent: none` is a configuration value set in a file, not a seam.

## Documentation updates

- `docs/cowork_driver.md`, `Consent`: the driver joins the caller table; `run` and `submit` ask
  rather than refuse; `consent: none` is no longer "the route for this repository's own
  integration tier". `Failure taxonomy` is unchanged.
- `docs/cli.md`: anything reaching a session asks at its first submission, not just `run` and
  `ask`.
- `tests/README.md`: the `unattended` fixture paragraph, the name wherever it appears, and one
  line saying the integration tier asks once before any of its tests run and that
  `-m "integration and not live"` takes the keyboard in two of them.
- `cowork.py`: the `_consented` and `consent` docstrings.

## Implementation steps

> **For the implementer:** work autonomously end to end, editing files only, then run
> **Verification steps** in one batch. Do the third box before running the unit tier: after the
> first, a unit test that drives the firing path opens a real dialog and blocks for ten seconds
> rather than failing. Never run any integration selection without telling the developer first:
> two of those tests take the keyboard even without `live`.

Tick a box when it is verified, then commit. Do not batch ticks. `CLAUDE.md`.

- [x] `_consented` calls `cowork.consent`, the `CONSENT_DIALOG` import goes, docstring says why
- [x] `tests/integration/conftest.py`: a session-scoped autouse fixture asks once
- [x] Delete `test_a_submission_with_no_consent_raises_code_2_and_fires_nothing`
- [x] The `unattended` fixture forces `consent: dialog`, is renamed `attended`, and the five
      tests that take it follow
- [ ] `test_a_live_run_returns_the_marker` asserts `consent: dialog` and the flag set afterwards
- [ ] The four documentation updates above

## Verification steps

1. `scripts/lint.sh --fix`, then `scripts/lint.sh`.
2. `scripts/test.sh`. It must finish in its usual time: a ten-second pause is a unit test that
   opened a dialog.
3. Tell the developer first. `scripts/test.sh -m "integration and not live"`: the dialog appears
   once, before the first test, and two of those tests then activate Finder.
4. Tell the developer first. `scripts/test.sh -m integration`: the dialog still appears exactly
   once for the whole run.
5. By hand. Start that run, switch to a text editor and type. The dialog must arrive in front of
   the editor before anything activates another application. Cancel it and confirm every
   integration test errors with code 2, and that nothing was typed into the editor.
