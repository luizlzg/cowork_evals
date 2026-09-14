# plugins

Fixture plugins for this repository's own tests. Not shipped, and not a source of eval
coverage for anything.

Plugins under test live in the repository that owns them and installs this package. See
[../docs/library.md](../docs/library.md).

```
plugins/<plugin>/.claude-plugin/plugin.json
plugins/<plugin>/skills/<skill>/SKILL.md
plugins/<plugin>/evals/<skill>/<case>/prompt.md
plugins/<plugin>/evals/<skill>/<case>/graders/<name>.md
plugins/<plugin>/evals/<skill>/<case>/checks/<name>.py
plugins/<plugin>/tests/<name>.py
```

The layout is the standard one, because a fixture that does not look like a real plugin
proves nothing about discovery. The case format is
[../docs/eval_format.md](../docs/eval_format.md).

`smoke` holds four cases, all under `evals/plugin/`.

| Case            | Asks for                              | Graded by                                    |
| --------------- | ------------------------------------- | -------------------------------------------- |
| `python-version` | `python3 -V`                         | a `regex` grader over the last message       |
| `writes-a-file` | one word written to `written.txt`     | a `file_exists` grader over the created file |
| `capped-turns`  | one word in the reply                 | a `regex` grader over the last message       |
| `checked-file`  | one word written to `written.txt`     | a `file_exists` grader, and two checks over the file's contents |

`python-version` matches the exact string [../docs/runtime.md](../docs/runtime.md) records, so
it proves a case reaches a running command on the interpreter the backend put there. See
[../docs/docker.md](../docs/docker.md) for the container's half of that. Whether this
fixture and each backend it fires are built is the status table in
[../docs/running_evals.md](../docs/running_evals.md).

`writes-a-file` is the fixture for the run validity check. It writes no `allowed_tools`, so
`Write` reaches it from the operator grant alone: under the default grant the file is created
and the case passes, and under a grant that omits `Write` the run cannot create it and the
verdict fails the run by name rather than scoring what the model wrote instead. The narrowing
belongs to `integration/test_cli.py`, which types it as `--allow-tools`, and the default grant
in `cowork_evals.yaml` is untouched. The two conditions are
[../docs/running_evals.md](../docs/running_evals.md).

The exact string carries a patch release. The container installs it, and the CoWork VM runs
it, so this fixture serves both backends. The CoWork backend loads no plugin, and no case here
needs one: each writes `runs: 1`, carries no skill, and asks for something any session can do.

`checked-file` is the fixture for the check layer. It asks for the same file `writes-a-file`
asks for, and asserts what is inside it, which no grader type can express: the `file_exists`
grader beside the checks sees that the file appeared and never what it says. The grader is
also what makes the case loadable at all, because the harness refuses a case carrying no
grader; see [../docs/eval_format.md](../docs/eval_format.md). It carries two checks on purpose.
`the_file_says_written` passes, and `the_file_is_a_workbook` fails, so one run produces the
`FAIL` line, the appended grader result, the `checks.jsonl` line and the `scratch/` directory
that `integration/test_cli.py` reads. It is the only case here that always exits 1, which is
what `smoke/tests/test_fails.py` is for the test image. It carries no `no-cowork` tag: a check
runs on the host after the run is graded, and needs nothing a session cannot do. See
[../docs/checks.md](../docs/checks.md).

`capped-turns` is the fixture for the `no-cowork` tag. It writes `max_turns`, which no CoWork
session honours, so it carries the tag and satisfies both directions the validator checks. On
the container backend it runs like any other case and passes. On CoWork it is not submitted
and is counted, which is what makes it the one case here that an integration test drives
through that backend without a VM boot, a ceiling entry or a session. The tag is
[../docs/eval_format.md](../docs/eval_format.md).

Four cases, and each integration test that fires one names it with a case glob. A test about
one mechanism pays for one case, and a CoWork test that submits pays for one VM boot.

None carries a skill. Whether a model activates a skill is an eval question, and this
fixture answers a mechanism question. All four cases are therefore `plugin` ones: a directory
under `evals/` is a skill name, `plugin` or `mocks`, and there is no skill to name. See
[../docs/eval_format.md](../docs/eval_format.md).

`smoke/tests/` is the fixture for the test image, and is a fixture and not a suite. Four
files, one exit code each, run one at a time by the integration tier.

| File                | Is                                                                | Exits |
| ------------------- | ------------------------------------------------------------------- | ----- |
| `test_passes.py`    | One `assert True`. A green suite that asserts nothing about the runtime | 0 |
| `test_runtime.py`   | Three things a plain Python image fails: the interpreter is 3.10, `import uno` resolves from the LibreOffice deb set, and one pinned CoWork wheel imports | 0 |
| `test_fails.py`     | One assertion that is false                                       | 1     |
| `test_needs_311.py` | `except*`, which is 3.11 grammar and does not parse on 3.10       | 2     |

The last one is the failure the test image exists to produce: a suite written against a
newer interpreter than a session has fails here, rather than passing on a laptop and failing
in a session. It is a syntax error on the interpreter it runs on, so it cannot be collected
alongside another file, and running the directory as a whole exits 2 for that reason alone.

All four are outside `testpaths`, so `scripts/test.sh` collects none of them, and all four
run on the container's 3.10 interpreter. `test_needs_311.py` is also the one file ruff does
not read, named in `[tool.ruff] extend-exclude`: ruff targets `py310` and the file exists in
order not to parse there. See [../docs/cowork_test.md](../docs/cowork_test.md).

One plugin root carries both `evals/` and `tests/`, so target resolution reaches each
without a rule of its own.

Do not confuse it with `docs/claude_code/eval_smoke/`, which proves the harness itself
works, with nothing from this repository in the way. That one is also written here, not
vendored; see [../docs/claude_code/README.md](../docs/claude_code/README.md). When a run
fails, it tells you whether the problem is the harness or this package.
