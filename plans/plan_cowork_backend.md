# Plan: the CoWork backend

Branch `feat/cowork-backend`. Eight phases.

Everything this plan reads already exists: `plugins/smoke/`, `src/cowork_evals/config.py`,
`src/cowork_evals/cowork.py` and `src/cowork_evals/docker/__init__.py`. It waits on nothing.

## Scope

The layer above the CoWork driver. It reads the same case tree as every other backend,
submits each case's prompt through the driver, grades what the session produced, and writes
the same `aggregate-result.json` v1 document.

The driver is not rewritten. It submits one prompt and returns one session document, which
is its scope in [`../docs/cowork_driver.md`](../docs/cowork_driver.md). Repeating a case,
grading it, aggregating across its runs and writing the result document are this layer's
work. The one change to it is phase 6's: `_recent` becomes public as `recent()`, so the
trailing 24-hour window is implemented once and not twice.

`claude plugin eval` is not in this path. That harness loads a plugin, and only Claude Code
knows how.

| Builds                                | Is                                                              |
| ------------------------------------- | ----------------------------------------------------------------- |
| `src/cowork_evals/cases.py`           | The case reader. Backend-neutral, and `plan_cli.md` validates over it |
| `src/cowork_evals/grader.py`          | The four structural graders over the session document           |
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
- `python-frontmatter` is the one dependency added. `PyYAML` is already in `pyproject.toml`.
- Judged graders call `claude -p`. No SDK, and no second credential route.
- No mock, fake, stub, patch or injected seam. The unit tier reads hand-written case trees
  and hand-written session documents from disk and asserts over literals.
- A fixture carries no account identifier, profile identifier, session identifier or real
  prompt. [`../README.md`](../README.md).
- One exception type is added, `CaseError` in `cases.py`. The ceiling refusal reuses
  `CoWorkError(2, ...)`, which [`../docs/cli.md`](../docs/cli.md) already maps onto exit 3.
  Nothing returns an error code, calls `sys.exit` or prints.

## Phase 1: The case reader

`src/cowork_evals/cases.py`. It parses what
[`../docs/eval_format.md`](../docs/eval_format.md) defines, the way the harness parses it,
so both backends see the same case set.

- [x] Add `python-frontmatter` to `dependencies` in `pyproject.toml`. It splits the `---`
      block from the body and returns empty metadata when there is no block.
- [x] Frozen `Grader`: `name`, `type`, `weight`, `config`, `markdown`, `path`. `name`
      defaults to the filename without `.md`, `weight` to 1, and `config` is every other
      frontmatter key as authored.
- [x] Frozen `Case`: `name`, `directory`, `prompt`, `graders`, `tags`, `source`,
      `frontmatter_keys`, `case_yaml_keys`, `path`. `name` defaults to the case directory
      name, which is the harness's rule for a prose case. `source` is `prose` or `mixed`,
      which is the v1 document's field. Discovery needs a `prompt.md`, so `case_yaml`
      cannot occur here. The two key sets are the keys the files wrote out, which phase 2
      reads.
- [x] A `prompt.md` with no frontmatter is read, not refused: empty metadata, the body is
      the prompt, and `name` is the directory name. Its missing keys are the validator's,
      in `plan_cli.md` phase 1, which cannot report what the reader refused to build.
      `CaseError` is for a tree that cannot be read at all: unparsable YAML, or no plugin
      root.
- [x] A grader file with empty metadata is ignored, as the harness ignores it.
      [`../docs/eval_format.md`](../docs/eval_format.md) records the trap.
- [x] Read `case.yaml` when present, and keep the `context.*` keys it wrote.
- [x] `discover(root, *, tags=(), case_glob=None)`: recurse, a directory holding `prompt.md`
      is a case, anything else is searched through, and the result is sorted by path.
      `tags` matches the frontmatter `tags`, `case_glob` globs the case `name`, which is
      what the harness globs and which defaults to the directory name. Those are `--tag`
      and `--case` in [`../docs/cli.md`](../docs/cli.md). Phase 8 corrects
      [`../docs/eval_format.md`](../docs/eval_format.md), which says `--case` globs the
      directory name.
- [x] `plugin_root(target)`: the nearest ancestor holding `.claude-plugin/plugin.json`, and
      `CaseError` when there is none.
- [x] Move `plugin_root` here from `src/cowork_evals/docker/__init__.py:95`. The docker
      module keeps a wrapper of the same name, which catches `CaseError` and raises
      `DockerError`, so `tests/unit/test_docker.py:217-229` still imports it from there and
      still asserts `DockerError`.
- [x] `tests/unit/test_cases.py` over hand-written trees under `tests/data/cases/`: every
      frontmatter key, no optional key, a `prompt.md` with no `---` block, a grader with no
      `---` block, a `case.yaml`, a grouping directory that is not a case, a tag filter, a
      case glob against a `name` that differs from the directory name, and a missing plugin
      root.

## Phase 2: The skip rule

`src/cowork_evals/cowork_backend.py`, as `skips(case, plugin_root)` returning a frozen
`Skips`: `case`, the reasons the case submits nothing, and `graders`, a mapping of grader
name to the reason that grader is not scored. The two are never one list. A case skip
submits nothing and leaves `arms.with` empty; a grader skip runs the case and drops that
grader from the score. Phases 5 and 6 both read the difference.

`cases.py` stays backend-neutral. The rule is in
[`../docs/running_evals.md`](../docs/running_evals.md): a written-out key is honoured when
this backend's behaviour already satisfies it, and skipped otherwise. It reads written keys,
never merged defaults.

| Written out                                             | Level  | On CoWork                                       |
| --------------------------------------------------------- | ------ | ------------------------------------------------- |
| `runs: N`                                               | case   | Honoured. Submit the prompt N times             |
| `timeout_seconds`                                       | case   | Honoured as that case's driver `run_timeout`    |
| `arm: with-only` or `arm: both`                         | grader | Honoured. One arm runs, it is the with-arm, and every grader is scored in it |
| `max_turns`                                             | case   | The case is skipped. No turn cap reaches a session |
| `model`, `allowed_tools`, `append_system_prompt`, `env` | case   | The case is skipped. The session decides        |
| Any `context.*` in `case.yaml`                          | case   | The case is skipped. Nothing stages files into the VM |
| A `mocks/` directory at or above the case, from `evals/` down | suite, group or case | The case is skipped. Stand-ins are the harness's, and the MCP servers here are real |
| `target` or `focus` of `mock_calls`                     | grader | That grader is skipped, and the case still runs |

The `mocks/` row reads the three layers
[`../docs/claude_code/plugin_eval_reference.md`](../docs/claude_code/plugin_eval_reference.md)
defines, so `evals/mocks/` skips every case in the plugin and a case's own `mocks/` skips
that case alone.

The last row is the only grader skip this function decides. The other one, an `llm` grader
whose focus turns out to be an image, is read from the file's bytes, which exist only after
the run, so phase 4 decides it and records it the same way.

- [x] Implement the table. A skipped grader is excluded from the run's `score`, so a case
      does not fail for a grader that was never asked.
- [x] Correct every statement that pins one run per case: the skip table in
      [`../docs/running_evals.md`](../docs/running_evals.md), the sentence `It pins one run
      per case` in the same file, the row in
      [`../docs/approaches.md`](../docs/approaches.md) that lumps `runs`, `max_turns` and
      `timeout_seconds` together, which splits because `max_turns` still skips, and the
      `--runs N` row in [`../docs/cli.md`](../docs/cli.md), which refuses the option today.
      The `arm:` row in `approaches.md` becomes honoured: skipping it would leave the gate
      red for every case that carries it for portability.
- [x] Add a `--timeout-seconds N` row to the option table in
      [`../docs/cli.md`](../docs/cli.md): accepted on `--cowork`, refused on `--venv` and
      `--docker`. `claude plugin eval` has no timeout flag, so there is nothing to map it
      onto there, and only this backend sets a per-case `run_timeout` itself. It is the
      sibling of `--runs N`, and `plan_cli.md` phase 5 already reads the table expecting
      both.
- [x] `tests/unit/test_cowork_backend.py`: one assertion per row above.

## Phase 3: The structural graders

`src/cowork_evals/grader.py`. One `Case` and one session document in, one result per grader
out. It submits nothing and re-runs over a stored session document for free. The semantics
are the grader table in
[`../docs/claude_code/plugin_eval_reference.md`](../docs/claude_code/plugin_eval_reference.md),
and matching them exactly is what makes a case portable between backends.

- [ ] Frozen `GraderResult`: `name`, `passed`, `weight`, `explanation`, and optional
      `judge_votes`, `evidence`, `skipped`, `skip_reason`. It serializes to the run-level
      grader object. `withOnly` is always `false`, because `ablation` is `none` here and
      nothing is dropped for an arm. `scored` is `not skipped`, which widens the
      reference's `scored` = `not withOnly` to the one other exclusion this backend has.
      Phase 5 counts it as a departure, and phase 8 records it.
- [ ] One path convention for a produced file, and the driver does not change to get it.
      `outputs` in the session document is relative to the session directory, so every entry
      carries an `outputs/` prefix. This layer strips it once, and every grader that names a
      produced file names it relative to `outputs/`. That is what makes `path: report.md`
      mean here what it means under the harness, where the created-file list is relative to
      the workspace. Phase 8 records it.
- [ ] `resolve_target(document, spec)`: `last_message` to `final_text`, `trace` to one JSON
      object per line, `json.dumps` of every entry of `turns` followed by every entry of
      `tool_calls` in the order the document lists them, `files` to the stripped `outputs`
      list joined by newlines, and `{source: file, path}` to that path under
      `<session_dir>/outputs/`, which is the one place a produced file is readable from the
      host. The session directory is a field of the document. It returns text every time,
      because `regex` and the judge both read text and the reference makes `files`
      newline-separated. `file_exists` is the one grader that does not go through it: it
      reads the stripped list. An unreadable file, and a `path` that resolves outside
      `outputs/`, are each a failed grader carrying the reason, never an exception. The
      reference confines a file target to the workspace, and `outputs/` is the workspace
      here.
- [ ] `regex`: the pattern is a JavaScript RegExp source. Compile it with `re`, mapping
      `i`, `m` and `s` onto `re.I`, `re.M` and `re.S`, adding `re.ASCII` unless the flags
      carry `u` or `v`, and ignoring `d`, `g` and `y`. `re.ASCII` is what makes `\d` and
      `\w` ASCII-only as they are in JavaScript. A pattern `re` cannot compile is a failed
      grader naming the error. Every pattern in the format compiles through this one
      function, `input_match` on `tool_used` and `tool_order` included. Phase 8 records the
      divergence.
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
- [ ] `file_exists`: match `path` against each stripped `outputs` entry with
      `pathlib.PurePath.full_match`, which is the harness's glob semantics, `**/` at any
      depth and `*` within a segment. `exists` defaults to true.
- [ ] `explanation` is mechanical, in the harness's register: `matched Alex`,
      `Skill called 1x (expected 1 or more)`.
- [ ] An unknown grader type is a failed grader naming the type, not an exception.
- [ ] `tests/unit/test_grader.py` over hand-written session documents under
      `tests/data/documents/`: every grader type, every target, all three `match` values,
      the `min: 0, max: 0` idiom, the `{tool, input_match}` form of `tool_order`, a `**/`
      glob, a bare file name with no `**/`, which matches because the prefix is stripped, an
      unreadable file, a `path` escaping `outputs/`, an uncompilable pattern, and an unknown
      type.

The trace rendering is this backend's and is not the harness's `trace.jsonl`, so a `regex`
grader on `target: trace` is not portable between backends. Every other target is. Phase 8
records it.

## Phase 4: The judge

`src/cowork_evals/judge.py`. `llm` and `baseline`, three votes, majority. The model is the
caller's `judge_model` where one was given, and `eval.judge_model` from
`src/cowork_evals/config.py` otherwise. [`../docs/cli.md`](../docs/cli.md) accepts
`--judge-model M` on this backend, so phase 6 carries it down and phase 5 records it as
`suite.judgeModel`. A judged grader never gates, which is the gate table in
[`../docs/running_evals.md`](../docs/running_evals.md), so nothing here raises.

- [ ] `judge_argv(model)`: `claude -p --output-format json --model <model>
      --strict-mcp-config`. `--strict-mcp-config` keeps the developer's MCP servers out of a
      text vote. The composed text goes on stdin, so a long trace never reaches the
      argument list.
- [ ] Compose one text: the rubric, the material, and a closing instruction to answer with
      exactly `PASS` or `FAIL`. Send the same text three times. The material is truncated to
      100000 characters, head and tail kept, which is what the harness shows a judge.
- [ ] Take the reply and the spend from the `--output-format json` document. The spend fills
      `judgeCostUsd`.
- [ ] The grader passes on two or more `PASS` votes. A reply that is neither word is a lost
      vote and is not a `PASS`. Three lost votes is a failed grader naming the reason.
- [ ] `llm` reads `criteria` and `focus`, resolved through phase 3. `target` on an `llm`
      grader is ignored, because the harness ignores it.
- [ ] `baseline` reads `baseline_file` under the case directory and `criteria`.
- [ ] Refuse a file that is not UTF-8 text and fail the grader naming it, except an image,
      which is a grader skip carrying its reason rather than a failure: the harness shows
      the judge the image and one text call cannot. It is detected from the file's bytes, as
      the harness detects it, so it is decided here and not in phase 2's `skips`. Phase 5
      writes it into the result document as any other grader skip.
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
      `pyproject.toml`'s `live` marker already reads `submits a real run`.

## Phase 5: The v1 result document

`src/cowork_evals/results.py`. The same document the harness writes, so one gate covers
every backend. The contract is
[`../docs/claude_code/plugin_eval_reference.md`](../docs/claude_code/plugin_eval_reference.md).
It is additive-only, which is what permits the three added fields and the one widened
one.

- [ ] Canonical camelCase, `schemaVersion: 1`, `partial: false`, `startedAt`,
      `durationSeconds` and `costUsd` for the suite. `partial` is always false: this backend
      never stops a suite part way, and the ceiling refusal in phase 6 happens before the
      first submission.
- [ ] `claudeVersion` is the host `claude --version`. No CLI ran the suite on this backend,
      and that version is the judge's. Phase 8 says so.
- [ ] `costUsd` is the judge spend and nothing else. A CoWork run is billed to the account
      and is not observable from the host. It is never estimated. Phase 8 says so.
- [ ] `suite`: `root` at the plugin root, `ablation: "none"`, `threshold: 0`, `judgeModel`,
      `plugins` from `.claude-plugin/plugin.json` with the folder basename as the `name`
      fallback, and `caseFilter` and `tagFilters` when given.
- [ ] Per case: `name`, `dir` relative to `suite.root`, `source`, `promptMarkdown`,
      `model`, `runsPerCase`, `timeoutSeconds` and `maxTurns` as the case's declared values
      and never an override, absent where the case declares none, the grader definitions,
      `arms.with` with one entry per run, and `aggregates`. No `arms.without`. One rule for
      all four: the reference makes them what the case asked for, and what actually ran is
      read from `arms.with` and from the run's `cowork` object.
- [ ] A grader definition carries `name`, `type`, `weight`, `graderMarkdown` on a judged
      grader, and `config` as the author wrote it with the defaults phase 3 applies filled
      in. `Grader.config` from phase 1 is the authored keys alone, so the filling in happens
      here.
- [ ] Per run: `score` is the weighted fraction of scored graders that passed, and 0 when
      there were none to score, which is the reference's rule and covers a case whose
      graders were all skipped and a case with no grader file at all. `passed` when `score`
      is 1.0.
- [ ] The rest of a run: `turns` from the session document's assistant turns, `costUsd` and
      `judgeCostUsd` both the judge spend, `startedAt` from `submitted_at`,
      `durationSeconds` from `collected_at` minus `submitted_at`, `error`, `tracePath` at
      the session transcript, and `skippedPaidGraders: false`.
- [ ] Two of those read a driver field that can be `None`: `submitted_at`, when the audit
      record carries no timestamp, and `transcript`, when the session has no transcript
      directory. `startedAt` and `tracePath` are then absent, and `durationSeconds` is
      absent rather than computed against a missing start. Every field but `error` is absent
      rather than null, which is the reference's rule.
- [ ] Case `aggregates`: `score` as the mean run score, `passRate` as the fraction of runs
      scoring 1.0. Above `runs: 1` that rate is the flake rate
      [`../docs/running_evals.md`](../docs/running_evals.md) makes a precondition for
      automating a suite.
- [ ] Three added fields and one widened field, and no other departure: `skipped` and
      `skipReason` on a case, the same pair on a grader result,
      `cowork: {sessionDir, timeoutSeconds}` on a run, and `scored: false` on a skipped
      grader result. `cowork.timeoutSeconds` is the timeout that run ran under, which is the
      override where one was given, and it is the one place an effective value is recorded.
      `cowork.sessionDir` is what re-grades a stored run without submitting again. The gate
      in `plan_cli.md` reads `skipped`.
- [ ] A skipped case carries `skipped: true`, `skipReason`, an empty `arms.with`, and
      `aggregates` of `score` 0 and `passRate` 0. A case has no `score` and no `passed` of
      its own in v1; those two are run fields.
- [ ] A run the driver raised on carries `error` as the code and message, `score` 0 and no
      graders.
- [ ] Suite `aggregates`: `casesTotal`, `casesPassed`, `overallScore`, `overallPassRate`.
      No `meanDelta`: there is no baseline arm. A mean over nothing is 0, so a selection
      that matched no case writes `casesTotal: 0` and three zeros rather than dividing by
      zero. Whether an empty selection passes is the gate's, in `plan_cli.md`.
- [ ] `casesPassed` is the reference's rule, a case scoring at or above `threshold`, minus
      every skipped case. `threshold` is 0 here, so without that subtraction a skipped case
      would count as passed. It is the one behavioural departure beside the four above, and
      phase 8 records it. Nothing reads it to decide anything: the gate in `plan_cli.md`
      reads the grader results and `skipped`.
- [ ] `tests/unit/test_results.py`: build a result document from hand-written cases and
      session documents and assert every field. One case passed, one failed, one skipped,
      one errored, one with `runs: 2` where the two runs disagree, and an empty selection.

## Phase 6: The backend function

Back to `src/cowork_evals/cowork_backend.py`. It takes a case path and an output directory
and returns the path to the `aggregate-result.json` it wrote. That contract is
[`README.md`](README.md).

- [ ] `run(target, output_dir, *, config=None, runs=None, timeout_seconds=None,
      judge_model=None, tags=(), case_glob=None)`: resolve the plugin root, discover the
      cases, run each, write the result document, return its path.
- [ ] `judge_model` replaces `eval.judge_model` for every judged grader in the suite, and
      reaches phase 4 and `suite.judgeModel`. It is `--judge-model M` in
      [`../docs/cli.md`](../docs/cli.md), and the parameter is the only route that option
      has on this backend.
- [ ] `runs` and `timeout_seconds` replace every case's declared value, and are `--runs N`
      and `--timeout-seconds N` in [`../docs/cli.md`](../docs/cli.md). Neither multiplies
      what the case declared. The result document records the declared value on the case, as
      phase 5 sets it, so the case says what it asked for while `arms.with` says how many
      runs there were and each run's `cowork.timeoutSeconds` says what it ran under.
- [ ] `plan(target, *, config=None, runs=None, timeout_seconds=None, judge_model=None,
      tags=(), case_glob=None)`: the same resolution and the same arithmetic, returning a
      frozen `Plan`: one entry per case carrying its name, its `Skips`, its effective run
      count and its effective timeout, and three numbers, the submissions the suite will
      make, `CoWork.recent()` and `max_runs`.
      It submits nothing, so it carries the case skips and the grader skips phase 2 decides
      and not the image-focus skip phase 4 decides after a run. `run` calls it, and so does
      `--dry-run --cowork` in `plan_cli.md` phase 6, which prints exactly those and would
      otherwise re-derive them.
- [ ] A target covering more than one plugin root raises `CaseError`.
      [`../docs/cli.md`](../docs/cli.md) makes that a usage error, and the CLI is what exits.
- [ ] Rename `_recent` to `recent()` in `src/cowork_evals/cowork.py` and make it public. It
      is the count of submissions in the trailing 24 hours, and it already owns
      `CEILING_WINDOW` and the timestamp parsing. The backend calls it rather than
      re-deriving the window over `history()`. `tests/unit/test_cowork.py` gains one
      assertion over it against a hand-written run log, and phase 8 adds the row to the API
      table.
- [ ] Before submitting anything, sum the effective run count over the cases that will
      submit, which is `runs` where it was given, the declared `runs` where the case wrote
      one, and 1 otherwise, because a case that writes no `runs` key runs once here.
      [`../docs/running_evals.md`](../docs/running_evals.md) is where that rule lives. Raise
      `CoWorkError(2, ...)` when that total plus `CoWork.recent()` is above `max_runs`. A
      skipped case submits nothing and costs no ceiling entry.
- [ ] Per run: `CoWork.run(case.prompt)`, then phase 3, then phase 4 for judged graders.
      Each run is its own session and its own session document. Cases run in sequence, and
      the runs of a case run in sequence: there is one desktop application and one composer.
- [ ] The `CoWork` for a case carries that case's effective `timeout_seconds` as
      `run_timeout`, which is the override where one was given. `Config` is frozen, so a
      differing timeout is a differing `CoWork`. The ceiling and the run log are files and
      still count across instances.
- [ ] A `CoWorkError` is caught per run and becomes that run's `error`. The remaining runs of
      that case still fire, and the suite continues.
- [ ] Code 7, the run timeout, is caught and then collected. The error carries
      `session_dir`, so `collect` reads the session as it stands and the run is graded on
      what it produced, with `error` recording the timeout. That is what the harness does.
      The CoWork session is not stopped and keeps running in the VM. A `collect` that then
      raises code 8, meaning the session wrote no assistant text before the timeout, leaves
      the run with `error` naming the timeout, `score` 0 and no graders.
- [ ] Write `<output_dir>/aggregate-result.json`. The caller created that directory, as it
      does for `Docker.run`. Name no run directory, write no `latest` symlink, write no
      `env.txt`, prune nothing, print nothing, decide no pass or fail.
- [ ] `tests/unit/test_cowork_backend.py`: the multi-plugin refusal, `plan()` over a
      hand-written case tree with and without each override, the ceiling arithmetic against
      a hand-written run log, the result document a suite of skipped cases produces, and
      that `plugins/smoke/`'s case is found, resolves its plugin root and reports no skip.
      Nothing here starts a session, and none of it needs a profile.

## Phase 7: The integration tier, and the measurements

`tests/integration/test_cowork_backend.py`. It needs a signed-in CoWork, the desktop
application running, the macOS Accessibility grant, and `cowork_evals.yaml` naming the
active profile. A missing precondition fails the test and never skips it.

The fixture is `plugins/smoke/evals/plugin/python-version/`, which exists. It carries no
skill, writes `runs: 1`, and its prompt asks for `python3 -V`, so it is answerable by a
session with no plugin loaded, which is the situation this backend is always in. Its one
`regex` grader matches `Python 3\.10\.12`, the string
[`../docs/runtime.md`](../docs/runtime.md) records for the session interpreter and the
string the container asserts too. Nothing about the fixture changes here.

Nothing here asserts over the reader or the skip rule. Neither needs a profile or a session,
so both are phase 6's unit boxes.

Two facts about the grader mapping cannot be read from a file: whether a CoWork transcript
records a `Skill` `tool_use`, and whether a session writes files under `outputs/`. Both are
measured against the sessions already in the profile before anything is fired, because that
costs nothing.

- [ ] Assert `claude --version` is reachable, naming the reason when it is not. The judge
      and `claudeVersion` both need it.
- [ ] Walk every session in the configured profile through `collect`, and record both facts.
      A session with no assistant text raises code 8, which the walk catches and steps over,
      as `tests/integration/test_cowork.py:37` already does. Marked `integration`, not
      `live`: it submits nothing.
- [ ] Where the profile does not already show both, fire one prompt that provokes them:
      use any skill the session has, then write a named file. One run, marked `live`. A
      profile that shows both costs nothing here.
- [ ] Fire `plugins/smoke/` through `run()` and assert the result document says the case
      passed. Marked `live`. One VM boot, one ceiling entry, one permanent session.

| Measurement                                        | If it fails                                                                    |
| -------------------------------------------------- | -------------------------------------------------------------------------------- |
| A transcript carries a `Skill` `tool_use` record  | The skill-fired idiom in [`../docs/eval_format.md`](../docs/eval_format.md) cannot be graded here. `docs/cowork_driver.md` records that and drops the row. Phase 3 is unchanged: `tool_used` still grades every other tool |
| A session writes a produced file under `outputs/` | `file_exists` cannot be graded here. `docs/cowork_driver.md` and `docs/approaches.md` record it and drop the row |

- [ ] Record in `docs/cowork_driver.md`: the capture date, the wall clock of one case, the
      ceiling entries one suite costs, and both measurements. No machine name, no user name,
      no home directory path, no profile name.

## Phase 8: Documentation

Nothing durable may survive only in this file.

- [ ] `docs/cowork_driver.md`, what this backend does that the reference does not: the
      precondition that the plugin under test is already deployed, the three added fields
      and the widened `scored`, `casesPassed` excluding a skipped case, the judge through
      `claude -p`, what `claudeVersion` and `costUsd` mean here, and the JavaScript to
      Python regex divergence.
- [ ] `docs/cowork_driver.md`, the rows phase 3 made false: `tool_order`, which names
      `tool_names`; `{source: file, path}`, which names the session directory and not
      `outputs/`; the stripped `outputs/` prefix that makes a produced-file path mean the
      same here as under the harness; and that `target: trace` renders this backend's way,
      so a regex over it is not portable. The same section says the grader prints one result
      per grader, and nothing here prints. Add `recent()` to the API table.
- [ ] `docs/approaches.md`: the same deployment precondition, the rows phase 2 corrected,
      and the `llm` and `baseline` row, which says both are honoured and does not say an
      image focus is skipped.
- [ ] `docs/cli.md`: `--runs N` accepted on `--cowork`, the `--timeout-seconds N` row phase 2
      added, `claude` on `PATH` added to the `--cowork` preflight row because the judge and
      `claudeVersion` both need it, and that host spend here is the judge alone while the
      account's own spend is unbounded from this side.
- [ ] `docs/running_evals.md`: mark the CoWork backend built, record that a CoWork run
      writes `aggregate-result.json` and no `report.html`, and correct the `plugins/smoke/`
      status row, which calls the fixture the container backend's alone.
- [ ] `docs/library.md`: one row per new module in the ships table, `python-frontmatter`
      named beside `PyYAML` as a runtime dependency, and the `eval:` section's reader row,
      which names the `claude plugin eval` argument list alone and now also feeds this
      backend's judge.
- [ ] `docs/eval_format.md`: `--case` globs the case name, not the case directory name,
      which is what the harness does and what phase 1 built. The two differ only for a case
      whose `name` is not its directory name. And, only where phase 7 dropped the
      skill-fired idiom or `file_exists` on this backend, a pointer at
      `docs/cowork_driver.md`.
- [ ] `tests/README.md`: a row per new test file, and the integration tier's preconditions.
- [ ] `plugins/README.md`: `smoke` serves this backend as well.
- [ ] Re-read every touched file for a statement this plan made false.
- [ ] `plans/README.md`: mark this plan `implemented`.
