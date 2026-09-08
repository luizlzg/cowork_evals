# Plan: the command

Branch `feat/cli`. Eight phases, one commit each.

This plan assembles what the backend plans built and rebuilds none of it. The contract it
holds them to is [`README.md`](README.md): a backend takes a case path and an output
directory and returns the path to the `aggregate-result.json` it produced.

It is executed after `plan_cowork_backend.md` is merged. `run --cowork` calls
`cowork_evals.cowork_backend.run`, and the validator here reads the `Case` and `Grader`
that `src/cowork_evals/cases.py` produces. Neither exists until that plan is finished.

## Scope

The layer above every backend: the option surface, the preflight, the run directory, the
gate, and the process a consumer invokes.

| Builds                            | Is                                                                |
| --------------------------------- | ------------------------------------------------------------------- |
| `src/cowork_evals/validate.py`    | The case validator over `cases.py`                                |
| `src/cowork_evals/logs.py`        | Scope naming, the run directory, `env.txt`, `latest`, pruning, the tee |
| `src/cowork_evals/gate.py`        | The gate over `aggregate-result.json`, and `gate.txt`             |
| `src/cowork_evals/preflight.py`   | The unmet conditions of each backend, for `check` and for `run`   |
| `src/cowork_evals/cli.py`         | The parser, the four verbs, the dispatch and the exit codes       |
| `[project.scripts]`               | The `cowork_evals` executable                                     |
| `tests/unit/test_validate.py`, `tests/unit/test_logs.py`, `tests/unit/test_gate.py`, `tests/unit/test_preflight.py`, `tests/unit/test_cli.py`, `tests/integration/test_cli.py` | [`../tests/README.md`](../tests/README.md) |

References: the surface is [`../docs/cli.md`](../docs/cli.md), the log layout, the pinned
flags and the gate are [`../docs/running_evals.md`](../docs/running_evals.md), the settings
layers are [`../docs/library.md`](../docs/library.md), and the rules the validator enforces
are [`../docs/eval_format.md`](../docs/eval_format.md).

## Out of scope

| Not built                                                     | Belongs to              |
| --------------------------------------------------------------- | ------------------------ |
| The venv backend, the mirror build and the staged runtime      | `plan_venv.md`, skipped |
| A second entry point, or a per-backend executable              | nobody. [`../CLAUDE.md`](../CLAUDE.md) |
| `report.html` on the CoWork backend                            | nobody                  |
| The 3.10 and import check over the code under test             | nowhere yet             |
| A hook, a CI job, a cadence                                    | the consumer repository |
| Any eval over a shipped plugin, and any suite                  | the consumer repository |

## Decisions this plan settles

Each of these was open in [`../docs/cli.md`](../docs/cli.md). Phase 8 writes each one into
that file.

| Decision                                                                                   | Settled by      |
| --------------------------------------------------------------------------------------------- | --------------- |
| `--venv` parses on every verb and fails preflight with exit 3, naming the venv backend as not built | the developer |
| A case that violates the format fails inside `run`'s preflight, with exit 3                | the developer   |
| `argparse` from the standard library. No third-party argument, output or colour library    | this plan       |
| `--out DIR` replaces the whole `logs/evals` root, so the run directory is `<out>/<stamp>-<scope>` | this plan |
| `--dry-run --cowork` prints the cases it would submit rather than a command line, because that backend builds none | this plan |
| `prune --venv` fails with exit 3. It cannot know which mirror is current without the venv backend's digest | this plan |
| `prune` with no selection flag is a usage error, exit 2                                    | this plan       |
| `setup --all` builds the container backend, prints one line for the venv backend, and exits on the container result | this plan |
| `check --all` counts the venv backend as an unmet condition, so it exits 3 until plan 3 is written | this plan  |
| A sweep stopped by `EVAL_MAX_COST_TOTAL_USD` is a gate failure, exit 1                     | this plan       |
| Any `partial: true` fails the gate, whatever the reason                                    | this plan       |
| A grader result carrying `scored: false` is a skip and fails the gate, because `--ablation none` drops nothing | this plan |

## Constraints

- Python 3.14, ruff `target-version = "py314"`.
- No dependency is added. `argparse`, `importlib.metadata`, `shutil`, `threading` and `os`
  are the standard library. `RunOptions.resolve` supplies the defaults, `Docker` is the
  container backend, `cowork_backend.run` is the CoWork backend, `cases.discover` and
  `cases.plugin_root` do the discovery, and `env.setting` reads the settings. Nothing here
  writes a parser, a settings layer or a second argument list.
- No mock, fake, stub, patch or injected seam. The unit tier runs the real parser, gates
  hand-written documents on disk, builds real run directories under `tmp_path`, and proves
  the tee against a real child process.
- Printing happens in `cli.py` and nowhere else. `sys.exit` is called in one function.
- No fixture and no example in a document carries a machine name, a user name, a home
  directory path, an account identifier, a profile identifier or a session identifier.
  [`../README.md`](../README.md).
- The exit codes are the table in [`../docs/cli.md`](../docs/cli.md). No backend's exit code
  reaches an operator unchanged.

## Phase 1: The case validator

`src/cowork_evals/validate.py`. It reads what `cases.py` produced and reports what
[`../docs/eval_format.md`](../docs/eval_format.md) calls an error. It writes nothing and
runs no case.

- [ ] `Violation` frozen: `path`, `rule`, `detail`. `violations(root)` returns them sorted
      by path, and an empty list means the tree is valid.
- [ ] The `<skill>` layer, both directions. A directory directly under `evals/` is `plugin`,
      `mocks`, or the name of a directory under `<plugin>/skills/`. A plugin with no
      `skills/` directory admits only `plugin` and `mocks`. A skill with no eval directory
      is reported as a line and is not a violation: coverage is a precondition for
      automating a suite in [`../docs/running_evals.md`](../docs/running_evals.md), not a
      rule of the format.
- [ ] `tags` names the case's own `<skill>` directory.
- [ ] `plugins: ["../../.."]` resolves, from the case directory, to the same directory
      `cases.plugin_root` resolved. [`../docs/cli.md`](../docs/cli.md) requires the
      cross-check.
- [ ] `name` is present. `tags` and `plugins` are present.
- [ ] Any frontmatter key outside the table in
      [`../docs/eval_format.md`](../docs/eval_format.md) is a violation, `context.*`
      in `prompt.md` included.
- [ ] The caps: `runs` at most 50, `max_turns` at most 200, `timeout_seconds` at most 3600.
      Each `env` key starts with `EVAL_`.
- [ ] `case.yaml` carries `schema_version: "1.1"` and `name`, and no key outside
      `context.scaffold_script`, `context.history_file` and `context.add_dirs`.
- [ ] A `context.add_dirs` entry that resolves outside its own case directory is a
      violation.
- [ ] A grader `weight` is greater than 0. An unknown grader `type` is a violation.
- [ ] A file under `graders/` with no `---` block is a violation. The harness ignores it, so
      the case runs with fewer graders than it appears to have.
- [ ] `tests/unit/test_validate.py` over hand-written trees under `tests/data/validate/`:
      one clean tree, and one violation of every rule above.

## Phase 2: The run directory, and the log layout

`src/cowork_evals/logs.py`. The layout is
[`../docs/running_evals.md`](../docs/running_evals.md), and one module writes all of it, so
no backend has to.

- [ ] `scope_name(target, roots)`: `<plugin>-<skill>-<case>` for a case directory,
      `<plugin>-<skill>` for a skill directory, `<plugin>` for an `evals/` directory, and
      `all` for a path covering more than one plugin root. The plugin name is
      `.claude-plugin/plugin.json`'s `name`, and the folder basename when that file names
      none.
- [ ] Every character outside `[A-Za-z0-9._-]` in a scope name becomes `-`. It is a
      directory name.
- [ ] `run_dir(root, scope)`: `<root>/<yyyymmdd-hhmmss>-<scope>`, local time. A second
      invocation inside the same second appends `-2`, then `-3`.
- [ ] The root is `<cwd>/logs/evals`, and `--out DIR` replaces it with `DIR`.
- [ ] `write_env(run_dir, backend, image=None)`: one `name: value` line per row, for
      `cowork_evals` from `importlib.metadata`, `claude --version`, `python3 -V`, `backend`,
      and `image` on the container backend. A command that does not run records the failure
      on its line rather than raising.
- [ ] `point_latest(root, run_dir)`: a relative symlink at `<root>/latest`, replaced through
      a temporary name and `os.replace`, so it is never absent between two runs.
- [ ] `prune(root, days)`: delete directories whose name matches the stamp pattern and whose
      stamp is older than `days`. Read the stamp from the name, never the modification time,
      which a later read moves. Nothing else under the root is touched, and `latest` is
      re-pointed or removed when it dangles.
- [ ] `tee(run_dir)`: a context manager over `run.log`. It opens a pipe, dups the write end
      onto file descriptors 1 and 2, and runs a thread that copies bytes to both the saved
      terminal descriptor and the file. It restores both descriptors and joins the thread on
      the way out. A child process inherits descriptors 1 and 2, so the harness's and the
      container's output reaches the file. Wrapping `sys.stdout` does not, which is why this
      is at the descriptor level.
- [ ] The copy is bytes and is never decoded, so a progress carriage return survives.
- [ ] `tests/unit/test_logs.py`: the four scope shapes, the slug rule, the collision suffix,
      the `env.txt` lines, the symlink replacement, pruning by name with a fixture whose
      modification time contradicts its name, a dangling `latest`, and a real
      `subprocess.run` whose output is asserted in `run.log`.

## Phase 3: The gate

`src/cowork_evals/gate.py`. It reads result documents and decides once for the whole
invocation. The conditions are the gate table in
[`../docs/running_evals.md`](../docs/running_evals.md).

- [ ] `GateResult` frozen: `passed`, `lines`. `gate(run_dir)` reads every
      `<plugin>/aggregate-result.json` one level under the run directory.
- [ ] A missing or unparsable document is a failure naming the path. So is a document whose
      `schemaVersion` is not 1. An unknown field is ignored: the contract is additive-only.
- [ ] The `with` arm only.
- [ ] A grader result carries `name`, `passed` and `scored`, never `type`. Join it to that
      case's grader definition by name to learn its class. A result with no matching
      definition is a failure naming it.
- [ ] A failed `regex`, `tool_used`, `tool_order` or `file_exists` grader fails the gate.
- [ ] A failed `llm` or `baseline` grader is printed and does not fail the gate.
- [ ] A case carrying `skipped: true`, a grader result carrying `skipped: true`, and a
      grader result carrying `scored: false` each fail the gate, with the reason on the
      line.
- [ ] `partial: true` fails the gate, whatever `partialReason` says. Correct the row in
      [`../docs/running_evals.md`](../docs/running_evals.md) in phase 8, which names two
      reasons today.
- [ ] A run carrying `error` fails the gate. That is the CoWork case the driver could not
      run or collect.
- [ ] One line per failure, then one summary line with the case counts and the overall
      score. The caller writes the text to `gate.txt` and prints it.
- [ ] `tests/unit/test_gate.py` over hand-written documents under `tests/data/results/`:
      a pass, each structural grader failing, a judged grader failing under an otherwise
      passing document, a skipped case, `scored: false`, `partial: true`, a run with an
      `error`, a missing document, an unparsable document, a wrong `schemaVersion`, and a
      run directory holding two plugins gated once.

## Phase 4: Preflight

`src/cowork_evals/preflight.py`. One function per backend, each returning the unmet
conditions in order, each line naming the command that fixes it. It writes nothing and
builds nothing. `Docker.check` already has this shape and is reused unchanged.

| Backend    | Conditions                                                                       |
| ---------- | ---------------------------------------------------------------------------------- |
| `--venv`   | One line: the backend is not built, and `plans/README.md` says plan 3 is skipped |
| `--docker` | `Docker.check()`                                                                  |
| `--cowork` | macOS, a loadable `cowork_evals.yaml` naming a profile, a readable sessions root, and the Accessibility grant |

- [ ] `checks(backend) -> list[str]`, and `checks_all()` covering all three.
- [ ] The CoWork profile condition comes from `Config.load()`. `CoWorkError` code 2 becomes
      one line carrying its message. [`../docs/cli.md`](../docs/cli.md) already maps that
      code onto a failed preflight.
- [ ] The Accessibility grant is probed with
      `osascript -e 'tell application "System Events" to get the name of the first process'`.
      It submits nothing and starts no session. A non-zero exit, or error 1002 on stderr, is
      the missing grant, which is what
      [`../docs/cowork_driver.md`](../docs/cowork_driver.md) records for it.
- [ ] `validate.violations` is not called here. Case validation needs a resolved target, so
      `run` calls it after scope resolution, in phase 6.
- [ ] `tests/unit/test_preflight.py`: the venv line, the shape of each returned list, and
      the CoWork lines against a configuration file written to `tmp_path`. Nothing here
      starts a daemon or a session.

## Phase 5: The parser, and the executable

`src/cowork_evals/cli.py`, and `[project.scripts]`. The surface is
[`../docs/cli.md`](../docs/cli.md), and this phase builds the parse and the refusals only.
The verbs do their work in phase 6.

- [ ] `[project.scripts] cowork_evals = "cowork_evals.cli:console_main"` in
      `pyproject.toml`. `main(argv=None) -> int` returns a code, `console_main` calls
      `sys.exit` on it, and nothing else in the package exits.
- [ ] Four subparsers: `run`, `setup`, `check`, `prune`. `--version` prints the installed
      distribution version from `importlib.metadata`.
- [ ] The backend is a mutually exclusive group. It is required on `run` and has no default.
- [ ] Every option in the table in [`../docs/cli.md`](../docs/cli.md), with no raw argument
      tail and no pass-through to `claude plugin eval`.
- [ ] An option the chosen backend refuses exits 2, naming the option and the backend. The
      table is read from [`../docs/cli.md`](../docs/cli.md) as `plan_cowork_backend.md`
      leaves it, which accepts `--runs` and `--timeout-seconds` on `--cowork`.
- [ ] Defaults come from `RunOptions.resolve`, so `.env` and the process environment reach
      the harness through the one path that already exists.
- [ ] `KeyboardInterrupt` returns 130.
- [ ] `tests/unit/test_cli.py`: each verb's parse tree, every refusal row, an unknown option
      as exit 2, `run` with no path as exit 2, `run` with no backend as exit 2, and the
      version string.

## Phase 6: The verbs

Still `src/cowork_evals/cli.py`. Each verb, end to end.

### run

- [ ] Resolve the log root, then prune directories older than `--older-than`, default 30.
      It happens before `--dry-run` exits, so an unattended run reclaims space.
- [ ] Resolve the target to a list of plugin roots. A path at or under one root is that
      root. A path covering several is every directory below it holding
      `.claude-plugin/plugin.json` with a sibling `evals/`, sorted by path.
- [ ] More than one plugin root on `--cowork` is a usage error, exit 2.
- [ ] Preflight the backend. Any unmet condition prints and exits 3, having created no run
      directory.
- [ ] Validate every selected plugin root. Any violation prints the file and the rule and
      exits 3.
- [ ] `--dry-run` exits 0 here. On `--docker` it prints `Docker.run_argv`, one argument per
      line. On `--cowork` it prints one line per case with the run count and the timeout
      that case would run under, then the ceiling arithmetic. Neither creates a run
      directory.
- [ ] Create the run directory, open the tee, write `env.txt`, and point `latest`.
- [ ] Per plugin root, in order: sum `costUsd` over the documents written so far, refuse to
      continue when the sum has reached `EVAL_MAX_COST_TOTAL_USD`, create
      `<run_dir>/<plugin>/`, and call the backend. The check runs before the first plugin,
      so a ceiling of 0 stops the invocation before it spends anything.
- [ ] A stop on the ceiling writes its line into `gate.txt` and the invocation exits 1. A
      sweep that stops on the ceiling is never a pass.
- [ ] A `DockerError` or a `CaseError` raised while running a plugin prints, and the sweep
      continues with the next plugin. The gate then reads a missing document and exits 1.
- [ ] A `CoWorkError` with code 2 raised before any case ran is the rate ceiling, and it
      exits 3. Every other code reaches the result document, which is what
      `plan_cowork_backend.md` built.
- [ ] Gate the run directory once, write `gate.txt`, print it, and return 0 or 1.

### setup, check and prune

- [ ] `setup --docker`: `Docker.build()` when the image is absent, then the interactive
      login when `has_credential()` is false. An image already at the current digest prints
      `current` and returns 0.
- [ ] `setup --venv` returns 3 with the not-built line. `setup --all` builds the container
      backend, prints the same line for the venv backend, and returns the container result.
- [ ] `check` prints the unmet conditions from phase 4 and returns 0 when every named
      backend is ready, 3 otherwise. `check --all` covers all three, so it returns 3 while
      the venv backend is unbuilt.
- [ ] `prune --logs` deletes run directories under the resolved root older than
      `--older-than`, default 30.
- [ ] `prune --docker` deletes every image tagged `cowork-evals:*` except the current
      digest, restricted by `--older-than` against the image creation date. The container
      login is left alone.
- [ ] `prune --venv` returns 3 with the not-built line. Without that backend's digest there
      is no current mirror to keep.
- [ ] `prune` with no selection flag returns 2.
- [ ] `tests/unit/test_cli.py` grows: the sweep's plugin root resolution over a
      hand-written two-plugin tree, the multi-plugin refusal on `--cowork`, both `--dry-run`
      outputs, the ceiling arithmetic against hand-written documents, and each `setup`,
      `check` and `prune` return code that needs no daemon.

## Phase 7: The integration tier, and the measurements

`tests/integration/test_cli.py`. It needs a reachable daemon and the image built by
`scripts/image.sh` for the container tests, and a signed-in CoWork with the Accessibility
grant for the CoWork one. A missing precondition fails the test and never skips it.

The fixture is `plugins/smoke/evals`, unchanged. Nothing new is added to `plugins/`.

- [ ] `check --docker` returns 0 on a ready machine, and its lines name the fix when it does
      not. Marked `integration`, not `live`.
- [ ] `cowork_evals run --docker plugins/smoke/evals` returns 0. Assert the run directory
      holds `run.log`, `env.txt`, `gate.txt`, `smoke/aggregate-result.json`,
      `smoke/report.html` and `smoke/debug.txt`, and that `latest` points at it. Marked
      `live`.
- [ ] Assert `run.log` holds a line the harness printed. That is the descriptor-level tee
      proven against a real child, and it cannot be reached without one.
- [ ] `cowork_evals run --cowork plugins/smoke/evals` returns 0, writes
      `aggregate-result.json` and writes no `report.html`. Marked `live`. One VM boot, one
      ceiling entry, one permanent session.
- [ ] The failing-gate path is asserted in the unit tier over a hand-written document. A
      second eval run buys nothing the gate tests do not already cover.
- [ ] Record in [`../docs/running_evals.md`](../docs/running_evals.md): the wall clock and
      the `costUsd` of the Docker smoke row in the cost table, with the capture date. The
      two local rows stay `not yet measured` and gain a note that they wait on plan 3.
- [ ] The full-sweep row stays unmeasured here. This repository holds one fixture plugin, so
      a sweep measurement belongs to a consumer. The sweep path itself is covered in the
      unit tier with `--dry-run`.

## Phase 8: Documentation

Nothing durable may survive only in this file.

- [ ] [`../docs/cli.md`](../docs/cli.md): remove the design notice, and write in every row
      of the decisions table above.
- [ ] [`../docs/running_evals.md`](../docs/running_evals.md): mark the package and CLI, the
      gate and the case validator built; correct the `partial` row; add the `backend` and
      `image` lines to `env.txt` in the log layout; record the measurement.
- [ ] [`../docs/library.md`](../docs/library.md): the five new modules, `[project.scripts]`
      now present, and the sentence saying it is not in `pyproject.toml` yet removed.
- [ ] [`../docs/approaches.md`](../docs/approaches.md): the `--docker` row now runs through
      `cowork_evals run`, and the paragraph saying it runs through `Docker.run` goes.
- [ ] [`../docs/eval_format.md`](../docs/eval_format.md): which rules the validator
      enforces, and that a skill with no eval directory is reported and is not a violation.
- [ ] [`../README.md`](../README.md): check every command in the usage block against the
      built surface, `setup --venv` included.
- [ ] [`../tests/README.md`](../tests/README.md): a row per new test file, and the new tier
      preconditions.
- [ ] [`../scripts/README.md`](../scripts/README.md): confirm the paragraph saying the
      backends, the gate and the validator are not scripts is still true.
- [ ] Re-read every touched file for a statement this plan made false.
- [ ] [`README.md`](README.md): mark this plan `implemented`.
