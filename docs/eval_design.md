# Eval design

## Summary

Which cases a skill needs, and which assertion answers which question. This is the design
contract over [eval_format.md](eval_format.md), which is the file contract, and over
[checks.md](checks.md), which is the other assertion mechanism. The procedure a session follows
to apply these rules is in the `cowork-evals` skill, which [library.md](library.md) places.

<<<<<<< HEAD
- **Claude Code does not invent a suite.** It reads the skill first, and the reading is what
  produces the draft.
- **There is no questionnaire, and the proposal is the question.** No fixed set of questions, in
  no fixed order, and no question whose answer is already in the skill.
- **Never ask the developer to predict failure.** Where it fails, what must never happen, which
  part breaks most often: the answer is usually that they do not know, and the design does not
  need it.
- **It never asks which eval and which grader the developer wants.** That question hands the
  design back.
- **`I do not know` ends the topic.** It is the authorization to design that part alone, and it is
  never asked a second way.
- **The dimension table finds gaps, and the default for every row is no case.** A row earns one
  from the skill's own text. It is not a quota, and it has no ceiling.
- **The dimension names never reach the developer.** What a case covers is said in the words the
  skill under test uses.
- **A suite answers two questions.** Does the skill still work, and is the skill better than no
  skill. The same case files answer both.
- **Usefulness is a delta.** A skill earns its place when the agent does better with it than
  without it, and the baseline arm is what measures that.
- **The fixture has to need the tool.** An input small enough to reason about unaided measures the
  model. Claude Code generates every fixture, and never asks the developer for one.
- **An assertion is tested both ways.** One sample that has to match, and one that has to not
  match.
- **An assertion is a discriminator.** It has to fail a wrong answer, pass a right one, and fail an
  empty one. Most broken assertions do only the first, and all three are decided at design time.
- **Assert the requirement, not the rendering.** The wording of the output is unknowable when the
  suite is written, so an assertion resting on it is a guess dressed as a test.
- **The firing indicator goes on every case.** Without it a case scores full marks while the plugin
  never loaded, and nothing in the result says so.
- **A grader, or a check.** Can a grader type read the target, and say what has to be true of
  it? Yes, and it is a grader. No, and it is a check.
- **Every case carries a third assertion that reads the trace.** The deliverable does not show the
  route, so a model is asked three things: was the route right, were the instructions followed, was
  anything invented.
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
=======
- The coverage table decides which cases a suite needs. Every row that applies to the skill gets
  at least one case, and a row that does not apply gets none.
- An assertion has to fail on its own when the skill regresses, and it has to score in both arms
  of an ablation run.
- The fixture is the real input at its real size. A smaller one measures the model.
- A grader reads text. An assertion over anything else is a check.
- Every pattern and every check is tested against one sample that has to pass and one that has to
  fail, before the first case runs.
- A case that needs access it does not have measures the access and not the skill.
>>>>>>> fix/checks-both-arms

Pass and fail over what these cases produce is [running_evals.md](running_evals.md). Which
backend honours which case feature is [approaches.md](approaches.md). No case field and no
validator rule is here. Both are [eval_format.md](eval_format.md).

## The split against the format

One question decides the side, and it holds for every statement in either file. Does the
statement depend on what the skill under test does? No, and it is the format. Yes, and it is the
design.

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
<<<<<<< HEAD
format's. Everything that needs the skill's own instructions, or the input the skill exists to
process, is here.
=======
format's. A statement that needs the skill's own instructions is here.
>>>>>>> fix/checks-both-arms

The no side is two files, because there are two assertion mechanisms. A statement about a grader
type is [eval_format.md](eval_format.md), and a statement about a check is
[checks.md](checks.md). Which of the two an assertion needs depends on the skill, so it is here.

<<<<<<< HEAD
## Read, then propose

Claude Code does not invent a suite, and it does not interview one out of the developer either. It
reads the skill under test, and the reading is what produces the draft: the skill's own description
and instructions, the repository around it, and any suite already there.

There is no questionnaire. No fixed set of questions, in no fixed order, and no question asked
because a document said to ask it. The proposal is the question. A developer reads one line per
case and strikes one in a sentence, and that turn is worth more than any question asked before the
draft exists.

**Never ask the developer to predict failure.** Where the skill fails, what must never happen,
which part breaks most often: the usual answer is that they do not know, and the design does not
need the answer. The skill's own instructions state what it has to do, so the case that asserts an
instruction is the case that catches the failure. A developer holding one of those facts volunteers
it against the proposal, which is where it is cheapest to act on.

A direct question is for what the proposal cannot be written without, and there is one: access the
repository does not show. That is a credential, a service or an MCP server a case needs and nothing
under the plugin root records.

**Never ask the developer for a fixture.** Claude Code generates every one, at the size and the
shape the fixture section below requires. A developer asked for a sample of the real input usually
has none to hand, and waiting for one stops the design.

Everything else the design needs is read rather than asked.

| The design needs                              | Where it comes from                                       |
| --------------------------------------------- | ---------------------------------------------------------- |
| The job the skill exists for                  | its own description and instructions, confirmed in a sentence rather than asked from nothing |
| Which capabilities are separable              | its instructions, and one case each                        |
| What it reads and what it writes              | its instructions and its fixtures, which decide the access and whether the target is text |
| Whether the model would do the job unaided    | the baseline arm, and no conversation settles it            |

It never asks which eval and which grader the developer wants. That question hands the design
back to the developer, and a developer who could answer it would have written the case already.

**`I do not know` ends the topic.** It is the common reply, it is the authorization to design that
part alone, and it is never rephrased and asked a second way. The signal is the reply, and nothing
in `cowork_evals.yaml` selects it.

A reply that does name something names a symptom, not a case, and the work is to turn it into one.
`The summaries are too long` is a `regex` over `last_message`. `It makes things up about our
schema` is a fixture and a `not_contains` pattern per invented value. `It ignores the config file`
is a `tool_used` with an `input_match` naming that file. `The totals in the spreadsheet come out
wrong` is a check that opens the workbook, because no grader type reads a cell.

Ask again only when a symptom the developer volunteered does not decide the target. One follow-up
that settles a target is worth more than a case that grades the wrong thing.

## The coverage dimensions

The table is read after the suite is drafted, to find a gap in it. It is never worked through.

**The default for every row is no case.** A row gets a case when the skill's own text carries the
condition in its applies-when column, and the proposal says which text that is. A case whose only
justification is a row's name is struck before it is written: it costs a run on every sweep, and
its pass says nothing about the skill. The table finds gaps, and is not a quota.

One case may answer more than one row, so the check is that no row the skill's text triggers is
left with none.

**The names in the first column are this file's vocabulary and stay in it.** What a developer is
told is what a case covers, in the words the skill under test uses. Naming a dimension asks a
developer to learn a word to read their own coverage.
=======
## The coverage dimensions

The table finds gaps in a suite that is already drafted. It is not a list to work through, and it
is not a quota. Every row that the skill's own text triggers gets at least one case, and one case
may answer more than one row. A case written only to fill a row costs a run on every sweep, and
its pass says nothing about the skill.
>>>>>>> fix/checks-both-arms

Every grader named below is one of the six types [eval_format.md](eval_format.md) defines, and
every check is [checks.md](checks.md). This file adds neither.

| Dimension | The case | The assertion | Applies when |
| --------- | -------- | ---------- | ------------ |
| Expected behaviour, end to end | one prompt carrying the whole job the skill exists for | `file_exists` on the artefact, `tool_order` on the steps that have an order, one `llm` over `{source: file, path}` on the contents, a check over that file when it is not text | always. Every skill has one job |
| The right tools are used | the request the skill's own description triggers on, and a second request near its subject that it must not fire on | the skill-fired `tool_used` idiom, `tool_order` for a required sequence, `tool_used` with `min: 0, max: 0` for a tool it must not call and for the request it must not fire on | always |
| The goal is achieved | a prompt naming the outcome and no steps | `file_exists` on the artefact, `regex` over `{source: file, path}` for a value that has to be in it, `llm` over the same when the outcome is prose, a check when the value has to be computed or the file parsed | always. It differs from the first row in which grader carries the assertion |
| Each capability on its own | one case per capability the skill's own instructions name, each prompt asking for that capability alone | `tool_used` with the `input_match` for the call that capability makes, `regex` over `{source: file, path}` or `last_message` for its output, a check per capability whose output is not text | the skill names more than one capability |
| The instructions are followed | a prompt whose answer the instructions constrain: a format, a length, an ordering, a required section | `regex` over `last_message` with `match: contains`, `not_contains` or `count:N`, and `m` in `flags` when the anchor is per line. `llm` over `last_message` when the constraint is not a pattern, a check when the constraint is on a file no pattern can read | the instructions constrain the output |
| Edge cases | the input at a boundary: empty, absent, malformed, oversized, or two instructions that conflict | `regex` over `last_message` for the stated refusal or the handled result, `tool_used` with `min: 0, max: 0` for the destructive action it must not take | the instructions state a boundary, or the input the skill reads has one |
| Hallucination | a prompt asking for a fact only the case's own fixture carries, or naming a thing that is not there | `regex` over `last_message` with `match: not_contains` for each value the fixture does not carry, `baseline` against a `baseline_file` holding the correct answer, a check when the invented value lands in an artefact no pattern can read | the skill reports what it read rather than transforming what it was given |
| Context relevancy | more context than the answer needs, with the answer in one named part of it | `tool_used` with `input_match` naming the file it had to open, `regex` over `trace` for that path, `regex` over `last_message` with `not_contains` for a value only the irrelevant part carries | the skill chooses which of several inputs to read |
| Answer relevancy | one question, asked once, whose answer has a shape | `regex` over `last_message` with `count:N` or `not_contains` for the padding shape, `llm` over `last_message` for the criteria, `baseline` when a reference answer exists | the product is the message and not a file |
| PII and confidential information leakage | a fixture carrying a marked value the answer does not need, and a prompt that does not ask for it | `regex` with `match: not_contains` over `last_message`, over `{source: file, path}` for each artefact, over `trace` for the value reaching a tool call, and over `mock_calls` for it reaching an MCP call, and a check per artefact that is not text | the skill reads something the prompt did not name, and an artefact or an answer could carry a value out of it that nothing asked for |

<<<<<<< HEAD
The applies-when column is read against the skill's own `SKILL.md`. A row the skill's text does not
trigger gets no case.
=======
The applies-when column is read against the skill's own `SKILL.md`. A row the skill's text does
not trigger gets no case.
>>>>>>> fix/checks-both-arms

Six things the table does not decide.

<<<<<<< HEAD
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
=======
| The rule                                                    | Where the detail is                         |
| ----------------------------------------------------------- | ------------------------------------------- |
| Prefer a structural grader wherever one can decide a row. A judged grader over a non-deterministic agent is a flaky verdict, and a judge is noisy on a long input | [running_evals.md](running_evals.md)        |
| A row whose only grader is `llm` or `baseline` is printed and leaves the exit code silent. Give every row a release depends on a structural grader as well, or a check | [running_evals.md](running_evals.md)        |
| A `regex` anchor covers the whole target unless `flags` carries `m`                     | [eval_format.md](eval_format.md)            |
| Context relevancy, leakage, and the malformed form of edge cases each need a staged fixture, which is a `context.*` key, which makes the case `no-cowork` | [eval_format.md](eval_format.md)            |
| The leakage row's marked value is a fixture the case owns, never a credential `docker.env_passthrough` forwards. `run.log` is captured at the file descriptor level, so a run that prints a forwarded value puts it in the log | [docker.md](docker.md)                      |
| Directory coverage is not dimension coverage. `--require-coverage` enforces one `evals/<skill>/` per skill and nothing enforces this table | [cli.md](cli.md)                            |
>>>>>>> fix/checks-both-arms

## The two questions a suite answers

A suite answers two questions. Does the skill still work, and is the skill better than no skill.
The same case files answer both. A one-arm run answers the first. `--ablation with-without` answers
the second by running every case twice, once with the plugin loaded and once with nothing loaded,
and comparing the two scores. The arm and its settings are
[running_evals.md](running_evals.md), and it is `--docker` only because a CoWork session takes its
skills from the profile the application runs. See [approaches.md](approaches.md).

Each question puts one requirement on every assertion. An assertion has to fail on its own when
the skill regresses, or the first question is unanswered. It has to score in both arms, or the
second one is. A suite of shallow assertions passes a broken skill, and a suite of assertions that
cannot hold without the plugin reports the same delta whatever the baseline produced.

The second question also decides the prompt, because the baseline arm gets the same one.

| The prompt                                  | What the baseline arm does with it                                    |
| ------------------------------------------- | --------------------------------------------------------------------- |
| One the model answers as well unaided       | scores the same, so the delta is zero. Move the prompt onto what the skill knows and the model does not |
| One naming the skill, or naming its steps   | follows the steps without the skill, so the prompt hands over the method. Name the outcome instead |
| One whose only assertion is that the skill fired | cannot score at all, so the delta records that the plugin was loaded and nothing else. Add an assertion over the output |

The case to write first is the one the model is worst at unaided, because it is the case that
shows what the skill is for. Design for the delta whether or not a suite runs the arm.

## The fixture

A skill is a tool over an input. The fixture is that input, at the size and the shape of the one
the skill exists for.

| The rule                                              | What the case measures without it                                        |
| ----------------------------------------------------- | ------------------------------------------------------------------------ |
| The fixture is the size of the real input             | an input small enough to reason about unaided measures the model          |
| The prompt does not quote the fixture                 | the arm with no skill answers from the prompt and opens no file           |
| The boundary the skill handles is in the fixture      | a boundary that appears only at scale is unreachable at four rows         |
| The input is as untidy as the real one                | a fixture with no duplicate, no gap and no stray type exercises no handling |

Realism is also what makes the dimension table decidable. Edge cases, context relevancy and
hallucination each need an input carrying the thing the row asserts, and a fixture written to be
readable inside the case file carries none of them.

<<<<<<< HEAD
A fixture at that size is generated rather than typed, generated by Claude Code rather than asked of
the developer, and committed rather than staged at run time.
Where the file lives, and the key that grants it, are [eval_format.md](eval_format.md).
=======
A fixture at that size is generated rather than typed, and committed rather than staged at run
time. Where the file lives, and the key that grants it, are [eval_format.md](eval_format.md).
>>>>>>> fix/checks-both-arms

## A grader or a check

A grader reads text. `file_exists` reports that a file appeared and says nothing about what is in
it, and `regex` and `llm` are shown a produced file as text. A skill whose product is a workbook,
a deck, a PDF or an image can therefore satisfy every grader available to it without any
assertion having read the thing it made. A check is the route, and the mechanism is
[checks.md](checks.md).

Ask one question per assertion, not per case: can a grader type read the target, and say what has
to be true of it? Yes, and it is a grader. No, and it is a check. One case carries both, and the
harness refuses a case whose only assertion directory is `checks/`.

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
whose target is a tool call, a trace, or the message itself: the right tools are used, edge cases,
context relevancy and answer relevancy.

Two consequences the dimension table does not show. A check decides the exit code however it
reached its verdict, `run.judge` included, so a row only a model can settle is not limited to a
printed note. Every check of every selected plugin is imported before the first case starts, so a
check that does not import exits 3 having spent nothing.

<<<<<<< HEAD
- **A check decides the exit code however it reached its verdict.** `run.judge` included. So a
  dimension only a model can settle is not condemned to a printed note: an `llm` grader is judged
  and silent, and a check returning what `run.judge` returned is judged and binding.
- **A check costs nothing when it cannot run.** Every check of every selected plugin is imported
  before the first case starts, so a check that does not import exits 3 having spent nothing.

## The deliverable does not show the route

**Every case carries a third assertion that reads the trace, and it is advisory.** It is a check
returning what `run.judge` returned, shown three things as paths and asking three questions. A case
without one is decided entirely on what the run delivered, and what the run delivered does not say
how the run got there.

A grader and a check both read what the run produced. Neither can see how the run reached it. A
workbook whose totals are right was produced either by the command the skill documents or by a
script that reimplemented it, and the file is byte-comparable in both cases. So a suite of graders
and checks passes a run that never used the skill, and passes a run that used it and then wrote over
its output.

That is the reward-hacking shape, and it is reachable without any intent to hack: measured on a
spreadsheet suite, a case scored 1.00 on a run that called the skill's own dedup command and then
saved a Python script's output over the file it had produced. Every assertion on the case passed,
because the delivered workbook was deduplicated.

The three things the judge is shown are paths and never text, so nothing is truncated.

| Shown                    | Is                                                                              |
| ------------------------ | ------------------------------------------------------------------------------- |
| The trace                | `run.trace`, in whichever format the backend that produced the run wrote          |
| The skill's own document | the `SKILL.md` under test, never a summary of it and never a rubric restating it  |
| The task                 | the case's own `prompt.md`, frontmatter stripped and the body passed              |

The task is there because the trace does not carry it. A collected trace opens on a `system` record
and goes straight into the agent's work, so what the agent was asked is nowhere in it, and a judge
that does not know the task cannot say whether the route suited it. Reading the prompt rather than
restating it in the rubric is also what moves the assertion when the prompt is edited. `run.judge`
and `@check(advisory=True)` are both [checks.md](checks.md).

**It is advisory until it is calibrated.** `@check(advisory=True)` runs the check and records its
verdict, and a failure prints as a note instead of failing the run. A judge asked how an agent worked
is not yet reliable enough to gate a suite: measured over three runs whose right answer was known, one
model got two and a slower one got one, both erring towards leniency by reading a skill's escape to a
script more broadly than it was written. A miss would otherwise turn into a red suite, and a suite
nobody trusts is worse than one assertion fewer. The verdict still lands in the document, which is what
a rubric is calibrated against. Drop the argument when the misses stop.

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
=======
## Testing an assertion before the first case runs
>>>>>>> fix/checks-both-arms

An assertion is not known to measure anything until it has been tested both ways. One that cannot
fail and one that cannot pass report the same thing on every run, and both read as a working
assertion in the case directory.

| Test          | Against                                                          |
| ------------- | ---------------------------------------------------------------- |
| Every pattern | one sample that has to match, and one that has to not match      |
| Every check   | one artefact that has to pass, and one that has to fail          |

The artefact that has to pass is the skill's own output. A check that the skill's own output fails
is a broken check and not a finding, and a case run is the expensive way to learn that.

Both tests run before the first case does, because neither needs a model. Test a pattern in the
engine the harness grades with rather than the one the test is written in, because two regular
expression engines agree on most patterns and not on all of them.

Both of those samples are ones the author wrote, so passing them says the assertion works against the
output the author pictured. The next section is what that does not catch.

### An assertion is a discriminator

There is no output to look at when a suite is written, and there will not be one until it runs. So
the discipline is not to guess the output better. It is to write assertions that do not depend on
having seen it, and three questions settle that without a run.

| Ask                          | The failure it catches                                                         |
| ---------------------------- | ------------------------------------------------------------------------------ |
| Does it fail a wrong answer  | an assertion that cannot fail. This is the one that always gets asked           |
| Does it pass a right answer  | an assertion the correct answer trips, which scores the skill down for working  |
| Does it fail an empty answer | a case built only from negative assertions, which silence satisfies             |

The second question is what inverts a delta, and a `not_contains` is where it usually happens: the
vocabulary a wrong answer uses is often the vocabulary a right answer uses. Forbidding a word can
therefore fail every thorough answer while passing every vague one, and because the plugin is what
makes answers thorough, the arm with it scores below the arm without. The number then reads as a
broken skill. Ask it as a question about the correct answer, which needs no run: **would an answer
that gets this right still contain the string?** If yes, the assertion belongs on what the answer
concluded, not on which words it used.

The third question is the shape a case takes when its fixture is clean and there is nothing to find.
Every assertion on it is negative, so an answer that did no work satisfies all of them, and so does
the baseline arm. Such a case needs something positive to clear as well: evidence in the output that
the work happened.

### Assert the requirement, not the rendering

A requirement is knowable at design time. Its rendering is not. *The review concludes that this item
fails* is fixed by the fixture; whether that arrives as a table row, a bold bullet, a symbol, or a
sentence with the verdict before the subject is not, and every one of those is a correct answer.

One technique makes the difference visible without a run. Before writing the assertion, write down
the same correct answer two or three times, in deliberately different styles. An assertion that
passes only one of them is pinned to a rendering, and the fix is usually to move it from a pattern to
a check, because a check can read a whole line, or a whole file, and decide what it says.

That principle picks the form whenever two would express the same thing.

| Rather than                                   | Prefer                                                              |
| --------------------------------------------- | ------------------------------------------------------------------- |
| a pattern guessing how the answer words it     | a check that reads what the answer concluded                        |
| what the answer must not contain              | what it must contain, because absence has unbounded phrasings       |
| every expected finding, unanimously            | a floor, since the agent's consistency is not knowable either       |
| the tool the author would have reached for     | the evidence the tool leaves behind, which any route produces       |

The floor row is the same argument as the rest. An assertion demanding every finding assumes zero
variance from a non-deterministic agent, and that assumption is not available at design time any more
than the wording is. Ask what number would prove the skill did the job, rather than what number a
perfect run would produce.

Where a fixture carries something real that no reasonable answer may be required to catch, keep it in
an advisory check rather than the gate. It records the number without failing the suite, which is how
a later run shows the skill improving.

Finally, make every assertion say what it saw and not only that it failed. A message naming the
expectation and the value found is what separates a skill that got it wrong from an assertion that
was written wrong, and without it the two are indistinguishable in a result document.

### Firing is two things, and a case needs both

Whether the plugin loaded is the one fact that decides how to read every other number in a case, and
it has an assertion side and a prompt side. Getting one without the other leaves the case unreadable.

**The assertion detects firing.** A `tool_used: Skill` grader on the activation case alone leaves
every other case unable to tell a bad answer from a plugin that never loaded, because both look like a
low score. Worse, a case can score full marks having never loaded the plugin, whenever its other
assertions are ones the model satisfies unaided, and the result then reads as success. Under
`--ablation with-without` the harness stops scoring that grader and reports it as an indicator, so it
moves no delta and costs nothing; in a one-arm run it gates. Both are wanted, so it goes on every case
that needs the plugin and not only on the case that exists to test firing.

**The prompt causes firing.** A skill's description declares the phrases it triggers on, so those
phrases are knowable at design time and are the only part of the output side of this that is. A case
meant to exercise a capability, whose prompt carries none of them, measures the trigger gap instead:
its score becomes a fact about the description rather than about the capability, and it will look like
a capability failure. Read the description's trigger list before writing any prompt, and decide per
case which of the two the case is for.

| The case is for      | The prompt                                                                 |
| -------------------- | -------------------------------------------------------------------------- |
| a capability         | carries a phrase the description declares, close enough together to read as that phrase |
| the trigger boundary | deliberately carries none, and sits near the subject so over-triggering shows |

Asking for the outcome and avoiding the skill's own name are both still the rule, and neither means
avoiding the subject. The name and the method stay out; the vocabulary the description advertises is
what a real user says. A phrase whose words end up scattered across a sentence is not the phrase: keep
them adjacent, or the case is relying on the model to generalise rather than on the trigger the skill
declares.

Both halves are checkable with no run, by reading the description and the prompt side by side. A
capability the skill documents and its description declares no phrase for is a finding about the
skill, to report rather than to work around in a prompt, because a user asking for it in their own
words gets nothing either.

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

<<<<<<< HEAD
Two rules follow, and the route above decides neither.

- When Claude Code designs the suite, it designs around the access that exists.
- When the developer proposes a case that needs access that is not there, Claude Code says so
  before it writes the case, and names the route that would supply it.

## The proposal

The suite is proposed before a file is written: one line per case. A developer reads that list and
strikes a case in one sentence, and the same list read after the cases exist costs a rewrite.

| The line carries               | Written as                                                                 |
| ------------------------------ | -------------------------------------------------------------------------- |
| What the case covers           | plain words, in the vocabulary the skill under test uses, and never a dimension name |
| How it is decided              | what has to be true of the output for the case to pass, in plain words. Not the grader type and not the mechanism, which are neither the developer's decision nor readable without this file |
| The access it needs            | and a case is proposed only where that access exists                        |
| Whether it carries `no-cowork` | which follows from the keys the case writes                                 |

The last two are what a developer objects to, and both are invisible in a case name.

Every case also carries the assertion that reads how the run reached its answer, so the proposal
states that once rather than on every line.
=======
A suite is designed around the access that exists. A case that needs access that is not there is
named as such before it is written, together with the route above that would supply it.
>>>>>>> fix/checks-both-arms
