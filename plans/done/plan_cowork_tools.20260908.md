# Plan: the CoWork driver library

Branch `feat/cowork-tools`, cut from `main`. Eight phases, one commit each.

**Implemented. Every box is ticked and the branch is merged.** The file stays, per
[`README.md`](README.md). Three things below were proposed here and reversed during the
work; the section that follows records them, and the rest of the file is left as it was
written, scope, decisions, constraints and phases alike. Where anything below and that
section disagree, that section is what was built.

## What changed during implementation

The developer decided each of these while the work was in flight. The phases below are the
proposal, not the outcome.

| Proposed here                                        | Built instead                                     | Why                                                        |
| ---------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------ |
| `src/cowork_evals/prompt_lint.py`, a deny-list refusing a prompt on a live account | Nothing. The module was written in phase 3 and removed | A refusal the developer did not ask for. `CLAUDE.md`, never invent a restriction |
| `runner`, a callable seam so a test passes a recording fake | Nothing. `open` and `osascript` are run directly | A fake is a mock. `CLAUDE.md`, never mock. What a test cannot reach without the application, the live test in `tests/integration/` reaches by firing one |
| `tests/test_*.py`, one flat directory                | `tests/unit/` and `tests/integration/`, selected by `-m integration` | A test needing a real profile cannot sit in the default selection |

Three modules therefore became two, `config.py` and `cowork.py`, and the driver has no
deny-list and no injectable seam. All of it is in
[`../docs/cowork_driver.md`](../docs/cowork_driver.md) and
[`../tests/README.md`](../tests/README.md).

## Scope

A Python library that drives the CoWork desktop application: submit one prompt, wait for the
run to finish, and return what the session produced. It manages CoWork and nothing else.

The behaviour it implements is [`../docs/cowork_driver.md`](../docs/cowork_driver.md): the
submission sequence, the completion signal, the reading rules, the session document, the rate
ceiling, the prompt linter and the failure taxonomy. The application internals it couples to
are [`../docs/cowork_desktop.md`](../docs/cowork_desktop.md), which phase 2 re-probes. This
plan adds the API and the configuration file, which neither of those defines.

| Builds                                              | Is                                              |
| ---------------------------------------------------- | ------------------------------------------------ |
| `src/cowork_evals/__init__.py`                      | The package tree the library lives in           |
| `src/cowork_evals/config.py`                        | `cowork_evals.yaml`, and the `Config` it produces |
| `src/cowork_evals/prompt_lint.py`                   | The deny-list linter that protects a live account |
| `src/cowork_evals/cowork.py`                        | The library                                     |
| `tests/test_config.py`, `tests/test_prompt_lint.py`, `tests/test_cowork.py` | [`../tests/README.md`](../tests/README.md) |

## Out of scope

| Not built                                           | Belongs to                                     |
| ----------------------------------------------------- | ----------------------------------------------- |
| A command line over the library, `python -m` included | its own plan. It wraps the API below and adds nothing |
| Everything above the driver: the `cowork_evals` command, the backends, the graders, the gate | [`../docs/cli.md`](../docs/cli.md) |
| Any `cowork_evals.yaml` section other than `cowork:` | the plan that builds the thing it configures   |
| The `.env` loader, which carries credentials and not configuration | the plan that builds the Docker backend |
| Attachments, the `file` and `folder` parameters, and plugin staging | a later plan. They are unfired router parameters in `docs/cowork_desktop.md`, so sending one is a measurement first. `prompt` widens from `str` to a list additively when it is done |

The library is importable and nothing else. It has no entry point, no console script and no
`__main__`, and this plan adds none. See [`../CLAUDE.md`](../CLAUDE.md).

## The API

One object holds the configuration. Every name below is public; everything else in the
modules is private.

```python
from cowork_evals import Config, CoWork, CoWorkError

cw = CoWork()                                    # reads cowork_evals.yaml
cw = CoWork(profile="...", max_runs=10)          # the same, with overrides
cw = CoWork.from_file("other.yaml")

doc = cw.run("Summarize the last three emails")  # submit, wait, collect

class CoWork:
    def __init__(self, config: Config | None = None, *, runner=None, **overrides) -> None
    @classmethod
    def from_file(cls, path: Path, **overrides) -> CoWork

    config: Config                               # frozen, read only

    def run(self, prompt: str) -> dict
    def submit(self, prompt: str) -> Path
    def wait(self, session_dir: Path) -> Path
    def collect(self, session_dir: Path, *, prompt: str | None = None) -> dict
    def sessions(self, root: Path | None = None) -> list[Path]
    def history(self, run_log: Path | None = None) -> list[dict]
    def deep_link(self, prompt: str) -> str

class CoWorkError(Exception):
    code: int                                    # the failure taxonomy
    session_dir: Path | None
```

| Method      | Does                                          | Returns                          | Fires |
| ----------- | ----------------------------------------------- | --------------------------------- | ----- |
| `run`       | `submit`, then `wait`, then `collect`         | The session document             | yes   |
| `submit`    | Steps 1 to 7 of the sequence                  | The attributed session directory | yes   |
| `wait`      | Step 8, the completion signal                 | The same directory               | no    |
| `collect`   | Step 9, reading one session already on disk   | The session document             | no    |
| `sessions`  | Every session directory under a root          | Paths, sorted                    | no    |
| `history`   | The run log                                   | One dictionary per line, oldest first | no |
| `deep_link` | Builds the URL, percent-encoding the prompt   | The URL                          | no    |

Rules that hold for all of them:

- Construction resolves the configuration and validates nothing else. It reads no session,
  starts no process and raises only on a malformed configuration file. A missing `profile`
  is refused by the first method that needs one, never at construction, so
  `CoWork().collect(archived_dir)` works on a machine that has no CoWork.
- A failure raises `CoWorkError` carrying the taxonomy code. No method returns an error
  code, calls `sys.exit`, or prints.
- `config` is a frozen dataclass and is not reassigned. A different configuration is a
  different `CoWork`.
- `sessions` and `history` default to the configured paths and take an argument to read
  somewhere else, which is what the tests use.
- `runner` is the test seam: a callable that runs `open` and `osascript`. It defaults to a
  real subprocess runner, and a test passes a recording fake to the constructor.
- `collect` takes `prompt` when the caller knows what was submitted, which fills `prompt` and
  `prompt_sha256`. Without it those two come from the audit record.
- Every public callable is fully type hinted, and the session document is JSON-serializable:
  dictionaries, lists, strings, numbers and `None`, with every path a string.

Only `Config`, `CoWork` and `CoWorkError` are exported from `cowork_evals`. There are no
module level functions, so there is one way to call the library. `__init__.py` is a docstring
until phase 4, which adds those three re-exports and `__all__` and nothing else.

## Configuration

One file, `cowork_evals.yaml`, in the working directory of the repository that imports this
package. It is the only configuration route: there are no `COWORK_*` environment variables.

```yaml
cowork:
  profile: <the Application Support profile directory name>   # required
  surface: cowork
  settle_seconds: 3
  session_timeout: 120
  idle_seconds: 20
  run_timeout: 1800
  max_runs: 50
  run_log: ~/.cowork-runs.jsonl
  log_dir: logs
```

| Rule                                                                                     |
| ------------------------------------------------------------------------------------------ |
| A missing file is not an error. Every field falls back to its default, and a missing `profile` is refused at the first call that fires |
| An unknown key inside `cowork:` is an error, so a typo is never a silent default          |
| An unknown top level section is ignored, so a later plan adds `docker:` without touching this loader |
| An override passed to the `CoWork` constructor or to `Config.load` beats the file, which beats the default |
| `~` in a path is expanded. A relative path resolves against the working directory          |

## Logging

Two files, and they are not the same thing.

| File                                          | Is                                                    | Lifetime            |
| ---------------------------------------------- | ------------------------------------------------------ | ------------------- |
| `<log_dir>/<yyyymmdd-hhmmss>-cowork_evals.log` | What the driver did: the link fired, the session found, the signal seen, the failure raised | One per firing call |
| `run_log`, `~/.cowork-runs.jsonl`              | One JSON line per submission. The rate ceiling counts it | Append only, forever |

The run log cannot be per-run, because the ceiling counts the submissions in the trailing 24
hours. It stays in the home directory, because the ceiling protects one CoWork account and
an account is not per-project.

The diagnostic log is written by `run` and `submit` only, through a handler on the
`cowork_evals` logger. The library never configures the root logger and never adds a handler
twice. `log_dir: null` turns the file off, and the logger then carries whatever handler the
caller attached.

## Where this plan overrides the documents

[`../docs/cowork_driver.md`](../docs/cowork_driver.md) calls itself the contract the driver
is built to. It is, for behaviour. On these six points it is stale, this plan wins, and
phase 8 rewrites that file. Read this table before reading it.

| That file says                                            | Build this instead                              |
| ----------------------------------------------------------- | ------------------------------------------------ |
| "standard library only, one module"                       | Three modules, and PyYAML                       |
| A `COWORK_*` environment variable per setting             | `cowork_evals.yaml`, and no environment variable |
| "The exit code is the failure taxonomy, on every command" | A raised `CoWorkError` carrying that code       |
| Three commands and a flag table under `python -m`         | Methods on `CoWork`. No command line at all     |
| `exit_code` in the session document                       | No `exit_code`, and a `log_file` key            |
| Every reading function takes a path argument              | Methods default to the configured path and accept an override |

[`../docs/library.md`](../docs/library.md) is stale in one place with the same cause: it
says `COWORK_*` is read from the environment and `.env`. Configuration is the YAML file.
`.env` keeps credentials, and this plan does not touch it.

## Decisions this plan settles

Phase 8 writes each of these into the document that owns it.

| Decision                                                                             | Recorded in             |
| -------------------------------------------------------------------------------------- | ----------------------- |
| The API above: a `CoWork` object holding the configuration, with seven methods         | `docs/cowork_driver.md` |
| The object is the only surface. No module level function, so a caller passes a configuration once | `docs/cowork_driver.md` |
| A failure raises and carries the taxonomy code. Exit codes belong to a command line, not to the library | `docs/cowork_driver.md` |
| Configuration is `cowork_evals.yaml`. The seven `COWORK_*` environment variables are dropped | `docs/cowork_driver.md`, `docs/library.md` |
| PyYAML is the first dependency of this package, and `dependencies` stops being empty  | `docs/library.md`       |
| A per-run diagnostic log, separate from the run log the ceiling counts                | `docs/cowork_driver.md` |
| `deep_link` is public and pure, which is what a dry run is built from later           | `docs/cowork_driver.md` |
| The session document drops `exit_code` and gains `log_file`                           | `docs/cowork_driver.md` |
| Three modules, not one: `config.py`, `prompt_lint.py`, `cowork.py`                    | `docs/cowork_driver.md` |
| `[tool.uv] package = false` is removed when `src/cowork_evals/` appears, not when `[project.scripts]` appears | `docs/library.md` |

Test fixtures are written by hand from the recorded record shapes, never copied from a
profile. That follows the public repository rule in [`../README.md`](../README.md): a session
directory copied off a live profile carries an account identifier, a profile identifier, a
session identifier and the prompts of a real account. Phase 8 writes it into
`tests/README.md`.

## Constraints

- Python 3.14, ruff `target-version = "py314"`. This package runs on a laptop and is bound by
  nothing about CoWork. [`../docs/library.md`](../docs/library.md).
- PyYAML is the only dependency this plan adds. Anything else needs a row in the dependency
  table in [`../docs/library.md`](../docs/library.md) and a reason.
- Nothing writes anywhere under the CoWork profile. The run log and the diagnostic log are
  the only files the library owns. [`../docs/cowork_driver.md`](../docs/cowork_driver.md).
- Importing a module reads no file, resolves no configuration and starts no process.
- No test starts a CoWork session. A test asserts over a fixture directory. The one live run
  is phase 7, and it is not a test.
  [`../tests/README.md`](../tests/README.md).
- Mocking and patching are not used. The `runner` parameter is the only seam.

## Phase 1: The package tree

- [x] Create `src/cowork_evals/__init__.py`, holding a docstring and nothing else.
- [x] Add `[build-system]` to `pyproject.toml`: `requires = ["hatchling"]`,
      `build-backend = "hatchling.build"`, and `[tool.hatch.build.targets.wheel]` with
      `packages = ["src/cowork_evals"]`.
- [x] Set `dependencies = ["PyYAML>=6"]`.
- [x] Remove `[tool.uv] package = false`.

`scripts/lint.sh` runs ruff over `.`, so it reaches `src/` with no change.

`scripts/init.sh`, then `scripts/test.sh` and `scripts/lint.sh` pass, and
`uv run python -c "import cowork_evals, yaml"` succeeds.

## Phase 2: Re-probe the desktop internals

The completion signal keys on the terminal `command_lifecycle` state, and
[`../docs/cowork_desktop.md`](../docs/cowork_desktop.md) records that this state was not
observed. Establish it, and the other shapes the phase 4 reader acts on, before writing that
reader. Everything here is read from session directories already on disk. Nothing is
submitted.

- [x] Record the terminal `command_lifecycle` state name, its keys, and whether it carries
      the final assistant text, the turn count and the cost.
- [x] Record whether a lifecycle record carries `command_uuid`, and whether one session
      directory holds more than one command.
- [x] Record whether `.claude/projects/session/` is present in every session directory.
- [x] Confirm that discovery by structure selects sessions and nothing else: a directory
      three levels below the sessions root holding `audit.jsonl`.
- [x] Write all of it into `docs/cowork_desktop.md` with the capture date, and extend that
      file's coupling list with every key phase 4 reads.

`docs/cowork_desktop.md` carries no row reading `not observed`, and every field the
phase 4 reader uses appears in its coupling list. Redact identifiers, per the public
repository rule.

If the terminal state cannot be established from the directories on disk, the library ships
with quiescence as its only signal, labelled a heuristic in the code, and
`docs/cowork_driver.md` records that the lifecycle path is unreachable. Both code paths stay
either way, because the fallback is needed when a run stalls before its terminal record.

## Phase 3: Configuration and the prompt linter

`src/cowork_evals/config.py` and `src/cowork_evals/prompt_lint.py`. Both are pure: they read
their own file or their argument, and nothing else.

- [x] `Config.load(path=None, **overrides)`: read `cowork_evals.yaml` with `yaml.safe_load`,
      apply the five rules in the configuration section above, and return a frozen `Config`.
- [x] Expand `~` and resolve a relative path against the working directory.
- [x] `sessions_root` derived from `profile`, as `docs/cowork_desktop.md` records it.
- [x] Split a prompt into sentences on `.`, `;`, `?`, `!` and newline.
- [x] Compile each linter rule's patterns once, case-insensitive, on word boundaries.
- [x] Exempt a sentence naming `outputs/`, `/sessions/`, `/tmp`, `TMPDIR` or `the session`.
- [x] Return the refusal reason naming the rule and the sentence, or `None`.
- [x] No flag, no argument and no configuration key that disables the linter.

`tests/test_config.py` passes: a missing file yields defaults, an unknown key inside
`cowork:` raises, an unknown top level section is ignored, an override beats the file, and
`~` is expanded. `tests/test_prompt_lint.py` passes: one refused prompt per rule, and every
exemption the design names, including `Reply with exactly: PONG`, `in order to` and
`Write the summary to outputs/summary.md`.

## Phase 4: Reading a session

The `CoWork` object, then `sessions` and `collect` and the private readers under them. The
rules are the reading rules in [`../docs/cowork_driver.md`](../docs/cowork_driver.md), and
the record shapes are `docs/cowork_desktop.md` as phase 2 leaves it.

- [x] `CoWork(config=None, *, runner=None, **overrides)` and `CoWork.from_file(path)`: hold
      the resolved configuration, expose it as `.config`, and validate nothing else.
- [x] Re-export `Config`, `CoWork` and `CoWorkError` from `__init__.py`, with `__all__`.
- [x] `sessions(root=None)`: every directory three levels below the root holding
      `audit.jsonl`, sorted. The root defaults to `config.sessions_root`.
- [x] Parse `audit.jsonl`, skipping an unparsable line.
- [x] Select the main transcript: the newest top level file by modification time under
      `.claude/projects/session/`. Record the rest separately, and record `subagents/*.jsonl`
      separately again.
- [x] Read `message.content` as either a string or a list of blocks.
- [x] Pair a `tool_result` to its `tool_use` by `tool_use_id`, and drop a result whose call
      is absent from this transcript.
- [x] Take `final_text` from the last assistant text turn. A run with none raises code 8.
- [x] List `outputs/` relative to the session directory.
- [x] `collect(session_dir, prompt=None)`: the session document, every key in the design's
      table except `exit_code`, plus `log_file`, and no other key. It needs no profile, so it
      reads an archived session on a machine that has no CoWork.
- [x] Tolerate a session directory with no transcript, which phase 2 establishes as possible.

`tests/test_cowork.py` passes over hand-written fixtures under `tests/data/cowork/`:
a one-turn session, a session with a tool call and its result, a session with a subagent
transcript, a session with a partial last line, a session with no assistant output, and a
session with no transcript directory. `json.dumps(CoWork().collect(fixture))` succeeds with
no profile configured, and the document carries exactly the documented keys.

## Phase 5: The run log, the rate ceiling and the diagnostic log

- [x] Append one line per submission to `run_log`, holding the timestamp, the prompt hash,
      the session directory and the outcome. Log a failed submission too.
- [x] `history(run_log=None)`: the run log as a list of dictionaries, oldest first.
- [x] Count the entries in the trailing 24 hours and raise code 2 at `max_runs`. The window
      is fixed. `collect` never checks it.
- [x] Raise code 2 for an unset or unreadable profile, for a prompt longer than 14336
      characters, and for a linted prompt, all before anything is fired.
- [x] Open `<log_dir>/<yyyymmdd-hhmmss>-cowork_evals.log` on the `cowork_evals` logger at the
      start of a firing call, create `log_dir` if absent, and close the handler when the call
      returns or raises. `log_dir: null` turns it off. The root logger is never touched.
- [x] Put the log path in the session document as `log_file`.

`tests/test_cowork.py` covers each refusal over a temporary run log and a temporary
profile: no profile, prompt too long, ceiling reached, a linted prompt. Each raises
`CoWorkError` with `.code == 2`. A failed submission leaves a line `history` reads back. Two
calls in one process leave two log files and no duplicated handler. `log_dir: null` writes no
file.

## Phase 6: Submit, wait and run

The four firing methods: `deep_link`, `submit`, `wait` and `run`. The nine steps and the code
each failure produces are the sequence table in [`../docs/cowork_driver.md`](../docs/cowork_driver.md).

- [x] `deep_link(prompt)`: percent-encode the prompt, and omit `surface` when it is empty.
- [x] Record the baseline set of session directories before firing.
- [x] Fire the link with `open` through `runner`, sleep `settle_seconds`, then send Return
      through `osascript`. A non-zero return raises code 3.
- [x] Poll for a session directory not in the baseline until `session_timeout`. None raises
      code 4. More than one raises code 5.
- [x] Keep polling for the `user` audit record after the directory appears, and compare its
      prompt with the submitted one. A mismatch raises code 6.
- [x] `wait`: block until the completion signal fires, on the terminal lifecycle state,
      falling back to quiescence. Count quiescence only after the run has started.
      `run_timeout` raises code 7.
- [x] `run`: `submit`, then `wait`, then `collect`, passing the submitted prompt through.
- [x] Every raise from `submit`, `wait` and `run` carries `session_dir` when one is known, and
      is written to the diagnostic log before it leaves the library.

`tests/test_cowork.py` passes against a `CoWork` built with a recording fake as
`runner`: `deep_link` encodes a prompt with spaces and newlines; the fake records the `open`
and `osascript` argument lists;
discovery returns the one new directory against a fixture baseline; two new directories raise
code 5; a mismatched audit prompt raises code 6; quiescence does not fire before the run has
started. Every taxonomy code except 3 and 7 is raised in a test.

## Phase 7: The live smoke run

One real submission, run by a person in their own terminal. That is the default because it
needs no Claude Code permission rule: the rules in
[`../docs/cowork_desktop.md`](../docs/cowork_desktop.md) exist only so an assistant may run
`open` and `osascript`, and an assistant cannot write them. An assistant runs this phase
instead only when `.claude/settings.local.json` already carries both rules.

What is required either way: the desktop application, the macOS Accessibility grant for the
terminal that owns the process, a signed-in CoWork, and `disableDeepLinkRegistration` unset.

- [x] Confirm the grant is in place and that `cowork_evals.yaml` names the active profile.
- [x] Build a `CoWork()` from `cowork_evals.yaml` and call `run()` with a read-only prompt
      that asks for one exact marker token back.
- [x] Confirm the returned document holds the marker in `final_text`, that `history()` reads
      back one new line, and that the library wrote nothing under the profile.
- [x] Confirm the diagnostic log names the fired link, the discovered session and the
      completion signal that fired.
- [x] Call `sessions()` and confirm it finds the new session.
- [x] Record the wall clock time of the run in `docs/cowork_desktop.md`.

The call returns the marker and raises nothing. A missing grant raises `CoWorkError`
with `.code == 3` and `osascript` error 1002 on stderr, and that blocks the phase rather than
skipping it. This run leaves one permanent session in the account history, and that is
expected.

## Phase 8: Documentation, and removal

Nothing durable may survive only in this file.

- [x] `docs/cowork_driver.md`: replace the `COWORK_*` configuration table with
      `cowork_evals.yaml`, add the API, state that the exit codes in that file are the
      taxonomy a `CoWorkError` carries rather than something the library returns, remove
      `exit_code` from the session document table and add `log_file`, and record the `CoWork`
      object, the three modules, the two log files and the completion signal as phase 2
      measured it.
- [x] `docs/library.md`: add PyYAML to the dependency table, correct the
      `[tool.uv] package = false` row, and correct the `.env` precedence text, which no longer
      covers `COWORK_*`.
- [x] `docs/running_evals.md`: split the status row `The CoWork driver and its backend` into
      two, and mark the driver built.
- [x] `README.md`: add `src/` and `cowork_evals.yaml` to the layout table.
- [x] `tests/README.md`: add a row per new test file, and the hand-written fixture rule.
- [x] Re-read every touched file for a statement this plan made false.
- [x] `plans/README.md`: correct the build order paragraph, which assigns the package
      skeleton to the CLI plan. This plan brings it.

`scripts/test.sh` and `scripts/lint.sh` pass. Nothing under `docs/` links to this
plan, and `plans/README.md` holds a row for it marked `implemented`.
