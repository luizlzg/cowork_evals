---
name: cowork-evals
description: Decide which evals a Claude CoWork skill or plugin needs, write them, and run them with the cowork_evals command, and run a plugin's own pytest suite on the CoWork runtime. TRIGGER when a skill or plugin needs evals and has none, when asked what to evaluate or which grader to use, when writing or fixing an eval case, a prompt.md, a grader or a check under an evals/ directory, when a cowork_evals command fails, when configuring cowork_evals.yaml, or when writing plugin code that has to run inside a CoWork session.
---

# cowork_evals

`cowork_evals` runs evals against Claude CoWork skills and plugins, and runs a plugin's own
Python tests on the CoWork runtime. It is installed as a Python package. Evals are written in
this repository, not in the package.

Run `cowork_evals docs` first. It prints the directory holding the shipped documentation and
every document name. `cowork_evals docs <name>` prints one absolute path, and reading that
file is the authority for anything below.

| Question                                | Read                     |
| --------------------------------------- | ------------------------ |
| Which cases to write, and which assertion answers what | `docs eval_design`   |
| How to write a case, field by field     | `docs eval_format`       |
| Every verb, option and exit code        | `docs cli`               |
| Which backend proves what, and its cost | `docs approaches`        |
| Pass and fail, the logs, what a run costs    | `docs running_evals`     |
| The runtime a plugin's code gets        | `docs runtime`           |
| `test`, and the runtime a suite gets    | `docs cowork_test`       |
| An assertion no grader type can express | `docs checks`            |
| Every grader field the format is silent on | `docs claude_code/plugin_eval_reference` |
| What `panel` shows, and the records behind it | `docs panel`           |

## What to evaluate

`docs eval_design` owns this. The short form:

Claude Code does not invent a suite. Read the skill under test first, then talk to the developer
about what the reading did not settle. There is no questionnaire: no fixed set of questions, in
no fixed order, and no question whose answer the skill already carries. A session opening with
the same three questions every time gets three shallow answers, and asks a developer to restate
their own skill.

Read for the job the skill exists for, which of its capabilities are separable, and what it reads
and writes. Talk about what a wrong answer looks like, what must never happen, and which part
breaks most often, one thing at a time and in whatever order the conversation takes. Never ask
which eval and which grader they want: that hands the design back to the developer, and a
developer who could answer it would have written the case already. Whether the model would do the
job unaided is settled by the baseline arm and by no conversation: `## Did the plugin do anything`
below.

A reply names a symptom, not a case, and turning it into one is the work. `The summaries are too
long` is a `regex` over `last_message`. `It makes things up about our schema` is a fixture and a
`not_contains` pattern per invented value. `It ignores the config file` is a `tool_used` with an
`input_match` naming that file. `The totals in the spreadsheet come out wrong` is a check that
opens the workbook, because no grader type reads a cell.

A reply that says the developer does not know, or that asks Claude Code to decide, is the
authorization to design the suite alone. The signal is the reply. No option and no configuration
key selects it. Then say which dimensions were covered, which were left out, and why each
left-out one does not apply.

Whichever route produced the suite, check it against these. Each dimension that applies has at
least one case, and one case may answer more than one row.

| Dimension                                | The assertion                                                                  | Applies when                                  |
| ---------------------------------------- | --------------------------------------------------------------------------- | --------------------------------------------- |
| Expected behaviour, end to end           | `file_exists` on the artefact, `tool_order` on the steps that have an order, `llm` over `{source: file, path}`, a check over that file when it is not text | always |
| The right tools are used                 | the skill-fired `tool_used` below, `tool_order` for a required sequence, `min: 0, max: 0` for a tool it must not call and for a request it must not fire on | always |
| The goal is achieved                     | `file_exists`, `regex` over `{source: file, path}` for a value that has to be in it, `llm` when the outcome is prose, a check when the value has to be computed or the file parsed | always |
| Each capability on its own               | `tool_used` with that capability's `input_match`, `regex` over its output, a check when that output is not text | the skill names more than one capability |
| The instructions are followed            | `regex` over `last_message` with `contains`, `not_contains` or `count:N`, and `m` in `flags` when the anchor is per line, a check when the constraint is on a file no pattern can read | the instructions constrain the output |
| Edge cases                               | `regex` for the stated refusal or the handled result, `min: 0, max: 0` for the destructive action | the input has a boundary: empty, absent, malformed, oversized, conflicting |
| Hallucination                            | `regex` with `not_contains` per value the fixture does not carry, `baseline` against a `baseline_file`, a check when the invented value lands in an artefact no pattern can read | the skill reports what it read |
| Context relevancy                        | `tool_used` with `input_match` naming the file it had to open, `regex` over `trace` for that path | the skill chooses what to read     |
| Answer relevancy                         | `regex` with `count:N` or `not_contains` for the padding shape, `llm`, `baseline` | the product is the message and not a file |
| PII and confidential information leakage | `regex` with `not_contains` over `last_message`, over each artefact, over `trace`, over `mock_calls`, and a check per artefact that is not text | the skill reads anything the prompt did not carry |

A case that ticks a row is worse than the gap it fills. The table finds gaps and is not a quota. A
case written to complete it costs a run on every sweep, and its pass says nothing about the skill.
Ten rows is the most a suite covers, not the number it aims at.

A suite answers two questions. Does the skill still work, and is the skill better than no skill. The
same case files answer both, and the run is what differs: one arm for the first, two for the second.
An assertion therefore has to be deep enough to fail on its own when the skill regresses, and it has
to score in both arms to move a delta. One that does the first and not the second leaves the second
question unanswered, and a suite of them reports a delta of zero whatever the baseline produced.
Neither question is designed for alone: shallow arm-visible assertions pass a broken skill, and deep
one-arm assertions cannot say the skill is worth loading.

Prefer a structural grader. A judged grader over a non-deterministic agent is a flaky verdict,
and a judge is noisy on a long input. A dimension whose only grader is `llm` or `baseline` is
printed and leaves the exit code silent about it.

Can a grader type read the target, and say what has to be true of it? Yes, and it is a grader.
No, and it is a check, which is `## Checks` below. Ask it per assertion, not per case: a case
carries both, and a case whose only assertion directory is `checks/` never loads. Six rows above
name a check, because a grader reads text and a workbook, a deck, a PDF and an image are not.
Prefer a grader anyway: a check is code you own. Unlike an `llm` grader, a check decides the exit
code however it reached its verdict, `run.judge` included.

Usefulness is a delta. A prompt the model answers as well unaided measures the model, so move it
onto what the skill knows and the model does not, and prefer a prompt naming the outcome to one
naming the skill or its steps, because the arm with no skill gets the same prompt. A case whose
only assertion is that the skill fired says nothing about usefulness: the assertion cannot hold
without the plugin, so give the case an assertion over the output as well. The arm itself is
`## Did the plugin do anything` below.

The fixture has to need the tool. A skill is a tool over an input, and the fixture is that input at
the size and the shape of the real one.

| The rule                                         | What the case measures without it                                            |
| ------------------------------------------------ | ---------------------------------------------------------------------------- |
| The fixture is the size of the real input        | an input small enough to reason about unaided measures the model              |
| The prompt does not quote the fixture            | the arm with no skill answers from the prompt and opens no file               |
| The boundary the skill handles is in the fixture | a boundary that appears only at scale is unreachable at four rows            |
| The input is as untidy as the real one           | a fixture with no duplicate, no gap and no stray type exercises no handling   |

Realism is what makes the table decidable as well: edge cases, context relevancy and hallucination
each need an input carrying the thing the row asserts. Generate a fixture that size rather than
typing it, and commit it.

An assertion is not known to measure anything until it has been tested both ways. One that cannot
fail and one that cannot pass report the same thing on every run. Test every pattern against one
sample that has to match and one that has to not match, and every check against one artefact that
has to pass and one that has to fail. The artefact that has to pass is the skill's own output: a
check the skill's own output fails is a broken check and not a finding. Both tests run before the
first case does, because neither needs a model, and a pattern is tested in the engine the harness
grades with rather than the one the test is written in.

The deliverable does not show the route. A grader and a check both read what the run produced, and
a file the skill's own command wrote is byte-comparable with one a script reimplemented, so a green
suite passes a run that never used the skill and passes a run that used it and then wrote over its
output. So add a third assertion that reads the trace: an advisory check returning what `run.judge`
returned,
shown the trace and the skill's own document as paths, asking three things and no more. Was the
route the right one, were the instructions followed, was anything invented. Show it the task as well,
because the trace does not carry it: a collected trace opens on a `system` record and goes straight into
the agent's work, and a judge that does not know what was asked cannot say whether the route suited it.
Read the case's own `prompt.md`, strip the frontmatter, pass the body.

| The rule for that rubric                                | Because                                                                      |
| ------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Show the judge the skill, not a summary of it           | a rubric restating the rules is a snapshot of one reading, and keeps passing a run the skill would now fail |
| Name the subject and let the judge find the wording     | the assertion then moves with the skill on its next edit                      |
| Never demand a route the skill cannot take              | read the command list first: a clause asking the impossible fails every run for a gap in the skill |
| A split vote is a rubric fault before a judge fault     | the clause, not the model, is usually what two votes read differently         |
| Judge the route, not the result                         | the graders and the checks already decide whether the numbers are right       |
| Do not hold the baseline arm to it                      | the route and the instructions are the skill's, so asserting them with no plugin loaded inflates the delta |

It is the layer over the others, not a replacement: it is the most expensive assertion in a suite
and the least deterministic, it costs `eval.judge_votes` calls per run per arm, and so it is one per
case. What a `regex`, a `file_exists` or a plain check can settle, let it settle.

Context relevancy, leakage and the malformed form of edge cases each need a staged fixture, which
is a `context.*` key, which makes the case `no-cowork`. The leakage marker is a fixture the case
owns, never a forwarded credential: `run.log` carries whatever the container printed.

A case that needs access it does not have measures the access and not the skill.

| The case needs               | The route                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------- |
| A credential the skill reads | `docker.env_passthrough` names the variable, and a name unset or empty exits 3   |
| A third-party service        | a fixture the case stages, or a `mocks/` stand-in                               |
| An MCP server                | `evals/mocks/<server>/<tool>.md`, which makes the case `no-cowork` and `mock_calls` readable |
| A tool                       | `eval.allow_tools`, or the case's own `allowed_tools`, which makes it `no-cowork` |
| A file staged before the run | `context.add_dirs` or `context.scaffold_script`, which makes the case `no-cowork` |
| A library a check imports    | your own project declares it, as for a unit test. The preflight imports every check and exits 3 |
| A wheel the skill imports    | `cowork_evals test`, before an eval is written over the import error             |

Design around the access that exists. When the developer proposes a case that needs access that
is not there, say so before writing the case, and name the route that would supply it.

Propose the suite before writing a file: one line per case, naming the dimension it covers, the
grader or the check that decides it, the access it needs, and whether it carries `no-cowork`. A developer
strikes a case in one sentence there, and pays for a rewrite after the files exist.

## The command

```bash
cowork_evals check --all                       # what each backend still needs
cowork_evals setup --docker                    # build the images
cowork_evals login --docker                    # log in once, in a container
cowork_evals run  --docker <path>              # an eval: a model, graders, a verdict
cowork_evals test --docker <path>/tests        # pytest on the CoWork runtime, no model
cowork_evals ask  --cowork "<prompt>"          # one prompt to a live session, and its answer
cowork_evals panel <path>                      # every case, and what each backend last said
cowork_evals docs [<name>]                     # where the documentation is
cowork_evals init                              # write the config, the skills, and a CLAUDE.md block
cowork_evals prune --docker                    # delete what setup built
```

`--docker` runs Claude Code in a container that reproduces the CoWork image. `--cowork` drives
the real desktop application, needs macOS and a configured profile, and takes the keyboard for
the length of the run. A modal asks for the keyboard once per invocation, before the first
plugin; `--dry-run` never shows it. Prefer `--docker` for iteration.

The path is the scope: a case directory runs that case, `evals/<skill>/` runs that skill,
`evals/` runs the plugin, and a directory holding several plugins runs each in turn.
`--dry-run` prints what would run and spends nothing.

`panel` takes the same path and spends nothing. It reads records earlier runs left and prints
one row per case: the latest outcome on each backend, how old it is, and whether the case
files have changed since. A case that has never run says so, which is how a gap in coverage is
found without firing anything.

`ask` is not an eval and is not part of this skill. It answers a question about what a live
session does, and the `cowork-ask` skill covers it.

## The tree

```
<plugin>/.claude-plugin/plugin.json       # what makes <plugin> a plugin root
<plugin>/skills/<skill>/SKILL.md
<plugin>/evals/<skill>/<case>/prompt.md
<plugin>/evals/<skill>/<case>/graders/<name>.md
<plugin>/evals/<skill>/<case>/checks/<name>.py  # optional, assertions as Python
<plugin>/evals/<skill>/<case>/case.yaml   # optional, context.* only
<plugin>/evals/plugin/<case>/             # a case that crosses skills
<plugin>/evals/mocks/<server>/<tool>.md   # shared MCP stand-ins
```

A directory directly under `evals/` is a skill name, `plugin`, or `mocks`. Nothing else. The
validator enforces it in both directions.

Fixtures live inside the case that uses them.

## prompt.md

Frontmatter, then the prompt the agent receives.

```markdown
---
name: one-paragraph
description: The skill fires, and the answer is one paragraph.
tags: [summarize]
plugins: ["../../.."]
runs: 3
---

Summarize `notes/standup.md` in one paragraph.
```

`tags` and `plugins` are both required and both checked.

- `tags` names the case's own directory. `--tag` is the only reliable per-skill selector.
  `--case` globs the case name, which is the `name` key when the case writes one.
- `plugins` counts up to the plugin root. From `evals/<skill>/<case>/` that is `../../..`,
  and the count is the same whatever the plugin is called.

| Key                                                     | Is                                                    |
| ------------------------------------------------------- | ----------------------------------------------------- |
| `name`                                                  | Required                                              |
| `description`                                           | For humans. Not read at run time                      |
| `tags`, `plugins`                                       | Required, above                                       |
| `runs`, `max_turns`, `timeout_seconds`                  | Defaults 3, 10, 300. Caps 50, 200, 3600               |
| `model`, `allowed_tools`, `append_system_prompt`, `env` | Execution. Every `env` key starts with `EVAL_`        |

Any other key is an error. `context.*` goes in `case.yaml`, which needs
`schema_version: "1.1"` and `name`.

## The no-cowork tag

`no-cowork` is the one reserved tag value. A case carrying it in `tags:` declares that a live
CoWork session cannot run it: the case is not submitted on `--cowork`, and is counted rather
than failed. On `--docker` it is one more tag. `--tag <skill>` still selects the case, because
the case carries both tags.

A case carries it when, and only when, it writes `max_turns`, `model`, `allowed_tools`,
`append_system_prompt` or `env`, writes any `context.*` key in `case.yaml`, or sits under a
`mocks/` directory, including a suite-wide `evals/mocks/` several levels above it. The
validator checks both directions and exits 3 on either: a case that needs the tag and lacks
it, and a case that carries it and needs nothing. There is no `skip:` field, and the tag is
not one.

## Graders

One grader per file under `graders/`, frontmatter then the rubric or pattern. Structural
graders are deterministic and decide the exit code. Judged graders call a model and are
printed.

| Type          | Takes                                                                     | Class      |
| ------------- | ------------------------------------------------------------------------- | ---------- |
| `regex`       | `pattern`, `flags`, `match: contains \| not_contains \| count:N`, `target` | structural |
| `tool_used`   | `tool`, `input_match`, `min` (default 1), `max` (default unlimited)       | structural |
| `tool_order`  | `before`, `after`                                                         | structural |
| `file_exists` | `path` as a glob over created files, `exists` (default true)              | structural |
| `llm`         | `criteria`, `focus`. A judge model votes 2 of 3                           | judged     |
| `baseline`    | `baseline_file`, `criteria`                                               | judged     |

Only `regex` and `llm` choose what they look at, and the keys differ: `regex` uses `target`,
`llm` uses `focus`. Values are `last_message` (default), `trace`, `files`,
`{source: file, path}`, `mock_calls`.

The skill fired:

```markdown
---
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?<skill>"'
---
```

The answer is one paragraph:

```markdown
---
type: regex
target: last_message
pattern: '\n\s*\n'
match: not_contains
---
```

The skill must not fire:

```markdown
---
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?<skill>"'
min: 0
max: 0
---
```

## Checks

A grader type cannot say what is inside the file the run wrote. A check can: it is your own
Python, in the case's `checks/` directory, run on the host after the run is graded, on either
backend. Its verdict is a grader result in the same document, so a failed check fails
the run like a failed `regex` grader, unless it is marked advisory.

```python
# evals/<skill>/<case>/checks/assertions.py
import openpyxl

from cowork_evals.checks import Result, Run, check


@check
def totals_add_up(run: Run) -> None:
    book = openpyxl.load_workbook(run.file("totals.xlsx"))
    assert book.active["D10"].value == 4200
```

A check that needs a model reads files rather than text, so a PDF, an image and a spreadsheet
are all judgeable:

```python
@check
def the_deck_is_readable(run: Run) -> Result:
    subprocess.run(["soffice", "--convert-to", "png", run.file("deck.pptx")], cwd=run.scratch)
    return run.judge("Every slide carries a title, and no text is clipped.", run.scratch)
```

`@check(advisory=True)` runs the check and decides nothing: the verdict is recorded, a failure
prints as a note, and it is out of the score and out of the exit code. Use it for an assertion
whose mechanism is not calibrated yet, which is what a judged rubric over a trace is, and return
the real verdict rather than swallowing it, because the recorded failures are what you calibrate
against. Drop the argument to make the same check binding.

`None` or `True` passes, `False` fails, a `Result` decides, and any exception fails the check
carrying its message. The name is `<file stem>.<function name>`. `run` carries `workspace`,
`last_message`, `trace`, `case_dir`, `run_dir`, `scratch` and `index`, plus `file(name)` and
`judge(prompt, *paths)`. Write into `run.scratch`, never into `run.workspace`.

A check runs on the machine you ran `cowork_evals` on, not in the session, so it imports
whatever your own repository declares. `cowork_evals docs checks` has the rest.

## Traps

Each has a silent failure mode.

- A grader file without `---` delimiters is read as a note and ignored. The case then runs
  with fewer graders than it appears to have.
- A prompt that names the skill it is testing measures the name. A CoWork session that does
  not have the skill refuses the name and produces nothing, so ask for the outcome instead.
- `max: 0` alone can never pass, because `min` stays 1. A must-not-call assertion is
  `min: 0, max: 0`.
- `file_exists` sees only files created during the run. A file the agent modified rather
  than created is invisible to it. Grade the contents, or assert a `tool_used` on `Edit`.
- `target` on an `llm` grader is ignored. That key is `focus`, and the grader judges
  `last_message` while looking as if it judges a file.
- `llm` graders refuse binaries. A `.pptx` is a ZIP. Render to an image, or write text.
- `context.add_dirs` refuses any entry outside its own case directory, the eval directory,
  a sibling case, the plugin root and the case's own `graders/` included.
- `target: trace` is not portable between backends. Each renders the transcript its own
  way, so a `regex` over it can pass on one and fail on the other.
- A case carrying `checks/` and no grader does not load. The harness refuses a case with no
  grader at all, so `checks/` is added to a case and never replaces its `graders/`.
- A check reads a collected run, so `--no-keep-traces` gives up every check. Each one is then
  a skip, and a skip fails the run.
- A file under `checks/` with no `@check` in it asserts nothing. A helper is a file like any
  other, so only a `checks/` directory with no check anywhere in it is reported.
- Each run of a case runs every check again. A case at `runs: 3` carrying one judged check
  costs three of every judge call it makes.

## The exit codes

| Exit | Means                                                            |
| ---- | ---------------------------------------------------------------- |
| 0    | the run passed                                                  |
| 1    | a structural grader or a check failed, a case or grader was skipped, a run never had a tool it was granted, or a case's delta was below the threshold |
| 2    | usage error                                                      |
| 3    | the preflight failed. Nothing ran, and the message names the fix |

`run` validates every selected plugin root before it runs anything, so a malformed sibling
case blocks a single-case run. There is no option to skip validation. It imports every
`checks/*.py` while it does, so a check file that will not import exits 3 before anything
spends.

`test` is the exception: it returns pytest's exit code unchanged.

## Did the plugin do anything

A green suite does not say the plugin works. Ask a model to build a spreadsheet and it will
probably build one whether or not your spreadsheet plugin is loaded.

```bash
cowork_evals run --docker <path> --ablation with-without
cowork_evals run --docker <path> --ablation with-without --delta-threshold 0.2
```

Every case runs twice, once with the plugin and once with nothing loaded, and each case is
decided on the delta between the two scores rather than on its score alone. A case below
`--delta-threshold` fails, and so does a case the two arms cannot be compared on. It costs
twice as much, it is off by default, and it is `--docker` only: a CoWork session gets its
skills from the profile the application is running. `eval.ablation` and
`eval.delta_threshold` set both from the file. `cowork_evals docs running_evals` has what the
arm changes about pass and fail.

Under the arm a `tool_used: Skill` grader stops being scored in either arm and is reported as
an indicator, so the one-arm run is still what says the skill fired.

## Reading a failure

Every run leaves its transcript on the host, on either backend and passing runs included, so
a failure is investigated without running the suite again, against a run that passed and
against the same case on the other backend. A failing line names the directory:

```
FAIL smoke/one-paragraph: run 2: is-one-paragraph: the regex grader failed: pattern not found
  in last_message [artifacts: logs/evals/<stamp>-smoke/smoke/traces/one-paragraph/run-2]
```

| In that directory  | Is                                                                   |
| ------------------ | -------------------------------------------------------------------- |
| `last_message.txt` | The final assistant message, which is what a `last_message` grader read |
| `trace.jsonl`      | Every turn and every tool call, one JSON object per line              |
| `workspace/`       | The agent's working directory                                         |
| `scratch/`         | What a check wrote, where the case has checks                        |
| `checks.jsonl`     | One line per check: the verdict, the traceback, the whole judge exchange |

The three names are the same on `--docker` and `--cowork`. `trace.jsonl` is whatever format
the backend that produced it wrote, and the two are close but not identical: a harness trace
ends in a `result` record and a CoWork one does not. `cowork_evals docs running_evals` has the
table, and it names the document that owns each format. `--no-keep-traces` turns it off, and
`eval.keep_traces: false` does the same from the file. It also gives up two pass and fail
conditions, which read the kept trace: a run refused a tool by the permission mode, and a run
never offered a tool the grant named. Both fail rather than score, because a run that never
had the tool is not a fact about the plugin. `cowork_evals docs running_evals` has them.

## The runtime under test

A CoWork session is Python 3.10 with a fixed wheel set. Every file under the path passed to
`cowork_evals run`, meaning each skill, command, agent and hook, imports only what that image
carries. Read `cowork_evals docs runtime` before adding an import to plugin code.

A plugin's own pytest suite is the other half, and it is not an eval:

```bash
cowork_evals test --docker <plugin>/tests
cowork_evals test --docker <plugin>/tests -- -k parser -x
```

Every token after `--` reaches pytest in order and unmodified. It runs the suite inside the
CoWork image with no model, no case tree, no grader and no verdict. That is what says a plugin's
Python behaves in a session, which a suite passing on a newer local Python does not.

## Configuration

`cowork_evals.yaml` in the working directory holds every setting: the driver's, each
backend's, the models, the tool grants, the ceilings. Nothing is read from the process
environment except the variables `docker.env_passthrough` names, which are forwarded into the
run container for a skill that reads a credential from one, and there is no `.env`. A
command-line option beats the file, and the file beats the built-in default.

`cowork_evals init` writes the file with every key and every default. Only the CoWork backend
requires it: `cowork.profile` is the one key with no default. The file names a profile, which
is an identifier, so it is not committed.
