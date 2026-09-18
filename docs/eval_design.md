# Eval design

## Summary

Which cases a skill needs, and which assertion answers which question. This is the design
contract over [eval_format.md](eval_format.md), which is the file contract, and over
[checks.md](checks.md), which is the other assertion mechanism. The procedure a session follows
to apply these rules is in the `cowork-evals` skill, which [library.md](library.md) places.

- The coverage table decides which cases a suite needs. Every row that applies to the skill gets
  at least one case, and a row that does not apply gets none.
- An assertion has to fail on its own when the skill regresses, and it has to score in both arms
  of an ablation run.
- The fixture is the real input at its real size. A smaller one measures the model.
- A grader reads text. An assertion over anything else is a check.
- Every pattern and every check is tested against one sample that has to pass and one that has to
  fail, before the first case runs.
- A case that needs access it does not have measures the access and not the skill.

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
format's. A statement that needs the skill's own instructions is here.

The no side is two files, because there are two assertion mechanisms. A statement about a grader
type is [eval_format.md](eval_format.md), and a statement about a check is
[checks.md](checks.md). Which of the two an assertion needs depends on the skill, so it is here.

## The coverage dimensions

The table finds gaps in a suite that is already drafted. It is not a list to work through, and it
is not a quota. Every row that the skill's own text triggers gets at least one case, and one case
may answer more than one row. A case written only to fill a row costs a run on every sweep, and
its pass says nothing about the skill.

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

The applies-when column is read against the skill's own `SKILL.md`. A row the skill's text does
not trigger gets no case.

Six things the table does not decide.

| The rule                                                    | Where the detail is                         |
| ----------------------------------------------------------- | ------------------------------------------- |
| Prefer a structural grader wherever one can decide a row. A judged grader over a non-deterministic agent is a flaky verdict, and a judge is noisy on a long input | [running_evals.md](running_evals.md)        |
| A row whose only grader is `llm` or `baseline` is printed and leaves the exit code silent. Give every row a release depends on a structural grader as well, or a check | [running_evals.md](running_evals.md)        |
| A `regex` anchor covers the whole target unless `flags` carries `m`                     | [eval_format.md](eval_format.md)            |
| Context relevancy, leakage, and the malformed form of edge cases each need a staged fixture, which is a `context.*` key, which makes the case `no-cowork` | [eval_format.md](eval_format.md)            |
| The leakage row's marked value is a fixture the case owns, never a credential `docker.env_passthrough` forwards. `run.log` is captured at the file descriptor level, so a run that prints a forwarded value puts it in the log | [docker.md](docker.md)                      |
| Directory coverage is not dimension coverage. `--require-coverage` enforces one `evals/<skill>/` per skill and nothing enforces this table | [cli.md](cli.md)                            |

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

A fixture at that size is generated rather than typed, and committed rather than staged at run
time. Where the file lives, and the key that grants it, are [eval_format.md](eval_format.md).

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

## Testing an assertion before the first case runs

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

A suite is designed around the access that exists. A case that needs access that is not there is
named as such before it is written, together with the route above that would supply it.
