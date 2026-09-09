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
plugins/<plugin>/tests/<name>.py
```

The layout is the standard one, because a fixture that does not look like a real plugin
proves nothing about discovery. The case format is
[../docs/eval_format.md](../docs/eval_format.md).

`smoke` holds one case at `evals/plugin/python-version/`, whose prompt asks for
`python3 -V` and whose regex grader matches the exact string
[../docs/runtime.md](../docs/runtime.md) records, so it proves a case reaches a running
command on the interpreter the backend put there. See
[../docs/docker.md](../docs/docker.md) for the container's half of that. Whether this
fixture and each backend it fires are built is the status table in
[../docs/running_evals.md](../docs/running_evals.md).

The exact string carries a patch release. The container installs it, and the CoWork VM runs
it, so this fixture serves both backends. The CoWork backend loads no plugin, and this case
needs none: it writes `runs: 1`, carries no skill, and asks for a command any session can
run.

It carries no skill. Whether a model activates a skill is an eval question, and this fixture
answers a mechanism question. The case is therefore a `plugin` one: a directory under
`evals/` is a skill name, `plugin` or `mocks`, and there is no skill to name. See
[../docs/eval_format.md](../docs/eval_format.md).

`smoke/tests/` is the fixture for the test image, and is a fixture and not a suite.
`test_runtime.py` asserts three things a plain Python image fails: the interpreter is
3.10, `import uno` resolves from the LibreOffice deb set, and one pinned CoWork wheel
imports. `test_fails.py` fails on purpose, so the integration tier can prove that pytest's
exit 1 reaches the caller unchanged. Both are outside `testpaths`, so `scripts/test.sh`
collects neither, and both run on the container's 3.10 interpreter. See
[../docs/cowork_test.md](../docs/cowork_test.md).

One plugin root carries both `evals/` and `tests/`, so target resolution reaches each
without a rule of its own.

Do not confuse it with `docs/claude_code/eval_smoke/`, which proves the harness itself
works, with nothing from this repository in the way. That one is also written here, not
vendored; see [../docs/claude_code/README.md](../docs/claude_code/README.md). When a run
fails, it tells you whether the problem is the harness or this package.
