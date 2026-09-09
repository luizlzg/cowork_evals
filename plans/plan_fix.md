# Plan: the consistency fixes

Branch `feat/fix-consistency`. Seven phases.

This plan holds what two audits found on 2026-09-08: one over `src/`, `scripts/` and
`tests/`, one over the documents. Thirty-one items. It waits on nothing, and it runs before
`plan_cowork_backend.md`, because phase 1 changes what that plan and `plan_cli.md` both
read.

## How to work this file

**Every item is a claim, not an instruction. Confirm it before you change anything.** The
audits were read from the files, but line numbers move and an auditor can be wrong. Each
item names the evidence and the check.

| Outcome                        | What to do                                                     |
| ------------------------------ | -------------------------------------------------------------- |
| The claim holds                | Apply the fix, tick the box, commit                            |
| The claim is wrong             | Tick the box and append `not a defect: <one line why>` to it   |
| The fix is bigger than it looks | Tick nothing. Add a line under the item and ask the developer |

Tick a box the moment that item is verified, before starting the next one. Never carry a
finished item unticked, and never tick one that is not verified. The file is the state: a
cleared context resumes from here, so at every instant the ticks must say exactly what is
done.

Commit whenever `scripts/test.sh` and `scripts/lint.sh` are both green, which is normally
one commit per box. Where a box cannot leave the suite green on its own, because the
refactor around it is mid-flight, the tick still goes in immediately and the next green
commit carries it and names in its message which boxes it carries.

The two rules these items are measured against are new, in
[`../CLAUDE.md`](../CLAUDE.md): **One config file** and **A split needs a rule**.

## Out of scope

| Not here                                         | Belongs to               |
| ------------------------------------------------ | ------------------------- |
| The CoWork backend                               | `plan_cowork_backend.md` |
| The command, the gate, the validator             | `plan_cli.md`            |
| The venv backend                                 | `plan_venv.md`, skipped  |
| Any new feature                                  | nobody                   |

Nothing here adds behaviour. Every item removes a duplicate, corrects a false statement, or
merges two routes into one.

## Constraints

- Python 3.14, ruff `target-version = "py314"`.
- No mock, fake, stub, patch or injected seam.
- `scripts/test.sh` passes before every commit. `scripts/lint.sh` too.
- No document links to a plan, this one included.

## Phase 1: One configuration file

The defect: configuration is split between `cowork_evals.yaml`, read by
`src/cowork_evals/config.py`, and `.env` plus the process environment, read by
`src/cowork_evals/env.py`. The two key sets do not overlap, so nothing conflicts. The
problem is that no rule says which side a new setting goes on. The driver was built first
and got a YAML file; `env.py` was built for the container backend and absorbed settings that
are not environmental at all. A model name is a choice, not a fact about the machine.

The developer decided on 2026-09-08 to consolidate onto `cowork_evals.yaml`.

The shape, decided with the developer:

| Section   | Holds                                                                  |
| --------- | ---------------------------------------------------------------------- |
| `cowork:` | `profile`, `surface`, the four timeouts, `max_runs`, `run_log`, `log_dir` |
| `eval:`   | `model`, `judge_model`, `allow_tools`, `max_cost_usd`, `max_cost_total_usd` |
| `docker:` | `platform`, `claude_code_version`, `login_dir`, `extra_ca_file`        |

The rule, which is what the old split lacked: the section is named for the thing that reads
it. `Config` becomes the whole file, holding three frozen nested dataclasses. `CoWork` takes
`config.cowork`.

- [x] Confirm the split is as described. `src/cowork_evals/env.py` `DEFAULTS` should list
      eight names, and `src/cowork_evals/config.py` `_FIELDS` nine.
- [x] `config.py`: three frozen dataclasses, `CoWorkSection`, `EvalSection`,
      `DockerSection`, and a frozen `Config` holding one of each. Keep the existing
      `_FIELDS` idiom: one converter per field, run in `__post_init__`, the key set doubling
      as the accepted-key set. An unknown key inside a known section stays an error. An
      unknown top level section stays ignored.
- [x] Defaults move across unchanged: `model` `sonnet`, `judge_model` `haiku`,
      `allow_tools` `["Bash"]`, `max_cost_usd` 5, `max_cost_total_usd` 25, `platform`
      `linux/arm64`, `claude_code_version` `2.1.265`, `login_dir`
      `~/.cache/cowork_evals/claude`, `extra_ca_file` none.
- [x] `allow_tools` becomes a list in YAML rather than a whitespace-separated string. It
      still replaces the default rather than adding to it, so a widened value names `Bash`
      again.
- [x] `extra_ca_file` is an explicit key. `SSL_CERT_FILE` is no longer read. A machine
      behind a TLS-inspecting proxy names the certificate in `cowork_evals.yaml`.
- [x] `CLAUDE_CODE_WALNUT_SPIRE` becomes a module constant in `harness.py`, not a setting.
      The package exports it into the child; no developer chooses it.
- [x] Delete `src/cowork_evals/env.py` and `tests/unit/test_env.py`. Remove
      `python-dotenv` from `pyproject.toml`.
- [x] `harness.py`: `RunOptions.resolve` takes a `Config` instead of calling `setting()`.
      An explicit argument still beats the file.
- [x] `docker/__init__.py`: `Docker.__init__` takes a `Config` and resolves every setting
      once at construction, `extra_ca_file` included. Today `platform` and
      `claude_code_version` are frozen on the instance while `extra_ca_file` re-reads the
      environment on every property access, against the class docstring's own claim that a
      `Docker` holds frozen configuration.
- [x] `login_dir` uses `Config`'s path convention, which expands `~` and resolves a relative
      path against the working directory. `Docker.__init__` applies only `.expanduser()`
      today, so a relative `login_dir` reaches `docker -v` unresolved.
- [x] `tests/unit/test_config.py` covers the three sections, every default, an unknown key
      in each section, and a wrong type in each section.
- [x] `tests/unit/test_harness.py` and `tests/unit/test_docker.py` build a `Config` rather
      than setting environment variables. The `environment(...)` helper goes if nothing else
      uses it.
- [x] `docs/library.md`: one settings route. Delete the four-layer table and the `.env`
      section. The ladder is: a command-line option beats the file, the file beats the
      built-in default.
- [x] `docs/cowork_driver.md`: the configuration section now describes the `cowork:` section
      of a larger file, and the sentence "`.env` carries credentials and not configuration"
      goes.
- [x] `docs/cli.md` and `docs/running_evals.md`: every `EVAL_*` reference becomes a
      `cowork_evals.yaml` key. `docs/running_evals.md`'s pinned-flag table maps each flag to
      a config key rather than a variable.
- [x] `docs/docker.md`: the `CLAUDE_CODE_VERSION` environment route goes.
- [x] `README.md`: the example `cowork_evals.yaml` shows all three sections.
      not a defect: `README.md` carries no example configuration file. The example lives in
      `docs/library.md`, which owns the settings route, and shows all three sections. The
      layout row at `README.md:53` called the file the driver's and was corrected.

## Phase 2: Statements that are false

Each of these says something the repository contradicts. They are first because a reader
acts on them.

- [x] `docs/cowork_driver.md:106` says "A command line over this library is not built and
      belongs to its own plan." [`../CLAUDE.md`](../CLAUDE.md) forbids a second entry point,
      `docs/cowork_driver.md:40` already says the driver has no console script, and
      `plans/README.md` lists no such plan. Delete the sentence. The driver is reached
      through `cowork_evals run --cowork`, which `docs/cowork_driver.md:27` already says.
- [x] `docs/library.md:155` says the container login applies "when no API key is set".
      `docs/docker.md:224` says there is no API key route and records the developer's
      decision of 2026-09-08. Delete the clause. `docs/docker.md` owns credentials.
- [x] `plans/README.md` marks `plan_docker.md` implemented, while
      `docs/running_evals.md:326` still reads `not yet measured` for the Docker smoke row.
      `plans/README.md:126` says a row reading that means the box filling it is not ticked.
      `docs/docker.md:198` records that the run happened on 2026-09-08. Either recover the
      wall clock and cost from that run and fill the row, or re-run
      `plugins/smoke/evals` through the container and record what it costs. Until one of
      those, `plan_docker.md` is not implemented and `plans/README.md` should say so.
      The run's `aggregate-result.json` survives on disk, so the row is filled from it and
      `plan_docker.md` stays implemented. No container was fired.
- [x] `README.md:27-33` shows three example commands, all `--venv`. That backend is not
      built and its plan is skipped. Change the quickstart to `--docker`, the built one.
- [x] `docs/README.md:42` classifies `cowork_driver.md` as design. It is built:
      `docs/running_evals.md:31` says so, and so does `docs/cowork_driver.md:11`. Fixed by
      the phase 5 item that removes the classification from the index.
      The classification now reads part built, so the index no longer contradicts the
      status table. The phase 5 item still removes the sentence.
- [x] `docs/README.md:29` says two files here are measurements. Four are:
      `docs/running_evals.md:116` and `:143`, `docs/docker.md:382-408` and
      `docs/staged_runtime.md:77-97` all carry dated snapshots. Replace the enumeration with
      the rule: any dated snapshot is re-probed when its subject changes.

## Phase 3: One name per artifact

The defect: "result document" names two different things.
`docs/cowork_driver.md:258` uses it for the driver's per-session dictionary and says that
dictionary holds exactly seventeen keys. `docs/cowork_driver.md:302` then says a skip is
written into "the result document", which those seventeen keys have no room for. A skip
belongs in `aggregate-result.json`, which `docs/running_evals.md:228` and
`docs/cli.md:157` also call "the result document".

- [x] Confirm both uses exist and refer to different artifacts.
      Both exist. The driver's document holds sixteen keys, not seventeen.
- [ ] Rename the driver's output to **session document** throughout
      `docs/cowork_driver.md`: the section title at `:258`, the method table at `:69-72`,
      and `:26`, `:286` and `:297`.
- [ ] "Result document" then means `aggregate-result.json` v1 and nothing else, everywhere.
- [ ] `docs/cowork_driver.md:302-306` reads correctly once renamed: a skip is written into
      the result document, which is the aggregate.
- [ ] `src/cowork_evals/cowork.py` docstrings and `tests/` follow the same rename.
- [ ] `plans/plan_cowork_backend.md` follows it too. That plan reads the driver's output on
      every second line and currently inherits the ambiguity.

## Phase 4: The code defects

Five findings that can produce a wrong result rather than a wrong reading.

- [ ] `tests/integration/test_docker.py:55-78` builds its own container argument list,
      copying the preamble from `src/cowork_evals/docker/__init__.py:203-232`: `--platform`,
      `--user`, `HOME`, `CLAUDE_CODE_WALNUT_SPIRE`, both `--security-opt` values. The tests
      that prove bubblewrap starts and the mounts behave therefore assert against argv the
      test built. Check it: delete `systempaths=unconfined` from `run_argv` and see whether
      any test fails. If none does, factor the shared preamble into one method that both
      `run_argv` and the test call. [`../tests/README.md`](../tests/README.md) forbids a
      stand-in.
- [ ] `src/cowork_evals/docker/__init__.py:42-53` sets `CONTAINER_HOME`, `CONTAINER_PLUGIN`,
      `CONTAINER_LOGS`, `EXTRA_CA_SECRET` and `CONTAINER_EXTRA_CA`, and
      `docker/Dockerfile:101`, `:102` and `:167-168` write the same five literals again.
      `Docker.digest` hashes the Dockerfile but not the Python constants, so editing the
      Python side leaves a cached image that never created the path. Pass them to the
      Dockerfile as `ARG`s from `build_argv`, or at minimum add them to the digest input.
- [ ] `scripts/image.sh:35` filters `Docker.check()` output with
      `not line.startswith("no credential")`. `check()` returns free text, and rewording the
      message at `docker/__init__.py:347` silently changes what `image.sh --check` reports.
      Give `check()` a discriminator: return `(condition, message)` pairs, or split it into
      `check_image()` and `check_credential()`.
- [ ] `src/cowork_evals/docker/probe.py:42-44` probes `ssh`, `bwrap` and `socat`, and
      `parity.compare()` iterates `EXPECTED_VERSIONS` and `ABSENT` only, so those three
      results are discarded. `docker/Dockerfile:24-27` says `bwrap` and `socat` are what the
      Bash sandbox needs. Assert in `compare()` that the probed key set equals
      `EXPECTED_VERSIONS | ABSENT`, and add the three somewhere they are read.
- [ ] Three implementations of PEP 503 name normalisation disagree:
      `docker/parity.py:60-68` uses `packaging.canonicalize_name`,
      `tests/unit/test_environments.py:36-47` uses a local `re.sub`, and
      `scripts/cowork_venv.sh:43-45` uses awk. The awk one does not fold a run of separators
      to one hyphen, so `foo__bar` normalises differently in the shell than in Python. Put
      one `normalize()` in the package, import it in the test, and have `cowork_venv.sh`
      call it through `uv run python3 -c`.

## Phase 5: Facts written more than once

[`../CLAUDE.md`](../CLAUDE.md) says each index owns its rules and nothing restates them.
Each item below names the one file that should own the fact.

- [ ] Build status appears in eleven files, against `docs/running_evals.md:15`, "Nothing
      else carries one; they link here". The restatements are at `README.md:19-20`,
      `docs/approaches.md:6-7` and `:132-135`, `docs/cli.md:6`, `docs/library.md:9-11`,
      `docs/docker.md:11-14`, `docs/cowork_driver.md:11-12`, `docs/environments.md:22-24`,
      `docs/staged_runtime.md:7`, `docs/README.md:41-43`, `plugins/README.md:20` and `:26`.
      Replace each with a link. `docs/running_evals.md` owns build status.
- [ ] `docs/running_evals.md:21` bundles the package and the CLI into one `no` row. The
      package exists on disk; only `[project.scripts]` is missing, which
      `docs/library.md:30` states correctly. Split the row in two.
- [ ] The Bash sandbox readable set is stated near-verbatim in `docs/running_evals.md:94-97`,
      `docs/staged_runtime.md:15-17`, `docs/environments.md:86-91` and
      `docs/approaches.md:89-93`. Keep it in `docs/staged_runtime.md`, which
      `docs/README.md:25` assigns that subject, and link from the other three.
- [ ] The `.cowork-runtime/` staging exception is stated in `docs/running_evals.md:109-111`,
      `docs/library.md:159-163`, `docs/staged_runtime.md:71-75` and `docs/cli.md:41-43`.
      Keep it in `docs/library.md`, which owns where state lives, and link from the rest.
- [ ] `docs/cowork_driver.md:6-9` says the measured application internals are in
      `docs/cowork_desktop.md` and "Do not restate them here", then restates three of them:
      the 14336 character cap at `:234-235` against `docs/cowork_desktop.md:66-67`, the
      verbatim prompt record at `:230-232` against `:153-154`, and the transcript reading
      rules at `:242-256` against `:102-118`. State only the design decision in
      `cowork_driver.md` and link the measured value.
- [ ] `docs/approaches.md:51` says the CoWork backend honours no `runs` value, while
      `docs/running_evals.md:62-65` says `runs: 1` and an absent key both run once. The
      smoke fixture writes `runs: 1`. `plan_cowork_backend.md` phase 2 rewrites both rows
      anyway, so this item is a check that it did, not a separate edit.
- [ ] `README.md:68-75` restates the script index and omits `scripts/login.sh`, which
      `scripts/README.md:24` and `tests/README.md:88-92` both call a precondition of the
      integration tier. Replace the block with the commands a first clone needs and a link.
      `scripts/README.md` owns the task list.
- [ ] `docs/library.md:162` says the consumer git-ignores "`logs/`, `.cowork-runtime/` and
      `.env`, and nothing else". `cowork_evals.yaml` names a profile, which is an
      identifier, and this repository's own `.gitignore:29` ignores it. After phase 1 every
      consumer has one. Correct the list. `.env` comes out of it in phase 1.
- [ ] `3.10.12` is written in `docker/parity.py:32`,
      `tests/integration/test_docker.py:30`, and the smoke grader's pattern and filename.
      Have the integration test read `parity.EXPECTED_VERSIONS["python3"]`. The grader has
      to stay a literal, because it runs in the sandbox, so give it a comment naming
      `parity.py` as the sibling to update.
- [ ] `src/cowork_evals/harness.py:20` holds `DEBUG_FILE_NAME` and
      `docker/__init__.py:47` holds `RESULT_NAME`. Both are rows of the log layout at
      `docs/running_evals.md:264-266` and both belong to the harness, not to one backend:
      the CoWork and venv backends write `aggregate-result.json` too. Move `RESULT_NAME`
      into `harness.py`.
- [ ] One condition has four remedies. `docker/__init__.py:345` and `:347` print
      `cowork_evals setup --docker`, which does not exist yet; `scripts/login.sh:36` says
      `scripts/login.sh`; `tests/integration/test_docker.py:43` and `:93` say
      `scripts/image.sh`; `scripts/README.md:24` says both scripts. One function should
      return the remedy per condition, and it names the script until the command exists.

## Phase 6: Smaller items

- [ ] `src/cowork_evals/cowork.py:63` chooses between `Config.load(**overrides)` and the
      private `_override(config, overrides)` imported from `config.py`, two mechanisms for
      one rule that `docs/cowork_driver.md:191` states once. Make it one function.
- [ ] `CoWork.from_file` at `src/cowork_evals/cowork.py:66-69` has no caller and no test,
      and is a third route to the same two lines. It is documented at
      `docs/cowork_driver.md:187`, so it is a designed surface. Add a test or ask the
      developer to drop it.
- [ ] `working_directory` is defined twice, at `tests/conftest.py:65-80` and
      `tests/unit/test_config.py:15-22`, with the module-level one shadowing the fixture.
      Delete the local one.
- [ ] `scripts/image.sh:19-27` and `scripts/login.sh:20-28` dispatch on `$1` twice, and the
      `--check` arms setting `NO_CACHE=""` and `FORCE=""` are unreachable because the second
      `if` execs. Those values are interpolated into a `python3 -c` heredoc, so an empty one
      would generate `docker.build(no_cache=)`. Move `--check` into the single `case`, as
      every other script in `scripts/` does.
- [ ] `scripts/cowork_venv.sh:29-30` keeps `TEST_ONLY_DIRECT` and `TEST_ONLY_ALL`, the
      second being the hand-written transitive closure of the first. A pytest release that
      gains a dependency makes `--check` report a spurious extra package. Derive the closure
      or drop that half of the check.
- [ ] `docs/claude_code/eval_smoke/run.sh` is shell and is linted by nothing:
      `scripts/lint.sh:28` and `tests/unit/test_environments.py:96` both glob `scripts/*.sh`
      only. Widen both globs, or write the exemption into
      `docs/claude_code/README.md`.
- [ ] `src/cowork_evals/docker/__init__.py:9` links a module docstring to `plan_cli.md`.
      Documentation never links to a plan. Point it at `docs/cli.md`.
- [ ] Four files call a file a "page", against the writing rules:
      `docker/parity.py:8`, `docker/__init__.py:8`, `tests/unit/test_env.py:84` (deleted in
      phase 1) and `tests/integration/test_docker.py:29`.
- [ ] `max_cost_total_usd` is defaulted, documented and tested, and read nowhere. After
      phase 1 it is a YAML key nothing reads. Mark it in `config.py` as belonging to the
      unbuilt gate, naming `plan_cli.md` phase 6 as what will read it, or leave it out until
      then.
- [ ] The smoke grader matches `Python 3\.10\.12`, but `docs/staged_runtime.md:118` records
      the staged interpreter as 3.10.16, and `docs/running_evals.md:33` says the fixture
      serves both Claude Code backends. It cannot serve the venv one as written. Loosen the
      pattern to `Python 3\.10\.` and rename the grader file, or record in
      `plugins/README.md` that the fixture is container-only until the venv backend pins a
      patch release. The container assertion in `docs/docker.md:93` stays exact either way.

## Phase 7: The index, and the boundary that has no rule

- [ ] `docs/README.md` gains a row for `docs/claude_code/`. `docs/eval_format.md:10` calls
      the vendored reference the authority where it is silent, and the index that owns
      reference material omits the directory holding it.
- [ ] `tests/README.md:4-5` lists what the suite covers and omits the container and parity
      work that its own table at `:41-44` lists as existing.
- [ ] `plans/README.md` describes plan 3 in the present tense at `:45`, `:53` and `:59-65`
      while marking it skipped at `:28`. Say once that the following sections describe it as
      designed.
- [ ] `docs/running_evals.md:28` is the one status row naming no design file, reading
      `nowhere yet`. Either write the design or say in the row that it is deliberately
      undesigned.
- [ ] Nothing states which subjects belong to `docs/running_evals.md` and which to
      `docs/staged_runtime.md`. `running_evals.md:4` calls itself design that is "true
      whether or not a given piece is built", yet it holds the sole record of what is built,
      the staged runtime reasoning at `:75-111`, and a host measurement at `:114-158`.
      `docs/README.md:25` assigns the staged runtime subject to `staged_runtime.md`. Move
      `:75-111` and `:114-158` there. Then decide where build status lives and write that
      rule into `docs/README.md`. This is the same defect as phase 1, in the documents.
- [ ] Re-read every file this plan touched for a statement it made false.
- [ ] `plans/README.md`: add this plan to the table and mark it `implemented`.
