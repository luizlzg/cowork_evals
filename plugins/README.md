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
```

The layout is the standard one, because a fixture that does not look like a real plugin
proves nothing about discovery. The case format is
[../docs/eval_format.md](../docs/eval_format.md).

`smoke` is built. One case at `evals/plugin/python-version/`, whose prompt asks for
`python3 -V` and whose regex grader matches the exact string
[../docs/runtime.md](../docs/runtime.md) records, so it proves a case reaches a running
command on the interpreter the backend put there. See
[../docs/staged_runtime.md](../docs/staged_runtime.md) for the venv backend's half of that
and [../docs/docker.md](../docs/docker.md) for the container's. The status table for
everything unbuilt is [../docs/running_evals.md](../docs/running_evals.md).

The case is a `plugin` one, not a skill one, because a directory under `evals/` is a skill
name, `plugin` or `mocks`, and this plugin carries no skill. See
[../docs/eval_format.md](../docs/eval_format.md).

It carries no skill. Whether a model activates a skill is an eval question, and this fixture
answers a mechanism question.

Do not confuse it with `docs/claude_code/eval_smoke/`, which proves the harness itself
works, with nothing from this repository in the way. That one is also written here, not
vendored; see [../docs/claude_code/README.md](../docs/claude_code/README.md). When a run
fails, it tells you whether the problem is the harness or this package.
