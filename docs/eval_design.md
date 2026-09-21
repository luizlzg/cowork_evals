# Eval design

## Summary

This file is about deciding what to evaluate in a Claude CoWork skill, and about writing assertions
that measure the skill rather than the model underneath it. It follows the whole arc of the work:
reading the skill to produce a draft suite, agreeing that draft with the developer, writing the
cases, and reading what a run reports back.

It sits over two other files. [eval_format.md](eval_format.md) is the contract a case file is
written to, and [checks.md](checks.md) is how to write a Python assertion where no grader type will
do. Neither decides what to assert, which is what this file is for. What a finished suite does with
pass and fail is [running_evals.md](running_evals.md), and which backend honours which part of a
case is [approaches.md](approaches.md).

Four things are worth knowing before the rest.

- Reading the skill produces the draft suite. The developer is asked very little, and never asked to
  predict where the skill will fail.
- A case earns its place by measuring something the skill's own text says it does. There is no quota
  to fill and no target number of cases.
- An assertion is only useful if it would fail a wrong answer and pass a right one, and both of
  those are settled before the suite ever runs.
- When a run fails, work out whether the skill was wrong or the assertion was wrong before reporting
  anything.

## How the work goes

A suite starts with reading rather than with questions. The skill under test says what it is for,
names the capabilities it has, and describes what it reads and writes. The repository around it
usually holds a real input. Any suite already there shows what someone previously thought was worth
asserting, and where they stopped. Between them that is enough to draft the whole suite, so draft it
first and bring the developer a draft rather than a questionnaire.

Show that draft before writing any file, as one line per case. Each line says what the case covers in
plain words, what has to be true of the output for the case to pass, what access it needs, and
whether it will carry the `no-cowork` tag. Write it in the vocabulary the skill itself uses rather
than the vocabulary of this file, because a developer reading `the leakage dimension is covered` has
to learn a word before finding out what was tested. At that point they can strike a case in one
sentence. The same objection raised after the files exist costs a rewrite.

Some questions are worth asking and some only cost a turn. The ones that cost a turn ask the
developer to predict failure: where the skill goes wrong, what must never happen, which part breaks
most often. The answer is almost always that they do not know, and the design does not need it,
because the skill's instructions already state what it has to do and a case asserting an instruction
is the case that catches that instruction being broken. Asking which eval or which grader they want
is worse, since it hands the design back to the person who asked for it. Asking for a fixture is no
better: a developer rarely has a sample of the real input to hand, and waiting for one stops the
work, so generate every fixture instead.

That leaves one thing genuinely worth asking about, which is access the repository does not reveal. A
credential the skill reads, a service it calls, an MCP server it needs: nothing under the plugin root
records any of those, so ask.

When a developer says they do not know, that ends the topic. It is the common answer, it is
permission to design that part alone, and asking the same question a second way spends another turn
for nothing.

When a developer does volunteer something, what they give you is a symptom rather than a case, and
turning it into one is the work. `The summaries are too long` becomes a `regex` over `last_message`.
`It makes things up about our schema` becomes a fixture plus a `not_contains` pattern for each
invented value. `It ignores the config file` becomes a `tool_used` grader with an `input_match`
naming that file. `The totals in the spreadsheet come out wrong` becomes a check that opens the
workbook, because no grader type can read a cell.

Once the draft is agreed, write the fixtures, the prompts and the assertions, then run the suite on
`--docker` and again under `--ablation with-without`. Reading what comes back is the last section
here.

## Which cases the suite needs

Skills fail in a small number of recognisable ways, and the table below lists them. Read it against a
draft you already have, as a way of finding a gap you missed. It is not a list to work through in
order, it is not a quota, and it sets no ceiling on how many cases a suite should have.

The default for every row is no case at all. A row earns one when the skill's own text carries the
condition in its applies-when column, and one case often answers several rows at once. A case written
only so that a row has something in it still costs a full run every time the suite is swept, and its
passing says nothing about the skill.

Every grader named below is one of the six types [eval_format.md](eval_format.md) defines, and every
check is [checks.md](checks.md). This file adds neither.

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

Read the applies-when column against the skill's own `SKILL.md`. Where the skill's text does not carry
the condition, the row gets nothing.

Three of these rows need a fixture staged before the run, which means a `context.*` key, which makes
the case `no-cowork`: context relevancy, leakage, and the malformed form of edge cases. For the
leakage row the marked value is always something the case's own fixture carries, never a real
credential forwarded by `docker.env_passthrough`, because `run.log` captures whatever the container
prints. See [docker.md](docker.md).

Nothing enforces this table. `cowork_evals run --require-coverage` checks only that each skill has an
`evals/<skill>/` directory, which is a much weaker thing, and that is why the table is written down
here. See [cli.md](cli.md).

## Measuring the skill and not the model

A suite that only ever runs with the plugin loaded cannot tell you whether the plugin helped. Ask a
model to build a spreadsheet and it will probably build one whether or not your spreadsheet skill is
in the profile. `--ablation with-without` answers that: it runs every case twice, once with the
plugin and once with nothing loaded, and reports the difference between the two scores. It is
`--docker` only, because a CoWork session takes its skills from whatever profile the application is
running and nothing can unload them for one arm. See [approaches.md](approaches.md).

That arm changes what makes a good prompt, because the run without the plugin gets the same prompt as
the run with it. A prompt the model answers just as well unaided produces a delta of zero, so move it
onto something the skill knows and the model does not. A prompt that names the skill, or walks
through its steps, hands the method to the arm that has no skill, so name the outcome instead and let
the skill supply the method. The case worth writing first is the one the model is worst at unaided,
because that is the case that shows what the skill is for.

The same arm puts a second requirement on every assertion. An assertion has to be deep enough to fail
on its own when the skill regresses, or a green suite means nothing, and it has to be able to score in
both arms, or the delta cannot move. Assertions that only hold when the plugin is loaded report the
same delta whatever the baseline produced, and a suite of shallow assertions passes a skill that is
thoroughly broken. Design for the delta whether or not you intend to run the arm, because "would the
model have done this anyway" is the same question either way.

The fixture is the other half of measuring the skill. A skill is a tool over an input, so the fixture
has to be that input at the size and shape of the real one.

| The rule                                              | What the case measures without it                                        |
| ----------------------------------------------------- | ------------------------------------------------------------------------ |
| The fixture is the size of the real input             | an input small enough to reason about unaided measures the model          |
| The prompt does not quote the fixture                 | the arm with no skill answers from the prompt and never opens the file    |
| The boundary the skill handles is in the fixture      | a boundary that appears only at scale is unreachable at four rows         |
| The input is as untidy as the real one                | a fixture with no duplicate, no gap and no stray type exercises no handling |

Realism is also what makes the table in the previous section decidable. Edge cases, hallucination and
context relevancy each need an input that actually carries the thing the row asserts, and a fixture
small enough to read inside the case file carries none of them. Generate a fixture that size rather
than typing one, and commit it. Where the file lives and the key that grants it are
[eval_format.md](eval_format.md).

## Choosing the assertions

Every case carries three assertions, and they answer three different questions.

The first is whether the plugin loaded at all. A `tool_used: Skill` grader answers it, and it belongs
on every case that needs the plugin rather than only on the case written to test activation. Without
it a case can score full marks having never loaded the plugin, whenever the rest of its assertions
are things the model satisfies unaided, and nothing in the result will say so. Under
`--ablation with-without` the harness stops scoring that grader and reports it as an indicator
instead, so it moves no delta; in a one-arm run it gates. See [running_evals.md](running_evals.md).

Firing has a prompt side as well. A skill's description declares the phrases it triggers on, so a
case meant to exercise a capability has to carry one of those phrases, with its words kept together
rather than scattered across a sentence. A case meant to test the trigger boundary deliberately
carries none of them while staying near the subject, so that over-triggering shows. Both halves are
checkable by reading the description and the prompt side by side. A capability the skill documents but
its description declares no phrase for is a finding about the skill worth reporting, not something to
work around in a prompt.

The second assertion is whether the output is right, and there the choice is between a grader and a
check. A grader reads text. `file_exists` reports that a file appeared and says nothing about what is
in it, while `regex` and `llm` are handed a produced file as text. So a skill whose product is a
workbook, a deck, a PDF or an image can satisfy every grader available to it without a single
assertion having looked at the thing it made. A check is the way out, and the mechanism is
[checks.md](checks.md).

Ask the question once per assertion rather than once per case: can a grader type read this target and
say what has to be true of it? If yes it is a grader, and if no it is a check. One case usually
carries both, and the harness refuses a case whose only assertion directory is `checks/`. Prefer the
grader where either would work, because a grader is a file the harness reads while a check is code you
own, maintain and declare the imports of.

| The assertion is over                                    | Why no grader type reaches it                    |
| -------------------------------------------------------- | ------------------------------------------------ |
| What is inside a file that is not text                   | `regex` and `llm` are shown the bytes as text    |
| A value that has to be computed or parsed out            | no grader type computes                          |
| Two produced files that have to agree                    | a grader reads one target                        |
| A file the agent changed rather than created             | `file_exists` globs created files                |
| A property a model has to look at rather than read       | `llm` is shown text, and `run.judge` is shown the paths |

Whichever you pick, prefer a structural grader to a judged one. A judged grader over a
non-deterministic agent gives a flaky verdict, and a judge is noisy on long input. It matters for pass
and fail too, because `llm` and `baseline` results are printed but carry no verdict, so a dimension
resting on one of them leaves the exit code silent about it. A check is the exception worth knowing:
it decides the exit code however it reached its verdict, `run.judge` included, so a question only a
model can settle does not have to end up as a printed note. Checks are also cheap when they are
broken, since every check of every selected plugin is imported before the first case starts, and one
that will not import exits 3 having spent nothing.

## The third assertion, over the route the run took

A grader and a check both read what the run produced, and neither can see how the run got there. A
workbook whose totals are right might have come from the command the skill documents, or from a script
that reimplemented it, and the file is byte-for-byte comparable either way. So a suite of graders and
checks will happily pass a run that never used the skill, and will pass a run that used the skill and
then wrote over its output. On a real spreadsheet suite a case scored 1.00 on a run that called the
skill's own dedup command and then saved a Python script's output over the file it had produced.

The third assertion reads the transcript, and a model is what reads it. It is a check that returns
whatever `run.judge` returned, shown three paths rather than any text so that nothing is truncated:
`run.trace` for the transcript, the `SKILL.md` under test, and the case's own `prompt.md` with its
frontmatter stripped. The prompt is there because the transcript does not carry it. A collected trace
opens on a `system` record and goes straight into the agent's work, so what the agent was asked
appears nowhere in it, and a judge that does not know the task cannot say whether the route suited it.
Reading the prompt file rather than restating the task in the rubric also means editing a prompt moves
the assertion with it.

It asks three questions and no more.

| The question                    | The run fails it when                                                      |
| ------------------------------- | -------------------------------------------------------------------------- |
| Was the route the right one     | the deliverable came from something other than what the skill documents for it, or from a command that ran and was then superseded |
| Were the instructions followed  | the skill states a thing to do, or an order to do it in, and the run did not |
| Was anything invented           | a value in the final message appears in no tool result                      |

Write it as `@check(advisory=True)` until the rubric is calibrated. An advisory check records its real
verdict and decides nothing, so a failure prints as a note and stays out of both the score and the
exit code. A model asked how an agent worked is not yet reliable enough to gate a suite: over three
runs whose right answer was known, one model got two of them and a slower one got one, both erring
towards leniency. The verdict still lands in the result document, which is what you calibrate the
rubric against, and dropping the argument makes the same check binding once the misses stop.

Six things to get right in the rubric, and the first is what makes the assertion a regression test
rather than a snapshot.

| The rule                                                  | Because                                                                    |
| --------------------------------------------------------- | -------------------------------------------------------------------------- |
| Show the judge the skill, not a summary of it             | a rubric that restates the rules captures one reading of them, and keeps passing a run the skill itself would now fail |
| Name the subject and let the judge find the wording       | the assertion then moves with the skill the next time it is edited          |
| Never demand a route the skill cannot take                | read its command list first. A clause asking the impossible fails every run for a gap in the skill |
| Treat a split vote as a rubric fault before a judge fault | usually it is the clause, not the model, that two votes read differently    |
| Judge the route, not the result                           | the graders and the checks already decide whether the numbers are right     |
| Do not hold the baseline arm to it                        | the route and the instructions both belong to the skill, so asserting them with no plugin loaded fails by construction and inflates the delta |

It is the most expensive assertion in a suite and the least deterministic, costing
`eval.judge_votes` model calls per run per arm, so it is one per case and not one per question.
Anything a `regex`, a `file_exists` or a plain check can settle, let them settle.

## Knowing the assertions work before the suite runs

An assertion that cannot fail and an assertion that cannot pass report the same thing on every run,
and both look like working assertions sitting in a case directory. So test every one of them both
ways first: every pattern against one sample that has to match and one that has to not match, and
every check against one artefact that has to pass and one that has to fail. Neither test needs a
model, so both are cheap. Test a pattern in the engine the harness grades with rather than the one
your own tests run in, because two regular expression engines agree on most patterns and not on all
of them, and remember that a `regex` anchor covers the whole target unless `flags` carries `m`.

The artefact that has to pass is the skill's own output. A check that the skill's own output fails is
a broken check rather than a finding, and a full case run is an expensive way to discover that.

Both of those samples are written by the same person who wrote the assertion, though, so passing them
only proves the assertion works against the output that person imagined. There is no real output to
look at when a suite is written and there will not be one until it runs, so the discipline is not to
guess the output better. It is to write assertions that do not depend on having seen it, and three
questions get you there without a run.

| Ask                          | The failure it catches                                                         |
| ---------------------------- | ------------------------------------------------------------------------------ |
| Does it fail a wrong answer  | an assertion that cannot fail. This is the one everybody asks                   |
| Does it pass a right answer  | an assertion a correct answer trips, which scores the skill down for working    |
| Does it fail an empty answer | a case built only from negative assertions, which silence satisfies             |

The second question is the one that inverts a delta, and `not_contains` is usually where it happens.
The vocabulary a wrong answer uses is often the vocabulary a right answer uses, so forbidding a word
can fail every thorough answer while passing every vague one. Since the plugin is what makes answers
thorough, the arm with the plugin then scores below the arm without it, and the number reads as a
broken skill. Ask it as a question about the correct answer, which needs no run: would an answer that
gets this right still contain that string? If it would, move the assertion onto what the answer
concluded rather than which words it used.

The third question catches the shape a case takes when its fixture is clean and there is nothing to
find. Every assertion on such a case is negative, so an answer that did no work satisfies all of
them, and so does the baseline arm. A case like that needs something positive to clear as well, such
as evidence in the output that the work happened.

### Assert the requirement, not the rendering

A requirement is knowable when you write the suite and its rendering is not. That a review concludes
some item fails is fixed by the fixture. Whether that conclusion arrives as a table row, a bold
bullet, a symbol, or a sentence with the verdict before the subject is fixed by nothing, and all four
are correct answers.

One technique makes the difference visible without a run. Before writing the assertion, write the same
correct answer down two or three times in deliberately different styles. An assertion that passes only
one of them is pinned to a rendering, and the fix is usually to move it from a pattern to a check,
because a check can read a whole line or a whole file and decide what it says.

| Rather than                                   | Prefer                                                              |
| --------------------------------------------- | ------------------------------------------------------------------- |
| a pattern guessing how the answer words it     | a check that reads what the answer concluded                        |
| what the answer must not contain              | what it must contain, because absence has unbounded phrasings       |
| every expected finding, unanimously            | a floor, since the agent's consistency is not knowable either       |
| the tool you would have reached for            | the evidence that tool leaves behind, which any route produces      |

The floor in the third row is the same argument as the rest. Demanding every finding assumes zero
variance from a non-deterministic agent, and that assumption is no more available at design time than
the wording is. Ask what number would prove the skill did its job, rather than what number a perfect
run would produce.

Finally, make every assertion say what it saw and not only that it failed. A message naming both the
expectation and the value found is what separates a skill that got something wrong from an assertion
that was written wrong, and without it the two are indistinguishable in a result document.

## What a case cannot measure without the access it needs

A case that needs access it does not have measures the access rather than the skill, and it fails for
a reason that has nothing to do with what is being evaluated.

| The case needs                | Absent, the case measures                                       | The route                                                                   |
| ----------------------------- | ---------------------------------------------------------------- | --------------------------------------------------------------------------- |
| A credential the skill reads  | the credential, and every case fails for a reason that is not the skill | `docker.env_passthrough` names the variable, and a name unset or empty exits 3. See [docker.md](docker.md) |
| A third-party service         | that service's uptime as well as the skill                       | a fixture the case stages, or a `mocks/` stand-in                           |
| An MCP server                 | nothing. The tool is not there                                   | `evals/mocks/<server>/<tool>.md`, which makes the case `no-cowork` and makes `mock_calls` a readable target |
| A tool                        | the grant. A run that never had a granted tool fails rather than scores | `eval.allow_tools`, or the case's own `allowed_tools`, which makes the case `no-cowork`. See [running_evals.md](running_evals.md) |
| A file staged before the run  | a prompt with nothing to read                                    | `context.add_dirs` or `context.scaffold_script` in `case.yaml`, which makes the case `no-cowork` |
| A library a check imports     | nothing about the skill. The suite does not start                | your own project declares it, as it would for a unit test. The preflight imports every check and exits 3. See [checks.md](checks.md) |
| A wheel the skill imports     | an import error inside the session, in every case at once        | `cowork_evals test` catches it before an eval is written over it. See [runtime.md](runtime.md) |
| The deployed stack            | the container, and not CoWork                                    | the honoured subset in [approaches.md](approaches.md)                       |

So design around the access that exists. When a developer proposes a case that needs access which is
not there, say so before writing the case and name the route above that would supply it.

## Reading the run

A run leaves a score for each case and a list of the assertions that failed, and the first thing to do
with a failure is work out whose fault it is. There are two possibilities. Either the skill did the
wrong thing, which is exactly what the suite exists to catch, or the assertion is wrong and would have
failed a correct answer too. Telling those apart is the whole task, and the score is no help with it.

What does help is that everything the assertions read is still on disk. The run directory holds the
final message, the agent's workspace, the transcript, and the recorded exchange for any check that
asked a judge. Open them, work out what a correct answer to that prompt would have looked like, and
ask whether the assertion would have passed it. If it would not have, the assertion is broken, and the
score it produced measured the assertion instead of the skill. If it would have, the failure is real
and the assertion stays exactly as it is. Answer that question from the files rather than from the
score, and never change an assertion because the number would look better without it.

A broken assertion is worth fixing straight away, and fixing it does not mean running the case again.
A structural grader and a check are both deterministic functions of the files the run already left
behind, so once the pattern or the Python is corrected you can work out what it would have said and
what the case would have scored, with no model call and no second run. The one exception is
`--no-keep-traces`, which throws those files away, so a case fixed under it has to run again before it
can be scored at all.

Judged assertions are left alone. An `llm` grader, a `baseline` grader and the advisory check over the
route all ask a model, so their verdicts cannot be reproduced by hand, and a disagreement between two
runs is not by itself evidence of anything wrong with the rubric. Pass the verdict and its reasoning
through as they stand.

Then send the developer one message rather than a conversation, carrying the score for each case,
every failure with the reason it gave, which of those failures turned out to be broken assertions and
what you changed about them, the corrected scores, and whatever is left over as a genuine finding
about the skill.

## What belongs in this file

One question decides whether a statement belongs here or in [eval_format.md](eval_format.md): does it
depend on what the skill under test does? The `prompt.md` keys, the grader types, the reserved tag,
the validator rules and the authoring traps do not, so they are the format's. Which cases a suite
needs, which grader class to prefer, which of the two assertion mechanisms a case wants, and what a
missing access changes all do, so they are here. Where a statement is about a check specifically, the
mechanism is [checks.md](checks.md) and the decision to use one is here. The format is enforced by the
validator, and nothing enforces the design, which is why it is written down.
