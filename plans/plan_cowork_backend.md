# Plan: the CoWork backend

Branch `feat/cowork-backend`. Eight phases, one commit each.

Everything this plan reads already exists: `plugins/smoke/`, `src/cowork_evals/env.py`,
`src/cowork_evals/cowork.py` and `src/cowork_evals/docker/__init__.py`. It waits on nothing.

## Scope

The layer above the CoWork driver. It reads the same case tree as every other backend,
submits each case's prompt through the driver, grades what the session produced, and writes
the same `aggregate-result.json` v1 document.

The driver is not rewritten. It submits one prompt and returns one document, which is its
scope in [`../docs/cowork_driver.md`](../docs/cowork_driver.md). Repeating a case,
grading it, aggregating across its runs and writing the document are this layer's work. The
one change to it is phase 6's: `_recent` becomes public as `recent()`, so the trailing
24-hour window is implemented once and not twice.

`claude plugin eval` is not in this path. That harness loads a plugin, and only Claude Code
knows how.

| Builds                                | Is                                                              |
| ------------------------------------- | ----------------------------------------------------------------- |
| `src/cowork_evals/cases.py`           | The case reader. Backend-neutral, and `plan_cli.md` validates over it |
| `src/cowork_evals/grader.py`          | The four structural graders over the driver's result document   |
| `src/cowork_evals/judge.py`           | The `claude -p` judge behind `llm` and `baseline`               |
| `src/cowork_evals/results.py`         | The v1 `aggregate-result.json` document                          |
| `src/cowork_evals/cowork_backend.py`  | The skip rule, `plan(target)` and `run(target, output_dir)`      |
| `tests/unit/test_cases.py`, `tests/unit/test_grader.py`, `tests/unit/test_judge.py`, `tests/unit/test_results.py`, `tests/unit/test_cowork_backend.py`, `tests/integration/test_judge.py`, `tests/integration/test_cowork_backend.py` | [`../tests/README.md`](../tests/README.md) |

References: the case format is [`../docs/eval_format.md`](../docs/eval_format.md), the
grader and document contracts are
[`../docs/claude_code/plugin_eval_reference.md`](../docs/claude_code/plugin_eval_reference.md),
and the skip rule is [`../docs/running_evals.md`](../docs/running_evals.md).

## The plugin under test is not loaded

The deep link carries a prompt. It does not install a plugin, and nothing on the host writes
into the VM's configuration. A CoWork run therefore exercises the plugin set already
deployed to the signed-in account.

A case path selects which cases run. It does not select which code runs. A local edit to a
skill is invisible to this backend until it is deployed. This plan builds no check for it,
because it is not verifiable from the host. Phase 8 writes it into
[`../docs/cowork_driver.md`](../docs/cowork_driver.md) and
[`../docs/approaches.md`](../docs/approaches.md).

## Out of scope

| Not built                                                                | Belongs to              |
| -------------------------------------------------------------------------- | ------------------------ |
| The `cowork_evals` command, `[project.scripts]`, option parsing           | `plan_cli.md`           |
| Scope naming, the run directory, `env.txt`, the `latest` symlink, pruning | `plan_cli.md`          |
| The gate, and any pass or fail decision                                   | `plan_cli.md`           |
| The case validator: the `<skill>` layer, the `plugins:` cross-check, an unknown frontmatter key | `plan_cli.md` |
| Walking a path that covers several plugin roots                           | `plan_cli.md`           |
| `report.html` on this backend                                             | nobody                  |
| Any eval over a shipped plugin, any suite, any cadence                    | the consumer repository |

The CoWork backend writes `aggregate-result.json` and nothing else. The gate reads only that
document. Phase 8 records the absence in the log layout.

## Constraints

- Python 3.14, ruff `target-version = "py314"`.
- Reuse before writing. `python-frontmatter` parses the `---` blocks, `PyYAML` parses
  `case.yaml`, `re` matches patterns, `pathlib.PurePath.full_match` matches file globs, and
  `subprocess` runs `claude`. Nothing in this plan writes a parser, a glob engine or an HTTP
  client.
- `python-frontmatter` is the one dependency added. `PyYAML` and `python-dotenv` are already
  in `pyproject.toml`.
- Judged graders call `claude -p`. No SDK, and no second credential route.
- No mock, fake, stub, patch or injected seam. The unit tier reads hand-written case trees
  and hand-written driver result documents from disk and asserts over literals.
- A fixture carries no account identifier, profile identifier, session identifier or real
  prompt. [`../README.md`](../README.md).
- One exception type is added, `CaseError` in `cases.py`. The ceiling refusal reuses
  `CoWorkError(2, ...)`. [`../docs/cli.md`](../docs/cli.md) maps a code 2 raised while
  running a case onto exit 1 and only a preflight code 2 onto exit 3, so a refusal raised
  before any case submits is not covered by that table today. Phase 8 corrects the row.
  Nothing returns an error code, calls `sys.exit` or prints.

## Phase 1: The case reader

`src/cowork_evals/cases.py`. It parses what
[`../docs/eval_format.md`](../docs/eval_format.md) defines, the way the harness parses it,
so both backends see the same case set.

- [ ] Add `python-frontmatter` to `dependencies` in `pyproject.toml`. It splits the `---`
      block from the body and returns empty metadata when there is no block.
- [ ] Frozen `Grader`: `name`, `type`, `weight`, `config`, `markdown`, `path`. `name`
      defaults to the filename without `.md`, `weight` to 1, and `config` is every other
      frontmatter key as authored.
- [ ] Frozen `Case`: `name`, `directory`, `prompt`, `graders`, `tags`, `source`,
      `frontmatter_keys`, `case_yaml_keys`, `path`. `source` is `prose`, `case_yaml` or
      `mixed`, which is the v1 document's field. The two key sets are the keys the files
      wrote out, which phase 2 reads.
- [ ] A `prompt.md` with no frontmatter raises `CaseError` naming the file.
- [ ] A grader file with empty metadata is ignored. The harness ignores it, and
      [`../docs/eval_format.md`](../docs/eval_format.md) records the trap.
- [ ] Read `case.yaml` when present, and keep the `context.*` keys it wrote.
- [ ] `discover(root, *, tags=(), case_glob=None)`: recurse, a directory holding `prompt.md`
      is a case, anything else is searched through, and the result is sorted by path.
      `tags` matches the frontmatter `tags`, `case_glob` globs the case directory name.
      Those are `--tag` and `--case` in [`../docs/cli.md`](../docs/cli.md).
- [ ] `plugin_root(target)`: the nearest ancestor holding `.claude-plugin/plugin.json`, and
      `CaseError` when there is none.
- [ ] Move `plugin_root` here from `src/cowork_evals/docker/__init__.py:60` and point the
      container backend at this one. It raises `CaseError` here, so the container backend
      wraps it and still raises `DockerError`, which leaves `tests/unit/test_docker.py`
      unchanged.
- [ ] `tests/unit/test_cases.py` over hand-written trees under `tests/data/cases/`: every
      frontmatter key, no optional key, a grader with no `---` block, a `case.yaml`, a
      grouping directory that is not a case, a tag filter, a case glob, and a missing
      plugin root.

## Phase 2: The skip rule

`src/cowork_evals/cowork_backend.py`, as `skips(case, plugin_root)` returning one reason
string per unhonourable key. `cases.py` stays backend-neutral. The rule is in
[`../docs/running_evals.md`](../docs/running_evals.md): a written-out key is honoured when
this backend's behaviour already satisfies it, and skipped otherwise. It reads written keys,
never merged defaults.

| Written in the case                             | On CoWork                                       |
| ------------------------------------------------- | ------------------------------------------------- |
| `runs: N`                                       | Honoured. Submit the prompt N times            |
| `timeout_seconds`                               | Honoured as that case's driver `run_timeout`   |
| `arm: with-only` or `arm: both`                 | Honoured. One arm runs, it is the with-arm, and it is scored |
| `max_turns`                                     | Skipped. No turn cap reaches a session         |
| `model`, `allowed_tools`, `append_system_prompt`, `env` | Skipped. The session decides           |
| Any `context.*` in `case.yaml`                  | Skipped. Nothing stages files into the VM      |
| An `evals/mocks/` directory in the plugin root  | Skipped, every case in that plugin. The harness applies stand-ins suite-wide and the MCP servers here are real |
| A grader with `target` or `focus` of `mock_calls` | That grader is skipped, and the case still runs |
| An `llm` or `baseline` grader with an image focus | That grader is skipped. The judge is one text call and cannot show an image |

- [ ] Implement the table. A skipped grader is excluded from the run's `score`, so a case
      does not fail for a grader that was never asked.
- [ ] Correct the four statements that pin one run per case: the skip table in
      [`../docs/running_evals.md`](../docs/running_evals.md), the sentence `It pins one run
      per case` in the same file, the `runs`, `timeout_seconds` and `arm:` rows in
      [`../docs/approaches.md`](../docs/approaches.md), and the `--runs N` row in
      [`../docs/cli.md`](../docs/cli.md), which refuses the option today. Skipping `arm:`
      would leave the gate red for every case that carries it for portability.
- [ ] Add a `--timeout-seconds N` row to the option table in
      [`../docs/cli.md`](../docs/cli.md): accepted on `--cowork`, refused on `--venv` and
      `--docker`. `claude plugin eval` has no timeout flag, so there is nothing to map it
      onto there, and only this backend sets a per-case `run_timeout` itself. It is the
      sibling of `--runs N`, and `plan_cli.md` phase 5 already reads the table expecting
      both.
- [ ] `tests/unit/test_cowork_backend.py`: one assertion per row above.

## Phase 3: The structural graders

`src/cowork_evals/grader.py`. One `Case` and one driver result document in, one result per
grader out. It submits nothing and re-runs over a stored document for free. The semantics
are the grader table in
[`../docs/claude_code/plugin_eval_reference.md`](../docs/claude_code/plugin_eval_reference.md),
and matching them exactly is what makes a case portable between backends.

- [ ] Frozen `GraderResult`: `name`, `passed`, `weight`, `explanation`, and optional
      `judge_votes`, `evidence`, `skipped`, `skip_reason`. It serializes to the run-level
      grader object. `withOnly` is always `false`, because `ablation` is `none` here and
      nothing is dropped for an arm. `scored` is `not skipped`, which widens the
      reference's `scored` = `not withOnly` to the one other exclusion this backend has.
      Phase 5 counts it as a departure, and phase 8 records it.
- [ ] `resolve_target(document, spec, case_dir, session_dir)`: `last_message` to
      `final_text`, `trace` to one JSON object per line, `json.dumps` of every entry of
      `turns` followed by every entry of `tool_calls` in the order the document lists them,
      `files` to `outputs`, and `{source: file, path}` to that path under the session's
      `outputs/` directory, which is the one place a produced file is readable from the
      host. An unreadable file is a failed grader carrying the reason, never an
      exception.
- [ ] `regex`: the pattern is a JavaScript RegExp source. Compile it with `re`, mapping
      `i`, `m` and `s` onto `re.I`, `re.M` and `re.S`, adding `re.ASCII` unless the flags
      carry `u` or `v`, and ignoring `d`, `g` and `y`. `re.ASCII` is what makes `\d` and
      `\w` ASCII-only as they are in JavaScript. A pattern `re` cannot compile is a failed
      grader naming the error. Record the divergence in `docs/` in phase 8.
- [ ] `regex` `match`: `contains` (default), `not_contains`, and `count:N` which requires
      **exactly** N matches.
- [ ] `tool_used`: count calls in `tool_calls` whose `name` is `tool` and whose input,
      JSON-encoded, matches `input_match`. Pass when the count is within `min` (default 1)
      and `max` (default unlimited). `min: 0, max: 0` passes on zero calls.
- [ ] `tool_order`: `before` and `after` are each a tool name or `{tool, input_match}`.
      Both must have been called, and the **first** matching `before` call must precede the
      **first** matching `after` call. It reads `tool_calls`, not `tool_names`, because of
      the object form. Correct the `tool_order` row in
      [`../docs/cowork_driver.md`](../docs/cowork_driver.md), which names `tool_names`.
- [ ] `file_exists`: match `path` against each entry of `outputs` with
      `pathlib.PurePath.full_match`, which is the harness's glob semantics, `**/` at any
      depth and `*` within a segment. `exists` defaults to true.
- [ ] A run with no scored graders scores 0, which is the reference's rule.
- [ ] `explanation` is mechanical, in the harness's register: `matched Alex`,
      `Skill called 1x (expected 1 or more)`.
- [ ] That trace rendering is this backend's and is not the harness's `trace.jsonl`, so a
      `regex` grader on `target: trace` is not portable between backends. Every other
      target is. Record it in `docs/` in phase 8.
- [ ] An unknown grader type is a failed grader naming the type, not an exception.
- [ ] `tests/unit/test_grader.py` over hand-written documents under `tests/data/documents/`:
      every grader type, every target, all three `match` values, the `min: 0, max: 0` idiom,
      the `{tool, input_match}` form of `tool_order`, a `**/` glob, an unreadable file, an
      uncompilable pattern, and an unknown type.

## Phase 4: The judge

`src/cowork_evals/judge.py`. `llm` and `baseline`, three votes, majority. The model is
`EVAL_JUDGE_MODEL` through `src/cowork_evals/env.py`. A judged grader never gates, which is
the gate table in [`../docs/running_evals.md`](../docs/running_evals.md), so nothing here
raises.

- [ ] `judge_argv(model)`: `claude -p --output-format json --model <model>
      --strict-mcp-config`. `--strict-mcp-config` keeps the developer's MCP servers out of a
      text vote. The composed text goes on stdin, so a long trace never reaches the
      argument list.
- [ ] Compose one text: the rubric, the material, and a closing instruction to answer with
      exactly `PASS` or `FAIL`. Send the same text three times.
- [ ] Take the reply and the spend from the `--output-format json` document. The spend fills
      `judgeCostUsd`.
- [ ] The grader passes on two or more `PASS` votes. A reply that is neither word is a lost
      vote and is not a `PASS`. Three lost votes is a failed grader naming the reason.
- [ ] `llm` reads `criteria` and `focus`, resolved through phase 3. `target` on an `llm`
      grader is ignored, because the harness ignores it.
- [ ] `baseline` reads `baseline_file` under the case directory and `criteria`.
- [ ] Refuse a file that is not UTF-8 text and fail the grader naming it. An image focus is
      a skip rather than a failure, per phase 2, because the harness grades it and this
      backend cannot.
- [ ] `explanation` is `judge votes: PASS FAIL PASS`. `evidence` is what the judge was
      shown, truncated at 2000 characters.
- [ ] `CLAUDE_CODE_WALNUT_SPIRE` is not exported. It gates `claude plugin eval`, and this is
      `claude -p`.
- [ ] `tests/unit/test_judge.py`: `judge_argv`, the composed text for both grader types,
      vote counting from recorded reply documents, the lost-vote paths, and the non-text
      refusal. Nothing here starts a process.
- [ ] `tests/integration/test_judge.py`, marked `live`: one rubric with a string that must
      pass and one that must fail. It proves the stdin invocation and the reply parsing. Six
      short calls, no CoWork session, no ceiling entry. Neither marker needs a change:
      `tests/integration/conftest.py` marks the directory `integration`, and
      `pyproject.toml`'s `live` marker already reads `submits a real run` and covers an
      eval run as well as a CoWork one.

## Phase 5: The v1 result document

`src/cowork_evals/results.py`. The same document the harness writes, so one gate covers
every backend. The contract is
[`../docs/claude_code/plugin_eval_reference.md`](../docs/claude_code/plugin_eval_reference.md).
It is additive-only, which is what permits the three added fields and the one widened
one.

- [ ] Canonical camelCase, `schemaVersion: 1`, `partial: false`, `startedAt`,
      `durationSeconds` and `costUsd` for the suite.
- [ ] `claudeVersion` is the host `claude --version`. No CLI ran the suite on this backend,
      and that version is the judge's. Phase 8 says so.
- [ ] `costUsd` is the judge spend and nothing else. A CoWork run is billed to the account
      and is not observable from the host. It is never estimated. Phase 8 says so.
- [ ] `suite`: `root` at the plugin root, `ablation: "none"`, `threshold: 0`, `judgeModel`,
      `plugins` from `.claude-plugin/plugin.json` with the folder basename as the `name`
      fallback, and `caseFilter` and `tagFilters` when given.
- [ ] Per case: `name`, `dir` relative to `suite.root`, `source`, `promptMarkdown`,
      `runsPerCase` as the declared `runs` and never the override, `timeoutSeconds` as the
      timeout it ran under, the grader definitions, `arms.with` with one entry per run, and
      `aggregates`. No `arms.without`.
- [ ] Per run: `score` as the weighted fraction of scored graders that passed, `passed` when
      `score` is 1.0, `turns` from the document's assistant turns, `costUsd` and
      `judgeCostUsd` both the judge spend, `startedAt` from `submitted_at`,
      `durationSeconds` from `collected_at` minus `submitted_at`, `error`, `tracePath` at
      the session transcript, and `skippedPaidGraders: false`.
- [ ] Case `aggregates`: `score` as the mean run score, `passRate` as the fraction of runs
      scoring 1.0. Above `runs: 1` that rate is the flake rate
      [`../docs/running_evals.md`](../docs/running_evals.md) makes a precondition for
      automating a suite.
- [ ] Three added fields and one widened field, and no other departure: `skipped` and
      `skipReason` on a case, the same pair on a grader result, `cowork: {sessionDir}` on a
      run, and `scored: false` on a skipped grader result. The gate in `plan_cli.md` reads
      `skipped`.
- [ ] A skipped case carries `skipped: true`, an empty `arms.with`, `score` 0 and
      `passed: false`, and is never counted in `aggregates.casesPassed`.
- [ ] A run the driver raised on carries `error` as the code and message, `score` 0 and no
      graders.
- [ ] Suite `aggregates`: `casesTotal`, `casesPassed`, `overallScore`, `overallPassRate`.
      No `meanDelta`: there is no baseline arm.
- [ ] `tests/unit/test_results.py`: build a document from hand-written cases and driver
      documents and assert every field. One case passed, one failed, one skipped, one
      errored, and one with `runs: 2` where the two runs disagree.

## Phase 6: The backend function

Back to `src/cowork_evals/cowork_backend.py`. It takes a case path and an output directory
and returns the path to the `aggregate-result.json` it wrote. That contract is
[`README.md`](README.md).

- [ ] `run(target, output_dir, *, config=None, runs=None, timeout_seconds=None, tags=(),
      case_glob=None)`: resolve the plugin root, discover the cases, run each, write the
      document, return its path.
- [ ] `runs` and `timeout_seconds` replace every case's declared value, and are `--runs N`
      and `--timeout-seconds N` in [`../docs/cli.md`](../docs/cli.md). Neither multiplies
      what the case declared. The document still records the declared `runs` as
      `runsPerCase`, so it says what the case asked for while `arms.with` says what ran,
      and `timeoutSeconds` records the timeout the run actually ran under.
- [ ] `plan(target, *, config=None, runs=None, timeout_seconds=None, tags=(),
      case_glob=None)`: the same resolution and the same arithmetic, returning per case its
      name, its skip reasons, its effective run count and its effective timeout, with the
      ceiling numbers. It submits nothing. `run` calls it, and so does `--dry-run --cowork`
      in `plan_cli.md` phase 6, which prints exactly those and would otherwise re-derive
      them.
- [ ] A target covering more than one plugin root raises `CaseError`.
      [`../docs/cli.md`](../docs/cli.md) makes that a usage error, and the CLI is what exits.
- [ ] Rename `_recent` to `recent()` in `src/cowork_evals/cowork.py` and make it public. It
      is the count of submissions in the trailing 24 hours, and it already owns
      `CEILING_WINDOW` and the timestamp parsing. The backend calls it rather than
      re-deriving the window over `history()`. `tests/unit/test_cowork.py` gains one
      assertion over it against a hand-written run log, and phase 8 adds the row to the API
      table.
- [ ] Before submitting anything, sum the effective run count over the cases that will
      submit, which is `runs` where it was given and the declared `runs` otherwise, and
      raise `CoWorkError(2, ...)` when that total plus `CoWork.recent()` is above
      `max_runs`. A suite that stops halfway has already spent what it spent.
- [ ] A skipped case submits nothing and costs no ceiling entry.
- [ ] Per run: `CoWork.run(case.prompt)`, then phase 3, then phase 4 for judged graders.
      Each run is its own session and its own document.
- [ ] The `CoWork` for a case carries that case's effective `timeout_seconds` as
      `run_timeout`, which is the override where one was given.
      `Config` is frozen, so a differing timeout is a differing `CoWork`. The ceiling and the
      run log are files and still count across instances.
- [ ] A `CoWorkError` is caught per run and becomes that run's `error`. The remaining runs of
      that case still fire, and the suite continues.
- [ ] Code 7, the run timeout, is caught and then collected. The error carries
      `session_dir`, so `collect` reads the session as it stands and the run is graded on
      what it produced, with `error` recording the timeout. That is what the harness does.
      The CoWork session is not stopped and keeps running in the VM.
- [ ] Cases run in sequence, and the runs of a case run in sequence. There is one desktop
      application and one composer.
- [ ] Write `<output_dir>/aggregate-result.json`. Name no run directory, write no `latest`
      symlink, write no `env.txt`, prune nothing, print nothing, decide no pass or fail.
- [ ] `tests/unit/test_cowork_backend.py`: the multi-plugin refusal, `plan()` over a
      hand-written case tree with and without each override, the ceiling arithmetic against
      a hand-written run log, and the document a suite of skipped cases produces. Nothing
      here starts a session.

## Phase 7: The integration tier, and the measurements

`tests/integration/test_cowork_backend.py`. It needs a signed-in CoWork, the desktop
application running, the macOS Accessibility grant, and `cowork_evals.yaml` naming the
active profile. A missing precondition fails the test and never skips it.

The fixture is `plugins/smoke/evals/plugin/python-version/`, which exists. It
carries no skill, writes `runs: 1`, and its prompt asks for `python3 -V`, so it is
answerable by a session with no plugin loaded, which is the situation this backend is always
in. Its one `regex` grader matches `Python 3\.10\.12`, the string
[`../docs/runtime.md`](../docs/runtime.md) records for the session interpreter and the
string the container asserts too. Nothing about the fixture changes here.

Two facts about the grader mapping cannot be read from a file. Both are measured against the
sessions already in the profile before anything is fired, because that costs nothing.

- [ ] Assert the reader finds `plugins/smoke/`'s case, resolves its plugin root and reports
      no skip. No session.
- [ ] Assert `claude --version` is reachable, naming the reason when it is not. The judge
      and `claudeVersion` both need it.
- [ ] Walk every session in the configured profile through `collect`, and record whether any
      transcript carries a `Skill` `tool_use` record and whether any session holds files
      under `outputs/`. A session with no assistant text raises code 8, which the walk
      catches and steps over, as `tests/integration/test_cowork.py:37` already does. Marked
      `integration`, not `live`: it submits nothing.
- [ ] For each of the two that the profile has no example of, fire one case that provokes
      it: a prompt asking the session to use any skill it has, and a prompt asking it to
      write a named file. Marked `live`. A profile that already shows both costs nothing
      here.
- [ ] Fire `plugins/smoke/` through `run()` and assert the document says the case passed.
      Marked `live`. One VM boot, one ceiling entry, one permanent session.

| Measurement                                        | If it fails                                                                    |
| -------------------------------------------------- | -------------------------------------------------------------------------------- |
| A transcript carries a `Skill` `tool_use` record  | The skill-fired idiom in [`../docs/eval_format.md`](../docs/eval_format.md) cannot be graded here. `docs/cowork_driver.md` records that and drops the row. Phase 3 is unchanged: `tool_used` still grades every other tool |
| A session writes a produced file under `outputs/` | `file_exists` cannot be graded here. `docs/cowork_driver.md` and `docs/approaches.md` record it and drop the row |

- [ ] Record in `docs/cowork_driver.md`: the capture date, the wall clock of one case, the
      ceiling entries one suite costs, and both measurements. No machine name, no user name,
      no home directory path, no profile name.

## Phase 8: Documentation

Nothing durable may survive only in this file.

- [ ] `docs/cowork_driver.md`: the precondition that the plugin under test is already
      deployed, the three added fields and the widened `scored`, the judge through
      `claude -p`, the JavaScript to Python regex divergence, the `target: trace` rendering
      and that a regex over it is not portable, `recent()` in the API table, what
      `claudeVersion` and `costUsd` mean here, the corrected `tool_order` row, and the
      phase 7 measurements.
- [ ] `docs/approaches.md`: the same precondition, and the rows phase 2 corrected.
- [ ] `docs/cli.md`: `--runs N` accepted on `--cowork`, `--timeout-seconds N` added to the
      option table and accepted on every backend, `claude` on `PATH` added to the
      `--cowork` preflight row because the judge and `claudeVersion` both need it, the
      driver-code mapping row corrected so a code 2 raised before any case submits is exit 3
      and not exit 1, the ceiling arithmetic that refuses a suite too large for `max_runs`,
      and that host spend here is the judge alone while the account's own spend is unbounded
      from this side.
- [ ] `docs/running_evals.md`: mark the CoWork backend built, and record that a CoWork run
      writes `aggregate-result.json` and no `report.html`.
- [ ] `docs/library.md`: the five new modules, and `python-frontmatter` in the dependency
      list.
- [ ] `docs/eval_format.md`: only if phase 7 dropped the skill-fired idiom or `file_exists`
      on this backend, in which case that file points at `docs/cowork_driver.md`.
- [ ] `tests/README.md`: a row per new test file, and the integration tier's preconditions.
- [ ] `plugins/README.md`: `smoke` serves this backend as well.
- [ ] Re-read every touched file for a statement this plan made false.
- [ ] `plans/README.md`: mark this plan `implemented`.
