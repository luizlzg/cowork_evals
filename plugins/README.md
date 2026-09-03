# plugins

Plugins under test. One directory per plugin, in the standard Claude Code layout.

```
plugins/<plugin>/.claude-plugin/plugin.json
plugins/<plugin>/skills/<skill>/SKILL.md
plugins/<plugin>/evals/<skill>/<case>/prompt.md
plugins/<plugin>/evals/<skill>/<case>/graders/<name>.md
```

`claude plugin eval` loads exactly one plugin per run, so a case that spans two plugins is
not expressible. See [../docs/plugin_eval.md](../docs/plugin_eval.md) for the case format
and its limits.

A plugin here is either developed in this repository or copied in from the marketplace
repository that owns it. Copy it, do not symlink it: the harness resolves the plugin root
from the case's `plugins:` frontmatter, and a symlink makes that path ambiguous.

`smoke` is the exception. It proves the CoWork mirror reaches a running case: its one skill
reports the interpreter version, and its grader asserts 3.10. It is not a shipped plugin and
is never a source of eval coverage.

Do not confuse it with `docs/claude_code/eval_smoke/`, which is vendored and proves the
harness itself works, with no wrapper from this repository in the way. When a run fails,
that one tells you whether the problem is the harness or this repository.
