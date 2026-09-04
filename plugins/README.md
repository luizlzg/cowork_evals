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

`smoke` proves the CoWork mirror reaches a running case: its one skill reports the
interpreter version, and its grader asserts 3.10.

Do not confuse it with `docs/claude_code/eval_smoke/`, which is vendored and proves the
harness itself works, with nothing from this repository in the way. When a run fails, that
one tells you whether the problem is the harness or this package.
