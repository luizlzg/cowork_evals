# eval_smoke

A throwaway plugin whose only purpose is to answer one question: does `claude plugin eval`
still work on this machine, independently of anything this repository builds?

Two skills, three cases, and one of each grader type: `regex`, `tool_used` with `min: 1`,
`tool_used` with `min: 0, max: 0`, and `llm`.

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
the CoWork mirror; this one proves only the harness.

Vendored. Do not edit except to repath it.
