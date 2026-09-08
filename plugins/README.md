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

`smoke` is designed and not built. Its one skill reports the interpreter version and its
grader asserts 3.10, so it proves the staged runtime reaches a running case. See
[../docs/staged_runtime.md](../docs/staged_runtime.md). The status table for
everything unbuilt is [../docs/running_evals.md](../docs/running_evals.md).

Do not confuse it with `docs/claude_code/eval_smoke/`, which proves the harness itself
works, with nothing from this repository in the way. That one is also written here, not
vendored; see [../docs/claude_code/README.md](../docs/claude_code/README.md). When a run
fails, it tells you whether the problem is the harness or this package.
