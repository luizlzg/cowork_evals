# eval_smoke

A throwaway plugin whose only purpose is to answer one question: does `claude plugin eval`
still work on this machine, independently of anything this repository builds?

Two skills, three cases, and six graders covering four shapes: `regex`, `tool_used` with
`min: 1`, `tool_used` with `min: 0, max: 0`, and `llm`.

```bash
docs/claude_code/eval_smoke/run.sh                    # all three cases
docs/claude_code/eval_smoke/run.sh --case 'capital-*' # one case or a glob
```

`run.sh` calls `claude plugin eval` directly. It does not use `cowork_evals`, does not
write to `logs/`, and is not gated: when the harness is what you
are debugging, this repository's wrapper is one more thing that can be wrong.

It also proves the enablement variable works, because it exports it.

Not a plugin under test. It lives under `docs/` because it is reference material, and it is
never released, registered or packaged. `plugins/smoke/` is the separate case that proves
a case reaches a running command on the interpreter the container backend put there; this
one proves only the harness.

## It does not follow this repository's case format

[`../../eval_format.md`](../../eval_format.md) puts a case at `evals/<skill>/<case>/`, with
`tags:` and `plugins: ["../../.."]`. These cases sit at `evals/<case>/` with no `tags:` and
`plugins: ["../.."]`, which is the harness's own shape and nothing else.

They also write out `max_turns` and `allowed_tools`. The CoWork backend honours neither, and
a case that writes out a key that backend cannot honour is skipped there, which fails the
gate. See [`../../running_evals.md`](../../running_evals.md). These cases never run on that
backend, so it costs them nothing. Do not copy those two keys into a case that has to run on
both.

That is deliberate and it is the point of the directory. When the harness is what you are
debugging, every convention this repository adds is one more thing that can be wrong. The
case validator skips this tree.

Written here, not vendored. Edit it when it is wrong.
