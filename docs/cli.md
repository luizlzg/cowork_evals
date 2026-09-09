# cowork_evals

The command. One executable, four verbs, three backends. It is the whole surface a consumer
repository sees; the boundary behind it is [library.md](library.md).

What of this command is built is the status table in
[running_evals.md](running_evals.md).

## Synopsis

```
cowork_evals run   (--venv | --docker | --cowork) <path> [options]
cowork_evals setup (--venv | --docker | --all)
cowork_evals check (--venv | --docker | --cowork | --all)
cowork_evals prune [--venv] [--docker] [--logs] [--older-than DAYS]
cowork_evals --version
```

The backend is required on `run` and has no default. A default means an operator reads
`passed` and believes CoWork was exercised. Which backend proves what is
[approaches.md](approaches.md).

## The path is the scope

`run` takes one path. What that path points at decides what runs, and there is no separate
sweep command.

| Path points at                     | Runs                              | Scope name in the log directory |
| ---------------------------------- | --------------------------------- | ------------------------------- |
| a case directory                   | that case                         | `<plugin>-<skill>-<case>`       |
| `evals/<skill>/`                   | that skill's cases                | `<plugin>-<skill>`              |
| `evals/`                           | that plugin's whole suite         | `<plugin>`                      |
| a directory holding several plugins | each plugin in turn, gated once  | `all`                           |

The plugin root is the parent of `evals/`, and it is accepted only when it holds
`.claude-plugin/plugin.json`. A sweep finds plugins by that file, not by a fixed glob.

A multi-plugin path is a usage error on `--cowork`. There is no sweep on that backend, for
the reason in [running_evals.md](running_evals.md).

`run --venv` writes `.cowork-runtime/` into each plugin root it runs, and removes it when
that plugin's run ends. [library.md](library.md) says why that is the one write into a
consumer checkout, and [staged_runtime.md](staged_runtime.md) says what is in it.

A case's `plugins: ["../../.."]` frontmatter states the plugin root a second time.
The case validator checks that the two resolve to the same directory, because the harness
reads the frontmatter and the CoWork backend resolves the path. See
[eval_format.md](eval_format.md).

## Options on run

Named options only. No raw argument tail is forwarded to `claude plugin eval`: that harness
runs on two backends of three, so a pass-through would be silently ignored on the third.

| Option                    | `--venv` | `--docker` | `--cowork`                        |
| ------------------------- | -------- | ---------- | --------------------------------- |
| `--runs N`                | yes      | yes        | yes, replacing each case's own    |
| `--timeout-seconds N`     | refused  | refused    | yes, as each run's `run_timeout`  |
| `--model M`               | yes      | yes        | refused, the session decides      |
| `--judge-model M`         | yes      | yes        | yes, for judged graders           |
| `--allow-tools T...`      | yes      | yes        | refused, the session decides      |
| `--max-cost-usd N`        | yes      | yes        | refused, the driver's `max_runs` binds |
| `--tag T`, `--case GLOB`  | yes      | yes        | yes                               |
| `--out DIR`               | yes      | yes        | yes                               |
| `--build-missing`         | yes      | yes        | refused, nothing to build         |
| `--dry-run`               | yes      | yes        | yes                               |

`--timeout-seconds N` is refused on the two Claude Code backends because
`claude plugin eval` has no timeout flag to map it onto. Only the CoWork backend sets a
per-case `run_timeout` itself.

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

`run` verifies its backend and never builds. An eval run already costs minutes and money,
and a run that silently spends ten more building an image is not readable in a log.

| Backend    | Requires                                                             | Fails when                                                  |
| ---------- | -------------------------------------------------------------------- | ----------------------------------------------------------- |
| `--venv`   | `claude` on `PATH`, the mirror at the current digest, the uv interpreter the mirror was built from | the mirror is absent or stale, `python3 -V` is not 3.10, or the interpreter to stage is absent |
| `--docker` | a Docker or Rancher daemon, the image at the current digest, and the container login | the daemon is down, the image is absent or stale, or there is no login |
| `--cowork` | macOS, the CoWork desktop application, an Accessibility grant        | the grant is missing, so there is no headless route and no CI |

A failed preflight exits 3 and prints one line naming the command that fixes it:

```
mirror is stale: run `cowork_evals setup --venv`
```

`--build-missing` builds instead of failing. It is off by default and exists for unattended
use.

## setup

| Command          | Builds                                                                    | Idempotent                            |
| ---------------- | ------------------------------------------------------------------------- | ------------------------------------- |
| `setup --venv`   | `~/.cache/cowork_evals/venv-<digest>/` from `requirements_installable.txt` | prints `current` and exits 0          |
| `setup --docker` | the image tagged `cowork-evals:<digest>`, then the container login if one is needed | prints `current` and exits 0 |
| `setup --all`    | both                                                                       | both                                  |

`setup --docker` builds one image. Each run gets a fresh container from it, so there is no
long-lived container to create. When no container login exists, it then starts one
interactive container to log in. That step needs a terminal and a browser. See
[docker.md](docker.md).

There is no `setup --cowork`. The desktop application and the Accessibility grant are
installed and granted by hand, and `check --cowork` reports what is missing.

Where each artefact lives, and how each digest is computed, is
[library.md](library.md).

## check

`check` verifies the same conditions as the preflight table above, writes nothing, and never
builds. It exits 0 when every named backend is ready and 3 otherwise, listing each unmet
condition and its fix. `check --all` includes `--cowork`, so it reports the Accessibility
grant on a machine that has no CoWork installed rather than failing the whole invocation.

## prune

Deletes artefacts this CLI created and nothing else.

| Flag                | Deletes                                                       |
| ------------------- | ------------------------------------------------------------- |
| `--venv`            | cached mirrors, except the one at the current digest          |
| `--docker`          | images tagged `cowork-evals:*`, except the current digest     |
| `--logs`            | run directories under the resolved log root                   |
| `--older-than DAYS` | restricts every selection above. Default 30                   |

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

`claude plugin eval` exits 2 on partial results; the venv and Docker backends turn that into
a `partial: true` result document, and the gate turns that into exit 1. See
[plugin_eval.md](plugin_eval.md).

The CoWork driver has its own taxonomy, codes 2 to 8, carried by a raised `CoWorkError` and
never by an exit code. It is in [cowork_driver.md](cowork_driver.md). The `--cowork` backend
maps it:

| Driver code                                            | Becomes                                          |
| ------------------------------------------------------- | ------------------------------------------------ |
| 2, for configuration or the rate ceiling               | Checked in preflight, before any case: exit 3    |
| 2 to 8, raised while running a case                    | That case is an error in the result document, and the gate exits 1 |
| No raise                                               | The case is graded normally                      |
