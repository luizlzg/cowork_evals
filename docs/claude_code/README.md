# Claude Code reference

Reference material for `claude plugin eval`. Two of the three files here are vendored.

| File                                                   | Is                                          | Ours |
| ------------------------------------------------------- | -------------------------------------------- | ---- |
| [`plugin_eval_quickref.md`](plugin_eval_quickref.md)   | Anthropic's condensed harness reference     | no   |
| [`plugin_eval_reference.md`](plugin_eval_reference.md) | Anthropic's full harness reference: every flag, grader, sandbox detail and the results JSON field by field | no |
| [`eval_smoke/`](eval_smoke/)                           | A runnable throwaway plugin that proves the harness works | yes |

`eval_smoke/` was written here and is edited like any other file in this repository. It sits
under `docs/` because it is reference material, not because it came from outside. See
[`eval_smoke/README.md`](eval_smoke/README.md).

## Provenance of the two vendored documents

`claude plugin eval` is in early access and has no public documentation page. The CLI
carries both documents zstd-compressed inside the executable. They were extracted from
CLI 2.1.252 and are reproduced verbatim.

They do not follow this repository's writing rules, and they are not edited. Re-extract
after a `claude update` that changes the harness, and record the new version here:

```python
import re, subprocess, pathlib

b = pathlib.Path("<path to the claude executable>").read_bytes()
for m in re.finditer(re.escape(b"\x28\xb5\x2f\xfd"), b):
    d = subprocess.run(
        ["zstd", "-d", "-q", "--stdout", "-"],
        input=b[m.start() : m.start() + 4_000_000],
        capture_output=True,
    ).stdout
    if b"plugin eval" in d and b"grader" in d:
        pathlib.Path(f"doc_{m.start():08x}.md").write_bytes(d)
```

[`../plugin_eval.md`](../plugin_eval.md) is this repository's own summary of the same
material, written to the rules in `CLAUDE.md`. Read that first. Come here for a detail it
does not carry, and prefer `claude plugin eval --help` in your own build over both when
they disagree.
