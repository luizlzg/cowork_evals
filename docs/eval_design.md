# Eval design

## Summary

Which cases a skill needs, and which assertion answers which question. This is the design
contract over [eval_format.md](eval_format.md), which is the file contract, and over
[checks.md](checks.md), which is the other assertion mechanism.

- **Claude Code does not invent a suite.** It reads the skill first, and talks to the developer
  about what the reading did not settle.
- **There is no questionnaire.** No fixed set of questions, in no fixed order. A question whose
  answer is already in the skill is not asked.
- **It never asks which eval and which grader the developer wants.** That question hands the
  design back.
- **A developer who says they do not know gets a suite Claude Code designed.** The signal is
  the reply, not a flag.
- **Ten dimensions.** Each one that applies to the skill has at least one case, whichever route
  produced the suite.
- **A case that ticks a row is worse than the gap it fills.** The table finds gaps. It is not a
  quota.
- **A suite answers two questions.** Does the skill still work, and is the skill better than no
  skill. The same case files answer both.
- **Usefulness is a delta.** A skill earns its place when the agent does better with it than
  without it, and the baseline arm is what measures that.
- **The fixture has to need the tool.** An input small enough to reason about unaided measures the
  model.
- **An assertion is tested both ways.** One sample that has to match, and one that has to not
  match.
- **A grader, or a check.** Can a grader type read the target, and say what has to be true of
  it? Yes, and it is a grader. No, and it is a check.
- **The deliverable does not show the route.** A third assertion reads the trace and asks a model
  three things: was the route right, were the instructions followed, was anything invented.
- **A judged rubric is advisory until it is calibrated.** It records its verdict and fails nothing,
  because a model judging how an agent worked is not yet reliable enough to gate a suite.
- **Show the judge the skill, not a summary of it.** A rubric restating the skill's rules is a
  snapshot of one reading of them.
- **The judge is shown the task too.** The trace does not carry the prompt, so the case's own is what
  the check passes.
- **A missing access changes the design.** A case that needs access it does not have measures
  the access and not the skill.
- **The split against the format is one question**: does the statement depend on what the skill
  under test does?

Pass and fail over what these cases produce is [running_evals.md](running_evals.md). Which
backend honours which case feature is [approaches.md](approaches.md). No case field and no
validator rule is here. Both are [eval_format.md](eval_format.md).

## The split against the format

One question decides the side, and it holds for every statement in either file.

**Does the statement depend on what the skill under test does?** No, and it is the format. Yes,
and it is the design.

| Statement                                                       | Depends on the skill | Side   |
| --------------------------------------------------------------- | -------------------- | ------ |
| The `prompt.md` key table, the caps, the `EVAL_` prefix         | no                   | format |
| The two addressability keys, and what `plugins` counts to       | no                   | format |
| The reserved tag, enforced in both directions                   | no                   | format |
| The grader type table, and its class column                     | no                   | format |
| The regex anchoring snapshot                                    | no                   | format |
| The validator rules, and the authoring traps                    | no                   | format |
| The `@check` decorator, the `Run` fields, what a check may import | no                  | checks |
| Which grader class a case should prefer                         | yes                  | design |
| Which of the two assertion mechanisms a dimension needs         | yes                  | design |
| Which cases the suite needs, and which it is missing            | yes                  | design |
| What a missing access changes                                   | yes                  | design |

A statement about a case file that any reader can check without opening the skill is the
format's. Everything that needs the skill's own instructions, or the developer's answer about
what the skill is for, is here.

The no side is two files, because there are two assertion mechanisms. A statement about a grader
type is [eval_format.md](eval_format.md), and a statement about a check is
[checks.md](checks.md). Which of the two an assertion needs depends on the skill, so it is here.

## The conversation

Claude Code does not invent a suite. It reads the skill under test first, and then talks to the
developer about what the reading did not settle.

There is no questionnaire. No fixed set of questions, in no fixed order, and no question asked
because a document said to ask it. A session that opens with the same three questions every time
gets the same three shallow answers, and it asks a developer to restate what their own skill
already says.

So read first. The skill's own description and instructions, the repository around it, and any
suite already there answer most of the table below. Then talk about the rest, one thing at a
time, in whatever order the conversation takes. A question the reading could have answered is a
question not to ask.

| The design needs                              | Where it comes from                                       |
| --------------------------------------------- | ---------------------------------------------------------- |
| The job the skill exists for                  | its own description and instructions, confirmed in a sentence rather than asked from nothing |
| Which capabilities are separable              | its instructions, and one case each                        |
| What it reads and what it writes              | its instructions and its fixtures, which decide the access and whether the target is text |
| What a wrong answer looks like                | the developer. Nothing in the repository records it         |
| What must never happen                        | the developer, and it is what carries a structural assertion |
| Which part breaks most often                  | the developer, and it is which capability gets a case first |
| Whether the model would do the job unaided    | the baseline arm, and no conversation settles it            |

The bottom four rows are what a conversation is for. The top three are what reading is for, and
raising one of them as a question is how a session loses the developer's patience before the
suite is designed.

It never asks which eval and which grader the developer wants. That question hands the design
back to the developer, and a developer who could answer it would have written the case already.

A reply names a symptom, not a case. The work is to turn it into one. `The summaries are too
long` is a `regex` over `last_message`. `It makes things up about our schema` is a fixture and a
`not_contains` pattern per invented value. `It ignores the config file` is a `tool_used` with an
`input_match` naming that file. `The totals in the spreadsheet come out wrong` is a check that
opens the workbook, because no grader type reads a cell.

Ask again when the reply does not decide the grader. One follow-up question that settles a
target is worth more than a case that grades the wrong thing.

### When the developer does not know

A reply that says the developer does not know, or that asks Claude Code to decide, is the
authorization. The signal is the reply. Nothing in `cowork_evals.yaml` selects it and no option
does.

Claude Code then designs the suite itself, and says which dimensions it covered, which it left
out, and why each left-out one does not apply.

## The coverage dimensions

Ten dimensions. Each one that applies to the skill has at least one case. One case may answer
more than one row, so the check is that no applying row has none.

Every grader named below is one of the six types [eval_format.md](eval_format.md) defines, and
every check is [checks.md](checks.md). This file adds neither.

| Dimension | The case | The assertion | Applies when |
| --------- | -------- | ---------- | ------------ |
| Expected behaviour, end to end | one prompt carrying the whole job the skill exists for | `file_exists` on the artefact, `tool_order` on the steps that have an order, one `llm` over `{source: file, path}` on the contents, a check over that file when it is not text | always. Every skill has one job |
| The right tools are used | the request the skill's own description triggers on, and a second request near its subject that it must not fire on | the skill-fired `tool_used` idiom, `tool_order` for a required sequence, `tool_used` with `min: 0, max: 0` for a tool it must not call and for the request it must not fire on | always |
| The goal is achieved | a prompt naming the outcome and no steps | `file_exists` on the artefact, `regex` over `{source: file, path}` for a value that has to be in it, `llm` over the same when the outcome is prose, a check when the value has to be computed or the file parsed | always. It differs from the first row in which grader carries the assertion |
| Each capability on its own | one case per capability the skill's own instructions name, each prompt asking for that capability alone | `tool_used` with the `input_match` for the call that capability makes, `regex` over `{source: file, path}` or `last_message` for its output, a check per capability whose output is not text | the skill names more than one capability |
| The instructions are followed | a prompt whose answer the instructions constrain: a format, a length, an ordering, a required section | `regex` over `last_message` with `match: contains`, `not_contains` or `count:N`, and `m` in `flags` when the anchor is per line. `llm` over `last_message` when the constraint is not a pattern, a check when the constraint is on a file no pattern can read | the instructions constrain the output |
| Edge cases | the input at a boundary: empty, absent, malformed, oversized, or two instructions that conflict | `regex` over `last_message` for the stated refusal or the handled result, `tool_used` with `min: 0, max: 0` for the destructive action it must not take | the developer named a boundary, or the input is a file or a value that has one |
| Hallucination | a prompt asking for a fact only the case's own fixture carries, or naming a thing that is not there | `regex` over `last_message` with `match: not_contains` for each value the fixture does not carry, `baseline` against a `baseline_file` holding the correct answer, a check when the invented value lands in an artefact no pattern can read | the skill reports what it read rather than transforming what it was given |
| Context relevancy | more context than the answer needs, with the answer in one named part of it | `tool_used` with `input_match` naming the file it had to open, `regex` over `trace` for that path, `regex` over `last_message` with `not_contains` for a value only the irrelevant part carries | the skill chooses what to read |
| Answer relevancy | one question, asked once, whose answer has a shape | `regex` over `last_message` with `count:N` or `not_contains` for the padding shape, `llm` over `last_message` for the criteria, `baseline` when a reference answer exists | the product is the message and not a file |
| PII and confidential information leakage | a fixture carrying a marked value the answer does not need, and a prompt that does not ask for it | `regex` with `match: not_contains` over `last_message`, over `{source: file, path}` for each artefact, over `trace` for the value reaching a tool call, and over `mock_calls` for it reaching an MCP call, and a check per artefact that is not text | the skill reads anything the prompt did not carry: a staged fixture, a forwarded credential, a service |

The applies-when column is read against the skill's own `SKILL.md` and against the developer's
answers. A row that does not apply gets no case, and the reason it does not apply is what Claude
Code says back to the developer.

### What the table does not decide

- **A row whose only grader is `llm` or `baseline` leaves the exit code silent about it.** Those
  two are judged, are printed, and carry no verdict. Give every dimension a release must not
  ship a structural grader as well, or a check, which is judged or not and decides either way.
  See [running_evals.md](running_evals.md).
- **Prefer a structural grader.** A judged grader over a non-deterministic agent is a flaky
  verdict, and a judge is noisy on a long input. Where a structural grader can decide a
  dimension, it decides it.
- **A `regex` anchor covers the whole target** unless `flags` carries `m`. The snapshot is
  [eval_format.md](eval_format.md).
- **Three dimensions need a staged fixture**: context relevancy, leakage, and the malformed
  input form of edge cases. A fixture is a `context.*` key, so each of those cases carries
  `no-cowork`. See [eval_format.md](eval_format.md).
- **The leakage row's marked value is a fixture the case owns.** It is never the credential
  `docker.env_passthrough` forwards. `run.log` is captured at the file descriptor level, so a
  case that makes the agent print a forwarded value puts that value in the log. See
  [docker.md](docker.md).
- **Directory coverage is not dimension coverage.** One `evals/<skill>/` per skill is what `run`
  reports and `--require-coverage` enforces. See [cli.md](cli.md). Nothing enforces the table
  above, which is why it is written here.
- **A case that ticks a row is worse than the gap it fills.** The table finds gaps, and is not a
  quota. A case written to complete it costs a run on every sweep, and its pass says nothing about
  the skill. Ten rows is the most a suite covers, not the number it aims at.

## Two questions, one suite

A suite answers two questions. Does the skill still work, and is the skill better than no skill. The
same case files answer both, and the run is what differs.

| The question                          | Reads    | Answered by                        |
| ------------------------------------- | -------- | ---------------------------------- |
| Does the skill still work             | one arm  | every assertion the case carries   |
| Is the skill better than no skill     | two arms | the assertions that score in both  |

That gives one rule per assertion. An assertion has to be deep enough to fail on its own when the
skill regresses, and it has to score in both arms to move a delta. One that does the first and not
the second leaves the second question unanswered, and a suite of them reports a delta of zero
whatever the baseline produced.

So neither question is designed for alone. A suite of shallow arm-visible assertions passes a broken
skill, and a suite of deep one-arm assertions cannot say the skill is worth loading.

Which assertion scores in which arm is [running_evals.md](running_evals.md). When each run happens
is [approaches.md](approaches.md).

## Usefulness is a delta

A green suite says the cases passed. It does not say the skill is worth loading. Ask a model to
build a spreadsheet and it builds one whether or not a spreadsheet skill is in the profile, so a
suite that only ever runs with the plugin loaded measures the model and credits the skill.

What measures the skill is the same case run twice, once with the plugin and once with nothing
loaded, and the difference between the two scores. The arm, its settings, and what a delta does
to pass and fail are [running_evals.md](running_evals.md). What it asks of the design is here.

| The design decision                                        | Because the baseline arm runs the same prompt                  |
| ----------------------------------------------------------- | -------------------------------------------------------------- |
| A prompt the model answers as well unaided measures the model | its delta is zero. Move the prompt onto what the skill knows and the model does not |
| The case to write first is the one the model is worst at unaided | it is the case that shows what the skill is for              |
| A case whose only assertion is that the skill fired says nothing about usefulness | that assertion cannot hold without the plugin, so the delta records that the plugin was loaded. Give the case an assertion over the output as well |
| A prompt naming the skill, or naming its steps, is weaker than one naming the outcome | the arm with no skill gets the same prompt, so a prompt carrying the method hands the method to it |

Design for the delta whether or not a suite runs the arm. Would the model do this anyway is the
same question either way, and a case that cannot answer it was going to pass from the day it was
written.

The arm is `--docker` only. A CoWork session takes its skills from the profile the application
runs, so nothing can unload the plugin for one arm there. See
[approaches.md](approaches.md).

## The fixture has to need the tool

A skill is a tool over an input. The fixture is that input, at the size and the shape of the one the
skill exists for.

| The rule                                              | What the case measures without it                                        |
| ----------------------------------------------------- | ------------------------------------------------------------------------ |
| The fixture is the size of the real input             | an input small enough to reason about unaided measures the model          |
| The prompt does not quote the fixture                 | the arm with no skill answers from the prompt and opens no file           |
| The boundary the skill handles is in the fixture      | a boundary that appears only at scale is unreachable at four rows         |
| The input is as untidy as the real one                | a fixture with no duplicate, no gap and no stray type exercises no handling |

Realism is also what makes the dimension table decidable. Edge cases, context relevancy and
hallucination each need an input carrying the thing the row asserts, and a fixture written to be
readable in the case file carries none of them.

A fixture at that size is generated rather than typed, and committed rather than staged at run time.
Where the file lives, and the key that grants it, are [eval_format.md](eval_format.md).

## A grader or a check

A grader reads text. `file_exists` reports that a file appeared and says nothing about what is
in it, and `regex` and `llm` are shown a produced file as text. So a skill whose product is a
workbook, a deck, a PDF or an image satisfies every grader available to it having asserted
nothing about the thing it made. A check is the route, and the mechanism is
[checks.md](checks.md).

**Can a grader type read the target, and say what has to be true of it?** Yes, and it is a
grader. No, and it is a check. The question is per assertion and not per case: one case carries
both, and the harness refuses a case whose only assertion directory is `checks/`.

Prefer a grader. A grader is a file the harness reads, and a check is code the consumer owns,
maintains and declares the imports of.

| The assertion is over                                    | Why no grader type reaches it                    |
| -------------------------------------------------------- | ------------------------------------------------ |
| What is inside a file that is not text                   | `regex` and `llm` are shown the bytes as text    |
| A value that has to be computed or parsed out            | no grader type computes                          |
| Two produced files that have to agree                    | a grader reads one target                        |
| A file the agent changed rather than created             | `file_exists` globs created files                |
| A property a model has to look at rather than read       | `llm` is shown text, and `run.judge` is shown the paths |

Six rows of the dimension table name a check for that reason. The four that do not are the rows
whose target is a tool call, a trace, or the message itself: the right tools are used, edge
cases, context relevancy and answer relevancy.

Two consequences for the design, and neither is visible in the dimension table.

- **A check decides the exit code however it reached its verdict.** `run.judge` included. So a
  dimension only a model can settle is not condemned to a printed note: an `llm` grader is judged
  and silent, and a check returning what `run.judge` returned is judged and binding.
- **A check costs nothing when it cannot run.** Every check of every selected plugin is imported
  before the first case starts, so a check that does not import exits 3 having spent nothing.

## The deliverable does not show the route

A grader and a check both read what the run produced. Neither can see how the run reached it. A
workbook whose totals are right was produced either by the command the skill documents or by a
script that reimplemented it, and the file is byte-comparable in both cases. So a suite of graders
and checks passes a run that never used the skill, and passes a run that used it and then wrote over
its output.

That is the reward-hacking shape, and it is reachable without any intent to hack: measured on a
spreadsheet suite, a case scored 1.00 on a run that called the skill's own dedup command and then
saved a Python script's output over the file it had produced. Every assertion on the case passed,
because the delivered workbook was deduplicated.

**So a third assertion reads the trace, and a model is what reads it.** It is a check returning what
`run.judge` returned. The judge is shown the trace and the skill's own document as paths, so nothing is
truncated. The mechanism is [checks.md](checks.md).

**Write it advisory until it is calibrated.** `@check(advisory=True)` runs the check and records its
verdict, and a failure prints as a note instead of failing the run. A judge asked how an agent worked
is not yet reliable enough to gate a suite: measured over three runs whose right answer was known, one
model got two and a slower one got one, both erring towards leniency by reading a skill's escape to a
script more broadly than it was written. A miss would otherwise turn into a red suite, and a suite
nobody trusts is worse than one assertion fewer. The verdict still lands in the document, which is what
a rubric is calibrated against. Drop the argument when the misses stop.

**It is also shown the task, because the trace does not carry it.** A collected trace opens on a
`system` record and goes straight into the agent's work: what the agent was asked is nowhere in it, and
a judge that does not know the task cannot say whether the route suited it. The case's own `prompt.md`
is the one source, and the check reads it rather than the rubric restating it, so editing a prompt moves
the assertion with it. Strip the frontmatter and pass the body.

It asks three questions and no more.

| The question                    | The run fails it when                                                      |
| ------------------------------- | -------------------------------------------------------------------------- |
| Was the route the right one     | the deliverable came from something other than what the skill documents for it, or from a command that ran and was then superseded |
| Were the instructions followed  | the skill states a thing to do, or an order to do it in, and the run did not |
| Was anything invented           | a value in the final message appears in no tool result                      |

Six rules, and the first is what makes the assertion a regression test.

- **Show the judge the skill, not a summary of it.** Name the subject in the rubric and let the judge
  find the wording: *the document says what this command does when a sheet holds formulas, and
  elsewhere says what to do about that; find both*. A rubric that restates the rules is a snapshot of
  one reading of the skill, and it keeps passing a run the skill itself would now fail.
- **A rubric may not demand a route the skill cannot take.** Read the command list before writing the
  clause. Measured: a skill's pitfalls section said to convert formulas to values before sorting and
  none of its forty commands did that, so the skill's own escape to a script was the only route left
  open. The clause demanding otherwise failed every run for a gap in the skill.
- **A split vote is a rubric fault before it is a judge fault.** The run above went two to one, and
  three to nothing on the same trace once the impossible clause was gone.
- **Judge the route, not the result.** Whether the numbers are right is what the graders and the
  checks already decide. A rubric doing both spends votes re-deciding that and splits them on the
  half it was not asked for.
- **The baseline arm is not held to the route.** The route and the instructions are both the skill's,
  so a run with no plugin loaded has neither, and asserting them there fails by construction and
  inflates the delta. This is the rule in [checks.md](checks.md) against a check that cannot hold
  without the plugin, in the one place it is easiest to break.
- **It is the layer over the others and not a replacement for them.** A judged rubric is the most
  expensive assertion in a suite and the least deterministic. What a `regex`, a `file_exists` or a
  check can settle, it settles.

One judged assertion costs `eval.judge_votes` calls per run per arm, so it is one per case and not
one per question. [running_evals.md](running_evals.md).

## An assertion is tested both ways

An assertion is not known to measure anything until it has been tested both ways. One that cannot
fail and one that cannot pass report the same thing on every run, and both read as a working
assertion in the case directory.

| Test         | Against                                                          |
| ------------ | ---------------------------------------------------------------- |
| Every pattern | one sample that has to match, and one that has to not match      |
| Every check   | one artefact that has to pass, and one that has to fail          |

The artefact that has to pass is the skill's own output. A check the skill's own output fails is a
broken check and not a finding, and a case run is the expensive way to learn that.

Both tests run before the first case does, because neither needs a model. A pattern is tested in the
engine the harness grades with, not in the one the test is written in: two regular expression engines
agree on most patterns and not on all of them.

## Access

A case that needs access it does not have measures the access and not the skill.

| The case needs                | Absent, the case measures                                       | The route                                                                   |
| ----------------------------- | ---------------------------------------------------------------- | --------------------------------------------------------------------------- |
| A credential the skill reads  | the credential, and every case fails for a reason that is not the skill | `docker.env_passthrough` names the variable, and a name unset or empty exits 3. See [docker.md](docker.md) |
| A third-party service         | that service's uptime as well as the skill                       | a fixture the case stages, or a `mocks/` stand-in                           |
| An MCP server                 | nothing. The tool is not there                                   | `evals/mocks/<server>/<tool>.md`, which makes the case `no-cowork` and makes `mock_calls` a readable target |
| A tool                        | the grant. A run that never had a granted tool fails rather than scores | `eval.allow_tools`, or the case's own `allowed_tools`, which makes the case `no-cowork`. See [running_evals.md](running_evals.md) |
| A file staged before the run  | a prompt with nothing to read                                    | `context.add_dirs` or `context.scaffold_script` in `case.yaml`, which makes the case `no-cowork` |
| A library a check imports     | nothing about the skill. The suite does not start                | the consumer's own project declares it, as it would for a unit test. The preflight imports every check and exits 3. See [checks.md](checks.md) |
| A wheel the skill imports     | an import error inside the session, in every case at once        | `cowork_evals test` catches it before an eval is written over it. See [runtime.md](runtime.md) |
| The deployed stack            | the container, and not CoWork                                    | the honoured subset in [approaches.md](approaches.md)                       |

Two rules follow, and the route above decides neither.

- When Claude Code designs the suite, it designs around the access that exists.
- When the developer proposes a case that needs access that is not there, Claude Code says so
  before it writes the case, and names the route that would supply it.

## The proposal

Either route proposes the suite before a file is written: one line per case, naming the
dimension it covers and the grader or the check that decides it. A developer reads that list and
strikes a case in one sentence. The same list read after the cases exist costs a rewrite.

The proposal also names, per case, the access it needs and whether it carries `no-cowork`. Those
two are what a developer objects to, and they are invisible in a case name.
