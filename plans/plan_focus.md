# focus: the driver takes the keyboard without destroying what is in it

Branch: `feat/focus`.

## Scope

The driver fires a deep link and sends a synthetic Return to the frontmost window. It never
clears the composer, and it never checks what is frontmost. Both are defects, and both were
measured on 2026-09-12 by two real submissions that failed.

This plan makes the keyboard hand-off explicit and safe: the developer is asked once, in a
window they cannot miss, the composer is cleared before the prompt is inserted, and no
keystroke is sent unless CoWork is the frontmost application at that moment.

It is the driver's, not `ask`'s. `cowork_backend.run` calls `driver.run` once per case, so
every `run --cowork` case gets the same mechanism.

It builds:

| Part                                  | Is                                                                 |
| ------------------------------------- | -------------------------------------------------------------------- |
| The consent dialog                    | A macOS modal, once per process, that forces itself in front of whatever the developer is working in |
| The frontmost guard                   | A check that CoWork is frontmost, immediately before each keystroke  |
| The composer clear                    | Select all and delete, before the deep link inserts the prompt       |
| `cowork.consent` and `cowork.consent_timeout` | The two configuration keys behind them                      |
| Driver code 9                         | CoWork was not frontmost when a keystroke was due                    |

It does not build:

| Not built                                    | Why                                                                |
| -------------------------------------------- | -------------------------------------------------------------------- |
| A lock on the keyboard or the mouse          | macOS offers none to an unprivileged process. The dialog buys intent, and the guard buys safety |
| A headless route                             | The synthetic Return still needs the Accessibility grant. `docs/cowork_desktop.md` is unchanged |
| A retry after a failed frontmost check       | Retrying blind is how a keystroke reaches an editor. It refuses     |
| Any change to `ask`, the backends or the gate | One call is added in the CLI. Nothing above the driver changes shape |
| Reading the composer                          | Nothing here reads the screen. `docs/cowork_desktop.md` holds that rule |

## The measurement

Snapshot 2026-09-12. Two submissions, one prompt, both raised code 6.

| Submitted                          | Recorded in `audit.jsonl`                    |
| ---------------------------------- | -------------------------------------------- |
| `Reply with the single word: ready` | `Reply with the single word: readyennumera` |
| `Reply with the single word: ready` | `Reply with the single word: read`          |

The developer was typing in another application while the driver held the keyboard. The first
submission carried their characters into the prompt. The second lost the prompt's own last
character.

Attribution refused both, so nothing was submitted to a grader and nothing was scored on an
altered prompt. The driver failed closed. That is the only reason this is a safety and
usability fix rather than a correctness one, and it is why the guard below never replaces
attribution.

## The hazard the obvious fix creates

`System Events` sends a keystroke to the frontmost process, whatever it is. A stray Return is
harmless. A stray select-all and delete is not: it selects and deletes the contents of
whatever field has focus, which can be a source file in an editor.

A clear that does not check what is frontmost is worse than the bug it fixes. The guard is not
optional, and it applies to the Return as well.

The guard narrows the window between the check and the keystroke. It does not close it: focus
can change in between. Attribution remains the backstop, and a keystroke that lands elsewhere
is still caught as code 6 rather than graded.

## The sequence

`docs/cowork_driver.md` holds nine steps. This inserts three and leaves the rest as they are.

| #  | Step                | Does                                                             | Fails as |
| -- | ------------------- | ------------------------------------------------------------------ | -------- |
| 1  | Refuse              | Configuration, the rate ceiling and the prompt cap                | 2        |
| 2  | Record the baseline | List the session directories that already exist                   |          |
| 2a | Consent             | The modal, once per process. Cancel refuses                       | 2        |
| 2b | Activate and guard  | Activate CoWork, then check it is frontmost                       | 3, 9     |
| 2c | Clear               | Select all and delete, in the composer                            | 3        |
| 3  | Fire the deep link  | `open claude://claude.ai/new?q=<prompt>&surface=<surface>`        | 3        |
| 4  | Settle              | Sleep `settle_seconds`                                            |          |
| 4a | Guard               | Check CoWork is still frontmost                                   | 9        |
| 5  | Submit              | Send the synthetic Return                                         | 3        |
| 6  | Discover            | Poll for a session directory that is not in the baseline          | 4, 5     |
| 7  | Attribute           | Compare the recorded prompt with the submitted one                | 6        |
| 8  | Wait                | Block until the completion signal fires                           | 7        |
| 9  | Collect             | Build the session document                                        | 8        |

The clear is step 2c and not a step after the deep link. The deep link is what puts the prompt
in the composer, so clearing after it deletes the prompt.

Step 4a is between the settle and the Return, so the gap between the last check and the
keystroke is as small as the sequence allows.

## Consent

### Once per process, and the CLI is what asks

The developer approves once for a whole invocation. A 20-case suite asks once, not 20 times.

The driver knows submissions and nothing above them: `cowork_backend._run_case` builds a new
`CoWork` per case, and `CoWorkSection` is frozen, so instance state cannot carry the answer.
Consent is therefore module state in `cowork.py`, set by a module-level `consent()` and read
by `_fire_and_attribute`. One process, one operator, one keyboard.

| Caller                          | Calls                                                    |
| ------------------------------- | ---------------------------------------------------------- |
| `cli._ask`, before the driver   | `cowork.consent(config.cowork)` once                     |
| `cli._each_plugin`, before the first plugin | the same, once for the whole sweep           |
| A library caller                | the same, or sets `cowork.consent: none` in the file      |

`run` and `submit` refuse with code 2 when consent was never given and `consent` is `dialog`.
Nothing has fired at that point, so it is the same class as every other step 1 refusal.

`collect`, `sessions`, `history`, `recent` and `deep_link` never ask. They fire nothing.
`ask --session` and `ask --dry-run` therefore never show the modal.

### The modal

```sh
osascript -e 'tell me to activate' \
          -e 'display dialog "cowork_evals is about to drive CoWork. \
              Do not use the keyboard or the mouse until it finishes." \
              with title "cowork_evals" buttons {"Cancel", "Go"} \
              giving up after <consent_timeout>'
```

| Property           | Is                                                                          |
| ------------------ | ----------------------------------------------------------------------------- |
| `tell me to activate` | What forces the modal in front of the editor the developer is working in   |
| No `default button`   | A Return typed into the editor mid-sentence must not dismiss it. Without a default, Return activates nothing and the developer has to click |
| Cancel             | Non-zero exit from `osascript`, which becomes code 2. Nothing has fired       |
| `giving up after N`   | Proceeds. An unattended run is the case this exists for                    |

`display dialog` needs no Accessibility grant. Only the keystrokes do, and the preflight
already covers that.

### Configuration

Two keys in the `cowork:` section, which `docs/cowork_driver.md` owns.

| Key                | Default  | Is                                                                  |
| ------------------ | -------- | ---------------------------------------------------------------------- |
| `consent`          | `dialog` | `dialog` shows the modal once per process. `none` fires without asking |
| `consent_timeout`  | 20       | Seconds before the modal gives up and proceeds                       |

`consent: none` is the documented route for an unattended run and for this repository's own
integration tier. It is a configuration value and not a test seam: a test sets it in a
configuration file exactly as a consumer would, and no parameter exists to inject an answer.

## The guard

```sh
osascript -e 'tell application "System Events" to get name of first process whose frontmost is true'
```

| Result                    | Means                                                            |
| ------------------------- | ------------------------------------------------------------------ |
| The CoWork process name   | Proceed with the keystroke                                       |
| Any other name            | Code 9. Nothing is typed                                         |
| `osascript` non-zero      | Code 3, as every other `osascript` failure is                    |

The name to compare against is measured, not guessed, and goes in
`docs/cowork_desktop.md` beside the bundle id. `Claude` is what
`tell application "Claude" to activate` already uses, and whether the process name matches the
application name is the measurement phase 4 makes.

Code 9 is new and is not code 3. A grading layer has to tell "the driver refused to type into
something that was not CoWork" apart from "osascript is broken", and code 3 already carries
the second.

## The clear

```sh
osascript -e 'tell application "System Events" to keystroke "a" using command down' \
          -e 'tell application "System Events" to key code 51'
```

Key code 51 is Delete. It runs behind the guard, so the worst case it can reach is a CoWork
field that is not the composer, and the contents of a CoWork composer are a draft.

It does not read what it cleared and does not report it. Reading the composer means reading
the screen, which `docs/cowork_desktop.md` rules out.

## Decisions

Every one of these is settled. None is left to the implementer.

| Decision                                              | Reason                                                                  |
| ----------------------------------------------------- | -------------------------------------------------------------------------- |
| The consent timeout proceeds, it does not refuse      | Developer's call, 2026-09-12. An unattended suite is the case the key exists for |
| The frontmost check is CoWork, and it aborts          | Developer's call, 2026-09-12. A retry after a failed check is how a keystroke reaches an editor |
| Approval is once for all cases of an invocation       | Developer's call, 2026-09-12. A 20-case suite asking 20 times is unusable  |
| Consent is module state, not instance state           | A frozen `CoWorkSection` and a new `CoWork` per case cannot carry it       |
| The modal has no default button                       | A Return typed into an editor must not dismiss it                          |
| The clear is before the deep link                     | The deep link is what inserts the prompt. Clearing after deletes it        |
| The guard does not replace attribution                | The guard narrows a race it cannot close. Code 6 stays the backstop        |
| Code 9 is new rather than folded into code 3          | A refusal to type is not a broken `osascript`, and a grading layer tells them apart |
| Nothing reads the composer                            | Reading the field is reading the screen. `docs/cowork_desktop.md`          |

## Phases

Work in order. Tick a box when it is verified, then commit. Do not batch ticks.

### Phase 1: the guard and the clear

- [x] `cowork.frontmost()`: the process name `osascript` reports, or a `CoWorkError` code 3
- [x] `CoWork._guard()`: code 9 when the frontmost process is not CoWork, naming what was
- [x] `CoWork._clear()`: activate, guard, select all, delete
- [x] `_fire_and_attribute` runs the clear before the deep link and guards before the Return
- [x] Code 9 is in `CoWorkError`'s taxonomy and nothing collapses it into code 3

### Phase 2: consent

- [x] `cowork.consent(section)`: the modal, once per process, and the module flag behind it
- [x] Cancel is code 2. The timeout proceeds. `consent: none` never shows it
- [x] `run` and `submit` refuse with code 2 when consent was never given
- [x] `collect`, `sessions`, `history`, `recent` and `deep_link` never ask
- [x] `CoWorkSection` gains `consent` and `consent_timeout`, with the defaults above
- [x] `data/cowork_evals.example.yaml` gains both keys

### Phase 3: the callers

- [ ] `cli._ask` calls `consent` once, before the driver, and not on `--session` or `--dry-run`
      (blocked: the `ask` verb is plan 8's and is not on `main`)
- [x] `cli._each_plugin` calls it once, before the first plugin, on `--cowork` only
- [x] `run --cowork --dry-run` never asks

### Phase 4: tests

Activate the testing rules in `tests/README.md` first. No mock, no fake, no stub, no patch,
no skip.

- [ ] Unit: `consent: none` leaves the module flag alone and refuses nothing
- [ ] Unit: `run` under `consent: dialog` with no consent given raises code 2, and fires nothing
- [ ] Unit: `collect` and `deep_link` work under `consent: dialog` with no consent given
- [ ] Unit: the two new keys load, take their defaults, and refuse a wrong type
- [ ] Unit: code 9 is distinct from code 3 in the taxonomy
- [ ] Integration: `frontmost()` returns this machine's actual frontmost process name
- [ ] Integration: one real submission under `consent: none` clears a composer that was
      primed with text by hand, and the audit prompt matches the submitted one exactly

### Phase 5: documentation, and the measurement

- [ ] `docs/cowork_driver.md`: the sequence table, the two keys, code 9, and the consent section
- [ ] `docs/cowork_desktop.md`: the CoWork process name as `System Events` reports it, dated
      and called a snapshot, beside the bundle id
- [ ] `docs/cowork_desktop.md`: one section recording the 2026-09-12 contamination, dated,
      and what the composer does with a deep link fired into a non-empty field
- [ ] `docs/cli.md`: one paragraph saying `run --cowork` and `ask` ask once, and what `none` is
- [ ] `README.md`: the sentence about a CoWork run taking the keyboard says the modal asks first
- [ ] `plans/README.md`: the row moves to `implemented` on the merge, and the file moves to
      `done/plan_focus.<YYYYMMDD>.md`

## Verification

- [ ] `scripts/lint.sh`
- [ ] `scripts/test.sh tests/unit`
- [ ] `scripts/test.sh` with the default selection, green
- [ ] `scripts/test.sh -m integration -k focus`, on a machine with the profile and the grant
- [ ] Type text into the CoWork composer by hand, then `cowork_evals ask --cowork "Reply with
      the single word: ready"`. It prints `ready`, and the audit prompt carries no extra text
- [ ] Start an ask, click into an editor before the Return, and confirm it exits on code 9
      with nothing typed into the editor
- [ ] `plans/plan_ask.md` phase 5 is unblocked: the four measurements run without a code 6
