# Eval design

## Summary

What to evaluate in a Claude CoWork skill, and how to write assertions that measure the skill rather
than the model underneath it. It follows the work from reading the skill to reading what a run
reports back.

[eval_format.md](eval_format.md) is the contract a case file is written to.
[checks.md](checks.md) is how to write a Python assertion where no grader will do. Neither decides
what to assert. Pass and fail is [running_evals.md](running_evals.md), and which backend honours
which part of a case is [approaches.md](approaches.md).

## How the work goes

Read first. The skill under test, the repository around it, and any suite already there are enough to
draft the whole suite. Bring the developer a draft, not a questionnaire.

Propose before writing any file, one line per case:

- what the case covers, in plain words
- what has to be true of the output for it to pass
- what access it needs
- whether it carries `no-cowork`

Use the words the skill uses, not this file's. A developer reading `the leakage dimension is covered`
has to learn a word to find out what was tested. They can strike a case in one sentence at this
point. After the files exist, the same objection costs a rewrite.

Then ask almost nothing.

| Never ask                                                                   | Because                                                          |
| --------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Where the skill fails, what must never happen, which part breaks most often | they usually do not know, and the skill's instructions already state what it has to do |
| Which eval or which grader they want                                        | it hands the design back                                          |
| For a fixture, or a sample of the real input                                | they rarely have one to hand. Generate every fixture              |

One thing is worth asking: access the repository does not show, such as a credential the skill reads,
a service it calls, or an MCP server. `I do not know` ends a topic.

What a developer volunteers is a symptom, not a case. `The summaries are too long` is a `regex` over
`last_message`. `It ignores the config file` is a `tool_used` with an `input_match` naming that file.
`The totals come out wrong` is a check that opens the workbook, because no grader reads a cell.

Write the fixtures, the prompts and the assertions. Run on `--docker`, then under
`--ablation with-without`. Reading what comes back is the last section here.

## Which cases the suite needs

Skills fail in a small number of recognisable ways, and the table lists them. Read it against a draft
you already have, to find a gap you missed.

The default for every row is no case. A row earns one when the skill's own text carries the condition
beside it, and one case often answers several rows. There is no quota and no target number of cases.
A case written only to fill a row costs a run on every sweep and says nothing about the skill.

Every grader below is one of the six types [eval_format.md](eval_format.md) defines, and every check
is [checks.md](checks.md). This file adds neither.

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

Three rows need a fixture staged before the run, which is a `context.*` key, which makes the case
`no-cowork`: context relevancy, leakage, and the malformed form of edge cases. The leakage row's
marked value is always the case's own fixture, never a real credential forwarded by
`docker.env_passthrough`, because `run.log` captures whatever the container prints. See
[docker.md](docker.md).

Nothing enforces this table. `--require-coverage` only checks that each skill has an
`evals/<skill>/` directory. See [cli.md](cli.md).

## Measuring the skill and not the model

A suite that only runs with the plugin loaded cannot say whether the plugin helped. Ask a model to
build a spreadsheet and it will probably build one either way.

`--ablation with-without` runs every case twice, once with the plugin and once with nothing loaded.
The difference between the scores is the answer. It is `--docker` only, because a CoWork session takes
its skills from the profile the application is running. See [approaches.md](approaches.md).

The baseline run gets the same prompt, which decides what makes a prompt useful.

| The prompt                                | In the baseline arm                                                |
| ----------------------------------------- | ------------------------------------------------------------------ |
| One the model answers as well unaided     | scores the same, so the delta is zero. Move it onto what the skill knows |
| One naming the skill, or its steps        | follows the steps without the skill. Name the outcome instead       |
| The one the model is worst at unaided     | the case worth writing first                                       |

Every assertion needs two properties from that arm. It has to fail on its own when the skill
regresses, and it has to score in both arms, or the delta cannot move. Design for the delta whether
or not you run the arm.

The fixture is the other half. A skill is a tool over an input, so the fixture is that input at the
size and shape of the real one.

| The rule                                          | Without it the case measures                                       |
| ------------------------------------------------- | ------------------------------------------------------------------ |
| The fixture is the size of the real input         | the model, since a small input can be reasoned about unaided        |
| The prompt does not quote the fixture             | the prompt. The arm with no skill never opens the file              |
| The boundary the skill handles is in the fixture  | nothing. A boundary that appears at scale is unreachable at four rows |
| The input is as untidy as the real one            | nothing. No duplicate, no gap and no stray type exercises no handling |

Realism is also what makes the table above decidable: edge cases, hallucination and context relevancy
each need an input carrying the thing the row asserts. Generate a fixture that size rather than typing
one, and commit it. Where it lives is [eval_format.md](eval_format.md).

## Choosing the assertions

Every case carries three assertions.

**Did the plugin load?** A `tool_used: Skill` grader, on every case that needs the plugin and not
only the one testing activation. Without it a case can score full marks having never loaded the
plugin, whenever its other assertions are ones the model satisfies unaided.

Under `--ablation with-without` the harness reports that grader as an indicator rather than scoring
it, so it moves no delta. In a one-arm run it gates.

Firing has a prompt side too. A skill's description declares the phrases it triggers on, so a
capability case carries one of them with its words kept together. A case testing the trigger boundary
carries none, while staying near the subject. A capability the skill documents but declares no phrase
for is a finding about the skill, not something to work around in a prompt.

**Is the output right?** A grader or a check. A grader reads text: `file_exists` says a file appeared
and nothing about what is in it, and `regex` and `llm` are handed a produced file as text.

So a skill whose product is a workbook, a deck, a PDF or an image can satisfy every grader available
to it without one assertion having looked at the thing it made.

Ask per assertion, not per case: can a grader type read this target and say what has to be true of it?
Yes is a grader, no is a check. One case usually carries both, and the harness refuses a case whose
only assertion directory is `checks/`.

| The assertion is over                                    | Why no grader type reaches it                    |
| -------------------------------------------------------- | ------------------------------------------------ |
| What is inside a file that is not text                   | `regex` and `llm` are shown the bytes as text    |
| A value that has to be computed or parsed out            | no grader type computes                          |
| Two produced files that have to agree                    | a grader reads one target                        |
| A file the agent changed rather than created             | `file_exists` globs created files                |
| A property a model has to look at rather than read       | `llm` is shown text, and `run.judge` is shown the paths |

Prefer a grader where either works: a grader is a file the harness reads, a check is code you own.

Prefer a structural grader to a judged one. A judge over a non-deterministic agent is flaky, and
`llm` and `baseline` results are printed but carry no verdict, so a dimension resting on one leaves
the exit code silent. A check is the exception, since it decides the exit code however it reached its
verdict, `run.judge` included.

**Did the run take the right route?** The next section.

## The third assertion, over the route the run took

A grader and a check read what the run produced. Neither sees how it got there. A workbook whose
totals are right might come from the skill's own command or from a script that reimplemented it, and
the file is identical either way.

So a suite of graders and checks passes a run that never used the skill. Measured: a case scored 1.00
on a run that called the skill's dedup command and then saved a Python script's output over the file
it had produced.

The third assertion reads the transcript, and a model reads it. It is a check returning what
`run.judge` returned, shown three paths rather than text so nothing is truncated:

- `run.trace`
- the `SKILL.md` under test
- the case's own `prompt.md`, frontmatter stripped, because the transcript does not carry the task

It asks three questions and no more.

| The question                    | The run fails it when                                                      |
| ------------------------------- | -------------------------------------------------------------------------- |
| Was the route the right one     | the deliverable came from something other than what the skill documents for it, or from a command that ran and was then superseded |
| Were the instructions followed  | the skill states a thing to do, or an order to do it in, and the run did not |
| Was anything invented           | a value in the final message appears in no tool result                      |

Write it `@check(advisory=True)` until the rubric is calibrated. An advisory check records its real
verdict and decides nothing: a failure prints as a note, out of the score and out of the exit code.

A model asked how an agent worked is not reliable enough to gate a suite yet. Measured over three
runs whose right answer was known, one model got two and a slower one got one, both erring towards
leniency. The verdict still lands in the document, which is what you calibrate against.

| The rule for the rubric                                   | Because                                                                    |
| --------------------------------------------------------- | -------------------------------------------------------------------------- |
| Show the judge the skill, not a summary of it             | a rubric restating the rules captures one reading, and keeps passing a run the skill would now fail |
| Name the subject and let the judge find the wording       | the assertion then moves with the skill the next time it is edited          |
| Never demand a route the skill cannot take                | read its command list first. A clause asking the impossible fails every run |
| Treat a split vote as a rubric fault before a judge fault | usually the clause, not the model, is what two votes read differently       |
| Judge the route, not the result                           | the graders and the checks already decide whether the numbers are right     |
| Do not hold the baseline arm to it                        | the route and the instructions are the skill's, so asserting them with no plugin loaded fails by construction and inflates the delta |

It is the most expensive assertion in a suite and the least deterministic, costing
`eval.judge_votes` model calls per run per arm. One per case, not one per question.

## Knowing the assertions work before the suite runs

An assertion that cannot fail and one that cannot pass report the same thing every run, and both look
like working assertions in a case directory. So test each one both ways before any case runs.

| Test          | Against                                                      |
| ------------- | ------------------------------------------------------------ |
| Every pattern | one sample that has to match, and one that has to not match  |
| Every check   | one artefact that has to pass, and one that has to fail       |

Neither test needs a model. Three things to get right:

- Test a pattern in the engine the harness grades with, not the one your own tests use. Two regular
  expression engines agree on most patterns and not all.
- A `regex` anchor covers the whole target unless `flags` carries `m`.
- The artefact that has to pass is the skill's own output. A check its own output fails is a broken
  check, not a finding.

Both samples are yours, so passing them only proves the assertion works on the output you imagined.
There is no real output until the suite runs. So write assertions that do not depend on having seen
one, which three questions settle.

| Ask                          | The failure it catches                                                         |
| ---------------------------- | ------------------------------------------------------------------------------ |
| Does it fail a wrong answer  | an assertion that cannot fail. The one everybody asks                           |
| Does it pass a right answer  | an assertion a correct answer trips, which scores the skill down for working    |
| Does it fail an empty answer | a case of only negative assertions, which silence satisfies                     |

The middle question inverts deltas, and `not_contains` is where it happens. A wrong answer's
vocabulary is usually a right answer's, so forbidding a word fails thorough answers and passes vague
ones. The plugin is what makes answers thorough, so its arm scores lower.

Ask whether an answer that gets this right would still contain the string. If it would, assert what
the answer concluded.

The last question is the shape of a case whose fixture is clean. Every assertion on it is negative, so
doing no work satisfies them all. Give it something positive to clear.

A requirement is knowable when you write the suite. Its rendering is not. That a review concludes an
item fails is fixed by the fixture. Whether it arrives as a table row, a bold bullet, a symbol or a
sentence is not, and all four are correct.

So write the same correct answer two or three ways in different styles first. One that passes only
one of them is pinned to a wording.

| Rather than                                   | Prefer                                                              |
| --------------------------------------------- | ------------------------------------------------------------------- |
| a pattern guessing how the answer words it     | a check that reads what the answer concluded                        |
| what the answer must not contain              | what it must contain, because absence has unbounded phrasings       |
| every expected finding, unanimously            | a floor, since the agent's consistency is not knowable either       |
| the tool you would have reached for            | the evidence that tool leaves behind, which any route produces      |

The floor is the same argument: demanding every finding assumes zero variance from a
non-deterministic agent. Ask what number would prove the skill did its job.

Make every assertion say what it saw, not only that it failed. Otherwise a skill that got something
wrong and an assertion written wrong look identical in the result document.

## What a case cannot measure without the access it needs

A case that needs access it does not have measures the access rather than the skill.

| The case needs                | Absent, the case measures                                       | The route                                                                   |
| ----------------------------- | ---------------------------------------------------------------- | --------------------------------------------------------------------------- |
| A credential the skill reads  | the credential, and every case fails for a reason that is not the skill | `docker.env_passthrough` names the variable, and a name unset or empty exits 3. See [docker.md](docker.md) |
| A third-party service         | that service's uptime as well as the skill                       | a fixture the case stages, or a `mocks/` stand-in                           |
| An MCP server                 | nothing. The tool is not there                                   | `evals/mocks/<server>/<tool>.md`, which makes the case `no-cowork` and makes `mock_calls` a readable target |
| A tool                        | the grant. A run that never had a granted tool fails rather than scores | `eval.allow_tools`, or the case's own `allowed_tools`, which makes the case `no-cowork`. See [running_evals.md](running_evals.md) |
| A file staged before the run  | a prompt with nothing to read                                    | `context.add_dirs` or `context.scaffold_script` in `case.yaml`, which makes the case `no-cowork` |
| A library a check imports     | nothing about the skill. The suite does not start                | your own project declares it, as for a unit test. The preflight imports every check and exits 3. See [checks.md](checks.md) |
| A wheel the skill imports     | an import error inside the session, in every case at once        | `cowork_evals test` catches it first. See [runtime.md](runtime.md)           |
| The deployed stack            | the container, and not CoWork                                    | the honoured subset in [approaches.md](approaches.md)                       |

Design around the access that exists. When a developer proposes a case that needs access which is not
there, say so before writing it and name the route that would supply it.

## Reading the run

A run leaves a score per case and a list of the assertions that failed. Work out whose fault each
failure is before reporting anything. There are two possibilities: the skill did the wrong thing,
which is what the suite exists to catch, or the assertion would have failed a correct answer too.

Everything the assertions read is still on disk. The run directory holds the final message, the
agent's workspace, the transcript, and the recorded exchange for any check that asked a judge. Open
them. Work out what a correct answer would have looked like, and ask whether the assertion would have
passed it.

| The answer | The failure is | What to do |
| --- | --- | --- |
| It would not have passed | a broken assertion | fix it. The score it produced measured the assertion, not the skill |
| It would have passed | real | report it, and leave the assertion alone |

Answer that from the files, never from the score. Never change an assertion because the number would
look better without it.

Fixing a broken assertion does not mean running the case again. A structural grader and a check are
deterministic over the files the run left, so once the pattern or the Python is corrected you can work
out what it would have said and what the case would have scored. No model call, no second run. The
exception is `--no-keep-traces`, which throws those files away.

Judged assertions are left alone. An `llm` grader, a `baseline` grader and the advisory check over the
route all ask a model, so their verdicts cannot be reproduced by hand. Pass the verdict and its
reasoning through as they stand.

Then send the developer one message: the score per case, every failure with its reason, which were
broken assertions and what you changed, the corrected scores, and what is left as a finding about the
skill.

## What belongs in this file

One question decides whether a statement belongs here or in [eval_format.md](eval_format.md): does it
depend on what the skill under test does?

The `prompt.md` keys, the grader types, the reserved tag and the validator rules do not. Which cases
a suite needs, which grader to prefer, which assertion mechanism a case wants and what a missing
access changes all do. The validator enforces the format; nothing enforces the design.
