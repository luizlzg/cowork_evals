# cowork_evals

## Summary

The command. One executable, four verbs, two backends. It is the whole surface a consumer
repository sees; the boundary behind it is [library.md](library.md).

- **The backend is required on `run`** and has no default. Which backend proves what is
  [approaches.md](approaches.md).
- **The path is the scope.** One path argument decides whether a case, a skill, a plugin or a
  whole tree runs. There is no separate sweep command.
- **Options are named.** Nothing is forwarded raw to `claude plugin eval`.
- **`run` verifies and never builds.** A failed preflight exits 3 and names the command that
  fixes it.
- **The exit code is the CLI's.** No backend's code reaches an operator unchanged.

What of this command is built is the status table in
[running_evals.md](running_evals.md).

## Synopsis

```
cowork_evals run   (--docker | --cowork) <path> [options]
cowork_evals setup (--docker | --all)
cowork_evals check (--docker | --cowork | --all)
cowork_evals prune [--docker] [--logs] [--older-than DAYS]
cowork_evals --version
```

`setup --all` is `setup --docker` today, and stays in the surface so the three verbs that
take a backend read the same.

## The path is the scope

`run` takes one path. What that path points at decides what runs.

| Path points at                      | Runs                            | Scope name in the log directory |
| ----------------------------------- | ------------------------------- | ------------------------------- |
| a case directory                    | that case                       | `<plugin>-<skill>-<case>`       |
| `evals/<skill>/`                    | that skill's cases              | `<plugin>-<skill>`              |
| `evals/`                            | that plugin's whole suite       | `<plugin>`                      |
| a directory holding several plugins | each plugin in turn, gated once | `all`                           |

The plugin root is the parent of `evals/`, and it is accepted only when it holds
`.claude-plugin/plugin.json`. A sweep finds plugins by that file, not by a fixed glob.

A multi-plugin path is a usage error on `--cowork`. There is no sweep on that backend, for
the reason in [running_evals.md](running_evals.md).

A case's `plugins: ["../../.."]` frontmatter states the plugin root a second time. The case
validator checks that the two resolve to the same directory, because the harness reads the
frontmatter and the CoWork backend resolves the path. See
[eval_format.md](eval_format.md).

## Options on run

Named options only. No raw argument tail is forwarded to `claude plugin eval`: that harness
runs on one backend of two, so a pass-through would be silently ignored on the other.

| Option                   | `--docker` | `--cowork`                             |
| ------------------------ | ---------- | -------------------------------------- |
| `--runs N`               | yes        | yes, replacing each case's own         |
| `--timeout-seconds N`    | refused    | yes, as each run's `run_timeout`       |
| `--model M`              | yes        | refused, the session decides           |
| `--judge-model M`        | yes        | yes, for judged graders                |
| `--allow-tools T...`     | yes        | refused, the session decides           |
| `--max-cost-usd N`       | yes        | refused, the driver's `max_runs` binds |
| `--tag T`, `--case GLOB` | yes        | yes                                    |
| `--out DIR`              | yes        | yes                                    |
| `--build-missing`        | yes        | refused, nothing to build              |
| `--dry-run`              | yes        | yes                                    |

`--timeout-seconds N` is refused on the Docker backend because `claude plugin eval` has no
timeout flag to map it onto. Only the CoWork backend sets a per-case `run_timeout` itself.

Defaults come from the `eval:` section of `cowork_evals.yaml`, in
[running_evals.md](running_evals.md), which also says which underlying flag each option maps
to and why that flag is pinned. An option beats the file, and the file beats the built-in
default; the ladder is [library.md](library.md). Two pinned flags have no option:
`--threshold`, because the gate decides, and `--ablation`, because a baseline arm changes
which graders are scored. `eval.max_cost_total_usd` has no option either; it bounds the
invocation rather than a run.

An option the chosen backend cannot honour is refused at parse time. That is an operator
mistake, so it is a usage error. A *case* that needs a field the backend cannot honour is
reported skipped and fails the gate. The two are different and are never conflated.

`--dry-run` prints the command line it would run, one argument per line, and exits 0 without
running anything or creating a run directory. Pruning of old run directories happens before
that exit, so it is exercised too. The tests assert over this, so the option surface, the
backend mapping and the target's position ahead of the variadic flags are covered without a
live run.

## Preflight

`run` verifies its backend and never builds. An eval run already costs minutes and money, and
a run that silently spends ten more building an image is not readable in a log.

| Backend    | Requires                                                             | Fails when                                                  |
| ---------- | -------------------------------------------------------------------- | ----------------------------------------------------------- |
| `--docker` | a Docker or Rancher daemon, the image at the current digest, and the container login | the daemon is down, the image is absent or stale, or there is no login |
| `--cowork` | macOS, the CoWork desktop application, an Accessibility grant, `claude` on `PATH`, and the suite inside the driver's `max_runs` | the grant is missing, so there is no headless route and no CI, or `claude` is absent, or the suite would exceed the ceiling |

A failed preflight exits 3 and prints one line naming the command that fixes it:

```
image is stale: run `cowork_evals setup --docker`
```

`--build-missing` builds instead of failing. It is off by default and exists for unattended
use.

`claude` is a `--cowork` precondition because the judge behind an `llm` or `baseline` grader
is `claude -p`, and because `claudeVersion` in the result document is the host
`claude --version`. The signed-in CLI is the one credential route; there is no second one.

Host spend on `--cowork` is the judge alone. The CoWork session itself is billed to the
signed-in account and is not observable from the host, so `--max-cost-usd` is refused there
and the ceiling that binds is the driver's `max_runs`. See
[cowork_driver.md](cowork_driver.md).

## setup

| Command          | Builds                                                                             | Idempotent                   |
| ---------------- | ---------------------------------------------------------------------------------- | ---------------------------- |
| `setup --docker` | the image tagged `cowork-evals:<digest>`, then the container login if one is needed | prints `current` and exits 0 |
| `setup --all`    | the same                                                                            | the same                     |

`setup --docker` builds one image. Each run gets a fresh container from it, so there is no
long-lived container to create. When no container login exists, it then starts one
interactive container to log in. That step needs a terminal and a browser. See
[docker.md](docker.md).

There is no `setup --cowork`. The desktop application and the Accessibility grant are
installed and granted by hand, and `check --cowork` reports what is missing.

Where each artefact lives, and how the digest is computed, is [library.md](library.md).

## check

`check` verifies the same conditions as the preflight table above, writes nothing, and never
builds. It exits 0 when every named backend is ready and 3 otherwise, listing each unmet
condition and its fix. `check --all` includes `--cowork`, so it reports the Accessibility
grant on a machine that has no CoWork installed rather than failing the whole invocation.

## prune

Deletes artefacts this CLI created and nothing else.

| Flag                | Deletes                                                   |
| ------------------- | --------------------------------------------------------- |
| `--docker`          | images tagged `cowork-evals:*`, except the current digest |
| `--logs`            | run directories under the resolved log root               |
| `--older-than DAYS` | restricts every selection above. Default 30               |

`run` prunes log directories older than 30 days on its own, so `prune --logs` is for
reclaiming space on purpose. `prune --docker` leaves the container login alone: it is a
credential, not a build product, and deleting it forces an interactive login.

## Exit codes

| Code | Means                                                                       |
| ---- | --------------------------------------------------------------------------- |
| 0    | the gate passed, or the verb succeeded                                      |
| 1    | the gate failed. The conditions are in [running_evals.md](running_evals.md) |
| 2    | usage error: unknown option, an option the backend refuses, or no path      |
| 3    | preflight failed. Nothing ran and nothing was written                       |
| 130  | interrupted                                                                 |

The exit code is the CLI's, and no backend's code reaches an operator unchanged.

`claude plugin eval` exits 2 on partial results; the Docker backend turns that into a
`partial: true` result document, and the gate turns that into exit 1. See
[plugin_eval.md](plugin_eval.md).

The CoWork driver has its own taxonomy, codes 2 to 8, carried by a raised `CoWorkError` and
never by an exit code. It is in [cowork_driver.md](cowork_driver.md). The `--cowork` backend
maps it:

| Driver code                              | Becomes                                                            |
| ---------------------------------------- | ------------------------------------------------------------------ |
| 2, for configuration or the rate ceiling | Checked in preflight, before any case: exit 3                      |
| 2 to 8, raised while running a case      | That case is an error in the result document, and the gate exits 1 |
| No raise                                 | The case is graded normally                                        |
