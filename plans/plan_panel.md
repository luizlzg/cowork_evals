# Panel

## Summary

A plugin repository holds many plugins, each with several skills, and each skill has eval
cases: a prompt run against a model, with graders that decide whether the answer was good.
`cowork_evals run` executes the cases under one path and prints a verdict for those cases, and
that is the only place a result ever appears. There is no way to ask what state the
repository's evals are in as a whole: which cases pass, which fail, which have never been run
at all, and how long ago any of it was measured. That gap matters because running evals is slow
and costs money, so nobody runs them often. Most of what is known about a repository's evals at
any moment came from runs made days or weeks ago, and it survives only in a terminal. What is
left on disk does not answer it either, because each run writes a directory under `logs/evals/`
that `prune` deletes once it is older than the retention it is given, thirty days by default.

This plan records one line per case per run, in a file per case under `logs/evals/history/`,
and adds a `cowork_evals panel` command that reads those lines together with the case files on
disk. After it, one command that spends nothing prints every eval case under a path with its
latest result on each backend, when it last ran, how long it took, how often it flakes, and
whether the case files have changed since that result was produced.

## References

`docs/cli.md` for the verb surface and the scope rule, `docs/running_evals.md` for pass and
fail and the log layout, `docs/library.md` for `What ships` and `Where state lives`,
`tests/README.md` for the tiers and the fixture rule.

`cases.py` reads every definition the panel shows. `results.py` writes the document it reads
back, `verdict.py` decides pass and fail over that document, `logs.py` owns the run tree, and
`cli.py` holds `_sweep` and `_prune`.

## Requirements

- A record outlives the run directory, because that directory is deleted on a retention the
  operator sets and the record is all that is left after.
- Definitions are read from the case tree at render time, because `cases.discover` already
  parses all of them and a second copy drifts from the tree.
- Status is per backend, because a container pass is not evidence about a CoWork session.
- A case with no record reads as never run, because coverage is the first question the panel
  answers.
- `outcome` is what `verdict.decide` decided, because a second rule would disagree with it on
  the same document.
- A record says whether the case files changed since, because a green row over edited files is
  not evidence about the files that are there now.
- An append that fails is a warning and leaves the exit code alone, because recording a result
  is not deciding one.

## Out of scope

- **Automatic retention.** A keep-N or keep-days rule deletes the newest record of a case that
  runs twice a year, which is the row the panel most needs. `prune --history` is the operator's
  act.
- **The plugin's git revision on a record.** It needs a subprocess against a tool that may be
  absent, in a tree that may not be a repository, and it changes on every unrelated commit. The
  case digest answers the same question without either problem.
- **A second store for invocation-level facts.** Each record carries its own, so one case file
  is read with no join and no second file can go missing.
- **Deleting the history of cases no longer in the tree.** `prune` takes no path and cannot
  know what the tree holds now. Retiring one case is `rm` of one file.
- **An exit code that means the panel is red.** `run` already exits on the verdict, and a
  second code deciding the same thing from older data would disagree with it.

## Constraints

- `logs.prune` deletes only children of the log root whose names match the run stamp pattern,
  so a sibling directory under that root survives it. `logs.py`.
- The v1 result document is additive-only, and is read here and never extended here.
  `docs/cowork_backend.md`.
- A backend takes a case path and an output directory and returns a result document. It never
  names a directory, prunes, or decides. `plans/README.md`.
- A run directory is named `slug(plugin_name(root))`, suffixed `-2` when two plugins in one
  sweep share a manifest name. The history path is not, because it has to be stable across
  invocations, so two plugins of one name share a history directory. `logs.py`.

Everything in `CLAUDE.md` binds this plan as it binds every other, and is not repeated here.

## High-level design

Three kinds of fact reach the panel. What a case is lives in the case tree. What one case did
in one invocation lives in the history. Latest status, age, flake rate and staleness are
derived at render time and stored nowhere.

The history is the only new persistent state. Its rule against the existing run tree is: what
one invocation produced lives in that invocation's run directory and is deleted with it, and
what outlives that deletion lives in the history. A record therefore holds a summary and two
join keys back into the run tree, the invocation id and the trace path, and the panel reports
the artefacts as gone when that directory is not there.

The history is partitioned on the case, at
`logs/evals/history/<plugin>/<the case's directory under evals/>.jsonl`. That is
`<plugin>/<skill>/<case>.jsonl` for the ordinary tree and stays unique for the two shapes that
are not ordinary: a case directly under `evals/`, which has no skill, and a case nested deeper
than one skill directory, where two cases can share a directory name. The case is the panel's
own row, so the path is the lookup key and a read is one file open. Two invocations collide only when both run
the same case. A retired case is one file to delete. Partitioning on the plugin or the skill
was rejected: the path would carry part of a case's identity and each record the rest, a read
would become a scan and a filter, and two invocations touching one plugin would contend.

A record is self-contained. It repeats the plugin, skill and case the path already says, and
carries its own invocation id, timestamp, backend and versions, so one line is readable alone.

`run` appends after the verdict, once, from the documents the invocation produced. No backend
changes and nothing writes a record during a run. `panel` reads the case tree with
`cases.discover`, reads the newest record per case and backend, and prints the join.

## Implementation details

### panel.py

`src/cowork_evals/panel.py` holds the store and the render, and is the only thing that writes
or deletes a path under the history root. That mirrors `logs.py` over the run tree, and the
rule between the two modules is the rule between the two trees, above.

| Function                             | Does                                                        |
| ------------------------------------ | ------------------------------------------------------------- |
| `path(root, plugin, case_dir)`       | The case file: the plugin, then the case's directory under `evals/`, every component through `logs.slug` |
| `append(root, records)`              | Group by path, create parents, one `flock` and one `write` per file |
| `read(path)`                         | Every record in one file, oldest first                      |
| `digest(case_dir)`                   | `sha256` over the files that define the case                |
| `records(run_dir, outcomes, backend, image)` | One invocation's records, from its result documents |
| `rows(root, cases)`                  | One row per case, joined to its newest record per backend   |
| `table`, `markdown`, `snapshot`      | The three renders over those rows                           |
| `prune(root, days)`                  | Drop old records, delete an emptied file, then an emptied directory |

`append` opens each file `"a"` under `fcntl.flock(LOCK_EX)` and writes all of that file's lines
in one call, so a reader sees whole lines. `read` skips a line that does not parse and reports
it, because a truncated last line must not make a whole case unreadable.

`digest` hashes bytes, so a whitespace change counts. It covers `prompt.md`, `case.yaml` when
the case has one, and each `graders/*.md` in path order, which is every file that defines the
case. It is computed at append time and recomputed at render time, and the two are compared.

`records` re-reads each `<plugin>/aggregate-result.json` itself rather than having `decide`
return the documents. It applies no pass or fail rule, so nothing is duplicated but the walk,
and `verdict.decide` keeps its narrow return.

### The record

One JSON object per line. An optional field is absent, never null.

| Field                           | From                                                        |
| ------------------------------- | ------------------------------------------------------------- |
| `schemaVersion`                 | `1`                                                         |
| `invocation`                    | the run directory's name                                    |
| `startedAt`, `claudeVersion`    | the document                                                |
| `backend`, `image`              | `args.backend`, and `Docker.tag` on the container backend   |
| `coworkEvals`                   | `logs.distribution_version()`                               |
| `plugin`, `pluginVersion`       | `suite.plugins[0]`, not the run directory's name            |
| `skill`                         | `validate._skill_of`'s rule: the first component of `dir` when there is more than one, absent otherwise |
| `case`, `dir`                   | the case entry's `name` and `dir`                           |
| `caseDigest`                    | `digest(<suite.root>/<dir>)`                                |
| `outcome`                       | `verdict.decide`: `pass`, `fail` or `declared`              |
| `score`, `passRate`, `delta`    | the case's `aggregates`, `delta` only when present          |
| `runs`                          | the length of `arms.with`                                   |
| `durationSeconds`, `costUsd`    | summed over the runs, from `durationSeconds` and `judgeCostUsd` |
| `failedGraders`, `error`        | scored graders that did not pass, and the first run error   |
| `deniedTools`, `unofferedTools` | the union over the runs, when `traces.py` wrote them        |
| `tracePath`                     | the first failing run's, else the first run's               |

### The verdict change

`_judge_case` already reaches all three outcomes: it returns early after `totals.declare_one`,
and otherwise compares the failure count before and after itself to call `totals.pass_one`.
The change is to return that conclusion instead of discarding it. `_judge_document` collects,
`decide` collects, and `Verdict` gains `outcomes: tuple[CaseOutcome, ...]`. `text` and `passed`
are unchanged and no caller breaks.

`CaseOutcome` is a frozen dataclass of `plugin`, `dir`, `name` and `outcome`. `plugin` there is
the run directory's child name, which is what `_judge_document` holds, and `dir` is the case's
`dir`. The pair is the join key `panel.records` uses. The `plugin` that goes into a record is
the manifest name from `suite.plugins[0]`, which is not always the directory name.

### The configuration

A fourth section, `panel:`, read by `panel.py`, with one key: `panel.root`, a path, default
`logs/evals/history`, resolved from the working directory like every other. `--out` does not
move it, because `--out` relocates what one invocation produced and the history is not one
invocation's.

`PanelSection` is built like the three beside it in `config.py`, and joins them in
`__init__.__all__`, which exports the configuration a consumer imports. The key goes in
`data/cowork_evals.example.yaml`.

### The command

`cli._sweep` calls `panel.records` after `verdict.decide`, then `panel.append`. A `--dry-run`
and every refusal return earlier, so neither appends. An `OSError` prints `panel: <reason>` on
stderr and the exit code stays the verdict's.

`cli._panel` resolves its path with `plugin_roots` and `_targets`, the rule `run` uses,
discovers the cases, and prints the table. `--markdown FILE` and `--json FILE` write the other
two renders, and both may be given at once. `--removed` adds rows for history with no case in
the tree. `panel` takes no backend, because it renders both columns and reaches neither.

There is no `--tag` and no `--case`. The path is the only selector, because the panel exists to
show what has never run, and a filter hides exactly those rows.

A path selecting no case is exit 2, as on `run`. A history file with a line that does not parse
prints `panel: <path>: <reason>` on stderr, renders the row from the records that did parse,
and leaves the exit code at 0, which is how a failed append behaves on `run`.

`cli._prune` gains `--history`, reusing the existing `--older-than DAYS`. It ignores `--out`:
that option names the log root, and the history root is `panel.root`.

### The columns

plugin, skill, case and description from the tree, the description empty for a case that
writes none; a docker column and a cowork column each holding an outcome and an age in days; then score, duration, flake rate over that backend's
records, stale when the tree's digest differs, and the artefacts path, marked gone when it is
not on disk.

A backend with no record for that case reads `never run`. The cowork column of a case carrying
`no-cowork` reads `declared` whether or not it has ever been submitted, because the tag is in
the tree and is the reason no record will ever appear there.

## Testing

Three rules bind every test written for this plan. The first two are `CLAUDE.md`'s and
`tests/README.md`'s, and they are absolute.

- **Never mock.** No mock, fake, stub, patch or injected seam appears in a test, and no library
  that supplies one becomes a dependency. No production parameter exists to accept one. A test
  that asserts against a stand-in asserts against itself. A test runs against the real thing or
  it is not written.
- **Never skip.** No test is skipped, and no `if` bypasses the assertions inside one. A missing
  image, an unbuilt environment or an unconfigured profile fails an integration test rather
  than skipping it, because a skipped test reports as a pass and hides what it was written to
  catch.
- **A test asserts a rule this plan invents, never one the standard library already
  guarantees.** No test of a round trip through `json` and an appended file, no test of a
  formatter returning a string, no test of a dataclass default, no tautological test and no
  padding for coverage.

Either of the first two is lifted only when the developer approves that exception, asked
explicitly. Nothing in this plan needs either lifted: every subject is a real file on disk read
by the real reader.

What that leaves to cover: which file a record lands in; which files the digest covers; the
join of a case tree to its newest record per backend, including a case with no record, a record
with no case and a `no-cowork` case; what pruning deletes; every field of a record against the
document it came from; and the outcome `verdict.decide` returns against the lines it prints
beside it. For the renders, the invariant worth holding is that the JSON snapshot carries the
same rows as everything else, and that is the one assertion.

Unit, except one integration test that needs a real run. Fixtures are real files under
`tests/data/history/` and the real `plugins/smoke` tree. Follow `tests/README.md`: one file per
unit under test, named after the unit; the directory is the tier; fixtures under `tests/data/`.

The integration test must point `panel.root` at a temporary directory, by writing a
`cowork_evals.yaml` the way `integration/conftest.py`'s `unattended` fixture already writes
one. That is configuration a consumer would write, not a seam. `--out` does not move the
history, so a test left on the default would append to the developer's own history tree.

## Documentation updates

- `docs/panel.md`, new: the history tree, the record, the partition rule, the rule against the
  run tree, the render and its columns. It is a mechanism file, so everything measured about
  the store lives there.
- `docs/README.md`: a row after `environments.md`, and `the next four are the mechanisms`
  becomes five.
- `docs/cli.md`: `eight verbs` becomes nine; `panel` joins the verbs that take no backend in
  the summary; the synopsis line; a `panel` section; a `--history` row in the `prune` flag
  table.
- `docs/library.md`: a `src/cowork_evals/panel.py` row in `What ships`; `the eight verbs`
  becomes nine on the `cli.py` row; a history row in `Where state lives`, saying `--out` does
  not move it.
- `docs/running_evals.md`: a status table row for the history and the verb over it; one line in
  `Logs` saying a run directory is not the record of what a case did.
- `README.md`: a `cowork_evals panel` line in `The command` block. The summary table is the
  four structural problems and gains nothing.
- `tests/README.md`: a `unit/test_panel.py` row, and the panel in the scope sentence.
- `data/cowork_evals.example.yaml`: the `panel:` section.

## Implementation steps

> **For the implementer:** Work autonomously end-to-end. Do not pause to ask for permission to
> run shell commands during the writing phase — assume any such request will be denied.
> Complete **Implementation steps**, **Test steps**, and **Documentation updates** by editing
> files only. Once everything is written, run **Verification steps** yourself in one batch at
> the end.

Tick a box once it is verified, and tick it then rather than in a batch at the end: this file
is the only record of where the work stopped if the context is lost. `CLAUDE.md`.

- [x] `PanelSection` in `config.py`, on `_Sections`, on `Config` and in `Config.load`
- [x] `PanelSection` in `__init__.__all__`, and the key in `data/cowork_evals.example.yaml`
- [x] `panel.py`: `path`, `append`, `read` and `digest`
- [x] `panel.py`: `prune`
- [x] `CaseOutcome` and `Verdict.outcomes` in `verdict.py`, no condition moved or copied
- [x] `panel.records`, from an invocation's result documents and outcomes
- [ ] The call from `cli._sweep` after the verdict, a failed append a stderr warning
- [x] `panel.rows`, joining the case tree to the newest record per backend
- [x] `panel.table`, `panel.markdown` and `panel.snapshot`
- [x] The `panel` verb in the parser, and `cli._panel` in the dispatch
- [x] `--history` on `cli._prune`

## Test steps

- [ ] `unit/test_config.py`: `panel.root` read from a file and resolved to an absolute path
- [ ] `unit/test_panel.py`: the path for an ordinary case, one directly under `evals/`, one
      nested deeper than a single skill directory, and one whose names need slugging
- [ ] `unit/test_panel.py`: three cases in one append land in three files, parents created
- [ ] `unit/test_panel.py`: an unparsable last line reported, the records before it returned
- [ ] `unit/test_panel.py`: the digest moves when `prompt.md`, `case.yaml` or a grader changes,
      and not when any other file in the case directory does
- [ ] `unit/test_panel.py`: prune drops records by age, deletes an emptied file, then an
      emptied directory
- [ ] `unit/test_verdict.py`: the outcome for a passing, failing, declared and two-arm
      document, each agreeing with the lines printed beside it
- [ ] `unit/test_panel.py`: every field of a record, from a hand-written result document and
      its outcomes, including a two-arm one
- [ ] `unit/test_panel.py`: rows over `plugins/smoke` with no history: every case never run,
      and `capped-turns` reading `declared` in the cowork column from its tag alone
- [ ] `unit/test_panel.py`: two backends for one case, the newest of each selected
- [ ] `unit/test_panel.py`: a stale row, and a row whose trace directory is gone
- [ ] `unit/test_panel.py`: a removed case hidden by default, shown with `--removed`
- [ ] `unit/test_panel.py`: the JSON snapshot carries one entry per row, with the row's values
- [ ] `unit/test_cli.py`: the verb and `prune --history` parse, a path selecting no case exits
      2, and an unparsable history line leaves the exit code at 0
- [ ] `integration/test_cli.py`: one `run --docker plugins/smoke` with `panel.root` in a
      temporary directory, then `panel` showing that run

## Verification steps

1. `scripts/lint.sh --fix`, then `scripts/lint.sh`.
2. `scripts/test.sh tests/unit/test_panel.py`.
3. `scripts/test.sh`, the whole unit tier.
4. `scripts/image.sh` and `scripts/login.sh`, then
   `scripts/test.sh -m "integration and not live"`, which spends nothing and catches breakage
   first.
5. `scripts/test.sh -m integration`. This one spends: it fires real container runs, `claude -p`
   judge calls and, with a profile configured, real CoWork sessions. `tests/README.md` puts it
   at the end of a plan, which is here.
6. By hand: `cowork_evals run --docker plugins/smoke`, then
   `cowork_evals panel plugins/smoke`. One row per case, each with a docker outcome at an age
   of 0 days and an artefacts path that exists, `never run` in the cowork column for two of
   them and `declared` for `capped-turns`. Then edit
   `plugins/smoke/evals/plugin/python-version/graders/reports-3-10-12.md`, run `panel` again,
   confirm that row reads stale, and restore the file.
7. `cowork_evals panel plugins/smoke --markdown /tmp/panel.md --json /tmp/panel.json`, and
   confirm both hold the same rows as the table.
