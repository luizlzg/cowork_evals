# cowork_evals

## Summary

The command. One executable, nine verbs, two backends. It is the whole surface a consumer
repository sees; the boundary behind it is [library.md](library.md).

- **The backend is required on every verb but `prune`, `panel`, `docs` and `init`** and has no
  default. Which backend proves what is [approaches.md](approaches.md).
- **The path is the scope.** One path argument decides whether a case, a skill, a plugin or a
  whole tree runs. There is no separate sweep command.
- **A verb names its object only when that object is not an eval.** `run` runs evals, which
  is what this command is. `test` runs pytest and `ask` submits one prompt, so both say so.
  `setup`, `check` and `prune` act on a backend and carry no object at all. `panel` renders
  both backend columns and reaches neither. `docs` and `init` act on neither: they read what
  the package ships and write into the working directory.
- **Options are named.** Nothing is forwarded raw to `claude plugin eval`. `test` is the one
  verb that takes a raw tail, because pytest is the only thing behind it.
- **`run` verifies and never builds.** A failed preflight exits 3 and names the command that
  fixes it.
- **The exit code is the CLI's.** No backend's code reaches an operator unchanged. `test` is
  the one exception, and it returns pytest's.

The venv backend has no flag on any verb. `--venv` is an unknown option and `argparse` exits
2. Its design stays in [staged_runtime.md](staged_runtime.md), and a plan that builds it adds
the flag.

What of this command is built is the status table in
[running_evals.md](running_evals.md).

## Synopsis

```
cowork_evals run   (--docker | --cowork) <path> [options]
cowork_evals ask   --cowork <prompt> [--timeout-seconds N] [--json] [--dry-run]
cowork_evals ask   --cowork --session <dir> [--json]
cowork_evals test  --docker <path> [--build-missing] [--dry-run] [-- PYTEST_ARGS]
cowork_evals setup --docker
cowork_evals check (--docker | --cowork | --all)
cowork_evals prune [--docker] [--logs] [--history] [--older-than DAYS] [--out DIR]
cowork_evals panel <path> [--markdown FILE] [--json FILE] [--removed]
cowork_evals docs  [<name>]
cowork_evals init
cowork_evals --version
```

`setup` takes `--docker` alone. It is the only backend with anything to build, and there is
no `setup --all`.

`ask` takes `--cowork` alone, exactly as `test` takes `--docker` alone. It reaches a live
session, and the container has none.

`prune`, `panel`, `docs` and `init` are the four verbs that take no backend. `prune` requires
at least one selection flag, and none is a usage error. `panel` renders a column for each
backend and reaches neither. `docs` and `init` take no backend because neither reaches one:
`docs` reads the shipped tree, and `init` writes files.

## The path is the scope

`run` takes one path. What that path points at decides what runs.

| Path points at                      | Runs                            | Scope name in the log directory |
| ----------------------------------- | ------------------------------- | ------------------------------- |
| a case directory                    | that case                       | `<plugin>-<skill>-<case>`       |
| `evals/<skill>/`                    | that skill's cases              | `<plugin>-<skill>`              |
| `evals/`                            | that plugin's whole suite       | `<plugin>`                      |
| a directory holding several plugins | each plugin in turn, decided once | `all`                           |
| anything else inside one root       | that plugin's whole suite       | `<plugin>`                      |

The last row is the plugin root itself, a `skills/` directory, and any other path inside one
root. The run is that plugin's, and the scope name says so.

The plugin root is the parent of `evals/`, and it is accepted only when it holds
`.claude-plugin/plugin.json`. A sweep finds plugins by that file with a sibling `evals/`, not
by a fixed glob, so a directory carrying a manifest and no `evals/` is not swept.

The plugin name in a scope name is `.claude-plugin/plugin.json`'s `name`, and the folder
basename when that file names none. Every character outside `[A-Za-z0-9._-]` becomes `-`. Two
plugins in one sweep whose manifests carry the same name get two directories, the second
suffixed `-2`, so neither result document overwrites the other and the verdict reads both.

A multi-plugin path is a usage error on `--cowork`. There is no sweep on that backend, for
the reason in [running_evals.md](running_evals.md).

A case's `plugins: ["../../.."]` frontmatter states the plugin root a second time. The case
validator checks that the two resolve to the same directory, because the harness reads the
frontmatter and the CoWork backend resolves the path. See
[eval_format.md](eval_format.md).

## Options on run

Named options only. No raw argument tail is forwarded to `claude plugin eval`: that harness
runs on one backend of two, so a pass-through would be silently ignored on the other.

| Option                   | `--docker` | `--cowork`                             |
| ------------------------ | ---------- | -------------------------------------- |
| `--runs N`               | yes        | yes, replacing each case's own         |
| `--timeout-seconds N`    | refused    | yes, as each run's `run_timeout`       |
| `--model M`              | yes        | refused, the session decides           |
| `--judge-model M`        | yes        | yes, for judged graders                |
| `--allow-tools T...`     | yes        | refused, the session decides           |
| `--max-cost-usd N`       | yes        | refused, the driver's `max_runs` binds |
| `--ablation MODE`        | yes        | refused, that backend runs one arm     |
| `--delta-threshold N`    | yes        | refused, there is no delta to decide on |
| `--keep-traces`          | yes        | yes                                    |
| `--tag T`, `--case GLOB` | yes        | yes                                    |
| `--out DIR`              | yes        | yes                                    |
| `--require-coverage`     | yes        | yes                                    |
| `--build-missing`        | yes        | refused, nothing to build              |
| `--dry-run`              | yes        | yes                                    |

`--timeout-seconds N` is refused on the Docker backend because `claude plugin eval` has no
timeout flag to map it onto. Only the CoWork backend sets a per-case `run_timeout` itself.

`--require-coverage` reads the tree and not a backend, so no backend refuses it. It is off by
default.

`--ablation with-without` runs every case a second time with no plugin loaded, and the verdict
then decides each case on the delta between the two scores rather than on the with-arm score
alone. `--delta-threshold N` is what that delta has to reach, and a case below it fails. Both
default to the `eval:` section, `none` and `0`. The arm is off by default because it runs
every case twice and so costs twice as much, and because it stops scoring the one grader that
says the skill fired at all. What the arm changes about pass and fail is
[running_evals.md](running_evals.md).

Both are refused on `--cowork`. A session gets its skills from the profile the desktop
application is running, and nothing here chooses which profile that is, so there is no
baseline arm on that backend and no delta to decide on. See
[cowork_backend.md](cowork_backend.md).

`--keep-traces` is on by default and `--no-keep-traces` turns it off, which is what puts each
run's transcript, final assistant message and workspace under the run's log directory. Both
backends honour it and both leave the same three names, so no backend refuses it. What is
kept, where it is read from and what is thrown away is
[running_evals.md](running_evals.md). It is the one option of the three states: untyped is the
file's value, and both `--keep-traces` and `--no-keep-traces` beat the file. `False` is a
value an operator typed and not a default, which is why the refusal table cannot read it as
untyped and why the option carries both forms.

`--no-keep-traces` also gives up two pass and fail conditions. A run that was refused a tool by
the permission mode, and a run that was never offered a tool the grant named, are both read out
of the kept trace, so with no trace neither is found and neither fails. The suite then scores a
run that could not have passed and says nothing about it. Both conditions are
[running_evals.md](running_evals.md).

`--out DIR` replaces the whole `logs/evals` root, so the run directory is
`<out>/<stamp>-<scope>`. It is accepted on `prune` too, which otherwise resolves
`<cwd>/logs/evals`. `--older-than DAYS` is a `prune` flag only: `run` prunes at a fixed 30
days.

Defaults come from the `eval:` section of `cowork_evals.yaml`, in
[running_evals.md](running_evals.md), which also says which underlying flag each option maps
to and why that flag is pinned. An option beats the file, and the file beats the built-in
default; the ladder is [library.md](library.md). One pinned flag has no option:
`--threshold`, because this package decides. `eval.max_cost_total_usd` has no option either,
because it bounds the invocation rather than a run. `--delta-threshold` is the other way
round: it is an option over a setting that maps to no harness flag at all, because the
verdict reads it here.

An option the chosen backend cannot honour is refused at parse time. That is an operator
mistake, so it is a usage error. A *case* that needs a field the backend cannot honour says so
with a tag, is not submitted there and is counted. The two are different and are never
conflated. The tag is [eval_format.md](eval_format.md).

An option whose value its setting refuses is a usage error too, and it is refused before the
configuration file is read, so `--delta-threshold 5` exits 2 whatever the file says. The check
is the setting's, not the option's, which is why the two rungs cannot disagree:
[library.md](library.md). The message names the option rather than the key.

`--dry-run` exits 0 without running anything and without creating a run directory. What it
prints differs per backend, because only one of them builds a command line.

| Backend    | Prints                                                                        |
| ---------- | ------------------------------------------------------------------------------- |
| `--docker` | the `docker run` command line, one argument per line, `--keep-temp` and the `TMPDIR` behind it included |
| `--cowork` | one line per case with its run count, its timeout, what it declares and its grader skips, then the rate ceiling arithmetic |

What each case declares is the point of the CoWork dry run: a declared case submits nothing, so
an operator reads which ones before spending. Pruning of old run directories happens before the
exit, so an unattended dry run still reclaims space. The tests assert over both, so the option surface,
the backend mapping and the target's position ahead of the variadic flags are covered without
a live run.

## Preflight

`run` verifies its backend and never builds. An eval run already costs minutes and money, and
a run that silently spends ten more building an image is not readable in a log.

| Backend    | Requires                                                             | Fails when                                                  |
| ---------- | -------------------------------------------------------------------- | ----------------------------------------------------------- |
| `--docker` | a Docker or Rancher daemon, the image at the current digest, the container login, and every name in `docker.env_passthrough` set on the host | the daemon is down, the image is absent or stale, there is no login, a forwarded name is unset or empty, or one of them would carry Claude's own credential |
| `--cowork` | macOS, `claude` on `PATH`, a `cowork_evals.yaml` naming a profile, a readable sessions root under it, an Accessibility grant, and the suite inside the driver's `max_runs` | the grant is missing, so there is no headless route and no CI, or `claude` is absent, or no profile is configured, or the suite would exceed the ceiling |
| `test`     | a Docker or Rancher daemon, the eval image, and the test image over it        | the daemon is down, or either image is absent or stale |

A forwarded name that is unset or empty on the host is an unmet condition, one line per
name, because an empty string is not a value. A name that would carry Claude's own credential
is refused whatever it holds, and the line names the container login as the one route. Every
line names the variable and never its value. See [docker.md](docker.md).

The desktop application itself is not probed. What the backend reads is the profile directory
the application writes sessions into, and an unreadable one is the condition that matters. See
[cowork_desktop.md](cowork_desktop.md).

`test` has a preflight of its own because it starts a container. It never reads the container
login: there is no model call in that path. It is not a backend, and the row is here because
it is selected the way one is. See [cowork_test.md](cowork_test.md).

`ask` verifies the `--cowork` row, minus the rate ceiling, which is the driver's and is
checked inside it. `ask --session` verifies nothing: it reads a directory already on disk.

### Taking the keyboard

A CoWork submission types into the frontmost application, so `run --cowork` and
`ask --cowork` each ask for the keyboard once per invocation, in a modal that forces itself
in front of whatever you are working in. `run` asks once before the first plugin, whatever
the suite holds, and `ask` asks once before its one submission. Cancel refuses, and nothing
has fired at that point: the sweep fails the run and exits 1, and `ask` exits 3.

`--dry-run` never asks, because nothing would be submitted, and neither does `ask --session`,
which reads a directory.

`cowork.consent: none` in the configuration file fires without asking, which is the route for
an unattended run. `cowork.consent_timeout` is how long the modal waits before going ahead on
its own. Both keys, and the guard that refuses to type when CoWork is not frontmost, are in
[cowork_driver.md](cowork_driver.md).

A failed preflight exits 3 and prints one line naming the command that fixes it:

```
image cowork-evals:<digest> is absent: run cowork_evals setup --docker
```

`--build-missing` builds the container image instead of failing. It is off by default and
exists for unattended use. A missing container login still fails the preflight, because that
login is interactive. On `test` it builds the test image, and the eval image first when that
is absent too.

`run` also refuses three things a backend cannot report. Each happens before anything is
created and before anything is deleted, so exit 2 and exit 3 leave the log root untouched.

| Refusal                                                    | Exits |
| ---------------------------------------------------------- | ----- |
| A case that violates the format, in any selected plugin root | 3   |
| An uncovered skill, under `--require-coverage`             | 3     |
| A selection that matches no case at all                    | 2     |

`run` validates every selected plugin root, not only the target, so a malformed sibling case
blocks a single-case run. There is no option to skip validation. The rules are
[eval_format.md](eval_format.md).

A skill under `skills/` with no directory of that name under `evals/` is always reported.
`--require-coverage` turns that report into a preflight failure. Coverage is not a rule of the
format, which is why it is a flag and not a violation.

A selection matching no case at all is an operator mistake: a mistyped `--tag` must not read
as a pass, and the refusal catches it before a container starts. One plugin of a sweep
matching none is normal under `--tag` and is not a failure.

### A case cannot be left out of one invocation

`--case GLOB` takes one glob over the case name, with `*` and `?`. There is no negation and
no list. `--tag T` only includes, and repeating it widens the selection. Neither can leave one
case out: the options say which cases to keep, never which to drop. The flags behind them are
`claude plugin eval --case` and `--tag`, in
[claude_code/plugin_eval_reference.md](claude_code/plugin_eval_reference.md), and on the
container backend the harness finds and picks the cases itself, so there is nothing here to
filter after it.

No option is added for it. Excluding a case would mean invoking the harness once per case,
which writes one result document per case, and both the log layout and the pass and fail
rules in [running_evals.md](running_evals.md) read one document per plugin.

What works is a tag on the case. Put one in the case's frontmatter, name it in `--tag`, and
the set is the cases carrying it. A case to be left out of the usual sweep carries a tag the
usual sweep does not name. The frontmatter key is [eval_format.md](eval_format.md).

What the invocation selected is printed rather than inferred. The verdict's last line carries
how many cases the path holds, how many the filters kept, how many ran and how many passed.
[running_evals.md](running_evals.md) says what each of the four means.

The order is preflight, then validation, then the selection count, then pruning, then the
`--dry-run` exit.

`--dry-run` skips the preflight and keeps everything after it. Nothing behind the preflight
is reached by a dry run: the image tag is a hash of local files, the container argument list
is built without asking the daemon, and the `--cowork` plan reads the case tree and the
configuration. A dry run therefore validates a case on a machine with no daemon, no image, no
credential and no profile, and a malformed case still exits 3. The ceiling belongs to the
preflight, and a dry run on `--cowork` prints the same arithmetic instead of refusing on it.

That is what makes `run --dry-run` the way to check a case without spending anything. There
is no separate validate verb.

A dry run exits 0 on both backends once the preflight it skips and the validation it keeps are
past. A suite whose every case declares `no-cowork` plans no submission and is a pass, because
a declared case is counted rather than failed, and a real run of it would exit 0 as well. An
empty selection is a different thing and is refused earlier, with exit 2. A malformed case,
the missing tag and the unneeded tag included, is exit 3.

`claude` is a `--cowork` precondition because the judge behind an `llm` or `baseline` grader
is `claude -p`, and because `claudeVersion` in the result document is the host
`claude --version`. The signed-in CLI is the one credential route; there is no second one.

Host spend on `--cowork` is the judge alone. The CoWork session itself is billed to the
signed-in account and is not observable from the host, so `--max-cost-usd` is refused there
and the ceiling that binds is the driver's `max_runs`. See
[cowork_driver.md](cowork_driver.md).

## ask

`ask` submits one prompt to a real CoWork session, waits, and prints the answer. It runs no
eval: no case tree, no grader, no result document, no verdict and no run directory. It is how a
question about what a live session actually does is answered by asking one.

| Option               | Is                                                                 |
| -------------------- | -------------------------------------------------------------------- |
| `--cowork`           | the only backend. There is no `ask --docker`                       |
| `<prompt>`           | the prompt. `-` reads it from standard input                       |
| `--session <dir>`    | print a session already on disk. Submits nothing, costs nothing    |
| `--timeout-seconds N`| this run's timeout, replacing `cowork.run_timeout`                 |
| `--json`             | print the session document instead of the text                     |
| `--dry-run`          | print the deep link and the ceiling arithmetic. Submits nothing    |

It takes no other option. Every option it does not carry configures a suite, and `ask` runs
no suite: no `--runs`, no `--tag`, no `--case`, no `--out` and no `--require-coverage`.

`--json` here is this verb's output form. It is unrelated to the harness flag of the same
name, which [plugin_eval.md](plugin_eval.md) records as never emitted.

### What is printed, and where

| Form        | Standard output          | Standard error                                            |
| ----------- | ------------------------ | ----------------------------------------------------------- |
| default     | the final assistant text | session directory, assistant turn count, tool names, outputs, driver log |
| `--json`    | the session document     | nothing                                                   |
| `--dry-run` | the deep link            | the ceiling arithmetic                                    |

The split is so that `cowork_evals ask --cowork "..." > answer.txt` holds the answer and
nothing else. A footer line whose value is empty is not printed: a session that called no
tool has no `tools` line. `--json` prints no footer, because every footer value is a field of
the document it printed.

The session document is the driver's, field by field in
[cowork_driver.md](cowork_driver.md).

### What it writes

Nothing on the host. No run directory, no `latest`, no `env.txt` and no pruning; `test` is
the precedent. The session directory in the profile is the permanent record, and the driver's
run log is the driver's. The verb never saves the session document: printing it is what it is
for.

### The ceiling

The rate ceiling is the driver's `cowork.max_runs`, checked in `CoWork` before the submission
and counted from the run log. There is no second ceiling in this verb, because one number
gets one source. `--dry-run` prints the arithmetic instead of spending against it.

### Usage errors

Each returns 2, from the verb rather than from `argparse`, with a message naming what was
typed.

| Typed                                | Refused because                      |
| ------------------------------------ | ------------------------------------ |
| neither a prompt nor `--session`     | there is nothing to print            |
| a prompt and `--session` together    | the session is either new or on disk |
| `--timeout-seconds` with `--session` | nothing waits                        |
| `--dry-run` with `--session`         | nothing would be submitted           |

### Preflight

The CoWork row of the preflight table above, minus the rate ceiling, which is the driver's.

`--session` skips the preflight entirely. It reads a directory, so it needs no macOS, no
profile and no Accessibility grant, and it runs against an archived session on a machine that
has no CoWork.

`--dry-run` skips it too, for the reason `run --dry-run` does: nothing behind the preflight is
reached. The deep link is built from the prompt and the ceiling arithmetic is read from the
run log, so a dry run checks a prompt on a machine with no CoWork at all.

A submission asks for the keyboard once, after the preflight, in the modal
[Taking the keyboard](#taking-the-keyboard) describes. Cancel exits 3 and fires nothing.

### Exit codes

| Code | Means                                                              |
| ---- | -------------------------------------------------------------------- |
| 0    | a session document was printed                                     |
| 2    | a usage error above                                                |
| 3    | the CoWork preflight is unmet, or the driver raised code 2         |
| 1    | everything else the driver raised. No session document was printed |
| 130  | interrupted                                                        |

Driver code 2 is configuration or the rate ceiling, which is the preflight class, so it maps
to 3 and matches what `run --cowork` does with the same code.

Code 7 is a run timeout and carries a session directory. The session keeps running in the VM,
so the verb collects that directory, prints what the session produced, and still exits 1.
That is what the CoWork backend already does with a timeout. See
[cowork_backend.md](cowork_backend.md).

## test

`test` runs a consumer's pytest suite inside the CoWork image. No model, no harness, no case
tree, no grader, no result document and no verdict. The mechanism is
[cowork_test.md](cowork_test.md), and it is not restated here.

| Option            | Is                                                                  |
| ----------------- | --------------------------------------------------------------------- |
| `--docker`        | the only backend. There is no `test --cowork`                       |
| `<path>`          | a path inside one plugin root. A path covering several is a usage error, because pytest takes one rootdir |
| `--build-missing` | build the test image, and the eval image first when that is absent too |
| `--dry-run`       | print the container argument list, one argument per line, and return 0 |
| `-- PYTEST_ARGS`  | the pytest tail                                                     |

It takes no other option. Every option it does not carry configures a harness run, and `test`
runs no harness.

The pytest tail begins at `--`. Every token after it reaches pytest in order and unmodified,
and this command claims none of them: `-- --dry-run` is pytest's argument and never this
verb's. A raw tail is forbidden on `run`, because the harness runs on two backends and a
pass-through would be silently ignored on the other. It is allowed here because pytest is the
only thing behind this verb.

`test` creates nothing on the host: no run directory, no `env.txt`, no `latest`, no pruning
and no verdict. Those five exist for `aggregate-result.json`, which pytest does not produce. It
validates no case and reads no `evals/` either, so a malformed case never blocks a test run.

`test --dry-run` prints before the preflight, unlike `run --dry-run`, which prunes the log
root and so must not act behind a failed one. A dry run here does nothing at all beyond
printing, so there is nothing for a preflight to guard.

## setup

| Command          | Builds                                                                                                     | Idempotent                   |
| ---------------- | ------------------------------------------------------------------------------------------------------------ | ---------------------------- |
| `setup --docker` | `cowork-evals:<digest>`, then `cowork-evals-test:<digest>` over it, then the container login if one is needed | prints `current` and exits 0 |

`setup --docker` builds two images. Each run gets a fresh container from one of them, so there
is no long-lived container to create. When no container login exists, it then starts one
interactive container to log in. That step needs a terminal and a browser. See
[docker.md](docker.md) and [cowork_test.md](cowork_test.md).

There is no `setup --cowork`. The desktop application and the Accessibility grant are
installed and granted by hand, and `check --cowork` reports what is missing.

Where each artefact lives, and how the digest is computed, is [library.md](library.md).

## check

`check` verifies the same conditions as the preflight table above, writes nothing, and never
builds. It exits 0 when every named backend is ready and 3 otherwise, listing each unmet
condition and its fix. The backend is required, so `check` with none is a usage error.

`check --docker` reports both images and the container login. The login is unmet for `run` and
is not read by `test`'s preflight, and `check` reports the condition either way.

`check --all` covers `--docker` and `--cowork`, so it reports the Accessibility grant on a
machine that has no CoWork installed rather than failing the whole invocation. It returns 0 on
a machine where both are ready.

The two forms print differently, and the split is which of the two the output is.

| Form                              | Prints                                                   | Stream |
| --------------------------------- | -------------------------------------------------------- | ------ |
| `--docker`, `--cowork`            | `ready`, or the unmet lines alone                        | stdout, then stderr for the lines |
| `--all`                           | one section per backend, each named, then `ready` or its indented unmet lines | stdout |

A named backend is a refusal: the operator asked about that one, and an unmet condition is
what stops them. `--all` is a report, so a ready backend is stated rather than silent, every
line says which backend it belongs to, and the whole thing goes to one stream in backend
order.

```
$ cowork_evals check --all
docker: ready
cowork: not ready
  no CoWork profile configured: set cowork.profile in cowork_evals.yaml
```

The exit code does not change with the form: 0 when nothing is unmet, 3 otherwise.

`check` never reads the rate ceiling. That condition needs a target and `check` takes none, so
it is `run`'s alone.

## prune

Deletes artefacts this CLI created and nothing else.

| Flag                | Deletes                                                                             |
| ------------------- | ------------------------------------------------------------------------------------- |
| `--docker`          | images tagged `cowork-evals:*` and `cowork-evals-test:*`, except the current digest of each |
| `--logs`            | run directories under the resolved log root                                         |
| `--history`         | records under `panel.root`, and a file and a directory each leaves empty             |
| `--older-than DAYS` | restricts every selection above. Default 30                                         |
| `--out DIR`         | the log root `--logs` resolves, replacing `<cwd>/logs/evals`                        |

`--out` does not reach `--history`. That option names the log root, and the history root is
`panel.root`, which `--out` does not move. See [panel.md](panel.md).

At least one selection flag is required. `prune` with none is a usage error. The two are not
exclusive: pruning images and logs in one invocation is ordinary.

An image is selected by its creation date and a run directory by the stamp in its name, never
by a modification time, which a later read moves.

`run` prunes log directories older than 30 days on its own, so `prune --logs` is for
reclaiming space on purpose. `prune --docker` leaves the container login alone: it is a
credential, not a build product, and deleting it forces an interactive login.

## panel

`panel` prints what state the evals under a path are in, from records earlier runs left. It
reaches no backend, spends nothing and writes nothing under the history root.

```
cowork_evals panel plugins/mail                 # every case, and its latest result
cowork_evals panel plugins/mail --markdown p.md # the same rows, as a Markdown table
```

| Option            | Is                                                                     |
| ----------------- | ------------------------------------------------------------------------ |
| `<path>`          | the scope, resolved exactly as `run` resolves it                       |
| `--markdown FILE` | write the same rows as a Markdown table                                |
| `--json FILE`     | write the same rows as a JSON snapshot                                 |
| `--removed`       | add a row for history whose case is no longer in the tree              |

Both file options may be given at once, and both carry the rows the table carries.

There is no `--tag` and no `--case`. The path is the only selector, because the verb exists to
show what has never run and a filter hides exactly those rows.

There is no backend flag: the output carries a column for each backend and reaches neither.
There is no exit code that means the panel is red either. `run` already exits on the verdict,
and a second code deciding the same thing from older data would disagree with it.

| Condition                                | Exit |
| ---------------------------------------- | ---- |
| rows printed                             | 0    |
| a history line that does not parse       | 0, and the line named on stderr |
| a path selecting no case                 | 2    |
| a path with no plugin root at or above it | 2   |

The history, the record, the digest and the columns are [panel.md](panel.md).

## docs

`docs` prints where the documentation this package ships landed. It reads the filesystem,
writes nothing, needs no configuration and reaches no backend.

```
cowork_evals docs            # the directory, then every document name
cowork_evals docs cli        # the path of one document
cowork_evals docs cli.md     # the same document. The extension is optional
```

With no argument the first line is the directory holding the tree and every line after it is
a document name. With a name it prints one absolute path and nothing else, which is what
makes it usable from a script and from an agent that will then read the file.

A name is the path inside the tree without the extension, so a nested document is
`claude_code/plugin_eval_reference`. Two directories hold a `README.md`, so a bare basename
would not identify one.

The tree carries one worked example as a real plugin, at `claude_code/eval_smoke/`. Its
`prompt.md` and its graders are cases, not documents, so they are not listed. They still
ship, and `docs claude_code/README` says what they are.

| Condition                            | Prints                                     | Exit |
| ------------------------------------ | ------------------------------------------ | ---- |
| no argument                          | the directory, then every name             | 0    |
| a known name                         | one absolute path                          | 0    |
| an unknown name                      | the refusal, then every name, on stderr    | 2    |
| a package built without the tree     | one line saying so, on stderr              | 3    |

Where the tree sits differs between an install and a checkout, which is why a document is
found through this verb rather than by a relative path. That rule, and the two reference
rules that follow from it, are in [library.md](library.md).

## init

`init` writes what a consumer repository needs to use this command, into the working
directory. It takes no backend and no option.

| Target                                  | Is                                                          |
| --------------------------------------- | ----------------------------------------------------------- |
| `cowork_evals.yaml`                     | Every key and every default, and a placeholder for `cowork.profile` |
| `.claude/skills/cowork-evals/SKILL.md`  | The eval-authoring skill: the tree, the keys, the graders, the traps |
| `.claude/skills/cowork-ask/SKILL.md`    | The ask skill: when to ask a live session, what it costs, what counts as evidence |
| `CLAUDE.md`                             | A block naming the command, the `docs` verb and the runtime constraint |

The skills are whatever the package ships, one directory each under
`src/cowork_evals/data/skills/`, installed at `.claude/skills/<directory name>/SKILL.md`.
Which skill fires on what, and why they are two files and not one, is
[library.md](library.md).

It never overwrites. A target that exists is reported as kept and is left exactly as it is,
so a second run changes nothing and a consumer's own edits survive. `CLAUDE.md` is appended
to when it exists and does not carry the block, and created when it is absent; the block's
own heading is the marker, so an edited block is recognised and never appended twice.

Regenerating a target means deleting it first. That is the operator's act, and there is no
option here that overwrites a file.

### Upgrading the package does not refresh what init wrote

`init` overwrites nothing, so a target written by an older version stays as it is. The skills
are where that matters: the eval-authoring one carries the case format, and a stale copy
teaches an out-of-date one to every session that reads it. Nothing detects the drift and
nothing warns about it.

After upgrading `cowork-evals`, take the new skills:

```sh
rm -r .claude/skills/cowork-evals .claude/skills/cowork-ask
cowork_evals init
```

The other two targets hold a consumer's own values, so leaving them alone is right.
`cowork_evals.yaml` gains a key only when a release adds one, and every key has a built-in
default, so an old file keeps working. The `CLAUDE.md` block is prose a consumer edits.

A skill is a copy and not a link, so deleting it is the only way it changes. That is
deliberate: a consumer edits the file after `init` writes it, and a refresh that overwrote
would destroy those edits without asking.

| Condition                                | Prints                                 | Exit |
| ---------------------------------------- | -------------------------------------- | ---- |
| a target was written                     | one `wrote` line per target            | 0    |
| every target was already there           | one `kept` line per target, then a summary | 0    |
| a source is missing from the installation | one line saying so, on stderr          | 3    |

`cowork_evals.yaml` names a profile, which is an identifier. Add it to the repository's
ignore list. See [library.md](library.md).

## Exit codes

| Code | Means                                                                       |
| ---- | --------------------------------------------------------------------------- |
| 0    | the run passed, or the verb succeeded                                      |
| 1    | the run failed, or the driver raised on `ask`. The conditions are in [running_evals.md](running_evals.md) |
| 2    | usage error: unknown option, an option the backend refuses, a value its setting refuses, or no path |
| 3    | preflight failed. Nothing ran and nothing was written                       |
| 130  | interrupted                                                                 |

Code 1 is one code because it is one thing to an operator: the verb reached its backend and
the work did not succeed. `run` and `ask` are the two verbs that can return it.

The exit code is the CLI's, and no backend's code reaches an operator unchanged. `test` is the
one exception: once the container starts it returns pytest's code, unchanged and
uninterpreted, and [cowork_test.md](cowork_test.md) lists those. Every code in the table above
is still reachable on that verb before the container starts, on a parse failure or a failed
preflight.

Exit 3 means nothing ran and nothing was written on every path. The CoWork rate ceiling is
checked in the preflight, and pruning happens behind every refusal, so neither breaks that.

`claude plugin eval` exits 2 on partial results; the Docker backend turns that into a
`partial: true` result document, and that becomes exit 1. See
[plugin_eval.md](plugin_eval.md).

The CoWork driver has its own taxonomy, codes 2 to 9, carried by a raised `CoWorkError` and
never by an exit code. It is in [cowork_driver.md](cowork_driver.md). The `--cowork` backend
maps it:

| Driver code                              | Becomes                                                            |
| ---------------------------------------- | ------------------------------------------------------------------ |
| 2, for configuration or the rate ceiling | Checked in preflight, before any case: exit 3                      |
| 2 to 8, raised while running a case      | That case is an error in the result document, and the run exits 1 |
| No raise                                 | The case is graded normally                                        |
