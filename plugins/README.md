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

`smoke` holds one case at `evals/plugin/python-version/`, whose prompt asks for
`python3 -V` and whose regex grader matches the exact string
[../docs/runtime.md](../docs/runtime.md) records, so it proves a case reaches a running
command on the interpreter the backend put there. See
[../docs/docker.md](../docs/docker.md) for the container's half of that. Whether this
fixture and each backend it fires are built is the status table in
[../docs/running_evals.md](../docs/running_evals.md).

The exact string carries a patch release, which is the one the image installs, so this
fixture is the container backend's alone. The venv backend stages an interpreter from the
mirror, and the mirror pins `3.10` and takes whatever patch release uv resolves: the staged
one in [../docs/staged_runtime.md](../docs/staged_runtime.md) is a different patch, and the
grader does not match it. The fixture serves the venv backend when that backend pins a patch
release.

It carries no skill. Whether a model activates a skill is an eval question, and this fixture
answers a mechanism question. The case is therefore a `plugin` one: a directory under
`evals/` is a skill name, `plugin` or `mocks`, and there is no skill to name. See
[../docs/eval_format.md](../docs/eval_format.md).

Do not confuse it with `docs/claude_code/eval_smoke/`, which proves the harness itself
works, with nothing from this repository in the way. That one is also written here, not
vendored; see [../docs/claude_code/README.md](../docs/claude_code/README.md). When a run
fails, it tells you whether the problem is the harness or this package.
