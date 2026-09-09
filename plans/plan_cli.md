# Plan: the command

Branch `feat/cli`. Eight phases, one commit each.

This plan assembles what the backend plans built and rebuilds none of it. The contract it
holds them to is [`README.md`](README.md): a backend takes a case path and an output
directory and returns the path to the `aggregate-result.json` it produced.

## What it waits on

`plan_cowork_backend.md` and `plan_test.md`. This plan is executed after both are merged,
and it is the last plan for that reason.

`plan_cowork_backend.md` builds `cases.py`, which this plan's validator reads, and
`cowork_backend.py`, which `run --cowork` calls.

It calls two functions on that backend and nothing else:

```
cowork_backend.run(target, output_dir, *, config=None, runs=None, timeout_seconds=None,
                   judge_model=None, tags=(), case_glob=None) -> Path
cowork_backend.plan(target, *, config=None, runs=None, timeout_seconds=None,
                    judge_model=None, tags=(), case_glob=None) -> Plan
```

`judge_model` is the one parameter with no fallback: `judge.py` otherwise reads
`eval.judge_model`, so the parameter is the only route `--judge-model M` has on `--cowork`.

That plan also corrects [`../docs/cli.md`](../docs/cli.md) to accept `--runs N` and
`--timeout-seconds N` on `--cowork`, and adds `claude` on `PATH` to the `--cowork` preflight
row. This plan reads the file as it then stands and does not redo either.

[`plan_test.md`](plan_test.md). It builds `PytestImage`, which the `test` verb calls, and
the second container image behind it. That plan builds no verb: a fifth verb is a parser
entry and a dispatch, and both are this plan's. It calls two methods on it and nothing
else:

```
PytestImage.check() -> list[tuple[Condition, str]]
PytestImage.run(target, *, pytest_args=()) -> int
```

`run` returns pytest's exit code unchanged, which is the one place a code from below
reaches an operator. That is the verb's whole contract, and it is
[`../docs/cowork_test.md`](../docs/cowork_test.md).

Configuration is `cowork_evals.yaml`, read through `Config` and `RunOptions.resolve`. This
plan defines no setting and reads nothing from the process environment.

## Two backends, not three

The venv backend is not built and no plan builds it. This command therefore carries no
`--venv` flag on any verb: `--venv` is an unknown option and `argparse` exits 2. The
backends are `--docker` and `--cowork`.

Its design is not removed. [`../docs/staged_runtime.md`](../docs/staged_runtime.md) and
[`../docs/environments.md`](../docs/environments.md) keep it, and
[`../plans/README.md`](README.md) keeps plan 3 skipped. When a plan builds it, that plan adds
the flag. Phase 8 removes every statement that offers it today.

## Scope

The layer above every backend: the option surface, the preflight, the run directory, the
gate, and the process a consumer invokes.

| Builds                                | Is                                                                |
| ------------------------------------- | ------------------------------------------------------------------- |
| `src/cowork_evals/validate.py`        | The case validator and the skill coverage report, over `cases.py` |
| `src/cowork_evals/logs.py`            | Scope naming, the run directory, `env.txt`, `latest`, pruning, the tee |
| `src/cowork_evals/gate.py`            | The gate over `aggregate-result.json`, and `gate.txt`             |
| `src/cowork_evals/preflight.py`       | The unmet conditions of each backend, for `check` and for `run`   |
| `src/cowork_evals/cli.py`             | The parser, the five verbs, the dispatch and the exit codes       |
| `src/cowork_evals/docker/__init__.py` | `images()` and `remove_image()` for `prune --docker`, and `remedy()` naming the command |
| `[project.scripts]`                   | The `cowork_evals` executable                                     |
| `tests/unit/test_validate.py`, `tests/unit/test_logs.py`, `tests/unit/test_gate.py`, `tests/unit/test_preflight.py`, `tests/unit/test_cli.py`, `tests/unit/test_docker.py`, `tests/integration/test_cli.py` | [`../tests/README.md`](../tests/README.md) |

References: the surface is [`../docs/cli.md`](../docs/cli.md), the log layout and the gate
are [`../docs/running_evals.md`](../docs/running_evals.md), the settings ladder is
[`../docs/library.md`](../docs/library.md), and the rules the validator enforces are
[`../docs/eval_format.md`](../docs/eval_format.md).

## Out of scope

| Not built                                                      | Belongs to              |
| ---------------------------------------------------------------- | ------------------------ |
| The venv backend, its flag, the mirror build and the staged runtime | a plan that builds it |
| A second entry point, or a per-backend executable               | nobody. [`../CLAUDE.md`](../CLAUDE.md) |
| `report.html` on the CoWork backend                             | nobody                  |
| The 3.10 and import check over the code under test              | nowhere yet             |
| A hook, a CI job, a cadence                                     | the consumer repository |
| Any eval over a shipped plugin, and any suite                   | the consumer repository |

## Decisions

Each row is a statement [`../docs/cli.md`](../docs/cli.md) does not yet make. Phase 8 writes
every one of them into that file.

| Decision                                                                                   | Settled by      |
| --------------------------------------------------------------------------------------------- | --------------- |
| The venv backend has no flag on any verb. `--venv` is an unknown option, exit 2             | the developer   |
| A case that violates the format fails inside `run`'s preflight, with exit 3                | the developer   |
| A selection that matches no case at all is a usage error, exit 2, refused before anything is created. One plugin of a sweep matching none is normal under `--tag` and is not a failure | the developer |
| A skill under `skills/` with no directory under `evals/` is always reported. `--require-coverage` turns it into a preflight failure, exit 3 | the developer |
| `--out DIR` replaces the whole `logs/evals` root, so the run directory is `<out>/<stamp>-<scope>`. It is accepted on `prune` too, which otherwise resolves `<cwd>/logs/evals` | this plan |
| `--dry-run --cowork` prints the cases it would submit rather than a command line, because that backend builds none | this plan |
| `run` order is preflight, then validate, then the selection count, then prune, then the `--dry-run` exit, so exit 2 and exit 3 leave the log root untouched | this plan |
| `prune` with no selection flag is a usage error, exit 2                                    | this plan       |
| `test` returns pytest's exit code unchanged once the container starts. It is the one verb whose code is not this command's, and the exit table gains that exception | the developer |
| `test` carries `--docker`, a path, `--build-missing`, `--dry-run` and a pytest tail, and no other option. Every option it does not carry configures a harness run, and `test` runs no harness | this plan |
| The pytest tail begins at `--`. Every token after it reaches pytest in order and unmodified, and `argparse` claims none of them | this plan |
| A raw tail is forbidden on `run` because the harness runs on two backends, and allowed on `test` because pytest is the only thing behind it | this plan |
| `test` creates nothing on the host: no run directory, no `env.txt`, no `latest`, no pruning and no gate. It produces no `aggregate-result.json`, which is what all five exist for | this plan |
| `test` validates no case and reads no `evals/`. A malformed case never blocks a test run | this plan |
| A path covering several plugin roots is a usage error on `test`, exit 2. pytest takes one rootdir | this plan |
| `test`'s preflight is the daemon and the test image, and never the container login. There is no model call in that path | this plan |
| The backend is required on every verb except `prune`, so `check` with no backend is exit 2 | this plan       |
| `setup` takes `--docker` alone. It is the only backend with anything to build              | this plan       |
| `check --all` covers `--docker` and `--cowork`, and returns 0 on a ready machine           | this plan       |
| Any `partial: true` fails the gate, whatever the reason                                    | this plan       |
| A grader result carrying `scored: false` is a skip and fails the gate, because `--ablation none` drops nothing | this plan |
| A run carrying `error` fails the gate on every backend, not only on CoWork                 | this plan       |
| A sweep stopped by the total cost ceiling fails the gate, exit 1                           | this plan       |
| `--older-than` is a `prune` flag only. `run` prunes at a fixed 30 days                     | this plan       |
| `--build-missing` builds the container image. A missing container login still fails preflight, because that login is interactive | this plan |
| The CoWork rate ceiling is checked in preflight, so exit 3 keeps meaning nothing was written | this plan      |
| The per-plugin directory is the plugin name slugged, with `-2` on a collision, so two plugins sharing a manifest name do not overwrite one document | this plan |
| `run` validates every selected plugin root, not only the target, so a malformed sibling case blocks a single-case run. There is no option to skip validation | this plan |

## Constraints

- Python 3.14, ruff `target-version = "py314"`.
- No dependency is added. `argparse`, `importlib.metadata`, `shutil`, `threading` and `os`
  are the standard library, and no third-party argument, output or colour library is used.
  `RunOptions.resolve` supplies the defaults, `Docker` is the container backend,
  `cowork_backend.run` and `cowork_backend.plan` are the CoWork backend, `cases.discover`
  and `cases.plugin_root` do the discovery, and `Config` carries the settings. Nothing here
  writes a parser, a settings layer, a second configuration file or a second argument list.
- No mock, fake, stub, patch or injected seam. The unit tier runs the real parser, gates
  hand-written documents on disk, builds real run directories under `tmp_path`, and proves
  the tee against a real child process.
- Printing happens in `cli.py` and nowhere else. `sys.exit` is called in one function,
  `console_main`. `argparse` raises `SystemExit(2)` from inside `parse_args` for an unknown
  option or a missing path, which is the one exit `main` does not return; the tests for
  those rows assert on `SystemExit`, not on a return value.
- No fixture and no example in a document carries a machine name, a user name, a home
  directory path, an account identifier, a profile identifier or a session identifier.
  [`../README.md`](../README.md).
- The exit codes are the table in [`../docs/cli.md`](../docs/cli.md). No backend's exit code
  reaches an operator unchanged.

## Phase 1: The case validator, and coverage

`src/cowork_evals/validate.py`. It reads what `cases.py` produced and reports what
[`../docs/eval_format.md`](../docs/eval_format.md) calls an error. It writes nothing and
runs no case.

- [x] `Violation` frozen: `path`, `rule`, `detail`. `violations(root)` returns them sorted
      by path, and an empty list means the tree is valid.
- [x] `uncovered(root) -> list[str]`, one line per directory under `<plugin>/skills/` with
      no directory of that name under `evals/`. It is a second return value and never a
      violation: coverage is not a rule of the format, and `--require-coverage` in phase 5
      is what turns it into a failure.
- [x] The `<skill>` layer, both directions. A directory directly under `evals/` is `plugin`,
      `mocks`, or the name of a directory under `<plugin>/skills/`. A plugin with no
      `skills/` directory admits only `plugin` and `mocks`.
- [x] `tags` names the case's own `<skill>` directory.
- [x] `plugins: ["../../.."]` resolves, from the case directory, to the same directory
      `cases.plugin_root` resolved. [`../docs/cli.md`](../docs/cli.md) requires the
      cross-check.
- [x] `name` is present. `tags` and `plugins` are present.
- [x] Any frontmatter key outside the table in
      [`../docs/eval_format.md`](../docs/eval_format.md) is a violation, `context.*`
      in `prompt.md` included.
- [x] The caps: `runs` at most 50, `max_turns` at most 200, `timeout_seconds` at most 3600.
      Each `env` key starts with `EVAL_`. That key is the case's execution environment for
      the agent under test, which the harness reads. It is not this package's configuration.
- [x] `case.yaml` carries `schema_version: "1.1"` and `name`, and no key outside
      `context.scaffold_script`, `context.history_file` and `context.add_dirs`.
- [x] A `context.add_dirs` entry that resolves outside its own case directory is a
      violation.
- [x] A grader `weight` is greater than 0. An unknown grader `type` is a violation.
- [x] A file under `graders/` with no `---` block is a violation. The harness ignores it, so
      the case runs with fewer graders than it appears to have.
- [x] `tests/unit/test_validate.py` over hand-written trees under `tests/data/validate/`:
      one clean tree, one violation of every rule above, and one tree whose only finding is
      an uncovered skill, which returns no violation.

## Phase 2: The run directory, and the log layout

`src/cowork_evals/logs.py`. The layout is
[`../docs/running_evals.md`](../docs/running_evals.md), and one module writes all of it, so
no backend has to.

- [x] `scope_name(target, roots)`: `<plugin>-<skill>-<case>` for a case directory,
      `<plugin>-<skill>` for a skill directory, `<plugin>` for an `evals/` directory, `all`
      for a path covering more than one plugin root, and `<plugin>` for any other path
      inside one root, the plugin root itself included. The plugin name is
      `.claude-plugin/plugin.json`'s `name`, and the folder basename when that file names
      none.
- [x] `slug(name)`: every character outside `[A-Za-z0-9._-]` becomes `-`. Both a scope name
      and a per-plugin directory name go through it.
- [x] `run_dir(root, scope)`: `<root>/<yyyymmdd-hhmmss>-<scope>`, local time. A second
      invocation inside the same second appends `-2`, then `-3`.
- [x] `plugin_dir(run_dir, name)`: `<run_dir>/<slug>`, with the same `-2` suffix on a
      collision. Two plugins in one sweep whose manifests carry the same `name` get two
      directories, so neither document is overwritten and the gate reads both.
- [x] The root is `<cwd>/logs/evals`, and `--out DIR` replaces it with `DIR`.
- [x] `write_env(run_dir, backend, image=None)`: one `name: value` line per row, for
      `cowork_evals` from `importlib.metadata`, `claude --version`, `python3 -V`, `backend`,
      and `image` on the container backend. A command that does not run records the failure
      on its line rather than raising.
- [x] `point_latest(root, run_dir)`: a relative symlink at `<root>/latest`, replaced through
      a temporary name and `os.replace`, so it is never absent between two runs.
- [x] `prune(root, days)`: delete directories whose name matches the stamp pattern and whose
      stamp is older than `days`. Read the stamp from the name, never the modification time,
      which a later read moves. Nothing else under the root is touched, and `latest` is
      re-pointed or removed when it dangles.
- [x] `tee(run_dir)`: a context manager over `run.log`. It opens a pipe, dups the write end
      onto file descriptors 1 and 2, and runs a thread that copies bytes to both the saved
      terminal descriptor and the file. It restores both descriptors and joins the thread on
      the way out. A child process inherits descriptors 1 and 2, so the harness's and the
      container's output reaches the file. Wrapping `sys.stdout` does not, which is why this
      is at the descriptor level.
- [x] The copy is bytes and is never decoded, so a progress carriage return survives.
- [x] `tests/unit/test_logs.py`: the five scope shapes, the slug rule, both collision
      suffixes, the `env.txt` lines, the symlink replacement, pruning by name with a fixture
      whose modification time contradicts its name, a dangling `latest`, and a real
      `subprocess.run` whose output is asserted in `run.log`.

## Phase 3: The gate

`src/cowork_evals/gate.py`. It reads result documents and decides once for the whole
invocation. The conditions are the gate table in
[`../docs/running_evals.md`](../docs/running_evals.md).

- [x] `GateResult` frozen: `passed`, `lines`. `gate(run_dir, *, extra=())` reads every
      `<plugin>/aggregate-result.json` one level under the run directory. `extra` is a
      failure line the caller already has, which is how the cost ceiling reaches the gate
      without a second code path.
- [x] A missing or unparsable document is a failure naming the path. So is a document whose
      `schemaVersion` is not 1. An unknown field is ignored: the contract is additive-only.
- [x] The `with` arm only.
- [x] A grader result carries `name`, `passed` and `scored`, never `type`. Join it to that
      case's grader definition by name to learn its class. A result with no matching
      definition is a failure naming it.
- [x] A failed `regex`, `tool_used`, `tool_order` or `file_exists` grader fails the gate.
- [x] A failed `llm` or `baseline` grader is printed and does not fail the gate.
- [x] A case carrying `skipped: true`, a grader result carrying `skipped: true`, and a
      grader result carrying `scored: false` each fail the gate, with the reason on the
      line.
- [x] `partial: true` fails the gate, whatever `partialReason` says. Correct the row in
      [`../docs/running_evals.md`](../docs/running_evals.md) in phase 8, which names two
      reasons today and misses `interrupted`.
- [x] A run carrying `error` fails the gate, on every backend. It is the CoWork case the
      driver could not run or collect, and it is also a harness run that timed out, hit the
      turn cap or exited non-zero: those are graded on what they produced, so the score
      alone does not catch them. Correct the row in
      [`../docs/running_evals.md`](../docs/running_evals.md) in phase 8, which names only
      the CoWork case.
- [x] A document whose `aggregates.casesTotal` is 0 is not a failure. A `--tag` sweep
      matches no case in most plugins, and failing on that would make every filtered sweep
      red. The whole selection matching nothing is refused in phase 6, before anything runs.
      Record it in [`../docs/running_evals.md`](../docs/running_evals.md) in phase 8, beside
      the gate table.
- [x] One line per failure, then one summary line with the case counts and the overall
      score. Over a sweep the counts are summed across plugins and the score is the mean of
      each document's `aggregates.overallScore`. The caller writes the text to `gate.txt`
      and prints it.
- [x] `tests/unit/test_gate.py` over hand-written documents under `tests/data/results/`:
      a pass, each structural grader failing, a judged grader failing under an otherwise
      passing document, a skipped case, `scored: false`, `partial: true`, a run with an
      `error` under an otherwise passing document, an empty document passing, a missing
      document, an unparsable document, a wrong `schemaVersion`, an `extra` line, and a run
      directory holding two plugins gated once.

## Phase 4: Preflight

`src/cowork_evals/preflight.py`. One function per backend, each returning the unmet
conditions in order, each line naming the command that fixes it. It writes nothing and
builds nothing.

| Backend    | Conditions                                                                       |
| ---------- | ---------------------------------------------------------------------------------- |
| `--docker` | `Docker.check()`                                                                  |
| `--cowork` | macOS, `claude` on `PATH`, a loadable `cowork_evals.yaml` naming a profile, a readable sessions root, and the Accessibility grant |
| `test`     | `PytestImage.check()`. The same daemon condition, the test image, and never the container login |

- [ ] `remedy()` in `src/cowork_evals/docker/__init__.py` names `cowork_evals setup --docker`
      for both `IMAGE` and `CREDENTIAL`, and its docstring loses the sentence saying that
      command is not built. It names `scripts/image.sh` and `scripts/login.sh` today, and a
      consumer never sees `scripts/`. `tests/unit/test_docker.py` asserts the new strings,
      and `scripts/image.sh --check` and `scripts/login.sh --check` still read `remedy()`.
- [ ] `checks(backend) -> list[str]`, and `checks_all()` covering both. Each takes the
      loaded `Config`, so `cowork_evals.yaml` is read once per invocation and every verb and
      every backend sees the same one. `Docker.check()` already returns one
      `(Condition, message)` pair per unmet condition and is reused as it stands.
- [ ] The CoWork profile condition comes from `Config.load()` and then `profile_dir` on its
      `cowork:` section. Construction validates only the file, and a missing `profile` is
      refused by the first property that needs one, so both calls are made here.
      `CoWorkError` code 2 becomes one line carrying its message.
- [ ] The Accessibility grant is probed with
      `osascript -e 'tell application "System Events" to get the name of the first process'`.
      It submits nothing and starts no session. A non-zero exit, or error 1002 on stderr, is
      the missing grant, which is what
      [`../docs/cowork_driver.md`](../docs/cowork_driver.md) records for it.
- [ ] `cowork_ceiling(target, **overrides) -> list[str]`, called by `run` and not by
      `check`. It calls `cowork_backend.plan`, which submits nothing, and returns one line
      when the plan's submission count plus `CoWork.recent()` is above `max_runs`. The
      arithmetic is `plan()`'s; this compares its three numbers. `cowork_backend.run` raises
      `CoWorkError(2, ...)` on the same condition, which is that backend's own guard and is
      unreachable behind this check.
- [ ] `validate.violations` is not called here. Case validation needs a resolved target, so
      `run` calls it after scope resolution, in phase 6.
- [ ] `tests/unit/test_preflight.py`: the shape of each returned list, the CoWork lines
      against a configuration file written to `tmp_path`, and the ceiling line against a
      hand-written case tree and run log. Nothing here starts a daemon or a session.

## Phase 5: The parser, and the executable

`src/cowork_evals/cli.py`, and `[project.scripts]`. The surface is
[`../docs/cli.md`](../docs/cli.md), and this phase builds the parse and the refusals only.
The verbs do their work in phase 6.

- [ ] `[project.scripts] cowork_evals = "cowork_evals.cli:console_main"` in
      `pyproject.toml`. `main(argv=None) -> int` returns a code, `console_main` calls
      `sys.exit` on it, and nothing else in the package exits.
- [ ] Five subparsers: `run`, `test`, `setup`, `check`, `prune`. `--version` prints the
      installed distribution version from `importlib.metadata`.
- [ ] The backend is a mutually exclusive group, required and with no default, and its
      members differ per verb: `run` takes `--docker` and `--cowork`, `test` takes
      `--docker` alone, `setup` takes `--docker`, and `check` takes both backends plus
      `--all`. `run --all` is a usage error, and so is `test --cowork`: that backend is not
      a member, so `argparse` exits 2 and there is no refusal message to write.
      `prune` takes any combination of its selection flags and requires at least one.
- [ ] Every option in the table in [`../docs/cli.md`](../docs/cli.md), with no raw argument
      tail and no pass-through to `claude plugin eval`. `--older-than` is on `prune` alone,
      and `--out` is on `run` and `prune`.
- [ ] `--require-coverage` on `run`, off by default, accepted on both backends. It reads the
      tree and not a backend, so no backend refuses it.
- [ ] `test` takes a path, `--build-missing`, `--dry-run` and a pytest tail as
      `nargs=argparse.REMAINDER` after the path, separated by `--`. It takes no other
      option: each of the others configures a harness run.
- [ ] The refusals: `--runs`, `--judge-model` and `--timeout-seconds` accepted on
      `--cowork`; `--model`, `--allow-tools`, `--max-cost-usd` and `--build-missing` refused
      there; `--timeout-seconds` refused on `--docker`. An option the chosen backend refuses
      exits 2, naming the option and the backend.
- [ ] Defaults come from `RunOptions.resolve` over the loaded `Config`. An option beats the
      file, the file beats the built-in default, and there is no third layer. No option is
      ever read from the process environment.
- [ ] `KeyboardInterrupt` returns 130.
- [ ] `tests/unit/test_cli.py`: each verb's parse tree, every refusal above, `--venv` on
      each verb as `SystemExit(2)`, an unknown option as `SystemExit(2)`, `run` with no path
      as `SystemExit(2)`, `run` with no backend as `SystemExit(2)`, `check` with no backend
      as `SystemExit(2)`, `test --cowork` as `SystemExit(2)`, a `test` tail surviving `--`
      token for token, and the version string.

## Phase 6: The verbs

Still `src/cowork_evals/cli.py`. Each verb, end to end.

### The option mapping

One table, because the two backends take different arguments and nothing else states it.

| Option                | `--docker`                        | `--cowork`                     |
| --------------------- | --------------------------------- | ------------------------------ |
| `--runs N`            | `RunOptions.runs`                 | `run(runs=)`                   |
| `--timeout-seconds`   | refused                           | `run(timeout_seconds=)`        |
| `--model`             | `RunOptions.model`                | refused                        |
| `--judge-model`       | `RunOptions.judge_model`          | `run(judge_model=)`            |
| `--allow-tools`       | `RunOptions.allow_tools`          | refused                        |
| `--max-cost-usd`      | `RunOptions.max_cost_usd`         | refused                        |
| `--tag T`             | `RunOptions.tags`                 | `run(tags=)`                   |
| `--case GLOB`         | `RunOptions.case`                 | `run(case_glob=)`              |
| `--build-missing`     | `Docker.build()` in preflight     | refused                        |
| `--require-coverage`  | `validate.uncovered`, in preflight | the same                      |
| `--out DIR`           | the log root                      | the log root                   |
| `--dry-run`           | `Docker.run_argv`                 | `cowork_backend.plan`          |

### run

- [ ] Resolve the target to a list of plugin roots. A path at or under one root is that
      root. A path covering several is every directory below it holding
      `.claude-plugin/plugin.json` with a sibling `evals/`, sorted by path.
- [ ] More than one plugin root on `--cowork` is a usage error, exit 2.
- [ ] Preflight the backend. On `--docker` with `--build-missing`, an absent or stale image
      is built here instead of failing; every other unmet condition still fails, the
      container login included, because that login is interactive.
- [ ] On `--cowork`, preflight also calls `preflight.cowork_ceiling`, so a suite too large
      for `max_runs` is refused before anything is created.
- [ ] Validate every selected plugin root, not only the target. Any violation prints the
      file and the rule and exits 3.
- [ ] Print `validate.uncovered` for every selected root. It fails nothing on its own. Under
      `--require-coverage` an uncovered skill exits 3, like any other preflight condition.
- [ ] Count the selection: `cases.discover` over every selected root with `--tag` and
      `--case` applied. Zero across all of them is a usage error, exit 2, naming the path
      and the filters. A mistyped `--tag` must not read as a pass, and this catches it
      before a container starts. One root of several matching zero is normal under a filter
      and is not an error.
- [ ] Any unmet condition, violation or empty selection exits before anything is created and
      before anything is deleted.
- [ ] Resolve the log root and prune directories older than 30 days. It happens after every
      refusal above, so exit 2 and exit 3 leave the root untouched, and before the
      `--dry-run` exit, so an unattended dry run still reclaims space.
- [ ] `--dry-run` exits 0 here. On `--docker` it prints `Docker.run_argv`, one argument per
      line. On `--cowork` it prints one line per case with its run count, its timeout and
      its `Skips`, then the ceiling arithmetic, all from `cowork_backend.plan`. The skips
      are the point of the dry run: a skipped case fails the gate, so an operator reads
      which ones before spending. Neither creates a run directory.
- [ ] Create the run directory, open the tee, write `env.txt`, and point `latest`.
- [ ] Per plugin root, in order: sum `costUsd` over the documents written so far, stop when
      the sum has reached `eval.max_cost_total_usd`, create the plugin directory with
      `logs.plugin_dir`, and call the backend through the mapping above. The check runs
      before the first plugin, so a ceiling of 0 stops the invocation before it spends
      anything. On `--cowork` that sum is the judge spend alone, because the session is
      billed to the account and is not observable from the host, so the ceiling that binds
      there is the driver's `max_runs` in preflight and not this one.
- [ ] A stop on the ceiling becomes one `extra` line to the gate. The gate then reads the
      documents written so far, adds that line, and the invocation exits 1. A sweep that
      stops on the ceiling is never a pass.
- [ ] A `DockerError` or a `CaseError` raised while running a plugin prints, and the sweep
      continues with the next plugin. The gate then reads a missing document and exits 1.
- [ ] A `CoWorkError` raised while running a case reaches the result document, which is what
      `plan_cowork_backend.md` built.
- [ ] Gate the run directory once, write `gate.txt`, print it, and return 0 or 1.

### test

The verb is a preflight and one call. Nothing between the two inspects, wraps or interprets
what pytest produced. [`../docs/cowork_test.md`](../docs/cowork_test.md) is the mechanism.

- [ ] Resolve the path to one plugin root with `cases.plugin_root`. A path covering several
      is a usage error, exit 2.
- [ ] Preflight `PytestImage.check()`: the daemon and the test image, never the container
      login. Any unmet condition prints and returns 3, having created nothing.
- [ ] `--build-missing` builds the test image, and the base image first when that is absent
      too. Without it, either being absent or stale returns 3 naming
      `cowork_evals setup --docker`.
- [ ] No case validation, no log directory, no `env.txt`, no `latest`, no pruning and no
      gate. The verb writes nothing on the host.
- [ ] `--dry-run` prints `PytestImage.run_argv`, one argument per line, and returns 0
      without starting a container.
- [ ] Return `PytestImage.run(target, pytest_args=...)` unchanged. `main` returns it and
      `console_main` exits on it. A failing suite is a result, not an error, and nothing
      here remaps a code.

### setup, check and prune

- [ ] `setup --docker`: `Docker.build()` when the image is absent, then `PytestImage.build()`
      when the test image is absent, then the interactive
      login when `has_credential()` is false. An image already at its current digest prints
      `current` and returns 0.
- [ ] `check` prints the unmet conditions from phase 4 and returns 0 when every named
      backend is ready, 3 otherwise. `check --all` covers both backends, so a ready machine
      returns 0. `check --docker` reports both images and the container login: the login is
      unmet for `run` and is not read by `test`'s preflight.
- [ ] `prune --logs` deletes run directories under the resolved root older than
      `--older-than`, default 30.
- [ ] `Docker.images()` returns each `cowork-evals:*` and `cowork-evals-test:*` tag with its
      creation date, from `docker image ls`. `Docker.remove_image(tag)` removes one, from
      `docker image rm`. Both live in the docker module, because nothing outside it builds a
      `docker` argument list.
- [ ] `prune --docker` removes every image `Docker.images()` returns except the current
      digest of each of the two, restricted by `--older-than` against the creation date. The
      container login is left alone.
- [ ] `prune` with no selection flag returns 2.
- [ ] `tests/unit/test_cli.py` grows: the sweep's plugin root resolution over a
      hand-written two-plugin tree, two plugins sharing a manifest name getting two
      directories, the multi-plugin refusal on `--cowork`, the empty selection refusal and a
      filtered sweep where one root of two matches nothing and the invocation proceeds, the
      `--require-coverage` refusal and the same tree passing without the flag, all three
      `--dry-run` outputs, the multi-plugin refusal on `test`, the ceiling arithmetic
      against hand-written documents, and each `setup`, `check` and `prune` return code that
      needs no daemon.
- [ ] `tests/unit/test_docker.py` grows: the `images()` and `remove_image()` argument lists,
      asserted without a daemon.

## Phase 7: The integration tier

`tests/integration/test_cli.py`. It needs a reachable daemon, the image built by
`scripts/image.sh` and the login made by `scripts/login.sh`. No test here needs a CoWork
profile. A missing precondition fails the test and never skips it.

The fixture is `plugins/smoke/evals`, unchanged. Nothing new is added to `plugins/`.

- [ ] `check --docker` returns 0 on a ready machine, and its lines name the fix when it does
      not. Marked `integration`, not `live`.
- [ ] `cowork_evals run --docker plugins/smoke/evals` returns 0. Assert the run directory
      holds `run.log`, `env.txt`, `gate.txt`, `smoke/aggregate-result.json`,
      `smoke/report.html` and `smoke/debug.txt`, and that `latest` points at it. Marked
      `live`.
- [ ] Assert, over that same run and not a second one, that `run.log` holds a line the
      harness printed. That is the descriptor-level tee proven against a real child, and it
      cannot be reached without one.
- [ ] No live CoWork run here. `plan_cowork_backend.md` phase 7 already fires
      `plugins/smoke/` through `cowork_backend.run` against a real session, and everything
      this plan builds above that backend is backend-neutral and is proven on `--docker`
      above: the run directory, the tee, `env.txt`, `latest` and the gate. What is left is
      the option mapping, covered by `--dry-run --cowork` in the unit tier, and the absence
      of `report.html`, which is an assertion about a file the backend never writes. A VM
      boot, a ceiling entry and a permanent session in the account buy none of it.
- [ ] `cowork_evals test --docker plugins/smoke/tests` returns 0, and the same path with the
      failing fixture returns 1, both through the real executable. It costs a container and
      no model call, so it is `integration` and not `live`. What the container itself proves
      is `plan_test.md`'s integration tier; this proves only that the verb reaches it and
      returns its code.
- [ ] The failing-gate path is asserted in the unit tier over a hand-written document. A
      second eval run buys nothing the gate tests do not already cover.
- [ ] The Docker smoke row in the cost table of
      [`../docs/running_evals.md`](../docs/running_evals.md) is already measured through
      `Docker.run`. Re-record it with a new capture date only if the run above differs; the
      command adds no model call, so a difference is a finding. The two local rows stay
      `not yet measured`, and the full-sweep row stays unmeasured: this repository holds one
      fixture plugin, so a sweep measurement belongs to a consumer, and the sweep path is
      covered in the unit tier with `--dry-run`.

## Phase 8: Documentation

Nothing durable may survive only in this file.

- [ ] [`../docs/cli.md`](../docs/cli.md), the venv removal: the synopsis, the `--venv`
      column of the option table, the `--venv` preflight row, the `setup --venv` and
      `setup --all` rows, the `prune --venv` row, and the sentence saying `run --venv`
      writes `.cowork-runtime/` into each plugin root. One sentence replaces them: the venv
      backend is designed in
      [`../docs/staged_runtime.md`](../docs/staged_runtime.md) and has no flag until a plan
      builds it.
- [ ] [`../docs/cli.md`](../docs/cli.md), the `test` verb: the synopsis line, "four verbs"
      becoming five, a `test` section holding its options and its preflight row, the clause
      allowing a raw tail there beside the sentence forbidding one on `run`, the second
      image in the `setup --docker` and `prune` rows, and the one exception to "the exit
      code is the CLI's" in the exit table. The mechanism behind it is
      [`../docs/cowork_test.md`](../docs/cowork_test.md), which `plan_test.md` wrote, and it
      is linked and not restated.
- [ ] [`../docs/cli.md`](../docs/cli.md): write in every row of the decisions table above.
      That includes `--require-coverage`, the empty selection, the `--older-than` and
      `--out` scopes, what `--build-missing` does and does not build, that `check` requires
      a backend, and the exit-3 row, which keeps `Nothing ran and nothing was written`
      because the CoWork ceiling moved into preflight and pruning moved behind it.
- [ ] [`../docs/cli.md`](../docs/cli.md), the two tables phase 2 and phase 4 made
      incomplete: the scope table, which tabulates four shapes and not the fifth, a path
      inside a plugin root that is neither a case, a skill nor `evals/`; and the `--cowork`
      preflight row, which names the desktop application where phase 4 checks a configured
      profile and a readable sessions root.
- [ ] [`../docs/cli.md`](../docs/cli.md), the `--dry-run` paragraph, which says the command
      line is printed on every backend.
- [ ] [`../docs/running_evals.md`](../docs/running_evals.md): mark the executable and its
      verbs, the gate and the case validator built; correct the `partial` row, which misses
      `interrupted`; correct the `error` row, which names only the CoWork case; record that
      an empty document passes the gate and that an empty selection is refused before the
      run; correct the log-root sentence, which says the root is the working directory
      rather than `logs/evals` under it; add the `backend` and `image` lines to `env.txt` in
      the log layout; and state that coverage, its fourth automation precondition, is
      reported by `run` and enforced by `--require-coverage`.
- [ ] [`../docs/approaches.md`](../docs/approaches.md): the `cowork_evals run --venv` row of
      the command table and the two `--venv` rows of the cadence table, which tell an author
      to run a flag that does not parse. The three approaches stay; the cadence moves to
      `--docker` until the venv backend is built. And the sentence saying `docker.md` says
      what reaches the container until the `--docker` command is built.
- [ ] [`../docs/library.md`](../docs/library.md): the five new modules in the ships table,
      `[project.scripts]` now present, which removes the sentence saying it is not in
      `pyproject.toml` yet, the two rows of the state table naming `setup --venv` and
      `run --venv`, and the sentence saying the two requirements files are read at run time
      by `setup --venv`.
- [ ] [`../docs/docker.md`](../docs/docker.md): the sentence saying that until the command
      reaches the container a run goes through `cowork_evals.docker.Docker.run`, and the
      `remedy()` change, which makes `setup --docker` the command a failed check names.
- [ ] [`../docs/eval_format.md`](../docs/eval_format.md): which rules the validator
      enforces, and that a skill with no eval directory is reported and is not a violation.
- [ ] [`../docs/environments.md`](../docs/environments.md): the usage block offering
      `setup --venv` and `check --venv` as the shipped route, and the row of the
      requirements table naming `setup --venv`. The design stays; the commands become what a
      plan that builds it would add. [`../docs/staged_runtime.md`](../docs/staged_runtime.md)
      names no `--venv` command and needs no change.
- [ ] [`../README.md`](../README.md): check the usage block against the built surface.
      `check --all` now returns 0 on a ready machine, so it stays.
- [ ] [`../tests/README.md`](../tests/README.md): a row per new test file, and the new tier
      preconditions.
- [ ] [`../docs/cowork_test.md`](../docs/cowork_test.md): the sentence naming
      `scripts/cowork_pytest.sh` as the route until the verb exists, which the verb now
      replaces. The script stays as a development task.
- [ ] Re-read every touched file for a statement this plan made false.
- [ ] [`README.md`](README.md): mark this plan `implemented`.
