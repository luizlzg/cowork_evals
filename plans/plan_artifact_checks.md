# Artifact checks

## Summary

`cowork_evals` runs eval cases against a Claude Code plugin: a prompt goes to a model, the
model answers and sometimes writes a file, and graders decide whether what came back was
good. The graders are `claude plugin eval`'s, the Claude Code harness this package drives,
and they are five fixed types: match a regular expression, assert a tool was called, assert
two calls happened in order, assert a file was created, or send text to a judge model. None
of them can look inside a binary file. A skill that produces a spreadsheet can be asserted to
have created `totals.xlsx` and nothing further: the harness's judge refuses a `.xlsx` because
it is a ZIP archive, and a regular expression over compressed bytes matches nothing that
means anything. The same holds for `.pptx`, `.docx` and PDF, which are the artifacts the
skills under test produce most often.

This plan adds a second class of grader, evaluated by this package after a run rather than by
the harness. A check names a file the run produced, a conversion to apply to it, and an
assertion over the conversion: a workbook becomes CSV and is matched or judged, a deck
becomes one PNG per slide and is judged as images, a document becomes Markdown. A conversion
that fails is itself a failure, which is how a malformed artifact is caught without writing a
format validator for each type. After this plan a case can assert that a produced spreadsheet
holds the right numbers wherever in the sheet they sit, and that a produced deck looks right,
and those assertions decide the run's pass or fail beside the harness's own.

## References

`docs/eval_format.md` for the authoring contract a case is written to and the closed grader
table, `docs/running_evals.md` for pass and fail, the pinned flags, the log layout and the
status table, `docs/cowork_backend.md` for the judge and the additive-only result document,
`docs/docker.md` for the image and how a container is run, `docs/runtime.md` for what the
image carries, `docs/approaches.md` for what each backend honours, `docs/cli.md` for the verb
surface and the preflight, `tests/README.md` for the two tiers.

`cases.py` reads a case and holds the grader type tables. `grader.py` evaluates the four
structural types. `judge.py` is the `claude -p` judge behind `llm` and `baseline`.
`traces.py` collects each run's workspace onto the host and already rewrites the result
document. `results.py` writes the v1 document. `verdict.py` decides pass and fail over it.
`validate.py` is the case validator. `docker/__init__.py` holds the image, the tag and the
mount layout. `cli.py` holds `_run`, `_sweep` and the preflight.

## Requirements

- A check reads a file the run produced, because a grader that reads only the final message
  cannot say anything about an artifact.
- A check converts before it asserts, because every artifact format worth checking is binary
  and neither a regular expression nor a text judge can read one.
- A conversion that fails is a failure of the run, because a file the format's own tooling
  cannot open is not a correct answer, whatever the rubric would have said about it.
- A check is authored in the case, beside the graders, because an assertion about a case
  belongs with the case and nowhere else.
- A check is written in a file `claude plugin eval` never reads, because the harness's grader
  type list is closed and an unknown type there refuses the case at load and destroys the
  whole suite's result document.
- The assertion vocabulary is the grader vocabulary, because a second set of matching rules
  over the same kind of material would drift from the first.
- A check runs on both backends, because a produced artifact exists on both and the case
  format does not vary per backend.
- A deterministic check decides pass and fail and a judged one is printed, because that is
  already the rule and the layer that evaluates a grader is not what makes it flaky.
- The conversion is kept on disk beside the workspace, because a human reading a failed check
  needs to see what was actually asserted over.
- A converter is a named member of a closed set, because an author-supplied script is
  arbitrary shell running as the developer, which is the reason `--no-scaffold` is pinned.

## Out of scope

- **Author-supplied converters.** A `convert:` naming a script in the case directory is the
  scaffold trust problem again: arbitrary shell, from a case tree, running as the developer on
  their own machine. The closed set covers every artifact the image can produce. If a format
  outside it is needed, the converter is added to this package, where it is reviewed.
- **Checking a file the run did not produce.** A check reads the run's workspace. A fixture
  staged with `context.add_dirs` is an input and asserting over it asserts nothing about the
  plugin.
- **A converter that runs on the host.** The conversions need LibreOffice, pandoc and poppler
  at the versions the CoWork image pins. Nothing guarantees any of them on a developer's
  laptop, and a conversion that silently differs from the session's own tooling is worse than
  no conversion.
- **Editing the harness's grader set.** `claude plugin eval` is not this repository's, and its
  five types stay exactly as they are.
- **A cost ceiling over judged checks.** `--max-cost-usd` bounds the harness's own run and
  never bounded the CoWork judge either. A second ceiling here would be this package
  inventing a restriction nobody asked for.
- **Rendering a check into the panel.** The panel records the outcome `verdict.decide`
  reached, and a check changes what that outcome is, not how it is recorded.

## Constraints

- The harness's grader type list is closed, and an unrecognised type in `prompt.md`
  frontmatter or a grader file refuses the case at load: nothing runs, no
  `aggregate-result.json` is written, and the command exits 1. One malformed case costs the
  whole suite its result document. `docs/eval_format.md`.
- A case directory holding a subdirectory that is not `graders/` is inert to the harness.
  Discovery descends only into directories, and a directory with no `prompt.md` is not a case.
  `cases.py`, `docs/eval_format.md`.
- The agent under test cannot read the `evals/` tree: the sandbox grants the plugin entry by
  entry around it and denies it outright, and only `context.add_dirs` entries inside the case
  are readable. `docs/claude_code/plugin_eval_reference.md`.
- The v1 result document is additive-only. This repository already adds `declaredUnrunnable`,
  `declaredReason`, `skipped`, `skipReason` and `cowork` to it. `docs/cowork_backend.md`.
- Each run's workspace is already on the host at
  `<run dir>/traces/run-<n>/workspace/`, moved from the kept sandbox on Docker and copied
  from the session's `outputs/` on CoWork, in one layout for both backends. It exists only
  when the invocation kept its traces. `traces.py`, `docs/running_evals.md`.
- `traces.py` already rewrites the result document after a run, so post-run modification of
  that document is established and needs no new mechanism.
- A backend takes a case path and an output directory and returns a result document. It never
  names a directory, prunes, or decides pass and fail. `plans/README.md`.
- The image carries LibreOffice 26.2.5 as `soffice`, pandoc, poppler-utils, ghostscript,
  imagemagick, tesseract, and `openpyxl==3.1.5`, `python-pptx==1.0.2` and `pandas==2.3.3`
  among its 127 pins. `src/cowork_evals/docker/Dockerfile`, `docs/runtime.md`.
- The container runs with the host user's numeric uid and gid and mounts under
  `/work`. `docker/__init__.py`.
- `judge.py` sends the rubric and the material as one text on stdin to `claude -p
  --strict-mcp-config`, with no tools granted. It cannot see an image today.
- Structural graders decide the verdict; judged graders are printed and decide nothing; a
  skip fails the run. `verdict.py`, `docs/running_evals.md`.

Everything in `CLAUDE.md` binds this plan as it binds every other, and is not repeated here.

## High-level design

A check is a grader this package evaluates. It differs from a harness grader in one way: it
converts the artifact before it asserts over it. Everything else, the matching rules, the
judge, the weights, the classes, is what a grader already does.

**Where a check is written.** `evals/<skill>/<case>/checks/<name>.md`, one check per file,
frontmatter then the rubric or the pattern. The directory mirrors `graders/` exactly. The rule
that decides which of the two a new assertion goes in: an assertion `claude plugin eval` can
evaluate goes in `graders/`, an assertion that needs the artifact converted first goes in
`checks/`. The harness never opens `checks/`, so its closed type list is not touched and a
check cannot cost a suite its result document.

**When a check runs.** After the backend returns and after `traces.collect` has put each run's
workspace on the host, and before the verdict. That ordering is forced: a check reads the
workspace, the workspace is what collection produces, and the verdict reads the results a
check appends. A check therefore needs the invocation to be keeping its traces, and a
selected case carrying a check under `eval.keep_traces: false` is a preflight failure naming
the key, because evaluating no assertion silently is worse than refusing to start.

**How a check runs.** Once per run of the case, against that run's workspace, exactly as a
grader is evaluated once per run. The conversion happens in the run container, from the image
`docker/__init__.py` already builds and tags: the artifact's own tooling is pinned there at
the versions the CoWork session has, which is the only place the conversion means anything.
On the CoWork backend that is the one thing that reaches for Docker, and the `--cowork`
preflight says so when a selected case carries a check.

**What a check produces.** Two grader results per check, appended to each run's `graders[]`
in the result document, with their definitions appended to the case's `graders[]`:

| Result           | Type              | Is                                          | Decides |
| ---------------- | ----------------- | ------------------------------------------- | ------- |
| `<name>/convert` | `convert`         | Whether the conversion succeeded            | yes     |
| `<name>`         | `regex` or `llm`  | The assertion over the conversion           | `regex` yes, `llm` no |

Splitting them is what keeps the class rule intact with no special case. A conversion is
deterministic, so it decides; a rubric over the conversion obeys the rule every rubric obeys.
`convert` is one new structural type and exists only in a check. `verdict.py` builds a name to
type map off the case's grader definitions and treats anything outside `cases.JUDGED` as
structural, so it needs no change at all; `cases.STRUCTURAL` names `convert` for the
vocabulary the reader and the validator share.

**What a conversion produces.** Text conversions produce one file, because a `regex` grader
asserts over one target and `count:N` means nothing over a set. A workbook's sheets and a
PDF's pages are concatenated in order, each part preceded by a line naming it. Image
conversions produce one PNG per slide or page, and the judged check that reads them names
every one of them in a single judge call, because a rubric is about the deck and judging each
slide against it separately would fail every rubric that names one slide.

## Implementation details

### The check file

`evals/<skill>/<case>/checks/<name>.md`. Frontmatter, then the rubric for a judged check or
nothing for a matched one.

| Key                       | Is                                                                  |
| ------------------------- | ------------------------------------------------------------------- |
| `type`                    | `regex` or `llm`. Required                                          |
| `artifact`                | The produced file, relative to the workspace. Required              |
| `convert`                 | `csv`, `png`, `md` or `txt`. Required                               |
| `name`, `weight`          | As on a grader: the filename without `.md`, and 1                   |
| `pattern`, `flags`, `match` | `regex` only, and the same semantics as the grader                |
| `criteria`                | `llm` only, in the body as the grader writes it                     |

There is no `target` and no `focus`. `artifact` is the one key that says what a check looks
at, whatever its type, because the split between those two keys is the silent trap
`docs/eval_format.md` already names and a new file should not reproduce it.

`arm:` is not accepted. A check is evaluated after collection, over a workspace the document
does not partition by arm, and honouring it would mean claiming an ablation semantics the
layer does not have.

### The converters

One new module, `convert.py`. It holds the closed set, the argv each member builds, and
nothing else: it runs no container and reads no configuration, so every argv is a pure
function a unit test asserts over. The rule for adding a member: it wraps a tool already on
the image, and it produces UTF-8 text or PNG.

| `convert` | Accepts                     | Produces                     | Built from                                      |
| --------- | --------------------------- | ---------------------------- | ----------------------------------------------- |
| `csv`     | `.xlsx`, `.xlsm`, `.csv`    | One UTF-8 text file          | `soffice --headless --convert-to csv`           |
| `png`     | `.pptx`, `.docx`, `.pdf`    | `page-001.png`, ...          | `soffice` to PDF, then `pdftoppm -png -r 150`   |
| `md`      | `.docx`, `.pptx`, `.html`   | One UTF-8 text file          | `pandoc -t gfm`                                 |
| `txt`     | `.pdf`                      | One UTF-8 text file          | `pdftotext -layout`                             |

`csv` goes through LibreOffice and not through `openpyxl`, although both are on the image,
because LibreOffice recalculates a workbook on load and `openpyxl` does not: a skill that
writes formulas without cached values produces a file `openpyxl` reads as empty cells, and
the check would fail an artifact that is correct. LibreOffice exports one CSV per sheet, and
the module concatenates them in sheet order under a `# <sheet name>` line each. The exact
filter token for all-sheet export is measured in phase 2; if it is unavailable in 26.2.5, the
converter loops over sheet indices, which produces the same files at the cost of one
invocation per sheet.

`png` goes through PDF rather than through an image export, because LibreOffice's PDF export
is the path the document tooling is actually exercised on and `pdftoppm` numbers its output
predictably.

A converter whose `artifact` extension is not in its Accepts column is a failed `convert`
result naming both, before any container starts. That is not a restriction invented here: it
is the tool refusing, reported early instead of as an opaque exit code.

### Running a conversion

One `docker run` per check, in `checks.py`, the module that owns the layer:

- The image is `Docker.tag`, built by `Docker` as a run already builds it. No new image and no
  second Dockerfile.
- `<run dir>/traces/run-<n>/workspace` mounts read-only, because a conversion that modified
  the artifact would invalidate every later check over it.
- `<run dir>/traces/run-<n>/converted/<check name>` mounts writable and is where the
  conversion lands. It sits beside `workspace/` because it is an artefact of the run and is
  what a human reads when a check fails.
- `--network none`, because no converter needs a network and the image's own tooling is the
  only thing running.
- The uid, gid and `HOME` are what a run already passes.
- The timeout is `eval.convert_timeout_seconds`, default 120.

A non-zero exit, a timeout, or an empty output directory is a failed `convert` result carrying
the converter's stderr, truncated. Nothing here raises, which is the rule `grader.py` and
`judge.py` already hold to.

### Asserting over the conversion

A `regex` check is `grader.py`'s existing regex evaluation with the conversion's single file
as the target. No new matching code, and `pattern`, `flags` and `match` mean exactly what they
mean on a grader, JavaScript RegExp source compiled with Python's `re` through the one
function that already does it.

An `llm` check over a text conversion is `judge.py` unchanged: rubric and material as one text
on stdin, three votes, two to pass.

An `llm` check over a `png` conversion needs `judge.py` to gain one mode. The call becomes
`claude -p --strict-mcp-config --allowedTools Read`, with the rubric and the list of converted
image paths in the prompt, and the judge reads them itself. Read is granted on exactly the
check's converted directory and nothing else.

Phase 2 measures whether a `Read`-granted `claude -p` returns a usable verdict over a PNG. If
it does not, `convert: png` does not ship and a deck is checked through `convert: md`, which
gives the judge the deck's text; the plan is then complete without the image route and
`docs/artifact_checks.md` records the measurement and the omission.

### The result document

`checks.py` appends to the document `traces.collect` has already rewritten, in the same pass
over the same file:

- Each check's two definitions go onto the case's `graders[]`, carrying `name`, `type`,
  `weight`, and a `check` object holding `artifact` and `convert`. `check` is this
  repository's own field, like `cowork` on a run, and the contract is additive-only.
- Each check's two results go onto every run's `graders[]`, carrying `name`, `passed`,
  `weight`, `scored`, `explanation`, and `evidence` on a judged one. A `convert` result's
  `explanation` is the converter's failure or the list of files it produced.
- The case aggregate's `score` is recomputed over the widened result set, because the document
  states a score and a stale one would disagree with its own graders.

`verdict.py` needs no condition changed. It reads `graders[]`, classifies on type, and
`convert` is structural because `cases.STRUCTURAL` names it.

### The validator

`validate.py` gains the checks rules, each exit 3 in `run`'s preflight like every other:

| Rule                                                                              |
| --------------------------------------------------------------------------------- |
| Every file under `checks/` carries a `---` block                                   |
| `type` is `regex` or `llm`                                                         |
| `artifact` and `convert` are present, and `convert` is in the closed set           |
| `artifact` resolves inside the workspace, so no `..` and no absolute path          |
| The `artifact` extension is one the named converter accepts                        |
| `weight` is above 0                                                                |
| No `target`, `focus` or `arm` key                                                  |
| `checks` is not a `context.add_dirs` entry                                          |

The last one is the same rule the harness holds for `graders/`: an `add_dirs` entry naming
`checks` would hand the agent under test the assertions it is being judged against.

A case with a `checks/` directory and no file in it is a violation, because an empty
assertion directory is an author who meant to write one.

### The preflight and the command

`cli.py`'s `_run_preflight` gains two conditions, both read off the selected cases:

- A selected case carries a check and `eval.keep_traces` is false: exit 3 naming the key.
  A check reads the workspace, and with traces off there is no workspace.
- A selected case carries a check on `--cowork` and Docker is unavailable: exit 3 with the
  same remedy text the `--docker` preflight already prints. The conversion needs the image on
  either backend.

`_sweep` calls the layer between `traces.collect` and `verdict.decide`. A check that could not
be evaluated at all, meaning the workspace is missing, is a failed `convert` result and not a
warning, because a missing workspace means the assertion did not happen.

### The configuration

One new key, `eval.convert_timeout_seconds`, default 120, in the one configuration file. The
image is `docker`'s and is not duplicated, and the judge model is `eval.judge_model`, which
already answers for every judged grader. No new section: a conversion is part of running an
eval.

## Testing

Unit by default, integration for what needs a container or a model, per `tests/README.md`.
Nothing is mocked and nothing is skipped.

The split that decides the tier here: a pure function over a path, a parsed check or a
document is unit; anything that starts a container or calls `claude` is integration. That is
the same split `docker/__init__.py` and `judge.py` already sit either side of.

Unit, in `tests/unit/`:

- `checks.py` reads a `checks/` directory into the same shape `cases.py` reads `graders/`,
  including the filename-as-name default and the weight default.
- A check file with no `---` block, an unknown `convert`, a missing `artifact`, an `artifact`
  escaping the workspace, a `target`/`focus`/`arm` key, and a mismatched extension each fail
  the validator with the named rule.
- `checks` as an `add_dirs` entry fails the validator.
- Every converter's argv, asserted as a string list against the mount paths, with no container
  started.
- The concatenation: several CSV parts become one text file, in sheet order, each under its
  `# <sheet>` line.
- The document append: definitions land on the case, results land on every run, `scored` is
  right on both, and the recomputed score matches the widened set.
- `verdict.decide` over a document carrying check results: a failed `convert` fails the case, a
  failed `llm` check does not, a failed `regex` check does.
- The two new preflight conditions, each returning 3 with the key named.

Integration, in `tests/integration/`, marked `integration`:

- Each converter against a real fixture artifact in the container: a workbook with two sheets
  and a formula whose value is not cached converts to CSV holding the computed number, a deck
  converts to one PNG per slide, a document converts to Markdown, a PDF converts to text.
- A corrupt `.xlsx`, meaning a file with an `.xlsx` name that is not a ZIP, produces a failed
  `convert` result carrying the converter's error.
- The image judge: a `Read`-granted `claude -p` over a converted PNG returns a usable verdict.
  This is the phase 2 measurement and it stays as a test.
- One end-to-end `run --docker` over a fixture case in `plugins/` that produces a workbook and
  carries both a `regex` and an `llm` check, asserting the verdict reads them.

Reminders for the implementer:

- Follow the repository's existing test conventions: match the layout and style of the tests
  already in `tests/unit/` and `tests/integration/`.
- Never mock. A test that appears to need one is a finding about the design; say so rather
  than reaching for `unittest.mock`. Only the developer can waive the rule.
- Test behaviour, not getters. No test exists to raise a coverage number.

## Documentation updates

- `docs/artifact_checks.md`, new. The mechanism: the closed converter set and what each wraps,
  the container invocation and its mounts, the two results per check, the image judge and what
  phase 2 measured about it, and the `convert` type. Added to the table in `docs/README.md` in
  reading order, beside the other mechanism files.
- `docs/eval_format.md`. The authoring contract only: the `checks/` layer in the tree, the
  check file's key table, the rule that decides `graders/` against `checks/`, the validator
  rules, and the trap that a check is invisible to `claude plugin eval`. It links to
  `docs/artifact_checks.md` for how a conversion works and restates none of it.
- `docs/running_evals.md`. A status table row for the layer, the preflight conditions, and the
  `converted/` directory in the log layout.
- `docs/approaches.md`. One row in `What each backend honours`: checks, yes on both, and the
  note that the conversion needs the image on either.
- `docs/cli.md`. The two new preflight failures and their exit code.
- `docs/library.md`. `eval.convert_timeout_seconds` in the configuration table.
- `src/cowork_evals/data/cowork_evals.example.yaml`. The new key with its default, commented,
  which `tests/unit/test_resources.py` already asserts against the built-in defaults.
- `src/cowork_evals/data/skills/cowork-evals/SKILL.md`. The check file shape and when to reach
  for one, at the density the rest of that file is written at.
- `plugins/README.md`. The fixture case the integration tier needs, and what it is not.
- `plans/README.md`. Row 16, `plan_artifact_checks.md`, branch `feat/artifact-checks`, status
  `written`, and a paragraph in the section list saying what it builds.

## Implementation steps

> **For the implementer:** Work autonomously end-to-end. Do not pause to ask for permission to
> run shell commands during the writing phase — assume any such request will be denied.
> Complete **Implementation steps**, **Test steps**, and **Documentation updates** by editing
> files only. Once everything is written, run **Verification steps** yourself in one batch at
> the end.

Phase 1, the reader and the validator:

- [ ] `cases.py`: read `checks/` into a `Check` dataclass beside `Grader`, and add `convert` to
      `STRUCTURAL`.
- [ ] `validate.py`: the eight rules in the table above, each with its own violation name.
- [ ] `validate.py`: refuse `checks` as an `add_dirs` entry.

Phase 2, the converters and the measurement:

- [ ] `convert.py`: the closed set, the argv builder for each member, and the accepted
      extensions.
- [ ] Measure the LibreOffice all-sheet CSV filter token against 26.2.5 in the image. If it is
      not available, implement the per-sheet loop instead. Record what was measured in
      `docs/artifact_checks.md` as a snapshot with its date.
- [ ] Measure whether a `Read`-granted `claude -p` returns a usable verdict over a PNG. Record
      it as a snapshot with its date. If it does not, drop `png` from the set, drop the image
      mode below, and say so in `docs/artifact_checks.md`.

Phase 3, the layer:

- [ ] `checks.py`: run one conversion per check in the container, over one run's workspace,
      into `converted/<check name>/`.
- [ ] `checks.py`: the text concatenation, in part order, under a naming line each.
- [ ] `checks.py`: evaluate a `regex` check through `grader.py`'s existing evaluation.
- [ ] `judge.py`: the image mode, `--allowedTools Read` scoped to the converted directory, all
      images named in one call. Skip if phase 2 said to.
- [ ] `checks.py`: evaluate an `llm` check through `judge.py`, text or image.
- [ ] `checks.py`: append the two definitions and the two results per check, and recompute the
      case aggregate's score.

Phase 4, the wiring:

- [ ] `config.py`: `eval.convert_timeout_seconds`, default 120.
- [ ] `cli.py`: the two preflight conditions.
- [ ] `cli.py`: call the layer in `_sweep`, between `traces.collect` and `verdict.decide`.
- [ ] `plugins/`: the fixture case that produces a workbook and carries both kinds of check.

## Test steps

- [ ] Unit: the check reader, including the name and weight defaults.
- [ ] Unit: each of the eight validator rules, one test per violation.
- [ ] Unit: `checks` refused as an `add_dirs` entry.
- [ ] Unit: each converter's argv.
- [ ] Unit: the text concatenation over several parts.
- [ ] Unit: the document append, both definitions and both results, and the recomputed score.
- [ ] Unit: `verdict.decide` over check results, all three cases in the Testing section.
- [ ] Unit: the two preflight conditions.
- [ ] Integration: the four converters against real fixture artifacts in the container.
- [ ] Integration: a corrupt `.xlsx` produces a failed `convert` result carrying the error.
- [ ] Integration: the image judge over a converted PNG.
- [ ] Integration: one `run --docker` over the fixture case, asserting the verdict reads both
      checks.

## Verification steps

1. [ ] `scripts/lint.sh`.
2. [ ] The new unit tests.
3. [ ] The full unit suite.
4. [ ] `-m integration`, at the end of the plan, per `tests/README.md`.
5. [ ] By hand: write a case whose prompt asks for a two-sheet workbook with a computed total
       in a cell the prompt does not name, give it one `regex` check over `convert: csv`
       asserting the number is present and one `llm` check asserting the totals are right,
       run `cowork_evals run --docker` over it, and confirm the verdict reads both, that
       `converted/` holds the CSV, and that corrupting the produced file by hand and
       re-grading the stored run fails the `convert` result.
